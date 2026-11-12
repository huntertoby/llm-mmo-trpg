"""新手引導的資料（Phase 6F-2；09 9.6.9 #99、#125，21 21.5，18 18.7.1）。

- :class:`BattleHint`：戰鬥短提示（#99「戰鬥中出現短提示，可以關掉」）。新手任務各步的 ``teach``
  （``content/world/quests/<region>.yaml``）列這一步那場戰鬥要教的提示；``world/newcomer.yaml`` 的
  ``battle_hints`` 是任何大世界戰鬥都可能出現的提示（冰面、陷阱、致命地形、被推撞）。
  觸發條件（``trigger``）由畫面照戰況判斷；提示只影響畫面，不改戰鬥結果。
- :class:`NewcomerContent`（``content/world/newcomer.yaml``）：開局在主城（#125）的開場文字、
  新手區（第一次傳送免費的目的地）、指引句。
- :class:`RangeContent`（同檔的 ``range``，Phase TR-1，#134）：主城工坊靶場——武器架的大類順序、
  沙盒試打的地圖與木樁、每大類 2 招示範招、守印人的台詞、還沒選武器時手上拿的佔位武器。

確定性：只是資料；引擎只讀 ``start_region``（:func:`trpg.world.town.free_first_teleport`）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute

__all__ = [
    "BATTLE_HINT_TRIGGERS",
    "NEWCOMER_FILE",
    "BattleHint",
    "BattleHintTrigger",
    "NewcomerContent",
    "OpeningLine",
    "RangeContent",
    "RangeDummy",
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


type RangeClass = Literal["melee", "ranged", "focus"]


class RangeDummy(ContentModel):
    """靶場的一個木樁（#134：會動、站在水上、普通）：``unit`` 是單位範本，``at`` 是地圖上的位置。"""

    unit: _Id
    at: tuple[int, int]
    label_zh: str = Field(min_length=1, max_length=20)
    """畫面上的說明（例「會動的木樁」）。"""


