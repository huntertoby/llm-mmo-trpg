"""第二批提前的主武器（Phase 3I-1，``docs/phases/Phase3I計畫.md``；08 8.11，玩法決定 #46）。

拳套（體質／敏捷取較高，反擊）、鐮刀（意志／力量取平均，收割）、鞭（敏捷／感知取平均，射程 2，
纏繞）；錘改取較高。行為一致測試：每把新武器 × 屬性組合實際跑普攻與武器技，``damage_dealt``
的骰外加成等於卡片的「目前 +N」；反擊、收割、纏繞各一組引擎表格測試。
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with, of
from tests.engine.test_weapons_24a1 import U1, U2, armed, dice, hit, kinds, state_of, weapon
from trpg.content.battle import WeaponDef
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, EndTurn, SetReactionMode, resolve
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ReactionTriggered,
    StatusApplied,
    StatusRemoved,
    StatusSaveRolled,
)
from trpg.engine.lifecycle import weapon_reaction_rules
from trpg.engine.modifiers import ATTACK, reap_permille, skill_use
from trpg.engine.rules.statuses import effective_attribute, move_points_for_turn
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import StatusInstance, UnitState
from trpg.shared.bonus_text import plain_text
from trpg.shared.types import Attribute, Team

FIRE = {"type": "damage", "dice": "1d4", "element": "fire"}


# ---------------------------------------------------------------------------
# 資料與雙屬性取法
# ---------------------------------------------------------------------------


def test_the_new_weapons_are_data_with_the_designed_parameters() -> None:
    w = library().weapons
    fist, scythe, whip = w["fist"], w["scythe"], w["whip"]
    assert (fist.weapon_class, fist.range, fist.two_handed, fist.counter) == (
        "melee",
        1,
        True,
        True,
    )
    assert (fist.scaling_attr, fist.secondary_scaling_attr, fist.attr_mode) == ("con", "dex", "max")
    assert (scythe.range, scythe.two_handed) == (1, True)
    assert (scythe.scaling_attr, scythe.secondary_scaling_attr, scythe.attr_mode) == (
        "wil",
        "str",
        "mean",
    )
    assert scythe.reap is not None
    assert (scythe.reap.hp_permille, scythe.reap.damage_permille) == (300, 250)
    assert (whip.range, whip.reach, whip.two_handed) == (2, 1, False)
    assert (whip.scaling_attr, whip.secondary_scaling_attr, whip.attr_mode) == (
        "dex",
        "wis",
        "mean",
    )
    assert whip.entangle is not None and whip.entangle.move_penalty == 2
    for wid, kind in (("fist", "fist"), ("scythe", "scythe"), ("whip", "whip")):
        look = w[wid].look
        assert look is not None and look.kind == kind and look.form and look.material


def test_every_dual_attribute_weapon_follows_the_same_class_or_mixed_rule() -> None:
    """全武器表核對（#46）：同類（都是物理或都是心智）取較高、一物理一心智取平均。"""
    checked = []
    for w in library().weapons.values():
        if w.secondary_scaling_attr is None:
            continue
        same = w.scaling_attr.is_physical == w.secondary_scaling_attr.is_physical
        assert w.attr_mode == ("max" if same else "mean"), w.id
        checked.append(w.id)
    assert {"dagger", "hammer", "fist", "scythe", "whip"} <= set(checked)


def test_the_schema_rejects_a_dual_attribute_mode_against_the_rule() -> None:
    with pytest.raises(ValidationError, match="attr_mode"):
        weapon("hammer", attr_mode="mean")
    with pytest.raises(ValidationError, match="attr_mode"):
        weapon("scythe", attr_mode="max")


def test_every_attribute_has_a_main_weapon_now() -> None:
    """補平六屬性：除了智力（法杖）以外，每個屬性都有近戰主武器吃它（智力的魔導劍在 3I-3）。"""
    attrs: set[Attribute] = set()
    for w in library().weapons.values():
        if not w.summon_only:
            attrs.add(w.scaling_attr)
            if w.secondary_scaling_attr is not None:
                attrs.add(w.secondary_scaling_attr)
    assert attrs == set(Attribute)


