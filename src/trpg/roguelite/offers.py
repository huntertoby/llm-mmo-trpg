"""升級與重骰的技能候選，以及把候選裝上主角（Phase 3-5a；3-24b2 改用共用候選產生器）。

候選由 :func:`trpg.skillgen.candidates.generate_candidates` 產生（06 6.27.4）：**加深**（持有最多的
關鍵字）、**橋接**（同時帶兩個已持有的關鍵字）、**新方向**（還沒有的關鍵字），依序排列；每個候選的標示
存在 ``SkillOffer.tags``。產生器的輸入：主角目前技能的關鍵字分布（只看專屬規則）、武器大類、這一輪的
行為紀錄（``RunState.behavior``）、候選的階級（依主角等級，``offer_tier_by_level``）與種子。

種子是 ``Rng(一輪的種子).fork("offer/<n>").next_u32()``，``n`` 是 ``RunState.offers_made``（第幾組
候選），所以同一輪同一時點的候選固定。

新技能跟主屬性（Phase 3H-3）：候選產生器拿到主角目前的屬性，加深與橋接優先取縮放屬性＝最高屬性的
技能，新方向保留給不同屬性（見 ``trpg.skillgen.candidates``）。

LLM 來源（Phase 4-L6）：``run.llm`` 為真而且外層裝了提議器（``trpg.roguelite.llm_hook``）時，候選
產生器先請 LLM 提議（失敗退回組合器與技能池，候選仍湊滿）；題目、嘗試次數與來源記在候選的
``OfferTag.llm``，run 內配額與紀錄由 :func:`offer_updates` 併入 ``RunState``。

``off_route``（偏離路線，0.2 C）仍照舊標示：候選的縮放屬性與主角目前最高屬性不同的索引（只是標示，
不再刻意湊一個）；武器技看主角手上武器的縮放屬性（3H-7）。
``roguelite.yaml`` 的 ``offer_size``、``off_route_per_offer``、
``offer_max_attempts`` 從 3-24b2 起不再使用（保留欄位，見報告待決）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.battle import WeaponDef
from trpg.content.equipment import Loadout, loadout_held, resolve_loadout
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_slot_problems
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.llm_hook import current_proposer
from trpg.roguelite.names import unique_skill_name
from trpg.roguelite.state import LlmRecord, OfferTag, RunState, SkillOffer
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute
from trpg.skillgen.candidates import (
    Candidate,
    CandidateRequest,
    CandidateRules,
    follows_attr,
    generate_candidates,
    keyword_distribution,
)
from trpg.skillgen.proposal_topic import primitive_uses

__all__ = [
    "candidate_request",
    "equip_problems",
    "make_offer",
    "offer_updates",
    "skill_defs",
    "take_candidate",
]


def _hero_loadout(library: ContentLibrary, run: RunState) -> Loadout:
    """主角這一輪的裝備（測試模式挑的裝備優先；與 ``progress.run_loadout`` 同一個規則）。"""
    if run.test_equipment:
        return resolve_loadout(run.test_equipment, library.items, library.affixes)
    return library.loadout_of(run.hero)


def candidate_request(library: ContentLibrary, run: RunState) -> CandidateRequest:
    """第 ``run.offers_made`` 組候選的產生器輸入（見模組說明）。"""
    held = skill_defs(library, run, run.hero.skills)
    weapon = library.weapons[run.hero.weapon]
    return CandidateRequest(
        keyword_counts=keyword_distribution(held, library),
        weapon_class=weapon.weapon_class,
        seed=Rng(run.seed).fork(f"offer/{run.offers_made}").next_u32(),
        tier=library.roguelite.offer_tier(run.level),
        behavior=dict(run.behavior),
        hero_attributes=dict(run.hero.attributes),  # 新技能跟主屬性（Phase 3H-3）
        weapon_attrs=weapon_scaling_attrs(weapon),  # 武器技看手上武器（Phase 3H-7）
        held=loadout_held(weapon, _hero_loadout(library, run)),  # 招牌技與武器親和（3I-5）
        llm_uses=dict(run.llm_uses),  # run 內配額（Phase 4-L6）
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
            general_share_permille=settings.general_share_permille,
            llm_share_permille=settings.llm_share_permille,
            llm_theme_permille=settings.llm_theme_permille,
        ),
        llm=current_proposer() if run.llm else None,
    )
    top = top_attribute(run.hero.attributes)
    candidates = tuple(c.skill for c in found)
    return SkillOffer(
        reason="level_up" if reason == "level_up" else "reroll",
        tier=request.tier,
        top_attribute=top,
        candidates=candidates,
        off_route=tuple(
            i for i, s in enumerate(candidates) if not follows_attr(s, top, request.weapon_attrs)
        ),
        tags=tuple(_tag(c, run.offers_made) for c in found),
    )


def _tag(candidate: Candidate, offer_index: int) -> OfferTag:
    trace = candidate.llm
    record = (
        None
        if trace is None
        else LlmRecord(
            offer=offer_index,
            kind=candidate.kind,
            keywords=trace.keywords,
            rarity=trace.rarity,
            core_primitive=trace.core_primitive,
            menu_seed=trace.menu_seed,
            theme=trace.theme,
            attempts=trace.attempts,
            ok=trace.ok,
            codes=trace.codes,
            reason=trace.reason,
            name_source=trace.name_source,
            name_attempts=trace.name_attempts,
            name_codes=trace.name_codes,
            prompt_version=trace.prompt_version,
            naming_prompt_version=trace.naming_prompt_version,
        )
    )
    return OfferTag(
        kind=candidate.kind,
        keywords=candidate.keywords,
        source=candidate.source,
        fallback=candidate.fallback,
        llm=record,
    )


def offer_updates(run: RunState, offer: SkillOffer) -> dict[str, object]:
    """產生一組候選之後要併入 ``RunState`` 的欄位（Phase 4-L6）：LLM 生成開關打開時，累加候選裡各
    原語的出現次數（run 內配額）並附上這組候選的 LLM 紀錄；關閉時是空的（行為與以往相同）。"""
    if not run.llm:
        return {}
    uses = dict(run.llm_uses)
    for primitive, count in primitive_uses(offer.candidates).items():
        uses[primitive] = uses.get(primitive, 0) + count
    records = tuple(t.llm for t in offer.tags if t.llm is not None)
    return {"llm_uses": dict(sorted(uses.items())), "llm_log": (*run.llm_log, *records)}


def weapon_scaling_attrs(weapon: WeaponDef) -> tuple[Attribute, ...]:
    """武器的縮放屬性（含第二縮放屬性）：武器技實際吃的屬性（3H-6）。"""
    second = weapon.secondary_scaling_attr
    return (weapon.scaling_attr,) if second is None else (weapon.scaling_attr, second)


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
