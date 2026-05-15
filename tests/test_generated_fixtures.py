from __future__ import annotations

from pathlib import Path

import pytest

from krforest.replay import load_fixture
from tests.runners import RUNNERS
from tests.utils import assert_case

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def all_fixture_files() -> list[Path]:
    if not FIXTURE_DIR.exists():
        return []
    return sorted(FIXTURE_DIR.glob("*/*.json"))


@pytest.mark.parametrize(
    "fixture_path",
    all_fixture_files(),
    ids=lambda path: f"{path.parent.name}/{path.stem}",
)
def test_generated_fixtures(fixture_path: Path):
    case = load_fixture(fixture_path)
    function_name = str(case["function"])
    runner = RUNNERS[function_name]

    parsed = runner["parse"](case["response"]["body"])
    processed = runner["process"](parsed)

    assert_case(
        processed,
        case["processed"],
        case.get("assertion", {"mode": "snapshot"}),
    )
