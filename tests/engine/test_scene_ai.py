"""AI 與場景物件原語（Phase 3C-5b，``docs/phases/Phase3C計畫.md`` 7A.5）。

效用 AI 對投擲物件（物件 × 落點）與推倒（壓住的敵人）以便宜的幾何估計篩選候選
（:mod:`trpg.engine.ai.scene_objects`）；穿透（無視半掩護）已包含在預覽的命中率裡。
``trpg sim maps`` 會統計三種場景物件事件。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import replace
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
    template,
)
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.engine import Attack, BattleState, UseSkill, preview
from trpg.engine.ai.scene_objects import scene_estimate
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.events import ObjectToppled
from trpg.shared.types import ObjectId, Surface, Team, UnitId
from trpg.sim.batch import map_spec, run_one
from trpg.sim.lineup import build_allies

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
FLAT = "\n".join(["0000000"] * 7)
HURL = "skill_telekinetic_hurl"
TOPPLE = "skill_quake_topple"
ARROW = "skill_armor_piercing_arrow"


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _hurl_scene(foes: Sequence[tuple[int, int]], barrel: str = "oil_barrel") -> BattleState:
    """U1 法師在 (0, 3)，旁邊 (1, 3) 有可舉起的物件；敵人不反應。"""
    m = make_map(FLAT, ally=[(0, 3)], enemy=list(foes), objects=[(1, 3, barrel)])
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([HURL]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def _estimates(state: BattleState, skill_id: str) -> dict[tuple[int, int], object]:
    """技能每個選取的估計，依落點（投擲）或物件所在格（推倒）。"""
    skill = state.ruleset.skill_def(skill_id)
    hero = state.units[U1]
    actions, areas = legal_actions_with_areas(state)
    found: dict[tuple[int, int], object] = {}
    for action in actions:
        if isinstance(action, UseSkill) and action.skill_id == skill_id:
            area = areas[id(action)]
            found[area.tiles[0]] = scene_estimate(state, hero, skill, action, area)
    return found


# ---------------------------------------------------------------------------
# 投擲物件
# ---------------------------------------------------------------------------


def _hurl_scene_with(foes: Sequence[tuple[int, int]], skills: Sequence[str]) -> BattleState:
    m = make_map(FLAT, ally=[(0, 3)], enemy=list(foes), objects=[(1, 3, "oil_barrel")])
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([HURL, *skills]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def test_hurl_estimate_counts_the_explosion_when_the_barrel_lands_on_fire() -> None:
    """油桶落在火上才爆炸（3D-3）：空格 (3, 3) 有火焰時，波及 (4, 3) 的敵人。"""
    state = _hurl_scene([(4, 3), (4, 0)])
    state.set_tile(3, 3, replace(state.tile(3, 3), surface=Surface.FIRE, surface_remaining=2))
    found = _estimates(state, HURL)
    assert found[(4, 3)] is not None  # 落在敵人身上
    near = found[(3, 3)]  # 空格，但落點有火：油桶爆炸（半徑 1）波及 (4, 3)
    assert near is not None and near > 0  # type: ignore[operator]
    assert found[(1, 1)] is None  # 周圍沒有敵人：不納入候選


def test_hurl_estimate_counts_oil_only_when_the_caster_has_a_fire_skill() -> None:
    plain = _estimates(_hurl_scene([(4, 3)]), HURL)
    assert plain[(3, 3)] is None  # 沒有火：油桶只漏油，空格落點沒有價值
    with_fire = _estimates(_hurl_scene_with([(4, 3)], ["skill_fire_bolt"]), HURL)
    oil = with_fire[(3, 3)]  # 有火焰技能：鋪油（含 (4, 3)）是兩步連招的第一步
    assert oil is not None and oil > 0  # type: ignore[operator]
    assert with_fire[(1, 1)] is None  # 油鋪不到敵人：不納入


def test_a_crate_only_counts_when_it_lands_on_an_enemy() -> None:
    state = _hurl_scene([(4, 3)], barrel="crate")
    found = _estimates(state, HURL)
    assert found[(4, 3)] is not None
    assert found[(3, 3)] is None  # 木箱不會爆炸：落在旁邊的空格沒有效果


def test_the_ai_picks_the_barrel_and_a_landing_beside_the_enemies() -> None:
    state = _hurl_scene([(4, 3), (3, 4)])
    ranked = _ai().rank(state)
    hurls = [s for s in ranked if isinstance(s.action, UseSkill) and s.action.skill_id == HURL]
    assert hurls, "投擲物件應該進入候選"
    best = max(hurls, key=lambda s: s.score)
    assert best.score > 0
    assert best.action.target_object_id == ObjectId("obj_0001")  # type: ignore[union-attr]
    assert best.preview is not None and best.preview.affected_units  # 預覽看到爆炸波及的敵人


def test_the_number_of_full_previews_per_skill_stays_bounded() -> None:
    state = _hurl_scene([(4, 3), (3, 4), (4, 4), (3, 3)])
    ai = _ai()
    actions, _ = legal_actions_with_areas(state)
    hurls = [a for a in actions if isinstance(a, UseSkill) and a.skill_id == HURL]
    scored = [
        s for s in ai.rank(state) if isinstance(s.action, UseSkill) and s.action.skill_id == HURL
    ]
    assert len(hurls) > ai.skill_candidates > 0
    assert len(scored) <= ai.skill_candidates  # 列舉再多，也只對前幾名跑完整預覽


# ---------------------------------------------------------------------------
# 推倒
# ---------------------------------------------------------------------------


def _topple_scene(foes: Sequence[tuple[int, int]]) -> BattleState:
    """U1 戰士在 (1, 3)，石柱 (3, 3)；敵人不反應。"""
    m = make_map(FLAT, ally=[(1, 3)], enemy=list(foes), objects=[(3, 3, "stone_pillar")])
    hero = template("hero_fighter", reactions=[], skills=[TOPPLE], max_mana=99)
    spawns = [spawn(Team.ALLY, (1, 3), hero)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def test_topple_estimate_needs_an_enemy_under_the_falling_pillar() -> None:
    crushed = _estimates(_topple_scene([(4, 3)]), TOPPLE)
    assert crushed[(3, 3)] is not None and crushed[(3, 3)] > 0  # type: ignore[operator]
    assert _estimates(_topple_scene([(6, 6)]), TOPPLE)[(3, 3)] is None  # 倒下的方向沒有人
    assert _estimates(_topple_scene([(3, 1)]), TOPPLE)[(3, 3)] is None  # 在柱子旁邊也壓不到


def test_the_ai_topples_the_pillar_onto_enemies() -> None:
    state = _topple_scene([(4, 3), (5, 3)])
    ranked = _ai().rank(state)
    topples = [s for s in ranked if isinstance(s.action, UseSkill) and s.action.skill_id == TOPPLE]
    assert topples and topples[0].score > 0
    assert topples[0].preview is not None
    crushed = [e for e in topples[0].preview.max_events if isinstance(e, ObjectToppled)]
    assert crushed and set(crushed[0].units) == {U2, U3}
    best = _ai()(state)
    assert not isinstance(best, Attack) or topples[0].score > 0


# ---------------------------------------------------------------------------
# 穿透
# ---------------------------------------------------------------------------


def test_the_ai_sees_the_pierce_hit_chance_behind_cover() -> None:
    """掩護後的敵人：穿透箭的預覽命中率比一般射擊高，AI 的分數用的就是預覽。"""
    m = make_map(FLAT, ally=[(0, 3)], enemy=[(4, 3)], objects=[(3, 3, "crate")])
    hero = template("hero_archer", reactions=[], skills=[ARROW], max_mana=99)
    spawns = [spawn(Team.ALLY, (0, 3), hero), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=200))]
    state = give_turn(make_state(m, spawns), U1)
    shot = UseSkill(unit_id=U1, skill_id=ARROW, target_id=U2)
    attack = Attack(unit_id=U1, target_id=U2)
    assert preview(state, shot).targets[0].hit_chance > (preview(state, attack).hit_chance or 0)
    ranked = _ai().rank(state)
    assert any(isinstance(s.action, UseSkill) and s.action.skill_id == ARROW for s in ranked)


# ---------------------------------------------------------------------------
# sim maps：場景物件事件的統計與 --ally-build
# ---------------------------------------------------------------------------


def test_sim_metrics_count_scene_events() -> None:
    lib, allies = build_allies(library(), ["build_telekinesis"])
    spec = map_spec(lib, "narrow_halls", [2], allies=allies)
    outcome = run_one(spec, 2)
    assert outcome.metrics is not None
    assert outcome.metrics.scene_events.get("hurled", 0) >= 1


def test_sim_maps_takes_an_ally_build_and_prints_the_scene_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = [
        "sim", "maps", "--maps", "narrow_halls", "--ally-build", "build_telekinesis",
        "--seeds", "1", "--seed-start", "2", "--jobs", "1",
    ]  # fmt: skip
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "我方 build：build_telekinesis" in out
    assert "場景物件（整批合計）：投擲物件" in out
    assert main([*argv[:5], "build_nope", *argv[6:]]) == 2


def test_an_ai_battle_with_pierce_shots_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """build_ranged 在 dark_forest 種子 4：AI 用穿甲箭穿過倒木，紀錄重播一致（Phase 3C-5b）。

    3-20 跑步改變 AI 軌跡，種子原為 0。"""
    log = tmp_path / "pierce.json"
    argv = ["battle", "--map", "dark_forest", "--seed", "4", "--ally-build", "build_ranged"]
    assert main([*argv, "--log-json", str(log)]) == 0
    out = capsys.readouterr().out
    assert "穿過了" in out and "穿甲箭" in out
    assert '"shot_pierced"' in log.read_text(encoding="utf-8")
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()


def test_an_ai_battle_with_a_topple_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """build_push 在 lava_crossing 種子 1：AI 推倒石柱，重播一致（3F-4b 換技能後種子 0→1）。"""
    log = tmp_path / "topple.json"
    argv = ["battle", "--map", "lava_crossing", "--seed", "1", "--ally-build", "build_push"]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert "倒下，壓住" in capsys.readouterr().out
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()
