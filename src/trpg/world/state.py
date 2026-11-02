"""大世界的狀態：世界快照（``trpg-world/1``）與角色（``trpg-char/1``）（Phase 5A-2）。

``docs/phases/Phase5計畫.md`` 2.4、2.5、6.4。所有集合型欄位都以排序後的 tuple 存放（守則 2），
同樣的動作序列一定得到逐字相同的 JSON。角色欄位盡量和 :class:`trpg.roguelite.state.RunState`
同名同型別（2.2；``hero``、``origin``、``level``、``xp``、``hp``、``mana``、``stamina``）。

Phase 5A-6 加上成長欄位（靈感點、閃現狀態、生成技能、用法統計、技能階級、配點、精英首殺、誓約），
和 ``RunState`` 同名同型別，讓 :mod:`trpg.world.growth` 轉成 ``RunState`` 呼叫 roguelite 的成長
函式。
全部有預設值，``trpg-char/1`` 不升版號。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.skills import SkillDef
from trpg.content.world_oaths import OathDifficulty
from trpg.roguelite.state import PendingFlash, SkillOffer
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute
from trpg.skillgen.flash_state import SkillFlash
from trpg.skillgen.usage import SkillUsage
from trpg.world.clock import DayPhase

__all__ = [
    "CHAR_FORMAT",
    "WORLD_FORMAT",
    "CharacterState",
    "ClearedLocation",
    "CompanionAffinity",
    "CompanionBench",
    "EncounterResult",
    "EventTrigger",
    "LastBattle",
    "LocationRef",
    "NextBattleMod",
    "OathState",
    "PendingOffer",
    "PerceptionMark",
    "QuestState",
    "ShadowRecord",
    "ShadowReport",
    "ShadowSnapshot",
    "ThreadState",
    "TimedFlag",
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
    objective: Literal["escape", "defend"] | None = None
    """戰鬥解法指定的勝利條件（Phase 5B-4c；地圖支援時用它，否則全滅）；``None``＝地圖預設。"""
    world_flags: tuple[str, ...] = ()
    """遇敵當下有效的世界旗標（排序；Phase 5B-4c 世界級線頭到期結局的遭遇加人）。"""


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
    narrated: bool = False
    """說書人已經敘述過這個事件（Phase 5B-3；每個事件只能敘述、換骨架 1 次）。"""
    combat_solution: int | None = Field(default=None, ge=0)
    """選了戰鬥解法（Phase 5B-4b）：骨架 ``solutions`` 的索引；遭遇結束時結算事件。"""

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


class OathState(_Model):
    """目前的誓約（Phase 5A-6 接點；06 6.26、09 9.6.10 #106）：一直有效到自己解除。加成與違反判定在
    5C-3。"""

    template: str = Field(pattern=ID_PATTERN)
    params: dict[str, str | int] = Field(default_factory=dict)
    difficulty: OathDifficulty
    sworn_at: int = Field(ge=0)

    @field_validator("params")
    @classmethod
    def _sorted_params(cls, params: dict[str, str | int]) -> dict[str, str | int]:
        return dict(sorted(params.items()))


class LastBattle(_Model):
    """最近一次戰鬥的結果（Phase 5A-7；5A-5 待決 1）：``fight`` 結算時寫入（勝負都算），讓重新整理的
    畫面仍看得到輸贏。由日誌決定，可重播。"""

    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    won: bool
    end_reason: str | None = None
    rounds: int = Field(ge=0)
    xp_gained: int = Field(ge=0)
    level_before: int = Field(ge=1)
    level: int = Field(ge=1)
    at: int = Field(ge=0)
    oath: str | None = None
    """這場帶的誓約模板（5C-3；``None``＝沒有誓約）。"""
    oath_broken: bool = False
    """這場違反了誓約（戰鬥中或戰鬥結束時判定，5C-3）。"""


class CompanionBench(_Model):
    """劇情夥伴加入時替下的隊伍成員（5C-3；任務結束時還原）：傭兵 ID 或影子複本，與它的打法。"""

    mercenary: str | None = Field(default=None, pattern=ID_PATTERN)
    shadow: ShadowSnapshot | None = None
    ai: str | None = Field(default=None, pattern=ID_PATTERN)
    position: int = Field(default=1, ge=0)
    """原本在隊伍出場順序的第幾名（0 起算；5C-3 替掉第 2 名＝1）。"""

    @property
    def member_id(self) -> str:
        if self.mercenary is not None:
            return self.mercenary
        assert self.shadow is not None
        return self.shadow.owner


class CompanionAffinity(_Model):
    """劇情夥伴今天已經因為「帶他打贏」加了多少好感度（18.7.6：阿岳每天最多 +6）。"""

    day: int = Field(ge=0)
    gained: int = Field(ge=0)


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


class QuestState(_Model):
    """一個接過的任務（Phase 5B-4）：完成了幾步、是否已完成。"""

    quest: str = Field(pattern=ID_PATTERN)
    steps_done: int = Field(default=0, ge=0)
    done: bool = False
    started_at: int = Field(ge=0)
    completed_at: int | None = Field(default=None, ge=0)


class PendingOffer(_Model):
    """任務給的技能三選一，還沒選（Phase 5B-4；07 7.6）。候選已經產生好，選的時候不重抽。

    ``source``（Phase 5B-4c）：``quest``＝任務（``quest``、``step`` 是任務與步驟）；
    ``opportunity``＝事件的機遇解法（``quest``＝骨架 ID、``step``＝``opportunity``）。"""

    quest: str = Field(pattern=ID_PATTERN)
    step: str = Field(pattern=ID_PATTERN)
    offer: SkillOffer
    source: Literal["quest", "opportunity"] = "quest"


def _check_threads(threads: tuple[ThreadState, ...]) -> tuple[ThreadState, ...]:
    keys = [t.key() for t in threads]
    ids = [t.thread for t in threads]
    if keys != sorted(keys) or len(set(ids)) != len(ids):
        raise ValueError("threads 必須依建立時間、ID 排序且同一線頭不重複")
    return threads


class TimedFlag(_Model):
    """限時的世界旗標（Phase 5B-4c）：``until``（UTC 秒）以前有效。"""

    flag: str = Field(pattern=ID_PATTERN)
    until: int = Field(ge=0)


class ShadowSnapshot(_Model):
    """一個角色最後一次在城鎮整備時存下的影子（Phase 5C-2；09 9.6.10 #102）。

    借用時整份複製進招募者的角色（:attr:`CharacterState.shadows`），開戰時再照招募者壓強度上限
    （:mod:`trpg.world.shadows`，#87）。"""

    owner: str = Field(pattern=ID_PATTERN)
    """影子主人的角色 ID。"""
    hero: UnitTemplate
    """主角範本：名稱、屬性、武器、裝備中的技能與反應規則、基礎 HP。"""
    level: int = Field(ge=1)
    skill_tier: int | None = Field(default=None, ge=1)
    attribute_points: int = Field(default=0, ge=0)
    """還沒分配的屬性點（強度上限先扣這些）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    skills: tuple[SkillDef, ...] = ()
    """裝備中、不在內容庫的技能定義（依 ID 排序）。"""
    ai_profile: str | None = Field(default=None, pattern=ID_PATTERN)
    """主人設定的預設打法（#102）；``None``＝範本的 ``ai_profile``。"""
    gear: tuple[str, ...] = ()
    """裝備欄位預留（5D 接物品等級；目前影子不帶裝備）。"""
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    saved_at: int = Field(ge=0)

    @field_validator("attribute_spent")
    @classmethod
    def _sorted_spent(cls, spent: dict[Attribute, int]) -> dict[Attribute, int]:
        return dict(sorted(spent.items()))


