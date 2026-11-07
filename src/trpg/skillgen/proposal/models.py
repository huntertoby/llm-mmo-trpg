"""提議模型的資料型別與共用小工具：常數、:class:`ProposalError`、:class:`ProposalContext`、
:class:`ProposalResult`、:class:`ProposalModels`、pydantic 型別組合函式。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeAliasType, Union, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
)

from trpg.content.battle import ID_PATTERN
from trpg.content.skills import (
    CONSUME_THEN_TYPES,
    GAMBLE_BRANCH_TYPES,
    ON_KILL_TYPES,
    ZONE_EFFECT_TYPES,
    Origin,
    SkillDef,
    SkillRarity,
)
from trpg.shared.types import Attribute

LLM_ID_PREFIX = "skill_llm_"


PROPOSAL_KINDS: tuple[str, ...] = ("active", "passive", "stance", "reaction")
"""開放提議的技能種類（反應技 Phase 4-L8 開放，帶 ``reaction``；修正型需要 ``modifiers``，
不開放）。"""


CLOSED_SKELETONS: frozenset[str] = frozenset({"modifier", "trap"})
"""不開放的骨架（需要提議模型沒有的欄位：修正規則、陷阱設定）。"""


NESTED_EFFECT_TYPES: dict[str, tuple[str, ...]] = {
    "then": CONSUME_THEN_TYPES,
    "win": GAMBLE_BRANCH_TYPES,
    "lose": GAMBLE_BRANCH_TYPES,
    "on_kill": ON_KILL_TYPES,
    "effects": ZONE_EFFECT_TYPES,
}
"""巢狀效果參數（``type: effects``）可用的效果類型；其中不是原語的類型（``refund_ap``、
``damage_multiplier`` 等）是只能巢狀的效果（Phase 4-L8b，``skill_primitives.yaml`` 的
``nested_only_effects``，父結構以 YAML 的 ``parents`` 為準）。"""


_MAX_NESTED = 2


_MAX_VARIANTS = 2


_MAX_TAGS = 8


# 提議中「由呼叫端或引擎決定、LLM 不能填」的 SkillDef 欄位（文件化用；模型本來就沒有這些欄位）。
CALLER_FIELDS: tuple[str, ...] = ("id", "tier", "rank", "rarity", "provenance", "schema_version")


type Stage = Literal["proposal", "skill", "rules"]


class _Proposal(BaseModel):
    """提議模型的基底：拼錯或多填的欄位一律報錯（錯誤可定位）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True, slots=True)
class ProposalError:
    """給 LLM 的一條結構化錯誤。

    - ``stage``：``proposal``（提議格式）、``skill``（轉成技能時的 schema 檢查）、``rules``（跨檔案
      驗證、預算與骨架規則）。
    - ``path``：出錯的 JSON 路徑（例如 ``effects[1].dice``；技能層級為空字串）。
    - ``code``：穩定的英文代碼（pydantic 錯誤型別或驗證器的規則代碼，例如 ``budget.over``）。
    - ``message``：繁體中文原因。
    - ``allowed``：可用值（列舉型錯誤才有）。
    """

    stage: Stage
    path: str
    code: str
    message: str
    allowed: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "stage": self.stage,
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }
        if self.allowed:
            data["allowed"] = list(self.allowed)
        return data


@dataclass(frozen=True, slots=True)
class ProposalContext:
    """呼叫端決定的欄位（LLM 不能填）：階級、稀有度、等級、來源。

    ``hero_attributes``（Phase 3H-3，07 7.2）：給主角的屬性時，技能的縮放屬性由引擎改成其中最高的、
    且在 ``skill_scaling.yaml`` 允許範圍內的屬性（LLM 填的 ``scaling_attr`` 只是提議，會被取代；
    ID 以取代後的內容雜湊）。沒有給時（3H-7）LLM 填的屬性在允許範圍內就保留，否則取範圍裡第一個；
    第二屬性同樣限在範圍內。"""

    tier: int
    rarity: SkillRarity
    rank: int = 1
    origin: Origin = "level_up"
    hero_attributes: Mapping[Attribute, int] | None = None
    held: Mapping[str, str] | None = None
    """主角手上的主手武器與副手（ID → 中文名；Phase 3I-5）。有值時，提議的「手持某種武器時」
    條件只能指定這些裝備（否則加成永遠不會成立）；``None`` ＝ 不檢查。"""
    keywords: tuple[str, ...] = ()
    """題目的關鍵字（Phase 4-L6）：技能（依專屬規則推導）必須全部帶到，否則
    ``keyword.required``。"""
    core_primitive: str | None = None
    """題目指定的核心原語（Phase 4-L6）：技能的效果必須用到它，否則 ``core.required``。"""
    weapon_class: str | None = None
    """主角的武器大類（``melee``／``ranged``／``focus``；Phase 4-L6）：技能的武器需求必須與它相容
    （含 ``held``），否則 ``weapon.incompatible``，讓模型重提而不是白白浪費這個候選。"""


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """:func:`evaluate_proposal` 的結果：``skill`` 為 ``None`` 時 ``errors`` 不為空。"""

    skill: SkillDef | None
    errors: tuple[ProposalError, ...]

    @property
    def ok(self) -> bool:
        return self.skill is not None and not self.errors


