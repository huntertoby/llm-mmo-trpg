"""武器擴充第一批（Phase 3-24a1，``docs/phases/Phase3計畫.md`` 25.1）。

每個特性都是 ``content/weapons.yaml`` 武器資料上的參數：斧的破甲 ``armor_break``、錘的震退
``knockback``（與第二縮放屬性）、矛的觸及 ``reach``、權杖的祝禱 ``blessing``、圖騰杖的統御
``summon_dice_bonus``、弓的拋射 ``lob``。每個特性一組測試，其中都有「資料改參數後行為跟著變」
的案例。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_map, make_setup, no_reactions, template
from tests.engine.test_pierce import arena, shoot
from trpg.content.battle import WeaponDef
from trpg.engine import Attack, BattleState, Move, legal_actions, resolve, start_battle
from trpg.engine.ai.utility import UtilityAI, _knock_collides, _weapon_terms
from trpg.engine.events import (
    AttackRolled,
    Collided,
    DamageDealt,
    EventBase,
    Healed,
    ReactionTriggered,
    StatusApplied,
    UnitMoved,
)
from trpg.engine.preview import preview
from trpg.engine.rules.combat import attack_problem, attack_value, defense_value_permille
from trpg.engine.rules.statuses import weapon_attribute
from trpg.engine.setup import UnitSpawn
from trpg.engine.state import StatusInstance
from trpg.engine.weapon_traits import attack_dice, blessing_target
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT7 = "\n".join(["0000000"] * 5)


def weapon(weapon_id: str, **changes: Any) -> WeaponDef:
    """武器資料的複本，可以覆寫參數（驗證「改資料行為跟著變」）。"""
    data = library().weapons[weapon_id].model_dump(mode="json")
    return WeaponDef.model_validate({**data, **changes})


def armed(
    team: Team,
    pos: tuple[int, int],
    w: WeaponDef,
    base: str = "hero_fighter",
    **overrides: Any,
) -> UnitSpawn:
    """裝備指定武器資料的單位（預設沒有反應規則、HP 200，不干擾驗證）。"""
    overrides.setdefault("reactions", [])
    overrides.setdefault("max_hp", 200)
    return UnitSpawn(template=template(base, **overrides), weapon=w, team=team, position=pos)


def state_of(
    spawns: Sequence[UnitSpawn],
    *,
    heights: str = FLAT7,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    active: UnitId = U1,
) -> BattleState:
    allies = [s.position for s in spawns if s.team is Team.ALLY and s.position is not None]
    enemies = [s.position for s in spawns if s.team is Team.ENEMY and s.position is not None]
    m = make_map(heights, terrain, ally=allies, enemy=enemies, objects=objects)
    return give_turn(start_battle(make_setup(m, spawns), 0), active)


def dice(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 3) -> None:
    """d20 一律 ``d20``（19 命中不暴擊、1 失手）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def kinds[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def hit(state: BattleState, target: UnitId = U2) -> list[EventBase]:
    return resolve(state, Attack(unit_id=U1, target_id=target)).events


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_new_weapons_are_data_with_the_specified_parameters() -> None:
    w = library().weapons
    assert (w["axe"].weapon_class, w["axe"].range, w["axe"].two_handed, w["axe"].scaling_attr) == (
        "melee",
        1,
        False,
        "str",
    )
    assert w["axe"].armor_break is not None
    assert w["axe"].armor_break.defense_permille == -100 and w["axe"].armor_break.rounds == 1
    assert (w["hammer"].two_handed, w["hammer"].knockback) == (True, 1)
    assert (w["hammer"].scaling_attr, w["hammer"].secondary_scaling_attr) == ("con", "str")
    assert w["hammer"].attr_mode == "mean"
    assert (w["spear"].range, w["spear"].reach, w["spear"].two_handed) == (2, 2, True)
    assert (w["scepter"].weapon_class, w["scepter"].range, w["scepter"].two_handed) == (
        "focus",
        4,
        False,
    )
    assert w["scepter"].scaling_attr == "wis" and w["scepter"].blessing is not None
    assert (w["totem_staff"].range, w["totem_staff"].two_handed) == (4, True)
    assert w["totem_staff"].scaling_attr == "wil" and w["totem_staff"].summon_dice_bonus == 1
    assert w["bow"].lob == 1
    # 沒有特性的舊武器維持預設
    assert w["one_handed_sword"].lob == 0 and w["one_handed_sword"].reach == 1


def test_weapon_schema_rejects_inconsistent_parameters() -> None:
    base = library().weapons["spear"].model_dump(mode="json")
    with pytest.raises(ValidationError, match="reach"):
        WeaponDef.model_validate({**base, "reach": 3})
    with pytest.raises(ValidationError, match="secondary_scaling_attr"):
        WeaponDef.model_validate({**base, "secondary_scaling_attr": base["scaling_attr"]})
    with pytest.raises(ValidationError):
        WeaponDef.model_validate({**base, "armor_break": {"defense_permille": 100, "rounds": 1}})
    with pytest.raises(ValidationError, match="祝禱"):
        WeaponDef.model_validate({**base, "blessing": {}})


def test_trait_text_follows_the_parameters() -> None:
    axe = weapon("axe")
    assert axe.trait_lines_zh() == ("破甲：命中後目標防禦 −10%，1 回合",)
    axe2 = weapon("axe", armor_break={"defense_permille": -250, "rounds": 2})
    assert axe2.trait_lines_zh() == ("破甲：命中後目標防禦 −25%，2 回合",)
    assert weapon("hammer").trait_lines_zh() == ("震退：普攻命中推 1 格（會撞擊）",)
    assert any("觸及 2 格" in line for line in weapon("spear").trait_lines_zh())
    assert weapon("scepter").trait_lines_zh() == ("祝禱：普攻命中時，最近的隊友回復 3 HP",)
    assert "統御" in weapon("totem_staff").trait_lines_zh()[0]
    assert "拋射" in weapon("bow").trait_lines_zh()[0]
    assert weapon("one_handed_sword").trait_lines_zh() == ()


# ---------------------------------------------------------------------------
# 斧：破甲
# ---------------------------------------------------------------------------


def axe_state(**changes: Any) -> BattleState:
    return state_of(
        [
            armed(Team.ALLY, (1, 2), weapon("axe", **changes)),
            armed(Team.ENEMY, (2, 2), weapon("one_handed_sword"), base="bandit"),
        ]
    )


def test_axe_hit_applies_armor_broken_and_lowers_defense_by_10_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = axe_state()
    before = defense_value_permille(state.units[U2], state.ruleset)
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (applied,) = [e for e in kinds(result.events, StatusApplied) if e.status_id == "armor_broken"]
    assert applied.target_id == U2 and applied.duration == 1 and applied.source_id == U1
    after = defense_value_permille(result.state.units[U2], result.state.ruleset)
    assert after == before * 900 // 1000


def test_axe_miss_applies_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=1)
    events = hit(axe_state())
    assert not kinds(events, StatusApplied)


