"""roguelite 一輪的 API 格式（Phase 3-5a；``/api/runs``）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.api.schemas import BattleResponse
from trpg.content.maps import Objective
from trpg.narrative.skills import KeywordRef, SkillCard
from trpg.roguelite.save import RUN_ID_PATTERN
from trpg.roguelite.state import BattleRecord
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute

__all__ = [
    "BattlePlanOut",
    "CreateRunRequest",
    "DevPackOut",
    "HeroOut",
    "LoadRunRequest",
    "NodeOut",
    "OfferOut",
    "OfferTagOut",
    "RunBattleResponse",
    "RunResponse",
    "RunRules",
    "SaveOut",
    "SaveSummary",
    "SkillGrowthOut",
    "StartKeywordOption",
    "StartOptions",
    "StartPreview",
    "StartPreviewRequest",
    "StartWeaponOption",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CreateRunRequest(_ApiModel):
    """開新一輪（Phase 3-24b2）：``weapon`` ＋ ``keywords``（一般開局），或 ``dev_pack``（開發者
    起始包），或 ``build``（回歸範本，開發與測試用）——三者擇一；種子；開局配點（省略時全部點在
    武器的縮放屬性，以 build 開局時為技能最常用的縮放屬性）。"""

    build: str | None = None
    seed: int = Field(ge=0, le=MASK64)
    attributes: dict[Attribute, int] | None = None
    weapon: str | None = None
    """起始武器（Phase 3-24b2）。"""
    keywords: tuple[str, ...] | None = None
    """選的關鍵字（Phase 3-24b2；``roguelite.yaml`` 的 ``start.keywords`` 個）。"""
    dev_pack: str | None = None
    """開發者起始包 ID（Phase 3-24b2，開發用）。"""

    @model_validator(mode="after")
    def _one_start(self) -> CreateRunRequest:
        given = [
            self.build is not None,
            self.dev_pack is not None,
            self.weapon is not None or self.keywords is not None,
        ]
        if sum(given) != 1:
            raise ValueError("開局必須擇一：weapon＋keywords、dev_pack 或 build")
        if (self.weapon is None) != (self.keywords is None):
            raise ValueError("weapon 與 keywords 必須一起給")
        return self


class StartWeaponOption(_ApiModel):
    """開局可選的武器（Phase 3-24b2）。"""

    id: str
    name_zh: str
    weapon_class: str
    traits_zh: tuple[str, ...] = ()
    hp: int
    """選這把武器時主角的最大 HP（未配點）。"""
    mana: int


class StartOptions(_ApiModel):
    """開局選項（Phase 3-24b2）：全部武器、全部關鍵字、要選幾個關鍵字。"""

    weapons: tuple[StartWeaponOption, ...]
    keywords: tuple[KeywordRef, ...]
    keyword_count: int


class StartPreviewRequest(_ApiModel):
    """開局預覽：武器、種子與目前已選的關鍵字（依選擇順序）。"""

    weapon: str
    seed: int = Field(ge=0, le=MASK64)
    keywords: tuple[str, ...] = ()


class StartKeywordOption(_ApiModel):
    """一個關鍵字的起始技能預覽：``skill`` 為 ``None`` 表示這把武器湊不到（不可選）。已選的關鍵字
    是實際會拿到的技能；沒選的是「下一個選它」時會拿到的技能。"""

    keyword: KeywordRef
    selected: bool
    skill: SkillCard | None


class StartPreview(_ApiModel):
    weapon: str
    seed: int
    options: tuple[StartKeywordOption, ...]


class DevPackOut(_ApiModel):
    """開發者起始包（Phase 3-24b2，開發用；只在開發者選單顯示）。"""

    id: str
    label_zh: str
    weapon: str
    weapon_name_zh: str
    keywords: tuple[KeywordRef, ...]


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


class SkillGrowthOut(_ApiModel):
    """技能成長的規則（Phase 3-26a，``content/skill_growth.yaml``）：前端不寫死數值。"""

    max_level: int
    upgrade_cost: int
    points_per_level: int
    trait_level: int
    evolve_level: int
    evolve_uses: int = 0
    """升到 ``evolve_level`` 前要用過的次數（Phase 3-26b）。"""


class EvolutionOptionOut(_ApiModel):
    """一支分歧進化（Phase 3-26b）：``index`` 是送 ``evolve`` 時的索引。"""

    index: int
    branch: Literal["deepen", "bridge"]
    label_zh: str
    """「加深」或「橋接」。"""
    template: str
    keyword: KeywordRef | None
    """帶的關鍵字（換形狀等不看關鍵字的模板為 ``None``）。"""
    summary_zh: str
    fallback: bool
    """橋接做不出來、改用第二個加深模板。"""
    card: SkillCard
    """進化後的技能卡（等級沿用目前的等級＋升上去的級數，由前端顯示）。"""


class EvolutionChoiceOut(_ApiModel):
    """一個升到分歧進化那一級時要二選一的技能（已達門檻、還沒進化）。"""

    skill_id: str
    name_zh: str
    options: tuple[EvolutionOptionOut, ...]
    """0～2 支；沒有任何合格的進化時為空（照常升級，不進化）。"""


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
    start_keywords: tuple[KeywordRef, ...] = ()
    """開局選的關鍵字（Phase 3-24b2；以 build 開局時為空）。"""
    dev_pack: str | None = None
    """開發者起始包 ID（Phase 3-24b2，開發用）。"""
    skill_points: int = 0
    """還沒花的技能點（Phase 3-26a）。"""
    skill_growth: SkillGrowthOut | None = None
    bench: tuple[SkillCard, ...] = ()
    """備用技能（Phase 3-26a；卸下的技能，等級保留，卡片的 ``growth`` 帶實際等級）。"""
    evolutions: tuple[EvolutionChoiceOut, ...] = ()
    """升到分歧進化那一級時可選的兩支（Phase 3-26b；只列已達門檻、還沒進化的裝備中主動技能）。"""


class BattlePlanOut(_ApiModel):
    index: int
    map_id: str
    map_name_zh: str
    boss: bool
    enemies: tuple[str, ...]
    """敵人的中文名。"""
    done: bool
    objective: Objective
    """本場的勝利條件（Phase 3-22）：全滅、撤離（出口格＋輪數）或守點（守點格＋輪數）。"""


class OfferTagOut(_ApiModel):
    """候選的標示（Phase 3-24b2）：加深／橋接／新方向與它帶的關鍵字。"""

    kind: Literal["deepen", "bridge", "new"]
    label_zh: str
    """「加深」「橋接」「新方向」。"""
    keywords: tuple[KeywordRef, ...]
    fallback: bool
    """定義做不到而退回（例：只持有 1 個關鍵字時的橋接改成「持有的 ＋ 新的」）。"""
    source: Literal["pool", "composer"]


class OfferOut(_ApiModel):
    reason: Literal["level_up", "reroll"]
    tier: int
    top_attribute: Attribute
    candidates: tuple[SkillCard, ...]
    off_route: tuple[int, ...]
    """「偏離路線」候選的索引。"""
    tags: tuple[OfferTagOut, ...] = ()
    """與 ``candidates`` 一一對應的標示（Phase 3-24b2）。"""


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
