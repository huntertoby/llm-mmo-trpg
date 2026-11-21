"""許願池「願望驅動」的候選與挑選（Phase PK-4；07 7.6「許願池：願望驅動」，#165 補，使用者：
「A（建議）」；06 6.7 挑選模式）。

1. **需求標籤**（:class:`~trpg.content.skill_pick.WishTags`）：關鍵字（內容庫的 16 個，最多
   2）、元素（最多 1；角色到第二元素的階級起最多 2，WC-2，#167）、效果類型（最多 2）、形狀（最多
   1）、種類（最多 1），清單在
   ``skill_pick.yaml`` 的 ``wish_tags``。LLM 翻出來的標籤經 :func:`clean_wish_tags` 丟掉清單外的
   那一項、其餘照用；玩家從清單點選的、引擎收到的一律用 :func:`wish_tags_problem` 檢查。
2. **照標籤做候選**（:func:`wish_pool`）：用獨立亂數串流 ``Rng(seed).fork("pick.wish")`` 抽組合器
   種子，**關鍵字、種類是出題條件**（有關鍵字標籤時每張至少帶一個；有種類標籤時只收那一種；沒有
   種類標籤時每個種子照 06 6.34.1 的比例擲種類），湊到 ``pool.wish_candidates``（候選量）個不同
   設計就停（最多抽 ``pool.wish_seed_permille`` ‰ 的種子）；元素、效果類型、形狀的標籤一張都沒做到時
   用那個標籤的獨立串流補抽（:func:`_tag_draws`，只收做到它的）。願望有兩個元素時，帶其中一個元素的
   候選另外用 ``pick.wish.dual`` 串流加上另一個元素（:func:`_dual_draws`，
   :func:`~trpg.skillgen.composer_dual.add_second_element`）。WC-2 補配方（#167 第 5 題）：效果標籤
   有召喚時，補抽指定召喚骨架（:data:`SUMMON_HINT`）；關鍵字標籤是組合器不做的（形態）時，候選另外
   放進同關鍵字的手寫技能（:func:`handwritten_pool`，07 7.6 第 2 點「形態例外」）；有元素標籤時，
   沒帶到那個元素的候選另外換成那個元素（:func:`_element_draws`，
   :func:`~trpg.skillgen.composer_retheme.retheme`）。SK-5（玩法交接 4.1.34 第 10 點後補）：效果
   標籤同時有傷害和治療時，另外做吸血版本（:func:`_lifesteal_draws`，
   :func:`~trpg.skillgen.composer_lifesteal.add_lifesteal`）。玩家手上的技能、要排除的 ID、傳說、
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
from trpg.content.player_pool import player_skills
from trpg.content.skill_pick import WISH_TAG_GROUPS, WishEffectTag, WishTags
from trpg.content.skills import SkillDef, damage_elements, weapon_problem
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import (
    CandidateRequest,
    LlmTrace,
    composer_kinds,
    skill_has_keywords,
)
from trpg.skillgen.composer_dual import add_second_element, second_element_tier
from trpg.skillgen.composer_lifesteal import add_lifesteal, lifesteal_ready
from trpg.skillgen.composer_retheme import retheme
from trpg.skillgen.keywords import derive_keywords, pool_skills
from trpg.skillgen.memo import by_id
from trpg.skillgen.pick_offer import same_structure
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
from trpg.skillgen.validate import minimum_tier

__all__ = [
    "BORROW_WISH",
    "PHYSICAL",
    "SUMMON_HINT",
    "WISH_DUAL_FORK",
    "WISH_FORK",
    "WISH_LIFESTEAL_FORK",
    "WISH_RELAX_FORK",
    "WishCard",
    "WishChosen",
    "WishPick",
    "WishPicker",
    "WishResult",
    "borrow_pool",
    "clean_wish_tags",
    "dual_elements",
    "element_slots",
    "handwritten_keywords",
    "handwritten_pool",
    "menu_limits",
    "skill_tag_ids",
    "tag_hits",
    "tag_label",
    "tag_labels",
    "tag_limits",
    "wish_cards",
    "wish_miss_zh",
    "wish_pool",
    "wish_tags_problem",
]

WISH_FORK: Final = "pick.wish"
"""照標籤抽候選的亂數串流（``Rng(seed).fork("pick.wish")``）。"""
WISH_RELAX_FORK: Final = "pick.wish.relax"
"""候選不到 3 個時放寬（不看種類與關鍵字）補抽的亂數串流。"""
WISH_TAG_FORK: Final = "pick.wish.tag"
"""標籤補抽的亂數串流（``pick.wish.tag/<類>/<值>``；:func:`_tag_draws`）。"""
WISH_DUAL_FORK: Final = "pick.wish.dual"
"""雙元素（WC-2，#167）：帶其中一個元素的候選加上另一個元素的亂數串流（每個候選再 ``fork`` 它的
位置）；最多加 ``pool.wish_tag_extra`` 個設計。"""
WISH_LIFESTEAL_FORK: Final = "pick.wish.lifesteal"
"""吸血版本（SK-5）：重調強度的亂數（``…/have/<位置>``）與專門補抽的組合器種子（``…/draw``，每個
種子再 ``fork`` 它的序號）；最多加 ``pool.wish_tag_extra`` 個設計。"""
LIFESTEAL_TAGS: Final = ("damage", "heal")
"""效果標籤同時有這兩個才做吸血版本（SK-5；只許「治療」時不做，治療本來就由光環出）。"""
_ACTIVE_FAMILY: tuple[str, ...] = ("active", "stance")
_KINDS: dict[str, tuple[str, ...]] = {
    "active": _ACTIVE_FAMILY,
    "passive": ("passive",),
    "reaction": ("reaction",),
}
SUMMON_HINT: Final = "summon"
"""效果標籤「召喚」補抽時指定給組合器的骨架（WC-2，#167 第 5 題「組合器會抽召喚」）。"""
_DUAL = 2
"""雙元素（WC-2）：願望的兩個元素。"""
_SKIPPED_KEYS = frozenset({"narrative", "provenance", "cost"})


