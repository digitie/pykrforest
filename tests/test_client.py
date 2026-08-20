from __future__ import annotations

import pytest

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


def line_shp_zip(tmp_path) -> bytes:
    import zipfile

    import shapefile

    base = tmp_path / "dule"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYLINE, encoding="cp949")
    writer.field("Name", "C", size=80)
    writer.field("ID", "C", size=20)
    writer.line([[(953901.165, 1952032.08), (954901.165, 1953032.08)]])
    writer.record("지리산둘레길 테스트", "DULE-1")
    writer.close()
    base.with_suffix(".prj").write_text(KOREA_2000_UNIFIED_WKT, encoding="ascii")

    archive_path = tmp_path / "dule.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf", ".prj"):
            archive.write(base.with_suffix(suffix), arcname=f"dule{suffix}")
    return archive_path.read_bytes()


def nested_line_shp_zip(tmp_path) -> bytes:
    import zipfile

    inner = line_shp_zip(tmp_path)
    archive_path = tmp_path / "mountain.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("mountain/123456789.zip", inner)
        archive.writestr("mountain/123456789_geojson.zip", b"not parsed")
        archive.writestr("mountain/123456789_gpx.zip", b"not parsed")
    return archive_path.read_bytes()


def same_name_line_shp_zip(tmp_path) -> bytes:
    import zipfile

    import shapefile

    base = tmp_path / "same-name"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYLINE, encoding="cp949")
    writer.field("Name", "C", size=80)
    writer.field("ID", "C", size=20)
    writer.line([[(953901.165, 1952032.08), (954901.165, 1953032.08)]])
    writer.record("같은 노선명", "DULE-1")
    writer.line([[(953901.165, 1952032.08), (955901.165, 1954032.08)]])
    writer.record("같은 노선명", "DULE-2")
    writer.close()
    base.with_suffix(".prj").write_text(KOREA_2000_UNIFIED_WKT, encoding="ascii")

    archive_path = tmp_path / "same-name.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf", ".prj"):
            archive.write(base.with_suffix(suffix), arcname=f"same-name{suffix}")
    return archive_path.read_bytes()


def same_name_without_id_line_shp_zip(tmp_path) -> bytes:
    import zipfile

    import shapefile

    base = tmp_path / "same-name-no-id"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYLINE, encoding="cp949")
    writer.field("Name", "C", size=80)
    writer.line([[(953901.165, 1952032.08), (954901.165, 1953032.08)]])
    writer.record("같은 노선명")
    writer.line([[(953901.165, 1952032.08), (955901.165, 1954032.08)]])
    writer.record("같은 노선명")
    writer.close()
    base.with_suffix(".prj").write_text(KOREA_2000_UNIFIED_WKT, encoding="ascii")

    archive_path = tmp_path / "same-name-no-id.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf", ".prj"):
            archive.write(base.with_suffix(suffix), arcname=f"same-name-no-id{suffix}")
    return archive_path.read_bytes()


def binary_zip(tmp_path) -> bytes:
    import zipfile

    archive_path = tmp_path / "risk.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("risk.tif", b"TIFF")
        archive.writestr("risk.tif.xml", b"<metadata />")
    return archive_path.read_bytes()


async def test_legacy_xml_endpoint_sends_service_key_and_parses_page(fake_client_factory):
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

    page = await client.travel.forest_services(num_of_rows=1)

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


async def test_data_go_json_endpoint_adds_type_and_parses_items(fake_client_factory):
    payload = public_payload(
        [
            {
                "doname": "전국",
                "meanavg": "27",
                "analdate": "202608201200",
                "regioncode": "00",
            },
            {"doname": "서울", "meanavg": "22", "analdate": "202608201200"},
        ],
        total_count=2,
    )
    client, session = fake_client_factory(FakeResponse(payload))

    page = await client.safety.wildfire_risk_forecast(exclude_forecast=True, num_of_rows=2)

    call = session.calls[0]
    assert call["url"].endswith("/forestPointV2/forestPointListGeongugSearchV2")
    assert call["params"]["_type"] == "json"
    assert call["params"]["excludeForecast"] == 1
    assert page.items[0].region_name == "전국"
    assert page.items[1].mean_average == 22.0
    assert page.items[0].analysis_at is not None
    assert page.items[0].analysis_at.utcoffset() is not None
    assert page.context.provider == "data.go.kr"
    assert "ServiceKey" not in page.context.request_params


