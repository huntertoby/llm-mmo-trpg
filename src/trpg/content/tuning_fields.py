"""數值工坊的欄位白名單（``content/tuning_fields.yaml``；Phase NW-1a）。

- 只由 ``trpg.api.tuning`` 讀；**不登記進** ``KNOWN_CONTENT_FILES``、不進 ``library.files``，所以改
  這份不會改內容 digest（``content_digest``、``ruleset_hash``、``hash_ruleset``）。
- 欄位路徑：點號分段，``name[*]`` 是清單的每一項，例 ``phases[*].trigger.permille``；具體的路徑把
  ``*`` 換成索引，例 ``phases[1].trigger.permille``（:func:`parse_path`）。
- 載入檢查（:func:`tuning_field_problems`）：每個路徑都對得到對象 schema 的整數欄位、禁止表
  （:data:`BUILTIN_FORBIDDEN` ∪ 檔內 ``forbidden_files``）的檔不能被對象的 ``glob`` 選到、不開 ID／
  ``*_zh``／外觀欄位、同一對象的路徑不重複。
"""

from __future__ import annotations

import fnmatch
import re
import types
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Final, Literal, TypeAliasType, Union, get_args, get_origin

from pydantic import BaseModel, Field

from trpg.content.battle import Dice, UnitTemplate
from trpg.content.environment import AiProfileTable
from trpg.content.loader import load_content_file
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel
from trpg.content.skill_rules import BudgetRules
from trpg.content.skills import SkillDef
from trpg.content.skills.constants import ON_KILL_TYPES
from trpg.content.skills.primitives import PrimitiveTable
from trpg.shared.errors import ContentError

__all__ = [
    "BUILTIN_FORBIDDEN",
    "FORBIDDEN_SEGMENTS",
    "SKILL_KINDS",
    "TABLE_KINDS",
    "TARGET_MODELS",
    "TUNING_FIELDS_FILE",
    "FieldKind",
    "PathPart",
    "TuningField",
    "TuningFields",
    "TuningTarget",
    "effect_type_ids",
    "format_path",
    "load_tuning_fields",
    "parse_path",
    "path_matches",
    "target_files",
    "tuning_field_problems",
]

TUNING_FIELDS_FILE: Final = "tuning_fields.yaml"

BUILTIN_FORBIDDEN: Final = (
    "skill_primitives.yaml",
    "skill_shapes.yaml",
    "modifier_changes.yaml",
    "llm/*.yaml",
    "rules/hit_table.yaml",
    "skill_icon_*.yaml",
    TUNING_FIELDS_FILE,
)
"""程式固定的禁止表（NW 第 3 節「一律不開」）：schema 匯入時從固定資料夾讀的檔（草稿看不到）、
產生的命中表、美術 PM 維護的圖示表、白名單本身。"""

FORBIDDEN_SEGMENTS: Final = frozenset(
    {
        "id",
        "doll",
        "look",
        "look_range",
        "tags",
        "weapon",
        # 技能的非數值欄位（NW-2 規格 3.2）
        "type",
        "kind",
        "affects",
        "status",
        "surface",
        "object",
        "element",
        "tier",
        "rank",
        "rarity",
        "skeleton",
        "category",
        "weapon_req",
        "weapon_only",
        "scaling_attr",
        "secondary_scaling_attr",
        "mastery",
        "enemy_only",
        "pool_regions",
        "icon_prop",
        "budget_bonus_permille",
        "activation",
        "exclusive_group",
        "pierce",
        "include_caster",
        "when",
        "anchor",
        "release",
        "count",
        "modifiers",
        "narrative",
        "provenance",
    }
)
"""路徑中不能出現的欄位名（ID、外觀、引用、技能的非數值欄位）；另外 ``*_zh`` 一律不開。"""

