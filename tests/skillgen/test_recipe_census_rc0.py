"""``scripts/recipe_census.py``（RC-0 組合器配方盤點）：確定性、門檻參數、格子清單。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from trpg.content.library import load_library

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def census() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recipe_census_script", ROOT / "scripts" / "recipe_census.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["recipe_census_script"] = module
    spec.loader.exec_module(module)
    return module


def test_cells_cover_keywords_kinds_tiers_rarities(census: ModuleType) -> None:
    lib = load_library()
    tiers = census.player_tiers(lib)
    assert tiers[0] == 1
    cells = census.build_cells(lib, None, census.KINDS, tiers, census.RARITIES)
    rows = 1 + len(lib.keywords.ids())
    assert len(cells) == rows * 3 * len(tiers) * 3
    assert cells[0].keyword == census.NO_KEYWORD


def test_results_do_not_depend_on_order(census: ModuleType) -> None:
    """每格只由自己的參數決定：先後順序（等同分給不同行程）不影響計時以外的結果。"""
    cells = [
        census.Cell(census.NO_KEYWORD, "active", 1, "common"),
        census.Cell("ignite", "active", 2, "rare"),
        census.Cell("ignite", "passive", 1, "common"),
    ]
    forward = census.run_census(cells, 3, 12, 1, diag_seeds=2)
    backward = census.run_census(list(reversed(cells)), 3, 12, 1, diag_seeds=2)
    assert census.stable_view(forward) == census.stable_view(list(reversed(backward)))


def test_thin_threshold_and_design_floor(census: ModuleType) -> None:
    cell = census.Cell(census.NO_KEYWORD, "active", 1, "common")
    [result] = census.run_census([cell], 4, 12, 1, diag_seeds=0)
    assert result.legal == 4
    assert census.classify(result, thin=12) == "thin"
    assert census.classify(result, thin=1) == "ok"
    blocked = census.Cell(census.NO_KEYWORD, "passive", 1, "common")
    [none] = census.run_census([blocked], 2, 12, 1, diag_seeds=0)
    assert none.blocked_by_design
    assert census.classify(none, thin=12) == "n/a"


def test_design_key_tells_summon_units_apart(census: ModuleType) -> None:
    """HC-6a：召喚不同的召喚物算不同設計；沒有召喚物的效果鍵照舊（只有類型與狀態 ID）。"""
    lib = load_library()
    summons = sorted(
        (s for s in lib.skills.values() if any(e.type == "summon" for e in s.effects)),
        key=lambda s: s.id,
    )
    base = summons[0]
    effects = list(base.effects)
    index = next(i for i, e in enumerate(effects) if e.type == "summon")
    units = {e.unit for s in summons for e in s.effects if e.unit}
    other = sorted(units - {effects[index].unit})[0]
    effects[index] = effects[index].model_copy(update={"unit": other})
    swapped = base.model_copy(update={"effects": tuple(effects)})
    assert census.design_key(base) != census.design_key(swapped)
    plain = next(s for s in lib.skills.values() if all(e.unit is None for e in s.effects))
    assert all("@" not in key for key in census.design_key(plain)[3])
