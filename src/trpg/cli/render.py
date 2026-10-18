"""文字渲染：地圖網格、戰場網格、繁體中文戰鬥紀錄與統計。

引擎事件只描述發生了什麼；所有顯示文字都在這裡產生。
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from trpg.content.library import Ruleset
from trpg.content.maps import MapDef, SpawnUnitsEvent
from trpg.engine.environment import Telegraph
from trpg.engine.events import (
    AttackRolled,
    BattleEnded,
    BattleStarted,
    ChainLimitReached,
    CheckRolled,
    DamageDealt,
    EffectFizzled,
    ElementTouched,
    EnteredDeadlyTerrain,
    EnvironmentEnded,
    EnvironmentStarted,
    EventBase,
    Healed,
    InitiativeRolled,
    InitiativeTieBroken,
    ManeuverRolled,
    MapEventTriggered,
    MoveBlocked,
    ObjectAttacked,
    ObjectCreated,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExploded,
    ObjectIgnited,
    ObjectMoved,
    PushResisted,
    ReactionDeclined,
    ReactionTriggered,
    RoundEnded,
    RoundStarted,
    SkillCooldownChanged,
    SkillUsed,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    StatusResisted,
    StatusSaveRolled,
    SurfaceChanged,
    SurfaceEntered,
    TerrainChanged,
    TurnEnded,
    TurnOrderSet,
    TurnSkipped,
    TurnStarted,
    UnitDowned,
    UnitEscaped,
    UnitFell,
    UnitMoved,
    UnitSpawned,
    UnitStoodUp,
)
from trpg.engine.rules.combat import is_concealed
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, Surface, Team

__all__ = [
    "BattleStats",
    "describe_event",
    "render_battle_grid",
    "render_map",
    "render_telegraph",
    "render_unit_table",
    "unit_markers",
]

_PPM = 1_000_000
_PERMILLE = 1000
_LABEL_WIDTH = 14
_WIDE_CHAR_START = 0x2E7F  # 之後的 CJK 字元在終端機佔兩格

_CAUSE_NAMES = {
    "attack": "",
    "fall": "墜落",
    "deadly_terrain": "致命地形",
    "status": "持續",
    "effect": "",
    "explosion": "爆炸",
    "conduct": "傳導",
    "surface": "表面",
}

_END_REASONS = {
    "eliminate": "全滅",
    "escaped": "撤離成功",
    "escape_failed": "撤離超時",
    "defended": "守住守點",
    "point_lost": "守點失守",
    "round_limit": "輪數上限",
}

_OBJECTIVES = {"eliminate": "擊倒所有敵人", "escape": "撤離", "defend": "守點"}

_DESTROY_CAUSES = {
    "damage": "被摧毀",
    "burned": "燒毀",
    "explosion": "炸毀",
    "filled": "被填平",
    "fell": "掉落深處",
    "effect": "被摧毀",
}


def _xy(pos: Pos) -> str:
    return f"({pos.x}, {pos.y})"


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
    """戰場網格：每格「高度 ＋ 單位／物件／地形字元 ＋ 表面字元」。"""
    markers = unit_markers(state)
    occupancy = state.occupancy()
    surf_glyph = _surface_glyphs(state.ruleset)
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
    return ("  圖例：" + "、".join(parts)) if parts else ""


def _status_text(state: BattleState, unit: UnitState) -> str:
    parts = []
    for s in unit.statuses:
        name = state.ruleset.status_def(s.status_id).name_zh
        parts.append(name if s.remaining is None else f"{name}{s.remaining}")
    if not unit.has_status("concealed") and is_concealed(state, unit):
        parts.append("隱蔽")
    return ("［" + "、".join(parts) + "］") if parts else ""


def render_unit_table(state: BattleState) -> str:
    markers = unit_markers(state)
    lines = []
    for unit in state.units_sorted():
        team = unit.team.display_name
        if unit.downed or unit.escaped:
            what = "倒下" if unit.downed else "已撤離"
            lines.append(f"  {markers[unit.id]} {team} {unit.name_zh}：{what}")
            continue
        lines.append(
            f"  {markers[unit.id]} {team} {unit.name_zh}：HP {unit.hp}/{unit.max_hp}"
            f"{f' 法力 {unit.mana}/{unit.max_mana}' if unit.max_mana else ''}"
            f" 耐力 {unit.stamina} 位置 {_xy(unit.pos)} 武器 {unit.weapon.name_zh}"
            f"{_status_text(state, unit)}"
        )
    return "\n".join(lines)


def _signed(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _attack_text(e: AttackRolled, name: dict[str, str], state: BattleState) -> str:
    if e.advantage == "none":
        dice = f"d20={e.natural}"
    else:
        label = "優勢" if e.advantage == "advantage" else "劣勢"
        dice = f"d20（{label} {e.rolls[0]}、{e.rolls[1]}）={e.natural}"
    parts = [dice, f"修正 {_signed(e.hit_modifier)}", f"熟練 {_signed(e.proficiency)}"]
    if e.situational:
        parts.append(f"高度 {_signed(e.situational)}")
    cover_note = ""
    if e.cover:
        parts.append(f"半掩護 {_signed(e.cover)}")
        obj = state.objects.get(e.cover_object_id) if e.cover_object_id is not None else None
        if obj is not None:
            cover_name = state.ruleset.object_def(obj.kind).name_zh
            cover_note = f"［命中 −{-e.cover}：{cover_name}掩護］"
    if e.natural == 20:  # noqa: PLR2004 - 自然 20
        verdict = "自然 20，暴擊！" if e.crit else "自然 20，命中"
    elif e.natural == 1:
        verdict = "自然 1，失手"
    else:
        verdict = ("暴擊！" if e.crit else "命中") if e.hit else "失手"
    verb = "攻擊"
    if e.skill_id is not None:
        verb = f"以「{state.ruleset.skill_def(e.skill_id).name_zh}」攻擊"
    return (
        f"{name[e.attacker_id]} {verb} {name[e.target_id]}：{' '.join(parts)} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}{cover_note}"
    )


def _skill_used_text(e: SkillUsed, name: dict[str, str]) -> str:
    costs = [f"AP {e.ap}"]
    if e.mana:
        costs.append(f"法力 {e.mana}")
    if e.hp_spent:
        costs.append(f"HP {e.hp_spent}")
    if e.cooldown:
        costs.append(f"冷卻 {e.cooldown} 回合")
    return f"{name[e.unit_id]} 施放「{e.name_zh}」（{'，'.join(costs)}）→ 影響 {len(e.tiles)} 格"


def _damage_text(e: DamageDealt, name: dict[str, str]) -> str:
    cause = _CAUSE_NAMES[e.cause]
    element = e.element.display_name
    kind = f"{cause}{element}" if cause and e.cause != "status" else element
    if e.cause in ("fall", "deadly_terrain"):
        kind = cause
    elif e.cause in ("explosion", "conduct", "surface"):
        kind = f"{cause}{element}"
    rolls = f"［骰 {'+'.join(str(r) for r in e.rolls)}］" if e.rolls else ""
    mod = ""
    if e.element_mod_ppm != _PPM:
        mod = f"（元素修正 ×{e.element_mod_ppm / _PPM:g}）"
    if e.weather_permille != 1000:  # noqa: PLR2004
        mod += f"（天氣 ×{e.weather_permille / 1000:g}）"
    if e.multiplier_permille != 1000:  # noqa: PLR2004
        mod += f"（格擋 ×{e.multiplier_permille / 1000:g}）"
    if e.status_ppm != _PPM:
        mod += f"（狀態 ×{e.status_ppm / _PPM:g}）"
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
    if isinstance(e, InitiativeTieBroken):
        return f"先攻平手（總值 {e.total}、敏捷 {e.dex}），以亂數決定：" + " → ".join(
            name[u] for u in e.order
        )
    if isinstance(e, TurnOrderSet):
        return "行動順序：" + " → ".join(name[u] for u in e.order)
    if isinstance(e, RoundStarted | RoundEnded):
        return None
    if isinstance(e, TurnStarted):
        mana = f"，法力 {e.mana}/{e.max_mana}" if e.max_mana else ""
        return f"— {name[e.unit_id]} 的回合（AP {e.ap}，移動 {e.move_points}{mana}）"
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
        return "  " + _attack_text(e, name, state)
    if isinstance(e, SkillUsed):
        return "  " + _skill_used_text(e, name)
    if isinstance(e, SkillCooldownChanged):
        if e.remaining > 0:
            return None
        return f"  {name[e.unit_id]} 的「{state.ruleset.skill_def(e.skill_id).name_zh}」冷卻結束"
    if isinstance(e, DamageDealt):
        return "    " + _damage_text(e, name)
    if isinstance(e, Healed):
        half = (
            f"（治療 ×{e.received_permille / _PERMILLE:g}）"
            if e.received_permille != _PERMILLE
            else ""
        )
        return f"    {name[e.target_id]} 回復 {e.amount} HP{half}，HP {e.hp_before} → {e.hp_after}"
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
        return f"戰鬥結束：{e.winner.display_name}勝利（{_END_REASONS[e.reason]}）"
    control = _describe_control(e, name, statuses)
    if control is not None:
        return control
    return _describe_environment(e, state, name, statuses)


def _describe_control(e: EventBase, name: dict[str, str], statuses: dict[str, str]) -> str | None:
    """狀態的抵抗判定、Boss 轉換與跳過回合（Phase 2B-1）。"""
    if isinstance(e, StatusSaveRolled):
        verdict = "施加成功" if e.applied else "被抵抗"
        dr = "，遞減中" if e.diminished else ""
        return (
            f"  {name[e.attacker_id]} 對 {name[e.target_id]} 施加「{statuses[e.status_id]}」"
            f"（{e.attack_attr.display_name} {e.attack_value} vs "
            f"{e.save_attr.display_name} {e.defense_value}{dr}）：d20={e.natural} "
            f"修正 {_signed(e.modifier)} 熟練 {_signed(e.proficiency)} = {e.total}"
            f"（目標 {e.target_number}）→ {verdict}"
        )
    if isinstance(e, StatusResisted):
        return f"  {name[e.target_id]} 抵抗了「{statuses[e.status_id]}」"
    if isinstance(e, StatusConverted):
        return (
            f"  {name[e.target_id]} 是首領：「{statuses[e.from_status]}」"
            f"轉為「{statuses[e.to_status]}」"
        )
    if isinstance(e, TurnSkipped):
        return f"  {name[e.unit_id]} 受到「{statuses[e.status_id]}」影響，跳過這個回合"
    return None


def _obj_name(state: BattleState, object_id: str) -> str:
    obj = state.objects.get(object_id)  # type: ignore[call-overload]
    return "物件" if obj is None else state.ruleset.object_def(obj.kind).name_zh


def _surface_name(state: BattleState, surface: Surface) -> str:
    return "無" if surface is Surface.NONE else state.ruleset.surface_def(surface).name_zh


def _describe_environment(  # noqa: PLR0911, PLR0912
    e: EventBase, state: BattleState, name: dict[str, str], statuses: dict[str, str]
) -> str | None:
    """Phase 1B 的事件（物件、表面、反應、環境回合……）。"""
    if isinstance(e, EnvironmentStarted):
        return "～ 環境回合 ～"
    if isinstance(e, EnvironmentEnded | ElementTouched | SurfaceEntered):
        return None
    if isinstance(e, ObjectAttacked):
        target = _obj_name(state, e.object_id) + _xy_of(state, e.object_id)
        return f"  {name[e.attacker_id]} 攻擊 {target}"
    if isinstance(e, ObjectDamaged):
        rolls = f"［骰 {'+'.join(str(r) for r in e.rolls)}］" if e.rolls else ""
        return (
            f"    {_obj_name(state, e.object_id)} 受到 {e.amount} 點{e.element.display_name}傷害"
            f"{rolls}，HP {e.hp_before} → {e.hp_after}"
        )
    if isinstance(e, ObjectDestroyed):
        return f"  ＊ {_obj_name(state, e.object_id)} {_xy(e.pos)} {_DESTROY_CAUSES[e.cause]}！"
    if isinstance(e, ObjectExploded):
        return f"  ＊ {_obj_name(state, e.object_id)} {_xy(e.pos)} 爆炸了！"
    if isinstance(e, ObjectIgnited):
        return (
            f"  {_obj_name(state, e.object_id)} {_xy(e.pos)} 著火了（{e.rounds} 次環境回合後燒毀）"
        )
    if isinstance(e, ObjectMoved):
        return f"  {_obj_name(state, e.object_id)} 被推到 {_xy(e.to_pos)}"
    if isinstance(e, ObjectCreated):
        return f"  {_xy(e.pos)} 出現了{state.ruleset.object_def(e.kind).name_zh}"
    if isinstance(e, SurfaceChanged):
        before, after = _surface_name(state, e.before), _surface_name(state, e.after)
        if e.after is Surface.NONE:
            return f"  {_xy(e.pos)} 的{before}消失了"
        if e.before is Surface.NONE:
            return f"  {_xy(e.pos)} 出現了{after}"
        return f"  {_xy(e.pos)} 的{before}變成了{after}"
    if isinstance(e, TerrainChanged):
        if e.terrain_before != e.terrain_after:
            t = state.ruleset.terrain_def(e.terrain_after).name_zh
            return f"  {_xy(e.pos)} 變成了{t}"
        return f"  {_xy(e.pos)} 的高度 {e.height_before} → {e.height_after}"
    if isinstance(e, CheckRolled):
        verdict = "通過" if e.success else "失敗"
        return (
            f"  {name[e.unit_id]} {e.attr.display_name}檢定：d20={e.roll} "
            f"{_signed(e.modifier)} = {e.total}（DC {e.dc}）→ {verdict}"
        )
    if isinstance(e, ManeuverRolled):
        kind = {"shove": "推擊", "trip": "絆倒", "knock_prone": "擊倒"}[e.maneuver]
        verdict = "成功" if e.success else "失敗"
        return (
            f"  {name[e.attacker_id]} 對 {name[e.target_id]} 使出{kind}：d20={e.natural} "
            f"修正 {_signed(e.modifier)} 熟練 {_signed(e.proficiency)} = {e.total}"
            f"（目標 {e.target_number}）→ {verdict}"
        )
    if isinstance(e, PushResisted):
        return f"  {name[e.unit_id]} 穩如泰山：推擊距離 {e.requested} → {e.distance}"
    if isinstance(e, ReactionTriggered):
        reaction = state.ruleset.reaction_def(e.reaction).name_zh
        cost = f"（耐力 −{e.stamina_spent}）" if e.stamina_spent else ""
        return f"  ⟳ {name[e.unit_id]} 反應：{reaction}{cost}"
    if isinstance(e, ReactionDeclined):
        reaction = state.ruleset.reaction_def(e.reaction).name_zh
        return f"  {name[e.unit_id]} 放棄反應：{reaction}"
    if isinstance(e, MapEventTriggered):
        return "  地圖事件：" + ("援軍出現！" if e.kind == "spawn_units" else "地形改變！")
    if isinstance(e, UnitSpawned):
        return f"  {name.get(e.unit_id, e.unit_id)} 出現在 {_xy(e.pos)}"
    if isinstance(e, UnitEscaped):
        return f"  {name[e.unit_id]} 從 {_xy(e.pos)} 撤離戰場"
    if isinstance(e, EffectFizzled):
        return None
    return None  # pragma: no cover - 新事件類型尚未有中文描述


def _xy_of(state: BattleState, object_id: str) -> str:
    obj = state.objects.get(object_id)  # type: ignore[call-overload]
    return "" if obj is None else " " + _xy(obj.pos)


def render_telegraph(state: BattleState, forecast: Telegraph) -> str:
    """環境預告（每輪開始時顯示）：本輪結束時環境回合將發生的變化。"""
    lines: list[str] = []
    name = {uid: u.name_zh for uid, u in state.units.items()}
    exploded = {c.object_id for c in forecast.changes if c.kind == "object_exploded"}
    for c in forecast.changes:
        if c.kind == "object_destroyed" and c.object_id in exploded:
            continue
        where = f"({c.pos.x}, {c.pos.y})" if c.pos is not None else ""
        if c.kind == "surface" and c.after is not None and c.before is not None:
            after = _surface_name(state, Surface(c.after))
            before = _surface_name(state, Surface(c.before))
            lines.append(f"{where} {before}→{after}")
        elif c.kind == "object_destroyed" and c.object_id is not None:
            lines.append(f"{where} {_obj_name(state, c.object_id)}將會倒塌")
        elif c.kind == "object_exploded" and c.object_id is not None:
            lines.append(f"{where} {_obj_name(state, c.object_id)}將會爆炸")
        elif c.kind == "object_ignited" and c.object_id is not None:
            lines.append(f"{where} {_obj_name(state, c.object_id)}將會著火")
        elif c.kind == "terrain":
            lines.append(f"{where} 地形改變")
        elif c.kind == "unit_spawned":
            lines.append(f"{where} 援軍出現")
        elif c.kind == "unit_downed" and c.unit_id is not None:
            lines.append(f"{name.get(c.unit_id, c.unit_id)} 將會倒下")
    for oid, rounds in forecast.burning:
        lines.append(f"{_obj_name(state, oid)}還能撐 {rounds} 次環境回合")
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
