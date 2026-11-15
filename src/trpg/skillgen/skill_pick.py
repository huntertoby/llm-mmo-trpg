"""技能生成「挑選模式」的候選池與打分（Phase PK-1、PK-1b；挑選模式提案第 4 節、第 7.1～7.2 節、
第 7.5～7.6 節，``docs/phases/技能生成-挑選模式提案.md``）。

流程（純函式、確定性）：

1. **候選池**（:func:`candidate_pool`）：組合器用 ``Rng(seed).fork("pick.pool")`` 分出的種子
   一個一個抽，參數同退回路徑 ``proposal_fallback._from_composer``（題目的種類、骨架、第一個
   關鍵字）；收下的條件也同它（:func:`~trpg.skillgen.proposal_fallback.fits_request`：種類、
   骨架、題目的全部關鍵字，只看專屬規則）＋ ``validate_skill`` 無違規＋武器相容。依 **設計鍵**
   （:func:`design_key`，定義同 ``scripts/recipe_census.py``：骨架＋種類＋形狀類型＋效果類型
   〔含狀態 ID〕＋元素標籤）去重，同一個設計只留第一個；湊滿 ``pool.designs`` 個或抽滿
   ``pool.seeds`` 個種子就停。
   - **PK-1b 同元素補抽**：玩家手上有元素技能、而池裡和它們同元素的設計少於
     ``pool.element_designs`` 個時，另外用 ``Rng(seed).fork("pick.element")``（獨立串流，不影響
     上面的種子）再抽最多 ``pool.element_seeds`` 個，只收同元素的新設計。
   - **手上已有的技能不進候選**（PK-1b）：和手上技能同 ID、同名或同設計鍵的一律略過。
   - 手寫技能（技能池）只在 ``pool.handwritten_max`` > 0 時加入（同階級、同稀有度，依 ID 排序；
     設計重複的略過）；送進前 K 前只留分數最高的 ``handwritten_max`` 個（:func:`pick_slate`）。
2. **打分**（:func:`score_candidate`）：只比「適不適合這位玩家」，**不比強弱**（預算比例不進分數）。
   關鍵字配合已是第 1 步的篩選；分數＝協同（候選與手上技能的 makes／uses 連線條數）＋關鍵字貼合
   （題目關鍵字是製造還是利用；多帶無關關鍵字扣分）＋主題相合（和手上技能共同的關鍵字）＋元素相合
   （手上同元素的技能招數；有元素另加一點）＋打法（行為紀錄 × 關鍵字的 ``actions``）＋屬性路線
   （:func:`~trpg.skillgen.candidates.route_rank`）＋手寫技能加分 − 怪條件
   （:func:`odd_conditions`）− 單薄（PK-2「這招有沒有料」，:func:`thin_reasons`）。
3. **排序**（:func:`rank_candidates`）：貪婪取前 K，每取一個時扣掉和已取的候選重複的部分（同骨架、
   同形狀、同效果種類、同元素），分數相同依候選池順序。

權重與數量在 ``content/skill_pick.yaml``（:class:`~trpg.content.skill_pick.SkillPickRules`，
數值工坊可改）。LLM 只從排好的前 K 個裡挑（``trpg.llm.pick``）；數值、結構都由這裡保證合法。
怪條件只在這裡扣分，**不改組合器與驗證器的合法判定**。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.content.skill_pick import PickWeights, SkillPickRules
from trpg.content.skills import SkillDef, skill_elements, weapon_problem
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
    "ELEMENT_FORK",
    "ODD_FIRST_ROUND",
    "ODD_INSCRIBE",
    "POOL_FORK",
    "THIN_CONDITIONAL",
    "THIN_FEW",
    "THIN_HOLLOW",
    "CandidatePool",
    "DesignKey",
    "PickCandidate",
    "PickSlate",
    "PickSource",
    "candidate_pool",
    "design_key",
    "design_label",
    "drop_thin",
    "element_partners",
    "is_nondamage",
    "odd_conditions",
    "pick_slate",
    "rank_candidates",
    "score_candidate",
    "synergy_links",
    "thin_reasons",
]

POOL_FORK = "pick.pool"
"""候選池種子的亂數串流名稱（``Rng(seed).fork(POOL_FORK)``）。"""
ELEMENT_FORK = "pick.element"
"""PK-1b 同元素補抽的亂數串流名稱（獨立於 :data:`POOL_FORK`）。"""
ODD_FIRST_ROUND = "first_round_non_damage"
"""怪條件：不是傷害的效果（狀態、揭露、刻紋…）只在第一輪才生效。"""
ODD_INSCRIBE = "conditional_inscribe"
"""怪條件：刻紋（本身沒有效果、留給之後的技能讀取）要滿足條件才刻得下。"""

type PickSource = Literal["composer", "pool"]
type DesignKey = tuple[str, str, str, tuple[str, ...], tuple[str, ...]]
"""（骨架, 種類, 形狀類型, 效果類型〔含狀態 ID〕, 元素標籤）。"""

_ELEMENTS = frozenset(e.value for e in Element)
_FIRST_ROUND = "first_round"
_INSCRIBE = "inscribe"
_DAMAGE = frozenset({"damage", "delayed_damage"})
THIN_HOLLOW = "hollow"
"""PK-2 單薄：有作用的效果一個都沒有（只有刻紋、標記、揭露）。"""
THIN_CONDITIONAL = "conditional_only"
"""PK-2 單薄：沒有傷害，而且每個有作用的效果都要條件成立才生效（技能層級或效果自己的條件）。"""
THIN_FEW = "few_effects"
"""PK-2 單薄：史詩以上，有作用的效果少於 ``weights.thin_epic_min_effects`` 個。"""
_HOLLOW_TYPES = frozenset({"inscribe", "reveal"})
"""本身沒有直接作用的效果（刻紋留給之後的技能讀取、揭露只顯示）。"""
_HOLLOW_STATUSES = frozenset({"marked"})
"""本身沒有直接作用的狀態（被標記：只給之後的攻擊優勢）。"""
_HIGH_RARITIES = frozenset({"epic", "legendary"})
_DAMAGING_TYPES = frozenset(
    {"damage", "delayed_damage", "detonate_runes", "charge_through", "hurl_object", "topple"}
)
"""會造成傷害的原語（#142 非傷害保底的判定；``damage_multiplier``、``self_damage_of_hit`` 必須搭配
傷害效果，不另列）。"""


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
    """各項分數（``synergy``、``keyword``、``theme``、``element``、``behavior``、``route``、
    ``pool``、``odd``、``thin``）；排序後才有 ``diversity``（負值）。"""


@dataclass(frozen=True, slots=True)
class CandidatePool:
    """:func:`candidate_pool` 的結果：去重後的候選（發現順序）、抽了幾個種子（含同元素補抽）、
    合法的組合器結果數（含重複的設計）。"""

    candidates: tuple[PickCandidate, ...]
    seeds_tried: int
    legal: int
    element_seeds: int = 0
    """其中同元素補抽用了幾個種子（PK-1b）。"""


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


@dataclass(frozen=True, slots=True)
class _Held:
    """手上已有的技能：ID、名稱、設計鍵（都不能進候選）。"""

    ids: frozenset[str]
    names: frozenset[str]
    keys: frozenset[DesignKey]

    @classmethod
    def of(cls, player: PickPlayer | None) -> _Held:
        skills = () if player is None else player.held_skills
        return cls(
            frozenset(s.id for s in skills),
            frozenset(s.name_zh for s in skills),
            frozenset(design_key(s) for s in skills),
        )

    def has(self, skill: SkillDef, key: DesignKey) -> bool:
        return skill.id in self.ids or skill.name_zh in self.names or key in self.keys


@dataclass(slots=True)
class _Composer:
    """組合器抽樣（候選池與同元素補抽共用）。"""

    library: ContentLibrary
    request: ProposalRequest
    ctx: ProposalContext
    kind: str
    skeleton: str | None
    keyword: str | None
    legal: int = 0

    def draw(self, rng: Rng, limit: int) -> Iterator[tuple[int, SkillDef | None]]:
        """抽 ``limit`` 個種子；每個種子回傳（種子, 合法且符合題目的技能或 ``None``）。"""
        for _ in range(limit):
            composer_seed = rng.next_u32()
            yield composer_seed, self._one(composer_seed)

    def _one(self, composer_seed: int) -> SkillDef | None:
        try:
            skill = compose_random_skill(
                composer_seed,
                tier=self.ctx.tier,
                rarity=self.ctx.rarity,
                skeleton=self.skeleton,
                library=self.library,
                keyword=self.keyword,
                hero_attributes=self.ctx.hero_attributes,
                kinds=(self.kind,),
            )
        except ComposeError:
            return None
        if not fits_request(skill, self.request, self.kind, self.library):
            return None
        if not _usable(skill, self.ctx) or validate_skill(skill, self.library):
            return None
        self.legal += 1
        return skill


def _player_elements(player: PickPlayer | None) -> frozenset[Element]:
    if player is None:
        return frozenset()
    return frozenset(e for s in player.held_skills for e in skill_elements(s))


def candidate_pool(
    library: ContentLibrary,
    request: ProposalRequest,
    ctx: ProposalContext,
    *,
    seed: int,
    rules: SkillPickRules | None = None,
    player: PickPlayer | None = None,
) -> CandidatePool:
    """組合器多種子抽樣（＋同元素補抽、＋手寫技能），依設計去重，排除手上已有的技能（見模組說明
    第 1 點）。"""
    rules = rules if rules is not None else library.skill_pick
    kind = wanted_kind(library, request)
    held = _Held.of(player)
    composer = _Composer(
        library,
        request,
        ctx,
        kind,
        _composer_skeleton(library, request, kind),
        request.keywords[0] if request.keywords else None,
    )
    found: dict[DesignKey, PickCandidate] = {}

    def keep(skill: SkillDef, composer_seed: int) -> bool:
        key = design_key(skill)
        if key in found or held.has(skill, key):
            return False
        found[key] = PickCandidate(skill, "composer", composer_seed, key)
        return True

    tried = 0
    for composer_seed, skill in composer.draw(Rng(seed).fork(POOL_FORK), rules.pool.seeds):
        tried += 1
        if skill is not None:
            keep(skill, composer_seed)
        if len(found) >= rules.pool.designs:
            break
    extra = _element_draw(composer, rules=rules, player=player, found=found, keep=keep, seed=seed)
    if rules.pool.handwritten_max > 0:
        for skill in sorted(player_skills(library).values(), key=lambda s: s.id):
            if skill.tier != ctx.tier or skill.rarity != ctx.rarity:
                continue
            if not fits_request(skill, request, kind, library) or not _usable(skill, ctx):
                continue
            key = design_key(skill)
            if key not in found and not held.has(skill, key):
                found[key] = PickCandidate(skill, "pool", None, key)
    return CandidatePool(tuple(found.values()), tried + extra, composer.legal, extra)


def _element_draw(
    composer: _Composer,
    *,
    rules: SkillPickRules,
    player: PickPlayer | None,
    found: dict[DesignKey, PickCandidate],
    keep: Callable[[SkillDef, int], bool],
    seed: int,
) -> int:
    """PK-1b 同元素補抽：回傳用了幾個種子（不需要補抽時為 0）。"""
    wanted = _player_elements(player)
    if not wanted or rules.pool.element_seeds <= 0:
        return 0

    def matching() -> int:
        return sum(1 for c in found.values() if skill_elements(c.skill) & wanted)

    if matching() >= rules.pool.element_designs:
        return 0
    used = 0
    for composer_seed, skill in composer.draw(
        Rng(seed).fork(ELEMENT_FORK), rules.pool.element_seeds
    ):
        used += 1
        if skill is not None and skill_elements(skill) & wanted:
            keep(skill, composer_seed)
        if matching() >= rules.pool.element_designs:
            break
    return used


# ---------------------------------------------------------------------------
# 打分與排序
# ---------------------------------------------------------------------------


def _hollow(effect: object) -> bool:
    kind = getattr(effect, "type", None)
    if kind in _HOLLOW_TYPES:
        return True
    return kind == "apply_status" and getattr(effect, "status", None) in _HOLLOW_STATUSES


def thin_reasons(skill: SkillDef, *, epic_min_effects: int = 2) -> tuple[str, ...]:
    """PK-2「這招有沒有料」（只給挑選打分扣分，不是規則；不改組合器與驗證器的合法判定）：

    - :data:`THIN_HOLLOW`：技能（第一層效果）有作用的效果一個都沒有——只刻符文、只上「被標記」、
      只揭露（PK-1b 的 Q5、Q16、Q20）。
    - :data:`THIN_CONDITIONAL`：沒有傷害，而且每個有作用的效果都要條件成立才生效（技能層級的條件
      或效果自己的條件；PK-1b 的 Q8「推開 2 格，若居高臨下」）。
    - :data:`THIN_FEW`：史詩以上，有作用的效果少於 ``epic_min_effects`` 個（PK-1b 的 Q12 史詩被動
      只有標記 3 回合）。

    沒有效果的技能（修正型被動）不算。依上面的順序回傳。"""
    effects = skill.effects
    if not effects:
        return ()
    useful = [e for e in effects if not _hollow(e)]
    found: list[str] = []
    if not useful:
        found.append(THIN_HOLLOW)
    elif not any(e.type in _DAMAGE for e in useful) and all(
        skill.condition is not None or getattr(e, "condition", None) is not None for e in useful
    ):
        found.append(THIN_CONDITIONAL)
    if skill.rarity in _HIGH_RARITIES and len(useful) < epic_min_effects:
        found.append(THIN_FEW)
    return tuple(found)


def _damaging(node: object) -> bool:
    if isinstance(node, list | tuple):
        return any(_damaging(item) for item in node)
    if not isinstance(node, dict):
        return False
    if node.get("type") in _DAMAGING_TYPES:
        return True
    return any(_damaging(value) for key, value in sorted(node.items()) if key != "narrative")


def is_nondamage(skill: SkillDef) -> bool:
    """#142 的「非傷害」技能（輔助、治療、控制、位移、召喚、防守）：技能（含接續段、變奏、條件分支）
    任何地方都沒有會造成傷害的原語（:data:`_DAMAGING_TYPES`）。召喚物自己的攻擊不算技能的傷害。"""
    return not _damaging(skill.model_dump(mode="json", exclude={"narrative", "provenance"}))


def synergy_links(
    library: ContentLibrary, skill: SkillDef, player: PickPlayer
) -> list[tuple[SkillDef, str]]:
    """候選與手上技能的 makes／uses 連線（只看專屬規則）：每條是（手上的技能, 關鍵字），同一招
    同一個關鍵字兩個方向都接上算兩條。依手上技能 ID、推導表順序。"""
    mine = derive_keywords(skill, library.keywords, exclusive_only=True)
    links: list[tuple[SkillDef, str]] = []
    for held in sorted(player.held_skills, key=lambda s: s.id):
        theirs = derive_keywords(held, library.keywords, exclusive_only=True)
        links += [(held, k) for k in mine.makes if k in theirs.uses]
        links += [(held, k) for k in mine.uses if k in theirs.makes]
    return links


def element_partners(skill: SkillDef, player: PickPlayer) -> list[SkillDef]:
    """手上和候選同元素的技能（物理不算元素），依 ID。"""
    mine = skill_elements(skill)
    if not mine:
        return []
    return [s for s in sorted(player.held_skills, key=lambda s: s.id) if skill_elements(s) & mine]


def odd_conditions(skill: SkillDef) -> tuple[str, ...]:
    """PK-1b 怪條件（只給挑選打分扣分，不是規則；不改組合器與驗證器的合法判定）：

    - :data:`ODD_INSCRIBE`：刻紋（本身沒有效果、留給之後的技能讀取）要滿足條件才刻得下——刻紋
      效果自己帶條件；或技能層級有條件、而技能沒有任何傷害效果（整招只剩有條件的刻紋與附帶效果）。
    - :data:`ODD_FIRST_ROUND`：不是傷害、也不是刻紋的效果自己帶「第一輪」（例「狀態易傷，若
      第一輪」）；或技能層級是「第一輪」、技能沒有傷害也沒有刻紋。

    每一處算一個（依效果順序；技能層級的最後算，最多一個）。"""
    found: list[str] = []
    has_damage = any(e.type in _DAMAGE for e in skill.effects)
    has_inscribe = any(e.type == _INSCRIBE for e in skill.effects)
    for effect in skill.effects:
        own = getattr(effect, "condition", None)
        if own is None:
            continue
        if effect.type == _INSCRIBE:
            found.append(ODD_INSCRIBE)
        elif effect.type not in _DAMAGE and own.type == _FIRST_ROUND:
            found.append(ODD_FIRST_ROUND)
    top = skill.condition.type if skill.condition is not None else None
    if top is not None and not has_damage:
        if has_inscribe:
            found.append(ODD_INSCRIBE)
        elif top == _FIRST_ROUND:
            found.append(ODD_FIRST_ROUND)
    return tuple(found)


def score_candidate(
    library: ContentLibrary,
    candidate: PickCandidate,
    player: PickPlayer,
    weights: PickWeights,
    request: ProposalRequest | None = None,
    *,
    keywords: Sequence[str] | None = None,
) -> PickCandidate:
    """候選的基本分（不含多樣性）：協同＋關鍵字貼合＋主題相合＋元素相合＋打法＋屬性路線＋手寫技能
    加分 − 怪條件 − 單薄。``request`` 是題目（關鍵字貼合要看；省略＝不算這一項）；``keywords``
    （PK-2 三選一的格子）有給時取代題目的關鍵字。回傳帶分數的候選。"""
    skill = candidate.skill
    found = derive_keywords(skill, library.keywords, exclusive_only=True)
    synergy = min(len(synergy_links(library, skill, player)), weights.synergy_max_links)
    if keywords is not None:
        wanted = tuple(keywords)
    else:
        wanted = tuple(request.keywords) if request is not None else ()
    held_kw = {
        k
        for held in player.held_skills
        for k in derive_keywords(held, library.keywords, exclusive_only=True).all()
    }
    others = [k for k in found.all() if k not in wanted]
    keyword = (
        weights.keyword_make * sum(1 for k in wanted if k in found.makes)
        + weights.keyword_use * sum(1 for k in wanted if k in found.uses)
        - weights.keyword_extra_penalty * sum(1 for k in others if k not in held_kw)
    )
    theme = weights.theme_per_keyword * min(
        sum(1 for k in others if k in held_kw), weights.theme_max_keywords
    )
    element = weights.element_match * min(
        len(element_partners(skill, player)), weights.element_match_max
    ) + (weights.element_any if skill_elements(skill) else 0)
    by_keyword = behavior_weights(library, player.behavior)
    behavior = min(
        weights.behavior_cap, weights.behavior_per_point * sum(by_keyword[k] for k in found.all())
    )
    route = 0
    if player.hero_attributes:
        rank = route_rank(skill, top_attribute(player.hero_attributes), player.weapon_attrs)
        route = {ROUTE_MAIN: weights.route_main, ROUTE_DUAL: weights.route_dual}.get(rank, 0)
    parts = (
        ("synergy", synergy * weights.synergy_per_link),
        ("keyword", keyword),
        ("theme", theme),
        ("element", element),
        ("behavior", behavior),
        ("route", route),
        ("pool", weights.pool_bonus if candidate.source == "pool" else 0),
        ("odd", -weights.odd_condition_penalty * len(odd_conditions(skill))),
        (
            "thin",
            -weights.thin_penalty
            * len(thin_reasons(skill, epic_min_effects=weights.thin_epic_min_effects)),
        ),
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


def drop_thin(candidates: Sequence[PickCandidate], weights: PickWeights) -> list[PickCandidate]:
    """PK-3（06 6.7「候選怎麼篩」，使用者題 2「B 擠掉」）：單薄的候選（:func:`thin_reasons`）不進給
    LLM 的前幾名；全部都單薄時照原樣（照分數給，不留空）。只影響挑選，不改合法判定。"""
    full = [
        c
        for c in candidates
        if not thin_reasons(c.skill, epic_min_effects=weights.thin_epic_min_effects)
    ]
    return full or list(candidates)


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


def _limit_handwritten(scored: Sequence[PickCandidate], limit: int) -> list[PickCandidate]:
    """手寫技能只留分數最高的 ``limit`` 個（同分取候選池較前面的）；組合器的候選照原順序全留。"""
    pool = [c for c in scored if c.source == "pool"]
    keep = {id(c) for c in sorted(pool, key=lambda c: -c.score)[:limit]}
    return [c for c in scored if c.source != "pool" or id(c) in keep]


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
    pool = candidate_pool(library, request, ctx, seed=seed, rules=rules, player=who)
    scored = [score_candidate(library, c, who, rules.weights, request) for c in pool.candidates]
    scored = _limit_handwritten(scored, rules.pool.handwritten_max)
    ranked = rank_candidates(drop_thin(scored, rules.weights), rules.weights, rules.pool.top_k)
    return PickSlate(ranked, len(pool.candidates), pool.seeds_tried)
