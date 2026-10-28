"""``trpg skills list`` / ``trpg skills show <id>``：技能的自動摘要（Phase 2A 5.2）。"""

from __future__ import annotations

from typing import TextIO

from trpg.content.battle import WeaponDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    SkillDef,
)
from trpg.narrative.skills import (
    CATEGORY_TEXT,
    KIND_TEXT,
    RARITY_TEXT,
    WEAPON_REQ_TEXT,
    activation_text,
    condition_summary,
    cost_summary,
    effect_summary,
    followup_text,
    mastery_text,
    modifier_summary,
    scaling_detail,
    skill_shape_text,
    variant_change_text,
    variant_condition_text,
    weapon_only_text,
)
from trpg.shared.types import Attribute

__all__ = ["cmd_skills_list", "cmd_skills_show", "pad"]


def pad(text: str, width: int) -> str:
    """以顯示寬度（全形 2、半形 1）補空白。"""
    used = sum(2 if ord(ch) > _WIDE_CHAR_START else 1 for ch in text)
    return text + " " * max(width - used, 1)


_WIDE_CHAR_START = 0x2E80


def cmd_skills_list(library: ContentLibrary, out: TextIO) -> int:
    skills = sorted(library.skills.values(), key=lambda s: s.id)
    print(f"技能（共 {len(skills)} 個）：", file=out)
    print(
        f"  {pad('ID', 24)}{pad('名稱', 12)}{pad('骨架', 10)}{pad('AP', 4)}代價 / 效果",
        file=out,
    )
    for skill in skills:
        cost = cost_summary(library, skill, with_ap=False)
        effects = "；".join(effect_summary(library, skill, e) for e in skill.effects)
        if skill.is_modifier:
            effects = "；".join(modifier_summary(library, skill, r) for r in skill.modifiers)
        # 不花 AP 的技能（被動、反應、姿態）顯示種類，不再顯示「None」（Phase 3-5a，0.10 #1）
        ap = KIND_TEXT[skill.kind] if skill.ap_cost is None else str(skill.ap_cost)
        if skill.is_modifier:
            ap = "修正"
        if skill.is_activatable:  # 常駐類傳說（Phase 3D-6）
            effects += f"［{activation_text(library, skill)}］"
        second = followup_text(library, skill)
        if second is not None:  # 複合技能（Phase 3F-3a）
            effects += f" → 第二段：{second}"
        print(
            f"  {pad(skill.id, 24)}{pad(skill.name_zh, 12)}{pad(skill.skeleton, 10)}"
            f"{pad(ap, 4)}{cost or '無'}",
            file=out,
        )
        when = f"［條件：{condition_summary(library, skill.condition)}］" if skill.condition else ""
        print(f"    {skill_shape_text(library, skill)}{when}：{effects}", file=out)
    return 0


def _unit_attributes(library: ContentLibrary, unit_id: str) -> dict[Attribute, int]:
    """單位範本或 build 英雄的屬性。"""
    template = library.units.get(unit_id)
    if template is not None:
        return dict(template.attributes)
    for build in library.builds.builds:
        if unit_id in (build.id, build.hero.id):
            return dict(build.hero.attributes)
    raise KeyError(f"找不到單位或 build：{unit_id}")


def _unit_weapon(library: ContentLibrary, unit_id: str | None) -> WeaponDef | None:
    """單位範本或 build 英雄的武器（武器技看手上武器，3H-6）；沒指定單位時為 ``None``。"""
    if unit_id is None:
        return None
    template = library.units.get(unit_id)
    if template is None:
        template = next(
            (b.hero for b in library.builds.builds if unit_id in (b.id, b.hero.id)), None
        )
    return None if template is None else library.weapons.get(template.weapon)


