"""Q 版技能主圖的推導 ``SkillIcon.art``（Phase QI-2a；需求 3.3，規格第 7 節 T-A1～T-A6、T-A8）。

- T-A1：推導表每一列至少一招實際技能（或「合成」：實際技能複製後改最少的欄位），斷言結果，而且斷言
  這招**確實走到這一列**（照順序呼叫拆出的各列函式，看第一個成立的是哪一列）；
- T-A2：402 招逐招比對美術的參考實作 ``docs/art/sample/tools/qskills_derive.py``（只讀載入）；
- T-A3：``content/skill_icon_art.yaml`` 和參考實作的同名常數逐表、逐筆、照順序相同（``terrain`` 換算
  除外）。**之後美術 PM 改表時，這一項要和表一起改（不是放寬）**；
- T-A4、T-A5：``icon_prop`` 插在道具第 2、3 列之間；出手吃最後決定的道具；
- T-A6：清單外的 ``icon_prop`` 執行期退回推導、不丟例外（D3）；
- T-A8：缺欄位、型別錯的草稿與工坊示範每一步都回傳 ``IconArt``。
"""

from __future__ import annotations

import importlib.util
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from tests.engine.helpers import PROJECT_ROOT, library
from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE
from trpg.content.skills import SkillDef
from trpg.narrative.skill_icon import icon_of, skill_icon
from trpg.narrative.skill_icon_art import (
    IconArt,
    IconArtRules,
    _action_damage,
    _action_effect,
    _action_setup,
    _action_status,
    _icon_prop,
    _is_modifier,
    _prop_modifier,
    _prop_special,
    _prop_spell,
    _read,
    default_icon_art_rules,
    derive_art,
    element_tags,
    icon_art_rules,
)

REFERENCE = PROJECT_ROOT / "docs" / "art" / "sample" / "tools" / "qskills_derive.py"
SKILLS_DIR = PROJECT_ROOT / "content" / "skills"
ART_FIELDS = ("prop", "motion", "act", "tint", "spark")


