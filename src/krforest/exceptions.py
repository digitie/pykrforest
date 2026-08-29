"""krforest 예외 계층."""

from __future__ import annotations

from typing import Any


class ForestApiError(Exception):
    """krforest 원격 API 통신·응답 처리 오류의 기반 클래스.

    카탈로그 조회(KeyError), 페이지·설정값 검증(ValueError), fixture 저장 시
    파일 충돌(FileExistsError) 등 로컬 입력 검증 실패는 이 계층에 포함되지
    않고 표준 라이브러리 예외가 그대로 발생한다. 즉 ``except ForestApiError``
    만으로는 이러한 오류를 포착할 수 없다.

    ``response``는 실패 지점에 따라 None, dict, 또는 dict가 아닌 원시 파싱
    결과값일 수 있으며 정해진 공통 구조가 없다. 접근하기 전 ``failure_kind``
    를 확인하고 값의 타입을 직접 검사해야 한다.
    """

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
