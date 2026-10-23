"""召喚物的說明（Phase 3-41a，說明整修清單第 1 節）：全部由召喚物範本、``core.yaml`` 的
``summon_infusions`` 與規則數值產生，和引擎同一個來源。

- :func:`summon_card_hp`：技能卡顯示的 HP，用引擎生成召喚物時的同一個函式
  （:func:`trpg.content.summons.summon_scaled_hp`／:func:`~trpg.content.summons.summon_spec_hp`），
  以 1 級、縮放屬性修正 0 的施放者計算。
- :func:`summon_innate_lines`：自帶能力（固有灌注、命中特性、纏繞、自爆、高台、光環、脈動）。
- :func:`summon_behavior_lines`：行為（不移動、不攻擊、預設模式、AI 模式）。
- :func:`summon_info`：技能卡可展開的「召喚物資訊」小卡（:class:`SummonInfoCard`）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import Dice, SummonHitRule, UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.rules import SummonInfusion
from trpg.content.skills import EffectSpec, SkillDef
from trpg.content.summons import SummonDef, summon_scaled_hp, summon_spec_hp
from trpg.engine.ids import BLOCKS_SIGHT_TAG, CONCEALED, IMMOVABLE, PRONE
from trpg.engine.weapon_traits import TRIP_ATTR

__all__ = [
    "SummonInfoCard",
    "infusion_hint",
    "infusion_phrases",
    "summon_acts",
    "summon_attack_text",
    "summon_behavior_lines",
    "summon_card_hp",
    "summon_defense_text",
    "summon_info",
    "summon_innate_lines",
]

_MODE_TEXT = {"guard": "守護我", "follow": "跟隨", "hold": "待命"}
"""召喚物模式的中文名（和戰鬥紀錄、召喚物面板同一套用詞）。"""

_HIT_WHEN = {
    "always": "普攻命中時",
    "target_in_water": "普攻命中站在水上的目標時",
    "self_in_water": "自己站在水上時，普攻命中後",
}


def _dice(dice: Dice, flat: int = 0) -> str:
    text = f"{dice.count}d{dice.sides}"
    return f"{text}＋{flat}" if flat else text


def _status(lib: ContentLibrary, status_id: str) -> str:
    return lib.ruleset.status_def(status_id).name_zh


def summon_card_hp(
    lib: ContentLibrary,
    summon: SummonDef,
    spec: EffectSpec | None = None,
    *,
    chosen_infusion: str | None = None,
) -> int:
    """技能卡上的召喚物最大 HP：和引擎同一個算法（定位係數、固有灌注與分歧進化的 HP），以 1 級、
    縮放屬性修正 0、沒有修正規則與裝備的施放者計算；``chosen_infusion`` 是施放時選的灌注（技能卡
    不選，測試用來和引擎生成的值對照）。"""
    core = lib.ruleset.core
    template = summon.template
    table = core.summon_infusions
    bonus = None if spec is None else spec.infusion
    keywords = dict.fromkeys(k for k in (template.innate, bonus, chosen_infusion) if k in table)
    hp = summon_scaled_hp(
        core,
        template,
        core.template_max_hp(template),
        infusion_hp_permille=sum(table[k].hp_permille for k in keywords if k is not None),
    )
    if spec is None:
        return hp
    return summon_spec_hp(
        hp, max_hp_permille=spec.max_hp_permille, power_permille=spec.power_permille
    )


def infusion_phrases(
    lib: ContentLibrary, infusion: SummonInfusion, *, attacks: bool = True
) -> list[str]:
    """一個灌注關鍵字的效果（``summon_infusions``），例：「普攻命中時施加「燃燒」2 回合」。
    ``attacks`` 為假（不攻擊的召喚物）時只列召喚當下生效的部分（隱蔽、HP）。"""
    parts = _attack_phrases(lib, infusion) if attacks else []
    if infusion.conceal_rounds:
        parts.append(f"召喚時獲得「{_status(lib, CONCEALED)}」{infusion.conceal_rounds} 回合")
    if infusion.hp_permille:
        parts.append(f"最大 HP +{infusion.hp_permille / 10:g}%")
    return parts


def _attack_phrases(lib: ContentLibrary, infusion: SummonInfusion) -> list[str]:
    parts: list[str] = []
    if infusion.status is not None:
        parts.append(f"普攻命中時施加「{_status(lib, infusion.status)}」{infusion.duration} 回合")
    if infusion.knockback:
        parts.append(f"普攻命中時把目標震退 {infusion.knockback} 格")
    if infusion.surface is not None:
        surface = lib.ruleset.surface_def(infusion.surface).name_zh
        parts.append(f"普攻命中時在目標格生成「{surface}」表面")
    if infusion.extra_damage is not None:
        element = infusion.extra_element.display_name
        parts.append(f"普攻命中時另加 {_dice(infusion.extra_damage)} {element}傷害")
    if infusion.trip:
        parts.append(
            f"普攻命中時絆倒目標使其「{_status(lib, PRONE)}」"
            f"（{TRIP_ATTR.display_name}對抗，每隻每輪 1 次）"
        )
    if infusion.height_permille:
        parts.append(f"站得比目標高時普攻傷害 +{infusion.height_permille / 10:g}%")
    return parts


def _hit_rule_text(lib: ContentLibrary, rule: SummonHitRule) -> str:
    parts: list[str] = []
    if rule.status is not None:
        parts.append(f"施加「{_status(lib, rule.status)}」{rule.duration} 回合")
    if rule.chain_targets:
        parts.append(
            f"攻擊沿水面連鎖到目標 {rule.chain_radius} 格內最多 {rule.chain_targets} 名其他敵人"
            f"（各受武器傷害 ×{rule.chain_permille / 1000:g}）"
        )
    return _HIT_WHEN[rule.when] + "，".join(parts)


def _pulse_lines(lib: ContentLibrary, template: UnitTemplate) -> list[str]:
    pulse = template.pulse
    if pulse is None:
        return []
    parts: list[str] = []
    if pulse.surface is not None:
        parts.append(f"在腳下生成「{lib.ruleset.surface_def(pulse.surface).name_zh}」表面")
    if pulse.heal_dice is not None or pulse.heal_flat:
        amount = (
            _dice(pulse.heal_dice, pulse.heal_flat) if pulse.heal_dice else str(pulse.heal_flat)
        )
        parts.append(f"治療 {pulse.heal_radius} 格內每個受傷的友方 {amount} HP（不含自己）")
    if pulse.shield_dice is not None or pulse.shield_flat:
        amount = (
            _dice(pulse.shield_dice, pulse.shield_flat)
            if pulse.shield_dice
            else str(pulse.shield_flat)
        )
        parts.append(f"給 HP 比例最低的友方 {amount} 點護盾（不含自己）")
    if pulse.pull_radius:
        parts.append(f"把 {pulse.pull_radius} 格內最近的一個敵人往自己拉近 1 格")
    return ["每次行動開始時：" + "；".join(parts)]


def summon_innate_lines(lib: ContentLibrary, summon: SummonDef) -> tuple[str, ...]:
    """召喚物自帶的能力（固有灌注、命中特性、纏繞、自爆、高台、光環、脈動），每項一句。"""
    template = summon.template
    rules = lib.ruleset
    lines: list[str] = []
    infusion = rules.core.summon_infusions.get(template.innate or "")
    if infusion is not None:
        lines += infusion_phrases(lib, infusion, attacks=summon_acts(template))
    lines += [_hit_rule_text(lib, rule) for rule in template.hit_rules]
    if template.snare is not None:
        snare = template.snare
        prone = f"並「{_status(lib, PRONE)}」" if snare.prone else ""
        lines.append(
            f"敵人進入相鄰格時纏住：施加「{_status(lib, snare.status)}」{snare.duration} 回合"
            f"{prone}（每輪 1 次）"
        )
    if template.detonate is not None:
        boom = template.detonate
        surface = (
            ""
            if boom.surface is None
            else f"，爆心周圍留下「{rules.surface_def(boom.surface).name_zh}」表面"
        )
        lines.append(
            f"和敵人相鄰或被打倒時自爆：{boom.radius} 格內的敵人受 {_dice(boom.dice, boom.flat)} "
            f"{boom.element.display_name}傷害{surface}，自己消失"
        )
    if template.platform is not None:
        lines.append(f"召喚時在旁邊升起 {template.platform.height} 層高台（消失時恢復）")
    if template.totem is not None:
        totem = template.totem
        lines.append(
            f"每次行動開始時：讓 {totem.radius} 格內的友方獲得「{_status(lib, totem.status)}」"
            f"{totem.duration} 回合"
        )
    lines += _pulse_lines(lib, template)
    if IMMOVABLE in template.tags:
        lines.append("不會被推動或傳送")
    if BLOCKS_SIGHT_TAG in template.tags:
        lines.append("擋住視線")
    return tuple(lines)


def summon_acts(template: UnitTemplate) -> bool:
    """召喚物會在自己的回合行動（移動或攻擊）：不是圖騰也不是 ``inert``。"""
    return template.totem is None and not template.inert


def summon_behavior_lines(lib: ContentLibrary, summon: SummonDef) -> tuple[str, ...]:
    """召喚物的行為：不移動、不攻擊（圖騰、``inert``）、預設模式與 AI 模式。"""
    template = summon.template
    if not summon_acts(template):
        return ("不移動、不攻擊（只有上面寫的自帶能力）",)
    lines: list[str] = []
    if template.speed == 0:
        lines.append("不移動；攻擊射程內的敵人")
    lines.append(f"預設模式「{_MODE_TEXT[template.default_mode]}」（可在召喚物面板切換）")
    profile = next((p for p in lib.ai_profiles.profiles if p.id == template.ai_profile), None)
    if profile is not None:
        lines.append(f"AI：{profile.name_zh}，{profile.description_zh}")
    return tuple(lines)


def summon_attack_text(summon: SummonDef) -> str:
    """召喚物的普攻（武器名、傷害骰、元素、射程）；不攻擊的為「不攻擊」。"""
    if not summon_acts(summon.template):
        return "不攻擊"
    weapon = summon.weapon
    return (
        f"{weapon.name_zh}：{_dice(weapon.dice, weapon.flat)} {weapon.element.display_name}傷害"
        f"（射程 {weapon.range}）"
    )


def summon_defense_text(summon: SummonDef) -> str:
    """護甲、抗性與弱點。"""
    template = summon.template
    parts = [f"護甲 {template.armor_bonus:+d}"]
    for group, permille in sorted(template.resist.items()):
        if permille:
            parts.append(f"{group.display_name}抗性 {permille / 10:g}%")
    for element, permille in sorted(template.element_mods.items()):
        if permille > 0:
            parts.append(
                f"怕{element.display_name}（受到的{element.display_name}傷害 +{permille / 10:g}%）"
            )
        elif permille < 0:
            parts.append(f"{element.display_name}傷害 −{-permille / 10:g}%")
    return "，".join(parts)


def _on_cast_only(infusion: SummonInfusion) -> bool:
    """只在召喚當下生效的灌注（HP、隱蔽）：不攻擊的召喚物也用得到。"""
    return bool(infusion.hp_permille or infusion.conceal_rounds)


def infusion_hint(lib: ContentLibrary, *, acts: bool = True) -> str:
    """召喚時灌注的一句話（清單 1.7）。例子取 ``summon_infusions`` 第一個帶狀態的關鍵字；不攻擊的
    召喚物（``acts`` 為假）只有召喚當下生效的灌注有用，例子改取那一類。"""
    table = lib.ruleset.core.summon_infusions
    names = {k.id: k.name_zh for k in lib.keywords.keywords}
    wanted = (lambda i: i.status is not None) if acts else _on_cast_only
    example = next(
        (
            f"{names[key]}→{infusion_phrases(lib, infusion)[0]}"
            for key, infusion in table.items()
            if wanted(infusion) and key in names
        ),
        None,
    )
    if not acts:
        note = f"；它不攻擊，只有召喚時生效的灌注有用，例：{example}" if example else ""
        return f"灌注：施放時從你持有的關鍵字選一個帶上{note}"
    return "灌注：施放時從你持有的關鍵字選一個帶上" + (f"（例：{example}）" if example else "")


class SummonInfoCard(BaseModel):
    """技能卡可展開的「召喚物資訊」（清單 1.8）：全部由範本與規則產生的文字。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    """召喚物範本 ID。"""
    name_zh: str
    count: int = 1
    """一次召喚幾隻（數量型進化）。"""
    hp: int
    """最大 HP（:func:`summon_card_hp`，和引擎同一個算法）。"""
    hp_note: str
    move: str
    defense: str
    attack: str
    innate: tuple[str, ...]
    """自帶能力，每項一句。"""
    behavior: tuple[str, ...]
    infusion: str
    """召喚時灌注的說明（:func:`infusion_hint`）。"""