# ---------------------------------------------------------------------------
# 標籤：檢查、清理、文字
# ---------------------------------------------------------------------------


def _allowed(library: ContentLibrary, group: str, menu: Sequence[str]) -> tuple[str, ...]:
    if group == "keywords":
        return tuple(menu)
    return tuple(i.id for i in library.skill_pick.wish_tags.items(group))


def dual_elements(library: ContentLibrary, tier: int) -> bool:
    """角色階級 ``tier`` 已到第二元素的階級（願望的元素上限改用 ``max_elements_dual``；WC-2，#167，
    07 7.6 第 1 點「角色 2 階起最多 2 個」）。"""
    return tier >= second_element_tier(library)


PHYSICAL: Final = "physical"
"""物理（WC-2b，#167 補：另外一格，不佔元素名額，1 階起就能和元素一起選；07 7.6 第 1 點）。"""


def element_slots(values: Sequence[str]) -> int:
    """元素標籤佔幾個名額：物理不算（WC-2b）。"""
    return sum(1 for v in values if v != PHYSICAL)


def tag_limits(library: ContentLibrary, tier: int = 1) -> dict[str, int]:
    """角色階級 ``tier`` 時每一類最多選幾個（依類別順序）。元素是「物理以外」的上限，物理另外可以
    再選（:func:`element_slots`，WC-2b）。"""
    rules = library.skill_pick.wish_tags
    dual = dual_elements(library, tier)
    return {g: rules.limit(g, dual=dual) for g in WISH_TAG_GROUPS}


def menu_limits(library: ContentLibrary, tier: int = 1) -> dict[str, int]:
    """清單上每一類最多能點幾個（面板與 LLM schema 用）：:func:`tag_limits`，元素再加物理那一格
    （WC-2b：物理不佔元素名額；清單裡有物理時才加）。超過的由 :func:`wish_tags_problem` 與
    :func:`clean_wish_tags` 照名額擋。"""
    limits = tag_limits(library, tier)
    ids = {i.id for i in library.skill_pick.wish_tags.elements}
    if PHYSICAL in ids:
        limits["elements"] += 1
    return limits


