from __future__ import annotations

import pytest

from krforest import API_ENDPOINTS, FILE_DATASETS, api_catalog, api_endpoints, file_datasets
from krforest.catalog import (
    DATA_GO_API_ACCOUNT_URL,
    api_endpoint,
    catalog_entries,
    catalog_entry,
    file_catalog,
    file_dataset,
)


def test_catalog_has_travel_and_safety_api_endpoints():
    keys = {endpoint.key for endpoint in API_ENDPOINTS}

    assert "forest_trail_services" in keys
    assert "national_recreation_forest_reservations" in keys
    assert "standard_recreation_forests" in keys
    assert "wildfire_stats" in keys
    assert "landslide_predictions" in keys
    assert {endpoint.provider for endpoint in API_ENDPOINTS} == {"forest.go.kr", "data.go.kr"}


def test_catalog_filters_by_category():
    travel = api_endpoints("travel")
    safety = file_datasets("safety")

    assert travel
    assert safety
    assert all("travel" in endpoint.categories for endpoint in travel)
    assert all("safety" in dataset.categories for dataset in safety)


def test_catalog_lookup_and_invalid_category():
    assert api_endpoint("baekdu_trails").data_go_id == "15002731"
    assert api_endpoint("national_recreation_forest_reservations").service_key_param == (
        "serviceKey"
    )
    assert api_endpoint("national_recreation_forest_reservations").response_format == "xml"
    standard = api_endpoint("standard_recreation_forests")
    assert standard.data_go_id == "15013111"
    assert standard.service_key_param == "serviceKey"
    assert standard.response_type_param == "type"
    assert file_dataset("15112801").formats == ("CSV",)
    assert file_dataset("PBD0000041").provider == "forest.go.kr"
    assert file_dataset("PBD0000031").download_path == "/trail/dule.zip"
    assert file_dataset("PBD0000221").download_path == "/sanrimedu/sanrimedu.zip"
    assert file_dataset("PBD0000220").provider == "forest.go.kr"
    assert file_dataset("PBD0000077").download_path == "traVllg_20141202.zip"
    assert file_dataset("PBD0000180").download_purpose_code == "3"
    assert file_dataset("PBD0000210").categories == ("safety",)

    with pytest.raises(ValueError, match="category"):
        api_endpoints("biology")


def test_human_readable_catalog_entries():
    reservation = catalog_entry("national_recreation_forest_reservations")
    reservation_by_id = catalog_entry("15134227")
    reservation_file = catalog_entry("15064418")

    assert reservation.kind == "api"
    assert reservation.dataset_name == "산림청_국립자연휴양림 예약정보"
    assert reservation.display_name == reservation.dataset_name
    assert reservation.service_key_url == reservation.detail_url
    assert reservation.service_key_url == "https://www.data.go.kr/data/15134227/openapi.do"
    assert reservation.service_key_account_url == DATA_GO_API_ACCOUNT_URL
    standard = catalog_entry("standard_recreation_forests")
    assert standard.dataset_name == "전국휴양림표준데이터"
    assert standard.service_key_url == "https://www.data.go.kr/data/15013111/standard.do"
    assert standard.response_type_param == "type"
    assert reservation_by_id == reservation
    assert reservation_file.kind == "file_dataset"
    assert reservation_file.service_key_url is None
    assert reservation_file.display_name == "산림청 국립자연휴양림관리소_국립자연휴양림 예약 정보"
    assert "예약 정보" in reservation_file.dataset_name
    assert any(entry.key == "wildfire_stats" for entry in api_catalog("safety"))
    assert any(entry.dataset_name for entry in file_catalog("travel"))
    assert len(catalog_entries("travel")) == len(api_endpoints("travel")) + len(
        file_datasets("travel")
    )


def test_file_catalog_keeps_to_travel_and_safety_scope():
    titles = " ".join(dataset.title for dataset in FILE_DATASETS)

    assert "산사태" in titles
    assert "숲길" in titles
    assert "산림교육센터" in titles
    assert "전통마을숲" in titles
    assert "국가표준곤충목록" not in titles
