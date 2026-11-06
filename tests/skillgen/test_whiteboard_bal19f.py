"""BAL-19f（玩法決定 #110，06 6.27.4、6.34.1）：白板配方補直線、錐形、環形、連鎖；被動與反應的觸發
時機補到 16 種、每種至少 2 個配方；號令型武器技白板；感知、意志的白板姿態；撤步護體（``step_back``）
改成把攻擊者推開（反應的自身推擊沒有方向，原本在引擎裡不會動）。

每個配方「做得出來、過驗證、預算 70～100%、關鍵字對得上」由 ``test_whiteboard.py``
對全部配方檢查。"""

from __future__ import annotations

from collections import Counter

import pytest

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
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_skills import duel
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, UseSkill, resolve
from trpg.engine.events import DamageDealt, ReactionTriggered, ShieldGained
from trpg.engine.state import StatusInstance
from trpg.shared.types import Attribute, Team
from trpg.skillgen.whiteboard import compose_whiteboard
from trpg.skillgen.whiteboard_check import whiteboard_keywords_of, whiteboard_problems

LIB = library()
RULES = LIB.composer.whiteboard


def _board(
    recipe: str, kind: str, *, tier: int = 1, seed: int = 3, wc: str | None = "melee"
) -> SkillDef:
    return compose_whiteboard(
        seed, kind=kind, tier=tier, library=LIB, recipe_id=recipe, weapon_class=wc
    )


# ---------------------------------------------------------------------------
# 形狀與觸發時機的覆蓋
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shape,tier", [("line", 1), ("cone", 1), ("ring", 1), ("chain", 3)])
def test_whiteboards_reach_line_cone_ring_and_chain(shape: str, tier: int) -> None:
    recipes = [r for r in RULES.recipes("active", tier) if shape in r.shapes]
    assert recipes, shape
    skill = _board(recipes[0].id, "active", tier=tier, wc=None)
    assert skill.shape.type == shape
    assert whiteboard_problems(skill, LIB, tier) == []


def test_chain_whiteboards_wait_for_tier_three() -> None:
    """連鎖跳躍 3 階（6.34.9）。"""
    assert not [r for t in (1, 2) for r in RULES.recipes("active", t) if "chain" in r.shapes]


def test_sixteen_trigger_timings_with_at_least_two_recipes_each() -> None:
    events = Counter(r.trigger_event for r in RULES.passive if r.trigger_event is not None)
    events += Counter(r.reaction_event for r in RULES.reaction if r.reaction_event is not None)
    assert len(events) >= 16, events
    assert min(events.values()) >= 2, events


# ---------------------------------------------------------------------------
# 撤步護體：反應的自身推擊沒有方向（BAL-19e 待決 6）→ 改成把攻擊者推開
# ---------------------------------------------------------------------------


def test_step_back_pushes_the_melee_attacker_away_and_shields_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _board("step_back", "reaction")
    assert skill.shape.type == "single"
    assert all(e.affects != "self" for e in skill.effects if e.type == "push")
    always(monkeypatch)
    result = answered(resolve(duel([skill]), Attack(unit_id=U2, target_id=U1)))
    assert of(result, ReactionTriggered)
    assert result.state.units[U1].xy == (3, 3)  # 持有者不動
    assert result.state.units[U2].xy == (5, 3)  # 攻擊者從 (4, 3) 被推開 1 格
    assert [g for g in of(result, ShieldGained) if g.unit_id == U1]


# ---------------------------------------------------------------------------
# 號令型武器技白板（BAL-19f 追加）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recipe,wc,attr", [("command_strike", "melee", "str"), ("command_shot", "ranged", "dex")]
)
@pytest.mark.parametrize("tier", [1, 2, 3])
def test_command_boards_are_weapon_attacks_with_the_summon_keyword(
    recipe: str, wc: str, attr: str, tier: int
) -> None:
    for seed in range(4):
        skill = _board(recipe, "active", tier=tier, seed=seed, wc=wc)
        assert skill.category == "weapon" and skill.weapon_req == wc
        assert skill.scaling_attr.value == attr
        assert [e.type for e in skill.effects] == ["damage", "apply_status"]
        assert skill.effects[1].status == "commanding" and skill.effects[1].affects == "self"
        assert not [e for e in skill.effects if e.type == "summon"]  # 本身不召喚
        assert whiteboard_keywords_of(skill, LIB) == ("summon",)
        assert whiteboard_problems(skill, LIB, tier) == []


