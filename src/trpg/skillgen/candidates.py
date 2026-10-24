"""共用候選產生器：加深、橋接、新方向（Phase 3-24b2，``docs/design/06-技能.md`` 6.27.4）。

所有技能來源（升級三選一〔測試原型〕、之後的任務、機遇、許願池）共用這個 **純函式**：

- 輸入（:class:`CandidateRequest`）：玩家持有技能的 **關鍵字分布**、目前 **武器大類**、**行為紀錄**
  （用過的動作類型與次數）、**種子**、候選技能的 **階級**、要排除的技能 ID。
- 輸出：最多三個 :class:`Candidate`，依序是

  | 種類 | 定義 |
  |---|---|
  | ``deepen`` 加深 | 帶玩家持有最多的關鍵字 |
  | ``bridge`` 橋接 | 同時帶玩家已持有的兩個關鍵字 |
  | ``new`` 新方向 | 帶玩家還沒有的關鍵字 |

- 來源：關鍵字技能池（內容庫的手寫技能，階級相符、非傳說、與武器相容）或隨機組合器（指定關鍵字）。
  每個候選以 ``composer_share_permille`` 決定先找哪個來源，找不到再換另一個。

**只看專屬規則**（PM 決定，3-24b1 待決 #2）：關鍵字分布與「技能帶某關鍵字」都以
``derive_keywords(..., exclusive_only=True)`` 判斷；通用規則只影響卡片顯示。

**通用池**（Phase 3-51，玩法決定 #55）：沒有任何關鍵字的手寫技能是基礎技能；「新方向」那一格有
``general_share_permille`` 的機率從通用池抽（候選的 ``keywords`` 為空）。

**退回**（定義做不到時，``Candidate.fallback`` 為真）：

- 持有 0 個關鍵字：加深與橋接都退回新方向（各自帶一個不同的、還沒有的關鍵字）。
- 持有 1 個關鍵字：橋接退回「持有的關鍵字 ＋ 一個還沒有的關鍵字」（向外橋接）；仍找不到就只帶持有的
  關鍵字。
- 加深找不到持有最多的關鍵字的技能時，依持有數往下找；新方向找不到時換另一個還沒有的關鍵字。
- 全部來源都找不到時少給（極少發生）。

**行為紀錄**：關鍵字的 ``actions``（``skill_keywords.yaml``，例如攀跳 → 高處）與玩家用過的動作次數
相乘當權重：加深在持有數並列時偏向行為相符的關鍵字；新方向抽關鍵字時，行為相符的權重較高。

**跟主屬性**（Phase 3H-3，07 7.2）：``CandidateRequest.hero_attributes`` 有值時，加深與橋接優先取
縮放屬性＝主角最高屬性的技能（技能池只看 ``scaling_attr``；隨機組合器的技能縮放屬性直接跟著最高
屬性，限在 ``skill_scaling.yaml`` 允許範圍內），**新方向保留給不同屬性**（組合器取允許範圍內次高
的）；偏好湊不到時放寬（取同來源的備選），所以候選數量不變。最高屬性同分依六屬性順序
（:func:`trpg.shared.types.top_attribute`）。

確定性：亂數只來自 ``Rng(request.seed).fork(<種類>)``；同樣的輸入必得同樣的候選。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import ComposeError, compose_random_skill

__all__ = [
    "CANDIDATE_KINDS",
    "Candidate",
    "CandidateKind",
    "CandidateRequest",
    "CandidateRules",
    "behavior_weights",
    "follows_attr",
    "generate_candidates",
    "keyword_distribution",
    "skill_has_keywords",
]

type AttrWant = Literal["same", "other"]
"""候選對縮放屬性的偏好（Phase 3H-3）：``same`` ＝ 主角最高的屬性（加深、橋接），``other`` ＝ 不同的
屬性（新方向）。"""

type CandidateKind = Literal["deepen", "bridge", "new"]
CANDIDATE_KINDS: tuple[CandidateKind, ...] = ("deepen", "bridge", "new")


@dataclass(frozen=True, slots=True)
class CandidateRules:
    """產生器的參數（roguelite 取自 ``roguelite.yaml`` 的 ``candidates``）。"""

    composer_share_permille: int = 500
    composer_tries: int = 8
    general_share_permille: int = 100
    """「新方向」那一格從通用池（基礎技能）抽的機率（‰；Phase 3-51，玩法決定 #55）。"""


