"""``trpg skills list`` / ``trpg skills show <id>``：技能的自動摘要（Phase 2A 5.2）。"""

from __future__ import annotations

from typing import TextIO

from trpg.content.battle import Dice
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    ConditionSpec,
    EffectSpec,
    ShapeSpec,
    SkillDef,
    condition_text,
    default_affects,
)

__all__ = ["cmd_skills_list", "cmd_skills_show", "effect_summary", "shape_summary"]

_AFFECTS = {
    "enemies": "敵方",
    "allies": "友方",
    "all": "所有單位",
    "self": "自己",
    "tiles": "影響的格子",
}
_RARITY = {"common": "普通", "rare": "稀有", "epic": "史詩", "legendary": "傳說"}
_CATEGORY = {"weapon": "武器技", "spell": "法術技"}
_WEAPON_REQ = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}
_KIND = {"active": "主動", "reaction": "反應", "passive": "被動", "stance": "姿態"}


def _dice(dice: Dice) -> str:
    return f"{dice.count}d{dice.sides}"


def shape_summary(library: ContentLibrary, shape: ShapeSpec) -> str:
    """形狀與參數的一句話，例如「錐形 3」「單體 射程 6」。"""
    name = library.ruleset.shape_def(shape.type).name_zh
    labels = {
        "range": "射程",
        "size": "大小",
        "radius": "半徑",
        "jumps": "跳躍",
        "jump_range": "跳躍距離",
    }
    parts: list[str] = []
    for key, value in shape.param_values().items():
        text = "武器射程" if value == "weapon" else str(value)
        parts.append(f"{labels[key]} {text}")
    return f"{name}（{'，'.join(parts)}）" if parts else name


def _effect_core(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:  # noqa: PLR0911
    rules = library.ruleset
    kind = spec.type
    if kind == "damage":
        if skill.category == "spell":
            assert spec.dice is not None and spec.element is not None
            attr, element = skill.scaling_attr.display_name, spec.element.display_name
            return f"{_dice(spec.dice)}＋{attr}加成的{element}傷害"
        permille = spec.multiplier_permille or 1000
        element = f"（{spec.element.display_name}）" if spec.element is not None else ""
        return f"武器傷害 ×{permille / 1000:g}{element}"
    if kind == "heal":
        assert spec.dice is not None
        return f"治療 {_dice(spec.dice)}＋{skill.scaling_attr.display_name}加成"
    if kind in ("push", "pull"):
        return f"{'推開' if kind == 'push' else '拉近'} {spec.distance} 格"
    if kind == "knock_prone":
        return f"擊倒（{skill.scaling_attr.display_name}對抗）"
    if kind == "teleport":
        return "傳送到目標格"
    if kind == "apply_status":
        assert spec.status is not None
        turns = f" {spec.duration} 回合" if spec.duration else ""
        return f"狀態「{rules.status_def(spec.status).name_zh}」{turns}"
    if kind == "create_surface":
        assert spec.surface is not None
        turns = f" {spec.duration} 回合" if spec.duration else ""
        return f"生成「{rules.surface_def(spec.surface).name_zh}」表面{turns}"
    if kind == "create_obstacle":
        assert spec.object is not None
        return f"生成「{rules.object_def(spec.object).name_zh}」"
    if kind == "destroy_object":
        return "摧毀可破壞的物件"
    if kind in ("raise_terrain", "lower_terrain"):
        verb = "抬高" if kind == "raise_terrain" else "降低"
        return f"{verb}地形 {spec.amount or 1} 層"
    return rules.primitive_def(kind).name_zh


def effect_summary(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """一個效果的一句話，含對象，例如「2d6＋智力加成的火焰傷害（敵方）」。"""
    primitive = library.ruleset.primitive_def(spec.type)
    affects = spec.affects or default_affects(primitive)
    text = f"{_effect_core(library, skill, spec)}（{_AFFECTS[affects]}）"
    if spec.condition is not None:
        text += f"，若{_condition(library, spec.condition)}"
    return text


def _condition(library: ContentLibrary, condition: ConditionSpec) -> str:
    rules = library.ruleset
    return condition_text(
        condition,
        status_name=lambda sid: rules.status_def(sid).name_zh,
        surface_name=lambda surface: rules.surface_def(surface).name_zh,
    )


def _cost_summary(skill: SkillDef, *, with_ap: bool = True) -> str:
    cost = skill.cost
    parts = [f"AP {skill.ap_cost}"] if with_ap else []
    if cost.mana:
        parts.append(f"法力 {cost.mana}")
    if cost.hp_percent:
        parts.append(f"HP {cost.hp_percent / 10:g}%")
    if cost.cooldown:
        parts.append(f"冷卻 {cost.cooldown} 回合")
    if cost.uses_per_battle:
        parts.append(f"每場 {cost.uses_per_battle} 次")
    return "，".join(parts)


def _pad(text: str, width: int) -> str:
    """以顯示寬度（全形 2、半形 1）補空白。"""
    used = sum(2 if ord(ch) > _WIDE_CHAR_START else 1 for ch in text)
    return text + " " * max(width - used, 1)


_WIDE_CHAR_START = 0x2E80


def cmd_skills_list(library: ContentLibrary, out: TextIO) -> int:
    skills = sorted(library.skills.values(), key=lambda s: s.id)
    print(f"技能（共 {len(skills)} 個）：", file=out)
    print(
        f"  {_pad('ID', 24)}{_pad('名稱', 12)}{_pad('骨架', 10)}{_pad('AP', 4)}代價 / 效果",
        file=out,
    )
    for skill in skills:
        cost = _cost_summary(skill, with_ap=False)
        effects = "；".join(effect_summary(library, skill, e) for e in skill.effects)
        print(
            f"  {_pad(skill.id, 24)}{_pad(skill.name_zh, 12)}{_pad(skill.skeleton, 10)}"
            f"{_pad(str(skill.ap_cost), 4)}{cost or '無'}",
            file=out,
        )
        when = f"［條件：{_condition(library, skill.condition)}］" if skill.condition else ""
        print(f"    {shape_summary(library, skill.shape)}{when}：{effects}", file=out)
    return 0


def cmd_skills_show(library: ContentLibrary, skill_id: str, out: TextIO) -> int:
    skill = library.skills.get(skill_id)
    if skill is None:
        raise KeyError(f"找不到技能：{skill_id}")
    print(f"{skill.name_zh}（{skill.id}）", file=out)
    print(
        f"  階級 T{skill.tier}（等第 {skill.rank}）  稀有度 {_RARITY[skill.rarity]}"
        f"  種類 {_KIND[skill.kind]}  骨架 {skill.skeleton}",
        file=out,
    )
    print(
        f"  分類 {_CATEGORY[skill.category]}  武器需求 {_WEAPON_REQ[skill.weapon_req]}"
        f"  縮放屬性 {skill.scaling_attr.display_name}",
        file=out,
    )
    print(f"  代價 {_cost_summary(skill)}", file=out)
    print(f"  形狀 {shape_summary(library, skill.shape)}", file=out)
    if skill.condition is not None:
        print(f"  使用條件 {_condition(library, skill.condition)}", file=out)
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
