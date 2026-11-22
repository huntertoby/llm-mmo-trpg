"""LLM 技能提議的重試迴圈、退回與統計（Phase 4-L5；設計文件 5.3、使用者決定 #3、#5）。

:func:`propose_skill` 每次嘗試：
``build_proposal_prompt``（重試時帶上一份提議與 ``feedback_payload``）→ ``client.complete`` →
:func:`~trpg.llm.response.clean_response` → ``evaluate_proposal``（數值由
:func:`~trpg.skillgen.proposal_budget.budget_filler` 補，只剩可修的數值錯誤時由引擎修一次，見
:func:`~trpg.skillgen.proposal_budget.evaluate_with_repair`）。合格就回傳；用盡次數、連不上
模型、或題目沒有可用結構（``SubsetError``）時退回
:func:`~trpg.skillgen.proposal_fallback.fallback_skill`。

LLM 只提議：技能的數值一律來自預算器；耗時只供報表，不進任何確定性狀態。
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.client import LLMClient
from trpg.llm.config import LLM_DEFAULTS
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.response import clean_response, drop_false_flags
from trpg.skillgen.proposal import ProposalContext, ProposalError, feedback_payload
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_fallback import fallback_skill
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError

__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "LLM_ERROR_CODES",
    "AttemptDetail",
    "AttemptRecord",
    "ProposalOutcome",
    "ProposalSource",
    "ProposalStats",
    "propose_skill",
]

type ProposalSource = Literal["llm", "composer", "pool", "workshop"]
type Clock = Callable[[], float]

DEFAULT_MAX_ATTEMPTS = LLM_DEFAULTS.max_retries
"""使用者決定 #5：每個候選最多 3 次（``config/llm.toml`` 的 ``max_retries``）。"""
LLM_ERROR_CODES = {
    LLMUnavailable: "llm.unavailable",
    LLMTimeout: "llm.timeout",
    LLMBadResponse: "llm.bad_response",
}
"""呼叫本身失敗時記在 :attr:`AttemptRecord.codes` 的代碼。"""
SUBSET_ERROR_CODE = "subset.unavailable"

logger = logging.getLogger("trpg.llm")


@dataclass(frozen=True, slots=True)
class AttemptDetail:
    """一次嘗試的完整診斷（LB-2）：只放在記憶體、供量測腳本寫進 JSON；不進存檔與日誌格式。

    - ``raw``：模型的原始輸出（清理前；呼叫失敗時為空字串）。
    - ``errors``：每條錯誤的 :meth:`~trpg.skillgen.proposal.ProposalError.diagnostic`
      （階段、路徑、代碼、訊息全文、可用值、pydantic 原始位置與輸入值）。
    - ``feedback``：這次失敗後回饋給模型的文字（下一次 prompt 的 ``<errors>``；最後一次或合格時為
      ``None``）。
    - ``call_error``：呼叫本身失敗（``llm.*``）時的例外訊息。
    """

    raw: str = ""
    errors: tuple[dict[str, object], ...] = ()
    feedback: str | None = None
    call_error: str | None = None

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {"raw": self.raw, "errors": [dict(e) for e in self.errors]}
        if self.feedback is not None:
            data["feedback"] = self.feedback
        if self.call_error is not None:
            data["call_error"] = self.call_error
        return data


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """一次 LLM 嘗試：回給 LLM 的錯誤代碼（合格時為空）、引擎修好的代碼、耗時（秒，只供報表）。"""

    codes: tuple[str, ...]
    seconds: float
    repaired: tuple[str, ...] = ()
    detail: AttemptDetail | None = field(default=None, compare=False, repr=False)
    """診斷（LB-2）：原始輸出、完整錯誤、回饋文字；不參與比較。"""


@dataclass(frozen=True, slots=True)
class ProposalOutcome:
    """:func:`propose_skill` 的結果。``attempts`` 是實際呼叫 LLM 的次數；``reason`` 是退回原因
    （``llm`` 來源時為 ``None``）。"""

    skill: SkillDef
    source: ProposalSource
    records: tuple[AttemptRecord, ...]
    reason: str | None = None

    @property
    def attempts(self) -> int:
        return len(self.records)

    @property
    def codes(self) -> tuple[tuple[str, ...], ...]:
        """每次嘗試的錯誤代碼。"""
        return tuple(r.codes for r in self.records)

    @property
    def seconds(self) -> float:
        return sum(r.seconds for r in self.records)


