"""閃現變化的 LLM 提議（Phase 3W-7；設計 ``docs/design/06-技能.md`` 6.34.3、6.34.7）。

選項來源 :class:`LlmFlashSource` 可替換 3W-1 的預設來源（``UsageSource``）。
一次呼叫請模型回傳一批（不指定 4 個、指定類別 3 個）**變化**——只有類別、模板與必要的關鍵字／元素／
形狀，**沒有任何數值**（守則 3）：

1. 回應先經 :func:`~trpg.llm.response.clean_response`、JSON 解析與 pydantic（多餘欄位、數值欄位、
   英文代號都拒絕）。
2. 每一項再由 :class:`~trpg.skillgen.flash_catalog.FlashCatalog` 檢查：類別與模板必須是這一次可用的
   （形態、種族這類原語不是模板，直接拒絕）、參數必須在模板的選單內；最後由引擎真的套用一次
   （:func:`~trpg.skillgen.flash_offer.try_variation`），套不上就拒絕。
3. 不合格的項目帶錯誤回饋重試（最多 ``max_attempts`` 次，合格的累積）；仍不足的數量與類別由
   :func:`~trpg.skillgen.flash_offer.make_offer` 用資料順序的模板補滿（4-L5 的「失敗退回模板」）。
   轉型保底
   仍由資料決定，不交給模型。

結果（提議的變化、錯誤代碼、prompt 版本號）寫成 :class:`FlashProposalRecord`，隨一輪存下來；重播用
:class:`RecordedSource` 直接取用，**不呼叫 LLM**。名稱由 :func:`name_offer` 交給 4-L7 命名步驟（命名
關閉時沿用「{前綴}・{原名}」）。

4-L11：``note_zh`` 另外檢查敘事與效果一致（提到的控制、元素、召喚詞要在變化後的技能找得到、變化加上
的效果要提到）與世界觀詞用量；不過的項目帶錯誤碼重試。命名時把變化前的技能交給命名步驟，名稱與敘事
同樣要提到變化加上的效果。

LF-2（減少白白重問）：要的數量不超過目錄的（模板, 參數）組合數；可修的錯本地修正
（:mod:`trpg.llm.flash_repair`，``flash.repaired.*``），重複的直接丟掉；``note_zh`` 不合格只丟說明
（``flash.note_dropped.*``），不再為說明重試，只有結構問題才為還缺的數量重試；大變化題目每項可順便
取 ``name_zh``（:func:`name_checker` 過了就直接用，不另呼叫命名步驟，``flash.name_dropped.*`` 時照
LF-1 另外命名）。
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world import load_world_style
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import LLMClient, MockLLMClient, OpenAICompatClient
from trpg.llm.config import LLMConfig
from trpg.llm.consistency import (
    NameCheck,
    added_word_choices,
    check_added,
    check_mentions,
    check_world_terms,
    skill_facts,
)
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.flash_repair import normalize_name, normalize_note, repair_fields
from trpg.llm.naming import apply_naming, check_archaic_text, check_name, name_skill
from trpg.llm.prompts.flash import (
    FLASH_PROMPT_VERSION,
    NOTE_MAX_CHARS,
    build_flash_messages,
    flash_schema,
)
from trpg.llm.prompts.naming import NAMING_PROMPT_VERSION
from trpg.llm.propose import LLM_ERROR_CODES, AttemptRecord
from trpg.llm.response import clean_response
from trpg.shared.rng import Rng
from trpg.skillgen.flash_catalog import FlashCatalog, build_catalog
from trpg.skillgen.flash_offer import (
    FlashOffer,
    FlashOptionSource,
    FlashRequest,
    UsageSource,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import Variation, seed_tag, slot_is_major
from trpg.skillgen.flash_text import VariationText, clean_note, text_map

__all__ = [
    "DEFAULT_FLASH_ATTEMPTS",
    "FlashNameRecord",
    "FlashProposalRecord",
    "FlashProposalStats",
    "Judged",
    "LlmFlashSource",
    "RecordedSource",
    "judge_items",
    "mock_flash_client",
    "mock_flash_source",
    "name_checker",
    "name_offer",
    "name_texts",
    "note_checker",
    "note_words",
    "propose_variations",
    "select_flash_source",
]

DEFAULT_FLASH_ATTEMPTS = 3
"""同 4-L5／使用者決定 #5：每個題目最多 3 次（``config/llm.toml`` 的 ``max_retries``）。"""
type Clock = Callable[[], float]
type NoteCheck = Callable[[Variation, str], list[NameCheck]]
"""（變化, note_zh）→ 一致性與世界觀詞的錯誤（4-L11）。"""
type FlashNameCheck = Callable[[Variation, str, str | None, Collection[str]], list[NameCheck]]
"""（變化, name_zh, 同一項合格的 note_zh, 這一題已取的名稱）→ 名稱的錯誤（LF-2）。"""
type ProposalSource = Literal["llm", "partial", "template"]
"""``llm``：模型湊滿了題目要的數量；``partial``：只有一部分，其餘用模板補；``template``：全部退回模板。"""

_NOTE_CHARS = re.compile(r"^[一-鿿　-〿＀-￯・—…‘-”、。，；：！？（）「」『』《》]+$")
_ENGLISH = re.compile(r"[A-Za-z_]")


