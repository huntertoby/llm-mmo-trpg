"""主城工坊靶場的 API 模型（Phase TR-1，#134；組法在 :mod:`trpg.api.world_range`）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.schemas import BattleResponse
from trpg.api.skill_cards import SkillCard
from trpg.content.battle import ID_PATTERN

__all__ = [
    "CLASS_ZH",
    "RangeDemoView",
    "RangeDummyView",
    "RangeLineView",
    "RangeRecommendResponse",
    "RangeReselectView",
    "RangeTrialRequest",
    "RangeTrialResponse",
    "RangeView",
]

CLASS_ZH = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RangeLineView(_ApiModel):
    speaker_zh: str
    text_zh: str


class RangeDummyView(_ApiModel):
    label_zh: str


class RangeDemoView(_ApiModel):
    """一個武器架（大類）與它的 2 招示範招（選完收回、不進技能庫；#150 起也是入門招）。"""

    weapon_class: Literal["melee", "ranged", "focus"]
    name_zh: str
    skills: tuple[SkillCard, ...]
    starter_weapon: str
    """這個大類的入門武器（#150 第 1 點，OB-1）。"""
    starter_weapon_zh: str
    notes_zh: dict[str, str] = Field(default_factory=dict)
    """示範卡片多寫的一句（技能 ID → 文字；#148，例燧石飛刃「靶場的油桶打破會流出油」）。只有
    有寫的招才有鍵；技能本體的說明（``skills``）不變。"""


class RangeReselectView(_ApiModel):
    """4 級前的免費重選（OB-3，#150 第 5 點）：能不能重選、不能的原因、確認畫面要列的東西。"""

    available: bool
    """現在可以送 ``opening_reselect``（正式選定過、4 級前、沒用過、在霧渡鎮或主城、沒有遭遇）。"""
    blocked_zh: str | None
    """不能重選的原因；可以時 ``None``。"""
    used: bool
    """免費重選已經用過了。"""
    before_level: int
    """升到這一級就不能重選（規則的常數；畫面不寫死）。"""
    weapon: str | None
    """目前正式選定的武器與關鍵字（重選畫面預填）。"""
    keywords: tuple[str, ...]
    returned_zh: tuple[str, ...]
    """重選會收回的招（中文名；起始 2 招與新手三選一拿到的、還在身上的）。"""
    weapon_returned: bool
    """起始武器本體會被收回（還在手上、背包或主手欄）；已經賣掉、寄走時為假（不收回也不扣錢）。"""
    lost_zh: tuple[str, ...]
    """會跟著起始武器一起消失、材料不退的強化等改動（每項一句；沒有就空）。"""


class RangeView(_ApiModel):
    """未完成開局（在主城工坊靶場）的畫面資料（TR-1，#134）。"""

    seed: int
    """開局種子：關鍵字預覽（``/api/runs/start-preview``）帶它，預覽的招就是確定出發會給的。"""
    stage: Literal["pick_class", "starter", "chosen"]
    """開局階段（OB-1，#150）：選大類中／入門期／正式選定後到 4 級前。"""
    weapon_class: Literal["melee", "ranged", "focus"] | None
    """選定的大類（``pick_class`` 為 ``None``）。"""
    recommended_keywords: tuple[str, ...]
    """標「推薦」的關鍵字（OB-2，#150 第 4 點；0～2 個，依序是第 1、第 2 個）：只在入門期、已經
    可以正式選定（打完新手第 2 步、人在霧渡鎮或主城）時才算，其他時候空。**以目前手上的武器（入門
    武器）算**：換別的武器時，第 2 個（要和這把武器實際給的起始兩招互相觸發）可能不同，逐把武器的
    查詢留給 OB-5（:func:`trpg.world.opening.recommended_keywords` 已經收 ``weapon``）。"""
    reselect: RangeReselectView | None = None
    """4 級前的免費重選（OB-3）：正式選定之後（``stage == "chosen"``）才有。"""
    racks: tuple[RangeDemoView, ...]
    dummies: tuple[RangeDummyView, ...]
    intro: tuple[RangeLineView, ...] = ()
    """守印人帶到靶場時說的話。"""
    done: tuple[RangeLineView, ...] = ()
    """確定出發之後守印人說的話（畫面在送出後顯示）。"""


class RangeTrialRequest(_ApiModel):
    """靶場試打：``keywords`` 空＝普攻＋該大類 2 招示範招；給了（最多 2 個）＝依序給的起始技能
    （看示範）。"""

    weapon: str = Field(pattern=ID_PATTERN)
    keywords: tuple[str, ...] = Field(default=(), max_length=2)


class RangeTrialResponse(_ApiModel):
    title_zh: str
    """戰鬥畫面的標題（例「靶場試打：單手劍」）。"""
    demo: bool
    """``True``＝示範招；``False``＝關鍵字的起始技能。"""
    skills_zh: tuple[str, ...]
    battle: BattleResponse


class RangeRecommendResponse(_ApiModel):
    """照玩家 **當下選的那把武器** 算的推薦關鍵字（OB-3；21.5「OB-2 補充」）。"""

    weapon: str
    keywords: tuple[str, ...]
    """標「推薦」的關鍵字，0～2 個（依序是第 1、第 2 個）：找不到能互相觸發的第 2 個就只有 1 個；
    兩招入門招都沒有專屬關鍵字就是空的。只標示、不強制。"""
