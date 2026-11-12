"""PB-1a：共用的頭目部位系統（``docs/design/05-戰鬥.md`` 5.12.2、``PhasePB-1計畫.md`` 4.11）。

合成頭目放在測試裡（不改 ``content/``），每列一條規則句、實際跑引擎：合法性（``part_targets`` 的
原因代碼）、傷害分流（部位扣頭目實際扣掉的 HP）、部位的護甲與元素覆寫、範圍與持續傷害不傷部位、
破壞（只一次、回血與換階段不長回來、破的那一下倒下不施效果）、封招、打斷蓄力、停機制、能力下降、
控制、多段攻擊、預覽、暫停點、重播、``clone`` 與 JSON 往返。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    spawn,
    template,
    with_rolls,
)
from trpg.content.battle import UnitTemplate
from trpg.content.rules import SkillSlots
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, legal_actions, preview, resolve, resume
from trpg.engine.actions import (
    Attack,
    Decision,
    EndTurn,
    FollowupTarget,
    UseRaceSkill,
    UseSkill,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import resolve_with, start_battle
from trpg.engine.context import Ctx
from trpg.engine.delayed import charge_infos
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect, HealEffect, ShieldEffect
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    FollowupCancelled,
    PartBroken,
    PartDamaged,
    PartStatDown,
    SkillFollowup,
    SkillSealed,
    StatusApplied,
    StatusRemoved,
)
from trpg.engine.parts import check_target_part, part_targets
from trpg.engine.rules.combat import defense_value_permille, element_modifier_ppm
from trpg.engine.rules.statuses import damage_dealt_permille, move_points_for_turn
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.setup import BattleSetup
from trpg.engine.state import StatusInstance, state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Team, UnitId

HERO = UnitId("unit_0001")
BOSS = UnitId("unit_0002")
CLEAVE = "skill_charged_cleave"
FLAT = "000000\n000000\n000000\n000000\n000000\n000000"

PHASES: tuple[dict[str, Any], ...] = (
    {"id": "one", "name_zh": "一"},
    {
        "id": "two",
        "name_zh": "二",
        "trigger": {"kind": "hp_below", "permille": 500},
        "skills": [CLEAVE],
        "add_statuses": [{"status": "mist_return"}],
    },
)

PARTS: tuple[dict[str, Any], ...] = (
    {
        "id": "back",
        "name_zh": "背",
        "reach": "behind",
        "on_break": [{"type": "stop_mechanic", "status": "mist_return"}],
    },
    {
        "id": "head",
        "name_zh": "頭",
        "hp_permille": 200,
        "on_break": [{"type": "seal_skill", "skill": CLEAVE}],
    },
    {
        "id": "tail",
        "name_zh": "尾",
        "exposed_in": ["two"],
        "on_break": [
            {"type": "stat_down", "stat": "damage_dealt", "amount": 750},
            {"type": "interrupt_charge"},
        ],
    },
)


def boss(parts: Sequence[dict[str, Any]] = PARTS, **overrides: Any) -> UnitTemplate:
    data: dict[str, Any] = {
        "max_hp": 100,
        "tags": ("boss", "humanoid"),
        "skills": (CLEAVE,),
        "reactions": (),
        "phases": PHASES,
        "parts": list(parts),
    }
    data.update(overrides)
    return template("bandit", **data)


def arena(
    *,
    hero: UnitTemplate | str = "hero_fighter",
    hero_at: tuple[int, int] = (2, 3),
    boss_at: tuple[int, int] = (3, 3),
    parts: Sequence[dict[str, Any]] = PARTS,
    heights: str = FLAT,
    rule_skills: Sequence[Any] = (),
    hero_weapon: str | None = None,
    seed: int = 0,
    **boss_overrides: Any,
) -> BattleState:
    """英雄（``unit_0001``）對合成頭目（``unit_0002``），輪到英雄；頭目面向西（背後格在東邊）。"""
    lib = library()
    hero_t = template(hero, reactions=()) if isinstance(hero, str) else hero
    setup = make_setup(
        make_map(heights, ally=[hero_at], enemy=[boss_at]),
        [
            spawn(Team.ALLY, hero_at, hero_t, hero_weapon, skills=None),
            spawn(Team.ENEMY, boss_at, boss(parts, **boss_overrides)),
        ],
        skills=rule_skills,
    )
    assert lib is not None
    state = give_turn(start_battle(setup, seed), HERO)
    state.units[BOSS].facing = "west"
    return state


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def reasons(state: BattleState, action: Attack | UseSkill) -> dict[str, str | None]:
    return {t.part_id: t.reason for t in part_targets(state, action)}


def attack(part: str | None = None) -> Attack:
    return Attack(unit_id=HERO, target_id=BOSS, target_part=part)


def in_phase_two(state: BattleState) -> BattleState:
    s = state.clone()
    s.units[BOSS].phase_index = 1
    return s


def damage(state: BattleState, part: str | None, flat: int = 10, **kw: Any) -> Ctx:
    """直接結算一次傷害（固定值，不擲骰），回傳結算後的工作區。"""
    ctx = Ctx(state.clone())
    execute(
        ctx,
        [
            DamageEffect(
                target_id=BOSS, source_id=HERO, cause="attack", flat=flat, part_id=part, **kw
            )
        ],
    )
    return ctx


# ---------------------------------------------------------------------------
# 1. 合法性：part_targets 的原因代碼與 IllegalActionError
# ---------------------------------------------------------------------------


def test_parts_are_listed_by_id_with_their_reasons() -> None:
    state = arena()
    assert reasons(state, attack()) == {"back": "need_behind", "head": None, "tail": "not_exposed"}
    assert reasons(in_phase_two(state), attack())["tail"] is None


def test_the_back_needs_a_melee_attacker_on_the_back_tile() -> None:
    assert reasons(arena(hero_at=(4, 3)), attack())["back"] is None
    assert reasons(arena(hero_at=(3, 2)), attack())["back"] == "need_behind"  # 側面
    archer = arena(hero="hero_archer", hero_at=(4, 3))
    assert reasons(archer, attack())["back"] == "need_behind"  # 遠程站在背後格也不算


HIGH: tuple[dict[str, Any], ...] = (
    {
        "id": "crown",
        "name_zh": "冠",
        "reach": "high_or_far",
        "on_break": [{"type": "interrupt_charge"}],
    },
    {
        "id": "knee",
        "name_zh": "膝",
        "reach": "disabled",
        "on_break": [{"type": "interrupt_charge"}],
    },
)


@pytest.mark.parametrize(("hero_at", "ok"), [((0, 3), False), ((0, 2), True), ((2, 3), False)])
def test_high_or_far_counts_beyond_three_tiles(hero_at: tuple[int, int], *, ok: bool) -> None:
    state = arena(hero="hero_archer", hero_at=hero_at, parts=HIGH)
    assert reasons(state, attack())["crown"] == (None if ok else "need_high_or_far")


def test_high_or_far_counts_a_higher_tile() -> None:
    heights = "000000\n000000\n001000\n000000\n000000\n000000"
    state = arena(hero_at=(2, 2), boss_at=(2, 3), parts=HIGH, heights=heights)
    assert reasons(state, attack())["crown"] is None
    level = arena(hero_at=(1, 3), boss_at=(2, 3), parts=HIGH)
    assert reasons(level, attack())["crown"] == "need_high_or_far"


@pytest.mark.parametrize("status", ["prone", "stun", "frozen"])
def test_disabled_parts_open_when_the_boss_is_down_stunned_or_frozen(status: str) -> None:
    state = arena(parts=HIGH)
    assert reasons(state, attack())["knee"] == "need_disabled"
    state.units[BOSS].statuses.append(StatusInstance(status_id=status, remaining=1))
    assert reasons(state, attack())["knee"] is None


def test_broken_parts_cannot_be_picked() -> None:
    state = arena()
    state.units[BOSS].broken_parts = ("head",)
    assert reasons(state, attack())["head"] == "broken"


AREA = make_skill(
    "skill_test_pb1_area",
    {"type": "square3", "range": 5},
    [{"type": "damage", "dice": "1d4", "element": "fire"}],
)
SINGLE = make_skill(
    "skill_test_pb1_bolt",
    {"type": "single", "range": 5},
    [{"type": "damage", "dice": "1d4", "element": "fire"}],
)
NO_DMG = make_skill(
    "skill_test_pb1_hex",
    {"type": "single", "range": 5},
    [{"type": "apply_status", "status": "weaken", "duration": 1}],
)


def mage_arena() -> BattleState:
    return arena(hero=caster_template([AREA, SINGLE, NO_DMG]), rule_skills=[AREA, SINGLE, NO_DMG])


@pytest.mark.parametrize(
    ("skill", "reason"),
    [(SINGLE.id, None), (NO_DMG.id, "no_damage")],
)
def test_only_single_target_damage_skills_can_pick(skill: str, reason: str | None) -> None:
    state = mage_arena()
    action = UseSkill(unit_id=HERO, skill_id=skill, target_id=BOSS)
    assert reasons(state, action)["head"] == reason


def test_area_skills_cannot_pick_and_cannot_carry_a_part() -> None:
    state = mage_arena()
    # 範圍技用 target_pos，不能和 target_part 一起給；給 target_id 時形狀不對 → area_skill
    action = UseSkill(unit_id=HERO, skill_id=AREA.id, target_id=BOSS)
    assert reasons(state, action)["head"] == "area_skill"
    with pytest.raises(ValueError, match="target_part"):
        UseSkill(
            unit_id=HERO, skill_id=AREA.id, target_pos=state.units[BOSS].pos, target_part="head"
        )


def test_race_skills_and_second_stages_have_no_part_field() -> None:
    with pytest.raises(ValueError, match="target_part"):
        UseRaceSkill.model_validate({"unit_id": HERO, "target_id": BOSS, "target_part": "head"})
    with pytest.raises(ValueError, match="target_part"):
        FollowupTarget.model_validate({"target_id": BOSS, "target_part": "head"})


@pytest.mark.parametrize(
    ("part", "message"),
    [
        ("nope", "沒有部位"),
        ("back", "背後"),
        ("tail", "露出"),
    ],
)
def test_illegal_parts_raise_with_a_reason(part: str, message: str) -> None:
    state = arena()
    assert check_target_part(state, attack(part)) is not None
    with pytest.raises(IllegalActionError, match=message):
        resolve(state, attack(part))


def test_targets_without_parts_reject_a_part() -> None:
    state = arena(parts=())
    assert part_targets(state, attack()) == ()
    with pytest.raises(IllegalActionError, match="沒有部位"):
        resolve(state, attack("head"))


def test_skills_reject_illegal_parts_too() -> None:
    state = mage_arena()
    with pytest.raises(IllegalActionError, match="傷害"):
        resolve(
            state, UseSkill(unit_id=HERO, skill_id=NO_DMG.id, target_id=BOSS, target_part="head")
        )


def test_legal_actions_never_list_part_variants() -> None:
    state = arena()
    assert all(getattr(a, "target_part", None) is None for a in legal_actions(state))


# ---------------------------------------------------------------------------
# 2～4. 傷害分流、防禦覆寫、範圍與持續傷害
# ---------------------------------------------------------------------------


def test_a_part_takes_exactly_what_the_boss_lost() -> None:
    state = arena()
    body, part = damage(state, None), damage(state, "head")
    assert body.state.units[BOSS].hp == part.state.units[BOSS].hp == 90
    dealt = of(part.events, DamageDealt)[0]
    hurt = of(part.events, PartDamaged)
    assert [(h.part_id, h.amount, h.hp_before, h.hp_after) for h in hurt] == [("head", 10, 20, 10)]
    assert part.events.index(hurt[0]) == part.events.index(dealt) + 1  # 緊接在 damage_dealt 之後
    assert of(body.events, PartDamaged) == [] and body.state.units[BOSS].part_hp["head"] == 20


def test_shields_and_multipliers_only_pass_on_the_hp_actually_lost() -> None:
    state = arena()
    ctx = Ctx(state.clone())
    execute(ctx, [ShieldEffect(target_id=BOSS, flat=6)])
    shielded = damage(ctx.state, "head", flat=10)
    assert [e.amount for e in of(shielded.events, PartDamaged)] == [4]  # 10 − 護盾 6
    halved = damage(state, "head", flat=10, multiplier_permille=500)
    assert [e.amount for e in of(halved.events, PartDamaged)] == [5]
    absorbed = damage(state.clone(), "head", flat=3)
    absorbed.state.units[BOSS].statuses.clear()
    ctx = Ctx(state.clone())
    execute(ctx, [ShieldEffect(target_id=BOSS, flat=9)])
    assert of(damage(ctx.state, "head", flat=5).events, PartDamaged) == []  # 全被護盾吸收


def test_part_armor_overrides_the_hit_defense() -> None:
    armored = [dict(PARTS[1], armor_bonus=40), PARTS[0]]
    state = with_rolls(arena(parts=armored), [(20, 10)])
    body = of(resolve(state, attack()).events, AttackRolled)[0]
    part = of(resolve(state, attack("head")).events, AttackRolled)[0]
    assert part.defense_value_permille > body.defense_value_permille
    same = with_rolls(arena(), [(20, 10)])
    assert (
        of(resolve(same, attack("head")).events, AttackRolled)[0].defense_value_permille
        == of(resolve(same, attack()).events, AttackRolled)[0].defense_value_permille
    )


def test_part_resistance_overrides_the_element_modifier() -> None:
    resist = [dict(PARTS[1], resist={"elemental": 500}), PARTS[0]]
    state = arena(parts=resist)
    body = damage(state, None, element=Element.FIRE)
    part = damage(state, "head", element=Element.FIRE)
    assert of(part.events, DamageDealt)[0].amount * 2 == of(body.events, DamageDealt)[0].amount
    assert of(part.events, PartDamaged)[0].amount == of(part.events, DamageDealt)[0].amount


@pytest.mark.parametrize("cause", ["status", "surface", "effect", "explosion"])
def test_damage_without_a_part_never_touches_parts(cause: str) -> None:
    ctx = Ctx(arena().clone())
    execute(ctx, [DamageEffect(target_id=BOSS, source_id=HERO, cause=cause, flat=8)])  # type: ignore[arg-type]
    assert of(ctx.events, PartDamaged) == [] and ctx.state.units[BOSS].part_hp["head"] == 20


# ---------------------------------------------------------------------------
# 5～10. 破壞與效果
# ---------------------------------------------------------------------------


def broken(state: BattleState, part: str, flat: int = 30) -> Ctx:
    return damage(state, part, flat=flat)


def test_a_part_breaks_once_and_stays_broken_through_heals_and_phases() -> None:
    state = in_phase_two(arena())
    ctx = broken(state, "tail")
    assert [e.part_id for e in of(ctx.events, PartBroken)] == ["tail"]
    unit = ctx.state.units[BOSS]
    assert unit.broken_parts == ("tail",) and unit.part_hp["tail"] == 0
    again = damage(ctx.state, "tail", flat=5)
    assert of(again.events, PartDamaged) == [] and of(again.events, PartBroken) == []
    healed = Ctx(again.state.clone())
    execute(healed, [HealEffect(target_id=BOSS, flat=50)])
    assert healed.state.units[BOSS].part_hp["tail"] == 0
    assert healed.state.units[BOSS].broken_parts == ("tail",)


def test_breaking_hit_that_downs_the_boss_applies_nothing() -> None:
    state = arena()
    state.units[BOSS].hp = 5
    state.units[BOSS].part_hp["head"] = 3
    ctx = broken(state, "head", flat=30)
    (event,) = of(ctx.events, PartBroken)
    assert not event.applied and of(ctx.events, SkillSealed) == []
    assert ctx.state.units[BOSS].sealed_skills == ()
    assert "被打碎" in (describe_event(event, ctx.state) or "")


def test_a_sealed_skill_leaves_legal_actions_and_stays_sealed_across_phases() -> None:
    state = arena()
    ctx = broken(state, "head")
    assert [(e.skill_id, e.part_id) for e in of(ctx.events, SkillSealed)] == [(CLEAVE, "head")]
    after = give_turn(ctx.state, BOSS)
    assert all(getattr(a, "skill_id", None) != CLEAVE for a in legal_actions(after))
    with pytest.raises(IllegalActionError, match="封住"):
        resolve(after, UseSkill(unit_id=BOSS, skill_id=CLEAVE))
    # 進入第二階段（技能組含 CLEAVE）仍封住
    hero = give_turn(after, HERO)
    hero.units[BOSS].hp = 40
    entered = resolve(hero, EndTurn(unit_id=HERO)).state
    assert entered.units[BOSS].phase_index == 1 and CLEAVE in entered.units[BOSS].sealed_skills
    assert all(
        getattr(a, "skill_id", None) != CLEAVE for a in legal_actions(give_turn(entered, BOSS))
    )


def charging(state: BattleState, **extra: Any) -> BattleState:
    s = state.clone()
    s.units[BOSS].statuses.append(StatusInstance(status_id=CHARGING, skill_id=CLEAVE, **extra))
    return s


@pytest.mark.parametrize("part", ["head", "tail"])
def test_breaking_interrupts_the_charge(part: str) -> None:
    state = charging(in_phase_two(arena()))
    assert charge_infos(state)
    ctx = broken(state, part)
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]
    assert not ctx.state.units[BOSS].has_status(CHARGING) and charge_infos(ctx.state) == ()
    assert "部位破壞" in (describe_event(of(ctx.events, FollowupCancelled)[0], ctx.state) or "")


def test_interrupt_covers_an_anchored_charge() -> None:
    anchored = charging(in_phase_two(arena()), anchor=Pos(x=1, y=1))
    assert charge_infos(anchored)[0].anchored
    ctx = broken(anchored, "tail")
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]
    assert charge_infos(ctx.state) == ()


DRAGON = "skill_form_dragon"
SLOTS = SkillSlots(active=12, passive=2, reaction=1, stance=2)


def test_interrupt_covers_a_directed_charge() -> None:
    dragon = caster_template(
        [DRAGON, CLEAVE],
        base="hero_fighter",
        max_hp=200,
        stamina=40,
        tags=("boss", "humanoid"),
        phases=PHASES,
        parts=list(PARTS),
    )
    m = make_map(FLAT, ally=[(1, 3)], enemy=[(3, 3)])
    hero = template("hero_fighter", reactions=())
    setup = make_setup(
        m,
        [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, (3, 3), dragon)],
        skill_slots=SLOTS,  # type: ignore[arg-type]
    )
    s = give_turn(start_battle(setup, 0), BOSS)
    s.units[BOSS].mana = s.units[BOSS].stamina = 40
    s = give_turn(resolve(s, UseSkill(unit_id=BOSS, skill_id=DRAGON)).state, BOSS)
    s = resolve(s, Attack(unit_id=BOSS, direction="west")).state
    status = s.units[BOSS].get_status(CHARGING)
    assert status is not None and status.direction == "west"
    s = in_phase_two(s)
    s.units[BOSS].part_hp["tail"] = 1
    ctx = broken(s, "tail")
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]
    assert charge_infos(ctx.state) == ()


RIPOSTE = "skill_parry_riposte"


def test_an_attacked_charge_broken_by_the_same_attack_never_releases() -> None:
    """``release: attacked``：部位破壞（傷害結算當下）先打斷，攻擊結算完找不到蓄力就不釋放。"""
    base = in_phase_two(arena(skills=(CLEAVE, RIPOSTE)))
    base.units[BOSS].statuses.append(StatusInstance(status_id=CHARGING, skill_id=RIPOSTE))
    body = resolve(with_rolls(base, [(20, 15)]), attack())
    assert of(body.events, SkillFollowup), "對照組：打本體會讓反擊釋放"
    s = with_rolls(base, [(20, 15)])
    s.units[BOSS].part_hp["tail"] = 1
    result = resolve(s, attack("tail"))
    assert [e.reason for e in of(result.events, FollowupCancelled)] == ["part_broken"]
    assert of(result.events, SkillFollowup) == []


def test_sealing_another_skill_keeps_the_charge() -> None:
    other = [
        dict(PARTS[1], on_break=[{"type": "seal_skill", "skill": "skill_rending_strike"}]),
        PARTS[0],
    ]
    s = charging(arena(parts=other, skills=(CLEAVE, "skill_rending_strike")))
    ctx = broken(s, "head")
    assert [e.skill_id for e in of(ctx.events, SkillSealed)] == ["skill_rending_strike"]
    assert of(ctx.events, FollowupCancelled) == [] and ctx.state.units[BOSS].has_status(CHARGING)


def test_no_charge_means_interrupt_does_nothing() -> None:
    ctx = broken(in_phase_two(arena()), "tail")
    assert of(ctx.events, FollowupCancelled) == []


def test_stopping_a_mechanic_removes_it_and_blocks_it_from_coming_back() -> None:
    # 第二階段中破背 → 移除 mist_return
    state = in_phase_two(arena(hero_at=(4, 3)))
    state.units[BOSS].statuses.append(StatusInstance(status_id="mist_return"))
    ctx = broken(state, "back")
    assert [e.status_id for e in of(ctx.events, StatusRemoved)] == ["mist_return"]
    assert not ctx.state.units[BOSS].has_status("mist_return")
    # 第一階段就先破 → 進第二階段時不加 mist_return（跳過、不發事件）
    early = broken(arena(hero_at=(4, 3)), "back").state
    hero = give_turn(early, HERO)
    hero.units[BOSS].hp = 40
    result = resolve(hero, EndTurn(unit_id=HERO))
    assert result.state.units[BOSS].phase_index == 1
    assert not result.state.units[BOSS].has_status("mist_return")
    assert all(e.status_id != "mist_return" for e in of(result.events, StatusApplied))


STATS: tuple[dict[str, Any], ...] = (
    {"type": "stat_down", "stat": "move", "amount": 2},
    {"type": "stat_down", "stat": "armor", "amount": 3},
    {"type": "stat_down", "stat": "hit", "amount": 4},
    {"type": "stat_down", "stat": "resist.elemental", "amount": 500},
    {"type": "stat_down", "stat": "damage_dealt", "amount": 750},
)


def stat_arena(effect: dict[str, Any]) -> BattleState:
    return arena(parts=[dict(PARTS[1], on_break=[effect]), PARTS[0]])


def test_stat_down_lowers_move_armor_hit_resist_and_damage() -> None:
    results: dict[str, tuple[int, int]] = {}
    for effect in STATS:
        state = stat_arena(effect)
        after = broken(state, "head").state
        (down,) = of(broken(state, "head").events, PartStatDown)
        assert down.stat == effect["stat"] and down.amount == effect["amount"]
        before_u, after_u = state.units[BOSS], after.units[BOSS]
        rules = state.ruleset
        match effect["stat"]:
            case "move":
                results["move"] = (
                    move_points_for_turn(rules, before_u),
                    move_points_for_turn(rules, after_u),
                )
            case "armor":
                results["armor"] = (
                    defense_value_permille(before_u, rules),
                    defense_value_permille(after_u, rules),
                )
            case "resist.elemental":
                results["resist"] = (
                    element_modifier_ppm(before_u, Element.FIRE, rules),
                    element_modifier_ppm(after_u, Element.FIRE, rules),
                )
            case "damage_dealt":
                results["dealt"] = (
                    damage_dealt_permille(rules, before_u),
                    damage_dealt_permille(rules, after_u),
                )
            case "hit":
                results["hit"] = (0, after_u.part_mods["hit"])
    assert results["move"][1] == results["move"][0] - 2
    assert results["armor"][1] < results["armor"][0]
    assert results["resist"][1] > results["resist"][0]  # 抗性下降 → 受到的修正變大
    assert results["dealt"] == (1000, 750)
    assert results["hit"] == (0, 4)


def test_hit_down_lowers_the_boss_attack_total() -> None:
    state = stat_arena(STATS[2])
    after = broken(state, "head").state
    boss_turn = with_rolls(give_turn(state, BOSS), [(20, 10)])
    hit_turn = with_rolls(give_turn(after, BOSS), [(20, 10)])
    swing = Attack(unit_id=BOSS, target_id=HERO)
    before = of(resolve(boss_turn, swing).events, AttackRolled)[0].total
    lowered = of(resolve(hit_turn, swing).events, AttackRolled)[0].total
    assert lowered == before - 4


def test_damage_dealt_down_lowers_the_boss_damage() -> None:
    state = in_phase_two(arena())
    after = broken(state, "tail").state
    hits = []
    for s in (state, after):
        ctx = Ctx(s.clone())
        execute(ctx, [DamageEffect(target_id=HERO, source_id=BOSS, cause="attack", flat=20)])
        hits.append(of(ctx.events, DamageDealt)[0].amount)
    assert hits[1] < hits[0]


def test_control_goes_through_the_normal_status_path() -> None:
    effect = {"type": "control", "status": "stun", "duration": 1}
    ctx = broken(stat_arena(effect), "head")
    applied = [e.status_id for e in of(ctx.events, StatusApplied)]
    converted = ctx.state.units[BOSS].statuses
    assert applied, "應該照一般施加狀態流程發事件"
    assert any(s.status_id == applied[0] for s in converted)


# ---------------------------------------------------------------------------
# 11～15. 多段攻擊、預覽、暫停點、重播、clone
# ---------------------------------------------------------------------------


def test_every_strike_of_a_multi_hit_weapon_hits_the_same_part() -> None:
    """R5：宣告時判一次；第一下讓頭目轉身（背後條件不再成立），後面幾下仍打同一個部位。"""
    state = arena(hero_at=(4, 3), hero_weapon="dual_dagger")
    assert library().weapons["dual_dagger"].strikes == 2
    s = with_rolls(state, [(20, 20), (20, 20)])
    s.units[BOSS].part_hp["back"] = 1000
    result = resolve(s, attack("back"))
    dealt = [e for e in of(result.events, DamageDealt) if e.target_id == BOSS]
    hurt = of(result.events, PartDamaged)
    assert len(dealt) >= 2 and [h.part_id for h in hurt] == ["back"] * len(dealt)
    # 第一下就打破：剩下的打本體（只有一次 part_damaged）
    s2 = with_rolls(state, [(20, 20), (20, 20)])
    s2.units[BOSS].part_hp["back"] = 1
    again = resolve(s2, attack("back"))
    assert len(of(again.events, PartDamaged)) == 1 and len(of(again.events, PartBroken)) == 1


def test_the_preview_shows_part_damage_without_side_effects() -> None:
    state = arena()
    before = state_to_json(state)
    shown = preview(state, attack("head"))
    assert of(list(shown.min_events), PartDamaged) and of(list(shown.max_events), PartDamaged)
    assert state_to_json(state) == before


PROMPT_BLOCK = [{"reaction": "block", "when": {"event": "targeted_by_melee"}, "mode": "prompt"}]


@pytest.mark.parametrize("accept", [True, False])
def test_resume_after_a_prompt_matches_a_straight_run(*, accept: bool) -> None:
    """打部位途中頭目的格擋詢問（``prompt``）：暫停 → 存檔 → 讀回 → resume，與直接 resume、以及
    帶著同一個決定一次跑完的結果相同。"""
    state = with_rolls(arena(reactions=PROMPT_BLOCK), [(20, 15)])
    action = attack("head")
    paused = resolve(state, action)
    assert paused.pending is not None and paused.pending.unit_id == BOSS
    decision = Decision(unit_id=BOSS, accept=accept)
    direct = resume(paused.state, decision)
    restored = resume(state_from_json(state_to_json(paused.state)), decision)
    straight = resolve_with(state, action, (accept,))
    assert state_to_json(restored.state) == state_to_json(direct.state)
    assert state_to_json(straight.state) == state_to_json(direct.state)
    assert of(direct.events, PartDamaged) and direct.state.units[BOSS].part_hp["head"] < 20


def _scripted(setup: BattleSetup) -> list[Any]:
    """手寫的動作序列：英雄每回合打頭目的「頭」（能打就打部位），其他單位照效用 AI。"""
    ai = UtilityAI(library().ai_profiles)

    def policy(state: BattleState) -> Any:
        unit = state.active
        assert unit is not None
        if unit.id == HERO and state.units[BOSS].alive and unit.ap >= 2:
            act = attack("head")
            if check_target_part(state, act) is None and any(
                isinstance(a, Attack) and a.target_id == BOSS for a in legal_actions(state)
            ):
                return act
        return ai(state)

    return [policy]


def test_a_battle_with_target_part_replays_exactly() -> None:
    setup = make_setup(
        make_map(FLAT, ally=[(2, 3)], enemy=[(3, 3)]),
        [
            spawn(Team.ALLY, (2, 3), template("hero_fighter", reactions=())),
            spawn(Team.ENEMY, (3, 3), boss()),
        ],
        max_rounds=12,
    )
    (policy,) = _scripted(setup)
    run = run_battle(setup, 3, policy)
    assert any(getattr(s, "target_part", None) == "head" for s in run.actions)
    assert of(run.events, PartDamaged)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert again.state.rng_state == run.state.rng_state
    assert state_to_json(again.state) == state_to_json(run.state)


def test_clone_and_json_keep_every_part_field() -> None:
    state = charging(in_phase_two(arena()))
    s = broken(state, "tail").state
    s.units[BOSS].sealed_skills = (CLEAVE,)
    s.units[BOSS].suppressed_statuses = ("mist_return",)
    unit = s.units[BOSS]
    for copy in (s.clone().units[BOSS], state_from_json(state_to_json(s)).units[BOSS]):
        assert copy.parts == unit.parts and copy.part_hp == unit.part_hp
        assert copy.broken_parts == unit.broken_parts == ("tail",)
        assert copy.sealed_skills == unit.sealed_skills
        assert copy.part_mods == unit.part_mods == {"damage_dealt": 750}
        assert copy.suppressed_statuses == unit.suppressed_statuses


def test_units_without_parts_serialize_no_part_keys() -> None:
    state = arena(parts=())
    text = state_to_json(state)
    for key in ("parts", "part_hp", "broken_parts", "sealed_skills", "part_mods", "suppressed"):
        assert f'"{key}' not in text
    assert '"target_part"' not in Attack(unit_id=HERO, target_id=BOSS).model_dump_json()


def test_part_hp_uses_the_opening_max_hp() -> None:
    state = arena()
    assert state.units[BOSS].max_hp == 100
    assert state.units[BOSS].part_hp == {"back": 20, "head": 20, "tail": 20}


def test_part_events_have_log_text() -> None:
    state = in_phase_two(arena())
    ctx = broken(state, "tail")
    lines = [describe_event(e, ctx.state) for e in ctx.events]
    text = "\n".join(line for line in lines if line)
    assert "尾受損" in text and "被打碎" in text and "造成的傷害降為 75%" in text
