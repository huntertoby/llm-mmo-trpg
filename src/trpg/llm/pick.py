"""技能「挑選模式」的 LLM 一步：從排好的候選挑一個並命名（Phase PK-1；提案第 7.3～7.6 節）。

:func:`pick_skill`：

1. 候選（:func:`trpg.skillgen.skill_pick.pick_slate`，或呼叫端給的 ``slate``）。
2. 候選是空的 → 照現行退回 **技能池 → 工坊**（``fallback_skill(skip_composer=True)``；
   組合器已在候選池抽過）；候選少於 ``pool.min_for_llm`` 個 → 不呼叫 LLM，直接用第一名。
3. 否則一次呼叫完成挑選＋命名（:mod:`trpg.llm.prompts.pick`，``skill-pick/1``）。回應先過
   pydantic（``PickText``），再檢查 index 範圍、名稱與兩段文字（同命名步驟：長度、字元集、禁字、
   重名、簡體、世界觀詞、古風詞、和效果一致）。不合格帶 ``<errors>`` 重試，最多
   ``max_attempts`` 次（預設 3＝重試 2 次）。
4. 用盡次數、連不上模型 → 取 **分數最高的那個**，名稱用組合式名稱（``fallback_naming``）。

LLM 不能改候選：結果只把名稱與敘事換掉（``apply_naming``）；手寫技能（技能池）保留原本的名稱與敘事。
耗時不進任何確定性狀態；相同輸入、相同 LLM 回應必得相同結果。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.effect_words import EffectWords, load_effect_words
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_elements
from trpg.content.world import WorldStyle, load_world_style
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.consistency import NameCheck, skill_facts, strict_facts
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.naming import (
    NamingText,
    apply_naming,
    check_consistency,
    check_naming,
    fallback_naming,
)
from trpg.llm.prompts.pick import PICK_PROMPT_VERSION, build_pick_messages, pick_schema
from trpg.llm.response import clean_response
from trpg.narrative.skills import skill_card
from trpg.skillgen.candidates import LlmTrace
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_offer import OfferPicker, SlotChoice, SlotPick
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import FallbackError, fallback_skill
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.proposal_topic import LlmAttempt, LlmProposer
from trpg.skillgen.skill_pick import PickSlate, element_partners, pick_slate, synergy_links

__all__ = [
    "DEFAULT_PICK_ATTEMPTS",
    "OFFER_BUDGET_S",
    "PickOutcome",
    "PickSource",
    "PickText",
    "candidate_card",
    "fit_notes",
    "make_offer_picker",
    "make_pick_proposer",
    "mock_offer_picker",
    "mock_pick_client",
    "pick_skill",
]

DEFAULT_PICK_ATTEMPTS = 3
"""最多呼叫幾次（提案 7.6：最多重試 2 次）。"""

type PickSource = Literal["llm", "top", "pool", "workshop"]
"""``llm``＝LLM 挑選並命名；``top``＝分數第一名（LLM 失敗、連不上或候選太少）；``pool``／
``workshop``＝候選池是空的，照現行退回。"""

_RARITY_ZH = {"common": "普通", "rare": "稀有", "epic": "史詩", "legendary": "傳說"}
_KIND_ZH = {"active": "主動", "passive": "被動", "reaction": "反應", "stance": "姿態"}


class PickText(BaseModel):
    """挑選回應的格式（多餘欄位直接拒絕）。"""

    model_config = ConfigDict(extra="forbid")

    pick: int
    name_zh: str
    concept: str
    cast_flavor: str

    def naming(self) -> NamingText:
        return NamingText(name_zh=self.name_zh, concept=self.concept, cast_flavor=self.cast_flavor)


@dataclass(frozen=True, slots=True)
class PickOutcome:
    """:func:`pick_skill` 的結果。``skill`` 是最後收下的技能（已命名）；``index`` 是 LLM 選的編號
    （不是 LLM 決定時為 ``None``）；``picked`` 是收下的候選在 ``slate.ranked`` 的位置。"""

    skill: SkillDef
    source: PickSource
    slate: PickSlate
    index: int | None = None
    picked: int | None = None
    attempts: int = 0
    codes: tuple[str, ...] = ()
    reason: str | None = None
    name_source: Literal["llm", "fallback", "handwritten"] = "fallback"
    raws: tuple[str, ...] = field(default=(), compare=False, repr=False)
    """每次呼叫的原始輸出（只給量測腳本；不進存檔）。"""


# ---------------------------------------------------------------------------
# prompt 的資料
# ---------------------------------------------------------------------------


def _keyword_names(library: ContentLibrary, skill: SkillDef) -> dict[str, list[str]]:
    found = derive_keywords(skill, library.keywords, exclusive_only=True)
    out: dict[str, list[str]] = {}
    if found.makes:
        out["makes"] = [plain_name(k, library) for k in found.makes]
    if found.uses:
        out["uses"] = [plain_name(k, library) for k in found.uses]
    return out


def fit_notes(library: ContentLibrary, skill: SkillDef, player: PickPlayer | None) -> list[str]:
    """PK-1b：候選和玩家手上技能的關係（卡片的 ``fit``；給 LLM 判斷主題）：協同（依手上技能分組，
    列接上的關鍵字）、同元素的手上技能、共同的其他關鍵字。沒有玩家資料時是空的。"""
    if player is None or not player.held_skills:
        return []
    notes: list[str] = []
    linked: dict[str, list[str]] = {}
    for held, keyword in synergy_links(library, skill, player):
        names = linked.setdefault(held.name_zh, [])
        word = plain_name(keyword, library)
        if word not in names:
            names.append(word)
    notes += [f"和手上「{name}」配合（{'、'.join(words)}）" for name, words in linked.items()]
    partners = element_partners(skill, player)
    if partners:
        element = "、".join(sorted(e.display_name for e in skill_elements(skill)))
        who = "、".join(f"「{s.name_zh}」" for s in partners)
        notes.append(f"和手上{who}同元素（{element}）")
    mine = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    held_kw = {
        k
        for held in player.held_skills
        for k in derive_keywords(held, library.keywords, exclusive_only=True).all()
    }
    shared = [plain_name(k, library) for k in mine if k in held_kw]
    if shared:
        notes.append(f"手上技能也有的關鍵字：{'、'.join(shared)}")
    return notes


def candidate_card(
    library: ContentLibrary,
    skill: SkillDef,
    index: int,
    *,
    fixed: bool = False,
    fit: Sequence[str] = (),
) -> dict[str, Any]:
    """一張候選的精簡卡片（中文、帶數值、沒有代號；提案 7.3）。``fixed``＝手寫技能，附原本名稱；
    ``fit``＝和玩家手上技能的關係（PK-1b，:func:`fit_notes`；空的不寫）。"""
    card = skill_card(library, skill)
    out: dict[str, Any] = {"index": index}
    if fixed:
        out["fixed_name"] = skill.name_zh
    out["kind"] = card.kind
    out["skeleton"] = card.skeleton_zh
    out["category"] = f"{card.category}（{card.weapon_req}）"
    out["cost"] = list(card.cost)
    out["shape"] = card.shape
    if card.timing is not None:  # 被動的觸發時機、反應技的反應時機
        out["timing"] = card.timing
    if card.condition is not None:
        out["condition"] = card.condition
    out["effects"] = list(card.effects)
    if card.element:
        out["element"] = card.element
    keywords = _keyword_names(library, skill)
    if keywords:
        out["keywords"] = keywords
    if fit:
        out["fit"] = list(fit)
    return out


def _request_payload(
    library: ContentLibrary,
    request: ProposalRequest,
    style: WorldStyle,
    weapon: str | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"style": style.style_payload(request.region)}
    out["weapon"] = weapon or "依技能需求"
    out["tier"] = request.tier
    out["rarity"] = _RARITY_ZH.get(request.rarity, request.rarity)
    if request.kind is not None:
        out["kind"] = _KIND_ZH.get(request.kind, request.kind)
    out["keywords"] = [plain_name(k, library) for k in request.keywords]
    return out


def _player_payload(library: ContentLibrary, player: PickPlayer | None) -> dict[str, Any]:
    skills = () if player is None else player.held_skills
    return {
        "skills": [
            {"name": s.name_zh, "keywords": _keyword_names(library, s)}
            for s in sorted(skills, key=lambda s: s.id)
        ]
    }


# ---------------------------------------------------------------------------
# 檢查與退回
# ---------------------------------------------------------------------------


def _parse(raw: str) -> PickText | str:
    try:
        return PickText.model_validate(json.loads(clean_response(raw)))
    except (json.JSONDecodeError, ValidationError):
        return "response.invalid"


def _feedback(errors: list[NameCheck], number: int, limit: int) -> str:
    payload = {
        "attempt": number,
        "max_attempts": limit,
        "errors": [{"code": e.code, "message": e.message} for e in errors],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _named(
    library: ContentLibrary, skill: SkillDef, used: Collection[str], *, handwritten: bool
) -> SkillDef:
    """不是 LLM 命名時的文字：手寫技能保留原文；組合器的換成組合式名稱與模板敘事。"""
    if handwritten:
        return skill
    return apply_naming(skill, fallback_naming(library, skill, used))


@dataclass(slots=True)
class _Pick:
    """一次挑選的狀態（重試迴圈）。"""

    client: LLMClient
    library: ContentLibrary
    slate: PickSlate
    messages_for: Callable[[str | None, str | None], list[Any]]
    schema: dict[str, Any]
    style: WorldStyle
    words: EffectWords
    used: set[str]
    archaic_ok: bool
    strict: bool = False
    """PK-2：加嚴的一致性檢查（高處、地形、墜落、打擊、形狀、單字元素）。"""
    codes: list[str] = field(default_factory=list)
    raws: list[str] = field(default_factory=list)
    previous: str | None = None
    feedback: str | None = None

    def check(self, text: PickText) -> list[NameCheck]:
        if not 0 <= text.pick < len(self.slate.ranked):
            return [NameCheck("pick.out_of_range", f"pick 要是 0～{len(self.slate.ranked) - 1}。")]
        candidate = self.slate.ranked[text.pick]
        if candidate.source == "pool":  # 手寫技能保留原本的名稱與敘事，不檢查文字
            return []
        naming = text.naming()
        if self.strict:
            facts = strict_facts(self.library, candidate.skill)
        else:
            facts = skill_facts(self.library, candidate.skill)
        errors = check_naming(naming, self.style.naming, self.used, archaic_ok=self.archaic_ok)
        return errors + check_consistency(naming, facts, self.words, strict=self.strict)

    def attempt(self, number: int, limit: int) -> PickText | str | None:
        """一次呼叫：合格回傳回應；應立即退回時回傳原因；可以重試時回傳 ``None``。"""
        try:
            raw = self.client.complete(
                self.messages_for(self.previous, self.feedback), json_schema=self.schema
            )
        except LLMUnavailable as exc:
            self.codes.append("llm.unavailable")
            return f"llm.unavailable：{exc}"
        except (LLMTimeout, LLMBadResponse) as exc:
            self.codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            return None
        self.raws.append(raw)
        parsed = _parse(raw)
        if isinstance(parsed, str):
            self.codes.append(parsed)
            self.previous = raw
            self.feedback = _feedback(
                [NameCheck(parsed, "回應必須是只含 pick、name_zh、concept、cast_flavor 的 JSON。")],
                number,
                limit,
            )
            return None
        errors = self.check(parsed)
        if not errors:
            return parsed
        self.codes.extend(e.code for e in errors)
        self.previous = parsed.model_dump_json()
        self.feedback = _feedback(errors, number, limit)
        return None


def pick_skill(
    client: LLMClient,
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    taken: Collection[str] = (),
    player: PickPlayer | None = None,
    slate: PickSlate | None = None,
    max_attempts: int = DEFAULT_PICK_ATTEMPTS,
    world: WorldStyle | None = None,
    words: EffectWords | None = None,
    weapon: str | None = None,
    strict: bool = False,
) -> PickOutcome:
    """挑選模式的一題（見模組說明）。``taken`` 是已用過的名稱（內容庫技能的名稱一併避開）；
    ``weapon`` 是持有者手上的武器名稱（命名照它寫）；``strict``（PK-2）＝名稱與描述用加嚴的一致性
    檢查（``effect_words.yaml`` 的 ``strict: true`` 詞組：高處、地形、墜落、打擊、形狀、單字元素；
    要在效果、條件或形狀裡找得到對應），不合格照常重試、用盡退回組合式名稱。候選池與技能池、工坊都做不出時丟
    :class:`~trpg.skillgen.proposal_fallback.FallbackError`（上層處理，同現行）。"""
    slate = (
        slate if slate is not None else pick_slate(library, request, ctx, seed=seed, player=player)
    )
    used = set(taken) | {s.name_zh for s in library.skills.values()}
    if not slate.ranked:
        held = () if player is None else tuple(sorted(s.id for s in player.held_skills))
        skill, origin = fallback_skill(
            library, request, ctx, seed=seed, skip_composer=True, exclude_ids=held
        )
        source: PickSource = "pool" if origin == "pool" else "workshop"
        named = _named(library, skill, used, handwritten=source == "pool")
        return PickOutcome(
            named, source, slate, reason="pick.empty", name_source=_text_source(source)
        )
    if len(slate.ranked) < library.skill_pick.pool.min_for_llm:
        return _top(library, slate, used, reason="pick.too_few")
    style = world if world is not None else load_world_style()
    payload = _request_payload(library, request, style, weapon)
    who = _player_payload(library, player)
    cards = [
        candidate_card(
            library,
            c.skill,
            i,
            fixed=c.source == "pool",
            fit=fit_notes(library, c.skill, player),
        )
        for i, c in enumerate(slate.ranked)
    ]

    def messages_for(previous: str | None, errors: str | None) -> list[Any]:
        return build_pick_messages(
            payload, who, cards, sorted(taken), previous=previous, errors=errors, world=style
        )

    loop = _Pick(
        client,
        library,
        slate,
        messages_for,
        pick_schema(len(slate.ranked), style),
        style,
        words if words is not None else load_effect_words(),
        used,
        style.archaic_ok(request.region),
        strict,
    )
    for number in range(1, max_attempts + 1):
        found = loop.attempt(number, max_attempts)
        if isinstance(found, PickText):
            chosen = slate.ranked[found.pick]
            handwritten = chosen.source == "pool"
            skill = chosen.skill if handwritten else apply_naming(chosen.skill, found.naming())
            return PickOutcome(
                skill,
                "llm",
                slate,
                index=found.pick,
                picked=found.pick,
                attempts=number,
                codes=tuple(dict.fromkeys(loop.codes)),
                name_source="handwritten" if handwritten else "llm",
                raws=tuple(loop.raws),
            )
        if found is not None:
            return _top(library, slate, used, reason=found, attempts=number, loop=loop)
    last = loop.codes[-1] if loop.codes else "—"
    return _top(
        library,
        slate,
        used,
        reason=f"用盡 {max_attempts} 次（最後：{last}）",
        attempts=max_attempts,
        loop=loop,
    )


def _text_source(source: str) -> Literal["fallback", "handwritten"]:
    return "handwritten" if source == "pool" else "fallback"


def _top(
    library: ContentLibrary,
    slate: PickSlate,
    used: Collection[str],
    *,
    reason: str,
    attempts: int = 0,
    loop: _Pick | None = None,
) -> PickOutcome:
    first = slate.ranked[0]
    handwritten = first.source == "pool"
    return PickOutcome(
        _named(library, first.skill, used, handwritten=handwritten),
        "top",
        slate,
        picked=0,
        attempts=attempts,
        codes=() if loop is None else tuple(dict.fromkeys(loop.codes)),
        reason=reason,
        name_source="handwritten" if handwritten else "fallback",
        raws=() if loop is None else tuple(loop.raws),
    )


# ---------------------------------------------------------------------------
# 接成提議器、Mock
# ---------------------------------------------------------------------------


def make_pick_proposer(
    client: LLMClient | Callable[[PickSlate, int], LLMClient],
    library: ContentLibrary,
    *,
    max_attempts: int = DEFAULT_PICK_ATTEMPTS,
    player: Callable[[], PickPlayer | None] | None = None,
    weapon: Callable[[ProposalContext], str | None] | None = None,
) -> LlmProposer:
    """挑選模式的 :data:`~trpg.skillgen.proposal_topic.LlmProposer`（和 ``make_proposer`` 同一個
    介面，之後接一輪或大世界的出題用；PK-1 還沒接上任何出題流程）。``client`` 可以是固定的
    client，或依（候選，種子）建立 client 的函式（Mock 用）。候選池是空的（退技能池、工坊）算
    失敗，交給呼叫端原本的退回順序；LLM 失敗改用第一名算成功（``pick_reason`` 記原因）。同一個
    提議器產生的技能不重名。"""
    taken: set[str] = set()

    def propose(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
        who = player() if player is not None else None
        slate = pick_slate(library, request, ctx, seed=seed, player=who)
        used = client if isinstance(client, LLMClient) else client(slate, seed)
        try:
            outcome = pick_skill(
                used,
                library,
                request,
                ctx,
                seed=seed,
                taken=taken,
                player=who,
                slate=slate,
                max_attempts=max_attempts,
                weapon=None if weapon is None else weapon(ctx),
            )
        except (FallbackError, ValueError) as exc:
            return LlmAttempt(None, 0, (), str(exc), prompt_version=PICK_PROMPT_VERSION)
        taken.add(outcome.skill.name_zh)
        base = LlmAttempt(
            None,
            outcome.attempts,
            outcome.codes,
            outcome.reason,
            prompt_version=PICK_PROMPT_VERSION if outcome.attempts else None,
            pick_seeds=slate.seeds,
            pick_designs=slate.designs,
            pick_index=outcome.index,
            pick_reason=outcome.reason,
        )
        if outcome.source in ("pool", "workshop"):
            return base
        name_source: Literal["llm", "fallback"] = (
            "llm" if outcome.name_source == "llm" else "fallback"
        )
        return replace(
            base,
            skill=outcome.skill,
            reason=None,
            name_source=name_source,
            name_attempts=outcome.attempts,
        )

    return propose


def mock_pick_client(
    library: ContentLibrary,
    slate: PickSlate,
    seed: int,
    *,
    index: int = 0,
    attempts: int = DEFAULT_PICK_ATTEMPTS,
) -> MockLLMClient:
    """Mock 挑選器（不需網路與金鑰）：永遠挑 ``index``，名稱與兩段文字照 Mock 命名
    （``candidate_source.mock_naming_client``：依種子挑詞、概念列效果摘要）。``index`` 超出範圍時
    照填，用來測退回。"""
    target = slate.ranked[index].skill if 0 <= index < len(slate.ranked) else None
    if target is None and slate.ranked:
        target = slate.ranked[0].skill
    if target is None:
        return MockLLMClient([])
    text: Mapping[str, Any] = json.loads(
        mock_naming_client(library, target, seed).complete([], json_schema=None)
    )
    body = json.dumps({"pick": index, **text}, ensure_ascii=False)
    return MockLLMClient([body] * attempts)


# ---------------------------------------------------------------------------
# PK-2：接上三選一（每格各挑一）
# ---------------------------------------------------------------------------

OFFER_BUDGET_S = 10.0
"""一份三選一請 LLM 的時間上限（秒；06 6.34.7「超過 10 秒改給組合器或模板版」）：用完後剩下的格子
不再呼叫，照分數第一名。"""


def _slot_trace(slot: SlotPick, outcome: PickOutcome) -> LlmTrace:
    llm = outcome.source == "llm"
    return LlmTrace(
        keywords=slot.keywords,
        rarity=slot.request.rarity,
        core_primitive=None,
        menu_seed=None,
        theme=None,
        attempts=outcome.attempts,
        ok=llm,
        codes=outcome.codes,
        reason=None if llm else outcome.reason,
        name_source="llm" if outcome.name_source == "llm" else "fallback",
        name_attempts=outcome.attempts,
        prompt_version=PICK_PROMPT_VERSION if outcome.attempts else None,
        pick_seeds=outcome.slate.seeds,
        pick_designs=outcome.slate.designs,
        pick_index=outcome.index,
        pick_reason=outcome.reason,
    )


def make_offer_picker(
    client: LLMClient | Callable[[PickSlate, int], LLMClient],
    library: ContentLibrary,
    *,
    max_attempts: int = DEFAULT_PICK_ATTEMPTS,
    budget_s: float = OFFER_BUDGET_S,
    clock: Callable[[], float] = time.monotonic,
) -> OfferPicker:
    """挑選模式接上三選一的挑選器（PK-2，:data:`~trpg.skillgen.pick_offer.OfferPicker`）：依序每格
    呼叫 :func:`pick_skill`（排好的候選由 ``trpg.skillgen.pick_offer`` 給，這裡不再抽）。

    - 候選少於 ``pool.min_for_llm`` 個 → 這格不請 LLM（``None``，照第一名、保留原名）。
    - 這份三選一已經用掉 ``budget_s`` 秒 → 剩下的格子不請 LLM（耗時只決定「請不請」，結果照樣記進
      存檔；重播只讀存檔，不呼叫 LLM）。
    - LLM 失敗 → 第一名＋組合式名稱（``llm`` 為假，紀錄的 ``ok`` 為假）。

    同一份三選一的名稱不重複，也不和玩家手上技能的名稱重複。``client`` 可以是固定的 client，或
    依（候選，種子）建立 client 的函式（Mock 用）。"""

    def pick(slots: Sequence[SlotPick], player: PickPlayer) -> list[SlotChoice | None]:
        taken = {s.name_zh for s in player.held_skills}
        start = clock()
        out: list[SlotChoice | None] = []
        for slot in slots:
            if len(slot.slate.ranked) < library.skill_pick.pool.min_for_llm:
                out.append(None)
                continue
            if clock() - start >= budget_s:
                out.append(None)
                continue
            used = client if isinstance(client, LLMClient) else client(slot.slate, slot.seed)
            ctx = ProposalContext(tier=slot.request.tier, rarity=slot.request.rarity)
            outcome = pick_skill(
                used,
                library,
                slot.request,
                ctx,
                seed=slot.seed,
                taken=sorted(taken),
                player=player,
                slate=slot.slate,
                max_attempts=max_attempts,
                weapon=slot.weapon_zh,
                strict=True,
            )
            taken.add(outcome.skill.name_zh)
            out.append(
                SlotChoice(
                    position=outcome.picked if outcome.picked is not None else 0,
                    skill=outcome.skill,
                    trace=_slot_trace(slot, outcome),
                    llm=outcome.source == "llm",
                )
            )
        return out

    return pick


def mock_offer_picker(
    library: ContentLibrary, *, index: int = 0, attempts: int = DEFAULT_PICK_ATTEMPTS
) -> OfferPicker:
    """Mock 挑選器（PK-2；不需網路與金鑰）：每格永遠挑 ``index``（超出範圍時照填，用來測退回），
    名稱照 Mock 命名（:func:`mock_pick_client`）。"""
    return make_offer_picker(
        lambda slate, seed: mock_pick_client(library, slate, seed, index=index, attempts=attempts),
        library,
        max_attempts=attempts,
        budget_s=float("inf"),
    )
