"""朝向與背刺（Phase 3D-8d，``docs/design/05-戰鬥.md`` 5.1「朝向與背刺」、``06-技能.md`` 6.21）。

- 每個單位有四方向的朝向（:attr:`UnitState.facing`），由引擎自動更新：主動移動（步行每一步、
  衝鋒、跳躍、直線衝撞）後面向最後一步的方向；瞬步落地、攻擊或對單位施放技能後面向目標。被推、
  拉、傳送、交換等強制位移不改朝向。
- 背後格 ＝ 位置 ＋ 朝向的反方向（只算相鄰的那一格）。
- 朝向只影響背刺（``from_behind`` 條件與近戰背刺加成）；其餘規則與朝向無關。
"""

from __future__ import annotations

from collections.abc import Iterable

from trpg.engine.rules.geometry import XY, axis_direction
from trpg.engine.state import BattleState, Facing, UnitState
from trpg.shared.types import Team

__all__ = [
    "FACING_VECTORS",
    "back_xy",
    "default_facing",
    "face_toward",
    "facing_between",
    "facing_toward_enemies",
    "is_behind",
    "opening_facing",
]

FACING_VECTORS: dict[Facing, XY] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
"""朝向 → 一步的位移（與 ``shapes.DIRECTIONS`` 相同：北 ＝ y − 1）。"""

_BY_VECTOR: dict[XY, Facing] = {v: k for k, v in FACING_VECTORS.items()}


def facing_between(src: XY, dest: XY) -> Facing | None:
    """從 ``src`` 看向 ``dest`` 的朝向：取位移較大的軸，兩軸相同時取左右（固定順序）；同一格時
    為 ``None``。"""
    vector = axis_direction(dest[0] - src[0], dest[1] - src[1])
    return None if vector is None else _BY_VECTOR[vector]


def face_toward(unit: UnitState, xy: XY) -> None:
    """``unit`` 轉向 ``xy``（同一格時不變）。巨型單位（GB-1a，05 5.12.4 第 7 點、T8）朝向固定、
    整場不轉：出招、被近戰打都不改。"""
    if unit.footprint > 1:
        return
    facing = facing_between(unit.xy, xy)
    if facing is not None:
        unit.facing = facing


def back_xy(unit: UnitState) -> XY:
    """``unit`` 的背後格（朝向的反方向相鄰格；可能在地圖外）。"""
    dx, dy = FACING_VECTORS[unit.facing]
    return (unit.xy[0] - dx, unit.xy[1] - dy)


def is_behind(attacker_xy: XY, target: UnitState) -> bool:
    """``attacker_xy`` 是 ``target`` 的背後格（只算相鄰的背後格）。

    巨型單位（GB-1a，T8）：站在背面那一排外側、和背面那一排相鄰（背面的 3 格之外各一格；斜角
    不算）。部位的「算從背後」（``counts_as_behind``）在 GB-1c。"""
    if target.footprint == 1:
        return attacker_xy == back_xy(target)
    half = target.footprint // 2
    dx, dy = FACING_VECTORS[target.facing]
    rx, ry = attacker_xy[0] - target.xy[0], attacker_xy[1] - target.xy[1]
    if dx != 0:  # 朝東西：背面是一整欄
        return rx == -dx * (half + 1) and abs(ry) <= half
    return ry == -dy * (half + 1) and abs(rx) <= half


def default_facing(team: Team) -> Facing:
    """沒有其他依據時的朝向：我方朝東（右）、敵方朝西（左）。"""
    return "east" if team is Team.ALLY else "west"


def _toward_centroid(origin_sum: XY, origin_count: int, others: Iterable[XY]) -> Facing | None:
    """從一群位置（座標和與個數）的重心看向另一群位置的重心的朝向（整數運算，不用除法）。"""
    points = list(others)
    if origin_count == 0 or not points:
        return None
    ox, oy = origin_sum
    tx = sum(p[0] for p in points)
    ty = sum(p[1] for p in points)
    n = len(points)
    vector = axis_direction(tx * origin_count - ox * n, ty * origin_count - oy * n)
    return None if vector is None else _BY_VECTOR[vector]


def opening_facing(team: Team, own: list[XY], enemies: list[XY]) -> Facing:
    """開場朝向：一個陣營的所有單位都面向「敵方起始位置的重心」相對「己方起始位置的重心」的
    方向；算不出來（重心重合）時用 :func:`default_facing`。"""
    sx = sum(p[0] for p in own)
    sy = sum(p[1] for p in own)
    facing = _toward_centroid((sx, sy), len(own), enemies)
    return default_facing(team) if facing is None else facing


def facing_toward_enemies(state: BattleState, xy: XY, team: Team) -> Facing:
    """戰鬥中出現的單位（援軍、召喚物）的朝向：面向場上存活敵人的重心；沒有敵人時用
    :func:`default_facing`。"""
    enemies = [u.xy for u in state.living_units() if u.team is not team]
    facing = _toward_centroid(xy, 1, enemies)
    return default_facing(team) if facing is None else facing