class _Item(BaseModel):
    """提議裡的一個變化（多餘欄位——例如數值——直接拒絕）。"""

    model_config = ConfigDict(extra="forbid")

    category: str
    template: str
    keyword: str | None = None
    element: str | None = None
    shape: str | None = None
    note_zh: str | None = None
    name_zh: str | None = None
    """LF-2：大變化題目順便取的名稱（小變化題目忽略）。"""


@dataclass(frozen=True, slots=True)
class _Issue:
    """一個被拒絕的項目（``index`` 為 ``None`` ＝ 整份回應有問題）。"""

    index: int | None
    code: str
    message: str
    template: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {"index": self.index, "code": self.code, "message": self.message}


# ---------------------------------------------------------------------------
# 解析與驗證
# ---------------------------------------------------------------------------


def _parse(text: str) -> tuple[list[object], list[_Issue]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [_Issue(None, "flash.not_json", f"不是合法的 JSON：{exc.msg}")]
    if not isinstance(data, dict):
        return [], [_Issue(None, "flash.schema", '最外層必須是物件 {"variations": [...]}')]
    issues: list[_Issue] = []
    extra = sorted(k for k in data if k != "variations")
    if extra:
        issues.append(_Issue(None, "flash.extra_field", f"多餘的欄位：{', '.join(extra)}"))
    items = data.get("variations")
    if not isinstance(items, list) or not items:
        issues.append(_Issue(None, "flash.schema", "variations 必須是非空的陣列"))
        return [], issues
    return list(items), issues


def _item_issue(index: int, raw: object) -> tuple[_Item | None, _Issue | None]:
    try:
        return _Item.model_validate(raw), None
    except ValidationError as exc:
        kinds = {e["type"] for e in exc.errors()}
        if "extra_forbidden" in kinds:
            fields = sorted(
                str(e["loc"][-1]) for e in exc.errors() if e["type"] == "extra_forbidden"
            )
            msg = f"多餘的欄位（不要填數值或自創欄位）：{', '.join(fields)}"
            return None, _Issue(index, "flash.extra_field", msg)
        return None, _Issue(index, "flash.schema", "每一項需要字串的 category 與 template")


def _note_problem(note: str) -> str | None:
    """說明的字元與長度問題（LF-2：只丟說明，代碼字尾）。"""
    if _ENGLISH.search(note):
        return "english"
    if len(note) > NOTE_MAX_CHARS:
        return "too_long"
    if not _NOTE_CHARS.match(note):
        return "charset"
    return None


def _repair(item: _Item, catalog: FlashCatalog) -> tuple[_Item, tuple[str, ...]]:
    fields: dict[str, str | None] = {
        "category": item.category,
        "template": item.template,
        "keyword": item.keyword,
        "element": item.element,
        "shape": item.shape,
    }
    fixed, codes = repair_fields(fields, catalog)
    if not codes:
        return item, ()
    return item.model_copy(update=fixed), codes


def _param_issue(index: int, item: _Item, catalog: FlashCatalog) -> _Issue | None:
    entry = catalog.entry(item.template)
    assert entry is not None
    for name, choices in (
        ("keyword", entry.keywords),
        ("element", entry.elements),
        ("shape", entry.shapes),
    ):
        given = getattr(item, name)
        if choices and given is None:
            msg = f"模板 {item.template} 需要填 {name}，可選：{', '.join(choices)}"
            return _Issue(index, "flash.param_missing", msg, item.template)
        if choices and given not in choices:
            msg = f"模板 {item.template} 的 {name} 只能是：{', '.join(choices)}"
            return _Issue(index, "flash.param_not_offered", msg, item.template)
        if not choices and given is not None:
            msg = f"模板 {item.template} 不用填 {name}（填 null）"
            return _Issue(index, "flash.param_unused", msg, item.template)
    return None


def _structure_issue(
    index: int, item: _Item, catalog: FlashCatalog, library: ContentLibrary
) -> _Issue | None:
    table = library.flash
    if all(c.id != item.category for c in table.categories):
        return _Issue(index, "flash.unknown_category", f"沒有類別 {item.category}", item.template)
    if item.category not in catalog.categories:
        msg = f"這一次不能用類別 {item.category}（可用：{', '.join(catalog.categories)}）"
        return _Issue(index, "flash.category_not_available", msg, item.template)
    entry = catalog.entry(item.template)
    if entry is None:
        known = (
            {t.id for t in table.minor}
            | {t.id for t in table.major}
            | {t.id for t in table.extra_major}
            | {t.id for t in table.transforms}
        )
        code = (
            "flash.template_not_available" if item.template in known else "flash.unknown_template"
        )
        return _Issue(index, code, f"模板 {item.template} 不在 <catalog> 內", item.template)
    if entry.category != item.category:
        msg = f"模板 {item.template} 屬於類別 {entry.category}，不是 {item.category}"
        return _Issue(index, "flash.category_mismatch", msg, item.template)
    return _param_issue(index, item, catalog)


def _note_text(
    variation: Variation, note: str | None, note_check: NoteCheck | None
) -> tuple[str | None, list[str]]:
    """LF-2：說明先本地修正，再檢查字元、長度、一致性；不合格只丟說明（``flash.note_dropped.*``），
    不拒絕變化、不重試。"""
    if note is None:
        return None, []
    text, codes = normalize_note(note)
    problem = _note_problem(text)
    if problem is None and note_check is not None:
        problems = note_check(variation, text)
        if problems:
            problem = problems[0].code.removeprefix("note_zh.")
    if problem is not None:
        return None, [*codes, f"flash.note_dropped.{problem}"]
    return text, list(codes)


def _name_text(
    variation: Variation,
    name: str | None,
    note: str | None,
    name_check: FlashNameCheck | None,
    taken: Collection[str],
) -> tuple[str | None, list[str]]:
    """LF-2 第 7 點：大變化題目順便取的名稱；本地修正後檢查，不合格只丟名稱
    （``flash.name_dropped.*``，之後照 LF-1 另外呼叫命名步驟）。"""
    if name is None or name_check is None or variation.source == "minor":
        return None, []
    text, codes = normalize_name(name)
    problems = name_check(variation, text, note, taken)
    if problems:
        return None, [*codes, f"flash.name_dropped.{problems[0].code.removeprefix('name_zh.')}"]
    return text, list(codes)


@dataclass(slots=True)
class Judged:
    """:func:`judge_items` 的附帶結果（LF-2）：本地修正與丟掉說明、名稱的代碼（不算錯，不重試），
    以及合格項目的說明與名稱（鍵 ＝ 變化的穩定鍵）。"""

    codes: list[str] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)


