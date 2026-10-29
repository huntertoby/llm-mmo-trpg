"""連段條件與資源互動（Phase 3D-1）：5 個條件、``restore_resource``、``steal_buff``、狀態分類。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, U3, battle, cast, hit_with, of
from trpg.content.battle import StatusDef
from trpg.content.skills import (
    ConditionSpec,
    ModifierSpec,
    SkillDef,
    condition_text,
    skill_problems,
)
from trpg.engine import (
    BattleState,
    Move,
    UseSkill,
    legal_actions,
    resolve,
    state_from_json,
    state_to_json,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import MoveUnitEffect
from trpg.engine.events import (
    EffectFizzled,
    ResourceRestored,
    SkillCooldownChanged,
    StatusApplied,
    StatusRemoved,
)
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import build_setup
from trpg.engine.state import StatusInstance
from trpg.engine.turns import start_turn
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team
from trpg.sim.lineup import build_allies, default_lineup

BURN: dict[str, Any] = {"type": "apply_status", "status": "burning"}
SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
SECOND = "skill_t_second"


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


def _gated(condition: dict[str, Any]) -> SkillDef:
    """技能層級的條件：不成立時不能施放。"""
    skill = make_skill(SID, SINGLE5, [BURN])
    return skill.model_copy(update={"condition": ConditionSpec.model_validate(condition)})


def _effect_level(condition: dict[str, Any]) -> SkillDef:
    return make_skill(SID, SINGLE5, [{**BURN, "condition": condition}])


def _usable(state: BattleState) -> bool:
    return any(isinstance(a, UseSkill) and a.skill_id == SID for a in legal_actions(state))


def _burned(result: Any) -> set[str]:
    return {e.target_id for e in of(result, StatusApplied) if e.status_id == "burning"}


def _step(state: BattleState, x: int, y: int) -> BattleState:
    caster = state.units[U1]
    path = (Pos(x=caster.pos.x, y=caster.pos.y), Pos(x=x, y=y))
    return resolve(state, Move(unit_id=U1, path=path)).state


# ---------------------------------------------------------------------------
# moved_this_turn
# ---------------------------------------------------------------------------


def test_moved_this_turn_needs_a_walk() -> None:
    skill = _gated({"type": "moved_this_turn"})
    state = battle(skill, [(5, 3)])
    assert not _usable(state)
    with pytest.raises(IllegalActionError, match="技能條件不成立"):
        cast(state, target_id=U2)
    walked = _step(state, 2, 3)
    assert walked.units[U1].moved_this_turn and _usable(walked)
    assert cast(walked, target_id=U2).state is not None


@pytest.mark.parametrize("mode", ["forced", "teleport"])
def test_being_pushed_or_teleported_does_not_count_as_moving(mode: str) -> None:
    skill = _gated({"type": "moved_this_turn"})
    state = battle(skill, [(5, 3)])
    ctx = Ctx(state)
    execute(ctx, [MoveUnitEffect(unit_id=U1, dest=(2, 3), mode=mode)])  # type: ignore[arg-type]
    assert state.units[U1].pos == Pos(x=2, y=3)
    assert not state.units[U1].moved_this_turn and not _usable(state)


def test_the_turn_record_is_cleared_when_the_next_turn_starts_and_serializes() -> None:
    skill = _gated({"type": "moved_this_turn"})
    state = _step(battle(skill, [(5, 3)]), 2, 3)
    state.units[U1].turn_cast_tags = ("fire", "ranged")
    again = state_from_json(state_to_json(state))
    assert again.units[U1].moved_this_turn and again.units[U1].turn_cast_tags == ("fire", "ranged")
    start_turn(Ctx(again), U1)
    assert not again.units[U1].moved_this_turn and again.units[U1].turn_cast_tags == ()


# ---------------------------------------------------------------------------
# adjacent_ally
# ---------------------------------------------------------------------------


def test_adjacent_ally_needs_a_living_friend_beside_the_caster() -> None:
    skill = _gated({"type": "adjacent_ally"})
    assert _usable(battle(skill, [(5, 3)], allies=[(3, 4)]))
    assert not _usable(battle(skill, [(5, 3)], allies=[(1, 1)]))  # 不相鄰
    assert not _usable(battle(skill, [(5, 3)], allies=[(4, 4)]))  # 斜角不算
    down = battle(skill, [(5, 3)], allies=[(3, 4)])
    down.units[U2].downed = True
    assert not _usable(down)
    assert not _usable(battle(skill, [(4, 3)]))  # 相鄰的是敵人


def test_adjacent_ally_as_an_effect_condition() -> None:
    skill = _effect_level({"type": "adjacent_ally"})
    near = battle(skill, [(5, 3)], allies=[(3, 4)])
    far = battle(skill, [(5, 3)], allies=[(0, 0)])
    assert _burned(cast(hit_with(near), target_id=U3)) == {U3}
    assert _burned(cast(hit_with(far), target_id=U3)) == set()


# ---------------------------------------------------------------------------
# target_isolated
# ---------------------------------------------------------------------------


def test_target_isolated_looks_at_the_targets_own_neighbours() -> None:
    skill = _effect_level({"type": "target_isolated"})
    pack = battle(skill, [(5, 3), (5, 4)])
    lone = battle(skill, [(5, 3), (0, 6)])
    assert _burned(cast(hit_with(pack), target_id=U2)) == set()
    assert _burned(cast(hit_with(lone), target_id=U2)) == {U2}


def test_target_isolated_as_a_skill_gate() -> None:
    skill = _gated({"type": "target_isolated"})
    assert _usable(battle(skill, [(5, 3), (0, 6)]))
    pack = battle(skill, [(5, 3)], allies=[(5, 4)])  # 目標身旁是施放者的隊友：仍然落單
    assert _usable(pack)


def test_target_isolated_ignores_the_dead() -> None:
    skill = _effect_level({"type": "target_isolated"})
    state = battle(skill, [(5, 3), (5, 4)])
    state.units[U3].downed = True
    assert _burned(cast(hit_with(state), target_id=U2)) == {U2}


# ---------------------------------------------------------------------------
# first_round
# ---------------------------------------------------------------------------


def test_first_round_only_holds_in_round_one() -> None:
    skill = _gated({"type": "first_round"})
    state = battle(skill, [(5, 3)])
    assert state.round == 1 and _usable(state)
    later = state.clone()
    later.round = 2
    assert not _usable(later)
    effect = _effect_level({"type": "first_round"})
    assert _burned(cast(hit_with(battle(effect, [(5, 3)])), target_id=U2)) == {U2}
    second = battle(effect, [(5, 3)])
    second.round = 3
    assert _burned(cast(hit_with(second), target_id=U2)) == set()


# ---------------------------------------------------------------------------
# cast_tag_this_turn
# ---------------------------------------------------------------------------


def _two_skills(condition_tag: str = "fire") -> BattleState:
    """``SID``：帶 fire 標籤、效果帶 cast_tag_this_turn 條件；``SECOND``：帶 fire 的單純技能。"""
    first = make_skill(
        SID, SINGLE5, [{**BURN, "condition": {"type": "cast_tag_this_turn", "tag": condition_tag}}]
    ).model_copy(update={"tags": ("fire",)})
    second = make_skill(SECOND, SINGLE5, [{"type": "damage", "dice": "1d4", "element": "fire"}])
    second = second.model_copy(update={"tags": ("fire", "spell")})
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(5, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([first, second])),
        spawn(Team.ENEMY, (5, 3), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[first, second]), U1)


def test_cast_tag_this_turn_does_not_count_the_cast_itself() -> None:
    result = cast(hit_with(_two_skills()), target_id=U2)
    assert _burned(result) == set()  # 這次施放不算
    assert result.state.units[U1].turn_cast_tags == ("fire",)


def test_cast_tag_this_turn_counts_earlier_casts_with_the_tag() -> None:
    state = _two_skills()
    after = resolve(hit_with(state), UseSkill(unit_id=U1, skill_id=SECOND, target_id=U2)).state
    assert after.units[U1].turn_cast_tags == ("fire", "spell")
    assert _burned(cast(hit_with(after), target_id=U2)) == {U2}


def test_cast_tag_this_turn_needs_the_matching_tag() -> None:
    state = _two_skills(condition_tag="ice")
    after = resolve(hit_with(state), UseSkill(unit_id=U1, skill_id=SECOND, target_id=U2)).state
    assert _burned(cast(hit_with(after), target_id=U2)) == set()


def test_cast_tag_requires_the_tag_parameter() -> None:
    bad = make_skill(SID, SINGLE5, [{**BURN, "condition": {"type": "cast_tag_this_turn"}}])
    assert any("tag" in p for p in _problems(bad))
    extra = make_skill(SID, SINGLE5, [{**BURN, "condition": {"type": "first_round", "tag": "x"}}])
    assert any("不接受參數 tag" in p for p in _problems(extra))


def test_condition_text_for_the_new_conditions() -> None:
    assert condition_text(ConditionSpec(type="moved_this_turn")) == "本回合移動過"
    assert condition_text(ConditionSpec(type="adjacent_ally")) == "身旁有友方"
    assert condition_text(ConditionSpec(type="target_isolated")) == "目標身邊沒有友方"
    assert condition_text(ConditionSpec(type="first_round")) == "第一輪"
    text = condition_text(
        ConditionSpec(type="cast_tag_this_turn", tag="fire"), tag_name={"fire": "火焰"}.__getitem__
    )
    assert text == "本回合已施放過帶「火焰」標籤的技能"
    assert "fire" not in condition_text(ConditionSpec(type="cast_tag_this_turn", tag="fire"))


def test_a_modifier_rule_may_use_a_new_condition_but_not_for_pre_target_changes() -> None:
    """修正規則的 ``condition`` 可以用新條件；選目標前就決定的改變（ap_delta 等）仍只能用
    ``self_hp_below``（3C-2）。"""
    ModifierSpec.model_validate(
        {
            "applies_to": {"all_attacks": True},
            "condition": {"type": "moved_this_turn"},
            "change": {"damage_permille": 100},
        }
    )
    with pytest.raises(ValidationError, match="self_hp_below"):
        ModifierSpec.model_validate(
            {
                "applies_to": {"all_attacks": True},
                "condition": {"type": "first_round"},
                "change": {"ap_delta": -1},
            }
        )


# ---------------------------------------------------------------------------
# restore_resource
# ---------------------------------------------------------------------------

MANA = {"type": "restore_resource", "resource": "mana", "amount": 5, "affects": "self"}
COOL = {"type": "restore_resource", "resource": "cooldown", "amount": 2, "affects": "self"}


def _self_skill(effect: dict[str, Any], cost: dict[str, Any] | None = None) -> SkillDef:
    return make_skill(SID, {"type": "self"}, [effect], cost=cost)


def test_restore_mana_is_capped_by_max_mana() -> None:
    state = battle(_self_skill(MANA), [(5, 3)])
    unit = state.units[U1]
    unit.mana = unit.max_mana - 3
    result = cast(state)
    (event,) = of(result, ResourceRestored)
    assert (event.resource, event.amount, event.mana_after) == ("mana", 3, unit.max_mana)
    assert result.state.units[U1].mana == unit.max_mana


def test_restore_mana_adds_the_full_amount_when_there_is_room() -> None:
    state = battle(_self_skill(MANA), [(5, 3)])
    state.units[U1].mana = 10
    result = cast(state)
    assert result.state.units[U1].mana == 15
    assert of(result, ResourceRestored)[0].amount == 5


def test_restore_mana_when_full_fizzles() -> None:
    result = cast(battle(_self_skill(MANA), [(5, 3)]))
    assert not of(result, ResourceRestored)
    assert [e.reason for e in of(result, EffectFizzled)] == ["mana_full"]


def test_restore_cooldown_skips_source_skills_and_the_casting_skill() -> None:
    skill = _self_skill(COOL, cost={"mana": 0, "cooldown": 4})
    state = battle(skill, [(5, 3)])
    unit = state.units[U1]
    other = "skill_fire_bolt"
    source_skill = "skill_mirror_cast"  # 傳說：cost.source
    assert library().skills[source_skill].cost.source is not None
    unit.cooldowns = {other: 3, source_skill: 3, "skill_cleave": 1}
    result = cast(state)
    cooldowns = result.state.units[U1].cooldowns
    assert cooldowns[other] == 1  # 3 − 2
    assert "skill_cleave" not in cooldowns  # 1 − 2，下限 0（移除）
    assert cooldowns[source_skill] == 3  # 花源力的技能不受影響
    assert cooldowns[SID] == 4  # 施放中的技能自己的冷卻不縮短
    (event,) = of(result, ResourceRestored)
    assert event.resource == "cooldown" and event.skill_ids == ("skill_cleave", other)
    changes = {e.skill_id: e.remaining for e in of(result, SkillCooldownChanged)}
    assert changes[other] == 1 and changes["skill_cleave"] == 0


def test_restore_cooldown_without_cooling_skills_fizzles() -> None:
    result = cast(battle(_self_skill(COOL), [(5, 3)]))
    assert [e.reason for e in of(result, EffectFizzled)] == ["no_cooldown"]


def test_restore_resource_can_target_an_ally() -> None:
    skill = make_skill(
        SID,
        SINGLE5,
        [{"type": "restore_resource", "resource": "mana", "amount": 4, "affects": "allies"}],
    )
    state = battle(skill, [(5, 3)], allies=[(4, 3)])
    ally = state.units[U2]
    ally.max_mana = 20
    ally.mana = 2
    result = cast(state, target_id=U2)
    assert result.state.units[U2].mana == 6
    assert of(result, ResourceRestored)[0].unit_id == U2


@pytest.mark.parametrize(
    ("effect", "needle"),
    [
        ({"type": "restore_resource", "amount": 2, "affects": "self"}, "resource"),
        (
            {"type": "restore_resource", "resource": "cooldown", "amount": 3, "affects": "self"},
            "冷卻最多",
        ),
        (
            {"type": "restore_resource", "resource": "mana", "amount": 11, "affects": "self"},
            "amount",
        ),
        (
            {"type": "restore_resource", "resource": "mana", "amount": 2, "affects": "enemies"},
            "affects",
        ),
        ({"type": "heal", "dice": "1d4", "resource": "mana", "affects": "self"}, "resource"),
    ],
)
def test_restore_resource_schema_rejections(effect: dict[str, Any], needle: str) -> None:
    try:
        skill = make_skill(SID, SINGLE5, [effect])
    except ValidationError as exc:
        assert needle in str(exc)
        return
    assert any(needle in p for p in _problems(skill))


# ---------------------------------------------------------------------------
# steal_buff
# ---------------------------------------------------------------------------

STEAL = {"type": "steal_buff", "affects": "enemies"}


def _steal_state(statuses: list[StatusInstance]) -> BattleState:
    state = battle(make_skill(SID, SINGLE5, [STEAL]), [(5, 3)])
    state.units[U2].statuses = list(statuses)
    return hit_with(state)


def test_steal_buff_moves_one_buff_with_its_remaining_rounds() -> None:
    result = cast(_steal_state([StatusInstance("guarded", 3)]), target_id=U2)
    assert not result.state.units[U2].has_status("guarded")
    stolen = result.state.units[U1].get_status("guarded")
    assert stolen is not None and stolen.remaining == 3
    (removed,) = of(result, StatusRemoved)
    assert (removed.target_id, removed.status_id, removed.reason) == (U2, "guarded", "stolen")
    (applied,) = of(result, StatusApplied)
    assert (applied.target_id, applied.status_id, applied.duration) == (U1, "guarded", 3)


def test_steal_buff_picks_the_longest_remaining_then_status_id() -> None:
    state = _steal_state(
        [StatusInstance("hasted", 2), StatusInstance("guarded", 3), StatusInstance("empowered", 3)]
    )
    result = cast(state, target_id=U2)
    assert result.state.units[U1].has_status("empowered")  # 同為 3 回合：empowered < guarded
    foe = result.state.units[U2]
    assert foe.has_status("guarded") and foe.has_status("hasted")


def test_steal_buff_prefers_a_permanent_buff() -> None:
    state = _steal_state([StatusInstance("defending", None), StatusInstance("guarded", 5)])
    result = cast(state, target_id=U2)
    stolen = result.state.units[U1].get_status("defending")
    assert stolen is not None and stolen.remaining is None


def test_steal_buff_keeps_the_shield_amount() -> None:
    result = cast(_steal_state([StatusInstance("shielded", 2, U2, 7)]), target_id=U2)
    stolen = result.state.units[U1].get_status("shielded")
    assert stolen is not None and stolen.amount == 7


def test_steal_buff_without_a_buff_fizzles_and_ignores_debuffs_and_neutral_statuses() -> None:
    state = _steal_state([StatusInstance("burning", 2), StatusInstance("undying", 2)])
    result = cast(state, target_id=U2)
    assert [e.reason for e in of(result, EffectFizzled)] == ["no_buff"]
    foe = result.state.units[U2]
    assert foe.has_status("burning") and foe.has_status("undying")
    assert not result.state.units[U1].statuses


def test_steal_buff_cannot_target_allies_or_self() -> None:
    for affects in ("allies", "all", "self"):
        skill = make_skill(SID, SINGLE5, [{"type": "steal_buff", "affects": affects}])
        assert any("affects" in p for p in _problems(skill)), affects


# ---------------------------------------------------------------------------
# 狀態分類
# ---------------------------------------------------------------------------


def test_every_status_has_a_polarity_consistent_with_beneficial() -> None:
    statuses = library().ruleset.statuses.statuses
    for status in statuses:
        assert status.polarity in ("buff", "debuff", "neutral"), status.id
        if status.polarity == "buff":
            assert status.beneficial and not status.stance, status.id
        if status.polarity == "debuff":
            assert not status.beneficial, status.id
        if status.stance or status.prevents_death or status.redirects_damage:
            assert status.polarity == "neutral", status.id
    buffs = {s.id for s in statuses if s.polarity == "buff"}
    assert buffs == {
        "defending",
        "guarded",
        "empowered",
        "hasted",
        "regenerating",
        "shielded",
        # 3W-2b：帶附帶效果的護盾
        "shielded_thorns",
        "shielded_mending",
        "shielded_wet",
        "shielded_marking",
        "overwatch",  # 3D-8c：監視（可被奪取或驅散）
        "rallied",  # 3-33e1：戰意（戰意圖騰的光環）
        "infused_fire",  # 3I-6：臨時附魔
        "infused_holy",
        "stoneskin",  # 3-54b：石膚（大地）
    }


def test_a_status_without_polarity_is_rejected() -> None:
    base = {"id": "x", "name_zh": "x", "description_zh": "x", "expires": "never"}
    with pytest.raises(ValidationError, match="polarity"):
        StatusDef.model_validate(base)
    with pytest.raises(ValidationError, match="beneficial"):
        StatusDef.model_validate({**base, "polarity": "buff"})
    with pytest.raises(ValidationError, match="beneficial"):
        StatusDef.model_validate({**base, "polarity": "debuff", "beneficial": True})
    StatusDef.model_validate({**base, "polarity": "neutral", "beneficial": True})


# ---------------------------------------------------------------------------
# 示範技能與重播
# ---------------------------------------------------------------------------

_DEMO = {
    "moved_this_turn": "skill_charging_strike",
    "adjacent_ally": "skill_shoulder_strike",
    "target_isolated": "skill_pick_off",
    "first_round": "skill_first_strike",
    "cast_tag_this_turn": "skill_arc_follow_up",
    "restore_resource": "skill_focus_surge",
    "steal_buff": "skill_blessing_thief",
}


def test_every_new_mechanic_has_an_equipped_hand_written_skill() -> None:
    lib = library()
    equipped = {s for b in lib.builds.builds for s in b.hero.skills}
    used: set[str] = set()
    for skill_id in [*_DEMO.values(), "skill_quicken_tide"]:
        skill = lib.skills[skill_id]
        assert skill_id in equipped
        used |= {e.type for e in skill.effects}
        used |= {e.condition.type for e in skill.effects if e.condition}
    assert set(_DEMO) <= used
    modes = {
        e.resource for s in lib.skills.values() for e in s.effects if e.type == "restore_resource"
    }
    assert modes == {"mana", "cooldown"}


@pytest.mark.parametrize(
    ("build", "map_id", "seed"),
    [
        ("build_support", "open_plain", 1),
        ("build_warlock", "open_plain", 2),
        ("build_striker", "open_plain", 3),
        ("build_assassin", "narrow_halls", 4),
    ],
)
def test_demo_battles_replay_exactly(build: str, map_id: str, seed: int) -> None:
    lib, allies = build_allies(library(), [build])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    run = run_battle(setup, seed, UtilityAI(lib.ai_profiles))
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


@pytest.mark.parametrize(
    ("build", "seed", "check"),
    [
        ("build_seer", 0, lambda e: isinstance(e, ResourceRestored) and e.resource == "mana"),
        (
            "build_seer",
            0,
            lambda e: isinstance(e, ResourceRestored) and e.resource == "cooldown",
        ),
        ("build_warlock", 5, lambda e: isinstance(e, StatusRemoved) and e.reason == "stolen"),
    ],
)
def test_the_ai_uses_the_resource_skills_in_a_real_battle(
    build: str, seed: int, check: Any
) -> None:
    lib, allies = build_allies(library(), [build])
    _, enemies = default_lineup(lib, "open_plain")
    setup = build_setup(lib, "open_plain", allies, enemies, max_rounds=30)
    run = run_battle(setup, seed, UtilityAI(lib.ai_profiles))
    assert any(check(e) for e in run.events)
