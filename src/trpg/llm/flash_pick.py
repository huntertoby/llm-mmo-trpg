"""閃現與重閃的「挑選模式」LLM 一步（Phase PK-3；06 6.7、6.34.7 #165，提案第 2、3 節、7.7）。

格子與候選由程式做好（:mod:`trpg.skillgen.flash_pick`、``flash_offer.flash_slots``）：每格的類別、
混合、指定類別、大變化的加深／橋接、轉型保底、強度下限都已經定了，LLM 只能為每格挑一個候選並寫文字。

:func:`pick_variations` 一次呼叫回答全部格子（:mod:`trpg.llm.prompts.flash_pick`，
``flash-pick/2``）：

1. 回應先過 JSON 與 pydantic（多餘欄位拒絕）；``pick`` 不在該格範圍、固定格（轉型）挑了別的，都
   當沒回答（那一格用第一個）。
2. 描述 ``note_zh``：同 LF-2——本地修正、字元與長度、敘事與效果一致（4-L11）、古風詞、世界觀詞；
   不合格只丟描述（``flash.note_dropped.*``），不重試。PK-4：描述也照變化名擋**多字的老套詞**
   （加嚴詞組只看多字詞；單字不擋），不合格帶 ``<errors>`` 重問，用完次數就沒有描述。
3. 名稱 ``name_zh``（大變化、轉型的格子）：同 LF-2 的名稱檢查（字數、字元集、禁字、重名、世界觀詞、
   古風詞、「・」、加上的效果要提到），再加 **加嚴詞組只用多字的**（PK-3，06 6.34.7「閃現的變化名
   只擋多字的老套詞」，使用者題 3 B：單字的風、土、石、斬、劈不擋）。不合格的格子帶 ``<errors>``
   重問（最多 ``max_attempts`` 次，一份閃現 10 秒內）；仍不合格就不給名稱（引擎用組合式名稱）。
4. 連不上模型、逾時、格式壞掉用完次數 → 每格第一個（＝原本出題的那一個）、沒有文字。
5. PK-4：挑完用 :func:`~trpg.skillgen.flash_pick.keep_mix` 守住混合至少 2 類（借了別類候選、挑得
   類別太集中時，從後面的格子改回第一個、那一格不留文字，代碼 ``pick.mix_kept``）；紀錄的
   ``picks``／``accepted`` 是守住之後的結果。

結果寫成 ``FlashProposalRecord``（``picks``＝每格的位置、``accepted``＝每格選中的變化、``texts``），
隨一輪或世界日誌存下；重播用紀錄（:func:`trpg.skillgen.flash_pick.picks_by_key`），不呼叫 LLM。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world import load_world_style
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.consistency import (
    NameCheck,
    added_word_choices,
    check_added,
    check_mentions,
    check_world_terms,
    effect_phrases,
    multi_char_strict,
    skill_facts,
    strict_facts,
)
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.flash_repair import normalize_name, normalize_note
from trpg.llm.naming import check_archaic_text, check_name, skill_summary
from trpg.llm.prompts.flash_pick import (
    NOTE_MAX_CHARS,
    build_flash_pick_messages,
    flash_pick_schema,
    slot_key,
)
from trpg.llm.response import clean_response
from trpg.skillgen.flash_offer import FlashRequest
from trpg.skillgen.flash_pick import FlashSlot, SlotOption, keep_mix
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.flash_text import VariationText

__all__ = [
    "FLASH_PICK_BUDGET_S",
    "FlashPickResult",
    "SlotAnswer",
    "chosen_variations",
    "flash_pick_name_words",
    "mock_flash_pick_client",
    "pick_variations",
]

FLASH_PICK_BUDGET_S = 10.0
"""一份閃現請 LLM 的時間上限（秒；06 6.34.7「超過 10 秒改給模板版」）：用完就不再重問。"""
TRANSFORM_ZH = "轉型"
STRICT_NOTE = "strict_word"
"""PK-4：描述用了多字的老套詞（加嚴詞組）時的代碼（``note_zh.strict_word`` 重問；
``flash.note_dropped.strict_word`` 記在紀錄）。"""
_KIND_ZH = {"active": "主動", "passive": "被動", "reaction": "反應", "stance": "姿態"}

type Clock = Callable[[], float]


class SlotAnswer(BaseModel):
    """回應裡一格的答案（多餘欄位拒絕）。"""

    model_config = ConfigDict(extra="forbid")

    pick: int
    note_zh: str | None = None
    name_zh: str | None = None


@dataclass(frozen=True, slots=True)
class FlashPickResult:
    """:func:`pick_variations` 的結果（``trpg.llm.flash_propose`` 寫成紀錄）。"""

    positions: tuple[int, ...]
    texts: tuple[VariationText, ...]
    attempts: int
    codes: tuple[tuple[str, ...], ...]
    answered: int
    """LLM 有效回答（pick 合格）的格子數。"""
    reason: str | None
    seconds: float
    raws: tuple[str, ...] = field(default=(), compare=False, repr=False)


def flash_pick_name_words(words: EffectWords | None = None) -> EffectWords:
    """閃現變化名用的詞表（PK-3）：加嚴詞組只留多字的詞（:func:`multi_char_strict`）。"""
    return multi_char_strict(words if words is not None else load_effect_words())


# ---------------------------------------------------------------------------
# prompt 的資料
# ---------------------------------------------------------------------------


def _usage_payload(library: ContentLibrary, request: FlashRequest) -> dict[str, Any]:
    usage = request.usage
    names = {k.id: k.name_zh for k in library.keywords.keywords}
    top = sorted(usage.target_keywords.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "uses": usage.uses,
        "avg_targets_permille": usage.avg_targets_permille,
        "avg_distance_permille": usage.avg_distance_permille,
        "kills": usage.kills,
        "target_keywords": [{"keyword": names.get(k, k), "times": n} for k, n in top],
    }


def _card(  # noqa: PLR0917 — 一張候選卡的資料
    library: ContentLibrary,
    option: SlotOption,
    index: int,
    before_facts: frozenset[str],
    words: EffectWords,
    slot_category: str | None = None,
) -> dict[str, Any]:
    after = option.skill
    card: dict[str, Any] = {"pick": index, "change": option.summary_zh}
    category = option.variation.category
    if (
        slot_category is not None
        and category != slot_category
        and option.variation.source != "transform"
    ):
        # PK-4：不指定類別時借來的別類候選，標出它自己的類別
        names = {c.id: c.name_zh for c in library.flash.categories}
        card["category"] = names.get(category, category)
    if option.variation.source == "transform":
        card["kind"] = _KIND_ZH.get(after.kind, after.kind)
    card["effect_summary"] = effect_phrases(library, after)
    added = added_word_choices(skill_facts(library, after) - before_facts, words)
    if added:
        card["words"] = added
    if option.weaker:
        card["weaker"] = True
    return card


def _category_zh(library: ContentLibrary, slot: FlashSlot) -> str:
    """格子類別的中文名（轉型保底那一格寫「轉型」）。"""
    if slot.fixed:
        return TRANSFORM_ZH
    found = {c.id: c.name_zh for c in library.flash.categories}
    return found.get(slot.category, slot.category)


def _slots_payload(
    library: ContentLibrary, slots: Sequence[FlashSlot], before: SkillDef, words: EffectWords
) -> list[dict[str, Any]]:
    before_facts = skill_facts(library, before)
    out: list[dict[str, Any]] = []
    for slot in slots:
        row: dict[str, Any] = {
            "slot": slot_key(slot.index),
            "category": _category_zh(library, slot),
            "name": slot.named,
        }
        if slot.fixed:
            row["fixed"] = True
        row["candidates"] = [
            _card(library, c, i, before_facts, words, slot.category)
            for i, c in enumerate(slot.candidates)
        ]
        out.append(row)
    return out


def _request_payload(request: FlashRequest, major: bool) -> dict[str, Any]:
    style = load_world_style()
    return {
        "flash_nth": request.nth,
        "major": major,
        "reflash": request.slot is not None,
        "category": request.category,
        "style": style.style_payload(request.region),
        "weapon": request.weapon_zh or "依技能需求",
    }


# ---------------------------------------------------------------------------
# 檢查
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Checker:
    """描述與名稱的檢查（見模組說明第 2、3 點）。"""

    library: ContentLibrary
    request: FlashRequest
    before: SkillDef
    words: EffectWords
    name_words: EffectWords
    library_names: frozenset[str]

    def note(
        self, option: SlotOption, raw: str | None
    ) -> tuple[str | None, list[str], NameCheck | None]:
        """描述：合格的文字、修正與丟棄碼、要不要重問（PK-4：只有多字老套詞會重問）。"""
        if raw is None:
            return None, [], None
        text, codes = normalize_note(raw)
        problem = _note_problem(text)
        if problem is None:
            problems = self._note_checks(option, text)
            if problems:
                problem = problems[0].code.removeprefix("note_zh.")
        if problem is not None:
            return None, [*codes, f"flash.note_dropped.{problem}"], None
        strict = self._note_strict(option, text)
        if strict is not None:
            return None, [*codes, f"flash.note_dropped.{STRICT_NOTE}"], strict
        return text, list(codes), None

    def _note_strict(self, option: SlotOption, note: str) -> NameCheck | None:
        """PK-4（06 6.34.7「閃現的變化名與描述只擋多字的老套詞」，玩法 PM 4.1.25 題 3 B）：描述也照
        變化名的加嚴詞組（只看多字詞，:func:`flash_pick_name_words`）比對；不符合就帶錯誤重問。"""
        facts = strict_facts(self.library, option.skill)
        found = check_mentions("note_zh", note, facts, self.name_words, strict=True)
        if not found:
            return None
        return NameCheck(f"note_zh.{STRICT_NOTE}", found[0].message)

    def _note_checks(self, option: SlotOption, note: str) -> list[NameCheck]:
        style = load_world_style()
        archaic = check_archaic_text(
            "note_zh", note, style.naming, archaic_ok=style.archaic_ok(self.request.region)
        )
        facts = skill_facts(self.library, option.skill)
        before = skill_facts(self.library, self.before)
        problems = check_mentions("note_zh", note, facts, self.words)
        problems += check_added([note], facts - before, self.words, code="note_zh.missing_added")
        problems += check_world_terms(None, {"note_zh": note}, style.naming.world_terms)
        return problems + archaic

    def name(
        self, option: SlotOption, raw: str, note: str | None, taken: Collection[str]
    ) -> tuple[str | None, list[NameCheck], list[str]]:
        text, codes = normalize_name(raw)
        style = load_world_style()
        used = self.library_names | frozenset(taken)
        problems = check_name(
            text, style.naming, used, archaic_ok=style.archaic_ok(self.request.region)
        )
        if text.count("・") > 1 or text.startswith("・") or text.endswith("・"):
            problems.append(
                NameCheck("name_zh.dots", "name_zh 的「・」最多一個，不放在開頭或結尾。")
            )
        if not problems:
            facts = strict_facts(self.library, option.skill)
            problems = check_mentions("name_zh", text, facts, self.name_words, strict=True)
            added = skill_facts(self.library, option.skill) - skill_facts(self.library, self.before)
            texts = [text] if note is None else [text, note]
            problems += check_added(texts, added, self.words, code="name_zh.missing_added")
        return (None if problems else text), problems, list(codes)


_NOTE_CHARS = re.compile(r"^[一-鿿　-〿＀-￯・—…‘-”、。，；：！？（）「」『』《》]+$")
_ENGLISH = re.compile(r"[A-Za-z_]")


def _note_problem(note: str) -> str | None:
    """描述的字元與長度問題（同 LF-2 ``flash_propose._note_problem``）。"""
    if _ENGLISH.search(note):
        return "english"
    if len(note) > NOTE_MAX_CHARS:
        return "too_long"
    if not _NOTE_CHARS.match(note):
        return "charset"
    return None


# ---------------------------------------------------------------------------
# 重試迴圈
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Slot:
    """一格目前的答案。``settled``＝不用再問（小變化格回答過、大變化格名稱也合格）。"""

    position: int = 0
    note: str | None = None
    name: str | None = None
    answered: bool = False
    settled: bool = False


@dataclass(slots=True)
class _Loop:
    client: LLMClient
    library: ContentLibrary
    request: FlashRequest
    slots: Sequence[FlashSlot]
    checker: _Checker
    messages: Callable[[str | None, str | None], list[Any]]
    schema: dict[str, Any]
    state: list[_Slot]
    codes: list[tuple[str, ...]] = field(default_factory=list)
    raws: list[str] = field(default_factory=list)
    previous: str | None = None
    feedback: str | None = None
    reason: str | None = None

    def attempt(self, number: int, limit: int) -> bool:
        """做一次呼叫；回傳要不要再問。"""
        try:
            raw = self.client.complete(
                self.messages(self.previous, self.feedback), json_schema=self.schema
            )
        except (LLMUnavailable, LLMTimeout, LLMBadResponse) as exc:
            code = {
                LLMUnavailable: "llm.unavailable",
                LLMTimeout: "llm.timeout",
                LLMBadResponse: "llm.bad_response",
            }[type(exc)]
            self.codes.append((code,))
            if isinstance(exc, LLMUnavailable):
                self.reason = f"{code}：{exc}"
                return False
            return True
        self.raws.append(raw)
        answers, issues = _parse(raw, len(self.slots))
        errors: list[NameCheck] = list(issues)
        notes: list[str] = []
        for i, answer in sorted(answers.items()):
            errors += self._take(i, answer, notes)
        codes = [e.code for e in errors] + notes
        self.codes.append(tuple(dict.fromkeys(codes)))
        if all(s.settled for s in self.state):
            return False
        self.previous = raw
        self.feedback = json.dumps(
            {
                "attempt": number,
                "max_attempts": limit,
                "errors": [{"code": e.code, "message": e.message} for e in errors],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return True

    def _take(self, i: int, answer: SlotAnswer, notes: list[str]) -> list[NameCheck]:
        slot, state = self.slots[i], self.state[i]
        if state.settled:
            return []
        label = slot_key(i)
        size = len(slot.candidates)
        if not 0 <= answer.pick < size or (slot.fixed and answer.pick != 0):
            return [NameCheck("pick.out_of_range", f"{label} 的 pick 要是 0～{size - 1}。")]
        option = slot.candidates[answer.pick]
        note, note_codes, strict = self.checker.note(option, answer.note_zh)
        notes += note_codes
        state.position, state.note, state.answered = answer.pick, note, True
        errors = self._name(i, option, answer, notes) if slot.named else []
        if strict is not None:  # PK-4：描述用了多字老套詞，這一格重問（用完次數就沒有描述）
            errors.append(NameCheck(strict.code, f"{label}：{strict.message}"))
        state.settled = not errors
        return errors

    def _name(
        self, i: int, option: SlotOption, answer: SlotAnswer, notes: list[str]
    ) -> list[NameCheck]:
        """大變化、轉型格的名稱：合格寫進 ``state.name``；不合格回傳要重問的錯誤。"""
        state = self.state[i]
        if answer.name_zh is None:  # 不重問（Mock 不寫名稱）；引擎用「{前綴}・{原名}」
            notes.append("flash.name_dropped.missing")
            return []
        taken = [s.name for j, s in enumerate(self.state) if s.name is not None and j != i]
        name, problems, fixed = self.checker.name(option, answer.name_zh, state.note, taken)
        notes += fixed
        if name is None:
            return [NameCheck(p.code, f"{slot_key(i)}：{p.message}") for p in problems]
        state.name = name
        return []


def _parse(raw: str, count: int) -> tuple[dict[int, SlotAnswer], list[NameCheck]]:
    try:
        data = json.loads(clean_response(raw))
    except json.JSONDecodeError:
        return {}, [NameCheck("response.invalid", "回應必須是 JSON。")]
    if not isinstance(data, dict):
        return {}, [NameCheck("response.invalid", "最外層必須是物件 {s0: {...}, ...}。")]
    out: dict[int, SlotAnswer] = {}
    issues: list[NameCheck] = []
    for i in range(count):
        item = data.get(slot_key(i))
        if item is None:
            issues.append(NameCheck("pick.missing", f"缺少 {slot_key(i)}。"))
            continue
        try:
            out[i] = SlotAnswer.model_validate(item)
        except ValidationError:
            issues.append(
                NameCheck("response.invalid", f"{slot_key(i)} 只能有 pick、note_zh、name_zh。")
            )
    return out, issues


def pick_variations(
    client: LLMClient,
    library: ContentLibrary,
    request: FlashRequest,
    slots: Sequence[FlashSlot],
    before: SkillDef,
    *,
    major: bool,
    max_attempts: int = 3,
    clock: Clock = time.perf_counter,
    budget_s: float = FLASH_PICK_BUDGET_S,
    words: EffectWords | None = None,
) -> FlashPickResult:
    """請 LLM 為每格挑一個候選並寫文字（見模組說明）。沒有格子時不呼叫。"""
    if not slots:
        return FlashPickResult((), (), 0, (), 0, None, 0.0)
    vocab = words if words is not None else load_effect_words()
    checker = _Checker(
        library,
        request,
        before,
        vocab,
        flash_pick_name_words(vocab),
        frozenset(s.name_zh for s in library.skills.values()),
    )
    skill = skill_summary(library, before)
    skill.pop("taken_names", None)
    payload = _slots_payload(library, slots, before, vocab)

    def messages(previous: str | None, errors: str | None) -> list[Any]:
        return list(
            build_flash_pick_messages(
                skill=skill,
                usage=_usage_payload(library, request),
                held_keywords=request.held_keywords,
                request=_request_payload(request, major),
                slots=payload,
                previous=previous,
                errors=errors,
            )
        )

    schema = flash_pick_schema([len(s.candidates) for s in slots], [s.named for s in slots])
    loop = _Loop(
        client, library, request, slots, checker, messages, schema, [_Slot() for _ in slots]
    )
    start = clock()
    for number in range(1, max_attempts + 1):
        if not loop.attempt(number, max_attempts) or clock() - start >= budget_s:
            break
    # PK-4：借別類候選後，混合至少 2 類由程式守住（不夠時從後面的格子改回第一個，那一格不留文字）
    need = library.flash.pricing.rule(request.category is not None).min_categories
    positions = keep_mix(slots, [s.position for s in loop.state], need)
    codes = list(loop.codes)
    texts = []
    for slot, state, position in zip(slots, loop.state, positions, strict=True):
        if position != state.position:
            codes.append(("pick.mix_kept",))
            continue
        if state.note is None and state.name is None:
            continue
        key = slot.candidates[state.position].variation.key()
        texts.append(VariationText(key=key, name_zh=state.name, note_zh=state.note))
    return FlashPickResult(
        positions=positions,
        texts=tuple(sorted(texts, key=lambda t: t.key)),
        attempts=len(loop.codes),
        codes=tuple(codes),
        answered=sum(s.answered for s in loop.state),
        reason=loop.reason,
        seconds=clock() - start,
        raws=tuple(loop.raws),
    )


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------


def mock_flash_pick_client(
    slots: Sequence[FlashSlot], *, index: int = 0, attempts: int = 3
) -> MockLLMClient:
    """Mock 挑選（不需網路與金鑰）：每格永遠挑 ``index``（超出範圍時照填，用來測退回；固定格照填），
    不寫描述與名稱（同 LF-2 的 Mock 不寫文字，名稱照「{前綴}・{原名}」）。"""
    body = json.dumps({slot_key(s.index): {"pick": index} for s in slots}, ensure_ascii=False)
    return MockLLMClient([body] * attempts)


def chosen_variations(
    slots: Sequence[FlashSlot], positions: Sequence[int]
) -> tuple[Variation, ...]:
    """每格選中的變化（位置超出範圍或固定格時用第一個）。"""
    out: list[Variation] = []
    for slot, position in zip(slots, positions, strict=True):
        ok = 0 <= position < len(slot.candidates) and not (slot.fixed and position)
        out.append(slot.candidates[position if ok else 0].variation)
    return tuple(out)
