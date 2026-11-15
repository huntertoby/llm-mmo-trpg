"""技能生成「挑選模式」的候選池與打分（Phase PK-1；挑選模式提案第 4 節、第 7.1～7.2 節、
第 7.5～7.6 節，``docs/phases/技能生成-挑選模式提案.md``）。

流程（純函式、確定性）：

1. **候選池**（:func:`candidate_pool`）：組合器用 ``Rng(seed).fork("pick.pool")`` 分出的種子
   一個一個抽，參數同退回路徑 ``proposal_fallback._from_composer``（題目的種類、骨架、第一個
   關鍵字）；收下的條件也同它（:func:`~trpg.skillgen.proposal_fallback.fits_request`：種類、
   骨架、題目的全部關鍵字，只看專屬規則）＋ ``validate_skill`` 無違規＋武器相容。依 **設計鍵**
   （:func:`design_key`，定義同 ``scripts/recipe_census.py``：骨架＋種類＋形狀類型＋效果類型
   〔含狀態 ID〕＋元素標籤）去重，同一個設計只留第一個；湊滿 ``pool.designs`` 個或抽滿
   ``pool.seeds`` 個種子就停。之後加入技能池裡符合題目的手寫技能（同階級、同稀有度，依 ID 排序；
   設計重複的略過）。
2. **打分**（:func:`score_candidate`）：只比「適不適合這位玩家」，**不比強弱**（預算比例不進分數）。
   關鍵字配合已是第 1 步的篩選；分數＝協同（候選與手上技能的 makes／uses 連線）＋打法（行為紀錄 ×
   關鍵字的 ``actions``）＋屬性路線（:func:`~trpg.skillgen.candidates.route_rank`）＋手寫技能加分。
3. **排序**（:func:`rank_candidates`）：貪婪取前 K，每取一個時扣掉和已取的候選重複的部分（同骨架、
   同形狀、同效果種類、同元素），分數相同依候選池順序。

權重與數量在 ``content/skill_pick.yaml``（:class:`~trpg.content.skill_pick.SkillPickRules`，
數值工坊可改）。LLM 只從排好的前 K 個裡挑（``trpg.llm.pick``）；數值、結構都由這裡保證合法。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.content.skill_pick import PickWeights, SkillPickRules
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Element, top_attribute
from trpg.skillgen.candidates import ROUTE_DUAL, ROUTE_MAIN, behavior_weights, route_rank
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import fits_request, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill

__all__ = [
    "POOL_FORK",
    "CandidatePool",
    "DesignKey",
    "PickCandidate",
    "PickSlate",
    "PickSource",
    "candidate_pool",
    "design_key",
    "design_label",
    "pick_slate",
    "rank_candidates",
    "score_candidate",
]

POOL_FORK = "pick.pool"
"""候選池種子的亂數串流名稱（``Rng(seed).fork(POOL_FORK)``）。"""

type PickSource = Literal["composer", "pool"]
type DesignKey = tuple[str, str, str, tuple[str, ...], tuple[str, ...]]
"""（骨架, 種類, 形狀類型, 效果類型〔含狀態 ID〕, 元素標籤）。"""

_ELEMENTS = frozenset(e.value for e in Element)


def design_key(skill: SkillDef) -> DesignKey:
    """骨架＋種類＋形狀類型＋效果類型（含狀態 ID）＋元素標籤；數值不同算同一個設計（同
    ``scripts/recipe_census.py``）。"""
    effects = tuple(
        sorted(e.type + ":" + str(getattr(e, "status", "") or "") for e in skill.effects)
    )
    elements = tuple(t for t in skill.tags if t in _ELEMENTS)
    return (skill.skeleton, skill.kind, skill.shape.type, effects, elements)


def design_label(key: DesignKey) -> str:
    """設計鍵的一行文字（紀錄與報表用），例
    ``strike|active|single|damage:,status:burning|fire``。"""
    skeleton, kind, shape, effects, elements = key
    return "|".join((skeleton, kind, shape, ",".join(effects), ",".join(elements)))


@dataclass(frozen=True, slots=True)
class PickCandidate:
    """候選池的一招：技能、來源、組合器種子（手寫技能為 ``None``）、設計鍵、分數與各項分數。"""

    skill: SkillDef
    source: PickSource
    seed: int | None
    key: DesignKey
    score: int = 0
    parts: tuple[tuple[str, int], ...] = ()
    """各項分數（``synergy``、``behavior``、``route``、``pool``、``diversity``）；排序後才有
    ``diversity``（負值）。"""


@dataclass(frozen=True, slots=True)
class CandidatePool:
    """:func:`candidate_pool` 的結果：去重後的候選（發現順序）、抽了幾個種子、合法的組合器
    結果數（含重複的設計）。"""

    candidates: tuple[PickCandidate, ...]
    seeds_tried: int
    legal: int


@dataclass(frozen=True, slots=True)
class PickSlate:
    """送給 LLM 的一份候選：排好的前 K 個、去重後的候選池大小、抽了幾個種子。"""

    ranked: tuple[PickCandidate, ...]
    pool_size: int
    seeds_tried: int

    @property
    def seeds(self) -> tuple[int | None, ...]:
        return tuple(c.seed for c in self.ranked)

    @property
    def designs(self) -> tuple[str, ...]:
        return tuple(design_label(c.key) for c in self.ranked)


# ---------------------------------------------------------------------------
# 候選池
# ---------------------------------------------------------------------------


def _usable(skill: SkillDef, ctx: ProposalContext) -> bool:
    if ctx.weapon_class is None:
        return True
    return weapon_problem(skill, ctx.weapon_class, ctx.held) is None


def _composer_skeleton(library: ContentLibrary, request: ProposalRequest, kind: str) -> str | None:
    """同退回路徑：沒指定骨架、種類不是主動時骨架＝種類（被動、反應、姿態各有同名骨架）。"""
    if request.skeleton is None and kind != "active" and kind in library.skeletons:
        return kind
    return request.skeleton


def candidate_pool(
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    rules: SkillPickRules | None = None,
) -> CandidatePool:
    """組合器多種子抽樣＋技能池的手寫技能，依設計去重（見模組說明第 1 點）。"""
    rules = rules if rules is not None else library.skill_pick
    kind = wanted_kind(library, request)
    skeleton = _composer_skeleton(library, request, kind)
    keyword = request.keywords[0] if request.keywords else None
    rng = Rng(seed).fork(POOL_FORK)
    found: dict[DesignKey, PickCandidate] = {}
    legal = 0
    tried = 0
    while tried < rules.pool.seeds and len(found) < rules.pool.designs:
        tried += 1
        composer_seed = rng.next_u32()
        try:
            skill = compose_random_skill(
                composer_seed,
                tier=ctx.tier,
                rarity=ctx.rarity,
                skeleton=skeleton,
                library=library,
                keyword=keyword,
                hero_attributes=ctx.hero_attributes,
                kinds=(kind,),
            )
        except ComposeError:
            continue
        if not fits_request(skill, request, kind, library) or not _usable(skill, ctx):
            continue
        if validate_skill(skill, library):
            continue
        legal += 1
        key = design_key(skill)
        if key not in found:
            found[key] = PickCandidate(skill, "composer", composer_seed, key)
    for skill in sorted(player_skills(library).values(), key=lambda s: s.id):
        if skill.tier != ctx.tier or skill.rarity != ctx.rarity:
            continue
        if not fits_request(skill, request, kind, library) or not _usable(skill, ctx):
            continue
        key = design_key(skill)
        if key not in found:
            found[key] = PickCandidate(skill, "pool", None, key)
    return CandidatePool(tuple(found.values()), tried, legal)


# ---------------------------------------------------------------------------
# 打分與排序
# ---------------------------------------------------------------------------


def _links(library: ContentLibrary, skill: SkillDef, player: PickPlayer) -> int:
    """候選與手上技能的 makes／uses 連線數（只看專屬規則）。"""
    mine = derive_keywords(skill, library.keywords, exclusive_only=True)
    links = 0
    for held in player.held_skills:
        theirs = derive_keywords(held, library.keywords, exclusive_only=True)
        links += sum(1 for k in mine.makes if k in theirs.uses)
        links += sum(1 for k in mine.uses if k in theirs.makes)
    return links


def score_candidate(
    library: ContentLibrary,
    candidate: PickCandidate,
    player: PickPlayer,
    weights: PickWeights,
) -> PickCandidate:
    """候選的基本分（不含多樣性）：協同＋打法＋屬性路線＋手寫技能加分。回傳帶分數的候選。"""
    skill = candidate.skill
    synergy = min(_links(library, skill, player), weights.synergy_max_links)
    keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    by_keyword = behavior_weights(library, player.behavior)
    behavior = min(
        weights.behavior_cap, weights.behavior_per_point * sum(by_keyword[k] for k in keywords)
    )
    route = 0
    if player.hero_attributes:
        rank = route_rank(skill, top_attribute(player.hero_attributes), player.weapon_attrs)
        route = {ROUTE_MAIN: weights.route_main, ROUTE_DUAL: weights.route_dual}.get(rank, 0)
    parts = (
        ("synergy", synergy * weights.synergy_per_link),
        ("behavior", behavior),
        ("route", route),
        ("pool", weights.pool_bonus if candidate.source == "pool" else 0),
    )
    return replace(candidate, score=sum(v for _, v in parts), parts=parts)


def _penalty(candidate: PickCandidate, chosen: Sequence[PickCandidate], w: PickWeights) -> int:
    skeleton, _, shape, effects, elements = candidate.key
    total = 0
    for other in chosen:
        o_skeleton, _, o_shape, o_effects, o_elements = other.key
        total += w.same_skeleton_penalty if skeleton == o_skeleton else 0
        total += w.same_shape_penalty if shape == o_shape else 0
        total += w.same_effects_penalty if effects == o_effects else 0
        total += w.same_element_penalty if elements and elements == o_elements else 0
    return total


def rank_candidates(
    candidates: Sequence[PickCandidate], weights: PickWeights, k: int
) -> tuple[PickCandidate, ...]:
    """貪婪取前 ``k`` 個（見模組說明第 3 點）：每一步取「基本分 − 和已取候選的重複扣分」最高的，
    同分取候選池裡較前面的。回傳的分數是扣分後的分數，``parts`` 多一項 ``diversity``。"""
    remaining = list(enumerate(candidates))
    chosen: list[PickCandidate] = []
    while remaining and len(chosen) < k:
        best_pos = 0
        best_value: int | None = None
        for pos, (_, cand) in enumerate(remaining):
            value = cand.score - _penalty(cand, chosen, weights)
            if best_value is None or value > best_value:
                best_pos, best_value = pos, value
        _, picked = remaining.pop(best_pos)
        penalty = picked.score - (best_value or 0)
        chosen.append(
            replace(picked, score=best_value or 0, parts=(*picked.parts, ("diversity", -penalty)))
        )
    return tuple(chosen)


def pick_slate(
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    player: PickPlayer | None = None,
    rules: SkillPickRules | None = None,
) -> PickSlate:
    """候選池 → 打分 → 排序，回傳送給 LLM 的前 ``pool.top_k`` 個。``player`` 省略時只看
    ``ctx.hero_attributes``（屬性路線）。"""
    rules = rules if rules is not None else library.skill_pick
    who = player or PickPlayer(hero_attributes=dict(ctx.hero_attributes or {}))
    pool = candidate_pool(library, request, ctx, seed=seed, rules=rules)
    scored = [score_candidate(library, c, who, rules.weights) for c in pool.candidates]
    ranked = rank_candidates(scored, rules.weights, rules.pool.top_k)
    return PickSlate(ranked, len(pool.candidates), pool.seeds_tried)