class ShadowReport(_Model):
    """影子被借用的戰報（#102；每天第一次）。"""

    day: int = Field(ge=0)
    at: int = Field(ge=0)
    borrower: str = Field(pattern=ID_PATTERN)
    borrower_name: str
    region: str = Field(pattern=ID_PATTERN)
    location: str = Field(pattern=ID_PATTERN)
    won: bool
    foes: tuple[str, ...] = ()
    """敵方單位（範本或變體 ID，依陣容順序）。"""
    coins: int = Field(default=0, ge=0)


class ShadowRecord(_Model):
    """世界上一個角色的影子與被借用的紀錄（5C-2）。"""

    snapshot: ShadowSnapshot
    coins: int = Field(default=0, ge=0)
    """被借用累計的任務幣（5D 任務幣做好後轉入主人角色）。"""
    reward_day: int | None = Field(default=None, ge=0)
    """最後一次給獎的日子（``refresh_day``）。"""
    reports: tuple[ShadowReport, ...] = ()
    """最近的戰報（新的在後）。"""


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
    timed_flags: tuple[TimedFlag, ...] = ()
    """限時的世界旗標（依旗標排序、不重複；Phase 5B-4c 世界級線頭的到期結局，例：之後 2 天）。"""
    shadows: tuple[ShadowRecord, ...] = ()
    """每個角色的影子（依主人 ID 排序、每人一筆；Phase 5C-2）。"""

    @field_validator("shadows")
    @classmethod
    def _shadows_sorted(cls, shadows: tuple[ShadowRecord, ...]) -> tuple[ShadowRecord, ...]:
        owners = [s.snapshot.owner for s in shadows]
        if owners != sorted(set(owners)):
            raise ValueError("shadows 必須依主人 ID 排序且每人一筆")
        return shadows

    def shadow_of(self, owner: str) -> ShadowRecord | None:
        return next((s for s in self.shadows if s.snapshot.owner == owner), None)

    @field_validator("timed_flags")
    @classmethod
    def _timed_sorted(cls, flags: tuple[TimedFlag, ...]) -> tuple[TimedFlag, ...]:
        names = [f.flag for f in flags]
        if names != sorted(set(names)):
            raise ValueError("timed_flags 必須依旗標排序且不重複")
        return flags

    def active_flags(self, now: int) -> tuple[str, ...]:
        """``now`` 有效的世界旗標：``flags`` 加上還沒過期的 ``timed_flags``（排序）。"""
        timed = (f.flag for f in self.timed_flags if f.until > now)
        return tuple(sorted({*self.flags, *timed}))

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
    """下一場戰鬥帶的修正（情境判定的獎懲，5B-2 起；依產生順序）。5A-6 起開戰時套用，打完一場
    （勝負都算）清空。"""

    # --- 5A-6 成長（和 RunState 同名同型別；邏輯在 trpg.world.growth） ---
    insight: int = Field(default=0, ge=0)
    """還沒花掉的靈感點（06 6.34.2 大世界：每升 1 級、每種精英首殺…；一般戰鬥不給）。"""
    flash: dict[str, SkillFlash] = Field(default_factory=dict)
    """每招學會的技能的閃現狀態（目前的技能 ID → 狀態；依 ID 排序）。"""
    flash_bases: tuple[SkillDef, ...] = ()
    """閃現過的生成技能的原本定義（依 ID 排序）。"""
    pending_flash: PendingFlash | None = None
    """已付點、還沒選的閃現選項；有它時只能送 ``flash_pick``。"""
    skill_usage: dict[str, SkillUsage] = Field(default_factory=dict)
    """每招技能的用法統計（閃現選項依它排序；依 ID 排序）。"""
    skill_tier: int | None = Field(default=None, ge=1)
    """主角技能目前照哪一階的預算配數值（07 7.6 的角色階級；``None`` ＝ 5A-6 以前的角色，下次升級時
    照角色階級重配一次）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    """分配出去（重配時退回）的屬性點（同 ``RunState``；新角色開局的點數不在內）。"""
    elite_kills: tuple[str, ...] = ()
    """首殺過的精英種類（排序、不重複；06 6.34.2「每種精英的首殺各 1 點」）。"""
    oath: OathState | None = None
    """目前的誓約（同時 1 個，#106）。"""
    oath_cooldown_until: int = Field(default=0, ge=0)
    """解除誓約後，這個時間（UTC 秒）以前不能再立（#106「現實 1 天」）。"""
    last_battle: LastBattle | None = None
    """最近一次戰鬥的結果（Phase 5A-7；``fight`` 寫入，其他動作不清除）。"""

    # --- 5B-4 任務與好感度（邏輯在 trpg.world.quests、trpg.world.affinity） ---
    quests: tuple[QuestState, ...] = ()
    """接過的任務（依任務 ID 排序、不重複）。"""
    affinity: dict[str, int] = Field(default_factory=dict)
    """NPC → 好感度（依 NPC 排序；沒有的 NPC＝0，9.6.11 #116）。"""
    pending_offers: tuple[PendingOffer, ...] = ()
    """任務給的、還沒選的技能三選一（依產生順序）；有它時只能送 ``offer_pick``。"""
    offers_made: int = Field(default=0, ge=0)
    """產生過幾組技能候選（候選種子的計數，同 ``RunState.offers_made``）。"""
    story_flags: tuple[str, ...] = ()
    """劇情旗標（排序、不重複；例：解鎖導師任務鏈）。"""

    # --- 5B-4b 好感度取得、祕密事件 ---
    talk_days: dict[str, int] = Field(default_factory=dict)
    """NPC → 最後一次 ``talk`` 的日子（``refresh_day``；每天第一次聊天加好感度，18.7.6）。"""
    unlocked_skeletons: tuple[str, ...] = ()
    """解鎖的 ``unlock_only`` 事件骨架（排序、不重複；信賴的 NPC 說出祕密時，18.7.7）。"""

    # --- 5B-4c 機遇、只出一次的骨架 ---
    opportunities: tuple[str, ...] = ()
    """拿過機遇技能的骨架（排序、不重複；同一個機遇每個角色只能拿一次，代決 5B4c-5）。"""
    opportunity_tier_ups: int = Field(default=0, ge=0)
    """機遇給過幾次高 1 階的三選一（07 7.6：每人每季最多 1 次；角色一季一份）。"""
    finished_skeletons: tuple[str, ...] = ()
    """解決過的 ``once`` 骨架（排序、不重複；18.4 補充「骨架 22 每個角色只出現到解決為止」）。"""

    # --- 5C-1 隊伍（邏輯在 trpg.world.party） ---
    mercenaries: tuple[str, ...] = ()
    """隊伍裡的系統傭兵（依選擇順序＝出場順序、不重複）。5C-2 起沒有隊友＝獨行（玩法 PM 定 ③）。"""

    # --- 5C-2 影子與打法（邏輯在 trpg.world.party、trpg.world.shadows） ---
    shadows: tuple[ShadowSnapshot, ...] = ()
    """隊伍裡借來的影子（借用當下的複本，依選擇順序；排在傭兵之後出場）。"""
    party_ai: dict[str, str] = Field(default_factory=dict)
    """隊伍成員（傭兵 ID 或影子主人 ID）→ 選的 AI 打法（依鍵排序；沒有＝預設）。"""
    shadow_ai: str | None = Field(default=None, pattern=ID_PATTERN)
    """自己影子的預設打法（#102；``None``＝範本的）。"""

    # --- 5C-3 劇情夥伴（邏輯在 trpg.world.companions） ---
    companions: tuple[str, ...] = ()
    """隊伍裡的劇情夥伴（只在對應任務裡跟著，佔一個隊友位；#97）。依加入順序，排在傭兵、影子之後出場。"""
    companion_bench: tuple[CompanionBench, ...] = ()
    """夥伴加入時替下的成員（任務結束時還原；玩家自己 ``hire`` 就清掉）。"""
    companion_affinity: dict[str, CompanionAffinity] = Field(default_factory=dict)
    """夥伴 → 今天「帶他打贏」加過的好感度（每天上限，18.7.6）。"""

    @field_validator("party_ai")
    @classmethod
    def _sorted_party_ai(cls, ai: dict[str, str]) -> dict[str, str]:
        return dict(sorted(ai.items()))

    @field_validator("talk_days")
    @classmethod
    def _sorted_talk_days(cls, days: dict[str, int]) -> dict[str, int]:
        return dict(sorted(days.items()))

    @field_validator("unlocked_skeletons", "opportunities", "finished_skeletons")
    @classmethod
    def _sorted_unlocked(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        if list(ids) != sorted(set(ids)):
            raise ValueError("骨架清單必須排序且不重複")
        return ids

    @field_validator("quests")
    @classmethod
    def _sorted_quests(cls, quests: tuple[QuestState, ...]) -> tuple[QuestState, ...]:
        ids = [q.quest for q in quests]
        if ids != sorted(set(ids)):
            raise ValueError("quests 必須依任務 ID 排序且不重複")
        return quests

    @field_validator("affinity")
    @classmethod
    def _sorted_affinity(cls, affinity: dict[str, int]) -> dict[str, int]:
        return dict(sorted(affinity.items()))

    @field_validator("story_flags")
    @classmethod
    def _sorted_flags(cls, flags: tuple[str, ...]) -> tuple[str, ...]:
        if list(flags) != sorted(set(flags)):
            raise ValueError("story_flags 必須排序且不重複")
        return flags

    def quest_state(self, quest: str) -> QuestState | None:
        return next((q for q in self.quests if q.quest == quest), None)

    @field_validator("elite_kills")
    @classmethod
    def _sorted_kills(cls, kills: tuple[str, ...]) -> tuple[str, ...]:
        if list(kills) != sorted(set(kills)):
            raise ValueError("elite_kills 必須排序且不重複")
        return kills

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

    generated_skills: tuple[SkillDef, ...] = ()
    """不在內容庫的技能（創角的組合器起始技能等；依 ID 排序，同 ``RunState.generated_skills``；
    5A-5；5A-6 起也含閃現、升階重配後的技能）。開戰時併進該場規則包、換技能認得它們。"""

    @field_validator("generated_skills")
    @classmethod
    def _generated_sorted(cls, skills: tuple[SkillDef, ...]) -> tuple[SkillDef, ...]:
        ids = [s.id for s in skills]
        if ids != sorted(set(ids)):
            raise ValueError("generated_skills 必須依 ID 排序且不重複")
        return skills

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
