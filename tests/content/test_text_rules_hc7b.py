"""HC-7 a 裁定 5：留 text 的 3 筆把數字搬進 content，檢查移到上一層（規則值不變、說明照現值組字）。

- 觸發時機的每輪次數：``skill_triggers.yaml`` 的 ``max_per_round``，由 Ruleset 層的技能檢查擋下。
- 道具技能的 AP：``world/items.yaml`` 的 ``item_skill_ap_cost``，由物品表擋下。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.content.world_economy import WorldItemTable
from trpg.skillgen.validate import validate_skill


def test_trigger_caps_come_from_content(library: ContentLibrary) -> None:
    triggers = library.ruleset.skill_triggers.by_id()
    assert triggers["on_keyword_exploited"].max_per_round == 1
    assert triggers["on_ap_spent_all"].max_per_round == 1
    assert triggers["on_battle_start"].max_per_round is None


def test_trigger_cap_is_checked_at_the_ruleset(library: ContentLibrary) -> None:
    """格式層照樣讀得進來（錯誤出現的地方改了），Ruleset 層擋下、字和改前相同。"""
    base = library.skills["skill_ember_resonance"]
    assert base.trigger is not None
    trigger = TriggerSpec.model_validate(
        {**base.trigger.model_dump(exclude_none=True), "max_per_round": 2}
    )
    skill = base.model_copy(update={"trigger": trigger})
    messages = [v.message for v in validate_skill(skill, library)]
    assert "on_keyword_exploited 每輪最多觸發 1 次（max_per_round 只能是 1）" in "\n".join(messages)
    assert not any("max_per_round" in m for m in (v.message for v in validate_skill(base, library)))


def _items(library: ContentLibrary, ap: int, cap: int) -> dict[str, Any]:
    pill = library.world_economy.items["item_hp_potion_small"]
    assert pill.skill is not None
    data = pill.model_dump(mode="json", exclude_none=True)
    data["skill"] = SkillDef.model_validate(
        {**pill.skill.model_dump(mode="json", exclude_none=True), "ap_cost": ap}
    ).model_dump(mode="json", exclude_none=True)
    return {"item_skill_ap_cost": cap, "items": [data]}


def test_item_skill_ap_comes_from_content(library: ContentLibrary) -> None:
    WorldItemTable.model_validate(_items(library, 1, 1))
    with pytest.raises(ValidationError, match=r"道具技能必須是主動、1 AP（8\.17）"):
        WorldItemTable.model_validate(_items(library, 2, 1))
    with pytest.raises(ValidationError, match=r"道具技能必須是主動、2 AP（8\.17）"):
        WorldItemTable.model_validate(_items(library, 1, 2))
