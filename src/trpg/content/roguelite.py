"""roguelite 一輪的參數（``content/roguelite.yaml``；Phase 3-5a）。

只定義 schema 與單檔檢查；地圖、單位範本是否存在、起始區放不放得下等跨檔案檢查由
:func:`roguelite_problems`（``trpg.content.library`` 載入時呼叫）負責。數值都是初值，未經模擬。
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.maps import TRAINING_ARCHETYPE, MapDef
from trpg.content.schemas import ContentModel
from trpg.shared.types import Team

__all__ = [
    "BossRules",
    "EncounterStep",
    "ObjectiveRotation",
    "RunRules",
    "RunSourceRules",
    "roguelite_problems",
]


class EncounterStep(ContentModel):
    """一場一般戰鬥的敵人：``options`` 之一（以一輪的種子抽）。"""

    options: tuple[tuple[str, ...], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _non_empty(self) -> EncounterStep:
        if any(not option for option in self.options):
            raise ValueError("每個遭遇選項至少要有 1 名敵人")
        return self


class BossRules(ContentModel):
    """Boss 戰：固定地圖（不進一般抽選）與敵人。3-5b 換成專屬地圖。"""

    map: str = Field(pattern=ID_PATTERN)
    enemies: tuple[str, ...] = Field(min_length=1)


class RunSourceRules(ContentModel):
    """源力在戰鬥之間的取得（設計文件 6.14.4；上限與開場保底在 ``core.yaml``）。"""

    after_battle: int = Field(ge=0)
    """打贏一場後 ＋N。"""
    campfire: int = Field(ge=0)
    """營火 ＋N。"""
    boss_floor: int = Field(ge=0)
    """進入 Boss 戰前至少 N 點。"""


class ObjectiveRotation(ContentModel):
    """勝利條件輪替（Phase 3-22）：一輪的一般戰鬥中至少幾場撤離、幾場守點，其餘全滅。
    Boss 戰一律全滅。"""

    min_escape: int = Field(default=0, ge=0)
    min_defend: int = Field(default=0, ge=0)


class RunRules(ContentModel):
    """``content/roguelite.yaml``。"""

    battles: int = Field(ge=1)
    """一般戰鬥的場數（之後 1 場 Boss）。"""
    map_pool: tuple[str, ...] = Field(min_length=1)
    """一般戰鬥的地圖池；每場先抽一個 **地圖類型**（同一輪不重複），再抽該類型的一張地圖。"""
    encounters: tuple[EncounterStep, ...]
    """第 1 場起每場的敵人（長度必須等於 ``battles``）。"""
    boss: BossRules
    objective_rotation: ObjectiveRotation = Field(default_factory=ObjectiveRotation)
    """一般戰鬥的勝利條件最少場數（Phase 3-22）。"""
    companions: tuple[str, ...]
    """每場的標準隊友（滿狀態、不升級、不跨戰鬥保留）。"""
    max_rounds: int = Field(ge=1)
    """每場的輪數上限（超過算沒有打贏）。"""
    xp_per_battle: int = Field(ge=0)
    level_thresholds: tuple[int, ...] = Field(min_length=1)
    """升到第 2、3、… 級需要的 **累計** 經驗（遞增）。"""
    attribute_points_per_level: int = Field(ge=0)
    base_attribute: int = Field(ge=1)
    """開局六項屬性的基礎值。"""
    start_free_points: int = Field(ge=0)
    """開局自由分配的點數。"""
    offer_size: int = Field(ge=1)
    """升級與重骰的技能候選數。"""
    off_route_per_offer: int = Field(ge=0)
    """候選中「偏離路線」的個數（縮放屬性與主角目前最高屬性不同）。"""
    offer_tier_by_level: tuple[int, ...] = Field(min_length=1)
    """主角等級 → 候選技能的階級（第 1 項為等級 1；超過長度用最後一項）。"""
    offer_max_attempts: int = Field(ge=1)
    """湊齊候選最多嘗試幾個組合器種子。"""
    campfire_after: tuple[int, ...]
    """在第幾場（一般戰鬥）打完之後有營火。"""
    rerolls_per_campfire: int = Field(ge=0)
    source: RunSourceRules

    @model_validator(mode="after")
    def _check(self) -> RunRules:
        if len(self.encounters) != self.battles:
            raise ValueError(f"encounters 必須有 {self.battles} 場，收到 {len(self.encounters)}")
        if list(self.level_thresholds) != sorted(set(self.level_thresholds)):
            raise ValueError("level_thresholds 必須嚴格遞增")
        bad = [n for n in self.campfire_after if not 1 <= n <= self.battles]
        if bad or len(set(self.campfire_after)) != len(self.campfire_after):
            raise ValueError(f"campfire_after 必須是 1～{self.battles} 且不重複")
        if self.off_route_per_offer > self.offer_size:
            raise ValueError("off_route_per_offer 不可超過 offer_size")
        if self.objective_rotation.min_escape + self.objective_rotation.min_defend > self.battles:
            raise ValueError("objective_rotation 的最少場數總和不可超過 battles")
        if self.boss.map in self.map_pool:
            raise ValueError(f"Boss 地圖 {self.boss.map} 不可在一般地圖池內")
        return self

    def offer_tier(self, level: int) -> int:
        table = self.offer_tier_by_level
        return table[min(level, len(table)) - 1]

    def summary(self) -> str:
        return f"{self.battles} 場 ＋ Boss（{self.boss.map}），地圖池 {len(self.map_pool)} 張"


def roguelite_problems(
    rules: RunRules,
    maps: Mapping[str, MapDef],
    units: Mapping[str, UnitTemplate],
    tiers: Mapping[int, int],
) -> list[str]:
    """跨檔案檢查：地圖與單位範本存在、雙方起始區放得下、地圖類型夠抽、階級有預算。"""
    problems: list[str] = []
    unknown_maps = sorted({m for m in (*rules.map_pool, rules.boss.map) if m not in maps})
    if unknown_maps:
        return [f"未知的地圖：{', '.join(unknown_maps)}"]
    enemy_sets = [o for step in rules.encounters for o in step.options]
    templates = {t for option in enemy_sets for t in option} | set(rules.boss.enemies)
    templates |= set(rules.companions)
    unknown_units = sorted(t for t in templates if t not in units)
    if unknown_units:
        problems.append(f"未知的單位範本：{', '.join(unknown_units)}")
    training = sorted(m for m in rules.map_pool if maps[m].archetype == TRAINING_ARCHETYPE)
    if training:
        problems.append(f"技能工坊的靶場不能進地圖池：{', '.join(training)}")
    archetypes = {maps[m].archetype for m in rules.map_pool}
    if len(archetypes) < rules.battles:
        problems.append(f"地圖池只有 {len(archetypes)} 種地圖類型，不夠 {rules.battles} 場不重複")
    most_enemies = max(len(o) for o in [*enemy_sets, rules.boss.enemies])
    allies = 1 + len(rules.companions)
    for map_id in sorted({*rules.map_pool, rules.boss.map}):
        zones = maps[map_id].start_zones
        if len(zones[Team.ALLY]) < allies or len(zones[Team.ENEMY]) < most_enemies:
            problems.append(f"地圖 {map_id} 的起始區放不下 {allies} 名我方或 {most_enemies} 名敵人")
    bad_tiers = sorted({t for t in rules.offer_tier_by_level if t not in tiers})
    if bad_tiers:
        problems.append(f"offer_tier_by_level 有沒有預算的階級：{bad_tiers}")
    return problems + _rotation_problems(rules, maps)


def _rotation_problems(rules: RunRules, maps: Mapping[str, MapDef]) -> list[str]:
    """勝利條件輪替要「不論抽到哪幾種地圖類型都排得出來」：支援某條件的地圖類型數，至少要有
    「未被抽中的類型數 ＋ 兩種條件的最少場數總和」（才保證抽中的類型裡有足夠的不同場次可用）。"""
    rotation = rules.objective_rotation
    archetypes = {maps[m].archetype for m in rules.map_pool}
    spare = max(0, len(archetypes) - rules.battles)
    need = rotation.min_escape + rotation.min_defend
    problems: list[str] = []
    for kind, minimum in (("escape", rotation.min_escape), ("defend", rotation.min_defend)):
        if minimum == 0:
            continue
        capable = {maps[m].archetype for m in rules.map_pool if maps[m].supports_objective(kind)}
        if len(capable) < spare + need:
            problems.append(
                f"支援 {kind} 的地圖類型只有 {len(capable)} 種，"
                f"不足以保證每輪排得出 {minimum} 場（至少需要 {spare + need} 種）"
            )
    return problems
