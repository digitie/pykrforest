"""저장된 fixture를 replay 테스트에서 검증하는 공통 함수."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .debug import jsonable


def load_fixture(path: str | Path) -> dict[str, Any]:
    """fixture JSON 파일을 읽어 dict로 반환한다."""

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise TypeError("fixture root must be an object")
    return data


def remove_fields(obj: Any, exclude_fields: Sequence[str], *, _path: str = "") -> Any:
    """snapshot 비교에서 제외할 필드를 재귀적으로 제거한다."""

    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            text_key = str(key)
            child_path = f"{_path}.{text_key}" if _path else text_key
            if text_key in exclude_fields or child_path in exclude_fields:
                continue
            result[text_key] = remove_fields(value, exclude_fields, _path=child_path)
        return result
    if isinstance(obj, list):
        return [remove_fields(value, exclude_fields, _path=_path) for value in obj]
    return obj


def assert_case(actual: Any, expected: Any, assertion: Mapping[str, Any]) -> None:
    """fixture assertion mode에 맞춰 replay 결과를 검증한다."""

    mode = str(assertion.get("mode", "snapshot"))
    actual_json = jsonable(actual)
    expected_json = jsonable(expected)

    if mode == "snapshot":
        exclude_fields = _string_list(assertion.get("exclude_fields", []))
        assert remove_fields(actual_json, exclude_fields) == remove_fields(
            expected_json,
            exclude_fields,
        )
    elif mode == "required_fields":
        for field in _string_list(assertion.get("required_fields", [])):
            assert _has_field(actual_json, field), f"missing required field: {field}"
    elif mode == "schema_only":
        assert actual_json is not None
    elif mode == "count":
        assert _extract_count(actual_json) == _extract_count(expected_json)
    else:
        raise ValueError(f"Unknown assertion mode: {mode}")


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return []


def _has_field(obj: Any, field: str) -> bool:
    current = obj
    for part in field.split("."):
        if isinstance(current, Mapping):
            if part not in current:
                return False
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return False
            if not 0 <= index < len(current):
                return False
            current = current[index]
        else:
            return False
    return True


def _extract_count(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        if "count" in obj:
            return obj["count"]
        if "items" in obj and isinstance(obj["items"], list):
            return len(obj["items"])
    if isinstance(obj, list):
        return len(obj)
    return obj
