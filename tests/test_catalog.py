from __future__ import annotations

import pytest

from pykrforest import API_ENDPOINTS, FILE_DATASETS, api_endpoints, file_datasets
from pykrforest.catalog import api_endpoint, file_dataset


def test_catalog_has_travel_and_safety_api_endpoints():
    keys = {endpoint.key for endpoint in API_ENDPOINTS}

    assert "forest_trail_services" in keys
    assert "national_recreation_forest_reservations" in keys
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
    assert file_dataset("15112801").formats == ("CSV",)

    with pytest.raises(ValueError, match="category"):
        api_endpoints("biology")


def test_file_catalog_keeps_to_travel_and_safety_scope():
    titles = " ".join(dataset.title for dataset in FILE_DATASETS)

    assert "산사태" in titles
    assert "숲길" in titles
    assert "국가표준곤충목록" not in titles
