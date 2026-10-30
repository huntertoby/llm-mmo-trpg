"""召喚物基本規則（Phase 3-33b，``docs/design/06-技能.md`` 6.29.1、6.29.7）：數值成長與快照、
灌注關鍵字、上限（2 隻／4 輪／3 隻硬上限）、傷害加成上限、Boss ×2 與 Boss AI 優先清擋路的召喚物。"""

from __future__ import annotations

from collections.abc import Sequence
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
from trpg.content.rules import CoreRules
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine import modifiers as mods
from trpg.engine.ai.summon import blocking_summons
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import DamageDealt, SummonExpired, UnitSummoned
from trpg.engine.infusion import infusion_options, preferred_infusion
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.targeting import compute_area
from trpg.engine.summons.core import growth_of, summon_limit
from trpg.engine.weapon_traits import apply_hit_traits
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
SKELETON = "summon_skeleton_warrior"
SPIRIT = "summon_elemental_spirit"
RAISE = "skill_raise_skeleton"
SPIRIT_SKILL = "skill_summon_spirit"
FIRE_BOLT = "skill_fire_bolt"
GALE_KICK = "skill_blazing_hurl"  # 製造 collision 的法術（任何武器）


def summon_skill(duration: int = 2, unit: str = SKELETON) -> SkillDef:
    return make_skill(
        "skill_t_summon",
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": unit, "duration": duration}],
    )


def arena(
    skills: Sequence[str | SkillDef] = (),
    *,
    owner: dict[str, Any] | None = None,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    foe_tags: Sequence[str] = (),
    custom: Sequence[SkillDef] = (),
    **core: int,
) -> BattleState:
    """U1 是施放者（我方法師站在 (0, 3)，可覆寫範本欄位 ``owner``）；之後是不反應的敵人。"""
    m = make_map(FLAT7, ally=[(0, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (0, 3), caster_template(list(skills), **(owner or {})))]
    for xy in foes:
        spawns.append(spawn(Team.ENEMY, xy, no_reactions(max_hp=300, tags=list(foe_tags))))
    defs = {d.id: d for d in (*[x for x in skills if isinstance(x, SkillDef)], *custom)}
    return give_turn(make_state(m, spawns, skills=list(defs.values()), **core), U1)  # type: ignore[arg-type]


def cast_at(
    state: BattleState, skill_id: str, x: int, y: int, infusion: str | None = None
) -> tuple[BattleState, UnitId]:
    action = UseSkill(unit_id=U1, skill_id=skill_id, target_pos=Pos(x=x, y=y), infusion=infusion)
    result = resolve(state, action)
    [event] = of(result, UnitSummoned)
    return result.state, event.unit_id


def ready(state: BattleState) -> BattleState:
    s = state.clone()
    s.units[U1].cooldowns = {}
    s.units[U1].ap = s.ruleset.core.ap_per_turn
    return s


# ---------------------------------------------------------------------------
# 數值成長與快照
# ---------------------------------------------------------------------------


def hp_of(owner: dict[str, Any]) -> tuple[int, int]:
    """施放者以 ``owner`` 覆寫範本欄位召喚骷髏：（最大 HP，普攻固定傷害）。"""
    skill = summon_skill()
    state, sid = cast_at(arena([skill], owner=owner, custom=[skill]), skill.id, 2, 3)
    unit = state.units[sid]
    return unit.max_hp, unit.weapon.flat


def melee_permille() -> int:
    """骷髏（近戰定位）的 HP 係數（‰；3-33f1）。"""
    return library().ruleset.core.summon_role_hp_permille["melee"]


def test_growth_follows_the_owner_level() -> None:
    base_hp, base_flat = hp_of({"level": 1, "attributes": {"int": 10}})
    hp5, flat5 = hp_of({"level": 5, "attributes": {"int": 10}})
    growth = library().ruleset.core.summon_growth
    # 成長的 HP 也跟著定位係數（骷髏是近戰，3-33f1）放大；取整容許差 1
    scaled = growth.hp_per_level * 4 * melee_permille() / 1000
    assert abs((hp5 - base_hp) - scaled) <= 1
    assert flat5 - base_flat == growth.flat_per_level_permille * 4 // 1000


def test_growth_follows_the_scaling_attribute() -> None:
    low, _ = hp_of({"attributes": {"int": 10}})
    high, _ = hp_of({"attributes": {"int": 20}})
    core = library().ruleset.core
    mod = (20 - core.ability_mod_base) // core.ability_mod_divisor
    scaled = core.summon_growth.hp_per_attr_mod * mod * melee_permille() / 1000
    assert abs((high - low) - scaled) <= 1
    # 縮放屬性之外的屬性不影響（召喚技能縮放智力）
    other, _ = hp_of({"attributes": {"int": 10, "str": 20}})
    assert other == low


def test_growth_values_are_integers_from_core_rules() -> None:
    state = arena([summon_skill()], owner={"level": 3, "attributes": {"int": 14}})
    g = growth_of(state, state.units[U1], "skill_t_summon")
    core = state.ruleset.core.summon_growth
    assert g.hp == core.hp_per_level * 2 + core.hp_per_attr_mod * 2
    assert (
        g.bonus_permille == core.bonus_per_level_permille * 2 + core.bonus_per_attr_mod_permille * 2
    )


def test_growth_is_a_snapshot_taken_when_summoned() -> None:
    skill = summon_skill()
    state = arena([skill], owner={"level": 2}, custom=[skill])
    state, sid = cast_at(state, skill.id, 2, 3)
    before = state.units[sid]
    snap = (before.max_hp, before.hp, before.weapon.flat, before.summon_bonus_permille)
    later = state.clone()
    later.units[U1].level = 9  # 之後施放者升級、屬性改變，都不影響已召喚的
    later.units[U1].attributes[Attribute.INT] = 30
    after = later.units[sid]
    assert (after.max_hp, after.hp, after.weapon.flat, after.summon_bonus_permille) == snap
    # 再召喚一隻才會用新的等級
    later = ready(later)
    later, sid2 = cast_at(later, skill.id, 2, 4)
    assert later.units[sid2].max_hp > snap[0]


def test_summoned_event_carries_the_grown_hp() -> None:
    skill = summon_skill()
    state = arena([skill], owner={"level": 4}, custom=[skill])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=2, y=3)))
    [event] = of(result, UnitSummoned)
    assert event.max_hp == result.state.units[event.unit_id].max_hp