def _mastery_active_for(
    library: ContentLibrary, skill: SkillDef, unit_id: str | None
) -> bool | None:
    """單位範本的 ``scaling_attr`` 屬性是否為最高（含並列）；沒指定單位時為 ``None``。"""
    if unit_id is None:
        return None
    attributes = _unit_attributes(library, unit_id)
    mine = skill.mastery_value(attributes.__getitem__, _unit_weapon(library, unit_id))
    return all(mine >= value for value in attributes.values())


def _print_body(library: ContentLibrary, skill: SkillDef, out: TextIO) -> None:
    """啟動方式（常駐類傳說，Phase 3D-6）與修正規則或效果的列表。"""
    if skill.is_activatable:
        print(f"  啟動 {activation_text(library, skill)}（啟動前不生效）", file=out)
    if skill.is_modifier:
        where = "裝在被動欄位，啟動後生效" if skill.is_activatable else "裝在被動欄位，持續生效"
        print(f"  修正規則（{where}）：", file=out)
        for i, rule in enumerate(skill.modifiers, start=1):
            print(f"    {i}. {modifier_summary(library, skill, rule)}", file=out)
        return
    print("  效果：", file=out)
    for i, spec in enumerate(skill.effects, start=1):
        print(f"    {i}. {effect_summary(library, skill, spec)}", file=out)
    for variant in skill.variants:  # 戰場變奏（Phase 3-25a）
        print(
            f"  戰場變奏「{variant.name_zh}」（{variant.id}）："
            f"{variant_condition_text(library, variant.when)} → "
            f"{variant_change_text(library, skill, variant)}",
            file=out,
        )
    second = followup_text(library, skill)
    if second is not None:  # 複合技能（Phase 3F-3a）
        follow = skill.followup_skill()
        assert follow is not None
        print(f"  第二段（骨架 {follow.skeleton}）：{second}", file=out)


def cmd_skills_show(
    library: ContentLibrary, skill_id: str, out: TextIO, *, unit_id: str | None = None
) -> int:
    skill = library.skills.get(skill_id)
    if skill is None:
        raise KeyError(f"找不到技能：{skill_id}")
    active = _mastery_active_for(library, skill, unit_id)
    print(f"{skill.name_zh}（{skill.id}）", file=out)
    print(
        f"  階級 T{skill.tier}（等第 {skill.rank}）  稀有度 {RARITY_TEXT[skill.rarity]}"
        f"  種類 {KIND_TEXT[skill.kind]}  骨架 {skill.skeleton}",
        file=out,
    )
    print(
        f"  分類 {CATEGORY_TEXT[skill.category]}  武器需求 {WEAPON_REQ_TEXT[skill.weapon_req]}"
        f"  縮放屬性 {scaling_detail(skill, _unit_weapon(library, unit_id))}",
        file=out,
    )
    limited = weapon_only_text(library, skill)
    if limited is not None:  # 專屬招牌技（3I-5）
        print(f"  {limited}（沒拿就不能裝備、不能施放）", file=out)
    if skill.mastery is not None:
        text = mastery_text(skill, active=active, weapon=_unit_weapon(library, unit_id))
        print(f"  專精加成 {text}", file=out)
    if skill.is_modifier and not skill.is_activatable:
        print("  代價 無（裝在被動欄位、不花 AP）", file=out)
    else:
        print(f"  代價 {cost_summary(library, skill)}", file=out)
    print(f"  形狀 {skill_shape_text(library, skill)}", file=out)
    if skill.condition is not None:
        print(f"  使用條件 {condition_summary(library, skill.condition)}", file=out)
    _print_body(library, skill, out)
    if skill.tags:
        print(f"  標籤 {'、'.join(skill.tags)}", file=out)
    if skill.narrative.concept:
        print(f"  概念 {skill.narrative.concept}", file=out)
    if skill.narrative.cast_flavor:
        print(f"  施放 {skill.narrative.cast_flavor}", file=out)
    prov = skill.provenance
    bound = "，綁定" if prov.bound else ""
    trade = "，可交易" if prov.tradeable else "，不可交易"
    print(f"  來源 {prov.origin}{bound}{trade}", file=out)
    return 0
