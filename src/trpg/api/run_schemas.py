"""roguelite 一輪的 API 格式（Phase 3-5a；``/api/runs``）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.schemas import BattleResponse
from trpg.narrative.skills import SkillCard
from trpg.roguelite.save import RUN_ID_PATTERN
from trpg.roguelite.state import BattleRecord
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute

__all__ = [
    "BattlePlanOut",
    "CreateRunRequest",
    "HeroOut",
    "LoadRunRequest",
    "NodeOut",
    "OfferOut",
    "RunBattleResponse",
    "RunResponse",
    "RunRules",
    "SaveOut",
    "SaveSummary",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CreateRunRequest(_ApiModel):
    """開新一輪：起始 build、種子、開局配點（省略時全部點在技能最常用的縮放屬性）。"""

    build: str
    seed: int = Field(ge=0, le=MASK64)
    attributes: dict[Attribute, int] | None = None


class LoadRunRequest(_ApiModel):
    run_id: str = Field(pattern=RUN_ID_PATTERN)


class RunRules(_ApiModel):
    """開局規則（``content/roguelite.yaml``）。"""

    start_points: int
    """開局的自由配點數。"""
    base_attribute: int
    """開局六項屬性的基礎值。"""
    hp_per_con_point: int
    """每點體質的最大 HP（``core.yaml``；配點預覽用）。"""


class HeroOut(_ApiModel):
    build_id: str
    name_zh: str
    level: int
    xp: int
    xp_next: int | None
    """升到下一級需要的累計經驗（已到等級上限為 ``None``）。"""
    attributes: dict[Attribute, int]
    hp: int
    max_hp: int
    hp_per_con_point: int
    """每點體質的最大 HP（``core.yaml``；前端的「＋N HP」預覽用）。"""
    hp_con_base: int
    """體質的基準值（高於它才有 HP 加成）。"""
    mana: int
    max_mana: int
    source: int
    source_max: int
    weapon: str
    weapon_name_zh: str = ""
    """武器中文名（Phase 3-18b，一輪中英雄面板顯示）。"""
    weapon_class: str = ""
    """武器大類（melee、ranged、focus）；前端不認得 ``weapon`` 時依此退回武器小圖示。"""
    weapon_traits_zh: tuple[str, ...] = ()
    """武器小特性的說明，每個特性一行（Phase 3-24a1）。"""
    skills: tuple[SkillCard, ...]


class BattlePlanOut(_ApiModel):
    index: int
    map_id: str
    map_name_zh: str
    boss: bool
    enemies: tuple[str, ...]
    """敵人的中文名。"""
    done: bool


class OfferOut(_ApiModel):
    reason: Literal["level_up", "reroll"]
    tier: int
    top_attribute: Attribute
    candidates: tuple[SkillCard, ...]
    off_route: tuple[int, ...]
    """「偏離路線」候選的索引。"""


class NodeOut(_ApiModel):
    """目前節點：``battle``（``battle_index``）、``level_up``（``level``、``points``、
    ``offer``）、``campfire``（``after_battle``、``rerolls_left``、重骰後的 ``offer``）、
    ``ended``（``victory``）。"""

    kind: Literal["battle", "level_up", "campfire", "ended"]
    battle_index: int | None = None
    boss: bool | None = None
    level: int | None = None
    points: int | None = None
    after_battle: int | None = None
    rerolls_left: int | None = None
    offer: OfferOut | None = None
    victory: bool | None = None


class RunResponse(_ApiModel):
    run_id: str
    seed: int
    node: NodeOut
    hero: HeroOut
    battles_done: int
    plan: tuple[BattlePlanOut, ...]
    history: tuple[BattleRecord, ...]
    battle_id: str | None
    """進行中的戰鬥（用 ``/api/battles/{battle_id}`` 操作）；沒有時為 ``None``。"""


class RunBattleResponse(_ApiModel):
    run: RunResponse
    battle: BattleResponse


class SaveOut(_ApiModel):
    run_id: str
    file: str
    """存檔檔名（在伺服器的存檔資料夾內）。"""
    format: str
    in_battle: bool


class SaveSummary(_ApiModel):
    run_id: str
    build_id: str
    build_name_zh: str
    seed: int
    level: int
    battles_done: int
    battles_total: int
    node: Literal["battle", "level_up", "campfire", "ended"]
    in_battle: bool
    victory: bool | None = None
    """已結束的一輪是否勝利；未結束為 ``None``。"""
