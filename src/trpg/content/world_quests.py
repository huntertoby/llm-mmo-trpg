"""大世界的任務、NPC 好感度、聊天內容與酒館傳聞（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16）。

- 任務（``content/world/quests/<region>.yaml``）：新手任務鏈、主線、區域任務鏈、隱藏任務
  （09 9.6.3、18.7）。任務結構與獎勵是資料（09 9.2 storylet），引擎（``trpg.world.quests``）
  依條件推進；LLM 只包裝。劇情技能（07 7.6「骨架固定、每人相同」）寫在同一個檔案的
  ``story_skills``，**不進技能池**。
- 好感度規則（``content/world/affinity.yaml``）：數值範圍與 5 級門檻（9.6.11 #116）、
  酒館每週傳聞數。
- 聊天與傳聞（``content/world/social/<region>.yaml``）：每位 NPC 依好感度能給的內容（玩法 PM 定：
  中立給一般傳聞、友善給隱藏任務入口、信賴才說祕密）、事件結果對好感度的影響、酒館傳聞池
  （9.6.7 #1、#3、#5）。

驗證分兩層：單檔（model validator）與跨檔案（:func:`quest_problems`、:func:`social_problems`）。
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Annotated, Final, Literal, get_args

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef
from trpg.content.world_events import WorldEventContent
from trpg.content.world_map import LocationMapDef
from trpg.content.world_rules import XP_SOURCES
from trpg.content.world_situations import Outcome
from trpg.shared.errors import ContentError

__all__ = [
    "AFFINITY_FILE",
    "AFFINITY_RANKS",
    "EVENT_CONDITION_KINDS",
    "WORLD_QUESTS_DIR",
    "WORLD_SOCIAL_DIR",
    "AffinityAtLeast",
    "AffinityRank",
    "AffinityRankDef",
    "AffinityRules",
    "AnyOf",
    "AtLocation",
    "EventAffinity",
    "HoldThread",
    "LeafCondition",
    "QuestCondition",
    "QuestDef",
    "QuestKind",
    "QuestStepDef",
    "QuestStepReached",
    "QuestTable",
    "RumorDef",
    "SituationDone",
    "SkillOfferReward",
    "SocialTable",
    "StepReward",
    "TalkEntry",
    "TalkKind",
    "Talked",
    "WinBattle",
    "WorldQuestContent",
    "load_world_quest_content",
    "quest_problems",
    "quest_refs",
    "social_problems",
]

WORLD_QUESTS_DIR = "world/quests"
"""任務的資料夾（相對於內容資料夾）；一區一檔，檔名＝``region``。"""
WORLD_SOCIAL_DIR = "world/social"
"""聊天內容、事件好感度與酒館傳聞的資料夾；一區一檔，檔名＝``region``。"""
AFFINITY_FILE = "world/affinity.yaml"
"""好感度規則（級距、酒館每週傳聞數）。"""

AffinityRank = Literal["hostile", "cold", "neutral", "friendly", "trusted"]
"""好感度 5 級（9.6.11 #116）：敵視／冷淡／中立／友善／信賴。"""
AFFINITY_RANKS: Final[tuple[AffinityRank, ...]] = get_args(AffinityRank)

QuestKind = Literal["starter", "main", "chain", "hidden"]
"""新手任務鏈／賽季主線／區域任務鏈／隱藏任務（09 9.6.3、18.7）。"""
TalkKind = Literal["rumor", "quest_entry", "secret"]
"""聊天能給的內容（9.6.7 #3：傳聞、隱藏任務入口；信賴才說的祕密）。"""

_TALK_MIN_RANK: Final[dict[TalkKind, AffinityRank]] = {
    "rumor": "neutral",
    "quest_entry": "friendly",
    "secret": "trusted",
}
"""玩法 PM 定（2026-11-03，照 #85 2a）：中立給一般傳聞、友善給隱藏任務入口、信賴才說祕密。"""

_MAX_LEVEL = 10
_MAX_DELTA = 100

_Id = Annotated[str, Field(pattern=ID_PATTERN)]


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    dup: set[str] = set()
    for value in values:
        if value in seen:
            dup.add(value)
        seen.add(value)
    return sorted(dup)


def _rank_index(rank: AffinityRank) -> int:
    return AFFINITY_RANKS.index(rank)


# ---------------------------------------------------------------------------
# 好感度規則
# ---------------------------------------------------------------------------


