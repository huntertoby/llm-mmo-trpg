"""大世界的狀態：世界快照（``trpg-world/1``）與角色（``trpg-char/1``）（Phase 5A-2）。

``docs/phases/Phase5計畫.md`` 2.4、2.5、6.4。所有集合型欄位都以排序後的 tuple 存放（守則 2），
同樣的動作序列一定得到逐字相同的 JSON。角色欄位盡量和 :class:`trpg.roguelite.state.RunState`
同名同型別（2.2；``hero``、``origin``、``level``、``xp``、``hp``、``mana``、``stamina``）。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.shared.rng import MASK64
from trpg.world.clock import DayPhase

__all__ = [
    "CHAR_FORMAT",
    "WORLD_FORMAT",
    "CharacterState",
    "ClearedLocation",
    "EncounterResult",
    "EventTrigger",
    "LocationRef",
    "NextBattleMod",
    "PerceptionMark",
    "ThreadState",
    "WorldState",
]

WORLD_FORMAT: Final = "trpg-world/1"
CHAR_FORMAT: Final = "trpg-char/1"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocationRef(_Model):
    """某區的某個地點。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)

    def key(self) -> tuple[str, str]:
        return (self.region, self.location)


class ClearedLocation(_Model):
    """所有人看到「已清空」的地點（09 9.6.7 #15）；``respawn_at``（UTC 秒）起敵人重生。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    respawn_at: int = Field(ge=0)


class PerceptionMark(_Model):
    """角色最後一次對某個隱藏地點做感知判定的日子（``refresh_day``；#112 每天 1 次）。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    day: int = Field(ge=0)


class EncounterResult(_Model):
    """遇敵的結果（只是資料，不開戰；開戰在 5A-4，敵人陣容在 5A-3）。"""

    region: str
    location: str
    """遇敵的地點（移動的目的地）。"""
    level: int = Field(ge=1)
    """該地點的建議等級（``level_max``）。"""
    battle_map: str | None
    """從目的地 ``battle_maps`` 抽的地圖；目的地沒有戰鬥地圖時為 ``None``
    （5A-4 從區域地圖池挑）。"""
    battle_seed: int = Field(ge=0, le=0xFFFFFFFF)
    weather: str
    day_phase: DayPhase
    at: int = Field(ge=0)
    """遇敵的時間（UTC 秒）。"""
    from_location: str | None = None
    """出發地點（撤退回這裡，5A-4）；5A-4 以前的資料沒有，撤退時回本區小鎮。"""


class EventTrigger(_Model):
    """觸發的事件（Phase 5B-1；只是「哪個骨架」的資料，解法與結果在 5B-2～5B-4）。

    ``skeleton`` 是引擎挑的預設骨架；``candidates`` 是當下所有合格的骨架（依 ID 排序），說書人
    （5B-3）只能從這裡換，不能自己多生事件（09 9.6.7 #6）。
    """

    region: str
    location: str
    skeleton: str
    candidates: tuple[str, ...]
    follows_thread: str | None = None
    """被接上的有效線頭（骨架的 ``follows`` 命中時）。"""
    weather: str
    day_phase: DayPhase
    at: int = Field(ge=0)

    @field_validator("candidates")
    @classmethod
    def _candidates_sorted(cls, candidates: tuple[str, ...]) -> tuple[str, ...]:
        if list(candidates) != sorted(set(candidates)):
            raise ValueError("candidates 必須排序且不重複")
        return candidates


class NextBattleMod(_Model):
    """下一場戰鬥帶的修正（Phase 5B-2：情境判定的短期 buff、debuff、敵人增援；09 9.6.4）。

    只記錄；之後的戰鬥接線開戰時套用並清掉。``source`` 是產生它的情境模板。
    """

    kind: Literal["buff", "debuff", "reinforce"]
    status: str | None = None
    """buff／debuff 的狀態（``statuses.yaml``）；增援為 ``None``。"""
    source: str = Field(pattern=ID_PATTERN)


class ThreadState(_Model):
    """一條進行中的線頭（09 9.6.7 #6；``expires_at``（UTC 秒）起到期）。"""

    thread: str = Field(pattern=ID_PATTERN)
    """線頭 ID（事件骨架 ``threads`` 裡的 ``id``）。"""
    skeleton: str = Field(pattern=ID_PATTERN)
    """留下這條線頭的事件骨架。"""
    region: str = Field(pattern=ID_PATTERN)
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)

    def key(self) -> tuple[int, str]:
        return (self.created_at, self.thread)


