"""戰場變奏（Phase 3-25b）的 API 視圖：技能列「目前會生效的型態」與預覽的型態。

型態由引擎的 :func:`trpg.engine.variants.varied_skill`（與施放、預覽、合法動作同一個函式）判定，
這裡只整理成 JSON 給前端；前端不自己判斷任何條件。
"""

from __future__ import annotations

from trpg.api.schemas import PreviewVariantOut, VariantStateOut
from trpg.engine.actions import Action, UseSkill
from trpg.engine.state import BattleState
from trpg.engine.variants import chosen_variant, target_point, varied_skill
from trpg.shared.types import UnitId

__all__ = ["preview_variant", "variant_states"]


def variant_states(
    state: BattleState, hero_id: UnitId, legal: tuple[Action, ...]
) -> tuple[VariantStateOut, ...]:
    """主角每一招帶變奏的技能：

    - ``active``：只看施放者位置的條件（站在表面上、身旁有牆）現在成立的型態（資料順序第一個）；
    - ``available``：目前的合法動作中，目標點會選出的型態（居高、目標點表面也在內；資料順序）。

    技能的順序與主角持有的技能相同；不帶變奏的技能不列。
    """
    hero = state.units[hero_id]
    out: list[VariantStateOut] = []
    for skill_id in hero.all_skills:
        skill = state.ruleset.skill_def(skill_id)
        if not skill.variants:
            continue
        caster_only = chosen_variant(state, hero, skill, None)
        reached = {
            variant
            for action in legal
            if isinstance(action, UseSkill) and action.skill_id == skill_id
            for variant in (varied_skill(state, hero, skill, target_point(state, action))[1],)
            if variant is not None
        }
        out.append(
            VariantStateOut(
                skill_id=skill_id,
                active=None if caster_only is None else caster_only.id,
                available=tuple(v.id for v in skill.variants if v.id in reached),
            )
        )
    return tuple(out)


def preview_variant(state: BattleState, action: Action) -> PreviewVariantOut | None:
    """``action``（預覽）會用到的型態；不是技能或沒有變奏成立時 ``None``。"""
    if not isinstance(action, UseSkill):
        return None
    skill = state.ruleset.skill_def(action.skill_id)
    if not skill.variants:
        return None
    caster = state.units[action.unit_id]
    _form, variant_id = varied_skill(state, caster, skill, target_point(state, action))
    if variant_id is None:
        return None
    return PreviewVariantOut(id=variant_id, name_zh=skill.variant(variant_id).name_zh)
