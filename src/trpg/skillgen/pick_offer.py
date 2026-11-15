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
   ``complete_slot_seeds``）個種子（湊到 ``pool.top_k`` 個不同設計就停），只收
   **完全符合這一格出題條件**的組合器技能（白板用
   :func:`~trpg.skillgen.whiteboard.compose_whiteboard`，所以白板規則照舊；完整技能用
   :func:`~trpg.skillgen.random_composer.compose_with_stats`）。依設計鍵去重；玩家手上
   已有的技能（同 ID、同設計）、這份三選一前面幾格已送出的設計、要排除的 ID 都不收。一張都
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
from trpg.content.skill_pick import PickWeights
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
    drop_thin,
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
LEVEL_EXACT = 0
"""放寬層級：全部關鍵字＋路線符合這一格（PK-2 的條件）。"""
LEVEL_RELAXED = 1
"""放寬層級：路線符合、只帶這一格的部分關鍵字（多關鍵字的格子，#110 ③ 放寬關鍵字）。"""
LEVEL_OFF = 2
"""放寬層級：全部關鍵字、但不符合這一格的路線（#110 ④ 最後才給、標偏離）。"""
LEVEL_OFF_RELAXED = 3
"""放寬層級：部分關鍵字＋不符合路線。"""
MAX_OFF_ROUTE = 2
"""一份三選一最多幾張偏離（06 6.27.4 #110「最多 2 張」；PK-3 起 LLM 挑了偏離的候選時檢查）。"""


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
    levels: dict[DesignKey, int] = field(default_factory=dict)
    """PK-3：每個候選設計的放寬層級（打分扣分用）。"""

    def follows(self, skill: SkillDef) -> bool:
        if self.top is None:
            return True
        return follows_attr(skill, self.top, self.request.weapon_attrs)

    def on_route(self, skill: SkillDef, original: Candidate) -> bool:
        """符合這一格的路線（#110）：加深、橋接要跟主路線（主屬性或雙屬性）；新方向照原本出題那一張
        （原本是不同屬性就要不同屬性，07 7.2；原本找不到不同屬性、跟了主路線，就照它），所以沒有 LLM
        時一份三選一的偏離張數不會比原本多。沒有主角屬性時都算符合。"""
        if self.top is None:
            return True
        if original.kind == "new":
            return self.follows(skill) == self.follows(original.skill)
        return self.follows(skill)

    def level(self, skill: SkillDef, original: Candidate) -> int | None:
        """這張技能在 ``original`` 那一格的放寬層級（PK-3，06 6.7「候選怎麼篩」，#110 的找法）：
        :data:`LEVEL_EXACT`（全部關鍵字＋路線符合）、:data:`LEVEL_RELAXED`（同路線、只帶這一格的部分
        關鍵字；只有多關鍵字的格子）、:data:`LEVEL_OFF`、:data:`LEVEL_OFF_RELAXED`（不符合路線）；
        硬條件不過（傳說、排除、已用、武器、種類、關鍵字完全不對）時 ``None``。種類照舊硬篩。"""
        request = self.request
        if skill.rarity == "legendary" or skill.id in request.exclude or skill.id in self.taken:
            return None
        if weapon_problem(skill, request.weapon_class, request.held) is not None:
            return None
        if _family(skill.kind, self.whiteboard) != _family(original.skill.kind, self.whiteboard):
            return None
        relaxed = self._relaxed(skill, original.keywords)
        if relaxed is None:
            return None
        if self.on_route(skill, original):
            return LEVEL_RELAXED if relaxed else LEVEL_EXACT
        return LEVEL_OFF_RELAXED if relaxed else LEVEL_OFF

    def _relaxed(self, skill: SkillDef, keywords: tuple[str, ...]) -> bool | None:
        """關鍵字：全部都有＝``False``；多關鍵字的格子只帶其中一部分＝``True``（#110 ③）；不符合
        ＝``None``。通用池那一格（#55，沒有關鍵字）照原本只收沒有任何關鍵字的技能。"""
        library = self.library
        if not keywords:
            found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
            return None if found else False
        if skill_has_keywords(skill, keywords, library):
            return False
        if len(keywords) >= _PAIR and any(
            skill_has_keywords(skill, (k,), library) for k in keywords
        ):
            return True
        return None

    def make(self, seed: int, original: Candidate, turn: int) -> SkillDef | None:
        """一個種子做一張符合這一格的技能；做不出來 ``None``。"""
        try:
            if self.whiteboard:
                return self._board(seed, original, turn)
            return self._complete(seed, original, turn)
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

    def _complete(self, seed: int, original: Candidate, turn: int) -> SkillDef | None:
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
            keyword=original.keywords[turn % len(original.keywords)],  # 雙關鍵字輪流指定
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
    """手上已有的技能：同 ID 或同設計鍵的不收。不比名稱（組合器的組合式名稱「火焰・打擊」之類常常
    同名，名稱由之後的命名步驟決定；同名的照 ``take_candidate`` 加「（二）」）。"""

    ids: frozenset[str]
    keys: frozenset[DesignKey]

    def has(self, skill: SkillDef, key: DesignKey) -> bool:
        return skill.id in self.ids or key in self.keys


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


