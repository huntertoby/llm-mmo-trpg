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
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.client import LLMClient, MockLLMClient, OpenAICompatClient
from trpg.llm.config import LLMConfig
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.naming import apply_naming, name_skill
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
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import Variation, seed_tag, slot_is_major

__all__ = [
    "DEFAULT_FLASH_ATTEMPTS",
    "FlashNameRecord",
    "FlashProposalRecord",
    "FlashProposalStats",
    "LlmFlashSource",
    "RecordedSource",
    "judge_items",
    "mock_flash_client",
    "mock_flash_source",
    "name_offer",
    "propose_variations",
    "select_flash_source",
]

DEFAULT_FLASH_ATTEMPTS = 3
"""同 4-L5／使用者決定 #5：每個題目最多 3 次（``config/llm.toml`` 的 ``max_retries``）。"""
type Clock = Callable[[], float]
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


def _text_issue(index: int, item: _Item) -> _Issue | None:
    note = item.note_zh
    if note is None:
        return None
    if _ENGLISH.search(note):
        return _Issue(index, "flash.english_text", "note_zh 不可有英文或代號", item.template)
    if len(note) > NOTE_MAX_CHARS or not _NOTE_CHARS.match(note):
        return _Issue(index, "flash.note_text", "note_zh 要是 40 字內的全形中文", item.template)
    return None


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


def judge_items(
    items: Sequence[object],
    catalog: FlashCatalog,
    library: ContentLibrary,
    check: Callable[[Variation], bool],
    taken: set[str],
) -> tuple[list[Variation], list[_Issue]]:
    """逐項檢查提議：回傳合格的變化（依回應順序、已去重、引擎真的套得上）與被拒絕的項目。
    ``taken`` 是已經合格的變化鍵（會更新）。"""
    accepted: list[Variation] = []
    issues: list[_Issue] = []
    for index, raw in enumerate(items):
        item, issue = _item_issue(index, raw)
        if item is not None:
            issue = _text_issue(index, item) or _structure_issue(index, item, catalog, library)
        if issue is None and item is not None:
            variation = catalog.resolve(item.template, item.keyword, item.element, item.shape)
            if variation is None:
                issue = _Issue(index, "flash.param_not_offered", "參數不在選單內", item.template)
            elif variation.key() in taken:
                issue = _Issue(index, "flash.duplicate", "這個變化重複了", item.template)
            elif not check(variation):
                issue = _Issue(index, "flash.not_applicable", "套不上這招", item.template)
            else:
                taken.add(variation.key())
                accepted.append(variation)
        if issue is not None:
            issues.append(issue)
    return accepted, issues


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
    """大變化／轉型選項的命名結果（:func:`name_offer`；命名關閉時為空）。"""


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
    taken: set[str] = field(default_factory=set)
    accepted: list[Variation] = field(default_factory=list)
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
        )
        schema = flash_schema(self.catalog, remaining)
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
        found, bad = judge_items(items, self.catalog, self.library, self._check, self.taken)
        issues += bad
        self.accepted += found
        self.rejected += [i.template for i in issues if i.template]
        codes = tuple(dict.fromkeys(i.code for i in issues))
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
) -> FlashProposalRecord:
    """請 LLM 為這次的閃現提議一批變化（最多 ``max_attempts`` 次，合格的累積）。`LLMUnavailable`
    立即停止；不足的部分由 :func:`~trpg.skillgen.flash_offer.make_offer` 用模板補。"""
    table = library.flash
    before = skill_before(library, request)
    major = slot_is_major(table.rules, request.state, request.nth)
    catalog = build_catalog(library, request, before, major=major)
    want = table.pricing.rule(request.category is not None).options
    tag = seed_tag(request.state.base_id, request.nth, request.reflashes, request.category)
    if not catalog.entries:
        return FlashProposalRecord(
            tag=tag, wanted=want, reason="目錄是空的（這一次沒有可提議的變化）"
        )
    loop = _Loop(client, library, request, before, catalog, major, want, max_attempts, clock)
    for number in range(1, max_attempts + 1):
        if not loop.attempt(number):
            break
    count = len(loop.accepted)
    source: ProposalSource = "llm" if count >= want else ("partial" if count else "template")
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
    )


