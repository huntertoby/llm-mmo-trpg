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
from trpg.skillgen.proposal import WEAPON_REQ_DOC, ProposalModels
from trpg.skillgen.proposal.schema_shape import shape_schema
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
    "LOCAL_CONTEXT_TOKENS",
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


BUDGET_NOTE_ZH = (
    "數值由遊戲補，但效果總強度必須到這一階預算的 70%～100%。"
    "只有一個沒有數值的核心效果（位移、淨化、地形、傳送等）一定過弱："
    "骨架允許附帶效果時請再加一個，依技能主題選，不一定是傷害"
    "（例：pull＋施加狀態、pull＋damage、cleanse＋heal、cleanse＋shield 都可；只有 pull 不可）。"
    "冷卻由遊戲依形狀自動補（大範圍形狀會加冷卻），不用填。"
    "選填欄位（代價、變奏、條件）越少越好，但效果數量不在此限。"
)
"""題目區的預算說明（Phase 6S-2：升級候選退回的第一大原因是單一核心效果過弱 ``budget.weak``；
6S-2c：例子改成中性，不暗示附帶效果固定是傷害）。"""
KEYWORD_NOTE_ZH = (
    "技能必須帶到 keywords 的每一個：照 available.keywords 的 ways 選一種寫法"
    "（例：ways 有 apply_status（status＝commanding）就加一個施加 commanding 給友方的效果）。"
)
"""題目有關鍵字時的說明（Phase 6S-2：``keyword.required``）。"""
CATEGORY_NOTE_ZH = "技能類別：weapon＝武器技（用武器出招），spell＝法術技。weapon_req " + (
    WEAPON_REQ_DOC
)
"""頂層欄位 ``category``／``weapon_req`` 的說明（LB-2：約束解碼看不到 schema 的說明文字，配對規則
原本只寫在 schema 的 ``description``，模型讀不到，Gemma 常填錯）。"""
ELEMENT_NOTE_ZH = "技能本身的元素，填在 JSON 頂層的 element（效果裡各自的 element 不算）。"
"""頂層欄位 ``element`` 的說明（LB-2：``exclusion.terrain_needs_earth`` 時 Gemma 只在效果裡寫
earth、頂層沒填，連續三次一樣）。"""
EFFECTS_NOTE_ZH = (
    "effects 第一個放核心效果；核心以外的每個效果都算附帶效果，數量不能超過所選骨架"
    " secondary.note 寫的上限（例：上限 1 個時，核心以外只能再放 1 個效果）。"
)
"""``effects`` 的說明（LB-2：``skeleton.secondary_count``）。"""
VARIANTS_NONE_ZH = "這個稀有度不能帶變奏：不要填 variants。"
VARIANTS_NOTE_ZH = (
    "選填，最多 {limit} 個；不填最容易通過。每個變奏＝id、name_zh、when（觸發條件）"
    "＋ shape、range_delta、element、add_effect、replace_effect 其中 1～2 項（不能 3 項以上）。"
    "range_delta 是射程加值，只能填 1 或 2（射程變遠），而且技能的形狀（或變奏換上的 shape）"
    "要有數字射程。{ranged}"
    "replace_effect 的 index 是要換掉的 effects 位置（從 0 起算），"
    "不能指向主傷害（第一個 damage 效果）；要加強傷害請用 add_effect。"
)
"""``variants`` 的說明（LB-2：變奏數量、替換內容 1～2 項、主傷害不能被換掉；LB-2b：射程加值
``range_delta``，``{ranged}`` 是 :func:`_ranged_shapes_note` 列的這題形狀）。"""
RANGED_SHAPES_ZH = (
    "這題有射程的形狀：{ranged}（shape.range 填 weapon 時不算）；"
    "{plain} 沒有射程，用這些形狀時不能填 range_delta。"
)
"""這題哪些形狀能配 ``range_delta``（LB-2b：初版重測 Gemma 在 line、cone、ring 上填 range_delta，
50 次嘗試 26 次被驗證器擋下）。"""
RANGED_SHAPES_NONE_ZH = "這題的形狀都沒有射程，不能填 range_delta。"
PASSIVE_NOTE_ZH = (
    "被動技能的 trigger.target 是 self 時（沒有 target 欄位的觸發一律是 self），"
    '每個效果都要明寫 "affects": "self"（不寫時預設是 enemies 或 allies，會被擋下）。'
)
"""被動技能的說明（LB-2：``passive.affects``；LB-2b：初版重測 Gemma 在 Q12 用沒有 target 欄位的
``on_turn_start``、效果不寫 ``affects``，三次都被 ``passive.affects`` 擋下，改成要明寫）。"""
LOCAL_CONTEXT_TOKENS = 16_384
"""本機模型（LM Studio）實際載入的上下文長度；system＋子集目錄＋題目＋ ``max_tokens`` 必須放得下
（``tests/llm/test_prompt_prefix.py`` 檢查）。"""


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


