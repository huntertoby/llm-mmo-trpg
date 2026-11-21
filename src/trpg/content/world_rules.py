"""大世界規則的數值（``content/world/rules.yaml``，Phase 5A-2）。

``docs/phases/Phase5計畫.md`` 6.4：補給（9.6.7 #11）、紮營花費（9.6.11 #114）、趕路（9.6.7 #9）、
遇敵機率（9.6.7 #9「越危險的區越高」）、隱藏地點感知判定的 DC（9.6.11 #112）、各區天氣權重
（05 5.1「各區天氣傾向」、9.6.10 #104）。數值都是開發 PM 定的初值，之後用模擬定（9.6.10
「數值類」）；改數值只改資料、不改程式（守則 4）。規則本身在 ``trpg.world``。

Phase 5A-4 加上 ``battle``（遇敵戰鬥的回寫：經驗、疲憊、已清空與重生）與 ``enemy_growth``（敵人依
地點建議等級成長）。

Phase 5A-6 加上 ``hero_growth``（主角的技能階級表、每級靈感點、精英首殺靈感、等級上限）。

Phase 6C-R2 加上 ``field``（實地地圖的規則數值：敵人視野、潛行、隱藏入口感知距離、就地切戰場、
一次走幾格；原本寫死在 ``trpg.world`` 的常數）。

HC-4d：數字欄位都沒有程式預設值，一律寫在 ``world/rules.yaml``（值照搬原本的預設）；
``field_maps`` 是實地地圖的大小建議與每區傳送石數（原本是 ``trpg.content.fields`` 的常數）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.fields import FieldMapRules
from trpg.content.regions import RegionTable
from trpg.content.schemas import ContentModel

__all__ = [
    "WALK_PATH_FORMAT_MAX",
    "BattleRules",
    "CalendarRules",
    "DayPartHours",
    "EncounterRates",
    "EnemyGrowthRules",
    "FieldRules",
    "HastenRules",
    "HeroGrowthRules",
    "OpportunityRules",
    "PerceptionRules",
    "RegionWeather",
    "SupplyRules",
    "WeatherWeights",
    "WishRules",
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

    max_rounds: int = Field(ge=1)
    fatigue_hp_permille: int = Field(ge=1, le=1000)
    """疲憊：全滅後下一場開場 HP 上限（最大 HP 的 ‰；9.6.9 #98）。"""
    clear_kinds: tuple[ClearKind, ...] = ("camp",)
    """打贏後寫「已清空」的地點種類（9.6.7 #15）。"""
    respawn_seconds: int = Field(ge=0)
    """已清空到重生的秒數（遊戲內 1 天＝1800 秒）。"""

    @model_validator(mode="after")
    def _unique_kinds(self) -> BattleRules:
        if len(set(self.clear_kinds)) != len(self.clear_kinds):
            raise ValueError("battle.clear_kinds 不可重複")
        return self


class EnemyGrowthRules(ContentModel):
    """敵人依地點建議等級成長（5A-4 追加 A；和主角同樣的成長，範本＝1 級基準）。

    ``attribute_points_per_level`` 是屬性點（量類，HC-2）：沒有 Python 預設值，一律寫在
    ``world/rules.yaml``。"""

    attribute_points_per_level: int = Field(ge=0)
    skill_tier_by_level: tuple[int, ...] = Field(min_length=1)
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


XP_SOURCES: Final = (
    "battle",
    "elite",
    "situation_success",
    "situation_partial",
    "quest_chain_step",
    "main_step",
    "bounty",
    "hidden_location",
)
"""經驗來源（``xp.shares_permille`` 的鍵；各來源的份數寫在 ``world/rules.yaml``，HC-4d）。"""


