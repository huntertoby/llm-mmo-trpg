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
from trpg.content.stacks import StackDef

__all__ = ["CONTROL_GROUP_TEXT", "stack_rules", "status_rules"]

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


def status_rules(status: StatusDef, library: ContentLibrary) -> tuple[str, ...]:
    """狀態的規則句（清單 4.1～4.4）：持續傷害與治療、元素解除、破甲、抵抗、控制遞減、Boss。"""
    core = library.ruleset.core
    lines: list[str] = []
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


def stack_rules(stack: StackDef, library: ContentLibrary) -> tuple[str, ...]:
    """層數的規則句（清單 5.5～5.7）：上限依來源、清空時機、超載。"""
    lines = [f"上限依來源（技能卡與裝備詞條各自寫明；最多 {stack.max} 層）"]
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
