"""升級與重骰的技能候選，以及把候選裝上主角（Phase 3-5a；3-24b2 改用共用候選產生器）。

候選由 :func:`trpg.skillgen.candidates.generate_candidates` 產生（06 6.27.4）：**加深**（持有最多的
關鍵字）、**橋接**（同時帶兩個已持有的關鍵字）、**新方向**（還沒有的關鍵字），依序排列；每個候選的標示
存在 ``SkillOffer.tags``。產生器的輸入：主角目前技能的關鍵字分布（只看專屬規則）、武器大類、這一輪的
行為紀錄（``RunState.behavior``）、候選的階級（依主角等級，``offer_tier_by_level``）與種子。

種子是 ``Rng(一輪的種子).fork("offer/<n>").next_u32()``，``n`` 是 ``RunState.offers_made``（第幾組
候選），所以同一輪同一時點的候選固定。

新技能跟主屬性（Phase 3H-3）：候選產生器拿到主角目前的屬性，加深與橋接優先取縮放屬性＝最高屬性的
技能，新方向保留給不同屬性（見 ``trpg.skillgen.candidates``）。

``off_route``（偏離路線，0.2 C）仍照舊標示：候選的縮放屬性與主角目前最高屬性不同的索引（只是標示，
不再刻意湊一個）。``roguelite.yaml`` 的 ``offer_size``、``off_route_per_offer``、
``offer_max_attempts`` 從 3-24b2 起不再使用（保留欄位，見報告待決）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_slot_problems
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.names import unique_skill_name
from trpg.roguelite.state import OfferTag, RunState, SkillOffer
from trpg.shared.rng import Rng
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import (
    CandidateRequest,
    CandidateRules,
    generate_candidates,
    keyword_distribution,
)

__all__ = ["candidate_request", "equip_problems", "make_offer", "skill_defs", "take_candidate"]


def candidate_request(library: ContentLibrary, run: RunState) -> CandidateRequest:
    """第 ``run.offers_made`` 組候選的產生器輸入（見模組說明）。"""
    held = skill_defs(library, run, run.hero.skills)
    return CandidateRequest(
        keyword_counts=keyword_distribution(held, library),
        weapon_class=library.weapons[run.hero.weapon].weapon_class,
        seed=Rng(run.seed).fork(f"offer/{run.offers_made}").next_u32(),
        tier=library.roguelite.offer_tier(run.level),
        behavior=dict(run.behavior),
        hero_attributes=dict(run.hero.attributes),  # 新技能跟主屬性（Phase 3H-3）
        # 進化前的技能也排除（Phase 3-26b：進化後原技能不再出現在候選）
        exclude=frozenset(
            (*run.hero.skills, *run.bench, *(r.base_id for r in run.evolutions.values()))
        ),
    )


def make_offer(library: ContentLibrary, run: RunState, reason: str) -> SkillOffer:
    """第 ``run.offers_made`` 組候選（呼叫者負責把計數器加 1）。"""
    settings = library.roguelite.candidates
    request = candidate_request(library, run)
    found = generate_candidates(
        library,
        request,
        CandidateRules(
            composer_share_permille=settings.composer_share_permille,
            composer_tries=settings.composer_tries,
        ),
    )
    top = top_attribute(run.hero.attributes)
    candidates = tuple(c.skill for c in found)
    return SkillOffer(
        reason="level_up" if reason == "level_up" else "reroll",
        tier=request.tier,
        top_attribute=top,
        candidates=candidates,
        off_route=tuple(i for i, s in enumerate(candidates) if s.scaling_attr != top),
        tags=tuple(
            OfferTag(kind=c.kind, keywords=c.keywords, source=c.source, fallback=c.fallback)
            for c in found
        ),
    )


def skill_defs(
    library: ContentLibrary, run: RunState, skill_ids: Sequence[str], extra: Sequence[SkillDef] = ()
) -> list[SkillDef]:
    """技能 ID → 定義（內容庫、主角的生成技能、``extra`` 依序查）。"""
    known = {s.id: s for s in (*run.generated_skills, *extra)}
    return [library.skills[i] if i in library.skills else known[i] for i in skill_ids]


def equip_problems(library: ContentLibrary, defs: Sequence[SkillDef]) -> list[str]:
    """裝備的問題：欄位上限（主動 ≤ 6、被動含修正 ≤ 3、反應 ≤ 1、姿態 ≤ 1）與規則改變型傳說 ≤ 1。"""
    return skill_slot_problems(defs, library.ruleset.core.skill_slots)


def take_candidate(
    library: ContentLibrary,
    run: RunState,
    offer: SkillOffer,
    pick: int | None,
    replace: str | None,
) -> RunState:
    """裝上候選 ``pick``（``None`` ＝ 跳過，不變）。``replace`` 是要換掉的技能（新技能放在它的
    位置）；裝不下時拋出 :class:`ChoiceError`（要求指定 ``replace``）。"""
    if pick is None:
        if replace is not None:
            raise ChoiceError("沒有選候選時不能指定要替換的技能")
        return run
    if not 0 <= pick < len(offer.candidates):
        raise ChoiceError(f"候選索引必須是 0～{len(offer.candidates) - 1}，收到 {pick}")
    skill = offer.candidates[pick]
    if skill.id not in library.skills:  # 生成技能：和這一輪已有的技能撞名時加「（二）」
        owned = skill_defs(library, run, [*run.hero.skills, *run.bench])
        skill = unique_skill_name(skill, (s.name_zh for s in owned if s.id != skill.id))
    skills = list(run.hero.skills)
    if replace is None:
        skills.append(skill.id)
    elif replace not in skills:
        raise ChoiceError(f"主角沒有技能 {replace}，不能替換")
    else:
        skills[skills.index(replace)] = skill.id
    defs = skill_defs(library, run, skills, (skill,))
    problems = equip_problems(library, defs)
    if problems:
        hint = "；請指定要替換的技能（replace）" if replace is None else ""
        raise ChoiceError("；".join(problems) + hint)
    # 被換掉的技能進備用（等級保留，3-26a；營火可以換回）
    bench = tuple(sorted({*run.bench, *([] if replace is None else [replace])}))
    # 候選可能是內容庫的手寫技能（技能池，3-24b2）：只有生成技能才存定義
    new = () if skill.id in library.skills else (skill,)
    keep = {*skills, *bench}
    generated = {s.id: s for s in (*run.generated_skills, *new) if s.id in keep}
    hero = run.hero.model_copy(update={"skills": tuple(skills)})
    return run.model_copy(
        update={
            "hero": hero,
            "bench": bench,
            "generated_skills": tuple(generated[k] for k in sorted(generated)),
        }
    )
