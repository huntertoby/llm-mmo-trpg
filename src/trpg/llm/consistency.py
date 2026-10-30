"""敘事與效果的一致性、世界觀詞用量（Phase 4-L11）。

LLM 寫的名稱、概念、施放敘事（與閃現 note_zh）只能描述技能真的有的效果：

- :func:`check_mentions`：提到詞表（``content/llm/effect_words.yaml``）裡的控制、元素、召喚等詞時，
  技能效果（:func:`skill_facts`：狀態、元素、表面、原語、召喚物）裡要找得到對應；
- :func:`check_added`：閃現變化加上的效果（:func:`added_facts`）要被提到；
- :func:`check_world_terms`：世界觀詞（``world_shattered.yaml`` 的 ``naming.world_terms``）的
  用量上限。

全部是純文字比對（確定性，不呼叫 LLM）；錯誤碼與中文說明交給命名與閃現提議的重試回饋。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from trpg.content.battle import StatusDef
from trpg.content.effect_words import EffectWordGroup, EffectWords
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_elements
from trpg.content.world import WorldTermRules
from trpg.shared.types import Element
from trpg.skillgen.player_text import plain_name

__all__ = [
    "NameCheck",
    "added_facts",
    "check_added",
    "check_mentions",
    "check_world_terms",
    "effect_phrases",
    "mentioned_groups",
    "skill_facts",
    "world_term_count",
]

_EXCLUDED = {"id", "name_zh", "narrative", "provenance", "tags"}
_NESTED_LEADS = {
    "on_kill": "打倒敵人時",
    "then": "之後",
    "win": "賭贏時",
    "lose": "賭輸時",
    "effects": "條件成立時",
}


@dataclass(frozen=True, slots=True)
class NameCheck:
    """一個檢查失敗：穩定代碼與給 LLM 的中文說明。"""

    code: str
    message: str


# ---------------------------------------------------------------------------
# 技能的效果鍵
# ---------------------------------------------------------------------------


def _walk(node: Any, primitives: frozenset[str], out: set[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk(item, primitives, out)
        return
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if isinstance(kind, str) and kind in primitives:
        out.add(f"primitive:{kind}")
    for key in ("status", "element", "surface", "unit"):
        value = node.get(key)
        if isinstance(value, str):
            out.add(f"{key}:{value}")
    if node.get("knock_prone") is True:
        out.add("primitive:knock_prone")
    on_hit = node.get("on_hit")
    if isinstance(on_hit, str):
        out.add(f"primitive:{on_hit}")
    for key in sorted(node):
        if key not in _EXCLUDED:
            _walk(node[key], primitives, out)


def skill_facts(library: ContentLibrary, skill: SkillDef) -> frozenset[str]:
    """技能（含接續段、變奏、修正規則、條件）出現的效果鍵：``primitive:push``、``status:burning``、
    ``element:fire``、``surface:water``、``unit:summon_vine``。技能本身的元素（:func:`skill_elements`）
    也算。"""
    primitives = frozenset(p.id for p in library.ruleset.primitives.primitives)
    out: set[str] = set()
    _walk(skill.model_dump(mode="json", exclude=_EXCLUDED), primitives, out)
    out.update(f"element:{e.value}" for e in skill_elements(skill))
    statuses = library.ruleset.statuses.by_id()
    for fact in sorted(out):
        if fact.startswith("status:"):
            out.update(_rider_facts(statuses.get(fact.removeprefix("status:"))))
    return frozenset(out)


def _rider_facts(status: StatusDef | None) -> set[str]:
    """狀態本身帶的附帶效果（護盾被打破時造表面、雷電傷害、施加狀態；3W-2b 的護盾橋接）。
    技能資料只寫狀態 ID，這些效果在狀態定義上，敘事提到它們（「一灘水」「雷電」）也算有對應。"""
    if status is None:
        return set()
    out: set[str] = set()
    if status.shield_break_surface is not None:
        out.add(f"surface:{status.shield_break_surface.value}")
    if status.shield_break_lightning:
        out.add(f"element:{Element.LIGHTNING.value}")
    if status.shield_break_status is not None:
        out.add(f"status:{status.shield_break_status}")
    return out


def added_facts(library: ContentLibrary, before: SkillDef, after: SkillDef) -> frozenset[str]:
    """閃現變化加上的效果鍵（變化後有、變化前沒有）。"""
    return skill_facts(library, after) - skill_facts(library, before)


# ---------------------------------------------------------------------------
# 詞表比對
# ---------------------------------------------------------------------------


def _strip_ignored(text: str, group: EffectWordGroup) -> str:
    for phrase in group.ignore:
        text = text.replace(phrase, "　")
    return text


def strip_similes(text: str, words: EffectWords) -> str:
    """去掉比喻片段（比喻引導詞起到下一個標點為止，標點保留）；規則是詞表資料。"""
    if not words.simile_markers:
        return text
    markers = "|".join(re.escape(m) for m in sorted(words.simile_markers, key=lambda m: -len(m)))
    end = re.escape(words.simile_end)
    pattern = f"(?:{markers})[^{end}]*" if end else f"(?:{markers}).*"
    return re.sub(pattern, "　", text)


def mentioned_groups(text: str, words: EffectWords) -> list[tuple[EffectWordGroup, str]]:
    """``text`` 提到的詞組與第一個被提到的詞（依詞表順序）；比喻片段不算。"""
    found: list[tuple[EffectWordGroup, str]] = []
    text = strip_similes(text, words)
    for group in words.groups:
        cleaned = _strip_ignored(text, group)
        word = next((w for w in group.words if w in cleaned), None)
        if word is not None:
            found.append((group, word))
    return found


def check_mentions(
    label: str, text: str, facts: frozenset[str], words: EffectWords
) -> list[NameCheck]:
    """``text`` 提到的詞在 ``facts`` 裡找不到對應時回報 ``{label}.effect_mismatch``（一段一個錯誤，
    說明列出全部不符的詞）。"""
    bad = [
        word
        for group, word in mentioned_groups(text, words)
        if not facts & set(group.matches.facts())
    ]
    if not bad:
        return []
    listed = "、".join(f"「{w}」" for w in bad)
    return [
        NameCheck(
            f"{label}.effect_mismatch",
            f"{label} 提到{listed}，但技能效果沒有對應的效果；只描述 effect_summary 裡有的效果，"
            "把這些詞拿掉或換掉。",
        )
    ]


def check_added(
    texts: Iterable[str], added: frozenset[str], words: EffectWords, *, code: str
) -> list[NameCheck]:
    """變化加上的效果（``added``）至少要被 ``texts`` 其中一段提到（每個加上的效果各自檢查，詞表沒有
    對應詞的效果不檢查）。"""
    joined = "\n".join(texts)
    missing: list[str] = []
    for fact in sorted(added):
        groups = [g for g in words.groups if fact in g.matches.facts()]
        if len(groups) != 1:  # 沒有對應詞、或同時對應多組（clear_surface 之類）的不要求
            continue
        if not any(any(w in _strip_ignored(joined, g) for w in g.words) for g in groups):
            missing.append(groups[0].words[0])
    if not missing:
        return []
    listed = "、".join(f"「{w}」" for w in dict.fromkeys(missing))
    return [
        NameCheck(
            code,
            f"這次變化加上的效果沒有被提到（例如{listed}），請在名稱或敘事裡寫出來。",
        )
    ]


# ---------------------------------------------------------------------------
# 世界觀詞
# ---------------------------------------------------------------------------


def world_term_count(text: str, terms: Iterable[str]) -> int:
    """世界觀詞出現的次數（由長到短、由左到右不重疊計數；同一詞重複也算）。"""
    ordered = sorted(set(terms), key=lambda t: (-len(t), t))
    count = 0
    index = 0
    while index < len(text):
        hit = next((t for t in ordered if t and text.startswith(t, index)), None)
        if hit is None:
            index += 1
        else:
            count += 1
            index += len(hit)
    return count


def check_world_terms(
    name: str | None, texts: Mapping[str, str], rules: WorldTermRules
) -> list[NameCheck]:
    """名稱：不得以世界觀詞開頭、前 ``name_prefix_len`` 個字不得含 ``name_prefix_chars``、最多
    ``name_max`` 個世界觀詞；其他每段文字最多 ``text_max`` 個。"""
    if not rules.terms and not rules.name_prefix_chars:
        return []
    out: list[NameCheck] = []
    if name is not None:
        head = name[: rules.name_prefix_len]
        if any(name.startswith(t) for t in rules.terms) or any(
            c in head for c in rules.name_prefix_chars
        ):
            banned = "、".join(f"「{c}」" for c in rules.name_prefix_chars)
            out.append(
                NameCheck(
                    "name_zh.world_prefix",
                    f"name_zh 不可用世界觀詞開頭，前 {rules.name_prefix_len} 個字也不可有{banned}；"
                    "改從技能的效果、元素與形狀取名。",
                )
            )
        if world_term_count(name, rules.terms) > rules.name_max:
            out.append(
                NameCheck(
                    "name_zh.world_terms",
                    f"name_zh 最多 {rules.name_max} 個世界觀詞（{_term_list(rules)}）。",
                )
            )
    for label, text in texts.items():
        if world_term_count(text, rules.terms) > rules.text_max:
            out.append(
                NameCheck(
                    f"{label}.world_terms",
                    f"{label} 最多 {rules.text_max} 個世界觀詞（{_term_list(rules)}），"
                    "改寫成具體的動作與效果。",
                )
            )
    return out


def _term_list(rules: WorldTermRules) -> str:
    return "、".join(rules.terms)


# ---------------------------------------------------------------------------
# 給 prompt 的效果摘要
# ---------------------------------------------------------------------------


def _name(library: ContentLibrary, kind: str, value: str) -> str:
    try:
        if kind == "status":
            return library.ruleset.status_def(value).name_zh
        if kind == "unit":
            return library.ruleset.summon_def(value).template.name_zh
    except KeyError:
        return plain_name(value, library)
    return plain_name(value, library)


def _phrase(library: ContentLibrary, effect: Any) -> str:
    base = plain_name(effect.type, library)
    details: list[str] = []
    element = effect.element
    if effect.type == "damage":
        zh = (element or Element.PHYSICAL).display_name
        base = f"{zh}傷害"
    elif element is not None:
        details.append(element.display_name)
    if effect.status is not None:
        details.append(f"狀態「{_name(library, 'status', effect.status)}」")
    if effect.surface is not None:
        details.append(f"表面「{library.ruleset.surface_def(effect.surface).name_zh}」")
    if effect.unit is not None:
        details.append(f"「{_name(library, 'unit', effect.unit)}」")
    if effect.knock_prone:
        details.append("擊倒")
    return f"{base}（{'、'.join(details)}）" if details else base


def _phrases(library: ContentLibrary, effects: Iterable[Any], lead: str, out: list[str]) -> None:
    for effect in effects:
        text = _phrase(library, effect)
        out.append(f"{lead}：{text}" if lead else text)
        for key, sub_lead in _NESTED_LEADS.items():
            nested = getattr(effect, key, None)
            if nested:
                _phrases(library, nested, sub_lead, out)


def effect_phrases(library: ContentLibrary, skill: SkillDef) -> list[str]:
    """技能效果的精簡中文摘要（給命名 prompt；沒有數值與代號），例如「風傷害」「推開」
    「生成表面（表面「水」）」「打倒敵人時：返還 AP」。接續段加「接續段」前綴。"""
    out: list[str] = []
    _phrases(library, skill.effects, "", out)
    follow = skill.followup_skill()
    if follow is not None:
        _phrases(library, follow.effects, "接續段", out)
    return list(dict.fromkeys(out))
