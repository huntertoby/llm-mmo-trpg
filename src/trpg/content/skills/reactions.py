"""反應與陷阱規格。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.constants import ReactionEvent


class ReactionSpec(ContentModel):
    """反應技的觸發設定（``docs/phases/Phase2E計畫.md`` 4.1）。

    - ``hit_by_melee``：持有者被近戰攻擊命中、傷害結算之後（仍存活）。
    - ``hit_by_attack``：被任何攻擊命中、傷害結算之後（仍存活）。
    - ``ally_hit_adjacent``：與持有者相鄰（曼哈頓距離 1）的友方被攻擊命中、**傷害結算之前**
      （只給 ``intercept`` 使用）。
    - ``enemy_leaves_adjacent``：敵人離開相鄰格時（同藉機攻擊）。
    - ``hit_by_spell``（3D-3）：被法術技（``category: spell``）命中、**傷害之前**；另一方是施放者。
    - ``ally_downed``（3D-3）：持有者視野內的友方倒下之後；另一方是倒下的友方（已倒下，所以形狀
      必須是 ``self``）。
    - ``enemy_enters_adjacent``（3D-3）：敵方單位 **主動移動**（步行、衝鋒、直線衝撞）進入持有者
      相鄰格之後（強制位移、傳送、跳躍、互換不算；本來就相鄰的移動不算「進入」）。
    - ``ally_targeted``（3D-3）：與持有者相鄰的友方被敵方單體技能或普攻選為目標、**命中判定之前**；
      另一方是攻擊者。
    """

    event: ReactionEvent


class TrapSpec(ContentModel):
    """陷阱技能的設定（``docs/phases/Phase2E計畫.md`` 5.2；技能必須有 ``place_trap`` 原語）。

    - ``trigger``：``enter`` 為敵人進入陷阱格時觸發、``rounds`` 輪（放置者的回合開始時倒數）後
      未觸發就消失；``delay`` 為 ``rounds`` 輪後（放置者回合開始時）觸發。
    - ``shape``：觸發時以陷阱格為中心的影響範圍；形狀 ID（``single``、``cross``、``square3``）須
      存在於 ``content/skill_shapes.yaml``（跨檔案檢查，見 :func:`skill_problems`；Phase 2F-1
      3.2——取代原本的 ``Literal``，讓引擎的形狀展開能涵蓋資料檔新增的形狀而不必改程式）。
    - 技能其餘的效果就是陷阱觸發時的效果（自動命中；狀態照常擲抵抗）。
    """

    trigger: Literal["enter", "delay"]
    rounds: int = Field(default=2, ge=1, le=6)
    shape: str = Field(default="single", pattern=ID_PATTERN)