TARGET_MODELS: Final[dict[str, type[BaseModel]]] = {
    "unit": UnitTemplate,
    "skill": SkillDef,
    "ai": AiProfileTable,
    "rules": CoreRules,
    "budget": BudgetRules,
}
"""對象種類 → 單一檔案的 schema（``ai``＝``ai_profiles.yaml``；PB-1n 先開部位的 ``parts:``；
BS-1 起 ``rules``＝``rules/core.yaml``（背刺與潛行偷襲的加成）、``budget``＝``skill_budget.yaml``
（無聲的預算成本）。``ai``、``rules``、``budget`` 都是「一個檔一個全體共用的表」）。"""

TABLE_KINDS: Final = ("ai", "rules", "budget")
"""一個檔就是一張全體共用的表（不是一隻單位或一招）的對象種類。"""

SKILL_KINDS: Final = ("active", "reaction", "passive", "stance", "modifier")
"""``TuningField.kinds`` 可填的技能種類（``SkillKind``）。"""

type FieldKind = Literal["int", "permille", "dice", "range", "skill_ids"]

_SEGMENT = re.compile(r"^([a-z_][a-z0-9_]*)(?:\[(\*|\d+)\])?$")

type PathPart = str | int
"""具體路徑的一段：鍵（字串）或清單索引（整數）。"""


class TuningField(ContentModel):
    """一個可改的欄位。"""

    path: str = Field(pattern=r"^[a-z_][a-z0-9_]*(\[\*\])?(\.[a-z_][a-z0-9_]*(\[\*\])?)*$")
    label_zh: str = Field(min_length=1)
    kind: FieldKind
    """``int``／``permille``：整數；``dice``：``NdM`` 字串；``range``：整數射程（現值是 ``weapon``
    時唯讀）；``skill_ids``：技能 ID 清單（NW-2 T2）。"""
    hint_min: int | None = None
    hint_max: int | None = None
    note_zh: str = Field(min_length=1)
    effect_types: tuple[str, ...] = ()
    """只展開到 ``type`` 在這份清單內的效果（NW-2 T1；空＝不篩）。效果＝路徑上最深、而且有
    ``type`` 鍵的那一層（例 ``effects[0].scaling.cap_permille`` 的 ``effects[0]``）。"""
    existing_only: bool = False
    """只有已寫的才展開（沒寫時不給插入：插入會讓沒有該機制的招多一個機制，屬結構）。"""
    kinds: tuple[str, ...] = ()
    """只展開給這些技能種類（``kind``；沒寫＝``active``）；空＝不篩。"""


class TuningTarget(ContentModel):
    """一類對象：``glob`` 選到的每個檔是一個對象（檔名＝對象 ID）。"""

    kind: Literal["unit", "skill", "ai", "rules", "budget"]
    label_zh: str = Field(min_length=1)
    glob: str = Field(min_length=1)
    exclude: tuple[str, ...] = ()
    """不開的對象 ID（``fnmatch`` 萬用字元）。"""
    fields: tuple[TuningField, ...] = Field(min_length=1)
    effect_sites: tuple[str, ...] = ()
    """效果所在的位置（例 ``effects[*]``、``followup.effects[*]``、``variants[*].add_effect``）；
    和 :attr:`effect_fields` 交叉成完整路徑（:meth:`all_fields`）。巢狀位置一律寫在這裡。"""
    effect_fields: tuple[TuningField, ...] = ()
    """效果層級的欄位（``path`` 相對效果，例 ``dice``、``scaling.cap_permille``）。"""

    @cached_property
    def _all(self) -> tuple[TuningField, ...]:
        crossed = tuple(
            item.model_copy(update={"path": f"{site}.{item.path}"})
            for site in self.effect_sites
            for item in self.effect_fields
        )
        return (*self.fields, *crossed)

    def all_fields(self) -> tuple[TuningField, ...]:
        """``fields`` ＋ ``effect_sites`` × ``effect_fields``（位置在外層、欄位在內層；同一個物件
        每次回傳同一組）。"""
        return self._all

    def field_for(self, path: str) -> TuningField | None:
        """具體路徑對到的白名單欄位（``phases[1].trigger.permille`` → ``phases[*]…``）。"""
        for item in self.all_fields():
            if path_matches(item.path, path):
                return item
        return None


