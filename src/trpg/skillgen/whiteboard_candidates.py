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

**同路線找法**（BAL-19g，06 6.27.4）：與完整版相同，加深、橋接依序 ① 同關鍵字、跟主路線 → ② 同
關鍵字的雙屬性白板 → ③ 換關鍵字 → ④ 才放寬屬性（偏離）；手寫池的退回也照同樣的偏好。

**階級**：白板用角色目前階級的預算與形狀（``request.tier``，6.34.9）；手寫池的退回也只取該階級
以下的技能。創角的起始技能不走這裡（一律 1 階）。

**確定性**：亂數只來自 ``Rng(request.seed).fork(<種類>)`` 與其子串流；同樣的輸入必得同樣的候選。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.content.skills import SkillDef, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import (
    ROUTE_OFF,
    AttrWant,
    Candidate,
    CandidateKind,
    CandidateRequest,
    _ranked_held,
    _weighted_order,
    behavior_weights,
    region_first,
    route_rank,
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

_SPARE = 2
"""不符合偏好的等級（:meth:`_Maker.grade`）。"""


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
        """關鍵字 ``keyword`` 的白板；做不出來回傳 ``None``（呼叫端換關鍵字）。同一個關鍵字依序找
        主路線（①）、雙屬性（②），都沒有才回傳不符合偏好的備選（BAL-19g，06 6.27.4）。"""
        board_kind = pick_whiteboard_kind(self.library, rng.fork(f"kind/{keyword}"))
        made: list[tuple[SkillDef, Literal["pool", "composer"]]] = []
        if keyword in self.active_keywords:
            if keyword not in whiteboard_keywords(self.library, board_kind, self.request.tier):
                board_kind = "active"
            kinds = [board_kind] if board_kind == "active" else [board_kind, "active"]
            for board in kinds:
                skill = self._compose(rng, board, keyword, want)
                if skill is None:
                    continue
                made.append((skill, "composer"))
                if self.grade(skill, want) == 0:
                    break
        if not made or min(self.grade(m[0], want) for m in made) == _SPARE:
            pooled = self._from_pool(rng, keyword, want)
            if pooled is not None:
                made.append((pooled, "pool"))
        if not made:
            return None
        return min(made, key=lambda m: self.grade(m[0], want))  # 同等級取先找到的

    def make_kind(
        self, rng: Rng, keyword: str, want: AttrWant, board_kind: WhiteboardKind
    ) -> tuple[SkillDef, Literal["pool", "composer"]] | None:
        """指定種類（被動保底用，Phase 5B-4b）的白板：組合器有該種類的配方先用，沒有再找手寫池同種類
        的技能；都沒有回傳 ``None``。"""
        made: list[tuple[SkillDef, Literal["pool", "composer"]]] = []
        if keyword in whiteboard_keywords(self.library, board_kind, self.request.tier):
            skill = self._compose(rng, board_kind, keyword, want)
            if skill is not None:
                made.append((skill, "composer"))
        if not made or self.grade(made[0][0], want) == _SPARE:
            pooled = self._from_pool(rng, keyword, want, kind=board_kind)
            if pooled is not None:
                made.append((pooled, "pool"))
        if not made:
            return None
        return min(made, key=lambda m: self.grade(m[0], want))

    def _compose(self, rng: Rng, board_kind: str, keyword: str, want: AttrWant) -> SkillDef | None:
        """白板最多試 ``tries`` 個種子：優先取縮放屬性符合偏好的（加深與橋接＝主角最高屬性，新方向
        ＝不同的屬性；3H-3；BAL-19g：主路線優先，其次雙屬性），湊不到就放寬取第一張。"""
        found: list[SkillDef | None] = [None, None, None]
        for _ in range(max(1, self.tries)):
            skill = self._one(rng, board_kind, keyword, want)
            if skill is None:
                continue
            grade = self.grade(skill, want)
            if grade == 0:
                return skill
            if found[grade] is None:
                found[grade] = skill
        return found[1] if found[1] is not None else found[2]

    def liked(self, skill: SkillDef, want: AttrWant) -> bool:
        """縮放屬性符合偏好（沒有主角屬性時一律符合；``same`` 含雙屬性技能）。"""
        return self.grade(skill, want) < _SPARE

    def grade(self, skill: SkillDef, want: AttrWant) -> int:
        """0 ＝ 完全符合偏好、1 ＝ 雙屬性技能靠第二屬性跟上主路線（只在 ``same``，仍算符合）、
        2 ＝ 不符合（備選）。"""
        request = self.request
        if not request.hero_attributes:
            return 0
        rank = route_rank(skill, top_attribute(request.hero_attributes), request.weapon_attrs)
        if want == "other":
            return 0 if rank == ROUTE_OFF else _SPARE
        return rank

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

    def _from_pool(
        self, rng: Rng, keyword: str, want: AttrWant, *, kind: WhiteboardKind | None = None
    ) -> SkillDef | None:
        """手寫技能池的 1 階技能（階級與白板一致）：依偏好的等級（主路線、雙屬性、備選；BAL-19g）
        分組，取最好的一組；組內優先選符合白板定義的。"""
        request = self.request
        tier = request.tier
        options = [
            skill
            for skill in player_skills(self.library).values()
            if skill.tier <= tier
            and minimum_tier(skill, self.library) <= tier  # 最低角色階級（3W-9，6.34.9）
            and skill.rarity != "legendary"
            and skill.form_id is None
            and skill.kind in WHITEBOARD_KINDS
            and (kind is None or skill.kind == kind)
            and skill.id not in self.taken
            and skill.id not in request.exclude
            and keyword in derive_keywords(skill, self.library.keywords, exclusive_only=True).all()
            and weapon_problem(skill, request.weapon_class, request.held) is None
        ]
        if not options:
            return None
        best = min(self.grade(s, want) for s in options)
        options = [s for s in options if self.grade(s, want) == best]
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
    """加深、橋接、新方向白板（依序；張數照 ``request.mix``，預設各一張；找不到的略過），再照
    ``request.min_passive`` 補被動（Phase 5B-4b）。見模組說明。"""
    order = library.keywords.ids()
    unknown = sorted(set(request.keyword_counts) - set(order))
    if unknown:
        raise ValueError(f"未知的關鍵字：{', '.join(unknown)}")
    behavior = behavior_weights(library, request.behavior)
    held = _ranked_held(request.keyword_counts, order, behavior)
    unheld = [k for k in order if k not in held]
    maker = _Maker(library, request, tries)
    deepen_count, bridge_count, new_count = request.mix
    found: list[Candidate | None] = []

    deepened: tuple[str, ...] = ()
    if deepen_count:
        deepen = _deepen(maker, request, held, unheld, behavior)
        found.append(deepen)
        deepened = () if deepen is None else deepen.keywords

    taken_keywords = set(deepened)
    if bridge_count:
        bridge = _bridge(maker, request, held, unheld, behavior, deepened=deepened)
        found.append(bridge)
        taken_keywords |= set() if bridge is None else set(bridge.keywords)

    for index in range(new_count):
        new = _new_direction(
            library,
            request,
            maker,
            held=held,
            unheld=unheld,
            behavior=behavior,
            taken_keywords=taken_keywords,
            index=index,
        )
        found.append(new)
        taken_keywords |= set() if new is None else set(new.keywords)
    result = [c for c in found if c is not None]
    if request.min_passive:
        result = _ensure_passive(maker, result, held=held, unheld=unheld)
    return tuple(result)


def _deepen(
    maker: _Maker,
    request: CandidateRequest,
    held: Sequence[str],
    unheld: Sequence[str],
    behavior: Mapping[str, int],
) -> Candidate | None:
    rng = Rng(request.seed).fork("deepen")
    # BAL-17：持有的與還沒有的關鍵字合成一串，先換關鍵字找同路線的，都沒有才放寬屬性
    hit = _first(maker, rng, "deepen", [*held, *_weighted_order(rng, unheld, behavior)])
    if hit is None:
        return None
    return Candidate("deepen", (hit[0],), hit[1], hit[2], not held or hit[0] != held[0])


def _bridge(
    maker: _Maker,
    request: CandidateRequest,
    held: Sequence[str],
    unheld: Sequence[str],
    behavior: Mapping[str, int],
    *,
    deepened: tuple[str, ...],
) -> Candidate | None:
    rng = Rng(request.seed).fork("bridge")
    others = [k for k in held if k not in deepened]
    outward = [k for k in _weighted_order(rng, unheld, behavior) if k not in deepened]
    hit = _first(maker, rng, "bridge", [*others, *outward])
    if hit is None:
        return None
    return Candidate("bridge", (hit[0],), hit[1], hit[2], hit[0] not in others)


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
    index: int = 0,
) -> Candidate | None:
    """第 ``index`` 張新方向（0 起）。第 1 張同原本（通用池擲骰、``fork("new")``）；之後的
    （Phase 5B-4b 新手鏈 2 張新方向）用 ``fork("new/<index>")``、不擲通用池、避開用過的關鍵字。
    還沒有的關鍵字裡，區域關鍵字（``request.region_keywords``）排前面。"""
    if index == 0:
        general = _general_board(library, request, maker)
        if general is not None:
            return general
    rng = Rng(request.seed).fork("new" if index == 0 else f"new/{index}")
    order = region_first(_weighted_order(rng, unheld, behavior), request.region_keywords)
    fresh = [k for k in order if k not in taken_keywords]
    hit = _first(maker, rng, "new", fresh, want="other")
    if hit is not None:
        return Candidate("new", (hit[0],), hit[1], hit[2])
    # 每個關鍵字都有了（或還沒有的都做不出來）：退回持有最少的關鍵字
    least = list(reversed(held))
    if index:
        least = [k for k in least if k not in taken_keywords] or least
    hit = _first(maker, rng, "new", least, want="other")
    return None if hit is None else Candidate("new", (hit[0],), hit[1], hit[2], True)


