"""LLM 提議的題目產生（Phase 4-L6，``docs/phases/Phase4計畫.md`` 3C 節、3F 節）。

候選產生器要請 LLM 提議技能時，由這裡決定 **題目**：稀有度、題目指定的核心原語（依種子與 run 內配額
加權抽出）、輪替選單的種子、主題詞。結構的多樣性由引擎決定，不交給模型的偏好；全部確定性（只用
``Rng``，同種子同 run 狀態必得同題目），結果（題目與生成的技能）寫進 run 紀錄，重播與讀檔不再抽、
不再呼叫 LLM。

:data:`LlmProposer` 是候選產生器注入的 **呼叫端**（真正呼叫模型的程式在 ``trpg.llm``；``skillgen``
不得匯入 ``llm``）：收到題目、技能上下文與種子，回傳 :class:`LlmAttempt`。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, SkillRarity
from trpg.content.world import DEFAULT_WORLD_FILE, load_world_style
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    SubsetError,
    legal_core_primitives,
    select_subset,
)

__all__ = [
    "TOPIC_RARITIES",
    "LlmAttempt",
    "LlmProposer",
    "TopicRequest",
    "composable_keywords",
    "make_topic",
    "pick_core_primitive",
    "primitive_uses",
]

TOPIC_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")
"""候選的 LLM 題目可用的稀有度（傳說要源力代價等提議模型沒有的欄位，不出題）。"""


@dataclass(frozen=True, slots=True)
class LlmAttempt:
    """一次 LLM 提議的結果。``skill`` 為 ``None`` ＝ 失敗（含 3 次重試後退回）；``attempts`` 是呼叫
    次數，``codes`` 是各次嘗試的錯誤代碼（去重、依出現順序），``reason`` 是失敗原因。"""

    skill: SkillDef | None
    attempts: int
    codes: tuple[str, ...] = ()
    reason: str | None = None
    name_source: Literal["llm", "fallback"] | None = None
    """命名（4-L7）的來源：``llm``（生成的名稱與敘事）或 ``fallback``（組合式名稱）；
    沒有命名步驟為 ``None``。"""
    name_attempts: int = 0
    name_codes: tuple[str, ...] = ()
    prompt_version: str | None = None
    """提議 prompt 的版本號（``trpg.llm`` 的 ``PROMPT_VERSION``；4-L8）；沒有請 LLM 為 ``None``。"""
    naming_prompt_version: str | None = None
    """命名 prompt 的版本號（``NAMING_PROMPT_VERSION``；4-L8）；沒有命名步驟為 ``None``。"""


type LlmProposer = Callable[[ProposalRequest, ProposalContext, int], LlmAttempt]
"""（題目，技能上下文，種子）→ :class:`LlmAttempt`。"""


@dataclass(frozen=True, slots=True)
class TopicRequest:
    """出題的輸入：階級、題目關鍵字、種子、run 內已出現的原語次數、主角資料。"""

    tier: int
    keywords: tuple[str, ...]
    seed: int
    uses: Mapping[str, int]
    hero_attributes: Mapping[Attribute, int] | None = None
    held: Mapping[str, str] | None = None
    theme_permille: int = 0
    weapon_class: str | None = None


def composable_keywords(library: ContentLibrary, keywords: Sequence[str]) -> bool:
    """關鍵字都能交給 LLM 出題（``KeywordDef.composable``；形態關鍵字只由手寫內容提供）。"""
    table = library.keywords.by_id()
    return all(k in table and table[k].composable for k in keywords)


def primitive_uses(skills: Sequence[SkillDef]) -> dict[str, int]:
    """一組候選技能的效果原語次數（每個技能對每種原語最多算 1；run 內配額用）。"""
    counts: dict[str, int] = {}
    for skill in skills:
        for primitive in sorted({e.type for e in skill.effects}):
            counts[primitive] = counts.get(primitive, 0) + 1
    return counts


def pick_core_primitive(
    library: ContentLibrary, legal: Sequence[str], uses: Mapping[str, int], rng: Rng
) -> str | None:
    """在合法核心原語中依權重抽一個（權重 ＝ 基礎權重 × 配額折減，``skill_composer.yaml`` 的
    ``llm_topic``；沒出現過或出現少的權重較高）。沒有合法原語回傳 ``None``。"""
    if not legal:
        return None
    rules = library.composer.llm_topic
    weights = [rules.weight_of(p, uses.get(p, 0)) for p in legal]
    roll = rng.randint(1, sum(weights))
    for primitive, weight in zip(legal, weights, strict=True):
        roll -= weight
        if roll <= 0:
            return primitive
    return legal[-1]


@lru_cache(maxsize=4)
def _theme_ids(root: Path) -> tuple[str, ...]:
    try:
        return load_world_style(root / DEFAULT_WORLD_FILE).theme_ids()
    except OSError:
        return ()


def _rarity_order(library: ContentLibrary, rng: Rng) -> list[SkillRarity]:
    """依稀有度權重（``rarity_weights``）不放回抽出的順序（只含 :data:`TOPIC_RARITIES`）。"""
    remaining = list(TOPIC_RARITIES)
    out: list[SkillRarity] = []
    while remaining:
        weights = [max(1, library.composer.rarity_weights[r]) for r in remaining]
        roll = rng.randint(1, sum(weights))
        for rarity, weight in zip(remaining, weights, strict=True):
            roll -= weight
            if roll <= 0:
                out.append(rarity)
                remaining.remove(rarity)
                break
    return out


def make_topic(
    library: ContentLibrary, topic: TopicRequest
) -> tuple[ProposalRequest, ProposalContext, int] | None:
    """依種子出一個題目（提議題目、技能上下文、送給提議迴圈的種子）。

    稀有度依權重抽，題目必須 :func:`select_subset` 得出（否則換下一個稀有度）；核心原語在合法的核心
    原語中依權重與 run 內配額抽，抽出後仍得不出子集就省略（退回 4-L4 行為）。題目關鍵字含不能交給
    LLM 的關鍵字（形態）或所有稀有度都出不了題時回傳 ``None``。"""
    if not composable_keywords(library, topic.keywords):
        return None
    rng = Rng(topic.seed).fork("llm_topic")
    themes = _theme_ids(library.root)
    theme = rng.choice(themes) if themes and rng.chance_permille(topic.theme_permille) else None
    menu_seed = rng.next_u32()
    for rarity in _rarity_order(library, rng):
        request = ProposalRequest(
            topic.tier,
            rarity,
            keywords=topic.keywords,
            menu_seed=menu_seed,
            theme=theme,
            weapon_class=topic.weapon_class,
        )
        try:
            legal = legal_core_primitives(library, request)
            select_subset(library, request)
        except SubsetError:
            continue
        core = pick_core_primitive(library, legal, topic.uses, rng.fork("core"))
        if core is not None:
            with_core = ProposalRequest(
                topic.tier,
                rarity,
                keywords=topic.keywords,
                core_primitive=core,
                menu_seed=menu_seed,
                theme=theme,
                weapon_class=topic.weapon_class,
            )
            try:
                select_subset(library, with_core)
            except SubsetError:
                pass
            else:
                request = with_core
        ctx = ProposalContext(
            topic.tier,
            rarity,
            hero_attributes=topic.hero_attributes,
            held=topic.held,
            weapon_class=topic.weapon_class,
        )
        return request, ctx, rng.next_u32()
    return None
