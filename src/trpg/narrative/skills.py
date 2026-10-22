"""技能的繁體中文描述（原在 ``trpg.cli.skills``，Phase 3-1 搬出，讓 CLI 與網頁技能卡片共用）。

- 形狀、縮放、專精、代價、條件與每個效果的一句話描述。
- 修正規則（Phase 3C-2，``kind: modifier``）的一句話描述（:func:`modifier_summary`）。
- :func:`skill_card` 把一個技能整理成 :class:`SkillCard`（pydantic，可直接當 API 回應）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import Dice
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    CHEAT_DEATH_STATUS,
    DAMAGE_MULTIPLIER,
    REDIRECT_STATUS,
    SELF_DAMAGE_OF_HIT,
    ConditionSpec,
    EffectSpec,
    ModifierSpec,
    ModifierTarget,
    ShapeSpec,
    SkillDef,
    VariantSpec,
    VariantWhen,
    condition_text,
    default_affects,
    on_hit_carrier,
)
from trpg.content.stacks import StackDef
from trpg.narrative.skill_icon import SkillIcon, skill_icon
from trpg.narrative.skill_levels import SkillLevelInfo
from trpg.shared.types import Surface, rune_name
from trpg.skillgen.keywords import SkillKeywords, derive_draft_keywords, derive_keywords

__all__ = [
    "CATEGORY_TEXT",
    "KIND_TEXT",
    "RARITY_TEXT",
    "WEAPON_REQ_TEXT",
    "KeywordRef",
    "SkillCard",
    "SkillCardKeywords",
    "SkillLevelInfo",
    "SkillVariantCard",
    "activation_text",
    "branch_text",
    "condition_summary",
    "cost_parts",
    "cost_summary",
    "draft_card_keywords",
    "effect_summary",
    "followup_text",
    "keywords_card",
    "mastery_text",
    "miss_text",
    "modifier_summary",
    "rule_change_text",
    "scaling_detail",
    "scaling_label",
    "scaling_text",
    "shape_summary",
    "skill_ap",
    "skill_card",
    "skill_shape_text",
    "variant_change_text",
    "variant_condition_text",
]

_AFFECTS = {
    "enemies": "敵方",
    "allies": "友方",
    "all": "所有單位",
    "self": "自己",
    "tiles": "影響的格子",
}
RARITY_TEXT = {"common": "普通", "rare": "稀有", "epic": "史詩", "legendary": "傳說"}
CATEGORY_TEXT = {"weapon": "武器技", "spell": "法術技"}
WEAPON_REQ_TEXT = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}
KIND_TEXT = {
    "active": "主動",
    "reaction": "反應",
    "passive": "被動",
    "stance": "姿態",
    "modifier": "修正",
}
_ACTION_TEXT = {"attack": "普攻", "shove": "推擊", "trip": "絆倒", "interact": "互動"}


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


def skill_shape_text(library: ContentLibrary, skill: SkillDef) -> str:
    """技能的形狀一句話；穿透的技能（Phase 3C-5b）加上「穿透」。"""
    text = shape_summary(library, skill.shape)
    return f"{text}・穿透" if skill.pierce else text


def followup_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """複合技能（Phase 3F-3a）第二段的一句話，例如「到達落點後，以落點為原點：錐形（大小 2）：
    傷害…」；不是複合技能時為 ``None``。"""
    follow = skill.followup_skill()
    if follow is None or skill.followup is None:
        return None
    effects = "；".join(effect_summary(library, follow, e) for e in follow.effects)
    when = f"［條件：{condition_summary(library, follow.condition)}］" if follow.condition else ""
    if skill.followup.release is not None:  # 延遲段（Phase 3F-4b）
        lead = _DELAYED_LEADS[skill.followup.release]
    else:
        lead = _FOLLOWUP_LEADS[skill.followup.when]
    return f"{lead}：{shape_summary(library, follow.shape)}{when}：{effects}"


_FOLLOWUP_LEADS = {
    "after_move": "到達落點後，以落點為原點",
    "after_action": "結算後，從自己的位置（自選落點）",
    "after_gather": "聚集後，以聚集點為中心",
    "on_kill": "擊倒敵人的話，從自己的位置（自選目標）",
    "on_hit": "命中的話，對同一個目標",
}
_DELAYED_LEADS = {
    "next_turn": "蓄力，下回合開始時以自己為中心釋放",
    "attacked": "蓄力，下回合開始前被敵人攻擊時以自己為中心釋放（沒被攻擊就失效）",
}
"""延遲段（Phase 3F-4b）第二段一句話的開頭（依 ``followup.release``）。"""
"""複合技能第二段一句話的開頭（依 ``followup.when``；Phase 3F-4a）。"""


def scaling_label(skill: SkillDef) -> str:
    """縮放屬性的簡稱：單屬性為「智力」，雙屬性為「力量／智力」（Phase 2H-2）。"""
    names = [skill.scaling_attr.display_name]
    if skill.secondary_scaling_attr is not None:
        names.append(skill.secondary_scaling_attr.display_name)
    return "／".join(names)


def scaling_detail(skill: SkillDef) -> str:
    """縮放屬性的完整說明：雙屬性為「力量 50%＋智力 50%」。"""
    if skill.secondary_scaling_attr is None:
        return skill.scaling_attr.display_name
    return f"{skill.scaling_attr.display_name} 50%＋{skill.secondary_scaling_attr.display_name} 50%"


def mastery_text(skill: SkillDef, *, active: bool | None = None) -> str:
    """專精加成的說明；``active`` 為 ``None`` 表示不知道單位（只顯示加成內容）。"""
    effect = "施放距離 +1" if skill.mastery == "range" else "施加的狀態持續 +1 回合"
    attr = skill.scaling_attr.display_name
    note = f"（{attr}為最高屬性時生效）"
    if active is not None:
        note = f"（{attr}為最高屬性，生效中）" if active else f"（{attr}不是最高屬性，未生效）"
    return effect + note


# ---------------------------------------------------------------------------
# 效果：依原語類型的描述器註冊表
# ---------------------------------------------------------------------------

type _EffectText = Callable[[ContentLibrary, SkillDef, EffectSpec], str]


_SCALE_TEXT = {
    "missing_hp_10pct": "你每少 10% 最大 HP",
    "distance": "與目標每距 1 格",
    "enemies_adjacent_target": "目標每有 1 名相鄰的敵人",
    "enemies_adjacent_self": "你每有 1 名相鄰的敵人",
}
"""依情況縮放的依據（Phase 3D-7b）。"""


def scaling_text(spec: EffectSpec) -> str | None:
    """傷害的縮放一句話（Phase 3D-7b），例如「你每少 10% 最大 HP，傷害 +8%（最多 +80%）」。"""
    scaling = spec.scaling
    if scaling is None:
        return None
    return (
        f"{_SCALE_TEXT[scaling.by]}，傷害 +{scaling.per_step_permille / 10:g}%"
        f"（最多 +{scaling.cap_permille / 10:g}%）"
    )


def _damage(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    discount = skill.damage_permille or 1000
    if skill.category == "spell":
        assert spec.dice is not None and spec.element is not None
        attr, element = scaling_label(skill), spec.element.display_name
        text = f"{_dice(spec.dice)}＋{attr}加成的{element}傷害"
        if skill.damage_permille is not None:
            text += f"（基礎傷害 ×{discount / 1000:g}）"
    else:
        permille = (spec.multiplier_permille or 1000) * discount // 1000
        element = f"（{spec.element.display_name}）" if spec.element is not None else ""
        text = f"武器傷害 ×{permille / 1000:g}{element}"
    extras: list[str] = []
    if spec.split_heal:
        extras.append("友方（含自己）改為治療同樣的骰值（不擲命中，只骰一次）")
    if spec.lifesteal_permille is not None:
        extras.append(f"吸血：你回復造成傷害的 {spec.lifesteal_permille / 10:g}%")
    if spec.explode:
        extras.append(f"爆骰（擲到最大值再擲一次，每顆最多再擲 {lib.ruleset.core.explode_max} 次）")
    if skill.crit_range is not None:
        extras.append(f"暴擊範圍 {skill.crit_range}–20")
    scale = scaling_text(spec)
    if scale is not None:
        extras.append(scale)
    if spec.on_kill:
        kill = "、".join(_on_kill_text(lib, skill, sub) for sub in spec.on_kill)
        extras.append(f"若這一招讓敵人倒下：{kill}")
    return text + "".join(f"，{e}" for e in extras)


def _on_kill_text(lib: ContentLibrary, skill: SkillDef, sub: EffectSpec) -> str:
    """擊殺時效果（``on_kill``，Phase 3D-8b）的一句話（對象一律是施放者）。"""
    if sub.type == "refund_ap":
        return f"返還 {sub.amount or 1} AP"
    if sub.type == "refund_cooldown":
        return "本技能冷卻歸零"
    return f"你{_effect_core(lib, skill, sub)}"


def _heal(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    return f"治療 {_dice(spec.dice)}＋{scaling_label(skill)}加成"


def _push_pull(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    text = f"{'推開' if spec.type == 'push' else '拉近'} {spec.distance} 格"
    if spec.collision_dice is not None:
        text += f"（撞擊傷害 {_dice(spec.collision_dice)}）"
    return text


def _knock_prone(_lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    return f"擊倒（{scaling_label(skill)}對抗）"


def _teleport(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "傳送到目標格"


def _dash(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "衝鋒到目標身旁（先結算，不消耗移動點數；途中會被藉機攻擊與陷阱攔下）"


def _leap(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "跳到目標格（無視中間的單位與低矮地形；不觸發藉機攻擊）"


def _shadowstep(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    if spec.landing == "behind":
        where = "瞬間出現在目標背後（背後被占住時改到最近的側面；先結算）"
    else:
        where = "瞬間出現在目標身旁自選的一格（先結算）"
    return where + "，不觸發藉機攻擊，落地後面向目標"


def _summon(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    try:
        summon = lib.ruleset.summon_def(spec.unit or "")
    except KeyError:
        name = spec.unit or "召喚物"
    else:
        template, weapon = summon.template, summon.weapon
        hp = lib.ruleset.core.template_max_hp(template)
        totem = template.totem
        if totem is not None:  # 圖騰（3D-4b）
            status = lib.ruleset.status_def(totem.status).name_zh
            return (
                f"在目標空格立起{template.name_zh}（HP {hp}），持續 {spec.duration} 輪"
                f"（緊接在你之後行動；不移動、不攻擊，每次行動開始時讓 {totem.radius} 格內的"
                f"友方獲得「{status}」{totem.duration} 回合）"
            )
        name = f"{template.name_zh}（HP {hp}，{weapon.name_zh}）"
    return f"在目標空格召喚{name}，持續 {spec.duration} 輪（緊接在你之後行動，由 AI 控制）"


def rule_change_text(library: ContentLibrary, rule_id: str) -> str:
    """規則改變（Phase 3D-6）的一句話，例如「規則改變「移山」：你可以推動……」。"""
    rules = library.ruleset
    try:
        rule = rules.rule_change_def(rule_id)
    except KeyError:
        return f"規則改變 {rule_id}"
    if rule.kind == "element_heals_allies":
        assert rule.element is not None and rule.permille is not None
        text = (
            f"你造成的{rule.element.display_name}傷害打到友方（不含自己）時，改為治療"
            f"（原本傷害的 {rule.permille / 10:g}%）"
        )
    elif rule.kind == "push_any_object":
        text = "你可以推動任何擋路的物件（例如土牆、矮牆、倒木），可推倒的照樣倒下；地形與橋面不行"
    elif rule.kind == "pass_through_apply":
        assert rule.status is not None
        status = rules.status_def(rule.status).name_zh
        text = (
            f"你步行經過敵人的相鄰格時，對他施加「{status}」{rule.duration} 回合"
            "（每次移動每個敵人一次）"
        )
    else:
        assert rule.unit is not None
        try:
            name = rules.summon_def(rule.unit).template.name_zh
        except KeyError:
            name = rule.unit
        text = f"你倒下時，在原地留下{name}（接替你的行動順序），持續 {rule.duration} 輪"
    return f"規則改變「{rule.name_zh}」：{text}"


def _rule_change(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return rule_change_text(lib, spec.rule or "")


def activation_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """常駐類傳說的啟動方式（Phase 3D-6）；其他技能為 ``None``。"""
    if skill.activation is None:
        return None
    core = library.ruleset.core
    head = f"花 AP {core.legendary_activation_ap} ＋ 源力 {skill.cost.source} 啟動"
    if skill.activation == "battle":
        return f"整場：{head}，本場剩餘時間有效"
    return f"限時：{head}，持續 {core.legendary_timed_rounds} 輪"


def _branch_effect_text(lib: ContentLibrary, skill: SkillDef, sub: EffectSpec) -> str:
    """賭注分支或失手反噬的一個效果（Phase 3D-7a）：倍率、自傷與一般效果（含對象）。"""
    if sub.type == DAMAGE_MULTIPLIER:
        assert sub.damage_multiplier_permille is not None
        return f"本次傷害 ×{sub.damage_multiplier_permille / 1000:g}"
    if sub.type == SELF_DAMAGE_OF_HIT:
        assert sub.self_damage_permille_of_hit is not None
        return f"你受到本次傷害的 {sub.self_damage_permille_of_hit / 10:g}%（不致命）"
    return effect_summary(lib, skill, sub)


def branch_text(
    lib: ContentLibrary, skill: SkillDef, effects: tuple[EffectSpec, ...] | None
) -> str:
    """賭注一個分支的一句話；沒有效果為「沒有額外效果」。"""
    if not effects:
        return "沒有額外效果"
    return "、".join(_branch_effect_text(lib, skill, sub) for sub in effects)


def _gamble(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.chance_permille is not None
    win = f"{spec.chance_permille / 10:g}%：{branch_text(lib, skill, spec.win)}"
    lose = f"{(1000 - spec.chance_permille) / 10:g}%：{branch_text(lib, skill, spec.lose)}"
    return f"賭注（命中後擲 d1000）——{win}｜{lose}"


def miss_text(lib: ContentLibrary, skill: SkillDef) -> str | None:
    """失手反噬（``cost.on_miss``，Phase 3D-7a）的一句話；沒有為 ``None``。"""
    if not skill.cost.on_miss:
        return None
    parts: list[str] = []
    for sub in skill.cost.on_miss:
        if sub.type == "apply_status" and sub.status is not None:
            name = lib.ruleset.status_def(sub.status).name_zh
            turns = f" {sub.duration} 回合" if sub.duration else ""
            parts.append(f"你獲得「{name}」{turns}")
        else:
            parts.append(f"{_damage(lib, skill, sub)}（對自己，不致命）")
    return "失手（含自然 1）時：" + "、".join(parts)


def _charge_through(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    after = f"擊倒（{scaling_label(skill)}對抗）" if spec.on_hit == "knock_prone" else "推到路徑旁"
    return (
        f"沿直線衝向目標格：沿途每個敵人各擲命中，命中受 {spec.dice} 物理傷害並{after}"
        "（隊友讓路；不觸發藉機攻擊；目標格的敵人背後被擋住時另受一次撞擊）"
    )


def _swap(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    check = f"（{scaling_label(skill)}對抗）" if spec.affects == "enemies" else ""
    return "與目標交換位置" + check


def _teleport_target(lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    core = lib.ruleset.core
    lethal = core.teleport_enemy_resist_bonus + core.teleport_lethal_resist_bonus
    return (
        f"把一個單位傳送到落點（友方必定成功；敵方{scaling_label(skill)}對抗，目標抵抗 "
        f"+{core.teleport_enemy_resist_bonus}；落點是致命地形時抵抗 +{lethal}，Boss 免疫）"
    )


def _swap_any(_lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    return f"讓射程內的兩個單位互換位置（含敵人時每個敵人各過{scaling_label(skill)}對抗）"


def _apply_status(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.status is not None
    turns = f" {spec.duration} 回合" if spec.duration else ""
    return f"狀態「{lib.ruleset.status_def(spec.status).name_zh}」{turns}"


def _create_surface(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.surface is not None
    turns = f" {spec.duration} 回合" if spec.duration else ""
    return f"生成「{lib.ruleset.surface_def(spec.surface).name_zh}」表面{turns}"


def _create_obstacle(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.object is not None
    turns = f"，{spec.duration} 回合後消失" if spec.duration else ""
    return f"生成「{lib.ruleset.object_def(spec.object).name_zh}」{turns}"


def _inscribe(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    rounds = spec.duration or lib.ruleset.core.rune_default_rounds
    return (
        f"在影響格刻下你專屬的「{rune_name(spec.element, spec.tag)}」，持續 {rounds} 輪"
        "（符文本身沒有效果，敵我都看得到；之後由你的技能讀取）"
    )


def _sacrifice_summon(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None and spec.radius is not None
    scope = "只有它所在的格子" if spec.radius == 0 else f"{spec.radius} 格內"
    if spec.element is not None:
        return (
            f"獻祭你的一個召喚物，在它的位置爆炸：{scope}的敵人自動命中，受到"
            f" {_dice(spec.dice)}＋{scaling_label(skill)}加成的{spec.element.display_name}傷害"
        )
    return (
        f"獻祭你的一個召喚物，在它的位置化為治療：{scope}的友方回復"
        f" {_dice(spec.dice)}＋{scaling_label(skill)}加成的 HP"
    )


def _detonate_runes(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    element = f"{spec.element.display_name}" if spec.element is not None else "符文元素的"
    return (
        f"引爆影響範圍內你自己的符文：每格移除符文，並對站在上面的單位自動命中，造成"
        f" {_dice(spec.dice)}＋{scaling_label(skill)}加成的{element}傷害"
    )


def _destroy_object(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "摧毀可破壞的物件"


def _overload_text(lib: ContentLibrary, stack: StackDef) -> str:
    """超載層數（Phase 3D-7b）的說明：每層加成與到門檻時的反噬。"""
    overload = stack.overload
    assert overload is not None
    backlash: list[str] = []
    for sub in overload.backlash:
        if sub.type == "damage":
            assert sub.dice is not None and sub.element is not None
            backlash.append(f"受到 {_dice(sub.dice)} {sub.element.display_name}傷害（不致命）")
        else:
            assert sub.status is not None
            backlash.append(f"獲得「{lib.ruleset.status_def(sub.status).name_zh}」")
    return (
        f"。超載：你帶「{overload.tag}」標籤的技能每層傷害"
        f" +{overload.per_stack_damage_permille / 10:g}%；"
        f"累積到 {overload.threshold} 層時，你{'、'.join(backlash)}並清空層數"
    )


def _stack(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.stack is not None
    stack = lib.ruleset.stack_def(spec.stack)
    if spec.type == "add_stack":
        text = f"累積 {spec.amount or 1} 層「{stack.name_zh}」（上限 {stack.max}）"
        return text + (_overload_text(lib, stack) if stack.overload is not None else "")
    assert spec.per_stack_permille is not None
    need = f"（至少 {skill.cost.stacks} 層才能施放）" if skill.cost.stacks else ""
    return f"消耗全部「{stack.name_zh}」，每層使本技能傷害 +{spec.per_stack_permille / 10:g}%{need}"


def _consume_status(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.status is not None and spec.then
    name = lib.ruleset.status_def(spec.status).name_zh
    then = "、".join(_effect_core(lib, skill, sub) for sub in spec.then)
    text = f"消耗目標身上的「{name}」，然後{then}"
    if spec.scale == "remaining_rounds":
        text += "（骰數 × 剩餘回合）"
    elif spec.scale == "stacks":
        assert spec.stack is not None
        text += f"（骰數 × 同時消耗的「{lib.ruleset.stack_def(spec.stack).name_zh}」層數）"
    if spec.splash is not None:
        text += f"，並波及周圍 {spec.splash} 格內的敵人"
    return text + "；目標沒有該狀態則不生效"


_ZONE_WHEN = {
    "enter": "進入區域時",
    "turn_start": "在區域內開始回合時",
    "both": "進入區域或在區域內開始回合時",
}
_ZONE_WHO = {"enemies": "敵人", "allies": "友方", "all": "任何單位"}
_DIRECTION_WORD = "施放方向"


def _zone(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """持續區域（Phase 3D-5）的一句話。"""
    assert spec.when is not None and spec.effects
    if spec.anchor == "caster":
        anchor = "跟著你移動"
    elif spec.anchor == "moving":
        anchor = f"每次環境回合向{_DIRECTION_WORD}前進 {spec.speed or 1} 格"
    else:
        anchor = "固定不動"
    who = _ZONE_WHO[spec.affects or "enemies"]
    then = "、".join(_effect_core(lib, skill, sub) for sub in spec.effects)
    text = f"建立持續 {spec.duration} 輪的區域（{anchor}）：{who}{_ZONE_WHEN[spec.when]}，{then}"
    if spec.surface is not None:
        text += f"；區域經過的格子留下「{lib.ruleset.surface_def(spec.surface).name_zh}」"
    return text


def _place_trap(_lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    trap = skill.trap
    assert trap is not None
    trigger = (
        f"敵人踩上時觸發（{trap.rounds} 輪後消失）"
        if trap.trigger == "enter"
        else (f"{trap.rounds} 輪後引爆")
    )
    shape = {"single": "該格", "cross": "十字範圍", "square3": "3×3 範圍"}[trap.shape]
    return f"放置隱藏陷阱：{trigger}，以{shape}結算其餘效果"


def _grant_ap(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return f"立刻獲得 {spec.amount or 1} AP（不超過本回合上限，每輪限一次）"


def _reset_cooldown(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    which = "全部技能" if spec.which == "all" else f"帶「{spec.tag}」標籤的技能"
    return f"{which}的冷卻歸零（花源力的技能除外）"


def _cheat_death(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    status = lib.ruleset.status_def(CHEAT_DEATH_STATUS)
    turns = spec.duration or status.duration
    return f"狀態「{status.name_zh}」{turns} 回合：受到致命傷害時 HP 留在 1（墜落與致命地形除外）"


def _redirect_damage(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    status = lib.ruleset.status_def(REDIRECT_STATUS)
    turns = spec.duration or status.duration
    share = (spec.permille or 0) / 10
    return f"狀態「{status.name_zh}」{turns} 回合：目標受到的傷害有 {share:g}% 轉給施放者"


def _copy_skill(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return (
        "立即複製施放本輪最後施放的主動技能（自己選目標，不扣法力與 AP、不進冷卻；"
        "傳說與改寫規則型除外）"
    )


def _extra_reaction(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return f"本輪反應次數 +{spec.amount or 1}（到下一輪開始）"


def _restore_resource(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    amount = spec.amount or 1
    if spec.resource == "cooldown":
        return f"目標所有技能的冷卻 −{amount}（花源力的技能除外）"
    return f"回復 {amount} 點法力（不超過上限）"


def _steal_buff(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "奪取目標身上一個增益（剩餘回合最長者），以相同的剩餘回合施加到自己身上"


def _dispel(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    if spec.count == "all":
        return "驅散目標身上的全部增益"
    return "驅散目標身上一個增益（剩餘回合最長者）"


def _reveal(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return (
        f"揭露範圍內的敵人：移除隱蔽，{spec.duration} 回合內不能再隱蔽；範圍內的敵方陷阱對你的"
        "陣營顯示（不擲命中）"
    )


def _revive(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return (
        f"讓射程內倒下的友方以 {(spec.hp_permille or 0) / 10:g}% 最大 HP 站起來"
        "（站回原位置，被占用時站到附近最近的空格；每個單位每場最多一次，召喚物不能被復活）"
    )


def _grant_skill(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.skill is not None
    granted = lib.ruleset.skill_def(spec.skill)
    return (
        f"讓目標暫時獲得技能「{granted.name_zh}」，持續 {spec.duration} 輪"
        "（在目標的回合結束時倒數；不佔技能欄位，重新施放只刷新輪數）"
    )


def _delayed_damage(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None and spec.element is not None
    where = "，只波及目標自己" if not spec.radius else f"，波及半徑 {spec.radius} 格內的所有單位"
    return (
        f"在目標身上綁定時炸彈（{lib.ruleset.status_def('time_bomb').name_zh}）：{spec.rounds} 次"
        f"環境回合後在目標當下的位置爆炸{where}（敵我不分），{_dice(spec.dice)}＋"
        f"{scaling_label(skill)}加成的{spec.element.display_name}傷害；目標倒下時立即爆炸；"
        "可被淨化移除"
    )


def _hurl_object(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    text = f"把 {spec.range} 格內的可推動物件丟到落點，落點單位受 {_dice(spec.dice)} 物理傷害"
    if spec.knock_prone:
        text += f"並擊倒（{scaling_label(skill)}對抗）"
    return text + "；油桶落地爆炸、可破壞的物件碎掉"


def _topple(lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    core = lib.ruleset.core
    return (
        f"推倒石柱或枯樹，往遠離自己的方向壓住 {core.topple_length} 格"
        f"（{_dice(core.topple_damage_dice)} 物理傷害並倒地）"
    )


def _terrain(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    verb = "抬高" if spec.type == "raise_terrain" else "降低"
    return f"{verb}地形 {spec.amount or 1} 層"


_EFFECT_TEXT: dict[str, _EffectText] = {
    "damage": _damage,
    "heal": _heal,
    "push": _push_pull,
    "pull": _push_pull,
    "knock_prone": _knock_prone,
    "teleport": _teleport,
    "dash": _dash,
    "leap": _leap,
    "shadowstep": _shadowstep,
    "charge_through": _charge_through,
    "summon": _summon,
    "swap": _swap,
    "teleport_target": _teleport_target,
    "swap_any": _swap_any,
    "apply_status": _apply_status,
    "create_surface": _create_surface,
    "create_obstacle": _create_obstacle,
    "destroy_object": _destroy_object,
    "inscribe": _inscribe,
    "detonate_runes": _detonate_runes,
    "sacrifice_summon": _sacrifice_summon,
    "add_stack": _stack,
    "consume_stack": _stack,
    "consume_status": _consume_status,
    "place_trap": _place_trap,
    "raise_terrain": _terrain,
    "lower_terrain": _terrain,
    "grant_ap": _grant_ap,
    "reset_cooldown": _reset_cooldown,
    "cheat_death": _cheat_death,
    "redirect_damage": _redirect_damage,
    "copy_skill": _copy_skill,
    "extra_reaction": _extra_reaction,
    "restore_resource": _restore_resource,
    "steal_buff": _steal_buff,
    "dispel": _dispel,
    "reveal": _reveal,
    "revive": _revive,
    "delayed_damage": _delayed_damage,
    "grant_skill": _grant_skill,
    "hurl_object": _hurl_object,
    "topple": _topple,
    "zone": _zone,
    "rule_change": _rule_change,
    "gamble": _gamble,
}


def _effect_core(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    describe = _EFFECT_TEXT.get(spec.type)
    if describe is None:
        return library.ruleset.primitive_def(spec.type).name_zh
    return describe(library, skill, spec)


def _surface_names(library: ContentLibrary, ids: tuple[str, ...]) -> str:
    return "／".join(f"「{library.ruleset.surface_def(Surface(i)).name_zh}」" for i in ids)


def variant_condition_text(library: ContentLibrary, when: VariantWhen) -> str:
    """戰場變奏（Phase 3-25a）的條件，例如「施放者站在「水」上」。"""
    if when.caster_surface is not None:
        return f"施放者站在{_surface_names(library, when.caster_surface)}上"
    if when.target_surface is not None:
        return f"目標點在{_surface_names(library, when.target_surface)}上"
    if when.caster_high_ground is not None:
        return "施放者比目標點高至少 1 層"
    return "施放者身旁（八方向）有牆壁或擋路物件"


def variant_change_text(library: ContentLibrary, skill: SkillDef, variant: VariantSpec) -> str:
    """戰場變奏（Phase 3-25a）的替換內容，例如「形狀改為直線（3 格）；傷害改為雷電」。"""
    form = skill.variant_form(variant.id)
    parts: list[str] = []
    if variant.shape is not None or variant.range_delta is not None:
        delta = "" if variant.range_delta is None else f"射程 {variant.range_delta:+d}，"
        parts.append(f"{delta}形狀為{skill_shape_text(library, form)}")
    if variant.replace_effect is not None:
        swap = variant.replace_effect
        text = effect_summary(library, form, form.effects[swap.index])
        parts.append(f"第 {swap.index + 1} 個效果改為{text}")
    if variant.add_effect is not None:
        parts.append(f"加上{effect_summary(library, form, form.effects[-1])}")
    if variant.element is not None:
        parts.append(f"傷害改為{variant.element.display_name}")
    return "；".join(parts)


def effect_summary(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """一個效果的一句話，含對象，例如「2d6＋智力加成的火焰傷害（敵方）」。"""
    primitive = library.ruleset.primitive_def(spec.type)
    affects = spec.affects or default_affects(primitive)
    text = _effect_core(library, skill, spec)
    if spec.type not in ("summon", "zone", "rule_change", "gamble"):  # 對象已寫在句中
        text += f"（{_AFFECTS[affects]}）"
    if spec.condition is not None:
        text += f"，若{condition_summary(library, spec.condition)}"
    return text


def condition_summary(library: ContentLibrary, condition: ConditionSpec) -> str:
    """條件的一句話（不含「若」或「使用條件」前綴）。"""
    rules = library.ruleset
    return condition_text(
        condition,
        status_name=lambda sid: rules.status_def(sid).name_zh,
        surface_name=lambda surface: rules.surface_def(surface).name_zh,
    )


# ---------------------------------------------------------------------------
# 修正規則（Phase 3C-2）
# ---------------------------------------------------------------------------


def _targets_text(target: ModifierTarget) -> str:
    """套用對象，例如「你的所有攻擊」「推擊、帶標籤 push 的技能」。"""
    parts: list[str] = []
    if target.all_attacks:
        parts.append("你的所有攻擊（普攻與攻擊技能）")
    if target.all_skills:
        parts.append("你施放的所有技能")
    parts += [_ACTION_TEXT[a] for a in target.actions if not (a == "attack" and target.all_attacks)]
    if target.skill_tags and not target.all_skills:
        parts.append(f"帶標籤 {'／'.join(target.skill_tags)} 的技能")
    return "、".join(parts)


_SIMPLE_CHANGE_TEXT = {
    "hit_bonus": "命中 {value:+d}",
    "cooldown_delta": "命中後該技能的冷卻 {value:+d} 回合（最少 0）",
    "ap_delta": "AP {value:+d}（最少 1）",
    "range_delta": "射程 {value:+d}",
    "grant_pierce": "遠程單體與直線技能獲得穿透（無視半掩護，穿過木製物件）",
    "area_delta": "範圍型形狀的大小 +{value}（直線與錐形的長度、環形與光環的半徑，有上限）",
    "allow_self_target": "治療、護盾、增益類技能的影響範圍也包含自己",
    "summon_attack_dice": "召喚物的攻擊傷害骰 +{value} 顆",
}
"""只有一個整數的改變：格式字串（``value`` 為改變的數值）。"""


def _shape_to_text(library: ContentLibrary, target: str) -> str:
    """``shape_to`` 的說明：列出 ``skill_shapes.yaml`` 的轉換表中轉成 ``target`` 的原形狀。"""
    shapes = library.ruleset.shapes.by_id()
    sources = [c for c in library.ruleset.shapes.conversions if c.to == target]
    names = "、".join(shapes[c.from_shape].name_zh for c in sources)
    return f"{names}形狀的技能轉為{shapes[target].name_zh}（效果原語不支援新形狀的技能不轉）"


def _change_text(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    change = rule.change
    kind = change.kind
    simple = _SIMPLE_CHANGE_TEXT.get(kind)
    if simple is not None:
        return simple.format(value=getattr(change, kind))
    if change.damage_permille is not None:
        return f"傷害 {change.damage_permille / 10:+g}%"
    if change.heal_permille is not None:
        return f"你的治療量 {change.heal_permille / 10:+g}%"
    if change.summon_hp_permille is not None:
        return f"你召喚的召喚物最大 HP +{change.summon_hp_permille / 10:g}%"
    if change.push_distance_delta is not None:
        cap = library.ruleset.core.max_displace_distance
        return (
            f"推擊與拉扯距離 +{change.push_distance_delta} 格"
            f"（最多 {cap} 格，超過的每格改為一次撞擊傷害）"
        )
    return _other_change_text(library, skill, rule)


def _other_change_text(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    change = rule.change
    if change.add_element is not None:
        return f"物理傷害改為{change.add_element.display_name}（已有元素的不變）"
    if change.add_tags is not None:
        return f"獲得標籤 {'、'.join(change.add_tags)}"
    if change.shape_to is not None:
        return _shape_to_text(library, change.shape_to)
    assert change.on_hit_effects is not None
    carrier = on_hit_carrier(skill, change.on_hit_effects)
    effects = "；".join(effect_summary(library, carrier, e) for e in carrier.effects)
    return f"命中後：{effects}"


def modifier_summary(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    """一條修正規則的一句話，例如「你的所有攻擊（普攻與攻擊技能）：傷害 +10%，若目標帶有狀態
    「燃燒」」。"""
    text = f"{_targets_text(rule.applies_to)}：{_change_text(library, skill, rule)}"
    if rule.condition is not None:
        text += f"，若{condition_summary(library, rule.condition)}"
    return text


def cost_parts(library: ContentLibrary, skill: SkillDef, *, with_ap: bool = True) -> list[str]:
    """代價的各段文字（AP、法力、HP、施放後狀態、冷卻、每場次數）。"""
    cost = skill.cost
    ap = skill_ap(library, skill)
    parts = [f"AP {ap}"] if with_ap and ap is not None else []
    if cost.mana:
        parts.append(f"法力 {cost.mana}")
    if cost.hp_percent:
        parts.append(f"HP {cost.hp_percent / 10:g}%")
    if cost.self_status:
        name = library.ruleset.status_def(cost.self_status.status).name_zh
        parts.append(f"施放後自身{name} {cost.self_status.duration} 回合")
    if cost.cooldown:
        parts.append(f"冷卻 {cost.cooldown} 回合")
    if cost.uses_per_battle:
        parts.append(f"每場 {cost.uses_per_battle} 次")
    if cost.source:
        parts.append(f"源力 {cost.source}")
    miss = miss_text(library, skill)
    if miss is not None:
        parts.append(miss)
    return parts


def skill_ap(library: ContentLibrary, skill: SkillDef) -> int | None:
    """技能列顯示的 AP：主動技能的 ``ap_cost``、修正型傳說的啟動 AP（Phase 3D-6）；被動等為
    ``None``。"""
    if skill.ap_cost is not None:
        return skill.ap_cost
    if skill.is_activatable:
        return library.ruleset.core.legendary_activation_ap
    return None


def cost_summary(library: ContentLibrary, skill: SkillDef, *, with_ap: bool = True) -> str:
    """代價的一句話，例如「AP 2，法力 3，冷卻 2 回合」。"""
    return "，".join(cost_parts(library, skill, with_ap=with_ap))


# ---------------------------------------------------------------------------
# 技能卡片
# ---------------------------------------------------------------------------


REACTION_TIMING_TEXT: dict[str, str] = {
    "hit_by_melee": "被近戰攻擊命中時",
    "hit_by_attack": "被攻擊命中時",
    "ally_hit_adjacent": "相鄰的友方被攻擊命中時",
    "enemy_leaves_adjacent": "相鄰的敵人離開時",
    "hit_by_spell": "被法術命中時（傷害結算之前）",
    "ally_downed": "友方倒下時",
    "enemy_enters_adjacent": "敵人走進相鄰格時",
    "ally_targeted": "相鄰的友方被敵人瞄準時（命中判定之前）",
}
"""反應技觸發事件的中文說明（Phase 3C-6a：技能卡片的「反應時機」一行）。"""


def timing_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """技能卡片的時機一行：反應技為「反應時機：…」、被動為「觸發時機：…」；其他技能為 ``None``。"""
    if skill.reaction is not None:
        event = skill.reaction.event
        return f"反應時機：{REACTION_TIMING_TEXT.get(event, event)}"
    if skill.trigger is not None:
        return f"觸發時機：{library.ruleset.trigger_def(skill.trigger.event).name_zh}"
    return None


class KeywordRef(BaseModel):
    """技能卡上的一個關鍵字（Phase 3-24b1）：代碼、顯示名稱與一句話說明（給部件說明框）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    description_zh: str
    variant: bool = False
    """只有特定地形的戰場變奏型態才有這個關鍵字（Phase 3-25b；技能卡標「（特定地形）」）。"""


