"""大世界的事件骨架、線頭與 NPC 人設卡（Phase 5B-1；``docs/phases/Phase5計畫.md`` 第 8 節）。

- 事件骨架（``content/world/events/<region>.yaml``）：誰、想要什麼、阻礙、賭注、可選解法、可能留下
  的線頭（``docs/design/09-世界與敘事.md`` 9.6.7 #6、9.2 storylet）。LLM 依世界狀態挑骨架、填角色
  與動機（5B-3），但骨架本身、解法清單與線頭都是資料；LLM 不能自己多生事件，線頭只能由事件
  結果產生。
- NPC 人設卡（``content/world/npcs/<region>.yaml``；18.5、#107）：給說書人用的個性、說話方式、
  祕密（不直接顯示給玩家）。
- 事件規則（``content/world/event_rules.yaml``）：事件出現頻率（依移動步數，9.6.7 #6）、線頭上限
  與到期（Q11）。規則本身在 ``trpg.world.events``、``trpg.world.threads``。

驗證分兩層：單檔（model validator）與跨檔案（:func:`world_event_problems`、
:func:`npc_card_problems`：地點、天氣、NPC、線頭的引用）。
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, get_args

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, DollHair, DollSlot
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel, duplicates
from trpg.content.world_address import address_problems
from trpg.content.world_map import LocationMapDef
from trpg.content.world_narration import (
    ACTOR_MAX_CHARS,
    STORY_TEMPLATES_FILE,
    StoryTemplates,
    load_story_templates,
)
from trpg.content.world_situations import AliasesZh, SituationContent, load_situation_content
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute

__all__ = [
    "EVENT_ART_IDS",
    "EVENT_RULES_FILE",
    "WORLD_EVENTS_DIR",
    "WORLD_NPCS_DIR",
    "EventArtId",
    "EventFrequency",
    "EventRules",
    "EventSkeletonDef",
    "EventSkeletonTable",
    "NpcCardDef",
    "NpcCardTable",
    "SolutionDef",
    "SolutionKind",
    "ThreadDef",
    "ThreadRules",
    "ThreadScope",
    "WorldEventContent",
    "load_world_event_content",
    "npc_card_problems",
    "world_event_problems",
]

WORLD_EVENTS_DIR = "world/events"
"""事件骨架的資料夾（相對於內容資料夾）；一區一檔，檔名＝``region``。"""
WORLD_NPCS_DIR = "world/npcs"
"""NPC 人設卡的資料夾；一區一檔，檔名＝``region``。"""
EVENT_RULES_FILE = "world/event_rules.yaml"
"""事件出現頻率與線頭規則的數值。"""

SolutionKind = Literal[
    "combat",  # 戰鬥（護送、撤離、不殺目標等寫在 note_zh）
    "situation",  # 情境判定（09 9.6.4）；attributes 是允許的屬性
    "parley",  # 交涉（付錢、給材料、換物）
    "abandon",  # 放棄
    "opportunity",  # 機遇（18.4 #12：帶特定技能靠近；條件見 requires_keyword）
]
EventArtId = Literal[
    "ambush",  # 遭遇・伏擊
    "chest",  # 寶箱
    "stele",  # 古碑
    "altar",  # 祭壇・機遇
    "villager",  # 村民求助
    "caravan",  # 商隊
    "trap",  # 陷阱
    "camp",  # 營火休息
    "anomaly",  # 異象・源晶裂痕
    "friend",  # 朋友的足跡
]
"""事件卡插圖的場景 ID（6C-ART2；``docs/art/事件插圖.md`` 第 2 節、
``docs/archive/art/Phase6剩餘美術移植需求.md`` 第 3 節）。只畫，不影響事件規則。"""
EVENT_ART_IDS: tuple[str, ...] = get_args(EventArtId)
"""已知的插圖 ID（順序同樣張）。"""
ThreadScope = Literal[
    "personal",  # 個人線頭：只屬於自己（9.6.7 #6「欠你的人情」）
    "world",  # 世界級線頭：出現在所有人的世界（「放走的頭目、鬆動的封印」）
]

_MAX_SITUATION_ATTRIBUTES = 3

_Id = Annotated[str, Field(pattern=ID_PATTERN)]


# ---------------------------------------------------------------------------
# 事件骨架
# ---------------------------------------------------------------------------


class SolutionDef(ContentModel):
    """骨架的一種可選解法（9.6.7 #6：戰鬥、情境判定、交涉、放棄）。"""

    kind: SolutionKind
    attributes: tuple[Attribute, ...] = ()
    """情境判定允許的屬性（只有 ``situation`` 可填，且必填 1～3 個）。"""
    note_zh: str = ""
    """18.4 括號裡的說明（例：「找安全路」「護送戰」「付錢」）；選項格的主字，玩家看得到，
    不放設計編號（TXT-1）。"""
    hint_zh: str = ""
    """選項的補充說明（TXT-1）：只放在說明卡（滑過選項時），不放進主字；空＝沒有。"""
    requires_keyword: str | None = Field(default=None, pattern=ID_PATTERN)
    """機遇的條件（Phase 5B-2；18.4 補充）：裝備的技能中任何一招帶這個關鍵字
    （``skill_keywords.yaml``）。只有 ``opportunity`` 可填。"""
    threads: tuple[_Id, ...] = Field(default=(), max_length=2)
    """成功時留下的線頭（Phase 5B-4b；只有 ``combat``、``parley`` 可填；本骨架的線頭或
    ``shared_threads``；9.6.7 #6「0～2 條」）。"""
    cost_supplies: int = Field(default=0, ge=0)
    """交涉付出的補給（Phase 5B-4b；只有 ``parley``；沒有金幣與道具，付錢、給材料都用補給代替）。"""
    waive_thread: str | None = Field(default=None, pattern=ID_PATTERN)
    """持有這條個人線頭時可以拿它抵掉付出（用掉；Phase 5B-4b，18.4 補充「用人情代替青竹節」）。
    只有 ``parley``。"""
    objective: Literal["escape", "defend"] | None = None
    """戰鬥解法的勝利條件（Phase 5B-4c，18.4 補充：護送、押送隊＝撤離；擋追兵、不殺獵人＝守點）；
    只有 ``combat``。``None``＝一般勝利。地圖沒有該勝利條件的資料時也是一般勝利。"""

    @model_validator(mode="after")
    def _check(self) -> SolutionDef:
        if self.requires_keyword is not None and self.kind != "opportunity":
            raise ValueError(f"{self.kind} 解法不可填 requires_keyword（只有 opportunity 可以）")
        if self.threads and self.kind not in ("combat", "parley"):
            raise ValueError(f"{self.kind} 解法不可填 threads（只有 combat、parley 可以）")
        if self.objective is not None and self.kind != "combat":
            raise ValueError(f"{self.kind} 解法不可填 objective（只有 combat）")
        if (self.cost_supplies or self.waive_thread is not None) and self.kind != "parley":
            raise ValueError(f"{self.kind} 解法不可填 cost_supplies／waive_thread（只有 parley）")
        if len(set(self.threads)) != len(self.threads):
            raise ValueError("解法的 threads 不可重複")
        if self.kind == "situation":
            if not 1 <= len(self.attributes) <= _MAX_SITUATION_ATTRIBUTES:
                raise ValueError("情境判定解法必須有 1～3 個允許的屬性")
            if len(set(self.attributes)) != len(self.attributes):
                raise ValueError("情境判定解法的屬性不可重複")
        elif self.attributes:
            raise ValueError(f"{self.kind} 解法不可填屬性（只有 situation 可以）")
        return self


