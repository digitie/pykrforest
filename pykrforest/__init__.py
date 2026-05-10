"""산림청 여행·안전 공공데이터 Python 클라이언트."""

from __future__ import annotations

from pykrtour import PlaceCoordinate

from .catalog import API_ENDPOINTS, FILE_DATASETS, api_endpoints, file_datasets
from .client import ForestClient, KrForestClient, PyKrForestClient
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
    ErosionControlDam,
    FileDataset,
    MountainWeather,
    Page,
    RawRecord,
)

__all__ = [
    "API_ENDPOINTS",
    "FILE_DATASETS",
    "ApiEndpoint",
    "CallContext",
    "ErosionControlDam",
    "FileDataset",
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
    "api_endpoints",
    "file_datasets",
]
