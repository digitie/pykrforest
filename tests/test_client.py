from __future__ import annotations

import pytest
from kraddr.base import Address, PlaceCoordinate

from krforest import ForestAuthError, Page
from krforest.exceptions import ForestNoDataError

from .conftest import FakeResponse, public_payload, xml_payload

KOREA_2000_UNIFIED_WKT = (
    'PROJCS["Korea_2000_Unified_CS",GEOGCS["GCS_Korea 2000",'
    'DATUM["D_Korea_2000",SPHEROID["GRS_1980",6378137,298.257222101]],'
    'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],'
    'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",38],'
    'PARAMETER["central_meridian",127.5],PARAMETER["scale_factor",0.9996],'
    'PARAMETER["false_easting",1000000],PARAMETER["false_northing",2000000],'
    'UNIT["Meter",1]]'
)


def download_html(name: str) -> str:
    return f"""
    <html><head>
      <script type="application/ld+json">
      {{"distribution": [{{"@type": "DataDownload",
        "contentUrl": "https://files.example.test/{name}.csv"}}]}}
      </script>
    </head></html>
    """


def shp_zip(tmp_path) -> bytes:
    import zipfile

    import shapefile

    base = tmp_path / "kidforest"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POINT, encoding="cp949")
    writer.field("이름", "C", size=80)
    writer.field("주소", "C", size=120)
    writer.field("운영현황", "C", size=40)
    writer.point(953901.165, 1952032.08)
    writer.record("테스트 유아숲체험원", "서울특별시 중구 세종대로 110", "운영")
    writer.close()
    base.with_suffix(".prj").write_text(KOREA_2000_UNIFIED_WKT, encoding="ascii")

    archive_path = tmp_path / "kidforest.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf", ".prj"):
            archive.write(base.with_suffix(suffix), arcname=f"kidforest{suffix}")
    return archive_path.read_bytes()


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


def test_standard_recreation_forests_uses_type_param_and_models(fake_client_factory):
    payload = public_payload(
        {
            "rcrfrstNm": "가리산자연휴양림",
            "ctprvnNm": "강원특별자치도",
            "rcrfrstType": "공립",
            "rcrfrstFcltyAr": "3050000",
            "aceptncCo": "1000",
            "admfee": "1000",
            "stayngPosblYn": "Y",
            "mstrFclty": "숲속의집",
            "rdnmadr": "강원특별자치도 홍천군 두촌면 가리산길 426",
            "latitude": "37.871",
            "longitude": "127.956",
            "phoneNumber": "033-435-6034",
            "institutionNm": "홍천군",
            "homepageUrl": "https://example.test",
            "referenceDate": "2025-01-01",
            "instt_code": "4250000",
        },
        total_count=1,
    )
    client, session = fake_client_factory(FakeResponse(payload))

    page = client.travel.standard_recreation_forests(
        sido_name="강원특별자치도",
        accommodation_available=True,
        num_of_rows=1,
    )

    call = session.calls[0]
    params = call["params"]
    assert call["url"] == "https://api.data.go.kr/openapi/tn_pubr_public_rcrfrst_api"
    assert params["serviceKey"] == "TEST_KEY"
    assert params["type"] == "json"
    assert "_type" not in params
    assert params["ctprvnNm"] == "강원특별자치도"
    assert params["stayngPosblYn"] == "Y"
    item = page.items[0]
    assert item.name == "가리산자연휴양림"
    assert item.coordinate == PlaceCoordinate(lon=127.956, lat=37.871)
    assert isinstance(item.address, Address)
    assert item.raw["instt_code"] == "4250000"


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


def test_client_catalog_returns_human_readable_entries(fake_client_factory):
    client, _session = fake_client_factory()

    entries = client.catalog("travel")

    assert any(entry.key == "national_recreation_forest_reservations" for entry in entries)
    assert any(
        entry.display_name == "산림청 국립자연휴양림관리소_국립자연휴양림 예약 정보"
        for entry in entries
    )


