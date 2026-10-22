"""普攻流（Phase 3-32a，08 8.25）：普攻精通、普攻連擊 ``affix_attack_combo``、分裂
``affix_attack_cleave``、四條武器特性強化、重複詞條的 ``duplicate_of``，與同種子確定。"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
)
from tests.engine.test_gear_g2 import Rolls, _spawn, _weapon_of
from trpg.content.equipment import AttackAffix, ItemDef, ValueRange, item_problems
from trpg.content.skills import ModifierSpec
from trpg.engine import Attack, BattleState, EndTurn, UseSkill, resolve, start_battle, weapon_traits
from trpg.engine import modifiers as mods
from trpg.engine.events import AttackRolled, DamageDealt, EventBase, GearTriggered
from trpg.engine.rules.combat import attack_problem, half_cover
from trpg.engine.runner import replay, run_battle
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import state_to_json
from trpg.engine.view import project_for
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
COMBO, CLEAVE = "affix_attack_combo", "affix_attack_cleave"
STILL = "affix_trait_longgun_still_crit"
MASTERY = "skill_attack_mastery"
# 六招近戰主動技（欄位上限 6 個主動技），用來把主動技能欄填到指定的空格數
ACTIVES = (
    "skill_bone_crusher",
    "skill_cleave",
    "skill_whirlwind",
    "skill_execute",
    "skill_shield_bash",
    "skill_gale_kick",
)


@pytest.fixture(autouse=True)
def _wide_combo_range() -> Iterator[None]:
    """內容的連擊詞條 N 只剩 3（3-32d）；引擎測試仍要驗證 N ＝ 2 的計數與「取較頻繁者」，
    所以測試期間把初值範圍放寬成 2～3（只換掉快取內容庫裡的詞條定義，結束後還原）。"""
    affixes = library().affixes
    original = affixes[COMBO]
    assert isinstance(original, AttackAffix)
    affixes[COMBO] = original.model_copy(update={"value": ValueRange(min=2, max=3)})
    yield
    affixes[COMBO] = original


class _Missed(Exception):
    """主要攻擊失手（換一個種子重來）。"""


def _fighting(
    slots: dict[str, Rolls],
    foes: Sequence[tuple[tuple[int, int], int]] = (((1, 0), 999),),
    *,
    skills: Sequence[str] = (),
    weapon: str | None = None,
    base: str = "hero_fighter",
    row: str = "0000\n0000",
    hero_xy: tuple[int, int] = (0, 0),
) -> BattleState:
    """U1 在 ``hero_xy``，``foes`` 是（座標，HP）：第一個是 U2（普攻的目標）。"""
    hero = _spawn(slots, base=base, weapon=weapon, skills=skills).model_copy(
        update={"position": hero_xy}
    )
    spawns = [hero] + [spawn(Team.ENEMY, xy, no_reactions("bandit")) for xy, _ in foes]
    m = make_map(row, ally=[hero_xy], enemy=[xy for xy, _ in foes])
    state = start_battle(make_setup(m, spawns), 0)
    for i, (_, hp) in enumerate(foes):
        foe = state.units[UnitId(f"unit_000{i + 2}")]
        foe.max_hp = foe.hp = hp
    return give_turn(state, U1)


def _attack(state: BattleState, target: UnitId = U2) -> tuple[BattleState, list[EventBase]]:
    state.units[U1].ap = 9  # 這些測試不關心 AP
    result = resolve(state, Attack(unit_id=U1, target_id=target))
    first = next(e for e in result.events if isinstance(e, AttackRolled))
    if not first.hit:
        raise _Missed
    return result.state, list(result.events)


def _scan[T](state: BattleState, plan: Callable[[BattleState], T]) -> T:
    """找一個種子，讓 ``plan`` 裡每一次主要攻擊都命中（連擊多出來的那一下命不命中都可以）。"""
    for seed in range(400):
        s = state.clone()
        s.rng_state = Rng(seed).get_state()
        try:
            return plan(s)
        except _Missed:
            continue
    raise AssertionError("找不到讓主要攻擊都命中的種子")


def _next_turn(state: BattleState) -> BattleState:
    """走完這個回合與其他人的回合，回到 U1 的下一個回合（新回合開始時清除每回合計數）。"""
    while True:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
        if state.active_unit == U1:
            return give_turn(state, U1)


def _rolled(events: list[EventBase], attacker: UnitId = U1) -> list[AttackRolled]:
    return [e for e in events if isinstance(e, AttackRolled) and e.attacker_id == attacker]


def _triggers(events: list[EventBase], name: str) -> list[GearTriggered]:
    return [e for e in events if isinstance(e, GearTriggered) and e.trigger == name]


def _multiplier(state: BattleState) -> int:
    foe = state.units[U2]
    return mods.damage_permille(state, state.units[U1], mods.ATTACK, Subject(foe, foe.xy))


# ---------------------------------------------------------------------------
# 1 普攻精通
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("actives", "expected"),
    [(0, 1150), (3, 1150), (4, 1100), (5, 1050), (6, 1000)],
    ids=["0-actives-capped", "3-actives", "4-actives", "5-actives", "6-actives-none-empty"],
)
def test_mastery_scales_with_empty_active_slots_and_caps_at_three(
    actives: int, expected: int
) -> None:
    state = _fighting({}, skills=(MASTERY, *ACTIVES[:actives]))
    assert _multiplier(state) == expected  # 每空 1 格 +5%，最多算 3 格（+15%）


def test_mastery_counts_the_bar_when_the_attack_resolves() -> None:
    state = _fighting({}, skills=(MASTERY, *ACTIVES[:3]))
    assert _multiplier(state) == 1150
    unit = state.units[U1]
    unit.skills = (*unit.skills, ACTIVES[3])  # 戰鬥中多裝一招：空格少一格
    assert _multiplier(state) == 1100


def test_mastery_ignores_passives_and_only_applies_to_basic_attacks() -> None:
    state = _fighting({}, skills=(MASTERY, ACTIVES[0]))
    unit, foe = state.units[U1], state.units[U2]
    assert mods.empty_active_slots(state, unit) == 5  # 被動（修正型）不佔主動欄
    cleave = library().skills["skill_cleave"]
    assert mods.damage_permille(state, unit, mods.skill_use(cleave), Subject(foe, foe.xy)) == 1000


def test_mastery_counts_towards_the_fifty_percent_damage_cap() -> None:
    # 精通 +150，加上兩枚玻璃（+200、遞減 +100）與低血傷害 +150 ＝ 600 → 截斷為 +500
    slots: dict[str, Rolls] = {
        "main_hand": [("affix_cost_glass", None)],
        "neck": [("affix_cost_glass", None)],
        "ring_1": [("affix_cond_low_hp_damage", 150)],
    }
    state = _fighting(slots, skills=(MASTERY,))
    state.units[U1].hp = 1
    assert _multiplier(state) == 1500


def test_mastery_damage_reaches_the_damage_event() -> None:
    state = _fighting({}, skills=(MASTERY, *ACTIVES[:3]))
    _, events = _scan(state, _attack)
    hit = next(e for e in events if isinstance(e, DamageDealt) and e.source_id == U1)
    assert hit.multiplier_permille == 1150


def test_mastery_passive_is_valid_and_within_budget() -> None:
    lib = library()
    skill = lib.skills[MASTERY]
    assert validate_skill(skill, lib) == []
    assert skill_budget(skill, lib).ok
    rule = skill.modifiers[0]
    assert rule.empty_slots_cap == 3 and rule.change.damage_permille == 50


@pytest.mark.parametrize(
    "bad",
    [
        {"change": {"hit_bonus": 1}, "empty_slots_cap": 3},
        {"change": {"damage_permille": -100}, "empty_slots_cap": 3},
        {"change": {"damage_permille": 80}, "empty_slots_cap": 3, "per_turn_limit": 1},
    ],
)
def test_empty_slots_cap_schema_limits(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="empty_slots_cap"):
        ModifierSpec.model_validate({"applies_to": {"actions": ["attack"]}, **bad})
    with pytest.raises(ValueError, match="empty_slots_cap"):  # 只能套用在普攻
        ModifierSpec.model_validate(
            {
                "applies_to": {"all_attacks": True},
                "change": {"damage_permille": 80},
                "empty_slots_cap": 3,
            }
        )


# ---------------------------------------------------------------------------
# 2 普攻連擊
# ---------------------------------------------------------------------------


def _combo_state(n: int = 2) -> BattleState:
    return _fighting({"main_hand": [(COMBO, n)]})


def test_combo_fires_on_every_nth_basic_hit_once_per_turn_and_resets() -> None:
    def plan(s: BattleState) -> list[tuple[int, int]]:
        found: list[tuple[int, int]] = []
        for turn in range(2):
            for _ in range(4 if turn == 0 else 2):
                s, events = _attack(s)
                found.append((len(_rolled(events)), len(_triggers(events, "attack_combo"))))
            s = _next_turn(s)
        return found

    got = _scan(_combo_state(), plan)
    # 第 1 回合：命中 1～4（第 2 次觸發；第 4 次同回合不再）；第 2 回合：命中 5、6（第 6 次觸發）
    assert got == [(1, 0), (2, 1), (1, 0), (1, 0), (1, 0), (2, 1)]


def test_combo_extra_hit_is_half_damage_and_does_not_count_as_a_hit() -> None:
    def plan(s: BattleState) -> list[EventBase]:
        s, _ = _attack(s)
        s, events = _attack(s)
        assert s.units[U1].attack_hits_landed == 2  # 多出來的那一下不計數、也不會再連擊
        extra = _rolled(events)[1]
        if not extra.hit:
            raise _Missed
        return events

    events = _scan(_combo_state(), plan)
    damages = [e for e in events if isinstance(e, DamageDealt) and e.source_id == U1]
    assert [d.multiplier_permille for d in damages] == [1000, 400]


def test_combo_needs_to_roll_again_and_can_miss() -> None:
    def plan(s: BattleState) -> list[EventBase]:
        s, _ = _attack(s)
        s, events = _attack(s)
        if _rolled(events)[1].hit:
            raise _Missed
        return events

    events = _scan(_combo_state(), plan)
    assert len([e for e in events if isinstance(e, DamageDealt) and e.source_id == U1]) == 1


def test_combo_counts_only_basic_attacks() -> None:
    state = _combo_state()
    unit = state.units[U1]
    unit.skills = ("skill_bone_crusher",)

    for seed in range(40):
        s = state.clone()
        s.rng_state = Rng(seed).get_state()
        s.units[U1].ap = 9
        result = resolve(s, UseSkill(unit_id=U1, skill_id="skill_bone_crusher", target_id=U2))
        assert result.state.units[U1].attack_hits_landed == 0


def test_combo_every_third_when_n_is_three() -> None:
    def plan(s: BattleState) -> list[int]:
        out: list[int] = []
        for _ in range(3):
            s, events = _attack(s)
            out.append(len(_triggers(events, "attack_combo")))
        return out

    assert _scan(_combo_state(3), plan) == [0, 0, 1]


def test_combo_keeps_the_more_frequent_duplicate_only() -> None:
    state = _fighting({"main_hand": [(COMBO, 3)], "hands": [(COMBO, 2)]})
    entries = [a for a in state.units[U1].gear.affixes if a.affix.id == COMBO]
    by_slot = {a.slot: a for a in entries}
    assert by_slot["hands"].active and by_slot["hands"].value == 2  # 每第 2 次較頻繁：生效
    assert not by_slot["main_hand"].active  # 每第 3 次：被取代
    assert [a.slot for a in state.units[U1].gear.active_affixes("attack")] == ["hands"]


def test_combo_does_not_stack_when_two_copies_are_worn() -> None:
    """兩件都有連擊：同 id 只算最強的 1 條，每回合最多 1 次額外攻擊。"""
    state = _fighting({"main_hand": [(COMBO, 2)], "hands": [(COMBO, 2)]})

    def plan(s: BattleState) -> int:
        total = 0
        for _ in range(4):
            s, events = _attack(s)
            total += len(_triggers(events, "attack_combo"))
        return total

    assert _scan(state, plan) == 1


def test_combo_does_not_fire_without_a_hit_on_the_target() -> None:
    state = _combo_state()
    assert state.units[U1].attack_hits_landed == 0


# ---------------------------------------------------------------------------
# 3 分裂
# ---------------------------------------------------------------------------

CLEAVE_FOES = (((1, 0), 999), ((2, 0), 30), ((1, 1), 12), ((3, 1), 5))


def _cleave_state() -> BattleState:
    return _fighting({"main_hand": [(CLEAVE, None)]}, CLEAVE_FOES)


def test_cleave_hits_the_lowest_hp_adjacent_enemy_for_half_once_per_turn() -> None:
    def plan(s: BattleState) -> tuple[list[EventBase], list[EventBase]]:
        s, first = _attack(s)
        s, second = _attack(s)
        return first, second

    first, second = _scan(_cleave_state(), plan)
    fired = _triggers(first, "attack_cleave")
    assert [(t.unit_id, t.other_id) for t in fired] == [(U1, U4)]  # (1,1) 的 HP 12 最低
    splash = [e for e in first if isinstance(e, DamageDealt) and e.target_id == U4]
    assert len(splash) == 1 and splash[0].multiplier_permille == 300 and splash[0].cause == "attack"
    assert not [e for e in first if isinstance(e, DamageDealt) and e.target_id == U3]
    assert not [
        e for e in first if isinstance(e, DamageDealt) and e.target_id == UnitId("unit_0005")
    ]
    assert _triggers(second, "attack_cleave") == []  # 同回合第二次不再分裂


def test_cleave_resets_next_turn() -> None:
    def plan(s: BattleState) -> int:
        s, _ = _attack(s)
        s = _next_turn(s)
        for foe in s.units.values():
            if foe.team is Team.ENEMY:
                foe.hp = foe.max_hp
        s, events = _attack(s)
        return len(_triggers(events, "attack_cleave"))

    assert _scan(_cleave_state(), plan) == 1


def test_cleave_ties_break_by_coordinates() -> None:
    foes = (((1, 0), 999), ((2, 0), 20), ((1, 1), 20))
    state = _fighting({"main_hand": [(CLEAVE, None)]}, foes)
    _, events = _scan(state, _attack)
    assert [t.other_id for t in _triggers(events, "attack_cleave")] == [U4]  # (1,1) 在 (2,0) 之前


def test_cleave_needs_another_adjacent_enemy_and_a_living_target() -> None:
    alone = _fighting({"main_hand": [(CLEAVE, None)]}, (((1, 0), 999), ((3, 1), 20)))
    _, events = _scan(alone, _attack)
    assert _triggers(events, "attack_cleave") == []
    kill = _fighting({"main_hand": [(CLEAVE, None)]}, (((1, 0), 1), ((2, 0), 20)))
    _, events = _scan(kill, _attack)
    assert _triggers(events, "attack_cleave") == []  # 目標被打倒了：沿用命中後效果的規則，不分裂


def test_cleave_never_hits_allies() -> None:
    hero = _spawn({"main_hand": [(CLEAVE, None)]}).model_copy(update={"position": (0, 0)})
    ally = spawn(Team.ALLY, (2, 0), no_reactions("bandit"))
    foe = spawn(Team.ENEMY, (1, 0), no_reactions("bandit"))
    m = make_map("0000\n0000", ally=[(0, 0), (2, 0)], enemy=[(1, 0)])
    state = give_turn(start_battle(make_setup(m, [hero, ally, foe]), 0), U1)
    state.units[UnitId("unit_0003")].hp = state.units[UnitId("unit_0003")].max_hp = 999
    _, events = _scan(state, lambda s: _attack(s, UnitId("unit_0003")))
    assert _triggers(events, "attack_cleave") == []


# ---------------------------------------------------------------------------
# 4 四條武器特性強化
# ---------------------------------------------------------------------------

TRAITS = {
    "affix_trait_bow_lob_cover": "bow",
    "affix_trait_bow_high_range": "bow",
    STILL: "longgun",
    "affix_trait_dagger_backstab_die": "dagger",
}


@pytest.mark.parametrize(("affix_id", "weapon"), TRAITS.items())
def test_traits_only_appear_on_their_own_weapon(affix_id: str, weapon: str) -> None:
    lib = library()
    assert lib.affixes[affix_id].weapons == (weapon,)
    other = next(w for w in ("one_handed_sword", "bow", "longgun", "dagger") if w != weapon)

    def problems(weapon_id: str) -> list[str]:
        item = ItemDef.model_validate(
            {
                "id": "item_t_trait",
                "name_zh": "測試",
                "slot_type": "weapon",
                "weapon": weapon_id,
                "affixes": [{"affix": affix_id, **({"value": 100} if affix_id == STILL else {})}],
            }
        )
        return item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment)

    assert problems(weapon) == []
    assert problems(other)


def test_bow_lob_cover_ignores_half_cover() -> None:
    lib = library()
    assert lib.weapons["bow"].ignore_cover is False
    assert _weapon_of({"main_hand": [("affix_trait_bow_lob_cover", None)]}, "bow").ignore_cover
    sword = _weapon_of({"main_hand": [("affix_trait_bow_lob_cover", None)]}, "one_handed_sword")
    assert sword == lib.weapons["one_handed_sword"]

    def cover_between(slots: dict[str, Rolls]) -> object:
        hero = _spawn(slots, base="hero_archer", weapon="bow").model_copy(
            update={"position": (0, 0)}
        )
        foe = spawn(Team.ENEMY, (4, 0), no_reactions("bandit"))
        m = make_map("00000", ally=[(0, 0)], enemy=[(4, 0)], objects=[(3, 0, "crate")])
        state = start_battle(make_setup(m, [hero, foe]), 0)
        return half_cover(state, state.units[U1], state.units[U2])

    assert cover_between({}) is not None
    assert cover_between({"main_hand": [("affix_trait_bow_lob_cover", None)]}) is None


def test_bow_high_range_adds_one_only_from_higher_ground() -> None:
    row = "10000000000"
    plain = _weapon_of({}, "bow")
    assert plain.range == 8 and plain.high_range == 0
    geared = _weapon_of({"main_hand": [("affix_trait_bow_high_range", None)]}, "bow")
    assert geared.range == 8 and geared.high_range == 1

    def reach(slots: dict[str, Rolls], hero_xy: tuple[int, int], foe_x: int) -> str | None:
        hero = _spawn(slots, base="hero_archer", weapon="bow").model_copy(
            update={"position": hero_xy}
        )
        foe = spawn(Team.ENEMY, (foe_x, 0), no_reactions("bandit"))
        m = make_map(row, ally=[hero_xy], enemy=[(foe_x, 0)])
        state = start_battle(make_setup(m, [hero, foe]), 0)
        return attack_problem(state, state.units[U1], state.units[U2])

    trait: dict[str, Rolls] = {"main_hand": [("affix_trait_bow_high_range", None)]}
    assert reach(trait, (0, 0), 9) is None  # 站在高處（高度 1 → 0）：射程 9
    assert reach(trait, (1, 0), 10) is not None  # 同樣的距離但自己不在高處：超出射程 8
    assert reach({}, (0, 0), 9) is not None  # 沒有詞條：8 格


def test_longgun_still_damage_applies_only_when_standing_still_and_counts_to_the_cap() -> None:
    lib = library()
    affix = lib.affixes[STILL]
    assert affix.category == "conditional" and affix.weapons == ("longgun",)
    stock = lib.weapons["longgun"]
    assert stock.steady is not None and stock.steady.crit_range == 2  # 長槍基礎值不動
    slots: dict[str, Rolls] = {"main_hand": [(STILL, 100)]}
    state = _fighting(slots, weapon="longgun")
    unit = state.units[U1]
    assert unit.weapon.steady == stock.steady
    unit.moved_this_turn = False
    assert _multiplier(state) == 1100  # 站定：傷害 +10%
    unit.moved_this_turn = True
    assert _multiplier(state) == 1000  # 本回合移動過：沒有加成
    # 計入全身 +50% 上限：+10% 加玻璃 +200、+100（第二枚遞減）加低血傷害 +150 ＝ 550 → 截斷為 +500
    slots = {
        "main_hand": [(STILL, 100)],
        "neck": [("affix_cost_glass", None)],
        "ring_1": [("affix_cost_glass", None)],
        "ring_2": [("affix_cond_low_hp_damage", 150)],
    }
    capped = _fighting(slots, weapon="longgun")
    capped.units[U1].moved_this_turn = False
    capped.units[U1].hp = 1
    assert _multiplier(capped) == 1500


def test_dagger_backstab_die_adds_a_die_only_for_backstabs() -> None:
    lib = library()
    base = lib.weapons["dagger"]
    assert base.backstab_dice == 0
    slots: dict[str, Rolls] = {"main_hand": [("affix_trait_dagger_backstab_die", None)]}
    assert _weapon_of(slots, "dagger").backstab_dice == 1
    state = _fighting(slots, weapon="dagger", row="000", hero_xy=(2, 0), foes=(((1, 0), 999),))
    state.units[U2].facing = "west"  # 背對攻擊者
    unit = state.units[U1]
    assert (weapon_traits.attack_dice(state, unit).count, unit.weapon.dice.sides) == (1, 4)
    assert weapon_traits.attack_dice(state, unit, backstab=True).count == 2

    # 目標朝西、攻擊者在它的東側（背後）：背刺 → 2 顆骰（暴擊時另外加倍，下面只看非暴擊）
    for seed in range(200):
        s = state.clone()
        s.rng_state = Rng(seed).get_state()
        try:
            s, events = _attack(s)
        except _Missed:
            continue
        roll = _rolled(events)[0]
        damage = next(e for e in events if isinstance(e, DamageDealt) and e.source_id == U1)
        if roll.crit:
            continue
        assert roll.backstab > 0
        assert len(damage.rolls) == 2
        break
    else:
        pytest.fail("找不到非暴擊的背刺")


def test_dagger_without_the_affix_rolls_one_die_from_behind() -> None:
    state = _fighting({}, weapon="dagger", row="000", hero_xy=(2, 0), foes=(((1, 0), 999),))
    state.units[U2].facing = "west"
    for seed in range(200):
        s = state.clone()
        s.rng_state = Rng(seed).get_state()
        try:
            s, events = _attack(s)
        except _Missed:
            continue
        if _rolled(events)[0].crit:
            continue
        damage = next(e for e in events if isinstance(e, DamageDealt) and e.source_id == U1)
        assert len(damage.rolls) == 1
        return
    pytest.fail("找不到非暴擊的背刺")


# ---------------------------------------------------------------------------
# 5 重複詞條與裝備視圖
# ---------------------------------------------------------------------------


def test_equipment_view_marks_inactive_duplicates_with_the_winning_slot() -> None:
    state = _fighting({"main_hand": [(COMBO, 3)], "hands": [(COMBO, 2)]})
    view = project_for(state, Team.ALLY)
    hero = next(u for u in view.units if u.id == U1)
    lines = {e.slot: e.affixes for e in hero.equipment}
    winner = next(a for a in lines["hands"] if a.affix_id == COMBO)
    loser = next(a for a in lines["main_hand"] if a.affix_id == COMBO)
    assert winner.active and winner.duplicate_of is None
    assert not loser.active
    assert loser.duplicate_of == "手的每第 2 次普攻命中：多攻擊一次（40% 傷害；每回合 1 次）"


def test_diminishing_numeric_duplicates_stay_active_until_the_fourth() -> None:
    slots: dict[str, Rolls] = {
        s: [("affix_attr_str", 1)] for s in ("main_hand", "neck", "ring_1", "ring_2")
    }
    state = _fighting(slots)
    view = project_for(state, Team.ALLY)
    hero = next(u for u in view.units if u.id == U1)
    lines = [a for e in hero.equipment for a in e.affixes]
    assert sorted((a.weight_permille, a.duplicate_of is None) for a in lines) == [
        (0, False),
        (250, True),
        (500, True),
        (1000, True),
    ]
    dup = next(a for a in lines if not a.active)
    assert dup.duplicate_of == "主手的力量 +1"


def test_equal_duplicates_report_the_first_slot() -> None:
    state = _fighting({"main_hand": [(COMBO, 2)], "hands": [(COMBO, 2)]})
    view = project_for(state, Team.ALLY)
    hero = next(u for u in view.units if u.id == U1)
    lines = {e.slot: next(a for a in e.affixes) for e in hero.equipment}
    assert lines["main_hand"].active and not lines["hands"].active
    assert lines["hands"].duplicate_of is not None
    assert lines["hands"].duplicate_of.startswith("主手的")


# ---------------------------------------------------------------------------
# 6 內容
# ---------------------------------------------------------------------------


def test_new_affixes_roll_on_the_listed_slots() -> None:
    lib = library()
    assert lib.affixes[COMBO].slots == ("weapon", "hands")
    assert lib.affixes[CLEAVE].slots == ("weapon",)
    value = lib.affixes[COMBO].value
    assert value is not None and (value.min, value.max) == (2, 3)
    for affix_id in TRAITS:
        assert lib.affixes[affix_id].slots == ("weapon",)
    still = lib.affixes[STILL].value
    assert still is not None and (still.min, still.max) == (100, 100)


def test_reference_builds_are_valid_and_kept_out_of_the_matrix() -> None:
    lib = library()
    ids = {b.id for b in lib.builds.sim_builds()}
    assert "build_attack_archer" not in ids and "build_skill_archer" not in ids
    attack = lib.builds.by_id()["build_attack_archer"].hero
    assert MASTERY in attack.skills
    assert sum(1 for s in attack.skills if lib.skills[s].kind == "active") == 3
    skill = lib.builds.by_id()["build_skill_archer"].hero
    actives = [lib.skills[s] for s in skill.skills if lib.skills[s].kind == "active"]
    assert len(actives) == 4  # 3-32c：2 範圍＋1 控制＋1 單體爆發，欄位沒滿、沒有精通
    area = {"skill_piercing_shot", "skill_thunder_clap"}
    assert area <= set(skill.skills) and {"skill_bear_trap", "skill_sniper_shot"} <= set(
        skill.skills
    )
    assert {s.shape.type for s in actives if s.id in area} == {"line", "cone"}
    assert MASTERY not in skill.skills
    assert any(e.type == "apply_status" for e in lib.skills["skill_bear_trap"].effects)
    assert all(s.weapon_req in ("any", "ranged") for s in actives)  # 弓手能用
    loadout = lib.loadout_of(attack)
    assert {a.affix.id for item in loadout.items for a in item.affixes} == {
        COMBO,
        CLEAVE,
        "affix_trait_bow_high_range",
    }


# ---------------------------------------------------------------------------
# 7 確定性與重播
# ---------------------------------------------------------------------------


def test_full_battle_with_the_attack_flow_replays_identically() -> None:
    """普攻流整場自動戰鬥：初始狀態 ＋ 步驟列表重播得到同樣的事件與最終狀態；同種子確定。"""
    hero = _spawn(
        {"main_hand": [(CLEAVE, None)], "hands": [(COMBO, 2)]},
        skills=(MASTERY, *ACTIVES[:2]),
    )
    foes = [spawn(Team.ENEMY, (3, y), no_reactions("bandit")) for y in range(3)]
    m = make_map("0000\n0000\n0000", ally=[(0, 0)], enemy=[(3, 0), (3, 1), (3, 2)])
    setup = make_setup(m, [hero, *foes], max_rounds=6)
    run = run_battle(setup, 5)
    again = replay(setup, 5, run.actions)
    dump = [e.model_dump(mode="json") for e in run.events]
    assert [e.model_dump(mode="json") for e in again.events] == dump
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump(mode="json") for e in run_battle(setup, 5).events] == dump
    triggers = {e["trigger"] for e in dump if e["type"] == "gear_triggered"}
    assert {"attack_combo", "attack_cleave"} <= triggers

    # 戰報文字：這些 trigger 名稱（含 3-31 的符文）不在 skill_triggers.yaml，不能因找不到而當掉
    lines = [
        describe_event(e, run.state) or ""
        for e in run.events
        if isinstance(e, GearTriggered) and e.trigger.startswith("attack_")
    ]
    assert lines and all("{n}" not in line for line in lines)
    assert any("普攻連擊" in line for line in lines) and any("普攻分裂" in line for line in lines)
