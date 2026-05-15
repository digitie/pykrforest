from __future__ import annotations

from collections.abc import Callable
from typing import Any

from krforest.debug import jsonable
from krforest.parser import parse_recreation_forest_reservation


def _parse_recreation_forest_reservations(body: dict[str, Any]) -> tuple[Any, ...]:
    items = body.get("items", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise TypeError("fixture response.body.items must be a list or object")
    return tuple(parse_recreation_forest_reservation(dict(item)) for item in items)


def _process_jsonable(parsed: Any) -> Any:
    return jsonable(parsed)


RUNNERS: dict[str, dict[str, Callable[[Any], Any]]] = {
    "national_recreation_forest_reservations": {
        "parse": _parse_recreation_forest_reservations,
        "process": _process_jsonable,
    },
}
