"""改動單 → 改後的檔案文字 → 驗證（NW-1a A4／A5，規格 5.5）。

順序（任何一步有錯就不往下）：

1. 轉型（:func:`to_changes`）：使用者打的文字轉整數，轉不了是欄位錯誤。
2. 對到白名單（檔在對象清單內、路徑對到欄位；階段門檻只開有 ``hp_below`` 的階段）、``old`` 等於
   磁碟現值（不同就「這個值已經被改過（現在是 X）」）、YAML 字面替換（:func:`prepare`）。
3. 單檔 schema（``UnitTemplate``）：pydantic 錯誤轉中文、依 ``loc`` 對到欄位
   （:func:`schema_errors`）。
4. 整包：草稿複本 ``load_checked_library`` ＋ ``library_violations``（＝``trpg content check``
   同一套；:func:`library_errors`）。``ContentError`` 指到改過的檔時掛在那個檔的欄位上，其他放頁首。
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from trpg.api.primitive_coverage import load_checked_library
from trpg.api.tuning.drafts import Change, normalize
from trpg.api.tuning.objects import concrete_fields, read_data
from trpg.api.tuning.schemas import (
    TuningBudgetFlag,
    TuningChangeIn,
    TuningFieldError,
    TuningMinMovesFlag,
    TuningSideChange,
)
from trpg.api.tuning.yaml_patch import MISSING, PatchError, PatchValue, lookup, patch_text
from trpg.content.library import ContentLibrary
from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import (
    TARGET_MODELS,
    PathPart,
    TuningFields,
    TuningTarget,
    format_path,
    parse_path,
    target_files,
)
from trpg.shared.errors import ContentError
from trpg.skillgen.library_check import library_violations

__all__ = [
    "ChangeValue",
    "KindOf",
    "Prepared",
    "convert",
    "kind_resolver",
    "library_errors",
    "prepare",
    "schema_errors",
    "target_of",
    "to_changes",
]

_TRIGGER_KINDS = frozenset({"hp_below", "tag_down", "round_at"})
"""``trigger`` 判別欄位的值：pydantic 的 ``loc`` 會多一段，對欄位時拿掉。"""


@dataclass
class Prepared:
    """套用改動單的結果：``texts`` 是改到的檔（相對路徑 → 改後全文），``originals`` 是改前全文。"""

    changes: tuple[Change, ...]
    texts: dict[str, str] = field(default_factory=dict)
    originals: dict[str, str] = field(default_factory=dict)
    errors: list[TuningFieldError] = field(default_factory=list)
    kinds: dict[str, str] = field(default_factory=dict)
    """檔 → 對象種類（``unit``／``skill``）。"""
    side: list[TuningSideChange] = field(default_factory=list)
    """附帶改動（例外清單；NW-2a T5）：文字已放進 ``texts``／``originals``。"""
    needs_confirm: list[TuningBudgetFlag] = field(default_factory=list)
    """預算超出區間、寫回要勾「我確定」的招（已假設會登記成例外）。"""
    needs_moves: list[TuningMinMovesFlag] = field(default_factory=list)
    """招式組低於 #149 下限、寫回要勾「我確定」的單位（R1）。"""


type ChangeValue = int | str | tuple[str, ...] | None
type KindOf = Callable[[str, str], str | None]
"""(檔, 具體路徑) → 白名單欄位的 ``kind``（對不到回 ``None``）。"""

_DICE_INPUT: Final = re.compile(r"^\s*(\d+)\s*[dD]\s*(\d+)\s*$")
_SKILL_ID: Final = re.compile(r"^skill_[a-z0-9_]+$")
_INT_ZH: Final = "要填整數（例：120）"


def _to_int(value: object) -> int | None:
    if value is None or (isinstance(value, int) and not isinstance(value, bool)):
        return value
    if not isinstance(value, str):
        raise ValueError(_INT_ZH)
    text = value.strip().replace("，", "").replace(",", "")
    if text in ("", "沒寫"):
        return None
    try:
        return int(text)
    except ValueError:
        raise ValueError(_INT_ZH) from None