class XpRules(ContentModel):
    """經驗來源與份數（5A-SIM2；07 7.8 方案 B）。

    1 份經驗＝``base`` ×（1000 ＋ ``level_permille`` ×（地點建議等級 − 1））÷ 1000；各來源給幾份寫在
    ``shares_permille``（1000‰＝1 份）。任務鏈、主線、懸賞、隱藏地點的份數先寫在這裡，等那些功能做好
    時接上。"""

    base: int = Field(ge=0)
    level_permille: int = Field(ge=0)
    shares_permille: dict[str, int]

    @model_validator(mode="after")
    def _shares(self) -> XpRules:
        missing = [k for k in XP_SOURCES if k not in self.shares_permille]
        extra = sorted(set(self.shares_permille) - set(XP_SOURCES))
        if missing or extra:
            raise ValueError(f"xp.shares_permille 缺 {missing}、多 {extra}")
        if any(v < 0 for v in self.shares_permille.values()):
            raise ValueError("xp.shares_permille 不可為負")
        return self

    def share_xp(self, location_level: int) -> int:
        """地點建議等級 ``location_level`` 的 1 份經驗。"""
        level = max(1, location_level)
        return self.base * (1000 + self.level_permille * (level - 1)) // 1000

    def xp_for(self, source: str, location_level: int) -> int:
        """``source`` 在地點建議等級 ``location_level`` 給的經驗。"""
        return self.share_xp(location_level) * self.shares_permille[source] // 1000


class HeroGrowthRules(ContentModel):
    """主角在大世界的成長（5A-6；07 7.6、7.8，06 6.34.2）。"""

    level_thresholds: tuple[int, ...] = Field(min_length=1)
    """升到第 2、3、… 級需要的 **累計** 經驗（嚴格遞增；5A-SIM2 方案 B）。"""

    skill_tier_by_level: tuple[int, ...] = Field(min_length=1)
    """角色等級 → 角色階級（07 7.6：1～3 級 1 階、4～7 級 2 階、8～10 級 3 階；玩法 PM 定）；
    超出表的等級用最後一格。原型的 ``offer_tier_by_level`` 只留給 roguelite。"""
    insight_per_level: int = Field(ge=0)
    """每升 1 級給的靈感點（06 6.34.2 大世界）。"""
    insight_per_elite_kind: int = Field(ge=0)
    """每種精英首殺給的靈感點（06 6.34.2）。"""
    level_cap: int = Field(ge=1)
    """等級上限（07 7.8、09 9.7 第一季 10 級）；到頂後經驗照累積、不換算（換算比例待定）。"""

    @model_validator(mode="after")
    def _tiers(self) -> HeroGrowthRules:
        if list(self.level_thresholds) != sorted(set(self.level_thresholds)):
            raise ValueError("hero_growth.level_thresholds 必須嚴格遞增")
        tiers = self.skill_tier_by_level
        if any(t < 1 for t in tiers) or list(tiers) != sorted(tiers):
            raise ValueError("hero_growth.skill_tier_by_level 必須 ≥ 1 且不遞減")
        return self

    def tier_for(self, level: int) -> int:
        table = self.skill_tier_by_level
        return table[min(max(level, 1), len(table)) - 1]


class OpportunityRules(ContentModel):
    """機遇給的技能三選一（Phase 5B-4c；07 7.6「通常同階，15% 機率高 1 階，每人每季最多
    1 次」）。"""

    tier_up_permille: int = Field(ge=0, le=1000)
    """這組候選高 1 階的機率 ‰（確定性種子擲）。"""
    tier_up_per_season: int = Field(ge=0)
    """每個角色（一季一份）最多幾次高 1 階。"""
    guarantee_from_day: int = Field(ge=0)
    """機遇保底（Phase 5B-4d，07 7.6「第 7 天前保底 1 次」）：賽季第幾天起，還沒遇過機遇的角色
    走到機遇骨架的地點就一定觸發（不看天氣、時段與機率）；0 ＝ 不保底。"""
    guarantee_waives_keyword: bool = False
    """保底觸發的機遇不檢查 ``requires_keyword``（Phase 5B-4e；三選一照樣指定該關鍵字）。"""


