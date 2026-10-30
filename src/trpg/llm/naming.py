"""技能命名與敘事（Phase 4-L7）：請同一個本機模型為已通過驗證的技能寫 ``name_zh``、``concept``、
``cast_flavor``。

LLM 只寫文字（守則 3）：結構與數值完全不動，結果只用 ``model_copy`` 換掉這三個欄位。每次回應先過
:func:`check_naming`（長度、空字串、字元集、禁字、重名）；不過就帶錯誤回饋重試，用盡次數或連不上模型
時改用 **組合式名稱與模板敘事**（:func:`fallback_naming`，和隨機組合器同樣的做法：「元素・骨架」）。

4-L11：prompt 帶效果摘要（``effect_summary``）；回應另外檢查敘事與效果一致（提到的控制、元素、召喚詞
要在效果裡找得到，閃現變化加上的效果要被提到）與世界觀詞用量（:mod:`trpg.llm.consistency`），
不過同樣帶錯誤碼重試、用盡退回模板。

結果（名稱與敘事）隨技能寫進 run 紀錄；重播與讀檔不再呼叫 LLM。
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from dataclasses import dataclass, replace
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_elements
from trpg.content.world import NamingRules, WorldStyle, load_world_style
from trpg.llm.client import LLMClient
from trpg.llm.consistency import (
    NameCheck,
    check_added,
    check_mentions,
    check_world_terms,
    effect_phrases,
    skill_facts,
)
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.prompts.naming import build_naming_messages, naming_schema
from trpg.llm.response import clean_response
from trpg.llm.simplified import simplified_chars
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal import combined_skill_name

__all__ = [
    "DEFAULT_NAMING_ATTEMPTS",
    "NameCheck",
    "NamingOutcome",
    "NamingText",
    "apply_naming",
    "check_consistency",
    "check_naming",
    "fallback_naming",
    "name_skill",
    "skill_summary",
    "template_text",
]

DEFAULT_NAMING_ATTEMPTS = 3
_NUMERALS = "二三四五六七八九十"
type NamingSource = Literal["llm", "fallback"]

_NAME_CHARS = re.compile(r"^[一-鿿・（）]+$")
SIMPLIFIED_CHECKED: tuple[str, ...] = ("concept", "cast_flavor")
"""檢查簡體字的欄位（Phase 4-L10a C4；字表見 :mod:`trpg.llm.simplified`）。"""
_TEXT_CHARS = re.compile(r"^[一-鿿　-〿＀-￯・—…‘-”、。，；：！？（）「」『』《》—…・]+$")
"""敘事文字允許的字元：中文字、全形標點與符號（沒有英文字母、數字、半形符號與空白）。"""


class NamingText(BaseModel):
    """命名回應的格式（多餘欄位直接拒絕）。"""

    model_config = ConfigDict(extra="forbid")

    name_zh: str
    concept: str
    cast_flavor: str


@dataclass(frozen=True, slots=True)
class NamingOutcome:
    """:func:`name_skill` 的結果：最後採用的文字、來源、呼叫次數與各次的錯誤代碼。"""

    text: NamingText
    source: NamingSource
    attempts: int
    codes: tuple[str, ...] = ()
    reason: str | None = None
    consistency_retries: int = 0
    """因一致性或世界觀詞檢查（4-L11）不過而重試的次數。"""


def _check_text(label: str, text: str, limit: int, rules: NamingRules) -> list[NameCheck]:
    if not text.strip():
        return [NameCheck(f"{label}.empty", f"{label} 不可為空。")]
    out: list[NameCheck] = []
    if len(text) > limit:
        out.append(NameCheck(f"{label}.too_long", f"{label} 最多 {limit} 個字，目前 {len(text)}。"))
    pattern = _NAME_CHARS if label == "name_zh" else _TEXT_CHARS
    if pattern.match(text) is None:
        out.append(
            NameCheck(
                f"{label}.charset", f"{label} 只能用全形中文字與全形標點，不可有英文、數字或空白。"
            )
        )
    lowered = text.lower()
    bad = next((t for t in rules.forbidden_terms if t.lower() in lowered), None)
    if bad is not None:
        out.append(NameCheck(f"{label}.forbidden", f"{label} 含有不可使用的字樣。"))
    found = simplified_chars(text) if label in SIMPLIFIED_CHECKED else []
    if found:  # 4-L10a C4：敘事要用繁體中文
        out.append(
            NameCheck(
                f"{label}.simplified",
                f"{label} 有簡體字（{'、'.join(found)}），請改用繁體中文。",
            )
        )
    return out


def check_naming(
    text: NamingText, rules: NamingRules, taken: Collection[str] = ()
) -> list[NameCheck]:
    """檢查命名文字：長度、空字串、字元集、禁字、簡體字（``concept``／``cast_flavor``，4-L10a）、
    重名（``taken`` 為已使用的技能名稱）、世界觀詞用量（4-L11，``rules.world_terms``）。"""
    errors = _check_text("name_zh", text.name_zh, rules.name_max_chars, rules)
    errors += _check_text("concept", text.concept, rules.concept_max_chars, rules)
    errors += _check_text("cast_flavor", text.cast_flavor, rules.flavor_max_chars, rules)
    if text.name_zh in taken:
        errors.append(NameCheck("name_zh.duplicate", "name_zh 和既有技能名稱重複，請換一個。"))
    errors += check_world_terms(
        text.name_zh,
        {"concept": text.concept, "cast_flavor": text.cast_flavor},
        rules.world_terms,
    )
    return errors


CONSISTENCY_SUFFIXES = (".effect_mismatch", ".missing_added", ".world_terms", ".world_prefix")
"""4-L11 一致性與世界觀詞檢查的錯誤碼字尾（統計「一致性檢查重試次數」用）。"""


def check_consistency(
    text: NamingText,
    facts: frozenset[str],
    words: EffectWords,
    added: frozenset[str] = frozenset(),
) -> list[NameCheck]:
    """敘事與效果一致（4-L11）：三段文字提到的控制、元素、召喚詞要在 ``facts``
    （:func:`skill_facts`）找得到；``added``（閃現變化加上的效果）至少要被其中一段提到。"""
    fields = {"name_zh": text.name_zh, "concept": text.concept, "cast_flavor": text.cast_flavor}
    errors = [
        e for label, body in fields.items() for e in check_mentions(label, body, facts, words)
    ]
    errors += check_added(fields.values(), added, words, code="narrative.missing_added")
    return errors


def skill_summary(
    library: ContentLibrary,
    skill: SkillDef,
    *,
    taken: Collection[str] = (),
    theme: str | None = None,
    added: Collection[str] = (),
) -> dict[str, Any]:
    """給命名 prompt 的技能結構描述：全是中文名稱，沒有任何數值或代號。``effect_summary`` 是
    效果的精簡摘要（4-L11，:func:`effect_phrases`）；``added`` 是閃現變化加上的效果鍵，有的話列成
    ``added_effects``。"""
    primitives = list(dict.fromkeys(plain_name(e.type, library) for e in skill.effects))
    keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    summary: dict[str, Any] = {
        "skeleton": plain_name(skill.skeleton, library),
        "kind": skill.kind,
        "rarity": skill.rarity,
        "tier": skill.tier,
        "effects": primitives,
        "effect_summary": effect_phrases(library, skill),
        "shape": plain_name(skill.shape.type, library),
        "keywords": [plain_name(k, library) for k in keywords],
        "taken_names": sorted(taken)[:60],
    }
    elements = sorted(e.display_name for e in skill_elements(skill))
    if elements:
        summary["element"] = elements
    if theme is not None:
        summary["theme"] = theme
    if added:
        summary["added_effects"] = _added_names(library, added)
    return summary


def _added_names(library: ContentLibrary, added: Collection[str]) -> list[str]:
    out: list[str] = []
    for fact in sorted(added):
        kind, _, value = fact.partition(":")
        if kind == "status":
            out.append(f"狀態「{library.ruleset.status_def(value).name_zh}」")
        elif kind == "unit":
            out.append(f"召喚「{library.ruleset.summon_def(value).template.name_zh}」")
        else:
            out.append(plain_name(value, library))
    return list(dict.fromkeys(out))


def fallback_naming(
    library: ContentLibrary, skill: SkillDef, taken: Collection[str] = ()
) -> NamingText:
    """組合式名稱與模板敘事（和隨機組合器同樣的做法）：「元素・骨架」；撞名時加「（二）」之類。"""
    skeleton = plain_name(skill.skeleton, library)
    base = combined_skill_name(library, skill)
    name = base
    for index in range(2, 100):
        if name not in taken:
            break
        mark = _NUMERALS[index - 2] if index - 2 < len(_NUMERALS) else str(index)
        name = f"{base}（{mark}）"
    return NamingText(
        name_zh=name,
        concept=f"以{skeleton}為本的技能。",
        cast_flavor="力量依你的意志成形。",
    )


def _parse(raw: str) -> NamingText | str:
    text = clean_response(raw)
    try:
        return NamingText.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError):
        return "response.invalid"


def _feedback(errors: list[NameCheck], number: int, limit: int) -> str:
    payload = {
        "attempt": number,
        "max_attempts": limit,
        "errors": [{"code": e.code, "message": e.message} for e in errors],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def name_skill(
    client: LLMClient,
    library: ContentLibrary,
    skill: SkillDef,
    *,
    taken: Collection[str] = (),
    theme: str | None = None,
    max_attempts: int = DEFAULT_NAMING_ATTEMPTS,
    world: WorldStyle | None = None,
    before: SkillDef | None = None,
    words: EffectWords | None = None,
) -> NamingOutcome:
    """請 LLM 為 ``skill`` 命名與寫敘事（最多 ``max_attempts`` 次），失敗時用組合式名稱。

    ``taken`` 是已使用的技能名稱（含內容庫的技能），重名算錯誤。``LLMUnavailable`` 立即退回；
    ``LLMTimeout``／``LLMBadResponse`` 算一次嘗試。不改技能本身（見 :func:`apply_naming`）。

    4-L11：另外檢查敘事與效果一致（:func:`check_consistency`）；``before`` 是閃現變化前的技能，
    給了就要求文字提到變化加上的效果。``words`` 省略時讀 ``content/llm/effect_words.yaml``。"""
    style = world if world is not None else load_world_style()
    vocab = words if words is not None else load_effect_words()
    used = set(taken) | {s.name_zh for s in library.skills.values()}
    facts = skill_facts(library, skill)
    added: frozenset[str] = frozenset() if before is None else facts - skill_facts(library, before)
    summary = skill_summary(library, skill, taken=set(taken), theme=theme, added=added)
    retries = 0
    codes: list[str] = []
    previous: str | None = None
    feedback: str | None = None
    reason = ""
    for number in range(1, max_attempts + 1):
        messages = build_naming_messages(summary, previous=previous, errors=feedback, world=style)
        try:
            raw = client.complete(messages, json_schema=naming_schema(style))
        except LLMUnavailable as exc:
            codes.append("llm.unavailable")
            reason = f"llm.unavailable：{exc}"
            return _fallback(library, skill, used, codes, reason, attempts=number)
        except (LLMTimeout, LLMBadResponse) as exc:
            codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            reason = codes[-1]
            continue
        parsed = _parse(raw)
        if isinstance(parsed, str):
            codes.append(parsed)
            previous = raw
            feedback = _feedback(
                [NameCheck(parsed, "回應必須是只含三個欄位的 JSON。")], number, max_attempts
            )
            reason = parsed
            continue
        errors = check_naming(parsed, style.naming, used)
        errors += check_consistency(parsed, facts, vocab, added)
        if not errors:
            return NamingOutcome(
                parsed, "llm", number, tuple(dict.fromkeys(codes)), consistency_retries=retries
            )
        retries += any(e.code.endswith(CONSISTENCY_SUFFIXES) for e in errors)
        codes.extend(e.code for e in errors)
        previous = parsed.model_dump_json()
        feedback = _feedback(errors, number, max_attempts)
        reason = errors[0].code
    outcome = _fallback(
        library,
        skill,
        used,
        codes,
        f"用盡 {max_attempts} 次（最後：{reason}）",
        attempts=max_attempts,
    )
    return replace(outcome, consistency_retries=retries)


def _fallback(
    library: ContentLibrary,
    skill: SkillDef,
    taken: Collection[str],
    codes: list[str],
    reason: str,
    *,
    attempts: int,
) -> NamingOutcome:
    return NamingOutcome(
        fallback_naming(library, skill, taken),
        "fallback",
        attempts,
        tuple(dict.fromkeys(codes)),
        reason,
    )


def template_text(
    library: ContentLibrary, skill: SkillDef, taken: Collection[str] = ()
) -> SkillDef:
    """命名關閉時（Phase 4-L8b）：名稱與敘事都換成組合式名稱與模板敘事（:func:`fallback_naming`），
    不採用提議裡的 ``concept``／``cast_flavor``。``taken`` 是已用過的名稱（內容庫技能的名稱一併
    避開）；結構與數值不動。"""
    used = set(taken) | {s.name_zh for s in library.skills.values()}
    return apply_naming(skill, fallback_naming(library, skill, used))


def apply_naming(skill: SkillDef, text: NamingText) -> SkillDef:
    """只換名稱與敘事兩個文字欄位；結構與數值不動。"""
    narrative = skill.narrative.model_copy(
        update={"concept": text.concept, "cast_flavor": text.cast_flavor}
    )
    return skill.model_copy(update={"name_zh": text.name_zh, "narrative": narrative})
