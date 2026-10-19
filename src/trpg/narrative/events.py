"""事件的繁體中文描述（原在 ``trpg.cli.render``，Phase 3-1 搬出，讓 CLI 與網頁共用）。

引擎事件只描述發生了什麼；所有顯示文字都在這裡產生。:func:`describe_event` 以事件類型查
註冊表 ``_HANDLERS``（``dict[type[EventBase], handler]``）；沒有對應處理器的事件類型回傳 ``None``。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from trpg.engine.events import (
    AttackIntercepted,
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
    ShieldAbsorbed,
    ShieldGained,
    SkillCooldownChanged,
    SkillTriggered,
    SkillUsed,
    StacksChanged,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    StatusResisted,
    StatusSaveRolled,
    SurfaceChanged,
    SurfaceEntered,
    TerrainChanged,
    TrapExpired,
    TrapPlaced,
    TrapTriggered,
    TriggerLimitReached,
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
from trpg.engine.state import BattleState
from trpg.shared.types import Pos, Surface

__all__ = [
    "SILENT_EVENT_TYPES",
    "battle_started_text",
    "describe_event",
    "object_name",
    "reaction_name",
    "surface_name",
    "xy_text",
]

_PPM = 1_000_000
_PERMILLE = 1000

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

_DESTROY_CAUSES = {
    "damage": "被摧毀",
    "burned": "燒毀",
    "explosion": "炸毀",
    "filled": "被填平",
    "fell": "掉落深處",
    "effect": "被摧毀",
}

_REMOVE_REASONS = {
    "depleted": "護盾耗盡了",
    "cleansed": "被淨化了",
    "source_lost": "解除了（來源離場）",
    "replaced": "被新的姿態取代了",
    "stance_ended": "取消了姿態",
    "downed": "解除了（倒下）",
    "thawed": "解除了（受到傷害）",
}


def xy_text(pos: Pos) -> str:
    """座標的顯示文字，例如 ``(3, 4)``。"""
    return f"({pos.x}, {pos.y})"


def object_name(state: BattleState, object_id: str) -> str:
    """物件的中文名稱（找不到時為「物件」）。"""
    obj = state.objects.get(object_id)  # type: ignore[call-overload]
    return "物件" if obj is None else state.ruleset.object_def(obj.kind).name_zh


def surface_name(state: BattleState, surface: Surface) -> str:
    """表面的中文名稱（沒有表面為「無」）。"""
    return "無" if surface is Surface.NONE else state.ruleset.surface_def(surface).name_zh


def _signed(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _rolls_text(rolls: tuple[int, ...] | list[int]) -> str:
    return f"［骰 {'+'.join(str(r) for r in rolls)}］" if rolls else ""


@dataclass(frozen=True)
class _View:
    """描述一個事件所需的名稱查表（單位名稱、狀態名稱）與戰鬥狀態。"""

    state: BattleState
    name: dict[str, str]
    statuses: dict[str, str]


type _Handler = Callable[[Any, _View], str | None]

_HANDLERS: dict[type[EventBase], _Handler] = {}


def _handles(*types: type[EventBase]) -> Callable[[_Handler], _Handler]:
    def register(fn: _Handler) -> _Handler:
        for t in types:
            _HANDLERS[t] = fn
        return fn

    return register


SILENT_EVENT_TYPES: tuple[type[EventBase], ...] = (
    RoundStarted,
    RoundEnded,
    EnvironmentEnded,
    ElementTouched,
    SurfaceEntered,
    EffectFizzled,
)
"""明確不顯示的事件類型（沒有處理器，:func:`describe_event` 回傳 ``None``）。"""


def describe_event(e: EventBase, state: BattleState) -> str | None:
    """把一個事件轉成一行繁體中文；不需要顯示的事件回傳 ``None``。"""
    handler = _HANDLERS.get(type(e))
    if handler is None:
        return None
    name: dict[str, str] = {uid: u.name_zh for uid, u in state.units.items()}
    statuses = {s.id: s.name_zh for s in state.ruleset.statuses.statuses}
    return handler(e, _View(state, name, statuses))


# ---------------------------------------------------------------------------
# 戰鬥流程與回合
# ---------------------------------------------------------------------------


def battle_started_text(state: BattleState, seed: int | None) -> str:
    """開場的描述；``seed`` 為 ``None`` 時不提種子（網頁 API 不公開種子）。"""
    text = f"戰鬥開始：{state.map_name_zh}（{state.width}×{state.height}）"
    return text if seed is None else f"{text}，種子 {seed}"


@_handles(BattleStarted)
def _battle_started(e: BattleStarted, v: _View) -> str:
    return battle_started_text(v.state, e.seed)


@_handles(InitiativeRolled)
def _initiative(e: InitiativeRolled, v: _View) -> str:
    return f"先攻：{v.name[e.unit_id]} d20={e.roll} {_signed(e.modifier)} = {e.total}"


@_handles(InitiativeTieBroken)
def _tie_broken(e: InitiativeTieBroken, v: _View) -> str:
    return f"先攻平手（總值 {e.total}、敏捷 {e.dex}），以亂數決定：" + " → ".join(
        v.name[u] for u in e.order
    )


@_handles(TurnOrderSet)
def _turn_order(e: TurnOrderSet, v: _View) -> str:
    return "行動順序：" + " → ".join(v.name[u] for u in e.order)


@_handles(TurnStarted)
def _turn_started(e: TurnStarted, v: _View) -> str:
    mana = f"，法力 {e.mana}/{e.max_mana}" if e.max_mana else ""
    return f"— {v.name[e.unit_id]} 的回合（AP {e.ap}，移動 {e.move_points}{mana}）"


@_handles(TurnEnded)
def _turn_ended(e: TurnEnded, v: _View) -> str:
    kept = f"，保留 {e.ap_carried} AP" if e.ap_carried else ""
    return f"  {v.name[e.unit_id]} 結束回合{kept}"


@_handles(TurnSkipped)
def _turn_skipped(e: TurnSkipped, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 受到「{v.statuses[e.status_id]}」影響，跳過這個回合"


@_handles(BattleEnded)
def _battle_ended(e: BattleEnded, _v: _View) -> str:
    if e.winner is None:
        return "戰鬥結束：達到輪數上限，平手" if e.reason == "round_limit" else "戰鬥結束：平手"
    return f"戰鬥結束：{e.winner.display_name}勝利（{_END_REASONS[e.reason]}）"


# ---------------------------------------------------------------------------
# 移動與位移
# ---------------------------------------------------------------------------


@_handles(UnitMoved)
def _unit_moved(e: UnitMoved, v: _View) -> str | None:
    if e.mode == "walk":
        return None  # 由 Move 動作整段顯示（見 CLI）
    verb = "被傳送到" if e.mode == "teleport" else "被推到"
    return f"  {v.name[e.unit_id]} {verb} {xy_text(e.to_pos)}"


@_handles(UnitStoodUp)
def _stood_up(e: UnitStoodUp, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 站了起來（消耗 {e.cost} 移動）"


@_handles(MoveBlocked)
def _move_blocked(e: MoveBlocked, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 無法移動到 {xy_text(e.to_pos)}"


@_handles(UnitFell)
def _unit_fell(e: UnitFell, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 從 {e.drop} 層高處跌落！"


@_handles(EnteredDeadlyTerrain)
def _deadly_terrain(e: EnteredDeadlyTerrain, v: _View) -> str:
    terrain = v.state.ruleset.terrain_def(e.terrain).name_zh
    return f"  {v.name[e.unit_id]} 掉進了{terrain}！"


@_handles(UnitDowned)
def _unit_downed(e: UnitDowned, v: _View) -> str:
    return f"  ＊ {v.name[e.unit_id]} 倒下了！"


# ---------------------------------------------------------------------------
# 攻擊、技能與傷害
# ---------------------------------------------------------------------------


@_handles(AttackRolled)
def _attack(e: AttackRolled, v: _View) -> str:
    state = v.state
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
        f"  {v.name[e.attacker_id]} {verb} {v.name[e.target_id]}：{' '.join(parts)} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}{cover_note}"
    )


@_handles(SkillUsed)
def _skill_used(e: SkillUsed, v: _View) -> str:
    costs = [f"AP {e.ap}"]
    if e.mana:
        costs.append(f"法力 {e.mana}")
    if e.hp_spent:
        costs.append(f"HP {e.hp_spent}")
    if e.cooldown:
        costs.append(f"冷卻 {e.cooldown} 回合")
    return (
        f"  {v.name[e.unit_id]} 施放「{e.name_zh}」（{'，'.join(costs)}）→ 影響 {len(e.tiles)} 格"
    )


@_handles(SkillTriggered)
def _skill_triggered(e: SkillTriggered, v: _View) -> str:
    timing = v.state.ruleset.trigger_def(e.trigger).name_zh
    costs = []
    if e.mana:
        costs.append(f"法力 {e.mana}")
    if e.hp_spent:
        costs.append(f"HP {e.hp_spent}")
    if e.cooldown:
        costs.append(f"冷卻 {e.cooldown} 回合")
    other = f"，對象 {v.name[e.other_id]}" if e.other_id is not None else ""
    cost = f"（{'，'.join(costs)}）" if costs else ""
    return (
        f"  ★ {v.name[e.unit_id]} 的被動「{e.name_zh}」觸發（{timing}，深度 {e.trigger_depth}）"
        f"{other}{cost}"
    )


@_handles(TriggerLimitReached)
def _trigger_limit(e: TriggerLimitReached, v: _View) -> str:
    return (
        f"  （觸發深度達到上限，{v.name[e.unit_id]} 的被動「{e.skill_id}」沒有觸發"
        f"，深度 {e.depth}）"
    )


@_handles(SkillCooldownChanged)
def _cooldown(e: SkillCooldownChanged, v: _View) -> str | None:
    if e.remaining > 0:
        return None
    return f"  {v.name[e.unit_id]} 的「{v.state.ruleset.skill_def(e.skill_id).name_zh}」冷卻結束"


@_handles(DamageDealt)
def _damage(e: DamageDealt, v: _View) -> str:
    cause = _CAUSE_NAMES[e.cause]
    element = e.element.display_name
    kind = f"{cause}{element}" if cause and e.cause != "status" else element
    if e.cause in ("fall", "deadly_terrain"):
        kind = cause
    elif e.cause in ("explosion", "conduct", "surface"):
        kind = f"{cause}{element}"
    mod = ""
    if e.element_mod_ppm != _PPM:
        mod = f"（元素修正 ×{e.element_mod_ppm / _PPM:g}）"
    if e.weather_permille != _PERMILLE:
        mod += f"（天氣 ×{e.weather_permille / _PERMILLE:g}）"
    if e.multiplier_permille != _PERMILLE:
        mod += f"（格擋/加成 ×{e.multiplier_permille / _PERMILLE:g}）"
    if e.status_ppm != _PPM:
        mod += f"（狀態 ×{e.status_ppm / _PPM:g}）"
    shield = f"（護盾吸收 {e.absorbed}）" if e.absorbed else ""
    return (
        f"    {v.name[e.target_id]} 受到 {e.amount} 點{kind}傷害{_rolls_text(e.rolls)}"
        f"{mod}{shield}，HP {e.hp_before} → {e.hp_after}"
    )


@_handles(Healed)
def _healed(e: Healed, v: _View) -> str:
    half = (
        f"（治療 ×{e.received_permille / _PERMILLE:g}）" if e.received_permille != _PERMILLE else ""
    )
    return f"    {v.name[e.target_id]} 回復 {e.amount} HP{half}，HP {e.hp_before} → {e.hp_after}"


@_handles(ChainLimitReached)
def _chain_limit(e: ChainLimitReached, _v: _View) -> str:
    return f"  （連鎖達到上限，{e.effect_kind} 效果沒有發生）"


# ---------------------------------------------------------------------------
# 狀態、護盾、層數與陷阱
# ---------------------------------------------------------------------------


@_handles(StatusApplied)
def _status_applied(e: StatusApplied, v: _View) -> str:
    verb = "刷新" if e.refreshed else "獲得"
    turns = f"（{e.duration} 回合）" if e.duration else ""
    return f"  {v.name[e.target_id]} {verb}狀態「{v.statuses[e.status_id]}」{turns}"


@_handles(ShieldGained)
def _shield_gained(e: ShieldGained, v: _View) -> str:
    extra = f"（取較大值，共 {e.total}）" if e.total != e.amount else ""
    return f"    {v.name[e.unit_id]} 獲得 {e.amount} 點護盾{extra}"


@_handles(ShieldAbsorbed)
def _shield_absorbed(e: ShieldAbsorbed, v: _View) -> str:
    return f"    {v.name[e.unit_id]} 的護盾吸收了 {e.absorbed} 點傷害，剩餘 {e.remaining}"


@_handles(StatusRemoved)
def _status_removed(e: StatusRemoved, v: _View) -> str | None:
    if e.reason == "stood_up":
        return None
    why = _REMOVE_REASONS.get(e.reason)
    text = f"  {v.name[e.target_id]} 的「{v.statuses[e.status_id]}」"
    return text + (f"{why}" if why else "結束了")


@_handles(StatusSaveRolled)
def _status_save(e: StatusSaveRolled, v: _View) -> str:
    verdict = "施加成功" if e.applied else "被抵抗"
    dr = "，遞減中" if e.diminished else ""
    return (
        f"  {v.name[e.attacker_id]} 對 {v.name[e.target_id]} 施加「{v.statuses[e.status_id]}」"
        f"（{e.attack_attr.display_name} {e.attack_value} vs "
        f"{e.save_attr.display_name} {e.defense_value}{dr}）：d20={e.natural} "
        f"修正 {_signed(e.modifier)} 熟練 {_signed(e.proficiency)} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}"
    )


@_handles(StatusResisted)
def _status_resisted(e: StatusResisted, v: _View) -> str:
    return f"  {v.name[e.target_id]} 抵抗了「{v.statuses[e.status_id]}」"


@_handles(StatusConverted)
def _status_converted(e: StatusConverted, v: _View) -> str:
    return (
        f"  {v.name[e.target_id]} 是首領：「{v.statuses[e.from_status]}」"
        f"轉為「{v.statuses[e.to_status]}」"
    )


@_handles(StacksChanged)
def _stacks(e: StacksChanged, v: _View) -> str:
    stack = v.state.ruleset.stack_def(e.stack_id).name_zh
    verb = {"gained": "累積", "consumed": "消耗", "expired": "過期清空"}[e.reason]
    return f"    {v.name[e.unit_id]} 的「{stack}」{verb}：{e.before} → {e.after} 層"


@_handles(TrapPlaced)
def _trap_placed(e: TrapPlaced, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    when = (
        f"敵人踩上時觸發，{e.rounds} 輪後消失" if e.trigger == "enter" else f"{e.rounds} 輪後引爆"
    )
    return f"    {v.name[e.owner_id]} 在 {xy_text(e.pos)} 設下陷阱「{skill}」（{when}）"


@_handles(TrapTriggered)
def _trap_triggered(e: TrapTriggered, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    who = f"{v.name[e.unit_id]} 踩中了" if e.unit_id is not None else "引爆了"
    return f"  ！{who} {xy_text(e.pos)} 的陷阱「{skill}」（{v.name[e.owner_id]} 設置）"


@_handles(TrapExpired)
def _trap_expired(e: TrapExpired, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    why = "放置者離場" if e.reason == "source_lost" else "沒人踩到，時間到"
    return f"  {v.name[e.owner_id]} 在 {xy_text(e.pos)} 的陷阱「{skill}」消失了（{why}）"


# ---------------------------------------------------------------------------
# 物件、表面、地形與環境
# ---------------------------------------------------------------------------


def _object_xy(state: BattleState, object_id: str) -> str:
    obj = state.objects.get(object_id)  # type: ignore[call-overload]
    return "" if obj is None else " " + xy_text(obj.pos)


@_handles(ObjectAttacked)
def _object_attacked(e: ObjectAttacked, v: _View) -> str:
    target = object_name(v.state, e.object_id) + _object_xy(v.state, e.object_id)
    return f"  {v.name[e.attacker_id]} 攻擊 {target}"


@_handles(ObjectDamaged)
def _object_damaged(e: ObjectDamaged, v: _View) -> str:
    return (
        f"    {object_name(v.state, e.object_id)} 受到 {e.amount} 點{e.element.display_name}傷害"
        f"{_rolls_text(e.rolls)}，HP {e.hp_before} → {e.hp_after}"
    )


@_handles(ObjectDestroyed)
def _object_destroyed(e: ObjectDestroyed, v: _View) -> str:
    return f"  ＊ {object_name(v.state, e.object_id)} {xy_text(e.pos)} {_DESTROY_CAUSES[e.cause]}！"


@_handles(ObjectExploded)
def _object_exploded(e: ObjectExploded, v: _View) -> str:
    return f"  ＊ {object_name(v.state, e.object_id)} {xy_text(e.pos)} 爆炸了！"


@_handles(ObjectIgnited)
def _object_ignited(e: ObjectIgnited, v: _View) -> str:
    return (
        f"  {object_name(v.state, e.object_id)} {xy_text(e.pos)} 著火了"
        f"（{e.rounds} 次環境回合後燒毀）"
    )


@_handles(ObjectMoved)
def _object_moved(e: ObjectMoved, v: _View) -> str:
    return f"  {object_name(v.state, e.object_id)} 被推到 {xy_text(e.to_pos)}"


@_handles(ObjectCreated)
def _object_created(e: ObjectCreated, v: _View) -> str:
    return f"  {xy_text(e.pos)} 出現了{v.state.ruleset.object_def(e.kind).name_zh}"


@_handles(SurfaceChanged)
def _surface_changed(e: SurfaceChanged, v: _View) -> str:
    before, after = surface_name(v.state, e.before), surface_name(v.state, e.after)
    if e.after is Surface.NONE:
        return f"  {xy_text(e.pos)} 的{before}消失了"
    if e.before is Surface.NONE:
        return f"  {xy_text(e.pos)} 出現了{after}"
    return f"  {xy_text(e.pos)} 的{before}變成了{after}"


@_handles(TerrainChanged)
def _terrain_changed(e: TerrainChanged, v: _View) -> str:
    if e.terrain_before != e.terrain_after:
        t = v.state.ruleset.terrain_def(e.terrain_after).name_zh
        return f"  {xy_text(e.pos)} 變成了{t}"
    return f"  {xy_text(e.pos)} 的高度 {e.height_before} → {e.height_after}"


@_handles(EnvironmentStarted)
def _environment_started(_e: EnvironmentStarted, _v: _View) -> str:
    return "～ 環境回合 ～"


@_handles(MapEventTriggered)
def _map_event(e: MapEventTriggered, _v: _View) -> str:
    return "  地圖事件：" + ("援軍出現！" if e.kind == "spawn_units" else "地形改變！")


@_handles(UnitSpawned)
def _unit_spawned(e: UnitSpawned, v: _View) -> str:
    return f"  {v.name.get(e.unit_id, e.unit_id)} 出現在 {xy_text(e.pos)}"


@_handles(UnitEscaped)
def _unit_escaped(e: UnitEscaped, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 從 {xy_text(e.pos)} 撤離戰場"


# ---------------------------------------------------------------------------
# 檢定與反應
# ---------------------------------------------------------------------------


@_handles(CheckRolled)
def _check_rolled(e: CheckRolled, v: _View) -> str:
    verdict = "通過" if e.success else "失敗"
    return (
        f"  {v.name[e.unit_id]} {e.attr.display_name}檢定：d20={e.roll} "
        f"{_signed(e.modifier)} = {e.total}（DC {e.dc}）→ {verdict}"
    )


@_handles(ManeuverRolled)
def _maneuver(e: ManeuverRolled, v: _View) -> str:
    kind = {"shove": "推擊", "trip": "絆倒", "knock_prone": "擊倒"}[e.maneuver]
    verdict = "成功" if e.success else "失敗"
    return (
        f"  {v.name[e.attacker_id]} 對 {v.name[e.target_id]} 使出{kind}：d20={e.natural} "
        f"修正 {_signed(e.modifier)} 熟練 {_signed(e.proficiency)} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}"
    )


@_handles(PushResisted)
def _push_resisted(e: PushResisted, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 穩如泰山：推擊距離 {e.requested} → {e.distance}"


def reaction_name(state: BattleState, reaction_id: str) -> str:
    """反應的顯示名稱：內建反應（``reactions.yaml``）或反應技（技能 ID）。"""
    if reaction_id.startswith("skill_"):
        return f"「{state.ruleset.skill_def(reaction_id).name_zh}」"
    return state.ruleset.reaction_def(reaction_id).name_zh


@_handles(ReactionTriggered)
def _reaction_triggered(e: ReactionTriggered, v: _View) -> str:
    cost = f"（耐力 −{e.stamina_spent}）" if e.stamina_spent else ""
    return f"  ⟳ {v.name[e.unit_id]} 反應：{reaction_name(v.state, e.reaction)}{cost}"


@_handles(ReactionDeclined)
def _reaction_declined(e: ReactionDeclined, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 放棄反應：{reaction_name(v.state, e.reaction)}"


@_handles(AttackIntercepted)
def _intercepted(e: AttackIntercepted, v: _View) -> str:
    name = v.name
    skill = "" if e.skill_id is None else f"「{v.state.ruleset.skill_def(e.skill_id).name_zh}」"
    return (
        f"  🛡 {name[e.guardian_id]} 攔截了 {name[e.attacker_id]} 對 {name[e.target_id]} 的"
        f"攻擊{skill}——改由 {name[e.guardian_id]} 承受"
    )