class AffinityRankDef(ContentModel):
    id: AffinityRank
    name_zh: str = Field(min_length=1)
    min: int
    """這一級的下限（含）。"""


class AffinityRules(ContentModel):
    """好感度的範圍與級距（9.6.11 #116），酒館每週傳聞數（開發 PM 定）。"""

    min_value: int = -100
    max_value: int = 100
    ranks: tuple[AffinityRankDef, ...]
    rumors_per_week: int = Field(default=3, ge=1)
    week_days: int = Field(default=7, ge=1)

    @model_validator(mode="after")
    def _check(self) -> AffinityRules:
        if self.min_value >= self.max_value:
            raise ValueError("min_value 必須小於 max_value")
        if tuple(r.id for r in self.ranks) != AFFINITY_RANKS:
            raise ValueError(f"ranks 必須依序是 {list(AFFINITY_RANKS)}")
        mins = [r.min for r in self.ranks]
        if mins[0] != self.min_value:
            raise ValueError("第一級（hostile）的 min 必須等於 min_value")
        if any(a >= b for a, b in pairwise(mins)) or mins[-1] > self.max_value:
            raise ValueError("ranks 的 min 必須遞增且不超過 max_value")
        return self

    def clamp(self, value: int) -> int:
        return max(self.min_value, min(self.max_value, value))

    def rank_of(self, value: int) -> AffinityRank:
        rank: AffinityRank = self.ranks[0].id
        for r in self.ranks:
            if value >= r.min:
                rank = r.id
        return rank

    def name_of(self, rank: AffinityRank) -> str:
        return next(r.name_zh for r in self.ranks if r.id == rank)

    def summary(self) -> str:
        bounds = "、".join(f"{r.name_zh} ≥ {r.min}" for r in self.ranks)
        return (
            f"好感度 {self.min_value}～{self.max_value}（{bounds}）；"
            f"酒館每 {self.week_days} 天 {self.rumors_per_week} 條傳聞"
        )


# ---------------------------------------------------------------------------
# 任務條件
# ---------------------------------------------------------------------------


class AtLocation(ContentModel):
    """狀態：角色在 ``location``。"""

    kind: Literal["at_location"] = "at_location"
    location: _Id


class HoldThread(ContentModel):
    """狀態：角色持有有效的線頭 ``thread``（個人或世界級）。"""

    kind: Literal["hold_thread"] = "hold_thread"
    thread: _Id


class AffinityAtLeast(ContentModel):
    """狀態：對 ``npc`` 的好感度級別 ≥ ``rank``。"""

    kind: Literal["affinity"] = "affinity"
    npc: _Id
    rank: AffinityRank


class QuestStepReached(ContentModel):
    """狀態：任務 ``quest`` 已完成至少 ``step`` 步。"""

    kind: Literal["quest_step"] = "quest_step"
    quest: _Id
    step: int = Field(ge=1)


class WinBattle(ContentModel):
    """事件：這個動作在 ``location`` 打贏一場戰鬥。"""

    kind: Literal["win_battle"] = "win_battle"
    location: _Id


class SituationDone(ContentModel):
    """事件：這個動作對骨架 ``skeleton`` 做了情境判定，結果在 ``outcomes``
    （``templates`` 空＝不限模板）。"""

    kind: Literal["situation"] = "situation"
    skeleton: _Id
    templates: tuple[_Id, ...] = ()
    outcomes: tuple[Outcome, ...] = ("success", "partial")

    @model_validator(mode="after")
    def _check(self) -> SituationDone:
        if not self.outcomes or len(set(self.outcomes)) != len(self.outcomes):
            raise ValueError("situation 條件的 outcomes 至少 1 個且不重複")
        return self


class Talked(ContentModel):
    """事件：這個動作和 ``npc`` 說了話（``talk`` 動作）。"""

    kind: Literal["talk"] = "talk"
    npc: _Id


type LeafCondition = Annotated[
    AtLocation
    | HoldThread
    | AffinityAtLeast
    | QuestStepReached
    | WinBattle
    | SituationDone
    | Talked,
    Field(discriminator="kind"),
]

EVENT_CONDITION_KINDS: Final = frozenset({"win_battle", "situation", "talk"})
"""事件型條件（只看這個動作產生的事件）；其他是狀態型。"""


class AnyOf(ContentModel):
    """任一個成立即可（2 個以上、不可巢狀）。"""

    kind: Literal["any_of"] = "any_of"
    conditions: tuple[LeafCondition, ...] = Field(min_length=2)