class ThreadDef(ContentModel):
    """事件結果可能留下的線頭（9.6.7 #6）。"""

    id: str = Field(pattern=ID_PATTERN)
    text_zh: str = Field(min_length=1)
    scope: ThreadScope = "personal"
    npc: str | None = Field(default=None, pattern=ID_PATTERN)
    """相關 NPC 人設卡。"""
    aliases_zh: AliasesZh = ()
    """用心清單 ① 的關鍵詞別名（``text_zh`` 之外；Phase 5C-3d）。"""
    hints_location: str | None = Field(default=None, pattern=ID_PATTERN)
    """線頭指向的隱藏地點（任務線索；必須是 ``reveal`` 含 ``quest_clue`` 的隱藏地點）。"""
    on_expire_zh: str = ""
    """到期結局（約 3 天到期「也是一種結局」）；空＝淡出。"""
    on_expire_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    """到期結局的旗標（Phase 5B-4b）：個人線頭給角色的劇情旗標、世界級給世界旗標；遭遇表的
    ``variants`` 依它換陣容。``None``＝淡出（留著、無效）。"""
    on_expire_seconds: int | None = Field(default=None, ge=1)
    """世界級到期結局旗標的有效時間（Phase 5B-4c，18.4 補充「之後 2 天」）：從線頭到期起算；
    ``None``＝永久。只有世界級、要有 ``on_expire_flag``。"""

    @model_validator(mode="after")
    def _check(self) -> ThreadDef:
        if self.on_expire_seconds is not None:
            if self.on_expire_flag is None:
                raise ValueError(f"線頭 {self.id}：on_expire_seconds 要搭配 on_expire_flag")
            if self.scope != "world":
                raise ValueError(f"線頭 {self.id}：只有世界級線頭可填 on_expire_seconds")
        return self


