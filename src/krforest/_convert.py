"""클라이언트와 테스트가 함께 쓰는 작은 변환 helper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree

_LATITUDE_KEYS: tuple[str, ...] = (
    "latitude",
    "lat",
    "yValue",
    "y_value",
    "Y",
    "y",
    "POINT_Y",
    "위도",
    "Latitude",
)
_LONGITUDE_KEYS: tuple[str, ...] = (
    "longitude",
    "lon",
    "lng",
    "xValue",
    "x_value",
    "X",
    "x",
    "POINT_X",
    "경도",
    "Longitude",
)
_ADDRESS_KEYS: tuple[str, ...] = (
    "address",
    "rdnmadr",
    "lnmadr",
    "주소",
    "소재지도로명주소",
    "소재지지번주소",
    "소재지주소",
    "기본주소",
    "주소지",
    "POFLC_NM",
    "DTADD",
)
# 산림청·data.go.kr이 결측을 나타내는 sentinel 좌표값. 정확히 비교해도 안전한 값만 둔다.
_MISSING_COORDINATE_VALUES: frozenset[float] = frozenset({-99.0, -999.0, 0.0})


def strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def to_int_or_none(value: Any) -> int | None:
    text = strip_or_none(value)
    if text is None:
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def to_float_or_none(value: Any) -> float | None:
    text = strip_or_none(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def without_none(params: Mapping[str, Any]) -> dict[str, Any]:
    """값이 None인 항목을 제거한 dict를 반환한다."""

    return {key: value for key, value in params.items() if value is not None}


def normalize_items(value: Any) -> list[dict[str, Any]]:
    """공공데이터 응답의 단일 객체/list/빈 값 형태를 list[dict]로 정규화한다."""

    if not value:
        return []
    if isinstance(value, Mapping):
        if "item" in value:
            return normalize_items(value["item"])
        return [dict(value)]
    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, Mapping):
                raise TypeError("items must contain objects")
            items.append(dict(item))
        return items
    raise TypeError("items must be an object, list, or empty value")


def xml_to_dict(text: str) -> dict[str, Any]:
    """XML 응답을 중첩 dict로 변환한다.

    공공데이터 XML 응답은 대체로 얕지만 ``item``처럼 반복되는 하위 태그는
    list로 유지해야 한다. Element attribute는 의도적으로 무시한다.
    """

    root = ElementTree.fromstring(text.strip())
    value = _element_value(root)
    if isinstance(value, dict):
        return {root.tag.rsplit("}", 1)[-1]: value}
    return {root.tag.rsplit("}", 1)[-1]: value}


def _element_value(element: ElementTree.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()

    grouped: dict[str, Any] = {}
    for child in children:
        tag = child.tag.rsplit("}", 1)[-1]
        value = _element_value(child)
        if tag in grouped:
            existing = grouped[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                grouped[tag] = [existing, value]
        else:
            grouped[tag] = value
    return grouped


def redact_secret(text: str, secret: str | None) -> str:
    if not secret:
        return text
    return text.replace(secret, "[redacted]")


SENSITIVE_PARAM_KEYS: frozenset[str] = frozenset(
    {
        "servicekey",
        "key",
        "certkey",
        "apikey",
        "xapikey",
        "authkey",
        "accesskey",
        "accesstoken",
        "refreshtoken",
        "authorization",
    }
)


def mask_params(params: Mapping[str, Any]) -> dict[str, Any]:
    masked = dict(params)
    for key in list(masked):
        if str(key).replace("_", "").lower() in SENSITIVE_PARAM_KEYS:
            value = str(masked[key])
            masked[key] = value[:4] + "..." if len(value) > 4 else "***"
    return masked


def public_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in without_none(params).items()
        if str(key).replace("_", "").lower() not in SENSITIVE_PARAM_KEYS
    }


def extract_coordinate(
    row: Mapping[str, Any],
    *,
    extra_latitude_keys: tuple[str, ...] = (),
    extra_longitude_keys: tuple[str, ...] = (),
) -> tuple[float | None, float | None]:
    """row에서 (latitude, longitude)를 추출한다. 결측 sentinel(-99, -999, 0)은 None."""

    lat = _first_float(row, (*_LATITUDE_KEYS, *extra_latitude_keys))
    lon = _first_float(row, (*_LONGITUDE_KEYS, *extra_longitude_keys))
    if lat is None or lon is None:
        return None, None
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return None, None
    if lat in _MISSING_COORDINATE_VALUES or lon in _MISSING_COORDINATE_VALUES:
        return None, None
    return lat, lon


def extract_address(
    row: Mapping[str, Any],
    *,
    extra_keys: tuple[str, ...] = (),
) -> str | None:
    """row에서 도로명/지번 주소 문자열을 우선 키 순서대로 찾아 반환한다."""

    for key in (*_ADDRESS_KEYS, *extra_keys):
        value = _lookup_text(row, key)
        if value is not None:
            return value
    return None


def _first_float(row: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = to_float_or_none(_lookup_raw(row, key))
        if value is not None:
            return value
    return None


def _lookup_text(row: Mapping[str, Any], key: str) -> str | None:
    value = strip_or_none(_lookup_raw(row, key))
    return value


def _lookup_raw(row: Mapping[str, Any], key: str) -> Any:
    if key in row:
        return row[key]
    target = key.lower()
    for candidate_key in row:
        if str(candidate_key).lower() == target:
            return row[candidate_key]
    return None
