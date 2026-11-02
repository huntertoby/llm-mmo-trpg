"""大世界規則的數值（``content/world/rules.yaml``，Phase 5A-2）。

``docs/phases/Phase5計畫.md`` 6.4：補給（9.6.7 #11）、紮營花費（9.6.11 #114）、趕路（9.6.7 #9）、
遇敵機率（9.6.7 #9「越危險的區越高」）、隱藏地點感知判定的 DC（9.6.11 #112）、各區天氣權重
（05 5.1「各區天氣傾向」、9.6.10 #104）。數值都是開發 PM 定的初值，之後用模擬定（9.6.10
「數值類」）；改數值只改資料、不改程式（守則 4）。規則本身在 ``trpg.world``。

Phase 5A-4 加上 ``battle``（遇敵戰鬥的回寫：經驗、疲憊、已清空與重生）與 ``enemy_growth``（敵人依
地點建議等級成長）；兩者都有預設值，舊的精簡 content 照常載入。

Phase 5A-6 加上 ``hero_growth``（主角的技能階級表、每級靈感點、精英首殺靈感、等級上限）；有預設值。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.regions import RegionTable
from trpg.content.schemas import ContentModel

__all__ = [
    "BattleRules",
    "EncounterRates",
    "EnemyGrowthRules",
    "HastenRules",
    "HeroGrowthRules",
    "PerceptionRules",
    "RegionWeather",
    "SupplyRules",
    "WeatherWeights",
    "WorldRules",
    "world_rules_problems",
]


class SupplyRules(ContentModel):
    """補給的上限與新角色帶的量（9.6.7 #11）。"""

    max: int = Field(ge=0)
    start: int = Field(ge=0)

    @model_validator(mode="after")
    def _start_within_max(self) -> SupplyRules:
        if self.start > self.max:
            raise ValueError(f"supplies.start（{self.start}）不可超過 max（{self.max}）")
        return self


class HastenRules(ContentModel):
    """趕路（9.6.7 #9）：花補給降低遇敵機率。"""

    cost: int = Field(ge=0)
    encounter_permille: int = Field(ge=0, le=1000)
    """趕路時的遇敵機率倍率（‰）。"""


class EncounterRates(ContentModel):
    """每一步的遇敵機率（‰）＝ min(max, base ＋ per_level ×（建議等級 − 1））。"""

    base_permille: int = Field(ge=0, le=1000)
    per_level_permille: int = Field(ge=0, le=1000)
    max_permille: int = Field(ge=0, le=1000)

    def permille_for(self, level: int | None) -> int:
        """建議等級 ``level`` 的遇敵機率；``None``（城鎮、傳送點）＝ 0。"""
        if level is None:
            return 0
        raw = self.base_permille + self.per_level_permille * max(0, level - 1)
        return min(self.max_permille, raw)


class PerceptionRules(ContentModel):
    """隱藏地點的感知判定 DC ＝ ``dc_base`` ＋ 建議等級 ÷ ``level_divisor``（捨去；#112）。"""

    dc_base: int
    level_divisor: int = Field(ge=1)

    def dc_for(self, level: int) -> int:
        return self.dc_base + level // self.level_divisor


class WeatherWeights(ContentModel):
    """半天的天氣權重：天氣 ID（``weather.yaml``）→ 權重（≥ 0，總和 > 0）。"""

    day: dict[str, int]
    night: dict[str, int]

    @model_validator(mode="after")
    def _weights(self) -> WeatherWeights:
        for phase, weights in (("day", self.day), ("night", self.night)):
            if any(w < 0 for w in weights.values()):
                raise ValueError(f"天氣權重（{phase}）不可為負")
            if sum(weights.values()) <= 0:
                raise ValueError(f"天氣權重（{phase}）總和必須大於 0")
        return self

    def for_phase(self, phase: str) -> tuple[tuple[str, int], ...]:
        """``phase``（``day``／``night``）的權重，依天氣 ID 排序（守則 2）。"""
        weights = self.day if phase == "day" else self.night
        return tuple(sorted(weights.items()))


class RegionWeather(WeatherWeights):
    """一個區域的天氣權重。"""

    region: str = Field(pattern=ID_PATTERN)


ClearKind = Literal[
    "camp", "ruin", "altar", "anomaly", "caravan", "village", "secret", "elite_lair", "boss"
]
"""打贏後可以寫「已清空」的地點種類（城鎮、傳送點不會遇敵，不在內）。"""


class BattleRules(ContentModel):
    """遇敵戰鬥與勝負回寫（5A-4；``docs/phases/Phase5計畫.md`` 9.4）。"""

    max_rounds: int = Field(default=30, ge=1)
    xp_per_battle: int = Field(default=100, ge=0)
    """打贏一場的經驗（Q8 初值；等級門檻沿用原型 ``roguelite.yaml`` 的 ``level_thresholds``）。"""
    fatigue_hp_permille: int = Field(default=800, ge=1, le=1000)
    """疲憊：全滅後下一場開場 HP 上限（最大 HP 的 ‰；9.6.9 #98）。"""
    clear_kinds: tuple[ClearKind, ...] = ("camp",)
    """打贏後寫「已清空」的地點種類（9.6.7 #15）。"""
    respawn_seconds: int = Field(default=1800, ge=0)
    """已清空到重生的秒數（遊戲內 1 天＝1800 秒）。"""

    @model_validator(mode="after")
    def _unique_kinds(self) -> BattleRules:
        if len(set(self.clear_kinds)) != len(self.clear_kinds):
            raise ValueError("battle.clear_kinds 不可重複")
        return self