@dataclass(frozen=True, slots=True)
class ProposalModels:
    """由內容庫產生的提議模型。``skill`` 是頂層型別（只有一個版型時是模型本身，否則是以 ``layout``
    區分的 union）；``excluded_primitives`` 是沒有開放或限制用途的原語（與原因）；``layouts`` 是版型
    （ID、中文說明）。"""

    skill: Any
    primitive_ids: tuple[str, ...]
    variant_primitive_ids: tuple[str, ...]
    excluded_primitives: tuple[tuple[str, str], ...]
    layouts: tuple[tuple[str, str], ...] = ()
    kinds: tuple[tuple[str, tuple[str, ...]], ...] = ()
    """各版型可選的技能種類（錯誤回饋的可用值用；4-L10a）。"""

    def json_schema(self) -> dict[str, Any]:
        """給 LLM（structured output／tool input schema）的 JSON Schema。

        只影響說明、不影響「哪些 JSON 合法」的註記關鍵字（pydantic 自動產生的 ``title``、與
        ``oneOf`` 重複的 OpenAPI ``discriminator`` 對照表、``default``）去掉以縮小 schema
        （Phase 4-L5b；約束解碼不使用它們）。驗證一律用 pydantic 模型本身，不看這份 schema。"""
        schema: dict[str, Any] = _compact(TypeAdapter(self.skill).json_schema())
        return schema


_ANNOTATION_KEYS = frozenset({"title", "discriminator", "default"})
""":func:`_compact` 去掉的註記關鍵字。"""


def _compact(node: Any) -> Any:
    """遞迴去掉 schema 節點上的 :data:`_ANNOTATION_KEYS`；``properties``／``$defs`` 的鍵是欄位名或
    定義名，不去。"""
    if isinstance(node, list):
        return [_compact(v) for v in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _ANNOTATION_KEYS:
            continue
        if key in ("properties", "$defs") and isinstance(value, dict):
            out[key] = {name: _compact(sub) for name, sub in value.items()}
        else:
            out[key] = _compact(value)
    return out


def _literal(values: Iterable[object]) -> Any:
    lit: Any = Literal
    return lit[tuple(values)]


def _list_of(item: Any) -> Any:
    return list[item]


def _union(models: Sequence[Any], discriminator: str) -> Any:
    if not models:
        raise ValueError("提議模型沒有任何可用的類型（篩選後的原語清單是空的）")
    if len(models) == 1:
        return models[0]
    return Annotated[Union[tuple(models)], Field(discriminator=discriminator)]  # noqa: UP007


def _strip_none(annotation: Any) -> Any:
    args = [a for a in get_args(annotation) if a is not type(None)]
    if not args:
        return annotation
    return args[0] if len(args) == 1 else Union[tuple(args)]  # noqa: UP007


def _id_choice(ids: Iterable[str], pattern: str = ID_PATTERN) -> tuple[Any, dict[str, Any]]:
    values = sorted(ids)
    if not values:
        return str, {"pattern": pattern}
    return _literal(values), {}


def _get(value: Any, key: str) -> Any:
    """dict 或模型的欄位值（判別函式用）。"""
    return value.get(key) if isinstance(value, dict) else getattr(value, key, None)


_GENERAL_TAG = "~general"
"""版型的效果 union 中「一般原語」那一支的標籤（不是原語 ID；錯誤路徑會略過它）。"""


def _alias(name: str, annotation: Any) -> Any:
    """具名的型別（JSON Schema 中只出現一次、各處以 ``$ref`` 引用）；``None`` 原樣回傳。"""
    if annotation is None:
        return None
    return TypeAliasType(name, annotation)


def _union_or_none(models: Sequence[Any]) -> Any:
    return _union(models, "type") if models else None
