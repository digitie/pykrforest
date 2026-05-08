from __future__ import annotations

import pytest

from pykrforest import ForestAuthError, ForestClient

from .conftest import FakeResponse, FakeSession, xml_payload


def test_from_env_uses_tripmate_fallback(monkeypatch):
    monkeypatch.delenv("PYKRFOREST_SERVICE_KEY", raising=False)
    monkeypatch.delenv("KFS_SERVICE_KEY", raising=False)
    monkeypatch.delenv("FOREST_SERVICE_KEY", raising=False)
    monkeypatch.delenv("DATA_GO_SERVICE_KEY", raising=False)
    monkeypatch.setenv("TRIPMATE_DATA_GO_SERVICE_KEY", "ENV_KEY")
    session = FakeSession([FakeResponse(text=xml_payload("<item><id>1</id></item>"))])

    client = ForestClient.from_env(session=session)
    client.travel.forest_services()

    assert session.calls[0]["params"]["ServiceKey"] == "ENV_KEY"


def test_missing_env_raises(monkeypatch):
    for name in (
        "PYKRFOREST_SERVICE_KEY",
        "KFS_SERVICE_KEY",
        "FOREST_SERVICE_KEY",
        "DATA_GO_SERVICE_KEY",
        "TRIPMATE_DATA_GO_SERVICE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ForestAuthError):
        ForestClient.from_env()