class EnemyGrowthRules(ContentModel):
    """敵人依地點建議等級成長（5A-4 追加 A；和主角同樣的成長，範本＝1 級基準）。"""

    attribute_points_per_level: int = Field(default=2, ge=0)
    skill_tier_by_level: tuple[int, ...] = Field(
        default=(1, 1, 1, 2, 2, 2, 2, 3, 3, 3), min_length=1
    )
    """等級 → 技能階級（07 7.6：1～3 級 1 階、4～7 級 2 階、8～10 級 3 階）；
    超出表的等級用最後一格。"""

    @model_validator(mode="after")
    def _tiers(self) -> EnemyGrowthRules:
        tiers = self.skill_tier_by_level
        if any(t < 1 for t in tiers) or list(tiers) != sorted(tiers):
            raise ValueError("enemy_growth.skill_tier_by_level 必須 ≥ 1 且不遞減")
        return self

    def tier_for(self, level: int) -> int:
        table = self.skill_tier_by_level
        return table[min(max(level, 1), len(table)) - 1]


class HeroGrowthRules(ContentModel):
    """主角在大世界的成長（5A-6；07 7.6、7.8，06 6.34.2）。經驗門檻沿用原型
    ``level_thresholds``。"""

    skill_tier_by_level: tuple[int, ...] = Field(
        default=(1, 1, 1, 2, 2, 2, 2, 3, 3, 3), min_length=1
    )
    """角色等級 → 角色階級（07 7.6：1～3 級 1 階、4～7 級 2 階、8～10 級 3 階；玩法 PM 定）；
    超出表的等級用最後一格。原型的 ``offer_tier_by_level`` 只留給 roguelite。"""
    insight_per_level: int = Field(default=2, ge=0)
    """每升 1 級給的靈感點（06 6.34.2 大世界）。"""
    insight_per_elite_kind: int = Field(default=1, ge=0)
    """每種精英首殺給的靈感點（06 6.34.2）。"""
    level_cap: int = Field(default=10, ge=1)
    """等級上限（07 7.8、09 9.7 第一季 10 級）；到頂後經驗照累積、不換算（換算比例待定）。"""

    @model_validator(mode="after")
    def _tiers(self) -> HeroGrowthRules:
        tiers = self.skill_tier_by_level
        if any(t < 1 for t in tiers) or list(tiers) != sorted(tiers):
            raise ValueError("hero_growth.skill_tier_by_level 必須 ≥ 1 且不遞減")
        return self

    def tier_for(self, level: int) -> int:
        table = self.skill_tier_by_level
        return table[min(max(level, 1), len(table)) - 1]


class WorldRules(ContentModel):
    """``content/world/rules.yaml``。"""

    supplies: SupplyRules
    camp_cost: int = Field(ge=0)
    hasten: HastenRules
    encounter: EncounterRates
    perception: PerceptionRules
    default_weather: WeatherWeights = WeatherWeights(day={"clear": 1}, night={"night": 1})
    """沒有列在 ``weather`` 的區域用這組。"""
    weather: tuple[RegionWeather, ...] = ()
    battle: BattleRules = BattleRules()
    enemy_growth: EnemyGrowthRules = EnemyGrowthRules()
    hero_growth: HeroGrowthRules = HeroGrowthRules()

    @model_validator(mode="after")
    def _unique_regions(self) -> WorldRules:
        seen: set[str] = set()
        for entry in self.weather:
            if entry.region in seen:
                raise ValueError(f"天氣權重的區域重複：{entry.region}")
            seen.add(entry.region)
        return self

    def weather_for(self, region: str) -> WeatherWeights:
        for entry in self.weather:
            if entry.region == region:
                return entry
        return self.default_weather

    def summary(self) -> str:
        return (
            f"補給上限 {self.supplies.max}、紮營 {self.camp_cost}、"
            f"遇敵 {self.encounter.base_permille}～{self.encounter.max_permille}‰、"
            f"{len(self.weather)} 區天氣"
        )


def world_rules_problems(
    rules: WorldRules, *, regions: RegionTable | None, weather_ids: Mapping[str, object]
) -> list[str]:
    """跨檔案檢查：天氣 ID 在 ``weather.yaml``、區域在 ``regions.yaml``。回傳排序過的問題。"""
    problems: list[str] = []
    groups: list[tuple[str, WeatherWeights]] = [("default_weather", rules.default_weather)]
    groups += [(f"weather[{w.region}]", w) for w in rules.weather]
    for label, weights in groups:
        for weather_id in sorted({*weights.day, *weights.night}):
            if weather_id not in weather_ids:
                problems.append(f"{label}：未知的天氣 {weather_id}")
    if rules.weather:
        if regions is None:
            problems.append("缺少 regions.yaml，無法檢查天氣權重的區域")
        else:
            known = {r.id for r in regions.regions}
            problems += [
                f"weather：未知的區域 {w.region}" for w in rules.weather if w.region not in known
            ]
    return sorted(problems)
