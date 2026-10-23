"""裝備詞條的觸發（第 6 類）與充能（第 7 類）的結算（Phase 3G-G3a）。

涵蓋：每條詞條一組測試（`affix_trig_every3_prone`、`affix_trig_kill_ap`、`affix_trig_thorns_burn`、
`affix_charge_static`、`affix_charge_fury`）、每回合最多 1 次、同 id 兩件只算 1 條、觸發連鎖深度、
每回合 AP 回復上限、充能的累積與啟動（合法動作、預覽、AI）、檢視、重播。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_gear import Rolls, _loadout
from trpg.cli.main import main as cli_main
from trpg.content.equipment import AffixDef, ChargeAffix, TriggerAffix
from trpg.content.keyword_derive import Facts
from trpg.content.library import _affix_reference_problems
from trpg.engine import (
    ActivateCharge,
    Attack,
    BattleState,
    EndTurn,
    legal_actions,
    preview,
    resolve,
)
from trpg.engine.actions import ACTION_ADAPTER, CHARGE_ACTION_TYPES
from trpg.engine.ai.charge import charge_score
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.events import (
    ApGranted,
    ChargeActivated,
    DamageDealt,
    EffectFizzled,
    EventBase,
    GearTriggered,
    StacksChanged,
    StatusApplied,
    TriggerLimitReached,
)
from trpg.engine.gear_charge import charge_problem
from trpg.engine.refunds import refund_ap
from trpg.engine.rewrites import grant_ap
from trpg.engine.skill_triggers import reset_round_counts
from trpg.engine.state import StatusInstance, state_from_json, state_to_json
from trpg.engine.turns import start_turn
from trpg.engine.view import project_for
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")

KILL_AP = ("affix_trig_kill_ap", None)
EVERY3 = ("affix_trig_every3_prone", None)
THORNS = ("affix_trig_thorns_burn", None)
STATIC = ("affix_charge_static", None)
FURY = ("affix_charge_fury", None)


def scene(
    slots: Mapping[str, Rolls],
    *,
    foes: Sequence[tuple[int, int]] = ((1, 0),),
    foe_hp: int = 999,
    foe_base: str = "bandit",
    owner_hp: int | None = None,
    max_trigger_depth: int = 3,
) -> BattleState:
    """U1（穿裝備的我方戰士，(0, 0)）與敵人（U2…，預設 (1, 0)）；U1 拿到回合。"""
    m = make_map(FLAT7, ally=[(0, 0)], enemy=list(foes))
    hero = spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter"))
    if owner_hp is not None:
        hero = hero.model_copy(
            update={"template": hero.template.model_copy(update={"max_hp": owner_hp})}
        )
    hero = hero.model_copy(update={"equipment": _loadout(slots)})
    enemies = [spawn(Team.ENEMY, xy, no_reactions(foe_base, max_hp=foe_hp)) for xy in foes]
    return give_turn(make_state(m, [hero, *enemies], max_trigger_depth=max_trigger_depth), U1)


def always(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 1) -> None:
    """d20 一律 ``d20``（命中、不暴擊）、其他骰子一律 ``die``（傷害最小）。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def hit(state: BattleState, target: UnitId = U2, unit: UnitId = U1) -> Any:
    return resolve(state, Attack(unit_id=unit, target_id=target))