def test_same_seed_and_inputs_give_the_same_summon() -> None:
    skill = summon_skill()

    def run() -> tuple[int, int, str | None]:
        s, sid = cast_at(arena([skill], owner={"level": 3}, custom=[skill]), skill.id, 2, 3)
        u = s.units[sid]
        return u.max_hp, u.weapon.flat, u.infusion

    assert run() == run()


# ---------------------------------------------------------------------------
# 灌注關鍵字
# ---------------------------------------------------------------------------


def test_infusion_options_are_held_keywords_with_a_mapping() -> None:
    state = arena([RAISE, FIRE_BOLT, GALE_KICK])
    assert infusion_options(state, state.units[U1]) == ("prone", "summon", "ignite", "collision")
    # 3-33e1：10 個關鍵字都有對照，召喚技能自己製造的「倒地」「召喚物」也能灌注
    plain = arena([RAISE])
    assert infusion_options(plain, plain.units[U1]) == ("prone", "summon")
    none = arena([FIRE_BOLT])  # 沒有召喚技能：持有的只有點燃
    assert infusion_options(none, none.units[U1]) == ("ignite",)


def test_infusion_defaults_to_the_first_option() -> None:
    state = arena([RAISE, FIRE_BOLT, GALE_KICK])
    state, sid = cast_at(state, RAISE, 2, 3)
    assert state.units[sid].infusion == "prone"


def test_a_chosen_infusion_is_recorded_on_the_summon_and_event() -> None:
    state = arena([RAISE, FIRE_BOLT, GALE_KICK])
    result = resolve(
        state, UseSkill(unit_id=U1, skill_id=RAISE, target_pos=Pos(x=2, y=3), infusion="collision")
    )
    [event] = of(result, UnitSummoned)
    assert event.infusion == "collision"
    assert result.state.units[event.unit_id].infusion == "collision"


def test_infusion_without_a_specific_keyword_is_the_summon_one() -> None:
    # 元素之靈沒有專屬關鍵字：召喚技能只製造「召喚物」，預設灌注它（3-33e1 起 10 個關鍵字都有對照）
    state, sid = cast_at(arena([SPIRIT_SKILL]), SPIRIT_SKILL, 2, 3)
    assert state.units[sid].infusion == "summon"
    state = arena([FIRE_BOLT])  # 沒有召喚技能：施放者持有點燃，不是召喚技能不能帶 infusion
    assert infusion_options(state, state.units[U1]) == ("ignite",)


