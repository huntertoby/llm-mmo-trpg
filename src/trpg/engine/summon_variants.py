"""召喚技能的分歧進化在召喚當下的結算（Phase 3-33f2，``docs/design/06-技能.md`` 6.28、6.29.4）。

- **加深**（``summon.max_hp_permille`` ＋ ``summon.trait``）：召喚物最大 HP 多 ‰，並多一個小特性
  （``core.summon_traits``：護甲、移動、暴擊範圍）。
- **橋接**（``summon.infusion``）：召喚物固有第二個灌注關鍵字（``UnitState.bonus_infusion``），
  和範本固有的、施放時選的並存；由 :func:`trpg.engine.summons.summon_unit` 在算灌注 HP 前設定。
- **數量型**（``summon.count: 2`` ＋ ``summon.power_permille``）：一次召喚 2 隻，每隻最大 HP 與傷害
  只有一般的 ``power_permille`` ‰（``UnitState.summon_power_permille`` 乘在傷害倍率上）；第二隻
  放在第一隻旁邊第一個合法的空格（東、西、南、北的順序）。
"""

from __future__ import annotations

from trpg.content.battle import WeaponDef
from trpg.content.skills import EffectSpec
from trpg.content.summons import summon_spec_hp
from trpg.engine.rules.geometry import XY
from trpg.engine.skills.targeting import summon_site_problem
from trpg.engine.state import BattleState, UnitState

__all__ = ["apply_summon_spec", "second_summon_site", "trait_adjusted"]

_PERMILLE = 1000
_SITE_ORDER: tuple[XY, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))
"""數量型第二隻的候選位置（相對第一隻）。"""
_MIN_CRIT = 2


def apply_summon_spec(state: BattleState, unit: UnitState, spec: EffectSpec | None) -> None:
    """召喚物剛建立、已套完成長與灌注 HP 之後，套用分歧進化的 HP、強度與小特性（呼叫端之後再把
    ``hp`` 補滿）。"""
    if spec is None:
        return
    unit.max_hp = summon_spec_hp(
        unit.max_hp, max_hp_permille=spec.max_hp_permille, power_permille=spec.power_permille
    )  # 和技能卡同一個函式（3-41a）
    if spec.power_permille is not None:
        unit.summon_power_permille = spec.power_permille
    unit.speed, unit.armor_bonus, unit.weapon = trait_adjusted(
        state, spec, speed=unit.speed, armor_bonus=unit.armor_bonus, weapon=unit.weapon
    )


def trait_adjusted(
    state: BattleState, spec: EffectSpec, *, speed: int, armor_bonus: int, weapon: WeaponDef
) -> tuple[int, int, WeaponDef]:
    """加深進化的小特性（``core.summon_traits``）對移動、護甲與暴擊範圍的調整；引擎生成召喚物與
    技能卡的「實際值」共用（3-41c）。"""
    trait = None if spec.trait is None else state.ruleset.core.summon_traits.get(spec.trait)
    if trait is None:
        return speed, armor_bonus, weapon
    if trait.crit_range_delta:
        crit = max(_MIN_CRIT, weapon.crit_range - trait.crit_range_delta)
        weapon = weapon.model_copy(update={"crit_range": crit})
    return speed + trait.speed_bonus, armor_bonus + trait.armor_bonus, weapon


def second_summon_site(state: BattleState, xy: XY) -> XY | None:
    """數量型第二隻的位置：``xy`` 旁邊第一個可以召喚的格子（東、西、南、北）；沒有時 ``None``。"""
    for dx, dy in _SITE_ORDER:
        site = (xy[0] + dx, xy[1] + dy)
        if summon_site_problem(state, site) is None:
            return site
    return None
