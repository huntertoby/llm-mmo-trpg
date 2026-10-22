"""灌注技能（Phase 3-33d，``docs/design/06-技能.md`` 6.29.3）：1 AP 借招、施放者當下付法力與冷卻、
屬性快照、以召喚物位置為原點、目標依模式、每隻每輪 1 次、禁止類別、倒下不退還、預覽、AI 會灌注、
同種子確定與重播。"""

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
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, project_for, resolve
from trpg.engine.actions import ACTION_ADAPTER, EndTurn, InfuseSkill, SetSummonMode
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.events import (
    DamageDealt,
    InfusedSkillCast,
    InfusionFizzled,
    SkillCooldownChanged,
    SkillInfused,
    SkillUsed,
    UnitSummoned,
)
from trpg.engine.lifecycle import down_unit
from trpg.engine.preview import preview
from trpg.engine.skill_infusion import infuse_choices, pick_infused, skill_ban
from trpg.engine.state import state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1 = UnitId("unit_0001")
SKELETON = "summon_skeleton_warrior"
SUMMON_ID = "skill_t_summon"
BOLT = "skill_t_bolt"
BLAST = "skill_t_blast"
HEAL = "skill_t_heal"


def summon_skill() -> SkillDef:
    return make_skill(
        SUMMON_ID,
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": SKELETON, "duration": 4}],
    )


def bolt(reach: int = 2) -> SkillDef:
    """單體、射程 ``reach``、法力 3、冷卻 2 的火球。"""
    return make_skill(
        BOLT,
        {"type": "single", "range": reach},
        [{"type": "damage", "dice": "1d4", "element": "fire"}],
        cost={"mana": 3, "cooldown": 2},
    )


def blast() -> SkillDef:
    """以格子為中心的十字（射程 3），打所有人（敵我不分）。"""
    return make_skill(
        BLAST,
        {"type": "cross", "range": 3},
        [{"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"}],
        cost={"mana": 2},
    )


def heal() -> SkillDef:
    return make_skill(
        HEAL, {"type": "single", "range": 3}, [{"type": "heal", "dice": "1d4"}], cost={"mana": 1}
    )


def pos(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def arena(
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    *,
    extra: Sequence[SkillDef] = (),
    summon_at: tuple[int, int] = (2, 3),
    owner: dict[str, Any] | None = None,
    seed: int = 0,
) -> tuple[BattleState, UnitId]:
    """U1 是施放者（(0, 3)），已在 ``summon_at`` 召喚骷髏；之後是不反應的敵人（HP 300）。回傳
    （輪到施放者的狀態，召喚物 ID）。"""
    skills = [summon_skill(), *(extra or [bolt()])]
    m = make_map(FLAT7, ally=[(0, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (0, 3), caster_template(skills, **(owner or {})))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=300)) for xy in foes]
    state = give_turn(make_state(m, spawns, skills=skills, seed=seed), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SUMMON_ID, target_pos=pos(*summon_at)))
    [event] = of(result, UnitSummoned)
    return give_turn(result.state, U1), event.unit_id


def foe_ids(state: BattleState) -> list[UnitId]:
    return [u.id for u in state.units_sorted() if u.team is Team.ENEMY]


def infuse(state: BattleState, sid: UnitId, skill_id: str = BOLT) -> Any:
    return resolve(state, InfuseSkill(unit_id=U1, summon_id=sid, skill_id=skill_id))


def end_turn(state: BattleState) -> Any:
    """施放者結束回合 → 輪到召喚物（召喚物排在施放者之後），回合開始時施放灌注的技能。"""
    return resolve(state, EndTurn(unit_id=U1))


# ---------------------------------------------------------------------------
# 代價與時機
# ---------------------------------------------------------------------------


def test_infusing_costs_one_ap_and_the_skills_mana_and_cooldown_now() -> None:
    state, sid = arena()
    owner = state.units[U1]
    result = infuse(state, sid)
    after = result.state.units[U1]
    assert after.ap == owner.ap - 1
    assert after.mana == owner.mana - 3
    assert after.cooldowns[BOLT] == 2
    [event] = of(result, SkillInfused)
    assert (event.unit_id, event.owner_id, event.skill_id, event.ap) == (sid, U1, BOLT, 1)
    assert of(result, SkillCooldownChanged)[0].remaining == 2
    assert not of(result, SkillUsed) and not of(result, DamageDealt)  # 還沒施放
    infused = result.state.units[sid].infused_skill
    assert infused is not None and infused.owner_id == U1 and infused.skill_id == BOLT


