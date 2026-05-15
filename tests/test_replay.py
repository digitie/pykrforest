from __future__ import annotations

import pytest

from krforest.replay import assert_case, remove_fields


def test_remove_fields_supports_nested_names_and_paths():
    value = {
        "updated_at": "2026-05-15",
        "items": [{"name": "A", "meta": {"request_id": "1", "keep": True}}],
    }

    assert remove_fields(value, ["updated_at", "items.meta.request_id"]) == {
        "items": [{"name": "A", "meta": {"keep": True}}]
    }


def test_assert_case_modes():
    assert_case(
        {"items": [{"name": "A", "updated_at": "new"}]},
        {"items": [{"name": "A", "updated_at": "old"}]},
        {"mode": "snapshot", "exclude_fields": ["updated_at"]},
    )
    assert_case(
        {"items": [{"name": "A"}]},
        {},
        {"mode": "required_fields", "required_fields": ["items.0.name"]},
    )
    assert_case({"items": [1, 2]}, {"items": [3, 4]}, {"mode": "count"})
    assert_case({"anything": True}, {}, {"mode": "schema_only"})


def test_assert_case_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown assertion mode"):
        assert_case({}, {}, {"mode": "custom"})
