"""krforest 예외 계층."""

from __future__ import annotations

from typing import Any


class ForestApiError(Exception):
    """모든 krforest 예외의 기반 클래스."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        endpoint: str | None = None,
        status_code: int | None = None,
        result_code: str | None = None,
        failure_kind: str | None = None,
        response: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.endpoint = endpoint
        self.status_code = status_code
        self.result_code = result_code
        self.failure_kind = failure_kind
        self.response = response
        self.params = params or {}

    @property
    def metadata(self) -> dict[str, Any]:
        """구조화된 오류 메타데이터를 반환한다."""

        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "result_code": self.result_code,
            "failure_kind": self.failure_kind,
            "params": self.params,
        }


class ForestAuthError(ForestApiError):
    """인증 실패 또는 서비스 활용신청 미승인 오류."""


class ForestRateLimitError(ForestApiError):
    """쿼터 초과 또는 rate limit 오류."""


class ForestRequestError(ForestApiError):
    """잘못된 요청 또는 지원하지 않는 파라미터 오류."""


class ForestNoDataError(ForestApiError):
    """데이터가 필요하지만 응답에 데이터가 없을 때의 오류."""


class ForestServerError(ForestApiError):
    """원격 서버 오류."""


class ForestParseError(ForestApiError):
    """원격 응답을 파싱할 수 없을 때의 오류."""
