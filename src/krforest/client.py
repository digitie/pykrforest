"""사용자용 산림청 공공데이터 클라이언트."""

from __future__ import annotations

import csv
import io
import json
import os
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.parse import urljoin

from kraddr.base import Address, PlaceCoordinate

from ._convert import strip_or_none
from ._http import ForestHttp, SessionLike
from .catalog import api_endpoint, api_endpoints, file_dataset, file_datasets
from .exceptions import ForestAuthError, ForestNoDataError, ForestParseError, ForestRequestError
from .models import (
    ApiEndpoint,
    ErosionControlDam,
    FileDataset,
    MountainWeather,
    Page,
    RawRecord,
    RecreationForest,
    RecreationForestReservation,
)

DEFAULT_ENV_NAMES = (
    "KRFOREST_SERVICE_KEY",
    "PYKRFOREST_SERVICE_KEY",
    "KFS_SERVICE_KEY",
    "FOREST_SERVICE_KEY",
    "DATA_GO_SERVICE_KEY",
    "TRIPMATE_DATA_GO_SERVICE_KEY",
)
T = TypeVar("T")

_RECREATION_FOREST_PROMOTION_ID = "15064415"
_RECREATION_FOREST_FACILITY_ID = "15064419"
_RECREATION_FOREST_POLICY_ID = "15064416"
_RECREATION_FOREST_RESERVATION_FILE_ID = "15064418"

_INSTITUTION_ID_KEYS = (
    "institution_id",
    "insttId",
    "insttid",
    "기관ID",
    "기관아이디",
    "기관코드",
    "휴양림ID",
)
_INSTITUTION_NAME_KEYS = (
    "institution_name",
    "insttNm",
    "insttnm",
    "기관명",
    "휴양림명",
    "자연휴양림명",
    "명칭",
)
_GOODS_NAME_KEYS = ("goodsNm", "goodsnm", "상품명", "객실명", "시설명")
_STAY_DATE_KEYS = ("stngDt", "stngdt", "숙박일자", "이용일자")
_STATUS_KEYS = ("status", "상태", "예약상태")
_PHONE_KEYS = ("phone_number", "전화번호", "대표전화번호", "연락처", "tel", "telNo")
_CAPACITY_KEYS = ("capacity", "최대수용인원", "수용인원", "정원")
_OPERATION_TIME_KEYS = ("operation_time", "운영시간", "이용시간")
_HOMEPAGE_KEYS = ("homepage_url", "홈페이지", "홈페이지주소", "url", "URL")
_REGION_KEYS = ("region", "지역", "시도", "시군구")
_DESCRIPTION_KEYS = ("description", "설명", "소개", "개요", "내용")
_EXTRA_ADDRESS_KEYS = ("소재지도로명주소", "기본주소", "주소지")