def _judge_one(
    index: int,
    raw: object,
    *,
    catalog: FlashCatalog,
    library: ContentLibrary,
    check: Callable[[Variation], bool],
    taken: set[str],
    judged: Judged,
) -> tuple[_Item | None, Variation | None, _Issue | None]:
    item, issue = _item_issue(index, raw)
    if item is None:
        return None, None, issue
    item, fixed = _repair(item, catalog)
    judged.codes += fixed
    issue = _structure_issue(index, item, catalog, library)
    if issue is not None:
        return item, None, issue
    variation = catalog.resolve(item.template, item.keyword, item.element, item.shape)
    if variation is None:
        return item, None, _Issue(index, "flash.param_not_offered", "參數不在選單內", item.template)
    if variation.key() in taken:
        judged.codes.append("flash.repaired.duplicate")  # 重複的直接丟掉，不算錯
        return item, None, None
    if not check(variation):
        return item, None, _Issue(index, "flash.not_applicable", "套不上這招", item.template)
    return item, variation, None


def judge_items(
    items: Sequence[object],
    catalog: FlashCatalog,
    library: ContentLibrary,
    check: Callable[[Variation], bool],
    taken: set[str],
    *,
    note_check: NoteCheck | None = None,
    notes: dict[str, str] | None = None,
    name_check: FlashNameCheck | None = None,
    judged: Judged | None = None,
) -> tuple[list[Variation], list[_Issue]]:
    """逐項檢查提議：回傳合格的變化（依回應順序、已去重、引擎真的套得上）與被拒絕的項目。
    ``taken`` 是已經合格的變化鍵（會更新）。

    LF-2：可修的錯先本地修正（:mod:`trpg.llm.flash_repair`；類別、單一參數、多填的參數、空白），
    重複的直接丟掉；只有結構問題（不在目錄、參數不在選單、套不上、格式）才算被拒絕。說明
    （``note_check``，4-L11 的一致性與古風詞）與名稱（``name_check``，只有大變化題目）不合格時只丟
    文字。修正與丟文字的代碼、合格的說明與名稱記進 ``judged``；``notes``（LF-1 的舊介面）給了也
    收下說明。"""
    judged = judged if judged is not None else Judged()
    accepted: list[Variation] = []
    issues: list[_Issue] = []
    for index, raw in enumerate(items):
        item, variation, issue = _judge_one(
            index, raw, catalog=catalog, library=library, check=check, taken=taken, judged=judged
        )
        if issue is not None:
            issues.append(issue)
        if item is None or variation is None:
            continue
        key = variation.key()
        taken.add(key)
        accepted.append(variation)
        note, codes = _note_text(variation, item.note_zh, note_check)
        name, name_codes = _name_text(
            variation, item.name_zh, note, name_check, judged.names.values()
        )
        judged.codes += codes + name_codes
        if note is not None:
            judged.notes[key] = note
            if notes is not None:
                notes[key] = note
        if name is not None:
            judged.names[key] = name
    return accepted, issues


def note_checker(
    library: ContentLibrary,
    request: FlashRequest,
    before: SkillDef,
    words: EffectWords | None = None,
) -> NoteCheck:
    """``note_zh`` 的一致性與世界觀詞檢查（4-L11）：提到的詞要在變化後的技能找得到、變化加上的效果要
    提到、世界觀詞不超過上限（``naming.world_terms.text_max``）。6L-2b：另外檢查古風詞
    （:func:`~trpg.llm.naming.check_archaic_text`，照原技能取得地點的區域 ``request.region``）。"""
    vocab = words if words is not None else load_effect_words()
    style = load_world_style()
    rules = style.naming.world_terms
    archaic_ok = style.archaic_ok(request.region)
    before_facts = skill_facts(library, before)

    def run(variation: Variation, note: str) -> list[NameCheck]:
        archaic = check_archaic_text("note_zh", note, style.naming, archaic_ok=archaic_ok)
        option = try_variation(library, request, variation)
        if option is None:
            return archaic
        facts = skill_facts(library, option.skill)
        problems = check_mentions("note_zh", note, facts, vocab)
        problems += check_added([note], facts - before_facts, vocab, code="note_zh.missing_added")
        problems += check_world_terms(None, {"note_zh": note}, rules)
        return problems + archaic

    return run