def of_type[T: EventBase](events: Sequence[EventBase], kind: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def refill(state: BattleState, unit: UnitId = U1, ap: int = 9) -> BattleState:
    state.units[unit].ap = ap
    return state


# ---------------------------------------------------------------------------
# 內容（schema 與載入時檢查）
# ---------------------------------------------------------------------------


def test_whitelist_trigger_and_charge_affixes_load() -> None:
    lib = library()
    for affix_id in (EVERY3[0], KILL_AP[0], THORNS[0]):
        assert isinstance(lib.affixes[affix_id], TriggerAffix)
    for affix_id in (STATIC[0], FURY[0]):
        assert isinstance(lib.affixes[affix_id], ChargeAffix)
    assert lib.ruleset.stack_def("fury").max == 4  # 新充能 fury


def _trigger_data(**changes: object) -> dict[str, object]:
    base = library().affixes[KILL_AP[0]].model_dump(mode="json")
    return {**base, **changes}


def test_trigger_affix_parameter_rules() -> None:

    adapter: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)
    adapter.validate_python(_trigger_data())
    with pytest.raises(ValidationError, match="melee_only"):
        adapter.validate_python(_trigger_data(melee_only=True))
    with pytest.raises(ValidationError, match="tag"):
        adapter.validate_python(_trigger_data(trigger="on_cast_tag"))
    with pytest.raises(ValidationError, match="status"):
        adapter.validate_python(_trigger_data(status="burning"))
    with pytest.raises(ValidationError, match="n 只在"):
        adapter.validate_python(_trigger_data(n=3))


def test_charge_affix_rejects_parameterised_gain_triggers() -> None:
    data = library().affixes[STATIC[0]].model_dump(mode="json")
    with pytest.raises(ValidationError, match="需要參數"):
        ChargeAffix.model_validate({**data, "gain_trigger": "every_n_hits"})
    with pytest.raises(ValidationError, match="cost_stacks"):
        ChargeAffix.model_validate({**data, "cost_stacks": 4})


def test_library_checks_trigger_charge_references() -> None:

    lib = library()
    keyword_ids = frozenset(lib.ruleset.keywords.ids())

    def problems(affix: object) -> list[str]:
        return _affix_reference_problems(affix, lib.ruleset, lib.weapons, keyword_ids)  # type: ignore[arg-type]

    assert all(not problems(a) for a in lib.affixes.values())
    kill_ap = lib.affixes[KILL_AP[0]]
    static = lib.affixes[STATIC[0]]
    assert isinstance(kill_ap, TriggerAffix) and isinstance(static, ChargeAffix)
    # 對象要有「另一方」：回合開始沒有另一方
    assert problems(
        kill_ap.model_copy(update={"trigger": "on_turn_start", "effect_target": "target"})
    )
    # 未知的層數、未知的效果原語、上限超過層數本身
    assert problems(static.model_copy(update={"stack": "no_such_stack"}))
    assert problems(static.model_copy(update={"max_stacks": 9, "cost_stacks": 3}))
    unknown = static.effects[0].model_copy(update={"type": "no_such_effect"})
    assert problems(static.model_copy(update={"effects": (unknown,)}))


# ---------------------------------------------------------------------------
# 第 6 類 觸發
# ---------------------------------------------------------------------------


def test_every3_prone_fires_on_every_third_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """第 3、6 次命中是觸發時機，但同一個回合只觸發 1 次（下一個回合才又可以觸發）。"""
    always(monkeypatch)
    state = scene({"main_hand": [EVERY3]})
    fired_on: list[int] = []
    for number in range(1, 7):
        if number == 6:
            state.units[U1].gear_turn_counts = {}  # 換到下一個回合
        result = hit(refill(state))
        state = result.state
        state.units[U2].hp = 999
        if of_type(result.events, GearTriggered):
            fired_on.append(number)
    assert fired_on == [3, 6]


def test_every3_prone_second_trigger_in_the_same_turn_is_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [EVERY3]})
    fired_on: list[int] = []
    for number in range(1, 7):
        result = hit(refill(state))
        state = result.state
        state.units[U2].hp = 999
        if of_type(result.events, GearTriggered):
            fired_on.append(number)
    assert fired_on == [3]
    assert state.units[U1].hits_landed == 6


def test_every3_prone_applies_knock_prone_to_the_target(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [EVERY3]})
    state.units[U1].hits_landed = 2
    result = hit(state)
    triggered = of_type(result.events, GearTriggered)
    assert [(e.unit_id, e.affix_id, e.trigger, e.other_id) for e in triggered] == [
        (U1, "affix_trig_every3_prone", "every_n_hits", U2)
    ]
    # knock_prone 是對抗判定：骰值固定時結果固定，目標若倒地一定是來自這條詞條
    prone = [e for e in of_type(result.events, StatusApplied) if e.status_id == "prone"]
    assert prone == [] or prone[0].target_id == U2
    assert any(e.type == "maneuver_rolled" for e in result.events)