def test_the_summon_casts_at_the_start_of_its_next_turn_from_its_own_tile() -> None:
    state, sid = arena(foes=((4, 3),))  # 敵人與施放者距離 4（射程 2 打不到），與召喚物距離 2
    foe = foe_ids(state)[0]
    with pytest.raises(IllegalActionError):
        resolve(state, UseSkill(unit_id=U1, skill_id=BOLT, target_id=foe))
    result = end_turn(infuse(state, sid).state)
    [cast] = of(result, InfusedSkillCast)
    assert cast.unit_id == sid and cast.origin == pos(2, 3) and cast.target_id == foe
    assert any(isinstance(e, DamageDealt) and e.source_id == sid for e in result.events)
    summon = result.state.units[sid]
    assert result.state.active_unit == sid and summon.infused_skill is None
    assert summon.ap == library().ruleset.core.ap_per_turn - 1  # 佔用召喚物 1 AP
    assert result.state.units[U1].cooldowns[BOLT] == 2  # 冷卻在灌注時就開始算，不重複


def test_out_of_the_summons_range_the_infusion_fizzles_without_refund() -> None:
    state, sid = arena(foes=((6, 6),))  # 與召喚物距離 7
    infused = infuse(state, sid).state
    result = end_turn(infused)
    [fizzle] = of(result, InfusionFizzled)
    assert (fizzle.unit_id, fizzle.reason) == (sid, "no_target")
    assert not of(result, InfusedSkillCast)
    assert result.state.units[U1].mana == infused.units[U1].mana  # 不退
    assert result.state.units[sid].infused_skill is None


def test_a_summon_that_falls_before_casting_loses_the_infusion() -> None:
    state, sid = arena()
    infused = infuse(state, sid).state
    ctx = Ctx(infused.clone())
    down_unit(ctx, ctx.state.units[sid])
    downed = ctx.state
    result = end_turn(downed)
    assert not of(result, InfusedSkillCast) and not of(result, InfusionFizzled)
    assert result.state.units[U1].mana == infused.units[U1].mana
    assert result.state.units[U1].cooldowns[BOLT] == 2


def test_a_stunned_summon_drops_the_infusion() -> None:
    state, sid = arena()
    infused = infuse(state, sid).state.clone()
    from trpg.engine.state import StatusInstance  # noqa: PLC0415

    infused.units[sid].statuses.append(StatusInstance("stun", remaining=2))
    result = end_turn(infused)
    [fizzle] = of(result, InfusionFizzled)
    assert fizzle.reason == "controlled"


# ---------------------------------------------------------------------------
# 快照
# ---------------------------------------------------------------------------


def _with_int(state: BattleState, value: int) -> BattleState:
    out = state.clone()
    owner = out.units[U1]
    owner.attributes = {**owner.attributes, Attribute.INT: value}
    return out


def _cast_damage(result: Any, sid: UnitId) -> list[int]:
    return [e.amount for e in result.events if isinstance(e, DamageDealt) and e.source_id == sid]


def test_the_snapshot_does_not_follow_the_casters_later_attributes() -> None:
    state, sid = arena(seed=3)
    infused = infuse(state, sid).state
    plain = end_turn(infused)
    changed = end_turn(_with_int(infused, 40))  # 灌注之後施放者的智力大幅改變
    assert _cast_damage(plain, sid) and _cast_damage(plain, sid) == _cast_damage(changed, sid)
    before = end_turn(infuse(_with_int(state, 40), sid).state)  # 灌注之前就改變：快照不同
    assert _cast_damage(before, sid) != _cast_damage(plain, sid)
    snap = dict(infused.units[sid].infused_skill.attributes)
    assert snap[Attribute.INT] == state.units[U1].attributes[Attribute.INT]


def test_the_summon_gets_its_own_attributes_back_after_casting() -> None:
    state, sid = arena()
    mine = dict(state.units[sid].attributes)
    result = end_turn(infuse(state, sid).state)
    assert of(result, InfusedSkillCast)
    assert result.state.units[sid].attributes == mine
    assert result.state.units[sid].weapon == state.units[sid].weapon


# ---------------------------------------------------------------------------
# 目標依模式
# ---------------------------------------------------------------------------


def test_follow_picks_the_best_selection_for_an_area_skill() -> None:
    # 十字：(4, 1)、(4, 2) 兩個敵人可以一起打；(1, 6) 單獨一個
    state, sid = arena(foes=((4, 1), (4, 2), (1, 6)), extra=[blast()])
    found = pick_infused(infuse(state, sid, BLAST).state, sid)
    assert found is not None
    _, area = found
    assert sorted(area.units) == sorted(foe_ids(state)[:2])


