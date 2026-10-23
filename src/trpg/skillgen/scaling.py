"""新技能跟主屬性（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2、``06-技能.md`` 6.10）。

隨機組合器、候選產生器與 LLM 提議產生技能之後，把 **縮放屬性改成主角目前最高的屬性**，但限在
``content/skill_scaling.yaml`` 的允許範圍內（武器技看武器、法術技依主題；內建技能池不改）：

- 允許範圍內有主角最高的屬性就用它；否則取允許範圍內主角數值最高的。
- 同分一律依六屬性順序（力量、敏捷、體質、智力、感知、意志）取第一個——確定性，不看 ``set`` 的
  迭代順序。
- ``avoid``：候選產生器的「新方向」要和主角最高屬性不同的屬性；允許範圍只剩 ``avoid`` 時不改，
  由呼叫者決定要不要換技能。
- 雙屬性技能（``secondary_scaling_attr``）：第二屬性若和新的主屬性相同就拿掉（技能退回單屬性）；
  專精加成跟著主屬性走，不受影響。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

__all__ = ["pick_scaling_attr", "retarget_scaling"]


def pick_scaling_attr(
    allowed: Collection[Attribute],
    attributes: Mapping[Attribute, int],
    avoid: Attribute | None = None,
) -> Attribute | None:
    """``allowed`` 中主角數值最高的屬性（並列依六屬性順序）；排除 ``avoid`` 後沒有時為 ``None``。"""
    pool = [a for a in Attribute if a in allowed and a != avoid]
    if not pool:
        return None
    best = max(attributes[a] for a in pool)
    return next(a for a in pool if attributes[a] == best)


def retarget_scaling(
    skill: SkillDef,
    attributes: Mapping[Attribute, int],
    library: ContentLibrary,
    *,
    avoid: Attribute | None = None,
) -> SkillDef:
    """把 ``skill`` 的縮放屬性改成 ``attributes`` 中最高、且在允許範圍內的屬性（見模組說明）。
    不需要改（或沒有可用的屬性）時回傳原技能。內容庫的技能（手寫技能池）不會經過這裡。"""
    allowed = library.skill_scaling.allowed_attrs(skill, library.weapons)
    attr = pick_scaling_attr(allowed, attributes, avoid)
    if attr is None or attr == skill.scaling_attr:
        return skill
    update: dict[str, object] = {"scaling_attr": attr}
    if skill.secondary_scaling_attr == attr:
        update["secondary_scaling_attr"] = None
    return skill.model_copy(update=update)
