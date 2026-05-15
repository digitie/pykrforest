"""사용자용 산림청 공공데이터 클라이언트."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.parse import urljoin

from ._http import ForestHttp, SessionLike
from .catalog import (
    FOREST_GO_FILE_DOWNLOAD_HISTORY_URL,
    FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
    api_endpoint,
    api_endpoints,
    catalog_entries,
    catalog_entry,
    file_dataset,
    file_datasets,
)
from .debug import DebugRun, jsonable, redact_sensitive
from .exceptions import (
    ForestApiError,
    ForestAuthError,
    ForestNoDataError,
    ForestParseError,
    ForestRequestError,
)
from .models import (
    ApiEndpoint,
    CatalogEntry,
    ErosionControlDam,
    FileDataset,
    ForestSpatialPoint,
    MountainWeather,
    Page,
    RawRecord,
    RecreationForest,
    RecreationForestReservation,
    StandardRecreationForest,
)
from .parser import (
    parse_erosion_control_dam,
    parse_mountain_weather,
    parse_recreation_forest_reservation,
    parse_standard_recreation_forest,
)
from .processor import (
    RECREATION_FOREST_FACILITY_ID,
    RECREATION_FOREST_POLICY_ID,
    RECREATION_FOREST_PROMOTION_ID,
    RECREATION_FOREST_RESERVATION_FILE_ID,
    build_recreation_forests,
    csv_records,
)
from .spatial import forest_spatial_points

DEFAULT_ENV_NAMES = (
    "KRFOREST_SERVICE_KEY",
    "PYKRFOREST_SERVICE_KEY",
    "KFS_SERVICE_KEY",
    "FOREST_SERVICE_KEY",
    "DATA_GO_SERVICE_KEY",
    "TRIPMATE_DATA_GO_SERVICE_KEY",
)
T = TypeVar("T")


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
        key = _normalize_service_key(service_key) or _first_env(DEFAULT_ENV_NAMES)
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

    def catalog(self, category: str | None = None) -> tuple[CatalogEntry, ...]:
        """디버그 UI와 선택 목록에 쓸 human-readable 카탈로그를 반환한다."""

        return catalog_entries(category)

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

    def debug_endpoint(
        self,
        endpoint_key: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_format: str | None = None,
    ) -> DebugRun:
        """디버그 UI가 사용할 수 있는 endpoint replay용 실행 결과를 반환한다."""

        endpoint = api_endpoint(endpoint_key)
        fmt = response_format or endpoint.response_format or (
            "json" if endpoint.provider == "data.go.kr" else "xml"
        )
        trace = [
            f"endpoint={endpoint.key}",
            f"provider={endpoint.provider}",
            f"response_format={fmt}",
        ]
        entry = catalog_entry(endpoint.key)
        input_data = {
            "endpoint_key": endpoint_key,
            "params": dict(params or {}),
            "page_no": page_no,
            "num_of_rows": num_of_rows,
            "response_format": response_format,
        }
        request: dict[str, Any] = {}
        try:
            query = _page_params(params, page_no=page_no, num_of_rows=num_of_rows)
            request = {
                "method": "GET",
                "url": endpoint.url,
                "query": {key: value for key, value in query.items() if value is not None},
                "headers": {"Accept": "application/json" if fmt == "json" else "application/xml"},
            }
            page = self.raw_endpoint(
                endpoint_key,
                params,
                page_no=page_no,
                num_of_rows=num_of_rows,
                response_format=response_format,
            )
        except ForestApiError as exc:
            trace.append("failed")
            return DebugRun(
                function=endpoint.key,
                input=redact_sensitive(jsonable(input_data)),
                request=redact_sensitive(jsonable(request)),
                response={},
                parsed=None,
                processed=None,
                trace=trace,
                catalog=jsonable(entry),
                error={
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "metadata": redact_sensitive(jsonable(exc.metadata)),
                },
            )
        except Exception as exc:
            trace.append("failed")
            return DebugRun(
                function=endpoint.key,
                input=redact_sensitive(jsonable(input_data)),
                request=redact_sensitive(jsonable(request)),
                response={},
                parsed=None,
                processed=None,
                trace=trace,
                catalog=jsonable(entry),
                error={
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "metadata": {},
                },
            )

        trace.append("success")
        request["url"] = page.context.request_url or endpoint.url
        request["query"] = dict(page.context.request_params)
        response = {
            "status_code": 200,
            "headers": {},
            "body": page.raw,
        }
        return DebugRun(
            function=endpoint.key,
            input=redact_sensitive(jsonable(input_data)),
            request=redact_sensitive(jsonable(request)),
            response=redact_sensitive(jsonable(response)),
            parsed=page,
            processed=page,
            trace=trace,
            catalog=jsonable(entry),
        )

    def debug_raw_endpoint(
        self,
        endpoint_key: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_format: str | None = None,
    ) -> DebugRun:
        """기존 명칭과 명확성을 위한 raw endpoint 디버그 alias."""

        return self.debug_endpoint(
            endpoint_key,
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
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
            response_type_param=endpoint.response_type_param,
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
            parse_mountain_weather,
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
            parse_recreation_forest_reservation,
            response_format="xml",
        )

    def standard_recreation_forests(
        self,
        *,
        name: str | None = None,
        sido_name: str | None = None,
        forest_type: str | None = None,
        accommodation_available: str | bool | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[StandardRecreationForest]:
        """전국휴양림표준데이터 OpenAPI 레코드를 주소와 좌표 포함 모델로 조회한다."""

        query = dict(params)
        query["rcrfrstNm"] = name
        query["ctprvnNm"] = sido_name
        query["rcrfrstType"] = forest_type
        query["stayngPosblYn"] = _yn_value(accommodation_available)
        return self._client._page(
            api_endpoint("standard_recreation_forests"),
            _page_params(query, page_no=page_no, num_of_rows=num_of_rows),
            parse_standard_recreation_forest,
        )

    def kid_forest_centers(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """산림청 유아숲체험원 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000220")
        data = self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    def recreation_forest_arboretums(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """산림청 휴양림수목원 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000180")
        data = self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    def recreation_forests(
        self,
        *,
        name: str | None = None,
        institution_id: str | None = None,
    ) -> tuple[RecreationForest, ...]:
        """휴양림 파일데이터를 조합해 위치, 주소, 시설, 예약 상세정보를 반환한다."""

        promotion_rows = csv_records(
            self._client.files.download(RECREATION_FOREST_PROMOTION_ID)
        )
        facility_rows = csv_records(self._client.files.download(RECREATION_FOREST_FACILITY_ID))
        policy_rows = csv_records(self._client.files.download(RECREATION_FOREST_POLICY_ID))
        reservation_rows = csv_records(
            self._client.files.download(RECREATION_FOREST_RESERVATION_FILE_ID)
        )
        return build_recreation_forests(
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
            parse_erosion_control_dam,
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
        if dataset.provider == "forest.go.kr":
            if dataset.download_url is None:
                raise ForestNoDataError(
                    "forest.go.kr file dataset does not define a download URL",
                    provider=dataset.provider,
                    endpoint=dataset.detail_url,
                    failure_kind="no_data",
                )
            return dataset.download_url
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

        dataset = file_dataset(data_go_id)
        if dataset.provider == "forest.go.kr":
            _submit_forest_go_download_history(
                self._client._http.session,
                dataset,
                timeout=self._client.timeout,
            )
        url = self.download_url(data_go_id)
        return self._client._http.get_bytes(
            url,
            max_bytes=max_bytes,
            provider=dataset.provider,
            endpoint=dataset.data_go_id,
        )


KrForestClient = ForestClient
PyKrForestClient = ForestClient


def _first_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = _normalize_service_key(os.getenv(name))
        if value:
            return value
    return None


def _normalize_service_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = "".join(str(value).split())
    return key or None


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


def _yn_value(value: str | bool | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "Y" if value else "N"
    return value


def _submit_forest_go_download_history(
    session: SessionLike,
    dataset: FileDataset,
    *,
    timeout: float,
) -> None:
    if dataset.download_path is None or dataset.source_path is None:
        return

    popup_params = {
        "pblicDataId": dataset.data_go_id,
        "tabs": "3",
        "searchSrvc": "",
        "subTitle": "",
        "fileNum": dataset.download_path,
        "url": dataset.source_path,
    }
    try:
        popup = _forest_go_request_with_retry(
            lambda: session.get(
                FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
                params=popup_params,
                timeout=timeout,
            ),
            dataset=dataset,
            endpoint=FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
        )
    except ForestRequestError:
        raise
    if int(popup.status_code) >= 400:
        raise ForestRequestError(
            f"HTTP {popup.status_code}: {popup.text[:200]}",
            provider=dataset.provider,
            endpoint=FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
            status_code=int(popup.status_code),
            failure_kind="request",
        )

    history_data = {
            "dataType": dataset.download_path,
            "url": dataset.source_path,
            "pblicDataId": dataset.data_go_id,
            "tabs": "3",
            "searchSrvc": "",
            "searchWrd": "",
            "searchCnd": "",
            "dnldPrps": dataset.download_purpose_code or "3",
            "dnldDetlPrps": "",
            "useAgree01": "Y",
    }
    response = _forest_go_request_with_retry(
        lambda: session.post(
            FOREST_GO_FILE_DOWNLOAD_HISTORY_URL,
            data=history_data,
            timeout=timeout,
            allow_redirects=False,
        ),
        dataset=dataset,
        endpoint=FOREST_GO_FILE_DOWNLOAD_HISTORY_URL,
    )
    if int(response.status_code) >= 400:
        raise ForestRequestError(
            f"HTTP {response.status_code}: {response.text[:200]}",
            provider=dataset.provider,
            endpoint=FOREST_GO_FILE_DOWNLOAD_HISTORY_URL,
            status_code=int(response.status_code),
            failure_kind="request",
        )


def _forest_go_request_with_retry(
    request: Callable[[], Any],
    *,
    dataset: FileDataset,
    endpoint: str,
) -> Any:
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            return request()
        except Exception as exc:  # pragma: no cover - network-dependent
            last_exc = exc
    raise ForestRequestError(
        f"forest.go.kr request failed: {last_exc}",
        provider=dataset.provider,
        endpoint=endpoint,
        failure_kind="network",
    )


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