@dataclass(frozen=True, slots=True)
class CandidateRequest:
    """產生器的輸入。``keyword_counts``：關鍵字 ID → 持有幾招帶該關鍵字的技能（見
    :func:`keyword_distribution`）；``behavior``：動作類型 → 用過的次数；``weapon_class``：
    ``melee``／``ranged``／``focus``。"""

    keyword_counts: Mapping[str, int]
    weapon_class: str
    seed: int
    tier: int
    behavior: Mapping[str, int] = field(default_factory=dict)
    exclude: frozenset[str] = frozenset()
    """不能出現的技能 ID（玩家已持有的）。"""
    hero_attributes: Mapping[Attribute, int] = field(default_factory=dict)
    """主角目前的六屬性（Phase 3H-3，07 7.2）。有值時：加深與橋接的候選優先取縮放屬性＝最高屬性的
    技能（同分依六屬性順序），新方向優先取不同屬性的技能；找不到再放寬。隨機組合器產生的技能
    縮放屬性直接跟著最高屬性（:func:`trpg.skillgen.scaling.retarget_scaling`）。空 ＝ 不看屬性
    （與 3H-3 之前完全相同）。"""
    weapon_attrs: tuple[Attribute, ...] = ()
    """主角手上武器的縮放屬性（含第二縮放屬性；Phase 3H-7）。武器技看手上武器（3H-6），所以比對
    屬性偏好時武器技用這個，不用技能自己的 ``scaling_attr``（只是顯示提示）；空 ＝ 退回技能的。"""


@dataclass(frozen=True, slots=True)
class Candidate:
    """一個候選：種類、它要帶的關鍵字、技能、來源；``fallback`` 表示定義做不到而退回。"""

    kind: CandidateKind
    keywords: tuple[str, ...]
    skill: SkillDef
    source: Literal["pool", "composer"]
    fallback: bool = False


def keyword_distribution(skills: Iterable[SkillDef], library: ContentLibrary) -> dict[str, int]:
    """持有技能的關鍵字分布（只看專屬規則；一招技能對每個關鍵字最多算 1）。依推導表順序，只列
    出現過的關鍵字。"""
    counts: Counter[str] = Counter()
    for skill in skills:
        counts.update(derive_keywords(skill, library.keywords, exclusive_only=True).all())
    return {k: counts[k] for k in library.keywords.ids() if counts[k] > 0}


def behavior_weights(library: ContentLibrary, behavior: Mapping[str, int]) -> dict[str, int]:
    """關鍵字 → 行為分數（玩家用過的、與該關鍵字相符的動作次數總和）。"""
    return {
        k.id: sum(behavior.get(action, 0) for action in k.actions)
        for k in library.keywords.keywords
    }


def follows_attr(skill: SkillDef, attr: Attribute, weapon_attrs: Sequence[Attribute] = ()) -> bool:
    """技能實際吃 ``attr``：武器技看手上武器的縮放屬性（``weapon_attrs``，含第二屬性；3H-6、
    3H-7），空時與法術技一樣看技能的 ``scaling_attr``。"""
    if skill.category == "weapon" and weapon_attrs:
        return attr in weapon_attrs or attr == skill.secondary_scaling_attr  # 3I-3：心智第二屬性
    return skill.scaling_attr == attr


def skill_has_keywords(skill: SkillDef, keywords: Sequence[str], library: ContentLibrary) -> bool:
    """技能（依專屬規則）同時製造或利用 ``keywords`` 的每一個。"""
    found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    return all(k in found for k in keywords)


