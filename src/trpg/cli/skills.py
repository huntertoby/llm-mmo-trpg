"""``trpg skills list`` / ``trpg skills show <id>``：技能的自動摘要（Phase 2A 5.2）。"""

from __future__ import annotations

from typing import TextIO

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    SkillDef,
)
from trpg.narrative.skills import (
    CATEGORY_TEXT,
    KIND_TEXT,
    RARITY_TEXT,
    WEAPON_REQ_TEXT,
    condition_summary,
    cost_summary,
    effect_summary,
    mastery_text,
    modifier_summary,
    scaling_detail,
    skill_shape_text,
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
        ap = "修正" if skill.is_modifier else str(skill.ap_cost)
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


def _mastery_active_for(
    library: ContentLibrary, skill: SkillDef, unit_id: str | None
) -> bool | None:
    """單位範本的 ``scaling_attr`` 屬性是否為最高（含並列）；沒指定單位時為 ``None``。"""
    if unit_id is None:
        return None
    attributes = _unit_attributes(library, unit_id)
    mine = attributes[skill.scaling_attr]
    return all(mine >= value for value in attributes.values())


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
        f"  縮放屬性 {scaling_detail(skill)}",
        file=out,
    )
    if skill.mastery is not None:
        print(f"  專精加成 {mastery_text(skill, active=active)}", file=out)
    if skill.is_modifier:
        print("  代價 無（裝在被動欄位、不花 AP）", file=out)
    else:
        print(f"  代價 {cost_summary(library, skill)}", file=out)
    print(f"  形狀 {skill_shape_text(library, skill)}", file=out)
    if skill.condition is not None:
        print(f"  使用條件 {condition_summary(library, skill.condition)}", file=out)
    if skill.is_modifier:
        print("  修正規則（裝在被動欄位，持續生效）：", file=out)
        for i, rule in enumerate(skill.modifiers, start=1):
            print(f"    {i}. {modifier_summary(library, skill, rule)}", file=out)
    else:
        print("  效果：", file=out)
        for i, spec in enumerate(skill.effects, start=1):
            print(f"    {i}. {effect_summary(library, skill, spec)}", file=out)
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
