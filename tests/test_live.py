from __future__ import annotations

import os

import pytest

from pykrforest import ForestAuthError, ForestClient

pytestmark = pytest.mark.live


def _service_key() -> str:
    for name in (
        "PYKRFOREST_SERVICE_KEY",
        "KFS_SERVICE_KEY",
        "FOREST_SERVICE_KEY",
        "DATA_GO_SERVICE_KEY",
        "TRIPMATE_DATA_GO_SERVICE_KEY",
    ):
        value = os.getenv(name)
        if value:
            return value
    pytest.skip("no Korea public-data service key environment variable is set")


def test_live_legacy_forest_services_returns_items():
    key = _service_key()
    client = ForestClient(key, timeout=20)

    page = client.travel.forest_services(num_of_rows=1)

    assert page.page_no >= 1
    assert page.num_of_rows >= 1
    assert page.total_count >= len(page.items)
    assert page.context.provider == "forest.go.kr"
    assert page.context.endpoint == "getforestservice"
    assert "ServiceKey" not in page.context.request_params
    assert key not in repr(page.context.request_params)
    assert page.items


def test_live_file_dataset_download_url_is_discoverable():
    key = _service_key()
    client = ForestClient(key, timeout=20)

    url = client.files.download_url("15112801")

    assert url.startswith("https://www.data.go.kr/cmm/cmm/fileDownload.do")
    assert "atchFileId=" in url
    assert "fileDetailSn=" in url


def test_live_data_go_safety_endpoint_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(key, timeout=20)

    try:
        page = client.safety.wildfire_stats(
            search_start_date="20240101",
            search_end_date="20241231",
            num_of_rows=1,
        )
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 1400000 forest safety APIs are not approved for this key")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.total_count >= len(page.items)


def test_live_recreation_forest_reservations_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(key, timeout=20)

    try:
        page = client.travel.recreation_forest_reservations(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15134227 recreation forest reservation API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "nationalRecreationForestReservationList"
        assert "serviceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)
