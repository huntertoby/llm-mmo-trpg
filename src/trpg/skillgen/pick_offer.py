"""挑選模式接上三選一（Phase PK-2；06 6.7 #165，提案第 6 節第 2 題 A「每格各挑一」）。

原型的升級三選一（白板）與完整技能三選一（原型特殊時刻、大世界機遇）在開關
（``skill_pick.yaml`` 的 ``enabled``）打開時走這裡：

1. **出題（程式）**：照原本的產生器決定格子（白板
   :func:`~trpg.skillgen.whiteboard_candidates.generate_whiteboard_candidates`、完整技能
   :func:`~trpg.skillgen.candidates.generate_candidates`，不請 LLM），所以加深／
   橋接／新方向、新方向 10% 通用池（#55）、同路線找法與偏離（#110）、種類 70／20／10 都和原本一樣。
   每一格記下「出題條件」：關鍵字、種類（白板分主動／被動／反應；完整技能分主動
   〔含姿態〕／被動／反應）、跟不跟主路線（:func:`~trpg.skillgen.candidates.follows_attr`）。
2. **每格的候選（程式）**：原本那一張（組合器做的才算）＋用獨立亂數串流
   ``Rng(seed).fork("pick.slot/<格>")`` 另外抽 ``pool.slot_seeds``（完整技能
   ``complete_slot_seeds``）個種子，只收**完全符合這一格出題條件**的組合器技能（白板用
   :func:`~trpg.skillgen.whiteboard.compose_whiteboard`，所以白板規則照舊；完整技能用
   :func:`~trpg.skillgen.random_composer.compose_with_stats`）。依設計鍵去重；玩家手上
   已有的技能（同 ID、同名、同設計）、這份三選一前面幾格已送出的設計、要排除的 ID 都不收。一張都
   沒有時才留原本那一張（例：手寫技能池的補位）。所以不論 LLM 挑哪一張，格子的意義、種類比例、
   偏離張數都和原本一樣。
3. **非傷害保底（#142）**：選一格只放非傷害候選（:func:`~trpg.skillgen.skill_pick.is_nondamage`）：
   原本那張已是非傷害的格子優先，否則依新方向 → 橋接 → 加深找候選裡有非傷害的格子；都沒有時依
   同樣順序用 ``Rng(seed).fork("pick.nondamage/<格>")`` 補抽 ``pool.nondamage_seeds`` 個種子。仍沒有
   就做不到（極少；記在 :class:`PickedSlot`）。
4. **打分（程式）**：每格照 :func:`~trpg.skillgen.skill_pick.score_candidate`（關鍵字＝這一格的
   關鍵字）打分、:func:`~trpg.skillgen.skill_pick.rank_candidates` 取前 ``pool.top_k`` 個。
5. **挑選（LLM，可沒有）**：裝了挑選器（:data:`OfferPicker`，``trpg.llm.pick``）時每格交給它挑一個
   並命名；挑選器只能回傳排好的候選之一、只換名稱與敘事（這裡再比一次結構，不一樣就不收）。沒有
   挑選器、這格不請 LLM、或 LLM 失敗時用**分數第一名**。

純函式、確定性：亂數只來自 ``Rng(request.seed)`` 的子串流；LLM 的結果由外層記錄（重播不呼叫）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute
from trpg.skillgen.candidates import (
    Candidate,
    CandidateKind,
    CandidateRequest,
    CandidateRules,
    LlmTrace,
    follows_attr,
    generate_candidates,
    skill_has_keywords,
)
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.proposal.models import PROPOSAL_KINDS
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.random_composer import ComposeError, compose_with_stats
from trpg.skillgen.skill_pick import (
    DesignKey,
    PickCandidate,
    PickSlate,
    design_key,
    is_nondamage,
    rank_candidates,
    score_candidate,
)
from trpg.skillgen.whiteboard import compose_whiteboard
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates

__all__ = [
    "NONDAMAGE_FORK",
    "SLOT_FORK",
    "OfferPicker",
    "PickedSlot",
    "SlotChoice",
    "SlotPick",
    "generate_pick_candidates",
    "pick_slots",
    "same_structure",
]

SLOT_FORK = "pick.slot"
"""每一格另外抽的候選的亂數串流（``Rng(seed).fork("pick.slot/<格>")``）。"""
NONDAMAGE_FORK = "pick.nondamage"
"""非傷害保底補抽的亂數串流（``Rng(seed).fork("pick.nondamage/<格>")``）。"""

_ACTIVE_FAMILY: tuple[str, ...] = ("active", "stance")
_PAIR = 2
SLOT_KEYWORD_TRIES = 30
"""完整技能每一格另外抽的候選：每個種子指定關鍵字最多試幾個變體（原本的產生器是 300；這裡只是
多找幾張候選，做不出來就換下一個種子，省 CPU 時間）。"""
_TEXT_FIELDS = frozenset({"id", "name_zh", "narrative", "description_zh"})


@dataclass(frozen=True, slots=True)
class SlotPick:
    """一格的挑選題目（交給 :data:`OfferPicker`）：第幾格、格子種類、這格的關鍵字、排好的候選、
    給 prompt 的題目（階級、稀有度、種類、關鍵字、區域、武器大類）與這格的種子。"""

    index: int
    kind: CandidateKind
    keywords: tuple[str, ...]
    slate: PickSlate
    request: ProposalRequest
    seed: int
    weapon_zh: str | None = None
    """持有者手上武器的中文名（命名照它寫）。"""


@dataclass(frozen=True, slots=True)
class SlotChoice:
    """挑選器對一格的回答：收下 ``slate.ranked`` 的第幾個（``position``）、命名後的技能、紀錄；
    ``llm`` 為假＝LLM 失敗，照分數第一名（名稱用組合式）。"""

    position: int
    skill: SkillDef
    trace: LlmTrace
    llm: bool


type OfferPicker = Callable[[Sequence[SlotPick], PickPlayer], Sequence[SlotChoice | None]]
"""一份三選一的挑選器（LLM 層實作，經 ``trpg.roguelite.llm_hook`` 掛上）：依序回答每一格；
``None``＝這一格不請 LLM（例：候選太少、時間用完），照分數第一名。"""


@dataclass(frozen=True, slots=True)
class PickedSlot:
    """一格的出題結果（:func:`pick_slots`；測試與比較用）。"""

    original: Candidate
    slate: PickSlate
    nondamage: bool = False
    """這一格是非傷害保底格（只放非傷害候選）。"""


@dataclass(slots=True)
class _Maker:
    """依一格的出題條件做候選。"""

    library: ContentLibrary
    request: CandidateRequest
    whiteboard: bool
    held_keywords: tuple[str, ...]
    attrs: Mapping[Attribute, int] | None
    top: Attribute | None
    held: _Held
    taken: set[str] = field(default_factory=set)
    sent: set[DesignKey] = field(default_factory=set)
    """前面幾格已經送出的設計（這一格不再收）。"""

    def follows(self, skill: SkillDef) -> bool:
        if self.top is None:
            return True
        return follows_attr(skill, self.top, self.request.weapon_attrs)

    def fits(self, skill: SkillDef, original: Candidate) -> bool:
        """完全符合 ``original`` 那一格的出題條件，而且可以給。"""
        request = self.request
        if skill.rarity == "legendary" or skill.id in request.exclude or skill.id in self.taken:
            return False
        if weapon_problem(skill, request.weapon_class, request.held) is not None:
            return False
        if _family(skill.kind, self.whiteboard) != _family(original.skill.kind, self.whiteboard):
            return False
        if self.follows(skill) != self.follows(original.skill):
            return False
        if original.keywords:
            return skill_has_keywords(skill, original.keywords, self.library)
        # 通用池那一格（#55）：照原本，只收沒有任何關鍵字的技能
        return not derive_keywords(skill, self.library.keywords, exclusive_only=True).all()

    def make(self, seed: int, original: Candidate, turn: int) -> SkillDef | None:
        """一個種子做一張符合這一格的技能；做不出來 ``None``。"""
        try:
            if self.whiteboard:
                return self._board(seed, original, turn)
            return self._complete(seed, original)
        except ComposeError:
            return None

    def _avoid(self, original: Candidate) -> Attribute | None:
        return self.top if original.kind == "new" and self.attrs else None

    def _board(self, seed: int, original: Candidate, turn: int) -> SkillDef:
        library, request = self.library, self.request
        keywords = original.keywords
        board = _family(original.skill.kind, whiteboard=True)
        uses: str | None = None
        if len(keywords) >= _PAIR:  # #130 雙關鍵字橋接：只有主動；輪流試利用者白板與一般配方
            keyword = keywords[turn % 2]
            uses = keywords[1 - turn % 2] if (turn // 2) % 2 == 0 else None
        elif keywords:
            keyword = keywords[0]
        else:
            keyword = library.composer.whiteboard.generic_keyword
        return compose_whiteboard(
            seed,
            kind=board,
            keyword=keyword,
            weapon_class=request.weapon_class,
            tier=request.tier,
            library=library,
            hero_attributes=self.attrs,
            avoid_attr=self._avoid(original),
            held=request.held or None,
            uses=uses,
            exploit_uses=self.held_keywords if uses is None and board == "active" else (),
        )

    def _complete(self, seed: int, original: Candidate) -> SkillDef | None:
        if not original.keywords:  # 通用池（手寫的基礎技能）那一格：組合器不做沒有關鍵字的完整技能
            return None
        request = self.request
        kind = original.skill.kind
        kinds = _ACTIVE_FAMILY if kind in _ACTIVE_FAMILY else (kind,)
        found = compose_with_stats(
            seed,
            tier=request.tier,
            category="spell" if request.weapon_class == "focus" else None,
            library=self.library,
            keyword=original.keywords[0],
            hero_attributes=self.attrs,
            avoid_attr=self._avoid(original),
            held=request.held or None,
            keyword_tries=SLOT_KEYWORD_TRIES,
            skip_legendary=True,
            kinds=kinds,
        )
        return found.skill


@dataclass(frozen=True, slots=True)
class _Held:
    ids: frozenset[str]
    names: frozenset[str]
    keys: frozenset[DesignKey]

    def has(self, skill: SkillDef, key: DesignKey) -> bool:
        return skill.id in self.ids or skill.name_zh in self.names or key in self.keys


def _family(kind: str, whiteboard: bool) -> str:
    """出題條件的「種類」：白板分主動／被動（含修正）／反應；完整技能的主動含姿態。"""
    if kind in ("passive", "modifier"):
        return "passive"
    if kind == "reaction":
        return "reaction"
    if kind in _ACTIVE_FAMILY:
        return "active"
    return kind if not whiteboard else "active"


def _originals(
    library: ContentLibrary, request: CandidateRequest, rules: CandidateRules, whiteboard: bool
) -> tuple[Candidate, ...]:
    if whiteboard:
        return generate_whiteboard_candidates(library, request, rules.composer_tries)
    return generate_candidates(library, request, replace(rules, llm_share_permille=0), llm=None)


def _slot_pool(maker: _Maker, index: int, original: Candidate, seeds: int) -> list[PickCandidate]:
    found: dict[DesignKey, PickCandidate] = {}

    def keep(skill: SkillDef, seed: int | None, source: Literal["composer", "pool"]) -> None:
        key = design_key(skill)
        if key in found or key in maker.sent or maker.held.has(skill, key):
            return
        found[key] = PickCandidate(skill, source, seed, key)

    if original.source == "composer":
        keep(original.skill, None, "composer")
    rng = Rng(maker.request.seed).fork(f"{SLOT_FORK}/{index}")
    for turn in range(seeds):
        seed = rng.next_u32()
        skill = maker.make(seed, original, turn)
        if skill is not None and maker.fits(skill, original):
            keep(skill, seed, "composer")
    if not found:  # 這一格一張都做不出來：留原本那一張（手寫技能池的補位、或手上同設計的）
        found[design_key(original.skill)] = PickCandidate(
            original.skill,
            "pool" if original.source == "pool" else "composer",
            None,
            design_key(original.skill),
        )
    return list(found.values())


def _nondamage_slot(
    maker: _Maker,
    originals: Sequence[Candidate],
    pools: list[list[PickCandidate]],
    seeds: int,
) -> int | None:
    """選非傷害保底格（見模組說明第 3 點）；選到的格子的候選只留非傷害的。做不到時 ``None``。"""
    order = list(reversed(range(len(originals))))  # 新方向 → 橋接 → 加深
    chosen = next(
        (i for i in order if is_nondamage(originals[i].skill) and _has_nondamage(pools[i])), None
    )
    if chosen is None:
        chosen = next((i for i in order if _has_nondamage(pools[i])), None)
    if chosen is None:
        for i in order:
            extra = _nondamage_draw(maker, i, originals[i], pools[i], seeds)
            if extra:
                pools[i] = [*pools[i], *extra]
                chosen = i
                break
    if chosen is None:
        return None
    pools[chosen] = [c for c in pools[chosen] if is_nondamage(c.skill)]
    return chosen


def _has_nondamage(pool: Sequence[PickCandidate]) -> bool:
    return any(is_nondamage(c.skill) for c in pool)


def _nondamage_draw(
    maker: _Maker, index: int, original: Candidate, pool: Sequence[PickCandidate], seeds: int
) -> list[PickCandidate]:
    have = {c.key for c in pool}
    found: dict[DesignKey, PickCandidate] = {}
    rng = Rng(maker.request.seed).fork(f"{NONDAMAGE_FORK}/{index}")
    for turn in range(seeds):
        seed = rng.next_u32()
        skill = maker.make(seed, original, turn)
        if skill is None or not is_nondamage(skill) or not maker.fits(skill, original):
            continue
        key = design_key(skill)
        if key in have or key in found or key in maker.sent or maker.held.has(skill, key):
            continue
        found[key] = PickCandidate(skill, "composer", seed, key)
    return list(found.values())


def pick_slots(
    library: ContentLibrary,
    request: CandidateRequest,
    rules: CandidateRules,
    *,
    player: PickPlayer,
    whiteboard: bool,
) -> list[PickedSlot]:
    """模組說明第 1～4 點：每一格的原本那一張與排好的候選（還沒交給 LLM）。"""
    pick = library.skill_pick
    originals = _originals(library, request, rules, whiteboard)
    held_skills = player.held_skills
    maker = _Maker(
        library,
        request,
        whiteboard,
        tuple(sorted(k for k, n in request.keyword_counts.items() if n > 0)),
        request.hero_attributes or None,
        top_attribute(request.hero_attributes) if request.hero_attributes else None,
        _Held(
            frozenset(s.id for s in held_skills),
            frozenset(s.name_zh for s in held_skills),
            frozenset(design_key(s) for s in held_skills),
        ),
    )
    pools: list[list[PickCandidate]] = []
    seeds = pick.pool.slot_seeds if whiteboard else pick.pool.complete_slot_seeds
    for index, original in enumerate(originals):
        pool = _slot_pool(maker, index, original, seeds)
        pools.append(pool)
        maker.sent.update(c.key for c in pool)
        maker.taken.update(c.skill.id for c in pool)
    chosen = _nondamage_slot(maker, originals, pools, pick.pool.nondamage_seeds)
    slots: list[PickedSlot] = []
    for index, (original, pool) in enumerate(zip(originals, pools, strict=True)):
        scored = [
            score_candidate(library, c, player, pick.weights, keywords=original.keywords)
            for c in pool
        ]
        ranked = rank_candidates(scored, pick.weights, pick.pool.top_k)
        slate = PickSlate(ranked, len(pool), seeds)
        slots.append(PickedSlot(original, slate, nondamage=index == chosen))
    return slots


def same_structure(a: SkillDef, b: SkillDef) -> bool:
    """兩招只差名稱與敘事（LLM 不能改候選的結構與數值，守則 3）。"""
    return a.model_dump(mode="json", exclude=set(_TEXT_FIELDS)) == b.model_dump(
        mode="json", exclude=set(_TEXT_FIELDS)
    )


def _slot_request(
    request: CandidateRequest, slot: PickedSlot, region: str | None
) -> ProposalRequest:
    skill = slot.original.skill
    return ProposalRequest(
        tier=request.tier,
        rarity=skill.rarity,
        kind=skill.kind if skill.kind in PROPOSAL_KINDS else None,
        keywords=slot.original.keywords,
        weapon_class=request.weapon_class,
        region=region,
    )


def generate_pick_candidates(
    library: ContentLibrary,
    request: CandidateRequest,
    rules: CandidateRules,
    *,
    player: PickPlayer,
    whiteboard: bool,
    picker: OfferPicker | None = None,
) -> tuple[Candidate, ...]:
    """挑選模式的三選一（見模組說明）。``picker``＝LLM 挑選器（省略＝每格都用分數第一名）；
    ``rules.llm_max_calls``（大世界機遇＝1）有設時只有前這麼多格請 LLM。回傳的
    :class:`~trpg.skillgen.candidates.Candidate` 帶 ``pick``（``llm``＝LLM 挑選並命名；``top``＝
    分數第一名）。"""
    slots = pick_slots(library, request, rules, player=player, whiteboard=whiteboard)
    asks = [
        SlotPick(
            index=i,
            kind=slot.original.kind,
            keywords=slot.original.keywords,
            slate=slot.slate,
            request=_slot_request(request, slot, request.region),
            seed=Rng(request.seed).fork(f"{SLOT_FORK}/{i}/llm").next_u32(),
            weapon_zh=next(iter(request.held.values()), None) if request.held else None,
        )
        for i, slot in enumerate(slots)
    ]
    cap = rules.llm_max_calls
    allowed = asks if cap <= 0 else asks[:cap]
    answers: Sequence[SlotChoice | None] = (
        picker(allowed, player) if picker is not None and allowed else ()
    )
    out: list[Candidate] = []
    for index, slot in enumerate(slots):
        answer = answers[index] if index < len(answers) else None
        out.append(_result(slot, answer))
    return tuple(out)


def _result(slot: PickedSlot, answer: SlotChoice | None) -> Candidate:
    ranked = slot.slate.ranked
    original = slot.original
    top = ranked[0]
    source: Literal["pool", "composer"] = "pool" if top.source == "pool" else "composer"
    base = Candidate(original.kind, original.keywords, top.skill, source, original.fallback)
    if answer is None:
        return replace(base, pick="top")
    position = answer.position
    if not 0 <= position < len(ranked) or not same_structure(answer.skill, ranked[position].skill):
        trace = replace(answer.trace, ok=False, pick_reason="pick.structure_changed")
        return replace(base, pick="top", llm=trace)
    chosen = ranked[position]
    return replace(
        base,
        skill=answer.skill,
        source="pool" if chosen.source == "pool" else "composer",
        pick="llm" if answer.llm else "top",
        llm=answer.trace,
    )
