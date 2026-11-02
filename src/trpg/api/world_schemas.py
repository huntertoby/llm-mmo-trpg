"""大世界的 API 格式（Phase 5A-5；``/api/world``，``docs/phases/Phase5計畫.md`` 10.3）。

``WorldView`` 是地點圖畫面的整份資料，全部由後端算好（前端不寫規則）。未發現的隱藏地點與連到它的
連線不放進回應。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trpg.api.schemas import BattleResponse
from trpg.narrative.skills import SkillCard
from trpg.shared.rng import MASK64
from trpg.world.actions import (
    CampAction,
    LoadoutAction,
    RestAction,
    RetreatAction,
    TeleportAction,
    TravelAction,
)

__all__ = [
    "CreateWorldCharacterRequest",
    "EncounterEnemyView",
    "EncounterView",
    "HereView",
    "TeleportOption",
    "WorldActionRequest",
    "WorldBattleResponse",
    "WorldCharacterSummary",
    "WorldCharacterView",
    "WorldClockView",
    "WorldLocationView",
    "WorldMapView",
    "WorldView",
]

NAME_MAX = 12


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


type WorldActionRequest = Annotated[
    TravelAction | CampAction | RetreatAction | RestAction | LoadoutAction | TeleportAction,
    Field(discriminator="kind"),
]
"""``POST /api/world/characters/{id}/actions`` 的請求（``fight`` 走開戰端點）。"""


class CreateWorldCharacterRequest(_ApiModel):
    """建立大世界角色（07 7.6 創角）。選項沿用 ``GET /api/runs/start-options``。"""

    name: str = Field(min_length=1, max_length=NAME_MAX)
    """角色名稱（只顯示用；前後空白會去掉）。"""
    weapon: str
    keywords: tuple[str, ...]
    race: str | None = None
    origin: str | None = None
    seed: int | None = Field(default=None, ge=0, le=MASK64)
    """起始技能的種子；省略由伺服器亂數。"""

    @field_validator("name")
    @classmethod
    def _strip(cls, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("名稱不可空白")
        return name


class WorldCharacterSummary(_ApiModel):
    character_id: str
    name: str
    level: int
    region_name_zh: str
    location_name_zh: str


class WorldCharacterView(_ApiModel):
    character_id: str
    name: str
    level: int
    xp: int
    xp_next: int | None
    """下一級的經驗門檻；已到頂為 ``None``。"""
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    supplies: int
    max_supplies: int
    fatigued: bool
    attribute_points: int
    weapon_name_zh: str
    race_name_zh: str | None
    skills: tuple[SkillCard, ...]
    """裝備的技能。"""
    bench: tuple[SkillCard, ...]
    """備用技能（擁有但沒裝上）。"""
    slots_zh: str
    """技能欄位上限的說明。"""


class WorldLocationView(_ApiModel):
    id: str
    name_zh: str
    kind: str
    kind_zh: str
    level_zh: str | None
    """建議等級（例：``Lv 3～4``）；城鎮與傳送點沒有。"""
    description_zh: str
    x: int
    y: int
    current: bool
    adjacent: bool
    """和目前位置相鄰。"""
    blocked_zh: str | None
    """相鄰但現在不能走過去的原因（例：還沒開放、有遭遇）；可以走時為 ``None``。"""
    cleared: bool
    """已清空（還沒重生，9.6.7 #15）。"""
    hidden: bool
    """隱藏地點（已發現才會出現在回應裡）。"""


class WorldMapView(_ApiModel):
    region: str
    name_zh: str
    level_zh: str
    locations: tuple[WorldLocationView, ...]
    edges: tuple[tuple[str, str], ...]


class TeleportOption(_ApiModel):
    region: str
    name_zh: str


class HereView(_ApiModel):
    location: str
    name_zh: str
    kind_zh: str
    description_zh: str
    can_rest: bool
    can_loadout: bool
    camp_problem_zh: str | None
    """不能紮營的原因；可以紮營時為 ``None``。"""
    camped: bool
    """正在這裡紮營（營火）。"""
    teleports: tuple[TeleportOption, ...]
    hasten_cost: int
    camp_cost: int


class EncounterEnemyView(_ApiModel):
    name_zh: str
    elite: bool
    affix_zh: str | None


class EncounterView(_ApiModel):
    location: str
    location_name_zh: str
    enemy_level: int
    map_name_zh: str
    weather_zh: str
    day_phase_zh: str
    enemies: tuple[EncounterEnemyView, ...]
    retreat_to_zh: str
    fatigued: bool
    """開場帶疲憊（HP 打折，9.6.9 #98）。"""
    hero_hp: int
    """主角開場 HP。"""
    in_battle: bool


class WorldClockView(_ApiModel):
    time_zh: str
    """遊戲內時刻 ``HH:MM``。"""
    day_phase: Literal["day", "night"]
    day_phase_zh: str
    weather_zh: str


class WorldView(_ApiModel):
    character: WorldCharacterView
    map: WorldMapView
    here: HereView
    encounter: EncounterView | None
    clock: WorldClockView
    events: tuple[str, ...]
    """這次請求的世界事件（中文句子）。"""
    battle_id: str | None


class WorldBattleResponse(_ApiModel):
    world: WorldView
    battle: BattleResponse