class TuningFields(ContentModel):
    """``content/tuning_fields.yaml``。"""

    forbidden_files: tuple[str, ...] = ()
    targets: tuple[TuningTarget, ...] = Field(min_length=1)

    def target(self, kind: str) -> TuningTarget | None:
        return next((t for t in self.targets if t.kind == kind), None)

    def summary(self) -> str:
        count = sum(len(t.all_fields()) for t in self.targets)
        return f"{len(self.targets)} 類對象、{count} 個欄位"


def parse_path(path: str) -> tuple[PathPart, ...]:
    """``phases[1].trigger.permille`` → ``("phases", 1, "trigger", "permille")``；``[*]`` 保留成
    字串 ``"*"``。格式不對拋 ``ValueError``。"""
    parts: list[PathPart] = []
    for segment in path.split("."):
        match = _SEGMENT.match(segment)
        if match is None:
            raise ValueError(f"欄位路徑格式不對：{path}")
        parts.append(match.group(1))
        index = match.group(2)
        if index is not None:
            parts.append("*" if index == "*" else int(index))
    return tuple(parts)


def format_path(parts: Sequence[PathPart]) -> str:
    """:func:`parse_path` 的反向。"""
    out = ""
    for part in parts:
        if isinstance(part, int) or part == "*":
            out += f"[{part}]"
        else:
            out += f".{part}" if out else part
    return out


def path_matches(pattern: str, path: str) -> bool:
    """具體路徑是否對到白名單的路徑（``*`` 對任何索引）。"""
    try:
        want, have = parse_path(pattern), parse_path(path)
    except ValueError:
        return False
    if len(want) != len(have):
        return False
    return all(
        w == h or (w == "*" and isinstance(h, int) and not isinstance(h, bool))
        for w, h in zip(want, have, strict=True)
    )


def _unwrap(tp: Any) -> list[Any]:
    """拆掉型別別名、``Annotated``、聯集與 ``None``，回傳候選型別。"""
    if isinstance(tp, TypeAliasType):
        return _unwrap(tp.__value__)
    origin = get_origin(tp)
    if origin is Annotated:
        return _unwrap(get_args(tp)[0])
    if origin is Union or isinstance(tp, types.UnionType):
        return [t for arg in get_args(tp) for t in _unwrap(arg) if t is not type(None)]
    return [tp]


def _step(candidates: list[Any], part: PathPart) -> list[Any]:
    out: list[Any] = []
    for tp in candidates:
        origin = get_origin(tp)
        if isinstance(part, str) and part != "*":
            if isinstance(tp, type) and issubclass(tp, BaseModel):
                info = tp.model_fields.get(part)
                if info is not None:
                    out += _unwrap(info.annotation)
            elif origin is dict:
                key_type, value_type = get_args(tp)
                if _key_ok(key_type, part):
                    out += _unwrap(value_type)
        elif origin in (tuple, list):
            out += _unwrap(get_args(tp)[0])
    return out


def _key_ok(key_type: Any, key: str) -> bool:
    if key_type is str:
        return True
    try:
        key_type(key)
    except (TypeError, ValueError):
        return False
    return True


def _is_id_tuple(tp: Any) -> bool:
    return get_origin(tp) in (tuple, list) and _unwrap(get_args(tp)[0]) == [str]


def _leaf_ok(model: type[BaseModel], parts: Sequence[PathPart], kind: str = "int") -> bool:
    """路徑對得到 schema，而且葉節點的型別合 ``kind``（NW-2 5.1）。"""
    candidates: list[Any] = [model]
    for part in parts:
        candidates = _step(candidates, part)
        if not candidates:
            return False
    if kind == "dice":
        return any(t is Dice for t in candidates)
    if kind == "skill_ids":
        return any(_is_id_tuple(t) for t in candidates)
    return any(t is int for t in candidates)


