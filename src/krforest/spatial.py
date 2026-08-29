"""산림청 SHP ZIP 파일을 사용자용 공간 레코드로 변환한다."""

from __future__ import annotations

import hashlib
import io
import json
import posixpath
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Collection, Iterator, Mapping
from functools import lru_cache
from typing import Any

from ._convert import extract_address, strip_or_none, to_float_or_none
from .exceptions import ForestParseError
from .models import FileDataset, ForestSpatialFeature, ForestSpatialPoint
from .parser import first_text

_NAME_KEYS = (
    "name",
    "이름",
    "FOREST_NM",
    "RCAR_NM",
    "MNTN_NM",
    "PMNTN_NM",
    "명칭",
    "시설명",
)
_SOURCE_ID_KEYS = (
    "PMNTN_SN",
    "PAST_SPOT_",
    "OBJECTID",
    "FID",
    "Name",
    "name",
    "ID",
    "id",
)
_ADDRESS_KEYS = (
    "address",
    "주소",
    "POFLC_NM",
    "DTADD",
    "소재지주소",
    "소재지도로명주소",
    "소재지지번주소",
)
_CATEGORY_KEYS = (
    "category",
    "FRTP_NM",
    "MAIN_FORTR",
    "RCAR_SCTIN",
    "운영현황",
    "비고",
    "구분",
    "종류",
)
_PHONE_KEYS = ("phone_number", "TEL_NO", "telNo", "전화번호", "연락처")
_HOMEPAGE_KEYS = ("homepage_url", "SITE_URL", "url", "URL", "홈페이지")
_YEAR_KEYS = ("year", "연도")
_OWNER_KEYS = ("owner_name", "OWNER_NM", "운영주체", "관리주체")
_STATUS_KEYS = ("operation_status", "운영현황")
_REGION_CODE_KEYS = ("region_code", "EMD_CD", "EMNDN_CD", "STD_SGGCD", "법정동코드")
_REGION_NAME_KEYS = ("region_name", "지역", "EMD_NM", "EMNDN_NM", "읍면동명")
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
        address = extract_address(raw, extra_keys=_ADDRESS_KEYS)

        latitude, longitude = _wgs84_point(projected_x, projected_y, transformer)
        points.append(
            ForestSpatialPoint(
                dataset_id=dataset.data_go_id,
                dataset_name=dataset.title,
                name=point_name,
                category=first_text(raw, *_CATEGORY_KEYS),
                address=address,
                phone_number=first_text(raw, *_PHONE_KEYS),
                homepage_url=first_text(raw, *_HOMEPAGE_KEYS),
                latitude=latitude,
                longitude=longitude,
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


def forest_spatial_features(
    data: bytes,
    dataset: FileDataset,
    *,
    name: str | None = None,
    geometry_types: Collection[str] | None = None,
) -> tuple[ForestSpatialFeature, ...]:
    """SHP/GeoJSON/GPX ZIP bytes를 지도 앱에서 쓰기 쉬운 피처 tuple로 변환한다."""

    archive = _open_archive(data)
    name_filter = strip_or_none(name)
    geometry_type_filter = frozenset(geometry_types) if geometry_types is not None else None
    features: list[ForestSpatialFeature] = []
    seen_source_ids: set[str] = set()

    for reader, prj_text, source_file, layer_name in _open_readers_from_archive(archive):
        transformer = _coordinate_transformer(prj_text)
        for shape_record in reader.iterShapeRecords():
            raw = _clean_record(shape_record.record.as_dict())
            feature_name = _feature_name(raw)
            if name_filter is not None and name_filter not in (feature_name or ""):
                continue

            shape_geometry_type = _shape_geometry_type(shape_record.shape)
            if geometry_type_filter is not None and shape_geometry_type not in geometry_type_filter:
                continue
            geometry = _shape_geometry(shape_record.shape, transformer)
            source_id = _feature_source_id(raw, source_file, geometry)
            if source_id in seen_source_ids:
                continue
            seen_source_ids.add(source_id)
            latitude, longitude = _shape_centroid(shape_record.shape, transformer)
            features.append(
                ForestSpatialFeature(
                    dataset_id=dataset.data_go_id,
                    dataset_name=dataset.title,
                    source_file=source_file,
                    layer_name=layer_name,
                    source_id=source_id,
                    name=feature_name,
                    geometry_type=shape_geometry_type or _geometry_type(geometry),
                    geometry=geometry,
                    bbox=_shape_bbox(shape_record.shape, transformer),
                    latitude=latitude,
                    longitude=longitude,
                    raw=raw,
                )
            )

    for source_file, payload in _geojson_members(archive):
        for feature in _geojson_features(payload):
            raw = _clean_record(feature.get("properties", {}))
            feature_name = _feature_name(raw) or strip_or_none(feature.get("name"))
            if name_filter is not None and name_filter not in (feature_name or ""):
                continue
            geometry = feature.get("geometry")
            if not isinstance(geometry, Mapping):
                geometry = None
            geometry_type = _geometry_type(geometry)
            if geometry_type_filter is not None and geometry_type not in geometry_type_filter:
                continue
            source_id = _feature_source_id(raw, source_file, geometry)
            if source_id in seen_source_ids:
                continue
            seen_source_ids.add(source_id)
            latitude, longitude = _geometry_centroid(geometry)
            features.append(
                ForestSpatialFeature(
                    dataset_id=dataset.data_go_id,
                    dataset_name=dataset.title,
                    source_file=source_file,
                    layer_name=_layer_name(source_file),
                    source_id=source_id,
                    name=feature_name,
                    geometry_type=geometry_type,
                    geometry=dict(geometry) if geometry is not None else None,
                    bbox=_geometry_bbox(geometry),
                    latitude=latitude,
                    longitude=longitude,
                    raw=raw,
                )
            )

    for source_file, feature in _gpx_features(archive):
        raw = _clean_record(feature.get("properties", {}))
        feature_name = _feature_name(raw) or strip_or_none(feature.get("name"))
        if name_filter is not None and name_filter not in (feature_name or ""):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, Mapping):
            geometry = None
        geometry_type = _geometry_type(geometry)
        if geometry_type_filter is not None and geometry_type not in geometry_type_filter:
            continue
        source_id = _feature_source_id(raw, source_file, geometry)
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        latitude, longitude = _geometry_centroid(geometry)
        features.append(
            ForestSpatialFeature(
                dataset_id=dataset.data_go_id,
                dataset_name=dataset.title,
                source_file=source_file,
                layer_name=_layer_name(source_file),
                source_id=source_id,
                name=feature_name,
                geometry_type=geometry_type,
                geometry=dict(geometry) if geometry is not None else None,
                bbox=_geometry_bbox(geometry),
                latitude=latitude,
                longitude=longitude,
                raw=raw,
            )
        )

    return tuple(features)


def archive_files(data: bytes) -> dict[str, bytes]:
    """ZIP 파일을 사람이 읽을 수 있는 파일명 key의 bytes dict로 푼다."""

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return {"download": data}

    files: dict[str, bytes] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        files[_zip_member_display_name(info)] = archive.read(info.filename)
    return files


def _open_reader(data: bytes) -> tuple[Any, str | None]:
    archive = _open_archive(data)
    readers = _open_readers_from_archive(archive)
    if not readers:
        raise ForestParseError(
            "forest.go.kr SHP archive must include .shp, .shx, and .dbf files",
            provider="forest.go.kr",
            failure_kind="parse",
        )
    reader, prj_text, _source_file, _layer_name = readers[0]
    return reader, prj_text


def _open_archive(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ForestParseError(
            "forest.go.kr dataset was not a valid ZIP archive",
            provider="forest.go.kr",
            failure_kind="parse",
        ) from exc


_MAX_ARCHIVE_DECOMPRESSED_BYTES = 200 * 1024 * 1024
_MAX_NESTED_ZIP_DEPTH = 2
_MAX_ZIP_COMPRESSION_RATIO = 100


def _guard_zip_member(info: zipfile.ZipInfo, budget: list[int]) -> None:
    if info.compress_size > 0 and info.file_size / info.compress_size > _MAX_ZIP_COMPRESSION_RATIO:
        raise ForestParseError(
            "forest.go.kr ZIP member has a suspicious compression ratio",
            provider="forest.go.kr",
            failure_kind="parse",
        )
    budget[0] += info.file_size
    if budget[0] > _MAX_ARCHIVE_DECOMPRESSED_BYTES:
        raise ForestParseError(
            "forest.go.kr ZIP archive exceeds the maximum allowed decompressed size",
            provider="forest.go.kr",
            failure_kind="parse",
        )


def _open_readers_from_archive(
    archive: zipfile.ZipFile,
    *,
    prefix: str = "",
    depth: int = 0,
    budget: list[int] | None = None,
) -> tuple[tuple[Any, str | None, str, str], ...]:
    try:
        import shapefile  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ForestParseError(
            "pyshp is required to parse forest.go.kr SHP datasets",
            provider="forest.go.kr",
            failure_kind="parse",
        ) from exc

    if budget is None:
        budget = [0]

    groups: dict[str, dict[str, zipfile.ZipInfo]] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        stem, extension = posixpath.splitext(info.filename)
        ext = extension.lower()
        if ext in {".shp", ".shx", ".dbf", ".prj"}:
            groups.setdefault(stem.lower(), {})[ext] = info

    readers: list[tuple[Any, str | None, str, str]] = []
    for members in groups.values():
        shp_info = members.get(".shp")
        shx_info = members.get(".shx")
        dbf_info = members.get(".dbf")
        if shp_info is None or shx_info is None or dbf_info is None:
            continue
        prj_info = members.get(".prj")
        prj_text = None
        if prj_info is not None:
            _guard_zip_member(prj_info, budget)
            prj_text = archive.read(prj_info.filename).decode("ascii", errors="ignore")
        _guard_zip_member(shp_info, budget)
        _guard_zip_member(shx_info, budget)
        _guard_zip_member(dbf_info, budget)
        try:
            reader = shapefile.Reader(
                shp=io.BytesIO(archive.read(shp_info.filename)),
                shx=io.BytesIO(archive.read(shx_info.filename)),
                dbf=io.BytesIO(archive.read(dbf_info.filename)),
                encoding="cp949",
                encodingErrors="replace",
            )
        except (shapefile.ShapefileException, struct.error, IndexError) as exc:
            raise ForestParseError(
                "forest.go.kr SHP archive contains a corrupt or truncated shapefile",
                provider="forest.go.kr",
                failure_kind="parse",
            ) from exc
        source_file = _join_archive_path(prefix, _zip_name_from_member(archive, shp_info.filename))
        readers.append((reader, prj_text, source_file, _layer_name(source_file)))

    # PBD0000041 is an aggregate ZIP whose actual SHP files live in one ZIP per
    # administrative area.  The *_geojson.zip and *_gpx.zip siblings contain the
    # same routes in alternate formats; selecting the SHP sibling avoids emitting
    # three copies of every feature while keeping direct GeoJSON/GPX archives
    # supported below in ``forest_spatial_features``.
    for info in archive.infolist():
        if info.is_dir() or not info.filename.lower().endswith(".zip"):
            continue
        nested_name = _zip_member_display_name(info)
        nested_stem = posixpath.splitext(posixpath.basename(nested_name))[0].lower()
        if nested_stem.endswith(("_geojson", "_gpx")):
            continue
        if depth >= _MAX_NESTED_ZIP_DEPTH:
            raise ForestParseError(
                "forest.go.kr ZIP archive nests ZIP files too deeply",
                provider="forest.go.kr",
                failure_kind="parse",
            )
        _guard_zip_member(info, budget)
        try:
            nested = zipfile.ZipFile(io.BytesIO(archive.read(info.filename)))
        except zipfile.BadZipFile:
            continue
        try:
            readers.extend(
                _open_readers_from_archive(
                    nested,
                    prefix=_join_archive_path(prefix, nested_name),
                    depth=depth + 1,
                    budget=budget,
                )
            )
        finally:
            nested.close()
    return tuple(readers)


def _feature_name(raw: Mapping[str, Any]) -> str | None:
    """산행로 DBF의 산 이름·구간 이름을 표시용 이름으로 결합한다."""

    mountain_name = first_text(raw, "MNTN_NM")
    segment_name = first_text(raw, "PMNTN_NM")
    if mountain_name is not None and segment_name is not None:
        if mountain_name == segment_name:
            return mountain_name
        return f"{mountain_name} {segment_name}"
    return first_text(raw, *_NAME_KEYS)


def _feature_source_id(
    raw: Mapping[str, Any],
    source_file: str,
    geometry: Mapping[str, Any] | None,
) -> str:
    """파일 피처의 재실행 가능한 source natural key를 만든다."""

    stable_fields = {
        key: value
        for key in _SOURCE_ID_KEYS
        if (value := first_text(raw, key)) is not None
    }
    if stable_fields:
        identity_payload: dict[str, Any] = {
            "fields": stable_fields,
            "source_file": source_file,
        }
        # Name-only DBF layers do not expose a row identity.  Including the
        # canonical geometry prevents first-wins dedup from merging distinct
        # segments that happen to share a display name.
        if set(key.lower() for key in stable_fields) <= {"name"}:
            identity_payload["geometry"] = geometry
        canonical = json.dumps(
            identity_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha1(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"{source_file}:keys:{digest}"

    canonical = json.dumps(
        {"geometry": geometry, "raw": dict(raw)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha1(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"{source_file}:sha1:{digest}"


def _join_archive_path(prefix: str, name: str) -> str:
    return posixpath.join(prefix, name) if prefix else name


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


@lru_cache(maxsize=32)
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


def _wgs84_point(
    x: float | None,
    y: float | None,
    transformer: Any,
) -> tuple[float | None, float | None]:
    """투영좌표(x, y)를 WGS84 (latitude, longitude)로 변환한다."""

    if x is None or y is None:
        return None, None
    if x == 0.0 and y == 0.0:
        return None, None
    if -180 <= x <= 180 and -90 <= y <= 90:
        return y, x
    lon, lat = transformer.transform(x, y)
    return lat, lon


def _shape_geometry(shape: Any, transformer: Any) -> dict[str, Any] | None:
    import shapefile

    try:
        geometry = getattr(shape, "__geo_interface__", None)
    except shapefile.GeoJSON_Error:
        return None
    if not isinstance(geometry, Mapping):
        return None
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        return dict(geometry)
    return {
        "type": geometry.get("type"),
        "coordinates": _transform_coordinates(coordinates, transformer),
    }


def _shape_geometry_type(shape: Any) -> str | None:
    import shapefile

    try:
        geometry = getattr(shape, "__geo_interface__", None)
    except shapefile.GeoJSON_Error:
        return None
    return geometry.get("type") if isinstance(geometry, Mapping) else None


def _shape_bbox(shape: Any, transformer: Any) -> tuple[float, float, float, float] | None:
    bbox = getattr(shape, "bbox", None)
    if not bbox or len(bbox) < 4:
        lat, lon = _shape_centroid(shape, transformer)
        if lat is None or lon is None:
            return None
        return (lon, lat, lon, lat)
    min_x, min_y, max_x, max_y = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    min_lon, min_lat = _transform_pair(min_x, min_y, transformer)
    max_lon, max_lat = _transform_pair(max_x, max_y, transformer)
    return (
        min(min_lon, max_lon),
        min(min_lat, max_lat),
        max(min_lon, max_lon),
        max(min_lat, max_lat),
    )


def _shape_centroid(shape: Any, transformer: Any) -> tuple[float | None, float | None]:
    """SHP shape의 중심점을 WGS84 (latitude, longitude)로 반환한다."""

    bbox = getattr(shape, "bbox", None)
    if bbox and len(bbox) >= 4:
        x = (float(bbox[0]) + float(bbox[2])) / 2
        y = (float(bbox[1]) + float(bbox[3])) / 2
        lon, lat = _transform_pair(x, y, transformer)
        return lat, lon
    points = getattr(shape, "points", None) or []
    if not points:
        return None, None
    lon, lat = _transform_pair(float(points[0][0]), float(points[0][1]), transformer)
    return lat, lon


def _transform_coordinates(value: Any, transformer: Any) -> Any:
    if _is_coordinate_pair(value):
        lon, lat = _transform_pair(float(value[0]), float(value[1]), transformer)
        rest = list(value[2:]) if isinstance(value, (list, tuple)) else []
        return [lon, lat, *rest]
    if isinstance(value, (list, tuple)):
        return [_transform_coordinates(item, transformer) for item in value]
    return value


def _transform_pair(x: float, y: float, transformer: Any) -> tuple[float, float]:
    if (x, y) != (0.0, 0.0) and -180 <= x <= 180 and -90 <= y <= 90:
        return x, y
    lon, lat = transformer.transform(x, y)
    return float(lon), float(lat)


def _is_coordinate_pair(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return False
    return isinstance(value[0], (int, float)) and isinstance(value[1], (int, float))


def _geojson_members(archive: zipfile.ZipFile) -> Iterator[tuple[str, dict[str, Any]]]:
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = _zip_member_display_name(info)
        lower = name.lower()
        if not (lower.endswith(".geojson") or lower.endswith(".json")):
            continue
        text = _decode_text(archive.read(info.filename))
        try:
            payload = json.loads(text)
        except ValueError:
            continue
        if isinstance(payload, dict):
            yield name, payload


def _geojson_features(payload: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features", [])
        if isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict):
                    yield feature
    elif payload.get("type") == "Feature":
        yield dict(payload)


def _gpx_features(archive: zipfile.ZipFile) -> Iterator[tuple[str, dict[str, Any]]]:
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = _zip_member_display_name(info)
        if not name.lower().endswith(".gpx"):
            continue
        try:
            root = ET.fromstring(archive.read(info.filename))
        except ET.ParseError:
            continue
        for point in root.findall(".//{*}wpt"):
            coordinates = _gpx_point(point)
            if coordinates is None:
                continue
            yield name, {
                "name": _element_text(point, "name"),
                "properties": _gpx_properties(point),
                "geometry": {"type": "Point", "coordinates": coordinates},
            }
        for tag in ("trk", "rte"):
            for line in root.findall(f".//{{*}}{tag}"):
                line_coordinates = [
                    parsed_point
                    for child in line.findall(".//{*}trkpt") + line.findall(".//{*}rtept")
                    if (parsed_point := _gpx_point(child)) is not None
                ]
                if line_coordinates:
                    yield name, {
                        "name": _element_text(line, "name"),
                        "properties": _gpx_properties(line),
                        "geometry": {"type": "LineString", "coordinates": line_coordinates},
                    }


def _gpx_point(element: ET.Element) -> list[float] | None:
    lat = to_float_or_none(element.attrib.get("lat"))
    lon = to_float_or_none(element.attrib.get("lon"))
    if lat is None or lon is None:
        return None
    return [lon, lat]


def _gpx_properties(element: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in ("name", "desc", "type"):
        value = _element_text(element, key)
        if value is not None:
            values[key] = value
    return values


def _element_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(f"{{*}}{tag}")
    if child is None:
        return None
    return strip_or_none(child.text)


def _geometry_type(geometry: Mapping[str, Any] | None) -> str | None:
    if geometry is None:
        return None
    value = geometry.get("type")
    return str(value) if value is not None else None


def _geometry_bbox(geometry: Mapping[str, Any] | None) -> tuple[float, float, float, float] | None:
    if geometry is None:
        return None
    pairs = list(_coordinate_pairs(geometry.get("coordinates")))
    if not pairs:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    return (min(xs), min(ys), max(xs), max(ys))


def _geometry_centroid(
    geometry: Mapping[str, Any] | None,
) -> tuple[float | None, float | None]:
    """GeoJSON geometry의 bbox 중심을 WGS84 (latitude, longitude)로 반환한다."""

    bbox = _geometry_bbox(geometry)
    if bbox is None:
        return None, None
    return (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2


def _coordinate_pairs(value: Any) -> Iterator[tuple[float, float]]:
    if _is_coordinate_pair(value):
        yield (float(value[0]), float(value[1]))
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _coordinate_pairs(child)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _layer_name(source_file: str) -> str:
    name = posixpath.basename(source_file)
    return posixpath.splitext(name)[0]


def _zip_name_from_member(archive: zipfile.ZipFile, member_name: str) -> str:
    try:
        info = archive.getinfo(member_name)
    except KeyError:
        return member_name
    return _zip_member_display_name(info)


def _zip_member_display_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except UnicodeError:
        return info.filename
