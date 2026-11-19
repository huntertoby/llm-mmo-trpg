"""組合器的元素配方（WC-2 第 5.4 項；#167 第 5 題「元素配方」）：換主題元素。

許願覆蓋表（WC-1）的「冰霜＋範圍 0%」不是規則擋住：組合器做得出冰霜的範圍技能（指定範圍骨架時，
冰霜和其他元素一樣常見），是因為元素由組合器在 8 個元素裡平均抽（武器技還要先擲到附魔），範圍形狀
本來就少，兩個條件疊起來每個桶子的 40 個種子抽不到。許願池的候選一樣是抽出來的，願望指定元素時
「元素＋另一個條件」常常湊不到。

:func:`retheme`：組合器組好的技能，主題元素換成 ``element``——技能標籤裡的主題元素、效果上寫著主題
元素的 ``element``（傷害、延遲爆炸、獻祭爆炸……）一起換；沒有元素的武器技（物理）＝附魔成這個元素
（傷害效果加上 ``element``）。結構、數值、代價都不動，等於組合器在同一個種子擲到另一個元素；和元素
有關的限制（大地才有震波、原語的 ``elements_any``……）由驗證器再檢查一次，不合格回傳 ``None``。
只換組合器的技能（``skill_rand_`` 開頭、沒有第二元素）。
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skill_scaling import ScalingFacts
from trpg.content.skills import SkillDef, damage_elements, skill_elements
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.mechanics import mechanic_tags
from trpg.skillgen.validate import validate_skill

__all__ = ["COMPOSER_PREFIX", "retheme"]

COMPOSER_PREFIX = "skill_rand_"
"""組合器技能的 ID 開頭。"""
_ELEMENT_VALUES = frozenset(e.value for e in Element)
_DAMAGE = "damage"


def _swap(node: Any, old: str | None, new: str) -> Any:
    """效果字典（含巢狀）裡 ``element`` 等於 ``old`` 的換成 ``new``；``old`` 為 ``None``＝沒寫元素的
    傷害效果補上 ``new``（物理附魔）。"""
    if isinstance(node, list):
        return [_swap(item, old, new) for item in node]
    if not isinstance(node, dict):
        return node
    out = {k: _swap(v, old, new) for k, v in node.items()}
    if old is None:
        if out.get("type") == _DAMAGE and out.get("element") in (None, Element.PHYSICAL.value):
            out["element"] = new
    elif out.get("element") == old:
        out["element"] = new
    return out


def retheme(library: ContentLibrary, skill: SkillDef, element: str) -> SkillDef | None:
    """``skill`` 的主題元素換成 ``element``（見模組說明）；做不到或不合格時 ``None``。"""
    if (
        element == Element.PHYSICAL.value
        or element not in _ELEMENT_VALUES
        or not skill.id.startswith(COMPOSER_PREFIX)
        or skill.element is not None
        or len(damage_elements(skill)) > 1
    ):
        return None
    themes = sorted(e.value for e in skill_elements(skill))
    old = themes[0] if themes else None
    if old == element:
        return None
    if old is None and (skill.category != "weapon" or skill.kind != "active"):
        return None  # 只有武器技有「物理」主題（法術技一定有元素）
    data = skill.model_dump(mode="json")
    data["effects"] = _swap(data["effects"], old, element)
    if data.get("followup"):
        data["followup"] = _swap(data["followup"], old, element)
    try:
        made = _finish(library, data, old or Element.PHYSICAL.value, element)
    except (ValidationError, BudgetError):
        return None
    if {e.value for e in skill_elements(made)} != {element}:
        return None
    return None if validate_skill(made, library) else made


def _finish(library: ContentLibrary, data: dict[str, Any], old: str, element: str) -> SkillDef:
    """標籤、暫定名稱、縮放屬性跟著新元素（同組合器的 ``_finish``）：標籤＝新元素、骨架、機制標籤；
    名稱的元素前綴換掉；法術技的縮放屬性不在新元素允許的範圍時取範圍裡第一個。"""
    skeleton = str(data["skeleton"])
    data["tags"] = [element, skeleton]
    found = mechanic_tags(SkillDef.model_validate(data), library.ruleset)
    data["tags"] = [element, skeleton, *(t for t in found if t not in (element, skeleton))]
    old_name, new_name = Element(old).display_name, Element(element).display_name
    data["name_zh"] = str(data["name_zh"]).replace(f"{old_name}・", f"{new_name}・", 1)
    if data["category"] == "spell":
        allowed = [a.value for a in library.scaling_range(ScalingFacts.of_draft(data))]
        if allowed and data["scaling_attr"] not in allowed:
            data["scaling_attr"] = allowed[0]
    return SkillDef.model_validate(data)