class EventSkeletonDef(ContentModel):
    """一個事件骨架（18.4 的一列）。"""

    id: str = Field(pattern=ID_PATTERN)
    number: int = Field(ge=1)
    """設計文件的編號（對照用；同區不重複）。"""
    who_zh: str = Field(min_length=1)
    want_zh: str = Field(min_length=1)
    obstacle_zh: str = ""
    stakes_zh: str = Field(min_length=1)
    locations: tuple[_Id, ...] = Field(min_length=1)
    """可能出現的地點（本區地點圖的 ID）。"""
    day_phase: Literal["day", "night"] | None = None
    """只在白天／夜晚出現；``None``＝不限。"""
    weather: tuple[_Id, ...] = ()
    """只在這些天氣出現（``weather.yaml`` 的 ID）；空＝不限。"""
    npcs: tuple[_Id, ...] = ()
    """相關 NPC 人設卡（同區）。"""
    solutions: tuple[SolutionDef, ...] = Field(min_length=1)
    threads: tuple[ThreadDef, ...] = ()
    follows: tuple[_Id, ...] = ()
    """這個骨架能接的線頭 ID（9.6.7 #6「產生下一個事件時優先接線頭」）。"""
    shared_threads: tuple[_Id, ...] = ()
    """本骨架的結果可以給、但定義在別的骨架的線頭（Phase 5B-4b；線頭 ID 全區唯一）。"""
    unlock_only: bool = False
    """只有角色解鎖後才會出現（Phase 5B-4b，18.7.7：信賴的 NPC 說出祕密時解鎖）。"""
    once: bool = False
    """每個角色只出現到解決為止（Phase 5B-4c，18.4 補充「骨架 22」）：結果不是放棄就不再出現。"""
    guarantee_text_zh: str | None = Field(default=None, min_length=1, max_length=150)
    """機遇保底觸發時的專用旁白（Phase 5B-4e；不看天氣也通的文字，不經說書人）；``None``＝照一般
    事件敘述。上限同說書人旁白（``TEXT_MAX_CHARS``）。"""
    guarantee_who_zh: str | None = Field(default=None, min_length=1, max_length=ACTOR_MAX_CHARS)
    """機遇保底觸發時事件卡的「誰」（Phase 5B-4f）；``None``＝照 ``who_zh``。上限同說書人角色
    （``ACTOR_MAX_CHARS``）。"""
    art: EventArtId | None = None
    """事件卡插圖的場景（6C-ART2；只畫，不影響規則）；``None``＝前端照第一個不是放棄的選項的
    圖示挑。"""

    def who_for(self, *, guaranteed: bool) -> str:
        """事件的「誰」：保底觸發且有 ``guarantee_who_zh`` 時用它，否則 ``who_zh``（5B-4f）。"""
        if guaranteed and self.guarantee_who_zh is not None:
            return self.guarantee_who_zh
        return self.who_zh

    def result_threads(self) -> frozenset[str]:
        """事件結果可以留下的線頭：本骨架的與 ``shared_threads``。"""
        return frozenset({*(t.id for t in self.threads), *self.shared_threads})

    def has_combat(self) -> bool:
        return any(s.kind == "combat" for s in self.solutions)

    @model_validator(mode="after")
    def _check(self) -> EventSkeletonDef:
        problems: list[str] = []
        for label, values in (
            ("locations", self.locations),
            ("weather", self.weather),
            ("npcs", self.npcs),
            ("follows", self.follows),
        ):
            for dup in duplicates(values):
                problems.append(f"{label} 重複：{dup}")
        own = {t.id for t in self.threads}
        problems += [f"follows 不可接自己的線頭 {t}" for t in self.follows if t in own]
        problems += [
            f"shared_threads 不可列自己的線頭 {t}" for t in self.shared_threads if t in own
        ]
        problems += [f"shared_threads 重複：{d}" for d in duplicates(self.shared_threads)]
        allowed = own | set(self.shared_threads)
        for index, solution in enumerate(self.solutions):
            problems += [
                f"第 {index} 個解法的線頭 {t} 不是本骨架的線頭"
                for t in solution.threads
                if t not in allowed
            ]
        if problems:
            raise ValueError(f"事件骨架 {self.id}：{'；'.join(problems)}")
        return self


