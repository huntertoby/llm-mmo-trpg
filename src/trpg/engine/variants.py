"""戰場變奏（Phase 3-25a，``docs/design/06-技能.md`` 6.24；``docs/phases/Phase3計畫.md`` 33）。

技能可以帶 0～2 個變奏（:class:`~trpg.content.skills.VariantSpec`）：條件成立時，施放的是套上替換
內容的型態（:meth:`~trpg.content.skills.SkillDef.variant_form`）。多個成立時取資料中排在前面的。

結算順序（PM 決定 #3）：**基礎 → 變奏（:func:`varied_skill`）→ 修正
（:func:`~trpg.engine.modifiers.shaped_skill`）**（Phase 3-26a 的技能等級在 3W-5b 移除）。
施放、預覽、合法動作與 AI 都經過 :func:`varied_skill`。

四種條件（PM 決定 #2）：

- ``caster_surface``：施放者所在格的表面在清單中；
- ``caster_high_ground``：施放者所在格比 **目標點** 高至少 1 層；
- ``caster_adjacent_blocker``：施放者八方向相鄰的格子（地圖內）有牆壁（:func:`is_wall`）或
  ``blocks_move`` 物件；地圖邊緣不算；
- ``target_surface``：**目標點** 的表面在清單中。

目標點（:func:`target_point`）：單位目標為該單位所在格；否則為指定格；否則為目標物件所在格；
方向型與自身型沒有目標點，依賴目標點的條件一律不成立。

這個模組只讀狀態（純函式、確定性）。
"""

from __future__ import annotations

from trpg.content.skills import SkillDef, VariantSpec, VariantWhen
from trpg.engine.actions import UseSkill
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.shapes import is_wall
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "chosen_variant",
    "possible_variants",
    "target_point",
    "variant_holds",
    "varied_skill",
]

_EIGHT: tuple[XY, ...] = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def target_point(state: BattleState, action: UseSkill) -> XY | None:
    """``action`` 的目標點：單位目標（``target_id``）所在格 → 指定格（``target_pos``）→ 目標物件
    所在格；都沒有（方向型、自身型）時為 ``None``。"""
    if action.target_id is not None:
        unit = state.units.get(action.target_id)
        if unit is not None:
            return unit.xy
    if action.target_pos is not None:
        return (action.target_pos.x, action.target_pos.y)
    if action.target_object_id is not None:
        obj = state.objects.get(action.target_object_id)
        if obj is not None:
            return obj.xy
    return None


def _surface_id(state: BattleState, xy: XY) -> str:
    return state.tile(*xy).surface.value


def _adjacent_blocker(state: BattleState, xy: XY) -> bool:
    x, y = xy
    for dx, dy in _EIGHT:
        cell = (x + dx, y + dy)
        if not state.in_bounds(*cell):
            continue
        if is_wall(state, cell) or state.object_has_tag(*cell, "blocks_move"):
            return True
    return False


def variant_holds(
    state: BattleState, caster: UnitState, when: VariantWhen, target: XY | None
) -> bool:
    """條件 ``when`` 對施放者 ``caster`` 與目標點 ``target`` 是否成立。"""
    if when.caster_surface is not None:
        return _surface_id(state, caster.xy) in when.caster_surface
    if when.caster_adjacent_blocker is not None:
        return _adjacent_blocker(state, caster.xy)
    if target is None or not state.in_bounds(*target):
        return False
    if when.caster_high_ground is not None:
        return state.tile(*caster.xy).height - state.tile(*target).height >= 1
    assert when.target_surface is not None
    return _surface_id(state, target) in when.target_surface


def chosen_variant(
    state: BattleState, caster: UnitState, skill: SkillDef, target: XY | None
) -> VariantSpec | None:
    """對目標點 ``target`` 生效的變奏：資料中第一個條件成立的；都不成立時為 ``None``。"""
    for variant in skill.variants:
        if variant_holds(state, caster, variant.when, target):
            return variant
    return None


def varied_skill(
    state: BattleState, caster: UnitState, skill: SkillDef, target: XY | None
) -> tuple[SkillDef, str | None]:
    """套用變奏後的技能與變奏 ID（沒有變奏成立時回傳原技能（同一個物件）與 ``None``）。"""
    if not skill.variants:
        return skill, None
    variant = chosen_variant(state, caster, skill, target)
    if variant is None:
        return skill, None
    return skill.variant_form(variant.id), variant.id


def possible_variants(
    state: BattleState, caster: UnitState, skill: SkillDef
) -> tuple[str | None, ...]:
    """在目前位置、對某個目標點可能選出的型態（變奏 ID；``None`` ＝ 基礎型態），依資料順序。

    不依賴目標點的條件現在就能判定：成立時它之後的型態（含基礎型態）都不可能被選到；不成立時略過。
    依賴目標點的條件要看各個目標點，所以都列入。合法動作以「各型態候選的聯集，目標點選出的型態
    接受它才合法」列舉（PM 決定 #4）。"""
    found: list[str | None] = []
    for variant in skill.variants:
        if variant.when.target_dependent:
            found.append(variant.id)
        elif variant_holds(state, caster, variant.when, None):
            found.append(variant.id)
            return tuple(found)
    found.append(None)
    return tuple(found)
