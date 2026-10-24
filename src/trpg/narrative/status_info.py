"""狀態與層數的規則說明（Phase 3-41a，說明整修清單第 4、5 節）：由 ``statuses.yaml``、
``stacks.yaml``、``core.yaml`` 與武器資料產生，和規則同一個來源。名詞對照表（``/api/glossary``）的
``rules_zh`` 用這裡的句子；``description_zh`` 只留不含數字的一句話。

- :func:`status_rules`：持續傷害與治療的骰值、元素解除、破甲幅度（依武器）、抵抗屬性、控制遞減、
  Boss 轉換。持續回合數不寫在狀態說明裡（由技能卡寫，清單 4.3）。
- :func:`stack_rules`：層數的上限依來源、超載的每層加成與反噬。
"""

from __future__ import annotations

from trpg.content.battle import StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.rules import CoreRules
from trpg.content.stacks import StackDef
from trpg.engine.ids import CONCEALED, DEFENDING, PRONE
from trpg.shared.types import Attribute

__all__ = [
    "BOOST_TEXT",
    "CONTROL_GROUP_TEXT",
    "stack_gain_text",
    "stack_rules",
    "status_rules",
]

CONTROL_GROUP_TEXT = {"movement": "移動類", "mental": "心智類", "hard": "硬控"}
"""控制類別（``control_group``）的中文名。"""


def _dice(count: int, sides: int) -> str:
    return f"{count}d{sides}"


def _armor_break_line(library: ContentLibrary) -> str:
    """破甲的幅度與回合數依武器（``weapons.yaml`` 的 ``armor_break``，清單 4.4）。"""
    parts = [
        f"{w.name_zh} {-w.armor_break.defense_permille / 10:g}%（{w.armor_break.rounds} 回合）"
        for w in sorted(library.weapons.values(), key=lambda w: w.id)
        if w.armor_break is not None
    ]
    return "防禦值降低的幅度依武器：" + "、".join(parts) if parts else "防禦值降低的幅度依來源"


def _entangle_line(library: ContentLibrary) -> str:
    """纏繞的移動點數減少量依武器（``weapons.yaml`` 的 ``entangle``，Phase 3I-1）。"""
    parts = [
        f"{w.name_zh} −{w.entangle.move_penalty}"
        for w in sorted(library.weapons.values(), key=lambda w: w.id)
        if w.entangle is not None
    ]
    amount = "、".join(parts) if parts else "依來源"
    return (
        f"下一個回合開始時移動點數減少（{amount}；最低 0），持續到該回合結束；"
        "重複施加只刷新、不疊加，不擲抵抗"
    )


NEUTRAL_PERMILLE = 1000
"""倍率欄位的中性值（×100%，不寫說明）。"""

_PERMILLE_FIELDS = (
    ("damage_dealt_permille", "自己造成的攻擊傷害"),
    ("damage_taken_permille", "受到的骰值傷害（不含墜落、致命地形等百分比傷害）"),
    ("healing_received_permille", "受到的治療"),
    ("move_permille", "回合開始時的移動點數（無條件捨去）"),
)
"""狀態的倍率欄位 → 說明句開頭（3-41c 第 4 點，數字由欄位產生）。"""


def _times(permille: int) -> str:
    return f"×{permille / 10:g}%"


def _attr_bonus_line(status: StatusDef) -> str | None:
    """屬性加值句：六個屬性同值寫「六個屬性各 +N」，否則逐一列出。"""
    bonus = status.attr_bonus
    if not bonus:
        return None
    values = set(bonus.values())
    if len(bonus) == len(Attribute) and len(values) == 1:
        return (
            f"六個屬性各 {next(iter(values)):+d}"
            "（命中、抵抗、傷害與治療的縮放都用加值後的屬性；先攻不變）"
        )
    return "、".join(f"{a.display_name} {v:+d}" for a, v in sorted(bonus.items()))


def _modifier_lines(status: StatusDef, core: CoreRules) -> list[str]:
    """由狀態欄位與核心規則產生的數值句（3-41c 第 4 點）：說明裡不再寫死數字。"""
    lines: list[str] = []
    for field, label in _PERMILLE_FIELDS:
        permille: int = getattr(status, field)
        if permille != NEUTRAL_PERMILLE:
            lines.append(f"{label} {_times(permille)}")
    if (attr := _attr_bonus_line(status)) is not None:
        lines.append(attr)
    if status.attack_bonus:
        lines.append(f"攻擊值 +{status.attack_bonus}")
    if status.attack_range_cap is not None:
        lines.append(f"攻擊與以單位為目標的技能只能選擇 {status.attack_range_cap} 格以內的單位")
    if status.id == DEFENDING:
        lines.append(f"防禦值 +{core.defend_defense_bonus_permille / 10:g}%")
    if status.id == PRONE:
        lines.append(f"站起來要消耗 {core.prone_stand_up_move_permille / 10:g}% 的移動點數（進位）")
    if status.id == CONCEALED:
        lines.append(f"超過 {core.concealed_ranged_max_distance} 格的遠程攻擊無法選為目標")
    return lines