def test_focus_casts_at_the_chosen_target() -> None:
    state, sid = arena(foes=((4, 1), (4, 2), (1, 6)), extra=[blast()])
    lone = foe_ids(state)[2]
    state = resolve(
        state, SetSummonMode(unit_id=U1, summon_id=sid, mode="focus", target_id=lone)
    ).state
    result = end_turn(infuse(state, sid, BLAST).state)
    [cast] = of(result, InfusedSkillCast)
    assert pos(1, 6) in cast.tiles
    assert not {pos(4, 1), pos(4, 2)} & set(cast.tiles)


def test_focus_on_an_unreachable_target_gives_up() -> None:
    state, sid = arena(foes=((3, 3), (6, 6)))
    far = foe_ids(state)[1]
    state = resolve(
        state, SetSummonMode(unit_id=U1, summon_id=sid, mode="focus", target_id=far)
    ).state
    result = end_turn(infuse(state, sid).state)
    assert of(result, InfusionFizzled)[0].reason == "no_target"


def test_guard_prefers_the_enemy_threatening_the_caster() -> None:
    # (1, 4) 緊貼施放者（威脅）；(2, 1) 速度改成 0、近戰，打不到施放者（不算威脅）
    state, sid = arena(foes=((1, 4), (2, 1)), summon_at=(2, 3), extra=[bolt(reach=3)])
    near, other = foe_ids(state)
    state.units[other].speed = 0  # 不能移動、近戰：不威脅施放者
    state = resolve(state, SetSummonMode(unit_id=U1, summon_id=sid, mode="guard")).state
    found = pick_infused(infuse(state, sid).state, sid)
    assert found is not None and found[0].target_id == near
    follow = pick_infused(
        infuse(
            resolve(state, SetSummonMode(unit_id=U1, summon_id=sid, mode="follow")).state, sid
        ).state,
        sid,
    )
    assert follow is not None  # 跟隨照評估選（兩者同分時取列舉在前的）


def test_support_skills_target_allies() -> None:
    state, sid = arena(extra=[heal()])
    state.units[U1].hp -= 5
    found = pick_infused(infuse(state, sid, HEAL).state, sid)
    assert found is not None and found[0].target_id in (U1, sid)


# ---------------------------------------------------------------------------
# 限制
# ---------------------------------------------------------------------------


def test_once_per_summon_per_round_and_one_pending_skill() -> None:
    state, sid = arena(extra=[bolt(), heal()])
    infused = infuse(state, sid).state
    with pytest.raises(IllegalActionError, match="待施放"):
        infuse(infused, sid, HEAL)
    cast = end_turn(infused).state  # 施放完：身上沒有待施放的，但本輪已灌注過
    again = give_turn(cast, U1)
    with pytest.raises(IllegalActionError, match="本輪已經被灌注過"):
        infuse(again, sid, HEAL)
    nxt = give_turn(again, U1)
    nxt.round += 1
    assert of(infuse(nxt, sid, HEAL), SkillInfused)


def test_needs_ap_mana_and_an_own_live_summon() -> None:
    state, sid = arena()
    broke = state.clone()
    broke.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        infuse(broke, sid)
    dry = state.clone()
    dry.units[U1].mana = 0
    with pytest.raises(IllegalActionError, match="法力不足"):
        infuse(dry, sid)
    foe = foe_ids(state)[0]
    with pytest.raises(IllegalActionError):
        infuse(state, foe)


def test_forbidden_skill_kinds_are_greyed_with_reasons() -> None:
    lib = library()
    rules = lib.ruleset
    banned = {
        "summon": summon_skill(),
        "legendary": make_skill(
            "skill_t_legend",
            {"type": "single", "range": 2},
            [{"type": "damage", "dice": "1d4", "element": "fire"}],
        ).model_copy(update={"rarity": "legendary"}),
    }
    state, _ = arena(extra=[bolt()])
    assert "召喚技能" in (skill_ban(state, banned["summon"]) or "")
    assert "傳說" in (skill_ban(state, banned["legendary"]) or "")
    followup = next(s for s in rules.skills.skills if s.followup is not None)
    assert "複合" in (skill_ban(state, followup) or "")
    rewrite = next(
        s
        for s in rules.skills.skills
        if s.rarity != "legendary"
        and s.kind == "active"
        and any(rules.primitive_def(e.type).category == "rule_rewrite" for e in s.effects)
    )
    assert "改變規則" in (skill_ban(state, rewrite) or "")
    assert skill_ban(state, bolt()) is None


def test_the_infuse_menu_lists_active_skills_with_reasons() -> None:
    state, sid = arena(extra=[bolt(), heal()])
    problem, choices = infuse_choices(state, state.units[U1], sid)
    assert problem is None
    by_id = {c.skill_id: c for c in choices}
    assert by_id[BOLT].problem is None and by_id[HEAL].problem is None
    assert "召喚技能" in (by_id[SUMMON_ID].problem or "")
    infused = infuse(state, sid).state
    problem, choices = infuse_choices(infused, infused.units[U1], sid)
    assert problem is not None and "待施放" in problem
    assert "冷卻" in ({c.skill_id: c for c in choices}[BOLT].problem or "")