def _element_rules(library: ContentLibrary, subset: ProposalSubset) -> list[str]:
    """要求技能元素的互斥規則（``require.elements_any``）中，這題用得到的那些 → 一句說明。"""
    statuses = "apply_status" in subset.primitives
    lines: list[str] = []
    for rule in library.exclusions.rules:
        need = rule.require.elements_any if rule.require is not None else None
        if not need or rule.when is None:
            continue
        matches = (rule.when, *(rule.when.any_of or ()))
        prims = sorted(
            {p for m in matches for p in (m.primitives_any or ()) if p in subset.primitives}
        )
        stats = sorted({s for m in matches for s in (m.statuses or ())}) if statuses else []
        used = [*prims, *(f"狀態 {s}" for s in stats)]
        if used:
            wanted = " 或 ".join(str(e) for e in need)
            lines.append(
                f"用到 {'、'.join(used)} 時，頂層 element 一定要填 {wanted}（{rule.name_zh}）。"
            )
    return lines


def field_notes(
    library: ContentLibrary, request: ProposalRequest, subset: ProposalSubset
) -> dict[str, str]:
    """頂層欄位的說明（LB-2）：約束解碼看不到 schema 的 ``description``，欄位的意思與跨欄位規則
    要寫進 prompt 的資料區，模型才讀得到。只列這題用得到的規則。"""
    notes = {
        "category": CATEGORY_NOTE_ZH,
        "element": "".join([ELEMENT_NOTE_ZH, *_element_rules(library, subset)]),
        "effects": EFFECTS_NOTE_ZH,
    }
    if subset.kind == "passive":
        notes["trigger"] = PASSIVE_NOTE_ZH
    else:
        limit = library.ruleset.core.variant_max_by_rarity.get(request.rarity, 0)
        notes["variants"] = (
            VARIANTS_NOTE_ZH.format(limit=limit, ranged=_ranged_shapes_note(library, subset))
            if limit
            else VARIANTS_NONE_ZH
        )
    return notes


def _ranged_shapes_note(library: ContentLibrary, subset: ProposalSubset) -> str:
    """這題的形狀哪些有數字射程（形狀定義有 ``range`` 參數；LB-2b，``range_delta`` 只能配它們）。"""
    shapes = library.ruleset.shapes.by_id()
    ranged = [s for s in subset.shapes if s in shapes and "range" in shapes[s].params]
    plain = [s for s in subset.shapes if s not in ranged]
    if not ranged:
        return RANGED_SHAPES_NONE_ZH
    if not plain:
        return f"這題有射程的形狀：{'、'.join(ranged)}（shape.range 填 weapon 時不算）。"
    return RANGED_SHAPES_ZH.format(ranged="、".join(ranged), plain="、".join(plain))


