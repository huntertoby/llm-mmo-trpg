"""E6-b2 測試共用：標了招牌的測試內容與穿在身上的測試物品。

現有內容的詞條都沒有標招牌，這裡把幾條詞條複製一份標上 ``signature``（同 E6-b1 的測試），
換進內容庫。
"""

from __future__ import annotations

from dataclasses import replace

from trpg.content.equipment import AffixRoll, ItemDef
from trpg.content.library import ContentLibrary

__all__ = [
    "GRAPPLE",
    "GUARD",
    "RANGED_BLOCK",
    "RULE_FIRE",
    "RULE_MOVE",
    "SMOKE",
    "gear_item",
    "sig_library",
]

GRAPPLE = "affix_act_grapple"
SMOKE = "affix_act_smoke"
GUARD = "affix_react_guard_ally"
RANGED_BLOCK = "affix_react_ranged_block"
RULE_FIRE = "affix_rule_fire_mends"
RULE_MOVE = "affix_rule_move_any_object"

_KINDS = {
    GRAPPLE: "action",
    SMOKE: "action",
    GUARD: "reaction",
    RANGED_BLOCK: "reaction",
    RULE_FIRE: "rule",
    RULE_MOVE: "rule",
}


def sig_library(base: ContentLibrary) -> ContentLibrary:
    """``base`` 的這幾條詞條標上招牌（其他不變）。"""
    affixes = dict(base.affixes)
    for affix_id, kind in _KINDS.items():
        affixes[affix_id] = affixes[affix_id].model_copy(update={"signature": kind})
    return replace(base, affixes=affixes)


def gear_item(
    item_id: str, slot_type: str, *affixes: str, legendary: bool = False, rarity: str = "rare"
) -> ItemDef:
    """一件帶這些詞條的測試物品（不是武器）。"""
    return ItemDef(
        id=item_id,
        name_zh=f"測試{item_id}",
        slot_type=slot_type,  # type: ignore[arg-type]
        legendary=legendary,
        rarity="legendary" if legendary else rarity,
        affixes=tuple(AffixRoll(affix=a) for a in affixes),
    )
