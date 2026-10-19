"""從技能內容推導的資訊：效果的實際對象與機制標籤（``docs/phases/Phase2B計畫.md`` 4.2）。

機制標籤由驗證器推導，不由人填寫；協同係數與互斥規則都以它們為基礎。推導只看資料欄位
（``control_group``、``on_turn_start_damage`` 等），不寫死狀態 ID。
"""

from __future__ import annotations

from trpg.content.battle import StatusDef
from trpg.content.environment import SurfaceDef
from trpg.content.library import Ruleset
from trpg.content.skill_rules import MECHANIC_TAGS
from trpg.content.skills import Affects, EffectSpec, SkillDef, default_affects

__all__ = ["affect_set", "mechanic_tags", "resolved_affects"]

_NEUTRAL = 1000  # 千分比倍率 ×1
_DISPLACE = frozenset(
    {
        "push",
        "pull",
        "teleport",
        "knock_prone",
        "dash",
        "leap",
        "swap",
        "teleport_target",
        "swap_any",
    }
)
_TERRAIN = frozenset({"create_obstacle", "destroy_object", "raise_terrain", "lower_terrain"})
_SINGLE_TARGET_SHAPES = frozenset({"self", "single", "ground_tile"})


def resolved_affects(rules: Ruleset, effect: EffectSpec) -> Affects:
    """效果的實際對象（省略 ``affects`` 時用原語的預設值）。"""
    if effect.affects is not None:
        return effect.affects
    return default_affects(rules.primitives.by_id()[effect.type])


def affect_set(affects: Affects) -> frozenset[str]:
    """對象的比對集合：``all``（敵我不分）同時算敵方與友方。"""
    if affects == "all":
        return frozenset({"all", "enemies", "allies"})
    return frozenset({affects})


def mechanic_tags(skill: SkillDef, rules: Ruleset) -> tuple[str, ...]:
    """技能的機制標籤（依 ``MECHANIC_TAGS`` 的順序）。"""
    statuses = rules.statuses.by_id()
    found: set[str] = set()
    if skill.shape.type not in _SINGLE_TARGET_SHAPES or (
        skill.trap is not None and skill.trap.shape != "single"
    ):
        found.add("area")
    for effect in skill.effects:
        kind = effect.type
        if kind == "damage":
            found.add("damage")
        elif kind == "heal":
            found.add("heal")
        elif kind in _DISPLACE:
            found.add("displace")
        elif kind in _TERRAIN:
            found.add("terrain")
        elif kind == "create_surface":
            found.add("surface")
            if effect.surface is not None and _surface_deals_damage(
                rules.surfaces.get(effect.surface), statuses
            ):
                found.add("dot")
        elif kind == "apply_status" and effect.status in statuses:
            found |= _status_tags(statuses[effect.status])
    return tuple(tag for tag in MECHANIC_TAGS if tag in found)


def _surface_deals_damage(surface: SurfaceDef, statuses: dict[str, StatusDef]) -> bool:
    """表面在回合開始造成傷害（直接傷害，或施加有回合開始傷害的狀態如燃燒）。"""
    tick = surface.on_turn_start
    if tick is None:
        return False
    if tick.damage is not None:
        return True
    status = statuses.get(tick.apply_status) if tick.apply_status is not None else None
    return status is not None and status.on_turn_start_damage is not None


def _status_tags(status: StatusDef) -> set[str]:
    tags: set[str] = set()
    if status.control_group is not None:
        tags.add("control")
    if status.damage_dealt_permille < _NEUTRAL or status.damage_taken_permille > _NEUTRAL:
        tags.add("debuff")
    if status.on_turn_start_damage is not None:
        tags.add("dot")
    return tags
