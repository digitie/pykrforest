"""krforest가 반환하는 Pydantic 모델."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field

RawRecord: TypeAlias = Mapping[str, Any]
Category: TypeAlias = Literal["travel", "safety"]
Provider: TypeAlias = Literal["forest.go.kr", "data.go.kr"]
CatalogKind: TypeAlias = Literal["api", "file_dataset"]
T = TypeVar("T")


class ForestModel(BaseModel):
    """불변 공개 객체의 기반 모델."""

    model_config = ConfigDict(frozen=True)


class CallContext(ForestModel):
    """응답을 만든 원격 호출의 메타데이터."""

    provider: str | None = None
    endpoint: str | None = None
    request_url: str | None = None
    request_params: RawRecord = Field(default_factory=dict)
    collected_at: datetime | None = None


class Page(ForestModel, Generic[T]):
    """페이지네이션 API 응답."""

    items: tuple[T, ...]
    total_count: int
    page_no: int
    num_of_rows: int
    raw: RawRecord = Field(repr=False)
    header: RawRecord = Field(default_factory=dict)
    context: CallContext = Field(default_factory=CallContext)

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def has_next_page(self) -> bool:
        if self.num_of_rows <= 0:
            return False
        return self.page_no * self.num_of_rows < self.total_count

    @property
    def next_page_no(self) -> int | None:
        if not self.has_next_page:
            return None
        return self.page_no + 1


class ApiEndpoint(ForestModel):
    """정리된 산림청 API endpoint 메타데이터."""

    key: str
    title: str
    data_go_id: str
    categories: tuple[Category, ...]
    provider: Provider
    service: str
    operation: str
    url: str
    detail_url: str
    description: str
    notes: str | None = None
    service_key_param: str = "ServiceKey"
    response_format: str | None = None
    response_type_param: str | None = None


class FileDataset(ForestModel):
    """정리된 data.go.kr 파일데이터 메타데이터."""

    data_go_id: str
    title: str
    categories: tuple[Category, ...]
    formats: tuple[str, ...]
    detail_url: str
    description: str
    provider: str = "data.go.kr"
    direct_download: bool = True
    download_url: str | None = None
    download_path: str | None = None
    source_path: str | None = None
    download_purpose_code: str | None = None


class CatalogEntry(ForestModel):
    """디버그 UI 표시와 선택에 쓰는 human-readable 카탈로그 항목."""

    kind: CatalogKind
    key: str
    display_name: str
    dataset_id: str
    dataset_name: str
    categories: tuple[Category, ...]
    provider: str
    description: str
    detail_url: str
    service_key_url: str | None = None
    service_key_account_url: str | None = None
    service: str | None = None
    operation: str | None = None
    url: str | None = None
    formats: tuple[str, ...] = ()
    service_key_param: str | None = None
    response_format: str | None = None
    response_type_param: str | None = None


class MountainWeather(ForestModel):
    """산악기상 관측 지점과 기상 원본 레코드."""

    latitude: float | None = None
    longitude: float | None = None
    raw: RawRecord = Field(repr=False)


class ErosionControlDam(ForestModel):
    """사방댐 원본 레코드."""

    latitude: float | None = None
    longitude: float | None = None
    raw: RawRecord = Field(repr=False)


class RecreationForestReservation(ForestModel):
    """국립자연휴양림 숙박 상품 예약 현황 레코드."""

    institution_id: str | None = None
    institution_name: str | None = None
    goods_name: str | None = None
    stay_date: str | None = None
    status: str | None = None
    raw: RawRecord = Field(repr=False)


class StandardRecreationForest(ForestModel):
    """전국휴양림표준데이터의 휴양림 위치·주소·시설 레코드."""

    name: str | None = None
    sido_name: str | None = None
    forest_type: str | None = None
    area: str | None = None
    capacity: str | None = None
    entrance_fee: str | None = None
    accommodation_available: str | None = None
    main_facilities: str | None = None
    address: str | None = None
    management_agency: str | None = None
    phone_number: str | None = None
    homepage_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    reference_date: str | None = None
    institution_code: str | None = None
    raw: RawRecord = Field(repr=False)


class ForestSpatialPoint(ForestModel):
    """SHP 파일에서 읽은 산림 공간 포인트 레코드."""

    dataset_id: str
    dataset_name: str
    name: str | None = None
    category: str | None = None
    address: str | None = None
    phone_number: str | None = None
    homepage_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    projected_x: float | None = None
    projected_y: float | None = None
    year: str | None = None
    owner_name: str | None = None
    operation_status: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    raw: RawRecord = Field(repr=False)


class ForestSpatialFeature(ForestModel):
    """SHP/GeoJSON/GPX 파일에서 읽은 산림 공간 피처 레코드."""

    dataset_id: str
    dataset_name: str
    source_file: str | None = None
    layer_name: str | None = None
    name: str | None = None
    geometry_type: str | None = None
    geometry: RawRecord | None = Field(default=None, repr=False)
    bbox: tuple[float, float, float, float] | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw: RawRecord = Field(repr=False)


class RecreationForest(ForestModel):
    """국립자연휴양림 파일데이터를 조합한 위치·주소·상세 정보."""

    institution_id: str | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    phone_number: str | None = None
    capacity: str | None = None
    operation_time: str | None = None
    homepage_url: str | None = None
    region: str | None = None
    description: str | None = None
    facilities: tuple[RawRecord, ...] = ()
    reservation_policies: tuple[RawRecord, ...] = ()
    reservation_records: tuple[RecreationForestReservation, ...] = ()
    raw: RawRecord = Field(default_factory=dict, repr=False)
