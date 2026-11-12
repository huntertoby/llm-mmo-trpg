"""技能圖示道具 ``icon_prop`` 的資料檢查（Phase IP-1，06 6.36，玩法決定 #151）。

- 允許清單是內容資料（``content/skill_icon_props.yaml``），57 個值（美術清單第 1 節）；
- 資料檢查的表格測試：期望值由 06 6.36 推得（清單外擋、大類不符擋、無大類技能任何值、元素／召喚／
  化身／中性道具不限大類、副手盾算近戰、法書與法器珠算法器）；
- 內容裡每個填了 ``icon_prop`` 的技能都過檢查（從內容檔讀，不手寫清單）；
- 載入整份內容時，清單外與大類不符的值由 ``load_library`` 擋下（``trpg content check`` 同一套）。
"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library import load_library
from trpg.content.library.skill_checks import _story_skill_problems, icon_prop_problems
from trpg.content.loader import load_content_file
from trpg.content.skill_icon_props import IconPropTable, icon_prop_problem
from trpg.shared.errors import ContentError

CONTENT = PROJECT_ROOT / "content"


def _table() -> IconPropTable:
    return load_content_file(CONTENT / "skill_icon_props.yaml", IconPropTable)


def test_allow_list_has_the_57_values_of_the_art_list() -> None:
    """美術清單第 1 節：武器 17＋副手 5＋中性 2＋元素 10＋召喚 12＋化身 10＋none 1＝57。"""
    table = _table()
    assert len(table.props) == 57
    assert Counter(p.group for p in table.props) == {
        "weapon": 17,
        "offhand": 5,
        "neutral": 2,
        "element": 10,
        "summon": 12,
        "form": 10,
        "special": 1,
    }
    # 只有武器與副手屬於某個大類；中性、元素、召喚、化身、none 不限（06 6.36）
    for prop in table.props:
        assert (prop.weapon_class is not None) == (prop.group in ("weapon", "offhand")), prop.id


# (icon_prop, 技能的 weapon_req, 期望合格, 說明)
_CASES: list[tuple[str, str, bool, str]] = [
    ("w:hammer", "melee", True, "合法值、大類相符"),
    ("w:bow", "ranged", True, "合法值、大類相符（遠程）"),
    ("w:staff", "focus", True, "合法值、大類相符（法器）"),
    ("w:laser_sword", "melee", False, "清單外的值"),
    ("w:Sword", "melee", False, "清單外的值（大小寫不同）"),
    ("w:sword", "ranged", False, "大類不符：弓技能填劍類道具"),
    ("w:bow", "melee", False, "大類不符：近戰招不畫弓"),
    ("w:staff", "melee", False, "大類不符：近戰招填法器"),
    ("w:sword", "any", True, "技能本身沒有武器大類（法術、裝備技）：任何道具都可以"),
    ("w:bow", "any", True, "沒有武器大類：遠程道具也可以"),
    ("w:kite_shield/tower", "any", True, "沒有武器大類：副手也可以"),
    ("el:fire", "melee", True, "元素道具配近戰"),
    ("el:fire", "ranged", True, "元素道具配遠程"),
    ("el:wind", "focus", True, "元素道具配法器"),
    ("summon:vine", "ranged", True, "召喚類道具不屬於任何大類"),
    ("form:werewolf", "melee", True, "化身類道具不屬於任何大類"),
    ("w:fist", "ranged", True, "拳腳是中性道具，不限大類"),
    ("w:kunai", "focus", True, "投擲是中性道具，不限大類"),
    ("none", "ranged", True, "沒有道具，不限大類"),
    ("w:round_shield", "melee", True, "副手盾算近戰"),
    ("w:kite_shield", "ranged", False, "副手盾算近戰：遠程招不能填"),
    ("w:tome", "focus", True, "法書算法器"),
    ("w:orb", "focus", True, "法器珠算法器"),
    ("w:tome", "melee", False, "法書算法器：近戰招不能填"),
    ("w:orb", "ranged", False, "法器珠算法器：遠程招不能填"),
]


@pytest.mark.parametrize(("icon_prop", "weapon_req", "ok", "why"), _CASES)
def test_icon_prop_check_table(icon_prop: str, weapon_req: str, ok: bool, why: str) -> None:
    problem = icon_prop_problem(icon_prop, weapon_req, _table())
    assert (problem is None) == ok, (why, problem)


def test_every_filled_skill_is_in_the_list_and_matches_its_weapon_class() -> None:
    """內容裡每個填了 ``icon_prop`` 的技能都在清單內、大類對得上（從內容檔讀，不手寫名單）。"""
    lib = library()
    filled = {sid: s for sid, s in lib.skills.items() if s.icon_prop is not None}
    assert len(filled) == 36  # 美術清單第 2 節的 36 招
    table = _table()
    for sid in sorted(filled):
        skill = filled[sid]
        assert icon_prop_problem(skill.icon_prop or "", skill.weapon_req, table) is None, sid
        assert skill.provenance.origin == "builtin", sid  # 只有手寫技能填
    assert icon_prop_problems(lib.skills, table) == []


def test_skill_without_icon_prop_serializes_as_before() -> None:
    """沒填的技能不輸出這個鍵（序列化與雜湊不因新欄位改變）；填了的有。"""
    lib = library()
    assert "icon_prop" not in lib.skills["skill_cleave"].model_dump(mode="json")
    assert lib.skills["skill_armor_breaker"].model_dump(mode="json")["icon_prop"] == "w:hammer"


def test_story_skills_cannot_fill_icon_prop() -> None:
    """只有 ``content/skills/`` 的手寫技能可以填（06 6.36）：劇情技能填了就擋。"""
    lib = library()
    base = lib.skills["skill_cleave"]
    problems = _story_skill_problems(
        base.model_copy(update={"icon_prop": "w:sword"}), lib.ruleset, lib.skills, lib.budget
    )
    assert any("icon_prop" in p for p in problems)
    assert not any(
        "icon_prop" in p for p in _story_skill_problems(base, lib.ruleset, lib.skills, lib.budget)
    )


@pytest.fixture(scope="module")
def content_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("ip1") / "content"
    shutil.copytree(CONTENT, dest)
    return dest


def _with_icon_prop(root: Path, skill_id: str, value: str) -> str:
    """把 ``skill_id`` 的 ``icon_prop`` 改成 ``value``；回傳原本的檔案內容（還原用）。"""
    path = root / "skills" / f"{skill_id}.yaml"
    original = path.read_text(encoding="utf-8")
    data = yaml.safe_load(original)
    data["icon_prop"] = value
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8", newline="\n")
    return original


@pytest.mark.parametrize(
    ("skill_id", "value", "needle"),
    [
        ("skill_cleave", "w:laser_sword", "不在圖示道具清單"),  # 近戰招、清單外
        ("skill_piercing_shot", "w:sword", "近戰道具"),  # 弓技能填劍類道具
    ],
)
def test_load_library_rejects_bad_icon_props(
    content_copy: Path, skill_id: str, value: str, needle: str
) -> None:
    original = _with_icon_prop(content_copy, skill_id, value)
    try:
        with pytest.raises(ContentError) as caught:
            load_library(content_copy)
        assert needle in str(caught.value) and skill_id in str(caught.value)
    finally:
        (content_copy / "skills" / f"{skill_id}.yaml").write_text(
            original, encoding="utf-8", newline="\n"
        )


def test_load_library_accepts_any_prop_on_classless_skill(content_copy: Path) -> None:
    """``weapon_req: any`` 的法術填遠程道具照樣通過（大類限制只看有大類的技能）。"""
    skill_id = "skill_static_palm"
    assert library().skills[skill_id].weapon_req == "any"
    original = _with_icon_prop(content_copy, skill_id, "w:bow")
    try:
        assert load_library(content_copy).skills[skill_id].icon_prop == "w:bow"
    finally:
        (content_copy / "skills" / f"{skill_id}.yaml").write_text(
            original, encoding="utf-8", newline="\n"
        )
