"""小變化模板的改法（Phase 3W-2，``docs/design/06-技能.md`` 6.34.4；``content/flash_templates.yaml``
的 ``minor`` 模板用 ``op`` 引用這裡的函式，登錄表是 :data:`FLASH_OPS`）。

每個改法的簽名 ``(技能, 模板, 變化, 內容庫) -> 草稿列表``：草稿是（技能欄位 dict、效果 dict 列表），
只描述「怎麼改」，**不寫強度**——強度由 :func:`trpg.skillgen.flash.apply_variation` 在預算上限提高後
依預算器重調（旋鈕從最弱開始往上調，守則 3）。做不出來（種類不對、形狀不能改、沒有可以改的效果）
時回傳空列表，那個變化就不會出現在選項裡。多個草稿時依序試，第一個合格的就是結果。

十三類（6.34.4；``op`` → 說明）：

=================  ============================================================
``area``           範圍 +1（形狀的大小參數）
``range``          距離 +1
``reshape``        換形狀（直線、錐形、十字、3×3；沿用進化的 ``reshape`` 候選）
``multi_hit``      多打一下：同一目標多一段命中（複製第一個傷害效果）
``followup``       接續段：命中後接一小段傷害（6.23 複合技，``when: on_hit``）
``element``        第二元素：多一個別種元素的傷害效果
``keyword_imbue``  第二個關鍵字（製造）：沿用橋接的 ``graft_makes``
``keyword_exploit``  第二個關鍵字（利用）：沿用橋接的 ``graft_uses``
``extend``         延長狀態、表面、區域 1 回合（沿用恆久的草稿）
``kill_refund``    擊殺返還 1 AP
``charge``         蓄力：冷卻 +2（最多 5）、威力提高
``light``          輕巧：AP −1（最少 1）、冷卻 0～1、威力降低
``potency``        輔助、觸發類的「效果 +」：結構不變，預算上限提高後重調得更強
``trigger_range``  觸發範圍 +1（被動、反應）
``trigger_cap``    每回合觸發次數上限 +1（被動；不超過 6.6）
``mod_potency``    修正幅度 +（修正型被動）
``mod_range``      作用範圍 +1（修正型被動：射程 +1，或多一條範圍 +1 的規則）
``mod_keyword``    加第二個關鍵字（修正型被動：多一條不同關鍵字條件的同樣修正）
``mod_relax``      條件放寬一級（修正型被動）
=================  ============================================================

輔助類（6.34.4）沒有獨立的改法：效果 + 用 ``potency``、範圍 +1 用 ``area``、附帶關鍵字用
``keyword_imbue``（模板用 ``keywords`` 限定不會傷到友方的關鍵字）。
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from typing import Any

from trpg.content.flash_templates import FlashTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.skills.constants import FOLLOWUP_FORBIDDEN
from trpg.engine.skill_levels import grow_shape
from trpg.shared.types import Element
from trpg.skillgen.composer_parts import Knob, dice_ladder
from trpg.skillgen.evolution import evolution_template, multiplier_ladder, template_drafts
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "FLASH_OPS",
    "STRICT_OPS",
    "Draft",
    "FlashOp",
    "base_draft",
    "tuning_extras",
]

type Draft = tuple[dict[str, Any], list[dict[str, Any]]]
type FlashOp = Callable[[SkillDef, FlashTemplate, Variation, ContentLibrary], list[Draft]]

MAX_CHARGE_COOLDOWN = 5
"""蓄力把冷卻加到最多幾回合（6.34.4）。"""
CHARGE_COOLDOWN_STEP = 2
MAX_LIGHT_COOLDOWN = 1
"""輕巧把冷卻壓到最多幾回合（6.34.4：0～1）。"""
MAX_TRIGGERS_PER_ROUND = 3
"""被動每回合觸發次數的上限（``TriggerSpec.max_per_round`` 的 schema 上限）。"""
MODIFIER_LADDER = tuple(range(50, 1001, 25))
"""修正幅度（‰）的旋鈕階梯。"""
RELAX_PERMILLE = 150
"""條件放寬一級：血量門檻（‰）放寬多少。"""
MAX_RELAX_PERMILLE = 900

STRICT_OPS = frozenset({"potency", "mod_potency"})
"""結構不變、只靠重調變強的改法：強度下限要嚴格大於變化前（否則可能「閃了沒變化」）。"""


# ---------------------------------------------------------------------------
# 共用
# ---------------------------------------------------------------------------


def base_draft(skill: SkillDef) -> Draft:
    """技能目前的欄位與效果（dict，可就地修改）。"""
    base = skill.model_dump(mode="json")
    effects: list[dict[str, Any]] = [
        e.model_dump(mode="json", exclude_none=True) for e in skill.effects
    ]
    base.pop("effects")
    return base, effects


def _reshapable(skill: SkillDef) -> bool:
    """形狀可以改（複合技能與陷阱不改形狀，同 5 級小特性的保守做法）。"""
    return skill.kind == "active" and skill.followup is None and skill.trap is None


def _first_damage(effects: Sequence[dict[str, Any]]) -> int | None:
    return next((i for i, e in enumerate(effects) if e["type"] == "damage"), None)


def _damage_element(skill: SkillDef) -> str | None:
    damage = next((e for e in skill.effects if e.type == "damage"), None)
    return None if damage is None or damage.element is None else damage.element.value


def _hits(skill: SkillDef) -> bool:
    return skill.kind in ("active", "passive", "reaction") and skill.trap is None


def _new_damage(skill: SkillDef, source: dict[str, Any], element: str | None) -> dict[str, Any]:
    """新增的傷害效果（數值之後由旋鈕調）：法術技用骰子、武器技用倍率。"""
    effect: dict[str, Any] = {"type": "damage"}
    if element is not None:
        effect["element"] = element
    if "affects" in source:
        effect["affects"] = source["affects"]
    if skill.category == "spell" or "dice" in source:
        effect["dice"] = "1d4"
    else:
        effect["multiplier_permille"] = 300
    return effect


# ---------------------------------------------------------------------------
# 範圍：範圍 +1、距離 +1、換形狀
# ---------------------------------------------------------------------------


def _op_area(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """範圍 +delta：形狀第一個可增加的大小參數（``size``／``radius``），不超過形狀上限（6.6）。"""
    if not _reshapable(skill):
        return []
    grown = grow_shape(library.ruleset, skill.shape, template.delta or 0)
    if grown == skill.shape:
        return []
    base, effects = base_draft(skill)
    base["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def _op_range(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """距離 +delta：固定射程（整數）加 delta，不超過形狀上限；武器射程與沒有射程的形狀不適用。"""
    shape = skill.shape
    if not _reshapable(skill) or not isinstance(shape.range, int) or shape.range < 1:
        return []
    param = library.ruleset.shape_def(shape.type).params.get("range")
    if param is None:
        return []
    value = min(shape.range + (template.delta or 0), param.max)
    if value == shape.range or value < 1:
        return []
    base, effects = base_draft(skill)
    base["shape"] = shape.model_copy(update={"range": value}).model_dump(
        mode="json", exclude_none=True
    )
    return [(base, effects)]


def _op_reshape(
    skill: SkillDef, template: FlashTemplate, variation: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """換形狀：``variation.shape``（省略時依序試模板列的形狀）；要有傷害效果，且不能換成同一種。"""
    if not _reshapable(skill) or not any(e.type == "damage" for e in skill.effects):
        return []
    shapes = (variation.shape,) if variation.shape is not None else template.shapes
    drafts: list[Draft] = []
    for shape in shapes:
        if shape.type == skill.shape.type:
            continue
        base, effects = base_draft(skill)
        base["shape"] = shape.model_dump(mode="json", exclude_none=True)
        drafts.append((base, effects))
    return drafts


# ---------------------------------------------------------------------------
# 連段：多打一下、接續段
# ---------------------------------------------------------------------------


def _op_multi_hit(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """多打一下：第一個傷害效果之後再加一個同元素、同對象的傷害效果（同一目標多一段命中）。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    if not _hits(skill) or skill.followup is not None or index is None or len(effects) >= 4:  # noqa: PLR2004 - MAX_EFFECTS
        return []
    source = effects[index]
    extra = _new_damage(skill, source, source.get("element"))
    effects.insert(index + 1, extra)
    return [(base, effects)]


