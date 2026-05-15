"""파싱된 값과 파일데이터를 사용자용 결과로 가공하는 함수."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from typing import Any

from kraddr.base import Address, PlaceCoordinate

from ._convert import strip_or_none
from .exceptions import ForestParseError
from .models import RecreationForest
from .parser import first_text, parse_recreation_forest_reservation

RECREATION_FOREST_PROMOTION_ID = "15064415"
RECREATION_FOREST_FACILITY_ID = "15064419"
RECREATION_FOREST_POLICY_ID = "15064416"
RECREATION_FOREST_RESERVATION_FILE_ID = "15064418"

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
_PHONE_KEYS = ("phone_number", "전화번호", "대표전화번호", "연락처", "tel", "telNo")
_CAPACITY_KEYS = ("capacity", "최대수용인원", "수용인원", "정원")
_OPERATION_TIME_KEYS = ("operation_time", "운영시간", "이용시간")
_HOMEPAGE_KEYS = ("homepage_url", "홈페이지", "홈페이지주소", "url", "URL")
_REGION_KEYS = ("region", "지역", "시도", "시군구")
_DESCRIPTION_KEYS = ("description", "설명", "소개", "개요", "내용")
_EXTRA_ADDRESS_KEYS = ("소재지도로명주소", "기본주소", "주소지")


def csv_records(data: bytes) -> tuple[dict[str, str], ...]:
    """UTF-8 또는 CP949 CSV 파일데이터를 레코드 tuple로 변환한다."""

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


def build_recreation_forests(
    promotion_rows: tuple[dict[str, str], ...],
    facility_rows: tuple[dict[str, str], ...],
    policy_rows: tuple[dict[str, str], ...],
    reservation_rows: tuple[dict[str, str], ...],
    *,
    name: str | None,
    institution_id: str | None,
) -> tuple[RecreationForest, ...]:
    """국립자연휴양림 관련 파일데이터를 휴양림 단위 상세 정보로 조합한다."""

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
        forest_id = first_text(base_row, *_INSTITUTION_ID_KEYS)
        forest_name = first_text(base_row, *_INSTITUTION_NAME_KEYS)
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
            text = first_text(base_row, *_EXTRA_ADDRESS_KEYS)
            address = Address.from_text(text) if text is not None else None
        if address is None:
            for row in facilities:
                address = Address.from_mapping(row)
                if address is None:
                    text = first_text(row, *_EXTRA_ADDRESS_KEYS)
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
                    parse_recreation_forest_reservation(dict(row)) for row in reservations
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
    forest_id = first_text(row, *_INSTITUTION_ID_KEYS)
    forest_name = first_text(row, *_INSTITUTION_NAME_KEYS)
    if forest_id is not None:
        keys.append(f"id:{forest_id}")
    if forest_name is not None:
        keys.append(f"name:{forest_name}")
    return tuple(keys)


def _first_text_from_rows(rows: tuple[Mapping[str, Any], ...], *keys: str) -> str | None:
    for row in rows:
        value = first_text(row, *keys)
        if value is not None:
            return value
    return None
