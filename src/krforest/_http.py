"""산림청과 data.go.kr API 비동기 HTTP helper."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import httpx

from ._convert import (
    mask_params,
    normalize_items,
    public_params,
    redact_secret,
    to_int_or_none,
    without_none,
    xml_to_dict,
)
from ._ratelimit import AsyncTokenBucket
from .exceptions import (
    ForestAuthError,
    ForestNoDataError,
    ForestParseError,
    ForestRateLimitError,
    ForestRequestError,
    ForestServerError,
)
from .models import CallContext


class ResponseLike(Protocol):
    status_code: int
    text: str
    content: bytes

    def json(self) -> Any: ...


class AsyncSessionLike(Protocol):
    async def get(self, url: str, **kwargs: Any) -> ResponseLike: ...

    async def post(self, url: str, **kwargs: Any) -> ResponseLike: ...

    async def aclose(self) -> None: ...


def _new_session(timeout: float) -> AsyncSessionLike:
    return cast(
        AsyncSessionLike,
        httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; krforest/0.1; "
                    "+https://github.com/digitie/python-krforest-api)"
                )
            },
        ),
    )


@dataclass(frozen=True, slots=True)
class NormalizedPayload:
    items: list[dict[str, Any]]
    page_no: int | None
    num_of_rows: int | None
    total_count: int | None
    raw: dict[str, Any]
    header: dict[str, Any]
    context: CallContext


class ForestHttp:
    """data.go.kr와 forest.go.kr 응답 envelope를 처리하는 비동기 HTTP 클라이언트."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 10.0,
        session: AsyncSessionLike | None = None,
        service_key_param: str = "ServiceKey",
        max_rps: float = 5.0,
    ) -> None:
        api_key = "".join(str(api_key).split())
        if not api_key:
            raise ForestAuthError("api_key is required", failure_kind="auth")
        if not service_key_param:
            raise ValueError("service_key_param must not be empty")
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or _new_session(timeout)
        self._owns_session = session is None
        self.service_key_param = service_key_param
        self._rate_limiter = AsyncTokenBucket(max_rps=max_rps)

    async def aclose(self) -> None:
        """내부에서 만든 HTTP 세션을 닫는다."""

        if self._owns_session:
            await self.session.aclose()

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        provider: str,
        endpoint: str,
        response_format: str = "xml",
        service_key_param: str | None = None,
        response_type_param: str | None = None,
    ) -> NormalizedPayload:
        key_param = service_key_param or self.service_key_param
        query: dict[str, Any] = {key_param: self.api_key}
        if provider == "data.go.kr" and response_format.lower() == "json":
            query[response_type_param or "_type"] = "json"
        if params:
            query.update(params)

        safe_context = CallContext(
            provider=provider,
            endpoint=endpoint,
            request_url=url,
            request_params=public_params(query),
            collected_at=datetime.now(UTC),
        )
        await self._rate_limiter.acquire()
        try:
            response = await self.session.get(
                url,
                params=without_none(query),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            message = redact_secret(str(exc), self.api_key)
            raise ForestRequestError(
                f"request failed: {message}",
                provider=provider,
                endpoint=endpoint,
                params=mask_params(query),
                failure_kind="network",
            ) from None
        _raise_for_status(
            response,
            provider=provider,
            endpoint=endpoint,
            api_key=self.api_key,
            params=query,
        )

        payload = _decode_payload(
            response,
            provider=provider,
            endpoint=endpoint,
            api_key=self.api_key,
            response_format=response_format,
        )
        return _normalize_payload(
            payload,
            provider=provider,
            endpoint=endpoint,
            api_key=self.api_key,
            context=safe_context,
        )

    async def get_bytes(
        self,
        url: str,
        *,
        max_bytes: int | None = None,
        provider: str = "data.go.kr",
        endpoint: str | None = None,
    ) -> bytes:
        await self._rate_limiter.acquire()
        try:
            response = await self.session.get(
                url,
                timeout=self.timeout,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            message = redact_secret(str(exc), self.api_key)
            raise ForestRequestError(
                f"request failed: {message}",
                provider=provider,
                endpoint=endpoint or url,
                failure_kind="network",
            ) from None
        _raise_for_status(
            response,
            provider=provider,
            endpoint=endpoint or url,
            api_key=self.api_key,
            params={},
        )
        data = getattr(response, "content", b"")
        if isinstance(data, bytes):
            return data if max_bytes is None else data[:max_bytes]
        encoded = str(data).encode()
        return encoded if max_bytes is None else encoded[:max_bytes]


def _decode_payload(
    response: ResponseLike,
    *,
    provider: str,
    endpoint: str,
    api_key: str,
    response_format: str,
) -> dict[str, Any]:
    text = response.text.strip()
    try_json = response_format.lower() == "json" or text.startswith("{")
    if try_json:
        try:
            payload = response.json()
        except ValueError:
            if not text.startswith("<"):
                message = redact_secret(text, api_key)[:300]
                raise ForestParseError(
                    f"response was not valid JSON: {message}",
                    provider=provider,
                    endpoint=endpoint,
                    failure_kind="parse",
                ) from None
        else:
            if not isinstance(payload, dict):
                raise ForestParseError(
                    "JSON response root must be an object",
                    provider=provider,
                    endpoint=endpoint,
                    response=payload,
                    failure_kind="parse",
                )
            return payload
    if text.startswith("<"):
        try:
            return xml_to_dict(text)
        except Exception as exc:
            message = redact_secret(str(exc), api_key)
            raise ForestParseError(
                f"response was not valid XML: {message}",
                provider=provider,
                endpoint=endpoint,
                failure_kind="parse",
            ) from exc
    message = redact_secret(text, api_key)[:300]
    raise ForestParseError(
        f"unsupported response body: {message}",
        provider=provider,
        endpoint=endpoint,
        failure_kind="parse",
    )


def _normalize_payload(
    payload: dict[str, Any],
    *,
    provider: str,
    endpoint: str,
    api_key: str,
    context: CallContext,
) -> NormalizedPayload:
    if "OpenAPI_ServiceResponse" in payload:
        _raise_openapi_service_error(
            payload["OpenAPI_ServiceResponse"],
            provider=provider,
            endpoint=endpoint,
            api_key=api_key,
        )

    try:
        response = payload["response"]
        header = response.get("header", {})
        body = response.get("body", {})
    except (KeyError, AttributeError) as exc:
        raise ForestParseError(
            "response did not contain response.header/body",
            provider=provider,
            endpoint=endpoint,
            response=payload,
            failure_kind="parse",
        ) from exc

    if not isinstance(header, dict) or not isinstance(body, dict):
        raise ForestParseError(
            "response.header and response.body must be objects",
            provider=provider,
            endpoint=endpoint,
            response=payload,
            failure_kind="parse",
        )

    code = str(header.get("resultCode", "")).strip()
    message = str(header.get("resultMsg", "")).strip()
    if code not in {"", "00", "0000", "NORMAL_CODE"}:
        if code == "03":
            return NormalizedPayload(
                items=[],
                page_no=to_int_or_none(body.get("pageNo")),
                num_of_rows=to_int_or_none(body.get("numOfRows")),
                total_count=0,
                raw=payload,
                header=header,
                context=context,
            )
        _raise_result_code(
            code,
            message,
            provider=provider,
            endpoint=endpoint,
            payload=payload,
            api_key=api_key,
        )

    try:
        items = normalize_items(body.get("items", []))
    except TypeError as exc:
        raise ForestParseError(
            str(exc),
            provider=provider,
            endpoint=endpoint,
            response=payload,
            failure_kind="parse",
        ) from exc

    parsed_total_count = to_int_or_none(body.get("totalCount"))
    return NormalizedPayload(
        items=items,
        page_no=to_int_or_none(body.get("pageNo")),
        num_of_rows=to_int_or_none(body.get("numOfRows")),
        total_count=parsed_total_count if parsed_total_count is not None else len(items),
        raw=payload,
        header=header,
        context=context,
    )


def _raise_for_status(
    response: ResponseLike,
    *,
    provider: str,
    endpoint: str,
    api_key: str,
    params: dict[str, Any],
) -> None:
    status = int(response.status_code)
    if status < 300:
        return
    text = redact_secret(response.text, api_key)[:300]
    kwargs: dict[str, Any] = {
        "provider": provider,
        "endpoint": endpoint,
        "status_code": status,
        "params": mask_params(params),
    }
    if status in {401, 403}:
        raise ForestAuthError(f"HTTP {status}: {text}", failure_kind="auth", **kwargs)
    if status == 429:
        raise ForestRateLimitError(f"HTTP {status}: {text}", failure_kind="rate_limit", **kwargs)
    if 300 <= status < 400:
        raise ForestRequestError(f"HTTP {status}: {text}", failure_kind="redirect", **kwargs)
    if 400 <= status < 500:
        raise ForestRequestError(f"HTTP {status}: {text}", failure_kind="request", **kwargs)
    if 500 <= status < 600:
        raise ForestServerError(f"HTTP {status}: {text}", failure_kind="server", **kwargs)


def _raise_result_code(
    code: str,
    message: str,
    *,
    provider: str,
    endpoint: str,
    payload: dict[str, Any],
    api_key: str,
) -> None:
    text = f"{provider} returned {code}: {message}" if code else message
    text = redact_secret(text, api_key)
    kwargs: dict[str, Any] = {
        "provider": provider,
        "endpoint": endpoint,
        "result_code": code or None,
        "response": _redact_payload(payload, api_key),
    }
    upper = text.upper()
    if code in {"20", "30", "31", "32", "33"} or "SERVICE_KEY" in upper or "AUTH" in upper:
        raise ForestAuthError(text, failure_kind="auth", **kwargs)
    if code == "22" or "LIMIT" in upper or "QUOTA" in upper:
        raise ForestRateLimitError(text, failure_kind="rate_limit", **kwargs)
    if code in {"04", "99"} or code.startswith("5"):
        raise ForestServerError(text, failure_kind="server", **kwargs)
    if code == "03":
        raise ForestNoDataError(text, failure_kind="no_data", **kwargs)
    raise ForestRequestError(text, failure_kind="request", **kwargs)


def _raise_openapi_service_error(
    data: Any,
    *,
    provider: str,
    endpoint: str,
    api_key: str,
) -> None:
    if not isinstance(data, dict):
        raise ForestParseError(
            "OpenAPI_ServiceResponse must be an object",
            provider=provider,
            endpoint=endpoint,
            response=data,
            failure_kind="parse",
        )
    header = data.get("cmmMsgHeader", data)
    if not isinstance(header, dict):
        raise ForestParseError(
            "OpenAPI_ServiceResponse header must be an object",
            provider=provider,
            endpoint=endpoint,
            response=data,
            failure_kind="parse",
        )
    code = str(header.get("returnReasonCode", "")).strip()
    message = str(
        header.get("returnAuthMsg")
        or header.get("errMsg")
        or header.get("resultMsg")
        or json.dumps(header, ensure_ascii=False)
    )
    _raise_result_code(
        code,
        message,
        provider=provider,
        endpoint=endpoint,
        payload=data,
        api_key=api_key,
    )


def _redact_payload(value: Any, api_key: str) -> Any:
    """body-level provider error payload에서 service key를 재귀적으로 제거한다."""

    if isinstance(value, str):
        return redact_secret(value, api_key)
    if isinstance(value, dict):
        return {key: _redact_payload(item, api_key) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_payload(item, api_key) for item in value]
    return value