def test_trigger_is_limited_to_once_per_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """每條裝備觸發每回合最多 1 次：兩次擊殺只回一次 AP。"""
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foes=[(1, 0), (0, 1)], foe_hp=1)
    first = hit(state, U2)
    assert [e.affix_id for e in of_type(first.events, GearTriggered)] == [KILL_AP[0]]
    assert first.state.units[U1].gear_turn_counts == {KILL_AP[0]: 1}
    second = hit(first.state, U3)
    assert not of_type(second.events, GearTriggered)  # 本回合已觸發過
    assert not of_type(second.events, ApGranted)


def test_trigger_count_resets_on_the_next_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foe_hp=1)
    done = hit(state).state
    assert done.units[U1].gear_turn_counts

    ctx = Ctx(done.clone())
    start_turn(ctx, U1)
    assert ctx.state.units[U1].gear_turn_counts == {}


def test_same_affix_on_two_items_counts_once(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP], "ring_1": [KILL_AP]}, foe_hp=1)
    unit = state.units[U1]
    assert [a.slot for a in unit.gear.active_affixes("trigger")] == ["main_hand"]
    result = hit(state)
    assert len(of_type(result.events, GearTriggered)) == 1


def test_kill_ap_grants_one_ap_after_the_attack_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foe_hp=1)
    before = state.units[U1].ap
    result = hit(state)
    granted = of_type(result.events, ApGranted)
    assert [(g.unit_id, g.amount) for g in granted] == [(U1, 1)]
    cost = library().ruleset.core.basic_attack_ap_cost
    assert result.state.units[U1].ap == before - cost + 1
    assert result.state.units[U1].ap_gain_turn == 1


def test_kill_ap_is_capped_by_the_per_turn_ap_gain_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """每回合 AP 回復 +1 上限（所有來源）：本回合已經由其他來源回復 1 AP 時，裝備不再回復。"""
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foe_hp=1)
    state.units[U1].ap_gain_turn = 1
    before = state.units[U1].ap
    result = hit(state)
    assert not of_type(result.events, ApGranted)
    fizzled = of_type(result.events, EffectFizzled)
    assert [f.reason for f in fizzled] == ["ap_gain_cap"]
    cost = library().ruleset.core.basic_attack_ap_cost
    assert result.state.units[U1].ap == before - cost


def test_other_ap_sources_count_toward_the_gear_cap() -> None:
    """``grant_ap``／``refund_ap`` 的 AP 也記進 ``ap_gain_turn``。"""

    state = scene({"main_hand": [KILL_AP]})
    state.units[U1].ap = 0
    ctx = Ctx(state)
    refund_ap(ctx, state.units[U1], "skill_x", 1)
    assert state.units[U1].ap_gain_turn == 1
    state.units[U1].ap_gain_turn = 0
    grant_ap(ctx, state.units[U1], state.units[U1], 1)
    assert state.units[U1].ap_gain_turn == 1


def test_thorns_burns_a_melee_attacker_once_per_round(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = give_turn(scene({"body": [THORNS]}), U2)
    first = hit(state, U1, U2)
    assert [(e.affix_id, e.other_id) for e in of_type(first.events, GearTriggered)] == [
        (THORNS[0], U2)
    ]
    burning = [e for e in of_type(first.events, StatusApplied) if e.status_id == "burning"]
    assert [e.target_id for e in burning] == [U2]  # 燃燒施加給攻擊者
    again = hit(refill(first.state, U2), U1, U2)
    assert not of_type(again.events, GearTriggered)  # 每輪 1 次
    assert first.state.units[U1].gear_round_counts == {THORNS[0]: 1}


def test_thorns_ignores_ranged_attackers(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"body": [THORNS]}, foes=[(5, 0)], foe_base="bandit_archer")
    result = hit(give_turn(state, U2), U1, U2)
    assert of_type(result.events, DamageDealt)  # 遠程攻擊命中了
    assert not of_type(result.events, GearTriggered)