def name_checker(
    library: ContentLibrary,
    request: FlashRequest,
    before: SkillDef,
    words: EffectWords | None = None,
) -> FlashNameCheck:
    """LF-2 第 7 點：提議時順便取的名稱的檢查，和命名步驟對名稱的要求一樣——字數、字元集、禁字、
    重名（內容庫與這一題已取的）、世界觀詞、古風詞（照原技能的區域，#126）；名稱提到的詞要在變化後
    的技能找得到；變化加上的效果要被名稱或同一項的說明提到（命名步驟是名稱或兩段敘事）。"""
    vocab = words if words is not None else load_effect_words()
    style = load_world_style()
    archaic_ok = style.archaic_ok(request.region)
    library_names = frozenset(s.name_zh for s in library.skills.values())
    before_facts = skill_facts(library, before)

    def run(
        variation: Variation, name: str, note: str | None, taken: Collection[str]
    ) -> list[NameCheck]:
        used = library_names | frozenset(taken)
        problems = check_name(name, style.naming, used, archaic_ok=archaic_ok)
        if problems:
            return problems
        option = try_variation(library, request, variation)
        if option is None:
            return [NameCheck("name_zh.not_applicable", "套不上這招")]
        facts = skill_facts(library, option.skill)
        problems = check_mentions("name_zh", name, facts, vocab)
        texts = [name] if note is None else [name, note]
        return problems + check_added(
            texts, facts - before_facts, vocab, code="name_zh.missing_added"
        )

    return run


def note_words(
    library: ContentLibrary,
    request: FlashRequest,
    before: SkillDef,
    catalog: FlashCatalog,
    words: EffectWords | None = None,
) -> dict[str, tuple[str, ...]]:
    """LF-2 第 5 點：目錄裡每個變化「會加上的效果」要用的詞（引擎先算 ``skill_facts`` 差集，寫成可
    直接引用的詞，每組以「／」分隔），鍵 ＝ 變化的穩定鍵；沒有要求的變化不列。寫進 prompt 的
    ``<catalog>``，減少 ``note_zh.missing_added``。"""
    vocab = words if words is not None else load_effect_words()
    before_facts = skill_facts(library, before)
    out: dict[str, tuple[str, ...]] = {}
    for key in sorted(catalog.pool):
        option = try_variation(library, request, catalog.pool[key])
        if option is None:
            continue
        choices = added_word_choices(skill_facts(library, option.skill) - before_facts, vocab)
        if choices:
            out[key] = tuple(choices)
    return out


# ---------------------------------------------------------------------------
# 重試迴圈
# ---------------------------------------------------------------------------


class FlashNameRecord(BaseModel):
    """大變化／轉型選項的命名（4-L7）結果。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: str
    source: Literal["llm", "fallback"]
    attempts: int
    codes: tuple[str, ...] = ()
    naming_prompt_version: str = NAMING_PROMPT_VERSION
    consistency_retries: int = 0
    """因一致性或世界觀詞檢查（4-L11）不過而重試的次數。"""


class FlashProposalRecord(BaseModel):
    """一次變化提議的紀錄（隨一輪存下來；重播直接用 ``accepted``，不再呼叫 LLM）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tag: str
    """種子標籤 ``flash/<原技能>/<第幾次>/<重閃次數>[/<指定類別>]``。"""
    prompt_version: str = FLASH_PROMPT_VERSION
    source: ProposalSource = "template"
    wanted: int = 0
    attempts: int = 0
    codes: tuple[tuple[str, ...], ...] = ()
    """每次嘗試被拒絕的錯誤代碼（整份回應的與各項的）。"""
    accepted: tuple[Variation, ...] = ()
    rejected: tuple[str, ...] = ()
    """被拒絕的模板 ID（沒有模板的整份回應錯誤不列）。"""
    reason: str | None = None
    seconds: float = 0.0
    """耗時（只供報表，不進任何確定性狀態）。"""
    names: tuple[FlashNameRecord, ...] = ()
    """大變化／轉型選項的命名結果（:func:`name_offer`、:func:`name_texts`；命名關閉時為空）。"""
    texts: tuple[VariationText, ...] = Field(default=(), exclude_if=lambda v: not v)
    """LF-1：玩家看得到的名稱與描述（依變化的鍵排序；出題時引擎再檢查一次才掛上）。"""


