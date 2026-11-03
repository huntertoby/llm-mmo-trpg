"""賽季日程、今日目標、懸賞、世界事件（``content/world/season.yaml``，Phase 5F-1）。

``docs/phases/Phase5計畫.md`` 35.4。依據：09 9.7（14 天節奏、懸賞先搶先贏、世界事件每 3～4 天
1 個）、9.6.9 #99（今日目標 3 條、新手期偏教學）、9.6.10 #103（全服進度、門檻依前一天上線人數
調整）、18 18.7.4（雲嶺懸賞）、19 19.9（世界事件）。規則在 :mod:`trpg.world.season_board`；
這裡只有資料與檢查（守則 4）。

跨檔案檢查（地點、遭遇表的陣容、詞綴、天氣、區域）在 :func:`season_problems`，由內容庫呼叫。
"""

from __future__ import annotations

import re
import string
from collections.abc import Collection, Mapping
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.maps import MapDef
from trpg.content.schemas import ContentModel
from trpg.content.world_encounters import MAX_GROUP_SIZE, EncounterTable, FixedElite
from trpg.content.world_enemies import EnemyCatalog
from trpg.content.world_map import LocationMapDef
from trpg.content.world_quests import QuestKind

__all__ = [
    "SEASON_FILE",
    "BossScore",
    "BossUnlock",
    "BountyDef",
    "ChronicleFact",
    "ChronicleTemplates",
    "DailyGoalDef",
    "DailyGoalRules",
    "GoalKind",
    "GoalSpec",
    "LeagueRules",
    "LevelBonusEffect",
    "Milestone",
    "SchedulePhase",
    "SealKeyRules",
    "SealKeySource",
    "SeasonBossDef",
    "SeasonContent",
    "ShopPriceEffect",
    "WorldEventDef",
    "WorldEventEffect",
    "season_problems",
    "shop_price_problems",
]

SEASON_FILE: Final = "world/season.yaml"

type GoalKind = Literal[
    "battle_won",
    "quest_step",
    "location_revealed",
    "situation_success",
    "talked",
    "camped",
    "bounty_claimed",
    "seal_key",
]
"""目標種類（今日目標與世界事件共用；由一步的世界事件判定）。``seal_key``（Phase 5F-3）是全服累積的
封印鑰匙：世界事件開始時進度帶入目前的全服鑰匙數，之後每把 +1。"""

type DayRange = tuple[int, int]


def _check_range(days: DayRange, where: str) -> None:
    first, last = days
    if first < 1 or last < first:
        raise ValueError(f"{where}：天數 {list(days)} 必須 1 起且結束不早於開始")


class GoalSpec(ContentModel):
    """一個目標：種類、次數與篩選。篩選只有對應種類能寫（``battle_won``：區域、天氣、精英、地點
    種類；``quest_step``：任務種類、任務 ID）。"""

    kind: GoalKind
    count: int = Field(ge=1)
    region: str | None = Field(default=None, pattern=ID_PATTERN)
    weather: tuple[str, ...] = ()
    """天氣 ID（任一符合即算；空＝不限）。"""
    elite: bool = False
    """只算陣容有精英的戰鬥。"""
    location_kinds: tuple[str, ...] = ()
    """地點種類（任一符合即算；空＝不限）。"""
    locations: tuple[str, ...] = ()
    """地點 ID（任一符合即算；空＝不限；Phase 5F-5a，19.9 #2「守住 3 個村落」）。
    要同時寫 ``region``。"""
    quest_kind: QuestKind | None = None
    quest: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _filters(self) -> GoalSpec:
        battle = bool(
            self.region or self.weather or self.elite or self.location_kinds or self.locations
        )
        quest = self.quest_kind is not None or self.quest is not None
        if battle and self.kind != "battle_won":
            raise ValueError(f"{self.kind} 不能寫區域、天氣、精英、地點種類的篩選")
        if quest and self.kind != "quest_step":
            raise ValueError(f"{self.kind} 不能寫任務的篩選")
        if self.locations and self.region is None:
            raise ValueError("寫了 locations 就要寫 region（地點 ID 屬於哪一區）")
        return self