class RangeContent(ContentModel):
    """主城工坊靶場（#134；21 21.5、09 9.6.9、06 6.27.3）。

    試打是 **沙盒**：在記憶體裡開一場戰鬥，不寫世界日誌、不給經驗與掉落、不耗 HP 與法力
    （:mod:`trpg.world.opening`）。"""

    racks: tuple[RangeClass, ...] = ("melee", "ranged", "focus")
    """武器架的大類順序（21.5：近戰、遠程、法器）。"""
    placeholder_weapon: _Id
    """還沒選武器（未完成開局）時角色手上的武器：只為了讓角色範本合法、畫面有東西可畫；
    確定出發時換成選的武器。"""
    map: _Id
    """試打的戰鬥地圖。"""
    hero_at: tuple[int, int]
    """主角的起始位置。"""
    dummies: tuple[RangeDummy, ...] = Field(min_length=1)
    max_rounds: int = Field(default=30, ge=1, le=200)
    demos: dict[RangeClass, tuple[_Id, ...]]
    """每大類的示範招（21.5：該大類 2 招；選完收回、不進技能庫）。#150 起也是入門招（21.5 第 1
    點；程式一律從這裡讀，換招只改資料）。"""
    demo_notes: dict[_Id, str] = Field(default_factory=dict)
    """示範卡片在技能本體說明之外多寫的一句（技能 ID → 文字；#148：燧石飛刃「靶場的油桶打破會
    流出油」）。只在靶場顯示，不改技能本體；鍵要是 ``demos`` 裡的招。"""
    starters: dict[RangeClass, _Id]
    """每大類的入門武器（#150 第 1 點）。"""
    intro: tuple[OpeningLine, ...] = ()
    """守印人帶到靶場時說的話（依序）。"""
    done: tuple[OpeningLine, ...] = ()
    """按「確定出發」之後守印人說的話（指示去霧渡鎮找渡婆婆）。"""
    # ---- OB-5（#150 前端）：選大類、正式選定畫面的台詞與畫面資料 ----
    loan: tuple[OpeningLine, ...] = ()
    """選了大類之後守印人多說的話（「手上這套是借你的…」）。"""
    demo_blurbs: dict[_Id, str] = Field(default_factory=dict)
    """示範招（入門招）在大類卡、示範卡上的一句白話說明（技能 ID → 文字）；鍵要是 ``demos`` 裡的
    招。只在靶場顯示，不改技能本體。"""
    keeper_object: _Id | None = None
    """守印人：主城實地地圖上的情境物件 ID（畫面取它的頭像）；``None``＝不放頭像。"""
    choose: tuple[OpeningLine, ...] = ()
    """導師（葛蘭）開「正式選定」畫面時說的話（#150 第 3 點）。"""
    choose_capital: tuple[OpeningLine, ...] = ()
    """在主城工坊靶場開「正式選定」畫面時守印人說的話。"""
    choose_done: tuple[OpeningLine, ...] = ()
    """在導師那裡正式選定完成後說的話（收回入門配備、接著補三選一）。"""
    choose_capital_done: tuple[OpeningLine, ...] = ()
    """在主城工坊靶場正式選定完成後守印人說的話（OB-5b，玩法 PM 定稿）。"""
    choose_place_zh: str = ""
    """導師那裡開的「正式選定」畫面，標題牌上的地方（「霧渡鎮導師堂」）。在主城開時畫面用主城地名。"""
    choose_objects: tuple[_Id, ...] = ()
    """主城實地地圖上能打開「正式選定」畫面的情境物件 ID（靶場、工坊師傅）。"""
    # ---- OB-6（#150 前端第二段）：4 級前免費重選的台詞（玩法 PM 定稿；空＝不說話） ----
    reselect: tuple[OpeningLine, ...] = ()
    """導師（葛蘭）開「重選」畫面時說的話（「重選開場」）。"""
    reselect_capital: tuple[OpeningLine, ...] = ()
    """在主城工坊靶場開「重選」畫面時守印人說的話（「主城重選」）。"""
    reselect_done: tuple[OpeningLine, ...] = ()
    """在導師那裡重選完成後說的話（彈窗，按「好」之後才出三選一）。"""
    reselect_capital_done: tuple[OpeningLine, ...] = ()
    """在主城工坊靶場重選完成後守印人說的話（OB-6 Q3）。"""
    reselect_reminder: tuple[OpeningLine, ...] = ()
    """正式選定後配點教學的收尾彈窗第二段：導師提醒 4 級前可以重選一次（OB-6 Q2；還有重選
    資格時才說）。"""

    @model_validator(mode="after")
    def _check(self) -> RangeContent:
        if sorted(self.racks) != sorted(set(self.racks)):
            raise ValueError("racks 不可重複")
        for cls in self.racks:
            if len(self.demos.get(cls, ())) != DEMOS_PER_CLASS:
                raise ValueError(f"demos.{cls} 要剛好 {DEMOS_PER_CLASS} 招示範招")
        shown = {s for ids in self.demos.values() for s in ids}
        extra = sorted(k for k, v in self.demo_notes.items() if k not in shown or not v.strip())
        if extra:
            raise ValueError(f"demo_notes 的鍵要是示範招、文字不可空白：{', '.join(extra)}")
        extra = sorted(k for k, v in self.demo_blurbs.items() if k not in shown or not v.strip())
        if extra:
            raise ValueError(f"demo_blurbs 的鍵要是示範招、文字不可空白：{', '.join(extra)}")
        if sorted(self.starters) != sorted(self.racks):
            raise ValueError("starters 要剛好涵蓋 racks 的每個大類")
        spots = [self.hero_at, *(d.at for d in self.dummies)]
        if len(spots) != len(set(spots)):
            raise ValueError("主角與木樁的位置不可重疊")
        return self