def summon_info(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> SummonInfoCard | None:
    """``skill`` 的召喚效果 ``spec`` 的資訊小卡；範本不存在時 ``None``。"""
    try:
        summon = lib.ruleset.summon_def(spec.unit or "")
    except KeyError:
        return None
    template = summon.template
    growth = lib.ruleset.core.summon_growth
    role = lib.ruleset.core.summon_role_hp_permille.get(template.role or "", 1000)
    attr = skill.scaling_attr.display_name
    hp_note = (
        f"施放者 1 級、{attr}修正 0 時；施放者每升 1 級 +{growth.hp_per_level}、"
        f"{attr}修正每 +1 再 +{growth.hp_per_attr_mod}，再乘定位係數 ×{role / 1000:g}"
    )
    acts = summon_acts(template)
    return SummonInfoCard(
        id=template.id,
        name_zh=template.name_zh,
        count=spec.count if isinstance(spec.count, int) else 1,
        hp=summon_card_hp(lib, summon, spec),
        hp_note=hp_note,
        move="不移動" if not acts or template.speed == 0 else f"{template.speed} 格",
        defense=summon_defense_text(summon),
        attack=summon_attack_text(summon),
        innate=summon_innate_lines(lib, summon),
        behavior=summon_behavior_lines(lib, summon),
        infusion=infusion_hint(lib, acts=acts),
    )