class ForestClient:
    """정리된 산림청 여행·안전 공공데이터 클라이언트.

    이 클라이언트는 두 계열의 공공데이터를 다룬다.

    * legacy ``api.forest.go.kr`` 숲길·산림문화 endpoint
    * ``apis.data.go.kr`` 산불, 산사태, 산악기상 endpoint

    파일데이터는 ``client.files``에서 정리된 카탈로그와 data.go.kr 상세 페이지의
    다운로드 URL 탐색 기능으로 제공한다.
    """

    def __init__(
        self,
        service_key: str | None = None,
        *,
        timeout: float = 10.0,
        session: SessionLike | None = None,
        service_key_param: str = "ServiceKey",
    ) -> None:
        key = service_key or _first_env(DEFAULT_ENV_NAMES)
        if not key:
            names = ", ".join(DEFAULT_ENV_NAMES)
            raise ForestAuthError(
                f"service_key is required. Pass service_key=... or set one of: {names}",
                failure_kind="auth",
            )
        self.service_key = key
        self.timeout = timeout
        self._http = ForestHttp(
            key,
            timeout=timeout,
            session=session,
            service_key_param=service_key_param,
        )
        self.travel = TravelNamespace(self)
        self.safety = SafetyNamespace(self)
        self.files = FileDataNamespace(self)

    @classmethod
    def from_env(
        cls,
        name: str = "KRFOREST_SERVICE_KEY",
        *,
        fallback_names: tuple[str, ...] = (
            "PYKRFOREST_SERVICE_KEY",
            "KFS_SERVICE_KEY",
            "FOREST_SERVICE_KEY",
            "DATA_GO_SERVICE_KEY",
            "TRIPMATE_DATA_GO_SERVICE_KEY",
        ),
        **kwargs: Any,
    ) -> ForestClient:
        service_key = os.getenv(name) or _first_env(fallback_names)
        if not service_key:
            names = ", ".join((name, *fallback_names))
            raise ForestAuthError(f"none of these environment variables are set: {names}")
        return cls(service_key=service_key, **kwargs)

    def endpoints(self, category: str | None = None) -> tuple[ApiEndpoint, ...]:
        """정리된 API endpoint 메타데이터를 반환한다."""

        return api_endpoints(category)

    def file_datasets(self, category: str | None = None) -> tuple[FileDataset, ...]:
        """정리된 파일데이터 메타데이터를 반환한다."""

        return file_datasets(category)

    def raw_endpoint(
        self,
        endpoint_key: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_format: str | None = None,
    ) -> Page[RawRecord]:
        """정리된 endpoint key로 호출하고 raw item mapping을 반환한다."""

        endpoint = api_endpoint(endpoint_key)
        return self._page(
            endpoint,
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            lambda row: row,
            response_format=response_format,
        )

    def iter_pages(
        self,
        fetch_page: Callable[..., Page[T]],
        *args: Any,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> Iterator[Page[T]]:
        """Page를 반환하는 클라이언트 메서드를 페이지 단위로 순회한다."""

        fetched = 0
        current = page_no
        pages = 0
        while True:
            page = fetch_page(*args, page_no=current, num_of_rows=num_of_rows, **kwargs)
            if page.is_empty:
                return
            yield page
            pages += 1
            fetched += len(page.items)
            if max_pages is not None and pages >= max_pages:
                return
            if max_items is not None and fetched >= max_items:
                return
            if not page.has_next_page or page.next_page_no is None:
                return
            current = page.next_page_no

    def _page(
        self,
        endpoint: ApiEndpoint,
        params: Mapping[str, Any] | None,
        parser: Callable[[dict[str, Any]], T],
        *,
        response_format: str | None = None,
    ) -> Page[T]:
        fmt = response_format or endpoint.response_format or (
            "json" if endpoint.provider == "data.go.kr" else "xml"
        )
        payload = self._http.get(
            endpoint.url,
            dict(params or {}),
            provider=endpoint.provider,
            endpoint=endpoint.operation,
            response_format=fmt,
            service_key_param=endpoint.service_key_param,
        )
        parsed: list[T] = []
        for row in payload.items:
            try:
                parsed.append(parser(row))
            except (TypeError, ValueError) as exc:
                raise ForestParseError(
                    f"{endpoint.key}: failed to parse item: {exc}",
                    provider=endpoint.provider,
                    endpoint=endpoint.operation,
                    failure_kind="parse",
                    response=row,
                ) from exc
        return Page(
            items=tuple(parsed),
            total_count=payload.total_count or len(parsed),
            page_no=payload.page_no or int(params.get("pageNo", 1) if params else 1),
            num_of_rows=payload.num_of_rows
            or int(params.get("numOfRows", len(parsed)) if params else 10),
            raw=payload.raw,
            header=payload.header,
            context=payload.context,
        )


@dataclass(frozen=True, slots=True)
class TravelNamespace:
    _client: ForestClient

    def forest_services(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """숲서비스와 둘레길 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "forest_trail_services",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def mountain_stories(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산 정보 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "mountain_stories",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def forest_spatial_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """등산로 산림공간정보 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "forest_spatial_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def baekdu_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """백두대간 등산로 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "baekdu_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def famous_mountain_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """명산등산로 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "famous_mountain_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def mountain_weather(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[MountainWeather]:
        """국립산림과학원 산악기상 레코드를 조회한다."""

        return self._client._page(
            api_endpoint("mountain_weather"),
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            lambda row: MountainWeather(
                coordinate=PlaceCoordinate.from_mapping(row),
                raw=row,
            ),
        )

    def recreation_forest_reservations(
        self,
        *,
        goods_name: str | None = None,
        start_stay_date: str | None = None,
        end_stay_date: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RecreationForestReservation]:
        """국립자연휴양림 예약정보 OpenAPI 레코드를 조회한다."""

        query = dict(params)
        query["goodsNm"] = goods_name
        query["startStngDt"] = start_stay_date
        query["endStngDt"] = end_stay_date
        return self._client._page(
            api_endpoint("national_recreation_forest_reservations"),
            _page_params(query, page_no=page_no, num_of_rows=num_of_rows),
            _parse_recreation_forest_reservation,
            response_format="xml",
        )

    def recreation_forests(
        self,
        *,
        name: str | None = None,
        institution_id: str | None = None,
    ) -> tuple[RecreationForest, ...]:
        """휴양림 파일데이터를 조합해 위치, 주소, 시설, 예약 상세정보를 반환한다."""

        promotion_rows = _csv_records(
            self._client.files.download(_RECREATION_FOREST_PROMOTION_ID)
        )
        facility_rows = _csv_records(self._client.files.download(_RECREATION_FOREST_FACILITY_ID))
        policy_rows = _csv_records(self._client.files.download(_RECREATION_FOREST_POLICY_ID))
        reservation_rows = _csv_records(
            self._client.files.download(_RECREATION_FOREST_RESERVATION_FILE_ID)
        )
        return _build_recreation_forests(
            promotion_rows,
            facility_rows,
            policy_rows,
            reservation_rows,
            name=name,
            institution_id=institution_id,
        )


@dataclass(frozen=True, slots=True)
class SafetyNamespace:
    _client: ForestClient

    def wildfire_stats(
        self,
        *,
        search_start_date: str | None = None,
        search_end_date: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산불 발생 통계 레코드를 조회한다."""

        query = dict(params)
        query["searchStDt"] = search_start_date
        query["searchEdDt"] = search_end_date
        return self._client.raw_endpoint(
            "wildfire_stats",
            query,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def wildfire_risk_forecast(
        self,
        *,
        exclude_forecast: bool | int | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """전국 산불위험 예보지수 레코드를 조회한다."""

        query = dict(params)
        if exclude_forecast is not None:
            query["excludeForecast"] = int(bool(exclude_forecast))
        return self._client.raw_endpoint(
            "wildfire_risk_forecast",
            query,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def past_landslides(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """과거 산사태 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "past_landslides",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def landslide_predictions(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산사태 예측정보 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "landslide_predictions",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def landslide_forecast_issues(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산사태 예보발령 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "landslide_forecast_issues",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def roadside_landslides(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """도로변 산사태 예방·복구 레코드를 조회한다."""

        return self._client.raw_endpoint(
            "roadside_landslides",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def erosion_control_dams(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[ErosionControlDam]:
        """사방댐 레코드를 조회한다."""

        return self._client._page(
            api_endpoint("erosion_control_dams"),
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            lambda row: ErosionControlDam(
                coordinate=PlaceCoordinate.from_mapping(row),
                raw=row,
            ),
        )


@dataclass(frozen=True, slots=True)
class FileDataNamespace:
    _client: ForestClient

    def datasets(self, category: str | None = None) -> tuple[FileDataset, ...]:
        """정리된 파일데이터 목록을 반환한다."""

        return file_datasets(category)

    def dataset(self, data_go_id: str) -> FileDataset:
        """정리된 파일데이터 하나를 반환한다."""

        return file_dataset(data_go_id)

    def download_url(self, data_go_id: str) -> str:
        """상세 페이지에서 data.go.kr 직접 파일 다운로드 URL을 찾는다."""

        dataset = file_dataset(data_go_id)
        response = _get_detail_page(
            self._client._http.session,
            dataset.detail_url,
            timeout=self._client.timeout,
        )
        if int(response.status_code) in {401, 403}:
            raise ForestAuthError(
                f"HTTP {response.status_code}: {response.text[:200]}",
                provider="data.go.kr",
                endpoint=dataset.detail_url,
                status_code=int(response.status_code),
                failure_kind="auth",
            )
        if int(response.status_code) >= 400:
            raise ForestRequestError(
                f"HTTP {response.status_code}: {response.text[:200]}",
                provider="data.go.kr",
                endpoint=dataset.detail_url,
                status_code=int(response.status_code),
                failure_kind="request",
            )
        return _extract_download_url(response.text, base_url=dataset.detail_url)

    def download(self, data_go_id: str, *, max_bytes: int | None = None) -> bytes:
        """정리된 파일데이터를 다운로드해 bytes로 반환한다."""

        url = self.download_url(data_go_id)
        return self._client._http.get_bytes(url, max_bytes=max_bytes)


KrForestClient = ForestClient
PyKrForestClient = ForestClient


def _first_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _page_params(
    params: Mapping[str, Any] | None,
    *,
    page_no: int,
    num_of_rows: int,
) -> dict[str, Any]:
    if page_no < 1:
        raise ValueError("page_no must be >= 1")
    if not 1 <= num_of_rows <= 1000:
        raise ValueError("num_of_rows must be between 1 and 1000")
    query = {"pageNo": page_no, "numOfRows": num_of_rows}
    if params:
        query.update(dict(params))
    return query


def _parse_recreation_forest_reservation(row: dict[str, Any]) -> RecreationForestReservation:
    return RecreationForestReservation(
        institution_id=_first_text(row, *_INSTITUTION_ID_KEYS),
        institution_name=_first_text(row, *_INSTITUTION_NAME_KEYS),
        goods_name=_first_text(row, *_GOODS_NAME_KEYS),
        stay_date=_first_text(row, *_STAY_DATE_KEYS),
        status=_first_text(row, *_STATUS_KEYS),
        raw=row,
    )


def _build_recreation_forests(
    promotion_rows: tuple[dict[str, str], ...],
    facility_rows: tuple[dict[str, str], ...],
    policy_rows: tuple[dict[str, str], ...],
    reservation_rows: tuple[dict[str, str], ...],
    *,
    name: str | None,
    institution_id: str | None,
) -> tuple[RecreationForest, ...]:
    facility_index = _index_rows(facility_rows)
    policy_index = _index_rows(policy_rows)
    reservation_index = _index_rows(reservation_rows)
    forests: list[RecreationForest] = []
    name_filter = strip_or_none(name)
    institution_filter = strip_or_none(institution_id)

    for base_row in _recreation_forest_base_rows(
        promotion_rows,
        facility_rows,
        policy_rows,
        reservation_rows,
    ):
        forest_id = _first_text(base_row, *_INSTITUTION_ID_KEYS)
        forest_name = _first_text(base_row, *_INSTITUTION_NAME_KEYS)
        if institution_filter is not None and forest_id != institution_filter:
            continue
        if name_filter is not None and name_filter not in (forest_name or ""):
            continue

        facilities = _lookup_rows(facility_index, forest_id=forest_id, name=forest_name)
        policies = _lookup_rows(policy_index, forest_id=forest_id, name=forest_name)
        reservations = _lookup_rows(reservation_index, forest_id=forest_id, name=forest_name)
        detail_rows: tuple[Mapping[str, Any], ...] = (base_row, *facilities)

        address = Address.from_mapping(base_row)
        if address is None:
            text = _first_text(base_row, *_EXTRA_ADDRESS_KEYS)
            address = Address.from_text(text) if text is not None else None
        if address is None:
            for row in facilities:
                address = Address.from_mapping(row)
                if address is None:
                    text = _first_text(row, *_EXTRA_ADDRESS_KEYS)
                    address = Address.from_text(text) if text is not None else None
                if address is not None:
                    break

        coordinate = PlaceCoordinate.from_mapping(base_row)
        if coordinate is None:
            for row in facilities:
                coordinate = PlaceCoordinate.from_mapping(row)
                if coordinate is not None:
                    break

        forests.append(
            RecreationForest(
                institution_id=forest_id,
                name=forest_name,
                coordinate=coordinate,
                address=address,
                phone_number=_first_text_from_rows(detail_rows, *_PHONE_KEYS),
                capacity=_first_text_from_rows(detail_rows, *_CAPACITY_KEYS),
                operation_time=_first_text_from_rows(detail_rows, *_OPERATION_TIME_KEYS),
                homepage_url=_first_text_from_rows(detail_rows, *_HOMEPAGE_KEYS),
                region=_first_text_from_rows(detail_rows, *_REGION_KEYS),
                description=_first_text_from_rows(detail_rows, *_DESCRIPTION_KEYS),
                facilities=facilities,
                reservation_policies=policies,
                reservation_records=tuple(
                    _parse_recreation_forest_reservation(dict(row)) for row in reservations
                ),
                raw={
                    "promotion": base_row,
                    "facilities": facilities,
                    "reservation_policies": policies,
                    "reservation_file_records": reservations,
                },
            )
        )
    return tuple(forests)


def _csv_records(data: bytes) -> tuple[dict[str, str], ...]:
    text = _decode_csv_text(data)
    if not text.strip():
        return ()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return ()
    records: list[dict[str, str]] = []
    for row in reader:
        record: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            clean_key = key.strip()
            clean_value = strip_or_none(value)
            if clean_key and clean_value is not None:
                record[clean_key] = clean_value
        if record:
            records.append(record)
    return tuple(records)


def _decode_csv_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ForestParseError(
        "CSV file dataset encoding is neither UTF-8 nor CP949",
        provider="data.go.kr",
        failure_kind="parse",
    )


def _recreation_forest_base_rows(
    promotion_rows: tuple[dict[str, str], ...],
    facility_rows: tuple[dict[str, str], ...],
    policy_rows: tuple[dict[str, str], ...],
    reservation_rows: tuple[dict[str, str], ...],
) -> tuple[dict[str, str], ...]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for row in (*promotion_rows, *facility_rows, *policy_rows, *reservation_rows):
        keys = _forest_index_keys(row)
        if not keys:
            continue
        if seen.intersection(keys):
            continue
        seen.update(keys)
        rows.append(row)
    return tuple(rows)


def _index_rows(rows: tuple[dict[str, str], ...]) -> dict[str, tuple[dict[str, str], ...]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        for key in _forest_index_keys(row):
            groups.setdefault(key, []).append(row)
    return {key: tuple(value) for key, value in groups.items()}


def _lookup_rows(
    index: Mapping[str, tuple[dict[str, str], ...]],
    *,
    forest_id: str | None,
    name: str | None,
) -> tuple[dict[str, str], ...]:
    keys: list[str] = []
    if forest_id:
        keys.append(f"id:{forest_id}")
    if name:
        keys.append(f"name:{name}")
    rows: list[dict[str, str]] = []
    seen: set[int] = set()
    for key in keys:
        for row in index.get(key, ()):
            identity = id(row)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(row)
    return tuple(rows)


def _forest_index_keys(row: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    forest_id = _first_text(row, *_INSTITUTION_ID_KEYS)
    forest_name = _first_text(row, *_INSTITUTION_NAME_KEYS)
    if forest_id is not None:
        keys.append(f"id:{forest_id}")
    if forest_name is not None:
        keys.append(f"name:{forest_name}")
    return tuple(keys)


def _first_text_from_rows(rows: tuple[Mapping[str, Any], ...], *keys: str) -> str | None:
    for row in rows:
        value = _first_text(row, *keys)
        if value is not None:
            return value
    return None


def _first_text(row: Mapping[str, Any], *keys: str) -> str | None:
    lower_key_map = {str(key).lower(): key for key in row}
    for key in keys:
        value = strip_or_none(row.get(key))
        if value is not None:
            return value
        actual_key = lower_key_map.get(key.lower())
        if actual_key is None:
            continue
        value = strip_or_none(row.get(actual_key))
        if value is not None:
            return value
    return None


def _extract_download_url(html: str, *, base_url: str) -> str:
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        text = match.group(1).strip()
        try:
            data = json.loads(text)
        except ValueError:
            continue
        urls = list(_walk_content_urls(data))
        if urls:
            return urljoin(base_url, urls[0])

    fallback_match = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
    if fallback_match:
        return str(urljoin(base_url, fallback_match.group(1).replace("\\/", "/")))

    raise ForestNoDataError(
        "data.go.kr file detail page did not contain a DataDownload contentUrl",
        provider="data.go.kr",
        endpoint=base_url,
        failure_kind="no_data",
    )


def _get_detail_page(session: SessionLike, url: str, *, timeout: float) -> Any:
    try:
        return session.get(url, timeout=timeout)
    except Exception as exc:
        fallback = url.replace("https://www.data.go.kr/", "http://www.data.go.kr/", 1)
        if fallback == url:
            raise ForestRequestError(
                f"failed to fetch data.go.kr file detail page: {exc}",
                provider="data.go.kr",
                endpoint=url,
                failure_kind="network",
            ) from exc
        try:
            return session.get(fallback, timeout=timeout)
        except Exception as fallback_exc:
            raise ForestRequestError(
                f"failed to fetch data.go.kr file detail page: {fallback_exc}",
                provider="data.go.kr",
                endpoint=url,
                failure_kind="network",
            ) from fallback_exc


def _walk_content_urls(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        content_url = value.get("contentUrl")
        if isinstance(content_url, str) and content_url:
            yield content_url
        for child in value.values():
            yield from _walk_content_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_content_urls(child)
