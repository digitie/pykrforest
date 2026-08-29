"""산림청 여행·안전 공공데이터 Python 클라이언트."""

from __future__ import annotations

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
from .client import ForestClient
from .config import ForestConfig
from .debug import DebugRun, debug_error, jsonable, redact_sensitive, save_fixture
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
    ForestSpatialFeature,
    ForestSpatialPoint,
    LandslideForecastIssue,
    MountainWeather,
    Page,
    RawRecord,
    RecreationForest,
    RecreationForestReservation,
    StandardRecreationForest,
    WildfireRiskForecast,
)

__version__ = "0.2.0"
PROVIDER_NAME = "python-krforest-api"

__all__ = [
    "API_ENDPOINTS",
    "PROVIDER_NAME",
    "DATA_GO_API_ACCOUNT_URL",
    "FILE_DATASETS",
    "ApiEndpoint",
    "CallContext",
    "CatalogEntry",
    "DebugRun",
    "ErosionControlDam",
    "FileDataset",
    "ForestConfig",
    "ForestSpatialFeature",
    "ForestSpatialPoint",
    "ForestApiError",
    "ForestAuthError",
    "ForestClient",
    "ForestNoDataError",
    "ForestParseError",
    "ForestRateLimitError",
    "ForestRequestError",
    "ForestServerError",
    "LandslideForecastIssue",
    "MountainWeather",
    "Page",
    "RawRecord",
    "RecreationForest",
    "RecreationForestReservation",
    "StandardRecreationForest",
    "WildfireRiskForecast",
    "__version__",
    "api_catalog",
    "api_endpoints",
    "catalog_entries",
    "catalog_entry",
    "debug_error",
    "file_catalog",
    "file_datasets",
    "jsonable",
    "redact_sensitive",
    "save_fixture",
]
