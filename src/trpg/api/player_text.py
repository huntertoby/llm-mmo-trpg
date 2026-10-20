"""給玩家看的工坊說明文字（Phase 3-5c-2）：去掉階段編號與程式識別字。

工坊的選項說明直接取自原語、形狀、骨架的定義，裡面有給開發者看的術語（``Phase 3D-7b``、
``refund_ap``、``rules/core.yaml``）。這裡在 API 層過濾：

1. 刪掉 ``Phase …`` 標記（連同前後括號）。
2. 識別字（含底線、點或斜線的英數字串）換成同一份選項裡的中文名（選項值、欄位名）或內容庫的
   中文名（狀態、表面、物件、反應、層數、元素）；找不到中文名的刪掉，再整理多餘的括號與標點。

純函式、不依賴 LLM；:func:`player_options` 套用到 :class:`~trpg.skillgen.option_models.DraftOptions`
的每個說明欄位（``description_zh``、``notes_zh``、``problems``）。
"""

from __future__ import annotations

import re
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.skillgen.option_models import DraftOptions

__all__ = ["IDENTIFIER", "PHASE_MARK", "clean_text", "player_options"]

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[_./][A-Za-z0-9]+)+")
"""程式識別字：含底線、點或斜線的英數字串（``refund_ap``、``core.explode_max``、``rules/core.yaml``）。"""

PHASE_MARK = re.compile(r"[（(]\s*Phase[^）)]*[）)]|Phase\s*[0-9A-Za-z\-]+")
"""階段編號：括號內的 ``Phase …``，或單獨的 ``Phase 3D-7b``。"""

_PAREN = re.compile(r"[（(][^（）()]*[）)]")
_FILE_REFERENCE = re.compile(r"[A-Za-z0-9_/]+\.ya?ml\s*(?:中的|裡的|的)?\s*")
_CORE_VALUE = re.compile(r"(?<![A-Za-z0-9_])core\.[a-z0-9_]+")

MANUAL_NAMES = {
    "on_move": "移動時的",
    "refund_ap": "返還 AP",
    "refund_cooldown": "冷卻歸零",
    "lifesteal_value_permille": "吸血價值係數",
    "collision_damage_dice": "撞擊傷害骰",
    "collision_die_points": "撞擊骰的點數",
}
"""選項樹與內容庫都查不到中文名、但說明裡常出現的識別字。"""

_EMPTY_BRACKETS = re.compile(r"[（(「『]\s*[）)」』]")
_REPEATED_SEPARATOR = re.compile(r"([、，；／,;/])\s*(?:[、，；／,;/]\s*)+")
_DANGLING_OPEN = re.compile(r"([（(「])\s*[、，；／,;/]\s*")
_DANGLING_CLOSE = re.compile(r"\s*[、，；／,;/]\s*([）)」])")
_SEPARATOR_AFTER_COLON = re.compile(r"([：:])\s*[、，；／,;/]\s*")
_LEADING_SEPARATOR = re.compile(r"^\s*[、，；／,;/：:]\s*")


def clean_text(text: str, names: dict[str, str]) -> str:
    """一段說明文字去掉階段編號，識別字換成 ``names`` 的中文名（沒有的刪掉）。"""
    text = PHASE_MARK.sub("", text)
    text = _FILE_REFERENCE.sub("", text)
    text = _CORE_VALUE.sub("核心規則的設定值", text)
    known = {**MANUAL_NAMES, **names}
    # 括號裡有查不到中文名的識別字：整段括號是給開發者看的補充，整段刪掉
    text = _PAREN.sub(
        lambda m: "" if any(i not in known for i in IDENTIFIER.findall(m.group(0))) else m.group(0),
        text,
    )
    text = IDENTIFIER.sub(lambda m: known.get(m.group(0), ""), text)
    for _ in range(3):  # 刪除後可能露出新的空括號或重複的分隔符
        text = _EMPTY_BRACKETS.sub("", text)
        text = _REPEATED_SEPARATOR.sub(r"\1", text)
        text = _DANGLING_OPEN.sub(r"\1", text)
        text = _DANGLING_CLOSE.sub(r"\1", text)
        text = _SEPARATOR_AFTER_COLON.sub(r"\1", text)
    text = _LEADING_SEPARATOR.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _collect_names(node: Any, names: dict[str, str]) -> None:
    """選項樹裡的 ``value → name_zh`` 與 ``field → name_zh``（欄位名取完整路徑與最後一段）。"""
    if isinstance(node, dict):
        name = node.get("name_zh")
        if isinstance(name, str):
            value = node.get("value")
            if isinstance(value, str):
                names.setdefault(value, name)
            field = node.get("field")
            if isinstance(field, str):
                names.setdefault(field, name)
                names.setdefault(field.rsplit(".", 1)[-1], name)
        for child in node.values():
            _collect_names(child, names)
    elif isinstance(node, list):
        for child in node:
            _collect_names(child, names)


def library_names(library: ContentLibrary) -> dict[str, str]:
    """內容庫的 ID → 中文名：狀態、表面、物件、反應、層數、元素、地形。"""
    rules = library.ruleset
    names: dict[str, str] = {}
    for group in (
        rules.statuses.statuses,
        rules.objects.objects,
        rules.reactions.reactions,
        rules.stacks.stacks,
        rules.terrain.terrain,
    ):
        names.update({e.id: e.name_zh for e in group})
    names.update({s.id.value: s.name_zh for s in rules.surfaces.surfaces})
    names.update({e.id.value: e.name_zh for e in library.elements.elements})
    return names


_TEXT_KEYS = ("description_zh", "notes_zh", "problems")


def _clean_tree(node: Any, names: dict[str, str]) -> Any:
    if isinstance(node, dict):
        return {
            key: _clean_value(value, names) if key in _TEXT_KEYS else _clean_tree(value, names)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_clean_tree(child, names) for child in node]
    return node


def _clean_value(value: Any, names: dict[str, str]) -> Any:
    if isinstance(value, str):
        return clean_text(value, names)
    if isinstance(value, list):
        return [_clean_value(v, names) for v in value]
    return value


def player_options(options: DraftOptions, library: ContentLibrary) -> DraftOptions:
    """工坊選項的說明文字改成給玩家看的版本（其他欄位不動）。"""
    data = options.model_dump(mode="json")
    names = library_names(library)
    tree_names: dict[str, str] = {}
    _collect_names(data, tree_names)
    names = {**names, **tree_names}
    return DraftOptions.model_validate(_clean_tree(data, names))
