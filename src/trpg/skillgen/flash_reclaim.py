"""收回家族的精煉、合體、專注（BAL-10e，``docs/design/06-技能.md`` 6.34.4「收回家族」；玩法決定
#75）。

每一種只寫「拿掉什麼」（``remove``，同小變化改法的簽名）與必要時的「換成什麼」旋鈕；預算、強度下限、
單發上限與減費用都走 :func:`trpg.skillgen.flash_trade.apply_trade`（登錄在
:data:`trpg.skillgen.flash_trade.TRADES`）。

- ``refine`` 精煉（主動技，元素與關鍵字）：拿掉一個附帶效果——附帶狀態、第二元素、第二關鍵字
  （製造：狀態、表面、倒地；利用：帶條件的加碼傷害），或接續段 → 主要效果的威力。
- ``refine_merge`` 精煉（主動技，連段）：同一目標的多段同元素傷害併成一段（總量不變，只換成單發）。
- ``fuse`` 合體（一次召喚 2 隻以上的召喚技，輔助）：召喚隻數 −1 → 召喚物最大 HP（照強壯）。
- ``focus_range`` 專注（被動、反應，觸發）：觸發距離上限或形狀大小收回一級 → 觸發效果的威力。
- ``focus_condition`` 專注（被動、反應，觸發）：觸發條件收緊一級（被攻擊 → 被近戰攻擊；沒有條件
  → 加一個條件；血量門檻收緊；「或」拿掉一支）→ 觸發效果的威力。
- ``focus_mod_range`` 專注（修正型被動，修正）：作用範圍（範圍 +n、射程 +n）收回一級 → 修正幅度。
- ``focus_mod_condition`` 專注（修正型被動，修正）：規則的條件收緊一級 → 修正幅度。

只拿技能身上真的有的（原生的與閃現加上的都算）；沒有可拿的就回傳空列表（這個選項不出）。
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

from trpg.content.flash_templates import FlashTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import ConditionSpec, EffectSpec, ShapeSpec, SkillDef
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.flash_ops import (
    RECLAIM_MOD_OP,
    SUMMON_HP_STEPS,
    Draft,
    base_draft,
    tuning_extras,
)
from trpg.skillgen.flash_state import Variation

__all__ = [
    "fuse_knobs",
    "modifier_gain",
    "op_focus_condition",
    "op_focus_mod_condition",
    "op_focus_mod_range",
    "op_focus_range",
    "op_fuse",
    "op_refine",
    "op_refine_merge",
]

_POWER = frozenset({"damage", "delayed_damage", "heal", "shield"})
"""主要效果（威力）的原語：第一個這種效果是「主要效果」，精煉不會拿掉它。"""
_KEYWORD_MAKERS = frozenset({"apply_status", "create_surface", "knock_prone"})
"""精煉可拿掉的「附帶狀態」與「第二關鍵字（製造）」原語（推拉是位移骨架的本體，不算附帶）。"""
_TIGHTER_EVENTS = {"hit_by_attack": "hit_by_melee"}
"""反應的觸發條件收緊一級（6.34.4 例：被攻擊時 → 被近戰攻擊時）。"""
TIGHTEN_PERMILLE = 150
"""血量門檻收緊一級（‰；同條件放寬 ``RELAX_PERMILLE`` 的一級）。"""
MIN_TIGHTEN_PERMILLE = 100
"""收緊後的血量門檻不低於這個值（‰）。"""
_TARGET_CONDITION = {"type": "target_hp_below", "permille": 500}
_SELF_CONDITION = {"type": "self_hp_below", "permille": 500}
"""沒有條件時加的條件（同條件放寬加的「或」分支）：有「目標」（被動的另一方、反應的單體目標、修正
規則）時先試目標血量，再試自身血量；只作用在自己身上時只用自身血量（目標條件會落到自己身上）。"""
_SHRINKABLE = ("size", "radius")
_TWO = 2


# ---------------------------------------------------------------------------
# 共用
# ---------------------------------------------------------------------------


def _skeleton_drafts(
    skill: SkillDef,
    template: FlashTemplate,
    draft: Draft,
    library: ContentLibrary,
) -> list[Draft]:
    """``draft`` 依「原骨架 → 模板的 ``skeletons``」各一份（只取允許這招種類與形狀的骨架；拿掉附帶
    效果後原骨架可能不再合適，例：控制技拿掉狀態後改試打擊）。"""
    base, effects = draft
    drafts: list[Draft] = []
    for name in dict.fromkeys((skill.skeleton, *template.skeletons)):
        skeleton = library.skeletons.get(name)
        if (
            skeleton is None
            or skill.kind not in skeleton.kinds
            or skill.shape.type not in skeleton.shapes
        ):
            continue
        drafts.append(({**copy.deepcopy(base), "skeleton": name}, copy.deepcopy(effects)))
    return drafts


def _main_power(skill: SkillDef) -> int | None:
    return next((i for i, e in enumerate(skill.effects) if e.type in _POWER), None)


def _element(effect: EffectSpec) -> str | None:
    return None if effect.element is None else effect.element.value


def _tightened(condition: dict[str, Any] | None, *, targeted: bool) -> list[dict[str, Any]]:
    """條件收緊一級的候選：沒有條件 → 加一個條件（``targeted``：有另一方目標）；有「或」→ 拿掉
    「或」那一支；血量門檻 → 收緊 :data:`TIGHTEN_PERMILLE`（不低於 :data:`MIN_TIGHTEN_PERMILLE`）；
    其他（狀態、表面……）已經是最緊的，不出。"""
    if condition is None:
        added = (_TARGET_CONDITION, _SELF_CONDITION) if targeted else (_SELF_CONDITION,)
        return [dict(c) for c in added]
    if condition.get("any_of"):
        return [{k: v for k, v in condition.items() if k != "any_of"}]
    permille = condition.get("permille")
    if isinstance(permille, int) and permille - TIGHTEN_PERMILLE >= MIN_TIGHTEN_PERMILLE:
        return [{**condition, "permille": permille - TIGHTEN_PERMILLE}]
    return []


def _shrunk(shape: ShapeSpec, library: ContentLibrary) -> ShapeSpec | None:
    """形狀第一個大小參數（``size``／``radius``）−1；已是最小值或沒有大小參數時 ``None``（觸發範圍
    +1 的反向，見 :func:`~trpg.engine.shape_growth.grow_shape`）。"""
    params = library.ruleset.shape_def(shape.type).params
    for name in _SHRINKABLE:
        value = getattr(shape, name)
        if name in params and isinstance(value, int):
            if value - 1 < params[name].min:
                return None
            return shape.model_copy(update={name: value - 1})
    return None


# ---------------------------------------------------------------------------
# 精煉
# ---------------------------------------------------------------------------


def _attachments(skill: SkillDef) -> list[int]:
    """可以拿掉的附帶效果（位置，由後往前：閃現加上的通常在後面）：附帶狀態、表面、倒地；和主要
    效果不同元素的傷害（第二元素）；帶條件的加碼傷害（第二關鍵字）。主要效果本身不算。"""
    main = _main_power(skill)
    if main is None:
        return []
    element = _element(skill.effects[main])
    found = [
        index
        for index, effect in enumerate(skill.effects)
        if index != main
        and (
            effect.type in _KEYWORD_MAKERS
            or (
                effect.type == "damage"
                and (effect.condition is not None or _element(effect) != element)
            )
        )
    ]
    return found[::-1]


def _refinable(skill: SkillDef) -> bool:
    return skill.kind == "active" and skill.trap is None and _main_power(skill) is not None


def op_refine(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """精煉：拿掉一個附帶效果（:func:`_attachments`，依序試），最後試拿掉接續段；主要效果留著。"""
    if not _refinable(skill):
        return []
    drafts: list[Draft] = []
    for index in _attachments(skill):
        base, effects = base_draft(skill)
        del effects[index]
        drafts += _skeleton_drafts(skill, template, (base, effects), library)
    if skill.followup is not None:
        base, effects = base_draft(skill)
        base["followup"] = None
        drafts += _skeleton_drafts(skill, template, (base, effects), library)
    return drafts


def op_refine_merge(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """多段併一段：和第一個傷害同元素、同對象、沒有條件的其他傷害段全部拿掉（總點數不變，全部換成
    那一段的威力）。"""
    if not _refinable(skill):
        return []
    first = next((i for i, e in enumerate(skill.effects) if e.type == "damage"), None)
    if first is None:
        return []
    main = skill.effects[first]
    extra = [
        index
        for index, effect in enumerate(skill.effects)
        if index != first
        and effect.type == "damage"
        and effect.condition is None
        and _element(effect) == _element(main)
        and effect.affects == main.affects
    ]
    if not extra:
        return []
    base, effects = base_draft(skill)
    for index in reversed(extra):
        del effects[index]
    return _skeleton_drafts(skill, template, (base, effects), library)


# ---------------------------------------------------------------------------
# 合體
# ---------------------------------------------------------------------------


def _summon_index(effects: list[dict[str, Any]]) -> int | None:
    return next((i for i, e in enumerate(effects) if e["type"] == "summon"), None)


def op_fuse(skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary) -> list[Draft]:
    """合體：召喚隻數 −1（剩一隻時拿掉 ``count`` 與每隻的弱化 ``power_permille``——一隻時不能低於
    1000‰）；變強的部分由 :func:`fuse_knobs` 調召喚物最大 HP。"""
    base, effects = base_draft(skill)
    index = _summon_index(effects)
    count = None if index is None else effects[index].get("count")
    if skill.kind != "active" or index is None or not isinstance(count, int) or count < _TWO:
        return []
    effect = effects[index]
    if count - 1 == 1:
        effect.pop("count", None)
        effect.pop("power_permille", None)
    else:
        effect["count"] = count - 1
    return [(base, effects)]


def fuse_knobs(effects: list[dict[str, Any]], _library: ContentLibrary) -> list[Knob]:
    """合體換到的強度：召喚物最大 HP 加成（照強壯 ``summon_toughen`` 的階梯，從目前的值起）。"""
    index = _summon_index(effects)
    if index is None:
        return []
    current = effects[index].get("max_hp_permille") or 0
    # 沒有加成時從「不加」（None）起；schema 不收 0
    values = (current or None, *(step for step in SUMMON_HP_STEPS if step > current))
    return [Knob(index, "max_hp_permille", values)]


# ---------------------------------------------------------------------------
# 專注
# ---------------------------------------------------------------------------


def op_focus_range(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """觸發範圍收回一級（觸發範圍 +1 的反向）：``trigger.max_distance`` −1（已是 1 不出）；沒有距離
    上限時形狀的大小 −1（形狀是自己、單體或已是最小時不出）。"""
    if skill.kind not in ("passive", "reaction"):
        return []
    base, effects = base_draft(skill)
    trigger = skill.trigger
    if trigger is not None and trigger.max_distance is not None:
        if trigger.max_distance <= 1:
            return []
        base["trigger"] = {**base["trigger"], "max_distance": trigger.max_distance - 1}
        return [(base, effects)]
    shrunk = _shrunk(skill.shape, library)
    if shrunk is None:
        return []
    base["shape"] = shrunk.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def op_focus_condition(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """觸發條件收緊一級：反應「被攻擊時 → 被近戰攻擊時」；技能條件照 :func:`_tightened`。"""
    if skill.kind not in ("passive", "reaction"):
        return []
    drafts: list[Draft] = []
    tighter = None if skill.reaction is None else _TIGHTER_EVENTS.get(skill.reaction.event)
    if tighter is not None:
        base, effects = base_draft(skill)
        base["reaction"] = {**base["reaction"], "event": tighter}
        drafts.append((base, effects))
    current = _dumped(skill.condition)
    for condition in _tightened(current, targeted=_has_target(skill)):
        base, effects = base_draft(skill)
        base["condition"] = condition
        drafts.append((base, effects))
    return drafts


def _dumped(condition: ConditionSpec | None) -> dict[str, Any] | None:
    return None if condition is None else condition.model_dump(mode="json", exclude_none=True)


def _has_target(skill: SkillDef) -> bool:
    """觸發時有「另一方」目標（技能條件看它）：被動 ``trigger.target: other``、單體的反應。"""
    if skill.kind == "reaction":
        return skill.shape.type == "single"
    return skill.trigger is not None and skill.trigger.target == "other"


def _rule_conditions(skill: SkillDef) -> Iterator[tuple[int, dict[str, Any]]]:
    for index, rule in enumerate(skill.modifiers):
        for condition in _tightened(_dumped(rule.condition), targeted=True):
            yield index, condition


def op_focus_mod_range(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """作用範圍收回一級（作用範圍 +1 的反向）：範圍 +n／射程 +n 的規則 −1；只有 +1 時拿掉那一條規則
    （修正型被動至少要留一條規則，只剩這一條時不出）。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        for field in ("area_delta", "range_delta"):
            value = getattr(rule.change, field)
            if not isinstance(value, int) or value < 1:
                continue
            base, effects = base_draft(skill)
            if value > 1:
                base["modifiers"][index]["change"][field] = value - 1
            elif len(skill.modifiers) > 1:
                del base["modifiers"][index]
            else:
                continue
            drafts.append((base, effects))
    return drafts


def op_focus_mod_condition(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """規則的條件收緊一級（照 :func:`_tightened`；依規則順序，最多 3 份草稿，同條件放寬）。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, condition in _rule_conditions(skill):
        base, effects = base_draft(skill)
        base["modifiers"][index]["condition"] = condition
        drafts.append((base, effects))
    return drafts[:3]


def modifier_gain(
    base: dict[str, Any], _effects: list[dict[str, Any]], library: ContentLibrary
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """專注（修正型被動）換到的修正幅度：同 BAL-10b 修正模板的旋鈕（傷害、治療幅度的細階梯，以及
    ``rules.modifier_knobs`` 的其他幅度）。"""
    return tuning_extras(RECLAIM_MOD_OP, base, library)
