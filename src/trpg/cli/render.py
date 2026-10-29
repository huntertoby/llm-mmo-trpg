"""文字渲染：地圖網格、戰場網格、環境預告與統計。

事件的中文描述在 ``trpg.narrative.events``（Phase 3-1 搬出）。
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from trpg.content.library import Ruleset
from trpg.content.maps import MapDef, SpawnUnitsEvent
from trpg.engine.activations import remaining_rounds
from trpg.engine.environment import Telegraph
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    UnitDowned,
)
from trpg.engine.rules.combat import is_concealed
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons.core import totem_of
from trpg.engine.traps import visible_traps
from trpg.engine.zones import next_zone_cells, zone_cells, zone_spec
from trpg.narrative.events import (
    DIRECTION_TEXT,
    cells_text,
    object_name,
    surface_name,
    xy_text,
    zone_anchor_text,
)
from trpg.narrative.telegraph import bomb_text, change_text
from trpg.shared.types import Pos, Surface, Team

__all__ = [
    "BattleStats",
    "render_battle_grid",
    "render_map",
    "render_telegraph",
    "render_unit_table",
    "render_zone_lines",
    "unit_markers",
]

TRAP_GLYPH = "^"
WELL_GLYPH = "$"
ZONE_GLYPH = "!"
REVEALED_TRAP_GLYPH = "x"
"""被揭露的敵方陷阱（Phase 3C-6a；3D-8a 的 ``reveal``）：與我方陷阱 ``^`` 區分。"""
"""持續區域（Phase 3D-5）涵蓋的空格的顯示字元（單位、物件、陷阱、源泉優先）。"""
"""源泉格（Phase 3C-4a）的顯示字元。"""
"""網格上我方陷阱的字元（只顯示放置者陣營看得到的陷阱）。"""

_LABEL_WIDTH = 14
_WIDE_CHAR_START = 0x2E7F  # 之後的 CJK 字元在終端機佔兩格

_OBJECTIVES = {"eliminate": "擊倒所有敵人", "escape": "撤離", "defend": "守點"}


def _header(width: int) -> str:
    return "    " + "".join(f"{x:<3}" for x in range(width)).rstrip()


def _surface_glyphs(ruleset: Ruleset) -> dict[Surface, str]:
    return {sd.id: sd.glyph for sd in ruleset.surfaces.surfaces}


def render_map(map_def: MapDef, ruleset: Ruleset) -> str:
    """``trpg map show``：每格顯示「高度 ＋ 地形或物件字元 ＋ 表面字元」。

    起始區以 ``a``（我方）／``e``（敵方）標示。
    """
    terrain = ruleset.terrain.by_id()
    objects = ruleset.objects.by_id()
    zones = {cell: "a" for cell in map_def.start_zones[Team.ALLY]}
    zones.update({cell: "e" for cell in map_def.start_zones[Team.ENEMY]})
    placed = {o.at: objects[o.kind].glyph for o in map_def.objects}
    placed.update({at: WELL_GLYPH for at in map_def.source_wells})
    surf_glyph = _surface_glyphs(ruleset)
    surfaces = {s.at: surf_glyph[s.surface] for s in map_def.surfaces}
    grid = map_def.grid()
    lines = [
        f"{map_def.name_zh}（{map_def.id}，類型 {map_def.archetype}，"
        f"{map_def.width}×{map_def.height}）",
        _header(map_def.width),
    ]
    for y, row in enumerate(grid):
        cells = []
        for x, (h, tid) in enumerate(row):
            mark = zones.get((x, y), placed.get((x, y), terrain[tid].glyph))
            cells.append(f"{h}{mark}{surfaces.get((x, y), ' ')}")
        lines.append(f"{y:>2}  " + " ".join(cells).rstrip())
    used = sorted({tid for row in grid for _, tid in row})
    legend = "、".join(f"{terrain[t].glyph} {terrain[t].name_zh}" for t in used)
    lines.append("")
    lines.append("圖例：數字為高度（0–3）；" + legend + "；a 我方起始區、e 敵方起始區")
    kinds = sorted({o.kind for o in map_def.objects})
    if kinds:
        lines.append(
            "物件：" + "、".join(f"{objects[k].glyph} {objects[k].name_zh}" for k in kinds)
        )
    if map_def.source_wells:
        lines.append(f"源泉格：{WELL_GLYPH}（我方單位進入時 +1 源力，之後消失）")
    used_surfaces = sorted({s.surface for s in map_def.surfaces})
    if used_surfaces:
        lines.append(
            "表面（第三個字元）："
            + "、".join(f"{surf_glyph[s]} {ruleset.surface_def(s).name_zh}" for s in used_surfaces)
        )
    lines.append(
        f"勝利條件：{_objective_text(map_def)}；天氣：{map_def.weather}"
        + (
            f"；預設陣容：我方 {','.join(map_def.encounter.allies)}、"
            f"敵方 {','.join(map_def.encounter.enemies)}"
            if map_def.encounter
            else ""
        )
    )
    for event in map_def.events:
        what = "援軍" if isinstance(event, SpawnUnitsEvent) else "地形變化"
        lines.append(f"地圖事件：第 {event.round} 輪結束時 {what}")
    return "\n".join(lines)


def _objective_text(map_def: MapDef) -> str:
    o = map_def.objective
    text = _OBJECTIVES[o.kind]
    if o.kind != "eliminate":
        tiles = "、".join(f"({x}, {y})" for x, y in o.tiles)
        text += f"（{o.rounds} 輪內，格子 {tiles}）"
    return text


def unit_markers(state: BattleState) -> dict[str, str]:
    """單位在網格上的代號：我方 A、B、C……，敵方 a、b、c……（依單位 ID）；召喚物（Phase 3D-4b）
    不分陣營，一律用數字 1–9（依單位 ID，超過 9 個後循環），單位表標明召喚者與到期輪。"""
    markers: dict[str, str] = {}
    counters = {Team.ALLY: 0, Team.ENEMY: 0}
    letters = {Team.ALLY: string.ascii_uppercase, Team.ENEMY: string.ascii_lowercase}
    summons = 0
    for unit in state.units_sorted():
        if unit.is_summon:
            markers[unit.id] = str(summons % 9 + 1)
            summons += 1
            continue
        i = counters[unit.team]
        counters[unit.team] += 1
        markers[unit.id] = letters[unit.team][i % 26]
    return markers


def render_battle_grid(state: BattleState) -> str:
    """戰場網格：每格「高度 ＋ 單位／物件／地形字元 ＋ 表面字元」。"""
    markers = unit_markers(state)
    occupancy = state.occupancy()
    surf_glyph = _surface_glyphs(state.ruleset)
    seen_traps = visible_traps(state, Team.ALLY)  # 我方的，加上被揭露的敵方陷阱
    my_traps = {t.xy for t in seen_traps if t.team is Team.ALLY}
    revealed_traps = {t.xy for t in seen_traps if t.team is not Team.ALLY}
    zoned = {xy for zone in state.zones for xy in zone_cells(state, zone)}  # 持續區域（3D-5）
    lines = [_header(state.width)]
    for y in range(state.height):
        cells = []
        for x in range(state.width):
            tile = state.tile(x, y)
            unit = occupancy.get((x, y))
            obj = state.object_at(x, y)
            if unit is not None:
                mark = markers[unit.id]
            elif obj is not None:
                mark = state.object_def(obj).glyph
            elif (x, y) in my_traps:
                mark = TRAP_GLYPH
            elif (x, y) in revealed_traps:
                mark = REVEALED_TRAP_GLYPH
            elif (x, y) in state.source_wells:
                mark = WELL_GLYPH
            elif (x, y) in zoned:
                mark = ZONE_GLYPH
            else:
                mark = state.ruleset.terrain_def(tile.terrain).glyph
            surface = surf_glyph[tile.surface] if tile.surface is not Surface.NONE else " "
            cells.append(f"{tile.height}{mark}{surface}")
        lines.append(f"{y:>2}  " + " ".join(cells).rstrip())
    return "\n".join(lines)


def render_legend(state: BattleState) -> str:
    """戰場上出現的物件與表面的圖例。"""
    kinds = sorted({o.kind for o in state.objects_sorted()})
    surfaces = sorted(
        {state.tile(x, y).surface for y in range(state.height) for x in range(state.width)}
        - {Surface.NONE}
    )
    parts = [
        f"{state.ruleset.object_def(k).glyph} {state.ruleset.object_def(k).name_zh}" for k in kinds
    ]
    parts += [
        f"{state.ruleset.surface_def(s).glyph} {state.ruleset.surface_def(s).name_zh}（表面）"
        for s in surfaces
    ]
    if any(u.is_summon and u.alive for u in state.units.values()):
        parts.append("1–9 召喚物（單位表有召喚者與到期輪）")
    seen = visible_traps(state, Team.ALLY)
    if any(t.team is Team.ALLY for t in seen):
        parts.append(f"{TRAP_GLYPH} 我方陷阱")
    if any(t.team is not Team.ALLY for t in seen):
        parts.append(f"{REVEALED_TRAP_GLYPH} 被揭露的敵方陷阱")
    if state.source_wells:
        parts.append(f"{WELL_GLYPH} 源泉")
    if state.zones:
        parts.append(f"{ZONE_GLYPH} 持續區域（單位表下方有名稱、範圍與剩餘輪數）")
    return ("  圖例：" + "、".join(parts)) if parts else ""


def _status_text(state: BattleState, unit: UnitState) -> str:
    parts = []
    for s in unit.statuses:
        name = state.ruleset.status_def(s.status_id).name_zh
        parts.append(name if s.remaining is None else f"{name}{s.remaining}")
    for stack_id, count in sorted(unit.stacks.items()):  # 層數（2E-3）
        parts.append(f"{state.ruleset.stack_def(stack_id).name_zh}×{count}")
    if not unit.has_status("concealed") and is_concealed(state, unit):
        parts.append("隱蔽")
    return ("［" + "、".join(parts) + "］") if parts else ""


def _source_text(state: BattleState, unit: UnitState) -> str:
    """我方單位的源力（Phase 3C-4a），例如「 源力 2/3」；敵方不顯示（一律 0）。"""
    if unit.team is not Team.ALLY or unit.is_summon:  # 召喚物沒有源力（Phase 3D-4a）
        return ""
    return f" 源力 {unit.source}/{state.ruleset.core.source_max}"


def _summon_text(state: BattleState, unit: UnitState) -> str:
    """召喚物的標註（Phase 3D-4b）：召喚者與到期輪，圖騰另註明；一般單位為空字串。"""
    if not unit.is_summon or unit.owner_id is None or unit.summon_expires_round is None:
        return ""
    owner_unit = state.units[unit.owner_id]
    owner = owner_unit.name_zh
    if not owner_unit.alive:  # 規則改變「殘影」的分身（Phase 3D-6）：召喚者已倒下
        return f" ［召喚物：{owner}留下，第 {unit.summon_expires_round} 輪的環境回合消失］"
    kind = "圖騰" if totem_of(state, unit) is not None else "召喚物"
    return f" ［{kind}：{owner}召喚，第 {unit.summon_expires_round} 輪結束時消失］"


def _activation_text(state: BattleState, unit: UnitState) -> str:
    """生效中的常駐類傳說（Phase 3D-6），例如「 ［傳說：戰神降臨 剩 3 輪］」。"""
    if not unit.activations:
        return ""
    parts = []
    for activation in unit.activations:
        name = state.ruleset.skill_def(activation.skill_id).name_zh
        left = remaining_rounds(state, activation)
        parts.append(f"{name} {'整場' if left is None else f'剩 {left} 輪'}")
    return f" ［傳說：{'、'.join(parts)}］"


def _granted_text(state: BattleState, unit: UnitState) -> str:
    """暫時獲得的技能與剩餘輪數（Phase 3D-8c），例如「 ［暫時技能：飛行 剩 3 輪］」。"""
    if not unit.granted_skills:
        return ""
    parts = [
        f"{state.ruleset.skill_def(g.skill_id).name_zh} 剩 {g.remaining} 輪"
        for g in unit.granted_skills
    ]
    return f" ［暫時技能：{'、'.join(parts)}］"


def render_zone_lines(state: BattleState) -> list[str]:
    """持續區域（Phase 3D-5）：每個區域一行——名稱、施放者、錨點、消失輪、格子與下一輪的位置。"""
    lines = []
    for zone in state.zones:
        skill = state.ruleset.skill_def(zone.skill_id).name_zh
        owner = state.units[zone.owner_id].name_zh
        anchor = zone_anchor_text(zone.anchor, zone.direction, zone.speed)
        affects = {"enemies": "敵方", "allies": "友方", "all": "所有人"}[
            zone_spec(state, zone).affects or "all"
        ]
        cells = tuple(Pos(x=x, y=y) for x, y in zone_cells(state, zone))
        line = (
            f"  {ZONE_GLYPH} 區域「{skill}」（{owner}，影響{affects}，{anchor}，"
            f"第 {zone.expires_round} 輪 {owner} 的回合結束時消失）：{cells_text(cells)}"
        )
        upcoming = next_zone_cells(state, zone)
        if upcoming is not None and zone.direction is not None:
            nxt = tuple(Pos(x=x, y=y) for x, y in upcoming)
            direction = DIRECTION_TEXT[zone.direction]
            line += f"；本輪結束時向{direction}移到 {cells_text(nxt) or '（消失）'}"
        lines.append(line)
    return lines


FACING_TEXT = {"north": "北↑", "east": "東→", "south": "南↓", "west": "西←"}
"""朝向的顯示文字（Phase 3D-8d）；單位的背後是朝向的反方向那一格。"""


def render_unit_table(state: BattleState) -> str:
    markers = unit_markers(state)
    lines = []
    for unit in state.units_sorted():
        team = unit.team.display_name
        if unit.downed or unit.escaped or unit.dismissed:
            what = "倒下" if unit.downed else "已撤離" if unit.escaped else "已消失"
            lines.append(f"  {markers[unit.id]} {team} {unit.name_zh}：{what}")
            continue
        lines.append(
            f"  {markers[unit.id]} {team} {unit.name_zh}：HP {unit.hp}/{unit.max_hp}"
            f"{f' 法力 {unit.mana}/{unit.max_mana}' if unit.max_mana else ''}"
            f"{_source_text(state, unit)}"
            f" 耐力 {unit.stamina} 位置 {xy_text(unit.pos)} 面向{FACING_TEXT[unit.facing]}"
            f" 武器 {unit.weapon.name_zh}"
            f"{_status_text(state, unit)}{_summon_text(state, unit)}"
            f"{_activation_text(state, unit)}{_granted_text(state, unit)}"
        )
    lines += render_zone_lines(state)
    return "\n".join(lines)


def render_telegraph(state: BattleState, forecast: Telegraph) -> str:
    """環境預告（每輪開始時顯示）：本輪結束時環境回合將發生的變化。"""
    lines: list[str] = []
    name = {uid: u.name_zh for uid, u in state.units.items()}
    exploded = {c.object_id for c in forecast.changes if c.kind == "object_exploded"}
    zone_kinds = (
        "zone_moved",
        "zone_expired",
        "bomb_exploded",
        "object_expired",
    )  # 區域（3D-5）、炸彈（3D-8b）、暫時障礙到期（3-11）：沿用網頁的預告文字
    for c in (c for c in forecast.changes if c.kind not in zone_kinds):
        if c.kind == "object_destroyed" and c.object_id in exploded:
            continue
        where = f"({c.pos.x}, {c.pos.y})" if c.pos is not None else ""
        if c.kind == "surface" and c.after is not None and c.before is not None:
            after = surface_name(state, Surface(c.after))
            before = surface_name(state, Surface(c.before))
            lines.append(f"{where} {before}→{after}")
        elif c.kind == "object_destroyed" and c.object_id is not None:
            lines.append(f"{where} {object_name(state, c.object_id)}將會倒塌")
        elif c.kind == "object_exploded" and c.object_id is not None:
            lines.append(f"{where} {object_name(state, c.object_id)}將會爆炸")
        elif c.kind == "object_ignited" and c.object_id is not None:
            lines.append(f"{where} {object_name(state, c.object_id)}將會著火")
        elif c.kind == "terrain":
            lines.append(f"{where} 地形改變")
        elif c.kind == "unit_spawned":
            lines.append(f"{where} 援軍出現")
        elif c.kind == "unit_downed" and c.unit_id is not None:
            lines.append(f"{name.get(c.unit_id, c.unit_id)} 將會倒下")
    lines += [change_text(state, c) for c in forecast.changes if c.kind in zone_kinds]
    announced = {c.unit_id for c in forecast.changes if c.kind == "bomb_exploded"}
    lines += [  # 下一次就爆炸的炸彈已有上面「爆炸」那一行（3C-6a），不重複
        bomb_text(state, b) for b in forecast.bombs if not (b.explodes and b.unit_id in announced)
    ]
    for oid, rounds in forecast.burning:
        lines.append(f"{object_name(state, oid)}還能撐 {rounds} 次環境回合")
    for event in forecast.upcoming:
        what = "援軍" if isinstance(event, SpawnUnitsEvent) else "地形變化"
        lines.append(f"下一輪結束時：{what}")
    if not lines:
        return ""
    unique = list(dict.fromkeys(lines))
    return "  環境預告：" + "；".join(unique)


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
                actual = e.amount - e.absorbed  # 被護盾吸收的不算
                stats.per_unit[e.target_id].taken += actual
                if e.source_id is not None:
                    stats.per_unit[e.source_id].dealt += actual
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
            result = (
                "倒下"
                if unit.downed
                else "已消失"
                if unit.dismissed
                else f"HP {unit.hp}/{unit.max_hp}"
            )
            lines.append(
                f"  {markers[uid]:<4} {label}{' ' * max(pad, 1)}{s.dealt:>8} {s.taken:>8}"
                f" {s.hits:>4}/{s.attacks:<4} {s.crits:>4} {s.kills:>4} {result}"
            )
        return "\n".join(lines)
