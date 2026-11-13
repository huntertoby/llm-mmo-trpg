"""KW-1（#161，06 6.27.1、6.32.1）：連擊、怒氣、專注、氣掛成關鍵字；條件「自身層數達 N」的驗證
與文字。

- 關鍵字表 12 → 16；四個新關鍵字的 ID ＝層數 ID，開局與許願池先隱藏（KW-2 補池子），組合器先不做。
- 推導：技能本身 ``add_stack``＝製造；``consume_stack`` 或條件「層數達 N」＝利用；自動累積、
  專注的下一招自動消耗都是背景規則，不算。
- 條件只能看自己身上的層數、``count`` 不超過上限；第一版只給手寫技能，不進 LLM schema。
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.test_proposal import _models
from trpg.content.library import ContentLibrary
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.narrative.skills import condition_summary
from trpg.skillgen.keywords import derive_keywords, keyword_pools
from trpg.skillgen.option_params import HANDWRITTEN_ONLY_CONDITION, condition_choice
from trpg.skillgen.validate import validate_skill

NEW = ("combo_point", "fury", "focus", "ki")
COND = "self_stack_at_least"


@cache
def lib() -> ContentLibrary:
    return library()


def skill(skill_id: str) -> SkillDef:
    return lib().skills[skill_id]


# ---------------------------------------------------------------------------
# 1. 關鍵字表
# ---------------------------------------------------------------------------


def test_the_keyword_list_grows_from_12_to_16() -> None:
    table = lib().keywords
    assert len(table.ids()) == 16
    assert table.ids()[-4:] == NEW
    names = {k: table.by_id()[k].name_zh for k in NEW}
    assert names == {"combo_point": "連擊", "fury": "怒氣", "focus": "專注", "ki": "氣"}


def test_the_new_keywords_wait_for_their_pools_before_opening_and_composer() -> None:
    """KW-2 補齊池子前：開局選單（＝許願池選單）不出現、組合器不做；推導與三選一照常。"""
    table = lib().keywords
    assert not set(NEW) & set(table.start_ids())
    assert all(not table.by_id()[k].composable for k in NEW)
    assert all(lib().ruleset.stack_def(k).owner == "self" for k in NEW)


# ---------------------------------------------------------------------------
# 2. 推導：製造＝add_stack，利用＝consume_stack 或「層數達 N」
# ---------------------------------------------------------------------------

DEMO = [
    # (技能, 製造, 利用)
    ("skill_flurry_jab", "combo_point", None),
    ("skill_combo_finisher", None, "combo_point"),
    ("skill_seething_rage", "fury", None),
    ("skill_rage_unleashed", None, "fury"),
    ("skill_steady_aim", "focus", None),
    ("skill_focused_shot", None, "focus"),
    ("skill_palm_strike", "ki", None),
    ("skill_qi_breath", None, "ki"),
]


@pytest.mark.parametrize(("skill_id", "makes", "uses"), DEMO)
def test_the_existing_stack_demos_derive_the_new_keywords(
    skill_id: str, makes: str | None, uses: str | None
) -> None:
    found = derive_keywords(skill(skill_id), lib().keywords, exclusive_only=True)
    assert set(found.makes) == ({makes} if makes else set())
    assert set(found.uses) == ({uses} if uses else set())


def test_the_demos_join_the_keyword_pools() -> None:
    pools = keyword_pools(lib())
    for skill_id, makes, uses in DEMO:
        assert skill_id in pools[makes or uses or ""], skill_id


def with_condition(base: SkillDef, condition: dict[str, Any], **update: Any) -> SkillDef:
    effects = (
        base.effects[0].model_copy(update={"condition": ConditionSpec.model_validate(condition)}),
        *base.effects[1:],
    )
    return base.model_copy(update={"effects": effects, **update})


def test_a_stack_condition_uses_the_keyword() -> None:
    made = with_condition(
        skill("skill_flurry_jab"), {"type": COND, "stack": "ki", "count": 2}, id="skill_kw1_probe"
    )
    found = derive_keywords(made, lib().keywords, exclusive_only=True)
    assert "ki" in found.uses


def test_automatic_gain_and_focus_auto_consume_are_not_keywords() -> None:
    """一般武器技（會自動累積連擊點、吃專注）不帶這四個關鍵字。"""
    plain = skill("skill_flurry_jab").model_copy(
        update={"effects": skill("skill_flurry_jab").effects[:1], "id": "skill_kw1_plain"}
    )
    found = derive_keywords(plain, lib().keywords, exclusive_only=True)
    assert not set(NEW) & set(found.all())


# ---------------------------------------------------------------------------
# 3. 條件的驗證、文字、LLM 與工坊
# ---------------------------------------------------------------------------

BAD = [
    # (條件, 訊息片段)
    ({"type": COND, "stack": "sunder", "count": 1}, "疊在敵人身上"),
    ({"type": COND, "stack": "combo_point", "count": 6}, "最多 5 層"),
    ({"type": COND, "stack": "no_such_stack", "count": 1}, "未知的層數"),
    ({"type": COND, "stack": "ki"}, "缺少必要參數 count"),
    ({"type": COND, "count": 2}, "缺少必要參數 stack"),
]


@pytest.mark.parametrize(("condition", "fragment"), BAD)
def test_bad_stack_conditions_are_rejected(condition: dict[str, Any], fragment: str) -> None:
    made = with_condition(skill("skill_combo_finisher"), condition)
    messages = [v.message for v in validate_skill(made, lib())]
    assert any(fragment in m for m in messages), messages


def test_a_good_stack_condition_passes_on_a_builtin_skill() -> None:
    made = with_condition(
        skill("skill_combo_finisher"), {"type": COND, "stack": "combo_point", "count": 5}
    )
    rules = {v.rule for v in validate_skill(made, lib())}
    assert "condition.handwritten_only" not in rules
    assert not any("stack" in v.message for v in validate_skill(made, lib()))


def test_the_stack_condition_is_for_handwritten_skills_only() -> None:
    base = with_condition(
        skill("skill_combo_finisher"), {"type": COND, "stack": "combo_point", "count": 3}
    )
    made = base.model_copy(
        update={"provenance": base.provenance.model_copy(update={"origin": "workshop"})}
    )
    found = [v for v in validate_skill(made, lib()) if v.rule == "condition.handwritten_only"]
    assert [v.message for v in found] == ["條件「自身層數達到」目前只給內建技能用"]
    schema = str(_models().json_schema())
    assert COND not in schema
    cond = lib().ruleset.conditions.by_id()[COND]
    assert condition_choice(cond, lib(), effect_level=True).info["unavailable_zh"] == (
        HANDWRITTEN_ONLY_CONDITION
    )


def test_the_condition_reads_in_chinese() -> None:
    spec = ConditionSpec(type=COND, stack="fury", count=3)
    assert condition_summary(lib(), spec) == "自身「怒氣」達 3 層"
    assert condition_summary(lib(), ConditionSpec(type=COND)) == "自身層數達到指定層數"


def test_unused_stack_fields_are_not_serialized() -> None:
    """``stack``／``count`` 沒填不輸出：既有技能的 JSON（規則包、parity 夾具）不變。"""
    dumped = ConditionSpec(type="first_round").model_dump(mode="json")
    assert "stack" not in dumped and "count" not in dumped
    full = ConditionSpec(type=COND, stack="ki", count=2).model_dump(mode="json")
    assert full["stack"] == "ki" and full["count"] == 2
