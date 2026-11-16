"""許願池「願望驅動」的候選與挑選（Phase PK-4；07 7.6「許願池：願望驅動」，#165 補，使用者：
「A（建議）」；06 6.7 挑選模式）。

1. **需求標籤**（:class:`~trpg.content.skill_pick.WishTags`）：關鍵字（內容庫的 16 個，最多
   2）、元素（最多 1）、效果類型（最多 2）、形狀（最多 1）、種類（最多 1），清單在
   ``skill_pick.yaml`` 的 ``wish_tags``。LLM 翻出來的標籤經 :func:`clean_wish_tags` 丟掉清單外的
   那一項、其餘照用；玩家從清單點選的、引擎收到的一律用 :func:`wish_tags_problem` 檢查。
2. **照標籤做候選**（:func:`wish_pool`）：用獨立亂數串流 ``Rng(seed).fork("pick.wish")`` 抽組合器
   種子，**關鍵字、種類是出題條件**（有關鍵字標籤時每張至少帶一個；有種類標籤時只收那一種；沒有
   種類標籤時每個種子照 06 6.34.1 的比例擲種類），湊到 ``pool.wish_candidates``（候選量）個不同
   設計就停（最多抽 :data:`WISH_SEED_PERMILLE` ‰ 的種子）；元素、效果類型、形狀的標籤一張都沒做到時
   用那個標籤的獨立串流補抽（:func:`_tag_draws`，只收做到它的）。玩家手上的技能、要排除的 ID、傳說、
   武器不合的不收。不到 3 個時用 ``pick.wish.relax`` 串流放寬（不看種類與關鍵字）補到 3 個。
3. **打分**：一般完整技能的分數（:func:`~trpg.skillgen.skill_pick.score_candidate`，關鍵字＝願望的
   關鍵字）＋ **願望相合**（``weights.wish_match`` × 命中的標籤數，:func:`tag_hits`）；單薄的先
   拿掉，依多樣性排好前 ``pool.wish_candidates`` 個。
4. **挑選**（:data:`WishPicker`，LLM 層實作）：一次挑 3 張不同的候選並命名、寫一句回應願望的話；
   只能挑排好的候選（這裡再比一次結構，不一樣就不收）。沒有挑選器或 LLM 失敗時依排序取前 3 名。
5. **做不到時照實寫**（:func:`wish_miss_zh`，由程式依標籤產生，不交 LLM）：「最接近你願望的一招：有
   {做到的}；{做不到的}這次做不到。」全部命中就沒有這行。

純函式、確定性：亂數只來自 ``Rng(request.seed)`` 的子串流；LLM 的回答由外層記錄（重播不呼叫）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal

from trpg.content.library import ContentLibrary
from trpg.content.skill_pick import WISH_TAG_GROUPS, WishEffectTag, WishTags
from trpg.content.skills import SkillDef, skill_elements, weapon_problem
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import (
    CandidateRequest,
    LlmTrace,
    composer_kinds,
    skill_has_keywords,
)
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.memo import by_id
from trpg.skillgen.pick_offer import SLOT_KEYWORD_TRIES, same_structure
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.random_composer import ComposeError, compose_with_stats
from trpg.skillgen.skill_pick import (
    DesignKey,
    PickCandidate,
    PickSlate,
    design_key,
    drop_thin,
    rank_candidates,
    score_candidate,
)

__all__ = [
    "WISH_CARDS",
    "WISH_FORK",
    "WISH_RELAX_FORK",
    "WISH_SEED_PERMILLE",
    "WishCard",
    "WishChosen",
    "WishPick",
    "WishPicker",
    "WishResult",
    "clean_wish_tags",
    "skill_tag_ids",
    "tag_hits",
    "tag_label",
    "tag_labels",
    "wish_cards",
    "wish_miss_zh",
    "wish_pool",
    "wish_tags_problem",
]

WISH_CARDS: Final = 3
"""許願給幾張（07 7.6「LLM 挑 3 張」）。"""
WISH_FORK: Final = "pick.wish"
"""照標籤抽候選的亂數串流（``Rng(seed).fork("pick.wish")``）。"""
WISH_RELAX_FORK: Final = "pick.wish.relax"
"""候選不到 3 個時放寬（不看種類與關鍵字）補抽的亂數串流。"""
WISH_SEED_PERMILLE: Final = 1500
"""最多抽 候選量 × 這個千分比 個種子（湊不到候選量就停在這裡；難做的關鍵字每個種子約 0.2 秒，
所以不抽太多，免得超過 10 秒）。"""
WISH_TAG_FORK: Final = "pick.wish.tag"
"""標籤補抽的亂數串流（``pick.wish.tag/<類>/<值>``；:func:`_tag_draws`）。"""
WISH_TAG_EXTRA: Final = 3
"""標籤補抽每個標籤最多補幾個設計。"""
_ACTIVE_FAMILY: tuple[str, ...] = ("active", "stance")
_KINDS: dict[str, tuple[str, ...]] = {
    "active": _ACTIVE_FAMILY,
    "passive": ("passive",),
    "reaction": ("reaction",),
}
_SKIPPED_KEYS = frozenset({"narrative", "provenance", "cost"})


# ---------------------------------------------------------------------------
# 標籤：檢查、清理、文字
# ---------------------------------------------------------------------------


def _allowed(library: ContentLibrary, group: str, menu: Sequence[str]) -> tuple[str, ...]:
    if group == "keywords":
        return tuple(menu)
    return tuple(i.id for i in library.skill_pick.wish_tags.items(group))


def wish_tags_problem(
    library: ContentLibrary, tags: WishTags, menu: Sequence[str], *, require_one: bool = False
) -> str | None:
    """標籤不合格的原因（繁體中文）；合格 ``None``。每一類：值在清單裡、不重複、不超過上限。
    ``require_one``（玩家從清單點選）＝至少要選一個。"""
    rules = library.skill_pick.wish_tags
    for group in WISH_TAG_GROUPS:
        values = tags.group(group)
        allowed = _allowed(library, group, menu)
        if len(set(values)) != len(values):
            return "標籤不能重複"
        if len(values) > rules.limit(group):
            return f"{_GROUP_ZH[group]}最多選 {rules.limit(group)} 個"
        unknown = [v for v in values if v not in allowed]
        if unknown:
            return f"沒有這個{_GROUP_ZH[group]}：{'、'.join(unknown)}"
    if require_one and tags.empty():
        return "至少要選一個標籤"
    return None


_GROUP_ZH: dict[str, str] = {
    "keywords": "關鍵字",
    "elements": "元素",
    "effects": "效果類型",
    "shapes": "形狀",
    "kinds": "種類",
}


def clean_wish_tags(
    library: ContentLibrary, raw: Mapping[str, object], menu: Sequence[str]
) -> tuple[WishTags, tuple[str, ...]]:
    """LLM 翻出來的標籤（已過 JSON 格式）：每一類只留清單裡的、不重複的值，超過上限的丟掉後面的
    （07 7.6「清單外或不合法的那一項丟掉，其餘照用」）。回傳標籤與丟掉的代碼
    （``wish.dropped.<類>``）。"""
    rules = library.skill_pick.wish_tags
    kept: dict[str, tuple[str, ...]] = {}
    codes: list[str] = []
    for group in WISH_TAG_GROUPS:
        values = raw.get(group, ())
        allowed = _allowed(library, group, menu)
        out: list[str] = []
        items = values if isinstance(values, list | tuple) else ()
        for value in items:
            if not isinstance(value, str) or value not in allowed or value in out:
                codes.append(f"wish.dropped.{group}")
                continue
            if len(out) >= rules.limit(group):
                codes.append(f"wish.dropped.{group}")
                continue
            out.append(value)
        kept[group] = tuple(out)
    return WishTags.model_validate(kept), tuple(codes)


def tag_label(library: ContentLibrary, group: str, value: str) -> str:
    """一個標籤的中文名（關鍵字用內容庫的名稱）。"""
    if group == "keywords":
        found = {k.id: k.name_zh for k in library.keywords.keywords}
        return found.get(value, value)
    names = {i.id: i.name_zh for i in library.skill_pick.wish_tags.items(group)}
    return names.get(value, value)


def tag_labels(library: ContentLibrary, tags: WishTags) -> tuple[str, ...]:
    """全部標籤的中文名（依類別順序）。"""
    return tuple(tag_label(library, g, v) for g in WISH_TAG_GROUPS for v in tags.group(g))


# ---------------------------------------------------------------------------
# 命中
# ---------------------------------------------------------------------------


def _walk(node: object, types: set[str], statuses: set[str]) -> None:
    if isinstance(node, list | tuple):
        for item in node:
            _walk(item, types, statuses)
        return
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if isinstance(kind, str):
        types.add(kind)
        status = node.get("status")
        if kind == "apply_status" and isinstance(status, str):
            statuses.add(status)
    for key, value in sorted(node.items()):
        if key not in _SKIPPED_KEYS:
            _walk(value, types, statuses)


def _effect_hit(library: ContentLibrary, tag: WishEffectTag, types: set[str], st: set[str]) -> bool:
    if types & set(tag.primitives) or st & set(tag.statuses):
        return True
    if not (tag.control_statuses or tag.beneficial_statuses):
        return False
    listed = {s for t in library.skill_pick.wish_tags.effects for s in t.statuses}
    defs = by_id(library.ruleset.statuses)
    for status in sorted(st - listed):
        found = defs.get(status)
        if found is None:
            continue
        if tag.control_statuses and found.control_group is not None:
            return True
        if tag.beneficial_statuses and found.polarity == "buff":
            return True
    return False


def _kind_of(skill: SkillDef) -> Literal["active", "passive", "reaction"]:
    if skill.kind in ("passive", "modifier"):
        return "passive"
    if skill.kind == "reaction":
        return "reaction"
    return "active"


def skill_tag_ids(library: ContentLibrary, skill: SkillDef) -> WishTags:
    """這招技能本身有的標籤（每一類全列，不受上限限制；給命中判定與測試）。"""
    rules = library.skill_pick.wish_tags
    types: set[str] = set()
    statuses: set[str] = set()
    _walk(skill.model_dump(mode="json", exclude=set(_SKIPPED_KEYS)), types, statuses)
    keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    elements = {e.value for e in skill_elements(skill)} or {"physical"}
    return WishTags.model_construct(
        keywords=tuple(keywords),
        elements=tuple(i.id for i in rules.elements if i.id in elements),
        effects=tuple(t.id for t in rules.effects if _effect_hit(library, t, types, statuses)),
        shapes=tuple(t.id for t in rules.shapes if skill.shape.type in t.shapes),
        kinds=(_kind_of(skill),),
    )


def tag_hits(
    library: ContentLibrary, skill: SkillDef, tags: WishTags
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """願望標籤裡，這招做到的與做不到的（中文名，依類別順序）。"""
    mine = skill_tag_ids(library, skill)
    hit: list[str] = []
    miss: list[str] = []
    for group in WISH_TAG_GROUPS:
        for value in tags.group(group):
            (hit if value in mine.group(group) else miss).append(tag_label(library, group, value))
    return tuple(hit), tuple(miss)


def wish_miss_zh(library: ContentLibrary, skill: SkillDef, tags: WishTags) -> str | None:
    """07 7.6 第 5 點：沒有命中全部標籤時卡上加的一行（程式產生）；全部命中或沒有標籤＝``None``。
    一個都沒命中時省略「有…；」。"""
    hit, miss = tag_hits(library, skill, tags)
    if not miss:
        return None
    lacking = "、".join(miss)
    if not hit:
        return f"最接近你願望的一招：{lacking}這次做不到。"
    return f"最接近你願望的一招：有{'、'.join(hit)}；{lacking}這次做不到。"


# ---------------------------------------------------------------------------
# 候選
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Filter:
    library: ContentLibrary
    request: CandidateRequest
    held_ids: frozenset[str]
    held_keys: frozenset[DesignKey]

    def ok(self, skill: SkillDef, tags: WishTags | None) -> bool:
        """硬條件：傳說、排除、手上已有、武器；``tags`` 有給時另看種類與關鍵字（至少一個）。"""
        request = self.request
        if skill.rarity == "legendary" or skill.id in request.exclude:
            return False
        if skill.id in self.held_ids or design_key(skill) in self.held_keys:
            return False
        if weapon_problem(skill, request.weapon_class, request.held) is not None:
            return False
        if tags is None:
            return True
        if tags.kinds and skill.kind not in _KINDS[tags.kinds[0]]:
            return False
        return not tags.keywords or any(
            skill_has_keywords(skill, (k,), self.library) for k in tags.keywords
        )


def _compose(
    library: ContentLibrary,
    request: CandidateRequest,
    seed: int,
    keyword: str | None,
    kinds: tuple[str, ...],
) -> SkillDef | None:
    try:
        return compose_with_stats(
            seed,
            tier=request.tier,
            category="spell" if request.weapon_class == "focus" else None,
            library=library,
            keyword=keyword,
            hero_attributes=request.hero_attributes or None,
            held=request.held or None,
            keyword_tries=SLOT_KEYWORD_TRIES,
            skip_legendary=True,
            kinds=kinds,
        ).skill
    except ComposeError:
        return None


def _draw(  # noqa: PLR0917 — 一次抽樣的參數
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags | None,
    fork: str,
    seeds: int,
    enough: int,
    found: dict[DesignKey, PickCandidate],
    need: Callable[[SkillDef], bool] | None = None,
) -> int:
    """抽到 ``found`` 湊滿 ``enough`` 個不同設計或抽滿 ``seeds`` 個種子；回傳抽了幾個種子。
    ``need``（標籤補抽）：另外要符合的條件。"""
    rng = Rng(request.seed).fork(fork)
    keywords = () if tags is None else tags.keywords
    tried = 0
    for turn in range(seeds):
        if len(found) >= enough:
            break
        seed = rng.next_u32()
        tried += 1
        if tags is not None and tags.kinds:
            kinds = _KINDS[tags.kinds[0]]
        else:
            kinds = composer_kinds(library, request.seed, f"wish/{fork}/{turn}")
        keyword = keywords[turn % len(keywords)] if keywords else None
        skill = _compose(library, request, seed, keyword, kinds)
        if skill is None or not check.ok(skill, tags) or (need is not None and not need(skill)):
            continue
        key = design_key(skill)
        if key not in found:
            found[key] = PickCandidate(skill, "composer", seed, key)
    return tried


def _tag_draws(  # noqa: PLR0917 — 一次補抽的參數
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
    enough: int,
) -> int:
    """標籤補抽：元素、效果類型、形狀（打分用的標籤）有哪一個是候選裡一張都沒做到的，就用那個標籤的
    獨立串流（``pick.wish.tag/<類>/<值>``）再抽最多 ``候選量 ÷ 2`` 個種子，只收做到它的（出題條件
    照舊），最多 :data:`WISH_TAG_EXTRA` 個。組合器做不出來就照實寫「做不到」。"""
    tried = 0
    for group in WISH_TAG_GROUPS[1:4]:
        for value in tags.group(group):
            single = WishTags.model_validate({group: (value,)})

            def hits(skill: SkillDef, single: WishTags = single) -> bool:
                return bool(tag_hits(library, skill, single)[0])

            if any(hits(c.skill) for c in found.values()):
                continue
            fork = f"{WISH_TAG_FORK}/{group}/{value}"
            target = len(found) + WISH_TAG_EXTRA
            tried += _draw(
                library, request, check, tags, fork, enough // 2, target, found, need=hits
            )
    return tried


def wish_pool(
    library: ContentLibrary, request: CandidateRequest, tags: WishTags, player: PickPlayer
) -> PickSlate:
    """模組說明第 2、3 點：照標籤做候選並排好（前 ``pool.wish_candidates`` 個）。"""
    pick = library.skill_pick
    enough = pick.pool.wish_candidates
    seeds = enough * WISH_SEED_PERMILLE // 1000
    check = _Filter(
        library,
        request,
        frozenset(s.id for s in player.held_skills),
        frozenset(design_key(s) for s in player.held_skills),
    )
    found: dict[DesignKey, PickCandidate] = {}
    tried = _draw(library, request, check, tags, WISH_FORK, seeds, enough, found)
    tried += _tag_draws(library, request, check, tags, found, enough)
    if len(found) < WISH_CARDS:  # 願望太窄：放寬補到 3 個（不看種類與關鍵字）
        tried += _draw(library, request, check, None, WISH_RELAX_FORK, seeds, WISH_CARDS, found)
    weight = pick.weights.wish_match
    scored = []
    for candidate in found.values():
        base = score_candidate(library, candidate, player, pick.weights, keywords=tags.keywords)
        wish = weight * len(tag_hits(library, candidate.skill, tags)[0])
        scored.append(replace(base, score=base.score + wish, parts=(*base.parts, ("wish", wish))))
    kept = drop_thin(scored, pick.weights)
    if len(kept) < WISH_CARDS:  # 不單薄的不到 3 張：照分數把單薄的補回來（06 6.7「不留空」）
        thin = sorted((c for c in scored if c not in kept), key=lambda c: -c.score)
        kept += thin[: WISH_CARDS - len(kept)]
    ranked = rank_candidates(kept, pick.weights, enough)
    return PickSlate(ranked, len(found), tried)


# ---------------------------------------------------------------------------
# 挑選
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WishPick:
    """交給挑選器的題目：排好的候選、標籤、階級、持有者手上武器的中文名、種子（Mock 命名用）。"""

    slate: PickSlate
    tags: WishTags
    tier: int
    seed: int
    weapon_zh: str | None = None


@dataclass(frozen=True, slots=True)
class WishCard:
    """挑選器挑的一張：``slate.ranked`` 的第幾個、命名後的技能、回應願望的一句（可沒有）、紀錄；
    ``llm`` 為假＝這張名稱是組合式（LLM 沒給合格的名稱）。"""

    position: int
    skill: SkillDef
    reply_zh: str | None
    trace: LlmTrace
    llm: bool


type WishPicker = Callable[[WishPick, PickPlayer], Sequence[WishCard]]
"""許願的挑選器（LLM 層實作，``trpg.llm.wish_pick``）：回傳最多 3 張；不夠的由這裡依排序補上。"""


@dataclass(frozen=True, slots=True)
class WishChosen:
    """給玩家的一張：技能、來源（``llm``＝LLM 挑選並命名；``top``＝依排序）、回應願望的一句、做不到
    時的那一行、這張帶的願望關鍵字、LLM 紀錄。"""

    skill: SkillDef
    pick: Literal["llm", "top"]
    reply_zh: str | None
    miss_zh: str | None
    keywords: tuple[str, ...]
    trace: LlmTrace | None = None


@dataclass(frozen=True, slots=True)
class WishResult:
    """:func:`wish_cards` 的結果：3 張與排好的候選（比較與測試用）。"""

    cards: tuple[WishChosen, ...]
    slate: PickSlate


def _keywords(library: ContentLibrary, skill: SkillDef, tags: WishTags) -> tuple[str, ...]:
    wanted = tuple(k for k in tags.keywords if skill_has_keywords(skill, (k,), library))
    if wanted:
        return wanted
    return tuple(derive_keywords(skill, library.keywords, exclusive_only=True).all())[:2]


def wish_cards(
    library: ContentLibrary,
    request: CandidateRequest,
    tags: WishTags,
    player: PickPlayer,
    *,
    picker: WishPicker | None = None,
) -> WishResult:
    """模組說明第 2～5 點：照標籤做候選、打分、請挑選器挑 3 張（沒有或失敗依排序補），每張附做不到時
    的那一行。"""
    slate = wish_pool(library, request, tags, player)
    ranked = slate.ranked
    answers: Sequence[WishCard] = ()
    if picker is not None and len(ranked) >= library.skill_pick.pool.min_for_llm:
        ask = WishPick(
            slate,
            tags,
            request.tier,
            Rng(request.seed).fork(f"{WISH_FORK}/llm").next_u32(),
            next(iter(request.held.values()), None) if request.held else None,
        )
        answers = picker(ask, player)
    used: set[int] = set()
    cards: list[WishChosen] = []
    for answer in answers[:WISH_CARDS]:
        position = answer.position
        if not 0 <= position < len(ranked) or position in used:
            continue
        if not same_structure(answer.skill, ranked[position].skill):
            continue
        used.add(position)
        skill = answer.skill
        cards.append(
            WishChosen(
                skill,
                "llm" if answer.llm else "top",
                answer.reply_zh,
                wish_miss_zh(library, skill, tags),
                _keywords(library, skill, tags),
                answer.trace,
            )
        )
    for position, candidate in enumerate(ranked):
        if len(cards) >= WISH_CARDS:
            break
        if position in used:
            continue
        used.add(position)
        skill = candidate.skill
        cards.append(
            WishChosen(
                skill,
                "top",
                None,
                wish_miss_zh(library, skill, tags),
                _keywords(library, skill, tags),
            )
        )
    return WishResult(tuple(cards), slate)
