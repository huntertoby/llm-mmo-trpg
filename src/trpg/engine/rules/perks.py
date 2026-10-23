"""屬性的常駐數值（Phase 3H-1，``docs/design/07-角色成長.md`` 7.2；資料在 ``rules/core.yaml`` 的
``attribute_perks``）。

屬性高於基準每 4 點升一階（有效屬性，含狀態與裝備加值）；每一種常駐數值由引擎的一個結算點讀取
:func:`attribute_perk`，門檻與每階數值都不寫死：

- ``collision_dealt``／``collision_taken``：``triggers._collision_damage``（撞擊傷害）；
- ``surface_duration``：``skills.primitives.terrain.create_surface``、``zones.create_zone``；
- ``reaction_hit``：``reactions._attack_once``（反應攻擊的命中）；
- ``reveal_range``：``rules.combat.concealment_problem``（鎖定隱蔽單位）、``traps.detect_traps``；
- ``control_resist``：``control.plan_status``（控制的抵抗屬性值）。
"""

from __future__ import annotations

from trpg.content.library import Ruleset
from trpg.content.rules import PerkKind
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.state import UnitState

__all__ = ["attribute_perk"]


def attribute_perk(rules: Ruleset, unit: UnitState, kind: PerkKind) -> int:
    """``unit`` 的 ``kind`` 常駐數值總加成（沒有任何階數時為 0）。"""
    perks = rules.core.attribute_perks
    if not perks.perks:
        return 0
    return perks.total(kind, lambda attr: effective_attribute(rules, unit, attr))