def _request_payload(
    request: ProposalRequest,
    subset: ProposalSubset,
    names: dict[str, str],
    world: WorldStyle | None = None,
    fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tier": request.tier,
        "rarity": request.rarity,
        "kind": subset.kind,
        "keywords": [{"id": k, "name_zh": names[k]} for k in request.keywords],
        "budget_note_zh": BUDGET_NOTE_ZH,
    }
    if fields:
        payload["fields_note_zh"] = fields
    if world is not None and request.region is not None:
        # 6L-1（#126）：取得地點的區域與風格。中性（創角、許願池、測試原型）不帶：提議只出結構，
        # 名稱與描述由命名步驟照風格寫
        payload["style"] = world.style_payload(request.region)
    if request.keywords:  # 6S-2：keyword.required 是升級候選第二大退回原因
        payload["keyword_note_zh"] = KEYWORD_NOTE_ZH
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


def _models_and_schema(
    library: ContentLibrary, subset: ProposalSubset, request: ProposalRequest
) -> tuple[ProposalModels, dict[str, Any]]:
    """提議模型與送給約束解碼的 schema（LB-2）。

    頂層先依技能類別分支（``weapon_req`` 只能選與 ``category`` 配對的值；約束解碼看不到 schema 的
    說明文字，4-L10a 寫在 ``WEAPON_REQ_DOC`` 的配對規則模型其實讀不到）；分支後超過
    :data:`SCHEMA_CHAR_LIMIT` 時改用不分支的模型（配對規則仍寫在 prompt 的欄位說明）。變奏數量的
    稀有度上限與「1～2 項替換內容」也寫進 schema（:func:`shape_schema`；驗證不變）。"""
    limit = library.ruleset.core.variant_max_by_rarity.get(request.rarity, 0)
    models = build_subset_models(library, subset, split_category=True)
    schema = shape_schema(models.json_schema(), variant_limit=limit)
    if json_chars(schema) > SCHEMA_CHAR_LIMIT:
        models = build_subset_models(library, subset)
        schema = shape_schema(models.json_schema(), variant_limit=limit)
    return models, schema


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

    LLM-1C：區塊順序與題目區改回 LLM-1 之前（``<request>`` 在最前、固定說明放在題目區內，
    接著 ``<available>``）；``<available>`` 是這題的子集，依 ``menu_seed`` 打亂（LLM-1A／1B）。

    子集大小的預算 = :data:`PROMPT_TOKEN_BUDGET` − 系統指令 − :data:`USER_RESERVE_TOKENS`；組好後
    再檢查整體訊息估算（含玩家文字與重試回饋）仍不超過上限、schema 字元數不超過
    :data:`SCHEMA_CHAR_LIMIT`，否則丟
    :class:`~trpg.skillgen.proposal_subset.SubsetError`。未知的骨架或關鍵字 ID 丟 ``ValueError``。
    """
    style = world if world is not None else load_world_style()
    system_tokens = estimate_messages_tokens(build_skill_proposal_messages({}, world=style)[:1])
    budget = PROMPT_TOKEN_BUDGET - system_tokens - USER_RESERVE_TOKENS
    subset = select_subset(library, request, token_budget=budget)
    names = {k.id: k.name_zh for k in library.ruleset.keywords.keywords}
    messages = build_skill_proposal_messages(
        _request_payload(request, subset, names, style, field_notes(library, request, subset)),
        available=available_payload(library, subset),
        previous_proposal=previous_proposal,
        errors=errors,
        player_text=player_text,
        world=style,
    )
    models, schema = _models_and_schema(library, subset, request)
    prompt = ProposalPrompt(messages, schema, models, subset)
    if prompt.tokens > PROMPT_TOKEN_BUDGET:
        raise SubsetError(f"提議 prompt 估算 {prompt.tokens} token，超過上限 {PROMPT_TOKEN_BUDGET}")
    if prompt.schema_chars > SCHEMA_CHAR_LIMIT:
        raise SubsetError(f"提議 schema {prompt.schema_chars} 字元，超過上限 {SCHEMA_CHAR_LIMIT}")
    return prompt