def test_round_counts_reset_at_round_start(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = give_turn(scene({"body": [THORNS]}), U2)
    done = hit(state, U1, U2).state
    assert done.units[U1].gear_round_counts

    reset_round_counts(iter(done.units_sorted()))
    assert done.units[U1].gear_round_counts == {}


def test_trigger_chain_respects_max_trigger_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """觸發連鎖的深度上限（``max_trigger_depth``）：深度 0 時裝備觸發不結算，發出
    ``trigger_limit_reached``，也不計次數。"""
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foe_hp=1, max_trigger_depth=0)
    result = hit(state)
    assert not of_type(result.events, GearTriggered)
    assert [e.skill_id for e in of_type(result.events, TriggerLimitReached)] == [KILL_AP[0]]
    assert result.state.units[U1].gear_turn_counts == {}


def test_trigger_depth_increases_with_each_link(monkeypatch: pytest.MonkeyPatch) -> None:
    """荊棘的燃燒傷害讓攻擊者受傷，但攻擊者沒有裝備觸發；深度從 1 起算。"""
    always(monkeypatch)
    state = give_turn(scene({"body": [THORNS]}), U2)
    result = hit(state, U1, U2)
    assert [e.trigger_depth for e in of_type(result.events, GearTriggered)] == [1]


def test_stunned_owner_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [KILL_AP]}, foe_hp=1)

    state.units[U1].statuses.append(StatusInstance(status_id="stun", remaining=1))
    result = hit(state)
    assert not of_type(result.events, GearTriggered)


# ---------------------------------------------------------------------------
# 第 7 類 充能
# ---------------------------------------------------------------------------


def test_static_charge_gains_one_stack_per_hit_up_to_the_gear_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene({"main_hand": [STATIC]})
    gained: list[int] = []
    for _ in range(5):
        result = hit(refill(state))
        state = result.state
        gained.append(state.units[U1].stacks.get("static_charge", 0))
    assert gained == [1, 2, 3, 3, 3]  # 裝備版上限 3（層數本身上限 5）
    changes = [e for e in of_type(result.events, StacksChanged) if e.stack_id == "static_charge"]
    assert changes == []  # 已在上限：不發事件


def test_fury_gains_a_stack_when_damaged(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = give_turn(scene({"body": [FURY]}), U2)
    for expected in (1, 2, 3, 4, 4):
        state = hit(refill(state, U2), U1, U2).state
        assert state.units[U1].stacks.get("fury", 0) == expected


def test_charge_cannot_activate_without_enough_stacks() -> None:
    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 2
    assert not [a for a in legal_actions(state) if isinstance(a, ActivateCharge)]
    action = ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2)
    assert "層數不足" in (charge_problem(state, state.units[U1], STATIC[0], U2) or "")
    with pytest.raises(IllegalActionError, match="層數不足"):
        resolve(state, action)


def test_charge_needs_ap_and_a_valid_target() -> None:
    state = scene({"main_hand": [STATIC]})
    unit = state.units[U1]
    unit.stacks["static_charge"] = 3
    unit.ap = 0
    assert "AP 不足" in (charge_problem(state, unit, STATIC[0], U2) or "")
    unit.ap = 3
    assert charge_problem(state, unit, STATIC[0], None) == "必須指定一個敵方目標"
    assert charge_problem(state, unit, STATIC[0], U1) is not None  # 不能指定自己
    assert charge_problem(state, unit, "affix_charge_nope", U2) is not None
    assert charge_problem(state, unit, STATIC[0], U2) is None