def wish_tags_problem(
    library: ContentLibrary,
    tags: WishTags,
    menu: Sequence[str],
    *,
    tier: int = 1,
    require_one: bool = False,
) -> str | None:
    """標籤不合格的原因（繁體中文）；合格 ``None``。每一類：值在清單裡、不重複、不超過角色階級
    ``tier`` 的上限（:func:`tag_limits`；省略＝1 階）。``require_one``（玩家從清單點選）＝至少要選
    一個。"""
    limits = tag_limits(library, tier)
    for group in WISH_TAG_GROUPS:
        values = tags.group(group)
        allowed = _allowed(library, group, menu)
        if len(set(values)) != len(values):
            return "標籤不能重複"
        used = element_slots(values) if group == "elements" else len(values)
        if used > limits[group]:
            extra = "（物理另外算）" if group == "elements" else ""
            return f"{_GROUP_ZH[group]}最多選 {limits[group]} 個{extra}"
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
    library: ContentLibrary, raw: Mapping[str, object], menu: Sequence[str], *, tier: int = 1
) -> tuple[WishTags, tuple[str, ...]]:
    """LLM 翻出來的標籤（已過 JSON 格式）：每一類只留清單裡的、不重複的值，超過角色階級 ``tier``
    的上限（:func:`tag_limits`）的丟掉後面的（07 7.6「清單外或不合法的那一項丟掉，其餘照用」）。回傳
    標籤與丟掉的代碼（``wish.dropped.<類>``）。"""
    limits = tag_limits(library, tier)
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
            used = element_slots(out) if group == "elements" else len(out)
            physical = group == "elements" and value == PHYSICAL
            if not physical and used >= limits[group]:
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


def _walk(node: object, types: set[str], statuses: set[str], params: set[str]) -> None:
    """技能資料裡的原語、施加的狀態、效果上有值的參數名（給命中判定）。"""
    if isinstance(node, list | tuple):
        for item in node:
            _walk(item, types, statuses, params)
        return
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if isinstance(kind, str):
        types.add(kind)
        status = node.get("status")
        if kind == "apply_status" and isinstance(status, str):
            statuses.add(status)
        params.update(k for k, v in node.items() if v not in (None, False, 0, "", [], {}))
    for key, value in sorted(node.items()):
        if key not in _SKIPPED_KEYS:
            _walk(value, types, statuses, params)


def _effect_hit(
    library: ContentLibrary, tag: WishEffectTag, types: set[str], st: set[str], params: set[str]
) -> bool:
    if types & set(tag.primitives) or st & set(tag.statuses) or params & set(tag.params):
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


_SINGLE = "single"


def _shape_of(skill: SkillDef) -> str:
    """命中判定用的形狀：被動作用在「觸發的那個人」（形狀自身、``trigger.target`` 不是持有者）算
    單體（WC-2，#167；07 7.6 第 2 點「命中判定」）；其他照技能的形狀。"""
    trigger = skill.trigger
    passive = skill.kind == "passive" and skill.shape.type == "self"
    if passive and trigger is not None and trigger.target != "self":
        return _SINGLE
    return skill.shape.type


_DAMAGE_TYPES = ("damage", "delayed_damage")


def _physical_damage(skill: SkillDef) -> bool:
    """技能（含接續段）有一段沒有元素（或寫物理）的傷害（WC-2b）。"""
    follow = skill.followup.effects if skill.followup is not None else ()
    return any(
        e.type in _DAMAGE_TYPES and (e.element is None or e.element.value == PHYSICAL)
        for e in (*skill.effects, *follow)
    )


