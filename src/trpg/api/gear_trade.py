"""裝備卡上的交易資料（Phase 6T-1a；08 8.13 #135、8.16 #136）。

背包、郵寄面板共用：能不能交易與綁定標籤、「最初得自：〈原主〉（〈來源〉）」、目前持有者、別大類主手
的兩行字（「別大類：可交易・可分解・可賣」＋「換上後不能用：〈招名〉」）。全部由後端算好。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.world.state import CharacterState
from trpg.world.trade import bound_zh, origin_zh
from trpg.world.weapon_mix import weapon_class_of

__all__ = ["CROSS_CLASS_ZH", "GearTrade", "gear_trade"]

CROSS_CLASS_ZH: Final = "別大類：可交易・可分解・可賣"


@dataclass(frozen=True)
class GearTrade:
    tradable: bool
    bound_zh: str | None
    origin_zh: str | None
    holder_zh: str
    cross_class_zh: str | None
    cross_class_lost_zh: str | None


def _lost_skills(library: ContentLibrary, char: CharacterState, weapon_class: str) -> list[str]:
    generated = {s.id: s for s in char.generated_skills}
    names: list[str] = []
    for skill_id in char.hero.skills:
        skill = generated.get(skill_id) or library.skills.get(skill_id)
        if skill is not None and skill.weapon_req not in ("any", weapon_class):
            names.append(skill.name_zh)
    return names


def gear_trade(library: ContentLibrary, char: CharacterState, item: ItemDef) -> GearTrade:
    """``char`` 身上的這件裝備的交易資料（見模組說明）。"""
    origin = char.gear_origin.get(item.id)
    label = bound_zh(origin)
    cross: str | None = None
    lost: str | None = None
    weapon = None if item.weapon is None else library.weapons.get(item.weapon)
    if weapon is not None and weapon.weapon_class != weapon_class_of(library, char):
        cross = CROSS_CLASS_ZH
        names = _lost_skills(library, char, weapon.weapon_class)
        lost = f"換上後不能用：{'、'.join(names)}" if names else None
    return GearTrade(
        tradable=label is None,
        bound_zh=label,
        origin_zh=None if origin is None else origin_zh(origin),
        holder_zh=f"目前持有：{char.hero.name_zh}",
        cross_class_zh=cross,
        cross_class_lost_zh=lost,
    )