class SchedulePhase(ContentModel):
    """9.7 的一段節奏（顯示用）。"""

    id: str = Field(pattern=ID_PATTERN)
    days: DayRange
    name_zh: str = Field(min_length=1)
    text_zh: str = ""

    @model_validator(mode="after")
    def _days(self) -> SchedulePhase:
        _check_range(self.days, f"日程 {self.id}")
        return self


class Milestone(ContentModel):
    """賽季的時間點（顯示用；規則在各段）。"""

    id: str = Field(pattern=ID_PATTERN)
    day: int = Field(ge=1)
    name_zh: str = Field(min_length=1)


class DailyGoalDef(ContentModel):
    id: str = Field(pattern=ID_PATTERN)
    text_zh: str = Field(min_length=1)
    goal: GoalSpec


class DailyGoalRules(ContentModel):
    """今日目標（#99）：每天 ``count`` 條、每條完成給 ``coins`` 任務幣；第 1～``newbie_days`` 天用
    固定的 ``newbie``，之後每天從 ``goals`` 確定性抽。"""

    count: int = Field(default=3, ge=1)
    coins: int = Field(default=1, ge=0)
    newbie_days: int = Field(default=2, ge=0)
    newbie: tuple[str, ...] = ()
    goals: tuple[DailyGoalDef, ...] = ()

    @model_validator(mode="after")
    def _goals(self) -> DailyGoalRules:
        ids = [g.id for g in self.goals]
        if len(set(ids)) != len(ids):
            raise ValueError("daily_goals.goals 的 ID 重複")
        if len(self.goals) < self.count:
            raise ValueError(f"daily_goals.goals 至少要 {self.count} 條")
        if self.newbie_days > 0:
            if len(self.newbie) != self.count or len(set(self.newbie)) != self.count:
                raise ValueError(f"daily_goals.newbie 必須是 {self.count} 條不重複的目標")
            unknown = [g for g in self.newbie if g not in ids]
            if unknown:
                raise ValueError(f"daily_goals.newbie 用了未知的目標 {', '.join(unknown)}")
        return self

    def goal_by_id(self) -> dict[str, DailyGoalDef]:
        return {g.id: g for g in self.goals}


class BountyDef(ContentModel):
    """一張懸賞（18.7.4）：貼出期間每個角色每天在 ``location`` 的第一場遭遇是這個陣容（``group``＋
    精英 ``elite`` 排最前；5F-1b），先打贏的人拿走當天的懸賞（大獎），其他人打倒拿小獎（9.6.3）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    level: int = Field(ge=1)
    """18.7.4 的等級（顯示用；敵人等級照地點）。"""
    group: str = Field(pattern=ID_PATTERN)
    elite: FixedElite
    coins: int = Field(default=0, ge=0)
    """大獎：當天第一個打倒的人拿的任務幣（另補經驗到懸賞份數）。"""
    consolation_coins: int = Field(default=0, ge=0)
    """小獎：已被別人搶下後打倒的任務幣（9.6.3「其他人拿小獎」；5F-1b）。"""
    from_day: int = Field(default=1, ge=1)
    """賽季第幾天起每天貼出。"""


class LevelBonusEffect(ContentModel):
    region: str = Field(pattern=ID_PATTERN)
    amount: int = Field(ge=1)


class ShopPriceEffect(ContentModel):
    """商店價格加成（Phase 5F-5b；19.9 #2 失敗「餘燼集商店價格 +20% 到季末」）：``shop`` 的買價
    加 ``permille``‰（整數千分比；200＝+20%），到季末重置才清掉。"""

    shop: str = Field(pattern=ID_PATTERN)
    permille: int = Field(ge=1, le=10_000)
    reason_zh: str = ""
    """商店畫面寫的加價原因（Phase 5F-5c，例「熔岩潰堤失守」；畫面顯示「原因：買價 +20%」）。
    空字串＝用世界事件的名字。"""


class WorldEventEffect(ContentModel):
    """世界事件成功或失敗寫回世界的效果：世界旗標、區域建議等級加成（9.6.7 #15）、全服封印鑰匙
    （Phase 5F-3；19.9 #2「封印鑰匙 +5」）、商店價格加成（Phase 5F-5b）。"""

    flags: tuple[str, ...] = ()
    level_bonus: tuple[LevelBonusEffect, ...] = ()
    seal_keys: int = Field(default=0, ge=0)
    shop_price: tuple[ShopPriceEffect, ...] = ()

    @model_validator(mode="after")
    def _ids(self) -> WorldEventEffect:
        bad = [f for f in self.flags if re.match(ID_PATTERN, f) is None]
        if bad:
            raise ValueError(f"世界旗標 ID 格式錯誤 {', '.join(bad)}")
        return self


