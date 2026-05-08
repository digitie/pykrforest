from __future__ import annotations

import pytest

from pykrforest import ForestAuthError, Page
from pykrforest.exceptions import ForestNoDataError

from .conftest import FakeResponse, public_payload, xml_payload


def test_legacy_xml_endpoint_sends_service_key_and_parses_page(fake_client_factory):
    xml = xml_payload(
        """
        <item>
          <dullegilid>dulle_18</dullegilid>
          <dullegildistance>13.4</dullegildistance>
        </item>
        """,
        num_of_rows=1,
    )
    client, session = fake_client_factory(FakeResponse(text=xml))

    page = client.travel.forest_services(num_of_rows=1)

    call = session.calls[0]
    assert call["url"].endswith("/trailInfoService/getforestservice")
    assert call["params"]["ServiceKey"] == "TEST_KEY"
    assert call["params"]["numOfRows"] == 1
    assert page.items == ({"dullegilid": "dulle_18", "dullegildistance": "13.4"},)
    assert page.total_count == 1
    assert page.context.provider == "forest.go.kr"
    assert page.context.endpoint == "getforestservice"
    assert "ServiceKey" not in page.context.request_params
    assert "TEST_KEY" not in repr(page.context.request_params)


def test_data_go_json_endpoint_adds_type_and_parses_items(fake_client_factory):
    payload = public_payload(
        [{"doname": "전국", "meanavg": "27"}, {"doname": "서울", "meanavg": "22"}],
        total_count=2,
    )
    client, session = fake_client_factory(FakeResponse(payload))

    page = client.safety.wildfire_risk_forecast(exclude_forecast=True, num_of_rows=2)

    call = session.calls[0]
    assert call["url"].endswith("/forestPoint/forestPointListGeongugSearch")
    assert call["params"]["_type"] == "json"
    assert call["params"]["excludeForecast"] == 1
    assert page.items[0]["doname"] == "전국"
    assert page.items[1]["meanavg"] == "22"
    assert page.context.provider == "data.go.kr"
    assert "ServiceKey" not in page.context.request_params


def test_wildfire_stats_maps_date_arguments(fake_client_factory):
    client, session = fake_client_factory(FakeResponse(public_payload([])))

    client.safety.wildfire_stats(
        search_start_date="20240101",
        search_end_date="20241231",
        num_of_rows=1,
    )

    params = session.calls[0]["params"]
    assert params["searchStDt"] == "20240101"
    assert params["searchEdDt"] == "20241231"


def test_iter_pages_uses_page_metadata(fake_client_factory):
    client, session = fake_client_factory(
        FakeResponse(
            xml_payload("<item><id>1</id></item>", page_no=1, num_of_rows=1, total_count=2)
        ),
        FakeResponse(
            xml_payload("<item><id>2</id></item>", page_no=2, num_of_rows=1, total_count=2)
        ),
    )

    pages = list(client.iter_pages(client.travel.forest_services, num_of_rows=1))

    assert [page.page_no for page in pages] == [1, 2]
    assert [page.items[0]["id"] for page in pages] == ["1", "2"]
    assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]


def test_page_helpers():
    page = Page(items=(1, 2), total_count=3, page_no=1, num_of_rows=2, raw={})

    assert page.has_next_page is True
    assert page.next_page_no == 2
    assert page.is_empty is False


def test_auth_error_redacts_key(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse(status_code=403, text="Forbidden TEST_KEY"))

    with pytest.raises(ForestAuthError) as exc_info:
        client.travel.forest_services()

    assert "[redacted]" in str(exc_info.value)
    assert "TEST_KEY" not in str(exc_info.value)
    assert exc_info.value.failure_kind == "auth"


def test_file_download_url_from_json_ld(fake_client_factory):
    html = """
    <html><head>
      <script type="application/ld+json">
      {"distribution": [{"@type": "DataDownload",
        "contentUrl": "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_1&fileDetailSn=1"}]}
      </script>
    </head></html>
    """
    client, session = fake_client_factory(
        FakeResponse(text=html),
        FakeResponse(text=html),
        FakeResponse(text="id,name\n1,trail\n", content=b"id,name\n1,trail\n"),
    )

    url = client.files.download_url("15112801")
    data = client.files.download("15112801")

    assert url.endswith("atchFileId=FILE_1&fileDetailSn=1")
    assert data.startswith(b"id,name")
    assert session.calls[0]["url"].endswith("/15112801/fileData.do")
    assert session.calls[1]["url"].endswith("/15112801/fileData.do")
    assert session.calls[2]["url"].endswith("atchFileId=FILE_1&fileDetailSn=1")


def test_file_download_url_missing_content_url_raises(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse(text="<html></html>"))

    with pytest.raises(ForestNoDataError):
        client.files.download_url("15112801")