class SkillCardKeywords(BaseModel):
    """技能製造與利用的關鍵字（Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1；由原語、條件、觸發
    自動推導）。技能卡顯示「製造：點燃｜利用：倒地」。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    makes: tuple[KeywordRef, ...] = ()
    uses: tuple[KeywordRef, ...] = ()


def keywords_card(library: ContentLibrary, found: SkillKeywords) -> SkillCardKeywords:
    """推導結果（關鍵字 ID）附上顯示名稱。"""
    defs = library.keywords.by_id()

    def ref(keyword_id: str) -> KeywordRef:
        d = defs[keyword_id]
        return KeywordRef(
            id=d.id,
            name_zh=d.name_zh,
            description_zh=d.description_zh,
            variant=keyword_id in found.variant,
        )

    return SkillCardKeywords(
        makes=tuple(ref(k) for k in found.makes), uses=tuple(ref(k) for k in found.uses)
    )


def skill_card_keywords(library: ContentLibrary, skill: SkillDef) -> SkillCardKeywords:
    """``skill`` 的製造與利用關鍵字（附顯示名稱）。"""
    return keywords_card(library, derive_keywords(skill, library.keywords))


def draft_card_keywords(library: ContentLibrary, draft: Mapping[str, Any]) -> SkillCardKeywords:
    """組到一半的技能草稿（技能工坊）目前製造與利用的關鍵字。"""
    return keywords_card(library, derive_draft_keywords(draft, library.keywords))


class SkillVariantCard(BaseModel):
    """技能卡上的一個戰場變奏型態（Phase 3-25b，6.24）：型態名、條件與替換內容的中文說明、
    型態自己的圖示（技能列在這個型態生效時換成它）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    condition: str
    """條件的一句話，例如「施放者站在「水」上」。"""
    condition_kind: str
    """``caster_surface``、``caster_high_ground``、``caster_adjacent_blocker``、``target_surface``。"""
    target_dependent: bool
    """條件看目標點（居高、目標點表面）：施放前要看預覽才知道生效哪個型態。"""
    change: str
    """替換內容的一句話，例如「形狀為直線（大小 3）；傷害改為雷電」。"""
    icon: SkillIcon