class WorldEventDef(ContentModel):
    """一個世界事件（#103、19.9）：全服共用一條進度；門檻＝``goal.count`` × 前一天上線人數
    ÷ ``base_players``（Q14），最少保留原門檻的 ``min_target_permille``（無條件進位）；前一天沒有
    上線紀錄時用原門檻（5F-1b，玩法 PM 2026-11-03 代決）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    text_zh: str = ""
    days: DayRange
    goal: GoalSpec
    base_players: int = Field(default=8, ge=1)
    min_target_permille: int = Field(default=250, ge=1, le=1000)
    """門檻下限：原門檻的千分比（250＝1/4，30 → 最少 8；無條件進位）。"""
    on_success: WorldEventEffect = WorldEventEffect()
    on_failure: WorldEventEffect = WorldEventEffect()

    @model_validator(mode="after")
    def _days(self) -> WorldEventDef:
        _check_range(self.days, f"世界事件 {self.id}")
        return self

    def min_target(self) -> int:
        """門檻下限（原門檻 × ``min_target_permille`` ‰，無條件進位、最少 1）。"""
        return max(1, -(-self.goal.count * self.min_target_permille // 1000))

    def target_for(self, players: int | None) -> int:
        """前一天上線 ``players`` 人時的門檻；``None`` 或 0＝沒有前一天的上線紀錄（用原門檻，
        代決 5F1-4、5F-1b）。"""
        if not players:
            return self.goal.count
        return max(self.min_target(), self.goal.count * players // self.base_players)


LEAGUE_EXCLUDED_ARCHETYPES: Final = frozenset({"boss", "training", "test"})
"""循環賽不能用的地圖類型（Boss 專屬、靶場、測試圖；Phase 5F-4）。"""


class LeagueRules(ContentModel):
    """影子循環賽（Phase 5F-4；09 9.7「季末保底」、#101）。規則在 :mod:`trpg.world.league`。"""

    signup_close_day: int = Field(default=13, ge=1)
    """最後可以報名的賽季日（含；#101 第 13 天截止）。"""
    maps: tuple[str, ...] = Field(min_length=1, max_length=8)
    """事先公布的地圖（9.7：3 張）。"""
    seeds: int = Field(default=2, ge=1, le=8)
    """每對組合 × 每張地圖的種子數；每個種子交換先後手各打 1 場。"""
    max_rounds: int = Field(default=30, ge=1)
    """到輪數上限＝和局。"""
    batch_size: int = Field(default=10, ge=1)
    """背景每批幾場（批與批之間讓出執行緒）。"""
    hp_permille: int = Field(default=1000, ge=1000, le=5000)
    """（5F-4b）開場最大 HP 倍率（‰；2000＝×2）：只套在循環賽，HP 每場滿。"""
    opening_statuses: tuple[str, ...] = ()
    """（5F-4b）雙方開場就掛上的狀態（``statuses.yaml``；例：``league_truce``＝第 1 輪不能造成
    傷害）。"""
    first_opening_statuses: tuple[str, ...] = ()
    """（5F-4b）只有先手那位開場掛上的狀態（例：先手少 1 AP）。"""

    @model_validator(mode="after")
    def _maps(self) -> LeagueRules:
        if len(set(self.maps)) != len(self.maps):
            raise ValueError("循環賽的地圖重複")
        return self