@pytest.mark.parametrize("bad", ["wet", "charged", "no_such_keyword"])
def test_an_unavailable_infusion_is_illegal(bad: str) -> None:
    # wet、charged：施放者沒有持有；其餘：不存在
    state = arena([RAISE, FIRE_BOLT])
    action = UseSkill(unit_id=U1, skill_id=RAISE, target_pos=Pos(x=2, y=3), infusion=bad)
    with pytest.raises(IllegalActionError):
        resolve(state, action)


def test_only_summon_skills_take_an_infusion() -> None:
    state = arena([RAISE, FIRE_BOLT])
    action = UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2, infusion="ignite")
    with pytest.raises(IllegalActionError):
        compute_area(state, state.units[U1], state.ruleset.skill_def(FIRE_BOLT), action)


def test_ai_picks_the_infusion_by_the_summon_role() -> None:
    state = arena([RAISE, FIRE_BOLT, GALE_KICK, SPIRIT_SKILL])
    owner = state.units[U1]
    assert preferred_infusion(state, owner, SKELETON) == "prone"  # 近戰：持有順序第一個偏好近戰的
    assert preferred_infusion(state, owner, SPIRIT) == "ignite"  # 遠程
    only_fire = arena([FIRE_BOLT])
    assert (
        preferred_infusion(only_fire, only_fire.units[U1], SKELETON) == "ignite"
    )  # 沒有符合的取第一個
    nothing = arena([])  # 沒有任何技能：沒有可選的
    assert preferred_infusion(nothing, nothing.units[U1], SKELETON) is None


def test_infused_attack_applies_the_mapped_status() -> None:
    state, sid = cast_at(arena([RAISE, FIRE_BOLT]), RAISE, 2, 3, "ignite")
    ctx = Ctx(state.clone())
    apply_hit_traits(ctx, ctx.state.units[sid], ctx.state.units[U2])
    assert ctx.state.units[U2].has_status("burning")
    plain, pid = cast_at(arena([RAISE, FIRE_BOLT]), RAISE, 2, 3, "summon")
    ctx = Ctx(plain.clone())
    apply_hit_traits(ctx, ctx.state.units[pid], ctx.state.units[U2])
    assert not ctx.state.units[U2].has_status("burning")


def test_collision_infusion_knocks_the_target_back() -> None:
    state, sid = cast_at(arena([RAISE, GALE_KICK], foes=((3, 3),)), RAISE, 2, 3, "collision")
    ctx = Ctx(state.clone())
    apply_hit_traits(ctx, ctx.state.units[sid], ctx.state.units[U2])
    assert ctx.state.units[U2].xy == (4, 3)


def test_every_infusion_mapping_names_a_real_status() -> None:
    core = library().ruleset.core
    for keyword, infusion in core.summon_infusions.items():
        assert keyword in {k.id for k in library().ruleset.keywords.keywords}
        if infusion.status is not None:
            library().ruleset.status_def(infusion.status)


# ---------------------------------------------------------------------------
# 上限：2 隻、4 輪、3 隻硬上限
# ---------------------------------------------------------------------------


def test_default_limits_are_two_summons_four_rounds_and_a_hard_cap_of_three() -> None:
    core = library().ruleset.core
    assert (core.summon_limit_per_owner, core.summon_max_duration, core.summon_hard_cap) == (
        2,
        4,
        3,
    )


def test_two_at_once_and_the_oldest_disappears() -> None:
    skill = summon_skill(duration=3)
    state = arena([skill], custom=[skill])
    state, first = cast_at(state, skill.id, 2, 3)
    state, second = cast_at(ready(state), skill.id, 2, 4)
    result = resolve(
        ready(state), UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=2, y=2))
    )
    [gone] = of(result, SummonExpired)
    assert (gone.unit_id, gone.reason) == (first, "limit")
    alive = [u.id for u in result.state.units_sorted() if u.is_summon and u.alive]
    assert second in alive and len(alive) == 2


def test_the_limit_never_exceeds_the_hard_cap() -> None:
    core = library().ruleset.core
    assert summon_limit(core.model_copy(update={"summon_limit_per_owner": 3})) == 3
    # 即使（繞過驗證）把上限設得比硬上限高，實際上限仍是硬上限
    assert summon_limit(core.model_copy(update={"summon_limit_per_owner": 5})) == 3
    with pytest.raises(ValueError):
        CoreRules.model_validate({**core.model_dump(), "summon_limit_per_owner": 4})