def skill_tag_ids(library: ContentLibrary, skill: SkillDef) -> WishTags:
    """這招技能本身有的標籤（每一類全列，不受上限限制；給命中判定與測試）。元素連第二元素一起算
    （:func:`~trpg.content.skills.damage_elements`，WC-2）；沒有元素＝物理。"""
    rules = library.skill_pick.wish_tags
    types: set[str] = set()
    statuses: set[str] = set()
    params: set[str] = set()
    _walk(skill.model_dump(mode="json", exclude=set(_SKIPPED_KEYS)), types, statuses, params)
    keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    elements = {e.value for e in damage_elements(skill)}
    if not elements or _physical_damage(skill):
        elements.add(PHYSICAL)  # WC-2b：一段物理（武器）傷害也算物理（「火焰劍」＝物理＋火焰）
    return WishTags.model_construct(
        keywords=tuple(keywords),
        elements=tuple(i.id for i in rules.elements if i.id in elements),
        effects=tuple(
            t.id for t in rules.effects if _effect_hit(library, t, types, statuses, params)
        ),
        shapes=tuple(t.id for t in rules.shapes if _shape_of(skill) in t.shapes),
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


def _compose(  # noqa: PLR0917 — 一次組合的參數（同 _draw）
    library: ContentLibrary,
    request: CandidateRequest,
    seed: int,
    keyword: str | None,
    kinds: tuple[str, ...],
    skeleton: str | None = None,
) -> SkillDef | None:
    if keyword is not None and keyword in handwritten_keywords(library):
        return None  # 組合器不做（形態）：候選由 :func:`_handwritten_draws` 放
    try:
        return compose_with_stats(
            seed,
            tier=request.tier,
            skeleton=skeleton,
            category="spell" if request.weapon_class == "focus" else None,
            library=library,
            keyword=keyword,
            hero_attributes=request.hero_attributes or None,
            held=request.held or None,
            keyword_tries=library.skill_pick.pool.slot_keyword_tries,
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
    skeleton: str | None = None,
) -> int:
    """抽到 ``found`` 湊滿 ``enough`` 個不同設計或抽滿 ``seeds`` 個種子；回傳抽了幾個種子。
    ``need``（標籤補抽）：另外要符合的條件；``skeleton``（WC-2 召喚）：指定給組合器的骨架（種類固定
    主動那一族）。"""
    rng = Rng(request.seed).fork(fork)
    keywords = () if tags is None else tags.keywords
    tried = 0
    for turn in range(seeds):
        if len(found) >= enough:
            break
        seed = rng.next_u32()
        tried += 1
        if skeleton is not None:
            kinds = _ACTIVE_FAMILY
        elif tags is not None and tags.kinds:
            kinds = _KINDS[tags.kinds[0]]
        else:
            kinds = composer_kinds(library, request.seed, f"wish/{fork}/{turn}")
        keyword = keywords[turn % len(keywords)] if keywords else None
        skill = _compose(library, request, seed, keyword, kinds, skeleton)
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
    照舊），最多 ``pool.wish_tag_extra`` 個。組合器做不出來就照實寫「做不到」。"""
    tried = 0
    for group in WISH_TAG_GROUPS[1:4]:
        for value in tags.group(group):
            single = WishTags.model_validate({group: (value,)})

            def hits(skill: SkillDef, single: WishTags = single) -> bool:
                return bool(tag_hits(library, skill, single)[0])

            if any(hits(c.skill) for c in found.values()):
                continue
            fork = f"{WISH_TAG_FORK}/{group}/{value}"
            target = len(found) + library.skill_pick.pool.wish_tag_extra
            hint = _summon_hint(group, value, tags)
            tried += _draw(
                library, request, check, tags, fork, enough // 2, target, found, hits, hint
            )
    return tried


def _summon_hint(group: str, value: str, tags: WishTags) -> str | None:
    """效果標籤「召喚」、種類可以是主動時，補抽指定召喚骨架（WC-2，#167 第 5 題）。"""
    if group != "effects" or value != SUMMON_HINT:
        return None
    return SUMMON_HINT if not tags.kinds or tags.kinds[0] == "active" else None


def handwritten_keywords(library: ContentLibrary) -> frozenset[str]:
    """組合器不做、候選從手寫技能放的關鍵字（``composable: false``；目前是形態，07 7.6 第 2 點
    「形態例外」，#167）。"""
    return frozenset(k.id for k in library.keywords.keywords if not k.composable)


def handwritten_pool(
    library: ContentLibrary, keyword: str, tier: int, kinds: Sequence[str] | None = None
) -> tuple[SkillDef, ...]:
    """``keyword`` 的手寫技能（專屬規則；依 ID）：不是傳說、角色階級 ``tier`` 用得到、種類在
    ``kinds`` 裡（``None``＝不限）。"""
    skills = pool_skills(library, keyword, starter_only=False, exclusive_only=True)
    return tuple(
        s
        for s in skills
        if s.rarity != "legendary"
        and (kinds is None or s.kind in kinds)
        and minimum_tier(s, library) <= tier
    )


def _handwritten_draws(
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
) -> None:
    """形態例外（WC-2，#167；07 7.6 第 2 點）：關鍵字標籤是組合器不做的，同關鍵字的手寫技能全部放進
    候選（出題條件照舊：種類、手上已有、武器）。"""
    kinds = _KINDS[tags.kinds[0]] if tags.kinds else None
    for keyword in tags.keywords:
        if keyword not in handwritten_keywords(library):
            continue
        for skill in handwritten_pool(library, keyword, request.tier, kinds):
            key = design_key(skill)
            if key not in found and check.ok(skill, tags):
                found[key] = PickCandidate(skill, "pool", None, key)


BORROW_WISH: Final = ("buff", "around")
"""預支技能（AP-2，06 6.3「許願池對到『增益』＋形狀『自身』時可以出現」）：效果標籤與形狀標籤。"""


def borrow_pool(library: ContentLibrary, tier: int) -> tuple[SkillDef, ...]:
    """手寫的預支技能（帶 ``borrow_ap``；依 ID）：不是傳說、角色階級 ``tier`` 用得到。組合器只由
    獨立串流做預支，許願另外把手寫的放進候選。"""
    return tuple(
        s
        for _, s in sorted(player_skills(library).items())
        if s.borrows_ap and s.rarity != "legendary" and minimum_tier(s, library) <= tier
    )


def _borrow_draws(
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
) -> None:
    """願望的效果標籤有「增益」、形狀標籤有「自身周圍」時，手寫的預支技能放進候選（出題條件照舊：
    種類、關鍵字、手上已有、武器）。其他願望不動（既有的許願結果不變）。"""
    effect, shape = BORROW_WISH
    if effect not in tags.effects or shape not in tags.shapes:
        return
    for skill in borrow_pool(library, request.tier):
        key = design_key(skill)
        if key not in found and check.ok(skill, tags):
            found[key] = PickCandidate(skill, "pool", None, key)


def _element_draws(
    library: ContentLibrary,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
) -> None:
    """元素配方（WC-2，#167 第 5 題）：每個願望元素（物理除外），沒帶到它的組合器候選依「命中其他
    標籤數」由多到少換成那個元素（:func:`~trpg.skillgen.composer_retheme.retheme`），最多加
    ``pool.wish_tag_extra`` 個新設計。"""
    for element in tags.elements:
        others = WishTags.model_validate({**tags.model_dump(), "elements": ()})
        lacking = [
            c
            for c in found.values()
            if element not in skill_tag_ids(library, c.skill).elements and c.source != "pool"
        ]
        lacking.sort(key=lambda c: -len(tag_hits(library, c.skill, others)[0]))
        added = 0
        for candidate in lacking:
            if added >= library.skill_pick.pool.wish_tag_extra:
                break
            skill = retheme(library, candidate.skill, element)
            if skill is None or not check.ok(skill, tags):
                continue
            key = design_key(skill)
            if key not in found:
                found[key] = PickCandidate(skill, candidate.source, candidate.seed, key)
                added += 1


def _dual_draws(
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
) -> None:
    """雙元素（WC-2，#167；模組說明第 2 點）：願望有兩個元素時，候選裡只差其中一個（不是物理）的，依
    發現順序加上那個元素（:func:`~trpg.skillgen.composer_dual.add_second_element`，串流
    ``pick.wish.dual/<位置>``），最多加 ``pool.wish_tag_extra`` 個新設計（不抽組合器種子）。兩個都不
    是物理時角色要到第二元素的階級；「物理＋元素」1 階起就做（WC-2b：物理不佔名額）。"""
    wanted = set(tags.elements)
    if len(wanted) < _DUAL:
        return
    if element_slots(tuple(wanted)) >= _DUAL and not dual_elements(library, request.tier):
        return
    rng = Rng(request.seed).fork(WISH_DUAL_FORK)
    added = 0
    for position, candidate in enumerate(list(found.values())):
        if added >= library.skill_pick.pool.wish_tag_extra:
            break
        missing = wanted - set(skill_tag_ids(library, candidate.skill).elements)
        if len(missing) != 1 or PHYSICAL in missing:
            continue
        (other,) = missing
        skill = add_second_element(library, candidate.skill, other, rng.fork(str(position)))
        if skill is None or not check.ok(skill, tags):
            continue
        key = design_key(skill)
        if key not in found:
            found[key] = PickCandidate(skill, candidate.source, candidate.seed, key)
            added += 1


def _add_lifesteal_versions(
    library: ContentLibrary,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
    sources: Sequence[PickCandidate],
    *,
    rng: Rng,
    room: int,
) -> int:
    """``sources`` 依序做吸血版本（亂數 ``rng.fork(<序號>)``），收進 ``found``，最多 ``room`` 個新
    設計；回傳加了幾個。"""
    added = 0
    for position, candidate in enumerate(sources):
        if added >= room:
            break
        skill = add_lifesteal(library, candidate.skill, rng.fork(str(position)))
        if skill is None or not check.ok(skill, tags):
            continue
        key = design_key(skill)
        if key not in found:
            found[key] = PickCandidate(skill, candidate.source, candidate.seed, key)
            added += 1
    return added


def _lifesteal_draws(  # noqa: PLR0917 — 一次補抽的參數（同 _tag_draws）
    library: ContentLibrary,
    request: CandidateRequest,
    check: _Filter,
    tags: WishTags,
    found: dict[DesignKey, PickCandidate],
    enough: int,
) -> int:
    """吸血配方（SK-5；07 7.6 第 2 點「照標籤專門做候選」）：效果標籤同時有傷害和治療、種類可以是
    主動時，

    1. 候選裡做得到吸血的組合器技能（打擊、範圍骨架的對敵傷害，:func:`lifesteal_ready`）依「命中
       其他標籤數」由多到少做吸血版本；
    2. 一個都沒做出來時，用 ``pick.wish.lifesteal/draw`` 串流專門補抽（骨架輪流指定
       ``structure.lifesteal_skeletons``，出題條件照舊）最多 ``候選量 ÷ 2`` 個種子，做吸血版本。

    兩步合計最多加 ``pool.wish_tag_extra`` 個新設計；回傳補抽了幾個種子。"""
    if not set(LIFESTEAL_TAGS) <= set(tags.effects) or (tags.kinds and tags.kinds[0] != "active"):
        return 0
    rng = Rng(request.seed).fork(WISH_LIFESTEAL_FORK)
    others = WishTags.model_validate({**tags.model_dump(), "effects": ()})
    ready = [c for c in found.values() if c.source != "pool" and lifesteal_ready(library, c.skill)]
    ready.sort(key=lambda c: -len(tag_hits(library, c.skill, others)[0]))
    added = _add_lifesteal_versions(
        library,
        check,
        tags,
        found,
        ready,
        rng=rng.fork("have"),
        room=library.skill_pick.pool.wish_tag_extra,
    )
    if added:
        return 0
    draw = rng.fork("draw")
    skeletons = library.composer.structure.lifesteal_skeletons
    keywords = tags.keywords
    tried = 0
    for turn in range(enough // 2):
        if added >= library.skill_pick.pool.wish_tag_extra:
            break
        seed = draw.next_u32()
        tried += 1
        keyword = keywords[turn % len(keywords)] if keywords else None
        skeleton = skeletons[turn % len(skeletons)]
        skill = _compose(library, request, seed, keyword, _ACTIVE_FAMILY, skeleton)
        if skill is None or not check.ok(skill, tags):
            continue
        source = PickCandidate(skill, "composer", seed, design_key(skill))
        added += _add_lifesteal_versions(
            library, check, tags, found, (source,), rng=draw.fork(str(turn)), room=1
        )
    return tried


def wish_pool(
    library: ContentLibrary, request: CandidateRequest, tags: WishTags, player: PickPlayer
) -> PickSlate:
    """模組說明第 2、3 點：照標籤做候選並排好（前 ``pool.wish_candidates`` 個）。"""
    pick = library.skill_pick
    enough = pick.pool.wish_candidates
    card_count = pick.pool.wish_cards
    seeds = enough * pick.pool.wish_seed_permille // 1000
    check = _Filter(
        library,
        request,
        frozenset(s.id for s in player.held_skills),
        frozenset(design_key(s) for s in player.held_skills),
    )
    found: dict[DesignKey, PickCandidate] = {}
    tried = _draw(library, request, check, tags, WISH_FORK, seeds, enough, found)
    _handwritten_draws(library, request, check, tags, found)
    _borrow_draws(library, request, check, tags, found)  # AP-2：增益＋自身時放進預支技能
    tried += _tag_draws(library, request, check, tags, found, enough)
    _element_draws(library, check, tags, found)
    _dual_draws(library, request, check, tags, found)
    tried += _lifesteal_draws(library, request, check, tags, found, enough)
    if len(found) < card_count:  # 願望太窄：放寬補到 3 個（不看種類與關鍵字）
        tried += _draw(library, request, check, None, WISH_RELAX_FORK, seeds, card_count, found)
    weight = pick.weights.wish_match
    scored = []
    for candidate in found.values():
        base = score_candidate(library, candidate, player, pick.weights, keywords=tags.keywords)
        wish = weight * len(tag_hits(library, candidate.skill, tags)[0])
        scored.append(replace(base, score=base.score + wish, parts=(*base.parts, ("wish", wish))))
    kept = drop_thin(scored, pick.weights)
    if len(kept) < card_count:  # 不單薄的不到 3 張：照分數把單薄的補回來（06 6.7「不留空」）
        thin = sorted((c for c in scored if c not in kept), key=lambda c: -c.score)
        kept += thin[: card_count - len(kept)]
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
    for answer in answers[: library.skill_pick.pool.wish_cards]:
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
        if len(cards) >= library.skill_pick.pool.wish_cards:
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