def _slot_pool(
    maker: _Maker, index: int, original: Candidate, seeds: int, enough: int, *, relax_until: int
) -> list[PickCandidate]:
    """一格的候選：最多抽 ``seeds`` 個種子，全部關鍵字＋路線符合的湊到 ``enough``（``pool.top_k``）
    個不同設計就停。PK-3：這種候選不到 ``relax_until`` 個時，照 #110 的找法依序放寬（部分關鍵字 →
    偏離路線 → 兩者），每一層整層補上（最多 ``enough`` 個），湊到 ``relax_until`` 個就不再往下。"""
    levels: list[dict[DesignKey, PickCandidate]] = [{} for _ in range(LEVEL_OFF_RELAXED + 1)]

    def keep(skill: SkillDef, seed: int | None, level: int) -> None:
        key = design_key(skill)
        if any(key in found for found in levels):
            return
        if key in maker.sent or maker.held.has(skill, key):
            return
        levels[level][key] = PickCandidate(skill, "composer", seed, key)
        maker.levels[key] = level

    if original.source == "composer":
        first = maker.level(original.skill, original)
        keep(original.skill, None, LEVEL_EXACT if first is None else first)
    rng = Rng(maker.request.seed).fork(f"{SLOT_FORK}/{index}")
    for turn in range(seeds):
        if len(levels[LEVEL_EXACT]) >= enough:
            break
        seed = rng.next_u32()
        skill = maker.make(seed, original, turn)
        level = None if skill is None else maker.level(skill, original)
        if skill is not None and level is not None:
            keep(skill, seed, level)
    found = list(levels[LEVEL_EXACT].values())
    for level in range(LEVEL_RELAXED, LEVEL_OFF_RELAXED + 1):
        if level == LEVEL_OFF and not found:
            # 路線符合的一張都做不出來：原本那一張（手寫技能池的補位）若符合路線就留著排第一
            # （PK-2 同樣的退路），偏離的只當它後面的備選
            found = _fallback(maker, original, only_on_route=True)
        if len(found) >= relax_until:
            break
        found += list(levels[level].values())[: max(0, enough - len(found))]
    return found or _fallback(maker, original, only_on_route=False)


def _fallback(maker: _Maker, original: Candidate, *, only_on_route: bool) -> list[PickCandidate]:
    """原本那一張（手寫技能池的補位、或手上同設計的）當這一格的退路。"""
    if only_on_route and not maker.on_route(original.skill, original):
        return []
    key = design_key(original.skill)
    # 前面幾格已送出同一個設計、或和手上的技能同設計：這裡不放（最後的退路照留，同 PK-2）
    if only_on_route and (key in maker.sent or maker.held.has(original.skill, key)):
        return []
    maker.levels.setdefault(key, LEVEL_EXACT)
    source: Literal["pool", "composer"] = "pool" if original.source == "pool" else "composer"
    return [PickCandidate(original.skill, source, None, key)]


