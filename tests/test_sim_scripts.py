"""批次模擬腳本（scripts/sim_demo_maps.py）：技能使用統計（Phase 2A-2 6.4 第 5 條）。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, hit_with
from trpg.engine import UseSkill, resolve

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sim_demo_maps.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sim_demo_maps", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sim_demo_maps_prints_win_rates_and_skill_usage_statistics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    assert module.main(["--seeds", "2", "--maps", "oil_depot"]) == 0
    out = capsys.readouterr().out
    assert "| oil_depot |" in out
    assert "技能使用統計" in out
    assert "| 技能 | 陣營 | 使用次數 | 命中率 | 平均傷害／次 | 平均治療／次 |" in out
    rows = [line for line in out.splitlines() if line.startswith("| ") and "（skill_" in line]
    assert rows, "至少有一個技能被使用"
    assert any("我方" in row for row in rows)


def test_collect_skill_stats_attributes_damage_and_hits_to_the_skill() -> None:
    module = _load()
    skill = make_skill(
        SID, {"type": "single", "range": 5}, [{"type": "damage", "dice": "1d6", "element": "fire"}]
    )
    state = hit_with(battle(skill, [(4, 3)]), [(6, 4)])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    stats: dict[str, object] = {}
    teams = {u.id: u.team for u in result.state.units.values()}
    module.collect_skill_stats(list(result.events), teams, stats)
    entry = stats[SID]
    assert (entry.uses, entry.rolls, entry.hits) == (1, 1, 1)  # type: ignore[attr-defined]
    assert entry.damage > 0  # type: ignore[attr-defined]