# ---------------------------------------------------------------------------
# 來源
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Search:
    library: ContentLibrary
    request: CandidateRequest
    rules: CandidateRules
    pool: tuple[tuple[SkillDef, tuple[str, ...]], ...]
    """可用的手寫技能與它（專屬規則）帶的關鍵字。"""
    taken: set[str]

    def usable(self, skill: SkillDef) -> bool:
        return (
            skill.rarity != "legendary"  # 傳說技能不當候選（組合器的隨機結果也一樣）
            and skill.id not in self.taken
            and skill.id not in self.request.exclude
            and weapon_problem(skill, self.request.weapon_class) is None
        )

    def _want_ok(self, skill: SkillDef, want: AttrWant | None) -> bool:
        if want is None:
            return True
        top = top_attribute(self.request.hero_attributes)
        return follows_attr(skill, top, self.request.weapon_attrs) == (want == "same")

    def from_pool(
        self, rng: Rng, keywords: Sequence[str], want: AttrWant | None
    ) -> tuple[SkillDef | None, SkillDef | None]:
        """（符合屬性偏好的技能，偏好放寬後的備選）；沒有偏好時只有第一個。"""
        options = [
            s for s, found in self.pool if all(k in found for k in keywords) and self.usable(s)
        ]
        if not options:
            return None, None
        liked = [s for s in options if self._want_ok(s, want)]
        if liked:
            return rng.choice(liked), None
        return None, rng.choice(options)

    def from_composer(
        self, rng: Rng, keywords: Sequence[str], want: AttrWant | None
    ) -> tuple[SkillDef | None, SkillDef | None]:
        if not keywords:
            return None, None
        hint = "spell" if self.request.weapon_class == "focus" else None
        attrs = self.request.hero_attributes or None
        avoid = top_attribute(self.request.hero_attributes) if want == "other" else None
        spare: SkillDef | None = None
        for _ in range(self.rules.composer_tries):
            seed = rng.next_u32()
            try:
                skill = compose_random_skill(
                    seed,
                    tier=self.request.tier,
                    category=hint,
                    library=self.library,
                    keyword=keywords[0],
                    hero_attributes=attrs,
                    avoid_attr=avoid,
                )
            except ComposeError:
                continue
            if self.usable(skill) and skill_has_keywords(skill, keywords, self.library):
                if self._want_ok(skill, want):
                    return skill, None
                spare = spare if spare is not None else skill
        return None, spare

    def find(
        self, rng: Rng, keywords: Sequence[str], want: AttrWant | None = None
    ) -> tuple[SkillDef, Literal["pool", "composer"]] | None:
        want = want if self.request.hero_attributes else None
        composer_first = rng.chance_permille(self.rules.composer_share_permille)
        order: tuple[Literal["pool", "composer"], ...] = (
            ("composer", "pool") if composer_first else ("pool", "composer")
        )
        spares: list[tuple[SkillDef, Literal["pool", "composer"]]] = []
        for source in order:
            skill, spare = (
                self.from_composer(rng, keywords, want)
                if source == "composer"
                else self.from_pool(rng, keywords, want)
            )
            if skill is not None:
                self.taken.add(skill.id)
                return skill, source
            if spare is not None:
                spares.append((spare, source))
        if spares:  # 偏好的屬性湊不到：放寬，仍取第一個來源的備選
            self.taken.add(spares[0][0].id)
            return spares[0]
        return None


def _pool(library: ContentLibrary, tier: int) -> tuple[tuple[SkillDef, tuple[str, ...]], ...]:
    found: list[tuple[SkillDef, tuple[str, ...]]] = []
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if skill.tier != tier or skill.rarity == "legendary":
            continue
        keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        if keywords:
            found.append((skill, keywords))
    return tuple(found)


# ---------------------------------------------------------------------------
# 三種候選
# ---------------------------------------------------------------------------


def _ranked_held(
    counts: Mapping[str, int], order: Sequence[str], behavior: Mapping[str, int]
) -> list[str]:
    """持有的關鍵字，依持有數（多→少）、行為分數（高→低）、推導表順序排列。"""
    held = [k for k in order if counts.get(k, 0) > 0]
    return sorted(held, key=lambda k: (-counts[k], -behavior.get(k, 0), order.index(k)))


def _weighted_order(rng: Rng, keywords: Sequence[str], behavior: Mapping[str, int]) -> list[str]:
    """依權重（1 ＋ 行為分數）不放回抽出的順序（確定性）。"""
    remaining = list(keywords)
    result: list[str] = []
    while remaining:
        weights = [1 + behavior.get(k, 0) for k in remaining]
        roll = rng.randint(1, sum(weights))
        for keyword, weight in zip(remaining, weights, strict=True):
            roll -= weight
            if roll <= 0:
                result.append(keyword)
                remaining.remove(keyword)
                break
    return result


def _first(
    search: _Search, rng: Rng, options: Iterable[tuple[str, ...]], want: AttrWant | None = None
) -> tuple[tuple[str, ...], SkillDef, Literal["pool", "composer"]] | None:
    for keywords in options:
        found = search.find(rng, keywords, want)
        if found is not None:
            return keywords, found[0], found[1]
    return None


