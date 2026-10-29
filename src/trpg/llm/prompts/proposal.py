"""技能提議 prompt 的組裝（Phase 4-L4）：題目 → 篩選子集 → 模型、JSON schema、available → messages。

``build_proposal_prompt`` 把 :mod:`trpg.skillgen.proposal_subset`（篩選、模型、``available``）與
:func:`~trpg.llm.prompts.builder.build_skill_proposal_messages`（資料區、跳脫）接起來，並確認
system ＋ user 訊息的估算不超過 :data:`PROMPT_TOKEN_BUDGET`；JSON schema 只用於約束解碼、不佔
prompt token（4-L5c），另以字元數上限 :data:`SCHEMA_CHAR_LIMIT` 做健全性檢查。
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
    SCHEMA_CHAR_LIMIT,
    ProposalRequest,
    ProposalSubset,
    SubsetError,
    available_payload,
    build_subset_models,
    json_chars,
    select_subset,
)

__all__ = [
    "PROMPT_TOKEN_BUDGET",
    "SCHEMA_CHAR_LIMIT",
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
        """system ＋ user 訊息的估算（JSON schema 不佔 prompt token）。"""
        return estimate_messages_tokens(self.messages)

    @property
    def schema_chars(self) -> int:
        """JSON schema 的字元數。"""
        return json_chars(self.json_schema)


def estimate_messages_tokens(messages: list[ChatMessage]) -> int:
    return sum(estimate_tokens(m["content"]) for m in messages)


def _request_payload(
    request: ProposalRequest,
    subset: ProposalSubset,
    names: dict[str, str],
    world: WorldStyle | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tier": request.tier,
        "rarity": request.rarity,
        "kind": subset.kind,
        "keywords": [{"id": k, "name_zh": names[k]} for k in request.keywords],
    }
    if request.skeleton is not None:
        payload["skeleton"] = request.skeleton
    if request.weapon_class is not None:  # 技能的武器需求必須與主角的武器相容（4-L6）
        payload["weapon_class"] = request.weapon_class
    if request.core_primitive is not None:  # 題目指定核心原語（4-L6）：提議必須用到它
        payload["core_primitive"] = request.core_primitive
        payload["core_primitive_note_zh"] = (
            f"核心效果必須使用原語 {request.core_primitive}（effects 要有 type 為它的效果）。"
        )
    if request.theme is not None and world is not None:  # 主題詞（4-L6）：不是元素
        theme = next((t for t in world.themes if t.id == request.theme), None)
        if theme is None:
            raise ValueError(
                f"未知的主題 {request.theme!r}（可用：{'、'.join(world.theme_ids())}）"
            )
        payload["theme"] = {"name_zh": theme.name_zh, "hint_zh": theme.hint_zh}
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
    再檢查整體訊息估算（含玩家文字與重試回饋）仍不超過上限、schema 字元數不超過
    :data:`SCHEMA_CHAR_LIMIT`，否則丟
    :class:`~trpg.skillgen.proposal_subset.SubsetError`。未知的骨架或關鍵字 ID 丟 ``ValueError``。
    """
    style = world if world is not None else load_world_style()
    system_tokens = estimate_messages_tokens(build_skill_proposal_messages({}, world=style)[:1])
    budget = PROMPT_TOKEN_BUDGET - system_tokens - USER_RESERVE_TOKENS
    subset = select_subset(library, request, token_budget=budget)
    models = build_subset_models(library, subset)
    names = {k.id: k.name_zh for k in library.ruleset.keywords.keywords}
    messages = build_skill_proposal_messages(
        _request_payload(request, subset, names, style),
        available=available_payload(library, subset),
        previous_proposal=previous_proposal,
        errors=errors,
        player_text=player_text,
        world=style,
    )
    prompt = ProposalPrompt(messages, models.json_schema(), models, subset)
    if prompt.tokens > PROMPT_TOKEN_BUDGET:
        raise SubsetError(f"提議 prompt 估算 {prompt.tokens} token，超過上限 {PROMPT_TOKEN_BUDGET}")
    if prompt.schema_chars > SCHEMA_CHAR_LIMIT:
        raise SubsetError(f"提議 schema {prompt.schema_chars} 字元，超過上限 {SCHEMA_CHAR_LIMIT}")
    return prompt
