"""情境判定的模板、規則與 LLM 提議的 schema（Phase 5B-2；``docs/phases/Phase5計畫.md`` 第 10 節）。

- 情境模板（``content/world/situations/<region>.yaml``）：事件骨架「情境判定」解法的可結算資料
  （``docs/design/09-世界與敘事.md`` 9.6.4）：允許的方法與屬性（2～3 種）、基準 DC、危險度、
  情境弱點（用心清單 ④）、帶來優勢的線頭、成功／部分成功／失敗三段的獎懲表。
- 情境規則（``content/world/situation_rules.yaml``）：方法 12 類與常見屬性、
  10 族 +1（9.6.11 #115）、判定上限（±2、用心 +2、種族 +1）、
  獎勵預算（依地點建議等級）、危險度允許的懲罰。
- LLM 提議（:class:`SituationProposal`）：純資料，``trpg.llm`` 產生、``trpg.world`` 核對（2.3：world
  不匯入 llm）。:func:`proposal_problems` 是不看世界狀態的靜態合法性檢查，兩邊共用。

LLM 只能提議：選允許的屬性與方法、難度 ±2、劣勢、勾用心清單（每項附引擎給的事實編號）。獎懲、
基準 DC、優勢、種族加值都來自資料與引擎狀態（守則 3）。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel, duplicates
from trpg.content.world_map import LocationMapDef
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute

if TYPE_CHECKING:  # 只給型別檢查用（world_events 會匯入本模組）
    from trpg.content.world_events import EventSkeletonTable

__all__ = [
    "ALIAS_MAX_CHARS",
    "ALIAS_MIN_CHARS",
    "CARE_ITEMS",
    "DC_SHIFT_LIMIT",
    "MAX_CARE_CLAIMS",
    "OUTCOMES",
    "PLAYER_TEXT_LIMIT",
    "SITUATION_RULES_FILE",
    "WORLD_SITUATIONS_DIR",
    "AliasesZh",
    "CareClaim",
    "CareItem",
    "CheckRules",
    "DangerDef",
    "MethodDef",
    "Outcome",
    "PenaltyKind",
    "SituationBudget",
    "SituationContent",
    "SituationFact",
    "SituationOutcomeDef",
    "SituationPenalties",
    "SituationProposal",
    "SituationRewards",
    "SituationRules",
    "SituationTemplateDef",
    "SituationTemplateTable",
    "WeaknessDef",
    "default_proposal",
    "load_situation_content",
    "proposal_problems",
    "situation_problems",
]

WORLD_SITUATIONS_DIR: Final = "world/situations"
"""情境模板的資料夾（相對於內容資料夾）；一區一檔，檔名＝``region``。"""
SITUATION_RULES_FILE: Final = "world/situation_rules.yaml"

DC_SHIFT_LIMIT: Final = 2
"""LLM 只能把難度調整在基準 ±2 內（9.6.4，使用者決定；資料只能更嚴、不能放寬）。"""
CARE_LIMIT: Final = 2
"""用心清單最多 +2（9.6.4 #85）。"""
RACE_BONUS_LIMIT: Final = 1
"""種族加值 +1（9.6.4 #89）。"""
MAX_CARE_CLAIMS: Final = 4
"""用心清單只有 4 項（9.6.4 ①～④）；提議最多列 4 筆。"""
PLAYER_TEXT_LIMIT: Final = 500
"""玩家回答的長度上限（字；同 ``trpg.llm.prompts.escape.PLAYER_TEXT_MAX_CHARS``）。"""
FACT_MAX_CHARS: Final = 80
ALIAS_MIN_CHARS: Final = 2
"""用心清單關鍵詞別名的最短長度（5C-3d 代決：單字太容易被順口帶到，至少 2 字）。"""
ALIAS_MAX_CHARS: Final = 20

_MIN_ATTRIBUTES = 2
_MAX_ATTRIBUTES = 3
_MAX_METHODS = 3
_DANGER_LEVELS = (1, 2, 3)

