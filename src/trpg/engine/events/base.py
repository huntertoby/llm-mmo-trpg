"""事件共用基底與跨領域共用的型別別名。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type AdvantageState = Literal["none", "advantage", "disadvantage"]
type DamageCause = Literal[
    "attack",
    "fall",
    "deadly_terrain",
    "status",
    "effect",
    "explosion",
    "conduct",
    "surface",
    "collision",
    "topple",
    "backlash",
]
"""``attack``：普攻與反應攻擊；``explosion``：爆炸；``conduct``：雷電沿水擴散；
``surface``：站在表面上（毒、聖光）；``collision``：撞擊（Phase 3C-3a）；``topple``：被推倒的物件
壓到（Phase 3C-5a）；``backlash``：賭博型技能的反噬（失敗分支、失手反噬；Phase 3D-7a，不會讓
受到的單位 HP 低於 1）。"""
type ObjectDestroyCause = Literal[
    "damage", "burned", "explosion", "filled", "fell", "effect", "hurled", "toppled"
]
"""``hurled``：被投擲後落地碎掉；``toppled``：被推倒（原物件移除，改由倒塌物取代；Phase 3C-5a）。"""
type MoveMode = Literal[
    "walk", "forced", "teleport", "teleported", "dash", "leap", "swap", "shadowstep", "slide"
]
"""``walk``：主動移動的一步；``forced``：強制位移（推擊等）；``teleport``：傳送（不墜落）；
``dash``：衝鋒的一步（同步行，會墜落與觸發陷阱）；``leap``：跳躍的落點；``swap``：與另一個單位
交換位置（Phase 3D-2）；``shadowstep``：瞬步到敵人身旁（Phase 3D-8d；不墜落，落點的陷阱、表面
照常結算）；``slide``：冰面滑倒後滑行的一格（#123，Phase 6E-2；不墜落、不觸發藉機攻擊，陷阱與
表面照常結算，見 ``unit_slid``）。"""
type SlideStopReason = Literal[
    "off_ice", "max_tiles", "wall", "object", "unit", "edge", "height", "deadly", "interrupted"
]
"""滑行停下的原因（#123）：``off_ice`` 滑到表面外的第一格；``max_tiles`` 滑滿上限（還在冰上）；
下一格是 ``wall`` 牆／不可站立的地形、``object`` 擋路的物件、``unit`` 其他單位、``edge`` 地圖邊緣、
``height`` 高度差 1 以上、``deadly`` 致命地形（停在目前這一格）；``interrupted`` 途中被陷阱等打斷
（定身、暈眩、被推離、倒下、撤離）。"""


class EventBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seq: int = Field(ge=0)
    round: int = Field(ge=1)
