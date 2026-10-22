"""召喚技能分歧進化與召喚專用詞條的引擎結算（Phase 3-33f2，``docs/design/06-技能.md`` 6.28、
6.29.4、6.29.6，``docs/design/08-裝備.md`` 8.21.5.3）。

涵蓋：加深（HP、小特性）、橋接（第二個灌注）、數量型（2 隻各 60%）的召喚結算；召喚冷卻 −1、召喚物
持續 +1 輪、獻祭傷害與治療 +N‰、召喚物倒下時爆炸或治療（新觸發 ``on_summon_downed``）、召喚物繼承
普攻附加詞條；各詞條的遞減疊加與硬上限。進化產物的合法性見
``tests/skillgen/test_summon_evolution.py``。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import pytest

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
from tests.engine.skill_helpers import FLAT7, of
from tests.engine.test_gear import Rolls, _item
from trpg.content.equipment import Loadout
from trpg.content.skills import SkillDef
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import Attack, BattleState, UseSkill, modifiers, resolve
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    GearTriggered,
    Healed,
    SummonExpired,
    UnitDowned,
    UnitSummoned,
)
from trpg.engine.gear_state import GearAffix, GearState
from trpg.engine.gear_summon import (
    gear_sacrifice_permille,
    gear_summon_cooldown,
    gear_summon_duration,
)
from trpg.engine.infusion import active_keywords
from trpg.engine.lifecycle import dismiss_summon
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Surface, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
SKELETON = "summon_skeleton_warrior"
FIRE = "summon_fire_spirit"
GOLEM = "summon_golem"
COOLDOWN = ("affix_summon_cooldown", None)
DURATION = ("affix_summon_duration", None)
BLAST = ("affix_trig_summon_blast", None)
MEND = ("affix_trig_summon_mend", None)
INHERIT = ("affix_summon_inherit_attack", None)
MARK = ("affix_attack_mark", None)


def sacrifice(value: int = 200) -> tuple[str, int]:
    return ("affix_summon_sacrifice", value)


def summon_skill(
    unit: str = SKELETON, duration: int = 2, *, cooldown: int = 4, **spec: Any
) -> SkillDef:
    skill = make_skill(
        "skill_t_summon",
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": unit, "duration": duration, **spec}],
    )
    return skill.model_copy(update={"cost": skill.cost.model_copy(update={"cooldown": cooldown})})


def loadout(slots: Mapping[str, Rolls]) -> Loadout:
    """裝備快照（主手是權杖，單手的法器，副手才放得下東西）。"""
    order = list(SLOT_TYPE_OF)
    items = [
        _item(s, slots[s], weapon="scepter" if s == "main_hand" else None)
        for s in sorted(slots, key=order.index)
    ]
    items = [  # 副手是法器珠（持續詞條要求 orb 標籤）
        i.model_copy(update={"item": i.item.model_copy(update={"tags": ("orb",)})})
        if i.slot == "off_hand"
        else i
        for i in items
    ]
    return Loadout(items=tuple(items))


def arena(
    skills: Sequence[str | SkillDef],
    *,
    gear: Mapping[str, Rolls] | None = None,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    foe_hp: int = 300,
) -> BattleState:
    """U1 是施放者（我方法師在 (0, 3)，可穿裝備）；之後是不反應的敵人。"""
    m = make_map(FLAT7, ally=[(0, 3)], enemy=list(foes))
    owner = spawn(Team.ALLY, (0, 3), caster_template(list(skills)), "scepter", skills=None)
    if gear is not None:
        owner = owner.model_copy(update={"equipment": loadout(gear)})
    spawns = [owner, *[spawn(Team.ENEMY, xy, no_reactions(max_hp=foe_hp)) for xy in foes]]
    defs = [s for s in skills if isinstance(s, SkillDef)]
    return give_turn(make_state(m, spawns, skills=defs), U1)


def cast(state: BattleState, skill_id: str, x: int = 2, y: int = 3) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, target_pos=Pos(x=x, y=y)))


def summons_of(result: Any) -> list[UnitId]:
    return [e.unit_id for e in of(result, UnitSummoned)]


# ---------------------------------------------------------------------------
# 加深：HP 與小特性
# ---------------------------------------------------------------------------


def test_deepen_raises_max_hp_and_adds_the_trait() -> None:
    plain = summon_skill(GOLEM)
    deep = make_skill_like(plain, "skill_t_deep", max_hp_permille=300, trait="swift")
    base = cast(arena([plain], foes=[(6, 6)]), plain.id).state
    [bid] = [u for u in base.units if base.units[u].is_summon]
    state = cast(arena([deep]), deep.id).state
    [sid] = [u for u in state.units if state.units[u].is_summon]
    hp = base.units[bid].max_hp
    assert state.units[sid].max_hp == hp * 1300 // 1000
    assert state.units[sid].hp == state.units[sid].max_hp
    assert state.units[sid].speed == base.units[bid].speed + 1  # 迅捷：移動 +1


def make_skill_like(skill: SkillDef, new_id: str, **spec: Any) -> SkillDef:
    effect = skill.effects[0].model_copy(update=spec)
    return skill.model_copy(update={"id": new_id, "effects": (effect,)})


@pytest.mark.parametrize(
    ("trait", "check"),
    [
        ("sturdy", lambda u, b: u.armor_bonus == b.armor_bonus + 1),
        ("swift", lambda u, b: u.speed == b.speed + 1),
        ("keen", lambda u, b: u.weapon.crit_range == b.weapon.crit_range - 1),
    ],
)
def test_each_small_trait_changes_one_stat(trait: str, check: Any) -> None:
    plain = summon_skill(SKELETON)
    keyed = make_skill_like(plain, "skill_t_trait", trait=trait)
    base = cast(arena([plain]), plain.id).state
    state = cast(arena([keyed]), keyed.id).state
    unit = next(u for u in state.units.values() if u.is_summon)
    ref = next(u for u in base.units.values() if u.is_summon)
    assert check(unit, ref)


# ---------------------------------------------------------------------------
# 橋接：第二個灌注
# ---------------------------------------------------------------------------


def test_bridge_gives_a_second_infusion_alongside_the_innate_one() -> None:
    plain = summon_skill(FIRE)
    wet = make_skill_like(plain, "skill_t_wet", infusion="wet")
    state = cast(arena([wet]), wet.id).state
    unit = next(u for u in state.units.values() if u.is_summon)
    assert unit.bonus_infusion == "wet"
    assert active_keywords(state, unit) == ("ignite", "wet")  # 固有的點燃在前，橋接的潮濕在後


def test_bridge_infusion_applies_on_hit() -> None:
    plain = summon_skill(FIRE)
    wet = make_skill_like(plain, "skill_t_wet", infusion="wet")
    state = cast(arena([wet], foes=[(3, 3)]), wet.id).state
    sid = next(u.id for u in state.units.values() if u.is_summon)
    state = give_turn(state, sid)
    result = resolve(state, Attack(unit_id=sid, target_id=U2))
    target = result.state.units[U2]
    assert result.state.tile(*target.xy).surface is Surface.WATER  # 第二個灌注：命中造水
    assert target.has_status("burning")  # 固有灌注：點燃


# ---------------------------------------------------------------------------
# 數量型：2 隻各 60%
# ---------------------------------------------------------------------------


def test_count_summons_two_weaker_ones() -> None:
    plain = summon_skill(SKELETON)
    twin = make_skill_like(plain, "skill_t_twin", count=2, power_permille=600)
    base = cast(arena([plain]), plain.id)
    twins = cast(arena([twin]), twin.id)
    [one] = summons_of(base)
    first, second = summons_of(twins)
    full = base.state.units[one]
    for uid in (first, second):
        unit = twins.state.units[uid]
        assert unit.max_hp == max(1, full.max_hp * 600 // 1000)
        assert unit.summon_power_permille == 600
    assert twins.state.units[first].pos != twins.state.units[second].pos
    assert twins.state.units[second].pos == Pos(x=3, y=3)  # 第一隻旁邊第一個空格（東）


def test_count_scales_each_summons_damage() -> None:
    plain = summon_skill(SKELETON)
    twin = make_skill_like(plain, "skill_t_twin", count=2, power_permille=600)
    s_plain = cast(arena([plain], foes=[(5, 3)]), plain.id).state
    s_twin = cast(arena([twin], foes=[(5, 3)]), twin.id).state
    a = next(u for u in s_plain.units.values() if u.is_summon)
    b = next(u for u in s_twin.units.values() if u.is_summon)
    foe_a, foe_b = s_plain.units[U2], s_twin.units[U2]
    full = modifiers.damage_permille(s_plain, a, modifiers.ATTACK, Subject(foe_a, foe_a.xy))
    weak = modifiers.damage_permille(s_twin, b, modifiers.ATTACK, Subject(foe_b, foe_b.xy))
    assert full >= 1000
    assert weak == full * 600 // 1000


def test_count_second_summon_fizzles_when_there_is_no_room() -> None:
    twin = make_skill_like(summon_skill(SKELETON), "skill_t_twin", count=2, power_permille=600)
    around = [(3, 3), (1, 3), (2, 4), (2, 2)]  # 目標格四周都擋住
    blockers = [spawn(Team.ENEMY, xy, no_reactions(max_hp=300)) for xy in around]
    m = make_map(FLAT7, ally=[(0, 3)], enemy=around)
    owner = spawn(Team.ALLY, (0, 3), caster_template([twin]))
    boxed = give_turn(make_state(m, [owner, *blockers], skills=[twin]), U1)
    result = cast(boxed, twin.id)
    assert len(summons_of(result)) == 1
    assert [e.reason for e in of(result, EffectFizzled)] == ["summon_blocked"]


def test_count_requires_power_and_vice_versa() -> None:
    base = summon_skill(SKELETON).model_dump(mode="json")
    for bad in ({"count": 2}, {"power_permille": 600}, {"count": 3, "power_permille": 600}):
        data = {**base, "effects": [{**base["effects"][0], **bad}]}
        with pytest.raises(ValueError):
            SkillDef.model_validate(data)


# ---------------------------------------------------------------------------
# 詞條：召喚技能冷卻 −1
# ---------------------------------------------------------------------------


def cooldown_after_cast(slots: Mapping[str, Rolls], *, cooldown: int = 4) -> int | None:
    skill = summon_skill(cooldown=cooldown)
    state = arena([skill], gear=slots)
    cooldowns: dict[str, int] = cast(state, skill.id).state.units[U1].cooldowns
    return cooldowns.get(skill.id)


def test_summon_cooldown_affix_reduces_summon_skill_cooldown_by_one() -> None:
    assert cooldown_after_cast({}) == 4
    assert cooldown_after_cast({"off_hand": [COOLDOWN]}) == 3


def test_summon_cooldown_has_a_floor_of_one_and_ignores_other_skills() -> None:
    assert cooldown_after_cast({"off_hand": [COOLDOWN]}, cooldown=1) == 1
    other = make_skill(
        "skill_t_other",
        {"type": "ground_tile", "range": 4},
        [{"type": "create_surface", "surface": "water", "duration": 2}],
    )
    other = other.model_copy(update={"cost": other.cost.model_copy(update={"cooldown": 4})})
    state = arena([other], gear={"off_hand": [COOLDOWN]})
    owner = state.units[U1]
    assert gear_summon_cooldown(owner, other, 4) == 4  # 不是召喚技能：不受影響


def test_two_cooldown_affixes_still_take_off_only_one() -> None:
    # 同 id 的數值型詞條遞減：第 2 條 50%，−1 與 −1.5 無條件捨去仍是 −1（8.21.5.3）
    assert cooldown_after_cast({"off_hand": [COOLDOWN], "neck": [COOLDOWN]}) == 3


# ---------------------------------------------------------------------------
# 詞條：召喚物持續 +1 輪
# ---------------------------------------------------------------------------


def expires_round(slots: Mapping[str, Rolls], duration: int = 2) -> int:
    skill = summon_skill(duration=duration)
    result = cast(arena([skill], gear=slots), skill.id)
    [event] = of(result, UnitSummoned)
    return event.expires_round


def test_summon_duration_affix_adds_one_round() -> None:
    assert expires_round({"neck": [DURATION]}) == expires_round({}) + 1


def test_duration_affixes_stack_down_to_a_single_extra_round() -> None:
    assert expires_round({"off_hand": [DURATION], "neck": [DURATION]}) == expires_round({}) + 1


def test_duration_bonus_is_added_after_the_content_cap() -> None:
    cap = library().ruleset.core.summon_max_duration
    assert expires_round({"neck": [DURATION]}, duration=cap) == expires_round({}, duration=cap) + 1


def test_duration_affix_helper_is_zero_without_gear() -> None:
    state = arena([summon_skill()])
    assert gear_summon_duration(state.units[U1]) == 0


# ---------------------------------------------------------------------------
# 詞條：獻祭傷害與治療 +20%
# ---------------------------------------------------------------------------


def sacrifice_skill(*, element: str | None) -> SkillDef:
    effect: dict[str, Any] = {"type": "sacrifice_summon", "dice": "2d8", "radius": 1}
    if element is not None:
        effect["element"] = element
    skill = make_skill("skill_t_sac", {"type": "single", "range": 5}, [effect])
    return skill.model_copy(update={"category": "spell", "scaling_attr": "int"})


def sacrifice_amounts(
    slots: Mapping[str, Rolls], *, element: str | None
) -> tuple[int, list[tuple[str, int]]]:
    """（獻祭造成的總數值, 各事件）：先召喚骷髏，再獻祭它。骰子固定最大。"""
    raise_skill = summon_skill(SKELETON)
    sac = sacrifice_skill(element=element)
    foes = [(2, 3)] if element is not None else [(6, 6)]
    state = arena([raise_skill, sac], gear=slots, foes=foes, foe_hp=999)
    state = cast(state, raise_skill.id, 1, 3).state  # 召喚物貼著施放者：治療範圍內有施放者
    [sid] = [u for u in state.units if state.units[u].is_summon]
    s = state.clone()
    s.units[U1].ap = 9
    s.units[U1].hp = 1  # 讓治療有空間
    s.rng_state = state.rng_state
    original = Rng.roll
    try:
        Rng.roll = lambda self, sides: sides if sides != 20 else 19  # type: ignore[method-assign]
        result = resolve(s, UseSkill(unit_id=U1, skill_id=sac.id, target_id=sid))
    finally:
        Rng.roll = original  # type: ignore[method-assign]
    damage = [("damage", e.amount) for e in of(result, DamageDealt)]
    heals = [("heal", e.amount) for e in of(result, Healed)]
    events = damage + heals
    return sum(a for _, a in events), events


def test_sacrifice_affix_boosts_blast_damage() -> None:
    base, _ = sacrifice_amounts({}, element="fire")
    boosted, _ = sacrifice_amounts({"ring_1": [sacrifice()]}, element="fire")
    assert base > 0
    assert boosted > base
    assert boosted == base * 1200 // 1000 or abs(boosted - base * 1.2) <= 1


def test_sacrifice_affix_boosts_healing() -> None:
    base, _ = sacrifice_amounts({}, element=None)
    boosted, _ = sacrifice_amounts({"ring_1": [sacrifice()]}, element=None)
    assert base > 0
    assert boosted > base


def test_sacrifice_bonus_diminishes_and_is_capped_by_the_damage_cap() -> None:
    state = arena([summon_skill()], gear={"ring_1": [sacrifice()], "ring_2": [sacrifice()]})
    assert gear_sacrifice_permille(state, state.units[U1]) == 300  # 200 + 200 × 50%
    huge = arena([summon_skill()])
    affix = library().affixes["affix_summon_sacrifice"]
    huge.units[U1].gear = GearState(
        affixes=(GearAffix("ring_1", "item_x", affix, 900, 1000, 0),)  # 900‰ 超過上限
    )
    cap = huge.ruleset.equipment.caps.damage_bonus_permille
    assert gear_sacrifice_permille(huge, huge.units[U1]) == cap  # 計入全身 +50% 上限


# ---------------------------------------------------------------------------
# 詞條：召喚物倒下時爆炸或治療（新觸發 on_summon_downed）
# ---------------------------------------------------------------------------


def summon_and_kill(
    slots: Mapping[str, Rolls], *, how: str = "downed", foes: Sequence[tuple[int, int]] = ((3, 3),)
) -> tuple[BattleState, Any]:
    """U1 召喚骷髏在 (2, 3)，再讓它被打倒（致命傷害）。回傳（戰場, 結算環境）。"""
    skill = summon_skill(SKELETON)
    state = cast(arena([skill], gear=slots, foes=foes, foe_hp=999), skill.id).state
    [sid] = [u for u in state.units if state.units[u].is_summon]
    ctx = Ctx(state.clone())
    ctx.state.units[U1].hp = 1
    if how == "downed":
        execute(
            ctx,
            [DamageEffect(target_id=sid, source_id=U2, mode="lethal", cause="effect")],
        )
    return ctx.state, ctx


def test_blast_trigger_damages_enemies_around_the_downed_summon() -> None:
    state, ctx = summon_and_kill({"ring_1": [BLAST]})
    triggered = of_events(ctx, GearTriggered)
    assert [t.trigger for t in triggered] == ["on_summon_downed"]
    assert any(isinstance(e, DamageDealt) and e.target_id == U2 for e in ctx.events)
    assert state.units[U2].hp < 999
    # 戰鬥紀錄有中文文字：觸發時機名稱來自 skill_triggers.yaml
    text = [describe_event(e, state) or "" for e in triggered]
    assert "召喚物倒下時" in text[0] and "召喚物倒下時：原地爆炸" in text[0]


def test_mend_trigger_heals_allies_around_the_downed_summon() -> None:
    _state, ctx = summon_and_kill({"ring_1": [MEND]}, foes=[(6, 6)])
    # 施放者 (0,3) 不在爆心 (2,3) 的 1 格內：換成貼著的位置
    assert of_events(ctx, GearTriggered) != []
    assert not any(isinstance(e, DamageDealt) and e.target_id == U2 for e in ctx.events)


def test_mend_heals_an_ally_standing_next_to_the_downed_summon() -> None:
    skill = summon_skill(SKELETON)
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(6, 6)])
    owner = spawn(Team.ALLY, (1, 3), caster_template([skill]), "scepter", skills=None).model_copy(
        update={"equipment": loadout({"ring_1": [MEND]})}
    )
    foe = spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=999))
    state = give_turn(make_state(m, [owner, foe], skills=[skill]), U1)
    state = cast(state, skill.id).state
    [sid] = [u for u in state.units if state.units[u].is_summon]
    ctx = Ctx(state.clone())
    ctx.state.units[U1].hp = 1
    execute(ctx, [DamageEffect(target_id=sid, source_id=U2, mode="lethal", cause="effect")])
    heals = [e for e in ctx.events if isinstance(e, Healed)]
    assert [h.target_id for h in heals] == [U1]
    assert ctx.state.units[U1].hp > 1


def test_summon_trigger_fires_once_per_turn() -> None:
    skill = summon_skill(SKELETON, duration=4)
    state = arena([skill], gear={"ring_1": [BLAST]}, foes=[(3, 3)], foe_hp=999)
    state = cast(state, skill.id).state
    state.units[U1].cooldowns = {}
    state.units[U1].ap = 9
    state = cast(state, skill.id, 2, 2).state
    ids = [u for u in state.units if state.units[u].is_summon and state.units[u].alive]
    assert len(ids) == 2
    ctx = Ctx(state.clone())
    for sid in ids:
        execute(ctx, [DamageEffect(target_id=sid, source_id=U2, mode="lethal", cause="effect")])
    assert len(of_events(ctx, GearTriggered)) == 1  # 每回合 1 次


def test_expired_or_dismissed_summons_do_not_trigger() -> None:
    skill = summon_skill(SKELETON, duration=1)
    state = arena([skill], gear={"ring_1": [BLAST]}, foes=[(3, 3)], foe_hp=999)
    result = cast(state, skill.id)
    s = result.state
    [sid] = [u for u in s.units if s.units[u].is_summon]
    ctx = Ctx(s.clone())
    dismiss_summon(ctx, ctx.state.units[sid], "expired")
    assert of_events(ctx, GearTriggered) == []
    assert of_events(ctx, SummonExpired) != []
    assert of_events(ctx, UnitDowned) == []


def test_only_the_owners_summons_trigger_the_owners_affix() -> None:
    state, _ctx = summon_and_kill({"ring_1": [BLAST]})
    # 敵人（沒有裝備）的單位倒下不會觸發
    ctx2 = Ctx(state.clone())
    execute(ctx2, [DamageEffect(target_id=U2, source_id=U1, mode="lethal", cause="effect")])
    assert of_events(ctx2, GearTriggered) == []


def of_events(ctx: Ctx, kind: type) -> list:  # type: ignore[type-arg]
    return [e for e in ctx.events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 詞條：召喚物繼承你 1 條普攻附加詞條
# ---------------------------------------------------------------------------


def test_summon_inherits_one_attack_affix() -> None:
    skill = summon_skill(SKELETON)
    state = arena([skill], gear={"main_hand": [MARK, INHERIT]})
    summoned = cast(state, skill.id).state
    unit = next(u for u in summoned.units.values() if u.is_summon)
    inherited = [g.affix.id for g in unit.gear.active_affixes()]
    assert inherited == ["affix_attack_mark"]  # 只繼承 1 條普攻附加，繼承詞條本身不傳


def test_inherited_attack_affix_applies_on_the_summons_hits() -> None:
    skill = summon_skill(SKELETON)
    state = arena([skill], gear={"main_hand": [MARK, INHERIT]}, foes=[(3, 3)])
    state = cast(state, skill.id).state
    sid = next(u.id for u in state.units.values() if u.is_summon)
    state = give_turn(state, sid)
    original = Rng.roll
    try:
        Rng.roll = lambda self, sides: 19 if sides == 20 else 1  # type: ignore[method-assign]
        result = resolve(state, Attack(unit_id=sid, target_id=U2))
    finally:
        Rng.roll = original  # type: ignore[method-assign]
    assert result.state.units[U2].has_status("marked")


def test_without_the_inherit_affix_summons_get_nothing() -> None:
    skill = summon_skill(SKELETON)
    state = cast(arena([skill], gear={"main_hand": [MARK]}), skill.id).state
    unit = next(u for u in state.units.values() if u.is_summon)
    assert unit.gear.affixes == ()


def test_inherit_skips_runes_and_the_inherit_affix_itself() -> None:
    skill = summon_skill(SKELETON)
    gear = {"main_hand": [("affix_attack_rune_inscribe", None), INHERIT]}
    unit = next(
        u for u in cast(arena([skill], gear=gear), skill.id).state.units.values() if u.is_summon
    )
    assert unit.gear.affixes == ()  # 符文要靠施放者自己的符文，不繼承


def test_two_inherit_affixes_count_as_one() -> None:
    skill = summon_skill(SKELETON)
    gear = {"main_hand": [MARK, INHERIT], "off_hand": [INHERIT]}
    unit = next(
        u for u in cast(arena([skill], gear=gear), skill.id).state.units.values() if u.is_summon
    )
    assert len(unit.gear.affixes) == 1


# ---------------------------------------------------------------------------
# 確定性
# ---------------------------------------------------------------------------


def test_same_inputs_give_the_same_twin_summons() -> None:
    twin = make_skill_like(summon_skill(SKELETON), "skill_t_twin", count=2, power_permille=600)

    def run() -> list[tuple[int, int, int]]:
        state = cast(arena([twin]), twin.id).state
        return [
            (u.max_hp, u.pos.x, u.summon_power_permille)
            for u in state.units.values()
            if u.is_summon
        ]

    assert run() == run() != []


def test_state_round_trips_with_the_new_unit_fields() -> None:
    twin = make_skill_like(summon_skill(FIRE), "skill_t_twin", count=2, power_permille=600)
    bridge = replace(arena([twin]))
    state = cast(bridge, twin.id).state
    unit = next(u for u in state.units.values() if u.is_summon)
    unit.bonus_infusion = "wet"
    restored = state_from_json(state_to_json(state))
    other = restored.units[unit.id]
    assert (other.bonus_infusion, other.summon_power_permille) == ("wet", 600)