CareItem = Literal[
    "clue",  # ① 用到自己查到的線索（持有的有效線頭）
    "npc_bond",  # ② 用到 NPC 的喜好或過去互動
    "exchange",  # ③ 提出拿得出來的交換條件
    "weakness",  # ④ 方法針對情境弱點
]
CARE_ITEMS: Final[tuple[CareItem, ...]] = ("clue", "npc_bond", "exchange", "weakness")

PenaltyKind = Literal["supplies", "debuff", "hurt", "reinforce"]
"""懲罰種類（9.6.4：輕的是失去補給、下一場戰鬥帶 debuff，最重到受傷或敵人增援）。"""

_Id = Annotated[str, Field(pattern=ID_PATTERN)]
AliasesZh = tuple[
    Annotated[str, Field(min_length=ALIAS_MIN_CHARS, max_length=ALIAS_MAX_CHARS)], ...
]
"""用心清單的關鍵詞別名（Phase 5C-3d）：玩家原文含其中任一個（完全字串包含）就算提到這筆事實。"""


# ---------------------------------------------------------------------------
# 規則
# ---------------------------------------------------------------------------


class MethodDef(ContentModel):
    """方法分類（9.6.11 #115）與常見屬性。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    attributes: tuple[Attribute, ...] = Field(min_length=1, max_length=2)


class CheckRules(ContentModel):
    """判定的上限（不可超過 9.6.4 已寫入的決定）。"""

    dc_shift_max: int = Field(ge=0, le=DC_SHIFT_LIMIT)
    partial_margin: int = Field(ge=0, le=20)
    """總值 ≥ DC − ``partial_margin`` 為部分成功。"""
    care_max: int = Field(ge=0, le=CARE_LIMIT)
    race_bonus: int = Field(ge=0, le=RACE_BONUS_LIMIT)


class SituationBudget(ContentModel):
    """獎勵預算（9.6.7 #6「獎勵照地點建議等級的預算表」；07 7.8 經驗來源比例）。"""

    xp_battle_permille: int = Field(ge=0, le=1000)
    """xp 預算＝打贏一場的經驗（``world/rules.yaml`` 的 ``xp``：1 份，隨地點建議等級）× 這個 ‰
    （07 7.8：情境判定成功＝一般戰鬥的 0.5 份）。"""
    supplies_max: int = Field(ge=0)
    threads_max: int = Field(ge=0, le=2)
    """一次事件結果最多留 2 條線頭（9.6.7 #6「0～2 條」）。"""
    buffs_max: int = Field(ge=0)
    reveals_max: int = Field(ge=0)

    def xp_for(self, xp_per_battle: int) -> int:
        """xp 預算（打贏一場給 ``xp_per_battle`` 時）。"""
        return xp_per_battle * self.xp_battle_permille // 1000


class DangerDef(ContentModel):
    """危險度允許的懲罰。"""

    level: int = Field(ge=1, le=3)
    penalties: tuple[PenaltyKind, ...]
    hurt_max_permille: int = Field(ge=0, le=1000)


class SituationRules(ContentModel):
    """``content/world/situation_rules.yaml``。"""

    methods: tuple[MethodDef, ...] = Field(min_length=1)
    race_methods: dict[str, str] = Field(default_factory=dict)
    """種族 → 該族 +1 的方法（9.6.11 #115）。"""
    check: CheckRules
    budget: SituationBudget
    dangers: tuple[DangerDef, ...]
    exchange_supplies: int = Field(ge=1)
    """用心清單 ③ 拿補給當交換條件時花掉的量。"""
    exchange_name_zh: str = Field(default="補給", min_length=1)
    """用心清單 ③ 的事實名稱（關鍵詞；事實文字「拿出 N 份〔名稱〕交換」；5D-R1 從程式移來）。"""
    exchange_aliases_zh: AliasesZh = ()
    """用心清單 ③ 的關鍵詞別名（事實名稱之外；5C-3d）。"""

    @model_validator(mode="after")
    def _check(self) -> SituationRules:
        problems = [f"方法 ID 重複：{d}" for d in duplicates(m.id for m in self.methods)]
        ids = {m.id for m in self.methods}
        problems += [
            f"種族 {race} 的方法 {method} 不存在"
            for race, method in sorted(self.race_methods.items())
            if method not in ids
        ]
        levels = sorted(d.level for d in self.dangers)
        if tuple(levels) != _DANGER_LEVELS:
            problems.append("危險度必須 1～3 各一筆")
        if problems:
            raise ValueError("；".join(problems))
        return self

    def method_by_id(self) -> dict[str, MethodDef]:
        return {m.id: m for m in self.methods}

    def danger(self, level: int) -> DangerDef:
        for danger in self.dangers:
            if danger.level == level:
                return danger
        raise KeyError(level)  # pragma: no cover - 驗證保證 1～3 都有

    def summary(self) -> str:
        c = self.check
        return (
            f"{len(self.methods)} 類方法、{len(self.race_methods)} 族加值；"
            f"難度 ±{c.dc_shift_max}、用心最多 +{c.care_max}、部分成功差 {c.partial_margin} 內"
        )


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------