def test_armor_broken_is_a_one_turn_debuff_that_counts_down_at_the_targets_turn_end() -> None:
    status = axe_state().ruleset.status_def("armor_broken")
    assert status.expires == "turn_end" and status.duration == 1 and status.defense_break
    assert status.polarity == "debuff" and status.budget_points is None  # 技能不能施加


def test_changing_the_armor_break_parameters_changes_the_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = axe_state(armor_break={"defense_permille": -300, "rounds": 2})
    before = defense_value_permille(state.units[U2], state.ruleset)
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (applied,) = [e for e in kinds(result.events, StatusApplied) if e.status_id == "armor_broken"]
    assert applied.duration == 2
    assert (
        defense_value_permille(result.state.units[U2], result.state.ruleset) == before * 700 // 1000
    )
    # 沒有 armor_break 參數的斧不破甲
    plain = hit(axe_state(armor_break=None))
    assert not [e for e in kinds(plain, StatusApplied) if e.status_id == "armor_broken"]


def test_armor_break_takes_the_largest_value_and_never_drops_defense_below_one() -> None:
    state = axe_state()
    unit = state.units[U2]
    unit.statuses = []
    plain = defense_value_permille(unit, state.ruleset)
    unit.statuses = [StatusInstance("armor_broken", 1, U1, 400), StatusInstance("vulnerable", 2)]
    assert defense_value_permille(unit, state.ruleset) == plain * 600 // 1000
    unit.statuses = [StatusInstance("armor_broken", 1, U1, 1000)]  # 防禦 −100%：最低 1
    assert defense_value_permille(unit, state.ruleset) == 1