class SkillCard(BaseModel):
    """一張技能卡片的顯示內容（繁體中文文字，給網頁技能卡片用）。

    ``*_id`` 與 ``scaling_attrs`` 是對應的英文代碼（Phase 3-2；給前端上色、排序與篩選用）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    skeleton: str
    tier: int
    rank: int
    rarity: str
    kind: str
    category: str
    weapon_req: str
    scaling: str
    ap_cost: int | None
    cost: tuple[str, ...]
    """代價各段文字（含 AP）。"""
    source_cost: int | None
    """花費的源力（``cost.source``，傳說技能，Phase 3C-4a）；沒有為 ``None``。"""
    shape: str
    condition: str | None
    effects: tuple[str, ...]
    modifiers: tuple[str, ...]
    """修正規則的中文描述（Phase 3C-2；只有修正技能有）。"""
    activation: str | None = None
    """常駐類傳說的啟動方式（Phase 3D-6），例如「限時：花 AP 1 ＋ 源力 1 啟動，持續 3 輪」。"""
    activation_id: str | None = None
    """``timed``／``battle``（Phase 3D-6）；其他技能為 ``None``。"""
    mastery: str | None
    tags: tuple[str, ...]
    concept: str
    cast_flavor: str
    rarity_id: str
    kind_id: str
    category_id: str
    weapon_req_id: str
    scaling_attrs: tuple[str, ...]
    """縮放屬性的代碼（主屬性在前；雙屬性縮放時兩個）。"""
    mastery_id: str | None
    timing: str | None = None
    """反應技的反應時機、被動的觸發時機一行（Phase 3C-6a）；其他技能為 ``None``。"""
    effect_ids: tuple[str, ...] = ()
    """效果原語的代碼，依技能內的順序（Phase 3D-8d：網頁用來分辨兩段選取的種類，例如一般瞬步
    ``shadowstep`` 與傳送他人 ``teleport_target`` 都是「單位 → 落點」）。"""
    followup: str | None = None
    """複合技能（Phase 3F-3a）第二段的一句話（:func:`followup_text`）；其他技能為 ``None``。"""
    followup_when: str | None = None
    """複合技能第二段的種類（``followup.when``，Phase 3F-4b；網頁只有「位移 → 動作」用兩段選取，
    其他種類照第一段選取）；其他技能為 ``None``。"""
    icon: SkillIcon
    """組裝式技能圖示的資料（Phase 3-17，:func:`trpg.narrative.skill_icon.skill_icon`）。"""
    keywords: SkillCardKeywords = SkillCardKeywords()
    """製造與利用的關鍵字（Phase 3-24b1，:func:`skill_card_keywords`）。"""
    variants: tuple[SkillVariantCard, ...] = ()
    """戰場變奏的所有型態（Phase 3-25b；資料順序，多個成立時取前面的）；沒有變奏為空。"""
    growth: SkillLevelInfo | None = None
    """技能等級的顯示資料（Phase 3-26a）：只有一輪中主角持有（裝備或備用）的主動技能卡片帶它，
    由 ``trpg.api.run_presenter`` 帶入實際等級；候選、技能庫與工坊的卡片為 ``None``。"""


def _variant_card(
    library: ContentLibrary, skill: SkillDef, variant: VariantSpec
) -> SkillVariantCard:
    return SkillVariantCard(
        id=variant.id,
        name_zh=variant.name_zh,
        condition=variant_condition_text(library, variant.when),
        condition_kind=variant.when.kind,
        target_dependent=variant.when.target_dependent,
        change=variant_change_text(library, skill, variant),
        icon=skill_icon(skill.variant_form(variant.id)),
    )


def skill_card(
    library: ContentLibrary, skill: SkillDef, *, mastery_active: bool | None = None
) -> SkillCard:
    """``skill`` 的卡片內容；``mastery_active`` 見 :func:`mastery_text`。"""
    return SkillCard(
        id=skill.id,
        name_zh=skill.name_zh,
        skeleton=skill.skeleton,
        tier=skill.tier,
        rank=skill.rank,
        rarity=RARITY_TEXT[skill.rarity],
        kind=KIND_TEXT[skill.kind],
        category=CATEGORY_TEXT[skill.category],
        weapon_req=WEAPON_REQ_TEXT[skill.weapon_req],
        scaling=scaling_detail(skill),
        ap_cost=skill_ap(library, skill),
        cost=tuple(cost_parts(library, skill, with_ap=skill_ap(library, skill) is not None)),
        source_cost=skill.cost.source,
        shape=skill_shape_text(library, skill),
        condition=(
            None if skill.condition is None else condition_summary(library, skill.condition)
        ),
        effects=tuple(effect_summary(library, skill, e) for e in skill.effects),
        modifiers=tuple(modifier_summary(library, skill, r) for r in skill.modifiers),
        activation=activation_text(library, skill),
        activation_id=skill.activation,
        mastery=(None if skill.mastery is None else mastery_text(skill, active=mastery_active)),
        tags=tuple(skill.tags),
        concept=skill.narrative.concept,
        cast_flavor=skill.narrative.cast_flavor,
        rarity_id=skill.rarity,
        kind_id=skill.kind,
        category_id=skill.category,
        weapon_req_id=skill.weapon_req,
        scaling_attrs=tuple(
            a.value for a in (skill.scaling_attr, skill.secondary_scaling_attr) if a is not None
        ),
        mastery_id=skill.mastery,
        timing=timing_text(library, skill),
        effect_ids=tuple(e.type for e in skill.effects),
        followup=followup_text(library, skill),
        followup_when=None if skill.followup is None else skill.followup.when,
        icon=skill_icon(skill),
        keywords=skill_card_keywords(library, skill),
        variants=tuple(_variant_card(library, skill, v) for v in skill.variants),
    )
