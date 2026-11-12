"""Q 版技能圖示補圖：7 個新中性道具與 19 招的 ``icon_prop``
（Phase QI-2d，T-D1～T-D3、T-D9、T-D10）。

期望值出處：
- 7 個道具的 ID 與 ``name_zh``：``docs/art/Q版小圖示-第3批技能主圖.md`` 17.7
  （``group: neutral``、不寫 ``weapon_class``）；
- 19 招的值：``docs/art/技能圖示道具清單.md`` 2.4 的資料版（玩法決定 #151 補充；
  規格 ``PhaseQI-2d計畫.md`` 第 6 節表），「改前」欄是 QI-2c 合併後 ``skill_icons.json`` 的
  ``art``（規格助手實查）；
- 不限大類：06 6.36「中性道具不限大類」。
其他資料一律讀實際內容。
"""

from __future__ import annotations

import re

import pytest

from tests.content.test_icon_prop_battle_ip1 import _icon_skills
from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library.skill_checks import icon_prop_problems
from trpg.content.loader import load_content_file
from trpg.content.skill_icon_props import ICON_PROP_PATTERN, IconPropTable, icon_prop_problem
from trpg.narrative.skill_icon import skill_icon
from trpg.narrative.skill_icon_art import icon_art_rules

NEW_PROPS = {
    "w:flask": "瓶",
    "w:smoke_bomb": "煙霧彈",
    "w:roar": "吼聲",
    "w:boot": "腳／靴",
    "w:shoulder": "肩撞",
    "w:fang": "獠牙",
    "w:slime": "黏液",
}

# 技能 → (改前 icon_prop, 改後 icon_prop, 改前 art 的 (prop, motion, act, tint))
TABLE: dict[str, tuple[str | None, str, tuple[str, str, str, str | None]]] = {
    "skill_trample": ("w:fist", "w:boot", ("w:fist", "swing", "combo", "impact")),
    "skill_prone_kick": ("w:fist", "w:boot", ("w:fist", "swing", "push", None)),
    "skill_gale_kick": ("w:fist", "w:boot", ("w:fist", "swing", "push", None)),
    "skill_leap_slam": ("w:fist", "w:boot", ("w:fist", "place", "dash", None)),
    "skill_prone_mark_strike": (None, "w:boot", ("w:sword", "swing", "knockdown", None)),
    "skill_heavy_stomp": (None, "w:boot", ("w:fist", "aura", "modify", "impact")),
    "skill_battering_ram": ("w:fist", "w:shoulder", ("w:fist", "swing", "push", None)),
    "skill_bull_rush": ("w:fist", "w:shoulder", ("w:fist", "place", "dash", None)),
    "skill_tiger_charge": ("w:fist", "w:shoulder", ("w:fist", "swing", "dash", None)),
    "skill_quake_topple": ("w:fist", "w:shoulder", ("w:fist", "swing", "knockdown", None)),
    "skill_oil_flask": (None, "w:flask", ("el:earth", "area", "surface", "earth")),
    "skill_splash_flask": (None, "w:flask", ("el:water", "area", "slow", None)),
    "skill_smoke_bomb": (None, "w:smoke_bomb", ("w:bow", "area", "surface", "steel")),
    "skill_gear_smoke_bomb": (None, "w:smoke_bomb", ("none", "area", "surface", "steel")),
    "skill_lingering_roar": (None, "w:roar", ("w:tome/book", "aura", "modify", "wind")),
    "skill_taunting_roar": (None, "w:roar", ("none", "spin", "curse", "fire")),
    "skill_wild_roar": (None, "w:roar", ("none", "spin", "curse", "steel")),
    "skill_venom_gore": (None, "w:fang", ("w:sword", "swing", "dot", "poison")),
    "skill_slime_glob": (None, "w:slime", ("el:earth", "shot", "slow", None)),
}
STILL_FIST = [
    "skill_prone_drag",
    "skill_decoy_swap",
    "skill_static_palm",
    "skill_armor_break_combo",
    "skill_form_pounce",
]