def test_command_board_follows_the_weapon_not_the_heros_mind() -> None:
    hero = {a: (16 if a is Attribute.WIL else 10) for a in Attribute}
    skill = compose_whiteboard(
        1, kind="active", tier=1, library=LIB, recipe_id="command_strike", hero_attributes=hero
    )
    assert skill.scaling_attr.value == "str"


def test_command_strike_hits_and_gives_the_owner_commanding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _board("command_strike", "active")
    always(monkeypatch)
    state = duel([skill], foe_turn=False)
    result = answered(resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2)))
    assert [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert result.state.units[U1].has_status("commanding")


def _summon_scene(commanding: bool) -> BattleState:
    """U1（召喚者）在 (1, 3)；U2（敵人）在 (4, 3)；U3 是 U1 的召喚物，在 (3, 3)，輪到 U3。"""
    m = make_map(FLAT7, ally=[(1, 3), (3, 3)], enemy=[(4, 3)])
    owner = caster_template([], base="hero_fighter", max_hp=999)
    spawns = [
        spawn(Team.ALLY, (1, 3), owner),
        spawn(Team.ENEMY, (4, 3), no_reactions("bandit", max_hp=999)),
        spawn(Team.ALLY, (3, 3), no_reactions("bandit", max_hp=999)),
    ]
    state = make_state(m, spawns)
    state.units[U3].owner_id = U1
    if commanding:
        state.units[U1].statuses.append(StatusInstance("commanding", None))
    return give_turn(state, U3)


@pytest.mark.parametrize("commanding,ppm", [(False, 1_000_000), (True, 1_250_000)])
def test_commanding_raises_the_summons_attack_damage(
    monkeypatch: pytest.MonkeyPatch, commanding: bool, ppm: int
) -> None:
    always(monkeypatch)
    result = answered(resolve(_summon_scene(commanding), Attack(unit_id=U3, target_id=U2)))
    (hit,) = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert hit.status_ppm == ppm


def test_commanding_lasts_until_the_owners_next_turn() -> None:
    status = LIB.ruleset.status_def("commanding")
    assert status.expires == "own_turn_start" and status.beneficial
    assert status.summon_damage_dealt_permille > 1000


# ---------------------------------------------------------------------------
# 感知、意志的白板姿態（BAL-19f 追加）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recipe,tier,attr",
    [
        ("dawn_stance", 2, "wis"),
        ("dawn_stance_hi", 3, "wis"),
        ("dusk_stance", 2, "wil"),
        ("dusk_stance_hi", 3, "wil"),
    ],
)
def test_wisdom_and_will_stance_boards(recipe: str, tier: int, attr: str) -> None:
    hero = {a: (16 if a.value == attr else 10) for a in Attribute}
    skill = compose_whiteboard(
        2, kind="active", tier=tier, library=LIB, recipe_id=recipe, hero_attributes=hero
    )
    assert skill.kind == "stance" and skill.scaling_attr.value == attr
    assert whiteboard_problems(skill, LIB, tier) == []


# ---------------------------------------------------------------------------
# 新觸發時機在引擎裡真的會觸發（各挑一個）
# ---------------------------------------------------------------------------


def test_ally_targeted_reaction_board_answers_the_attacker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """護衛電擊：相鄰隊友被瞄準時，電擊攻擊者。U1（持有者）在 (2, 3)、隊友 U2 在 (3, 3)、
    敵人 U3 在 (4, 3) 攻擊隊友。"""
    skill = _board("watch_spark", "reaction", wc="focus")
    always(monkeypatch)
    m = make_map(FLAT7, ally=[(2, 3), (3, 3)], enemy=[(4, 3)])
    owner = caster_template([skill.id], base="hero_mage", max_hp=999)
    spawns = [
        spawn(Team.ALLY, (2, 3), owner),
        spawn(Team.ALLY, (3, 3), no_reactions("bandit", max_hp=999)),
        spawn(Team.ENEMY, (4, 3), no_reactions("bandit", max_hp=999)),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill]), U3)
    result = answered(resolve(state, Attack(unit_id=U3, target_id=U2)))
    (trig,) = of(result, ReactionTriggered)
    assert (trig.unit_id, trig.trigger_unit_id) == (U1, U3)
    assert [d for d in of(result, DamageDealt) if d.target_id == U3]
