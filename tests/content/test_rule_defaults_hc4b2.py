"""HC-4b2：技能挑選、組合器、分歧進化、修正規則的預設值搬進 content 之後的規則對照。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.composer_rules import ComposerRules
from trpg.content.library import load_library
from trpg.content.rules import CoreRules
from trpg.content.skill_evolution import EvolutionTable
from trpg.content.skill_pick import SkillPickRules
from trpg.shared.errors import ContentError


def _read(rel: str) -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / rel).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    return root


@pytest.mark.parametrize(
    ("rel", "model", "path"),
    [
        ("skill_pick.yaml", SkillPickRules, ("pool", "seeds")),
        ("skill_pick.yaml", SkillPickRules, ("weights", "wish_match")),
        ("skill_pick.yaml", SkillPickRules, ("wish_tags", "max_keywords")),
        ("skill_composer.yaml", ComposerRules, ("whiteboard", "summon_ap_cost")),
        ("skill_composer.yaml", ComposerRules, ("structure", "borrow_cooldown")),
        ("skill_composer.yaml", ComposerRules, ("llm_topic", "base_weight")),
        ("skill_composer.yaml", ComposerRules, ("llm_cost", "max_cooldown")),
        ("skill_evolution.yaml", EvolutionTable, ("summon", "count_power_permille")),
        ("skill_evolution.yaml", EvolutionTable, ("far_distance",)),
    ],
)
def test_numbers_have_no_program_default(rel: str, model: Any, path: tuple[str, ...]) -> None:
    """程式不再有預設值：內容檔少寫一格就驗證失敗。"""
    data = _read(rel)
    node = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    with pytest.raises(ValidationError, match=path[-1]):
        model.model_validate(data)


def test_summon_units_need_a_range() -> None:
    data = _read("skill_composer.yaml")
    del data["recipes"]["summon_units"][0]["range"]
    with pytest.raises(ValidationError, match="range"):
        ComposerRules.model_validate(data)


def test_the_evolution_file_is_required(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "skill_evolution.yaml").unlink()
    with pytest.raises(ContentError, match=r"skill_evolution\.yaml"):
        load_library(root)


def test_count_evolution_follows_the_summon_count_limit(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    path = root / "skill_evolution.yaml"
    text = path.read_text(encoding="utf-8")
    assert text.count("  count_number: 2\n") == 1
    path.write_text(text.replace("  count_number: 2\n", "  count_number: 3\n"), encoding="utf-8")
    with pytest.raises(ContentError, match=r"skill_limits\.max_summon_count（2），收到 3"):
        load_library(root)


@pytest.mark.parametrize("name", ["push_distance_delta_max", "on_hit_max_displace"])
def test_modifier_displacement_cannot_exceed_the_displace_cap(name: str) -> None:
    """HC-4b 裁定 3：修正規則的推拉距離上限對照 ``max_displace_distance``。"""
    data = _read("rules/core.yaml")
    top = data["max_displace_distance"]
    data["skill_limits"]["modifier_bounds"][name] = top + 1
    with pytest.raises(ValidationError, match=f"modifier_bounds.{name}（{top + 1}）不能大於"):
        CoreRules.model_validate(data)
    data["skill_limits"]["modifier_bounds"][name] = top
    CoreRules.model_validate(data)


def test_wish_tag_limits_are_content_values() -> None:
    """願望標籤每類最多幾個只寫在 ``skill_pick.yaml``（07 7.6：關鍵字、效果 2 個，元素 2 階起
    2 個）。"""
    data = _read("skill_pick.yaml")
    rules = SkillPickRules.model_validate(data)
    assert (rules.wish_tags.limit("keywords"), rules.wish_tags.limit("effects")) == (2, 2)
    assert rules.wish_tags.limit("elements", dual=True) == 2
    data["wish_tags"]["max_keywords"] = 3
    assert SkillPickRules.model_validate(data).wish_tags.limit("keywords") == 3