def test_a_summon_expiring_at_the_end_of_this_turn_cannot_be_infused() -> None:
    state, sid = arena()
    late = state.clone()
    late.units[sid].summon_expires_round = late.round
    with pytest.raises(IllegalActionError, match="來不及"):
        infuse(late, sid)


# ---------------------------------------------------------------------------
# 預覽與視圖
# ---------------------------------------------------------------------------


def test_preview_shows_the_range_from_the_summon() -> None:
    state, sid = arena(foes=((4, 3),))
    foe = foe_ids(state)[0]
    p = preview(state, InfuseSkill(unit_id=U1, summon_id=sid, skill_id=BOLT))
    assert p.infusion is not None and p.infusion.origin == (2, 3)
    assert p.infusion.target_id == foe and p.infusion.tiles == ((4, 3),)
    assert p.affected_tiles == ((4, 3),) and p.ap_cost == 1
    far_state, far_sid = arena(foes=((6, 6),))
    q = preview(far_state, InfuseSkill(unit_id=U1, summon_id=far_sid, skill_id=BOLT))
    assert q.infusion is not None and q.infusion.no_target and q.infusion.tiles == ()


def test_the_view_shows_the_pending_skill() -> None:
    state, sid = arena()
    infused = infuse(state, sid).state
    view = {u.id: u for u in project_for(infused, Team.ALLY).units}[sid]
    assert view.infused_skill_id == BOLT and view.infused
    assert view.infused_skill_name_zh == infused.ruleset.skill_def(BOLT).name_zh
    after = {u.id: u for u in project_for(end_turn(infused).state, Team.ALLY).units}[sid]
    assert after.infused_skill_id is None


def test_the_action_round_trips_through_json() -> None:
    action = InfuseSkill(unit_id=U1, summon_id=UnitId("unit_0003"), skill_id=BOLT)
    assert ACTION_ADAPTER.validate_json(ACTION_ADAPTER.dump_json(action)) == action


# ---------------------------------------------------------------------------
# AI、確定性與重播
# ---------------------------------------------------------------------------


def _out_of_reach() -> tuple[BattleState, UnitId]:
    """敵人在施放者的武器（射程 5）與火球之外、在召喚物的火球射程內；施放者不能移動、
    召喚技冷卻中。"""
    state, sid = arena(foes=((6, 3),), owner={"speed": 0}, extra=[bolt(reach=4)])
    state.units[U1].cooldowns[SUMMON_ID] = 3
    return state, sid


def test_the_ai_infuses_when_only_the_summon_can_reach() -> None:
    state, sid = _out_of_reach()
    action = UtilityAI(library().ai_profiles)(state)
    assert action == InfuseSkill(unit_id=U1, summon_id=sid, skill_id=BOLT)


def test_the_ai_does_not_infuse_when_weighted_off() -> None:
    lib = library()
    profiles = lib.ai_profiles
    off = {"infuse_value_permille": 0}
    table = profiles.model_copy(
        update={
            "profiles": tuple(
                p.model_copy(update={"summon": p.summon.model_copy(update=off)})
                for p in profiles.profiles
            )
        }
    )
    state, _ = _out_of_reach()
    assert not isinstance(UtilityAI(table)(state), InfuseSkill)


def test_same_seed_same_result() -> None:
    state, sid = arena(seed=5)
    a = end_turn(infuse(state, sid).state)
    b = end_turn(infuse(state, sid).state)
    assert state_to_json(a.state) == state_to_json(b.state)
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


@pytest.mark.slow
def test_an_ai_battle_with_infusions_replays_identically() -> None:
    """dev_summoner（元素之靈＋火球）由 AI 打到結束：會灌注，且初始狀態 ＋ 動作列表重播一致。"""
    from trpg.engine.runner import replay, run_battle  # noqa: PLC0415
    from trpg.sim.summon_report import _spec  # noqa: PLC0415

    lib = library()
    found = False
    for plan_seed in range(1, 9):
        spec, _ = _spec(lib, "dev_summoner", "bandit_lair", plan_seed, 30)
        seed = spec.seeds[0]
        run = run_battle(spec.setup, seed, UtilityAI(lib.ai_profiles))
        if not any(isinstance(a, InfuseSkill) for a in run.actions):
            continue
        again = replay(spec.setup, seed, run.actions)
        assert state_to_json(again.state) == state_to_json(run.state)
        assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
        assert any(isinstance(e, InfusedSkillCast | InfusionFizzled) for e in run.events)
        found = True
        break
    assert found