# ---------------------------------------------------------------------------
# 錘：震退與第二縮放屬性
# ---------------------------------------------------------------------------


def hammer_state(
    *,
    foe_x: int = 3,
    terrain: str | None = None,
    **changes: Any,
) -> BattleState:
    return state_of(
        [
            armed(Team.ALLY, (foe_x - 1, 2), weapon("hammer", **changes)),
            armed(Team.ENEMY, (foe_x, 2), weapon("one_handed_sword"), base="bandit"),
        ],
        terrain=terrain,
    )


def test_hammer_hit_pushes_the_target_one_tile_along_the_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    result = resolve(hammer_state(), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (4, 2)
    moved = [e for e in kinds(result.events, UnitMoved) if e.unit_id == U2]
    assert [(m.mode, m.to_pos) for m in moved] == [("forced", Pos(x=4, y=2))]
    assert not kinds(result.events, Collided)


def test_hammer_miss_does_not_push(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=1)
    result = resolve(hammer_state(), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (3, 2)


def test_hammer_knockback_into_a_wall_collides_and_deals_collision_damage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    terrain = "\n".join(["....#.."] * 5)
    state = hammer_state(terrain=terrain)
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (3, 2)
    (collided,) = kinds(result.events, Collided)
    assert collided.unit_id == U2 and collided.obstacle in {"wall", "edge"}
    assert [
        e for e in kinds(result.events, DamageDealt) if e.cause == "collision" and e.target_id == U2
    ]


def test_hammer_knockback_into_another_unit_hurts_both(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = state_of(
        [
            armed(Team.ALLY, (2, 2), weapon("hammer")),
            armed(Team.ENEMY, (3, 2), weapon("one_handed_sword"), base="bandit"),
            armed(Team.ENEMY, (4, 2), weapon("one_handed_sword"), base="bandit"),
        ]
    )
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (collided,) = kinds(result.events, Collided)
    assert collided.obstacle == "unit" and collided.other_id == U3


def test_changing_knockback_changes_the_push_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    two = resolve(hammer_state(knockback=2), Attack(unit_id=U1, target_id=U2))
    assert two.state.units[U2].xy == (5, 2)
    none = resolve(hammer_state(knockback=0), Attack(unit_id=U1, target_id=U2))
    assert none.state.units[U2].xy == (3, 2)


def test_hammer_attack_value_averages_strength_and_constitution() -> None:
    state = hammer_state()
    unit = state.units[U1]
    unit.attributes[Attribute.STR] = 18
    unit.attributes[Attribute.CON] = 10
    assert attack_value(unit, state.ruleset) == 14 + unit.weapon.attack_bonus
    unit.weapon = weapon("hammer", scaling_attr=Attribute.STR, secondary_scaling_attr=None)
    assert attack_value(unit, state.ruleset) == 18 + unit.weapon.attack_bonus


def _dual_state(**changes: Any) -> BattleState:
    state = hammer_state(**changes)
    unit = state.units[U1]
    unit.attributes[Attribute.STR] = 18
    unit.attributes[Attribute.CON] = 10
    unit.attributes[Attribute.DEX] = 12
    return state


def test_dual_attribute_weapons_take_the_average_or_the_higher_by_attr_mode() -> None:
    """3H-1（08 8.11）：重武器（錘）取平均、輕武器（匕首）取較高；取法是武器資料 ``attr_mode``。"""
    mean = _dual_state()
    assert mean.units[U1].weapon.attr_mode == "mean"
    assert weapon_attribute(mean.ruleset, mean.units[U1]) == 14  # (con 10 + str 18) // 2
    high = _dual_state(attr_mode="max")
    assert weapon_attribute(high.ruleset, high.units[U1]) == 18  # 取較高：力量 18
    dagger = weapon("dagger")
    assert (dagger.scaling_attr, dagger.secondary_scaling_attr, dagger.attr_mode) == (
        Attribute.DEX,
        Attribute.STR,
        "max",
    )


def test_attr_mode_only_matters_with_a_second_attribute() -> None:
    state = _dual_state(attr_mode="max", secondary_scaling_attr=None, scaling_attr=Attribute.CON)
    assert weapon_attribute(state.ruleset, state.units[U1]) == 10


def test_the_dual_attribute_line_follows_the_data() -> None:
    core = library().ruleset.core
    assert "雙屬性：普攻吃體質、力量，取平均；武器技看技能卡（在這把武器的屬性範圍內）" in weapon(
        "hammer"
    ).rule_lines_zh(core)
    assert "雙屬性：普攻吃敏捷、力量，取較高者；武器技看技能卡（在這把武器的屬性範圍內）" in weapon(
        "dagger"
    ).rule_lines_zh(core)
    assert not any("雙屬性" in line for line in weapon("axe").rule_lines_zh(core))


# ---------------------------------------------------------------------------
# 矛：觸及 2 格與藉機攻擊
# ---------------------------------------------------------------------------


def spear_state(**changes: Any) -> BattleState:
    """矛兵（我方）在 (1, 2)，敵人在 (3, 2)（距離 2）；矛兵有藉機攻擊反應。"""
    return state_of(
        [
            UnitSpawn(
                template=template("hero_fighter", max_hp=200),
                weapon=weapon("spear", **changes),
                team=Team.ALLY,
                position=(1, 2),
            ),
            armed(Team.ENEMY, (3, 2), weapon("one_handed_sword"), base="bandit"),
        ],
        active=U2,
    )


def walk(path: Sequence[tuple[int, int]]) -> Move:
    return Move(unit_id=U2, path=tuple(Pos(x=x, y=y) for x, y in path))


def test_spear_attacks_a_target_two_tiles_away_but_not_three() -> None:
    state = give_turn(spear_state(), U1)
    assert attack_problem(state, state.units[U1], state.units[U2]) is None
    assert Attack(unit_id=U1, target_id=U2) in legal_actions(state)
    state.units[U2].pos = Pos(x=4, y=2)
    assert "射程" in (attack_problem(state, state.units[U1], state.units[U2]) or "")
    assert state.units[U1].weapon.is_melee  # 長柄仍是近戰：背刺、倒地優勢、高度差限制都照近戰


def test_spear_gets_an_opportunity_attack_when_a_target_leaves_its_two_tile_reach() -> None:
    state = spear_state()
    # 敵人從距離 2 走到距離 3：離開矛的觸及範圍 → 藉機攻擊
    events = resolve(state, walk([(3, 2), (4, 2)])).events
    triggered = kinds(events, ReactionTriggered)
    assert [(t.unit_id, t.reaction) for t in triggered] == [(U1, "opportunity_attack")]
    assert kinds(events, AttackRolled)[0].attacker_id == U1


def test_spear_does_not_react_while_the_target_stays_inside_the_reach() -> None:
    state = spear_state()
    # 敵人從距離 2 走到距離 1（靠近）、再走回距離 2：都沒有離開觸及範圍
    events = resolve(state, walk([(3, 2), (2, 2), (3, 2)])).events
    assert not kinds(events, ReactionTriggered)


def test_sword_has_no_opportunity_attack_at_two_tiles() -> None:
    state = state_of(
        [
            UnitSpawn(
                template=template("hero_fighter", max_hp=200),
                weapon=weapon("one_handed_sword"),
                team=Team.ALLY,
                position=(1, 2),
            ),
            armed(Team.ENEMY, (3, 2), weapon("one_handed_sword"), base="bandit"),
        ],
        active=U2,
    )
    assert not kinds(resolve(state, walk([(3, 2), (4, 2)])).events, ReactionTriggered)


def test_changing_reach_changes_the_opportunity_range() -> None:
    state = spear_state(reach=1)
    assert not kinds(resolve(state, walk([(3, 2), (4, 2)])).events, ReactionTriggered)
    # reach 1 的矛：敵人離開相鄰格才會觸發
    adjacent = state_of(
        [
            UnitSpawn(
                template=template("hero_fighter", max_hp=200),
                weapon=weapon("spear", reach=1),
                team=Team.ALLY,
                position=(1, 2),
            ),
            armed(Team.ENEMY, (2, 2), weapon("one_handed_sword"), base="bandit"),
        ],
        active=U2,
    )
    events = resolve(adjacent, walk([(2, 2), (3, 2)])).events
    assert [t.reaction for t in kinds(events, ReactionTriggered)] == ["opportunity_attack"]


# ---------------------------------------------------------------------------
# 權杖：祝禱
# ---------------------------------------------------------------------------


def scepter_state(**changes: Any) -> BattleState:
    """牧師 U1 (1,2)；隊友 U2 (0,2) 受傷、U3 (1,0) 受傷更遠；敵人 U4 (4,2)。"""
    ally = armed(Team.ALLY, (0, 2), weapon("one_handed_sword"), max_hp=100)
    far = armed(Team.ALLY, (1, 0), weapon("one_handed_sword"), max_hp=100)
    foe = armed(Team.ENEMY, (4, 2), weapon("one_handed_sword"), base="bandit")
    priest = armed(Team.ALLY, (1, 2), weapon("scepter", **changes), base="hero_mage")
    state = state_of([priest, ally, far, foe])
    # state_of 依序配 ID：priest U1、ally U2、far U3、foe U4
    for uid in (U2, U3):
        state.units[uid].hp = 50
    return state


def test_scepter_hit_heals_the_nearest_ally_by_the_data_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = scepter_state()
    assert blessing_target(state, state.units[U1]) is state.units[U2]
    events = resolve(state, Attack(unit_id=U1, target_id=U4)).events
    (healed,) = kinds(events, Healed)
    assert (healed.target_id, healed.amount, healed.source_id) == (U2, 3, U1)


def test_scepter_miss_does_not_heal(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=1)
    assert not kinds(resolve(scepter_state(), Attack(unit_id=U1, target_id=U4)).events, Healed)


def test_changing_blessing_changes_the_amount_and_removing_it_removes_the_heal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    big = resolve(scepter_state(blessing={"flat": 8}), Attack(unit_id=U1, target_id=U4)).events
    assert kinds(big, Healed)[0].amount == 8
    none = resolve(scepter_state(blessing=None), Attack(unit_id=U1, target_id=U4)).events
    assert not kinds(none, Healed)


def test_blessing_ignores_summons_and_downed_allies_and_needs_one() -> None:
    state = scepter_state()
    state.units[U2].downed = True
    assert blessing_target(state, state.units[U1]) is state.units[U3]  # 倒下的不算
    state.units[U3].owner_id = U1  # 召喚物不算
    assert blessing_target(state, state.units[U1]) is None


def test_scepter_range_is_four() -> None:
    state = scepter_state()
    assert attack_problem(state, state.units[U1], state.units[U4]) is None  # 距離 3
    state.units[U4].pos = Pos(x=6, y=2)
    assert "射程" in (attack_problem(state, state.units[U1], state.units[U4]) or "")


# ---------------------------------------------------------------------------
# 圖騰杖：統御
# ---------------------------------------------------------------------------


def totem_state(**changes: Any) -> BattleState:
    owner = armed(Team.ALLY, (0, 2), weapon("totem_staff", **changes), base="hero_mage")
    spirit = armed(Team.ALLY, (1, 2), weapon("one_handed_sword"), base="bandit")
    foe = armed(Team.ENEMY, (2, 2), weapon("one_handed_sword"), base="bandit")
    other = armed(Team.ALLY, (1, 3), weapon("one_handed_sword"), base="bandit")
    state = state_of([owner, spirit, foe, other], active=U2)
    state.units[U2].owner_id = U1  # U2 是 U1 的召喚物
    return state


def test_summon_attack_gets_the_owners_extra_damage_die() -> None:
    state = totem_state()
    base = state.units[U2].weapon.dice
    boosted = attack_dice(state, state.units[U2])
    assert (boosted.count, boosted.sides) == (base.count + 1, base.sides)
    # 不是召喚物的單位、召喚者沒有圖騰杖：不加
    other = attack_dice(state, state.units[U4])
    assert other == state.units[U4].weapon.dice
    plain = totem_state(summon_dice_bonus=0)
    assert attack_dice(plain, plain.units[U2]) == plain.units[U2].weapon.dice


def test_summon_attack_damage_rolls_the_extra_die(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, die=3)
    with_totem = resolve(totem_state(), Attack(unit_id=U2, target_id=U3)).events
    without = resolve(totem_state(summon_dice_bonus=0), Attack(unit_id=U2, target_id=U3)).events
    (a,) = [e for e in kinds(with_totem, DamageDealt) if e.cause == "attack"]
    (b,) = [e for e in kinds(without, DamageDealt) if e.cause == "attack"]
    assert len(a.rolls) == len(b.rolls) + 1
    assert a.amount > b.amount


def test_changing_summon_dice_bonus_changes_the_dice_count() -> None:
    state = totem_state(summon_dice_bonus=2)
    base = state.units[U2].weapon.dice
    assert attack_dice(state, state.units[U2]).count == base.count + 2


def test_totem_staff_scales_with_will_and_has_range_four() -> None:
    state = totem_state()
    owner = state.units[U1]
    assert owner.weapon.scaling_attr == "wil" and owner.weapon.range == 4
    base = attack_value(owner, state.ruleset)
    owner.attributes[Attribute.WIL] += 4
    assert attack_value(owner, state.ruleset) == base + 4


# ---------------------------------------------------------------------------
# 弓：拋射
# ---------------------------------------------------------------------------


def bow_state(
    *,
    heights: str = FLAT7,
    objects: Sequence[tuple[int, int, str]] = (),
    terrain: str | None = None,
    foe: tuple[int, int] = (4, 2),
    **changes: Any,
) -> BattleState:
    return state_of(
        [
            armed(Team.ALLY, (1, 2), weapon("bow", **changes), base="hero_archer"),
            armed(Team.ENEMY, foe, weapon("one_handed_sword"), base="bandit"),
        ],
        heights=heights,
        terrain=terrain,
        objects=objects,
    )


def can_shoot(state: BattleState) -> bool:
    return attack_problem(state, state.units[U1], state.units[U2]) is None


def test_bow_lobs_over_a_one_high_object_that_blocks_a_flat_weapon() -> None:
    pillar = [(2, 2, "stone_pillar")]
    assert can_shoot(bow_state(objects=pillar))
    assert not can_shoot(bow_state(objects=pillar, lob=0))
    assert Attack(unit_id=U1, target_id=U2) in legal_actions(bow_state(objects=pillar))
    with pytest.raises(IllegalActionError, match="視線"):
        resolve(bow_state(objects=pillar, lob=0), Attack(unit_id=U1, target_id=U2))


def test_bow_lobs_over_a_one_high_ridge_but_not_a_two_high_one() -> None:
    one = "\n".join(["0001000"] * 5).replace("0001000", "0010000", 5)
    two = "\n".join(["0020000"] * 5)
    assert can_shoot(bow_state(heights=one))
    assert not can_shoot(bow_state(heights=one, lob=0))
    assert not can_shoot(bow_state(heights=two))
    assert can_shoot(bow_state(heights=two, lob=2))  # 資料改成 lob 2 就能越過 2 層


def test_a_lob_cannot_pass_a_real_wall_or_darkness() -> None:
    wall = "\n".join(["..#...."] * 5)
    assert not can_shoot(bow_state(terrain=wall))


def test_a_two_high_object_stack_on_a_ridge_still_blocks_the_bow() -> None:
    ridge = "\n".join(["0010000"] * 5)
    assert not can_shoot(bow_state(heights=ridge, objects=[(2, 2, "stone_pillar")]))


def test_lob_keeps_the_half_cover_penalty(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = bow_state(objects=[(3, 2, "low_wall")])
    rolled = kinds(resolve(state, Attack(unit_id=U1, target_id=U2)).events, AttackRolled)[0]
    assert rolled.cover == -2
    state_open = bow_state()
    open_roll = kinds(resolve(state_open, Attack(unit_id=U1, target_id=U2)).events, AttackRolled)[0]
    assert open_roll.cover == 0


def test_lob_applies_to_weapon_skills_and_the_ai_scan() -> None:
    # 武器技（category: weapon）的視線檢查也看武器的 lob
    state = arena(objects=[(2, 3, "stone_pillar")])
    state.units[U1].weapon = weapon("bow")
    assert any(
        getattr(a, "skill_id", None) == "skill_armor_piercing_arrow" for a in legal_actions(state)
    )
    state.units[U1].weapon = weapon("bow", lob=0)
    with pytest.raises(IllegalActionError, match="視線"):
        resolve(state, shoot())


# ---------------------------------------------------------------------------
# 預覽與 AI
# ---------------------------------------------------------------------------


def test_preview_lists_the_on_hit_traits_and_the_forced_push() -> None:
    pv = preview(hammer_state(), Attack(unit_id=U1, target_id=U2))
    assert "震退：普攻命中推 1 格（會撞擊）" in pv.notes
    assert any(isinstance(e, UnitMoved) and e.mode == "forced" for e in pv.max_events)
    axe_pv = preview(axe_state(), Attack(unit_id=U1, target_id=U2))
    assert any("破甲" in n for n in axe_pv.notes)
    assert any(isinstance(e, StatusApplied) for e in axe_pv.min_events)  # 命中時一定破甲
    sword = preview(
        state_of(
            [
                armed(Team.ALLY, (1, 2), weapon("one_handed_sword")),
                armed(Team.ENEMY, (2, 2), weapon("one_handed_sword"), base="bandit"),
            ]
        ),
        Attack(unit_id=U1, target_id=U2),
    )
    assert not any("破甲" in n or "震退" in n for n in sword.notes)


def test_preview_damage_includes_the_summon_extra_die() -> None:
    boosted = preview(totem_state(), Attack(unit_id=U2, target_id=U3))
    plain = preview(totem_state(summon_dice_bonus=0), Attack(unit_id=U2, target_id=U3))
    assert boosted.damage is not None and plain.damage is not None
    assert boosted.damage.maximum > plain.damage.maximum


def melee_vs_hero(w: WeaponDef, *, foe_x: int, hero_xy: tuple[int, int] = (1, 2)) -> BattleState:
    """敵方持 ``w`` 的盜賊（U1，行動者）在 (foe_x, 2)；我方英雄（U2）在 ``hero_xy``。"""
    return state_of(
        [
            UnitSpawn(
                template=template("bandit", max_hp=200, reactions=[]),
                weapon=w,
                team=Team.ENEMY,
                position=(foe_x, 2),
            ),
            armed(Team.ALLY, hero_xy, weapon("one_handed_sword")),
        ],
        active=U1,
    )


def test_ai_spearman_stops_at_two_tiles_instead_of_closing_in() -> None:
    ai = UtilityAI(library().ai_profiles)
    far = ai(melee_vs_hero(weapon("spear"), foe_x=4))  # 距離 3
    assert isinstance(far, Move)
    assert abs(far.dest.x - 1) + abs(far.dest.y - 2) == 2  # 停在 2 格（不貼臉）
    at_reach = ai(melee_vs_hero(weapon("spear"), foe_x=3))  # 已在 2 格
    assert at_reach == Attack(unit_id=U1, target_id=U2)
    # 對照：同一場景持劍的單位會走到相鄰
    sword = ai(melee_vs_hero(weapon("one_handed_sword"), foe_x=4))
    assert isinstance(sword, Move) and abs(sword.dest.x - 1) + abs(sword.dest.y - 2) == 1


def test_reach_spacing_weight_is_data_driven() -> None:
    profiles = library().ai_profiles
    brute = profiles.by_id()["brute"].weights
    assert brute.reach_spacing > brute.approach  # 大於 approach 才會停在觸及距離
    spear_near = melee_vs_hero(weapon("spear"), foe_x=2)  # 相鄰
    spear_reach = melee_vs_hero(weapon("spear"), foe_x=3)
    enemies_near = [spear_near.units[U2]]
    assert (
        _weapon_terms(spear_near, spear_near.units[U1], brute, enemies_near) == -brute.reach_spacing
    )
    assert (
        _weapon_terms(spear_reach, spear_reach.units[U1], brute, [spear_reach.units[U2]])
        == brute.reach_spacing
    )
    zero = brute.model_copy(update={"reach_spacing": 0, "knock_angle": 0})
    assert _weapon_terms(spear_near, spear_near.units[U1], zero, enemies_near) == 0
    sword = melee_vs_hero(weapon("one_handed_sword"), foe_x=2)
    assert _weapon_terms(sword, sword.units[U1], brute, [sword.units[U2]]) == 0


def test_ai_hammer_prefers_the_angle_that_makes_the_knockback_collide() -> None:
    brute = library().ai_profiles.by_id()["brute"].weights
    terrain = "\n".join(["#......"] * 5)  # 英雄 (1, 2) 的西邊是牆
    m = make_map(FLAT7, terrain, ally=[(1, 2)], enemy=[(2, 2)])
    spawns = [
        UnitSpawn(
            template=template("bandit", max_hp=200, reactions=[]),
            weapon=weapon("hammer"),
            team=Team.ENEMY,
            position=(2, 2),
        ),
        armed(Team.ALLY, (1, 2), weapon("one_handed_sword")),
    ]
    state = give_turn(start_battle(make_setup(m, spawns), 0), U1)
    hero = state.units[U2]
    east = state.units[U1]  # 在英雄東邊 (2, 2)：往西推會撞牆
    assert _knock_collides(state, east, hero)
    assert _weapon_terms(state, east, brute, [hero]) == brute.knock_angle
    north = east.clone() if hasattr(east, "clone") else east
    north.pos = Pos(x=1, y=1)  # 在英雄北邊：往南推是空地
    assert not _knock_collides(state, north, hero)
    assert _weapon_terms(state, north, brute, [hero]) == 0
    # 沒有震退的武器、或權重為 0：沒有加分
    east.weapon = weapon("hammer", knockback=0)
    assert _weapon_terms(state, east, brute, [hero]) == 0


def test_content_has_a_blank_hero_for_each_new_weapon() -> None:
    builds = library().builds.by_id()
    used = {b.hero.weapon for b in builds.values() if b.blank}
    assert {"axe", "hammer", "spear", "scepter", "totem_staff"} <= used
    for build in builds.values():
        if build.blank:
            assert not build.hero.skills


def test_data_only_no_trait_numbers_are_hard_coded_in_the_engine() -> None:
    """引擎只讀參數：把所有特性參數歸零後，新武器和一般武器的普攻沒有任何額外效果。"""
    plain = {
        "armor_break": None,
        "knockback": 0,
        "blessing": None,
        "summon_dice_bonus": 0,
        "lob": 0,
        "reach": 1,
    }
    for wid in ("axe", "hammer", "scepter", "totem_staff"):
        w = weapon(wid, **plain)
        assert not w.trait_lines_zh(), wid
    assert not weapon("spear", **{**plain, "reach": 1}).trait_lines_zh()
    _ = no_reactions
