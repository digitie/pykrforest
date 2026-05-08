"""클라이언트와 테스트가 함께 쓰는 작은 변환 helper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree


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

    if value in (None, "", []):
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


def mask_params(params: Mapping[str, Any]) -> dict[str, Any]:
    masked = dict(params)
    for key in list(masked):
        if str(key).replace("_", "").lower() in {"servicekey", "key", "certkey"}:
            value = str(masked[key])
            masked[key] = value[:4] + "..." if len(value) > 4 else "***"
    return masked


def public_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in without_none(params).items()
        if str(key).replace("_", "").lower() not in {"servicekey", "key", "certkey"}
    }
