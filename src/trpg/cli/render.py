"""文字渲染：地圖網格、戰場網格、繁體中文戰鬥紀錄與統計。

引擎事件只描述發生了什麼；所有顯示文字都在這裡產生。
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from trpg.content.battle import TerrainDef
from trpg.content.maps import MapDef
from trpg.engine.events import (
    AttackRolled,
    BattleEnded,
    BattleStarted,
    ChainLimitReached,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    InitiativeRolled,
    MoveBlocked,
    RoundEnded,
    RoundStarted,
    StatusApplied,
    StatusRemoved,
    TurnEnded,
    TurnOrderSet,
    TurnStarted,
    UnitDowned,
    UnitFell,
    UnitMoved,
    UnitStoodUp,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, Team

__all__ = [
    "BattleStats",
    "describe_event",
    "render_battle_grid",
    "render_map",
    "render_unit_table",
    "unit_markers",
]

_PPM = 1_000_000
_LABEL_WIDTH = 14
_WIDE_CHAR_START = 0x2E7F  # 之後的 CJK 字元在終端機佔兩格

_CAUSE_NAMES = {
    "attack": "",
    "fall": "墜落",
    "deadly_terrain": "致命地形",
    "status": "持續",
    "effect": "",
}


def _xy(pos: Pos) -> str:
    return f"({pos.x}, {pos.y})"


def _header(width: int) -> str:
    return "    " + "".join(f"{x:<3}" for x in range(width)).rstrip()


def render_map(map_def: MapDef, terrain: dict[str, TerrainDef]) -> str:
    """``trpg map show``：每格顯示「高度 ＋ 地形字元」。

    起始區以 ``a``（我方）／``e``（敵方）標示。
    """
    zones = {cell: "a" for cell in map_def.start_zones[Team.ALLY]}
    zones.update({cell: "e" for cell in map_def.start_zones[Team.ENEMY]})
    grid = map_def.grid()
    lines = [
        f"{map_def.name_zh}（{map_def.id}，{map_def.width}×{map_def.height}）",
        _header(map_def.width),
    ]
    for y, row in enumerate(grid):
        cells = []
        for x, (h, tid) in enumerate(row):
            mark = zones.get((x, y), terrain[tid].glyph)
            cells.append(f"{h}{mark}")
        lines.append(f"{y:>2}  " + " ".join(cells))
    used = sorted({tid for row in grid for _, tid in row})
    legend = "、".join(f"{terrain[t].glyph} {terrain[t].name_zh}" for t in used)
    lines.append("")
    lines.append("圖例：數字為高度（0–3）；" + legend + "；a 我方起始區、e 敵方起始區")
    if map_def.objects:
        lines.append("物件：" + "、".join(f"{o.kind} {list(o.at)}" for o in map_def.objects))
    return "\n".join(lines)


def unit_markers(state: BattleState) -> dict[str, str]:
    """單位在網格上的代號：我方 A、B、C……，敵方 a、b、c……（依單位 ID）。"""
    markers: dict[str, str] = {}
    counters = {Team.ALLY: 0, Team.ENEMY: 0}
    letters = {Team.ALLY: string.ascii_uppercase, Team.ENEMY: string.ascii_lowercase}
    for unit in state.units_sorted():
        i = counters[unit.team]
        counters[unit.team] += 1
        markers[unit.id] = letters[unit.team][i % 26]
    return markers


def render_battle_grid(state: BattleState) -> str:
    markers = unit_markers(state)
    occupancy = state.occupancy()
    lines = [_header(state.width)]
    for y in range(state.height):
        cells = []
        for x in range(state.width):
            tile = state.tile(x, y)
            unit = occupancy.get((x, y))
            mark = markers[unit.id] if unit else state.ruleset.terrain_def(tile.terrain).glyph
            cells.append(f"{tile.height}{mark}")
        lines.append(f"{y:>2}  " + " ".join(cells))
    return "\n".join(lines)


def _status_text(state: BattleState, unit: UnitState) -> str:
    if not unit.statuses:
        return ""
    parts = []
    for s in unit.statuses:
        name = state.ruleset.status_def(s.status_id).name_zh
        parts.append(name if s.remaining is None else f"{name}{s.remaining}")
    return "［" + "、".join(parts) + "］"


def render_unit_table(state: BattleState) -> str:
    markers = unit_markers(state)
    lines = []
    for unit in state.units_sorted():
        team = unit.team.display_name
        if unit.downed:
            lines.append(f"  {markers[unit.id]} {team} {unit.name_zh}：倒下")
            continue
        lines.append(
            f"  {markers[unit.id]} {team} {unit.name_zh}：HP {unit.hp}/{unit.max_hp}"
            f" 位置 {_xy(unit.pos)} 武器 {unit.weapon.name_zh}{_status_text(state, unit)}"
        )
    return "\n".join(lines)


def _signed(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _attack_text(e: AttackRolled, name: dict[str, str]) -> str:
    if e.advantage == "none":
        dice = f"d20={e.natural}"
    else:
        label = "優勢" if e.advantage == "advantage" else "劣勢"
        dice = f"d20（{label} {e.rolls[0]}、{e.rolls[1]}）={e.natural}"
    parts = [dice, f"修正 {_signed(e.hit_modifier)}", f"熟練 {_signed(e.proficiency)}"]
    if e.situational:
        parts.append(f"高度 {_signed(e.situational)}")
    if e.natural == 20:  # noqa: PLR2004 - 自然 20
        verdict = "自然 20，暴擊！" if e.crit else "自然 20，命中"
    elif e.natural == 1:
        verdict = "自然 1，失手"
    else:
        verdict = ("暴擊！" if e.crit else "命中") if e.hit else "失手"
    return (
        f"{name[e.attacker_id]} 攻擊 {name[e.target_id]}：{' '.join(parts)} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}"
    )


def _damage_text(e: DamageDealt, name: dict[str, str]) -> str:
    cause = _CAUSE_NAMES[e.cause]
    element = e.element.display_name
    kind = f"{cause}{element}" if cause and e.cause != "status" else element
    if e.cause in ("fall", "deadly_terrain"):
        kind = cause
    rolls = f"［骰 {'+'.join(str(r) for r in e.rolls)}］" if e.rolls else ""
    mod = ""
    if e.element_mod_ppm != _PPM:
        mod = f"（元素修正 ×{e.element_mod_ppm / _PPM:g}）"
    return (
        f"{name[e.target_id]} 受到 {e.amount} 點{kind}傷害{rolls}{mod}"
        f"，HP {e.hp_before} → {e.hp_after}"
    )


def describe_event(e: EventBase, state: BattleState) -> str | None:  # noqa: PLR0911, PLR0912
    """把一個事件轉成一行繁體中文；不需要顯示的事件回傳 ``None``。"""
    name: dict[str, str] = {uid: u.name_zh for uid, u in state.units.items()}
    statuses = {s.id: s.name_zh for s in state.ruleset.statuses.statuses}
    if isinstance(e, BattleStarted):
        return f"戰鬥開始：{state.map_name_zh}（{state.width}×{state.height}），種子 {e.seed}"
    if isinstance(e, InitiativeRolled):
        return f"先攻：{name[e.unit_id]} d20={e.roll} {_signed(e.modifier)} = {e.total}"
    if isinstance(e, TurnOrderSet):
        return "行動順序：" + " → ".join(name[u] for u in e.order)
    if isinstance(e, RoundStarted | RoundEnded):
        return None
    if isinstance(e, TurnStarted):
        return f"— {name[e.unit_id]} 的回合（AP {e.ap}，移動 {e.move_points}）"
    if isinstance(e, TurnEnded):
        kept = f"，保留 {e.ap_carried} AP" if e.ap_carried else ""
        return f"  {name[e.unit_id]} 結束回合{kept}"
    if isinstance(e, UnitMoved):
        if e.mode == "walk":
            return None  # 由 Move 動作整段顯示（見 CLI）
        verb = "被傳送到" if e.mode == "teleport" else "被推到"
        return f"  {name[e.unit_id]} {verb} {_xy(e.to_pos)}"
    if isinstance(e, UnitStoodUp):
        return f"  {name[e.unit_id]} 站了起來（消耗 {e.cost} 移動）"
    if isinstance(e, MoveBlocked):
        return f"  {name[e.unit_id]} 無法移動到 {_xy(e.to_pos)}"
    if isinstance(e, UnitFell):
        return f"  {name[e.unit_id]} 從 {e.drop} 層高處跌落！"
    if isinstance(e, EnteredDeadlyTerrain):
        terrain = state.ruleset.terrain_def(e.terrain).name_zh
        return f"  {name[e.unit_id]} 掉進了{terrain}！"
    if isinstance(e, AttackRolled):
        return "  " + _attack_text(e, name)
    if isinstance(e, DamageDealt):
        return "    " + _damage_text(e, name)
    if isinstance(e, Healed):
        return f"    {name[e.target_id]} 回復 {e.amount} HP，HP {e.hp_before} → {e.hp_after}"
    if isinstance(e, StatusApplied):
        verb = "刷新" if e.refreshed else "獲得"
        turns = f"（{e.duration} 回合）" if e.duration else ""
        return f"  {name[e.target_id]} {verb}狀態「{statuses[e.status_id]}」{turns}"
    if isinstance(e, StatusRemoved):
        if e.reason == "stood_up":
            return None
        return f"  {name[e.target_id]} 的「{statuses[e.status_id]}」結束了"
    if isinstance(e, UnitDowned):
        return f"  ＊ {name[e.unit_id]} 倒下了！"
    if isinstance(e, ChainLimitReached):
        return f"  （連鎖達到上限，{e.effect_kind} 效果沒有發生）"
    if isinstance(e, BattleEnded):
        if e.winner is None:
            return "戰鬥結束：達到輪數上限，平手" if e.reason == "round_limit" else "戰鬥結束：平手"
        return f"戰鬥結束：{e.winner.display_name}勝利（全滅）"
    return None  # pragma: no cover - 新事件類型尚未有中文描述


@dataclass
class _UnitStats:
    attacks: int = 0
    hits: int = 0
    crits: int = 0
    dealt: int = 0
    taken: int = 0
    kills: int = 0


@dataclass
class BattleStats:
    """由事件日誌計算的統計。"""

    per_unit: dict[str, _UnitStats] = field(default_factory=dict)

    @classmethod
    def from_events(cls, events: list[EventBase], state: BattleState) -> BattleStats:
        stats = cls({uid: _UnitStats() for uid in sorted(state.units)})
        last_source: dict[str, str | None] = {}
        for e in events:
            if isinstance(e, AttackRolled):
                s = stats.per_unit[e.attacker_id]
                s.attacks += 1
                s.hits += e.hit
                s.crits += e.crit
            elif isinstance(e, DamageDealt):
                stats.per_unit[e.target_id].taken += e.amount
                if e.source_id is not None:
                    stats.per_unit[e.source_id].dealt += e.amount
                last_source[e.target_id] = e.source_id
            elif isinstance(e, UnitDowned):
                killer = last_source.get(e.unit_id)
                if killer is not None:
                    stats.per_unit[killer].kills += 1
        return stats

    def render(self, state: BattleState) -> str:
        markers = unit_markers(state)
        lines = ["  代號 單位          造成傷害 承受傷害 命中/攻擊 暴擊 擊倒 結果"]
        for uid, s in self.per_unit.items():
            unit = state.units[uid]  # type: ignore[index]
            label = f"{unit.team.display_name} {unit.name_zh}"
            pad = _LABEL_WIDTH - sum(2 if ord(ch) > _WIDE_CHAR_START else 1 for ch in label)
            result = "倒下" if unit.downed else f"HP {unit.hp}/{unit.max_hp}"
            lines.append(
                f"  {markers[uid]:<4} {label}{' ' * max(pad, 1)}{s.dealt:>8} {s.taken:>8}"
                f" {s.hits:>4}/{s.attacks:<4} {s.crits:>4} {s.kills:>4} {result}"
            )
        return "\n".join(lines)
