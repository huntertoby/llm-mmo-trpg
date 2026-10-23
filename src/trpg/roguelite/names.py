"""一輪裡的技能名稱（2026-10-23，使用者：「組合技能名稱拿掉 #編號，撞名加（二）」）。

隨機組合器的名稱是「元素・骨架」（不帶種子）；生成技能加進一輪時，若和這一輪已有的技能撞名，
在名稱後加「（二）」「（三）」……。改的只有顯示名稱 ``name_zh``，ID 不變；改名後的定義存進
``generated_skills``，讀檔與重播一致。
"""

from __future__ import annotations

from collections.abc import Iterable

from trpg.content.skills import SkillDef

__all__ = ["unique_skill_name"]

_NUMERALS = ("二", "三", "四", "五", "六", "七", "八", "九", "十")


def unique_skill_name(skill: SkillDef, taken: Iterable[str]) -> SkillDef:
    """``skill`` 的名稱若已在 ``taken`` 中，改成第一個沒用過的「名稱（二）」「名稱（三）」……；
    十個都用完時改用阿拉伯數字（「名稱（11）」）。沒有撞名時原樣回傳。"""
    names = set(taken)
    if skill.name_zh not in names:
        return skill
    for i in range(2, 1000):
        mark = _NUMERALS[i - 2] if i - 2 < len(_NUMERALS) else str(i)
        candidate = f"{skill.name_zh}（{mark}）"
        if candidate not in names:
            return skill.model_copy(update={"name_zh": candidate})
    return skill