class SituationRewards(ContentModel):
    """獎勵（9.6.4 公平原則：不給永久戰力；任務幣等 5D-1）。"""

    xp_permille: int = Field(default=0, ge=0, le=1000)
    """乘上地點的等級 xp 預算。"""
    supplies: int = Field(default=0, ge=0)
    threads: tuple[_Id, ...] = ()
    """留下的線頭（必須是本骨架的線頭，或骨架 ``shared_threads`` 列的線頭；5B-4b）。"""
    reveal: tuple[_Id, ...] = ()
    """揭露的隱藏地點（本區、``reveal`` 含 ``situation``）。"""
    buffs: tuple[_Id, ...] = ()
    """下一場戰鬥帶的短期 buff（``statuses.yaml``）。"""


class SituationPenalties(ContentModel):
    """懲罰（依危險度分級）。"""

    supplies: int = Field(default=0, ge=0)
    hurt_permille: int = Field(default=0, ge=0, le=1000)
    """失去最大 HP 的 ‰（最少留 1 HP）。"""
    debuffs: tuple[_Id, ...] = ()
    reinforce: bool = False
    """下一場戰鬥敵人增援。"""

    def kinds(self) -> list[PenaltyKind]:
        out: list[PenaltyKind] = []
        if self.supplies:
            out.append("supplies")
        if self.debuffs:
            out.append("debuff")
        if self.hurt_permille:
            out.append("hurt")
        if self.reinforce:
            out.append("reinforce")
        return out


class SituationOutcomeDef(ContentModel):
    """某個結果段的獎懲。"""

    rewards: SituationRewards = SituationRewards()
    penalties: SituationPenalties = SituationPenalties()


Outcome = Literal["success", "partial", "failure"]
OUTCOMES: Final[tuple[Outcome, ...]] = ("success", "partial", "failure")


class WeaknessDef(ContentModel):
    """情境弱點（用心清單 ④）：提議的方法在 ``methods`` 內才算「針對弱點」。"""

    id: str = Field(pattern=ID_PATTERN)
    text_zh: str = Field(min_length=1)
    methods: tuple[_Id, ...] = Field(min_length=1)
    aliases_zh: AliasesZh = ()
    """玩家原文提到 ``text_zh`` 或其中任一個別名，才可能算「針對弱點」（5C-3d）。"""


