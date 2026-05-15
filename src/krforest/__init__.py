"""산림청 여행·안전 공공데이터 Python 클라이언트."""

from __future__ import annotations

from kraddr.base import Address, PlaceCoordinate

from .catalog import (
    API_ENDPOINTS,
    DATA_GO_API_ACCOUNT_URL,
    FILE_DATASETS,
    api_catalog,
    api_endpoints,
    catalog_entries,
    catalog_entry,
    file_catalog,
    file_datasets,
)
from .client import ForestClient, KrForestClient, PyKrForestClient
from .debug import DebugRun, jsonable, redact_sensitive, save_fixture
from .exceptions import (
    ForestApiError,
    ForestAuthError,
    ForestNoDataError,
    ForestParseError,
    ForestRateLimitError,
    ForestRequestError,
    ForestServerError,
)
from .models import (
    ApiEndpoint,
    CallContext,
    CatalogEntry,
    ErosionControlDam,
    FileDataset,
    ForestSpatialPoint,
    MountainWeather,
    Page,
    RawRecord,
    RecreationForest,
    RecreationForestReservation,
    StandardRecreationForest,
)

__all__ = [
    "API_ENDPOINTS",
    "Address",
    "DATA_GO_API_ACCOUNT_URL",
    "FILE_DATASETS",
    "ApiEndpoint",
    "CallContext",
    "CatalogEntry",
    "DebugRun",
    "ErosionControlDam",
    "FileDataset",
    "ForestSpatialPoint",
    "ForestApiError",
    "ForestAuthError",
    "ForestClient",
    "ForestNoDataError",
    "ForestParseError",
    "ForestRateLimitError",
    "ForestRequestError",
    "ForestServerError",
    "KrForestClient",
    "MountainWeather",
    "Page",
    "PlaceCoordinate",
    "PyKrForestClient",
    "RawRecord",
    "RecreationForest",
    "RecreationForestReservation",
    "StandardRecreationForest",
    "api_catalog",
    "api_endpoints",
    "catalog_entries",
    "catalog_entry",
    "file_catalog",
    "file_datasets",
    "jsonable",
    "redact_sensitive",
    "save_fixture",
]