def _deepen(
    search: _Search, held: list[str], unheld: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("deepen")
    if held:
        hit = _first(search, rng, ((k,) for k in held), "same")
        if hit is not None:
            return Candidate("deepen", hit[0], hit[1], hit[2], fallback=hit[0][0] != held[0])
    hit = _first(search, rng, ((k,) for k in _weighted_order(rng, unheld, behavior)), "same")
    return None if hit is None else Candidate("deepen", hit[0], hit[1], hit[2], fallback=True)


def _bridge(
    search: _Search, held: list[str], unheld: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("bridge")
    pairs = [tuple(sorted(p, key=held.index)) for p in combinations(held, 2)]
    hit = _first(search, rng, rng.shuffled(pairs), "same")
    if hit is not None:
        return Candidate("bridge", hit[0], hit[1], hit[2])
    if held:
        outward = [(k, n) for k in held for n in _weighted_order(rng, unheld, behavior)]
        hit = _first(search, rng, [*outward, *((k,) for k in held)], "same")
    else:
        hit = _first(search, rng, ((k,) for k in _weighted_order(rng, unheld, behavior)), "same")
    return None if hit is None else Candidate("bridge", hit[0], hit[1], hit[2], fallback=True)


def _new(
    search: _Search, unheld: list[str], held: list[str], behavior: Mapping[str, int]
) -> Candidate | None:
    rng = Rng(search.request.seed).fork("new")
    hit = _first(search, rng, ((k,) for k in _weighted_order(rng, unheld, behavior)), "other")
    if hit is not None:
        return Candidate("new", hit[0], hit[1], hit[2])
    # 每個關鍵字都有了（或還沒有的都找不到技能）：退回持有最少的關鍵字
    hit = _first(search, rng, ((k,) for k in reversed(held)), "other")
    return None if hit is None else Candidate("new", hit[0], hit[1], hit[2], fallback=True)


def _general_pool(library: ContentLibrary, tier: int) -> tuple[SkillDef, ...]:
    """通用池：階級相符、非傳說、**沒有任何關鍵字**（含通用歸類）的手寫技能＝基礎技能（06 6.27.1，
    玩法 PM 2026-10-24 選 B：通用池與「基礎技能」同一個範圍）。"""
    found: list[SkillDef] = []
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if skill.tier != tier or skill.rarity == "legendary":
            continue
        if not derive_keywords(skill, library.keywords).all():
            found.append(skill)
    return tuple(found)


def _general(search: _Search) -> Candidate | None:
    """「新方向」有 ``general_share_permille`` 的機率從通用池抽（Phase 3-51，玩法決定 #55）。
    擲骰用獨立的 ``fork("new_general")``，沒中時不影響其他候選的亂數；池空時回傳 ``None``。"""
    rng = Rng(search.request.seed).fork("new_general")
    if not rng.chance_permille(search.rules.general_share_permille):
        return None
    options = [s for s in _general_pool(search.library, search.request.tier) if search.usable(s)]
    if not options:
        return None
    if search.request.hero_attributes:  # 新方向盡量取不同屬性；湊不到就放寬
        options = [s for s in options if search._want_ok(s, "other")] or options
    skill = rng.choice(options)
    search.taken.add(skill.id)
    return Candidate("new", (), skill, "pool")


def generate_candidates(
    library: ContentLibrary, request: CandidateRequest, rules: CandidateRules | None = None
) -> tuple[Candidate, ...]:
    """加深、橋接、新方向各一個候選（依序；找不到的種類略過）。見模組說明。"""
    rules = rules if rules is not None else CandidateRules()
    order = library.keywords.ids()
    unknown = sorted(set(request.keyword_counts) - set(order))
    if unknown:
        raise ValueError(f"未知的關鍵字：{', '.join(unknown)}")
    behavior = behavior_weights(library, request.behavior)
    held = _ranked_held(request.keyword_counts, order, behavior)
    search = _Search(library, request, rules, _pool(library, request.tier), set())
    found: list[Candidate | None] = []
    # 依「加深 → 橋接 → 新方向」的順序產生；退回到「還沒有的關鍵字」的候選用掉的關鍵字，不再給
    # 下一個候選（盡量讓三個候選不同），已被前一個候選用掉的技能也不會重複。
    unheld = [k for k in order if k not in held]
    deepen = _deepen(search, held, unheld, behavior)
    found.append(deepen)
    bridge = _bridge(search, held, _without(unheld, deepen), behavior)
    found.append(bridge)
    new = _general(search) or _new(
        search, _without(_without(unheld, deepen), bridge), held, behavior
    )
    found.append(new)
    return tuple(c for c in found if c is not None)


def _without(keywords: list[str], candidate: Candidate | None) -> list[str]:
    """退回到新方向的候選用掉的關鍵字，不再給下一個候選當「新方向」（盡量讓三個候選不同）。"""
    if candidate is None or not candidate.fallback:
        return keywords
    remaining = [k for k in keywords if k not in candidate.keywords]
    return remaining or keywords