class WishRules(ContentModel):
    """許願池（Phase WP-1；07 7.6、#88：主城花任務幣許願，每週 2 次；都不拿次數照扣、任務幣退一半）
    。
    數字是 WP-1 的初值（``docs/phases/PhaseWP計畫.md`` 第 6 節待決 2、3、6），之後只改這裡。"""

    per_week: int = Field(ge=0)
    """每個角色每週能許幾次（09 9.6 上限表）。"""
    cost_quest_coins: int = Field(ge=0)
    """每次許願的任務幣（設計沒寫數字，初值）。"""
    refund_permille: int = Field(ge=0, le=1000)
    """三選一都不拿時退還的比例（‰，捨去；#88 2b「任務幣退一半」）。"""
    text_max_chars: int = Field(ge=1, le=500)
    """願望文字最多幾個字（設計「一句話」；prompt 的玩家文字上限是 500）。"""
    max_keywords: int = Field(ge=1)
    """一次許願最多對到幾個關鍵字（07 7.6「1～2 個關鍵字」）。"""
    llm_cards: int = Field(ge=0, le=3)
    """一份三選一最多請 LLM 幾張（其餘組合器與技能池補滿；同機遇 6L-2b 的保守值）。"""


WALK_PATH_FORMAT_MAX: Final = 1000
"""``walk`` 請求格式的寬上限（6P-2：只防過大的請求）；一次最多幾格以規則
``field.walk_max_steps`` 為準，由 ``trpg.world.field`` 檢查。"""


class CalendarRules(ContentModel):
    """賽季日曆（Phase 5F-1）：每日刷新的時區與當地時刻（``docs/專案計畫.md`` 3.1：06:00
    Asia/Taipei）。遊戲日長度（30 分鐘）與天氣週期是使用者定的常數，不在這裡。"""

    utc_offset_minutes: int = Field(ge=-720, le=840)
    """當地時間和 UTC 的差（分鐘；台北 +480，沒有日光節約時間）。"""
    refresh_hour: int = Field(ge=0, le=23)
    """每日刷新的當地時刻（懸賞、今日目標、每天一次的判定）。"""


FALLBACK_CALENDAR: Final = CalendarRules(utc_offset_minutes=480, refresh_hour=6)
"""呼叫 :mod:`trpg.world.clock` 沒有給日曆時用的日曆（台北 6 點）：只有伺服器公告沒有內容庫的舊路徑
與測試會用到；有內容庫的地方一律走 :func:`trpg.world.calendar.calendar_of`（``world/rules.yaml`` 的
``calendar``）。HC-7 把原本 ``clock.py`` 的 ``UTC_OFFSET_SECONDS``、``REFRESH_HOUR`` 與
``calendar.py`` 的 ``NO_RULES_CALENDAR`` 兩份合成這一份，值和內容檔相同
（``tests/world/test_rule_defaults_hc7.py`` 對照）。"""


class DayPartHours(ContentModel):
    """``world/rules.yaml`` 的 ``day_parts``：早、午、晚、夜的起始鐘點（遊戲內時刻；HC-4d 從前端
    ``client/src/world/hud.ts`` 搬來，值照前端原本用的）。

    白天／夜晚照伺服器的 ``day_phase``（:func:`trpg.world.clock.day_phase`：遊戲日前半是白天），
    這張表只決定同一個時段裡的字：白天＝早（``noon`` 點前）、午；夜晚＝晚（``evening``～``night``
    點前）、夜。``morning``、``evening`` 要和世界時鐘的白天開始、夜晚開始一致
    （``tests/world/test_rule_defaults_hc4d.py`` 對照）。"""

    morning: int = Field(ge=0, le=23)
    """早的起始鐘點（＝遊戲日開頭、白天開始）。"""
    noon: int = Field(ge=0, le=23)
    """午的起始鐘點。"""
    evening: int = Field(ge=0, le=23)
    """晚的起始鐘點（＝夜晚開始）。"""
    night: int = Field(ge=0, le=23)
    """夜的起始鐘點（到隔天 ``morning`` 為止）。"""

    @model_validator(mode="after")
    def _ordered(self) -> DayPartHours:
        if not self.morning < self.noon < self.evening < self.night:
            raise ValueError("day_parts 的鐘點必須是 morning < noon < evening < night")
        return self


