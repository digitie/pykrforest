from __future__ import annotations

import pytest

from krforest import ForestAuthError, ForestClient

from .conftest import FakeResponse, FakeSession, xml_payload


def test_from_env_uses_krforest_key(monkeypatch):
    monkeypatch.setenv("KRFOREST_SERVICE_KEY", " \n ENV _KEY \t")
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient.from_env(session=session)
    client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "ENV_KEY"


def test_from_env_uses_tripmate_fallback(monkeypatch):
    monkeypatch.delenv("KRFOREST_SERVICE_KEY", raising=False)
    monkeypatch.delenv("PYKRFOREST_SERVICE_KEY", raising=False)
    monkeypatch.delenv("KFS_SERVICE_KEY", raising=False)
    monkeypatch.delenv("FOREST_SERVICE_KEY", raising=False)
    monkeypatch.delenv("DATA_GO_SERVICE_KEY", raising=False)
    monkeypatch.setenv("TRIPMATE_DATA_GO_SERVICE_KEY", "ENV_KEY")
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient.from_env(session=session)
    client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "ENV_KEY"


def test_explicit_service_key_copy_paste_whitespace_is_removed():
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient(" \r\n TEST _KEY \t", session=session)
    client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "TEST_KEY"


def test_missing_env_raises(monkeypatch):
    for name in (
        "KRFOREST_SERVICE_KEY",
        "PYKRFOREST_SERVICE_KEY",
        "KFS_SERVICE_KEY",
        "FOREST_SERVICE_KEY",
        "DATA_GO_SERVICE_KEY",
        "TRIPMATE_DATA_GO_SERVICE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ForestAuthError):
        ForestClient.from_env()