type QuestCondition = Annotated[
    AtLocation
    | HoldThread
    | AffinityAtLeast
    | QuestStepReached
    | WinBattle
    | SituationDone
    | Talked
    | AnyOf,
    Field(discriminator="kind"),
]


def _leaves(condition: QuestCondition) -> tuple[LeafCondition, ...]:
    if isinstance(condition, AnyOf):
        return condition.conditions
    return (condition,)


def _has_event(condition: QuestCondition) -> bool:
    return any(leaf.kind in EVENT_CONDITION_KINDS for leaf in _leaves(condition))


# ---------------------------------------------------------------------------
# 任務
# ---------------------------------------------------------------------------


class SkillOfferReward(ContentModel):
    """技能三選一（07 7.6：新手鏈與區域任務鏈出白板）。``bias_keywords`` 只是記錄（候選產生器
    沒有關鍵字偏向的輸入，見 5B-4 待決）。"""

    kind: Literal["whiteboard", "complete"]
    bias_keywords: tuple[_Id, ...] = ()


class StepReward(ContentModel):
    """完成一步的獎勵（全部可省略）。"""

    xp_source: str | None = None
    """經驗來源（``world/rules.yaml`` 的 ``xp.shares_permille`` 鍵）；``None``＝不給經驗。"""
    xp_level: int = Field(default=1, ge=1, le=_MAX_LEVEL)
    """份數換算用的地點建議等級（1 份＝100×(1＋10%×(等級−1))，5A-SIM2）。"""
    insight: int = Field(default=0, ge=0)
    """靈感點（06 6.34.2「任務鏈段落」）。"""
    offer: SkillOfferReward | None = None
    story_skill: str | None = Field(default=None, pattern=ID_PATTERN)
    """劇情技能（同檔 ``story_skills`` 的 ID）。"""
    affinity: dict[str, int] = Field(default_factory=dict)
    """NPC → 好感度增減。"""
    flags: tuple[_Id, ...] = ()
    """角色的劇情旗標。"""

    @model_validator(mode="after")
    def _check(self) -> StepReward:
        bad = sorted(n for n, d in self.affinity.items() if d == 0 or abs(d) > _MAX_DELTA)
        if bad:
            raise ValueError(f"好感度增減必須是 ±1～{_MAX_DELTA}：{bad}")
        if _duplicates(self.flags):
            raise ValueError(f"flags 重複：{_duplicates(self.flags)}")
        return self


class QuestStepDef(ContentModel):
    id: _Id
    text_zh: str = Field(min_length=1)
    when: tuple[QuestCondition, ...] = Field(min_length=1)
    """全部成立才完成這一步。"""
    reward: StepReward = Field(default_factory=StepReward)

    def has_event_condition(self) -> bool:
        return any(_has_event(c) for c in self.when)


