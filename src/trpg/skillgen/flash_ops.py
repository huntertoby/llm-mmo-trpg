"""小變化模板的改法（Phase 3W-2，``docs/design/06-技能.md`` 6.34.4；``content/flash_templates.yaml``
的 ``minor`` 模板用 ``op`` 引用這裡的函式，登錄表是 :data:`FLASH_OPS`）。

每個改法的簽名 ``(技能, 模板, 變化, 內容庫) -> 草稿列表``：草稿是（技能欄位 dict、效果 dict 列表），
只描述「怎麼改」，**不寫強度**——強度由 :func:`trpg.skillgen.flash_derive.apply_variation`
在預算上限提高後依預算器重調（旋鈕從最弱開始往上調，守則 3）。
做不出來（種類不對、形狀不能改、沒有可以改的效果）
時回傳空列表，那個變化就不會出現在選項裡。多個草稿時依序試，第一個合格的就是結果。

十三類（6.34.4；``op`` → 說明）：

=================  ============================================================
``area``           範圍 +1（形狀的大小參數）
``range``          距離 +1
``reshape``        換形狀（直線、錐形、十字、3×3；沿用進化的 ``reshape`` 候選）
``terrain_area``   地形變化：升降地形的技能換成 4～6 格（2 階）或 7 格以上（3 階）的形狀
``multi_hit``      多打一下：同一目標多一段命中（複製第一個傷害效果）
``followup``       接續段：命中後接一小段傷害（6.23 複合技，``when: on_hit``）
``element``        第二元素：多一個別種元素的傷害效果
``keyword_imbue``  第二個關鍵字（製造）：沿用橋接的 ``graft_makes``
``keyword_exploit``  第二個關鍵字（利用）：沿用橋接的 ``graft_uses``
``extend``         延長狀態、表面、區域 1 回合（沿用恆久的草稿）
``kill_refund``    擊殺返還 1 AP
``summon_toughen`` 強壯（召喚技能）：召喚物最大 HP 再多一截
``charge``         蓄力：冷卻 +2（最多 5）、威力提高
``light``          輕巧：AP −1（最少 1）、冷卻 0～1、威力降低
``potency``        輔助、觸發類的「效果 +」：結構不變，預算上限提高後重調得更強
``trigger_range``  觸發範圍 +1（被動、反應）
``trigger_cap``    每回合觸發次數上限 +1（被動；不超過 6.6）
``mod_potency``    修正幅度 +（修正型被動）
``mod_range``      作用範圍 +1（修正型被動：多一條光環半徑 +1 的規則，或射程 +1）
``mod_keyword``    加第二個關鍵字（修正型被動：條件改成「原條件，或另一個關鍵字的條件」，any_of）
``mod_relax``      條件放寬一級（修正型被動：血量門檻放寬，或條件加一個「或」分支）
``stance_light``   輕巧（姿態）：維持費 −1、元素姿態換到較低級（效果降低）
``stance_heavy``   蓄力（姿態）：維持費 +1、元素姿態換到較高級（效果提高）
``stance_potency`` 修正（姿態）：維持費不變、元素姿態換到較高級（效果提高）
``followup_potency``  接續段強化（複合技，BAL-10b）：接續段的傷害只往上調
``followup_area``  接續段範圍 +1（複合技，BAL-10b）
``followup_range`` 接續段距離 +1（複合技，BAL-10b）
``followup_element``  接續段加第二元素（複合技，BAL-10b）
``mod_duration``   持續回合 +1（修正型被動：命中後狀態／符文、召喚持續，BAL-10b）
``mod_stack``      計數上限 +1（修正型被動：依空欄位計算的格數，BAL-10b）
``mod_cooldown``   命中後冷卻 −1 → −2（修正型被動，BAL-10b）
``mod_cost``       代價減輕（修正型被動：負的幅度減輕一格，不讓代價消失，BAL-10b／10c）
``stance_enter_light``  進入代價 −1（姿態：冷卻、法力、耐力減一格，維持費不動，BAL-10b／10c）
``stance_enter_heavy``  進入代價 +1（姿態：進入時的法力或耐力加一格、本體提高一級，BAL-19e）
``self_rider``     附帶護身（姿態進入時、反應觸發時多一個作用於自己的效果，BAL-19e）
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
from trpg.content.skills import EffectSpec, SkillDef, skill_elements
from trpg.content.skills.constants import (
    ENTER_FORM,
    FLAT_BONUS_EFFECTS,
    FOLLOWUP_FORBIDDEN,
)
from trpg.content.skills.effects import composition_rules
from trpg.engine.shape_growth import grow_shape
from trpg.shared.types import Element
from trpg.skillgen.composer_parts import Knob, dice_ladder
from trpg.skillgen.evolution import evolution_template, multiplier_ladder, template_drafts
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "FIXED_FIRST_OPS",
    "FLASH_OPS",
    "RECLAIM_MOD_OP",
    "STRICT_OPS",
    "Draft",
    "FlashOp",
    "base_draft",
    "cell_count",
    "tuning_extras",
]

type Draft = tuple[dict[str, Any], list[dict[str, Any]]]
type FlashOp = Callable[[SkillDef, FlashTemplate, Variation, ContentLibrary], list[Draft]]

MAX_LIGHT_COOLDOWN = 1
"""輕巧把冷卻壓到最多幾回合（6.34.4：0～1）。"""
MODIFIER_LADDER = tuple(range(50, 1001, 25))
"""修正幅度（‰）的旋鈕階梯。"""

STRICT_OPS = frozenset({"potency", "mod_potency", "stance_potency", "followup_potency"})
"""結構不變、只靠重調變強的改法：強度下限要嚴格大於變化前（否則可能「閃了沒變化」）。"""
FIXED_FIRST_OPS = frozenset({"followup_potency"})
"""先用固定強度（草稿原樣）檢查、不合格才重調的改法（BAL-10b：取最小的合格增幅）。"""


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


def _new_damage(
    library: ContentLibrary, skill: SkillDef, source: dict[str, Any], element: str | None
) -> dict[str, Any]:
    """新增的傷害效果（數值之後由旋鈕調）：法術技用骰子、武器技用倍率。"""
    effect: dict[str, Any] = {"type": "damage"}
    if element is not None:
        effect["element"] = element
    if "affects" in source:
        effect["affects"] = source["affects"]
    if skill.category == "spell" or "dice" in source:
        effect["dice"] = "1d4"
    else:
        effect["multiplier_permille"] = library.flash.rules.new_damage_multiplier_permille
    return effect


# ---------------------------------------------------------------------------
# 範圍：範圍 +1、距離 +1、換形狀
# ---------------------------------------------------------------------------


def _op_area(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """範圍 +delta：形狀第一個可增加的大小參數（``size``／``radius``），不超過形狀上限（6.6）。

    BAL-12b 定（只限 ``delta`` 1）：陷阱改觸發範圍（``rules.area_trap_shapes`` 的下一個）；形狀沒有
    大小參數的地面格換成 ``rules.area_tile_shapes`` 的下一個（指定格 → 十字）。"""
    if (
        skill.kind == "active"
        and skill.followup is None
        and skill.trap is not None
        and template.delta == 1
    ):
        return _trap_area(skill, library.flash.rules.area_trap_shapes)
    if not _reshapable(skill):
        return []
    grown = grow_shape(library.ruleset, skill.shape, template.delta or 0)
    if grown == skill.shape:
        return _tile_area(skill, library) if template.delta == 1 else []
    base, effects = base_draft(skill)
    base["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def _next_in(ladder: Sequence[str], current: str) -> str | None:
    if current not in ladder or current == ladder[-1]:
        return None
    return ladder[ladder.index(current) + 1]


def _trap_area(skill: SkillDef, ladder: Sequence[str]) -> list[Draft]:
    """陷阱觸發範圍升一級（BAL-12b 定）。"""
    assert skill.trap is not None
    shape = _next_in(ladder, skill.trap.shape)
    if shape is None:
        return []
    base, effects = base_draft(skill)
    base["trap"] = {**base["trap"], "shape": shape}
    return [(base, effects)]


def _tile_area(skill: SkillDef, library: ContentLibrary) -> list[Draft]:
    """地面格半徑 +1（BAL-12b 定）：換成 ``area_tile_shapes`` 的下一個形狀，射程夾在新形狀的範圍內
    （同升階重配的換形狀）；效果允不允許新形狀交給驗證器。"""
    shape_id = _next_in(library.flash.rules.area_tile_shapes, skill.shape.type)
    if shape_id is None:
        return []
    spec: dict[str, Any] = {"type": shape_id}
    limits = library.ruleset.shape_def(shape_id).params.get("range")
    if limits is not None and isinstance(skill.shape.range, int):
        spec["range"] = min(max(skill.shape.range, limits.min), limits.max)
    base, effects = base_draft(skill)
    base["shape"] = spec
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


_TERRAIN_PRIMITIVES = frozenset({"raise_terrain", "lower_terrain"})


def _op_terrain_area(
    skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """地形變化（3W-2b，#58）：升降地形的技能換成影響格數落在 ``min_cells``～``max_cells`` 的形狀
    （2 階 4～6 格、3 階 7 格以上）；格數要比現在多，且技能原本不能已經在這個範圍內。形狀的稀有度
    與地形格數的稀有度門檻（rare／epic）由重調時依結構自動補（稀有度只是複雜度標記）。"""
    if not _reshapable(skill) or not any(e.type in _TERRAIN_PRIMITIVES for e in skill.effects):
        return []
    current = cell_count(skill.shape, library)
    shapes = (variation.shape,) if variation.shape is not None else template.shapes
    drafts: list[Draft] = []
    for shape in shapes:
        cells = cell_count(shape, library)
        if (
            cells is None
            or (current is not None and cells <= current)
            or cells < (template.min_cells or 1)
            or (template.max_cells is not None and cells > template.max_cells)
        ):
            continue
        # 升降地形的點數是固定的，階級高、預算變大後單靠地形追不上預算下限：先試純地形，再試「地形
        # ＋落石」（多一個大地傷害效果，強度由預算器調）
        for rocks in (False, True):
            base, effects = base_draft(skill)
            base["shape"] = shape.model_dump(mode="json", exclude_none=True)
            if rocks:
                if len(effects) >= library.ruleset.core.skill_limits.max_effects:
                    continue
                effects.append(_new_damage(library, skill, {}, "earth"))
            drafts.append((base, effects))
    return drafts


def cell_count(shape: Any, library: ContentLibrary) -> int | None:
    """形狀影響的格數（``skill_shapes.yaml`` 的 ``cell_count``）；沒有資料時 ``None``。"""
    definition = library.ruleset.shapes.by_id().get(shape.type)
    if definition is None or definition.cell_count is None:
        return None
    try:
        values = definition.with_defaults(shape.param_values())
        return definition.cell_count.count_for(values, solid=bool(getattr(shape, "solid", None)))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 連段：多打一下、接續段
# ---------------------------------------------------------------------------


def _op_multi_hit(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """多打一下：第一個傷害效果之後再加一個同元素、同對象的傷害效果（同一目標多一段命中）。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    full = len(effects) >= library.ruleset.core.skill_limits.max_effects
    if not _hits(skill) or skill.followup is not None or index is None or full:
        return []
    source = effects[index]
    extra = _new_damage(library, skill, source, source.get("element"))
    effects.insert(index + 1, extra)
    return [(base, effects)]


