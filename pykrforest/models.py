"""pykrforest가 반환하는 Pydantic 모델."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pykrtour import Address, PlaceCoordinate

RawRecord: TypeAlias = Mapping[str, Any]
Category: TypeAlias = Literal["travel", "safety"]
Provider: TypeAlias = Literal["forest.go.kr", "data.go.kr"]
T = TypeVar("T")


class ForestModel(BaseModel):
    """불변 공개 객체의 기반 모델."""

    model_config = ConfigDict(frozen=True)


class CallContext(ForestModel):
    """응답을 만든 원격 호출의 메타데이터."""

    provider: Provider | str | None = None
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


class MountainWeather(ForestModel):
    """산악기상 관측 지점과 기상 원본 레코드."""

    coordinate: PlaceCoordinate | None = None
    raw: RawRecord = Field(repr=False)


class ErosionControlDam(ForestModel):
    """사방댐 원본 레코드."""

    coordinate: PlaceCoordinate | None = None
    raw: RawRecord = Field(repr=False)


class RecreationForestReservation(ForestModel):
    """국립자연휴양림 숙박 상품 예약 현황 레코드."""

    institution_id: str | None = None
    institution_name: str | None = None
    goods_name: str | None = None
    stay_date: str | None = None
    status: str | None = None
    raw: RawRecord = Field(repr=False)


class RecreationForest(ForestModel):
    """국립자연휴양림 파일데이터를 조합한 위치·주소·상세 정보."""

    institution_id: str | None = None
    name: str | None = None
    coordinate: PlaceCoordinate | None = None
    address: Address | None = None
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
