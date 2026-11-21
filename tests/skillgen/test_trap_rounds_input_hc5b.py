"""HC-5b（HC-5a 裁定 5）：工坊草稿、自訂技能與 LLM 提議沒寫陷阱輪數時，輸入層在驗證前補
``skill_composer.yaml`` 的 ``trap.enter_rounds.min``（2）——結果和 HC-5a 之前（``TrapSpec.rounds``
程式預設 2）相同。內容檔的 ``TrapSpec.rounds`` 照舊必填。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.api.workshop import custom_skill_defs
from trpg.content.skills import SkillDef, TrapSpec
from trpg.skillgen.draft import draft_id, fill_trap_rounds
from trpg.skillgen.draft_check import check_draft

LIB = library()
OLD_DEFAULT = 2
"""HC-5a 之前 ``TrapSpec.rounds`` 的程式預設。"""


def _trap_skills() -> list[SkillDef]:
    """內容庫裡輪數剛好是舊預設（2）的陷阱技（照 ID 排序）。"""
    return [
        s
        for _, s in sorted(LIB.skills.items())
        if s.trap is not None and s.trap.rounds == OLD_DEFAULT
    ]


def _without_rounds(skill: SkillDef) -> dict[str, Any]:
    data = skill.model_dump(mode="json", exclude_none=True)
    data.pop("id")
    data["provenance"] = {"origin": "workshop"}
    del data["trap"]["rounds"]
    return data


def test_the_fill_value_is_the_old_default() -> None:
    assert LIB.composer.trap.enter_rounds.min == OLD_DEFAULT
    with pytest.raises(ValidationError, match="rounds"):  # 內容層照舊必填
        TrapSpec.model_validate({"trigger": "enter"})


def test_fill_only_touches_a_trap_without_rounds() -> None:
    bare = {"trap": {"trigger": "delay"}}
    assert fill_trap_rounds(bare, LIB) == {
        "trap": {"trigger": "delay", "rounds": OLD_DEFAULT},
        "id": draft_id(bare),  # ID 照補值前的內容（同 HC-5a 之前）
    }
    given = {"trap": {"trigger": "enter", "rounds": 4}}
    assert fill_trap_rounds(given, LIB) is given
    assert fill_trap_rounds({"name_zh": "x"}, LIB) == {"name_zh": "x"}
    raw = {"trap": {"trigger": "enter"}}
    fill_trap_rounds(raw, LIB)
    assert raw == {"trap": {"trigger": "enter"}}  # 輸入不被修改


def test_workshop_draft_without_rounds_checks_like_before() -> None:
    """工坊檢查：沒寫輪數的草稿和寫了舊預設 2 的草稿，檢查結果（含技能 ID、預算）完全相同。"""
    skills = _trap_skills()
    assert skills
    for skill in skills:
        data = _without_rounds(skill)
        filled = {**data, "trap": {**data["trap"], "rounds": OLD_DEFAULT}, "id": draft_id(data)}
        got = check_draft(data, LIB)
        assert got.skill is not None, (skill.id, got.problems)
        assert got.model_dump(mode="json") == check_draft(filled, LIB).model_dump(mode="json")


def test_custom_skills_without_rounds_load_like_before() -> None:
    """自訂技能（戰鬥請求帶的工坊技能）：沒寫輪數時補 2，和 HC-5a 之前相同。"""
    skill = _trap_skills()[0]
    data = {**_without_rounds(skill), "id": skill.id}
    (loaded,) = custom_skill_defs(LIB, [data])
    assert loaded.trap is not None and loaded.trap.rounds == OLD_DEFAULT
    assert loaded == skill.model_copy(update={"provenance": loaded.provenance})