class SituationTemplateDef(ContentModel):
    """一個情境模板（骨架的一個情境判定解法）。"""

    id: str = Field(pattern=ID_PATTERN)
    skeleton: str = Field(pattern=ID_PATTERN)
    solution: int = Field(ge=0)
    """骨架 ``solutions`` 的索引（0 起），必須是 ``situation``。"""
    note_zh: str = Field(min_length=1)
    methods: tuple[_Id, ...] = Field(min_length=1, max_length=_MAX_METHODS)
    attributes: tuple[Attribute, ...] = Field(
        min_length=_MIN_ATTRIBUTES, max_length=_MAX_ATTRIBUTES
    )
    """允許的屬性（9.6.4「2～3 種」）；開頭＝骨架解法列的屬性。"""
    base_dc: int = Field(ge=5, le=30)
    danger: int = Field(ge=1, le=3)
    weaknesses: tuple[WeaknessDef, ...] = ()
    advantage_threads: tuple[_Id, ...] = ()
    """持有其中任一有效線頭時判定有優勢（18.4 補充：暗門）。"""
    success: SituationOutcomeDef
    partial: SituationOutcomeDef
    failure: SituationOutcomeDef

    @model_validator(mode="after")
    def _check(self) -> SituationTemplateDef:
        problems: list[str] = []
        for label, values in (
            ("methods", self.methods),
            ("attributes", [a.value for a in self.attributes]),
            ("weaknesses", [w.id for w in self.weaknesses]),
            ("advantage_threads", self.advantage_threads),
        ):
            problems += [f"{label} 重複：{d}" for d in duplicates(values)]
        problems += [
            f"弱點 {w.id} 的方法 {m} 不在模板方法裡"
            for w in self.weaknesses
            for m in w.methods
            if m not in self.methods
        ]
        if problems:
            raise ValueError(f"情境模板 {self.id}：{'；'.join(problems)}")
        return self

    def outcome(self, outcome: Outcome) -> SituationOutcomeDef:
        return {"success": self.success, "partial": self.partial, "failure": self.failure}[outcome]

    def weakness_by_id(self) -> dict[str, WeaknessDef]:
        return {w.id: w for w in self.weaknesses}


