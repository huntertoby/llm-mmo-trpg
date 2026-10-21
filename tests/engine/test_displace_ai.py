"""AI 與位移他人（Phase 3D-2b）：效用 AI 把敵人傳送進致命地形、把快倒下的隊友換出來。

候選以便宜的估計篩選（:mod:`trpg.engine.ai.displace`），收益由預覽的位移成功率加權
（``utility._displace_gains``）。``trpg sim maps`` 的使用紀錄見 Phase 3D-2b 報告。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
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
from trpg.engine.ai.displace import displace_estimate
from trpg.engine.ai.utility import UtilityAI, _harmful
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.rules.movement import is_deadly
from trpg.shared.types import Team, UnitId
from trpg.sim.batch import map_spec, run_one
from trpg.sim.lineup import build_allies
from trpg.sim.metrics import SkillMetrics

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
BANISH = "skill_banish"
VOID = "skill_void_swap"
FLAT = "\n".join(["0000000"] * 7)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _terrain(cells: dict[tuple[int, int], str]) -> str:
    rows = [["."] * 7 for _ in range(7)]
    for (x, y), ch in cells.items():
        rows[y][x] = ch
    return "\n".join("".join(r) for r in rows)


def _scene(
    skill: str,
    *,
    allies: Sequence[tuple[int, int]] = (),
    foes: Sequence[tuple[int, int]],
    terrain: str | None = None,
    surfaces: Sequence[tuple[int, int, str]] = (),
    foe_tags: Sequence[str] = (),
    hurt: Sequence[int] = (),
) -> BattleState:
    """U1 是裝備 ``skill`` 的法師在 (0, 3)；``hurt`` 列出受重傷的友方索引（從 0 起算）。"""
    m = make_map(FLAT, terrain, ally=[(0, 3), *allies], enemy=list(foes), surfaces=surfaces)
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    for xy in foes:
        tags = list(foe_tags) if foe_tags else list(library().unit("bandit").tags)
        spawns.append(spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=200, tags=tags)))
    state = give_turn(make_state(m, spawns, skills=[]), U1)
    for index in hurt:
        unit = state.units[UnitId(f"unit_000{index + 2}")]
        unit.hp = max(1, unit.max_hp * 3 // 10)
    return state


def test_the_ai_banishes_an_enemy_into_deadly_terrain() -> None:
    terrain = _terrain({(3, 1): "~", (3, 5): "x"})
    state = _scene(BANISH, foes=[(3, 3)], terrain=terrain)
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == BANISH
    assert action.target_id == U2 and action.target_pos is not None
    assert is_deadly(state, (action.target_pos.x, action.target_pos.y))


def test_the_ai_does_not_banish_when_nothing_is_gained() -> None:
    """沒有致命地形或有害表面可去：傳送沒有收益，AI 不浪費 AP 與法力。"""
    state = _scene(BANISH, foes=[(3, 3)])
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == BANISH)


def test_a_boss_is_never_banished_into_deadly_terrain() -> None:
    terrain = _terrain({(3, 1): "~", (3, 5): "x"})
    state = _scene(BANISH, foes=[(3, 3)], terrain=terrain, foe_tags=["boss"])
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == BANISH)


def test_the_ai_banishes_onto_a_harmful_surface_only_when_it_is_worth_it() -> None:
    state = _scene(BANISH, foes=[(3, 3)], surfaces=[(3, 1, "fire")])
    estimates = _estimates(state, BANISH)
    assert estimates[(3, 1)] is not None and estimates[(3, 1)] > 0  # type: ignore[operator]
    assert estimates[(3, 5)] is None  # 沒有收益的落點不納入候選


def _estimates(state: BattleState, skill_id: str) -> dict[tuple[int, int], object]:
    skill = state.ruleset.skill_def(skill_id)
    hero = state.units[U1]
    actions, _ = legal_actions_with_areas(state)
    found: dict[tuple[int, int], object] = {}
    for action in actions:
        if isinstance(action, UseSkill) and action.skill_id == skill_id and action.target_pos:
            found[(action.target_pos.x, action.target_pos.y)] = displace_estimate(
                state, hero, skill, action, _harmful
            )
    return found


def test_the_estimate_ranks_a_deadly_landing_above_a_surface_and_skips_neutral_tiles() -> None:
    terrain = _terrain({(3, 1): "~"})
    state = _scene(BANISH, foes=[(3, 3)], terrain=terrain, surfaces=[(3, 5, "fire")])
    found = _estimates(state, BANISH)
    lava, fire, neutral = found[(3, 1)], found[(3, 5)], found[(4, 3)]
    assert lava is not None and fire is not None and neutral is None
    assert lava > fire  # type: ignore[operator]


def test_the_ai_swaps_a_nearly_dead_ally_out_of_the_enemies_reach() -> None:
    """快倒下的隊友被敵人包夾，AI 用虛空互換把他換到後面（與離敵人較遠的單位互換）。"""
    state = _scene(VOID, allies=[(4, 3), (1, 3)], foes=[(5, 3)], hurt=[0])
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == VOID
    assert U2 in (action.target_id, action.second_target_id)  # 受傷的隊友


def test_the_swap_estimate_values_getting_a_friend_off_a_burning_tile() -> None:
    state = _scene(VOID, allies=[(4, 3)], foes=[(2, 3)], surfaces=[(4, 3, "fire")])
    skill, hero = state.ruleset.skill_def(VOID), state.units[U1]
    actions, _ = legal_actions_with_areas(state)
    found = {
        (a.target_id, a.second_target_id): displace_estimate(state, hero, skill, a, _harmful)
        for a in actions
        if isinstance(a, UseSkill) and a.skill_id == VOID
    }
    swapped = found[(U2, U3)]  # 隊友離開火、敵人換進火
    assert swapped is not None and swapped > 0
    assert found[(U1, U2)] is None  # 只是把施放者換進火裡：不納入候選


def test_the_ai_does_not_swap_without_a_reason() -> None:
    state = _scene(VOID, allies=[(4, 3), (1, 3)], foes=[(6, 6)])
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == VOID)


def test_the_ai_uses_the_displacement_skills_in_real_battles() -> None:
    lib, allies = build_allies(library(), ["build_banisher"])
    used = 0
    for map_id, seed in (("frozen_lake", 0), ("lava_crossing", 1), ("dark_forest", 0)):
        outcome = run_one(map_spec(lib, map_id, [seed], allies=allies), seed)
        assert outcome.metrics is not None
        used += outcome.metrics.skills.get(BANISH, SkillMetrics()).uses
    assert used >= 1


def test_an_ai_battle_with_banishments_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "banish.json"
    argv = ["battle", "--map", "frozen_lake", "--seed", "0", "--ally-build", "build_banisher"]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert "放逐" in capsys.readouterr().out
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()


def test_an_ai_battle_with_a_void_swap_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """open_plain 種子 3：快倒下的主角與隊友弓手互換位置（沒有敵人，不檢定），紀錄重播一致。

    3-20 跑步改變 AI 軌跡，種子原為 0。"""
    log = tmp_path / "void_swap.json"
    argv = ["battle", "--map", "open_plain", "--seed", "3", "--ally-build", "build_banisher"]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert "施放「虛空互換」" in capsys.readouterr().out
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()