class EventSkeletonTable(ContentModel):
    """``content/world/events/<region>.yaml``：一區的事件骨架。"""

    region: str = Field(pattern=ID_PATTERN)
    skeletons: tuple[EventSkeletonDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> EventSkeletonTable:
        problems = [f"事件骨架 ID 重複：{d}" for d in duplicates(s.id for s in self.skeletons)]
        numbers = (str(s.number) for s in self.skeletons)
        problems += [f"事件骨架編號重複：{d}" for d in duplicates(numbers)]
        problems += [f"線頭 ID 重複：{d}" for d in duplicates(self.thread_ids())]
        if problems:
            raise ValueError("；".join(problems))
        return self

    def thread_ids(self) -> list[str]:
        """本檔所有線頭 ID（依骨架順序）。"""
        return [t.id for s in self.skeletons for t in s.threads]

    def skeleton_by_id(self) -> dict[str, EventSkeletonDef]:
        return {s.id: s for s in self.skeletons}

    def thread_by_id(self) -> dict[str, ThreadDef]:
        return {t.id: t for s in self.skeletons for t in s.threads}

    def summary(self) -> str:
        threads = len(self.thread_ids())
        return f"{self.region}：{len(self.skeletons)} 個事件骨架、{threads} 種線頭"


# ---------------------------------------------------------------------------
# NPC 人設卡
# ---------------------------------------------------------------------------


_PORTRAIT_HEX = r"^#[0-9a-fA-F]{6}$"


class NpcPortraitLook(ContentModel):
    """NPC 頭像的紙娃娃外觀（Phase 6C-7，``docs/art/NPC頭像.md`` 第 4 節；純顯示，不影響數值）。

    欄位同紙娃娃的 ``look``（``DollLook`` 與種族外觀 ``RaceLook`` 的常用子集，駝峰改底線）。
    地圖上的紙娃娃也用這一份（第 4 節第 5 項）。"""

    skin: str = Field(default="#f1c9a5", pattern=_PORTRAIT_HEX)
    hair: DollHair | None = None
    hair_color: str | None = Field(default=None, pattern=_PORTRAIT_HEX)
    bun_band: str | None = Field(default=None, pattern=_PORTRAIT_HEX)
    beard: bool = False
    tusks: bool | None = None
    """獠牙（獸人；RT-4 鏽牙，同種族外觀的 ``tusks``）。``None``＝沒有（選填，舊資料不用補）。"""
    build: Literal["stout", "tall"] | None = None
    ears: str | None = Field(default=None, pattern=ID_PATTERN)
    horns: str | None = Field(default=None, pattern=ID_PATTERN)
    horn_color: str | None = Field(default=None, pattern=_PORTRAIT_HEX)
    pattern: str | None = Field(default=None, pattern=ID_PATTERN)
    mark_color: str | None = Field(default=None, pattern=_PORTRAIT_HEX)


class NpcPortraitGear(ContentModel):
    """頭像紙娃娃身上的一件外觀（同紙娃娃 ``gear``；``material`` 可省略，前端用布料色）。

    QK-8（#145 身分道具）：``element`` 手持物的元素色（赫琳的火杖）；圍裙寫在 ``waist``
    （``kind: apron``，``trim``＝亮一階的邊）、郵袋寫在 ``back``（``kind: mailbag``）。純顯示，
    道具沒有任何規則效果。"""

    kind: str = Field(pattern=ID_PATTERN)
    material: str | None = Field(default=None, pattern=ID_PATTERN)
    color: str | None = Field(default=None, pattern=_PORTRAIT_HEX)
    trim: str | None = Field(default=None, pattern=_PORTRAIT_HEX)
    element: str | None = Field(default=None, pattern=ID_PATTERN)


NpcPortraitSlot = DollSlot | Literal["main_hand"]
"""頭像紙娃娃的外觀格：紙娃娃的格子再加 ``main_hand``（QK-8 手持物：鎚、弓、杖、拂塵、刀、劍；
地圖紙娃娃畫在主手，頭像不畫主手）。"""


class NpcPortrait(ContentModel):
    """NPC 頭像（6C-7）：``look``、``gear`` 寫法同紙娃娃；``extras`` 是只畫在頭像上的配件
    （斗笠、刀疤……；``fox``＝白狐，不用紙娃娃）。前端不認得的值略過。"""

    look: NpcPortraitLook | None = None
    gear: dict[NpcPortraitSlot, NpcPortraitGear] = Field(default_factory=dict)
    extras: tuple[Annotated[str, Field(pattern=ID_PATTERN)], ...] = Field(default=(), max_length=8)


class NpcCardDef(ContentModel):
    """NPC 人設卡（18.5、#107）。給說書人寫對話與旁白用；不影響數值。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    aliases_zh: AliasesZh = ()
    """用心清單 ② 的關鍵詞別名（``name_zh`` 之外，例：稱謂；Phase 5C-3d）。"""
    role_zh: str = ""
    location: str = Field(pattern=ID_PATTERN)
    """所在地點（本區地點圖的 ID）。"""
    personality_zh: str = Field(min_length=1)
    speech_zh: str = Field(min_length=1)
    secret_zh: str = ""
    """祕密：只給說書人參考，不直接顯示給玩家。"""
    hooks_zh: str = ""
    """和線頭、任務的關係。"""
    portrait: NpcPortrait | None = None
    """頭像與地圖紙娃娃的外觀（6C-7，選填；沒寫＝通用剪影）。"""
    address_zh: str = ""
    """這位 NPC 怎麼稱呼玩家（6R-2，#137；覆寫 ``world/address.yaml`` 的區域稱謂）：模板，只能用
    ``{name}``（玩家角色的名字；長輩口吻叫名字）。空＝照區域。"""

    @model_validator(mode="after")
    def _check_address(self) -> NpcCardDef:
        if self.address_zh:
            problems = address_problems(self.address_zh)
            if problems:
                raise ValueError(f"NPC {self.id}：" + "；".join(problems))
        return self


class NpcCardTable(ContentModel):
    """``content/world/npcs/<region>.yaml``：一區的 NPC 人設卡。"""

    region: str = Field(pattern=ID_PATTERN)
    npcs: tuple[NpcCardDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> NpcCardTable:
        dups = duplicates(n.id for n in self.npcs)
        if dups:
            raise ValueError(f"NPC ID 重複：{'、'.join(dups)}")
        return self

    def npc_by_id(self) -> dict[str, NpcCardDef]:
        return {n.id: n for n in self.npcs}

    def summary(self) -> str:
        return f"{self.region}：{len(self.npcs)} 張 NPC 人設卡"


# ---------------------------------------------------------------------------
# 事件規則
# ---------------------------------------------------------------------------


class EventFrequency(ContentModel):
    """事件出現機率（‰）＝ min(max, per_step ×（距離上次事件的步數））。"""

    per_step_permille: int = Field(ge=0, le=1000)
    max_permille: int = Field(ge=0, le=1000)


class ThreadRules(ContentModel):
    """線頭的上限與到期（9.6.7 #6「每人約 5 條、約 3 天到期」；Q11）。"""

    personal_limit: int = Field(ge=1)
    world_limit: int = Field(ge=1)
    expire_seconds: int = Field(ge=1)
    """到期秒數（現實時間）。"""


class EventRules(ContentModel):
    """``content/world/event_rules.yaml``。"""

    frequency: EventFrequency
    threads: ThreadRules

    def summary(self) -> str:
        f = self.frequency
        t = self.threads
        return (
            f"事件每步 +{f.per_step_permille}‰、上限 {f.max_permille}‰；"
            f"線頭上限 {t.personal_limit}（世界 {t.world_limit}）、"
            f"{t.expire_seconds // 3600} 小時到期"
        )


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


def _location_problems(
    label: str, location: str, world_map: LocationMapDef | None, region: str
) -> list[str]:
    if world_map is None:
        return []
    if location not in world_map.location_by_id():
        return [f"{label}：{region} 沒有地點 {location}"]
    return []


def _thread_problems(
    thread: ThreadDef,
    world_map: LocationMapDef | None,
    npc_ids: frozenset[str],
    region: str,
) -> list[str]:
    out: list[str] = []
    label = f"線頭 {thread.id}"
    if thread.npc is not None and thread.npc not in npc_ids:
        out.append(f"{label}：未知的 NPC {thread.npc}")
    if thread.hints_location is not None and world_map is not None:
        loc = world_map.location_by_id().get(thread.hints_location)
        if loc is None:
            out.append(f"{label}：{region} 沒有地點 {thread.hints_location}")
        elif not loc.hidden or "quest_clue" not in loc.reveal:
            out.append(
                f"{label}：hints_location {loc.id} 必須是可由任務線索（quest_clue）發現的隱藏地點"
            )
    return out


def world_event_problems(
    events: EventSkeletonTable,
    *,
    world_map: LocationMapDef | None,
    npcs: NpcCardTable | None,
    weather_ids: Mapping[str, object],
    thread_ids: Iterable[str],
    keyword_ids: Collection[str] | None = None,
) -> list[str]:
    """事件骨架的跨檔案檢查（地點、天氣、NPC、線頭、機遇關鍵字）。回傳排序過的問題清單。

    ``thread_ids`` 是所有區域的線頭 ID（``follows`` 可以接別區的線頭）；``keyword_ids`` 為
    ``None`` 時不檢查機遇的關鍵字。
    """
    region = events.region
    problems: list[str] = []
    if world_map is None:
        problems.append(f"事件骨架 {region}：沒有 {region} 的地點圖")
    npc_ids = frozenset() if npcs is None else frozenset(npcs.npc_by_id())
    known_threads = frozenset(thread_ids)
    for skeleton in events.skeletons:
        label = f"事件骨架 {skeleton.id}"
        for location in skeleton.locations:
            problems += _location_problems(label, location, world_map, region)
        problems += [f"{label}：未知的天氣 {w}" for w in skeleton.weather if w not in weather_ids]
        problems += [f"{label}：未知的 NPC {n}" for n in skeleton.npcs if n not in npc_ids]
        problems += [
            f"{label}：follows 是未知的線頭 {t}" for t in skeleton.follows if t not in known_threads
        ]
        problems += [
            f"{label}：shared_threads 是未知的線頭 {t}"
            for t in skeleton.shared_threads
            if t not in known_threads
        ]
        problems += [
            f"{label}：waive_thread 是未知的線頭 {s.waive_thread}"
            for s in skeleton.solutions
            if s.waive_thread is not None and s.waive_thread not in known_threads
        ]
        problems += _town_problems(label, skeleton, world_map)
        for thread in skeleton.threads:
            problems += _thread_problems(thread, world_map, npc_ids, region)
        if keyword_ids is not None:
            problems += [
                f"{label}：未知的關鍵字 {s.requires_keyword}"
                for s in skeleton.solutions
                if s.requires_keyword is not None and s.requires_keyword not in keyword_ids
            ]
    return sorted(problems)


def _town_problems(
    label: str, skeleton: EventSkeletonDef, world_map: LocationMapDef | None
) -> list[str]:
    """城鎮是安全區（玩法 PM 定，5B-4b）：有戰鬥解法的骨架不在城鎮出現。"""
    if world_map is None or not skeleton.has_combat():
        return []
    places = world_map.location_by_id()
    return [
        f"{label}：有戰鬥解法，不能出現在城鎮 {loc}"
        for loc in skeleton.locations
        if loc in places and places[loc].kind == "town"
    ]


def npc_card_problems(npcs: NpcCardTable, *, world_map: LocationMapDef | None) -> list[str]:
    """NPC 人設卡的跨檔案檢查（所在地點）。回傳排序過的問題清單。"""
    if world_map is None:
        return [f"NPC 人設卡 {npcs.region}：沒有 {npcs.region} 的地點圖"]
    problems: list[str] = []
    for npc in npcs.npcs:
        problems += _location_problems(f"NPC {npc.id}", npc.location, world_map, npcs.region)
    return sorted(problems)


# ---------------------------------------------------------------------------
# 載入
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorldEventContent:
    """載入後的事件骨架、NPC 人設卡與事件規則。"""

    events: dict[str, EventSkeletonTable] = field(default_factory=dict)
    npcs: dict[str, NpcCardTable] = field(default_factory=dict)
    rules: EventRules | None = None
    situations: SituationContent = field(default_factory=SituationContent)
    """情境模板與情境規則（Phase 5B-2；``trpg.content.world_situations``）。"""
    story: StoryTemplates | None = None
    """說書人的降級模板與各區語氣（Phase 5B-3；``trpg.content.world_narration``）。"""


def _load_region_dir[M: EventSkeletonTable | NpcCardTable](
    directory: Path, model: type[M]
) -> dict[str, tuple[Path, M]]:
    """載入一區一檔的資料夾（鍵＝``region``；檔名必須等於 ``region``）。"""
    if not directory.is_dir():
        return {}
    result: dict[str, tuple[Path, M]] = {}
    for path in sorted(directory.glob("*.yaml")):
        table = load_content_file(path, model)
        if table.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {table.region!r}）")
        result[table.region] = (path, table)
    return result


def _cross_region_duplicates(
    label: str, items: Iterable[tuple[Path, Iterable[str]]]
) -> tuple[Path, str] | None:
    """跨區重複的 ID：回傳第一個撞到的檔案與訊息。"""
    owner: dict[str, Path] = {}
    for path, ids in items:
        for item_id in ids:
            if item_id in owner and owner[item_id] != path:
                return path, f"{label} {item_id} 和 {owner[item_id].name} 重複"
            owner[item_id] = path
    return None


def load_world_event_content(
    root: Path,
    world_maps: Mapping[str, LocationMapDef],
    weather_ids: Mapping[str, object],
    files: list[tuple[Path, ContentModel]],
    *,
    status_ids: Collection[str] = (),
    enemy_only_ids: Collection[str] = (),
    keyword_ids: Collection[str] | None = None,
    race_ids: Collection[str] | None = None,
    tone_regions: Collection[str] = (),
) -> WorldEventContent:
    """載入 ``world/events/``、``world/npcs/``、``world/event_rules.yaml``，以及情境模板與規則
    （``world/situations/``、``world/situation_rules.yaml``；5B-2）。不存在＝空／``None``。

    ``tone_regions``：地點圖以外也可以寫說書語氣的區域（主城、``regions.yaml`` 還沒有地點圖的區；
    6L-1 C4）。

    跨檔案有問題丟 :class:`~trpg.shared.errors.ContentError`（指出檔案）；載入的檔案加進 ``files``。
    """
    events = _load_region_dir(root / WORLD_EVENTS_DIR, EventSkeletonTable)
    npcs = _load_region_dir(root / WORLD_NPCS_DIR, NpcCardTable)

    dup = _cross_region_duplicates(
        "NPC", ((p, [n.id for n in t.npcs]) for p, t in npcs.values())
    ) or _cross_region_duplicates(
        "事件骨架／線頭",
        ((p, [*(s.id for s in t.skeletons), *t.thread_ids()]) for p, t in events.values()),
    )
    if dup is not None:
        raise ContentError(dup[0], dup[1])

    for region in sorted(npcs):
        npc_path, npc_table = npcs[region]
        problems = npc_card_problems(npc_table, world_map=world_maps.get(region))
        if problems:
            raise ContentError(npc_path, "；".join(problems))
        files.append((npc_path, npc_table))

    all_threads = [t for _, table in events.values() for t in table.thread_ids()]
    for region in sorted(events):
        path, table = events[region]
        problems = world_event_problems(
            table,
            world_map=world_maps.get(region),
            npcs=npcs[region][1] if region in npcs else None,
            weather_ids=weather_ids,
            thread_ids=all_threads,
            keyword_ids=keyword_ids,
        )
        if problems:
            raise ContentError(path, "；".join(problems))
        files.append((path, table))

    rules_path = root / EVENT_RULES_FILE
    rules: EventRules | None = None
    if rules_path.is_file():
        rules = load_content_file(rules_path, EventRules)
        files.append((rules_path, rules))

    event_tables = {r: t for r, (_, t) in sorted(events.items())}
    situations = load_situation_content(
        root,
        events=event_tables,
        world_maps=world_maps,
        status_ids=status_ids,
        race_ids=race_ids,
        files=files,
        enemy_only_ids=enemy_only_ids,
    )
    story_path = root / STORY_TEMPLATES_FILE
    story: StoryTemplates | None = None
    if story_path.is_file():
        story = load_story_templates(story_path, regions={*world_maps, *tone_regions})
        files.append((story_path, story))
    return WorldEventContent(
        events=event_tables,
        npcs={r: t for r, (_, t) in sorted(npcs.items())},
        rules=rules,
        situations=situations,
        story=story,
    )