@cache
def _ref() -> ModuleType:
    """美術的參考實作（``docs/art/`` 不是套件；只讀載入，不改它）。"""
    spec = importlib.util.spec_from_file_location("qskills_derive", REFERENCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def _raw() -> dict[str, dict[str, Any]]:
    """技能 YAML 原文（參考實作吃的就是這個）。"""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(SKILLS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[data["id"]] = data
    return out


def _rules() -> IconArtRules:
    return icon_art_rules(library())


def _art(skill: SkillDef) -> IconArt:
    """正式路徑：``skill_icon(SkillDef)``（吃 ``model_dump``，沒填的鍵是 ``None``）。"""
    art = skill_icon(skill, _rules()).art
    assert art is not None
    return art


# ---- 第幾列（照順序呼叫拆出的各列函式，第一個成立的那列） ----------------------------------------


def _dump(skill: SkillDef) -> dict[str, Any]:
    return skill.model_dump(mode="json")


def prop_row(skill: SkillDef) -> str:  # noqa: PLR0911 （一列一個 return，和規則表逐列對照）
    raw, rules = _dump(skill), _rules()
    s = _read(raw, element_tags(raw))
    special = _prop_special(s, rules)
    if special is not None:
        return "1" if special.startswith("form:") else "2"
    if _icon_prop(raw, rules) is not None:
        return "2b"
    if _prop_modifier(s, rules) is not None:
        return "3"
    if s.weapon_req in ("ranged", "melee"):
        return "4a" if s.weapon_req == "ranged" else "4b"
    spell = _prop_spell(s, rules)
    el = s.elements[0] if s.elements else None
    if spell.startswith("summon:"):
        return "5"
    if el not in (None, "physical"):
        return "6"
    row = {"el:water": "7", "el:arcane": "8"}.get(spell, "9")
    return "last" if row == "9" and _art(skill).prop != "none" else row


def motion_row(skill: SkillDef) -> str:
    raw, rules = _dump(skill), _rules()
    kind = (raw.get("shape") or {}).get("type")
    if kind in rules.shape_motion:
        return "1"
    if _art(skill).prop.startswith("w:") and raw.get("weapon_req") == "melee":
        return "2"
    return "3" if _art(skill).motion == "swing" else "4"


def act_row(skill: SkillDef) -> str:
    raw, rules = _dump(skill), _rules()
    s = _read(raw, element_tags(raw))
    if _action_setup(s, rules) is not None:
        return "1" if _is_modifier(s) else "2"
    if _action_effect(s, rules.effect_action, rules) is not None:
        return "3-13"
    if _action_status(s, rules) is not None:
        return "14"
    if _action_effect(s, rules.late_action, rules) is not None:
        return "15-20"
    act, _tint = _action_damage(s, rules)
    return {"finisher": "21", "combo": "22", "hit": "23"}.get(act, "24")


# ---- 合成（實際技能複製後改最少的欄位；報告列出） ------------------------------------------


def _copy(skill_id: str, **update: Any) -> SkillDef:
    return library().skills[skill_id].model_copy(update=update)


def _no_effect_primitive() -> str:
    """不在任何記號表、也不是傷害或施加狀態的原語（記號第 24 列用）；照 ID 排序取第一個。"""
    rules = _rules()
    taken = {e for group, _a, _t in (*rules.effect_action, *rules.late_action) for e in group}
    taken |= {"damage", "apply_status"}
    free = sorted(p for p in library().ruleset.primitives.by_id() if p not in taken)
    return free[0]


SYNTH: dict[str, Any] = {
    # 道具第 3 列「攻擊遠程」：普攻精通改成遠程
    "mod_attack_ranged": lambda: _copy("skill_attack_mastery", weapon_req="ranged"),
    # 道具第 3 列「其餘」（修正技）：震懾餘波 QI-2d 填了 w:roar 後走 2b 列，
    # 這一列沒有別的實際技能，拿掉 icon_prop 當合成
    "lingering_roar_no_prop": lambda: _copy("skill_lingering_roar", icon_prop=None),
    # 道具第 4a 列「槍」：穿甲箭改名
    "ranged_gun": lambda: _copy("skill_armor_piercing_arrow", name_zh="穿甲槍擊"),
    # 道具第 4b 列名稱關鍵字（已被 icon_prop 取代、現在沒有實例）：孤注一擲改名
    "melee_fist": lambda: _copy("skill_all_in", name_zh="孤注一拳"),
    "melee_dagger": lambda: _copy("skill_all_in", name_zh="孤注一匕"),
    "melee_spear": lambda: _copy("skill_all_in", name_zh="孤注一槍"),
    "melee_axe": lambda: _copy("skill_all_in", name_zh="孤注一斧"),
    "melee_scythe": lambda: _copy("skill_all_in", name_zh="孤注一鐮"),
    "melee_hammer": lambda: _copy("skill_all_in", name_zh="孤注一鎚"),
    # 道具「最後」列：沒有元素、沒有武器大類的傷害招（捕獸夾拿掉放陷阱與狀態，只留傷害）
    "last_none_hit": lambda: _copy(
        "skill_bear_trap",
        effects=tuple(e for e in library().skills["skill_bear_trap"].effects if e.type == "damage"),
    ),
    # 出手第 1 列「沒有形狀」：用 dict 拿掉 shape（SkillDef 的 shape 必填）
    # 記號第 24 列：沒有傷害、沒有其他效果
    "act_none": lambda: _copy(
        "skill_bear_trap",
        effects=(
            library()
            .skills["skill_bear_trap"]
            .effects[0]
            .model_copy(update={"type": _no_effect_primitive()}),
        ),
    ),
}


def _skill(key: str) -> SkillDef:
    return SYNTH[key]() if key in SYNTH else library().skills[key]


# ---- T-A1 --------------------------------------------------------------------------------------

PROP_ROWS = [
    ("skill_form_bear", "1", "form:bear"),
    ("skill_akimbo_burst", "2", "w:dual_pistol"),
    ("skill_ambush_stab", "2b", "w:dagger"),
    ("skill_beam_of_mercy", "3", "el:holy"),
    ("skill_summon_elite", "3", "summon:spirit"),
    ("skill_timber_piercer", "3", "w:bow"),
    ("skill_attack_mastery", "3", "w:sword"),
    ("mod_attack_ranged", "3", "w:bow"),  # 合成
    ("skill_burning_shove", "3", "w:fist"),
    ("lingering_roar_no_prop", "3", "w:tome/book"),  # 合成（QI-2d）
    ("skill_lingering_roar", "2b", "w:roar"),  # QI-2d：#151 補充填 w:roar
    ("skill_rng_static_bolt", "4a", "w:crossbow"),
    ("skill_oil_spark_throw", "4a", "w:kunai"),
    ("ranged_gun", "4a", "w:longgun"),  # 合成
    ("skill_armor_piercing_arrow", "4a", "w:bow"),
    ("skill_shadow_ambush", "4b", "w:dagger"),
    ("skill_palm_strike", "4b", "w:fist"),
    ("skill_shield_bash", "4b", "w:kite_shield"),
    ("skill_whip_crack", "4b", "w:whip"),
    ("melee_fist", "4b", "w:fist"),  # 合成
    ("melee_dagger", "4b", "w:dagger"),  # 合成
    ("melee_spear", "4b", "w:spear"),  # 合成
    ("melee_axe", "4b", "w:axe"),  # 合成
    ("melee_scythe", "4b", "w:scythe"),  # 合成
    ("melee_hammer", "4b", "w:hammer"),  # 合成
    ("skill_cleave", "4b", "w:greatsword"),
    ("skill_all_in", "4b", "w:sword"),
    ("skill_fsum_cinder_pact", "5", "summon:spirit"),
    ("skill_air_burst", "6", "el:wind"),
    ("skill_downpour", "7", "el:water"),
    ("skill_afterimage_vow", "8", "el:arcane"),
    ("skill_bear_trap", "9", "none"),
    ("last_none_hit", "last", "el:arcane"),  # 合成
]


@pytest.mark.parametrize(("key", "row", "prop"), PROP_ROWS)
def test_prop_table_rows(key: str, row: str, prop: str) -> None:
    skill = _skill(key)
    assert prop_row(skill) == row
    assert _art(skill).prop == prop


MOTION_ROWS = [
    ("skill_chain_lightning", "1", "chain"),
    ("skill_ember_trail", "1", "thrust"),
    ("skill_ashen_oath", "1", "sweep"),
    ("skill_air_burst", "1", "spin"),
    ("skill_all_in_chant", "1", "area"),
    ("skill_cinder_dive", "1", "area"),
    ("skill_rune_burst", "1", "area"),
    ("skill_bear_trap", "1", "place"),
    ("skill_afterimage_vow", "1", "aura"),
    ("skill_shadow_backstab", "2", "thrust"),
    ("skill_all_in", "2", "swing"),
    ("skill_rx_dread_glare", "3", "swing"),
    ("skill_akimbo_burst", "4", "shot"),
]


@pytest.mark.parametrize(("key", "row", "motion"), MOTION_ROWS)
def test_motion_table_rows(key: str, row: str, motion: str) -> None:
    skill = _skill(key)
    assert motion_row(skill) == row
    assert _art(skill).motion == motion


def test_motion_without_shape_is_aura() -> None:
    """出手第 1 列「沒有形狀」（合成：SkillDef 的形狀必填，所以拿 dict 去掉 ``shape``）。"""
    raw = _dump(library().skills["skill_cleave"])
    raw.pop("shape")
    art = icon_of(raw, _rules()).art
    assert art is not None and art.motion == "aura"
    assert None in _rules().shape_motion


ACT_ROWS = [
    ("skill_burning_shove", "1", "modify", "fire"),
    ("skill_attack_mastery", "1", "modify", "blood"),
    ("skill_charged_cleave", "2", "builder", None),
    ("skill_form_bear", "3-13", "transform", None),
    ("skill_fsum_cinder_pact", "3-13", "summon", "fire"),
    ("skill_detonate_burning", "3-13", "detonate", "fire"),
    ("skill_bear_trap", "3-13", "trap", None),
    ("skill_banish", "3-13", "step", None),
    ("skill_death_spiral", "3-13", "dash", None),
    ("skill_gear_grapple", "3-13", "pull", None),
    ("skill_air_burst", "3-13", "push", None),
    ("skill_bone_crusher", "3-13", "knockdown", None),
    ("skill_bloodlust", "3-13", "heal", None),
    ("skill_ember_ward", "3-13", "shield", None),
    ("skill_blade_dance", "14", "dot", None),
    ("skill_deep_freeze", "14", "bind", None),
    ("skill_annotated_frost", "14", "slow", None),
    ("skill_hex_bolt", "14", "mark", None),
    ("skill_blinding_dark", "14", "curse", None),
    ("skill_fire_enchant", "14", "buff", None),
    ("skill_ashen_oath", "15-20", "surface", "fire"),
    ("skill_earth_collapse", "15-20", "surface", "stone"),
    ("skill_overcurrent", "15-20", "builder", None),
    ("skill_combo_finisher", "15-20", "finisher", None),
    ("skill_blessing_thief", "15-20", "curse", None),
    ("skill_afterimage_vow", "15-20", "buff", None),
    ("skill_ash_harvest", "21", "finisher", None),
    ("skill_akimbo_burst", "22", "combo", None),
    ("skill_all_in", "23", "hit", None),
    ("act_none", "24", "buff", None),  # 合成
]


@pytest.mark.parametrize(("key", "row", "act", "tint"), ACT_ROWS)
def test_act_table_rows(key: str, row: str, act: str, tint: str | None) -> None:
    """記號與染色。染色 ``None`` 的列只斷言記號（染色由 T-A2 逐招比對參考實作）。"""
    skill = _skill(key)
    assert act_row(skill) == row
    art = _art(skill)
    assert art.act == act
    if tint is not None:
        assert art.tint == tint


@pytest.mark.parametrize(
    ("skill_id", "spark"),
    [
        ("skill_frost_ledge_cleave", "ice"),
        ("skill_oil_spark_throw", "fire"),
        ("skill_cleave", None),
    ],
)
def test_spark_is_the_first_variant_element(skill_id: str, spark: str | None) -> None:
    assert _art(library().skills[skill_id]).spark == spark


# ---- T-A2 --------------------------------------------------------------------------------------


def test_every_skill_matches_the_reference_implementation() -> None:
    """402 招：沒填 ``icon_prop`` 的與 ``derive()`` 五欄完全相同；有填的 ``prop`` ＝
    ``icon_prop``、``motion`` ＝ 用 ``icon_prop`` 重算、其餘相同；元素底等於 ``elements[0]``／
    ``[1]``。差異必須 0。"""
    ref, lib = _ref(), library()
    raws = _raw()
    assert len(raws) == len(lib.skills) == 404  # BAL-21b lava_splash、BAL-21c rift_flicker
    diffs: list[str] = []
    filled = 0
    for skill_id, raw in raws.items():
        icon = skill_icon(lib.skills[skill_id], _rules())
        expected = ref.derive(raw)
        want = {k: expected[k] for k in ART_FIELDS}
        if raw.get("icon_prop"):
            filled += 1
            want["prop"] = raw["icon_prop"]
            want["motion"] = ref.derive_motion(raw, raw["icon_prop"])
        assert icon.art is not None
        got = icon.art.model_dump()
        els = (icon.elements[:1] or (None,))[0], (icon.elements[1:2] or (None,))[0]
        if got != want or els != (expected["el"], expected["el2"]):
            diffs.append(f"{skill_id}: {got} != {want}")
    assert filled == 47  # 36 招＋#151 補充新填 11 招（QI-2d）
    assert diffs == []


def test_model_dump_none_keys_count_as_missing() -> None:
    """``model_dump`` 帶出沒填的鍵（值 ``None``）：修正技 11 招的染色不能因此全變成 ``blood``。"""
    lib = library()
    modifiers = [s for s in lib.skills.values() if s.kind == "modifier"]
    tints = {s.id: _art(s).tint for s in modifiers}
    assert len({t for t in tints.values() if t is not None}) > 1
    for skill in modifiers:
        assert _art(skill) == derive_art(
            skill.model_dump(mode="json", exclude_none=True), _rules()
        ), skill.id


# ---- T-A3 --------------------------------------------------------------------------------------


def test_content_table_equals_the_reference_constants() -> None:
    table, ref = library().icon_art, _ref()
    assert table is not None
    assert [(r.weapon, r.look) for r in table.weapon_look] == list(ref.WEAPON_LOOK.items())
    assert [(r.words, r.kind) for r in table.melee_words] == list(ref.MELEE_WORDS)
    assert [(r.words, r.kind) for r in table.ranged_words] == list(ref.RANGED_WORDS)
    assert table.thrust_props == ref.THRUST_PROPS
    assert table.ranged_kinds == ref.RANGED_KINDS
    assert [(r.unit, r.group) for r in table.summon_group] == list(ref.SUMMON_GROUP.items())
    assert [(r.tag, r.prop) for r in table.mod_tag_prop] == list(ref.MOD_TAG_PROP.items())
    for name in (
        "summon_tint",
        "mod_tint",
        "dot",
        "bind",
        "curse",
        "status_tint",
        "cond_tint",
        "surface_tint",
    ):
        rows = getattr(table, name)
        assert [(r.key, r.tint) for r in rows] == list(getattr(ref, name.upper()).items()), name
    assert [(r.effects, r.act) for r in table.effect_action] == list(ref.EFFECT_ACTION)
    assert all(r.tint is None for r in table.effect_action)
    terrain = {"terrain": ("surface", "stone")}  # 載入後換算（需求 3.3 第 15～20 列）
    want_late = [(g, *terrain.get(a, (a, None))) for g, a in ref.LATE_ACTION]
    assert [(r.effects, r.act, r.tint) for r in table.late_action] == want_late
    assert [(r.shape, r.motion) for r in table.shape_motion] == list(ref.SHAPE_MOTION.items())
    assert table.needs_prop == ref.NEEDS_PROP


def test_default_rules_are_the_content_rules() -> None:
    """沒有內容庫時（``art=None``）讀的預設表和內容庫上的相同。"""
    assert default_icon_art_rules() == _rules()


# ---- T-A4、T-A5 --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("skill_id", "value", "prop"),
    [
        ("skill_form_bear", "w:axe", "form:bear"),  # 第 1 列優先
        ("skill_akimbo_burst", "w:sword", "w:dual_pistol"),  # 第 2 列優先
        ("skill_attack_mastery", "w:hammer", "w:hammer"),  # 蓋過第 3 列
        ("skill_rng_static_bolt", "w:longgun", "w:longgun"),  # 蓋過第 4a 列
        ("skill_air_burst", "w:fist", "w:fist"),  # 蓋過第 6 列
    ],
)
def test_icon_prop_sits_between_rows_2_and_3(skill_id: str, value: str, prop: str) -> None:
    skill = _copy(skill_id, icon_prop=value)
    assert _art(skill).prop == prop


MOTION_CHANGED = (
    "skill_ambush_stab",
    "skill_ember_bite",
    "skill_flurry_jab",
    "skill_ground_finish",
    "skill_marrow_thorn",
    "skill_venom_blade",
)


def test_motion_follows_the_final_prop() -> None:
    """``icon_prop`` 改了出手的 6 招（規格第 0 節第 6 列）：照新道具重算，而且和沒填時不同。"""
    ref, lib = _ref(), library()
    changed = []
    for skill_id, raw in _raw().items():
        if not raw.get("icon_prop"):
            continue
        plain = _art(lib.skills[skill_id].model_copy(update={"icon_prop": None}))
        art = _art(lib.skills[skill_id])
        assert art.motion == ref.derive_motion(raw, raw["icon_prop"]), skill_id
        if art.motion != plain.motion:
            changed.append(skill_id)
    assert tuple(changed) == MOTION_CHANGED
    assert _art(lib.skills["skill_ember_bite"]).motion == "shot"


def test_icon_prop_none_still_gets_the_arcane_prop_for_marks_on_a_prop() -> None:
    """``icon_prop: none`` 配畫在道具上的記號（孤注一擲的 ``hit``）→ ``el:arcane``，出手用它算。"""
    raw = _raw()["skill_all_in"]
    skill = _copy("skill_all_in", icon_prop="none")
    art = _art(skill)
    assert art.act in _rules().needs_prop
    assert art.prop == "el:arcane"
    assert art.motion == _ref().derive_motion(raw, "el:arcane")


# ---- T-A6 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["w:banana", "W:SWORD", 3, "", None, ["w:sword"]])
def test_icon_prop_outside_the_list_falls_back_to_derivation(value: object) -> None:
    raw = _dump(library().skills["skill_cleave"])
    plain = icon_of({**raw, "icon_prop": None}, _rules())
    icon = icon_of({**raw, "icon_prop": value}, _rules())
    assert icon.art == plain.art
    assert icon.icon_prop == (value if isinstance(value, str) and value else None)


# ---- T-A8 --------------------------------------------------------------------------------------


def test_empty_draft_is_none_aura_buff() -> None:
    art = icon_of({}).art
    assert art == IconArt(prop="none", motion="aura", act="buff", tint=None, spark=None)


@pytest.mark.parametrize(
    "draft",
    [
        {"effects": "x"},
        {"shape": 3},
        {"tags": 5},
        {"modifiers": [1]},
        {"kind": "modifier", "modifiers": [1]},
        {"followup": []},
        {"followup": {"when": "delayed", "effects": "x"}},
        {"variants": "x"},
        {"variants": [1, {"element": 3}]},
        {"effects": [{"type": "enter_form"}]},
        {"effects": [{"type": "summon", "unit": 3}]},
        {"effects": [{"type": "damage", "condition": "x"}]},
        {"effects": [{"type": "damage", "condition": {"type": ["x"]}}, {"type": "damage"}]},
        {"shape": {"type": ["x"], "range": "far"}, "weapon_req": "melee"},
        {"name_zh": 3, "weapon_req": "ranged"},
        {"icon_prop": {"x": 1}},
    ],
)
def test_garbage_drafts_never_raise(draft: dict[str, Any]) -> None:
    assert isinstance(icon_of(draft).art, IconArt)


def test_workshop_walk_steps_all_get_art() -> None:
    for walk in (STRIKE, DISPLACE, MODIFIER):
        draft: dict[str, Any] = {}
        for _step, picks in walk:
            draft.update(picks)
            assert isinstance(icon_of(draft, _rules()).art, IconArt)


def test_reference_lives_where_the_spec_says() -> None:
    assert Path(REFERENCE).is_file()


KNOWN_MISSING: dict[str, list[str]] = {}
"""推導表引用、但目前內容沒有的 ID（QI-2a 查證時為 0）。跨檔參照不在載入時擋（表是美術的，可以先
寫之後才有的 ID）；這裡列出來，表或內容改了讓清單變動時這項會失敗，照實更新清單並寫進報告。"""


def test_table_references_are_listed() -> None:
    lib = library()
    table, rs = lib.icon_art, lib.ruleset
    assert table is not None
    statuses = {s.id for s in rs.statuses.statuses}
    summons = {s.id for s in rs.summons.summons}
    surfaces = {s.id for s in rs.surfaces.surfaces}
    gear = set(lib.weapons) | set(lib.offhands)
    units = [*(r.unit for r in table.summon_group), *(r.key for r in table.summon_tint)]
    status_rows = (*table.dot, *table.bind, *table.curse, *table.status_tint)
    conditions = rs.conditions.by_id()
    primitives = rs.primitives.by_id()
    found = {
        "weapon": [r.weapon for r in table.weapon_look if r.weapon not in gear],
        "summon": [u for u in units if f"summon_{u}" not in summons and u not in summons],
        "status": [r.key for r in status_rows if r.key not in statuses],
        "condition": [
            r.key for r in table.cond_tint if r.key not in statuses and r.key not in conditions
        ],
        "surface": [r.key for r in table.surface_tint if r.key not in surfaces],
        "primitive": [
            e
            for r in (*table.effect_action, *table.late_action)
            for e in r.effects
            if e not in primitives
        ],
        "shape": [
            str(r.shape)
            for r in table.shape_motion
            if r.shape is not None and r.shape not in rs.shapes.by_id()
        ],
        "modifier_change": [
            r.key for r in table.mod_tint if r.key not in lib.modifier_changes.by_id()
        ],
    }
    assert {k: v for k, v in found.items() if v} == KNOWN_MISSING
