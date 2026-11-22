"""許願池「願望驅動」的第一步：願望 → 需求標籤（Phase PK-4；07 7.6「許願池：願望驅動」第 1 點）。

:func:`match_wish_tags`：願望只在 ``<player_input>``；LLM 從固定清單（``skill_pick.yaml`` 的
``wish_tags`` ＋ 內容庫關鍵字）選值，schema 用 ``enum``。回應先過 JSON 與 pydantic
（:class:`WishTagsText`：五類都是字串陣列、沒有多餘欄位）；格式不對帶 ``<errors>`` 重問（最多
``max_attempts`` 次，同 WP-1 對關鍵字的重試）。清單外、重複、超過上限的那一項丟掉、其餘照用
（:func:`~trpg.skillgen.wish_pick.clean_wish_tags`，代碼 ``wish.dropped.<類>``），**一個都沒選到
也算成功**（照一般完整技能的打分出題）。連不上模型或用完次數＝沒有標籤（引擎拒絕這次許願、不扣錢）。

引擎（``trpg.world.wish``）再驗一次標籤；這裡的驗證只決定要不要重問。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skill_pick import WISH_TAG_GROUPS, WishTags
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.config import LLM_DEFAULTS
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.prompts.wish_tags import (
    WISH_TAGS_PROMPT_VERSION,
    build_wish_tags_messages,
    wish_tags_schema,
)
from trpg.llm.response import clean_response
from trpg.skillgen.wish_pick import clean_wish_tags, menu_limits, tag_limits

__all__ = [
    "WishTagMatch",
    "WishTagsText",
    "match_wish_tags",
    "mock_wish_tags_client",
    "wish_tag_choices",
    "wish_tags_payload",
]


class WishTagsText(BaseModel):
    """回應的格式（多餘欄位拒絕；值是否在清單裡另外清理）。"""

    model_config = ConfigDict(extra="forbid")

    keywords: list[str]
    elements: list[str]
    effects: list[str]
    shapes: list[str]
    kinds: list[str]


@dataclass(frozen=True, slots=True)
class WishTagMatch:
    """:func:`match_wish_tags` 的結果：``tags`` 為 ``None``＝沒拿到（``reason`` 是原因）。"""

    tags: WishTags | None
    attempts: int
    codes: tuple[str, ...] = ()
    reason: str = ""
    seconds: float = 0.0
    prompt_version: str = WISH_TAGS_PROMPT_VERSION


def wish_tag_choices(library: ContentLibrary, menu: Sequence[str]) -> dict[str, tuple[str, ...]]:
    """每一類可以選的代碼（依類別順序；關鍵字是 ``menu``）。"""
    rules = library.skill_pick.wish_tags
    out: dict[str, tuple[str, ...]] = {"keywords": tuple(menu)}
    for group in WISH_TAG_GROUPS[1:]:
        out[group] = tuple(i.id for i in rules.items(group))
    return out


def wish_tags_payload(
    library: ContentLibrary, menu: Sequence[str], *, tier: int = 1
) -> dict[str, object]:
    """``<request>``：每一類的清單（代碼、名稱；關鍵字另有一句說明）與角色階級 ``tier`` 的上限
    （WC-2：元素 2 階起最多 2 個）。"""
    rules = library.skill_pick.wish_tags
    by_id = {k.id: k for k in library.keywords.keywords}
    out: dict[str, object] = {
        "keywords": [
            {"id": k, "name": by_id[k].name_zh, "hint": by_id[k].description_zh}
            for k in menu
            if k in by_id
        ]
    }
    for group in WISH_TAG_GROUPS[1:]:
        out[group] = [{"id": i.id, "name": i.name_zh} for i in rules.items(group)]
    out["max"] = menu_limits(library, tier)
    return out


def _feedback(number: int, code: str, message: str) -> str:
    return json.dumps(
        {"attempt": number, "errors": [{"code": code, "message": message}]}, ensure_ascii=False
    )


def match_wish_tags(
    client: LLMClient,
    library: ContentLibrary,
    wish: str,
    menu: Sequence[str],
    *,
    max_attempts: int = LLM_DEFAULTS.max_retries,
    tier: int = 1,
    clock: Callable[[], float] = time.perf_counter,
) -> WishTagMatch:
    """請模型把願望翻成需求標籤（見模組說明）。``tier`` 是許願角色的階級（上限照它，WC-2）。
    ``LLMUnavailable`` 立刻停；``LLMTimeout``／``LLMBadResponse`` 算一次嘗試。``clock`` 只用來計時
    （報表）。"""
    start = clock()
    choices = wish_tag_choices(library, menu)
    schema = wish_tags_schema(choices, menu_limits(library, tier))
    request = wish_tags_payload(library, menu, tier=tier)
    codes: list[str] = []
    errors: str | None = None
    reason = ""
    for number in range(1, max_attempts + 1):
        messages = build_wish_tags_messages(request, wish, errors=errors)
        try:
            raw = client.complete(messages, json_schema=schema)
        except LLMUnavailable as exc:
            codes.append("llm.unavailable")
            return WishTagMatch(
                None, number, tuple(codes), f"llm.unavailable：{exc}", clock() - start
            )
        except (LLMTimeout, LLMBadResponse) as exc:
            codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            reason = codes[-1]
            continue
        try:
            text = WishTagsText.model_validate(json.loads(clean_response(raw)))
        except (json.JSONDecodeError, ValidationError):
            codes.append("wish.format")
            reason = "wish.format"
            errors = _feedback(
                number,
                "wish.format",
                "只輸出 keywords、elements、effects、shapes、kinds 五個字串陣列。",
            )
            continue
        tags, dropped = clean_wish_tags(library, text.model_dump(), menu, tier=tier)
        codes.extend(dropped)
        return WishTagMatch(tags, number, tuple(codes), "", clock() - start)
    return WishTagMatch(
        None,
        max_attempts,
        tuple(codes),
        f"用盡 {max_attempts} 次（最後：{reason}）",
        clock() - start,
    )


def mock_wish_tags_client(
    library: ContentLibrary,
    wish: str,
    menu: Sequence[str],
    *,
    attempts: int = LLM_DEFAULTS.max_retries,
    tier: int = 1,
) -> MockLLMClient:
    """Mock（不需網路與金鑰）：每一類照清單順序，名稱有任一字出現在願望裡的就選（「凍」→ 冰凍、
    「火」→ 火焰、「召」→ 召喚），取到角色階級 ``tier`` 的上限為止；都沒有＝空陣列。確定性。"""
    rules = library.skill_pick.wish_tags
    limits = tag_limits(library, tier)
    names = {k.id: k.name_zh for k in library.keywords.keywords}
    body: dict[str, list[str]] = {
        "keywords": [k for k in menu if set(names.get(k, "")) & set(wish)][: limits["keywords"]]
    }
    for group in WISH_TAG_GROUPS[1:]:
        body[group] = [i.id for i in rules.items(group) if set(i.name_zh) & set(wish)][
            : limits[group]
        ]
    return MockLLMClient([json.dumps(body, ensure_ascii=False)] * attempts)
