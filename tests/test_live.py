from __future__ import annotations

import os

import pytest

from krforest import ForestAuthError, ForestClient

pytestmark = pytest.mark.live

LIVE_TIMEOUT = 60


def _service_key() -> str:
    value = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if value:
        return value
    pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")


async def test_live_legacy_forest_services_returns_items():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    page = await client.travel.forest_services(num_of_rows=1)

    assert page.page_no >= 1
    assert page.num_of_rows >= 1
    assert page.total_count >= len(page.items)
    assert page.context.provider == "forest.go.kr"
    assert page.context.endpoint == "getforestservice"
    assert "ServiceKey" not in page.context.request_params
    assert key not in repr(page.context.request_params)
    assert page.items


async def test_live_file_dataset_download_url_is_discoverable():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    url = await client.files.download_url("15112801")

    assert url.startswith("https://www.data.go.kr/cmm/cmm/fileDownload.do")
    assert "atchFileId=" in url
    assert "fileDetailSn=" in url


async def test_live_data_go_safety_endpoint_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.safety.wildfire_stats(
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


async def test_live_mountain_weather_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.travel.mountain_weather(num_of_rows=1)
    except ForestAuthError as exc:
        assert exc.provider == "data.go.kr"
        assert exc.failure_kind == "auth"
        assert key not in str(exc)
        pytest.xfail("data.go.kr 15084696 mountain weather API is not approved")
    else:
        assert page.context.provider == "data.go.kr"
        assert page.context.endpoint == "mountListSearch"
        assert "ServiceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        assert page.total_count >= len(page.items)


async def test_live_recreation_forest_reservations_is_either_authorized_or_clean_auth_error():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    try:
        page = await client.travel.recreation_forest_reservations(num_of_rows=1)
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


async def test_live_forest_education_centers_download_and_parse():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    records = await client.travel.forest_education_centers()

    assert records
    assert records[0].dataset_id == "PBD0000221"
    assert records[0].coordinate is not None


async def test_live_landslide_risk_map_archive_downloads_files():
    key = _service_key()
    client = ForestClient(api_key=key, timeout=LIVE_TIMEOUT)

    files = await client.safety.landslide_risk_map_files()

    assert any(name.endswith(".tif") for name in files)
    assert any(name.endswith(".xml") for name in files)