def test_trait_lines_follow_the_data() -> None:
    assert weapon("fist").trait_lines_zh() == (
        "反擊：相鄰敵人的近戰攻擊命中你時，自動回擊一次（佔本輪反應，不花 AP 與耐力）",
    )
    assert weapon("scythe").trait_lines_zh() == ("收割：目標 HP ≤ 30% 時，普攻與武器技傷害 +25%",)
    assert weapon("scythe", reap={"hp_permille": 500, "damage_permille": 400}).trait_lines_zh() == (
        "收割：目標 HP ≤ 50% 時，普攻與武器技傷害 +40%",
    )
    line = "纏繞：普攻命中後，目標下回合移動 −2（不疊加、不擲抵抗）"
    assert weapon("whip").trait_lines_zh() == (line,)
    assert weapon("whip").trait_lines_zh(on_hit_only=True) == (line,)
    assert weapon("fist").trait_lines_zh(on_hit_only=True) == ()


# ---------------------------------------------------------------------------
# 行為一致：普攻與武器技的骰外加成＝卡片「目前 +N」
# ---------------------------------------------------------------------------

ATTR_TABLE: list[tuple[str, dict[str, int]]] = [
    ("fist", {"con": 20, "dex": 10}),  # 取較高：體質 20
    ("fist", {"con": 9, "dex": 17}),  # 取較高：敏捷 17
    ("scythe", {"wil": 30, "str": 10}),  # 取平均 20
    ("scythe", {"wil": 11, "str": 16}),  # 取平均 13
    ("whip", {"dex": 16, "wis": 4}),  # 取平均 10
    ("whip", {"dex": 13, "wis": 18}),  # 取平均 15
    ("hammer", {"con": 10, "str": 20}),  # 取較高：力量 20（3I-1）
    ("hammer", {"con": 18, "str": 11}),
]

_CURRENT = re.compile(r"目前 \+(\d+)")


def _current(line: str) -> int:
    found = _CURRENT.search(plain_text(line))
    assert found is not None, line
    return int(found.group(1))


def _getter(state: BattleState, unit: UnitState) -> Any:
    return lambda a: effective_attribute(state.ruleset, unit, a)


def _attack_state(weapon_id: str, attrs: dict[str, int]) -> BattleState:
    foe_x = 2 + library().weapons[weapon_id].range
    return state_of(
        [
            armed(Team.ALLY, (2, 2), weapon(weapon_id), attributes=attrs),
            armed(Team.ENEMY, (foe_x, 2), weapon("one_handed_sword"), base="bandit", resist={}),
        ]
    )


