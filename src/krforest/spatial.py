"""산림청 SHP ZIP 파일을 사용자용 공간 레코드로 변환한다."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping
from typing import Any

from kraddr.base import Address, PlaceCoordinate

from ._convert import strip_or_none, to_float_or_none
from .exceptions import ForestParseError
from .models import FileDataset, ForestSpatialPoint
from .parser import first_text

_NAME_KEYS = ("name", "이름", "RCAR_NM", "명칭", "시설명")
_ADDRESS_KEYS = ("address", "주소", "DTADD", "소재지주소", "소재지도로명주소", "소재지지번주소")
_CATEGORY_KEYS = ("category", "RCAR_SCTIN", "운영현황", "구분", "종류")
_PHONE_KEYS = ("phone_number", "TEL_NO", "telNo", "전화번호", "연락처")
_HOMEPAGE_KEYS = ("homepage_url", "SITE_URL", "url", "URL", "홈페이지")
_YEAR_KEYS = ("year", "연도")
_OWNER_KEYS = ("owner_name", "OWNER_NM", "운영주체")
_STATUS_KEYS = ("operation_status", "운영현황")
_REGION_CODE_KEYS = ("region_code", "EMNDN_CD", "법정동코드")
_REGION_NAME_KEYS = ("region_name", "EMNDN_NM", "읍면동명")
_X_KEYS = ("POINT_X", "x", "X", "longitude", "lon", "경도")
_Y_KEYS = ("POINT_Y", "y", "Y", "latitude", "lat", "위도")


def forest_spatial_points(
    data: bytes,
    dataset: FileDataset,
    *,
    name: str | None = None,
) -> tuple[ForestSpatialPoint, ...]:
    """SHP ZIP bytes를 `ForestSpatialPoint` 튜플로 변환한다."""

    reader, prj_text = _open_reader(data)
    transformer = _coordinate_transformer(prj_text)
    name_filter = strip_or_none(name)
    points: list[ForestSpatialPoint] = []

    for shape_record in reader.iterShapeRecords():
        raw = _clean_record(shape_record.record.as_dict())
        point_name = first_text(raw, *_NAME_KEYS)
        if name_filter is not None and name_filter not in (point_name or ""):
            continue

        projected_x, projected_y = _record_point(raw, shape_record.shape)
        address = Address.from_mapping(raw)
        if address is None:
            address_text = first_text(raw, *_ADDRESS_KEYS)
            address = Address.from_text(address_text) if address_text is not None else None

        points.append(
            ForestSpatialPoint(
                dataset_id=dataset.data_go_id,
                dataset_name=dataset.title,
                name=point_name,
                category=first_text(raw, *_CATEGORY_KEYS),
                address=address,
                phone_number=first_text(raw, *_PHONE_KEYS),
                homepage_url=first_text(raw, *_HOMEPAGE_KEYS),
                coordinate=_place_coordinate(projected_x, projected_y, transformer),
                projected_x=projected_x,
                projected_y=projected_y,
                year=first_text(raw, *_YEAR_KEYS),
                owner_name=first_text(raw, *_OWNER_KEYS),
                operation_status=first_text(raw, *_STATUS_KEYS),
                region_code=first_text(raw, *_REGION_CODE_KEYS),
                region_name=first_text(raw, *_REGION_NAME_KEYS),
                raw=raw,
            )
        )

    return tuple(points)


def _open_reader(data: bytes) -> tuple[Any, str | None]:
    try:
        import shapefile  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ForestParseError(
            "pyshp is required to parse forest.go.kr SHP datasets",
            provider="forest.go.kr",
            failure_kind="parse",
        ) from exc

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ForestParseError(
            "forest.go.kr dataset was not a valid ZIP archive",
            provider="forest.go.kr",
            failure_kind="parse",
        ) from exc

    names = archive.namelist()
    shp_name = _member_by_suffix(names, ".shp")
    shx_name = _member_by_suffix(names, ".shx")
    dbf_name = _member_by_suffix(names, ".dbf")
    prj_name = _member_by_suffix(names, ".prj")
    if shp_name is None or shx_name is None or dbf_name is None:
        raise ForestParseError(
            "forest.go.kr SHP archive must include .shp, .shx, and .dbf files",
            provider="forest.go.kr",
            failure_kind="parse",
        )

    prj_text = archive.read(prj_name).decode("ascii", errors="ignore") if prj_name else None
    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(shp_name)),
        shx=io.BytesIO(archive.read(shx_name)),
        dbf=io.BytesIO(archive.read(dbf_name)),
        encoding="cp949",
    )
    return reader, prj_text


def _member_by_suffix(names: list[str], suffix: str) -> str | None:
    for name in names:
        if name.lower().endswith(suffix):
            return name
    return None


def _clean_record(record: Mapping[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in record.items():
        name = str(key).strip()
        if not name:
            continue
        if isinstance(value, str):
            text = strip_or_none(value)
            if text is not None:
                clean[name] = text
        elif value is not None:
            clean[name] = value
    return clean


def _record_point(raw: Mapping[str, Any], shape: Any) -> tuple[float | None, float | None]:
    x = to_float_or_none(first_text(raw, *_X_KEYS))
    y = to_float_or_none(first_text(raw, *_Y_KEYS))
    if x is not None and y is not None:
        return x, y

    points = getattr(shape, "points", None) or []
    if points:
        point = points[0]
        return to_float_or_none(point[0]), to_float_or_none(point[1])

    bbox = getattr(shape, "bbox", None)
    if bbox and len(bbox) >= 4:
        return (float(bbox[0]) + float(bbox[2])) / 2, (float(bbox[1]) + float(bbox[3])) / 2
    return None, None


def _coordinate_transformer(prj_text: str | None) -> Any:
    try:
        from pyproj import CRS, Transformer
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ForestParseError(
            "pyproj is required to convert forest.go.kr SHP coordinates to WGS84",
            provider="forest.go.kr",
            failure_kind="parse",
        ) from exc

    source = CRS.from_wkt(prj_text) if prj_text else CRS.from_epsg(5179)
    return Transformer.from_crs(source, CRS.from_epsg(4326), always_xy=True)


def _place_coordinate(
    x: float | None,
    y: float | None,
    transformer: Any,
) -> PlaceCoordinate | None:
    if x is None or y is None:
        return None
    if -180 <= x <= 180 and -90 <= y <= 90:
        return PlaceCoordinate(lon=x, lat=y)
    lon, lat = transformer.transform(x, y)
    return PlaceCoordinate(lon=lon, lat=lat)