def _error_text(error: Exception) -> str:
    return str(error) or type(error).__name__


def _log_errors(number: int, errors: Sequence[ProposalError]) -> None:
    """不合格的嘗試記進 ``trpg.llm`` 日誌（LB-2）：每條錯誤的代碼、路徑、訊息全文與 pydantic
    位置；不記模型原始輸出與 prompt（可能含玩家文字）。"""
    for error in errors:
        logger.info(
            "技能提議第 %d 次嘗試不合格：%s｜%s｜%s｜%s",
            number,
            error.code,
            error.path or "（技能層級）",
            error.message,
            error.loc or "—",
        )


@dataclass(slots=True)
class _Loop:
    """重試迴圈的狀態：已做的嘗試、上一份提議與回饋。"""

    client: LLMClient
    library: ContentLibrary
    request: ProposalRequest
    ctx: ProposalContext
    seed: int
    max_attempts: int
    player_text: str | None
    clock: Clock
    records: list[AttemptRecord] = field(default_factory=list)
    previous: str | None = None
    feedback: str | None = None

    def attempt(self, number: int) -> SkillDef | str | None:
        """一次嘗試：合格回傳技能；應立即退回時回傳原因；可以重試時回傳 ``None``。"""
        try:
            prompt = build_proposal_prompt(
                self.library,
                self.request,
                player_text=self.player_text,
                previous_proposal=self.previous,
                errors=self.feedback,
            )
        except SubsetError as exc:
            return f"{SUBSET_ERROR_CODE}：{exc}"
        start = self.clock()
        try:
            raw = self.client.complete(prompt.messages, json_schema=prompt.json_schema)
        except (LLMUnavailable, LLMTimeout, LLMBadResponse) as exc:
            code = LLM_ERROR_CODES[type(exc)]
            detail = AttemptDetail(call_error=_error_text(exc))
            self.records.append(AttemptRecord((code,), self.clock() - start, detail=detail))
            logger.info("技能提議第 %d 次嘗試：%s（%s）", number, code, detail.call_error)
            return f"{code}：{_error_text(exc)}" if isinstance(exc, LLMUnavailable) else None
        text = drop_false_flags(clean_response(raw))
        evaluation = evaluate_with_repair(
            text, prompt.models, self.library, self.ctx, seed=self.seed
        )
        result = evaluation.result
        codes = tuple(e.code for e in result.errors)
        seconds = self.clock() - start
        if result.ok and result.skill is not None:
            detail = AttemptDetail(raw=raw)
            self.records.append(AttemptRecord(codes, seconds, evaluation.repaired, detail))
            return result.skill
        self.previous = text
        self.feedback = feedback_payload(result.errors, number, self.max_attempts)
        detail = AttemptDetail(
            raw=raw,
            errors=tuple(e.diagnostic() for e in result.errors),
            feedback=self.feedback if number < self.max_attempts else None,
        )
        self.records.append(AttemptRecord(codes, seconds, evaluation.repaired, detail))
        _log_errors(number, result.errors)
        return None

    def exhausted(self) -> str:
        last = self.records[-1].codes if self.records else ()
        detail = "、".join(dict.fromkeys(last))
        return f"用盡 {self.max_attempts} 次" + (f"（最後一次：{detail}）" if detail else "")