def test_mountain_weather_returns_place_coordinate(fake_client_factory):
    payload = public_payload(
        {"stationName": "관악산", "xValue": "126.9636", "yValue": "37.4450"},
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = client.travel.mountain_weather(num_of_rows=1)

    assert isinstance(page.items[0].coordinate, PlaceCoordinate)
    assert page.items[0].coordinate == PlaceCoordinate(lon=126.9636, lat=37.445)
    assert page.items[0].raw["stationName"] == "관악산"


def test_mountain_weather_missing_coordinate_is_none(fake_client_factory):
    payload = public_payload(
        {"stationName": "관악산", "xValue": "-99.000000", "yValue": "-99.000000"},
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = client.travel.mountain_weather(num_of_rows=1)

    assert page.items[0].coordinate is None
    assert page.items[0].raw["stationName"] == "관악산"


def test_erosion_control_dams_returns_place_coordinate(fake_client_factory):
    payload = public_payload(
        {"name": "테스트사방댐", "longitude": "127.1", "latitude": "37.2"},
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = client.safety.erosion_control_dams(num_of_rows=1)

    assert page.items[0].coordinate == PlaceCoordinate(lon=127.1, lat=37.2)
    assert page.items[0].raw["name"] == "테스트사방댐"


def test_recreation_forest_reservations_uses_lowercase_service_key(fake_client_factory):
    xml = xml_payload(
        """
        <item>
          <stngdt>20240228</stngdt>
          <goodsnm>숲속의집</goodsnm>
          <insttid>FR001</insttid>
          <insttnm>덕유산자연휴양림</insttnm>
          <status>예약가능</status>
        </item>
        """,
        num_of_rows=1,
    )
    client, session = fake_client_factory(FakeResponse(text=xml))

    page = client.travel.recreation_forest_reservations(
        goods_name="숲속의집",
        start_stay_date="20240228",
        end_stay_date="20240228",
        num_of_rows=1,
    )

    call = session.calls[0]
    params = call["params"]
    assert call["url"].endswith(
        "/nationalRecreationForestReservationService/nationalRecreationForestReservationList"
    )
    assert params["serviceKey"] == "TEST_KEY"
    assert "ServiceKey" not in params
    assert "_type" not in params
    assert params["goodsNm"] == "숲속의집"
    assert params["startStngDt"] == "20240228"
    assert params["endStngDt"] == "20240228"
    assert "serviceKey" not in page.context.request_params
    assert page.items[0].institution_id == "FR001"
    assert page.items[0].institution_name == "덕유산자연휴양림"
    assert page.items[0].goods_name == "숲속의집"
    assert page.items[0].stay_date == "20240228"
    assert page.items[0].status == "예약가능"


def test_recreation_forests_combines_files_with_address_and_coordinate(fake_client_factory):
    promotion_csv = (
        "기관ID,기관명,주소,전화번호,최대수용인원,운영시간,설명\n"
        "FR001,덕유산자연휴양림,전북 무주군 무풍면 구천동로 530-62,"
        "063-322-1097,500,09:00-18:00,덕유산 숲\n"
    )
    facility_csv = (
        "기관ID,기관명,상품명,위도,경도,홈페이지,지역\n"
        "FR001,덕유산자연휴양림,숲속의집,35.9000,127.8000,"
        "https://www.foresttrip.go.kr,전북\n"
    )
    policy_csv = "기관ID,기관명,정책구분,정책유형\nFR001,덕유산자연휴양림,추첨,주말\n"
    reservation_csv = (
        "insttid,insttnm,goodsnm,stngdt,status\n"
        "FR001,덕유산자연휴양림,숲속의집,20240228,예약가능\n"
    )
    client, session = fake_client_factory(
        FakeResponse(text=download_html("promotion")),
        FakeResponse(text=promotion_csv, content=promotion_csv.encode()),
        FakeResponse(text=download_html("facility")),
        FakeResponse(text=facility_csv, content=facility_csv.encode()),
        FakeResponse(text=download_html("policy")),
        FakeResponse(text=policy_csv, content=policy_csv.encode()),
        FakeResponse(text=download_html("reservation")),
        FakeResponse(text=reservation_csv, content=reservation_csv.encode()),
    )

    forests = client.travel.recreation_forests()

    assert [call["url"] for call in session.calls[::2]] == [
        "https://www.data.go.kr/data/15064415/fileData.do",
        "https://www.data.go.kr/data/15064419/fileData.do",
        "https://www.data.go.kr/data/15064416/fileData.do",
        "https://www.data.go.kr/data/15064418/fileData.do",
    ]
    forest = forests[0]
    assert forest.institution_id == "FR001"
    assert forest.name == "덕유산자연휴양림"
    assert forest.coordinate == PlaceCoordinate(lon=127.8, lat=35.9)
    assert isinstance(forest.address, Address)
    assert forest.address.display_address == "전북 무주군 무풍면 구천동로 530-62"
    assert forest.phone_number == "063-322-1097"
    assert forest.homepage_url == "https://www.foresttrip.go.kr"
    assert forest.facilities[0]["상품명"] == "숲속의집"
    assert forest.reservation_policies[0]["정책구분"] == "추첨"
    assert forest.reservation_records[0].goods_name == "숲속의집"


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


def test_forest_go_shp_download_submits_personal_purpose(fake_client_factory):
    client, session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=b"PK\x03\x04zip"),
    )

    data = client.files.download("PBD0000220")

    popup_call, history_call, download_call = session.calls
    assert popup_call["url"].endswith("/fileDownloadPopup.do")
    assert popup_call["params"]["pblicDataId"] == "PBD0000220"
    assert popup_call["params"]["fileNum"] == "/kidforest/kidforest.zip"
    assert history_call["method"] == "POST"
    assert history_call["url"].endswith("/insertDownHistory.do")
    assert history_call["data"]["dnldPrps"] == "3"
    assert history_call["data"]["useAgree01"] == "Y"
    assert download_call["url"].endswith("/fileDown.do?dataType=/kidforest/kidforest.zip")
    assert data == b"PK\x03\x04zip"


def test_kid_forest_centers_parse_shp_with_address_and_coordinate(
    fake_client_factory,
    tmp_path,
):
    archive = shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    records = client.travel.kid_forest_centers(name="테스트")

    assert len(records) == 1
    record = records[0]
    assert record.dataset_id == "PBD0000220"
    assert record.name == "테스트 유아숲체험원"
    assert record.operation_status == "운영"
    assert isinstance(record.address, Address)
    assert record.address.display_address == "서울특별시 중구 세종대로 110"
    assert isinstance(record.coordinate, PlaceCoordinate)
    assert 126.0 < record.coordinate.lon < 128.0
    assert 37.0 < record.coordinate.lat < 38.0


def test_file_download_url_missing_content_url_raises(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse(text="<html></html>"))

    with pytest.raises(ForestNoDataError):
        client.files.download_url("15112801")
