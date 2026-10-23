"""工坊的關鍵字建議（Phase 3-51，玩法決定 #55、06 6.27.1）。

檢查面板除了顯示目前的關鍵字（或「基礎技能」），還列出「加哪一種效果或條件，就能接上哪個關鍵字」。
建議 **由推導表（``content/skill_keywords.yaml``）的專屬規則產生**，不寫死：每條規則轉成一句
「效果「施加狀態」（燃燒）」「條件「目標在表面上」（火）」。只是提示，不擋。

純函式：只讀內容庫與技能草稿，沒有亂數、沒有時間。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.keyword_derive import SkillKeywords
from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordRule
from trpg.skillgen.keywords import derive_draft_keywords

__all__ = ["KeywordHint", "draft_keyword_hints", "keyword_hints"]

MAX_WAYS_PER_SIDE = 4
"""每個關鍵字、每一側（製造或利用）最多列幾種做法。"""


class KeywordHint(BaseModel):
    """一個關鍵字的建議：製造或利用它可以加哪些效果、條件或觸發。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    makes: tuple[str, ...] = ()
    """製造這個關鍵字的做法（例：「效果「施加狀態」（燃燒）」）。"""
    uses: tuple[str, ...] = ()
    """利用這個關鍵字的做法。"""


def _safe_name(lookup: Any, key: str) -> str | None:
    try:
        return str(lookup(key).name_zh)
    except (KeyError, AttributeError):
        return None


def _param_names(library: ContentLibrary, rule: KeywordRule) -> list[str]:
    rules = library.ruleset
    out: list[str] = []
    if rule.status is not None and (n := _safe_name(rules.status_def, rule.status)):
        out.append(n)
    if rule.surface is not None and (n := _safe_name(rules.surface_def, rule.surface)):
        out.append(n)
    if rule.element is not None:
        out.append(rule.element.display_name)
    if rule.object is not None and (n := _safe_name(rules.object_def, rule.object)):
        out.append(n)
    if rule.stack is not None and (n := _safe_name(rules.stack_def, rule.stack)):
        out.append(n)
    if rule.unit is not None and rule.unit in library.units:
        out.append(library.units[rule.unit].name_zh)
    return out


def _source_text(library: ContentLibrary, rule: KeywordRule) -> str | None:
    rules = library.ruleset
    if rule.effect is not None:
        name = _safe_name(rules.primitive_def, rule.effect)
        return None if name is None else f"效果「{name}」"
    if rule.condition is not None:
        name = _safe_name(rules.condition_def, rule.condition)
        return None if name is None else f"條件「{name}」"
    if rule.trigger is not None:
        name = _safe_name(rules.trigger_def, rule.trigger)
        return None if name is None else f"被動觸發「{name}」"
    if rule.shape is not None:
        name = _safe_name(rules.shape_def, rule.shape)
        return None if name is None else f"形狀「{name}」"
    return None  # 修正規則的改變種類沒有玩家名稱，不列


def rule_way_text(library: ContentLibrary, rule: KeywordRule) -> str | None:
    """一條專屬規則轉成「加什麼」的一句話；不適合當建議的規則（修正規則、灌注）回傳 ``None``。"""
    if rule.grade != "exclusive" or rule.infusion is not None:
        return None
    text = _source_text(library, rule)
    if text is None:
        return None
    names = _param_names(library, rule)
    return text + (f"（{'、'.join(names)}）" if names else "")


def _ways(library: ContentLibrary, rules: tuple[KeywordRule, ...]) -> tuple[str, ...]:
    found = [w for r in rules if (w := rule_way_text(library, r)) is not None]
    return tuple(dict.fromkeys(found))[:MAX_WAYS_PER_SIDE]


def keyword_hints(
    library: ContentLibrary, have: SkillKeywords, *, side: Literal["makes", "uses", "both"] = "both"
) -> tuple[KeywordHint, ...]:
    """還沒接上的每個關鍵字（依推導表順序）的建議；已經製造且利用的關鍵字不列。"""
    out: list[KeywordHint] = []
    for keyword in library.keywords.keywords:
        makes = () if keyword.id in have.makes or side == "uses" else _ways(library, keyword.makes)
        uses = () if keyword.id in have.uses or side == "makes" else _ways(library, keyword.uses)
        if makes or uses:
            out.append(KeywordHint(id=keyword.id, name_zh=keyword.name_zh, makes=makes, uses=uses))
    return tuple(out)


def draft_keyword_hints(
    library: ContentLibrary, draft: Mapping[str, Any]
) -> tuple[KeywordHint, ...]:
    """技能草稿目前還沒接上的關鍵字與建議。"""
    return keyword_hints(library, derive_draft_keywords(draft, library.keywords))
