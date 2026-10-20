"""升級與重骰的技能候選（隨機組合器），以及把候選裝上主角（Phase 3-5a）。

候選的亂數串流是 ``Rng(一輪的種子).fork("offer/<n>")``，``n`` 是 ``RunState.offers_made``（第幾組
候選），所以同一輪同一時點的候選固定。每次從串流取一個組合器種子，交給
:func:`trpg.skillgen.random_composer.compose_random_skill`（階級依主角等級，``roguelite.yaml`` 的
``offer_tier_by_level``），過濾掉：組不出來的、武器不相容的、主角已經有的、同一組重複的。

- **順路**：縮放屬性 ＝ 主角目前最高屬性；組合器的分類提示依最高屬性（力量、敏捷 → 武器技，
  其他 → 法術技）。
- **偏離路線**（0.2 C）：縮放屬性不同。固定 ``off_route_per_offer`` 個，放在最後。
- 嘗試 ``offer_max_attempts`` 個種子仍湊不齊時，用多出來的合格技能補（偏離路線的索引以實際縮放
  屬性計算）；再不夠就少給（極少發生）。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_slot_problems, weapon_problem
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.start import top_attribute
from trpg.roguelite.state import RunState, SkillOffer
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute
from trpg.skillgen.random_composer import ComposeError, compose_random_skill

__all__ = ["equip_problems", "make_offer", "skill_defs", "take_candidate"]

_WEAPON_ATTRS = frozenset({Attribute.STR, Attribute.DEX})


def _compose(
    library: ContentLibrary, seed: int, tier: int, category: str | None
) -> SkillDef | None:
    try:
        return compose_random_skill(seed, tier=tier, category=category, library=library)
    except ComposeError:
        return None


def make_offer(library: ContentLibrary, run: RunState, reason: str) -> SkillOffer:
    """第 ``run.offers_made`` 組候選（呼叫者負責把計數器加 1）。"""
    rules = library.roguelite
    tier = rules.offer_tier(run.level)
    top = top_attribute(run.hero.attributes)
    weapon_class = library.weapons[run.hero.weapon].weapon_class
    need_off = rules.off_route_per_offer
    need_on = rules.offer_size - need_off
    hint = "weapon" if top in _WEAPON_ATTRS else "spell"
    rng = Rng(run.seed).fork(f"offer/{run.offers_made}")
    seen = set(run.hero.skills)
    on: list[SkillDef] = []
    off: list[SkillDef] = []
    spare: list[SkillDef] = []
    for _ in range(rules.offer_max_attempts):
        if len(on) >= need_on and len(off) >= need_off:
            break
        skill = _compose(library, rng.next_u32(), tier, hint if len(on) < need_on else None)
        if skill is None or skill.id in seen or weapon_problem(skill, weapon_class) is not None:
            continue
        seen.add(skill.id)
        bucket, need = (on, need_on) if skill.scaling_attr == top else (off, need_off)
        (bucket if len(bucket) < need else spare).append(skill)
    while len(on) < need_on and spare:
        on.append(spare.pop(0))
    while len(off) < need_off and spare:
        off.append(spare.pop(0))
    candidates = (*on, *off)
    return SkillOffer(
        reason="level_up" if reason == "level_up" else "reroll",
        tier=tier,
        top_attribute=top,
        candidates=candidates,
        off_route=tuple(i for i, s in enumerate(candidates) if s.scaling_attr != top),
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
    generated = {s.id: s for s in (*run.generated_skills, skill) if s.id in skills}
    hero = run.hero.model_copy(update={"skills": tuple(skills)})
    return run.model_copy(
        update={"hero": hero, "generated_skills": tuple(generated[k] for k in sorted(generated))}
    )