@dataclass(slots=True)
class _Loop:
    client: LLMClient
    library: ContentLibrary
    request: FlashRequest
    before: SkillDef
    catalog: FlashCatalog
    major: bool
    want: int
    max_attempts: int
    clock: Clock
    note_check: NoteCheck | None = None
    name_check: FlashNameCheck | None = None
    words: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    """目錄裡每個變化會加上的效果詞（LF-2，:func:`note_words`）。"""
    taken: set[str] = field(default_factory=set)
    accepted: list[Variation] = field(default_factory=list)
    judged: Judged = field(default_factory=Judged)
    records: list[AttemptRecord] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    previous: str | None = None
    feedback: str | None = None
    reason: str | None = None

    def _check(self, variation: Variation) -> bool:
        return try_variation(self.library, self.request, variation) is not None

    def attempt(self, number: int) -> bool:
        """做一次嘗試；回傳是否應該繼續重試。"""
        remaining = self.want - len(self.accepted)
        messages = build_flash_messages(
            self.library,
            self.request,
            self.before,
            self.catalog,
            count=remaining,
            major=self.major,
            already=[f"{v.category}/{v.template}" for v in self.accepted],
            previous_proposal=self.previous,
            errors=self.feedback,
            note_words=self.words,
        )
        schema = flash_schema(self.catalog, remaining, major=self.major)
        start = self.clock()
        try:
            raw = self.client.complete(messages, json_schema=schema)
        except (LLMUnavailable, LLMTimeout, LLMBadResponse) as exc:
            code = LLM_ERROR_CODES[type(exc)]
            self.records.append(AttemptRecord((code,), self.clock() - start))
            if isinstance(exc, LLMUnavailable):
                self.reason = f"{code}：{exc}"
                return False
            return True
        text = clean_response(raw)
        items, issues = _parse(text)
        before_codes = len(self.judged.codes)
        found, bad = judge_items(
            items,
            self.catalog,
            self.library,
            self._check,
            self.taken,
            note_check=self.note_check,
            name_check=self.name_check,
            judged=self.judged,
        )
        issues += bad
        self.accepted += found
        self.rejected += [i.template for i in issues if i.template]
        # 被拒絕的（會重試）在前，本地修正與丟掉文字的（LF-2，不重試）在後
        codes = tuple(dict.fromkeys([*(i.code for i in issues), *self.judged.codes[before_codes:]]))
        self.records.append(AttemptRecord(codes, self.clock() - start))
        if len(self.accepted) >= self.want:
            return False
        self.previous = text
        body = {
            "attempt": number,
            "max_attempts": self.max_attempts,
            "errors": [i.to_json() for i in issues],
        }
        self.feedback = json.dumps(body, ensure_ascii=False, sort_keys=True)
        return True


def propose_variations(
    client: LLMClient,
    library: ContentLibrary,
    request: FlashRequest,
    *,
    max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
    clock: Clock = time.perf_counter,
    shuffle_catalog: bool = True,
) -> FlashProposalRecord:
    """請 LLM 為這次的閃現提議一批變化（最多 ``max_attempts`` 次，合格的累積）。`LLMUnavailable`
    立即停止；不足的部分由 :func:`~trpg.skillgen.flash_offer.make_offer` 用模板補。

    ``shuffle_catalog``：``True``（預設；LLM-1A 使用者選 A）BAL-10c 的整份目錄依種子打亂（同一招
    連續重試仍同序）；``False`` 依模板 ID 固定排序（跨題共用 KV 前綴快取，但位置偏好較重）。"""
    table = library.flash
    before = skill_before(library, request)
    major = slot_is_major(table.rules, request.state, request.nth)
    # 目錄只列這招套得上的模板與參數（4-L10a F1／F2）：模型看不到會被 flash.not_applicable 擋下的
    # 選項；指定類別時目錄本來就只有該類
    catalog = build_catalog(
        library,
        request,
        before,
        major=major,
        applicable=lambda v: try_variation(library, request, v) is not None,
    )
    options = table.pricing.rule(request.category is not None).options
    tag = seed_tag(request.state.base_id, request.nth, request.reflashes, request.category)
    if not catalog.entries:
        return FlashProposalRecord(
            tag=tag, wanted=options, reason="目錄是空的（這一次沒有可提議的變化）"
        )
    # LF-2 第 1 點：要的數量不超過目錄裡不同的（模板, 參數）組合數（指定類別時常只有 1～2 個）
    want = min(options, catalog.combinations)
    # BAL-10c 的打亂是為了位置偏好（模型的第一個提議偏好選單前段）；只影響 prompt 與 schema。
    # LLM-1A：E4B 實測固定排序＋建議清單的位置偏好較重，預設改回打亂
    if shuffle_catalog:
        catalog = catalog.shuffled(request.seed, tag)
    words = load_effect_words()
    loop = _Loop(
        client,
        library,
        request,
        before,
        catalog,
        major,
        want,
        max_attempts,
        clock,
        note_check=note_checker(library, request, before, words),
        name_check=name_checker(library, request, before, words) if major else None,
        words=note_words(library, request, before, catalog, words),
    )
    for number in range(1, max_attempts + 1):
        if not loop.attempt(number):
            break
    count = len(loop.accepted)
    source: ProposalSource = "llm" if count >= want else ("partial" if count else "template")
    kept = {v.key() for v in loop.accepted[:want]}
    judged = loop.judged
    texts = tuple(
        VariationText(key=k, name_zh=judged.names.get(k), note_zh=judged.notes.get(k))
        for k in sorted(kept & (judged.notes.keys() | judged.names.keys()))
    )
    return FlashProposalRecord(
        tag=tag,
        source=source,
        wanted=want,
        attempts=len(loop.records),
        codes=tuple(r.codes for r in loop.records),
        accepted=tuple(loop.accepted[:want]),
        rejected=tuple(loop.rejected),
        reason=loop.reason,
        seconds=sum(r.seconds for r in loop.records),
        texts=texts,
    )


# ---------------------------------------------------------------------------
# 選項來源
# ---------------------------------------------------------------------------

type FlashClient = LLMClient | Callable[[FlashRequest, int], LLMClient]
type NamingClient = LLMClient | Callable[[SkillDef, int], LLMClient]
"""命名用的 client，或依（選項的技能, 種子）建立 client 的函式（Mock 用）。"""
type RecordSink = Callable[[FlashProposalRecord], None]


