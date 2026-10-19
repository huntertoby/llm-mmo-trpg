"""吸血、聖光雙效、驅散與揭露（Phase 3D-8a，``docs/phases/Phase3D計畫.md`` 8.1、8.4）：吸血（含
護盾、上限、滿血）、分流效果（友方治療、敵方傷害、只骰一次、骨架限制）、互斥規則放寬後其他組合
仍被拒、驅散 1 個／全部、沒有增益時不結算、揭露移除隱蔽並阻止再隱蔽、揭露陷阱、預覽、文字與重播。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, U3, battle, cast, of
from tests.engine.test_variance import script_randint
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, UseSkill, preview, state_to_json
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect
from trpg.engine.event_filter import event_visible_to
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EffectFizzled,
    Healed,
    StatusApplied,
    StatusRemoved,
    TrapRevealed,
)
from trpg.engine.rules.combat import is_concealed
from trpg.engine.rules.statuses import prevents_concealment
from trpg.engine.state import StatusInstance, TrapState
from trpg.engine.traps import own_traps, visible_traps
from trpg.engine.view import project_for
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary, skill_card
from trpg.shared.types import Attribute, Pos, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
SQUARE: dict[str, Any] = {"type": "square3", "range": 5}


def spell(
    shape: dict[str, Any], *effects: dict[str, Any], skeleton: str = "area", **fields: Any
) -> SkillDef:
    data = make_skill(SID, shape, list(effects)).model_dump(mode="json")
    data.update(skeleton=skeleton, **fields)
    return SkillDef.model_validate(data)


def drain(permille: int = 400, dice: str = "1d6") -> dict[str, Any]:
    return {"type": "damage", "dice": dice, "element": "shadow", "lifesteal_permille": permille}


def burst(**fields: Any) -> dict[str, Any]:
    return {
        "type": "damage",
        "dice": "1d12",
        "element": "holy",
        "affects": "all",
        "split_heal": True,
        **fields,
    }


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


def _wound(state: BattleState, unit_id: str, hp: int) -> None:
    state.units[unit_id].hp = hp  # type: ignore[index]


# ---------------------------------------------------------------------------
# 吸血
# ---------------------------------------------------------------------------


def test_lifesteal_heals_the_caster_for_a_share_of_the_damage_dealt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    _wound(state, U1, 5)
    script_randint(monkeypatch, [19, 10])
    result = cast(state, target_id=U2)
    (hit,) = of(result, DamageDealt)
    (heal,) = of(result, Healed)
    assert heal.cause == "lifesteal" and heal.target_id == U1 and heal.source_id == U1
    assert heal.amount == hit.amount * 500 // 1000 and heal.amount > 0
    assert (heal.hp_before, heal.hp_after) == (5, 5 + heal.amount)
    assert result.state.units[U1].hp == 5 + heal.amount


def test_lifesteal_is_floored_and_ignores_the_shield_absorption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(SINGLE5, drain(400, "1d10")), [(5, 3)])
    _wound(state, U1, 5)
    state.units[U2].statuses = [StatusInstance("shielded", 2, U2, 3)]
    script_randint(monkeypatch, [19, 10])
    result = cast(state, target_id=U2)
    (hit,) = of(result, DamageDealt)
    assert hit.absorbed == 3
    (heal,) = of(result, Healed)
    assert heal.amount == (hit.amount - 3) * 400 // 1000


def test_a_fully_absorbed_hit_steals_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(SINGLE5, drain(500, "1d4")), [(5, 3)])
    _wound(state, U1, 5)
    state.units[U2].statuses = [StatusInstance("shielded", 2, U2, 99)]
    script_randint(monkeypatch, [19, 4])
    result = cast(state, target_id=U2)
    (hit,) = of(result, DamageDealt)
    assert hit.amount == hit.absorbed
    assert of(result, Healed) == [] and result.state.units[U1].hp == 5


def test_lifesteal_never_heals_above_the_maximum_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    maximum = state.units[U1].max_hp
    _wound(state, U1, maximum - 1)
    script_randint(monkeypatch, [19, 10])
    result = cast(state, target_id=U2)
    (heal,) = of(result, Healed)
    assert heal.amount == 1 and result.state.units[U1].hp == maximum


def test_lifesteal_at_full_health_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    script_randint(monkeypatch, [19, 10])
    result = cast(state, target_id=U2)
    assert of(result, DamageDealt) and of(result, Healed) == []


def test_a_missed_attack_steals_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(SINGLE5, drain()), [(5, 3)])
    _wound(state, U1, 5)
    script_randint(monkeypatch, [1])
    result = cast(state, target_id=U2)
    assert of(result, DamageDealt) == [] and of(result, Healed) == []


def test_an_area_lifesteal_sums_the_damage_of_every_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(SQUARE, drain(500, "1d10")), [(5, 3), (5, 4)])
    _wound(state, U1, 3)
    script_randint(monkeypatch, [19, 19, 8, 6])
    result = cast(state, target_pos=Pos(x=5, y=3))
    hits = of(result, DamageDealt)
    (heal,) = of(result, Healed)
    assert len(hits) == 2
    assert heal.amount == sum(h.amount - h.absorbed for h in hits) * 500 // 1000


def test_lifesteal_does_not_count_damage_to_allies() -> None:
    """``affects: all`` 打到友方時，友方受到的傷害不算吸血。"""
    skill = spell(SQUARE, {**drain(500, "1d10"), "affects": "all"})
    state = battle(skill, [(5, 3)], allies=[(5, 4)])
    _wound(state, U1, 3)
    result = cast(state, target_pos=Pos(x=5, y=3))
    enemy_damage = sum(h.amount - h.absorbed for h in of(result, DamageDealt) if h.target_id == U3)
    assert sum(h.amount for h in of(result, Healed)) <= enemy_damage * 500 // 1000


def test_lifesteal_is_reduced_by_the_healing_received_modifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    _wound(state, U1, 3)
    state.units[U1].statuses = [StatusInstance("poison", 3, U2)]
    script_randint(monkeypatch, [19, 10])
    result = cast(state, target_id=U2)
    (heal,) = of(result, Healed)
    assert heal.received_permille == 500


def test_lifesteal_schema_limits() -> None:
    assert _problems(spell(SINGLE5, drain(500))) == []
    with pytest.raises(ValueError, match="lifesteal_permille"):
        spell(SINGLE5, drain(501))
    with pytest.raises(ValueError, match="lifesteal_permille"):
        spell(SINGLE5, drain(0))
    heal = {"type": "heal", "dice": "1d6", "lifesteal_permille": 100}
    with pytest.raises(ValueError, match="只有 damage"):
        spell(SINGLE5, heal)
    nested = {
        "type": "gamble",
        "chance_permille": 500,
        "win": [{"type": "damage", "dice": "1d4", "element": "fire", "lifesteal_permille": 100}],
    }
    with pytest.raises(ValueError, match="只能用在技能自己的傷害效果"):
        spell(SINGLE5, drain(), nested)


# ---------------------------------------------------------------------------
# 聖光雙效
# ---------------------------------------------------------------------------


def _burst_state(*, caster_inside: bool = False) -> BattleState:
    center = (4, 3) if caster_inside else (5, 3)
    state = battle(spell(SQUARE, burst()), [(center[0] + 1, 3)], allies=[(center[0], 4)])
    _wound(state, U2, 1)  # 友方 U2、敵人 U3
    return state


def test_the_split_effect_damages_enemies_and_heals_allies_with_one_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _burst_state()
    queue = script_randint(monkeypatch, [19, 7])  # 敵人命中；骰一次：7
    result = cast(state, target_pos=Pos(x=5, y=3))
    (hit,) = of(result, DamageDealt)
    (heal,) = of(result, Healed)
    assert hit.target_id == U3 and hit.rolls == (7,)
    assert heal.target_id == U2 and heal.rolls == (7,) and heal.cause == "heal"
    assert heal.amount > 0 and result.state.units[U2].hp > 1
    assert queue == []  # 全部骰值剛好用完：沒有第二次擲骰


def test_allies_do_not_roll_to_be_hit_by_the_split_effect() -> None:
    state = _burst_state()
    result = cast(state, target_pos=Pos(x=5, y=3))
    assert {r.target_id for r in of(result, AttackRolled)} == {U3}
    assert all(h.target_id != U2 for h in of(result, DamageDealt))


def test_the_caster_standing_in_the_area_is_healed_too(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _burst_state(caster_inside=True)
    _wound(state, U1, 2)
    script_randint(monkeypatch, [19, 5])
    result = cast(state, target_pos=Pos(x=4, y=3))
    assert {h.target_id for h in of(result, Healed)} == {U1, U2}
    assert all(h.target_id != U1 for h in of(result, DamageDealt))


def test_a_critical_hit_adds_dice_for_the_enemy_only(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _burst_state()
    queue = script_randint(monkeypatch, [20, 5, 9])  # 暴擊：預先擲的 5 ＋ 額外的 9
    result = cast(state, target_pos=Pos(x=5, y=3))
    (hit,) = of(result, DamageDealt)
    (heal,) = of(result, Healed)
    assert hit.crit and hit.rolls == (5, 9) and heal.rolls == (5,) and queue == []


def test_a_split_effect_with_no_one_in_the_area_rolls_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(SQUARE, burst()), [(1, 6)])
    queue = script_randint(monkeypatch, [])
    result = cast(state, target_pos=Pos(x=5, y=3))
    assert queue == [] and of(result, DamageDealt) == [] and of(result, Healed) == []


def test_split_heal_schema_restrictions() -> None:
    assert _problems(spell(SQUARE, burst())) == []
    with pytest.raises(ValueError, match="affects: all"):
        spell(SQUARE, burst(affects="enemies"))
    with pytest.raises(ValueError, match="只能用在 aura、area"):
        spell(SQUARE, burst(), skeleton="strike")
    with pytest.raises(ValueError, match="不能與 lifesteal"):
        spell(SQUARE, burst(lifesteal_permille=100))
    with pytest.raises(ValueError, match="不能與 lifesteal"):
        spell(SQUARE, burst(explode=True))
    with pytest.raises(ValueError, match="只能填 true"):
        spell(SQUARE, burst(split_heal=False))
    weapon = {"type": "damage", "affects": "all", "split_heal": True}
    with pytest.raises(ValueError, match="法術技"):
        SkillDef.model_validate(
            {**make_skill(SID, SQUARE, [weapon], category="weapon").model_dump(mode="json")}
        )


def test_the_split_effect_is_accepted_by_the_aura_skeleton_and_priced_on_both_sides() -> None:
    lib = library()
    holy = lib.skills["skill_holy_burst"]
    for skeleton in ("area", "aura"):
        skill = holy.model_copy(update={"skeleton": skeleton})
        assert [v for v in validate_skill(skill, lib) if v.rule.startswith("skeleton.")] == []
    (effect,) = skill_budget(holy, lib).effects
    assert effect.base == 13  # 1d12 平均 6.5：傷害 ＋ 友方治療
    assert effect.shape == 2 and str(effect.target) == "4/5"  # 方陣 ×2；敵我不分 ×0.8


def test_other_damage_plus_ally_heal_combinations_are_still_rejected() -> None:
    lib = library()
    holy = lib.skills["skill_holy_burst"]
    split = holy.effects[0]
    heal = split.model_copy(
        update={"type": "heal", "affects": "allies", "split_heal": None, "element": None}
    )
    plain = split.model_copy(update={"affects": "enemies", "split_heal": None})
    bad = holy.model_copy(update={"effects": (plain, heal)})
    assert any(v.rule == "exclusion.no_damage_with_ally_heal" for v in validate_skill(bad, lib))
    for ok in (holy, lib.skills["skill_life_drain"]):
        assert not any(v.rule.startswith("exclusion.") for v in validate_skill(ok, lib))


# ---------------------------------------------------------------------------
# 驅散
# ---------------------------------------------------------------------------

DISPEL_ALL = {"type": "dispel", "count": "all", "affects": "enemies"}
DISPEL_ONE = {"type": "dispel", "count": 1, "affects": "enemies"}


def _dispel_state(effect: dict[str, Any], statuses: list[StatusInstance]) -> BattleState:
    state = battle(spell(SINGLE5, effect, skeleton="control"), [(5, 3)])
    state.units[U2].statuses = statuses
    return state


def test_dispel_all_removes_every_buff_and_keeps_the_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _dispel_state(
        DISPEL_ALL,
        [
            StatusInstance("guarded", 3),
            StatusInstance("hasted", 2),
            StatusInstance("burning", 2),
            StatusInstance("concealed", 2),
        ],
    )
    script_randint(monkeypatch, [19, 19])  # 目標隱蔽：攻擊有劣勢，擲兩顆 d20
    result = cast(state, target_id=U2)
    removed = {(r.status_id, r.reason) for r in of(result, StatusRemoved)}
    assert removed == {("guarded", "dispelled"), ("hasted", "dispelled")}
    kept = {s.status_id for s in result.state.units[U2].statuses}
    assert kept == {"burning", "concealed"}  # 減益與中性狀態不是增益
    assert of(result, StatusApplied) == []  # 與奪取不同：施放者不會得到它們


def test_dispel_one_takes_the_longest_buff_first(monkeypatch: pytest.MonkeyPatch) -> None:
    buffs = [
        StatusInstance("hasted", 2),
        StatusInstance("guarded", 3),
        StatusInstance("empowered", 3),
    ]
    state = _dispel_state(DISPEL_ONE, buffs)
    script_randint(monkeypatch, [19])
    result = cast(state, target_id=U2)
    (removed,) = of(result, StatusRemoved)
    assert removed.status_id == "empowered"  # 同為 3 回合：依狀態 ID
    left = {s.status_id for s in result.state.units[U2].statuses}
    assert left == {"hasted", "guarded"}


def test_dispel_one_prefers_a_permanent_buff(monkeypatch: pytest.MonkeyPatch) -> None:
    buffs = [StatusInstance("guarded", 5), StatusInstance("defending", None)]
    state = _dispel_state(DISPEL_ONE, buffs)
    script_randint(monkeypatch, [19])
    (removed,) = of(cast(state, target_id=U2), StatusRemoved)
    assert removed.status_id == "defending"


def test_dispel_without_a_buff_fizzles(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _dispel_state(DISPEL_ALL, [StatusInstance("burning", 2)])
    script_randint(monkeypatch, [19])
    result = cast(state, target_id=U2)
    (fizzled,) = of(result, EffectFizzled)
    assert (fizzled.effect_kind, fizzled.reason) == ("dispel", "no_buff")
    assert of(result, StatusRemoved) == []


def test_a_missed_dispel_removes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _dispel_state(DISPEL_ALL, [StatusInstance("guarded", 3)])
    script_randint(monkeypatch, [1])
    result = cast(state, target_id=U2)
    assert result.state.units[U2].has_status("guarded")


def test_dispel_schema() -> None:
    assert _problems(spell(SINGLE5, DISPEL_ALL, skeleton="control")) == []
    assert _problems(spell(SINGLE5, DISPEL_ONE, skeleton="control")) == []
    for bad_count in (0, 2):
        bad = spell(SINGLE5, {**DISPEL_ONE, "count": bad_count}, skeleton="control")
        assert any("必須在 1–1 或 all" in p for p in _problems(bad))
    missing = spell(SINGLE5, {"type": "dispel", "affects": "enemies"}, skeleton="control")
    assert any("缺少必要參數" in p for p in _problems(missing))
    for affects in ("allies", "self", "all"):
        bad = spell(SINGLE5, {**DISPEL_ALL, "affects": affects}, skeleton="control")
        assert any("不能搭配" in p for p in _problems(bad))


def test_dispel_budget_counts_one_and_all_differently() -> None:
    lib = library()
    one = spell(SINGLE5, DISPEL_ONE, skeleton="control")
    everything = spell(SINGLE5, DISPEL_ALL, skeleton="control")
    assert skill_budget(one, lib).effects[0].points == lib.budget.dispel_one_points == 3
    assert skill_budget(everything, lib).effects[0].points == lib.budget.dispel_all_points == 6


# ---------------------------------------------------------------------------
# 揭露
# ---------------------------------------------------------------------------

REVEAL = {"type": "reveal", "duration": 2}


def _reveal_state(*, foes: list[tuple[int, int]] | None = None, **kw: Any) -> BattleState:
    return battle(spell(SQUARE, REVEAL, skeleton="control"), foes or [(5, 3)], **kw)


def test_reveal_removes_concealment_and_blocks_it_for_n_rounds() -> None:
    state = _reveal_state()
    state.units[U2].statuses = [StatusInstance("concealed", 4)]
    assert is_concealed(state, state.units[U2])
    result = cast(state, target_pos=Pos(x=5, y=3))
    removed = [(r.status_id, r.reason) for r in of(result, StatusRemoved)]
    assert removed == [("concealed", "revealed")]
    (applied,) = of(result, StatusApplied)
    assert (applied.target_id, applied.status_id, applied.duration) == (U2, "revealed", 2)
    foe = result.state.units[U2]
    assert not foe.has_status("concealed") and not is_concealed(result.state, foe)
    assert of(result, AttackRolled) == []  # 自動命中：不擲命中


def test_a_revealed_unit_cannot_hide_again() -> None:
    state = _reveal_state()
    revealed = cast(state, target_pos=Pos(x=5, y=3)).state
    ctx = Ctx(revealed)
    execute(ctx, [ApplyStatusEffect(target_id=U2, status_id="concealed", duration=3)])
    assert not revealed.units[U2].has_status("concealed")
    fizzled = [e for e in ctx.events if isinstance(e, EffectFizzled)]
    assert [(e.effect_kind, e.reason) for e in fizzled] == [("apply_status", "revealed")]


def test_reveal_beats_darkness() -> None:
    state = _reveal_state(surfaces=((5, 3, "darkness"),))
    assert is_concealed(state, state.units[U2])  # 站在黑暗中
    revealed = cast(state, target_pos=Pos(x=5, y=3)).state
    assert not is_concealed(revealed, revealed.units[U2])


def test_a_unit_without_the_revealed_status_can_hide_again() -> None:
    state = _reveal_state()
    revealed = cast(state, target_pos=Pos(x=5, y=3)).state
    foe = revealed.units[U2]
    assert prevents_concealment(revealed.ruleset, foe)
    foe.statuses = []
    assert not prevents_concealment(revealed.ruleset, foe)


def _enemy_trap(xy: tuple[int, int]) -> TrapState:
    return TrapState(
        owner_id=U3,
        team=Team.ENEMY,
        pos=Pos(x=xy[0], y=xy[1]),
        skill_id="skill_bear_trap",
        remaining=3,
        attributes=tuple((a, 10) for a in Attribute),
    )


def test_reveal_shows_enemy_traps_in_the_area_to_the_caster_team() -> None:
    state = _reveal_state(foes=[(6, 6), (1, 1)])
    state.traps = [_enemy_trap((5, 3)), _enemy_trap((1, 5))]
    assert visible_traps(state, Team.ALLY) == []
    result = cast(state, target_pos=Pos(x=5, y=3))
    (event,) = of(result, TrapRevealed)
    assert (event.unit_id, event.team, event.pos) == (U1, Team.ALLY, Pos(x=5, y=3))
    seen = visible_traps(result.state, Team.ALLY)
    assert [t.xy for t in seen] == [(5, 3)]  # 範圍外的陷阱沒有被揭露
    assert own_traps(result.state, Team.ALLY) == []  # 不算我方自己放的
    assert [t.xy for t in visible_traps(result.state, Team.ENEMY)] == [(5, 3), (1, 5)]
    view = project_for(result.state, Team.ALLY)
    assert [(t.pos.x, t.pos.y) for t in view.traps] == [(5, 3)]
    assert project_for(state, Team.ALLY).traps == ()


def test_the_trap_reveal_event_is_only_for_the_revealing_team() -> None:
    state = _reveal_state(foes=[(6, 6), (1, 1)])
    state.traps = [_enemy_trap((5, 3))]
    result = cast(state, target_pos=Pos(x=5, y=3))
    (event,) = of(result, TrapRevealed)
    assert event_visible_to(event, result.state, Team.ALLY)
    assert not event_visible_to(event, result.state, Team.ENEMY)


def test_own_traps_are_not_revealed_and_a_trap_is_revealed_only_once() -> None:
    state = _reveal_state(foes=[(6, 6), (1, 1)])
    mine = _enemy_trap((4, 3))
    state.traps = [TrapState(U1, Team.ALLY, mine.pos, mine.skill_id, 3, mine.attributes)]
    assert of(cast(state, target_pos=Pos(x=5, y=3)), TrapRevealed) == []
    state = _reveal_state(foes=[(6, 6), (1, 1)])
    state.traps = [_enemy_trap((5, 3))]
    once = cast(state, target_pos=Pos(x=5, y=3)).state
    once.units[U1].ap = 3
    assert of(cast(once, target_pos=Pos(x=5, y=3)), TrapRevealed) == []


def test_reveal_with_nothing_to_find_fizzles() -> None:
    state = _reveal_state(foes=[(1, 6)])
    result = cast(state, target_pos=Pos(x=5, y=3))
    (fizzled,) = of(result, EffectFizzled)
    assert (fizzled.effect_kind, fizzled.reason) == ("reveal", "nothing_hidden")


def test_reveal_schema_and_budget() -> None:
    assert _problems(spell(SQUARE, REVEAL, skeleton="control")) == []
    assert any("缺少必要參數" in p for p in _problems(spell(SQUARE, {"type": "reveal"})))
    assert any("必須在 1–3" in p for p in _problems(spell(SQUARE, {**REVEAL, "duration": 4})))
    lib = library()
    points = skill_budget(spell(SQUARE, REVEAL, skeleton="control"), lib).effects[0].base
    assert points == lib.budget.reveal_base_points + lib.budget.reveal_round_points * 2


# ---------------------------------------------------------------------------
# 預覽、文字、示範技能與重播
# ---------------------------------------------------------------------------


def test_the_preview_shows_the_lifesteal_as_a_heal_of_the_caster() -> None:
    state = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    _wound(state, U1, 3)
    plan = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    (heal,) = [h for h in plan.healed if h[0] == U1]
    assert heal[1] < heal[2]  # 最少回復 < 最多回復


def test_the_preview_of_the_split_effect_lists_the_healed_allies() -> None:
    state = _burst_state()
    plan = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=5, y=3)))
    assert [t.unit_id for t in plan.targets] == [U3]
    assert [h[0] for h in plan.healed] == [U2]


def test_skill_cards_and_log_lines_describe_the_new_mechanics() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_life_drain"])
    assert any("吸血：你回復造成傷害的 40%" in e for e in card.effects)
    card = skill_card(lib, lib.skills["skill_holy_burst"])
    assert any("友方（含自己）改為治療同樣的骰值" in e for e in card.effects)
    texts = {
        "skill_dispel_magic": "驅散目標身上的全部增益",
        "skill_flare_sight": "揭露範圍內的敵人",
    }
    for skill_id, text in texts.items():
        skill = lib.skills[skill_id]
        assert text in effect_summary(lib, skill, skill.effects[0])


def test_the_battle_log_text_marks_lifesteal_dispel_and_revealed_traps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drained = battle(spell(SINGLE5, drain(500, "1d10")), [(5, 3)])
    _wound(drained, U1, 3)
    dispelled = _dispel_state(DISPEL_ALL, [StatusInstance("guarded", 3)])
    trapped = _reveal_state(foes=[(6, 6), (1, 1)])
    trapped.traps = [_enemy_trap((5, 3))]
    script_randint(monkeypatch, [19, 10, 19])
    result = cast(drained, target_id=U2)
    (heal,) = of(result, Healed)
    assert "（吸血）" in (describe_event(heal, result.state) or "")
    result = cast(dispelled, target_id=U2)
    (removed,) = of(result, StatusRemoved)
    assert "被驅散了" in (describe_event(removed, result.state) or "")
    result = cast(trapped, target_pos=Pos(x=5, y=3))
    (event,) = of(result, TrapRevealed)
    assert "揭露了 (5, 3) 的敵方陷阱" in (describe_event(event, result.state) or "")


def test_the_ai_dispels_and_reveals_only_when_there_is_something_to_gain() -> None:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415

    ai = UtilityAI(library().ai_profiles)

    def picks_the_skill(state: BattleState) -> bool:
        action = ai(state)
        return isinstance(action, UseSkill) and action.skill_id == SID

    buffed = _dispel_state(DISPEL_ALL, [StatusInstance("guarded", 3)])
    assert picks_the_skill(buffed) and not picks_the_skill(_dispel_state(DISPEL_ALL, []))
    hidden = _reveal_state()
    hidden.units[U2].statuses = [StatusInstance("concealed", 4)]
    assert picks_the_skill(hidden) and not picks_the_skill(_reveal_state())


DEMOS = {
    "skill_life_drain": ("build_support", "lifesteal_permille"),
    "skill_holy_burst": ("build_healer", "split_heal"),
    "skill_dispel_magic": ("build_seer", "dispel"),
    "skill_flare_sight": ("build_seer", "reveal"),
}


@pytest.mark.parametrize("skill_id", sorted(DEMOS))
def test_the_demo_skills_are_valid_in_budget_and_equipped(skill_id: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
    build_id, marker = DEMOS[skill_id]
    assert skill_id in lib.builds.by_id()[build_id].hero.skills
    used = {e.type for e in skill.effects} | {n for e in skill.effects for n in e.param_values()}
    assert marker in used


@pytest.mark.parametrize("build", ["build_support", "build_healer", "build_seer"])
def test_a_battle_with_the_new_builds_replays_exactly(build: str) -> None:
    from tests.engine.test_zone_ai import _run  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run(build, "open_plain", 4)
    again = replay(setup, 4, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


def test_the_state_round_trips_with_a_revealed_trap() -> None:
    from trpg.engine import state_from_json  # noqa: PLC0415

    state = _reveal_state(foes=[(6, 6), (1, 1)])
    state.traps = [_enemy_trap((5, 3))]
    result = cast(state, target_pos=Pos(x=5, y=3)).state
    again = state_from_json(state_to_json(result))
    assert again.traps[0].revealed_to == (Team.ALLY,)
    assert state_to_json(again) == state_to_json(result)
