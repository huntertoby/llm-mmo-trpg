"""賽季日程、今日目標、懸賞、世界事件（``content/world/season.yaml``，Phase 5F-1）。

``docs/phases/Phase5計畫.md`` 35.4。依據：09 9.7（14 天節奏、懸賞先搶先贏、世界事件每 3～4 天
1 個）、9.6.9 #99（今日目標 3 條、新手期偏教學）、9.6.10 #103（全服進度、門檻依前一天上線人數
調整）、18 18.7.4（雲嶺懸賞）、19 19.9（世界事件）。規則在 :mod:`trpg.world.season_board`；
這裡只有資料與檢查（守則 4）。

跨檔案檢查（地點、遭遇表的陣容、詞綴、天氣、區域）在 :func:`season_problems`，由內容庫呼叫。
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.world_encounters import MAX_GROUP_SIZE, EncounterTable, FixedElite
from trpg.content.world_enemies import EnemyCatalog
from trpg.content.world_map import LocationMapDef
from trpg.content.world_quests import QuestKind

__all__ = [
    "SEASON_FILE",
    "BountyDef",
    "DailyGoalDef",
    "DailyGoalRules",
    "GoalKind",
    "GoalSpec",
    "LevelBonusEffect",
    "Milestone",
    "SchedulePhase",
    "SeasonContent",
    "WorldEventDef",
    "WorldEventEffect",
    "season_problems",
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
]
"""目標種類（今日目標與世界事件共用；由一步的世界事件判定）。"""

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
    quest_kind: QuestKind | None = None
    quest: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _filters(self) -> GoalSpec:
        battle = bool(self.region or self.weather or self.elite or self.location_kinds)
        quest = self.quest_kind is not None or self.quest is not None
        if battle and self.kind != "battle_won":
            raise ValueError(f"{self.kind} 不能寫區域、天氣、精英、地點種類的篩選")
        if quest and self.kind != "quest_step":
            raise ValueError(f"{self.kind} 不能寫任務的篩選")
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
    """一張懸賞（18.7.4）：貼出期間在 ``location`` 遇敵就是這個陣容（``group``＋精英 ``elite`` 排
    最前），先打贏的人拿走當天的懸賞。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    level: int = Field(ge=1)
    """18.7.4 的等級（顯示用；敵人等級照地點）。"""
    group: str = Field(pattern=ID_PATTERN)
    elite: FixedElite
    coins: int = Field(default=0, ge=0)
    from_day: int = Field(default=1, ge=1)
    """賽季第幾天起每天貼出。"""


class LevelBonusEffect(ContentModel):
    region: str = Field(pattern=ID_PATTERN)
    amount: int = Field(ge=1)


class WorldEventEffect(ContentModel):
    """世界事件成功或失敗寫回世界的效果：世界旗標、區域建議等級加成（9.6.7 #15）。"""

    flags: tuple[str, ...] = ()
    level_bonus: tuple[LevelBonusEffect, ...] = ()

    @model_validator(mode="after")
    def _ids(self) -> WorldEventEffect:
        bad = [f for f in self.flags if re.match(ID_PATTERN, f) is None]
        if bad:
            raise ValueError(f"世界旗標 ID 格式錯誤 {', '.join(bad)}")
        return self


class WorldEventDef(ContentModel):
    """一個世界事件（#103、19.9）：全服共用一條進度；門檻＝``goal.count`` × max(前一天上線人數, 1)
    ÷ ``base_players``（最少 1，Q14）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    text_zh: str = ""
    days: DayRange
    goal: GoalSpec
    base_players: int = Field(default=8, ge=1)
    on_success: WorldEventEffect = WorldEventEffect()
    on_failure: WorldEventEffect = WorldEventEffect()

    @model_validator(mode="after")
    def _days(self) -> WorldEventDef:
        _check_range(self.days, f"世界事件 {self.id}")
        return self

    def target_for(self, players: int | None) -> int:
        """前一天上線 ``players`` 人時的門檻；``None``＝沒有前一天的資料（用原門檻，
        代決 5F1-4）。"""
        if players is None:
            return self.goal.count
        return max(1, self.goal.count * max(players, 1) // self.base_players)


class SeasonContent(ContentModel):
    """``content/world/season.yaml``。"""

    days: int = Field(ge=1)
    schedule: tuple[SchedulePhase, ...] = ()
    milestones: tuple[Milestone, ...] = ()
    daily_goals: DailyGoalRules | None = None
    bounties: tuple[BountyDef, ...] = ()
    world_events: tuple[WorldEventDef, ...] = ()

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
        if late:
            raise ValueError(f"超過賽季天數 {self.days}：{', '.join(late)}")
        return self

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
) -> list[str]:
    problems: list[str] = []
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


def season_problems(
    season: SeasonContent,
    *,
    world_maps: Mapping[str, LocationMapDef],
    encounters: Mapping[str, EncounterTable],
    catalog: EnemyCatalog,
    weather_ids: Collection[str],
    region_ids: Collection[str],
    location_kinds: Collection[str],
) -> list[str]:
    """跨檔案檢查（繁體中文、排序；空＝通過）。``region_ids`` 是區域表的區域（世界事件的建議等級
    加成可以指向還沒有地點圖的區域，例如灰燼荒原）。"""
    problems: list[str] = []
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
        )
        for effect in (event.on_success, event.on_failure):
            problems += [
                f"{where}：建議等級加成的區域 {b.region} 不在區域表"
                for b in effect.level_bonus
                if b.region not in region_ids
            ]
    return sorted(problems)