def status_rules(status: StatusDef, library: ContentLibrary) -> tuple[str, ...]:
    """狀態的規則句（清單 4.1～4.4、3-41c 第 4 點）：數值修正、持續傷害與治療、元素解除、破甲、
    抵抗、控制遞減、Boss。"""
    core = library.ruleset.core
    lines: list[str] = _modifier_lines(status, core)
    dot = status.on_turn_start_damage
    if dot is not None:
        lines.append(
            f"回合開始時受到 {_dice(dot.dice.count, dot.dice.sides)} {dot.element.display_name}傷害"
        )
    heal = status.on_turn_start_heal
    if heal is not None:
        lines.append(f"回合開始時恢復 {_dice(heal.dice.count, heal.dice.sides)} HP")
    if status.removed_by_element:
        names = "、".join(e.display_name for e in status.removed_by_element)
        lines.append(f"受到{names}傷害時立即解除")
    if status.defense_break:
        lines.append(_armor_break_line(library))
    if status.move_reduction:
        lines.append(_entangle_line(library))
    if status.save_attr is not None:
        lines.append(
            f"抵抗：由技能或動作施加在敵人身上時，目標以{status.save_attr.display_name}對抗施放者的"
            "技能屬性，成功就不會被施加（對友方、表面與環境造成的不擲抵抗）"
        )
    if status.control_group is not None:
        group = CONTROL_GROUP_TEXT[status.control_group]
        lines.append(
            f"控制遞減（{group}）：成功施加後 {core.control_dr_rounds} 輪內，同類控制的抵抗判定中"
            f"目標的屬性 ×{core.control_dr_resist_permille / 1000:g}"
        )
    converted = core.boss_control_conversion.get(status.id)
    if converted is not None:
        name = library.ruleset.status_def(converted).name_zh
        lines.append(f"對 Boss：改為施加「{name}」（持續時間不變）")
    return tuple(lines)


BOOST_TEXT = {"damage": "傷害", "heal": "治療", "shield": "護盾"}
"""層數消耗時加成的效果種類（``consumer.boosts``）的中文名。"""

_GAIN_WHEN = {
    "weapon_skill_hit": "你的武器技命中時",
    "basic_attack_hit": "你的普攻命中時",
    "damaged": "你受到傷害時",
    "kill": "你擊倒敵人時",
    "summon_downed": "你的召喚物倒下時",
    "heal_or_holy_cast": "你施放治療或神聖技能時",
    "turn_end_still": "你的回合結束且這回合沒有移動時",
}


def stack_gain_text(stack: StackDef) -> str:
    """層數自動累積的白話說明（Phase 3-52，06 6.32）；沒有自動累積規則時為空字串。"""
    parts: list[str] = []
    for rule in stack.gain:
        if rule.when == "element_hit":
            assert rule.element is not None
            when = f"你的{rule.element.display_name}傷害命中時"
        else:
            when = _GAIN_WHEN[rule.when]
        parts.append(f"{when} +{rule.amount} 層")
    if not parts:
        return ""
    where = "疊在被命中的敵人身上" if stack.owner == "target" else "累積在你身上"
    return f"{where}：{'；'.join(parts)}（只有帶著消耗它的技能才會自動累積）"


def _consumer_line(stack: StackDef, library: ContentLibrary) -> str:
    consumer = stack.consumer
    if consumer is None:
        return ""
    boosts = "、".join(BOOST_TEXT[b] for b in consumer.boosts)
    line = f"消耗：技能每層提高{boosts}"
    if consumer.requires_any:
        names: list[str] = []
        for req in consumer.requires_any:
            if req.tag is not None:
                names.append(f"帶「{library.ruleset.skill_tags.name(req.tag)}」標籤")
            elif req.element is not None:
                names.append(f"{req.element.display_name}傷害")
            elif req.effect is not None:
                names.append(f"「{library.ruleset.primitives.by_id()[req.effect].name_zh}」效果")
        line += f"（限{'、'.join(names)}的技能）"
    return line


def stack_rules(stack: StackDef, library: ContentLibrary) -> tuple[str, ...]:
    """層數的規則句（清單 5.5～5.7）：上限依來源、清空時機、超載。"""
    lines = [f"上限依來源（技能卡與裝備詞條各自寫明；最多 {stack.max} 層）"]
    gain = stack_gain_text(stack)
    if gain:
        lines.append(gain)
    consumer = _consumer_line(stack, library)
    if consumer:
        lines.append(consumer)
    if stack.expires_after_rounds is not None:
        lines.append(f"{stack.expires_after_rounds} 輪沒有再累積就清空")
    overload = stack.overload
    if overload is not None:
        tag = library.ruleset.skill_tags.name(overload.tag)
        backlash: list[str] = []
        for sub in overload.backlash:
            if sub.type == "damage" and sub.dice is not None and sub.element is not None:
                backlash.append(
                    f"受到 {_dice(sub.dice.count, sub.dice.sides)} {sub.element.display_name}傷害"
                    "（不致命）"
                )
            elif sub.status is not None:
                backlash.append(f"獲得「{library.ruleset.status_def(sub.status).name_zh}」")
        per = overload.per_stack_damage_permille / 10
        lines.append(
            f"超載：每層讓你帶「{tag}」標籤的技能傷害 +{per:g}%；"
            f"累積到 {overload.threshold} 層時你{'、'.join(backlash)}並清空層數"
        )
    return tuple(lines)
