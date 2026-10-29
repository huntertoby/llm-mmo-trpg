"""升級與完整技能三選一的技能候選，以及把候選裝上主角（Phase 3-5a；3-24b2 改用共用候選產生器）。

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

角色階級（Phase 3W-9，06 6.34.9）：候選的階級是 :func:`~trpg.skillgen.skill_tier.character_tier`；
手寫池退回的技能（階級和角色不同）照角色階級重配成生成技能（``<原 ID>_t<階級>``），候選池也只取最低
角色階級（``min_character_tier``）不高於角色的技能。

白板（Phase 3W-4，06 6.34.1）：``roguelite.yaml`` 的 ``candidates.whiteboard`` 為真（預設）時，
三選一一律是白板（單一效果、1 階，主動 70／被動 20／反應 10；
:mod:`trpg.skillgen.whiteboard_candidates`），LLM 來源在這個模式下關閉；為假時走完整技能的
候選產生器。

完整技能三選一（Phase 3W-5，06 6.34.6）：一律走完整技能的候選產生器（組合器、技能池；LLM 開著時
先請 LLM 整招提議），再把每個候選照「已閃 3 次」的預算上限（``flash_templates.yaml`` 的
``complete.budget_permille``，+120‰）重做（:func:`as_complete`；3W-5b 起預算分數至少 ×1.12，
召喚加召喚物 HP 與傷害、姿態加幅度，仍加不上去時減代價）。

``off_route``（偏離路線，0.2 C）仍照舊標示：候選的縮放屬性與主角目前最高屬性不同的索引（只是標示，
不再刻意湊一個）；武器技看主角手上武器的縮放屬性（3H-7）。
``roguelite.yaml`` 的 ``offer_size``、``off_route_per_offer``、
``offer_max_attempts`` 從 3-24b2 起不再使用（保留欄位，見報告待決）。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar

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
from trpg.skillgen.complete import complete_strength
from trpg.skillgen.proposal_topic import primitive_uses
from trpg.skillgen.skill_tier import character_tier, retier
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates

_TIER_ID = re.compile(r"^(skill_[a-z0-9_]+?)_t(\d+)$")

__all__ = [
    "COMPLETE_SUFFIX",
    "CompleteObserver",
    "as_complete",
    "at_run_tier",
    "candidate_request",
    "equip_problems",
    "library_base",
    "make_offer",
    "observe_complete",
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
        tier=character_tier(library, run.level),  # 角色階級（3W-9：技能預算用角色階級，同一個函式）
        behavior=dict(run.behavior),
        hero_attributes=dict(run.hero.attributes),  # 新技能跟主屬性（Phase 3H-3）
        weapon_attrs=weapon_scaling_attrs(weapon),  # 武器技看手上武器（Phase 3H-7）
        held=loadout_held(weapon, _hero_loadout(library, run)),  # 招牌技與武器親和（3I-5）
        llm_uses=dict(run.llm_uses),  # run 內配額（Phase 4-L6）
        # 閃現前的原本技能也排除（Phase 3W-5：閃現後原技能不再出現在候選）
        exclude=frozenset(
            (
                *run.hero.skills,
                *run.bench,
                *(f.base_id for f in run.flash.values()),
                *(
                    b
                    for s in (*run.hero.skills, *run.bench)
                    if (b := library_base(library, s)) is not None
                ),
            )
        ),
    )


def library_base(library: ContentLibrary, skill_id: str) -> str | None:
    """``skill_id`` 對應的手寫技能 ID：本身在內容庫裡，或是手寫技能重配到角色階級後的
    ``<原 ID>_t<階級>``（3W-9）；都不是時 ``None``（生成技能）。"""
    if skill_id in library.skills:
        return skill_id
    found = _TIER_ID.match(skill_id)
    if found is not None and found.group(1) in library.skills:
        return found.group(1)
    return None


def at_run_tier(library: ContentLibrary, skill: SkillDef, tier: int) -> SkillDef:
    """技能換到角色階級 ``tier``（3W-9，:func:`~trpg.skillgen.skill_tier.retier`）；階級相同時原樣
    回傳。手寫技能不能改內容庫，重配後成為一招生成技能，ID 是 ``<原 ID>_t<階級>``（再升階時換成新
    階級的後綴）；生成技能沿用 ID。候選也走這裡，所以卡片上的數字就是拿到後的數字。"""
    if skill.tier == tier:
        return skill
    done = retier(library, skill, tier)
    base = library_base(library, skill.id)
    if base is None:
        return done
    return done.model_copy(update={"id": f"{base}_t{tier}"})


COMPLETE_SUFFIX = "_cp"
"""完整技能的 ID 後綴（候選是內容庫的手寫技能時，重調後成為生成技能 ``<原 ID>_cp``）。"""


type CompleteObserver = Callable[[SkillDef, SkillDef], None]
"""完整技能的觀察者：``(原本的技能, 完整技能)``（模擬報表量實際加上的 ‰ 用；只讀不改）。"""

_COMPLETE_OBSERVER: ContextVar[CompleteObserver | None] = ContextVar(
    "trpg_complete_observer", default=None
)


@contextmanager
def observe_complete(observer: CompleteObserver | None) -> Iterator[None]:
    """在 ``with`` 區塊內，每次 :func:`as_complete` 做出完整技能都通知 ``observer``（離開時還原；
    3W-R2，取代模擬在執行期替換 ``as_complete``）。不影響結果。"""
    token = _COMPLETE_OBSERVER.set(observer)
    try:
        yield
    finally:
        _COMPLETE_OBSERVER.reset(token)


def as_complete(library: ContentLibrary, skill: SkillDef) -> SkillDef:
    """把一招技能變成完整技能的強度（06 6.34.6：視為已閃 3 次，預算上限
    +``complete.budget_permille``‰，而且實際加上去，3W-5b：
    :func:`~trpg.skillgen.complete.complete_strength`）。手寫技能重調後換成生成技能
    ``<原 ID>_cp``。裝了觀察者（:func:`observe_complete`）時通知它。"""
    result = complete_strength(library, skill)
    if library_base(library, skill.id) is not None or result.id in library.skills:
        result = result.model_copy(update={"id": f"{skill.id}{COMPLETE_SUFFIX}"})
    observer = _COMPLETE_OBSERVER.get()
    if observer is not None:
        observer(skill, result)
    return result


def make_offer(library: ContentLibrary, run: RunState, reason: str) -> SkillOffer:
    """第 ``run.offers_made`` 組候選（呼叫者負責把計數器加 1）。``reason`` 為 ``level_up``（白板
    三選一）或 ``complete``（完整技能三選一，Phase 3W-5）。"""
    settings = library.roguelite.candidates
    request = candidate_request(library, run)
    complete = reason == "complete"
    if settings.whiteboard and not complete:  # 白板三選一（3W-4）：單一效果、1 階；LLM 來源關閉
        found = generate_whiteboard_candidates(library, request, settings.composer_tries)
        tier = request.tier
    else:
        found = generate_candidates(
            library,
            request,
            CandidateRules(
                composer_share_permille=settings.composer_share_permille,
                composer_tries=settings.composer_tries,
                general_share_permille=settings.general_share_permille,
                llm_share_permille=settings.llm_share_permille,
                llm_theme_permille=settings.llm_theme_permille,
                llm_reaction_permille=settings.llm_reaction_permille,
            ),
            llm=current_proposer() if run.llm else None,
        )
        tier = request.tier
    top = top_attribute(run.hero.attributes)
    candidates = tuple(at_run_tier(library, c.skill, tier) for c in found)
    if complete:
        candidates = tuple(as_complete(library, s) for s in candidates)
    return SkillOffer(
        reason="complete" if complete else "level_up",
        tier=tier,
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
    # 被換掉的技能進備用（閃現狀態保留；營火可以換回）
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
