from __future__ import annotations

import json
from typing import Any

import pytest

from pykrforest import ForestClient


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        status_code: int = 200,
        text: str | None = None,
        content: bytes | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._json_error = json_error
        self.status_code = status_code
        if text is not None:
            self.text = text
        elif isinstance(payload, str):
            self.text = payload
        else:
            self.text = json.dumps(payload)
        self.content = content if content is not None else self.text.encode()

    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)


def public_payload(
    item: Any,
    *,
    result_code: str = "00",
    result_msg: str = "NORMAL SERVICE.",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int | None = None,
) -> dict[str, Any]:
    items = "" if item is None else {"item": item}
    if total_count is None:
        if isinstance(item, list):
            total_count = len(item)
        elif item is None:
            total_count = 0
        else:
            total_count = 1
    return {
        "response": {
            "header": {"resultCode": result_code, "resultMsg": result_msg},
            "body": {
                "items": items,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
                "totalCount": total_count,
            },
        }
    }


def xml_payload(
    item_xml: str,
    *,
    result_code: str = "00",
    result_msg: str = "NORMAL SERVICE.",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int = 1,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>{result_code}</resultCode>
    <resultMsg>{result_msg}</resultMsg>
  </header>
  <body>
    <items>{item_xml}</items>
    <numOfRows>{num_of_rows}</numOfRows>
    <pageNo>{page_no}</pageNo>
    <totalCount>{total_count}</totalCount>
  </body>
</response>"""


@pytest.fixture
def fake_client_factory() -> Any:
    def factory(*responses: FakeResponse, **kwargs: Any) -> tuple[ForestClient, FakeSession]:
        session = FakeSession(list(responses))
        client = ForestClient("TEST_KEY", session=session, **kwargs)
        return client, session

    return factory
