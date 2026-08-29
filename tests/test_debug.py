from __future__ import annotations

import json

import pytest

from krforest import save_fixture
from krforest.debug import jsonable, redact_sensitive, slugify

from .conftest import FakeResponse, public_payload


async def test_save_fixture_redacts_sensitive_values_and_blocks_overwrite(tmp_path):
    path = save_fixture(
        base_dir=tmp_path,
        function_name="wildfire_stats",
        case_name="Seoul auth case",
        description="민감정보 마스킹 확인",
        input_data={"serviceKey": "SECRET", "region": "서울"},
        request_data={"headers": {"Authorization": "Bearer SECRET"}},
        response_data={"body": {"access_token": "SECRET", "items": []}},
        parsed_result={"items": []},
        processed_result={"items": [], "updated_at": "2026-05-15T20:30:00+09:00"},
        library_version="0.1.0",
    )

    data = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "seoul_auth_case.json"
    assert data["input"]["serviceKey"] == "<REDACTED>"
    assert data["request"]["headers"]["Authorization"] == "<REDACTED>"
    assert data["response"]["body"]["access_token"] == "<REDACTED>"
    assert data["assertion"]["mode"] == "snapshot"
    assert data["meta"]["source"] == "debug_ui"

    with pytest.raises(FileExistsError):
        save_fixture(
            base_dir=tmp_path,
            function_name="wildfire_stats",
            case_name="Seoul auth case",
            description="중복 저장 방지",
            input_data={},
            request_data={},
            response_data={},
            parsed_result={},
            processed_result={},
        )


async def test_debug_endpoint_returns_debug_run_without_service_key(fake_client_factory):
    payload = public_payload({"doname": "전국", "meanavg": "27"}, total_count=1)
    client, _session = fake_client_factory(FakeResponse(payload))

    run = await client.debug_endpoint(
        "wildfire_risk_forecast",
        {"excludeForecast": 1},
        num_of_rows=1,
    )
    data = jsonable(run)

    assert run.function == "wildfire_risk_forecast"
    assert run.error is None
    assert run.request["method"] == "GET"
    assert "ServiceKey" not in run.request["query"]
    assert "TEST_KEY" not in repr(data)
    assert data["processed"][0]["doname"] == "전국"
    assert data["response"]["elapsed_ms"] >= 0
    assert data["catalog"]["dataset_name"] == "산림청 국립산림과학원_산불위험예보정보"
    assert data["catalog"]["display_name"] == data["catalog"]["dataset_name"]
    assert data["catalog"]["service_key_url"].endswith("/15084817/openapi.do")
    assert data["catalog"]["service_key_account_url"].endswith(
        "/iim/api/selectAPIAcountView.do"
    )
    assert data["trace"][-1].startswith("success in")


async def test_debug_endpoint_error_has_structured_traceback_and_provider_fields(
    fake_client_factory,
):
    client, _session = fake_client_factory(FakeResponse(status_code=403, text="forbidden"))

    run = await client.debug_endpoint("wildfire_stats", {}, num_of_rows=1)
    data = jsonable(run)

    assert run.error is not None
    assert data["error"]["type"] == "ForestAuthError"
    assert data["error"]["failure_kind"] == "auth"
    assert data["error"]["status_code"] == 403
    assert data["error"]["retryable"] is False
    assert isinstance(data["error"]["traceback"], list) and data["error"]["traceback"]
    assert "TEST_KEY" not in repr(data)
    assert data["trace"][-1].startswith("failed after")


async def test_redact_sensitive_and_slugify_are_recursive():
    value = {
        "nested": [{"x-api-key": "SECRET"}],
        "public": "ok",
    }

    assert redact_sensitive(value)["nested"][0]["x-api-key"] == "<REDACTED>"
    assert slugify(" 예약 정보 / 정상 케이스 ") == "예약_정보_정상_케이스"
