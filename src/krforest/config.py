"""런타임 설정 로딩."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .exceptions import ForestAuthError

DEFAULT_ENV_NAME = "DATA_GO_KR_SERVICE_KEY"
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RPS = 5.0


@dataclass(frozen=True, slots=True)
class ForestConfig:
    """명시 인자와 환경 변수에서 만든 산림청 API 실행 설정."""

    api_key: str
    timeout: float = DEFAULT_TIMEOUT
    max_rps: float = DEFAULT_MAX_RPS

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        timeout: float | str | None = None,
        max_rps: float | str | None = None,
    ) -> ForestConfig:
        resolved_key = _normalize_api_key(api_key) or _normalize_api_key(
            os.getenv(DEFAULT_ENV_NAME)
        )
        if not resolved_key:
            raise ForestAuthError(
                f"api_key is required. Pass api_key=... or set {DEFAULT_ENV_NAME}",
                failure_kind="auth",
            )
        return cls(
            api_key=resolved_key,
            timeout=_resolve_positive_float(timeout, default=DEFAULT_TIMEOUT, field_name="timeout"),
            max_rps=_resolve_positive_float(max_rps, default=DEFAULT_MAX_RPS, field_name="max_rps"),
        )

def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = "".join(str(value).split())
    return key or None


def _resolve_positive_float(
    value: float | str | None,
    *,
    default: float,
    field_name: str,
) -> float:
    if value is None or value == "":
        return default
    try:
        resolved = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive number") from exc
    if resolved <= 0:
        raise ValueError(f"{field_name} must be greater than 0")
    return resolved
