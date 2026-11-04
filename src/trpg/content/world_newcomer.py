"""新手引導的資料（Phase 6F-2；09 9.6.9 #99、#125，21 21.5，18 18.7.1）。

- :class:`BattleHint`：戰鬥短提示（#99「戰鬥中出現短提示，可以關掉」）。新手任務各步的 ``teach``
  （``content/world/quests/<region>.yaml``）列這一步那場戰鬥要教的提示；``world/newcomer.yaml`` 的
  ``battle_hints`` 是任何大世界戰鬥都可能出現的提示（冰面、陷阱、致命地形、被推撞）。
  觸發條件（``trigger``）由畫面照戰況判斷；提示只影響畫面，不改戰鬥結果。
- :class:`NewcomerContent`（``content/world/newcomer.yaml``）：開局在主城（#125）的開場文字、
  新手區（第一次傳送免費的目的地）、指引句。

確定性：只是資料；引擎只讀 ``start_region``（:func:`trpg.world.town.free_first_teleport`）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "BATTLE_HINT_TRIGGERS",
    "NEWCOMER_FILE",
    "BattleHint",
    "BattleHintTrigger",
    "NewcomerContent",
    "OpeningLine",
    "load_newcomer",
]

NEWCOMER_FILE: Final = "world/newcomer.yaml"

type BattleHintTrigger = Literal[
    "battle_start",
    "enemy_on_water",
    "water_present",
    "reaction",
    "ice_present",
    "trap_present",
    "lethal_terrain",
    "pushed",
]
BATTLE_HINT_TRIGGERS: Final[tuple[str, ...]] = (
    "battle_start",
    "enemy_on_water",
    "water_present",
    "reaction",
    "ice_present",
    "trap_present",
    "lethal_terrain",
    "pushed",
)
"""提示的觸發條件（畫面判斷）：

- ``battle_start``：開場。
- ``enemy_on_water``：有敵人站在水面上。
- ``water_present``：戰場上有水面。
- ``reaction``：主角有反應規則，或有人的反應觸發了。
- ``ice_present``：戰場上有冰面。
- ``trap_present``：看得到陷阱。
- ``lethal_terrain``：戰場上有致命地形（``terrain.yaml`` 的 ``deadly``）。
- ``pushed``：我方有人被推撞（強制位移）。
"""

_Id = Annotated[str, Field(pattern=ID_PATTERN)]


class BattleHint(ContentModel):
    """一則戰鬥短提示（#99）：每種提示每個角色只出一次、可以關掉（畫面記錄）。"""

    id: _Id
    trigger: BattleHintTrigger
    text_zh: str = Field(min_length=1, max_length=60)


class OpeningLine(ContentModel):
    """開場的一句話（說書人或 NPC；模型關閉時就用這句當模板文字）。"""

    speaker_zh: str = Field(min_length=1)
    text_zh: str = Field(min_length=1)


class NewcomerContent(ContentModel):
    """``content/world/newcomer.yaml``（#125 開局在主城、#99 戰鬥短提示）。"""

    start_region: _Id
    """新手區：新角色還沒到過這一區的小鎮時，主城可以直接傳送過去（第一次傳送免費，21.5）。"""
    opening: tuple[OpeningLine, ...] = ()
    """新角色在主城醒來時的開場（依序）。"""
    guide_capital_zh: str = Field(min_length=1)
    """還沒到過新手區時的指引（任務追蹤與開場）：例「到霧渡鎮找渡婆婆」。"""
    guide_capital_how_zh: str = Field(min_length=1)
    """主城裡怎麼過去：例「站上中央廣場的傳送陣」。"""
    guide_town_zh: str = Field(min_length=1)
    """到了新手區、還沒接新手任務時的指引：例「找頭上有『！』的渡婆婆說話」。"""
    main_advice_zh: str = Field(min_length=1)
    """新手任務鏈完成前，主線的建議：``{quest}``＝新手任務名。"""
    battle_hints: tuple[BattleHint, ...] = ()
    """任何大世界戰鬥都可能出現的提示（新手任務各步另有 ``teach``）。"""
    flash_lesson: tuple[OpeningLine, ...] = ()
    """第一次閃現的引導（#132）：新手任務第 1 步完成、回到城鎮、還沒閃現過時（說書人＋導師）。"""
    reflash_lesson: tuple[OpeningLine, ...] = ()
    """升到 ``reflash_level`` 級、閃現過之後，導師改教重閃（#132）。"""
    reflash_level: int = Field(default=3, ge=2)

    @model_validator(mode="after")
    def _check(self) -> NewcomerContent:
        ids = [h.id for h in self.battle_hints]
        if len(ids) != len(set(ids)):
            raise ValueError("battle_hints 的 ID 重複")
        if "{quest}" not in self.main_advice_zh:
            raise ValueError("main_advice_zh 要有 {quest}（新手任務名）")
        return self


def load_newcomer(root: Path) -> tuple[Path, NewcomerContent] | None:
    """讀 ``world/newcomer.yaml``（不存在＝``None``；跨檔案檢查在內容庫）。"""
    path = root / NEWCOMER_FILE
    if not path.is_file():
        return None
    return path, load_content_file(path, NewcomerContent)
