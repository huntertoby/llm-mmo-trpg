"""化身招與看手上武器的招不能填 ``icon_prop``（Phase QI-2a D4，06 6.36；T-A7）。

這兩類招的圖示固定畫化身／那把武器（推導表道具第 1、2 列排在 ``icon_prop`` 前面），填了不生效，
所以資料檢查擋下。看的是效果與複合第二段的效果（和圖示推導同一份效果清單）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library import load_library
from trpg.content.library.skill_checks import icon_prop_fixed_problem, icon_prop_problems
from trpg.content.loader import load_content_file
from trpg.content.skill_icon_props import IconPropTable
from trpg.content.skills import SkillDef
from trpg.shared.errors import ContentError

CONTENT = PROJECT_ROOT / "content"


def _table() -> IconPropTable:
    return load_content_file(CONTENT / "skill_icon_props.yaml", IconPropTable)


def _followup_wielding() -> SkillDef:
    """合成：複合招（重劈蓄力）的第二段第一個效果加上「手持鐵錘」條件；第一段沒有條件。"""
    base = library().skills["skill_charged_cleave"]
    data = base.model_dump(mode="json", exclude_none=True)
    assert data["followup"]["effects"]
    first = data["followup"]["effects"][0]
    data["followup"]["effects"][0] = {
        **first,
        "condition": {"type": "wielding_weapon", "weapon": "hammer"},
    }
    skill = SkillDef.model_validate(data)
    assert not any(e.condition is not None for e in skill.effects)
    return skill


@pytest.mark.parametrize(
    ("label", "needle"),
    [
        ("form", "化身招"),  # 效果有 enter_form
        ("wielding", "wielding_weapon"),  # 第一段效果帶條件
        ("followup_wielding", "wielding_weapon"),  # 條件只在複合第二段的效果
    ],
)
def test_form_and_wielding_skills_cannot_fill_icon_prop(label: str, needle: str) -> None:
    lib = library()
    skill = {
        "form": lib.skills["skill_form_bear"],
        "wielding": lib.skills["skill_akimbo_burst"],
        "followup_wielding": _followup_wielding(),
    }[label]
    assert skill.icon_prop is None
    assert icon_prop_fixed_problem(skill) is not None  # 沒填時函式照樣指出這是固定道具的招
    assert icon_prop_problems({skill.id: skill}, _table()) == []  # 沒填就沒有問題
    filled = skill.model_copy(update={"icon_prop": "el:fire"})  # 不限大類的值，只剩 D4 擋
    problems = icon_prop_problems({skill.id: filled}, _table())
    assert len(problems) == 1 and needle in problems[0] and skill.id in problems[0]


def test_ordinary_skill_is_not_fixed() -> None:
    lib = library()
    for skill_id in ("skill_cleave", "skill_charged_cleave", "skill_air_burst"):
        assert icon_prop_fixed_problem(lib.skills[skill_id]) is None, skill_id


def test_current_content_has_no_blocked_skill() -> None:
    """目前內容 0 招被 D4 擋（47 招有填的都不是這兩類）；化身 10 招、wielding_weapon 24 招。"""
    lib = library()
    fixed = [s for s in lib.skills.values() if icon_prop_fixed_problem(s) is not None]
    forms = [s for s in fixed if any(e.type == "enter_form" for e in s.effects)]
    assert len(forms) == 10
    assert len(fixed) - len(forms) == 24
    assert not [s.id for s in fixed if s.icon_prop is not None]
    assert icon_prop_problems(lib.skills, _table()) == []


@pytest.fixture(scope="module")
def content_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("qi2a") / "content"
    shutil.copytree(CONTENT, dest)
    return dest


@pytest.mark.parametrize("skill_id", ["skill_form_bear", "skill_akimbo_burst"])
def test_load_library_rejects_icon_prop_on_fixed_skills(content_copy: Path, skill_id: str) -> None:
    path = content_copy / "skills" / f"{skill_id}.yaml"
    original = path.read_text(encoding="utf-8")
    data = yaml.safe_load(original)
    data["icon_prop"] = "el:fire"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8", newline="\n")
    try:
        with pytest.raises(ContentError) as caught:
            load_library(content_copy)
        assert skill_id in str(caught.value) and "不能填 icon_prop" in str(caught.value)
    finally:
        path.write_text(original, encoding="utf-8", newline="\n")
