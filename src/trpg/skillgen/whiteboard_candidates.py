"""白板版的候選產生器：升級與任務三選一一律是白板（Phase 3W-4，``docs/design/06-技能.md`` 6.34.1）。

沿用 :mod:`trpg.skillgen.candidates` 的輸入（:class:`~trpg.skillgen.candidates.CandidateRequest`）與
輸出（:class:`~trpg.skillgen.candidates.Candidate`），仍是 加深／橋接／新方向 三個候選（6.27.4），
但每個候選都是一張 **白板**（單一效果、一個關鍵字）：

| 候選 | 白板的關鍵字 |
|---|---|
| ``deepen`` 加深 | 玩家持有最多的關鍵字 |
| ``bridge`` 橋接 | 玩家持有的另一個關鍵字；持有不到 2 個時向外取一個還沒有的 |
| ``new`` 新方向 | 玩家還沒有的關鍵字（行為相符的權重較高）；持有全部時退回持有最少的 |

**種類**：每個候選各自以 ``whiteboard.kind_permille``（主動 70／被動 20／反應 10，07 7.6）
擲骰決定白板的種類（獨立的 ``fork``，不消耗其他亂數）；該關鍵字沒有這個種類的配方時改出
主動白板。

**來源**：白板由組合器的單一效果模式（:func:`~trpg.skillgen.whiteboard.compose_whiteboard`，
``source == "composer"``）產生；關鍵字沒有任何白板配方時（召喚物、形態，以及單一效果湊不到
預算下限的倒地、撞擊、潮濕）退回手寫技能池的 1 階技能（``source == "pool"``，優先選符合
白板定義的）。**LLM 來源在白板模式下關閉**（LLM 整招提議保留給之後的完整技能三選一，
3W-7 另做「變化提議」）。

**階級**：白板用角色目前階級的預算與形狀（``request.tier``，6.34.9）；手寫池的退回也只取該階級
以下的技能。創角的起始技能不走這裡（一律 1 階）。

**確定性**：亂數只來自 ``Rng(request.seed).fork(<種類>)`` 與其子串流；同樣的輸入必得同樣的候選。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import (
    AttrWant,
    Candidate,
    CandidateKind,
    CandidateRequest,
    _ranked_held,
    _weighted_order,
    behavior_weights,
    follows_attr,
)
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import ComposeError
from trpg.skillgen.validate import minimum_tier
from trpg.skillgen.whiteboard import (
    WHITEBOARD_KINDS,
    WhiteboardKind,
    compose_whiteboard,
    is_whiteboard,
    whiteboard_keywords,
)

__all__ = ["generate_whiteboard_candidates", "pick_whiteboard_kind"]


def pick_whiteboard_kind(library: ContentLibrary, rng: Rng) -> WhiteboardKind:
    """依 ``whiteboard.kind_permille`` 擲骰決定白板的種類（主動、被動、反應；依固定順序累計）。"""
    permille = library.composer.whiteboard.kind_permille
    roll = rng.randint(1, sum(permille.values()))
    for kind in WHITEBOARD_KINDS:
        roll -= permille[kind]
        if roll <= 0:
            return kind
    return "active"  # pragma: no cover - roll 一定在 [1, 總和]


class _Maker:
    """替一個關鍵字做出白板（或退回手寫池的 1 階技能）；記住這次產生已經用掉的技能 ID。"""

    def __init__(self, library: ContentLibrary, request: CandidateRequest, tries: int) -> None:
        self.library = library
        self.request = request
        self.tries = tries
        self.taken: set[str] = set()
        self.active_keywords = whiteboard_keywords(library, "active", request.tier)

    def make(
        self, rng: Rng, kind: CandidateKind, keyword: str, want: AttrWant
    ) -> tuple[SkillDef, Literal["pool", "composer"]] | None:
        """關鍵字 ``keyword`` 的白板；做不出來回傳 ``None``（呼叫端換關鍵字）。"""
        board_kind = pick_whiteboard_kind(self.library, rng.fork(f"kind/{keyword}"))
        if keyword in self.active_keywords:
            if keyword not in whiteboard_keywords(self.library, board_kind, self.request.tier):
                board_kind = "active"
            made = self._compose(rng, board_kind, keyword, want)
            if made is not None:
                return made, "composer"
            if board_kind != "active":
                made = self._compose(rng, "active", keyword, want)
                if made is not None:
                    return made, "composer"
        pooled = self._from_pool(rng, keyword)
        return None if pooled is None else (pooled, "pool")

    def _compose(self, rng: Rng, board_kind: str, keyword: str, want: AttrWant) -> SkillDef | None:
        """白板最多試 ``tries`` 個種子：優先取縮放屬性符合偏好的（加深與橋接＝主角最高屬性，新方向
        ＝不同的屬性；3H-3），湊不到就放寬取第一張。"""
        spare: SkillDef | None = None
        for _ in range(max(1, self.tries)):
            skill = self._one(rng, board_kind, keyword, want)
            if skill is None:
                continue
            if self.liked(skill, want):
                return skill
            spare = spare if spare is not None else skill
        return spare

    def liked(self, skill: SkillDef, want: AttrWant) -> bool:
        """縮放屬性符合偏好（沒有主角屬性時一律符合）。"""
        request = self.request
        if not request.hero_attributes:
            return True
        top = top_attribute(request.hero_attributes)
        return follows_attr(skill, top, request.weapon_attrs) == (want == "same")

    def _one(self, rng: Rng, board_kind: str, keyword: str, want: AttrWant) -> SkillDef | None:
        request = self.request
        attrs = request.hero_attributes or None
        avoid = top_attribute(request.hero_attributes) if want == "other" and attrs else None
        try:
            skill = compose_whiteboard(
                rng.next_u32(),
                kind=board_kind,
                keyword=keyword,
                weapon_class=request.weapon_class,
                tier=request.tier,
                library=self.library,
                hero_attributes=attrs,
                avoid_attr=avoid,
                held=request.held or None,
            )
        except ComposeError:
            return None
        if skill.id in self.taken or skill.id in request.exclude:
            return None
        return skill

    def _from_pool(self, rng: Rng, keyword: str) -> SkillDef | None:
        """手寫技能池的 1 階技能（優先選符合白板定義的；階級與白板一致）。"""
        request = self.request
        tier = request.tier
        options = [
            skill
            for skill_id in sorted(self.library.skills)
            if (skill := self.library.skills[skill_id]).tier <= tier
            and minimum_tier(skill, self.library) <= tier  # 最低角色階級（3W-9，6.34.9）
            and skill.rarity != "legendary"
            and skill.form_id is None
            and skill.kind in WHITEBOARD_KINDS
            and skill.id not in self.taken
            and skill.id not in request.exclude
            and keyword in derive_keywords(skill, self.library.keywords, exclusive_only=True).all()
            and weapon_problem(skill, request.weapon_class, request.held) is None
        ]
        if not options:
            return None
        boards = [s for s in options if is_whiteboard(s, self.library, s.tier)]
        return rng.choice(boards or options)


def _first(
    maker: _Maker,
    rng: Rng,
    kind: CandidateKind,
    keywords: Sequence[str],
    *,
    want: AttrWant = "same",
) -> tuple[str, SkillDef, Literal["pool", "composer"]] | None:
    spare: tuple[str, SkillDef, Literal["pool", "composer"]] | None = None
    for keyword in keywords:
        made = maker.make(rng, kind, keyword, want)
        if made is None:
            continue
        if maker.liked(made[0], want):
            maker.taken.add(made[0].id)
            return keyword, made[0], made[1]
        spare = spare if spare is not None else (keyword, made[0], made[1])
    if spare is not None:  # 偏好的屬性湊不到：放寬，取第一個
        maker.taken.add(spare[1].id)
    return spare


def generate_whiteboard_candidates(
    library: ContentLibrary, request: CandidateRequest, tries: int = 8
) -> tuple[Candidate, ...]:
    """加深、橋接、新方向各一張白板（依序；找不到的種類略過）。見模組說明。"""
    order = library.keywords.ids()
    unknown = sorted(set(request.keyword_counts) - set(order))
    if unknown:
        raise ValueError(f"未知的關鍵字：{', '.join(unknown)}")
    behavior = behavior_weights(library, request.behavior)
    held = _ranked_held(request.keyword_counts, order, behavior)
    unheld = [k for k in order if k not in held]
    maker = _Maker(library, request, tries)
    found: list[Candidate | None] = []

    rng = Rng(request.seed).fork("deepen")
    hit = _first(maker, rng, "deepen", held) if held else None
    if hit is None:
        hit = _first(maker, rng, "deepen", _weighted_order(rng, unheld, behavior))
        found.append(None if hit is None else Candidate("deepen", (hit[0],), hit[1], hit[2], True))
    else:
        found.append(Candidate("deepen", (hit[0],), hit[1], hit[2], hit[0] != held[0]))
    deepened = () if found[0] is None else found[0].keywords

    rng = Rng(request.seed).fork("bridge")
    others = [k for k in held if k not in deepened]
    hit = _first(maker, rng, "bridge", others)
    outward = [k for k in _weighted_order(rng, unheld, behavior) if k not in deepened]
    if hit is not None:
        found.append(Candidate("bridge", (hit[0],), hit[1], hit[2]))
    else:
        hit = _first(maker, rng, "bridge", outward)
        found.append(None if hit is None else Candidate("bridge", (hit[0],), hit[1], hit[2], True))
    taken_keywords = set(deepened) | (set() if found[1] is None else set(found[1].keywords))

    found.append(
        _new_direction(
            library,
            request,
            maker,
            held=held,
            unheld=unheld,
            behavior=behavior,
            taken_keywords=taken_keywords,
        )
    )
    return tuple(c for c in found if c is not None)


def _general_board(
    library: ContentLibrary, request: CandidateRequest, maker: _Maker
) -> Candidate | None:
    """「新方向」有 ``general_share_permille`` 的機率出通用池白板（#55、6.34.1；沒有關鍵字的基礎
    白板，例：振奮、重擊）。擲骰用獨立的 ``fork("new_general")``，沒中時不影響其他候選的亂數。"""
    rng = Rng(request.seed).fork("new_general")
    if not rng.chance_permille(library.roguelite.candidates.general_share_permille):
        return None
    hit = _first(maker, rng, "new", [library.composer.whiteboard.generic_keyword], want="other")
    return None if hit is None else Candidate("new", (), hit[1], hit[2])


def _new_direction(
    library: ContentLibrary,
    request: CandidateRequest,
    maker: _Maker,
    *,
    held: Sequence[str],
    unheld: Sequence[str],
    behavior: Mapping[str, int],
    taken_keywords: set[str],
) -> Candidate | None:
    general = _general_board(library, request, maker)
    if general is not None:
        return general
    rng = Rng(request.seed).fork("new")
    fresh = [k for k in _weighted_order(rng, unheld, behavior) if k not in taken_keywords]
    hit = _first(maker, rng, "new", fresh, want="other")
    if hit is not None:
        return Candidate("new", (hit[0],), hit[1], hit[2])
    # 每個關鍵字都有了（或還沒有的都做不出來）：退回持有最少的關鍵字
    hit = _first(maker, rng, "new", list(reversed(held)), want="other")
    return None if hit is None else Candidate("new", (hit[0],), hit[1], hit[2], True)