async def test_wildfire_risk_sido_and_sigungu_use_v2_filters(fake_client_factory):
    sido_payload = public_payload({"doname": "강원특별자치도", "meanavg": "18"})
    sigungu_payload = public_payload(
        {
            "doname": "강원특별자치도",
            "sigun": "속초시",
            "regioncode": "51",
            "sigucode": "51820",
            "meanavg": "18",
        }
    )
    client, session = fake_client_factory(
        FakeResponse(sido_payload), FakeResponse(sigungu_payload)
    )

    sido = await client.safety.wildfire_risk_forecast_sido(
        local_areas="51000", num_of_rows=1
    )
    sigungu = await client.safety.wildfire_risk_forecast_sigungu(
        local_areas="51820", upper_local_code="51", num_of_rows=1
    )

    assert sido.items[0].scope == "sido"
    assert session.calls[0]["url"].endswith("/forestPointV2/forestPointListSidoSearchV2")
    assert session.calls[0]["params"]["localAreas"] == "51000"
    assert sigungu.items[0].scope == "sigungu"
    assert session.calls[1]["url"].endswith(
        "/forestPointV2/forestPointListSigunguSearchV2"
    )
    assert session.calls[1]["params"]["localAreas"] == "51820"
    assert session.calls[1]["params"]["upplocalcd"] == "51"
    assert sigungu.items[0].region_code == "51820"
    assert sigungu.items[0].region_name == "속초시"