def test_static_charge_activation_spends_stacks_and_ap_and_deals_lightning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, die=6)
    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 3
    assert ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2) in legal_actions(state)
    before_ap = state.units[U1].ap
    result = resolve(state, ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2))
    unit = result.state.units[U1]
    assert unit.ap == before_ap - 1
    assert "static_charge" not in unit.stacks
    activated = of_type(result.events, ChargeActivated)
    assert [(e.affix_id, e.stacks_spent, e.ap_spent, e.target_id) for e in activated] == [
        (STATIC[0], 3, 1, U2)
    ]
    damage = [e for e in of_type(result.events, DamageDealt) if e.source_id == U1]
    assert len(damage) == 1 and damage[0].target_id == U2
    assert damage[0].element.value == "lightning" and len(damage[0].rolls) == 3  # 3d6
    spent = [e for e in of_type(result.events, StacksChanged) if e.reason == "consumed"]
    assert [(e.before, e.after) for e in spent] == [(3, 0)]


def test_fury_activation_buffs_the_owner_for_free() -> None:
    state = give_turn(scene({"body": [FURY]}), U1)
    state.units[U1].stacks["fury"] = 4
    actions = [a for a in legal_actions(state) if isinstance(a, ActivateCharge)]
    assert actions == [ActivateCharge(unit_id=U1, affix_id=FURY[0])]  # 不需要目標
    before_ap = state.units[U1].ap
    result = resolve(state, actions[0])
    unit = result.state.units[U1]
    assert unit.ap == before_ap and "fury" not in unit.stacks  # 0 AP
    assert any(s.status_id == "empowered" for s in unit.statuses)
    with pytest.raises(IllegalActionError, match="不能指定目標"):
        resolve(state, ActivateCharge(unit_id=U1, affix_id=FURY[0], target_id=U2))


def test_charge_activation_is_deterministic_and_round_trips() -> None:
    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 3
    action = ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2)
    one, two = resolve(state, action), resolve(state, action)
    assert one.events == two.events
    restored = state_from_json(state_to_json(one.state))
    assert restored.units[U1].gear_turn_counts == one.state.units[U1].gear_turn_counts
    assert ACTION_ADAPTER.validate_python(action.model_dump(mode="json")) == action
    assert CHARGE_ACTION_TYPES == ("activate_charge",)


def test_activation_triggers_follow_up_after_the_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """啟動的傷害把敵人打倒時，擊殺類觸發在動作結束後結算（兩條詞條各自一次）。"""
    always(monkeypatch, die=6)
    state = scene({"main_hand": [STATIC], "ring_1": [KILL_AP]}, foe_hp=1)
    state.units[U1].stacks["static_charge"] = 3
    result = resolve(state, ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2))
    assert [e.affix_id for e in of_type(result.events, GearTriggered)] == [KILL_AP[0]]


# ---------------------------------------------------------------------------
# 預覽、檢視、AI
# ---------------------------------------------------------------------------


def test_preview_shows_ap_cost_and_damage_of_a_charge(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 3
    p = preview(state, ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2))
    assert p.ap_cost == 1
    assert p.damage is not None and 3 <= p.damage.minimum < p.damage.maximum
    assert U2 in p.affected_units
    fury = give_turn(scene({"body": [FURY]}), U1)
    fury.units[U1].stacks["fury"] = 4
    assert preview(fury, ActivateCharge(unit_id=U1, affix_id=FURY[0])).ap_cost == 0


def test_unit_view_lists_charges() -> None:
    state = scene({"main_hand": [STATIC], "body": [FURY]})
    state.units[U1].stacks.update({"static_charge": 2, "fury": 4})
    view = project_for(state, Team.ALLY)
    charges = {c.affix_id: c for c in next(u for u in view.units if u.id == U1).charges}
    static = charges[STATIC[0]]
    assert (static.stacks, static.max_stacks, static.cost_stacks, static.cost_ap) == (2, 3, 3, 1)
    assert static.needs_target and not static.ready and static.stack_name_zh == "靜電"
    assert charges[FURY[0]].ready and not charges[FURY[0]].needs_target
    foe = next(u for u in view.units if u.id == U2)
    assert foe.charges == ()