def _to_dice(value: object) -> str | None:
    if value is None or (isinstance(value, str) and value.strip() in ("", "沒寫")):
        return None
    match = _DICE_INPUT.match(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError("骰子要寫成 NdM（例：2d6）")
    return f"{int(match.group(1))}d{int(match.group(2))}"


def _to_ids(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "沒寫":
            return None
        items = [x for x in re.split(r"[\s,，、]+", value.strip()) if x]
    elif isinstance(value, list | tuple):
        items = [str(x) for x in value]
    else:
        raise ValueError("要填技能 ID 清單（例：skill_fire_bolt, skill_parry_riposte）")
    bad = [x for x in items if _SKILL_ID.match(x) is None]
    if bad:
        raise ValueError(f"技能 ID 格式不對：{bad[0]}（要像 skill_fire_bolt）")
    if len(set(items)) != len(items):
        raise ValueError("同一招不能放兩次")
    return tuple(items)


def convert(value: object, kind: str | None) -> ChangeValue:
    """依欄位種類轉型（NW-2a）；轉不了丟 ``ValueError``（訊息是中文）。``kind`` 是 ``None``（對不到
    白名單）時照值的樣子轉：清單、骰子字串、其他當整數。"""
    if kind == "dice":
        return _to_dice(value)
    if kind == "skill_ids":
        return _to_ids(value)
    if kind is None:
        if isinstance(value, list | tuple):
            return _to_ids(value)
        if isinstance(value, str) and _DICE_INPUT.match(value):
            return _to_dice(value)
    return _to_int(value)


def _old_value(value: object) -> ChangeValue:
    if isinstance(value, list | tuple):
        return tuple(str(x) for x in value)
    if value is None or isinstance(value, int | str):
        return value
    return None


def to_changes(
    items: Iterable[TuningChangeIn], kind_of: KindOf | None = None
) -> tuple[list[Change], list[TuningFieldError]]:
    """請求的改動 → :class:`Change`；新值轉不了（依 ``kind_of`` 查到的欄位種類）回欄位錯誤。"""
    changes: list[Change] = []
    errors: list[TuningFieldError] = []
    for item in items:
        kind = kind_of(item.file, item.path) if kind_of is not None else None
        try:
            new = convert(item.new, kind)
        except ValueError as exc:
            errors.append(TuningFieldError(file=item.file, path=item.path, message_zh=str(exc)))
            continue
        try:
            changes.append(
                Change(file=item.file, path=item.path, old=_old_value(item.old), new=new)
            )
        except ValidationError:
            errors.append(
                TuningFieldError(
                    file=item.file, path=item.path, message_zh="檔名或欄位路徑格式不對"
                )
            )
    return changes, errors


def target_of(content_dir: Path, table: TuningFields, rel: str) -> TuningTarget | None:
    """這個檔屬於哪類對象（不在白名單內回 ``None``）。"""
    for target in table.targets:
        if any(
            p.relative_to(content_dir).as_posix() == rel for p in target_files(content_dir, target)
        ):
            return target
    return None


def kind_resolver(table: TuningFields) -> KindOf:
    """(檔, 具體路徑) → 欄位種類（只看路徑樣式，不讀檔）。"""

    def kind_of(rel: str, path: str) -> str | None:
        for target in table.targets:
            if Path(rel).match(target.glob):
                found = target.field_for(path)
                return None if found is None else found.kind
        return None

    return kind_of


def _shown(value: object) -> str:
    if value is None:
        return "沒寫"
    if isinstance(value, list | tuple):
        return "[" + ", ".join(str(x) for x in value) + "]"
    return str(value)


def _value_problem(content_dir: Path, kind: str, now: object, new: ChangeValue) -> str | None:
    """新值和欄位種類對不對、引用的招在不在（NW-2a）。"""
    if kind == "range" and now == "weapon":
        return "射程是「武器射程」，不能改成數字（屬結構）"
    try:
        same = convert(new, kind) == new
    except ValueError as exc:
        return str(exc)
    if not same:
        return "值的型別不對"
    if kind == "skill_ids" and isinstance(new, tuple):
        missing = [x for x in new if not (content_dir / "skills" / f"{x}.yaml").is_file()]
        if missing:
            return f"沒有這招：{'、'.join(missing)}"
    return None


def _check_file(
    content_dir: Path, target: TuningTarget, rel: str, changes: Sequence[Change]
) -> tuple[str | None, str, list[TuningFieldError]]:
    """一個檔：白名單、``old`` 比對、型別、字面替換。回傳 (改後全文或 None, 原文, 錯誤)。"""
    raw = (content_dir / rel).read_bytes().decode("utf-8")
    data = read_data(content_dir / rel)
    allowed = {path: f for f, path, _label in concrete_fields(data, target)}
    errors: list[TuningFieldError] = []
    edits: list[tuple[Sequence[PathPart], PatchValue]] = []
    for change in changes:

        def fail(message: str, change: Change = change) -> None:
            errors.append(TuningFieldError(file=rel, path=change.path, message_zh=message))

        field = allowed.get(change.path)
        if field is None:
            fail("這個欄位數值工坊不開放")
            continue
        parts = parse_path(change.path)
        current = lookup(data, parts)
        now = _old_value(None if current is MISSING else current)
        if now != change.old:
            fail(f"這個值已經被改過（現在是 {_shown(now)}），請重新載入")
            continue
        problem = _value_problem(content_dir, field.kind, now, change.new)
        if problem is not None:
            fail(problem)
            continue
        edits.append((parts, change.new))
    if errors:
        return None, raw, errors
    try:
        return patch_text(raw, edits), raw, []
    except PatchError as exc:
        path = str(exc).split("：", 1)[0]
        return None, raw, [TuningFieldError(file=rel, path=path, message_zh=str(exc))]


def prepare(content_dir: Path, table: TuningFields, changes: Iterable[Change]) -> Prepared:
    """對到白名單、比對 ``old``、字面替換（第 2 步）。"""
    out = Prepared(changes=normalize(changes))
    by_file: dict[str, list[Change]] = defaultdict(list)
    for change in out.changes:
        by_file[change.file].append(change)
    for rel in sorted(by_file):
        target = target_of(content_dir, table, rel)
        if target is None:
            out.errors += [
                TuningFieldError(file=rel, path=c.path, message_zh="這個檔不在數值工坊可改的範圍")
                for c in by_file[rel]
            ]
            continue
        text, raw, errors = _check_file(content_dir, target, rel, by_file[rel])
        out.errors += errors
        out.originals[rel] = raw
        out.kinds[rel] = target.kind
        if text is not None and text != raw:
            out.texts[rel] = text
    return out


def _message_zh(error: Any) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    known = {
        "greater_than_equal": f"不能小於 {ctx.get('ge')}",
        "less_than_equal": f"不能大於 {ctx.get('le')}",
        "greater_than": f"要大於 {ctx.get('gt')}",
        "less_than": f"要小於 {ctx.get('lt')}",
        "int_parsing": "要填整數",
        "int_type": "要填整數",
        "int_from_float": "要填整數（不能有小數）",
        "missing": "必填",
    }
    if kind in known:
        return known[kind]
    return str(error.get("msg", "")).removeprefix("Value error, ")


def _field_path(loc: Sequence[Any]) -> str:
    parts: list[PathPart] = []
    for i, part in enumerate(loc):
        if isinstance(part, str) and part in _TRIGGER_KINDS and i and loc[i - 1] == "trigger":
            continue
        parts.append(part)
    return format_path(parts) if parts else ""


def _owners(paths: Sequence[str], where: str, message: str = "") -> list[str]:
    """pydantic 的 ``loc`` 對到哪幾筆改動：完全相同，或是改動的上一層（例 ``effects[0]`` 的
    model 驗證錯誤對到 ``effects[0].dice``）；整個 model 的驗證錯誤（``loc`` 是空的）照訊息裡提到的
    欄位名對（例「主動技能的 ap_cost 必須是 1 到 3」→ ``ap_cost``）。"""
    if where in paths:
        return [where]
    if not where:
        return [
            p
            for p in paths
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(_leaf_name(p))}(?![A-Za-z0-9_])", message)
        ]
    return [p for p in paths if p.startswith((f"{where}.", f"{where}["))]


def _leaf_name(path: str) -> str:
    return str(parse_path(path)[-1])


def schema_errors(prepared: Prepared) -> tuple[list[TuningFieldError], list[str]]:
    """改後的單檔 schema 檢查（第 3 步；單位 ``UnitTemplate``、技能 ``SkillDef``）：
    (欄位錯誤, 頁首錯誤)。"""
    fields: list[TuningFieldError] = []
    page: list[str] = []
    for rel, text in sorted(prepared.texts.items()):
        model = TARGET_MODELS.get(prepared.kinds.get(rel, ""))
        if model is None:  # 附帶改動的檔（skill_budget.yaml）：整包檢查會驗
            continue
        paths = [c.path for c in prepared.changes if c.file == rel]
        try:
            model.model_validate(parse_yaml(text.removeprefix("﻿")))
        except ValidationError as exc:
            for error in exc.errors(include_url=False):
                message = _message_zh(error)
                owners = _owners(paths, _field_path(error["loc"]), message)
                fields += [TuningFieldError(file=rel, path=p, message_zh=message) for p in owners]
                if not owners:
                    page.append(f"{rel}：{message}")
    return fields, page


def library_errors(
    draft_dir: Path, prepared: Prepared, sink: list[ContentLibrary] | None = None
) -> tuple[list[TuningFieldError], list[str]]:
    """草稿複本的整包檢查（第 4 步）：(欄位錯誤, 頁首錯誤)。載入成功時把內容庫放進 ``sink``
    （#149 下限檢查用，NW-2a R1）。"""
    try:
        library = load_checked_library(draft_dir)
        if sink is not None:
            sink.append(library)
    except ContentError as exc:
        try:
            rel = exc.path.resolve().relative_to(draft_dir.resolve()).as_posix()
        except ValueError:
            rel = exc.path.as_posix()
        mine = [c for c in prepared.changes if c.file == rel]
        if not mine:  # 例：玩家這一邊不能裝敵人專用招，錯誤掛在 sim/builds.yaml，訊息以單位 ID 開頭
            mine = [
                c
                for c in prepared.changes
                if prepared.kinds.get(c.file) == "unit" and f"{Path(c.file).stem}：" in exc.reason
            ]
        if mine:
            return [
                TuningFieldError(file=c.file, path=c.path, message_zh=exc.reason) for c in mine
            ], []
        return [], [f"{rel}：{exc.reason}"]
    violations = library_violations(library)
    return [], [f"技能違規：{v}" for v in violations]
