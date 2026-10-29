"""Phase 3W-2b 第 6 點：3W-4b 補配方（06 6.34.1，3664e63f）。

潮濕被動／反應、倒地反應、撞擊被動、標記被動：每個配方在各階級做得出來、通過白板定義與預算窗、推導
出對的關鍵字，放進戰鬥真的照卡片結算；創角選召喚物時優先給遠程的基本召喚物。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_new_triggers import _push, _wall_scene
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_skills import duel
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.engine import Attack, BattleState, EndTurn, resolve
from trpg.engine.effects import run_effects
from trpg.engine.events import (
    DamageDealt,
    ReactionTriggered,
    SkillTriggered,
    StatusApplied,
)
from trpg.shared.types import Surface, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard
from trpg.skillgen.whiteboard_check import whiteboard_keywords_of, whiteboard_problems

LIB = library()
NEW = {
    "damp_ward": ("passive", "wet"),
    "crash_bonus": ("passive", "collision"),
    "scout_mark": ("passive", "marked"),
    "splash_retort": ("reaction", "wet"),
    "trip_retort": ("reaction", "prone"),
}
U3, U4 = UnitId("unit_0003"), UnitId("unit_0004")


def _board(recipe: str, seed: int = 3, tier: int = 1) -> SkillDef:
    """近戰武器能用的白板（戰鬥測試的持有者是戰士）。"""
    kind = NEW[recipe][0]
    return compose_whiteboard(
        seed, kind=kind, tier=tier, library=LIB, recipe_id=recipe, weapon_class="melee"
    )


@pytest.mark.parametrize("recipe", sorted(NEW))
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_new_recipes_compose_valid_whiteboards_in_the_budget_window(recipe: str, tier: int) -> None:
    for seed in range(8):
        skill = _board(recipe, seed, tier)
        assert validate_skill(skill, LIB) == []
        assert whiteboard_problems(skill, LIB, tier) == []
        report = skill_budget(skill, LIB)
        assert report.min_ratio <= report.ratio <= report.max_ratio
        assert whiteboard_keywords_of(skill, LIB) == (NEW[recipe][1],), (recipe, seed)


def _rolled(skill: SkillDef, damage: DamageDealt) -> bool:
    """實擲的骰數＝卡片：法術技是效果寫的骰數；武器技用武器骰（至少一顆）。"""
    effect = next(e for e in skill.effects if e.type == "damage")
    if effect.dice is not None:
        return len(damage.rolls) == effect.dice.count
    return len(damage.rolls) >= 1


def test_splash_retort_hits_the_attacker_and_wets_his_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _board("splash_retort")
    always(monkeypatch)
    state = duel([skill])
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    assert of(result, ReactionTriggered)
    back = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert back and _rolled(skill, back[0])  # 卡片的骰數＝實擲的骰數
    foe = result.state.units[U2]
    assert result.state.tile(*foe.xy).surface is Surface.WATER


def test_trip_retort_knocks_the_melee_attacker_prone(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _board("trip_retort")
    always(monkeypatch)
    result = answered(resolve(duel([skill]), Attack(unit_id=U2, target_id=U1)))
    assert of(result, ReactionTriggered)
    assert result.state.units[U2].has_status("prone")
    back = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert back and _rolled(skill, back[0])


def test_trip_retort_ignores_ranged_attackers(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _board("trip_retort")
    always(monkeypatch)
    state = duel([skill], foe="bandit_archer", foe_xy=(6, 3))
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    assert not of(result, ReactionTriggered)


def test_damp_ward_shields_and_wets_the_owner_once_per_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _board("damp_ward")
    always(monkeypatch)
    state = duel([skill])
    first = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    fired = [e for e in of(first, SkillTriggered) if e.skill_id == skill.id]
    assert len(fired) == 1
    me = first.state.units[U1]
    assert first.state.tile(*me.xy).surface is Surface.WATER
    second = answered(resolve(first.state, Attack(unit_id=U2, target_id=U1)))
    assert [e for e in of(second, SkillTriggered) if e.skill_id == skill.id] == []  # 每回合 1 次


def test_crash_bonus_adds_damage_when_a_pushed_unit_collides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _board("crash_bonus")
    always(monkeypatch)
    result = run_effects(_wall_scene([skill]), [_push(U1)])
    fired = [e for e in result.events if isinstance(e, SkillTriggered) and e.skill_id == skill.id]
    assert len(fired) == 1 and fired[0].trigger == "on_collision"
    extra = [d for d in result.events if isinstance(d, DamageDealt) and d.cause != "collision"]
    assert [d.target_id for d in extra] == [U2]
    assert _rolled(skill, extra[0])


def _scout_scene(skill: SkillDef, foes: Sequence[tuple[int, int]]) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill], max_hp=999))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=999)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def _next_turn_of_owner(state: BattleState, foes: int) -> list[object]:
    """每個人依序結束回合，直到回到 U1 的下一個回合（回傳這段的所有事件，最後一項是狀態）。"""
    events: list[object] = []
    result = resolve(state, EndTurn(unit_id=U1))
    events += result.events
    for _ in range(foes + 1):
        if result.state.active_unit == U1:
            break
        active = result.state.active_unit
        assert active is not None
        result = answered(resolve(result.state, EndTurn(unit_id=active)))
        events += result.events
    events.append(result.state)
    return events


def test_scout_mark_marks_only_the_nearest_enemy_within_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=20)  # 抵抗判定一定失敗，標記一定上身
    skill = _board("scout_mark")
    assert skill.trigger is not None
    assert (skill.trigger.target, skill.trigger.max_distance) == ("nearest_enemy", 3)
    # U2 在 2 格、U3 在 3 格、U4 在 6 格外
    state = _scout_scene(skill, [(5, 3), (6, 3), (3, 6)])
    *events, after = _next_turn_of_owner(state, 3)
    applied = [e for e in events if isinstance(e, StatusApplied) and e.status_id == "marked"]
    assert [e.target_id for e in applied] == [U2]
    assert isinstance(after, BattleState)
    assert after.units[U2].has_status("marked")
    assert not after.units[U3].has_status("marked") and not after.units[U4].has_status("marked")


def test_scout_mark_needs_an_enemy_in_range_and_costs_nothing_otherwise() -> None:
    skill = _board("scout_mark")
    state = _scout_scene(skill, [(3, 6)])  # 3 格外（曼哈頓 3 剛好在內）→ 改放 4 格外
    far = _scout_scene(skill, [(0, 0)])
    mana = far.units[U1].mana
    *events, after = _next_turn_of_owner(far, 1)
    assert not [e for e in events if isinstance(e, SkillTriggered)]
    assert isinstance(after, BattleState) and after.units[U1].mana >= mana
    del state


def test_scout_mark_picks_the_lower_id_on_a_distance_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=20)
    skill = _board("scout_mark")
    state = _scout_scene(skill, [(5, 3), (1, 3)])  # 都是 2 格
    *events, after = _next_turn_of_owner(state, 2)
    applied = [
        e.target_id for e in events if isinstance(e, StatusApplied) and e.status_id == "marked"
    ]
    assert applied == [U2]
    assert isinstance(after, BattleState)


def test_creation_prefers_the_ranged_basic_summon() -> None:
    """選「召喚物」時推導出來沒有別的關鍵字的遠程基本召喚物優先（近戰骷髏會推導成倒地）。"""
    for seed in range(12):
        skill = compose_whiteboard(seed, kind="active", keyword="summon", tier=1, library=LIB)
        assert skill.effects[0].unit == "summon_elemental_spirit"
        assert whiteboard_keywords_of(skill, LIB) == ("summon",)


def test_nearest_enemy_trigger_schema() -> None:
    ok = TriggerSpec(event="on_turn_start", target="nearest_enemy", max_distance=3)
    assert ok.max_distance == 3
    with pytest.raises(ValidationError):  # 必須指定幾格內
        TriggerSpec(event="on_turn_start", target="nearest_enemy")
    with pytest.raises(ValidationError):  # self 不能有距離上限
        TriggerSpec(event="on_turn_start", target="self", max_distance=3)