def _request_tag(request: FlashRequest) -> str:
    return seed_tag(request.state.base_id, request.nth, request.reflashes, request.category)


class LlmFlashSource(UsageSource):
    """LLM 變化提議的選項來源（可替換預設的 :class:`UsageSource`）。``ranked``／``transforms`` 沿用
    用法統計排序的模板（補位與轉型保底），``proposed`` 先請模型挑。

    ``client`` 可以是固定的 client，或依（題目，種子）建立 client 的函式（Mock 用）。每次提議的
    提議紀錄累積在 :attr:`records`，也會交給 ``sink``（寫進 run 紀錄與統計）。

    LF-1：提議時模型寫的 ``note_zh`` 收進紀錄的 ``texts``；``naming`` 給了就再為大變化與轉型選項
    命名（:func:`name_texts`）。:meth:`texts` 把這些文字交給 ``make_offer`` 掛到選項上。"""

    def __init__(
        self,
        client: FlashClient,
        *,
        max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
        sink: RecordSink | None = None,
        clock: Clock = time.perf_counter,
        naming: NamingClient | None = None,
    ) -> None:
        self.client = client
        self.max_attempts = max_attempts
        self.sink = sink
        self.clock = clock
        self.naming = naming
        self.records: list[FlashProposalRecord] = []

    def proposed(
        self, library: ContentLibrary, request: FlashRequest, skill: SkillDef
    ) -> Sequence[Variation]:
        used = (
            self.client
            if isinstance(self.client, LLMClient)
            else self.client(request, request.seed)
        )
        record = propose_variations(
            used, library, request, max_attempts=self.max_attempts, clock=self.clock
        )
        if self.naming is not None:
            record = name_texts(
                record,
                self.naming,
                library,
                request,
                max_attempts=self.max_attempts,
                clock=self.clock,
            )
        self.records.append(record)
        if self.sink is not None:
            self.sink(record)
        return record.accepted

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        """這一次（同標籤、最後一筆）提議紀錄的文字（LF-1）。"""
        tag = _request_tag(request)
        record = next((r for r in reversed(self.records) if r.tag == tag), None)
        return {} if record is None else text_map(record.texts)


class RecordedSource(UsageSource):
    """重播用：直接取用存下來的提議（:class:`FlashProposalRecord`），不呼叫 LLM。找不到同標籤的
    紀錄時不提議（全部用模板）。LF-1：文字（名稱與描述）也從紀錄拿。"""

    def __init__(self, records: Iterable[FlashProposalRecord]) -> None:
        self.by_tag = {r.tag: r for r in records}

    def proposed(
        self, library: ContentLibrary, request: FlashRequest, skill: SkillDef
    ) -> Sequence[Variation]:
        record = self.by_tag.get(_request_tag(request))
        return () if record is None else record.accepted

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        record = self.by_tag.get(_request_tag(request))
        return {} if record is None else text_map(record.texts)


def select_flash_source(
    config: LLMConfig,
    *,
    client: FlashClient | None = None,
    sink: RecordSink | None = None,
) -> FlashOptionSource:
    """依 ``config/llm.toml`` 的 ``generate`` 開關（網頁的 ``llm`` 開關同一個）選來源：關 ＝ 預設的
    :class:`UsageSource`；開 ＝ :class:`LlmFlashSource`（沒給 client 時用本機模型；LF-1 起同一個
    client 也為大變化與轉型命名）。"""
    if not config.generate:
        return UsageSource()
    used = client if client is not None else OpenAICompatClient(config)
    naming = used if isinstance(used, LLMClient) else None
    return LlmFlashSource(used, max_attempts=config.max_retries, sink=sink, naming=naming)


# ---------------------------------------------------------------------------
# 命名（4-L7）
# ---------------------------------------------------------------------------


def name_offer(
    offer: FlashOffer,
    client: LLMClient | Callable[[SkillDef, int], LLMClient],
    library: ContentLibrary,
    *,
    seed: int,
    taken: set[str],
    max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
    before: SkillDef | None = None,
    region: str | None = None,
    weapon: str | None = None,
) -> tuple[FlashOffer, tuple[FlashNameRecord, ...]]:
    """大變化與轉型的選項請 4-L7 命名步驟取名與寫敘事（只換文字，失敗用「{前綴}・{原名}」）。
    小變化不改名。命名關閉時不要呼叫這個函式——選項的名稱本來就是「{前綴}・{原名}」。
    ``before``（4-L11，:func:`~trpg.skillgen.flash_offer.skill_before`）給了就要求名稱或敘事提到
    變化加上的效果。``region``／``weapon``（6L-1，#126）：原技能取得地點的區域與持有者的武器。"""
    options = []
    names: list[FlashNameRecord] = []
    for option in offer.options:
        if option.variation.source == "minor":
            options.append(option)
            continue
        used = client if isinstance(client, LLMClient) else client(option.skill, seed)
        result = name_skill(
            used,
            library,
            option.skill,
            taken=taken,
            max_attempts=max_attempts,
            before=before,
            region=region,
            weapon=weapon,
        )
        taken.add(result.text.name_zh)
        named = (
            option.skill if result.source == "fallback" else apply_naming(option.skill, result.text)
        )
        options.append(option.model_copy(update={"skill": named}))
        names.append(
            FlashNameRecord(
                template=option.variation.template,
                source=result.source,
                attempts=result.attempts,
                codes=result.codes,
                consistency_retries=result.consistency_retries,
            )
        )
    return offer.model_copy(update={"options": tuple(options)}), tuple(names)