class SealKeySource(ContentModel):
    """封印鑰匙的一個來源（Phase 5F-3；19.6.2）：個人每個來源第一次達成給 1 把。

    - ``elite_first_kill``：第一次打倒精英 ``unit``（例：雲頂觀的霧鎖真人）；來源 ID＝``id``。
    - ``bounty_claimed``：每張懸賞第一次搶下（來源 ID＝``bounty:<懸賞 ID>``）。"""

    id: str = Field(pattern=ID_PATTERN)
    kind: Literal["elite_first_kill", "bounty_claimed"]
    unit: str | None = Field(default=None, pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)

    @model_validator(mode="after")
    def _unit(self) -> SealKeySource:
        if (self.kind == "elite_first_kill") != (self.unit is not None):
            raise ValueError(f"鑰匙來源 {self.id}：只有 elite_first_kill 要寫 unit")
        return self


class SealKeyRules(ContentModel):
    """封印鑰匙（19.6.2）：個人至少 ``required`` 把才能挑戰賽季 Boss。"""

    required: int = Field(default=1, ge=0)
    sources: tuple[SealKeySource, ...] = ()


class BossUnlock(ContentModel):
    """賽季 Boss 的解鎖（09 9.7）：``flag``（封印鑰匙集滿的世界旗標）出現後最早第 ``earliest_day``
    天、且至少 ``announce_hours`` 小時後解鎖；沒有集滿時第 ``forced_day`` 天強制；解鎖前
    ``announce_hours`` 小時公告；開放到第 ``close_day`` 天結束。"""

    earliest_day: int = Field(ge=1)
    forced_day: int = Field(ge=1)
    close_day: int = Field(ge=1)
    announce_hours: int = Field(default=24, ge=0, le=72)
    flag: str = Field(pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _order(self) -> BossUnlock:
        if not self.earliest_day <= self.forced_day <= self.close_day:
            raise ValueError("season_boss.unlock：要 earliest_day ≤ forced_day ≤ close_day")
        return self


class BossScore(ContentModel):
    """通關評分（#87：輪數、全隊存活、有沒有人倒下）：
    ``max(0, base − per_round × 輪數) + per_survivor × 存活人數 + no_down（沒人倒下）``。"""

    base: int = Field(default=1000, ge=0)
    per_round: int = Field(default=20, ge=0)
    per_survivor: int = Field(default=100, ge=0)
    no_down: int = Field(default=200, ge=0)

    def score(self, *, rounds: int, survivors: int, no_down: bool) -> int:
        kept = max(0, self.base - self.per_round * rounds)
        return kept + self.per_survivor * survivors + (self.no_down if no_down else 0)


class SeasonBossDef(ContentModel):
    """賽季 Boss（Phase 5F-3；19.7、09 9.7、#87、#100、#101）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    battle_map: str = Field(pattern=ID_PATTERN)
    units: tuple[str, ...] = Field(min_length=1, max_length=MAX_GROUP_SIZE)
    """敵方陣容（第一個是本體；站位照地圖 ``start_zones.enemy`` 的順序）。"""
    level: int = Field(ge=1, le=99)
    unlock: BossUnlock
    daily_attempts: int = Field(default=3, ge=1)
    """每帳號每天的挑戰次數（#100）。"""
    entry_kinds: tuple[str, ...] = ("town",)
    """能出發挑戰的地點種類。"""
    title_zh: str = Field(min_length=1)
    score: BossScore = BossScore()


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


class ChronicleFact(ContentModel):
    """編年史一種事實的寫法（Phase 5F-5c）：``text`` 裡的 ``{items}`` 換成各項（每項用 ``item``
    排版、:attr:`ChronicleTemplates.joiner` 串起來）。"""

    text: str = Field(min_length=1)
    item: str = "{name}"

    @model_validator(mode="after")
    def _check(self) -> ChronicleFact:
        if _placeholders(self.text) != {"items"}:
            raise ValueError(f"編年史模板 {self.text!r} 只能用 {{items}}")
        if _placeholders(self.item) != {"name"}:
            raise ValueError(f"編年史模板 {self.item!r} 只能用 {{name}}")
        return self


class ChronicleTemplates(ContentModel):
    """季末編年史的固定模板（Phase 5F-5c，玩法 PM 2026-11-03 代決：第一季用固定模板、列事實細節；
    LLM 傳記 07 7.11 是後期）。每個角色一行：``line`` 的 ``{season}``＝季名、``{facts}``＝依序
    （等級、精英、Boss、首殺、主線章節、事件、配方、循環賽）有內容的事實用 ``separator`` 串起來；
    都沒有＝``empty``。只寫狀態與日誌裡確實發生過的事。"""

    line: str = Field(min_length=1)
    separator: str = Field(min_length=1)
    joiner: str = Field(min_length=1)
    empty: str = Field(min_length=1)
    level: str = Field(min_length=1)
    """``{level}``＝季末的等級。"""
    elites: ChronicleFact
    bosses: ChronicleFact
    """區域 Boss（``world/loot.yaml`` 的 ``bosses``）與賽季 Boss。"""
    first_kills: ChronicleFact
    chapters: ChronicleFact
    events: ChronicleFact
    recipes: ChronicleFact
    league: str = Field(min_length=1)
    """``{rank}``＝循環賽最終名次。"""

    @model_validator(mode="after")
    def _check(self) -> ChronicleTemplates:
        for text, names in (
            (self.line, {"season", "facts"}),
            (self.level, {"level"}),
            (self.league, {"rank"}),
        ):
            if _placeholders(text) != names:
                raise ValueError(f"編年史模板 {text!r} 要用而且只能用 {sorted(names)}")
        return self


class SeasonContent(ContentModel):
    """``content/world/season.yaml``。"""

    days: int = Field(ge=1)
    schedule: tuple[SchedulePhase, ...] = ()
    milestones: tuple[Milestone, ...] = ()
    daily_goals: DailyGoalRules | None = None
    bounties: tuple[BountyDef, ...] = ()
    world_events: tuple[WorldEventDef, ...] = ()
    seal_keys: SealKeyRules = SealKeyRules()
    season_boss: SeasonBossDef | None = None
    league: LeagueRules | None = None
    """影子循環賽（Phase 5F-4）；``None``＝這一季沒有循環賽。"""
    chronicle: ChronicleTemplates | None = None
    """季末編年史的模板（Phase 5F-5c）；``None``＝編年史只寫季名。"""

    @model_validator(mode="after")
    def _season(self) -> SeasonContent:
        expected = 1
        for phase in self.schedule:
            if phase.days[0] != expected:
                raise ValueError(f"日程 {phase.id} 應從第 {expected} 天開始（依序、不重疊）")
            expected = phase.days[1] + 1
        if self.schedule and expected != self.days + 1:
            raise ValueError(f"日程要涵蓋第 1～{self.days} 天")
        for label, ids in (
            ("日程", [p.id for p in self.schedule]),
            ("時間點", [m.id for m in self.milestones]),
            ("懸賞", [b.id for b in self.bounties]),
            ("世界事件", [e.id for e in self.world_events]),
        ):
            if len(set(ids)) != len(ids):
                raise ValueError(f"{label}的 ID 重複")
        late = [m.id for m in self.milestones if m.day > self.days]
        late += [b.id for b in self.bounties if b.from_day > self.days]
        late += [e.id for e in self.world_events if e.days[1] > self.days]
        boss = self.season_boss
        if boss is not None and boss.unlock.close_day > self.days:
            late.append(f"{boss.id}（close_day）")
        if self.league is not None and self.league.signup_close_day > self.days:
            late.append("league.signup_close_day")
        if late:
            raise ValueError(f"超過賽季天數 {self.days}：{', '.join(late)}")
        if boss is not None:
            self._check_boss(boss)
        return self

    def _check_boss(self, boss: SeasonBossDef) -> None:
        """時間點 ``boss_earliest``／``boss_forced`` 有寫時要和解鎖規則一致；解鎖旗標要是某個世界
        事件成功時給的；鑰匙來源 ID 不重複。"""
        days = {m.id: m.day for m in self.milestones}
        for milestone, day in (
            ("boss_earliest", boss.unlock.earliest_day),
            ("boss_forced", boss.unlock.forced_day),
        ):
            if milestone in days and days[milestone] != day:
                raise ValueError(
                    f"時間點 {milestone} 是第 {days[milestone]} 天，解鎖規則是第 {day} 天"
                )
        flags = {f for e in self.world_events for f in e.on_success.flags}
        if boss.unlock.flag not in flags:
            raise ValueError(
                f"season_boss.unlock.flag {boss.unlock.flag} 不是任何世界事件成功的旗標"
            )
        ids = [s.id for s in self.seal_keys.sources]
        if len(set(ids)) != len(ids):
            raise ValueError("seal_keys.sources 的 ID 重複")

    def phase_on(self, day: int) -> SchedulePhase | None:
        return next((p for p in self.schedule if p.days[0] <= day <= p.days[1]), None)

    def bounty_by_id(self) -> dict[str, BountyDef]:
        return {b.id: b for b in self.bounties}

    def event_by_id(self) -> dict[str, WorldEventDef]:
        return {e.id: e for e in self.world_events}


def _goal_problems(
    where: str,
    goal: GoalSpec,
    *,
    regions: Collection[str],
    weather_ids: Collection[str],
    location_kinds: Collection[str],
    world_maps: Mapping[str, LocationMapDef] | None = None,
) -> list[str]:
    problems: list[str] = []
    if goal.locations and world_maps is not None and goal.region is not None:
        world_map = world_maps.get(goal.region)
        known = set() if world_map is None else set(world_map.location_by_id())
        problems += [
            f"{where}：區域 {goal.region} 沒有地點 {loc}"
            for loc in goal.locations
            if loc not in known
        ]
    if goal.region is not None and goal.region not in regions:
        problems.append(f"{where}：未知的區域 {goal.region}")
    problems += [f"{where}：未知的天氣 {w}" for w in goal.weather if w not in weather_ids]
    problems += [
        f"{where}：未知的地點種類 {k}" for k in goal.location_kinds if k not in location_kinds
    ]
    return problems


def _bounty_problems(
    bounty: BountyDef,
    *,
    world_maps: Mapping[str, LocationMapDef],
    encounters: Mapping[str, EncounterTable],
    catalog: EnemyCatalog,
) -> list[str]:
    where = f"懸賞 {bounty.id}"
    world_map = world_maps.get(bounty.region)
    table = encounters.get(bounty.region)
    if world_map is None or bounty.location not in world_map.location_by_id():
        return [f"{where}：區域 {bounty.region} 沒有地點圖或未知的地點 {bounty.location}"]
    if table is None:
        return []  # 沒有遭遇表（精簡的內容資料夾）：不會遇敵，懸賞陣容用不到
    if bounty.location not in table.location_by_id():
        return [f"{where}：地點 {bounty.location} 沒有遭遇表"]
    group = table.group_by_id().get(bounty.group)
    if group is None:
        return [f"{where}：未知的陣容 {bounty.group}"]
    if group.third or len(group.units) + 1 > MAX_GROUP_SIZE:
        return [f"{where}：懸賞陣容不能有第三方，加精英也不能超過 {MAX_GROUP_SIZE} 名"]
    return _bounty_elite_problems(where, bounty, catalog)


def _bounty_elite_problems(where: str, bounty: BountyDef, catalog: EnemyCatalog) -> list[str]:
    if not catalog.has(bounty.elite.unit):
        return [f"{where}：未知的精英 {bounty.elite.unit}"]
    try:
        reason = catalog.affix_problem(
            catalog.template(bounty.elite.unit), bounty.elite.affix, allow_elite=True
        )
    except KeyError:
        return [f"{where}：未知的詞綴 {bounty.elite.affix}"]
    if reason is not None:
        return [f"{where}：精英不能套用詞綴（{reason}）"]
    return []


def _boss_problems(
    season: SeasonContent,
    *,
    units: Collection[str],
    maps: Mapping[str, MapDef] | None,
    catalog: EnemyCatalog,
) -> list[str]:
    problems = [
        f"封印鑰匙來源 {s.id}：未知的單位 {s.unit}"
        for s in season.seal_keys.sources
        if s.unit is not None and units and s.unit not in units
    ]
    boss = season.season_boss
    if boss is None or maps is None:
        return problems
    where = f"賽季 Boss {boss.id}"
    problems += [f"{where}：未知的單位 {u}" for u in boss.units if not catalog.has(u)]
    map_def = maps.get(boss.battle_map)
    if map_def is None:
        problems.append(f"{where}：未知的地圖 {boss.battle_map}")
    elif map_def.archetype != "boss":
        problems.append(f"{where}：地圖 {boss.battle_map} 不是 Boss 地圖（archetype: boss）")
    return problems


def season_problems(
    season: SeasonContent,
    *,
    world_maps: Mapping[str, LocationMapDef],
    encounters: Mapping[str, EncounterTable],
    catalog: EnemyCatalog,
    weather_ids: Collection[str],
    region_ids: Collection[str],
    location_kinds: Collection[str],
    battle_maps: Mapping[str, str] | None = None,
    units: Collection[str] = (),
    maps: Mapping[str, MapDef] | None = None,
    status_ids: Collection[str] | None = None,
) -> list[str]:
    """跨檔案檢查（繁體中文、排序；空＝通過）。``region_ids`` 是區域表的區域（世界事件的建議等級
    加成可以指向還沒有地點圖的區域，例如灰燼荒原）。``battle_maps`` 是戰鬥地圖 ID → 地圖類型
    （循環賽的地圖檢查，5F-4；``None``＝不檢查）。``units``／``maps``（Phase 5F-3）：賽季 Boss 的
    陣容與 Boss 地圖、封印鑰匙來源的單位。``status_ids`` 是狀態 ID（循環賽的開場狀態，5F-4b；
    ``None``＝不檢查）。"""
    problems: list[str] = _boss_problems(season, units=units, maps=maps, catalog=catalog)
    if season.league is not None and battle_maps is not None:
        problems += _league_problems(season.league, battle_maps)
    if season.league is not None and status_ids is not None:
        problems += [
            f"循環賽的開場狀態 {s} 不在 statuses.yaml"
            for s in (*season.league.opening_statuses, *season.league.first_opening_statuses)
            if s not in status_ids
        ]
    rules = season.daily_goals
    for goal_def in () if rules is None else rules.goals:
        problems += _goal_problems(
            f"今日目標 {goal_def.id}",
            goal_def.goal,
            regions=region_ids,
            weather_ids=weather_ids,
            location_kinds=location_kinds,
        )
    for bounty in season.bounties:
        problems += _bounty_problems(
            bounty, world_maps=world_maps, encounters=encounters, catalog=catalog
        )
    for event in season.world_events:
        where = f"世界事件 {event.id}"
        problems += _goal_problems(
            where,
            event.goal,
            regions=region_ids,
            weather_ids=weather_ids,
            location_kinds=location_kinds,
            world_maps=world_maps,
        )
        for effect in (event.on_success, event.on_failure):
            problems += [
                f"{where}：建議等級加成的區域 {b.region} 不在區域表"
                for b in effect.level_bonus
                if b.region not in region_ids
            ]
    return sorted(problems)


def shop_price_problems(season: SeasonContent, shop_ids: Collection[str]) -> list[str]:
    """世界事件的商店價格加成指到的商店都要存在（Phase 5F-5b；商店在 ``world/shops/``，經濟比賽季
    晚載入，所以另外檢查）。"""
    return sorted(
        f"世界事件 {event.id}：價格加成的商店 {row.shop} 不存在"
        for event in season.world_events
        for effect in (event.on_success, event.on_failure)
        for row in effect.shop_price
        if row.shop not in shop_ids
    )


def _league_problems(league: LeagueRules, battle_maps: Mapping[str, str]) -> list[str]:
    problems: list[str] = []
    for map_id in league.maps:
        archetype = battle_maps.get(map_id)
        if archetype is None:
            problems.append(f"循環賽的地圖 {map_id} 不存在")
        elif archetype in LEAGUE_EXCLUDED_ARCHETYPES:
            problems.append(f"循環賽的地圖 {map_id} 是 {archetype} 類地圖，不能用")
    return problems
