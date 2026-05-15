"""디버그 UI와 fixture 저장을 위한 공통 도구."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel

SENSITIVE_KEYS = {
    "authorization",
    "apikey",
    "xapikey",
    "servicekey",
    "certkey",
    "accesstoken",
    "refreshtoken",
}
DEFAULT_ASSERTION = {
    "mode": "snapshot",
    "exclude_fields": ["fetched_at", "request_id", "updated_at"],
    "required_fields": [],
}


@dataclass
class DebugRun:
    """디버그 실행 한 번의 입력, 요청, 응답, 파싱, 가공 결과."""

    function: str
    input: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    parsed: Any
    processed: Any
    trace: list[str]
    catalog: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


def jsonable(obj: Any) -> Any:
    """Pydantic v2 모델과 컨테이너를 JSON 저장 가능한 값으로 변환한다."""

    if isinstance(obj, DebugRun):
        return {
            "function": obj.function,
            "input": jsonable(obj.input),
            "request": jsonable(obj.request),
            "response": jsonable(obj.response),
            "parsed": jsonable(obj.parsed),
            "processed": jsonable(obj.processed),
            "trace": jsonable(obj.trace),
            "catalog": jsonable(obj.catalog),
            "error": jsonable(obj.error),
        }
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Mapping):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(value) for value in obj]
    if isinstance(obj, set):
        return [jsonable(value) for value in sorted(obj, key=repr)]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def redact_sensitive(obj: Any) -> Any:
    """fixture에 저장하면 안 되는 인증 값을 재귀적으로 마스킹한다."""

    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            text_key = str(key)
            if _is_sensitive_key(text_key):
                result[text_key] = "<REDACTED>"
            else:
                result[text_key] = redact_sensitive(value)
        return result
    if isinstance(obj, list):
        return [redact_sensitive(value) for value in obj]
    return obj


def slugify(value: str) -> str:
    """fixture 디렉터리와 파일명으로 쓸 수 있는 이름을 만든다."""

    text = value.strip().lower()
    text = re.sub(r"[^\w가-힣.-]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "case"


def save_fixture(
    *,
    base_dir: str | Path,
    function_name: str,
    case_name: str,
    description: str,
    input_data: Mapping[str, Any],
    request_data: Mapping[str, Any],
    response_data: Mapping[str, Any],
    parsed_result: Any,
    processed_result: Any,
    assertion: Mapping[str, Any] | None = None,
    library_version: str | None = None,
    overwrite: bool = False,
) -> Path:
    """디버그 실행 결과를 pytest replay용 fixture JSON으로 저장한다."""

    safe_function_name = slugify(function_name)
    safe_case_name = slugify(case_name)
    fixture_dir = Path(base_dir) / safe_function_name
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / f"{safe_case_name}.json"

    if fixture_path.exists() and not overwrite:
        raise FileExistsError(f"Fixture already exists: {fixture_path}")

    fixture = {
        "name": safe_case_name,
        "function": function_name,
        "description": description,
        "input": redact_sensitive(jsonable(input_data)),
        "request": redact_sensitive(jsonable(request_data)),
        "response": redact_sensitive(jsonable(response_data)),
        "parsed": redact_sensitive(jsonable(parsed_result)),
        "processed": redact_sensitive(jsonable(processed_result)),
        "assertion": dict(assertion or DEFAULT_ASSERTION),
        "meta": {
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "library_version": library_version,
            "source": "debug_ui",
        },
    }

    with fixture_path.open("w", encoding="utf-8") as file:
        json.dump(fixture, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return fixture_path


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("_", "").replace("-", "").lower()
    return normalized in SENSITIVE_KEYS
