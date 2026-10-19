"""AI 與直線衝撞（Phase 3D-2c）：效用 AI 在路徑上有敵人時選終點衝過去，沒有敵人就不衝。

候選終點只列四方向的直線（數量很小），便宜的估計是「路徑上的敵人數 × 3 ＋ 終點的位置價值變化」，
收益由預覽（沿途每個敵人的命中率與傷害）計算。``trpg sim maps`` 的使用紀錄見 Phase 3D-2c 報告。
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.engine import BattleState, UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.shared.types import Team, UnitId

U1 = UnitId("unit_0001")
BULL = "skill_bull_rush"
FLAT = "\n".join(["0000000"] * 7)


def _scene(foes: list[tuple[int, int]]) -> BattleState:
    """U1 是裝備蠻牛衝陣的戰士，在 (0, 3)；``foes`` 是不反應、HP 200 的盜賊。"""
    m = make_map(FLAT, None, ally=[(0, 3)], enemy=foes)
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([BULL], base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[]), U1)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def test_the_ai_charges_along_the_line_the_enemies_stand_on() -> None:
    state = _scene([(2, 3), (4, 3)])
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == BULL
    assert action.target_pos is not None and action.target_pos.y == 3
    assert action.target_pos.x >= 3  # 至少穿過 (2, 3) 的敵人；終點的位置價值決定停在哪


def test_the_ai_does_not_charge_when_nobody_is_on_the_line() -> None:
    """路徑上沒有敵人：衝撞只有位置價值，不納入候選（與傳送、跳躍不同，它是攻擊技能）。"""
    state = _scene([(4, 5), (5, 6)])
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == BULL)


def test_the_ai_uses_the_charge_in_real_battles(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["battle", "--map", "bridge_chasm", "--seed", "2", "--ally-build", "build_charger"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "直線衝撞：" in out and "以「蠻牛衝陣」攻擊" in out


def test_an_ai_battle_with_charges_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """bridge_chasm 種子 2：衝撞一次撞到兩個敵人（命中、擊倒），紀錄重播一致。"""
    log = tmp_path / "charge.json"
    argv = ["battle", "--map", "bridge_chasm", "--seed", "2", "--ally-build", "build_charger"]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert "直線衝撞" in capsys.readouterr().out
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()