DEMOS_PER_CLASS: Final = 2
"""每大類的示範招數（21.5）。"""


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
    # ---- 配點教學與升級畫面（6F-4，#133、C2；18 18.5 葛蘭、07 7.2） ----
    mentor_npc: _Id | None = None
    """新手區的駐堂導師（人設卡 ID，例 ``gran``）：配點教學只在他所在的城鎮出；``None``＝任何
    城鎮。"""
    allocate_lesson: tuple[OpeningLine, ...] = ()
    """配點教學（#133）：升到 2 級、回到導師所在的城鎮、還有沒分配的屬性點時，導師先教配點
    （排在第一次閃現之前）。空＝沒有配點教學。"""
    allocate_again_lesson: tuple[OpeningLine, ...] = ()
    """略過配點教學之後，第一次進城鎮或營火時再提示一次的話（OB-3，09 9.6.9）；空＝沿用
    ``allocate_lesson``。"""
    allocate_done_zh: str = ""
    """配完之後導師說的話（接第一次閃現）。"""
    allocate_skip_zh: str = ""
    """按「之後再說」時導師說的話。"""
    level_up_zh: str = ""
    """升級畫面（C2）：``{level}``＝新等級、``{points}``＝屬性點、``{insight}``＝靈感；空＝不出升級畫面。"""
    level_up_mentor_zh: str = ""
    """還沒上過配點教學時接在升級畫面後面的一句（「回霧渡鎮找導師堂的葛蘭，學怎麼配點。」）。"""
    attribute_notes: dict[Attribute, str] = Field(default_factory=dict)
    """配點教學裡六個屬性的白話說明（滑過時）。"""
    # ---- OB-5（#150 前端）：走新開局流程的角色用的字（空＝沿用上面舊流程的字） ----
    allocate_respec_lesson: tuple[OpeningLine, ...] = ()
    """正式選定之後的配點教學（點數已照推薦配好，教重配再分）；空＝沿用 ``allocate_lesson``。"""
    allocate_respec_done_zh: str = ""
    """上面那種教學配完之後導師說的話；空＝沿用 ``allocate_done_zh``。"""
    level_up_starter_zh: str = ""
    """入門期的升級畫面（屬性點已自動配好）：``{level}``、``{insight}``；空＝照 ``level_up_zh``。"""
    level_up_choose_zh: str = ""
    """入門期、已經打完新手前兩步時的升級畫面（指示回導師那裡）：``{level}``、``{insight}``。"""
    guide_choose_zh: str = ""
    """入門期打完新手前兩步之後任務追蹤的指引（「回霧渡鎮導師堂找葛蘭」）；空＝不出。"""
    starter_teach_note_zh: str = ""
    """入門期接在 ``starter_teach_hints`` 那幾則戰鬥短提示句尾的話。"""
    starter_teach_hints: tuple[_Id, ...] = ()
    """入門期句尾要加 ``starter_teach_note_zh`` 的戰鬥短提示 ID。"""
    range: RangeContent | None = None
    """主城工坊靶場（TR-1，#134）；``None``＝沒有靶場（建角時就要選武器與關鍵字）。"""

    @model_validator(mode="after")
    def _check(self) -> NewcomerContent:
        ids = [h.id for h in self.battle_hints]
        if len(ids) != len(set(ids)):
            raise ValueError("battle_hints 的 ID 重複")
        if "{quest}" not in self.main_advice_zh:
            raise ValueError("main_advice_zh 要有 {quest}（新手任務名）")
        for name in ("level_up_zh", "level_up_starter_zh", "level_up_choose_zh"):
            text = getattr(self, name)
            if text and "{level}" not in text:
                raise ValueError(f"{name} 要有 {{level}}（新等級）")
        return self


def load_newcomer(root: Path) -> tuple[Path, NewcomerContent] | None:
    """讀 ``world/newcomer.yaml``（不存在＝``None``；跨檔案檢查在內容庫）。"""
    path = root / NEWCOMER_FILE
    if not path.is_file():
        return None
    return path, load_content_file(path, NewcomerContent)
