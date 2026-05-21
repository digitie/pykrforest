from __future__ import annotations

import pytest

from krforest import ForestAuthError, ForestClient

from .conftest import FakeResponse, FakeSession, xml_payload


async def test_from_env_uses_data_go_kr_key(monkeypatch):
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", " \n ENV _KEY \t")
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient.from_env(session=session)
    await client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "ENV_KEY"


async def test_explicit_service_key_copy_paste_whitespace_is_removed():
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient(api_key=" \r\n TEST _KEY \t", session=session)
    await client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "TEST_KEY"


async def test_missing_env_raises(monkeypatch):
    for name in (
        "KRFOREST_SERVICE_KEY",
        "KFS_SERVICE_KEY",
        "FOREST_SERVICE_KEY",
        "DATA_GO_SERVICE_KEY",
        "TRIPMATE_DATA_GO_SERVICE_KEY",
        "DATA_GO_KR_SERVICE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ForestAuthError):
        ForestClient.from_env()


async def test_from_env_does_not_fallback_to_legacy_names(monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    for name in (
        "KRFOREST_SERVICE_KEY",
        "KFS_SERVICE_KEY",
        "FOREST_SERVICE_KEY",
        "DATA_GO_SERVICE_KEY",
        "TRIPMATE_DATA_GO_SERVICE_KEY",
    ):
        monkeypatch.setenv(name, "LEGACY_KEY")

    with pytest.raises(ForestAuthError):
        ForestClient.from_env()
