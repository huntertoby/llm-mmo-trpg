"""技能的繁體中文描述（原在 ``trpg.cli.skills``，Phase 3-1 搬出，讓 CLI 與網頁技能卡片共用）。

- 形狀、縮放、專精、代價、條件與每個效果的一句話描述。
- 修正規則（Phase 3C-2，``kind: modifier``）的一句話描述（:func:`modifier_summary`）。
- :func:`skill_card` 把一個技能整理成 :class:`SkillCard`（pydantic，可直接當 API 回應）。
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import Dice
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    CHEAT_DEATH_STATUS,
    REDIRECT_STATUS,
    ConditionSpec,
    EffectSpec,
    ModifierSpec,
    ModifierTarget,
    ShapeSpec,
    SkillDef,
    condition_text,
    default_affects,
    on_hit_carrier,
)

__all__ = [
    "CATEGORY_TEXT",
    "KIND_TEXT",
    "RARITY_TEXT",
    "WEAPON_REQ_TEXT",
    "SkillCard",
    "condition_summary",
    "cost_parts",
    "cost_summary",
    "effect_summary",
    "mastery_text",
    "modifier_summary",
    "scaling_detail",
    "scaling_label",
    "shape_summary",
    "skill_card",
    "skill_shape_text",
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


def _damage(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    if skill.category == "spell":
        assert spec.dice is not None and spec.element is not None
        attr, element = scaling_label(skill), spec.element.display_name
        return f"{_dice(spec.dice)}＋{attr}加成的{element}傷害"
    permille = spec.multiplier_permille or 1000
    element = f"（{spec.element.display_name}）" if spec.element is not None else ""
    return f"武器傷害 ×{permille / 1000:g}{element}"


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


def _summon(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    try:
        summon = lib.ruleset.summon_def(spec.unit or "")
    except KeyError:
        name = spec.unit or "召喚物"
    else:
        template, weapon = summon.template, summon.weapon
        totem = template.totem
        if totem is not None:  # 圖騰（3D-4b）
            status = lib.ruleset.status_def(totem.status).name_zh
            return (
                f"在目標空格立起{template.name_zh}（HP {template.max_hp}），持續 {spec.duration} 輪"
                f"（緊接在你之後行動；不移動、不攻擊，每次行動開始時讓 {totem.radius} 格內的"
                f"友方獲得「{status}」{totem.duration} 回合）"
            )
        name = f"{template.name_zh}（HP {template.max_hp}，{weapon.name_zh}）"
    return f"在目標空格召喚{name}，持續 {spec.duration} 輪（緊接在你之後行動，由 AI 控制）"


def _charge_through(_lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    after = f"擊倒（{scaling_label(skill)}對抗）" if spec.on_hit == "knock_prone" else "推到路徑旁"
    return (
        f"沿直線衝到終點格：沿途每個敵人各擲命中，命中受 {spec.dice} 物理傷害並{after}"
        "（隊友讓路；不觸發藉機攻擊）"
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
    return f"生成「{lib.ruleset.object_def(spec.object).name_zh}」"


def _destroy_object(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "摧毀可破壞的物件"


def _stack(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.stack is not None
    stack = lib.ruleset.stack_def(spec.stack)
    if spec.type == "add_stack":
        return f"累積 {spec.amount or 1} 層「{stack.name_zh}」（上限 {stack.max}）"
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
    "charge_through": _charge_through,
    "summon": _summon,
    "swap": _swap,
    "teleport_target": _teleport_target,
    "swap_any": _swap_any,
    "apply_status": _apply_status,
    "create_surface": _create_surface,
    "create_obstacle": _create_obstacle,
    "destroy_object": _destroy_object,
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
    "hurl_object": _hurl_object,
    "topple": _topple,
}


def _effect_core(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    describe = _EFFECT_TEXT.get(spec.type)
    if describe is None:
        return library.ruleset.primitive_def(spec.type).name_zh
    return describe(library, skill, spec)


def effect_summary(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """一個效果的一句話，含對象，例如「2d6＋智力加成的火焰傷害（敵方）」。"""
    primitive = library.ruleset.primitive_def(spec.type)
    affects = spec.affects or default_affects(primitive)
    text = _effect_core(library, skill, spec)
    if spec.type != "summon":  # 召喚的對象是選定的空格，不寫「（自己）」（3D-4b）
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
    parts = [f"AP {skill.ap_cost}"] if with_ap else []
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
    return parts


def cost_summary(library: ContentLibrary, skill: SkillDef, *, with_ap: bool = True) -> str:
    """代價的一句話，例如「AP 2，法力 3，冷卻 2 回合」。"""
    return "，".join(cost_parts(library, skill, with_ap=with_ap))


# ---------------------------------------------------------------------------
# 技能卡片
# ---------------------------------------------------------------------------


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
        ap_cost=skill.ap_cost,
        cost=tuple(cost_parts(library, skill, with_ap=skill.ap_cost is not None)),
        source_cost=skill.cost.source,
        shape=skill_shape_text(library, skill),
        condition=(
            None if skill.condition is None else condition_summary(library, skill.condition)
        ),
        effects=tuple(effect_summary(library, skill, e) for e in skill.effects),
        modifiers=tuple(modifier_summary(library, skill, r) for r in skill.modifiers),
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
    )