class FieldRules(ContentModel):
    """實地地圖的規則數值（Phase 6C-R2；原本是 ``trpg.world`` 的常數，值不變）。"""

    sight_range: int = Field(ge=0)
    """敵人的視野距離（前方扇形、曼哈頓距離；21.10 第 3、12 條）。"""
    sneak_sight_divisor: int = Field(ge=1)
    """潛行中敵人視野＝``sight_range // sneak_sight_divisor``（捨去小數；21.10 第 6 條）。"""
    perceive_range: int = Field(ge=0)
    """走到隱藏入口幾格內自動感知（曼哈頓距離；21.6、21.10 第 17 條）。"""
    cut_size: int = Field(ge=1)
    """就地開打的戰場邊長（21.4）。"""
    min_enemy_cells: int = Field(ge=1)
    min_ally_cells: int = Field(ge=1)
    """就地開打的起始區至少幾格（6C-3 驗收：敵方 4 格、我方 3 格）。"""
    gap_ally_first: int = Field(ge=1)
    gap_other: int = Field(ge=1)
    """就地開打的距離（#124，21.10 第 26 條）：雙方最近兩單位之間的空格數（曼哈頓距離＝格數＋1，
    不看高低差）；我方先手 ``gap_ally_first``，敵方先手或沒有先手 ``gap_other``。"""
    gap_fallback: int = Field(ge=1)
    """兩種距離都放不下時再試的距離；也放不下才退回模板。"""
    gap_third: int = Field(ge=1)
    """三方混戰的第三方離我方起始區每一格至少隔幾格（6E-3b，21.10 第 26 條細節）；6E-3c：永遠
    套用，雙方退到 ``gap_fallback`` 時也一樣。"""

    def gaps(self, ally_first: bool) -> tuple[int, ...]:
        """依序要試的距離（規定的 → 另一個 → ``gap_fallback``；重複的只試一次）。"""
        first, other = (
            (self.gap_ally_first, self.gap_other)
            if ally_first
            else (self.gap_other, self.gap_ally_first)
        )
        return tuple(dict.fromkeys((first, other, self.gap_fallback)))

    walk_max_steps: int = Field(ge=1, le=WALK_PATH_FORMAT_MAX)
    """一次 ``walk`` 最多幾格（6B-2 第 3.2 節；6P-2 起由這裡決定，世界畫面的
    ``FieldView.walk_max_steps`` 告訴前端分段送）；不得超過請求格式的寬上限
    :data:`WALK_PATH_FORMAT_MAX`。"""

    def sneak_sight(self) -> int:
        """潛行中敵人的視野距離。"""
        return self.sight_range // self.sneak_sight_divisor


class WorldRules(ContentModel):
    """``content/world/rules.yaml``。"""

    week_days: int = Field(ge=1)
    """一週幾天（以早上 6 點刷新的日子算；酒館傳聞、商店每週限量，5D-R1）。"""
    calendar: CalendarRules
    """每日刷新的時區與時刻（Phase 5F-1）。"""
    supplies: SupplyRules
    camp_cost: int = Field(ge=0)
    hasten: HastenRules
    encounter: EncounterRates
    perception: PerceptionRules
    default_weather: WeatherWeights = WeatherWeights(day={"clear": 1}, night={"night": 1})
    """沒有列在 ``weather`` 的區域用這組。"""
    weather: tuple[RegionWeather, ...] = ()
    battle: BattleRules
    enemy_growth: EnemyGrowthRules
    hero_growth: HeroGrowthRules
    xp: XpRules
    opportunity: OpportunityRules
    wish: WishRules
    """許願池（Phase WP-1）。"""
    field: FieldRules
    """實地地圖的規則數值（Phase 6C-R2）。"""
    field_maps: FieldMapRules
    day_parts: DayPartHours
    """早、午、晚、夜的起始鐘點（HC-4d；經 API 的 ``WorldClockView.day_parts`` 給前端）。"""
    """實地地圖的大小建議與每區傳送石數（HC-4d，原本是 ``trpg.content.fields`` 的常數）。"""

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