def _passive_keywords(
    candidate: Candidate, held: Sequence[str], unheld: Sequence[str], used: set[str]
) -> list[str]:
    """把候選換成被動時要試的關鍵字：原本的關鍵字，再來是符合該候選定義（新方向＝還沒有的優先；
    加深、橋接＝持有的優先）、別的候選沒用到的。"""
    own = list(candidate.keywords)
    rest = [*unheld, *reversed(held)] if candidate.kind == "new" else [*held, *unheld]
    return [*own, *(k for k in rest if k not in used and k not in own)]


def _ensure_passive(
    maker: _Maker, found: list[Candidate], *, held: Sequence[str], unheld: Sequence[str]
) -> list[Candidate]:
    """被動保底（Phase 5B-4b，07 7.6 新手鏈「至少 1 招被動」）：被動不足 ``min_passive`` 張時，從
    最後一張往前換成同種類的被動白板（亂數 ``fork("passive/<索引>")``）；做不出來就保持原樣。"""
    need = maker.request.min_passive - sum(1 for c in found if c.skill.kind == "passive")
    result = list(found)
    for index in reversed(range(len(result))):
        if need <= 0:
            break
        candidate = result[index]
        if candidate.skill.kind == "passive":
            continue
        used = {k for i, c in enumerate(result) if i != index for k in c.keywords}
        want: AttrWant = "other" if candidate.kind == "new" else "same"
        rng = Rng(maker.request.seed).fork(f"passive/{index}")
        for keyword in _passive_keywords(candidate, held, unheld, used):
            made = maker.make_kind(rng, keyword, want, "passive")
            if made is None:
                continue
            maker.taken.add(made[0].id)
            if candidate.kind == "new":  # 6F-1：新方向換成還沒有的關鍵字仍是新方向，不算退回
                fallback = keyword in held
            else:
                fallback = candidate.fallback or keyword not in candidate.keywords
            result[index] = Candidate(candidate.kind, (keyword,), made[0], made[1], fallback)
            need -= 1
            break
    return result