def test_three_summons_fit_when_the_limit_is_raised_to_the_hard_cap() -> None:
    skill = summon_skill(duration=3)
    state = arena([skill], custom=[skill], summon_limit_per_owner=3)
    for y in (3, 4, 2):
        state, _ = cast_at(ready(state), skill.id, 2, y)
    alive = [u for u in state.units.values() if u.is_summon and u.alive]
    assert len(alive) == 3
    result = resolve(
        ready(state), UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=3, y=3))
    )
    assert [e.reason for e in of(result, SummonExpired)] == ["limit"]  # 第四隻頂掉最舊的
    assert len([u for u in result.state.units.values() if u.is_summon and u.alive]) == 3


def test_duration_is_capped_at_four_rounds() -> None:
    skill = summon_skill(duration=9)
    state = arena([skill], custom=[skill])
    state, sid = cast_at(state, skill.id, 2, 3)
    assert state.units[sid].summon_expires_round == state.round + 4


# ---------------------------------------------------------------------------
# 傷害加成上限
# ---------------------------------------------------------------------------


def rule(change: dict[str, int]) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": "skill_t_atk_bonus",
            "name_zh": "修正",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": [{"applies_to": {"actions": ["attack"]}, "change": change}],
        }
    )


def bonus_of(state: BattleState, sid: UnitId) -> int:
    summon = state.units[sid]
    return mods.summon_damage_bonus(state, summon, mods.ATTACK, Subject(None, (6, 6)))


def test_summon_bonus_counts_toward_the_owners_cap() -> None:
    skill = summon_skill()
    cap = library().ruleset.equipment.caps.damage_bonus_permille
    alone = arena([skill], custom=[skill])
    alone, sid = cast_at(alone, skill.id, 2, 3)
    alone.units[sid].summon_bonus_permille = cap - 100
    assert bonus_of(alone, sid) == cap - 100  # 沒有其他來源：全部算

    boosted = rule({"damage_permille": 300})
    state = arena([skill, boosted], custom=[skill, boosted])
    state, sid = cast_at(state, skill.id, 2, 3)
    state.units[sid].summon_bonus_permille = cap - 100
    assert bonus_of(state, sid) == cap - 300  # 施放者自己占 300，只剩 cap−300 的空間

    full = rule({"damage_permille": cap})
    state = arena([skill, full], custom=[skill, full])
    state, sid = cast_at(state, skill.id, 2, 3)
    state.units[sid].summon_bonus_permille = 200
    assert bonus_of(state, sid) == 0  # 施放者已經頂到上限：召喚物沒有加成
    assert mods.damage_permille(state, state.units[sid], mods.ATTACK, Subject(None, (6, 6))) == 1000


def test_summon_bonus_never_pushes_total_damage_past_the_cap() -> None:
    skill = summon_skill()
    cap = library().ruleset.equipment.caps.damage_bonus_permille
    state = arena([skill], custom=[skill], owner={"level": 99, "attributes": {"int": 40}})
    state, sid = cast_at(state, skill.id, 2, 3)
    summon = state.units[sid]
    assert summon.summon_bonus_permille > cap  # 成長本身會超過上限
    total = mods.damage_permille(state, summon, mods.ATTACK, Subject(None, (6, 6)))
    assert total == 1000 + cap


# ---------------------------------------------------------------------------
# Boss ×2 與 Boss AI
# ---------------------------------------------------------------------------


def hit_summon(foe_tags: Sequence[str], source: UnitId = U2) -> int:
    """敵人 U2 對我方召喚物造成固定 10 點傷害（無骰、無屬性修正）時實際扣的血。"""
    skill = summon_skill()
    state = arena([skill], custom=[skill], foe_tags=foe_tags)
    state, sid = cast_at(state, skill.id, 2, 3)
    ctx = Ctx(state.clone())
    execute(
        ctx, [DamageEffect(target_id=sid, source_id=source, cause="effect", flat=10, min_damage=1)]
    )
    [dealt] = [e for e in ctx.events if isinstance(e, DamageDealt)]
    return dealt.amount


def test_boss_deals_double_damage_to_summons() -> None:
    core = library().ruleset.core  # 敵方傷害倍率（BAL-4b，content）：一般 enemy、Boss boss
    assert hit_summon(()) == 10 * core.enemy_damage_permille // 1000
    assert hit_summon(("boss",)) == 20 * core.boss_damage_permille // 1000
    assert library().ruleset.core.boss_summon_damage_permille == 2000


