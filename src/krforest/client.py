"""사용자용 산림청 공공데이터 비동기 클라이언트."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Collection, Iterator, Mapping
from dataclasses import dataclass
from types import TracebackType
from typing import Any, TypeVar
from urllib.parse import urljoin

from ._http import AsyncSessionLike, ForestHttp, ResponseLike
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
from .config import ForestConfig
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
    ForestSpatialFeature,
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
from .spatial import (
    archive_files as parse_archive_files,
)
from .spatial import (
    forest_spatial_features,
    forest_spatial_points,
)

T = TypeVar("T")


class ForestClient:
    """산림청 여행·안전 공공데이터 비동기 facade."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float | str | None = None,
        max_rps: float | str | None = None,
        session: AsyncSessionLike | None = None,
        service_key_param: str = "ServiceKey",
    ) -> None:
        self.config = ForestConfig.from_env(
            api_key=api_key,
            timeout=timeout,
            max_rps=max_rps,
        )
        self.api_key = self.config.api_key
        self.timeout = self.config.timeout
        self._http = ForestHttp(
            self.api_key,
            timeout=self.timeout,
            session=session,
            service_key_param=service_key_param,
            max_rps=self.config.max_rps,
        )
        self.travel = TravelNamespace(self)
        self.safety = SafetyNamespace(self)
        self.files = FileDataNamespace(self)
        self.closed = False

    @classmethod
    def from_env(cls, **kwargs: Any) -> ForestClient:
        """환경 변수 기반 설정으로 클라이언트를 만든다."""

        return cls(**kwargs)

    @classmethod
    def aio(cls, **kwargs: Any) -> ForestClient:
        """krheritage와 같은 생성 패턴을 위한 비동기 클라이언트 생성자."""

        return cls(**kwargs)

    async def __aenter__(self) -> ForestClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self.closed = True

    def endpoints(self, category: str | None = None) -> tuple[ApiEndpoint, ...]:
        """정리된 API endpoint 메타데이터를 반환한다."""

        return api_endpoints(category)

    def file_datasets(self, category: str | None = None) -> tuple[FileDataset, ...]:
        """정리된 파일데이터 메타데이터를 반환한다."""

        return file_datasets(category)

    def catalog(self, category: str | None = None) -> tuple[CatalogEntry, ...]:
        """디버그 UI와 선택 목록에서 쓰는 human-readable 카탈로그를 반환한다."""

        return catalog_entries(category)

    async def raw_endpoint(
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
        return await self._page(
            endpoint,
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            lambda row: row,
            response_format=response_format,
        )

    async def debug_endpoint(
        self,
        endpoint_key: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_format: str | None = None,
    ) -> DebugRun:
        """디버그 UI가 저장 가능한 endpoint replay 결과를 반환한다."""

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
            page = await self.raw_endpoint(
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

    async def iter_pages(
        self,
        fetch_page: Callable[..., Awaitable[Page[T]]],
        *args: Any,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[T]]:
        """Page 반환 메서드를 비동기 페이지 단위로 순회한다."""

        fetched = 0
        current = page_no
        pages = 0
        while True:
            page = await fetch_page(*args, page_no=current, num_of_rows=num_of_rows, **kwargs)
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

    async def _page(
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
        payload = await self._http.get(
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
        requested_page_no = int(params["pageNo"]) if params and "pageNo" in params else 1
        requested_num_of_rows = (
            int(params["numOfRows"]) if params and "numOfRows" in params else max(len(parsed), 10)
        )
        return Page(
            items=tuple(parsed),
            total_count=payload.total_count if payload.total_count is not None else len(parsed),
            page_no=payload.page_no or requested_page_no,
            num_of_rows=payload.num_of_rows or requested_num_of_rows,
            raw=payload.raw,
            header=payload.header,
            context=payload.context,
        )


@dataclass(frozen=True, slots=True)
class TravelNamespace:
    _client: ForestClient

    async def forest_services(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """숲길 서비스와 둘레길 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "forest_trail_services",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def mountain_stories(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산 정보 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "mountain_stories",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def forest_spatial_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """등산로 산림공간정보 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "forest_spatial_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def baekdu_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """백두대간 등산로 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "baekdu_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def famous_mountain_trails(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """명산 등산로 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "famous_mountain_trails",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def mountain_weather(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[MountainWeather]:
        """국립산림과학원 산악기상 레코드를 조회한다."""

        return await self._client._page(
            api_endpoint("mountain_weather"),
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            parse_mountain_weather,
        )

    async def recreation_forest_reservations(
        self,
        *,
        goods_name: str | None = None,
        start_stay_date: str | None = None,
        end_stay_date: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RecreationForestReservation]:
        """국립자연휴양림 예약 정보 OpenAPI 레코드를 조회한다."""

        query = dict(params)
        query["goodsNm"] = goods_name
        query["startStngDt"] = start_stay_date
        query["endStngDt"] = end_stay_date
        return await self._client._page(
            api_endpoint("national_recreation_forest_reservations"),
            _page_params(query, page_no=page_no, num_of_rows=num_of_rows),
            parse_recreation_forest_reservation,
        )

    async def standard_recreation_forests(
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
        """전국 휴양림 표준데이터를 주소와 좌표 포함 모델로 조회한다."""

        query = dict(params)
        query["rcrfrstNm"] = name
        query["ctprvnNm"] = sido_name
        query["rcrfrstType"] = forest_type
        query["stayngPosblYn"] = _yn_value(accommodation_available)
        return await self._client._page(
            api_endpoint("standard_recreation_forests"),
            _page_params(query, page_no=page_no, num_of_rows=num_of_rows),
            parse_standard_recreation_forest,
        )

    async def forest_trail_file_features(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialFeature, ...]:
        """산림청 등산로정보 ZIP을 공간 feature DTO로 반환한다."""

        return await self._client.files.spatial_features(
            "PBD0000041",
            name=name,
            geometry_types={"LineString", "MultiLineString"},
        )

    async def dulle_trail_features(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialFeature, ...]:
        """산림청 둘레길정보 ZIP을 공간 feature DTO로 반환한다."""

        return await self._client.files.spatial_features(
            "PBD0000031",
            name=name,
            geometry_types={"LineString", "MultiLineString"},
        )

    async def forest_education_centers(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """산림교육센터 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000221")
        data = await self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    async def kid_forest_centers(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """유아숲체험원 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000220")
        data = await self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    async def traditional_village_forests(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """전통마을숲 위치 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000077")
        data = await self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    async def recreation_forest_arboretums(
        self,
        *,
        name: str | None = None,
    ) -> tuple[ForestSpatialPoint, ...]:
        """휴양림 수목원 SHP를 주소와 WGS84 좌표 포함 레코드로 반환한다."""

        dataset = file_dataset("PBD0000180")
        data = await self._client.files.download(dataset.data_go_id)
        return forest_spatial_points(data, dataset, name=name)

    async def recreation_forests(
        self,
        *,
        name: str | None = None,
        institution_id: str | None = None,
    ) -> tuple[RecreationForest, ...]:
        """휴양림 파일데이터를 조합해 위치, 주소, 시설, 예약 상세를 반환한다."""

        promotion_data = await self._client.files.download(RECREATION_FOREST_PROMOTION_ID)
        facility_data = await self._client.files.download(RECREATION_FOREST_FACILITY_ID)
        policy_data = await self._client.files.download(RECREATION_FOREST_POLICY_ID)
        reservation_data = await self._client.files.download(RECREATION_FOREST_RESERVATION_FILE_ID)
        return build_recreation_forests(
            csv_records(promotion_data),
            csv_records(facility_data),
            csv_records(policy_data),
            csv_records(reservation_data),
            name=name,
            institution_id=institution_id,
        )


@dataclass(frozen=True, slots=True)
class SafetyNamespace:
    _client: ForestClient

    async def wildfire_stats(
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
        return await self._client.raw_endpoint(
            "wildfire_stats",
            query,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def wildfire_risk_forecast(
        self,
        *,
        exclude_forecast: bool | int | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """전국 산불위험 예보지도 레코드를 조회한다."""

        query = dict(params)
        if exclude_forecast is not None:
            query["excludeForecast"] = int(bool(exclude_forecast))
        return await self._client.raw_endpoint(
            "wildfire_risk_forecast",
            query,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def past_landslides(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """과거 산사태 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "past_landslides",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def landslide_predictions(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산사태 예측정보 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "landslide_predictions",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def landslide_forecast_issues(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """산사태 예보 발령 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "landslide_forecast_issues",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def roadside_landslides(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[RawRecord]:
        """임도별 산사태 예방·복구 레코드를 조회한다."""

        return await self._client.raw_endpoint(
            "roadside_landslides",
            params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def erosion_control_dams(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        **params: Any,
    ) -> Page[ErosionControlDam]:
        """사방댐 레코드를 조회한다."""

        return await self._client._page(
            api_endpoint("erosion_control_dams"),
            _page_params(params, page_no=page_no, num_of_rows=num_of_rows),
            parse_erosion_control_dam,
        )

    async def landslide_risk_map_files(self) -> dict[str, bytes]:
        """산사태위험지도 ZIP을 파일명 기준 bytes dict로 반환한다."""

        return await self._client.files.archive_files("PBD0000210")


@dataclass(frozen=True, slots=True)
class FileDataNamespace:
    _client: ForestClient

    def datasets(self, category: str | None = None) -> tuple[FileDataset, ...]:
        """정리된 파일데이터 목록을 반환한다."""

        return file_datasets(category)

    def dataset(self, data_go_id: str) -> FileDataset:
        """정리된 파일데이터 하나를 반환한다."""

        return file_dataset(data_go_id)

    async def download_url(self, data_go_id: str) -> str:
        """상세 페이지에서 직접 파일 다운로드 URL을 찾는다."""

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
        response = await _get_detail_page(
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

    async def download(self, data_go_id: str, *, max_bytes: int | None = None) -> bytes:
        """정리된 파일데이터를 다운로드해 bytes로 반환한다."""

        dataset = file_dataset(data_go_id)
        if dataset.provider == "forest.go.kr":
            await _submit_forest_go_download_history(
                self._client._http.session,
                dataset,
                timeout=self._client.timeout,
            )
        url = await self.download_url(data_go_id)
        return await self._client._http.get_bytes(
            url,
            max_bytes=max_bytes,
            provider=dataset.provider,
            endpoint=dataset.data_go_id,
        )

    async def archive_files(self, data_go_id: str) -> dict[str, bytes]:
        """ZIP 파일데이터를 다운로드한 뒤 파일명 key의 bytes dict로 반환한다."""

        return parse_archive_files(await self.download(data_go_id))

    async def spatial_features(
        self,
        data_go_id: str,
        *,
        name: str | None = None,
        geometry_types: Collection[str] | None = None,
    ) -> tuple[ForestSpatialFeature, ...]:
        """SHP/GeoJSON/GPX 파일데이터를 공간 feature DTO로 반환한다.

        `geometry_types`를 주면 해당 geometry만 좌표 변환·DTO 생성한다. 대형
        aggregate route archive에서 Point 레코드를 제외할 때 사용한다.
        """

        dataset = file_dataset(data_go_id)
        return forest_spatial_features(
            await self.download(data_go_id),
            dataset,
            name=name,
            geometry_types=geometry_types,
        )


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


async def _submit_forest_go_download_history(
    session: AsyncSessionLike,
    dataset: FileDataset,
    *,
    timeout: float,
) -> None:
    if dataset.download_path is None or dataset.source_path is None:
        return

    tabs = _forest_go_tabs(dataset)
    popup_params = {
        "pblicDataId": dataset.data_go_id,
        "tabs": tabs,
        "searchSrvc": "",
        "subTitle": "",
        "fileNum": dataset.download_path,
        "url": dataset.source_path,
    }
    popup = await _forest_go_request_with_retry(
        lambda: session.get(
            FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
            params=popup_params,
            timeout=timeout,
        ),
        dataset=dataset,
        endpoint=FOREST_GO_FILE_DOWNLOAD_POPUP_URL,
    )
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
        "tabs": tabs,
        "searchSrvc": "",
        "searchWrd": "",
        "searchCnd": "",
        "dnldPrps": dataset.download_purpose_code or "3",
        "dnldDetlPrps": "",
        "useAgree01": "Y",
    }
    response = await _forest_go_request_with_retry(
        lambda: session.post(
            FOREST_GO_FILE_DOWNLOAD_HISTORY_URL,
            data=history_data,
            timeout=timeout,
            follow_redirects=False,
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


def _forest_go_tabs(dataset: FileDataset) -> str:
    return "4" if "safety" in dataset.categories else "3"


async def _forest_go_request_with_retry(
    request: Callable[[], Awaitable[ResponseLike]],
    *,
    dataset: FileDataset,
    endpoint: str,
    attempts: int = 3,
    backoff: float = 0.5,
) -> ResponseLike:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await request()
        except Exception as exc:  # pragma: no cover - network-dependent
            last_exc = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(backoff * (2**attempt))
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


async def _get_detail_page(
    session: AsyncSessionLike,
    url: str,
    *,
    timeout: float,
) -> ResponseLike:
    try:
        return await session.get(url, timeout=timeout)
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
            return await session.get(fallback, timeout=timeout)
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
