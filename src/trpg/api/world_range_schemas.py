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


class RangeView(_ApiModel):
    """未完成開局（在主城工坊靶場）的畫面資料（TR-1，#134）。"""

    seed: int
    """開局種子：關鍵字預覽（``/api/runs/start-preview``）帶它，預覽的招就是確定出發會給的。"""
    stage: Literal["pick_class", "starter", "chosen"]
    """開局階段（OB-1，#150）：選大類中／入門期／正式選定後到 4 級前。"""
    weapon_class: Literal["melee", "ranged", "focus"] | None
    """選定的大類（``pick_class`` 為 ``None``）。"""
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