def _table() -> IconPropTable:
    return load_content_file(PROJECT_ROOT / "content" / "skill_icon_props.yaml", IconPropTable)


# ---- T-D1 --------------------------------------------------------------------------------------


def test_allow_list_has_the_seven_new_neutral_props() -> None:
    by_id = _table().by_id()
    for pid, zh in NEW_PROPS.items():
        prop = by_id[pid]
        assert prop.group == "neutral", pid
        assert prop.weapon_class is None, pid
        assert prop.name_zh == zh, pid
        assert re.fullmatch(ICON_PROP_PATTERN, pid), pid
        assert pid.startswith("w:"), pid  # 沒有新前綴


# ---- T-D2 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", sorted(TABLE))
def test_nineteen_skills_have_the_new_values(skill_id: str) -> None:
    assert library().skills[skill_id].icon_prop == TABLE[skill_id][1]


def test_counts_of_fist_and_new_values() -> None:
    skills = library().skills
    for sid in STILL_FIST:
        assert skills[sid].icon_prop == "w:fist", sid
    fist = sorted(s.id for s in skills.values() if s.icon_prop == "w:fist")
    new = sorted(s.id for s in skills.values() if s.icon_prop in NEW_PROPS)
    assert fist == sorted(STILL_FIST)
    assert new == sorted(TABLE)


# ---- T-D3 --------------------------------------------------------------------------------------


def _skill_with_req(req: str) -> str:
    """實際內容裡第一招（依 ID）``weapon_req`` 是 req、沒填 ``icon_prop``、
    不是化身／看武器招的技能。"""
    lib = library()
    table = _table()
    for sid in sorted(lib.skills):
        s = lib.skills[sid]
        if s.weapon_req != req or s.icon_prop is not None or s.provenance.origin != "builtin":
            continue
        probe = s.model_copy(update={"icon_prop": "w:fist"})
        if icon_prop_problems({sid: probe}, table) == []:
            return sid
    raise AssertionError(req)


@pytest.mark.parametrize("req", ["melee", "ranged", "focus", "any"])
@pytest.mark.parametrize("prop", sorted(NEW_PROPS))
def test_new_props_are_not_bound_to_a_weapon_class(prop: str, req: str) -> None:
    lib = library()
    sid = _skill_with_req(req)
    skill = lib.skills[sid].model_copy(update={"icon_prop": prop})
    assert icon_prop_problem(prop, req, _table()) is None
    assert icon_prop_problems({sid: skill}, _table()) == []


# ---- T-D9 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", sorted(TABLE))
def test_derivation_only_swaps_the_prop(skill_id: str) -> None:
    lib = library()
    rules = icon_art_rules(lib)
    old_value, new_value, (old_prop, motion, act, tint) = TABLE[skill_id]
    skill = lib.skills[skill_id]
    after = skill_icon(skill, rules)
    before = skill_icon(skill.model_copy(update={"icon_prop": old_value}), rules)
    assert after.art is not None and before.art is not None
    assert after.art.prop == new_value
    assert before.art.prop == old_prop
    for field in ("motion", "act", "tint", "spark"):
        assert getattr(after.art, field) == getattr(before.art, field), field
    assert after.elements == before.elements
    assert (after.art.motion, after.art.act, after.art.tint, after.art.spark) == (
        motion,
        act,
        tint,
        None,
    )


# ---- T-D10 -------------------------------------------------------------------------------------


def test_battle_replay_parametrization_covers_the_new_eleven() -> None:
    """``test_icon_prop_battle_ip1.py`` 的參數化（有填 ``icon_prop`` 的招）自動含新填的
    11 招：36 → 47。"""
    ids = {s.id for s in _icon_skills()}
    newly = {sid for sid, (old, _new, _art) in TABLE.items() if old is None}
    assert len(newly) == 11
    assert newly <= ids
    assert len(ids) == 47
