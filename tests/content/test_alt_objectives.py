"""地圖的 ``alt_objectives``（Phase 3-22）：schema 驗證與隨附地圖資料。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_map
from trpg.content.maps import MapDef, check_map

_ROWS = "\n".join("0" * 8 for _ in range(4))


def _map(alt: dict[str, Any]) -> MapDef:
    data = make_map(_ROWS, ally=[(0, 0)], enemy=[(7, 3)]).model_dump(mode="json")
    data["alt_objectives"] = alt
    return MapDef.model_validate(data)


def test_alt_objectives_build_the_matching_objective() -> None:
    m = _map(
        {"escape": {"rounds": 5, "tiles": [[7, 0]]}, "defend": {"rounds": 4, "tiles": [[3, 1]]}}
    )
    escape = m.objective_for("escape")
    assert (escape.kind, escape.rounds, escape.tiles) == ("escape", 5, ((7, 0),))
    defend = m.objective_for("defend")
    assert (defend.kind, defend.rounds, defend.tiles) == ("defend", 4, ((3, 1),))
    assert m.objective_for("eliminate").kind == "eliminate"
    assert m.supports_objective("escape") and m.supports_objective("eliminate")


def test_missing_kind_is_unsupported() -> None:
    m = _map({"defend": {"rounds": 4, "tiles": [[3, 1]]}})
    assert not m.supports_objective("escape")
    with pytest.raises(ValueError, match="沒有 escape"):
        m.objective_for("escape")
    assert make_map(_ROWS).alt_objectives is None


@pytest.mark.parametrize(
    ("alt", "message"),
    [
        ({}, "至少要設定"),
        ({"escape": {"rounds": 0, "tiles": [[7, 0]]}}, "rounds"),
        ({"escape": {"rounds": 3, "tiles": []}}, "tiles"),
        ({"escape": {"rounds": 3, "tiles": [[7, 0], [7, 0]]}}, "不可重複"),
        ({"escape": {"rounds": 3, "tiles": [[8, 0]]}}, "超出地圖範圍"),
        ({"defend": {"rounds": 3, "tiles": [[0, 0]]}}, "在起始區內"),
        ({"escape": {"rounds": 3, "tiles": [[7, 3]]}}, "在起始區內"),
    ],
)
def test_validation_rejects_bad_alt_objectives(alt: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _map(alt)


def test_check_map_requires_standable_and_reachable_tiles() -> None:
    lib = library()
    core = lib.ruleset.core
    terrain = lib.ruleset.terrain.by_id()
    walled = make_map(
        _ROWS, "\n".join(["........"] * 3 + ["..#....."]), ally=[(0, 0)], enemy=[(7, 3)]
    )
    data = walled.model_dump(mode="json")
    data["alt_objectives"] = {"escape": {"rounds": 5, "tiles": [[2, 3]]}}
    problems = check_map(MapDef.model_validate(data), terrain, core)
    assert any("不可站立" in p and "alt_objectives.escape" in p for p in problems)
    # 被深淵整列隔開 → 走不到
    split = make_map(_ROWS, "\n".join(["...x...."] * 4), ally=[(0, 0)], enemy=[(1, 3)]).model_dump(
        mode="json"
    )
    split["alt_objectives"] = {"defend": {"rounds": 5, "tiles": [[6, 1]]}}
    problems = check_map(MapDef.model_validate(split), terrain, core)
    assert any("無法從我方起始格" in p for p in problems)


def test_shipped_pool_maps_cover_enough_escape_and_defend() -> None:
    """Phase 3-22 24.1 第 1 項：地圖池至少 4 張可撤離、4 張可守點，資料通過 check_map。"""
    lib = library()
    pool = [lib.map(m) for m in lib.roguelite.map_pool]
    assert sum(m.supports_objective("escape") for m in pool) >= 4
    assert sum(m.supports_objective("defend") for m in pool) >= 4
    for m in pool:
        assert (
            check_map(m, lib.ruleset.terrain.by_id(), lib.ruleset.core, lib.ruleset.objects.by_id())
            == []
        )
    # 吊橋、冰湖適合撤離；廢墟（懸崖前哨）、油庫適合守點
    assert lib.map("bridge_chasm").supports_objective("escape")
    assert lib.map("frozen_lake").supports_objective("escape")
    assert lib.map("cliff_outpost").supports_objective("defend")