def effect_type_ids(content_dir: Path) -> set[str]:
    """``effect_types`` 可填的值：``skill_primitives.yaml`` 的原語與只能巢狀的效果，加上
    ``on_kill`` 專用的效果（``refund_ap``…）。"""
    table = load_content_file(content_dir / "skill_primitives.yaml", PrimitiveTable)
    ids = {p.id for p in table.primitives} | {p.id for p in table.nested_only_effects}
    return ids | set(ON_KILL_TYPES)


def target_files(content_dir: Path, target: TuningTarget) -> list[Path]:
    """對象的檔（依檔名排序；去掉 ``exclude``）。"""
    return [
        p
        for p in sorted(content_dir.glob(target.glob))
        if p.is_file() and not any(fnmatch.fnmatchcase(p.stem, x) for x in target.exclude)
    ]


def _forbidden(rel: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(rel, pattern) for pattern in patterns)


def tuning_field_problems(table: TuningFields, content_dir: Path | None = None) -> list[str]:
    """白名單的問題（空列表＝沒問題）。給了 ``content_dir`` 時另檢查對象的檔不在禁止表內。"""
    problems: list[str] = []
    forbidden = (*BUILTIN_FORBIDDEN, *table.forbidden_files)
    kinds = [t.kind for t in table.targets]
    if len(set(kinds)) != len(kinds):
        problems.append("targets 的 kind 不能重複")
    has_types = any(f.effect_types for t in table.targets for f in t.all_fields())
    known_types = effect_type_ids(content_dir) if content_dir is not None and has_types else None
    for target in table.targets:
        model = TARGET_MODELS[target.kind]
        if _forbidden(target.glob, forbidden):
            problems.append(f"{target.kind}：{target.glob} 在禁止表內")
        if content_dir is not None:
            for path in target_files(content_dir, target):
                rel = path.relative_to(content_dir).as_posix()
                if _forbidden(rel, forbidden):
                    problems.append(f"{target.kind}：{rel} 在禁止表內")
        seen: set[str] = set()
        for item in target.all_fields():
            if item.path in seen:
                problems.append(f"{target.kind}：欄位 {item.path} 重複")
            seen.add(item.path)
            problems += [f"{target.kind}：{p}" for p in _field_problems(model, item, known_types)]
    return problems


_KIND_ZH: Final = {
    "int": "整數",
    "permille": "整數",
    "range": "整數",
    "dice": "骰子",
    "skill_ids": "ID 清單",
}


def _field_problems(
    model: type[BaseModel], item: TuningField, known_types: set[str] | None
) -> list[str]:
    problems: list[str] = []
    parts = parse_path(item.path)
    names = [p for p in parts if isinstance(p, str) and p != "*"]
    if any(n in FORBIDDEN_SEGMENTS or n.endswith("_zh") for n in names):
        problems.append(f"欄位 {item.path} 不開（ID、文字、外觀或技能結構）")
    elif not _leaf_ok(model, parts, item.kind):
        problems.append(f"欄位 {item.path} 對不到 schema 的{_KIND_ZH[item.kind]}欄位")
    if item.hint_min is not None and item.hint_max is not None and item.hint_min > item.hint_max:
        problems.append(f"欄位 {item.path} 的建議範圍下限大於上限")
    if known_types is not None:
        bad = sorted(set(item.effect_types) - known_types)
        if bad:
            problems.append(f"欄位 {item.path} 的 effect_types 不是原語：{'、'.join(bad)}")
    bad_kinds = sorted(set(item.kinds) - set(SKILL_KINDS))
    if bad_kinds:
        problems.append(f"欄位 {item.path} 的 kinds 不對：{'、'.join(bad_kinds)}")
    return problems


def load_tuning_fields(content_dir: Path) -> TuningFields:
    """讀 ``<content_dir>/tuning_fields.yaml`` 並做 :func:`tuning_field_problems`；有問題拋
    ``ContentError``。"""
    path = content_dir / TUNING_FIELDS_FILE
    table = load_content_file(path, TuningFields)
    problems = tuning_field_problems(table, content_dir)
    if problems:
        raise ContentError(path, "白名單有問題：\n" + "\n".join(f"  - {p}" for p in problems))
    return table