def _nondamage_slot(
    maker: _Maker,
    originals: Sequence[Candidate],
    pools: list[list[PickCandidate]],
    seeds: int,
    enough: int,
) -> int | None:
    """選非傷害保底格（見模組說明第 3 點）；選到的格子的候選只留非傷害的，不到 ``enough`` 個時
    用非傷害補抽補上（同一條串流）。做不到時 ``None``。"""
    order = list(reversed(range(len(originals))))  # 新方向 → 橋接 → 加深
    chosen = next(
        (i for i in order if is_nondamage(originals[i].skill) and _has_nondamage(pools[i])), None
    )
    if chosen is None:
        chosen = next((i for i in order if _has_nondamage(pools[i])), None)
    drawn = False
    if chosen is None:
        for i in order:
            extra = _nondamage_draw(maker, i, originals[i], pools[i], seeds=seeds, enough=enough)
            if extra:
                pools[i] = [*pools[i], *extra]
                chosen, drawn = i, True
                break
    if chosen is None:
        return None
    kept = [c for c in pools[chosen] if is_nondamage(c.skill)]
    if not drawn and len(kept) < enough:
        kept += _nondamage_draw(
            maker, chosen, originals[chosen], kept, seeds=seeds, enough=enough - len(kept)
        )
    pools[chosen] = kept
    return chosen


def _has_nondamage(pool: Sequence[PickCandidate]) -> bool:
    return any(is_nondamage(c.skill) for c in pool)


def _nondamage_draw(
    maker: _Maker,
    index: int,
    original: Candidate,
    pool: Sequence[PickCandidate],
    *,
    seeds: int,
    enough: int,
) -> list[PickCandidate]:
    have = {c.key for c in pool}
    found: dict[DesignKey, PickCandidate] = {}
    rng = Rng(maker.request.seed).fork(f"{NONDAMAGE_FORK}/{index}")
    for turn in range(seeds):
        if len(found) >= enough:
            break
        seed = rng.next_u32()
        skill = maker.make(seed, original, turn)
        if skill is None or not is_nondamage(skill):
            continue
        level = maker.level(skill, original)
        if level is None:
            continue
        key = design_key(skill)
        if key in have or key in found or key in maker.sent or maker.held.has(skill, key):
            continue
        found[key] = PickCandidate(skill, "composer", seed, key)
        maker.levels[key] = level
    # 同一層級的放寬順序：全部關鍵字＋路線符合的在前
    return sorted(found.values(), key=lambda c: maker.levels[c.key])


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
            frozenset(design_key(s) for s in held_skills),
        ),
    )
    pools: list[list[PickCandidate]] = []
    seeds = pick.pool.slot_seeds if whiteboard else pick.pool.complete_slot_seeds
    for index, original in enumerate(originals):
        pool = _slot_pool(
            maker, index, original, seeds, pick.pool.top_k, relax_until=pick.pool.relax_until
        )
        pools.append(pool)
        maker.sent.update(c.key for c in pool)
        maker.taken.update(c.skill.id for c in pool)
    chosen = _nondamage_slot(maker, originals, pools, pick.pool.nondamage_seeds, pick.pool.top_k)
    slots: list[PickedSlot] = []
    for index, (original, pool) in enumerate(zip(originals, pools, strict=True)):
        scored = [
            _relaxed(
                score_candidate(library, c, player, pick.weights, keywords=original.keywords),
                maker.levels.get(c.key, LEVEL_EXACT),
                pick.weights,
            )
            for c in pool
        ]
        ranked = _rank(scored, maker.levels, pick.weights, pick.pool.top_k)
        slate = PickSlate(ranked, len(pool), seeds)
        slots.append(PickedSlot(original, slate, nondamage=index == chosen))
    return slots