def test_boss_double_damage_only_applies_to_summons() -> None:
    skill = summon_skill()
    state = arena([skill], custom=[skill], foe_tags=("boss",))
    ctx = Ctx(state.clone())
    execute(ctx, [DamageEffect(target_id=U1, source_id=U2, cause="effect", flat=10, min_damage=1)])
    [dealt] = [e for e in ctx.events if isinstance(e, DamageDealt)]
    assert dealt.amount == 10  # 打施放者本人不加倍


def boss_arena(summon_xy: tuple[int, int]) -> tuple[BattleState, UnitId]:
    """Boss（U2，(6,3)）、我方施放者 U1（(0,3)）與一隻我方召喚物；輪到 Boss。"""
    skill = summon_skill()
    state = arena([skill], custom=[skill], foes=((6, 3),), foe_tags=("boss",))
    state, sid = cast_at(state, skill.id, *summon_xy)
    boss = state.clone()
    boss.active_unit = U2
    boss.turn_pos = boss.turn_order.index(U2)
    boss.units[U2].ap = boss.ruleset.core.ap_per_turn
    boss.units[U2].move_points = 0
    return boss, sid


def test_blocking_summons_lie_between_the_boss_and_the_hero() -> None:
    state, sid = boss_arena((3, 3))
    assert sid in blocking_summons(state, state.units[U2], 1)
    off, side = boss_arena((2, 5))
    assert side not in blocking_summons(off, off.units[U2], 1)


def blocked_arena(
    boss_tags: Sequence[str], boss_skills: Sequence[str] | None = None
) -> tuple[BattleState, UnitId]:
    """施放者 U1（(2,3)）、擋在中間的召喚物 (3,3)、盜賊頭目（U2，(4,3)）；輪到頭目。"""
    skill = summon_skill()
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (2, 3), caster_template([skill])),
        spawn(
            Team.ENEMY,
            (4, 3),
            no_reactions(
                "bandit_boss",
                max_hp=300,
                tags=list(boss_tags),
                **({} if boss_skills is None else {"skills": list(boss_skills)}),
            ),
        ),
    ]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    state, sid = cast_at(state, skill.id, 3, 3)
    state = state.clone()
    state.active_unit = U2
    state.turn_pos = state.turn_order.index(U2)
    state.units[U2].ap = state.ruleset.core.ap_per_turn
    return state, sid


def best_on(state: BattleState, sid: UnitId, points: int) -> Any:
    """AI 對召喚物 ``sid`` 的最高分動作（``boss_blocker_points`` 覆寫為 ``points``）。"""
    table = library().ai_profiles
    patched = table.model_copy(
        update={
            "profiles": tuple(
                p.model_copy(
                    update={"summon": p.summon.model_copy(update={"boss_blocker_points": points})}
                )
                for p in table.profiles
            )
        }
    )
    ranked = UtilityAI(patched, override="brute").rank(state)
    return max(
        (r for r in ranked if getattr(r.action, "target_id", None) == sid),
        key=lambda r: r.score,
    ).score


def test_boss_ai_scores_hits_on_a_blocking_summon_higher() -> None:
    boss, sid = blocked_arena(("boss", "elite"))
    assert sid in blocking_summons(boss, boss.units[U2], 1)
    assert best_on(boss, sid, 60) > best_on(boss, sid, 0)


def test_non_boss_units_get_no_blocker_bonus() -> None:
    plain, sid = blocked_arena(())
    assert best_on(plain, sid, 60) == best_on(plain, sid, 0)


def test_boss_ai_actually_attacks_the_blocking_summon() -> None:
    boss, sid = blocked_arena(("boss", "elite"), boss_skills=())  # 只有普攻：打得到的只有召喚物
    action = UtilityAI(library().ai_profiles)(boss)
    assert getattr(action, "target_id", None) == sid
    result = resolve(boss, action)
    assert any(isinstance(e, DamageDealt) and e.target_id == sid for e in result.events)


def test_area_skills_also_hurt_summons_in_the_area() -> None:
    skill = summon_skill()
    state = arena([skill], custom=[skill], foes=((6, 3),), foe_tags=("boss",))
    state, sid = cast_at(state, skill.id, 3, 3)
    ctx = Ctx(state.clone())
    execute(
        ctx,
        [
            DamageEffect(target_id=t, source_id=U2, cause="explosion", flat=5, min_damage=1)
            for t in (U1, sid)
        ],
    )
    amounts = {e.target_id: e.amount for e in ctx.events if isinstance(e, DamageDealt)}
    assert amounts[sid] == 2 * amounts[U1]
