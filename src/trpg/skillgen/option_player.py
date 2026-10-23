"""工坊選項的玩家版說明（Phase 3-48c，玩法決定 #44）。

內容資料的 ``description_zh`` 是給開發者看的（含英文代號、檔名、階段編號）。送給前端之前，
:func:`playerize` 對每個欄位與選項的說明做一次處理：

1. 能由規則產生的部分用程式產生——核心規則的數值（rune_limit_per_owner → 6）、參數名（→ 中文名）、
   ID（→ 中文名，沿用 plainify）；檔名與階段編號整段拿掉。
2. 處理完仍含英文詞的，玩家版改用原語的 ``player_description``（只有原語選項有）；都沒有就留空
   （前端不顯示說明）。原文放在 ``dev_description_zh``，``?dev=1`` 才顯示。

巢狀效果在 3-48d 開放（``option_nested``）；``later`` 旗標保留給之後還沒開放的選項。

:func:`content_dev_texts`、:func:`option_dev_texts` 列出全部「含英文代號或開發者語氣」的說明
（匯出給玩法 PM 改寫，``scripts/export_workshop_descriptions.py``）。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from trpg.content.library import ContentLibrary
from trpg.content.skills import PrimitiveDef
from trpg.skillgen.option_models import Choice, FieldSpec
from trpg.skillgen.player_text import plainify

__all__ = [
    "fill_placeholders",
    "content_dev_texts",
    "has_dev_text",
    "localize",
    "option_dev_texts",
    "playerize",
]

_ENGLISH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]+")
_ALLOWED = {"AP", "HP", "MP", "YAML"}
_PHASE = re.compile(r"（?\bPhase\s*[0-9][0-9A-Za-z\-]*[^）：:]{0,2}[）：:]?")
_FILE_NOTE = re.compile(r"（(?:見\s*)?(?:rules/)?[A-Za-z_./]*\.yaml[^）]*）")
_CORE_REF = re.compile(r"(?:rules/)?core\.yaml\s*(?:的\s*)?|\bcore\.")


def has_dev_text(text: str) -> bool:
    """說明含英文代號（欄位名、ID、檔名、階段編號）。"""
    return any(word not in _ALLOWED for word in _ENGLISH.findall(text))


def _core_values(library: ContentLibrary) -> dict[str, str]:
    core = library.ruleset.core
    out: dict[str, str] = {}
    for name in type(core).model_fields:
        value = getattr(core, name)
        if isinstance(value, int) and not isinstance(value, bool):
            out[name] = str(value)
    return out


def fill_placeholders(text: str, library: ContentLibrary) -> str:
    """玩家語氣說明裡的 ``{名稱}`` 由程式依核心規則填入（3-48h：數值與清單不寫死）：
    ``{rune_max_rounds}`` 符文持續上限、``{summon_traits}`` 召喚物小特性的中文名；
    ``{<core 的整數欄位>}`` 也可用。"""
    if "{" not in text:
        return text
    core = library.ruleset.core
    values = _core_values(library)
    values["summon_traits"] = "、".join(t.name_zh for t in core.summon_traits.values())
    return re.sub(r"\{([a-z_]+)\}", lambda m: values.get(m.group(1), m.group(0)), text)


def localize(text: str, library: ContentLibrary, names: dict[str, str] | None = None) -> str:
    """說明的程式化中文處理（見模組說明 1）；``names``：這段說明所屬欄位的參數名 → 中文名。"""
    values = _core_values(library)
    out = _PHASE.sub("", text)
    out = re.sub(
        r"(?:rules/)?core\.yaml的?\s*([A-Za-z_]+)|\bcore\.([A-Za-z_]+)",
        lambda m: values.get(m.group(1) or m.group(2), ""),
        out,
    )
    out = re.sub(
        r"\b([a-z_]+)（(?:rules/)?core\.yaml，初值\s*(\d+)[^）]*）",
        lambda m: m.group(2),
        out,
    )
    out = _FILE_NOTE.sub("", out)
    out = _ENGLISH.sub(lambda m: values.get(m.group(0), m.group(0)), out)
    zh = dict(names or {})
    out = _ENGLISH.sub(lambda m: zh.get(m.group(0), m.group(0)), out)
    return plainify(out, library)


def _player_text(
    text: str,
    library: ContentLibrary,
    names: dict[str, str],
    fallback: str | None,
    scope: str | None = None,
) -> tuple[str, str]:
    """``(玩家版, 原文)``；原文為空表示這段說明本來就可以給玩家看。

    玩法 PM 改寫過的說明（``content/workshop_text.yaml``，3-48f）優先，依原文（與欄位範圍）查表。
    """
    if text == "":
        return text, ""
    rewritten = library.workshop_text.lookup(text, scope)
    if rewritten is not None:
        return fill_placeholders(rewritten, library), text
    if not has_dev_text(text):
        return text, ""
    cleaned = localize(text, library, names)
    if not has_dev_text(cleaned):
        return cleaned, text
    return (fallback or ""), text


def _choice(
    choice: Choice,
    library: ContentLibrary,
    names: dict[str, str],
    *,
    primitives: dict[str, PrimitiveDef] | None,
    owner: str = "",
) -> Choice:
    """``primitives`` 不是 ``None`` 時，這個選項是效果原語。"""
    own = {**names, **{p.field: p.name_zh for p in choice.params}}
    primitive = None if primitives is None else primitives.get(str(choice.value))
    fallback = None if primitive is None else primitive.player_description
    text, dev = _player_text(choice.description_zh, library, own, fallback)
    return choice.model_copy(
        update={
            "description_zh": text,
            "dev_description_zh": dev,
            "params": playerize(choice.params, library, own, str(choice.value)),
        }
    )


def _field(
    field: FieldSpec, library: ContentLibrary, names: dict[str, str], owner: str = ""
) -> FieldSpec:
    primitives = (
        {p.id: p for p in library.ruleset.primitives.primitives}
        if field.type == "effects"
        else None
    )
    own = {**names, **{f.field: f.name_zh for f in field.fields}}
    scope = f"{owner}.{field.field}" if owner else field.field
    text, dev = _player_text(field.description_zh, library, own, None, scope)
    return field.model_copy(
        update={
            "description_zh": text,
            "dev_description_zh": dev,
            "fields": playerize(field.fields, library, own, field.field),
            "choices": tuple(
                _choice(c, library, own, primitives=primitives, owner=field.field)
                for c in field.choices
            ),
        }
    )


def playerize(
    fields: tuple[FieldSpec, ...],
    library: ContentLibrary,
    names: dict[str, str] | None = None,
    owner: str = "",
) -> tuple[FieldSpec, ...]:
    """欄位與選項（遞迴）的說明換成玩家版（``owner``：這些欄位所屬的選項或欄位，查對照表的範圍用）。"""
    return tuple(_field(f, library, names or {}, owner) for f in fields)


# ---------------------------------------------------------------------------
# 匯出：含開發者語氣的說明（給玩法 PM 改寫；scripts/export_workshop_descriptions.py）
# ---------------------------------------------------------------------------


def _walk(prefix: str, fields: tuple[FieldSpec, ...]) -> Iterator[tuple[str, str]]:
    for field in fields:
        here = f"{prefix}.{field.field}"
        if field.dev_description_zh:
            yield here, field.dev_description_zh
        yield from _walk(here, field.fields)
        for choice in field.choices:
            there = f"{here}={choice.value}"
            if choice.dev_description_zh:
                yield there, choice.dev_description_zh
            yield from _walk(there, choice.params)


def option_dev_texts(steps: dict[str, tuple[FieldSpec, ...]]) -> list[tuple[str, str]]:
    """程式組出的欄位（已 :func:`playerize`）裡，有玩家版的說明原文：``(路徑, 原文)``。"""
    out: list[tuple[str, str]] = []
    for step, fields in steps.items():
        out += _walk(f"工坊.{step}", fields)
    return out


def _described(items: Iterable[object], kind: str) -> Iterator[tuple[str, str]]:
    for item in items:
        item_id = str(getattr(getattr(item, "id", None), "value", getattr(item, "id", "")))
        text = getattr(item, "description_zh", "")
        if isinstance(text, str) and text:
            yield f"{kind}.{item_id}", text
        for name, param in (getattr(item, "params", None) or {}).items():
            spec_text = getattr(param, "description_zh", "")
            if isinstance(spec_text, str) and spec_text:
                yield f"{kind}.{item_id}.{name}", spec_text


def content_dev_texts(library: ContentLibrary) -> list[tuple[str, str]]:
    """內容資料（原語、形狀、條件、觸發時機、骨架、狀態、層數）裡含英文代號的 ``description_zh``，
    連同各參數的說明：``(「種類.ID[.參數]」, 原文)``。"""
    rules = library.ruleset
    groups: list[tuple[str, Iterable[object]]] = [
        ("原語", rules.primitives.primitives),
        ("形狀", rules.shapes.shapes),
        ("條件", rules.conditions.conditions),
        ("觸發", rules.skill_triggers.triggers),
        ("骨架", library.skeletons.values()),
        ("狀態", rules.statuses.statuses),
        ("層數", rules.stacks.stacks),
    ]
    seen: dict[str, str] = {}
    for kind, items in groups:
        for key, text in _described(items, kind):
            if has_dev_text(text):
                seen.setdefault(key, text)
    return sorted(seen.items())
