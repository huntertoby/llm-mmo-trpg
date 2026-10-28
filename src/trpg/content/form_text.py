"""形態的說明文字（Phase 3J-1a，``docs/design/06-技能.md`` 6.30）：全部由 ``content/forms.yaml`` 的
資料產生（卡片句、HUD 的形態說明、天生武器的「目前 +N」）。"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.forms import CHOSEN, FormDef, FormEntry, FormTable
from trpg.content.rules import CoreRules
from trpg.shared.bonus_text import bonus_text
from trpg.shared.types import Attribute, Element

__all__ = [
    "form_effect_lines",
    "form_entry_lines",
    "form_sentence",
    "natural_trait_lines",
    "natural_weapon_text",
    "upkeep_text",
]

_PERMILLE = 1000


def _percent(permille: int) -> str:
    """千分比 → 「+15%」「−10%」（整數百分比；不整除時一位小數）。"""
    sign = "+" if permille >= 0 else "−"
    value = abs(permille) / 10
    return f"{sign}{value:g}%"


def _signed(n: int) -> str:
    return f"+{n}" if n >= 0 else f"−{-n}"


def _element_text(element: Element | str, chosen: Element | None) -> str:
    if element == CHOSEN:
        return "所選元素" if chosen is None else chosen.display_name
    assert isinstance(element, Element)
    return element.display_name


def _attrs_text(form: FormDef) -> str:
    attrs = form.natural_weapon.attrs
    names = "／".join(a.display_name for a in attrs)
    if len(attrs) == 1:
        return names
    same = attrs[0].is_physical == attrs[1].is_physical
    return f"{names}取{'較高' if same else '平均'}"


def natural_weapon_text(
    form: FormDef,
    core: CoreRules,
    *,
    chosen: Element | None = None,
    attr_get: Callable[[Attribute], int] | None = None,
) -> str:
    """天生武器的一句話：「熊爪 1d8 近戰（力量／體質取較高 × 0.3，目前 +3）」。``attr_get`` 有值時
    附「目前 +N」（和普攻同一個算法：武器縮放值 × ``basic_attack_attr_multiplier_permille``）。"""
    weapon = form.natural_weapon
    reach = "近戰" if weapon.attack == "melee" else f"遠程 {weapon.range}"
    if weapon.charge is not None:
        reach = f"蓄力（錐形，大小 {weapon.charge.size}）"
    if weapon.attack == "melee" and weapon.range > 1:
        reach += f"（射程 {weapon.range}）"
    permille = core.basic_attack_attr_multiplier_permille
    scale = f"{_attrs_text(form)} × {permille / _PERMILLE:g}"
    if attr_get is not None:
        value = weapon.weapon_def(form.id, chosen).scaling_value(attr_get)
        scale += f"，{bonus_text(value, permille)}"
    element = ""
    if weapon.element is not None:
        element = f"{weapon.element.display_name}"
    elif weapon.element_choices:
        names = "、".join(e.display_name for e in weapon.element_choices)
        element = (
            f"{chosen.display_name}（進入時選{names}）"
            if chosen is not None
            else f"元素（進入時選{names}）"
        )
    extra = f"，{element}傷害" if element else ""
    bonus = f"，天生武器傷害 {_percent(weapon.damage_permille)}" if weapon.damage_permille else ""
    traits = "".join(f"，{line}" for line in natural_trait_lines(form))
    return f"{weapon.name_zh} {weapon.dice} {reach}（{scale}）{extra}{bonus}{traits}"


def natural_trait_lines(form: FormDef) -> list[str]:
    """天生武器的特性（資料順序固定）：蓄力（3J-2）、打幾下、推擊、觸及、流血、背刺暴擊。"""
    t = form.natural_weapon.traits
    lines: list[str] = []
    if form.natural_weapon.charge is not None:
        lines.append(
            "普攻＝選方向開始蓄力，下回合開始時朝該方向釋放（蓄力中倒下、暈眩、冰凍或離開形態就取消）"
        )
    if t.strikes > 1:
        lines.append(f"普攻打 {t.strikes} 下（各自擲命中）")
    if t.knockback:
        lines.append(f"命中推擊 {t.knockback} 格")
    if t.reach > 1:
        lines.append(f"觸及 {t.reach}")
    if t.bleed:
        lines.append(f"命中流血 {t.bleed} 回合")
    if t.backstab_crit:
        lines.append(f"背刺暴擊範圍再 +{t.backstab_crit}")
    return lines


def form_effect_lines(form: FormDef, *, chosen: Element | None = None) -> list[str]:
    """形態中的效果（資料順序固定）：最大 HP、防禦、移動、受傷修正、治療加成、高度差。"""
    e = form.effects
    lines: list[str] = []
    if e.max_hp_permille:
        lines.append(f"最大 HP {_percent(e.max_hp_permille)}")
    if e.defense_permille:
        lines.append(f"防禦 {_percent(e.defense_permille)}")
    if e.move:
        lines.append(f"移動 {_signed(e.move)}")
    for mod in e.damage_taken:
        delta = mod.permille - _PERMILLE
        lines.append(f"受{_element_text(mod.element, chosen)}傷害 {_percent(delta)}")
    if e.heal_permille:
        lines.append(f"你施放的治療 {_percent(e.heal_permille)}")
    if e.flat_height:
        lines.append(f"高度差 {e.flat_height} 以內當平地走")
    return lines


def form_entry_lines(entry: FormEntry, *, chosen: Element | None = None) -> list[str]:
    """進入獎勵（資料順序固定）。"""
    lines: list[str] = []
    if entry.shield_max_hp_permille is not None:
        pct = _percent(entry.shield_max_hp_permille).removeprefix("+")
        lines.append(f"護盾＝最大 HP 的 {pct}（{entry.shield_duration} 回合）")
    if entry.heal_max_hp_permille is not None:
        pct = _percent(entry.heal_max_hp_permille).removeprefix("+")
        lines.append(f"回復最大 HP 的 {pct}")
    if entry.next_attack_hit:
        lines.append(f"下一次攻擊命中 +{entry.next_attack_hit}")
    if entry.next_attack_crit:
        lines.append(f"下一次攻擊暴擊範圍 +{entry.next_attack_crit}")
    if entry.move:
        lines.append(f"本回合移動 +{entry.move}")
    if entry.conceal is not None:
        lines.append(f"隱蔽 {entry.conceal} 回合")
    if entry.burst is not None:
        b = entry.burst
        element = _element_text(b.element, chosen)
        lines.append(f"{b.radius} 格內的敵人受 {b.dice} {element}傷害")
    if entry.collision_permille:
        lines.append(f"本回合你造成的撞擊傷害 {_percent(entry.collision_permille)}")
    if entry.heal_adjacent is not None:
        h = entry.heal_adjacent
        lines.append(
            f"治療相鄰友方 {h.dice}＋{h.attr.display_name} × {h.attr_permille / _PERMILLE:g}"
        )
    return lines


def upkeep_text(table: FormTable, form: FormDef) -> str:
    """維持費與冷卻：「每回合開始 −5 耐力（不夠就自動解除）；離開後冷卻 2 回合」。"""
    resource, amount = table.upkeep(form)
    name = "耐力" if resource == "stamina" else "法力"
    return (
        f"每回合開始 −{amount} {name}（不夠就自動解除）；離開後這個形態冷卻 {table.cooldown} 回合"
    )


def form_sentence(
    table: FormTable,
    form: FormDef,
    core: CoreRules,
    *,
    attr_get: Callable[[Attribute], int] | None = None,
) -> str:
    """技能卡的一句話：「化身為熊（物理形態，持續到取消）：普攻改用熊爪 1d8 近戰（…）；形態中：
    最大 HP +15%、防禦 +10%、移動 −1；進入時：護盾＝最大 HP 的 10%；每回合開始 −5 耐力…」。"""
    kind = "物理" if form.category == "physical" else "心智"
    parts = [f"化身為{form.name_zh}（{kind}形態，持續到取消）"]
    parts.append(f"普攻改用{natural_weapon_text(form, core, attr_get=attr_get)}")
    effects = form_effect_lines(form)
    if effects:
        parts.append("形態中：" + "、".join(effects))
    entry = form_entry_lines(form.entry)
    if entry:
        parts.append("進入時：" + "、".join(entry))
    parts.append(upkeep_text(table, form))
    return parts[0] + "：" + "；".join(parts[1:])
