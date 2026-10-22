"""事件的繁體中文描述（原在 ``trpg.cli.render``，Phase 3-1 搬出，讓 CLI 與網頁共用）。

引擎事件只描述發生了什麼；所有顯示文字都在這裡產生。:func:`describe_event` 以事件類型查
註冊表 ``_HANDLERS``（``dict[type[EventBase], handler]``）；沒有對應處理器的事件類型回傳 ``None``。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from trpg.engine.events import (
    ActivationExpired,
    ApGranted,
    ApRefunded,
    AttackIntercepted,
    AttackRolled,
    BacklashTriggered,
    BattleEnded,
    BattleStarted,
    BombExploded,
    BombTicked,
    ChainLimitReached,
    ChargeActivated,
    CheckRolled,
    Collided,
    DamageDealt,
    DamageRedirected,
    DeathCheated,
    EffectFizzled,
    ElementTouched,
    EnteredDeadlyTerrain,
    EnvironmentEnded,
    EnvironmentStarted,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    GambleRolled,
    GearHpLost,
    GearTriggered,
    GuardSet,
    Healed,
    InfusedSkillCast,
    InfusionFizzled,
    InitiativeRolled,
    InitiativeTieBroken,
    ManeuverRolled,
    MapEventTriggered,
    MoveBlocked,
    ObjectAttacked,
    ObjectCreated,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExpired,
    ObjectExploded,
    ObjectHurled,
    ObjectIgnited,
    ObjectMoved,
    ObjectToppled,
    OverloadTriggered,
    PushResisted,
    ReactionDeclined,
    ReactionModeSet,
    ReactionsGranted,
    ReactionTriggered,
    ResourceRestored,
    RoundEnded,
    RoundStarted,
    RuleChangeTriggered,
    RuneInscribed,
    RuneRemoved,
    ShieldAbsorbed,
    ShieldGained,
    ShotPierced,
    SkillActivated,
    SkillCooldownChanged,
    SkillCopied,
    SkillFollowup,
    SkillGranted,
    SkillGrantExpired,
    SkillInfused,
    SkillTriggered,
    SkillUsed,
    SnareTriggered,
    SourceChanged,
    StacksChanged,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    StatusResisted,
    StatusSaveRolled,
    SummonCommanded,
    SummonDetonated,
    SummonExpired,
    SummonModeSet,
    SummonPulled,
    SurfaceChanged,
    SurfaceEntered,
    TerrainChanged,
    TotemPulsed,
    TrapExpired,
    TrapPlaced,
    TrapRevealed,
    TrapTriggered,
    TriggerLimitReached,
    TurnEnded,
    TurnOrderSet,
    TurnSkipped,
    TurnStarted,
    UnitAimed,
    UnitCharged,
    UnitDashed,
    UnitDowned,
    UnitEscaped,
    UnitFell,
    UnitMoved,
    UnitRan,
    UnitRevived,
    UnitSpawned,
    UnitStoodUp,
    UnitSummoned,
    UnitVaulted,
    WallToppled,
    WeaponReloaded,
    ZoneCreated,
    ZoneExpired,
    ZoneMoved,
    ZoneTriggered,
)
from trpg.engine.skill_triggers import MODIFIER_ON_HIT
from trpg.engine.state import BattleState
from trpg.shared.types import Pos, Surface, rune_name

__all__ = [
    "DIRECTION_TEXT",
    "SILENT_EVENT_TYPES",
    "battle_started_text",
    "cells_text",
    "describe_event",
    "object_name",
    "reaction_name",
    "surface_name",
    "xy_text",
    "zone_anchor_text",
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
    "collision": "撞擊",
    "topple": "壓傷",
    "backlash": "反噬",
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
    "hurled": "摔得粉碎",
    "toppled": "倒下了",
}

_REMOVE_REASONS = {
    "depleted": "護盾耗盡了",
    "cleansed": "被淨化了",
    "source_lost": "解除了（來源離場）",
    "replaced": "被新的姿態取代了",
    "stance_ended": "取消了姿態",
    "downed": "解除了（倒下）",
    "thawed": "解除了（受到傷害）",
    "consumed": "被消耗了",
    "spent": "擋下致命傷害後消失了",
    "stolen": "被奪走了",
    "dispelled": "被驅散了",
    "revealed": "被揭露而消失了",
    "fired": "射擊後結束了",
    "ambushed": "在偷襲之後解除了",
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
    if e.mode in ("walk", "dash"):
        return None  # 由 Move 動作整段顯示（見 CLI）；衝鋒由 unit_dashed 整段顯示
    verb = _MOVE_VERBS.get(e.mode, "被推到")
    return f"  {v.name[e.unit_id]} {verb} {xy_text(e.to_pos)}"


_MOVE_VERBS = {
    "teleport": "被傳送到",
    "teleported": "被傳送到",
    "leap": "跳躍到",
    "swap": "交換位置，換到",
    "shadowstep": "瞬步到",
}


_FIZZLE_TEXT = {
    "dash_blocked": "  衝鋒被擋下，沒有抵達目標身旁：其餘效果不結算",
    "dash_no_path": "  衝鋒找不到路：其餘效果不結算",
    "shadowstep_blocked": "  瞬步找不到落腳處：其餘效果不結算",
    "charge_no_path": "  衝撞被擋住，停不下來",
    "swap_blocked": "  無法交換位置（有一方站不上對方的格子）",
    "summon_blocked": "  召喚位置被占據，召喚失敗",
    "unknown_summon": "  召喚失敗（未知的召喚物）",
    "followup_blocked": "  位移被擋下，沒有抵達落點：第二段不結算",
    "followup_caster_down": "  施放者倒下了：第二段不結算",
    "followup_no_target": "  第二段沒有合法的目標：第二段不結算",
    "followup_not_triggered": "  沒有達成條件（擊殺或命中）：第二段不結算",
    "followup_declined": "  放棄了第二段",
}


@_handles(EffectFizzled)
def _effect_fizzled(e: EffectFizzled, _v: _View) -> str | None:
    return _FIZZLE_TEXT.get(e.reason)  # 其他原因（沒有對象、沒有增益……）不顯示


@_handles(UnitDashed)
def _unit_dashed(e: UnitDashed, v: _View) -> str:
    route = "→".join(xy_text(p) for p in e.path)
    if len(e.path) == 1:
        return f"  ➤ {v.name[e.unit_id]} 衝向 {v.name[e.target_id]}（已在身旁）"
    return f"  ➤ {v.name[e.unit_id]} 衝向 {v.name[e.target_id]}：{route}"


@_handles(UnitCharged)
def _unit_charged(e: UnitCharged, v: _View) -> str:
    route = "→".join(xy_text(p) for p in e.path)
    blocked = "" if e.path[-1] == e.target else f"（被擋住，停在 {xy_text(e.path[-1])}）"
    return f"  ➤ {v.name[e.unit_id]} 直線衝撞：{route}{blocked}"


@_handles(UnitStoodUp)
def _stood_up(e: UnitStoodUp, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 站了起來（消耗 {e.cost} 移動）"


@_handles(UnitRan)
def _ran(e: UnitRan, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 跑步（本回合移動 +{e.bonus}，剩餘 {e.move_points}）"


@_handles(UnitVaulted)
def _vaulted(e: UnitVaulted, v: _View) -> str:
    verb = "攀爬到" if e.kind == "climb" else "跳到"
    return f"  {v.name[e.unit_id]} {verb} {xy_text(e.to_pos)}"


@_handles(GuardSet)
def _guard_set(e: GuardSet, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 守護 {v.name[e.ally_id]}（到下回合開始）"


@_handles(UnitAimed)
def _aimed(e: UnitAimed, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 瞄準（下一次攻擊命中 +{e.bonus}）"


@_handles(WeaponReloaded)
def _reloaded(e: WeaponReloaded, v: _View) -> str:
    return f"  {v.name[e.unit_id]} 裝填（花 {e.cost} AP，彈匣 {e.ammo} 發）"


@_handles(MoveBlocked)
def _move_blocked(e: MoveBlocked, v: _View) -> str | None:
    if e.forced:
        return None  # 被推擊擋下：以接著的「撞上了…」為主（Phase 3C-6a）
    return f"  {v.name[e.unit_id]} 無法移動到 {xy_text(e.to_pos)}"


_OBSTACLE_NAMES = {
    "wall": "撞上了牆壁",
    "edge": "撞上了地圖邊緣",
    "unit": "撞上了",
    "object": "撞上了",
}


@_handles(Collided)
def _collided(e: Collided, v: _View) -> str:
    name = v.name[e.unit_id]
    if e.obstacle == "excess":
        return f"  {name} 被推得太猛，受到衝擊（{e.shortfall} 次撞擊）"
    target = _OBSTACLE_NAMES[e.obstacle]
    if e.other_id is not None:
        target += v.name[e.other_id]
    elif e.object_id is not None:
        target += object_name(v.state, e.object_id)
    return f"  {name} {target}！少走 {e.shortfall} 格，受到 {e.shortfall} 次撞擊"


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


def _bonus_parts(e: AttackRolled) -> list[str]:
    """命中判定的情境加值：高度、修正規則、背刺與潛行偷襲（Phase 3D-8d）。"""
    parts: list[str] = []
    if e.situational:
        parts.append(f"高度 {_signed(e.situational)}")
    if e.modifier_bonus:
        parts.append(f"修正規則 {_signed(e.modifier_bonus)}")
    if e.backstab:
        parts.append(f"背刺 {_signed(e.backstab)}")
    if e.ambush:
        parts.append(f"偷襲 {_signed(e.ambush)}")
    return parts


@_handles(AttackRolled)
def _attack(e: AttackRolled, v: _View) -> str:
    state = v.state
    if e.advantage == "none" or len(e.rolls) == 1:  # 預覽的強制結果只有一顆骰
        dice = f"d20={e.natural}"
    else:
        label = "優勢" if e.advantage == "advantage" else "劣勢"
        dice = f"d20（{label} {e.rolls[0]}、{e.rolls[1]}）={e.natural}"
    parts = [dice, f"修正 {_signed(e.hit_modifier)}", f"熟練 {_signed(e.proficiency)}"]
    parts += _bonus_parts(e)
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
    if e.backstab:
        verb = f"從背後{verb}"
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
    if e.source:
        costs.append(f"源力 {e.source}")
    form = ""
    if e.variant is not None:  # 戰場變奏（Phase 3-25a）：「（型態名）」
        form = f"（{v.state.ruleset.skill_def(e.skill_id).variant(e.variant).name_zh}）"
    return (
        f"  {v.name[e.unit_id]} 施放「{e.name_zh}」{form}（{'，'.join(costs)}）"
        f"→ 影響 {len(e.tiles)} 格"
    )


@_handles(SkillTriggered)
def _skill_triggered(e: SkillTriggered, v: _View) -> str:
    if e.trigger == MODIFIER_ON_HIT:
        target = f"，對象 {v.name[e.other_id]}" if e.other_id is not None else ""
        return (
            f"  ★ {v.name[e.unit_id]} 的修正「{e.name_zh}」命中後效果（深度 {e.trigger_depth}）"
            f"{target}"
        )
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
    elif e.cause in ("explosion", "conduct", "surface", "collision", "topple", "backlash"):
        kind = f"{cause}{element}"
    mod = ""
    if e.element_mod_ppm != _PPM:
        mod = f"（元素修正 ×{e.element_mod_ppm / _PPM:g}）"
    if e.weather_permille != _PERMILLE:
        mod += f"（天氣 ×{e.weather_permille / _PERMILLE:g}）"
    rest = e.multiplier_permille * _PERMILLE // e.pierce_permille  # 扣掉穿透折扣後的格擋／加成
    if rest != _PERMILLE:
        mod += f"（格擋/加成 ×{rest / _PERMILLE:g}）"
    if e.pierce_permille != _PERMILLE:
        mod += f"（穿透後方 ×{e.pierce_permille / _PERMILLE:g}）"
    if e.status_ppm != _PPM:
        mod += f"（狀態 ×{e.status_ppm / _PPM:g}）"
    shield = f"（護盾吸收 {e.absorbed}）" if e.absorbed else ""
    linked = f"（{e.redirected} 點轉給連結者）" if e.redirected else ""
    burst = f"（爆骰 ×{e.exploded}）" if e.exploded else ""
    return (
        f"    {v.name[e.target_id]} 受到 {e.amount} 點{kind}傷害{_rolls_text(e.rolls)}{burst}"
        f"{mod}{shield}{linked}，HP {e.hp_before} → {e.hp_after}"
    )


@_handles(Healed)
def _healed(e: Healed, v: _View) -> str:
    half = (
        f"（治療 ×{e.received_permille / _PERMILLE:g}）" if e.received_permille != _PERMILLE else ""
    )
    steal = "（吸血）" if e.cause == "lifesteal" else ""
    name, hp = v.name[e.target_id], f"HP {e.hp_before} → {e.hp_after}"
    return f"    {name} 回復 {e.amount} HP{steal}{half}，{hp}"


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
    verb = {"gained": "累積", "consumed": "消耗", "expired": "過期清空", "overload": "超載清空"}[
        e.reason
    ]
    return f"    {v.name[e.unit_id]} 的「{stack}」{verb}：{e.before} → {e.after} 層"


# ---------------------------------------------------------------------------
# 源力與改寫規則型原語（Phase 3C-4a）
# ---------------------------------------------------------------------------


@_handles(SourceChanged)
def _source_changed(e: SourceChanged, v: _View) -> str | None:
    name = v.name[e.unit_id]
    change = f"源力 {e.before} → {e.after}"
    if e.reason == "skill":
        return f"    ✦ {name} 花費源力：{change}"
    if e.reason == "well":
        where = "" if e.pos is None else f" {xy_text(e.pos)}"
        full = "（已達上限）" if e.after == e.before else ""
        return f"  ✦ {name} 汲取了源泉{where}：{change}{full}，源泉消失了"
    other = "精英" if e.other_id is None else v.name[e.other_id]
    return f"  ✦ {name} 擊倒了 {other}，獲得源力：{change}"


@_handles(ApGranted)
def _ap_granted(e: ApGranted, v: _View) -> str:
    target = v.name[e.unit_id]
    if e.deferred:
        return f"    {target} 獲得 {e.amount} AP（下次回合開始時加上，共 {e.ap_after}）"
    return f"    {target} 獲得 {e.amount} AP（現在 {e.ap_after} AP）"


@_handles(ApRefunded)
def _ap_refunded(e: ApRefunded, v: _View) -> str:
    return f"    {v.name[e.unit_id]} 返還了 {e.amount} AP（擊殺時效果，現在 {e.ap_after} AP）"


@_handles(UnitRevived)
def _unit_revived(e: UnitRevived, v: _View) -> str:
    moved = "" if e.pos == e.from_pos else f"（原位置被占用，改站在 {xy_text(e.pos)}）"
    return (
        f"  ✚ {v.name[e.source_id]} 讓 {v.name[e.unit_id]} 重新站了起來"
        f"（HP {e.hp}，位置 {xy_text(e.pos)}）{moved}"
    )


@_handles(BombTicked)
def _bomb_ticked(e: BombTicked, v: _View) -> str:
    return f"  ◷ {v.name[e.unit_id]} 身上的定時炸彈還剩 {e.remaining} 輪（爆炸半徑 {e.radius} 格）"


@_handles(BombExploded)
def _bomb_exploded(e: BombExploded, v: _View) -> str:
    why = "倒數歸零" if e.cause == "timer" else f"{v.name[e.unit_id]} 倒下了"
    return (
        f"  ＊ 定時炸彈在 {xy_text(e.pos)} 爆炸了！（{why}，半徑 {e.radius} 格，"
        f"{e.element.display_name}）"
    )


@_handles(DamageRedirected)
def _damage_redirected(e: DamageRedirected, v: _View) -> str:
    return (
        f"    ✦ {v.name[e.to_id]} 分擔了 {v.name[e.from_id]} 的 {e.amount} 點傷害"
        f"（{v.statuses[e.status_id]}），HP {e.hp_before} → {e.hp_after}"
    )


@_handles(ReactionsGranted)
def _reactions_granted(e: ReactionsGranted, v: _View) -> str:
    return f"    {v.name[e.unit_id]} 本輪的反應次數 +{e.amount}（額外共 {e.total} 次）"


@_handles(ResourceRestored)
def _resource_restored(e: ResourceRestored, v: _View) -> str:
    who = v.name[e.unit_id]
    if e.resource == "mana":
        return f"    {who} 回復了 {e.amount} 點法力（現在 {e.mana_after}）"
    names = "、".join(f"「{v.state.ruleset.skill_def(s).name_zh}」" for s in e.skill_ids)
    return f"    {who} 的 {names} 冷卻 −{e.amount}"


@_handles(SkillCopied)
def _skill_copied(e: SkillCopied, v: _View) -> str:
    return (
        f"  ✦ {v.name[e.unit_id]} 複製了 {v.name[e.source_id]} 的「{e.name_zh}」"
        f"（不扣法力與 AP、不進冷卻）→ 影響 {len(e.tiles)} 格"
    )


_FOLLOWUP_LEAD = {
    "after_gather": "以聚集點",
    "on_kill": "擊倒目標後，在",
    "on_hit": "命中後，在",
    "delayed": "釋放蓄力，以",
}
"""複合技能第二段的開頭（Phase 3F-4a）；其他種類為「在」。"""


@_handles(SkillFollowup)
def _skill_followup(e: SkillFollowup, v: _View) -> str:
    lead = _FOLLOWUP_LEAD.get(e.when, "在")
    centered = e.when in ("after_gather", "delayed")
    where = f"{xy_text(e.origin)} 為中心" if centered else xy_text(e.origin)
    return (
        f"  ✦ {v.name[e.unit_id]} {lead} {where} 接著施展「{e.name_zh}」的第二段"
        f"→ 影響 {len(e.tiles)} 格"
    )


_RELEASE_TEXT = {"next_turn": "下回合開始時釋放", "attacked": "下回合開始前被敵人攻擊就釋放"}
"""延遲段的釋放時機（Phase 3F-4b）。"""
_CANCEL_TEXT = {
    "downed": "倒下了",
    "controlled": "被控制（暈眩或冰凍）",
    "expired": "到下回合開始都沒被攻擊",
    "replaced": "改為蓄力另一招",
}


@_handles(FollowupCharged)
def _followup_charged(e: FollowupCharged, v: _View) -> str:
    release = _RELEASE_TEXT.get(e.release, e.release)
    return (
        f"  ◷ {v.name[e.unit_id]} 開始蓄力「{e.name_zh}」：{release}"
        f"（以自己為中心，目前預計影響 {len(e.tiles)} 格）"
    )


@_handles(FollowupCancelled)
def _followup_cancelled(e: FollowupCancelled, v: _View) -> str:
    return f"  ✕ {v.name[e.unit_id]} 的蓄力「{e.name_zh}」取消了（{_CANCEL_TEXT[e.reason]}）"


@_handles(SkillActivated)
def _skill_activated(e: SkillActivated, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    when = (
        "本場剩餘時間有效"
        if e.expires_round is None
        else f"持續到第 {e.expires_round} 輪 {v.name[e.unit_id]} 的回合開始"
    )
    return f"  ✦ {v.name[e.unit_id]} 啟動了傳說「{skill}」（{when}）"


@_handles(SkillGranted)
def _skill_granted(e: SkillGranted, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    who = v.name[e.unit_id]
    if e.refreshed:
        return f"  ✦ {who} 的暫時技能「{skill}」刷新為 {e.duration} 輪"
    return f"  ✦ {who} 暫時獲得技能「{skill}」（{e.duration} 輪，在 {who} 的回合結束時倒數）"


@_handles(SkillGrantExpired)
def _skill_grant_expired(e: SkillGrantExpired, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    return f"  {v.name[e.unit_id]} 暫時獲得的技能「{skill}」期滿消失了"


@_handles(GambleRolled)
def _gamble_rolled(e: GambleRolled, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    result = "成功" if e.success else "失敗"
    return (
        f"  ✦ {v.name[e.unit_id]} 賭上了「{skill}」：d1000={e.roll}"
        f"（成功率 {e.chance_permille / 10:g}%，要 ≤ {e.chance_permille}）→ {result}"
    )


@_handles(BacklashTriggered)
def _backlash_triggered(e: BacklashTriggered, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    return f"  ✦ {v.name[e.unit_id]} 的「{skill}」失手了，遭到反噬"


@_handles(GearHpLost)
def _gear_hp_lost(e: GearHpLost, v: _View) -> str:
    return f"  ✦ {v.name[e.unit_id]} 的裝備代價：失去 {e.amount} HP（{e.hp_before} → {e.hp_after}）"


_ATTACK_TRIGGER_ZH = {
    "attack_rune": "普攻符文",
    "attack_combo": "普攻連擊",
    "attack_cleave": "普攻分裂",
}
"""普攻類詞條（3-31 符文、3-32a 連擊與分裂）的 ``gear_triggered.trigger``：不是
``skill_triggers.yaml`` 的觸發時機，所以另外列名稱。"""


@_handles(GearTriggered)
def _gear_triggered(e: GearTriggered, v: _View) -> str:
    timing = _ATTACK_TRIGGER_ZH.get(e.trigger) or v.state.ruleset.trigger_def(e.trigger).name_zh
    target = f"，對象 {v.name[e.other_id]}" if e.other_id is not None else ""
    return (
        f"  ★ {v.name[e.unit_id]} 的裝備「{e.name_zh}」（{timing}）觸發"
        f"（深度 {e.trigger_depth}）{target}"
    )


@_handles(ChargeActivated)
def _charge_activated(e: ChargeActivated, v: _View) -> str:
    stack = v.state.ruleset.stack_def(e.stack_id).name_zh
    target = f"，對象 {v.name[e.target_id]}" if e.target_id is not None else ""
    return (
        f"  ⚡ {v.name[e.unit_id]} 啟動裝備「{e.name_zh}」"
        f"（花 {e.stacks_spent} 層{stack}、{e.ap_spent} AP）{target}"
    )


@_handles(OverloadTriggered)
def _overload_triggered(e: OverloadTriggered, v: _View) -> str:
    stack = v.state.ruleset.stack_def(e.stack_id).name_zh
    return (
        f"  ✦ {v.name[e.unit_id]} 的「{stack}」累積到 {e.stacks} 層（門檻 {e.threshold}），超載了！"
    )


@_handles(ActivationExpired)
def _activation_expired(e: ActivationExpired, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    return f"  {v.name[e.unit_id]} 的傳說「{skill}」時間到了，不再生效"


@_handles(RuleChangeTriggered)
def _rule_change_triggered(e: RuleChangeTriggered, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    who = v.name[e.unit_id]
    if e.kind == "element_heals_allies":
        return f"    ✦ {who} 的「{skill}」：{e.amount} 點傷害改為治療 {v.name[e.other_id or '']}"
    if e.kind == "push_any_object":
        obj = v.state.objects.get(e.object_id) if e.object_id is not None else None
        name = "物件" if obj is None else v.state.ruleset.object_def(obj.kind).name_zh
        return f"    ✦ {who} 的「{skill}」：推動了本來推不動的{name}"
    if e.kind == "pass_through_apply":
        return f"    ✦ {who} 的「{skill}」：掠過 {v.name[e.other_id or '']} 身邊"
    return f"  ✦ {who} 的「{skill}」：倒下的地方留下了分身"


@_handles(DeathCheated)
def _death_cheated(e: DeathCheated, v: _View) -> str:
    return f"  ✦ {v.name[e.unit_id]} 的「{v.statuses[e.status_id]}」擋下了致命傷害，HP 留在 1"


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


@_handles(TrapRevealed)
def _trap_revealed(e: TrapRevealed, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    return f"  {v.name[e.unit_id]} 揭露了 {xy_text(e.pos)} 的敵方陷阱「{skill}」"


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
    verb = "撥到" if e.how == "shove_aside" else "推到"
    return f"  {object_name(v.state, e.object_id)} 被{verb} {xy_text(e.to_pos)}"


_DIRECTION_NAMES = {(0, -1): "北", (1, 0): "東", (0, 1): "南", (-1, 0): "西"}


@_handles(ObjectHurled)
def _object_hurled(e: ObjectHurled, v: _View) -> str:
    who = "" if e.source_id is None else f"{v.name[e.source_id]} "
    name = v.state.ruleset.object_def(e.kind).name_zh
    text = f"  ✦ {who}把{name} {xy_text(e.from_pos)} 丟向 {xy_text(e.to_pos)}"
    if e.outcome == "placed" and e.placed_pos is not None:
        if e.placed_pos != e.to_pos:
            return f"{text}，彈落到 {xy_text(e.placed_pos)}"
        return f"{text}，落在那裡"
    if e.outcome == "lost":
        return f"{text}，找不到落腳處"
    return text


@_handles(ObjectToppled)
def _object_toppled(e: ObjectToppled, v: _View) -> str:
    name = v.state.ruleset.object_def(e.kind).name_zh
    way = _DIRECTION_NAMES.get(e.direction, "")
    tiles = "、".join(xy_text(p) for p in e.tiles) or "沒有壓到任何格子"
    crushed = "、".join(v.name[u] for u in e.units)
    who = "" if e.source_id is None else f"{v.name[e.source_id]} 推倒了"
    text = f"  ✦ {who}{name} {xy_text(e.pos)}，往{way}倒下，壓住 {tiles}"
    return f"{text}（壓到 {crushed}）" if crushed else text


@_handles(ShotPierced)
def _shot_pierced(e: ShotPierced, v: _View) -> str:
    objects = "、".join(
        f"{object_name(v.state, oid)} {xy_text(p)}"
        for oid, p in zip(e.objects, e.object_tiles, strict=True)
    )
    text = f"  ➤ 「{v.state.ruleset.skill_def(e.skill_id).name_zh}」穿過了 {objects}"
    if e.behind:
        names = "、".join(v.name[u] for u in e.behind)
        text += f"，後方 {names} 只受 {e.behind_permille // 10}% 傷害"
    return text


@_handles(ObjectCreated)
def _object_created(e: ObjectCreated, v: _View) -> str:
    return f"  {xy_text(e.pos)} 出現了{v.state.ruleset.object_def(e.kind).name_zh}"


@_handles(ObjectExpired)
def _object_expired(e: ObjectExpired, v: _View) -> str:
    return f"  {v.state.ruleset.object_def(e.kind).name_zh} {xy_text(e.pos)} 消失了"


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


@_handles(UnitSummoned)
def _unit_summoned(e: UnitSummoned, v: _View) -> str:
    owner = v.name.get(e.owner_id, e.owner_id)
    summon = v.name.get(e.unit_id, e.unit_id)
    if e.orphan:  # 規則改變「殘影」的分身（Phase 3D-6）：召喚者已倒下
        return (
            f"  {owner} 的原地留下了 {summon}（{xy_text(e.pos)}，接替 {owner} 的行動順序，"
            f"第 {e.expires_round} 輪的環境回合消失）"
        )
    return (
        f"  {owner} 召喚了 {summon}，出現在 {xy_text(e.pos)}"
        f"（緊接在 {owner} 之後行動，第 {e.expires_round} 輪 {owner} 的回合結束時消失）"
    )


_SUMMON_MODE_TEXT = {"focus": "集火", "guard": "守護我", "follow": "跟隨", "hold": "待命"}


@_handles(SummonModeSet)
def _summon_mode_set(e: SummonModeSet, v: _View) -> str:
    summon = v.name.get(e.unit_id, e.unit_id)
    mode = _SUMMON_MODE_TEXT[e.mode]
    if e.reason == "target_gone":
        gone = v.name.get(e.target_id, e.target_id) if e.target_id is not None else "目標"
        return f"  集火目標 {gone} 離場：{summon} 退回{mode}"
    target = "" if e.target_id is None else f" → {v.name.get(e.target_id, e.target_id)}"
    return f"  {summon} 切換為{mode}{target}"


@_handles(SummonCommanded)
def _summon_commanded(e: SummonCommanded, v: _View) -> str:
    owner = v.name.get(e.owner_id, e.owner_id)
    summon = v.name.get(e.unit_id, e.unit_id)
    parts = []
    if e.dest is not None:
        parts.append(f"移動到 {xy_text(e.dest)}")
    if e.target_id is not None:
        parts.append(f"攻擊 {v.name.get(e.target_id, e.target_id)}")
    return f"  {owner} 指揮 {summon}：{'、'.join(parts)}"


@_handles(SkillInfused)
def _skill_infused(e: SkillInfused, v: _View) -> str:
    costs = [f"AP {e.ap}"]
    if e.mana:
        costs.append(f"法力 {e.mana}")
    if e.hp_spent:
        costs.append(f"HP {e.hp_spent}")
    if e.cooldown:
        costs.append(f"冷卻 {e.cooldown} 回合")
    owner = v.name.get(e.owner_id, e.owner_id)
    summon = v.name.get(e.unit_id, e.unit_id)
    return f"  {owner} 把「{e.name_zh}」灌注給 {summon}（{'，'.join(costs)}；下回合開始時施放）"


@_handles(InfusedSkillCast)
def _infused_skill_cast(e: InfusedSkillCast, v: _View) -> str:
    summon = v.name.get(e.unit_id, e.unit_id)
    target = ""
    if e.target_id is not None:
        target = f" → {v.name.get(e.target_id, e.target_id)}"
    elif e.target_pos is not None:
        target = f" → {xy_text(e.target_pos)}"
    return (
        f"  {summon} 施放灌注的「{e.name_zh}」{target}（從 {xy_text(e.origin)}）"
        f"→ 影響 {len(e.tiles)} 格"
    )


_INFUSION_FIZZLE_TEXT = {
    "no_target": "選不到目標",
    "controlled": "無法行動",
    "downed": "被打倒了",
    "gone": "消失了",
}


@_handles(InfusionFizzled)
def _infusion_fizzled(e: InfusionFizzled, v: _View) -> str:
    summon = v.name.get(e.unit_id, e.unit_id)
    if e.reason in ("downed", "gone"):  # 施放前就離場（3-33e2b）
        why = _INFUSION_FIZZLE_TEXT[e.reason]
        return f"  {summon}的灌注技能失效：{summon}{why}，「{e.name_zh}」沒有施放（法力與冷卻不退）"
    why = _INFUSION_FIZZLE_TEXT[e.reason]
    return f"  {summon} {why}，灌注的「{e.name_zh}」失效（法力與冷卻不退）"


@_handles(SnareTriggered)
def _snare_triggered(e: SnareTriggered, v: _View) -> str:
    vine = v.name.get(e.unit_id, e.unit_id)
    target = v.name.get(e.target_id, e.target_id)
    status = v.statuses.get(e.status_id, e.status_id)
    extra = "並絆倒" if e.prone else ""
    return f"  {vine} 纏住了 {target}（{status}{extra}）"


@_handles(SummonPulled)
def _summon_pulled(e: SummonPulled, v: _View) -> str:
    totem = v.name.get(e.unit_id, e.unit_id)
    target = v.name.get(e.target_id, e.target_id)
    return f"  {totem} 把 {target} 從 {xy_text(e.from_pos)} 拉近了 1 格"


_SUMMON_EXPIRY_TEXT = {
    "expired": "時間到了",
    "owner_gone": "召喚者離場",
    "limit": "超過同時存在的上限，最舊的召喚物",
    "sacrificed": "被獻祭",
    "detonated": "自爆了",
    "toppled": "被推倒了",
}


@_handles(SummonExpired)
def _summon_expired(e: SummonExpired, v: _View) -> str:
    why = _SUMMON_EXPIRY_TEXT[e.reason]
    return f"  {why}：{v.name.get(e.unit_id, e.unit_id)} 消失了"


_DETONATE_TEXT = {"arrived": "走到敵人身旁", "adjacent": "身旁有敵人", "downed": "被打倒"}


@_handles(SummonDetonated)
def _summon_detonated(e: SummonDetonated, v: _View) -> str:
    name = v.name.get(e.unit_id, e.unit_id)
    hit = "、".join(v.name.get(t, t) for t in e.targets) or "沒有波及任何人"
    return f"  {name} {_DETONATE_TEXT[e.reason]}，轟然自爆（{e.radius} 格內）：{hit}"


@_handles(WallToppled)
def _wall_toppled(e: WallToppled, v: _View) -> str:
    name = v.name.get(e.unit_id, e.unit_id)
    way = _DIRECTION_NAMES.get(e.direction, "")
    hit = "、".join(v.name[u] for u in e.units)
    text = f"  ✦ {name} 往{way}倒下"
    return f"{text}（壓到 {hit}）" if hit else text


@_handles(TotemPulsed)
def _totem_pulsed(e: TotemPulsed, v: _View) -> str:
    names = "、".join(v.name.get(t, t) for t in e.targets)
    status = v.statuses[e.status_id]
    totem = v.name.get(e.unit_id, e.unit_id)
    return f"  {totem} 散發光環（{e.radius} 格內）：{names} 獲得「{status}」"


DIRECTION_TEXT = {"north": "北", "east": "東", "south": "南", "west": "西"}
"""方向的中文（持續區域的紀錄與預告，Phase 3D-5）。"""


def cells_text(cells: tuple[Pos, ...], limit: int = 4) -> str:
    """格子清單的短文字：最多列 ``limit`` 格，其餘以「等 N 格」帶過。"""
    shown = "、".join(xy_text(p) for p in cells[:limit])
    return shown if len(cells) <= limit else f"{shown} 等 {len(cells)} 格"


def zone_anchor_text(anchor: str, direction: str | None, speed: int) -> str:
    """區域錨點的說明（紀錄、技能說明與網頁共用的字句）。"""
    if anchor == "caster":
        return "跟著施放者移動"
    if anchor == "moving" and direction is not None:
        return f"每次環境回合向{DIRECTION_TEXT[direction]}前進 {speed} 格"
    return "固定不動"


@_handles(ZoneCreated)
def _zone_created(e: ZoneCreated, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    owner = v.name.get(e.owner_id, e.owner_id)
    where = cells_text(e.cells)
    anchor = zone_anchor_text(e.anchor, e.direction, e.speed)
    return (
        f"    {owner} 展開持續區域「{skill}」：{where}（{anchor}，"
        f"第 {e.expires_round} 輪 {owner} 的回合結束時消失）"
    )


@_handles(ZoneMoved)
def _zone_moved(e: ZoneMoved, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    direction = DIRECTION_TEXT.get(e.direction, e.direction)
    return f"  「{skill}」區域向{direction}前進：{cells_text(e.cells)}"


@_handles(ZoneTriggered)
def _zone_triggered(e: ZoneTriggered, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    unit = v.name.get(e.unit_id, e.unit_id)
    if e.cause == "enter":
        return f"  ◇ {unit} 進入「{skill}」區域（深度 {e.trigger_depth}）"
    return f"  ◇ {unit} 在「{skill}」區域內開始回合（深度 {e.trigger_depth}）"


_ZONE_EXPIRY_TEXT = {
    "timeout": "時間到了",
    "owner_gone": "施放者離場",
    "limit": "超過同時存在的上限，最舊的區域",
    "blocked": "前方都是牆壁或地圖邊緣",
}


@_handles(ZoneExpired)
def _zone_expired(e: ZoneExpired, v: _View) -> str:
    skill = v.state.ruleset.skill_def(e.skill_id).name_zh
    owner = v.name.get(e.owner_id, e.owner_id)
    return f"  {_ZONE_EXPIRY_TEXT[e.reason]}：{owner} 的「{skill}」區域消失了"


@_handles(RuneInscribed)
def _rune_inscribed(e: RuneInscribed, v: _View) -> str:
    owner = v.name.get(e.owner_id, e.owner_id)
    return (
        f"  {owner} 在 {xy_text(e.pos)} 刻下{rune_name(e.element, e.tag)}"
        f"（剩 {e.remaining} 輪；只有 {owner} 讀得到）"
    )


_RUNE_REMOVAL_TEXT = {
    "expired": "時效到了，消失了",
    "limit": "超過同時存在的上限，最舊的符文消失了",
    "detonated": "被引爆了",
    "replaced": "被新刻下的符文取代了",
}


@_handles(RuneRemoved)
def _rune_removed(e: RuneRemoved, v: _View) -> str:
    owner = v.name.get(e.owner_id, e.owner_id)
    name = rune_name(e.element, e.tag)
    return f"  {owner} 的{name}（{xy_text(e.pos)}）{_RUNE_REMOVAL_TEXT[e.reason]}"


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
    kind = {
        "shove": "推擊",
        "trip": "絆倒",
        "knock_prone": "擊倒",
        "teleport": "傳送",
        "swap": "交換位置",
    }[e.maneuver]
    verdict = "成功" if e.success else "失敗"
    resist = f" 抵抗 {_signed(-e.resist_bonus)}" if e.resist_bonus else ""
    return (
        f"  {v.name[e.attacker_id]} 對 {v.name[e.target_id]} 使出{kind}：d20={e.natural} "
        f"修正 {_signed(e.modifier)} 熟練 {_signed(e.proficiency)}{resist} = {e.total}"
        f"（目標 {e.target_number}）→ {verdict}"
    )


@_handles(PushResisted)
def _push_resisted(e: PushResisted, v: _View) -> str:
    if e.reason == "immovable":
        return f"  {v.name[e.unit_id]} 紋風不動：不會被推動、拉扯或傳送"
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


_MODE_TEXT = {"auto": "自動", "prompt": "每次詢問", "off": "關閉"}


@_handles(ReactionModeSet)
def _reaction_mode_set(e: ReactionModeSet, v: _View) -> str:
    name = reaction_name(v.state, e.reaction)
    return f"{v.name[e.unit_id]} 將反應 {name} 設為{_MODE_TEXT[e.mode]}"


@_handles(AttackIntercepted)
def _intercepted(e: AttackIntercepted, v: _View) -> str:
    name = v.name
    skill = "" if e.skill_id is None else f"「{v.state.ruleset.skill_def(e.skill_id).name_zh}」"
    if e.guard:
        return (
            f"  🛡 {name[e.guardian_id]} 守護 {name[e.target_id]}：{name[e.attacker_id]} 的"
            f"攻擊{skill}改由 {name[e.guardian_id]} 承受"
        )
    return (
        f"  🛡 {name[e.guardian_id]} 攔截了 {name[e.attacker_id]} 對 {name[e.target_id]} 的"
        f"攻擊{skill}——改由 {name[e.guardian_id]} 承受"
    )