@pytest.mark.parametrize(("weapon_id", "attrs"), ATTR_TABLE)
def test_basic_attack_damage_matches_the_card_current_bonus(
    weapon_id: str, attrs: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = _attack_state(weapon_id, attrs)
    unit = state.units[U1]
    line = unit.weapon.attack_formula_zh(state.ruleset.core, _getter(state, unit))
    now = _current(line)
    (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == now
    if dealt.scaled_permille % 1000 == 0:  # 整數加成：傷害＝骰值＋目前加成
        assert dealt.amount == sum(dealt.rolls) + now


def _weapon_skill() -> SkillDef:
    base = make_skill(SID, {"type": "single", "range": 2}, [{"type": "damage"}], category="weapon")
    return SkillDef.model_validate({**base.model_dump(mode="json"), "weapon_req": "melee"})


@pytest.mark.parametrize(("weapon_id", "attrs"), ATTR_TABLE)
def test_weapon_skill_damage_matches_the_card_current_bonus(
    weapon_id: str, attrs: dict[str, int]
) -> None:
    skill = _weapon_skill()
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    unit = state.units[U1]
    unit.weapon = library().weapons[weapon_id]
    for name, value in attrs.items():
        unit.attributes[Attribute(name)] = value
    lines = skill.formula_lines_zh(state.ruleset.core, unit.weapon, _getter(state, unit))
    damage_line = next(line for line in lines if "目前" in line)
    assert unit.weapon.scaling_names_zh() in damage_line
    result = cast(hit_with(state), target_id=U2)
    (dealt,) = [e for e in of(result, DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == _current(damage_line)


# ---------------------------------------------------------------------------
# 拳套：反擊
# ---------------------------------------------------------------------------


def _fist_state(
    attacker: WeaponDef | None = None, *, distance: int = 1, fist_hp: int = 200, **fist: Any
) -> BattleState:
    """敵人（U1，拿 ``attacker``，先行動）打拿拳套的我方（U2）。"""
    w = attacker if attacker is not None else weapon("one_handed_sword")
    return state_of(
        [
            armed(Team.ENEMY, (2, 2), w, base="bandit"),
            armed(Team.ALLY, (2 + distance, 2), weapon("fist", **fist), max_hp=fist_hp),
        ]
    )


def _countered(events: list[Any]) -> bool:
    return any(e.reaction == "counter_attack" for e in kinds(events, ReactionTriggered))


COUNTER_TABLE = [
    # (說明, 攻擊者武器, 距離, d20, 拳套 HP, 期望反擊)
    ("相鄰近戰命中", "one_handed_sword", 1, 19, 200, True),
    ("相鄰近戰失手", "one_handed_sword", 1, 1, 200, False),
    ("矛隔 1 格命中（不相鄰）", "spear", 2, 19, 200, False),
    ("鞭隔 1 格命中（不相鄰）", "whip", 2, 19, 200, False),
    ("相鄰的遠程攻擊", "bow", 1, 19, 200, False),
    ("被打倒", "one_handed_sword", 1, 19, 1, False),
]


@pytest.mark.parametrize("row", COUNTER_TABLE, ids=[row[0] for row in COUNTER_TABLE])
def test_counter_fires_only_on_an_adjacent_melee_hit_that_leaves_you_standing(
    row: tuple[str, str, int, int, int, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    label, attacker, distance, d20, hp, expected = row
    dice(monkeypatch, d20=d20)
    state = _fist_state(weapon(attacker), distance=distance, fist_hp=hp)
    assert _countered(hit(state)) is expected, label


def test_counter_is_a_free_basic_attack_that_uses_the_reaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = _fist_state()
    before = state.units[U2]
    ap, stamina = before.ap, before.stamina
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (triggered,) = [e for e in kinds(result.events, ReactionTriggered)]
    assert (triggered.unit_id, triggered.trigger_unit_id, triggered.stamina_spent) == (U2, U1, 0)
    rolls = kinds(result.events, AttackRolled)
    assert [(r.attacker_id, r.target_id) for r in rolls] == [(U1, U2), (U2, U1)]
    assert any(e.source_id == U2 and e.target_id == U1 for e in kinds(result.events, DamageDealt))
    after = result.state.units[U2]
    assert (after.ap, after.stamina) == (ap, stamina)
    assert after.reactions_used == 1
    # 本輪的反應已用掉：第二次被打不再反擊
    again = resolve(result.state, Attack(unit_id=U1, target_id=U2))
    assert not _countered(again.events)


def test_a_weapon_without_counter_never_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    assert not _countered(hit(_fist_state(counter=False)))


def test_the_counter_rule_can_be_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = _fist_state()
    rules = {r.reaction for r in state.units[U2].reactions}
    assert "counter_attack" in rules
    state.units[U2].reactions = tuple(
        r.model_copy(update={"mode": "off"}) if r.reaction == "counter_attack" else r
        for r in state.units[U2].reactions
    )
    assert not _countered(hit(state))


def test_the_player_can_switch_the_counter_rule_with_set_reaction_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = _fist_state()
    state.active_unit = U2
    state.turn_pos = state.turn_order.index(U2)
    off = resolve(state, SetReactionMode(unit_id=U2, reaction="counter_attack", mode="off")).state
    off.active_unit = U1
    off.turn_pos = off.turn_order.index(U1)
    off.units[U1].ap = off.ruleset.core.ap_per_turn
    assert not _countered(hit(off))


def test_default_rules_put_counter_first_and_switch_block_off() -> None:
    """預設規則（範本沒寫反應）：格擋在傷害前就會用掉唯一的反應，所以拳套的預設格擋為 off。"""
    lib = library()
    rules = lib.ruleset
    defaults = rules.reactions.default_rules
    fist = weapon_reaction_rules(lib.weapons["fist"], rules, defaults, defaults=True)
    assert fist[0].reaction == "counter_attack" and fist[0].mode == "auto"
    assert {r.reaction: r.mode for r in fist[1:]} == {"block": "off", "opportunity_attack": "auto"}
    written = weapon_reaction_rules(lib.weapons["fist"], rules, defaults, defaults=False)
    assert {r.reaction: r.mode for r in written[1:]} == {
        "block": "auto",
        "opportunity_attack": "auto",
    }
    assert weapon_reaction_rules(lib.weapons["dagger"], rules, defaults, defaults=True) == defaults


def test_counter_also_answers_an_adjacent_melee_weapon_skill() -> None:
    skill = make_skill(SID, {"type": "single", "range": 1}, [{"type": "damage"}], category="weapon")
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    foe = state.units[U2]
    foe.weapon = library().weapons["fist"]
    foe.reactions = weapon_reaction_rules(foe.weapon, state.ruleset, (), defaults=False)
    foe.hp = foe.max_hp = 500
    result = cast(hit_with(state, [(20, 19)]), target_id=U2)
    assert _countered(result.events)


# ---------------------------------------------------------------------------
# 鐮刀：收割
# ---------------------------------------------------------------------------


def _foe(hp: int, max_hp: int = 100) -> UnitState:
    state = _attack_state("scythe", {})
    unit = state.units[U2]
    unit.hp, unit.max_hp = hp, max_hp
    return unit


REAP_TABLE = [
    # (目標 HP／最大, 期望加成)
    (30, 250),  # 剛好 30%：觸發
    (1, 250),
    (31, 0),  # 30% 以上：不觸發
    (100, 0),
]


@pytest.mark.parametrize(("hp", "expected"), REAP_TABLE)
def test_reap_reads_the_current_hp(hp: int, expected: int) -> None:
    state = _attack_state("scythe", {})
    scythe = state.units[U1]
    target = _foe(hp)
    assert reap_permille(scythe, ATTACK, Subject(target, target.xy)) == expected


def test_reap_applies_to_basic_attacks_and_weapon_skills_only() -> None:
    state = _attack_state("scythe", {})
    scythe = state.units[U1]
    target = _foe(10)
    subject = Subject(target, target.xy)
    weapon_skill = make_skill(
        SID, {"type": "single", "range": 1}, [{"type": "damage"}], category="weapon"
    )
    spell = make_skill(SID, {"type": "single", "range": 1}, [FIRE], category="spell")
    assert reap_permille(scythe, skill_use(weapon_skill), subject) == 250
    assert reap_permille(scythe, skill_use(spell), subject) == 0
    assert reap_permille(scythe, ATTACK, Subject(None, target.xy)) == 0  # 物件
    scythe.weapon = library().weapons["one_handed_sword"]
    assert reap_permille(scythe, ATTACK, subject) == 0


def test_reap_raises_the_basic_attack_damage_by_a_quarter(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    amounts = {}
    for hp in (200, 60):  # 30% of 200 = 60
        state = _attack_state("scythe", {"wil": 20, "str": 20})
        state.units[U2].hp, state.units[U2].max_hp = hp, 200
        (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.source_id == U1]
        amounts[hp] = dealt.amount
    assert amounts[60] == amounts[200] * 1250 // 1000


def test_reap_counts_toward_the_whole_body_damage_bonus_cap() -> None:
    state = _attack_state("scythe", {})
    caps = state.ruleset.equipment.caps.damage_bonus_permille
    from trpg.engine.gear import cap_damage_bonus  # noqa: PLC0415

    assert cap_damage_bonus(state.ruleset, caps + 250) == caps


# ---------------------------------------------------------------------------
# 鞭：纏繞
# ---------------------------------------------------------------------------


def _whip_state(**changes: Any) -> BattleState:
    return state_of(
        [
            armed(Team.ALLY, (2, 2), weapon("whip", **changes)),
            armed(Team.ENEMY, (4, 2), weapon("one_handed_sword"), base="bandit"),
            armed(Team.ENEMY, (6, 4), weapon("one_handed_sword"), base="bandit"),
        ]
    )


def _entangles(events: list[Any]) -> list[StatusApplied]:
    return [e for e in kinds(events, StatusApplied) if e.status_id == "entangled"]


def test_whip_hit_entangles_without_a_save(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    result = resolve(_whip_state(), Attack(unit_id=U1, target_id=U2))
    (applied,) = _entangles(result.events)
    assert (applied.target_id, applied.duration, applied.refreshed) == (U2, 1, False)
    assert not kinds(result.events, StatusSaveRolled)
    status = result.state.units[U2].get_status("entangled")
    assert status is not None and status.amount == 2
    assert result.state.units[U2].xy == (4, 2)  # 不拉近


def test_whip_miss_does_not_entangle(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=1)
    assert not _entangles(hit(_whip_state()))


ENTANGLE_TABLE = [
    # (速度, 其他狀態, 纏繞量, 期望移動點數)
    (6, [], 2, 4),
    (1, [], 2, 0),  # 最低 0
    (6, [StatusInstance("slow", 2, None)], 2, 1),  # 緩速 ×50% 再 −2
    (6, [], 3, 3),  # 資料改數值跟著變
]


@pytest.mark.parametrize(("speed", "others", "amount", "expected"), ENTANGLE_TABLE)
def test_entangle_reduces_the_next_turn_move_points(
    speed: int, others: list[StatusInstance], amount: int, expected: int
) -> None:
    state = _whip_state()
    unit = state.units[U2]
    unit.speed = speed
    unit.statuses = sorted(
        [*others, StatusInstance("entangled", 1, U1, amount)], key=lambda s: s.status_id
    )
    assert move_points_for_turn(state.ruleset, unit) == expected


def test_entangle_refreshes_instead_of_stacking(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    first = resolve(_whip_state(), Attack(unit_id=U1, target_id=U2))
    second = resolve(first.state, Attack(unit_id=U1, target_id=U2))
    (applied,) = _entangles(second.events)
    assert applied.refreshed
    statuses = [s for s in second.state.units[U2].statuses if s.status_id == "entangled"]
    assert len(statuses) == 1 and statuses[0].amount == 2
    assert move_points_for_turn(second.state.ruleset, second.state.units[U2]) == max(
        0, second.state.units[U2].speed - 2
    )


def test_entangle_lasts_through_the_target_next_turn_only(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = resolve(_whip_state(), Attack(unit_id=U1, target_id=U2)).state
    foe = state.units[U2]
    foe.hp = foe.max_hp
    state.units[U1].hp = state.units[U1].max_hp = 999
    # 一直結束回合，直到 U2 的回合開始：移動點數 −2；它的回合結束後纏繞移除
    for _ in range(6):
        active = state.active_unit
        assert active is not None
        if active == U2:
            break
        state = resolve(state, EndTurn(unit_id=active)).state
    assert state.active_unit == U2
    assert state.units[U2].move_points == state.units[U2].speed - 2
    ended = resolve(state, EndTurn(unit_id=U2))
    assert any(
        e.status_id == "entangled" and e.target_id == U2 for e in kinds(ended.events, StatusRemoved)
    )


def test_entangle_applied_during_the_target_own_turn_waits_for_its_next_turn() -> None:
    """反應攻擊（例如藉機攻擊）在目標自己的回合命中：持續 2，下一個回合才作用。"""
    from trpg.engine.weapon_traits import entangle_effect  # noqa: PLC0415

    state = _whip_state()
    effect = entangle_effect(state, state.units[U1], state.units[U2], 2)
    assert (effect.duration, effect.amount) == (1, 2)
    state.active_unit = U2
    assert entangle_effect(state, state.units[U1], state.units[U2], 2).duration == 2


def test_the_entangled_status_card_names_the_weapon_amount() -> None:
    from trpg.narrative.status_info import status_rules  # noqa: PLC0415

    lib = library()
    lines = status_rules(lib.ruleset.status_def("entangled"), lib)
    assert any("鞭 −2" in line and "不擲抵抗" in line for line in lines)
    assert not any("抵抗：" in line for line in lines)
