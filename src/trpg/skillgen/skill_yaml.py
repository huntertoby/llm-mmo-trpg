"""技能與 YAML 之間的轉換（組合器的產物可以存成 ``content/skills/<id>.yaml`` 的格式再載入）。"""

from __future__ import annotations

from typing import Any

import yaml

from trpg.content.skills import SkillDef

__all__ = ["skill_from_yaml", "skill_to_yaml"]


def skill_to_yaml(skill: SkillDef) -> str:
    """技能的 YAML 文字（省略 ``null`` 欄位；骰子寫成 ``2d6``）。"""
    data: dict[str, Any] = skill.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def skill_from_yaml(text: str) -> SkillDef:
    """:func:`skill_to_yaml` 的反向（做法同載入 ``content/skills/``：``safe_load`` 加驗證）。"""
    return SkillDef.model_validate(yaml.safe_load(text))