def _unavailable(record: FlashProposalRecord) -> bool:
    return record.reason is not None and record.reason.startswith(LLM_ERROR_CODES[LLMUnavailable])


def name_texts(
    record: FlashProposalRecord,
    client: NamingClient,
    library: ContentLibrary,
    request: FlashRequest,
    *,
    max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
    clock: Clock = time.perf_counter,
) -> FlashProposalRecord:
    """LF-1：為這一次出題的大變化與轉型選項命名，名稱寫進紀錄的 ``texts``（6.34.3：小變化不改名）。

    用紀錄裡的提議出一次題（純函式 :func:`~trpg.skillgen.flash_offer.make_offer`，和引擎之後出題
    同一套），對每個大變化、轉型選項呼叫命名步驟 :func:`~trpg.llm.naming.name_skill`（照原技能的
    區域與武器，#126；名稱或敘事要提到變化加上的效果，4-L11）。命名失敗的項目沒有名稱（引擎用
    「{前綴}・{原名}」）。那一項沒有描述時，命名的 ``concept`` 合格（:func:`clean_note`）就當描述。
    模型連不上（提議時已 ``llm.unavailable``）時不命名。"""
    if _unavailable(record):
        return record
    start = clock()
    offer = make_offer(library, request, RecordedSource([record]))
    big = [o for o in offer.options if o.variation.source != "minor"]
    if not big:
        return record
    before = skill_before(library, request)
    texts = dict(text_map(record.texts))
    names: list[FlashNameRecord] = []
    taken: set[str] = {t.name_zh for t in texts.values() if t.name_zh is not None}
    for option in big:
        given = texts.get(option.variation.key())
        if given is not None and given.name_zh is not None:
            # LF-2 第 7 點：提議時已經取好、通過檢查的名稱直接用，不另呼叫命名（attempts 0）
            names.append(
                FlashNameRecord(template=option.variation.template, source="llm", attempts=0)
            )
            continue
        # 依選項分流的種子（Mock 命名依種子挑詞；同一題各選項才不會撞名）
        seed = (
            Rng(request.seed).fork(f"llm.flash.naming/{option.variation.key()}").randint(0, 2**31)
        )
        used = client if isinstance(client, LLMClient) else client(option.skill, seed)
        result = name_skill(
            used,
            library,
            option.skill,
            taken=taken,
            max_attempts=max_attempts,
            before=before,
            region=request.region,
            weapon=request.weapon_zh,
        )
        names.append(
            FlashNameRecord(
                template=option.variation.template,
                source=result.source,
                attempts=result.attempts,
                codes=result.codes,
                consistency_retries=result.consistency_retries,
            )
        )
        if result.source != "llm":
            continue
        taken.add(result.text.name_zh)
        key = option.variation.key()
        old = texts.get(key)
        note = old.note_zh if old is not None else None
        texts[key] = VariationText(
            key=key, name_zh=result.text.name_zh, note_zh=note or clean_note(result.text.concept)
        )
    return record.model_copy(
        update={
            "names": (*record.names, *names),
            "texts": tuple(texts[k] for k in sorted(texts)),
            "seconds": record.seconds + (clock() - start),
        }
    )


# ---------------------------------------------------------------------------
# Mock（CI 與 --llm-mock）
# ---------------------------------------------------------------------------


def _item_json(variation: Variation) -> dict[str, Any]:
    return {
        "category": variation.category,
        "template": variation.template,
        "keyword": variation.keyword,
        "element": variation.element,
        "shape": None if variation.shape is None else variation.shape.type,
        "note_zh": None,  # 4-L11：note 要提到變化加上的效果，Mock 不寫
    }


def mock_flash_client(
    library: ContentLibrary, request: FlashRequest, seed: int, attempts: int
) -> MockLLMClient:
    """合格的提議回應（確定性：類別由種子洗牌後輪流取，只取引擎套得上的）。"""
    table = library.flash
    before = skill_before(library, request)
    major = slot_is_major(table.rules, request.state, request.nth)
    catalog = build_catalog(library, request, before, major=major)
    want = table.pricing.rule(request.category is not None).options
    rng = Rng(seed).fork("llm.flash.mock")
    queues = {c: [v for v in catalog.pool.values() if v.category == c] for c in catalog.categories}
    order = rng.shuffled(sorted(queues))
    picked: list[Variation] = []
    while len(picked) < want and any(queues.values()):
        for category in order:
            queue = queues[category]
            while queue:
                variation = queue.pop(0)
                if try_variation(library, request, variation) is not None:
                    picked.append(variation)
                    break
            if len(picked) >= want:
                break
    text = json.dumps({"variations": [_item_json(v) for v in picked]}, ensure_ascii=False)
    return MockLLMClient([text] * attempts)


def mock_flash_source(
    library: ContentLibrary,
    *,
    max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
    sink: RecordSink | None = None,
    naming: bool = False,
) -> LlmFlashSource:
    """Mock 提議來源：不需網路與金鑰。``naming``（LF-1）為真時大變化與轉型用 Mock 命名
    （:func:`~trpg.llm.candidate_source.mock_naming_client`）；預設關（不動既有快照）。"""
    return LlmFlashSource(
        lambda request, seed: mock_flash_client(library, request, seed, max_attempts),
        max_attempts=max_attempts,
        sink=sink,
        naming=(lambda skill, seed: mock_naming_client(library, skill, seed)) if naming else None,
    )