async def test_standard_recreation_forests_uses_type_param_and_models(fake_client_factory):
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

    page = await client.travel.standard_recreation_forests(
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
    assert item.latitude == 37.871
    assert item.longitude == 127.956
    assert item.address == "강원특별자치도 홍천군 두촌면 가리산길 426"
    assert item.raw["instt_code"] == "4250000"


async def test_wildfire_stats_maps_date_arguments(fake_client_factory):
    client, session = fake_client_factory(FakeResponse(public_payload([])))

    await client.safety.wildfire_stats(
        search_start_date="20240101",
        search_end_date="20241231",
        num_of_rows=1,
    )

    params = session.calls[0]["params"]
    assert params["searchStDt"] == "20240101"
    assert params["searchEdDt"] == "20241231"


async def test_client_catalog_returns_human_readable_entries(fake_client_factory):
    client, _session = fake_client_factory()

    entries = client.catalog("travel")

    assert any(entry.key == "national_recreation_forest_reservations" for entry in entries)
    assert any(
        entry.display_name == "산림청 국립자연휴양림관리소_국립자연휴양림 예약 정보"
        for entry in entries
    )


async def test_mountain_weather_returns_place_coordinate(fake_client_factory):
    payload = public_payload(
        {
            "obsid": "OBS-01",
            "obsname": "관악산",
            "localarea": "서울",
            "tm": "202608201200",
            "tm10m": "25.1",
            "tm2m": "24.3",
            "hm10m": "70",
            "hm2m": "75",
            "pa": "1001.2",
            "rn": "0.2",
            "cprn": "0.1",
            "ts": "23.4",
            "wd10m": "180",
            "wd10mstr": "남",
            "wd2m": "170",
            "wd2mstr": "남남동",
            "ws10m": "2.1",
            "ws2m": "1.4",
            "xValue": "126.9636",
            "yValue": "37.4450",
        },
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = await client.travel.mountain_weather(num_of_rows=1)

    assert page.items[0].latitude == 37.445
    assert page.items[0].longitude == 126.9636
    assert page.items[0].obs_id == "OBS-01"
    assert page.items[0].temperature_2m == 24.3
    assert page.items[0].observed_at is not None
    assert page.items[0].observed_at.utcoffset() is not None
    assert page.items[0].raw["obsname"] == "관악산"


async def test_landslide_forecast_issues_are_typed(fake_client_factory):
    payload = public_payload(
        {
            "frcstIssuKindCd": "1",
            "frcstIssuKindNm": "산사태주의보",
            "ocrnFrcstIssuInsttNm": "산림청",
            "frcstIssuStts": "발령",
            "frstFrcstIssuDt": "2026-08-20 12:00:00",
        }
    )
    client, session = fake_client_factory(FakeResponse(payload))

    page = await client.safety.landslide_forecast_issues(num_of_rows=1)

    assert session.calls[0]["url"].endswith("/forecastIssueService/forecastIssueList")
    assert session.calls[0]["params"]["_type"] == "json"
    assert page.items[0].issue_kind_name == "산사태주의보"
    assert page.items[0].issuing_institution == "산림청"
    assert page.items[0].issued_at is not None
    assert page.items[0].issued_at.utcoffset() is not None


async def test_mountain_weather_missing_coordinate_is_none(fake_client_factory):
    payload = public_payload(
        {"stationName": "관악산", "xValue": "-99.000000", "yValue": "-99.000000"},
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = await client.travel.mountain_weather(num_of_rows=1)

    assert page.items[0].latitude is None
    assert page.items[0].longitude is None
    assert page.items[0].raw["stationName"] == "관악산"


async def test_erosion_control_dams_returns_place_coordinate(fake_client_factory):
    payload = public_payload(
        {"name": "테스트사방댐", "longitude": "127.1", "latitude": "37.2"},
        total_count=1,
    )
    client, _session = fake_client_factory(FakeResponse(payload))

    page = await client.safety.erosion_control_dams(num_of_rows=1)

    assert page.items[0].latitude == 37.2
    assert page.items[0].longitude == 127.1
    assert page.items[0].raw["name"] == "테스트사방댐"


async def test_recreation_forest_reservations_uses_lowercase_service_key(fake_client_factory):
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

    page = await client.travel.recreation_forest_reservations(
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


async def test_recreation_forests_combines_files_with_address_and_coordinate(fake_client_factory):
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

    forests = await client.travel.recreation_forests()

    assert [call["url"] for call in session.calls[::2]] == [
        "https://www.data.go.kr/data/15064415/fileData.do",
        "https://www.data.go.kr/data/15064419/fileData.do",
        "https://www.data.go.kr/data/15064416/fileData.do",
        "https://www.data.go.kr/data/15064418/fileData.do",
    ]
    forest = forests[0]
    assert forest.institution_id == "FR001"
    assert forest.name == "덕유산자연휴양림"
    assert forest.latitude == 35.9
    assert forest.longitude == 127.8
    assert forest.address == "전북 무주군 무풍면 구천동로 530-62"
    assert forest.phone_number == "063-322-1097"
    assert forest.homepage_url == "https://www.foresttrip.go.kr"
    assert forest.facilities[0]["상품명"] == "숲속의집"
    assert forest.reservation_policies[0]["정책구분"] == "추첨"
    assert forest.reservation_records[0].goods_name == "숲속의집"


async def test_iter_pages_uses_page_metadata(fake_client_factory):
    client, session = fake_client_factory(
        FakeResponse(
            xml_payload("<item><id>1</id></item>", page_no=1, num_of_rows=1, total_count=2)
        ),
        FakeResponse(
            xml_payload("<item><id>2</id></item>", page_no=2, num_of_rows=1, total_count=2)
        ),
    )

    pages = [page async for page in client.iter_pages(client.travel.forest_services, num_of_rows=1)]

    assert [page.page_no for page in pages] == [1, 2]
    assert [page.items[0]["id"] for page in pages] == ["1", "2"]
    assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]


async def test_page_helpers():
    page = Page(items=(1, 2), total_count=3, page_no=1, num_of_rows=2, raw={})

    assert page.has_next_page is True
    assert page.next_page_no == 2
    assert page.is_empty is False


async def test_auth_error_redacts_key(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse(status_code=403, text="Forbidden TEST_KEY"))

    with pytest.raises(ForestAuthError) as exc_info:
        await client.travel.forest_services()

    assert "[redacted]" in str(exc_info.value)
    assert "TEST_KEY" not in str(exc_info.value)
    assert exc_info.value.failure_kind == "auth"


async def test_body_level_auth_error_redacts_key_from_message_and_response(
    fake_client_factory,
):
    payload = public_payload(None, result_code="20", result_msg="bad TEST_KEY")
    client, _session = fake_client_factory(FakeResponse(payload))

    with pytest.raises(ForestAuthError) as exc_info:
        await client.travel.forest_services()

    assert "TEST_KEY" not in str(exc_info.value)
    assert "TEST_KEY" not in repr(exc_info.value.response)
    assert "[redacted]" in str(exc_info.value)


async def test_file_download_url_from_json_ld(fake_client_factory):
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

    url = await client.files.download_url("15112801")
    data = await client.files.download("15112801")

    assert url.endswith("atchFileId=FILE_1&fileDetailSn=1")
    assert data.startswith(b"id,name")
    assert session.calls[0]["url"].endswith("/15112801/fileData.do")
    assert session.calls[1]["url"].endswith("/15112801/fileData.do")
    assert session.calls[2]["url"].endswith("atchFileId=FILE_1&fileDetailSn=1")


async def test_forest_go_shp_download_submits_personal_purpose(fake_client_factory):
    client, session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=b"PK\x03\x04zip"),
    )

    data = await client.files.download("PBD0000220")

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


async def test_safety_forest_go_download_uses_safety_tab_and_returns_archive_files(
    fake_client_factory,
    tmp_path,
):
    archive = binary_zip(tmp_path)
    client, session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    files = await client.safety.landslide_risk_map_files()

    popup_call, history_call, download_call = session.calls
    assert popup_call["params"]["pblicDataId"] == "PBD0000210"
    assert popup_call["params"]["tabs"] == "4"
    assert history_call["data"]["tabs"] == "4"
    assert history_call["data"]["dnldPrps"] == "3"
    assert download_call["url"].endswith("/fileDown.do?dataType=/sansatae/LDM_50110.zip")
    assert files["risk.tif"] == b"TIFF"
    assert files["risk.tif.xml"] == b"<metadata />"


async def test_forest_education_centers_parse_shp(fake_client_factory, tmp_path):
    archive = shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    records = await client.travel.forest_education_centers(name="테스트")

    assert len(records) == 1
    assert records[0].dataset_id == "PBD0000221"
    assert records[0].name == "테스트 유아숲체험원"
    assert records[0].operation_status == "운영"
    assert records[0].latitude is not None
    assert records[0].longitude is not None


async def test_kid_forest_centers_parse_shp_with_address_and_coordinate(
    fake_client_factory,
    tmp_path,
):
    archive = shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    records = await client.travel.kid_forest_centers(name="테스트")

    assert len(records) == 1
    record = records[0]
    assert record.dataset_id == "PBD0000220"
    assert record.name == "테스트 유아숲체험원"
    assert record.operation_status == "운영"
    assert record.address == "서울특별시 중구 세종대로 110"
    assert record.latitude is not None
    assert record.longitude is not None
    assert 126.0 < record.longitude < 128.0
    assert 37.0 < record.latitude < 38.0


async def test_dulle_trail_features_parse_line_shp(fake_client_factory, tmp_path):
    archive = line_shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    features = await client.travel.dulle_trail_features(name="지리산")

    assert len(features) == 1
    feature = features[0]
    assert feature.dataset_id == "PBD0000031"
    assert feature.name == "지리산둘레길 테스트"
    assert feature.geometry_type == "LineString"
    assert feature.geometry is not None
    assert feature.bbox is not None
    assert feature.latitude is not None
    assert feature.longitude is not None
    assert 126.0 < feature.longitude < 128.0
    assert 37.0 < feature.latitude < 38.0


async def test_forest_trail_features_parse_nested_shp_archive(
    fake_client_factory,
    tmp_path,
):
    archive = nested_line_shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    features = await client.travel.forest_trail_file_features(name="지리산")

    assert len(features) == 1
    feature = features[0]
    assert feature.dataset_id == "PBD0000041"
    assert feature.geometry_type == "LineString"
    assert feature.source_id is not None
    assert ":keys:" in feature.source_id


async def test_spatial_source_id_keeps_same_name_segments_distinct(
    fake_client_factory,
    tmp_path,
):
    archive = same_name_line_shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    features = await client.travel.dulle_trail_features()

    assert len(features) == 2
    assert len({feature.source_id for feature in features}) == 2


async def test_spatial_source_id_keeps_name_only_segments_distinct(
    fake_client_factory,
    tmp_path,
):
    archive = same_name_without_id_line_shp_zip(tmp_path)
    client, _session = fake_client_factory(
        FakeResponse(text="<html>popup</html>"),
        FakeResponse(status_code=302, text="moved"),
        FakeResponse(content=archive),
    )

    features = await client.travel.dulle_trail_features()

    assert len(features) == 2
    assert len({feature.source_id for feature in features}) == 2


async def test_file_download_url_missing_content_url_raises(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse(text="<html></html>"))

    with pytest.raises(ForestNoDataError):
        await client.files.download_url("15112801")