_FOLLOWUP_SKELETONS = ("strike", "combo", "area")
"""接續段依序試的骨架（原骨架優先）。"""


def _op_followup(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """接續段：命中後接一小段傷害（``when: on_hit``，自動對命中的同一個目標；6.23）。複合技、陷阱、
    變奏、常駐類傳說與有失手反噬的技能不加。"""
    blocked = (
        skill.kind != "active"
        or skill.followup is not None
        or skill.trap is not None
        or skill.variants
        or skill.cost.on_miss
        or skill.is_activatable
    )
    if blocked or any(e.type in FOLLOWUP_FORBIDDEN for e in skill.effects):
        return []
    index = next((i for i, e in enumerate(skill.effects) if e.type == "damage"), None)
    if index is None:
        return []
    source = skill.effects[index].model_dump(mode="json", exclude_none=True)
    element = source.get("element")
    second = _new_damage(skill, {k: v for k, v in source.items() if k != "affects"}, element)
    drafts: list[Draft] = []
    for skeleton in dict.fromkeys((skill.skeleton, *_FOLLOWUP_SKELETONS)):
        base, effects = base_draft(skill)
        base["followup"] = {
            "when": "on_hit",
            "skeleton": skeleton,
            "shape": {"type": "single", "range": 1},
            "effects": [dict(second)],
        }
        drafts.append((base, effects))
    return drafts


# ---------------------------------------------------------------------------
# 元素與關鍵字
# ---------------------------------------------------------------------------


def _op_element(
    skill: SkillDef, template: FlashTemplate, variation: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """第二元素：多一個 ``variation.element`` 的傷害效果（和主要傷害不同元素）。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    element = variation.element
    if (
        not _hits(skill)
        or element is None
        or index is None
        or len(effects) >= 4  # noqa: PLR2004 - MAX_EFFECTS
        or (template.elements and element not in template.elements)
        or element == (effects[index].get("element") or Element.PHYSICAL.value)
        or any(e.get("element") == element for e in effects)
    ):
        return []
    effects.insert(index + 1, _new_damage(skill, effects[index], element))
    return [(base, effects)]


def _keyword_op(op: str, side: str) -> FlashOp:
    """第二個關鍵字：沿用橋接的草稿（``graft_makes`` 製造、``graft_uses`` 利用）。"""

    def run(
        skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
    ) -> list[Draft]:
        keyword = variation.keyword
        evolution = evolution_template(library, op)
        if (
            evolution is None
            or keyword is None
            or (template.keywords and keyword not in template.keywords)
            or skill.kind not in ("active", "passive", "reaction")
        ):
            return []
        drafts = template_drafts(evolution, skill, keyword, SkillUsage(), library)
        out: list[Draft] = []
        for base, effects in drafts:
            _inherit_affects(skill, effects)
            out.append((base, effects))
            if side == "uses" and skill.kind == "active" and skill.skeleton != "combo":
                out.append(({**base, "skeleton": "combo"}, [dict(e) for e in effects]))
        return out

    return run


def _inherit_affects(skill: SkillDef, effects: list[dict[str, Any]]) -> None:
    """被動與反應的效果要寫對象（``affects``）：新加的效果沿用第一個效果的對象。"""
    if skill.kind == "active" or len(effects) <= len(skill.effects) or not skill.effects:
        return
    affects = skill.effects[0].affects
    if affects is not None:
        for effect in effects[len(skill.effects) :]:
            effect.setdefault("affects", affects)


# ---------------------------------------------------------------------------
# 延長與收割
# ---------------------------------------------------------------------------


def _op_extend(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """延長狀態、表面、區域 1 回合（沿用「恆久」的草稿；硬控狀態不延長）。"""
    evolution = evolution_template(library, "extend")
    if evolution is None or skill.kind not in ("active", "passive", "reaction"):
        return []
    return template_drafts(evolution, skill, None, SkillUsage(), library)


def _op_kill_refund(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """擊殺返還 1 AP：第一個傷害效果加 ``on_kill: refund_ap``（只有主動技能的傷害效果可以有）。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    if skill.kind != "active" or index is None or "on_kill" in effects[index]:
        return []
    effects[index]["on_kill"] = [{"type": "refund_ap", "amount": 1}]
    return [(base, effects)]


# ---------------------------------------------------------------------------
# 費用方向：蓄力、輕巧
# ---------------------------------------------------------------------------


def _op_charge(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """蓄力：冷卻 +2（最多 5 回合），威力由預算器依冷卻折抵提高。"""
    if skill.kind != "active":
        return []
    cooldown = skill.cost.cooldown or 0
    value = min(cooldown + CHARGE_COOLDOWN_STEP, MAX_CHARGE_COOLDOWN)
    if value <= cooldown:
        return []
    base, effects = base_draft(skill)
    base["cost"] = {**base["cost"], "cooldown": value}
    return [(base, effects)]


def _op_light(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """輕巧：AP −1（最少 1），冷卻壓到 0～1 回合，威力由預算器依較低的 AP 係數降低。"""
    if skill.kind != "active" or (skill.ap_cost or 1) <= 1:
        return []
    base, effects = base_draft(skill)
    base["ap_cost"] = (skill.ap_cost or 2) - 1
    cooldown = skill.cost.cooldown
    if cooldown is not None and cooldown > MAX_LIGHT_COOLDOWN:
        base["cost"] = {**base["cost"], "cooldown": MAX_LIGHT_COOLDOWN}
    return [(base, effects)]


# ---------------------------------------------------------------------------
# 輔助、觸發
# ---------------------------------------------------------------------------


def _op_potency(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """效果 +：結構不變（治療、護盾、增益、被動、反應的效果），預算上限提高後重調得更強。"""
    if skill.kind not in ("active", "passive", "reaction") or skill.trap is not None:
        return []
    return [base_draft(skill)]


def _op_trigger_range(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """觸發範圍 +delta（預設 1）：``trigger.max_distance`` 加 delta；沒有距離上限時看形狀的大小。"""
    if skill.kind not in ("passive", "reaction"):
        return []
    step = template.delta or 1
    base, effects = base_draft(skill)
    trigger = skill.trigger
    if trigger is not None and trigger.max_distance is not None:
        base["trigger"] = {**base["trigger"], "max_distance": trigger.max_distance + step}
        return [(base, effects)]
    if skill.shape.type == "self":
        return []
    grown = grow_shape(library.ruleset, skill.shape, step)
    if grown == skill.shape:
        return []
    base["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def _op_dual_scaling(
    skill: SkillDef, _t: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """雙屬性縮放（3 階）：加第二縮放屬性 ``variation.keyword``（屬性 ID；範圍同工坊的選單，
    ``library.secondary_range``）；稀有度由重調時依需求補到史詩以上。"""
    attr = variation.keyword
    if (
        attr is None
        or skill.kind not in ("active", "passive", "reaction")
        or skill.secondary_scaling_attr is not None
        or attr == skill.scaling_attr.value
        or attr not in {a.value for a in library.secondary_range(skill)}
    ):
        return []
    base, effects = base_draft(skill)
    base["secondary_scaling_attr"] = attr
    base["mastery"] = None
    return [(base, effects)]


def _op_trigger_cap(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """每回合觸發次數上限 +1（被動；最多 3，再由驗證器的 6.6 硬上限擋）。"""
    trigger = skill.trigger
    if (
        skill.kind != "passive"
        or trigger is None
        or trigger.max_per_round >= MAX_TRIGGERS_PER_ROUND
    ):
        return []
    base, effects = base_draft(skill)
    base["trigger"] = {**base["trigger"], "max_per_round": trigger.max_per_round + 1}
    return [(base, effects)]


# ---------------------------------------------------------------------------
# 修正型被動
# ---------------------------------------------------------------------------

_MAGNITUDES = ("damage_permille", "heal_permille")


def _op_mod_potency(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """修正幅度 +：有正的傷害或治療幅度的規則，幅度由預算器重調（旋鈕見 :func:`tuning_extras`）。"""
    if skill.kind != "modifier":
        return []
    if not any((getattr(m.change, name) or 0) > 0 for m in skill.modifiers for name in _MAGNITUDES):
        return []
    return [base_draft(skill)]


def _op_mod_range(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """作用範圍 +1：射程 +1 的規則升成 +2；否則多一條「範圍 +1」或「射程 +1」的規則。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        if rule.change.range_delta == 1:
            base, effects = base_draft(skill)
            base["modifiers"][index]["change"]["range_delta"] = 2
            drafts.append((base, effects))
    if len(skill.modifiers) < 2:  # noqa: PLR2004 - 修正規則最多 2 條
        applies = skill.modifiers[0].applies_to.model_dump(mode="json")
        for change in ({"range_delta": 1}, {"area_delta": 1}):
            base, effects = base_draft(skill)
            base["modifiers"].append({"applies_to": applies, "change": change})
            drafts.append((base, effects))
    return drafts


def _graft_condition(library: ContentLibrary, keyword: str) -> dict[str, Any] | None:
    graft = library.evolution.grafts.get(keyword)
    if graft is None or graft.uses is None or graft.uses.condition is None:
        return None
    return graft.uses.condition.model_dump(mode="json", exclude_none=True)


def _op_mod_keyword(
    skill: SkillDef, _t: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """加第二個關鍵字：多一條同樣修正、條件換成另一個關鍵字的規則（例：燃燒中的敵人 → 另加潮濕
    表面上的敵人）。兩條都成立時幅度相加。"""
    keyword = variation.keyword
    condition = None if keyword is None else _graft_condition(library, keyword)
    if skill.kind != "modifier" or condition is None or len(skill.modifiers) >= 2:  # noqa: PLR2004
        return []
    rule = skill.modifiers[0]
    if (
        rule.condition is None
        or rule.condition.model_dump(mode="json", exclude_none=True) == condition
    ):
        return []
    base, effects = base_draft(skill)
    clone = copy.deepcopy(base["modifiers"][0])
    clone["condition"] = condition
    base["modifiers"].append(clone)
    return [(base, effects)]


def _op_mod_relax(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """條件放寬一級：血量門檻放寬 150‰（最多 900‰）；其他條件放寬成沒有條件（預算照算，幅度由預算
    器重調得小一點）。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        condition = rule.condition
        if condition is None:
            continue
        base, effects = base_draft(skill)
        if condition.permille is not None:
            widened = min(condition.permille + RELAX_PERMILLE, MAX_RELAX_PERMILLE)
            if widened == condition.permille:
                continue
            base["modifiers"][index]["condition"]["permille"] = widened
        else:
            base["modifiers"][index]["condition"] = None
        drafts.append((base, effects))
    return drafts[:1]


# ---------------------------------------------------------------------------
# 登錄表與重調的額外旋鈕
# ---------------------------------------------------------------------------

FLASH_OPS: dict[str, FlashOp] = {
    "area": _op_area,
    "range": _op_range,
    "reshape": _op_reshape,
    "multi_hit": _op_multi_hit,
    "followup": _op_followup,
    "element": _op_element,
    "keyword_imbue": _keyword_op("bridge_imbue", "makes"),
    "keyword_exploit": _keyword_op("bridge_exploit", "uses"),
    "extend": _op_extend,
    "kill_refund": _op_kill_refund,
    "charge": _op_charge,
    "light": _op_light,
    "potency": _op_potency,
    "trigger_range": _op_trigger_range,
    "dual_scaling": _op_dual_scaling,
    "trigger_cap": _op_trigger_cap,
    "mod_potency": _op_mod_potency,
    "mod_range": _op_mod_range,
    "mod_keyword": _op_mod_keyword,
    "mod_relax": _op_mod_relax,
}
"""小變化的改法登錄表（``op`` → 草稿）。資料裡 ``op`` 沒有登錄的模板不會出現
（:func:`trpg.skillgen.flash.unimplemented_ops` 列出）。"""


def tuning_extras(
    op: str, base: dict[str, Any], library: ContentLibrary
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """重調時除了 ``effects`` 以外要一起調的字典與旋鈕（旋鈕的 ``index`` 是回傳字典的位置）：

    - 修正型被動：每條規則的 ``change``（傷害、治療幅度）；
    - 接續段：``followup.effects`` 的傷害（模板新加的那一段）。
    """
    if base.get("kind") == "modifier":
        changes = [m["change"] for m in base["modifiers"]]
        knobs = [
            Knob(i, name, MODIFIER_LADDER)
            for i, change in enumerate(changes)
            for name in _MAGNITUDES
            if (change.get(name) or 0) > 0
        ]
        return changes, knobs
    if op == "followup" and base.get("followup"):
        effects = base["followup"]["effects"]
        dice = dice_ladder(library.composer.dice)
        multipliers = multiplier_ladder(library)
        knobs = [
            Knob(i, "dice", dice) if "dice" in e else Knob(i, "multiplier_permille", multipliers)
            for i, e in enumerate(effects)
            if e["type"] == "damage"
        ]
        return effects, knobs
    return [], []