class QuestDef(ContentModel):
    id: _Id
    kind: QuestKind
    name_zh: str = Field(min_length=1)
    summary_zh: str = ""
    giver: str | None = Field(default=None, pattern=ID_PATTERN)
    """給任務的 NPC：接任務要在他所在的地點。"""
    start: tuple[QuestCondition, ...] = ()
    """接任務的條件（只能用狀態型條件）。"""
    steps: tuple[QuestStepDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> QuestDef:
        dup = _duplicates(s.id for s in self.steps)
        if dup:
            raise ValueError(f"任務 {self.id} 的步驟 ID 重複：{dup}")
        if any(_has_event(c) for c in self.start):
            raise ValueError(f"任務 {self.id} 的 start 只能用狀態型條件")
        return self


class QuestTable(ContentModel):
    """``content/world/quests/<region>.yaml``。"""

    region: _Id
    quests: tuple[QuestDef, ...] = ()
    story_skills: tuple[SkillDef, ...] = ()
    """劇情技能（07 7.6；不進技能池，只由任務給）。"""

    @model_validator(mode="after")
    def _check(self) -> QuestTable:
        for label, ids in (
            ("任務", [q.id for q in self.quests]),
            ("劇情技能", [s.id for s in self.story_skills]),
        ):
            dup = _duplicates(ids)
            if dup:
                raise ValueError(f"{label} ID 重複：{dup}")
        return self

    def quest_by_id(self) -> dict[str, QuestDef]:
        return {q.id: q for q in self.quests}

    def story_skill_by_id(self) -> dict[str, SkillDef]:
        return {s.id: s for s in self.story_skills}

    def summary(self) -> str:
        kinds = {k: sum(1 for q in self.quests if q.kind == k) for k in get_args(QuestKind)}
        steps = sum(len(q.steps) for q in self.quests)
        detail = "、".join(f"{k} {n}" for k, n in kinds.items() if n)
        return (
            f"{self.region}：{len(self.quests)} 個任務（{detail}）、{steps} 步、"
            f"{len(self.story_skills)} 招劇情技能"
        )


# ---------------------------------------------------------------------------
# 聊天、事件好感度、傳聞
# ---------------------------------------------------------------------------


class TalkEntry(ContentModel):
    """NPC 依好感度能給的一條內容（9.6.7 #3；級別照玩法 PM 定）。"""

    id: _Id
    npc: _Id
    rank: AffinityRank
    kind: TalkKind
    text_zh: str = Field(min_length=1)
    quest: str | None = Field(default=None, pattern=ID_PATTERN)
    """``quest_entry``：入口指向的隱藏任務。"""

    @model_validator(mode="after")
    def _check(self) -> TalkEntry:
        need = _TALK_MIN_RANK[self.kind]
        if self.kind == "secret" and self.rank != "trusted":
            raise ValueError(f"聊天內容 {self.id}：祕密只能是信賴（trusted）")
        if _rank_index(self.rank) < _rank_index(need):
            raise ValueError(f"聊天內容 {self.id}：{self.kind} 至少要 {need}")
        if (self.kind == "quest_entry") != (self.quest is not None):
            raise ValueError(f"聊天內容 {self.id}：只有 quest_entry 要填 quest（而且必填）")
        return self


class EventAffinity(ContentModel):
    """事件結果 → NPC 好感度增減（情境判定的骨架與結果）。"""

    skeleton: _Id
    outcome: Outcome
    npc: _Id
    delta: int = Field(ge=-_MAX_DELTA, le=_MAX_DELTA)

    @model_validator(mode="after")
    def _check(self) -> EventAffinity:
        if self.delta == 0:
            raise ValueError("事件好感度的 delta 不可為 0")
        return self


class RumorDef(ContentModel):
    """酒館傳聞（9.6.7 #1：指向機遇或隱藏地點的線索）。只是文字資訊，不給線頭、不揭露地點。"""

    id: _Id
    text_zh: str = Field(min_length=1)
    location: str | None = Field(default=None, pattern=ID_PATTERN)
    skeleton: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _check(self) -> RumorDef:
        if self.location is not None and self.skeleton is not None:
            raise ValueError(f"傳聞 {self.id}：location 與 skeleton 至多填一個")
        return self


class SocialTable(ContentModel):
    """``content/world/social/<region>.yaml``。"""

    region: _Id
    talk: tuple[TalkEntry, ...] = ()
    event_affinity: tuple[EventAffinity, ...] = ()
    rumors: tuple[RumorDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> SocialTable:
        for label, ids in (
            ("聊天內容", [t.id for t in self.talk]),
            ("傳聞", [r.id for r in self.rumors]),
        ):
            dup = _duplicates(ids)
            if dup:
                raise ValueError(f"{label} ID 重複：{dup}")
        return self

    def rumor_by_id(self) -> dict[str, RumorDef]:
        return {r.id: r for r in self.rumors}

    def summary(self) -> str:
        return (
            f"{self.region}：{len(self.talk)} 條聊天內容、{len(self.event_affinity)} 條事件好感度、"
            f"{len(self.rumors)} 條酒館傳聞"
        )


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Refs:
    """跨檔案檢查要查的表。"""

    world_map: LocationMapDef | None
    npcs: Collection[str]
    skeletons: Mapping[str, Collection[str]]
    """本區骨架 → 屬於它的情境模板。"""
    threads: Collection[str]
    keywords: Collection[str] | None


def _leaf_problems(where: str, leaf: LeafCondition, refs: _Refs, table: QuestTable) -> list[str]:
    problems: list[str] = []
    locations = set() if refs.world_map is None else set(refs.world_map.location_by_id())
    if isinstance(leaf, AtLocation | WinBattle) and leaf.location not in locations:
        problems.append(f"{where}：未知地點 {leaf.location}")
    elif isinstance(leaf, HoldThread) and leaf.thread not in refs.threads:
        problems.append(f"{where}：未知線頭 {leaf.thread}")
    elif isinstance(leaf, AffinityAtLeast | Talked) and leaf.npc not in refs.npcs:
        problems.append(f"{where}：未知 NPC {leaf.npc}")
    elif isinstance(leaf, QuestStepReached):
        quest = table.quest_by_id().get(leaf.quest)
        if quest is None:
            problems.append(f"{where}：未知任務 {leaf.quest}")
        elif leaf.step > len(quest.steps):
            problems.append(f"{where}：任務 {leaf.quest} 只有 {len(quest.steps)} 步")
    elif isinstance(leaf, SituationDone):
        templates = refs.skeletons.get(leaf.skeleton)
        if templates is None:
            problems.append(f"{where}：本區沒有骨架 {leaf.skeleton}")
        else:
            problems += [
                f"{where}：模板 {t} 不屬於骨架 {leaf.skeleton}"
                for t in leaf.templates
                if t not in templates
            ]
    return problems


def _condition_problems(
    where: str, conditions: Iterable[QuestCondition], refs: _Refs, table: QuestTable
) -> list[str]:
    problems: list[str] = []
    for condition in conditions:
        for leaf in _leaves(condition):
            problems += _leaf_problems(where, leaf, refs, table)
    return problems


def _reward_problems(where: str, reward: StepReward, refs: _Refs, table: QuestTable) -> list[str]:
    problems: list[str] = []
    if reward.xp_source is not None and reward.xp_source not in XP_SOURCES:
        problems.append(f"{where}：未知經驗來源 {reward.xp_source}")
    if reward.story_skill is not None and reward.story_skill not in table.story_skill_by_id():
        problems.append(f"{where}：未知劇情技能 {reward.story_skill}")
    problems += [f"{where}：未知 NPC {n}" for n in sorted(reward.affinity) if n not in refs.npcs]
    if reward.offer is not None and refs.keywords is not None:
        problems += [
            f"{where}：未知關鍵字 {k}" for k in reward.offer.bias_keywords if k not in refs.keywords
        ]
    return problems


def quest_problems(table: QuestTable, refs: _Refs) -> list[str]:
    """任務的跨檔案問題（排序）。"""
    problems: list[str] = []
    if refs.world_map is None:
        problems.append(f"區域 {table.region} 沒有地點圖")
    for quest in table.quests:
        if quest.giver is not None and quest.giver not in refs.npcs:
            problems.append(f"任務 {quest.id}：未知 NPC {quest.giver}")
        problems += _condition_problems(f"任務 {quest.id} start", quest.start, refs, table)
        for step in quest.steps:
            where = f"任務 {quest.id} 步驟 {step.id}"
            problems += _condition_problems(where, step.when, refs, table)
            problems += _reward_problems(where, step.reward, refs, table)
    return sorted(problems)


def social_problems(table: SocialTable, refs: _Refs, quests: QuestTable | None) -> list[str]:
    """聊天、事件好感度、傳聞的跨檔案問題（排序）。"""
    problems: list[str] = []
    if refs.world_map is None:
        problems.append(f"區域 {table.region} 沒有地點圖")
    locations = set() if refs.world_map is None else set(refs.world_map.location_by_id())
    quest_map = {} if quests is None else quests.quest_by_id()
    for entry in table.talk:
        if entry.npc not in refs.npcs:
            problems.append(f"聊天內容 {entry.id}：未知 NPC {entry.npc}")
        if entry.quest is not None:
            quest = quest_map.get(entry.quest)
            if quest is None or quest.kind != "hidden":
                problems.append(f"聊天內容 {entry.id}：{entry.quest} 不是本區的隱藏任務")
            elif quest.giver != entry.npc:
                problems.append(
                    f"聊天內容 {entry.id}：隱藏任務 {quest.id} 的 giver 不是 {entry.npc}"
                )
    for row in table.event_affinity:
        if row.skeleton not in refs.skeletons:
            problems.append(f"事件好感度：本區沒有骨架 {row.skeleton}")
        if row.npc not in refs.npcs:
            problems.append(f"事件好感度：未知 NPC {row.npc}")
    for rumor in table.rumors:
        if rumor.location is not None and rumor.location not in locations:
            problems.append(f"傳聞 {rumor.id}：未知地點 {rumor.location}")
        if rumor.skeleton is not None and rumor.skeleton not in refs.skeletons:
            problems.append(f"傳聞 {rumor.id}：本區沒有骨架 {rumor.skeleton}")
    return sorted(problems)


# ---------------------------------------------------------------------------
# 載入
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorldQuestContent:
    """載入後的任務、聊天與好感度規則。"""

    quests: dict[str, QuestTable] = field(default_factory=dict)
    social: dict[str, SocialTable] = field(default_factory=dict)
    affinity: AffinityRules | None = None

    def quest(self, region: str, quest_id: str) -> QuestDef | None:
        table = self.quests.get(region)
        return None if table is None else table.quest_by_id().get(quest_id)


def _load_dir[M: QuestTable | SocialTable](
    directory: Path, model: type[M]
) -> dict[str, tuple[Path, M]]:
    result: dict[str, tuple[Path, M]] = {}
    if not directory.is_dir():
        return result
    for path in sorted(directory.glob("*.yaml")):
        table = load_content_file(path, model)
        if table.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {table.region!r}）")
        result[table.region] = (path, table)
    return result


def _cross_region(label: str, items: Iterable[tuple[Path, Iterable[str]]]) -> None:
    owner: dict[str, Path] = {}
    for path, ids in items:
        for item_id in ids:
            if item_id in owner and owner[item_id] != path:
                raise ContentError(path, f"{label} {item_id} 和 {owner[item_id].name} 重複")
            owner[item_id] = path


def quest_refs(
    region: str,
    world_maps: Mapping[str, LocationMapDef],
    events: WorldEventContent,
    keyword_ids: Collection[str] | None,
) -> _Refs:
    npc_table = events.npcs.get(region)
    event_table = events.events.get(region)
    skeletons: dict[str, set[str]] = (
        {} if event_table is None else {s.id: set() for s in event_table.skeletons}
    )
    template_table = events.situations.templates.get(region)
    for template in () if template_table is None else template_table.templates:
        skeletons.setdefault(template.skeleton, set()).add(template.id)
    threads = {t for table in events.events.values() for t in table.thread_ids()}
    return _Refs(
        world_map=world_maps.get(region),
        npcs=set() if npc_table is None else set(npc_table.npc_by_id()),
        skeletons=skeletons,
        threads=threads,
        keywords=keyword_ids,
    )


def load_world_quest_content(
    root: Path,
    world_maps: Mapping[str, LocationMapDef],
    events: WorldEventContent,
    files: list[tuple[Path, ContentModel]],
    *,
    check_skill: Callable[[SkillDef], list[str]] | None = None,
    keyword_ids: Collection[str] | None = None,
) -> WorldQuestContent:
    """載入 ``world/quests/``、``world/social/``、``world/affinity.yaml``；不存在＝空／``None``。

    ``check_skill`` 是內容庫給的技能引用與費用檢查（劇情技能和 ``content/skills/`` 同一套）。
    """
    quests = _load_dir(root / WORLD_QUESTS_DIR, QuestTable)
    social = _load_dir(root / WORLD_SOCIAL_DIR, SocialTable)
    _cross_region("任務", ((p, [q.id for q in t.quests]) for p, t in quests.values()))
    _cross_region(
        "聊天內容／傳聞",
        ((p, [*(e.id for e in t.talk), *(r.id for r in t.rumors)]) for p, t in social.values()),
    )
    for region in sorted(quests):
        path, table = quests[region]
        problems = quest_problems(table, quest_refs(region, world_maps, events, keyword_ids))
        if check_skill is not None:
            for skill in table.story_skills:
                problems += [f"劇情技能 {skill.id}：{p}" for p in check_skill(skill)]
        if problems:
            raise ContentError(path, "；".join(problems))
        files.append((path, table))
    for region in sorted(social):
        path, s_table = social[region]
        q_table = quests[region][1] if region in quests else None
        problems = social_problems(
            s_table, quest_refs(region, world_maps, events, keyword_ids), q_table
        )
        if problems:
            raise ContentError(path, "；".join(problems))
        files.append((path, s_table))
    affinity_path = root / AFFINITY_FILE
    affinity: AffinityRules | None = None
    if affinity_path.is_file():
        affinity = load_content_file(affinity_path, AffinityRules)
        files.append((affinity_path, affinity))
    return WorldQuestContent(
        quests={r: t for r, (_, t) in sorted(quests.items())},
        social={r: t for r, (_, t) in sorted(social.items())},
        affinity=affinity,
    )