def _rank(
    scored: Sequence[PickCandidate],
    levels: Mapping[DesignKey, int],
    weights: PickWeights,
    top_k: int,
) -> tuple[PickCandidate, ...]:
    """單薄的先拿掉（全格都單薄才留，:func:`~trpg.skillgen.skill_pick.drop_thin`），再排序；**符合這一格
    路線的一律排在偏離的前面**（#110「最後才給不跟主路線的」：分數第一名只有在整格都偏離時才偏離，
    所以沒有 LLM 時的偏離張數不會比 PK-2 多）。"""
    kept = drop_thin(scored, weights)
    fit = [c for c in kept if levels.get(c.key, LEVEL_EXACT) < LEVEL_OFF]
    off = [c for c in kept if levels.get(c.key, LEVEL_EXACT) >= LEVEL_OFF]
    first = rank_candidates(fit, weights, top_k)
    return first + rank_candidates(off, weights, top_k - len(first))


def _relaxed(candidate: PickCandidate, level: int, weights: PickWeights) -> PickCandidate:
    """PK-3：放寬的候選扣分（``route_off``：不符合這一格的路線；``relaxed``：只帶部分關鍵字）。"""
    route = -weights.route_off_penalty if level in (LEVEL_OFF, LEVEL_OFF_RELAXED) else 0
    keyword = -weights.keyword_relaxed_penalty if level in (LEVEL_RELAXED, LEVEL_OFF_RELAXED) else 0
    if not route and not keyword:
        return candidate
    return replace(
        candidate,
        score=candidate.score + route + keyword,
        parts=(*candidate.parts, ("route_off", route), ("relaxed", keyword)),
    )


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
    只有候選至少 ``pool.min_for_llm`` 個的格子請 LLM；``rules.llm_max_calls``（大世界機遇＝1）有設時
    只有這些格子的前這麼多格請 LLM。回傳的
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
    # 只有候選夠多（``pool.min_for_llm``）的格子值得請 LLM；有上限時依格子順序取前幾個
    worth = [a for a in asks if len(a.slate.ranked) >= library.skill_pick.pool.min_for_llm]
    cap = rules.llm_max_calls
    allowed = worth if cap <= 0 else worth[:cap]
    answers: Sequence[SlotChoice | None] = (
        picker(allowed, player) if picker is not None and allowed else ()
    )
    by_slot = {ask.index: answer for ask, answer in zip(allowed, answers, strict=False)}
    found = [_result(slot, by_slot.get(i)) for i, slot in enumerate(slots)]
    return tuple(_cap_off_route(found, slots, request))


def _cap_off_route(
    found: list[Candidate], slots: Sequence[PickedSlot], request: CandidateRequest
) -> list[Candidate]:
    """PK-3：「跟主路線」改成扣分後，LLM 可能挑到偏離的候選；一份三選一的偏離超過
    :data:`MAX_OFF_ROUTE` 張（06 6.27.4 #110「最多 2 張」）時，從後面的格子起把「LLM 挑了偏離、而
    分數第一名不偏離」的格子改回第一名。"""
    if not request.hero_attributes:
        return found
    top = top_attribute(request.hero_attributes)

    def off(skill: SkillDef) -> bool:
        return not follows_attr(skill, top, request.weapon_attrs)

    for i in reversed(range(len(found))):
        if sum(off(c.skill) for c in found) <= MAX_OFF_ROUTE:
            break
        first = slots[i].slate.ranked[0]
        if found[i].pick == "llm" and off(found[i].skill) and not off(first.skill):
            trace = found[i].llm
            found[i] = replace(
                _result(slots[i], None),
                llm=None if trace is None else replace(trace, pick_reason="pick.off_route_cap"),
            )
    return found


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
