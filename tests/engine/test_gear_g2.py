"""裝備詞條第 3、4、5 類（Phase 3G-G2）：技能強化、普攻附加、武器特性強化，與遞減、硬上限的交互。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.test_gear import _item
from trpg.cli.main import main as cli_main
from trpg.content.battle import WeaponDef
from trpg.content.equipment import (
    EquippedAffix,
    ItemDef,
    KeywordAffix,
    Loadout,
    WeaponTraitAffix,
    item_problems,
)
from trpg.content.library import _trait_problems, load_library
from trpg.content.skills import SkillDef
from trpg.content.slots import SLOT_TYPE_OF
from trpg.engine import Attack, BattleState, UseSkill, resolve, start_battle, weapon_traits
from trpg.engine import modifiers as mods
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import EffectBase, PushEffect
from trpg.engine.events import StatusApplied
from trpg.engine.gear import build_gear
from trpg.engine.gear_enhance import (
    attack_keywords,
    gear_area_delta,
    gear_attack_element,
    gear_keyword_damage_permille,
    gear_status_duration,
    geared_weapon,
)
from trpg.engine.rules.weapons import range_damage_permille, weapon_hit_bonus
from trpg.engine.setup import UnitSpawn
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import StatusInstance
from trpg.shared.types import Element, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
type Rolls = Sequence[tuple[str, int | None]]


def _spawn(
    slots: Mapping[str, Rolls],
    *,
    base: str = "hero_fighter",
    weapon: str | None = None,
    skills: Sequence[str] = (),
) -> UnitSpawn:
    s = spawn(Team.ALLY, (0, 0), no_reactions(base, skills=tuple(skills)), weapon)
    order = list(SLOT_TYPE_OF)
    items = tuple(
        _item(slot, slots[slot], weapon=s.weapon.id if slot == "main_hand" else None)
        for slot in sorted(slots, key=order.index)
    )
    return s.model_copy(update={"equipment": Loadout(items=items)})


def _state(hero: UnitSpawn, row: str = "000", seed: int = 0) -> BattleState:
    m = make_map(row, ally=[(0, 0)], enemy=[(len(row) - 1, 0)])
    foe = spawn(Team.ENEMY, (len(row) - 1, 0), no_reactions("bandit"))
    return start_battle(make_setup(m, [hero, foe]), seed)


def _skill(skill_id: str) -> SkillDef:
    return library().skills[skill_id]


# ---------------------------------------------------------------------------
# 第 3 類 技能強化（關鍵字）
# ---------------------------------------------------------------------------


def test_prone_damage_applies_only_to_skills_that_exploit_prone() -> None:
    state = _state(_spawn({"main_hand": [("affix_kw_prone_damage", 100)]}))
    unit, foe = state.units[U1], state.units[U2]
    subject = Subject(foe, foe.xy)
    cleave, bolt = _skill("skill_cleave"), _skill("skill_fire_bolt")
    assert gear_keyword_damage_permille(state, unit, cleave, False) == 100
    assert gear_keyword_damage_permille(state, unit, bolt, False) == 0
    assert mods.damage_permille(state, unit, mods.skill_use(cleave), subject) == 1100
    assert mods.damage_permille(state, unit, mods.skill_use(bolt), subject) == 1000
    assert mods.damage_permille(state, unit, mods.ATTACK, subject) == 1000  # 普攻不選取


@pytest.mark.parametrize(
    ("slots", "expected"),
    [
        (("main_hand",), 100),
        (("main_hand", "neck"), 150),  # 100 + 50%
        (("main_hand", "neck", "ring_1"), 175),  # 100 + 50% + 25%
        (("main_hand", "neck", "ring_1", "ring_2"), 175),  # 第 4 件 0%
    ],
)
def test_keyword_damage_diminishes_by_copies(slots: tuple[str, ...], expected: int) -> None:
    # 測試用物品不檢查欄位，這裡只驗遞減
    state = _state(_spawn({s: [("affix_kw_prone_damage", 100)] for s in slots}))
    unit = state.units[U1]
    assert gear_keyword_damage_permille(state, unit, _skill("skill_cleave"), False) == expected


def test_total_damage_bonus_cap_includes_skill_modifiers() -> None:
    """全身傷害加成 +50% 是所有來源合計：裝備、技能強化與修正型被動一起算。"""
    hero = _spawn(
        {
            "main_hand": [("affix_kw_prone_damage", 150)],
            "neck": [("affix_kw_prone_damage", 150)],
            "ring_1": [("affix_cost_glass", None)],
        },
        skills=("skill_searing_scar",),
    )
    state = _state(hero)
    unit, foe = state.units[U1], state.units[U2]
    foe.statuses = [StatusInstance(status_id="burning", remaining=3)]
    subject = Subject(foe, foe.xy)
    use = mods.skill_use(_skill("skill_cleave"))
    # 修正型被動 100 ＋ 玻璃 200 ＋ 技能強化 150 ＋ 75 ＝ 525 → 截斷為 500
    assert mods.damage_permille(state, unit, use, subject) == 1500
    # 沒有被動：200 ＋ 225 ＝ 425，不截斷
    unit.skills = tuple(s for s in unit.skills if s != "skill_searing_scar")
    assert mods.damage_permille(state, unit, use, subject) == 1425


def test_burn_duration_follows_the_keyword_not_the_skill_name() -> None:
    state = _state(_spawn({"main_hand": [("affix_kw_burn_duration", None)]}))
    unit = state.units[U1]
    bolt = _skill("skill_fire_bolt")
    assert gear_status_duration(state, unit, bolt, False, "burning") == 1
    assert gear_status_duration(state, unit, bolt, False, "frozen") == 0
    assert gear_status_duration(state, unit, _skill("skill_cleave"), False, "burning") == 0
    assert mods.status_duration_bonus(state, unit, mods.skill_use(bolt), "burning") == 1


def test_burn_duration_two_copies_still_one_extra_round() -> None:
    state = _state(
        _spawn(
            {
                "main_hand": [("affix_kw_burn_duration", None)],
                "neck": [("affix_kw_burn_duration", None)],
            }
        )
    )
    unit = state.units[U1]
    assert gear_status_duration(state, unit, _skill("skill_fire_bolt"), False, "burning") == 1
    assert [a.weight_permille for a in unit.gear.active_affixes("keyword")] == [1000, 500]


def test_fire_bolt_burns_one_round_longer_with_the_affix() -> None:
    def burn_rounds(slots: Mapping[str, Rolls]) -> int | None:
        hero = _spawn(slots, base="hero_mage", skills=("skill_fire_bolt",))
        state = give_turn(_state(hero, "0000"), U1)
        state = with_rolls(state, [(20, 19)])
        result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U2))
        applied = [
            e for e in result.events if isinstance(e, StatusApplied) and e.status_id == "burning"
        ]
        assert applied
        return applied[0].duration

    plain = burn_rounds({})
    boosted = burn_rounds({"main_hand": [("affix_kw_burn_duration", None)]})
    assert plain is not None and boosted == plain + 1


def test_shock_area_grows_a_skill_that_creates_charged() -> None:
    lib = library()
    state = _state(_spawn({"neck": [("affix_kw_shock_area", None)]}))
    unit = state.units[U1]
    plain = _state(_spawn({})).units[U1]
    cleave = _skill("skill_cleave")
    assert cleave.shape.type == "cone"
    storm = cleave.model_copy(
        update={
            "effects": tuple(
                e.model_copy(update={"element": Element.LIGHTNING}) if e.type == "damage" else e
                for e in cleave.effects
            )
        }
    )
    assert (
        "charged"
        in lib.ruleset.skill_keywords(storm.model_copy(update={"id": "skill_t_storm"})).makes
    )
    storm = storm.model_copy(update={"id": "skill_t_storm"})
    assert gear_area_delta(state, unit, storm) == 1
    assert mods.shaped_skill(state, plain, storm) is storm
    grown = mods.shaped_skill(state, unit, storm).shape
    spec = lib.ruleset.shape_def("cone").params["size"]
    assert storm.shape.size is not None and grown.size == min(storm.shape.size + 1, spec.max)
    assert gear_area_delta(state, unit, cleave) == 0  # 沒有製造帶電的技能不變
    # 現有的製造帶電技能：選取成立，形狀沒有大小參數時不變
    chain = _skill("skill_chain_lightning")
    assert gear_area_delta(state, unit, chain) == 1
    assert mods.shaped_skill(state, unit, chain).shape == chain.shape


def test_shock_area_never_exceeds_the_shape_maximum() -> None:
    lib = library()
    state = _state(_spawn({"neck": [("affix_kw_shock_area", None)]}))
    unit = state.units[U1]
    cleave = _skill("skill_cleave")
    maxed = cleave.shape.model_copy(
        update={"size": lib.ruleset.shape_def("cone").params["size"].max}
    )
    storm = cleave.model_copy(
        update={
            "id": "skill_t_storm",
            "shape": maxed,
            "effects": tuple(
                e.model_copy(update={"element": Element.LIGHTNING}) if e.type == "damage" else e
                for e in cleave.effects
            ),
        }
    )
    assert mods.shaped_skill(state, unit, storm).shape == maxed


# ---------------------------------------------------------------------------
# 第 4 類 普攻附加
# ---------------------------------------------------------------------------


def test_attack_lightning_changes_physical_attacks_only() -> None:
    state = _state(_spawn({"main_hand": [("affix_attack_lightning", None)]}))
    unit = state.units[U1]
    assert gear_attack_element(unit) is Element.LIGHTNING
    assert mods.damage_element(state, unit, mods.ATTACK, Element.PHYSICAL) is Element.LIGHTNING
    # 3I-6：普攻附加 ＞ 武器本身的元素（優先順序見 test_attack_element.py）；普攻忽略傳入的 base
    assert mods.damage_element(state, unit, mods.ATTACK, Element.FIRE) is Element.LIGHTNING
    cleave = mods.skill_use(_skill("skill_cleave"))
    assert mods.damage_element(state, unit, cleave, Element.PHYSICAL) is Element.PHYSICAL
    assert "charged" in attack_keywords(state, unit).makes  # 普攻製造帶電


def test_attack_lightning_is_not_offered_on_elemental_staffs() -> None:
    lib = library()
    item = ItemDef.model_validate(
        {
            "id": "item_t_staff",
            "name_zh": "測試法杖",
            "slot_type": "weapon",
            "weapon": "lightning_staff",
            "affixes": [{"affix": "affix_attack_lightning"}],
        }
    )
    assert item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment)


def test_attack_mark_applies_marked_after_a_hit() -> None:
    def marks(slots: Mapping[str, Rolls]) -> list[StatusApplied]:
        state = give_turn(_state(_spawn(slots), "00"), U1)
        result = resolve(with_rolls(state, [(20, 19)]), Attack(unit_id=U1, target_id=U2))
        return [
            e for e in result.events if isinstance(e, StatusApplied) and e.status_id == "marked"
        ]

    found = marks({"main_hand": [("affix_attack_mark", None)]})
    assert len(found) == 1 and found[0].duration == 1 and found[0].target_id == U2
    assert marks({}) == []


def test_attack_mark_same_id_counts_once() -> None:
    items = tuple(_item(s, [("affix_attack_mark", None)]) for s in ("main_hand", "neck"))
    gear = build_gear(Loadout(items=items), library().ruleset.equipment)
    assert len(gear.active_affixes("attack")) == 1


def test_attack_status_gets_keyword_duration_bonus() -> None:
    """普攻命中附帶的「標記」製造標記關鍵字；技能強化詞條（include_attack）可以讓它多 1 回合。"""
    lib = library()
    boost = lib.affixes["affix_kw_burn_duration"].model_copy(
        update={"id": "affix_kw_mark_duration", "status": "marked", "keyword": "marked"}
    )
    neck = _item("neck", []).model_copy(
        update={"affixes": (EquippedAffix(affix=boost, value=None),)}
    )
    hero = _spawn({"main_hand": [("affix_attack_mark", None)]})
    hero = hero.model_copy(update={"equipment": Loadout(items=(*hero.equipment.items, neck))})
    state = give_turn(_state(hero, "00"), U1)
    result = resolve(with_rolls(state, [(20, 19)]), Attack(unit_id=U1, target_id=U2))
    marked = [e for e in result.events if isinstance(e, StatusApplied) and e.status_id == "marked"]
    assert marked and marked[0].duration == 2


# ---------------------------------------------------------------------------
# 第 5 類 武器特性強化
# ---------------------------------------------------------------------------


def _weapon_of(slots: Mapping[str, Rolls], weapon: str) -> WeaponDef:
    """不檢查穿戴合法性（同一個武器詞條在不同欄位重複），直接算遞減後的武器資料。"""
    order = list(SLOT_TYPE_OF)
    items = tuple(
        _item(slot, slots[slot], weapon=weapon if slot == "main_hand" else None)
        for slot in sorted(slots, key=order.index)
    )
    rules = library().ruleset.equipment
    gear = build_gear(Loadout(items=items), rules)
    return geared_weapon(library().weapons[weapon], gear, rules)


def test_hammer_knockback_plus_one() -> None:
    assert library().weapons["hammer"].knockback == 1
    geared = _weapon_of({"main_hand": [("affix_trait_hammer_knockback", None)]}, "hammer")
    assert geared.knockback == 2


def test_hammer_knockback_over_the_displace_cap_becomes_collisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """推擊距離上限 2：超過的格數改成撞擊傷害（額外撞擊次數）。"""
    hammer = library().weapons["hammer"].model_copy(update={"knockback": 2})
    hero = _spawn({"main_hand": [("affix_trait_hammer_knockback", None)]}, weapon="hammer")
    hero = hero.model_copy(update={"weapon": hammer})
    state = give_turn(_state(hero, "00"), U1)
    assert state.units[U1].weapon.knockback == 3
    pushes: list[PushEffect] = []
    original = execute

    def spy(ctx: Ctx, batch: list[EffectBase]) -> None:
        pushes.extend(e for e in batch if isinstance(e, PushEffect))
        original(ctx, batch)

    monkeypatch.setattr(weapon_traits, "execute", spy)
    resolve(with_rolls(state, [(20, 19)]), Attack(unit_id=U1, target_id=U2))
    assert pushes and pushes[0].distance == 2 and pushes[0].extra_collisions == 1


def test_axe_sunder_plus_one_round() -> None:
    base = library().weapons["axe"].armor_break
    assert base is not None
    geared = _weapon_of({"main_hand": [("affix_trait_axe_sunder", None)]}, "axe")
    assert geared.armor_break is not None and geared.armor_break.rounds == base.rounds + 1
    twice = _weapon_of(
        {
            "main_hand": [("affix_trait_axe_sunder", None)],
            "neck": [("affix_trait_axe_sunder", None)],
        },
        "axe",
    )
    assert twice.armor_break is not None and twice.armor_break.rounds == base.rounds + 1


def test_longgun_point_blank_penalty_is_halved() -> None:
    base = library().weapons["longgun"]
    geared = _weapon_of({"main_hand": [("affix_trait_longgun_pointblank", None)]}, "longgun")
    close = next(m for m in geared.range_mod if m.min_distance == 1)
    assert (close.hit, close.damage_permille) == (-1, 750)  # -2/500 → -1/750
    far = next(m for m in geared.range_mod if m.min_distance == 4)
    assert far == next(m for m in base.range_mod if m.min_distance == 4)  # 加成不變


def test_longgun_point_blank_two_copies_diminish() -> None:
    geared = _weapon_of(
        {
            "main_hand": [("affix_trait_longgun_pointblank", None)],
            "neck": [("affix_trait_longgun_pointblank", None)],
        },
        "longgun",
    )
    close = next(m for m in geared.range_mod if m.min_distance == 1)
    # 減少 50% ＋ 25% ＝ 75%：倍率 250‰ → -2 → 0（無條件捨去）、傷害 500 → 875
    assert (close.hit, close.damage_permille) == (0, 875)


def test_weapon_trait_only_applies_to_its_own_weapon() -> None:
    sword = _weapon_of({"main_hand": [("affix_trait_hammer_knockback", None)]}, "one_handed_sword")
    assert sword == library().weapons["one_handed_sword"]


def test_weapon_trait_changes_flow_into_the_hit_resolution() -> None:
    plain = _state(_spawn({}, weapon="longgun")).units[U1]
    geared = _state(
        _spawn({"main_hand": [("affix_trait_longgun_pointblank", None)]}, weapon="longgun")
    ).units[U1]
    assert weapon_hit_bonus(geared, 1) == weapon_hit_bonus(plain, 1) + 1
    assert range_damage_permille(geared, 1) == 750 and range_damage_permille(plain, 1) == 500


def test_crit_range_never_goes_below_the_cap() -> None:
    lib = library()
    rules = lib.ruleset.equipment
    affix = WeaponTraitAffix.model_validate(
        {
            "id": "affix_trait_t_crit",
            "category": "weapon_trait",
            "name_zh": "測試",
            "slots": ["weapon"],
            "weapons": ["longgun"],
            "param": "steady.crit_range",
            "delta": 5,
        }
    )
    item = _item("main_hand", [], weapon="longgun")
    item = item.model_copy(update={"affixes": (EquippedAffix(affix=affix, value=None),)})
    gear = build_gear(Loadout(items=(item,)), rules)
    geared = geared_weapon(lib.weapons["longgun"], gear, rules)
    assert geared.steady is not None and geared.steady.crit_range == 2  # 20 - 2 = 18 為下限
    assert geared.crit_range == 20


def test_unresolvable_trait_param_fails_at_load_time() -> None:
    lib = load_library()
    bad = lib.affixes["affix_trait_longgun_pointblank"].model_copy(update={"param": "point_blank"})
    assert isinstance(bad, WeaponTraitAffix)
    assert _trait_problems(bad, lib.weapons)
    ghost = bad.model_copy(update={"param": "knockback", "weapons": ("ghost",)})
    assert any("未知的武器" in p for p in _trait_problems(ghost, lib.weapons))
    good = lib.affixes["affix_trait_hammer_knockback"]
    assert isinstance(good, WeaponTraitAffix) and not _trait_problems(good, lib.weapons)


def test_every_whitelist_keyword_and_trait_resolves_against_the_content() -> None:
    lib = load_library()
    ids = set(lib.ruleset.keywords.ids())
    for affix in lib.affixes.values():
        if affix.category == "keyword":
            assert isinstance(affix, KeywordAffix) and affix.keyword in ids
        if affix.category == "weapon_trait":
            for weapon in affix.weapons:
                assert weapon in lib.weapons


# ---------------------------------------------------------------------------
# 含裝備的一場 --log-json + replay
# ---------------------------------------------------------------------------


def test_g2_gear_battle_log_json_and_replay(tmp_path: Path) -> None:
    log = tmp_path / "g2.json"
    args = ["battle", "--map", "test_flat_6x6", "--allies", "gear_tester_g2"]
    args += ["--enemies", "bandit,bandit", "--seed", "7", "--log-json", str(log)]
    assert cli_main(args) == 0
    text = log.read_text(encoding="utf-8")
    assert "trpg-battle-log/67" in text and '"affix_trait_hammer_knockback"' in text
    assert cli_main(["battle", "replay", str(log)]) == 0
