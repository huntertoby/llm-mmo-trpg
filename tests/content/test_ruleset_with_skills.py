"""Phase 3E-1 #6：``Ruleset.with_skills`` 加入生成的技能（走共用驗證、重建索引）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from trpg.content.skills import SkillDef

NEW = make_skill(
    "skill_t_generated",
    {"type": "single", "range": 4},
    [{"type": "damage", "dice": "2d6", "element": "fire"}],
)


def with_effects(*effects: dict[str, Any]) -> SkillDef:
    data = NEW.model_dump(mode="json")
    data["effects"] = list(effects)
    return SkillDef.model_validate(data)


def test_with_skills_adds_and_reindexes_without_touching_the_original() -> None:
    rules = library().ruleset
    extended = rules.with_skills([NEW])
    assert extended.skill_def(NEW.id) == NEW
    assert NEW.id in extended.skills.by_id()
    assert NEW.id not in rules.skills.by_id()


def test_with_skills_rejects_unknown_references() -> None:
    rules = library().ruleset
    bad = with_effects({"type": "apply_status", "status": "no_such_status", "duration": 2})
    with pytest.raises(ValueError, match="no_such_status"):
        rules.with_skills([bad])


def test_with_skills_runs_the_grant_skill_check() -> None:
    rules = library().ruleset
    effect = {"type": "grant_skill", "skill": "skill_time_surge", "duration": 3, "affects": "self"}
    data = NEW.model_dump(mode="json")
    data.update(effects=[effect], shape={"type": "self"}, weapon_req="any", scaling_attr="wis")
    with pytest.raises(ValueError, match="傳說"):
        rules.with_skills([SkillDef.model_validate(data)])


def test_with_skills_rejects_a_clashing_id_but_accepts_an_identical_repeat() -> None:
    rules = library().ruleset.with_skills([NEW])
    assert rules.with_skills([NEW]) is rules
    other = with_effects({"type": "damage", "dice": "1d4", "element": "ice"})
    with pytest.raises(ValueError, match="已存在"):
        rules.with_skills([other])
