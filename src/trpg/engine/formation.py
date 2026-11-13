"""陣法範圍加成與把傷害分給同門（Phase 5A-M2；``docs/design/18-雲嶺內容.md`` 18.2.1 劍陣弟子
「劍陣」、詞綴「連心的」）。

兩者都是狀態欄位（``statuses.yaml``，中性、不倒數；由範本 ``opening_statuses``／詞綴
``add_opening_statuses`` 開場掛上）：

- ``formation``（:class:`~trpg.content.battle.FormationSpec`）：持有者造成的攻擊傷害 × 陣法倍率
  （:func:`formation_permille`；傷害結算的 ``damage_dealt`` 那一步乘上）。
- ``ward``（:class:`~trpg.content.battle.WardSpec`，Phase 5A-M2b「陣眼石靈」）：持有者還在場時，
  範圍內的同門（不含持有者）受到的骰值傷害 × 護陣倍率（:func:`ward_permille`）；持有者倒下即解除。
- ``share_damage``（:class:`~trpg.content.battle.ShareDamageSpec`）：持有者受到的傷害分一部分給
  範圍內的同門（:func:`share_split`；傷害結算在護盾與靈魂連結之後套用）。

「同門」＝與 ``unit`` 同陣營、存活、在場、不是自己、帶 ``kin_tag``（省略時不看標籤）、
曼哈頓距離 ≤ ``range``；依單位 ID 排序。這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from trpg.content.battle import FormationSpec, ShareDamageSpec, WardSpec
from trpg.engine.rules.combat import PERMILLE
from trpg.engine.rules.footprint import unit_dist
from trpg.engine.state import BattleState, StatusInstance, UnitState

__all__ = [
    "formation_count",
    "formation_permille",
    "formation_specs",
    "kin_in_range",
    "share_spec",
    "share_split",
    "ward_holders",
    "ward_permille",
]


def kin_in_range(
    state: BattleState, unit: UnitState, kin_tag: str | None, reach: int
) -> list[UnitState]:
    """``unit`` 的同門（見模組說明），依單位 ID。``unit`` 的位置以 ``unit.xy`` 為準（可以是放到
    別格的虛擬複本）。"""
    return [
        u
        for u in state.living_units()
        if u.id != unit.id
        and u.team is unit.team
        and (kin_tag is None or u.has_tag(kin_tag))
        and unit_dist(u, unit) <= reach
    ]


def formation_specs(state: BattleState, unit: UnitState) -> list[FormationSpec]:
    """``unit`` 身上的陣法（依狀態順序）。"""
    specs: list[FormationSpec] = []
    for status in unit.statuses:
        spec = state.ruleset.status_def(status.status_id).formation
        if spec is not None:
            specs.append(spec)
    return specs


def formation_count(state: BattleState, unit: UnitState, spec: FormationSpec) -> int:
    """陣法算進去的同門人數（最多 ``max_allies``）。"""
    return min(len(kin_in_range(state, unit, spec.kin_tag, spec.range)), spec.max_allies)


def formation_permille(state: BattleState, unit: UnitState) -> int:
    """``unit`` 目前的陣法倍率（‰；沒有陣法時 1000）。多個陣法依狀態順序相乘、逐步捨去。"""
    total = PERMILLE
    for spec in formation_specs(state, unit):
        count = formation_count(state, unit, spec)
        own = PERMILLE + spec.per_ally_permille * count if count else spec.alone_permille
        total = total * own // PERMILLE
    return total


def share_spec(
    state: BattleState, unit: UnitState
) -> tuple[StatusInstance, ShareDamageSpec] | None:
    """``unit`` 身上第一個分傷狀態（依狀態順序）；沒有時為 ``None``。"""
    for status in unit.statuses:
        spec = state.ruleset.status_def(status.status_id).share_damage
        if spec is not None:
            return status, spec
    return None


def share_split(
    state: BattleState, unit: UnitState, spec: ShareDamageSpec, remaining: int
) -> list[tuple[UnitState, int]]:
    """``remaining`` 點要扣 HP 的傷害中，分給各同門的點數（依單位 ID；都是正數）。分出量 ＝
    ``remaining × permille ÷ 1000``（捨去），平分，餘數從 ID 小的開始各多 1 點。"""
    if remaining <= 0:
        return []
    kin = kin_in_range(state, unit, spec.kin_tag, spec.range)
    total = remaining * spec.permille // PERMILLE
    if not kin or total <= 0:
        return []
    each, extra = divmod(total, len(kin))
    shares = [(u, each + (1 if i < extra else 0)) for i, u in enumerate(kin)]
    return [(u, n) for u, n in shares if n > 0]


def ward_holders(state: BattleState, unit: UnitState) -> list[tuple[UnitState, WardSpec]]:
    """護住 ``unit`` 的護陣（Phase 5A-M2b）：同陣營、存活、不是 ``unit`` 自己的護陣持有者，
    ``unit`` 帶 ``kin_tag`` 且在持有者 ``range`` 格內；依持有者 ID、狀態順序。"""
    found: list[tuple[UnitState, WardSpec]] = []
    for holder in state.living_units():
        if holder.id == unit.id or holder.team is not unit.team:
            continue
        for status in holder.statuses:
            spec = state.ruleset.status_def(status.status_id).ward
            if (
                spec is not None
                and (spec.kin_tag is None or unit.has_tag(spec.kin_tag))
                and unit_dist(holder, unit) <= spec.range
            ):
                found.append((holder, spec))
    return found


def ward_permille(state: BattleState, unit: UnitState) -> int:
    """``unit`` 受到的護陣倍率（‰；沒有護陣時 1000）。多個護陣依序相乘、逐步捨去。"""
    total = PERMILLE
    for _, spec in ward_holders(state, unit):
        total = total * spec.taken_permille // PERMILLE
    return total