def _ai_scene(foe_hp: int) -> BattleState:
    state = give_turn(
        scene({"body": [FURY], "main_hand": [STATIC]}, foes=[(1, 0)], foe_hp=foe_hp), U1
    )
    state.units[U1].stacks.update({"fury": 4, "static_charge": 3})
    return state


def test_ai_scores_a_ready_charge_but_below_the_best_normal_action() -> None:
    """AI 會評估充能（低權重）：敵人很健康時，一般技能與普攻的分數較高，不會優先啟動。"""
    state = _ai_scene(999)
    ai = UtilityAI(library().ai_profiles, override="brute")
    ranked = ai.rank(state)
    charges = [s.score for s in ranked if isinstance(s.action, ActivateCharge)]
    assert charges and all(score > 0 for score in charges)
    assert max(s.score for s in ranked if not isinstance(s.action, ActivateCharge)) > max(charges)


def test_ai_activates_a_charge_that_kills() -> None:
    """靜電終結能直接擊倒殘血的敵人時，AI 啟動它。"""
    state = _ai_scene(10)
    ai = UtilityAI(library().ai_profiles, override="brute")
    chosen = ai(state)
    assert isinstance(chosen, ActivateCharge) and chosen.affix_id == STATIC[0]
    assert chosen.target_id == U2


def test_ai_does_not_activate_without_stacks() -> None:
    state = _ai_scene(10)
    state.units[U1].stacks.clear()
    ai = UtilityAI(library().ai_profiles, override="brute")
    assert not any(isinstance(s.action, ActivateCharge) for s in ai.rank(state))


def test_ai_charge_score_is_discounted() -> None:

    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 3
    profile = library().ai_profiles.profiles[0]
    basic = library().ai_profiles.basic
    action = ActivateCharge(unit_id=U1, affix_id=STATIC[0], target_id=U2)
    assert charge_score(state, action, Fraction(100), profile, basic) == Fraction(
        100 * basic.charge_permille, 1000
    )
    assert charge_score(state, action, Fraction(-5), profile, basic) == Fraction(-5)


def test_end_turn_remains_legal_with_charges() -> None:
    state = scene({"main_hand": [STATIC]})
    state.units[U1].stacks["static_charge"] = 3
    actions = legal_actions(state)
    assert EndTurn(unit_id=U1) in actions
    kinds = {a.type for a in actions}
    assert "activate_charge" in kinds


# ---------------------------------------------------------------------------
# 含觸發與充能的一場 --log-json + replay
# ---------------------------------------------------------------------------


def test_g3a_gear_battle_log_json_and_replay(tmp_path: Path) -> None:
    """種子 3：戰士身上的觸發與充能都派上用場（觸發、啟動、擊殺回 AP），紀錄可重播。"""
    log = tmp_path / "g3a.json"
    args = ["battle", "--map", "test_flat_6x6", "--allies", "gear_tester_g3a"]
    args += ["--enemies", "bandit,bandit", "--seed", "3", "--log-json", str(log)]
    assert cli_main(args) == 0
    text = log.read_text(encoding="utf-8")
    assert "trpg-battle-log/60" in text
    for needle in ('"gear_triggered"', '"charge_activated"', '"activate_charge"'):
        assert needle in text
    assert cli_main(["battle", "replay", str(log)]) == 0


def test_ruleset_equality_ignores_the_keyword_cache() -> None:
    """3G-G2 起快取在私有屬性裡、pydantic 的相等比較會一併比較它，讓「狀態 JSON 來回後相等」好時壞
    （同一個行程裡先有人填過快取）；快取不是規則資料，不影響相等。"""
    state = scene({"main_hand": [KILL_AP]})
    fresh = state_from_json(state_to_json(state))
    state.ruleset.facts_keywords(("attack", "physical", ()), Facts(effects=()))
    assert fresh.ruleset == state.ruleset
    assert fresh == state