class SituationTemplateTable(ContentModel):
    """``content/world/situations/<region>.yaml``：一區的情境模板。"""

    region: str = Field(pattern=ID_PATTERN)
    templates: tuple[SituationTemplateDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> SituationTemplateTable:
        dups = duplicates(t.id for t in self.templates)
        if dups:
            raise ValueError(f"情境模板 ID 重複：{'、'.join(dups)}")
        return self

    def template_by_id(self) -> dict[str, SituationTemplateDef]:
        return {t.id: t for t in self.templates}

    def summary(self) -> str:
        skeletons = len({t.skeleton for t in self.templates})
        return f"{self.region}：{len(self.templates)} 個情境模板（{skeletons} 個骨架）"


# ---------------------------------------------------------------------------
# LLM 提議（純資料；trpg.llm 與 trpg.world 共用）
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CareClaim(_Strict):
    """用心清單的一筆：項目＋引擎給的事實編號（9.6.4「LLM 只輸出清單項目＋事實編號」）。"""

    item: CareItem
    fact: str = Field(min_length=1, max_length=FACT_MAX_CHARS)


class SituationProposal(_Strict):
    """LLM 對一次情境判定的提議（pydantic 驗證；引擎另外檢查合法性）。"""

    attribute: Attribute
    method: str = Field(pattern=ID_PATTERN)
    dc_shift: int = Field(ge=-DC_SHIFT_LIMIT, le=DC_SHIFT_LIMIT)
    disadvantage: bool = False
    """回答明顯行不通時的劣勢（9.6.4）。"""
    care: tuple[CareClaim, ...] = Field(default=(), max_length=MAX_CARE_CLAIMS)


class SituationFact(_Strict):
    """引擎核對得到的一筆事實（給 LLM 挑選、給引擎核對）。"""

    item: CareItem
    fact: str = Field(min_length=1, max_length=FACT_MAX_CHARS)
    text_zh: str


def proposal_problems(
    template: SituationTemplateDef, rules: SituationRules, proposal: SituationProposal
) -> list[str]:
    """不看世界狀態的合法性檢查（屬性、方法、難度、筆數）；回傳問題清單（空＝合法）。"""
    problems: list[str] = []
    if proposal.attribute not in template.attributes:
        allowed = "、".join(a.value for a in template.attributes)
        problems.append(f"屬性 {proposal.attribute.value} 不在允許清單（{allowed}）")
    if proposal.method not in template.methods:
        problems.append(f"方法 {proposal.method} 不在允許清單（{'、'.join(template.methods)}）")
    else:
        method = rules.method_by_id().get(proposal.method)
        if method is None or proposal.attribute not in method.attributes:
            problems.append(f"方法 {proposal.method} 不能用屬性 {proposal.attribute.value}")
    if abs(proposal.dc_shift) > rules.check.dc_shift_max:
        problems.append(f"難度調整 {proposal.dc_shift} 超過 ±{rules.check.dc_shift_max}")
    if len(proposal.care) > MAX_CARE_CLAIMS:
        problems.append(f"用心清單最多 {MAX_CARE_CLAIMS} 筆")  # pragma: no cover - schema 已擋
    return problems


def default_proposal(template: SituationTemplateDef, rules: SituationRules) -> SituationProposal:
    """降級提議（LLM 連不上或提議一直不合法）：第一個屬性、能用它的第一個模板方法、±0、不勾清單。"""
    methods = rules.method_by_id()
    attribute = template.attributes[0]
    method = next(
        (m for m in template.methods if m in methods and attribute in methods[m].attributes),
        template.methods[0],
    )
    return SituationProposal(attribute=attribute, method=method, dc_shift=0)


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


def _template_shape_problems(
    template: SituationTemplateDef, rules: SituationRules, skeletons: EventSkeletonTable | None
) -> list[str]:
    label = f"情境模板 {template.id}"
    out: list[str] = []
    methods = rules.method_by_id()
    unknown = [m for m in template.methods if m not in methods]
    out += [f"{label}：未知的方法 {m}" for m in unknown]
    known = [methods[m] for m in template.methods if m in methods]
    for attribute in template.attributes:
        if not any(attribute in m.attributes for m in known):
            out.append(f"{label}：屬性 {attribute.value} 沒有模板方法能用")
    for method in known:
        if not any(a in template.attributes for a in method.attributes):
            out.append(f"{label}：方法 {method.id} 的常見屬性都不在模板屬性裡")
    if skeletons is None:
        return out
    skeleton = skeletons.skeleton_by_id().get(template.skeleton)
    if skeleton is None:
        return [*out, f"{label}：{skeletons.region} 沒有事件骨架 {template.skeleton}"]
    if template.solution >= len(skeleton.solutions):
        return [*out, f"{label}：骨架 {skeleton.id} 沒有第 {template.solution} 個解法"]
    solution = skeleton.solutions[template.solution]
    if solution.kind != "situation":
        out.append(f"{label}：骨架 {skeleton.id} 的第 {template.solution} 個解法不是情境判定")
    elif template.attributes[: len(solution.attributes)] != solution.attributes:
        out.append(f"{label}：模板屬性的開頭必須是骨架解法的屬性")
    own_threads = {t.id for t in skeleton.threads} | set(skeleton.shared_threads)
    for outcome in OUTCOMES:
        out += [
            f"{label}：{outcome} 的線頭 {t} 不是骨架 {skeleton.id} 的線頭"
            for t in template.outcome(outcome).rewards.threads
            if t not in own_threads
        ]
    return out


def _outcome_problems(
    template: SituationTemplateDef,
    rules: SituationRules,
    world_map: LocationMapDef | None,
    status_ids: Collection[str],
    enemy_only_ids: Collection[str] = (),
) -> list[str]:
    label = f"情境模板 {template.id}"
    budget = rules.budget
    danger = rules.danger(template.danger)
    locations = {} if world_map is None else world_map.location_by_id()
    out: list[str] = []
    for name in OUTCOMES:
        outcome = template.outcome(name)
        rew, pen = outcome.rewards, outcome.penalties
        where = f"{label} {name}"
        for value, cap, what in (
            (rew.supplies, budget.supplies_max, "補給"),
            (len(rew.threads), budget.threads_max, "線頭"),
            (len(rew.buffs), budget.buffs_max, "buff"),
            (len(rew.reveal), budget.reveals_max, "揭露地點"),
        ):
            if value > cap:
                out.append(f"{where}：{what} {value} 超過預算 {cap}")
        statuses = (*rew.buffs, *pen.debuffs)
        out += [f"{where}：未知的狀態 {s}" for s in statuses if s not in status_ids]
        # 06 6.35（5F-R2）：世界事件的效果不能引用只給敵人的狀態
        out += [
            f"{where}：狀態 {s} 只給敵人（enemy_only）" for s in statuses if s in enemy_only_ids
        ]
        for loc_id in rew.reveal:
            loc = locations.get(loc_id)
            if loc is None or not loc.hidden or "situation" not in loc.reveal:
                out.append(f"{where}：{loc_id} 不是可由情境判定揭露的隱藏地點")
        out += [
            f"{where}：危險度 {template.danger} 不允許懲罰 {k}"
            for k in pen.kinds()
            if k not in danger.penalties
        ]
        if pen.hurt_permille > danger.hurt_max_permille:
            out.append(f"{where}：受傷 {pen.hurt_permille}‰ 超過上限 {danger.hurt_max_permille}‰")
    return out


def situation_problems(
    table: SituationTemplateTable,
    *,
    rules: SituationRules | None,
    events: EventSkeletonTable | None,
    world_map: LocationMapDef | None,
    status_ids: Collection[str],
    thread_ids: Collection[str],
    enemy_only_ids: Collection[str] = (),
) -> list[str]:
    """情境模板的跨檔案檢查（骨架、解法、方法、線頭、地點、狀態、預算、危險度）。排序後回傳。

    ``enemy_only_ids``：只給敵人的狀態（06 6.35，5F-R2）；buff／debuff 引用它們算資料錯誤。"""
    region = table.region
    if rules is None:
        return [f"情境模板 {region}：沒有 {SITUATION_RULES_FILE}"]
    problems: list[str] = []
    if events is None:
        problems.append(f"情境模板 {region}：沒有 {region} 的事件骨架")
    for template in table.templates:
        problems += _template_shape_problems(template, rules, events)
        problems += _outcome_problems(template, rules, world_map, status_ids, enemy_only_ids)
        problems += [
            f"情境模板 {template.id}：advantage_threads 是未知的線頭 {t}"
            for t in template.advantage_threads
            if t not in thread_ids
        ]
    return sorted(problems)


def _rules_problems(rules: SituationRules, race_ids: Collection[str] | None) -> list[str]:
    if race_ids is None:
        return []
    return [f"未知的種族 {r}" for r in sorted(rules.race_methods) if r not in race_ids]


# ---------------------------------------------------------------------------
# 載入
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SituationContent:
    """載入後的情境模板與規則。"""

    templates: dict[str, SituationTemplateTable] = field(default_factory=dict)
    rules: SituationRules | None = None


def load_situation_content(
    root: Path,
    *,
    events: Mapping[str, EventSkeletonTable],
    world_maps: Mapping[str, LocationMapDef],
    status_ids: Collection[str],
    race_ids: Collection[str] | None,
    files: list[tuple[Path, ContentModel]],
    enemy_only_ids: Collection[str] = (),
) -> SituationContent:
    """載入 ``world/situation_rules.yaml`` 與 ``world/situations/``（不存在＝``None``／空）。"""
    rules_path = root / SITUATION_RULES_FILE
    rules: SituationRules | None = None
    if rules_path.is_file():
        rules = load_content_file(rules_path, SituationRules)
        problems = _rules_problems(rules, race_ids)
        if problems:
            raise ContentError(rules_path, "；".join(problems))
        files.append((rules_path, rules))

    directory = root / WORLD_SITUATIONS_DIR
    tables: dict[str, SituationTemplateTable] = {}
    owner: dict[str, Path] = {}
    thread_ids = frozenset(t for table in events.values() for t in table.thread_ids())
    for path in sorted(directory.glob("*.yaml")) if directory.is_dir() else []:
        table = load_content_file(path, SituationTemplateTable)
        if table.region != path.stem:
            raise ContentError(path, f"檔名必須與 region 相同（region 為 {table.region!r}）")
        for template in table.templates:
            if template.id in owner:
                other = owner[template.id].name
                raise ContentError(path, f"情境模板 {template.id} 和 {other} 重複")
            owner[template.id] = path
        problems = situation_problems(
            table,
            rules=rules,
            events=events.get(table.region),
            world_map=world_maps.get(table.region),
            status_ids=status_ids,
            thread_ids=thread_ids,
            enemy_only_ids=enemy_only_ids,
        )
        if problems:
            raise ContentError(path, "；".join(problems))
        files.append((path, table))
        tables[table.region] = table
    return SituationContent(templates=dict(sorted(tables.items())), rules=rules)