def _check_threads(threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
    keys = [t.key() for t in threads]
    ids = [t.thread for t in threads]
    if keys != sorted(keys) or len(set(ids)) != len(ids):
        raise ValueError("threads 必須依建立時間、ID 排序且同一線頭不重複")
    return threads


class WorldState(_Model):
    """共享的世界快照（``trpg-world/1``）。世界的變化由世界動作日誌重播得到，快照只是快取。"""

    format: Literal["trpg-world/1"] = WORLD_FORMAT
    season_id: str = Field(pattern=ID_PATTERN)
    season_seed: int = Field(ge=0, le=MASK64)
    season_start: int = Field(ge=0)
    """賽季開始的 UTC 秒數（5F-1 的日程用；本段只存）。"""
    flags: tuple[str, ...] = ()
    """世界旗標（排序、不重複）；地點的 ``unlock_flag`` 成立與否看這裡。"""
    cleared: tuple[ClearedLocation, ...] = ()
    """已清空的地點（依區域、地點排序；每個地點最多一筆）。寫入在 5A-4／5F-1。"""
    threads: tuple[ThreadState, ...] = ()
    """世界級線頭（所有人的世界都看得到；5B-1 起）。"""

    @field_validator("flags")
    @classmethod
    def _flags_sorted(cls, flags: tuple[str, ...]) -> tuple[str, ...]:
        if list(flags) != sorted(set(flags)):
            raise ValueError("flags 必須排序且不重複")
        return flags

    @field_validator("cleared")
    @classmethod
    def _cleared_sorted(cls, cleared: tuple[ClearedLocation, ...]) -> tuple[ClearedLocation, ...]:
        keys = [(c.region, c.location) for c in cleared]
        if keys != sorted(set(keys)):
            raise ValueError("cleared 必須依區域、地點排序且不重複")
        return cleared

    @field_validator("threads")
    @classmethod
    def _world_threads(cls, threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
        return _check_threads(threads)

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def is_cleared(self, region: str, location: str, now: int) -> bool:
        """``location`` 現在是否「已清空」（還沒到重生時間）。"""
        return any(
            c.region == region and c.location == location and now < c.respawn_at
            for c in self.cleared
        )


class CharacterState(_Model):
    """一個角色在大世界的狀態（``trpg-char/1``）。"""

    format: Literal["trpg-char/1"] = CHAR_FORMAT
    character_id: str = Field(pattern=ID_PATTERN)
    hero: UnitTemplate
    origin: str | None = None
    level: int = Field(ge=1)
    xp: int = Field(ge=0)
    hp: int = Field(ge=0)
    mana: int = Field(ge=0)
    stamina: int | None = Field(default=None, ge=0)
    """目前耐力；``None``＝滿（同 ``RunState``）。"""
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    supplies: int = Field(ge=0)
    revealed: tuple[LocationRef, ...] = ()
    """這個角色發現的隱藏地點（依區域、地點排序、不重複）。"""
    perception_marks: tuple[PerceptionMark, ...] = ()
    """每個隱藏地點最後一次感知判定的日子（依區域、地點排序、每地點一筆）。"""
    rng_counters: dict[str, int] = Field(default_factory=dict)
    """亂數串流 → 已用次數（依鍵排序；2.4 的 ``counter``）。"""
    pending_encounter: EncounterResult | None = None
    """還沒處理的遭遇；有它時不能移動或紮營（5A-4 開戰後清掉）。"""
    camped_at: LocationRef | None = None
    """目前紮營中的地點（營火；移動就清掉）。"""
    bench: tuple[str, ...] = ()
    """備用技能（學會但沒裝上的，排序；同 ``RunState.bench``）。換技能在城鎮與營火（5A-4）。"""
    fatigued: bool = False
    """疲憊（9.6.9 #98）：全滅後的下一場開場 HP 打折，打完一場就消失（5A-4）。"""
    attribute_points: int = Field(default=0, ge=0)
    """升級給的、還沒分配的屬性點（5A-4 只累積；分配之後再做）。"""
    visited_towns: tuple[str, ...] = ()
    """到過小鎮的區域 ID（排序、不重複）；城鎮之間的傳送只能去這些區（5A-4）。"""

    @field_validator("bench", "visited_towns")
    @classmethod
    def _sorted_ids(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("bench／visited_towns 必須排序且不重複")
        return ids

    event_steps: int = Field(default=0, ge=0)
    """距離上次事件走了幾步（事件出現機率用；5B-1）。"""
    pending_event: EventTrigger | None = None
    """觸發了、還沒處理的事件（5B-1；不擋移動，離開地點就作罷）。"""
    threads: tuple[ThreadState, ...] = ()
    """個人線頭（只屬於自己；5B-1 起）。"""
    next_battle: tuple[NextBattleMod, ...] = ()
    """下一場戰鬥帶的修正（情境判定的獎懲，5B-2 起；依產生順序）。"""

    @field_validator("revealed")
    @classmethod
    def _revealed_sorted(cls, refs: tuple[LocationRef, ...]) -> tuple[LocationRef, ...]:
        keys = [r.key() for r in refs]
        if keys != sorted(set(keys)):
            raise ValueError("revealed 必須依區域、地點排序且不重複")
        return refs

    @field_validator("perception_marks")
    @classmethod
    def _marks_sorted(cls, marks: tuple[PerceptionMark, ...]) -> tuple[PerceptionMark, ...]:
        keys = [(m.region, m.location) for m in marks]
        if keys != sorted(set(keys)):
            raise ValueError("perception_marks 必須依區域、地點排序且每地點一筆")
        return marks

    @field_validator("rng_counters")
    @classmethod
    def _counters(cls, counters: dict[str, int]) -> dict[str, int]:
        if any(v < 0 for v in counters.values()):
            raise ValueError("rng_counters 不可為負")
        return dict(sorted(counters.items()))

    @field_validator("threads")
    @classmethod
    def _char_threads(cls, threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
        return _check_threads(threads)

    def has_revealed(self, region: str, location: str) -> bool:
        return any(r.region == region and r.location == location for r in self.revealed)

    def perception_day(self, region: str, location: str) -> int | None:
        for mark in self.perception_marks:
            if mark.region == region and mark.location == location:
                return mark.day
        return None