# ---------------------------------------------------------------------------
# 統計（4-L9 評估）
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FlashProposalStats:
    """累加多個提議紀錄：一次通過率（第一次就湊滿）、退回率（全部用模板）、補位率
    （部分）、平均嘗試次數、各錯誤代碼、各類別與模板命中、名稱抽樣。退回率超過 ``alert_permille``
    （``fallback_alert_permille``）時 :attr:`alert` 為真。"""

    alert_permille: int = 200
    total: int = 0
    first_pass: int = 0
    attempts: int = 0
    seconds: float = 0.0
    sources: Counter[str] = field(default_factory=Counter)
    codes: Counter[str] = field(default_factory=Counter)
    categories: Counter[str] = field(default_factory=Counter)
    templates: Counter[str] = field(default_factory=Counter)
    name_samples: list[str] = field(default_factory=list)
    naming_calls: int = 0
    """另外呼叫命名步驟的次數（LF-1 的 :func:`name_texts`；LF-2 起提議時取好的名稱不算）。"""
    names_merged: int = 0
    """提議時順便取好、直接採用的名稱數（LF-2 第 7 點）。"""

    @classmethod
    def of(
        cls, records: Iterable[FlashProposalRecord], *, alert_permille: int = 200
    ) -> FlashProposalStats:
        stats = cls(alert_permille=alert_permille)
        for record in records:
            stats.add(record)
        return stats

    def add(self, record: FlashProposalRecord) -> None:
        self.total += 1
        self.attempts += record.attempts
        self.seconds += record.seconds
        self.sources[record.source] += 1
        if record.source == "llm" and record.attempts == 1:
            self.first_pass += 1
        for codes in record.codes:
            self.codes.update(codes)
        for name in record.names:
            self.naming_calls += name.attempts
            self.names_merged += name.attempts == 0 and name.source == "llm"
        for variation in record.accepted:
            self.categories[variation.category] += 1
            self.templates[variation.template] += 1

    def add_names(self, skills: Iterable[SkillDef], *, limit: int = 20) -> None:
        """名稱品質抽樣：把命名後的技能名稱與概念收進來（最多 ``limit`` 筆）。"""
        for skill in skills:
            if len(self.name_samples) < limit:
                self.name_samples.append(f"{skill.name_zh}：{skill.narrative.concept}")

    def _permille(self, part: int) -> int:
        return part * 1000 // self.total if self.total else 0

    @property
    def pass_permille(self) -> int:
        """通過率：模型自己湊滿題目數量（不論第幾次）。"""
        return self._permille(self.sources["llm"])

    @property
    def first_pass_permille(self) -> int:
        return self._permille(self.first_pass)

    @property
    def fallback_permille(self) -> int:
        return self._permille(self.sources["template"])

    @property
    def partial_permille(self) -> int:
        return self._permille(self.sources["partial"])

    @property
    def mean_attempts(self) -> float:
        return self.attempts / self.total if self.total else 0.0

    @property
    def alert(self) -> bool:
        return self.fallback_permille > self.alert_permille

    def _prefixed(self, prefix: str) -> int:
        return sum(n for code, n in self.codes.items() if code.startswith(prefix))

    @property
    def notes_dropped(self) -> int:
        """不合格而丟掉的說明數（LF-2：只丟說明、不重試；同一次嘗試同一種原因算一次）。"""
        return self._prefixed("flash.note_dropped.")

    @property
    def repairs(self) -> int:
        """本地修正數（LF-2，``flash.repaired.*``；同一次嘗試同一種修正算一次）。"""
        return self._prefixed("flash.repaired.")

    @property
    def mean_round_trips(self) -> float:
        """每題往返次數：提議的嘗試次數＋另外呼叫命名的次數。"""
        return (self.attempts + self.naming_calls) / self.total if self.total else 0.0

    def summary_lines(self) -> list[str]:
        """中文摘要表（CLI 與 4-L9 報告用）。"""
        alert = f"　（提醒：超過 {self.alert_permille / 10:g}%）" if self.alert else ""
        return [
            f"題目數　　　　{self.total}",
            f"通過率　　　　{self.pass_permille / 10:.1f}%（模型湊滿 {self.sources['llm']}）",
            f"一次通過率　　{self.first_pass_permille / 10:.1f}%（{self.first_pass}）",
            f"補位率　　　　{self.partial_permille / 10:.1f}%（補 {self.sources['partial']}）",
            f"退回率　　　　{self.fallback_permille / 10:.1f}%（{self.sources['template']}）"
            + alert,
            f"平均嘗試次數　{self.mean_attempts:.2f}",
            f"每題往返次數　{self.mean_round_trips:.2f}（命名呼叫 {self.naming_calls}、"
            f"提議時取名 {self.names_merged}）",
            f"丟掉的說明　　{self.notes_dropped}",
            f"本地修正　　　{self.repairs}",
            "錯誤代碼　　　" + (_counts(self.codes) or "（無）"),
            "類別命中　　　" + (_counts(self.categories) or "（無）"),
            "模板命中　　　" + (_counts(self.templates) or "（無）"),
        ]


def _counts(counter: Counter[str]) -> str:
    return "、".join(f"{k} {n}" for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))
