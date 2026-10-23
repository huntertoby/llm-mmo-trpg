"""說明整修補遺 3-41c：召喚物實際值、行為說明、狀態數字、傷害算法句、開局資源預覽、層數。

共同原則：規則說明由程式依實際規則產生，和規則同一個來源。
"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    spawn,
    template,
)
from trpg.api.hero_cards import hero_cards
from trpg.content.battle import Dice, WeaponDef
from trpg.content.skills import EffectSpec
from trpg.engine import Attack, UseSkill, resolve
from trpg.engine.events import DamageDealt, UnitSummoned
from trpg.engine.rules.statuses import effective_attribute, weapon_attribute
from trpg.engine.skills.targeting import damage_parameters
from trpg.engine.summons import summon_stats
from trpg.narrative.skills import CardOwner, skill_card
from trpg.narrative.status_info import status_rules
from trpg.narrative.summon_info import summon_behavior_lines
from trpg.roguelite.start import hero_resources, new_keyword_run, start_resources
from trpg.shared.bonus_text import plain_text
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1 = UnitId("unit_0001")
FLAT = "\n".join(["0000000"] * 7)
SID = "skill_t_card_summon"


# --- 第 2 點：召喚物資訊的實際值 --------------------------------------------------------------


def _summon_effects() -> list[tuple[str, EffectSpec]]:
    lib = library()
    return [
        (skill.id, e)
        for skill in sorted(lib.skills.values(), key=lambda s: s.id)
        for e in skill.effects
        if e.type == "summon"
    ]


@pytest.mark.parametrize(("level", "attr_value"), [(1, 10), (4, 14), (9, 20)])
def test_summon_actual_values_match_the_engine(level: int, attr_value: int) -> None:
    """表格測試：每個召喚技能、不同等級與屬性的施放者——卡片的實際值（HP、傷害骰、移動、護甲）
    和引擎生成的召喚物完全一致。"""
    lib = library()
    for skill_id, spec in _summon_effects():
        skill = lib.skills[skill_id]
        effect = spec.model_dump(mode="json", exclude_none=True)
        test_skill = make_skill(
            SID, {"type": "ground_tile", "range": 4}, [effect], attr=skill.scaling_attr.value
        )
        caster = caster_template([test_skill], attributes={skill.scaling_attr.value: attr_value})
        m = make_map(FLAT, None, ally=[(0, 3)], enemy=[(6, 6)])
        spawns = [spawn(Team.ALLY, (0, 3), caster), spawn(Team.ENEMY, (6, 6), template())]
        state = give_turn(make_state(m, spawns, skills=[test_skill]), U1)
        state.units[U1].level = level
        stats = summon_stats(state, state.units[U1], spec.unit or "", SID, spec)
        result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=2, y=3)))
        events = [e for e in result.events if isinstance(e, UnitSummoned)]
        assert events, skill_id
        unit = result.state.units[events[0].unit_id]
        assert (stats.max_hp, stats.speed, stats.armor_bonus) == (
            unit.max_hp,
            unit.speed,
            unit.armor_bonus,
        ), skill_id
        assert stats.weapon.dice == unit.weapon.dice and stats.weapon.flat == unit.weapon.flat
        assert stats.bonus_permille == unit.summon_bonus_permille
        # 戰鬥中的技能卡（API）也是同一個值
        cards = hero_cards(state, lib, U1).cards
        assert cards[SID].summons[0].hp == unit.max_hp
        assert cards[SID].summons[0].basis == "actual"


def test_baseline_cards_say_they_are_level_one_and_actual_ones_grow() -> None:
    lib = library()
    skill = lib.skills["skill_raise_skeleton"]
    [base] = skill_card(lib, skill).summons
    assert base.basis == "base" and base.basis_zh == "基準值（1 級）"
    spec = skill.effects[0]
    effect = spec.model_dump(mode="json", exclude_none=True)
    test_skill = make_skill(SID, {"type": "ground_tile", "range": 4}, [effect], attr="wil")
    caster = caster_template([test_skill], attributes={"wil": 18})
    m = make_map(FLAT, None, ally=[(0, 3)], enemy=[(6, 6)])
    spawns = [spawn(Team.ALLY, (0, 3), caster), spawn(Team.ENEMY, (6, 6), template())]
    state = give_turn(make_state(m, spawns, skills=[test_skill]), U1)
    state.units[U1].level = 5
    [live] = hero_cards(state, lib, U1).cards[SID].summons
    assert live.basis == "actual" and "5 級" in live.basis_zh
    assert live.hp > base.hp
    assert "5 級" in live.hp_note


# --- 第 3 點：召喚物行為的玩家說明 -------------------------------------------------------------

_DEV_WORDS = ("權重", "初值", "未經模擬", "AI", "weights")


def test_every_ai_profile_has_a_player_description() -> None:
    lib = library()
    for profile in lib.ai_profiles.profiles:
        text = profile.player_description_zh
        assert text.strip(), profile.id
        assert not re.search(r"\d|[A-Za-z_]{3,}", text), (profile.id, text)  # 沒有階段代號與英文
        assert not any(w in text for w in _DEV_WORDS), (profile.id, text)
        assert text != profile.description_zh


def test_summon_behavior_uses_the_player_text_not_the_developer_one() -> None:
    lib = library()
    profiles = {p.id: p for p in lib.ai_profiles.profiles}
    seen = 0
    for summon in lib.ruleset.summons.summons:
        profile = profiles[summon.template.ai_profile or ""]
        lines = summon_behavior_lines(lib, summon)
        joined = "".join(lines)
        assert profile.description_zh not in joined
        if "不移動、不攻擊" not in joined:
            assert profile.player_description_zh in joined
            seen += 1
    assert seen > 0


# --- 第 4 點：狀態說明的數字由欄位產生 ---------------------------------------------------------

_FIELD_NUMBER = re.compile(r"\d+%|[×＋+−-]\s*\d|\d\s*格|減半|一半|兩倍|加倍")


def test_status_descriptions_hold_no_hard_coded_numbers() -> None:
    """說明裡不得再寫死與欄位重複的數字（改由 ``status_rules`` 依欄位產生）。"""
    for status in library().ruleset.statuses.statuses:
        assert not _FIELD_NUMBER.search(status.description_zh), (status.id, status.description_zh)


@pytest.mark.parametrize(
    ("status_id", "expected"),
    [
        ("weaken", "自己造成的攻擊傷害 ×75%"),
        ("hasted", "回合開始時的移動點數（無條件捨去） ×150%"),
        ("slow", "回合開始時的移動點數（無條件捨去） ×50%"),
        ("vulnerable", "×125%"),
        ("guarded", "×70%"),
        ("poison", "受到的治療 ×50%"),
        ("blinded", "只能選擇 2 格以內的單位"),
        ("rallied", "攻擊值 +1"),
        ("empowered", "六個屬性各 +2"),
        ("stance_fury", "力量 +2"),
        ("defending", "防禦值 +25%"),
        ("concealed", "超過 2 格的遠程攻擊"),
    ],
)
def test_status_numbers_come_from_fields(status_id: str, expected: str) -> None:
    lib = library()
    lines = status_rules(lib.ruleset.status_def(status_id), lib)
    assert any(expected in line for line in lines), lines


def test_changing_a_status_field_changes_the_text() -> None:
    lib = library()
    weaken = lib.ruleset.status_def("weaken").model_copy(update={"damage_dealt_permille": 600})
    assert any("×60%" in line for line in status_rules(weaken, lib))
    both = lib.ruleset.status_def("stance_bulwark")
    lines = status_rules(both, lib)
    assert any("×75%" in line for line in lines) and any("×50%" in line for line in lines)


# --- 第 5 點：傷害算法句與引擎一致 -------------------------------------------------------------


def _weapon_ids() -> list[str]:
    lib = library()
    return sorted(w for w, d in lib.weapons.items() if not d.summon_only)


_ATTR_TABLE = [
    {},
    {"str": 14, "dex": 11},
    {"str": 11, "dex": 18, "con": 15, "wis": 17, "wil": 13},
    {"str": 22, "dex": 10, "con": 9, "int": 16, "wis": 12, "wil": 19},
]


@pytest.mark.parametrize("weapon_id", _weapon_ids())
@pytest.mark.parametrize("attrs", _ATTR_TABLE)
def test_basic_attack_formula_matches_engine_bonus(weapon_id: str, attrs: dict[str, int]) -> None:
    """表格測試：武器卡寫的「目前 +N」＝ 引擎普攻實際傷害事件的骰外加成（屬性 × 普攻倍率）；
    雙屬性武器的取法（較高／平均）也一致。"""
    lib = library()
    core = lib.ruleset.core
    weapon = lib.weapons[weapon_id]
    hero = template("hero_mage", reactions=[], skills=[], attributes=attrs)
    foe = template("bandit", reactions=[], armor_bonus=-30, max_hp=999)
    m = make_map(FLAT, None, ally=[(2, 3)], enemy=[(3, 3)])
    spawns = [spawn(Team.ALLY, (2, 3), hero, weapon=weapon_id), spawn(Team.ENEMY, (3, 3), foe)]
    state = give_turn(make_state(m, spawns), U1)
    unit = state.units[U1]
    now = weapon.scaling_value(lambda a: effective_attribute(lib.ruleset, unit, a))
    assert now == weapon_attribute(lib.ruleset, unit)
    line = weapon.attack_formula_zh(core, lambda a: effective_attribute(lib.ruleset, unit, a))
    permille = now * core.basic_attack_attr_multiplier_permille
    assert plain_text(line).endswith(f"（目前 +{permille // 1000}）"), line
    assert ("實際" in line) == (permille % 1000 != 0), line  # 帶小數才有說明標記
    assert line.startswith(f"普攻：{weapon.dice}")
    assert weapon.scaling_names_zh() in line
    # 引擎：實際普攻的傷害事件記錄的骰外加成（只供顯示的欄位）與卡片寫的一致
    foe_id = next(u.id for u in state.units.values() if u.team is Team.ENEMY)
    result = resolve(state, Attack(unit_id=U1, target_id=foe_id))
    hits = [e for e in result.events if isinstance(e, DamageDealt) and e.source_id == U1]
    assert hits, weapon_id
    assert hits[0].scaled_permille == permille
    assert hits[0].flat == weapon.flat


def test_dual_attribute_modes_are_named_on_the_card() -> None:
    lib = library()
    core = lib.ruleset.core
    dual = [w for w in lib.weapons.values() if w.secondary_scaling_attr is not None]
    assert dual
    for weapon in dual:
        how = "取較高" if weapon.attr_mode == "max" else "取平均"
        assert how in weapon.attack_formula_zh(core)
        assert any(how in line for line in weapon.rule_lines_zh(core))


@pytest.mark.parametrize("attr_value", [10, 13, 18])
def test_skill_formula_matches_engine_scaled_value(attr_value: int) -> None:
    """法術技、武器技、治療的算法句：「目前」加成 ＝ 引擎 ``damage_parameters`` 的 ``scaled``。"""
    lib = library()
    core = lib.ruleset.core
    checked = 0
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        dmg = next((e for e in skill.effects if e.type == "damage"), None)
        if dmg is None:
            continue
        hero = template(
            "hero_mage",
            reactions=[],
            skills=[],
            attributes={a.value: attr_value for a in Attribute},
        )
        m = make_map(FLAT, None, ally=[(2, 3)], enemy=[(6, 6)])
        state = make_state(
            m, [spawn(Team.ALLY, (2, 3), hero), spawn(Team.ENEMY, (6, 6), template())]
        )
        unit = state.units[U1]
        params = damage_parameters(state, unit, skill, dmg)
        mine = {a: effective_attribute(state.ruleset, unit, a) for a in Attribute}
        lines = skill.formula_lines_zh(core, unit.weapon, mine.__getitem__)
        damage_line = next(line for line in lines if line.startswith("傷害算法"))
        assert f"（目前 +{params.scaled_permille // 1000}）" in plain_text(damage_line), (
            skill.id,
            damage_line,
        )
        checked += 1
    assert checked > 90


def test_skill_card_formula_lines_without_owner_have_no_current_value() -> None:
    lib = library()
    plain = skill_card(lib, lib.skills["skill_cleave"])
    assert plain.formula_lines and all("目前" not in line for line in plain.formula_lines)
    weapon = lib.weapons["one_handed_sword"]
    owned = skill_card(
        lib,
        lib.skills["skill_cleave"],
        owner=CardOwner(weapon=weapon, attr_get=lambda a: 14),
    )
    assert any("目前 +" in line and str(weapon.dice) in line for line in owned.formula_lines)


def test_weapon_formula_follows_core_multiplier() -> None:
    lib = library()
    weapon = lib.weapons["one_handed_sword"]
    bigger = lib.ruleset.core.model_copy(update={"basic_attack_attr_multiplier_permille": 500})
    assert "× 0.5" in weapon.attack_formula_zh(bigger)


def test_weapon_scaling_value_is_the_single_source() -> None:
    """引擎與卡片共用 ``WeaponDef.scaling_value``：輕武器取較高、重武器取平均、單屬性即該屬性。"""
    base = library().weapons["one_handed_sword"]
    light = base.model_copy(
        update={
            "scaling_attr": Attribute.DEX,
            "secondary_scaling_attr": Attribute.STR,
            "attr_mode": "max",
        }
    )
    heavy = light.model_copy(update={"attr_mode": "mean"})
    values = {Attribute.DEX: 16, Attribute.STR: 11}
    assert light.scaling_value(values.__getitem__) == 16
    assert heavy.scaling_value(values.__getitem__) == 13
    assert base.scaling_value({Attribute.STR: 12}.__getitem__) == 12
    assert isinstance(light, WeaponDef) and Dice is not None


# --- 第 6 點：開局資源預覽 ---------------------------------------------------------------------


@pytest.mark.parametrize("weapon", ["one_handed_sword", "bow", "fire_staff"])
@pytest.mark.parametrize("alloc", [{}, {Attribute.CON: 4}, {Attribute.INT: 2, Attribute.STR: 2}])
def test_start_preview_equals_the_new_run_hero(weapon: str, alloc: dict[Attribute, int]) -> None:
    """開局預覽的 HP／法力／耐力 ＝ 開新一輪建立出的主角（同一個函式），含配點加成。"""
    lib = library()
    full = dict(alloc)
    if sum(full.values()) < 4:
        full[Attribute.WIS] = full.get(Attribute.WIS, 0) + 4 - sum(full.values())
    preview = start_resources(lib, weapon, full)
    keywords = lib.keywords.ids()[:2]
    run = new_keyword_run(lib, weapon, keywords, 7, full)
    core = lib.ruleset.core
    assert preview.hp == run.max_hp_in(core) == run.hp
    assert preview.mana == run.max_mana_in(core) == run.mana
    assert preview.stamina == run.max_stamina_in(core)
    assert preview == hero_resources(core, run.hero)


def test_start_preview_shows_allocation_bonus() -> None:
    lib = library()
    none = start_resources(lib, "one_handed_sword", {})
    con = start_resources(lib, "one_handed_sword", {Attribute.CON: 4})
    strong = start_resources(lib, "one_handed_sword", {Attribute.STR: 4})
    wis = start_resources(lib, "one_handed_sword", {Attribute.WIS: 4})
    assert con.hp > none.hp
    assert strong.stamina > none.stamina
    assert wis.mana > none.mana
    assert none.stamina > 0


# --- 第 1 點：層數 ----------------------------------------------------------------------------


def test_skill_cards_list_the_stacks_they_make_and_use() -> None:
    lib = library()
    made = [(s.id, ref) for s in lib.skills.values() for ref in skill_card(lib, s).stacks]
    assert made
    roles = {ref.role for _, ref in made}
    assert roles == {"makes", "uses"}
    for _, ref in made:
        assert ref.name_zh == lib.ruleset.stack_def(ref.id).name_zh