_FOLLOWUP_SKELETONS = ("strike", "combo", "area")
"""接續段依序試的骨架（原骨架優先）。"""


def _op_followup(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
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
    second = _new_damage(
        library, skill, {k: v for k, v in source.items() if k != "affects"}, element
    )
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


FOLLOWUP_OPS = frozenset(
    {"followup", "followup_potency", "followup_area", "followup_range", "followup_element"}
)
"""重調時連接續段的傷害一起調的改法（:func:`tuning_extras`）。"""
_FOLLOWUP_TUNED = frozenset({"damage"})
"""接續段裡當旋鈕的效果種類。"""


# BAL-10b：複合技的接續段強化（複合技不改第一段的形狀，也不再加接續段，改強化已有的接續段）


def _has_followup(skill: SkillDef) -> bool:
    return skill.kind == "active" and skill.followup is not None and skill.trap is None


def _followup_draft(skill: SkillDef) -> Draft:
    """:func:`base_draft`，但接續段只留有填的欄位（重調旋鈕看欄位在不在）。"""
    base, effects = base_draft(skill)
    if skill.followup is not None:
        base["followup"] = skill.followup.model_dump(mode="json", exclude_none=True)
    return base, effects


def _followup_tunable(skill: SkillDef) -> bool:
    """接續段有可以調的強度（傷害、治療、護盾的骰子或倍率）。"""
    followup = skill.followup
    return followup is not None and any(
        e.type in _FOLLOWUP_TUNED and (e.dice is not None or e.multiplier_permille is not None)
        for e in followup.effects
    )


def _op_followup_potency(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """接續段強化（連段）：結構不變，接續段的傷害變強（只往上調，不重設到最弱）。

    草稿依序是「接續段的某一個傷害往上 1～n 格」（先小步、再換下一個傷害）；先用固定強度直接檢查
    預算窗與強度下限（:data:`FIXED_FIRST_OPS`，取最小的合格增幅，留空間給之後的閃現），都不合格才交給
    重調器從這一格起往上調。內建複合技常已超過第一段骨架的核心占比（重調器不收），所以固定強度優先。"""
    if not _has_followup(skill) or not _followup_tunable(skill):
        return []
    drafts: list[Draft] = []
    for step in range(1, library.flash.rules.followup_potency_tries + 1):
        for index, effect in enumerate(skill.followup.effects if skill.followup else ()):
            if effect.type not in _FOLLOWUP_TUNED:
                continue
            base, effects = _followup_draft(skill)
            target = base["followup"]["effects"][index]
            field, ladder = _followup_knob(target, library)
            current = target.get(field)
            if current not in ladder or ladder.index(current) + step >= len(ladder):
                continue
            target[field] = ladder[ladder.index(current) + step]
            drafts.append((base, effects))
    return drafts


def _followup_knob(effect: dict[str, Any], library: ContentLibrary) -> tuple[str, tuple[Any, ...]]:
    """接續段傷害的旋鈕欄位與階梯（骰子或武器倍率）。"""
    if effect.get("dice") is not None:
        return "dice", dice_ladder(library.composer.dice)
    return "multiplier_permille", _followup_multipliers(library)


def _followup_multipliers(library: ContentLibrary) -> tuple[int, ...]:
    """接續段強化類的武器倍率階梯：原階梯＋``rules.followup_multiplier_step`` 的細格（BAL-11b）。"""
    ladder = multiplier_ladder(library)
    step = library.flash.rules.followup_multiplier_step
    if step is None:
        return ladder
    top = library.flash.rules.followup_fine_top_permille  # 細階梯只細到這裡，以上照原階梯
    return tuple(sorted({*ladder, *range(ladder[0], top, step)}))


def _op_followup_area(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """接續段範圍 +delta（範圍）：接續段形狀第一個可增加的大小參數（``size``／``radius``）。"""
    followup = skill.followup
    if not _has_followup(skill) or followup is None:
        return []
    grown = grow_shape(library.ruleset, followup.shape, template.delta or 0)
    if grown == followup.shape:
        return []
    base, effects = _followup_draft(skill)
    base["followup"]["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return _followup_eased((base, effects), library)


def _op_followup_range(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """接續段距離 +delta（範圍）：接續段形狀的固定射程（≥ 1）加 delta，不超過形狀上限。"""
    followup = skill.followup
    if not _has_followup(skill) or followup is None:
        return []
    shape = followup.shape
    param = library.ruleset.shape_def(shape.type).params.get("range")
    if param is None or not isinstance(shape.range, int) or shape.range < 1:
        return []
    value = min(shape.range + (template.delta or 0), param.max)
    if value <= shape.range:
        return []
    base, effects = _followup_draft(skill)
    base["followup"]["shape"] = shape.model_copy(update={"range": value}).model_dump(
        mode="json", exclude_none=True
    )
    return _followup_eased((base, effects), library)


def _op_followup_element(
    skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """接續段第二元素（元素）：接續段第一個傷害效果之後多一段 ``variation.element`` 的傷害。"""
    followup = skill.followup
    element = variation.element
    if not _has_followup(skill) or followup is None or element is None:
        return []
    base, effects = _followup_draft(skill)
    second = base["followup"]["effects"]
    index = _first_damage(second)
    if (
        index is None
        or len(second) >= library.ruleset.core.skill_limits.max_effects
        or (template.elements and element not in template.elements)
        or element == (second[index].get("element") or Element.PHYSICAL.value)
        or any(e.get("element") == element for e in (*second, *effects))
    ):
        return []
    second.insert(index + 1, _new_damage(library, skill, second[index], element))
    return _followup_eased((base, effects), library)


def _followup_eased(draft: Draft, library: ContentLibrary) -> list[Draft]:
    """``draft`` 本身，再接「接續段第一個傷害往下讓 1～n 格」的版本（預算花到範圍、距離或新元素上，
    原本的傷害可以變小；重調器被骨架占比擋住時，固定強度的檢查依序試這些）。"""
    base, effects = draft
    second = base["followup"]["effects"]
    index = next((i for i, e in enumerate(second) if e["type"] in _FOLLOWUP_TUNED), None)
    if index is None:
        return [draft]
    field, ladder = _followup_knob(second[index], library)
    current = second[index].get(field)
    if current not in ladder:
        return [draft]
    position = ladder.index(current)
    drafts = [draft]
    for step in range(1, min(library.flash.rules.followup_ease_steps, position) + 1):
        eased = copy.deepcopy(base)
        eased["followup"]["effects"][index][field] = ladder[position - step]
        drafts.append((eased, [dict(e) for e in effects]))
    return drafts


# ---------------------------------------------------------------------------
# 元素與關鍵字
# ---------------------------------------------------------------------------


def _op_element(
    skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """第二元素：多一個 ``variation.element`` 的傷害效果（和主要傷害不同元素）。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    element = variation.element
    if (
        not _hits(skill)
        or element is None
        or index is None
        or len(effects) >= library.ruleset.core.skill_limits.max_effects
        or (template.elements and element not in template.elements)
        or element == (effects[index].get("element") or Element.PHYSICAL.value)
        or any(e.get("element") == element for e in effects)
    ):
        return []
    effects.insert(index + 1, _new_damage(library, skill, effects[index], element))
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
            or _graft_blocked(skill)
        ):
            return []
        drafts = template_drafts(evolution, skill, keyword, SkillUsage(), library)
        out: list[Draft] = []
        for base, effects in drafts:
            _inherit_affects(skill, effects)
            if skill.category == "spell":
                _spell_graft_damage(skill, effects, library)
            out.append((base, effects))
            if side == "uses" and skill.kind == "active" and skill.skeleton != "combo":
                out.append(({**base, "skeleton": "combo"}, [dict(e) for e in effects]))
        return out

    return run


def _graft_blocked(skill: SkillDef) -> bool:
    """BAL-11b：技能裡有「必須是唯一的效果」或「其他效果只能作用在施放者」的原語（召喚、復活、
    規則改變、持續區域……；``skill_primitives.yaml`` 的組合規則）時，嫁接第二個關鍵字一定不合法，
    不出這類模板。"""
    rules = composition_rules()
    return any(
        (rule := rules.get(e.type)) is not None
        and (rule.sole_effect or rule.others_affect is not None)
        for e in skill.effects
    )


def _spell_graft_damage(
    skill: SkillDef, effects: list[dict[str, Any]], library: ContentLibrary
) -> None:
    """BAL-11b：法術技嫁接的傷害要有骰子與元素（schema 規定）。元素沿用這招的傷害元素、再來技能
    元素，都沒有時用物理；骰子先給最小一格（由預算器重調）。"""
    element = _damage_element(skill) or next(
        iter(sorted(e.value for e in skill_elements(skill))), Element.PHYSICAL.value
    )
    for effect in effects[len(skill.effects) :]:
        if effect["type"] == "damage":
            effect.setdefault("element", element)
            effect.setdefault("dice", dice_ladder(library.composer.dice)[0])


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
    """延長狀態、表面、區域 1 回合（沿用「恆久」的草稿；硬控狀態不延長）。

    BAL-12b 定：這些都延長不了時，改延長 ``rules.extend_effects`` 列的效果（召喚物存活、障礙、
    刻印）與陷阱持續回合（``rules.extend_trap``），各 +1 回合。"""
    evolution = evolution_template(library, "extend")
    if evolution is None or skill.kind not in ("active", "passive", "reaction"):
        return []
    drafts = template_drafts(evolution, skill, None, SkillUsage(), library)
    return drafts or _extend_wider(skill, library)


def _extend_wider(skill: SkillDef, library: ContentLibrary) -> list[Draft]:
    """延長放寬的草稿（BAL-12b 定）：有回合數的召喚、障礙、刻印 +1，陷阱的 ``rounds`` +1；
    參數上限交給驗證器（超過就不合法、不出）。沒有可延長的就不出。"""
    rules = library.flash.rules
    base, effects = base_draft(skill)
    changed = False
    for effect in effects:
        if effect["type"] in rules.extend_effects and effect.get("duration"):
            effect["duration"] += 1
            changed = True
    # 陷阱持續回合：只限觸發型（enter）；延遲型（delay）的 rounds 是引爆前的等待，加了反而變慢
    if rules.extend_trap and skill.trap is not None and skill.trap.trigger == "enter":
        base["trap"] = {**base["trap"], "rounds": skill.trap.rounds + 1}
        changed = True
    return [(base, effects)] if changed else []


def _op_summon_toughen(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """強壯（召喚技能，3W-2b）：召喚物的最大 HP 再多一截（``max_hp_permille``，往上一階）。召喚
    技能的點數是固定的，沒有骰子旋鈕可調，所以補這個讓召喚白板也有小變化可選。"""
    index = next((i for i, e in enumerate(skill.effects) if e.type == "summon"), None)
    if skill.kind != "active" or index is None or skill.effects[index].count not in (None, 1):
        return []
    current = skill.effects[index].max_hp_permille or 0
    drafts: list[Draft] = []
    for step in library.flash.rules.summon_hp_steps:  # 強度固定、沒有旋鈕：依序試
        if step <= current:
            continue
        base, effects = base_draft(skill)
        effects[index]["max_hp_permille"] = step
        drafts.append((base, effects))
    return drafts


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
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """蓄力：冷卻 +2（最多 5 回合），威力由預算器依冷卻折抵提高；至少一項一定要嚴格變強
    （FL-1a，:mod:`trpg.skillgen.flash_cost`）。"""
    if skill.kind != "active":
        return []
    cooldown = skill.cost.cooldown or 0
    rules = library.flash.rules
    value = min(cooldown + rules.charge_cooldown_step, rules.max_charge_cooldown)
    if value <= cooldown:
        return []
    base, effects = base_draft(skill)
    base["cost"] = {**base["cost"], "cooldown": value}
    return [(base, effects)]


def _op_light(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """輕巧：AP −1（最少 1），冷卻壓到 0～1 回合，威力由預算器依較低的 AP 係數降低。

    BAL-12b 定：AP 已經是 1 時，改成 ``template.cost_fields`` 依序的冷卻或資源（法力／耐力）減一格
    （冷卻 1；法力、耐力 1 × ``quantity_scale``），每項最少留一格（只減不拿掉）。FL-1a：至少一項
    一定要嚴格變弱、沒有一項變強（:mod:`trpg.skillgen.flash_cost`）。"""
    if skill.kind != "active":
        return []
    if (skill.ap_cost or 1) <= 1:
        return _light_cost_drafts(skill, template.cost_fields, library)
    base, effects = base_draft(skill)
    assert skill.ap_cost is not None  # AP 是 None 或 1 時上面已經改走減資源
    base["ap_cost"] = skill.ap_cost - 1
    cooldown = skill.cost.cooldown
    if cooldown is not None and cooldown > MAX_LIGHT_COOLDOWN:
        base["cost"] = {**base["cost"], "cooldown": MAX_LIGHT_COOLDOWN}
    return [(base, effects)]


def _paid(library: ContentLibrary, field: str, value: int) -> int:
    """卡片上的實付值（我方）：法力照 ``core.mana_cost``，其他照資料值。"""
    return library.ruleset.core.mana_cost(value) if field == "mana" else value


_LIGHT_COST_FIELDS = frozenset({"cooldown", "mana", "stamina"})
"""AP 已是 1 時輕巧能減的代價（BAL-12b 定；AP、源力不在這裡）。"""


def _light_cost_drafts(
    skill: SkillDef, fields: Sequence[str], library: ContentLibrary
) -> list[Draft]:
    """``fields`` 依序各減一格的草稿（法力、耐力一格 1 × ``quantity_scale``、冷卻 1；
    每項最少留一格；
    沒有可減的就不出）。

    FL-1c（06 6.34「費用方向」第 5 點）：「少付」以卡片上的實付值為準。減 1 之後實付沒變（法力照
    ``core.mana_cost`` 四捨五入，例：3 → 2 實付都是 2）就當作沒少付：這一項不出草稿，**也不改試
    後面的項目**（前面已經排進來的照舊）。"""
    drafts: list[Draft] = []
    for field in fields:
        current = getattr(skill.cost, field, None) if field in _LIGHT_COST_FIELDS else None
        step = library.ruleset.core.cost_floor(field)  # X10-2b：量類一格 1 × quantity_scale
        if not isinstance(current, int) or current - step < step:
            continue
        if _paid(library, field, current - step) == _paid(library, field, current):
            break
        base, effects = base_draft(skill)
        base["cost"] = {**base["cost"], field: current - step}
        drafts.append((base, effects))
    return drafts


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
    """觸發範圍 +delta（預設 1）：``trigger.max_distance`` 加 delta；沒有距離上限時看形狀的大小。

    BAL-19e：反應技的單體形狀沒有大小可加，改加射程（固定射程，不超過形狀上限；武器射程不適用）——
    反應的觸發者要在射程內才打得到（6.34.4「觸發範圍 +1」）。"""
    if skill.kind not in ("passive", "reaction"):
        return []
    step = template.delta or 1
    base, effects = base_draft(skill)
    trigger = skill.trigger
    if trigger is not None and trigger.max_distance is not None:
        base["trigger"] = {**base["trigger"], "max_distance": trigger.max_distance + step}
        return [(base, effects)]
    if skill.kind == "reaction" and skill.shape.type == "single":
        return _reaction_reach(skill, step, library)
    if skill.shape.type == "self":
        return []
    grown = grow_shape(library.ruleset, skill.shape, step)
    if grown == skill.shape:
        return []
    base["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def _reaction_reach(skill: SkillDef, step: int, library: ContentLibrary) -> list[Draft]:
    """反應技單體形狀的射程 +``step``（BAL-19e）：固定射程才加，不超過形狀上限。"""
    shape = skill.shape
    param = library.ruleset.shape_def(shape.type).params.get("range")
    if param is None or not isinstance(shape.range, int) or shape.range < 1:
        return []
    value = min(shape.range + step, param.max)
    if value == shape.range:
        return []
    base, effects = base_draft(skill)
    base["shape"] = shape.model_copy(update={"range": value}).model_dump(
        mode="json", exclude_none=True
    )
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
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """每回合觸發次數上限 +1（被動；最多 3，再由驗證器的 6.6 硬上限擋）。"""
    trigger = skill.trigger
    if (
        skill.kind != "passive"
        or trigger is None
        or trigger.max_per_round >= library.flash.rules.max_triggers_per_round
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
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """修正幅度 +：有正的傷害或治療幅度的規則，幅度由預算器重調（旋鈕見 :func:`tuning_extras`）。
    BAL-10b：沒有傷害、治療幅度時，其他有幅度的改變（召喚物 HP、推擊距離、命中後效果的骰子……，
    ``rules.modifier_knobs``）也可以當旋鈕，有條件、沒條件都適用。"""
    if skill.kind != "modifier":
        return []
    base, effects = base_draft(skill)
    if not _modifier_knobs(base["modifiers"], library, op="mod_potency")[1]:
        return []
    return [(base, effects)]


def _op_mod_range(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """作用範圍 +1（3W-2b：照光環半徑）：多一條「範圍 +1」（``area_delta``，範圍型形狀與光環的半徑
    +1）的規則；射程 +1 的規則升成 +2；都不行時多一條「射程 +1」。"""
    if skill.kind != "modifier":
        return []
    limits = library.ruleset.core.skill_limits
    bounds = limits.modifier_bounds
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        if rule.change.range_delta == 1:  # 射程 +1 升成上限（+2）
            base, effects = base_draft(skill)
            base["modifiers"][index]["change"]["range_delta"] = bounds.range_delta_max
            drafts.append((base, effects))
    if len(skill.modifiers) < limits.max_modifiers:
        applies = skill.modifiers[0].applies_to.model_dump(mode="json")
        has_area = any(m.change.area_delta is not None for m in skill.modifiers)
        for change in ({"area_delta": 1}, {"range_delta": 1}):
            if has_area and "area_delta" in change:
                continue
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
    """加第二個關鍵字：條件改成真正的「或」（``ConditionSpec.any_of``，3W-2b；例：燃燒中的敵人 →
    燃燒或潮濕表面上的敵人），規則只有一條。"""
    keyword = variation.keyword
    alternative = None if keyword is None else _graft_condition(library, keyword)
    if skill.kind != "modifier" or alternative is None:
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        condition = rule.condition
        if (
            condition is None
            or condition.any_of is not None
            or condition.model_dump(mode="json", exclude_none=True) == alternative
        ):
            continue
        base, effects = base_draft(skill)
        base["modifiers"][index]["condition"] = {
            **condition.model_dump(mode="json", exclude_none=True),
            "any_of": [alternative],
        }
        drafts.append((base, effects))
    return drafts[:1]


_RELAX_ALTERNATIVES = ("target_hp_below", "self_hp_below")
"""條件放寬時多加的「或」分支（依序試，門檻 ``rules.added_hp_condition_permille``；只改自己的規則
只能用 self_hp_below）。"""


def _op_mod_relax(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """條件放寬一級（3W-2b）：血量門檻放寬 150‰（最多 900‰）；其他條件加一個「或」分支（目標血量低於
    50%；選目標前就決定的規則改用自身血量低於 50%），例：居高臨下 → 居高臨下，或目標血量低於 50%。
    預算照 ``any_of`` 的最寬鬆倍率算，幅度由預算器重調。"""
    if skill.kind != "modifier":
        return []
    rules = library.flash.rules
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        condition = rule.condition
        if condition is None or condition.any_of is not None:
            continue
        if condition.permille is not None:
            widened = min(
                condition.permille + rules.hp_relax_step_permille, rules.hp_relax_max_permille
            )
            if widened == condition.permille:
                continue
            base, effects = base_draft(skill)
            base["modifiers"][index]["condition"]["permille"] = widened
            drafts.append((base, effects))
            continue
        for alternative in _RELAX_ALTERNATIVES:
            base, effects = base_draft(skill)
            added = {"type": alternative, "permille": rules.added_hp_condition_permille}
            base["modifiers"][index]["condition"]["any_of"] = [added]
            drafts.append((base, effects))
        break
    return drafts[:3]


# BAL-10b：修正型被動的持續回合、計數上限、冷卻、代價減輕（6.34.4「修正幅度 +」的同類補充）


def _op_mod_duration(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """持續回合 +1：命中後效果帶的狀態、符文持續回合 +1，或召喚物持續輪數 +1（最多 +2）。每條規則
    各一份草稿，依序試。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        change = rule.change
        if change.on_hit_effects and any(e.duration for e in change.on_hit_effects):
            base, effects = base_draft(skill)
            for effect in base["modifiers"][index]["change"]["on_hit_effects"]:
                if effect.get("duration"):
                    effect["duration"] += 1
            drafts.append((base, effects))
        delta = change.summon_duration_delta
        top = library.ruleset.core.skill_limits.modifier_bounds.summon_duration_delta_max  # HC-4b2
        if delta is not None and delta < top:
            base, effects = base_draft(skill)
            base["modifiers"][index]["change"]["summon_duration_delta"] = delta + 1
            drafts.append((base, effects))
    return drafts


def _op_mod_stack(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """計數上限 +1：「依空欄位數計算」的規則最多多算 1 格（``empty_slots_cap``，不超過主動技能
    欄數）。"""
    if skill.kind != "modifier":
        return []
    slots = min(library.flash.rules.max_empty_slots_cap, library.ruleset.core.skill_slots.active)
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        cap = rule.empty_slots_cap
        if cap is not None and cap < slots:
            base, effects = base_draft(skill)
            base["modifiers"][index]["empty_slots_cap"] = cap + 1
            drafts.append((base, effects))
    return drafts


def _op_mod_cooldown(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """冷卻：命中後冷卻 −1 的規則加深成 −2。"""
    if skill.kind != "modifier":
        return []
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        delta = rule.change.cooldown_delta
        deepest = -library.ruleset.core.skill_limits.modifier_bounds.cooldown_delta_max  # HC-4b2
        if delta is not None and delta > deepest:
            base, effects = base_draft(skill)
            base["modifiers"][index]["change"]["cooldown_delta"] = delta - 1
            drafts.append((base, effects))
    return drafts


def _op_mod_cost(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """代價減輕（修正型被動的「費用」方向）：負的傷害、治療幅度往 0 減輕
    ``rules.modifier_drawback_step`` ‰，命中 −n 改成 −(n−1)。
    BAL-10c（比照 3W-5b，減代價只減不拿掉）：
    減了就歸 0 的代價（AP +1、召喚上限 −1、射程 −1、只剩 1 格的傷害、治療、命中）不出。
    其他規則的幅度由預算器重調；至少留一條規則。每個代價各一份草稿，依序試。"""
    if skill.kind != "modifier" or len(skill.modifiers) < 2:  # noqa: PLR2004 - 至少留一條規則
        return []
    step = library.flash.rules.modifier_drawback_step
    drafts: list[Draft] = []
    for index, rule in enumerate(skill.modifiers):
        change = rule.change
        kind = change.kind
        value = getattr(change, kind)
        base, effects = base_draft(skill)
        if kind in ("damage_permille", "heal_permille", "hit_bonus") and value < 0:
            lighter = min(value + (1 if kind == "hit_bonus" else step), 0)
            if lighter == 0:
                continue  # 減了就消失：不出（BAL-10c）
            base["modifiers"][index]["change"][kind] = lighter
        else:
            continue
        drafts.append((base, effects))
    return drafts


# ---------------------------------------------------------------------------
# 姿態（元素姿態階梯上的換級；維持費在 SkillDef.stance_upkeep）
# ---------------------------------------------------------------------------


def _is_stance_effect(effect: EffectSpec, library: ContentLibrary) -> bool:
    """姿態的「姿態本體」效果：進入形態，或施加姿態狀態（元素姿態階梯上的或 ``stance`` 狀態）。"""
    if effect.type == ENTER_FORM:
        return True
    if effect.type != "apply_status" or effect.status is None:
        return False
    if library.flash.stance_rung(effect.status) is not None:
        return True
    return bool(library.ruleset.status_def(effect.status).stance)


def _stance_index(skill: SkillDef, library: ContentLibrary) -> int | None:
    """姿態本體效果的位置（BAL-10b：多效果姿態也可以，只要恰好一個姿態本體效果；其他效果不動）。"""
    if skill.kind != "stance":
        return None
    found = [i for i, e in enumerate(skill.effects) if _is_stance_effect(e, library)]
    return found[0] if len(found) == 1 else None


def _stance_rung(
    skill: SkillDef, library: ContentLibrary
) -> tuple[tuple[str, ...], int, int] | None:
    """姿態目前的元素姿態階梯、在階梯上的位置與效果的位置；不是元素姿態時 ``None``。"""
    index = _stance_index(skill, library)
    if index is None or skill.form_id is not None:
        return None
    status = skill.effects[index].status
    rung = None if status is None else library.flash.stance_rung(status)
    return None if rung is None else (rung[0], rung[1], index)


def _stance_drafts(
    skill: SkillDef, levels: Sequence[str], upkeep: int, ladder: tuple[str, ...], index: int
) -> list[Draft]:
    """每個候選級別一份草稿（維持費 ``upkeep``）；依序試，第一個通過預算窗與強度下限的是結果。"""
    drafts: list[Draft] = []
    for status in levels:
        if status not in ladder:
            continue
        base, effects = base_draft(skill)
        base["stance_upkeep"] = upkeep
        effects[index]["status"] = status
        drafts.append((base, effects))
    return drafts


def _entry_cost(
    skill: SkillDef, field: str, step: int, library: ContentLibrary
) -> dict[str, Any] | None:
    """姿態的進入代價（施放費用）``field`` 改 ``step`` 格（+1 加重、−1 減輕）後的 ``cost``；做不到
    （姿態的進入 AP 由規則固定、已經是 0、超過上限）時 ``None``。維持費不在這裡（#67、BAL-10b）。

    一格：冷卻 1；法力、耐力是量類，1 × ``quantity_scale``（``CoreRules.cost_floor``，X10-3c）。"""
    if field == "ap_cost":
        return None  # 姿態的 ap_cost 必須是 null（進入固定花 1 AP），沒有可動的
    cost = skill.cost.model_dump(mode="json")
    if field == "cooldown":
        current = skill.cost.cooldown or 0
        value = current + step
        if value < 0 or value > library.flash.rules.max_charge_cooldown:
            return None
        cost["cooldown"] = value or None
        return cost
    current = int(getattr(skill.cost, field))
    unit = library.ruleset.core.cost_floor(field)  # X10-3c：量類一格 1 × quantity_scale
    value = current + step * unit
    if value < (unit if step < 0 else 0):
        return None  # 法力、耐力減到 0 ＝ 代價消失，最少留一格（BAL-10c）
    cost[field] = value
    return cost


def _form_cost_drafts(
    skill: SkillDef, template: FlashTemplate, library: ContentLibrary, *, down: bool
) -> list[Draft]:
    """變身姿態的費用類（BAL-10b）：維持費照形態種類固定（#67），改用進入代價（``template.cost_fields``
    依序）當費用旋鈕——輕巧＝進入代價 −1、形態幅度降一格；蓄力＝進入代價 +1、形態幅度提高。模板沒填
    ``cost_fields`` 時不出（同 BAL-2c）。"""
    drafts: list[Draft] = []
    for field in template.cost_fields:
        cost = _entry_cost(skill, field, -1 if down else 1, library)
        if cost is not None:
            drafts += _magnitude_drafts(skill, library, 0, down=down, cost=cost)
    return drafts


def _op_stance_light(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """輕巧（姿態）：維持費 −1，效果降低一級；沒有維持費可減就不出。

    - 元素姿態（有階梯）：換到較低的級別；
    - 其他姿態狀態的姿態（狂怒、堅壁…）：姿態幅度降一格（不低於 100%）；
    - 變身姿態：見 :func:`_form_cost_drafts`（進入代價 −1）。
    多效果姿態（BAL-10b）只動姿態本體那個效果。"""
    family = _stance_family(skill, library)
    if family == "form":
        return _form_cost_drafts(skill, template, library, down=True)
    if family == "status" and skill.stance_upkeep > 0:
        return _magnitude_drafts(skill, library, skill.stance_upkeep - 1, down=True)
    rung = _stance_rung(skill, library)
    if rung is None or skill.stance_upkeep <= 0:
        return []
    ladder, position, index = rung
    return _stance_drafts(skill, ladder[:position][::-1], skill.stance_upkeep - 1, ladder, index)


def _op_stance_heavy(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """蓄力（姿態）：維持費 +1（最多 2），效果提高一級。

    - 元素姿態：換到較高的級別；其他姿態狀態的姿態：姿態幅度提高。
    - 變身姿態：見 :func:`_form_cost_drafts`（進入代價 +1）。"""
    family = _stance_family(skill, library)
    if family == "form":
        return _form_cost_drafts(skill, template, library, down=False)
    top = library.ruleset.core.skill_limits.max_stance_upkeep  # 維持費上限（HC-4d）
    if family == "status" and skill.stance_upkeep < top:
        return _magnitude_drafts(skill, library, skill.stance_upkeep + 1, down=False)
    rung = _stance_rung(skill, library)
    if rung is None or skill.stance_upkeep >= top:
        return []
    ladder, position, index = rung
    return _stance_drafts(skill, ladder[position + 1 :], skill.stance_upkeep + 1, ladder, index)


def _op_stance_potency(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """修正（姿態）：維持費不變，效果提高（預算分數嚴格變大）。

    - 元素姿態：換到較高的級別；其他姿態狀態的姿態：姿態幅度提高。
    - 變身姿態（BAL-2c）：形態幅度（``enter_form.magnitude_permille``）提高；維持費照形態種類
      固定。"""
    family = _stance_family(skill, library)
    if family in ("status", "form"):
        return _magnitude_drafts(skill, library, skill.stance_upkeep, down=False)
    rung = _stance_rung(skill, library)
    if rung is None:
        return []
    ladder, position, index = rung
    return _stance_drafts(skill, ladder[position + 1 :], skill.stance_upkeep, ladder, index)


def _op_stance_enter_light(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """進入代價 −1（姿態，BAL-10b）：施放費用（``template.cost_fields`` 依序）減一格（冷卻 1；法力、
    耐力 1 × ``quantity_scale``），姿態本體與維持費都不動（#67）。所有姿態（元素、白板、變身、
    多效果）都適用；沒有進入代價可減就不出。"""
    if _stance_family(skill, library) is None:
        return []
    drafts: list[Draft] = []
    for field in template.cost_fields:
        cost = _entry_cost(skill, field, -1, library)
        if cost is not None:
            base, effects = base_draft(skill)
            base["cost"] = cost
            drafts.append((base, effects))
    return drafts


def _op_stance_enter_heavy(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """沉勢（姿態，BAL-19e）：進入代價（``template.cost_fields`` 依序，法力、耐力）加一格（1 ×
    ``quantity_scale``），姿態本體提高一級（元素姿態換到較高的級別、其他姿態狀態的姿態幅度提高）；
    維持費不動（#67）。

    ``stance_enter_light`` 的反向。變身姿態不出（BAL-10c：變身姿態只出修正類）；進入冷卻不算代價
    （BAL-10c），模板不列。"""
    family = _stance_family(skill, library)
    if family not in ("status", "ladder"):
        return []
    drafts: list[Draft] = []
    for field in template.cost_fields:
        cost = _entry_cost(skill, field, 1, library)
        if cost is None:
            continue
        for base, effects in _stronger_body(skill, library):
            base["cost"] = cost
            drafts.append((base, effects))
    return drafts


def _stronger_body(skill: SkillDef, library: ContentLibrary) -> list[Draft]:
    """姿態本體往上一級的草稿（維持費不變）：元素姿態換到較高級別、其他姿態狀態的幅度提高。"""
    if _stance_family(skill, library) == "status":
        return _magnitude_drafts(skill, library, skill.stance_upkeep, down=False)
    rung = _stance_rung(skill, library)
    if rung is None:
        return []
    ladder, position, index = rung
    return _stance_drafts(skill, ladder[position + 1 :], skill.stance_upkeep, ladder, index)


def _weaker_body(skill: SkillDef, library: ContentLibrary) -> list[Draft]:
    """姿態本體往下一級的草稿（維持費不變；由近到遠）：附帶效果放不進預算時用。"""
    if _stance_family(skill, library) == "status":
        return _magnitude_drafts(skill, library, skill.stance_upkeep, down=True)
    rung = _stance_rung(skill, library)
    if rung is None:
        return []
    ladder, position, index = rung
    return _stance_drafts(skill, ladder[:position][::-1], skill.stance_upkeep, ladder, index)


def _op_self_rider(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """附帶護身（BAL-19e）：多一個作用於自己的效果（``template.rider``：護盾、治療、回復資源、淨化）。

    - 姿態（06 6.34.4 姿態的「修正」類）：進入姿態時生效。只給只有姿態本體一個效果的姿態（骨架的附帶
      效果最多 1 個；變身姿態的 ``enter_form`` 必須是唯一效果，不出）。先試姿態本體不變（附帶的骰子
      由預算器重調），放不進預算時再試本體降一級換附帶。
    - 反應（「觸發」類的效果 +）：反應觸發時順便生效。只給只有一個效果、而且沒有同種效果的反應
      （附帶效果最多 1 個；擋攻擊 ``intercept`` 的不出）；主要效果由預算器一起重調。
    強度下限照 6.34.3（預算分數不低於閃現前）。"""
    rider = template.rider
    if rider is None or len(skill.effects) != 1:
        return []
    extra = rider.model_dump(mode="json", exclude_none=True)
    base, effects = base_draft(skill)
    if skill.kind == "reaction":
        if skill.effects[0].type in (rider.type, "intercept"):
            return []
        return [(base, [*effects, extra])]
    if _stance_family(skill, library) not in ("status", "ladder"):
        return []
    drafts: list[Draft] = [(base, [*effects, copy.deepcopy(extra)])]
    for lowered, lowered_effects in _weaker_body(skill, library):
        drafts.append((lowered, [*lowered_effects, copy.deepcopy(extra)]))
    return drafts


def _stance_family(skill: SkillDef, library: ContentLibrary) -> str | None:
    """姿態屬於哪一族（BAL-2b）：``ladder`` 元素姿態階梯、``form`` 變身姿態（BAL-2c）、``status``
    其他姿態狀態的姿態（白板姿態：狂怒、堅壁…）；不是姿態或做不了時 ``None``。BAL-10b：多效果姿態
    看它唯一的姿態本體效果。"""
    if skill.kind != "stance":
        return None
    if skill.form_id is not None:
        return "form"
    index = _stance_index(skill, library)
    status_id = None if index is None else skill.effects[index].status
    if status_id is None:
        return None
    return "ladder" if library.flash.stance_rung(status_id) is not None else "status"


def _magnitude_drafts(
    skill: SkillDef,
    library: ContentLibrary,
    upkeep: int,
    *,
    down: bool,
    cost: dict[str, Any] | None = None,
) -> list[Draft]:
    """沒有階梯的姿態與變身姿態：維持費改成 ``upkeep``（變身姿態沒有每招維持費，不動），
    幅度（``magnitude_permille``，有利那一邊離 100% 的距離）換一格（``down`` 往低、否則往高；級距見
    ``rules.stance_magnitudes``，變身姿態用較細的 ``rules.form_magnitudes``）。``cost`` 是換掉的
    進入代價（BAL-10b，變身姿態的費用類）。依距離現在由近到遠各一份草稿，第一個通過預算窗與強度下限
    的是結果。"""
    index = _stance_index(skill, library)
    if index is None:
        return []
    start = skill.effects[index].magnitude_permille or 1000
    form = skill.form_id is not None
    rules = library.flash.rules
    values = rules.form_magnitudes if form else rules.stance_magnitudes
    wanted = [v for v in values if v < start][::-1] if down else [v for v in values if v > start]
    drafts: list[Draft] = []
    for value in wanted:
        base, effects = base_draft(skill)
        if not form:
            base["stance_upkeep"] = upkeep
        if cost is not None:
            base["cost"] = cost
        effects[index]["magnitude_permille"] = value
        drafts.append((base, effects))
    return drafts


# ---------------------------------------------------------------------------
# SK-1（#166，06 6.38 第 3 點）：側變與補模板
# ---------------------------------------------------------------------------


def _op_reshape_skeleton(
    skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """側變「換形狀並換骨架」：原骨架不允許新形狀時（例：打擊骨架只能單體），改試模板的
    ``skeletons``（範圍、連擊），比照收束的換骨架寫法。原骨架本來就允許的形狀交給「換形狀」
    （``reshape``），這裡不出，避免同一個變化出兩次。"""
    if not _reshapable(skill) or not any(e.type == "damage" for e in skill.effects):
        return []
    own = library.skeletons.get(skill.skeleton)
    shapes = (variation.shape,) if variation.shape is not None else template.shapes
    drafts: list[Draft] = []
    for shape in shapes:
        if shape.type == skill.shape.type or (own is not None and shape.type in own.shapes):
            continue
        for name in template.skeletons:
            skeleton = library.skeletons.get(name)
            if skeleton is None or skill.kind not in skeleton.kinds:
                continue
            if shape.type not in skeleton.shapes:
                continue
            base, effects = base_draft(skill)
            base["shape"] = shape.model_dump(mode="json", exclude_none=True)
            base["skeleton"] = name
            drafts.append((base, effects))
    return drafts


def _op_element_swap(
    skill: SkillDef, template: FlashTemplate, variation: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """側變「換元素」：這招所有帶元素的傷害效果（同一種元素）改成 ``variation.element``；關鍵字由
    元素推導，跟著換。只給「傷害只有一種非物理元素、其他效果不帶元素」的招（附帶的狀態、表面、
    區域跟元素綁在一起，換了會變成另一招，先不出）。"""
    new = variation.element
    if new is None or skill.kind not in ("active", "passive", "reaction") or skill.trap is not None:
        return []
    if template.elements and new not in template.elements:
        return []
    damages = [e for e in skill.effects if e.type == "damage"]
    elements = {e.element.value for e in damages if e.element is not None}
    if len(elements) != 1 or elements in ({new}, {Element.PHYSICAL.value}):
        return []
    if any(e.element is not None for e in skill.effects if e.type != "damage"):
        return []
    if skill.followup is not None or skill.variants:
        return []
    base, effects = base_draft(skill)
    for effect in effects:
        if effect["type"] == "damage" and effect.get("element") is not None:
            effect["element"] = new
    return [(base, effects)]


_PUSH_PULL = {"push": "pull", "pull": "push"}


def _op_push_pull(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """側變「推 ↔ 拉」：推擊換成拉扯（或反過來），距離與其他欄位照舊（強度依預算重算）。只給帶
    傷害的招（純位移的招換了之後沒有旋鈕能把強度調回預算窗）。"""
    if skill.kind != "active" or skill.trap is not None:
        return []
    if not any(e.type == "damage" for e in skill.effects):
        return []
    index = next((i for i, e in enumerate(skill.effects) if e.type in _PUSH_PULL), None)
    if index is None:
        return []
    base, effects = base_draft(skill)
    effects[index]["type"] = _PUSH_PULL[effects[index]["type"]]
    return [(base, effects)]


def _op_trigger_swap(
    skill: SkillDef, template: FlashTemplate, variation: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """側變「換觸發時機」：被動的 ``trigger.event``（或反應的 ``reaction.event``）照模板的
    ``trigger_swaps`` 換成 ``variation.keyword``（例：命中時 → 暴擊時、受傷時）。合不合法（另一方、
    骨架、預算）交給驗證器。"""
    target = variation.keyword
    if target is None:
        return []
    if skill.kind == "passive" and skill.trigger is not None:
        current, field = skill.trigger.event, "trigger"
    elif skill.kind == "reaction" and skill.reaction is not None and not skill.reaction.aid:
        current, field = str(skill.reaction.event), "reaction"
    else:
        return []
    if (current, target) not in template.trigger_swaps:
        return []
    base, effects = base_draft(skill)
    base[field] = {**base[field], "event": target}
    return [(base, effects)]


def _op_blood_price(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[Draft]:
    """側變「以血支付」：法力、耐力只留 1 點 × ``quantity_scale``（驗證器規定主動技至少花 1 點
    資源），其餘改付最大 HP 的千分比（``cost.hp_percent``）。生命代價的折抵＝省下的法力／耐力折抵 ＋
    ``rules.blood_bonus_permille``（不超過預算表的 ``hp_cap``），多出來的由預算器換成威力
    （「略升」）。"""
    cost = skill.cost
    if skill.kind != "active" or cost.hp_percent is not None:
        return []
    scale = library.ruleset.core.quantity_scale  # X10-2a：留 1 × 倍率；折抵每 scale 點計
    mana, stamina = min(cost.mana, scale), min(cost.stamina, scale)
    allowance = library.budget.allowance
    saved = (cost.mana - mana) * allowance.mana_per_point // scale + (
        cost.stamina - stamina
    ) * allowance.mana_per_point // (allowance.stamina_per_mana * scale)
    if saved <= 0:
        return []
    bonus = library.flash.rules.blood_bonus_permille
    hp = min(saved + bonus, allowance.hp_cap) // allowance.hp_per_permille
    if hp < 1:
        return []
    base, effects = base_draft(skill)
    base["cost"] = {**base["cost"], "mana": mana, "stamina": stamina, "hp_percent": hp}
    return [(base, effects)]


def _op_once_per_battle(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """每場一次：``cost.uses_per_battle`` 設成 1、拿掉冷卻（每場一次之後冷卻沒有意義），多出來的
    折抵由預算器換成威力。已經有次數上限的不出。"""
    if skill.kind != "active" or skill.cost.uses_per_battle is not None:
        return []
    base, effects = base_draft(skill)
    cost = {**base["cost"], "uses_per_battle": 1}
    cost.pop("cooldown", None)
    base["cost"] = cost
    return [(base, effects)]


def _op_kill_reset(
    skill: SkillDef, _t: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """擊殺重置（6.18 F）：第一個傷害效果加 ``on_kill: refund_cooldown``（這招擊殺目標時冷卻歸零）；
    要有冷卻。"""
    base, effects = base_draft(skill)
    index = _first_damage(effects)
    if skill.kind != "active" or index is None or "on_kill" in effects[index]:
        return []
    if not skill.cost.cooldown:
        return []
    effects[index]["on_kill"] = [{"type": "refund_cooldown"}]
    return [(base, effects)]


def _op_active_rider(
    skill: SkillDef, template: FlashTemplate, _v: Variation, _lib: ContentLibrary
) -> list[Draft]:
    """主動技多一個附帶效果（``template.rider``）：

    - ``affects: self``（蓄勢）：要有傷害效果；命中後自己得到狀態（例：激昂 1 回合）。
    - 其他（附淨化、附加速）：只給輔助技（有治療效果、沒有傷害），對象照治療的對象。
    數值是起點，由預算器重調；附帶效果的個數上限、合不合法交給驗證器。"""
    rider = template.rider
    if rider is None or skill.kind != "active" or skill.trap is not None:
        return []
    extra = rider.model_dump(mode="json", exclude_none=True)
    base, effects = base_draft(skill)
    if any(e["type"] == extra["type"] and e.get("status") == extra.get("status") for e in effects):
        return []
    if rider.affects == "self":
        if not any(e.type == "damage" for e in skill.effects):
            return []
        return [(base, [*effects, extra])]
    heal = next((e for e in skill.effects if e.type == "heal"), None)
    if heal is None or any(e.type in ("damage", "delayed_damage") for e in skill.effects):
        return []
    extra.pop("affects", None)
    if heal.affects is not None:
        extra["affects"] = heal.affects
    return [(base, [*effects, extra])]


def _conditional_bonus(
    skill: SkillDef, condition: dict[str, Any], library: ContentLibrary
) -> list[Draft]:
    """加一段有條件的傷害（同「借勢」的寫法：目標符合條件時加碼）；數值由預算器補。"""
    if skill.kind != "active" or skill.trap is not None or _graft_blocked(skill):
        return []
    index = _first_damage([e.model_dump(mode="json") for e in skill.effects])
    if index is None:
        return []
    base, effects = base_draft(skill)
    if any(e.get("condition") == condition for e in effects):
        return []
    extra = _new_damage(library, skill, effects[index], _damage_element(skill))
    extra["condition"] = condition
    return [(base, [*effects, extra])]


def _op_surface_exploit(
    skill: SkillDef, template: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """利用地面：目標站在 ``variation.keyword``（表面 ID，模板的 ``surfaces``）上時多一段傷害。"""
    surface = variation.keyword
    if surface is None or surface not in template.surfaces:
        return []
    return _conditional_bonus(skill, {"type": "target_on_surface", "surface": surface}, library)


_DISTANCE_CONDITIONS = ("point_blank", "long_range")


def _op_distance_bonus(
    skill: SkillDef, _t: FlashTemplate, variation: Variation, library: ContentLibrary
) -> list[Draft]:
    """距離加碼（6.38 第 1 點的條件）：``variation.keyword`` 是 ``point_blank``（貼身）或
    ``long_range``（遠距）；目標符合時多一段傷害。只給射程用得上的招（同組合器：貼身要固定射程
    至少 2、遠距要固定射程達到遠距門檻）。"""
    kind = variation.keyword
    reach = skill.shape.range
    if kind not in _DISTANCE_CONDITIONS or not isinstance(reach, int):
        return []
    point_blank = library.composer.condition.point_blank_min_reach
    need = point_blank if kind == "point_blank" else library.ruleset.core.far_distance
    if reach < need:
        return []
    return _conditional_bonus(skill, {"type": kind}, library)


# ---------------------------------------------------------------------------
# 登錄表與重調的額外旋鈕
# ---------------------------------------------------------------------------

FLASH_OPS: dict[str, FlashOp] = {
    "area": _op_area,
    "range": _op_range,
    "reshape": _op_reshape,
    "terrain_area": _op_terrain_area,
    "multi_hit": _op_multi_hit,
    "followup": _op_followup,
    "element": _op_element,
    "keyword_imbue": _keyword_op("bridge_imbue", "makes"),
    "keyword_exploit": _keyword_op("bridge_exploit", "uses"),
    "extend": _op_extend,
    "kill_refund": _op_kill_refund,
    "summon_toughen": _op_summon_toughen,
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
    "stance_light": _op_stance_light,
    "stance_heavy": _op_stance_heavy,
    "stance_potency": _op_stance_potency,
    # BAL-10b
    "followup_potency": _op_followup_potency,
    "followup_area": _op_followup_area,
    "followup_range": _op_followup_range,
    "followup_element": _op_followup_element,
    "mod_duration": _op_mod_duration,
    "mod_stack": _op_mod_stack,
    "mod_cooldown": _op_mod_cooldown,
    "mod_cost": _op_mod_cost,
    "stance_enter_light": _op_stance_enter_light,
    # BAL-19e
    "stance_enter_heavy": _op_stance_enter_heavy,
    "self_rider": _op_self_rider,
    # SK-1（#166，06 6.38 第 3 點）
    "reshape_skeleton": _op_reshape_skeleton,
    "element_swap": _op_element_swap,
    "push_pull": _op_push_pull,
    "trigger_swap": _op_trigger_swap,
    "blood_price": _op_blood_price,
    "once_per_battle": _op_once_per_battle,
    "kill_reset": _op_kill_reset,
    "active_rider": _op_active_rider,
    "surface_exploit": _op_surface_exploit,
    "distance_bonus": _op_distance_bonus,
}
"""小變化的改法登錄表（``op`` → 草稿）。資料裡 ``op`` 沒有登錄的模板不會出現
（:func:`trpg.skillgen.flash_derive.unimplemented_ops` 列出）。"""


def tuning_extras(
    op: str, base: dict[str, Any], library: ContentLibrary
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """重調時除了 ``effects`` 以外要一起調的字典與旋鈕（旋鈕的 ``index`` 是回傳字典的位置）：

    - 修正型被動：每條規則的 ``change``（傷害、治療幅度；BAL-10b 的修正模板在沒有傷害、治療幅度時
      另外用 ``rules.modifier_knobs`` 的幅度）；
    - 接續段：``followup.effects`` 的傷害（模板新加的那一段；BAL-10b 接續段強化類同樣調接續段）。
    """
    if base.get("kind") == "modifier":
        return _modifier_knobs(base["modifiers"], library, op=op)
    if op in FOLLOWUP_OPS and base.get("followup"):
        effects = base["followup"]["effects"]
        # BAL-10b 的接續段強化：接續段原有的數值只往上調（從目前的值起），不重設到最弱——內建複合技的
        # 接續段常已超過第一段骨架的核心占比，從最弱往上調會被占比限制擋住
        if op == "followup":  # 3W-2 起的行為（升階重配、完整技能也走這裡），照舊不動
            dice = dice_ladder(library.composer.dice)
            multipliers = multiplier_ladder(library)
            return effects, [
                Knob(i, "dice", dice)
                if "dice" in e
                else Knob(i, "multiplier_permille", multipliers)
                for i, e in enumerate(effects)
                if e["type"] == "damage"
            ]
        knobs = []
        for i, e in enumerate(effects):
            if e["type"] in _FOLLOWUP_TUNED:
                field, ladder = _followup_knob(e, library)
                knobs.append(Knob(i, field, _from_current(ladder, e.get(field), keep=True)))
        return effects, knobs
    return [], []


TRIGGER_FINE_OPS = frozenset({"potency"})
"""用「觸發效果 +1 固定值」細旋鈕的改法（BAL-12b 定：被動、反應的「效果 +」）。"""


def trigger_fine_knobs(
    op: str, base: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary
) -> list[Knob]:
    """被動、反應的「效果 +」（BAL-12b 定）：帶骰子的傷害（只限法術技）、治療、護盾的
    ``flat_bonus``（無 → +1 … +``rules.trigger_flat_bonus``）；``index`` 指向 ``effects``。只在一般
    重調失敗後才加（呼叫者決定）；``rules.trigger_flat_bonus`` 為 0、不是被動／反應時是空的。"""
    top = library.flash.rules.trigger_flat_bonus
    if op not in TRIGGER_FINE_OPS or not top or base.get("kind") not in ("passive", "reaction"):
        return []
    spell = base.get("category") == "spell"
    scale = library.ruleset.core.quantity_scale  # 固定值是量類：步距 × 倍率（X10-2a）
    values: tuple[int | None, ...] = (None, *range(scale, top + 1, scale))
    return [
        Knob(i, "flat_bonus", values)
        for i, e in enumerate(effects)
        if e["type"] in FLAT_BONUS_EFFECTS
        and (spell or e["type"] != "damage")
        and e.get("dice") is not None
        and not e.get("flat_bonus")
    ]


def _from_current(values: tuple[Any, ...], current: Any, keep: bool) -> tuple[Any, ...]:
    """旋鈕階梯從目前的值開始（``keep`` 且目前的值在階梯上時）；否則整條階梯。"""
    if keep and current in values:
        return values[values.index(current) :]
    return values


NEW_MOD_OPS = frozenset({"mod_duration", "mod_stack", "mod_cooldown", "mod_cost"})
"""BAL-10b 新增的修正模板。"""
RECLAIM_MOD_OP = "reclaim_modifier"
"""收回家族（BAL-10e 專注，:mod:`trpg.skillgen.flash_reclaim`）換修正幅度時用的旋鈕組：同
:data:`NEW_MOD_OPS` 的細階梯與其他幅度（結構一變點數常跳太多，要能往下補）。"""
FINE_MOD_OPS = NEW_MOD_OPS | {RECLAIM_MOD_OP}
EXTENDED_MOD_OPS = FINE_MOD_OPS | {"mod_potency"}
"""會用 ``rules.modifier_knobs`` 幅度的修正模板（``mod_potency`` 只在沒有傷害、治療幅度時；
BAL-10b）。"""


def _modifier_knobs(
    rules: list[dict[str, Any]], library: ContentLibrary, *, op: str
) -> tuple[list[dict[str, Any]], list[Knob]]:
    """修正規則重調的字典與旋鈕。

    - 正的傷害、治療幅度：一般用 :data:`MODIFIER_LADDER`；BAL-10b 新增的修正模板
      （:data:`NEW_MOD_OPS`）用較細的 ``rules.modifier_fine_step`` 階梯（結構一變點數常跳太多，
      要能往下補）。
    - :data:`EXTENDED_MOD_OPS` 再加 ``rules.modifier_knobs`` 列的幅度與命中後效果的骰子
      （``rules.modifier_on_hit_dice``；效果字典接在後面）；``mod_potency`` 只在沒有傷害、治療
      幅度時加，有的時候照舊。"""
    flash = library.flash.rules
    changes = [m["change"] for m in rules]
    fine = op in FINE_MOD_OPS
    ladder = tuple(range(flash.modifier_fine_step, 1001, flash.modifier_fine_step))
    plain = MODIFIER_LADDER
    if op == "mod_potency" and flash.modifier_potency_step is not None:  # BAL-11b：只在閃現強效
        plain = tuple(range(flash.modifier_potency_step, 1001, flash.modifier_potency_step))
    knobs = [
        Knob(i, name, ladder if fine else plain)
        for i, change in enumerate(changes)
        for name in _MAGNITUDES
        if (change.get(name) or 0) > 0
    ]
    if op not in EXTENDED_MOD_OPS or (knobs and not fine):
        return changes, knobs
    extra = list(changes)
    for i, change in enumerate(changes):
        for name, values in flash.modifier_knobs.items():
            if change.get(name) is not None:
                knobs.append(Knob(i, name, values))
    if flash.modifier_on_hit_dice:
        dice = dice_ladder(library.composer.dice)
        for change in changes:
            for effect in change.get("on_hit_effects") or ():
                if effect.get("dice") is not None:
                    extra.append(effect)
                    knobs.append(Knob(len(extra) - 1, "dice", dice))
    return extra, knobs
