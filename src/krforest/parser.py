"""원격 응답 레코드를 공개 Pydantic 모델로 파싱하는 함수."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kraddr.base import Address, PlaceCoordinate

from .models import (
    ErosionControlDam,
    MountainWeather,
    RecreationForestReservation,
    StandardRecreationForest,
)

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


def parse_mountain_weather(row: dict[str, Any]) -> MountainWeather:
    """산악기상 원본 레코드를 좌표 포함 모델로 파싱한다."""

    return MountainWeather(
        coordinate=PlaceCoordinate.from_mapping(row),
        raw=row,
    )


def parse_erosion_control_dam(row: dict[str, Any]) -> ErosionControlDam:
    """사방댐 원본 레코드를 좌표 포함 모델로 파싱한다."""

    return ErosionControlDam(
        coordinate=PlaceCoordinate.from_mapping(row),
        raw=row,
    )


def parse_recreation_forest_reservation(row: dict[str, Any]) -> RecreationForestReservation:
    """국립자연휴양림 예약정보 레코드를 안정적인 필드로 파싱한다."""

    return RecreationForestReservation(
        institution_id=first_text(row, *_INSTITUTION_ID_KEYS),
        institution_name=first_text(row, *_INSTITUTION_NAME_KEYS),
        goods_name=first_text(row, *_GOODS_NAME_KEYS),
        stay_date=first_text(row, *_STAY_DATE_KEYS),
        status=first_text(row, *_STATUS_KEYS),
        raw=row,
    )


def parse_standard_recreation_forest(row: dict[str, Any]) -> StandardRecreationForest:
    """전국휴양림표준데이터 레코드를 주소와 좌표 포함 모델로 파싱한다."""

    address = Address.from_mapping(row)
    if address is None:
        address_text = first_text(row, "rdnmadr", "lnmadr", "소재지도로명주소", "소재지지번주소")
        address = Address.from_text(address_text) if address_text is not None else None

    return StandardRecreationForest(
        name=first_text(row, "rcrfrstNm", "휴양림명"),
        sido_name=first_text(row, "ctprvnNm", "시도명"),
        forest_type=first_text(row, "rcrfrstType", "휴양림구분"),
        area=first_text(row, "rcrfrstFcltyAr", "휴양림면적"),
        capacity=first_text(row, "aceptncCo", "수용인원수"),
        entrance_fee=first_text(row, "admfee", "입장료"),
        accommodation_available=first_text(row, "stayngPosblYn", "숙박가능여부"),
        main_facilities=first_text(row, "mstrFclty", "주요시설명"),
        address=address,
        management_agency=first_text(row, "institutionNm", "관리기관명"),
        phone_number=first_text(row, "phoneNumber", "관리기관전화번호"),
        homepage_url=first_text(row, "homepageUrl", "홈페이지주소"),
        coordinate=PlaceCoordinate.from_mapping(row),
        reference_date=first_text(row, "referenceDate", "데이터기준일자"),
        institution_code=first_text(row, "instt_code", "제공기관코드"),
        raw=row,
    )


def first_text(row: Mapping[str, Any], *keys: str) -> str | None:
    """대소문자 차이를 흡수해 첫 번째 비어 있지 않은 문자열 값을 찾는다."""

    lower_key_map = {str(key).lower(): key for key in row}
    for key in keys:
        value = _strip_or_none(row.get(key))
        if value is not None:
            return value
        actual_key = lower_key_map.get(key.lower())
        if actual_key is None:
            continue
        value = _strip_or_none(row.get(actual_key))
        if value is not None:
            return value
    return None


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