# ---------------------------------------------------------------------------
# 選項來源
# ---------------------------------------------------------------------------

type FlashClient = LLMClient | Callable[[FlashRequest, int], LLMClient]
type RecordSink = Callable[[FlashProposalRecord], None]


class LlmFlashSource(UsageSource):
    """LLM 變化提議的選項來源（可替換預設的 :class:`UsageSource`）。``ranked``／``transforms`` 沿用
    用法統計排序的模板（補位與轉型保底），``proposed`` 先請模型挑。

    ``client`` 可以是固定的 client，或依（題目，種子）建立 client 的函式（Mock 用）。每次提議的
    提議紀錄累積在 :attr:`records`，也會交給 ``sink``（寫進 run 紀錄與統計）。"""

    def __init__(
        self,
        client: FlashClient,
        *,
        max_attempts: int = DEFAULT_FLASH_ATTEMPTS,
        sink: RecordSink | None = None,
        clock: Clock = time.perf_counter,
    ) -> None:
        self.client = client
        self.max_attempts = max_attempts
        self.sink = sink
        self.clock = clock
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
        self.records.append(record)
        if self.sink is not None:
            self.sink(record)
        return record.accepted


class RecordedSource(UsageSource):
    """重播用：直接取用存下來的提議（:class:`FlashProposalRecord`），不呼叫 LLM。找不到同標籤的
    紀錄時不提議（全部用模板）。"""

    def __init__(self, records: Iterable[FlashProposalRecord]) -> None:
        self.by_tag = {r.tag: r for r in records}

    def proposed(
        self, library: ContentLibrary, request: FlashRequest, skill: SkillDef
    ) -> Sequence[Variation]:
        tag = seed_tag(request.state.base_id, request.nth, request.reflashes, request.category)
        record = self.by_tag.get(tag)
        return () if record is None else record.accepted


def select_flash_source(
    config: LLMConfig,
    *,
    client: FlashClient | None = None,
    sink: RecordSink | None = None,
) -> FlashOptionSource:
    """依 ``config/llm.toml`` 的 ``generate`` 開關（網頁的 ``llm`` 開關同一個）選來源：關 ＝ 預設的
    :class:`UsageSource`；開 ＝ :class:`LlmFlashSource`（沒給 client 時用本機模型）。"""
    if not config.generate:
        return UsageSource()
    return LlmFlashSource(
        client if client is not None else OpenAICompatClient(config),
        max_attempts=config.max_retries,
        sink=sink,
    )


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
) -> tuple[FlashOffer, tuple[FlashNameRecord, ...]]:
    """大變化與轉型的選項請 4-L7 命名步驟取名與寫敘事（只換文字，失敗用「{前綴}・{原名}」）。
    小變化不改名。命名關閉時不要呼叫這個函式——選項的名稱本來就是「{前綴}・{原名}」。"""
    options = []
    names: list[FlashNameRecord] = []
    for option in offer.options:
        if option.variation.source == "minor":
            options.append(option)
            continue
        used = client if isinstance(client, LLMClient) else client(option.skill, seed)
        result = name_skill(used, library, option.skill, taken=taken, max_attempts=max_attempts)
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
            )
        )
    return offer.model_copy(update={"options": tuple(options)}), tuple(names)


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
        "note_zh": "貼合這招的用法。",
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
) -> LlmFlashSource:
    """Mock 提議來源：不需網路與金鑰。"""
    return LlmFlashSource(
        lambda request, seed: mock_flash_client(library, request, seed, max_attempts),
        max_attempts=max_attempts,
        sink=sink,
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
            "錯誤代碼　　　" + (_counts(self.codes) or "（無）"),
            "類別命中　　　" + (_counts(self.categories) or "（無）"),
            "模板命中　　　" + (_counts(self.templates) or "（無）"),
        ]


def _counts(counter: Counter[str]) -> str:
    return "、".join(f"{k} {n}" for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))
