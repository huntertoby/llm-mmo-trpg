"""許願池的 LLM 步驟（Phase WP-1；07 7.6、#88；``docs/phases/PhaseWP計畫.md`` 第 2、3 節）。

兩步，都只提議（守則 3）：

1. **對關鍵字**（:func:`match_wish`）：願望（只在 ``<player_input>``）
＋選單 → 1～``max_keywords`` 個
   關鍵字（schema 用 ``enum``）；不在選單、重複、數量不對帶 ``<errors>`` 重試，
   最多 ``max_attempts`` 次。
2. **提議技能**：照對到的關鍵字出完整技能三選一，LLM 那幾張用 :attr:`WishSource.proposer`（同一個
   願望放進技能提議的 ``<player_input>``，:func:`~trpg.llm.candidate_source.make_proposer`）；
   數值一律由
   預算器補。出題本身在 API 層（``trpg.api.world_pregen``）呼叫 ``make_offer``。

引擎（``trpg.world.wish``）再驗一次關鍵字與三選一；這裡的驗證只決定要不要重問。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.prompts.wish import WISH_PROMPT_VERSION, build_wish_messages, wish_schema
from trpg.llm.response import clean_response
from trpg.skillgen.proposal_topic import LlmProposer

__all__ = [
    "DEFAULT_WISH_ATTEMPTS",
    "WishMatch",
    "WishSource",
    "match_wish",
    "mock_wish_client",
    "wish_menu_payload",
]

DEFAULT_WISH_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class WishMatch:
    """:func:`match_wish` 的結果：``keywords`` 空＝沒對上（``reason`` 是原因）。"""

    keywords: tuple[str, ...]
    attempts: int
    codes: tuple[str, ...] = ()
    reason: str = ""
    seconds: float = 0.0
    prompt_version: str = WISH_PROMPT_VERSION


@dataclass(frozen=True, slots=True)
class WishSource:
    """API 層的許願來源：``client`` 對關鍵字（或依願望與選單建 client 的函式，Mock 用）；
    ``proposer(願望)``
    是把願望放進 ``<player_input>`` 的技能提議器。"""

    client: LLMClient | Callable[[str, Sequence[str]], LLMClient]
    proposer: Callable[[str], LlmProposer]
    max_attempts: int = DEFAULT_WISH_ATTEMPTS

    def client_for(self, wish: str, menu: Sequence[str]) -> LLMClient:
        """對關鍵字用的 client（Mock 依願望與選單建）。"""
        return self.client if isinstance(self.client, LLMClient) else self.client(wish, menu)


def wish_menu_payload(library: ContentLibrary, menu: Sequence[str]) -> list[dict[str, str]]:
    """``<request>`` 的選單：代碼、名稱、一句說明（內容庫的關鍵字說明）。"""
    by_id = {k.id: k for k in library.keywords.keywords}
    return [
        {"id": k, "name": by_id[k].name_zh, "hint": by_id[k].description_zh}
        for k in menu
        if k in by_id
    ]


def _problems(data: object, menu: Sequence[str], limit: int) -> list[tuple[str, str]]:
    if not isinstance(data, dict) or set(data) != {"keywords"}:
        return [("wish.format", '只輸出 {"keywords": [...]}')]
    keywords = data["keywords"]
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        return [("wish.format", "keywords 要是字串陣列")]
    out: list[tuple[str, str]] = []
    if not 1 <= len(keywords) <= limit:
        out.append(("wish.count", f"keywords 要有 1～{limit} 個"))
    if len(set(keywords)) != len(keywords):
        out.append(("wish.duplicate", "keywords 不能重複"))
    bad = [k for k in keywords if k not in menu]
    if bad:
        out.append(("wish.not_in_menu", f"不在 menu 裡：{'、'.join(bad)}；只能用 menu 的 id"))
    return out


def match_wish(
    client: LLMClient,
    library: ContentLibrary,
    wish: str,
    menu: Sequence[str],
    *,
    max_keywords: int = 2,
    max_attempts: int = DEFAULT_WISH_ATTEMPTS,
    clock: Callable[[], float] = time.perf_counter,
) -> WishMatch:
    """請模型從 ``menu`` 對到 1～``max_keywords`` 個關鍵字（見模組說明）。
    ``LLMUnavailable`` 立刻停；
    ``LLMTimeout``／``LLMBadResponse`` 算一次嘗試。``clock`` 只用來計時（報表）。"""
    start = clock()
    request = {"menu": wish_menu_payload(library, menu), "max": max_keywords}
    schema = wish_schema(menu, max_keywords)
    codes: list[str] = []
    errors: str | None = None
    reason = ""
    for number in range(1, max_attempts + 1):
        messages = build_wish_messages(request, wish, errors=errors)
        try:
            raw = client.complete(messages, json_schema=schema)
        except LLMUnavailable as exc:
            codes.append("llm.unavailable")
            return WishMatch((), number, tuple(codes), f"llm.unavailable：{exc}", clock() - start)
        except (LLMTimeout, LLMBadResponse) as exc:
            codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            reason = codes[-1]
            continue
        try:
            data: object = json.loads(clean_response(raw))
        except json.JSONDecodeError:
            data = None
        problems = _problems(data, menu, max_keywords)
        if not problems:
            assert isinstance(data, dict)
            return WishMatch(tuple(data["keywords"]), number, tuple(codes), "", clock() - start)
        codes.extend(code for code, _ in problems)
        reason = problems[0][0]
        errors = json.dumps(
            {
                "attempt": number,
                "errors": [{"code": c, "message": m} for c, m in problems],
            },
            ensure_ascii=False,
        )
    return WishMatch(
        (),
        max_attempts,
        tuple(codes),
        f"用盡 {max_attempts} 次（最後：{reason}）",
        clock() - start,
    )


def mock_wish_client(
    library: ContentLibrary,
    wish: str,
    menu: Sequence[str],
    *,
    max_keywords: int = 2,
    attempts: int = DEFAULT_WISH_ATTEMPTS,
) -> MockLLMClient:
    """Mock（不需網路與金鑰）：選單裡名稱有任一個字出現在願望中的關鍵字（例「凍」→ 冰凍），依選單
    順序取前 ``max_keywords`` 個；
    都沒有＝回空清單（驗證不過，測重試與退路）。確定性。"""
    by_id = {k.id: k.name_zh for k in library.keywords.keywords}
    found = [k for k in menu if set(by_id.get(k, "")) & set(wish)][:max_keywords]
    text = json.dumps({"keywords": found}, ensure_ascii=False)
    return MockLLMClient([text] * attempts)