def propose_skill(
    client: LLMClient,
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    player_text: str | None = None,
    clock: Clock = time.perf_counter,
) -> ProposalOutcome:
    """請 LLM 提議一個技能（最多 ``max_attempts`` 次），失敗時退回。見模組說明。

    ``LLMUnavailable`` 立即退回；``LLMTimeout``／``LLMBadResponse`` 算一次嘗試。``SubsetError``
    （題目沒有可用結構）不呼叫 LLM、直接退回。未知的骨架或關鍵字 ID 丟 ``ValueError``；退回也失敗時
    丟 :class:`~trpg.skillgen.proposal_fallback.FallbackError`。``clock`` 只用來計時（報表）。"""
    # 題目的關鍵字與指定的核心原語一併交給驗證器（Phase 4-L6：`keyword.required`、`core.required`）
    ctx = replace(
        ctx,
        keywords=request.keywords,
        core_primitive=request.core_primitive,
        weapon_class=request.weapon_class,
    )
    loop = _Loop(client, library, request, ctx, seed, max_attempts, player_text, clock)
    reason: str | None = None
    for number in range(1, max_attempts + 1):
        found = loop.attempt(number)
        if isinstance(found, SkillDef):
            return ProposalOutcome(found, "llm", tuple(loop.records))
        if found is not None:
            reason = found
            break
    skill, source = fallback_skill(library, request, ctx, seed=seed)
    return ProposalOutcome(skill, source, tuple(loop.records), reason or loop.exhausted())


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProposalStats:
    """累加多個 :class:`ProposalOutcome`：一次通過率、平均嘗試次數、退回率、各代碼與來源次數、
    平均耗時；退回率超過 ``alert_permille``（``config/llm.toml`` 的 ``fallback_alert_permille``）
    時 :attr:`alert` 為真。"""

    alert_permille: int = LLM_DEFAULTS.fallback_alert_permille
    total: int = 0
    first_pass: int = 0
    attempts: int = 0
    seconds: float = 0.0
    sources: Counter[str] = field(default_factory=Counter)
    codes: Counter[str] = field(default_factory=Counter)
    repaired: Counter[str] = field(default_factory=Counter)

    @classmethod
    def of(
        cls,
        outcomes: Iterable[ProposalOutcome],
        *,
        alert_permille: int = LLM_DEFAULTS.fallback_alert_permille,
    ) -> ProposalStats:
        stats = cls(alert_permille=alert_permille)
        for outcome in outcomes:
            stats.add(outcome)
        return stats

    def add(self, outcome: ProposalOutcome) -> None:
        self.total += 1
        self.attempts += outcome.attempts
        self.seconds += outcome.seconds
        self.sources[outcome.source] += 1
        if outcome.source == "llm" and outcome.attempts == 1:
            self.first_pass += 1
        for record in outcome.records:
            self.codes.update(record.codes)
            self.repaired.update(record.repaired)

    @property
    def fallbacks(self) -> int:
        return self.total - self.sources["llm"]

    def _permille(self, part: int) -> int:
        return int(Fraction(part * 1000, self.total)) if self.total else 0

    @property
    def first_pass_permille(self) -> int:
        return self._permille(self.first_pass)

    @property
    def fallback_permille(self) -> int:
        return self._permille(self.fallbacks)

    @property
    def mean_attempts(self) -> float:
        return self.attempts / self.total if self.total else 0.0

    @property
    def mean_seconds(self) -> float:
        return self.seconds / self.total if self.total else 0.0

    @property
    def alert(self) -> bool:
        return self.fallback_permille > self.alert_permille

    def summary_lines(self) -> list[str]:
        """中文摘要表（CLI 與報告用）。"""
        lines = [
            f"題目數　　　　{self.total}",
            f"一次通過率　　{self.first_pass_permille / 10:.1f}%（{self.first_pass}）",
            f"平均嘗試次數　{self.mean_attempts:.2f}",
            f"退回率　　　　{self.fallback_permille / 10:.1f}%（{self.fallbacks}）"
            + (f"　（提醒：超過 {self.alert_permille / 10:g}%）" if self.alert else ""),
            f"平均耗時　　　{self.mean_seconds:.2f} 秒",
            "來源　　　　　" + _counts(self.sources, ("llm", "composer", "pool", "workshop")),
            "錯誤代碼　　　" + (_counts(self.codes) or "（無）"),
            "引擎修補　　　" + (_counts(self.repaired) or "（無）"),
        ]
        return lines


def _counts(counter: Counter[str], order: Sequence[str] = ()) -> str:
    keys = [k for k in order if counter[k]] + sorted(k for k in counter if k not in order)
    return "、".join(f"{k} {counter[k]}" for k in keys if counter[k])
