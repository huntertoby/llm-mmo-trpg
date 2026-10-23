"""技能提議 prompt 的組裝（Phase 4-L4）：題目 → 篩選子集 → 模型、JSON schema、available → messages。

``build_proposal_prompt`` 把 :mod:`trpg.skillgen.proposal_subset`（篩選、模型、``available``）與
:func:`~trpg.llm.prompts.builder.build_skill_proposal_messages`（資料區、跳脫）接起來，並確認
system ＋ user 訊息 ＋ JSON schema 的估算不超過 :data:`PROMPT_TOKEN_BUDGET`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.llm.client import ChatMessage
from trpg.llm.prompts.builder import build_skill_proposal_messages
from trpg.llm.prompts.world import WorldStyle, load_world_style
from trpg.shared.tokens import PROMPT_TOKEN_BUDGET, estimate_tokens
from trpg.skillgen.proposal import ProposalModels
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    ProposalSubset,
    SubsetError,
    available_payload,
    build_subset_models,
    json_tokens,
    select_subset,
)

__all__ = [
    "PROMPT_TOKEN_BUDGET",
    "USER_RESERVE_TOKENS",
    "ProposalPrompt",
    "build_proposal_prompt",
    "estimate_messages_tokens",
    "estimate_tokens",
]

USER_RESERVE_TOKENS = 5_000
"""user 訊息中 schema 子集以外的預留：題目區塊、玩家文字（上限 500 字，跳脫後最多約 5 倍）、
重試時的上一次提議與錯誤回饋。固定值，讓同一題目的子集不隨重試改變。"""


@dataclass(frozen=True, slots=True)
class ProposalPrompt:
    """:func:`build_proposal_prompt` 的結果：送給 LLM 的 ``messages``、``json_schema``，以及驗證用的
    ``models``（傳給 ``evaluate_proposal``）與 ``subset``。"""

    messages: list[ChatMessage]
    json_schema: dict[str, Any]
    models: ProposalModels
    subset: ProposalSubset

    @property
    def tokens(self) -> int:
        """system ＋ user 訊息 ＋ JSON schema 的估算。"""
        return estimate_messages_tokens(self.messages) + json_tokens(self.json_schema)


def estimate_messages_tokens(messages: list[ChatMessage]) -> int:
    return sum(estimate_tokens(m["content"]) for m in messages)


def _request_payload(
    request: ProposalRequest, subset: ProposalSubset, names: dict[str, str]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tier": request.tier,
        "rarity": request.rarity,
        "kind": subset.kind,
        "keywords": [{"id": k, "name_zh": names[k]} for k in request.keywords],
    }
    if request.skeleton is not None:
        payload["skeleton"] = request.skeleton
    return payload


def build_proposal_prompt(
    library: ContentLibrary,
    request: ProposalRequest,
    *,
    player_text: str | None = None,
    previous_proposal: str | None = None,
    errors: str | None = None,
    world: WorldStyle | None = None,
) -> ProposalPrompt:
    """依題目組出提議 prompt。

    子集大小的預算 = :data:`PROMPT_TOKEN_BUDGET` − 系統指令 − :data:`USER_RESERVE_TOKENS`；組好後
    再檢查整體估算（含玩家文字與重試回饋）仍不超過上限，否則丟
    :class:`~trpg.skillgen.proposal_subset.SubsetError`。未知的骨架或關鍵字 ID 丟 ``ValueError``。
    """
    style = world if world is not None else load_world_style()
    system_tokens = estimate_messages_tokens(build_skill_proposal_messages({}, world=style)[:1])
    budget = PROMPT_TOKEN_BUDGET - system_tokens - USER_RESERVE_TOKENS
    subset = select_subset(library, request, token_budget=budget)
    models = build_subset_models(library, subset)
    names = {k.id: k.name_zh for k in library.ruleset.keywords.keywords}
    messages = build_skill_proposal_messages(
        _request_payload(request, subset, names),
        available=available_payload(library, subset),
        previous_proposal=previous_proposal,
        errors=errors,
        player_text=player_text,
        world=style,
    )
    prompt = ProposalPrompt(messages, models.json_schema(), models, subset)
    if prompt.tokens > PROMPT_TOKEN_BUDGET:
        raise SubsetError(f"提議 prompt 估算 {prompt.tokens} token，超過上限 {PROMPT_TOKEN_BUDGET}")
    return prompt
