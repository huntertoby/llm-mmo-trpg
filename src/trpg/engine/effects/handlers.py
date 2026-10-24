"""單位效果的處理器：damage、heal、move_unit、apply_status、remove_status，以及共用的
「抵達一格」邏輯 :func:`arrive`（墜落、致命地形、表面、撤離）。"""

from __future__ import annotations

from trpg.content.rule_changes import ELEMENT_HEALS_ALLIES
from trpg.engine.activations import active_rule_change
from trpg.engine.context import Ctx
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CleanseEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    MoveUnitEffect,
    RemoveStatusEffect,
    ShieldEffect,
    SwapUnitsEffect,
)
from trpg.engine.effects.queue import register_effect
from trpg.engine.events import (
    CheckRolled,
    DamageDealt,
    DamageRedirected,
    DeathCheated,
    EffectFizzled,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    MoveBlocked,
    MoveMode,
    RuleChangeTriggered,
    ShieldAbsorbed,
    ShieldGained,
    StatusApplied,
    StatusConverted,
    StatusRemoved,
    SurfaceEntered,
    UnitFell,
    UnitMoved,
)
from trpg.engine.ids import BOSS_TAG, CONCEALED, IMMOVABLE, SHIELDED
from trpg.engine.lifecycle import down_unit, escape_unit
from trpg.engine.rules.combat import PERMILLE, PPM, element_modifier_ppm
from trpg.engine.rules.facing import facing_between
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.movement import is_deadly, is_flying, is_standable
from trpg.engine.rules.statuses import (
    boss_converted_status,
    damage_dealt_permille,
    damage_taken_permille,
    effective_attribute,
    healing_received_permille,
    prevents_concealment,
    shield_amount,
    stance_status_ids,
)
from trpg.engine.source import credit_elite_kill, take_source_well
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.engine.traps import detect_traps, queue_trap_entry
from trpg.engine.zones import note_unit_moved
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

__all__ = ["ability_modifier", "apply_status", "arrive", "enter_surface", "weather_permille"]


def weather_permille(state: BattleState, element: Element) -> int:
    """天氣對 ``element`` 傷害的倍率（‰），例如下雨時火焰 700、雷電 1200。"""
    weather = state.weather
    if weather is None:
        return PERMILLE
    return PERMILLE + weather.element_damage_permille.get(element, 0)


def ability_modifier(ctx: Ctx, value: int) -> int:
    """檢定的屬性修正：``(屬性 − ability_mod_base) // ability_mod_divisor``。"""
    return (value - ctx.core.ability_mod_base) // ctx.core.ability_mod_divisor


@register_effect("damage")
def _damage(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, DamageEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    rolls: tuple[int, ...] = ()
    exploded = 0
    mod_ppm = PPM
    weather = PERMILLE
    multiplier = effect.multiplier_permille
    base_amount: int | None = None
    status_ppm = PPM
    absorbed = 0
    events: list[EventBase] = []
    if effect.mode == "lethal":
        amount = unit.hp
    elif effect.mode == "percent_max_hp":
        amount = max(unit.max_hp * effect.permille // PERMILLE, effect.min_damage)
    else:
        rolls, exploded = _damage_rolls(ctx, effect)
        raw_permille = (sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille
        if effect.apply_element_mod:
            mod_ppm = element_modifier_ppm(unit, effect.element, ctx.rules)
        if effect.apply_weather:
            weather = weather_permille(ctx.state, effect.element)
        dealt = _dealt_permille(ctx, effect)  # 虛弱
        status_ppm = dealt * damage_taken_permille(
            ctx.rules, unit, effect.element
        )  # 易傷、石膚；千分比 × 千分比
        multiplier = effect.multiplier_permille * _boss_vs_summon_permille(ctx, unit, effect)
        multiplier //= PERMILLE
        amount = max(
            raw_permille
            * mod_ppm
            * weather
            * multiplier
            * status_ppm
            // (PERMILLE * PPM * PERMILLE * PERMILLE * PPM),
            effect.min_damage,
        )
        base_amount = max(
            raw_permille * weather * dealt // (PERMILLE * PERMILLE * PERMILLE), effect.min_damage
        )
        mended = _mend_ally(ctx, unit, effect, amount)  # 規則改變「慈焰」（Phase 3D-6）
        if mended is not None:
            return mended
        amount = _cap_backlash(ctx, unit, effect, amount)
        absorbed = _absorb(ctx, unit, amount, events)  # 護盾：所有倍率之後、扣 HP 之前
    link = redirect_link(ctx, unit, effect)
    redirected = 0 if link is None else (amount - absorbed) * (link[0].amount or 0) // PERMILLE
    hp_before = unit.hp
    unit.hp = max(0, unit.hp - (amount - absorbed - redirected))
    cheated = _undying_status(ctx, unit, effect)
    if cheated is not None:
        unit.hp = 1
    events += [
        ctx.emit(
            DamageDealt,
            target_id=unit.id,
            source_id=effect.source_id,
            cause=effect.cause,
            element=effect.element,
            rolls=rolls,
            crit=effect.crit,
            element_mod_ppm=mod_ppm,
            amount=amount,
            hp_before=hp_before,
            hp_after=unit.hp,
            pos=unit.pos,
            weather_permille=weather,
            multiplier_permille=multiplier,
            pierce_permille=effect.pierce_permille,
            base_amount=base_amount,
            status_ppm=status_ppm,
            absorbed=absorbed,
            redirected=redirected,
            exploded=exploded,
            block_permille=effect.block_permille,
            flat=effect.flat,
            scaled_permille=effect.scaled_permille,
            scale_attr=effect.scale_attr,
        )
    ]
    events += _redirect(ctx, unit, link, redirected, effect)
    if cheated is not None:
        events += _cheat_death(ctx, unit, cheated, amount - absorbed - redirected - (hp_before - 1))
    if amount > 0:
        events.extend(_thaw(ctx, unit, effect.element))
    if unit.hp <= 0:
        events.extend(down_unit(ctx, unit))
        events.extend(credit_elite_kill(ctx, unit, effect.source_id))
    return events


def _boss_vs_summon_permille(ctx: Ctx, target: UnitState, effect: DamageEffect) -> int:
    """Boss（``boss`` 標籤）對敵方召喚物的傷害倍率（Phase 3-33b，``boss_summon_damage_permille``，
    ×2）；其他來源與目標為 1000。範圍技能、區域與表面等帶 ``source_id`` 的傷害一律適用。"""
    if not target.is_summon or effect.source_id is None:
        return PERMILLE
    source = ctx.state.units.get(effect.source_id)
    if source is None or source.team is target.team or not source.has_tag(BOSS_TAG):
        return PERMILLE
    return ctx.core.boss_summon_damage_permille


def _damage_rolls(ctx: Ctx, effect: DamageEffect) -> tuple[tuple[int, ...], int]:
    """傷害的骰值（與爆骰多擲的顆數）：暴擊時骰數加倍；聖光雙效（Phase 3D-8a）沿用已擲好的骰值，
    暴擊的額外骰子另擲。"""
    if effect.dice is None:
        return (), 0
    count = effect.dice.count * (2 if effect.crit else 1)
    if effect.preset_rolls is None:
        return _roll_damage_dice(ctx, effect.dice.sides, count, effect.explode_max)
    extra = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(count - len(effect.preset_rolls)))
    return effect.preset_rolls + extra, 0


def _roll_damage_dice(
    ctx: Ctx, sides: int, count: int, explode_max: int
) -> tuple[tuple[int, ...], int]:
    """擲 ``count`` 顆傷害骰；爆骰（Phase 3D-7b）：一顆骰擲到最大值就再擲一顆，每顆原本的骰子最多
    再擲 ``explode_max`` 次。回傳（全部擲出的值，依擲骰順序；多擲的顆數）。"""
    rolls: list[int] = []
    extra = 0
    for _ in range(count):
        value = ctx.rng.roll(sides)
        rolls.append(value)
        again = 0
        while sides > 1 and value == sides and again < explode_max:
            value = ctx.rng.roll(sides)
            rolls.append(value)
            again += 1
            extra += 1
    return tuple(rolls), extra


def _cap_backlash(ctx: Ctx, unit: UnitState, effect: DamageEffect, amount: int) -> int:
    """反噬（``cause: backlash``，Phase 3D-7a）不會讓單位的 HP 低於 1：護盾先吸收，超過的部分
    截斷。其他傷害不受影響。"""
    if effect.cause != "backlash":
        return amount
    return min(amount, unit.hp - 1 + shield_amount(ctx.rules, unit))


def _dealt_permille(ctx: Ctx, effect: DamageEffect) -> int:
    """攻擊者造成傷害的狀態倍率（‰，虛弱）；不是攻擊或沒有來源時 1000。"""
    source = None if effect.source_id is None else ctx.state.units.get(effect.source_id)
    if effect.cause == "attack" and source is not None:
        return damage_dealt_permille(ctx.rules, source)
    return PERMILLE


def _mend_ally(
    ctx: Ctx, unit: UnitState, effect: DamageEffect, amount: int
) -> list[EventBase] | None:
    """規則改變 ``element_heals_allies``（Phase 3D-6）：來源單位生效中的規則改變元素與這次傷害相同、
    受傷者是它的友方（不含自己）時，傷害改為治療 ``amount × permille‰``（再套用受到治療的倍率，
    例如中毒）。不扣護盾、不發 ``damage_dealt``。不適用時回傳 ``None``。"""
    if effect.source_id is None or effect.source_id == unit.id:
        return None
    source = ctx.state.units.get(effect.source_id)
    if source is None or source.team is not unit.team:
        return None
    change = active_rule_change(ctx.state, source, ELEMENT_HEALS_ALLIES)
    if change is None or change.rule.element is not effect.element:
        return None
    permille = change.rule.permille or PERMILLE
    received = healing_received_permille(ctx.rules, unit)
    heal = amount * permille * received // (PERMILLE * PERMILLE)
    hp_before = unit.hp
    unit.hp = min(unit.max_hp, unit.hp + heal)
    return [
        ctx.emit(
            RuleChangeTriggered,
            unit_id=source.id,
            skill_id=change.skill.id,
            rule=change.rule.id,
            kind=ELEMENT_HEALS_ALLIES,
            other_id=unit.id,
            amount=amount,
        ),
        ctx.emit(
            Healed,
            target_id=unit.id,
            source_id=source.id,
            rolls=(),
            amount=unit.hp - hp_before,
            hp_before=hp_before,
            hp_after=unit.hp,
            received_permille=received,
        ),
    ]


_UNPREVENTABLE_CAUSES = ("fall", "deadly_terrain")
"""免死（``prevents_death``）擋不下、靈魂連結（``redirects_damage``）也不轉移的傷害：墜落與致命
地形（Phase 3C-4a，保守）。"""


def redirect_link(
    ctx: Ctx, unit: UnitState, effect: DamageEffect
) -> tuple[StatusInstance, UnitState] | None:
    """``unit`` 受到這次傷害時有效的靈魂連結（Phase 3C-4b）：狀態與承受轉移的連結者。連結者必須
    仍在場上、不是 ``unit`` 自己；墜落、致命地形與 ``lethal`` 不轉移。"""
    if effect.mode == "lethal" or effect.cause in _UNPREVENTABLE_CAUSES:
        return None
    for status in unit.statuses:
        if not ctx.rules.status_def(status.status_id).redirects_damage or not status.amount:
            continue
        linked = None if status.source_id is None else ctx.state.units.get(status.source_id)
        if linked is not None and linked.alive and linked.id != unit.id:
            return status, linked
    return None


def _redirect(
    ctx: Ctx,
    unit: UnitState,
    link: tuple[StatusInstance, UnitState] | None,
    amount: int,
    effect: DamageEffect,
) -> list[EventBase]:
    """把 ``amount`` 點傷害轉給連結者：直接扣 HP（不經護盾、抗性與元素修正）；連結者的免死照常
    生效，HP 歸零則倒下（連結者倒下時，連結立即消失）。沒有連結或沒有轉移時什麼都不做。"""
    if link is None or amount <= 0:
        return []
    status, linked = link
    hp_before = linked.hp
    linked.hp = max(0, linked.hp - amount)
    cheated = _undying_status(ctx, linked, effect)
    if cheated is not None:
        linked.hp = 1
    events: list[EventBase] = [
        ctx.emit(
            DamageRedirected,
            from_id=unit.id,
            to_id=linked.id,
            status_id=status.status_id,
            amount=amount,
            hp_before=hp_before,
            hp_after=linked.hp,
        )
    ]
    if cheated is not None:
        events += _cheat_death(ctx, linked, cheated, amount - (hp_before - 1))
    if linked.hp <= 0:
        events.extend(down_unit(ctx, linked))
    return events


def _undying_status(ctx: Ctx, unit: UnitState, effect: DamageEffect) -> str | None:
    """這次傷害讓 HP 降到 0、且身上有擋得下它的免死狀態時，回傳該狀態 ID（依狀態順序取第一個）。"""
    if unit.hp > 0 or effect.mode == "lethal" or effect.cause in _UNPREVENTABLE_CAUSES:
        return None
    for status in unit.statuses:
        if ctx.rules.status_def(status.status_id).prevents_death:
            return status.status_id
    return None


def _cheat_death(ctx: Ctx, unit: UnitState, status_id: str, prevented: int) -> list[EventBase]:
    """免死擋下致命傷害：發出 ``death_cheated``，移除該狀態（原因 ``spent``）。"""
    unit.statuses = [s for s in unit.statuses if s.status_id != status_id]
    return [
        ctx.emit(DeathCheated, unit_id=unit.id, status_id=status_id, prevented=max(prevented, 0)),
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="spent"),
    ]


def _thaw(ctx: Ctx, unit: UnitState, element: Element) -> list[EventBase]:
    """受到 ``removed_by_element`` 含此元素的傷害時，移除對應狀態（冰凍遇火，Phase 2H-1）。"""
    thawed = [
        s.status_id
        for s in unit.statuses
        if element in ctx.rules.status_def(s.status_id).removed_by_element
    ]
    if not thawed:
        return []
    unit.statuses = [s for s in unit.statuses if s.status_id not in thawed]
    return [
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="thawed")
        for status_id in sorted(thawed)
    ]


def _absorb(ctx: Ctx, unit: UnitState, amount: int, events: list[EventBase]) -> int:
    """護盾吸收 ``amount`` 點傷害，回傳吸收的點數；吸收量歸零的護盾狀態立即移除。"""
    absorbed = 0
    kept: list[StatusInstance] = []
    removed: list[str] = []
    for status in unit.statuses:
        if (
            amount - absorbed > 0
            and status.amount is not None
            and ctx.rules.status_def(status.status_id).absorbs_damage
        ):
            take = min(status.amount, amount - absorbed)
            absorbed += take
            left = status.amount - take
            if left > 0:
                kept.append(
                    StatusInstance(status.status_id, status.remaining, status.source_id, left)
                )
            else:
                removed.append(status.status_id)
            if take > 0:
                events.append(
                    ctx.emit(ShieldAbsorbed, unit_id=unit.id, absorbed=take, remaining=left)
                )
            continue
        kept.append(status)
    unit.statuses = kept
    for status_id in removed:
        events.append(
            ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="depleted")
        )
    return absorbed


@register_effect("heal")
def _heal(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, HealEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    rolls: tuple[int, ...] = ()
    if effect.preset_rolls is not None:
        rolls = effect.preset_rolls
    elif effect.dice is not None:
        rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(effect.dice.count))
    received = healing_received_permille(ctx.rules, unit)  # 中毒
    amount = max(
        0,
        ((sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille)
        * received
        * effect.multiplier_permille
        // (PERMILLE * PERMILLE * PERMILLE),
    )
    hp_before = unit.hp
    unit.hp = min(unit.max_hp, unit.hp + amount)
    return [
        ctx.emit(
            Healed,
            target_id=unit.id,
            source_id=effect.source_id,
            rolls=rolls,
            amount=unit.hp - hp_before,
            hp_before=hp_before,
            hp_after=unit.hp,
            received_permille=received,
            cause=effect.cause,
        )
    ]


@register_effect("shield")
def _shield(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ShieldEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    rolls: tuple[int, ...] = ()
    if effect.dice is not None:
        rolls = tuple(ctx.rng.roll(effect.dice.sides) for _ in range(effect.dice.count))
    amount = max(
        0,
        ((sum(rolls) + effect.flat) * PERMILLE + effect.scaled_permille)
        * effect.multiplier_permille
        // (PERMILLE * PERMILLE),
    )
    status_id = SHIELDED
    current = unit.get_status(status_id)
    total = max(amount, 0 if current is None or current.amount is None else current.amount)
    duration = effect.duration or ctx.rules.status_def(status_id).duration
    if current is not None and duration is not None:  # 已有護盾：剩餘回合取較長者
        duration = max(duration, current.remaining or 0)
    instance = StatusInstance(status_id, duration, effect.source_id, total)
    others = [s for s in unit.statuses if s.status_id != status_id]
    unit.statuses = sorted([*others, instance], key=lambda s: s.status_id)
    return [
        ctx.emit(
            ShieldGained,
            unit_id=unit.id,
            source_id=effect.source_id,
            amount=amount,
            total=total,
            rolls=rolls,
        )
    ]


@register_effect("cleanse")
def _cleanse(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, CleanseEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    removable = [
        s.status_id
        for s in unit.statuses
        if ctx.rules.status_def(s.status_id).polarity == "debuff" and not s.cost_status
    ]  # 只移除減益；增益與中性保留（#60）；代價狀態（自己付的）移除不了（#62）
    if not removable:
        return []
    unit.statuses = [s for s in unit.statuses if s.status_id not in removable]
    return [
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=status_id, reason="cleansed")
        for status_id in sorted(removable)
    ]


_ACTIVE_MOVES: frozenset[str] = frozenset({"walk", "dash", "leap"})
"""改變朝向的移動方式（Phase 3D-8d）：步行、衝鋒與直線衝撞的每一步、跳躍。"""


def _face_move(unit: UnitState, start: XY, dest: XY) -> None:
    facing = facing_between(start, dest)
    if facing is not None:
        unit.facing = facing


def arrive(
    ctx: Ctx,
    unit: UnitState,
    dest: tuple[int, int],
    mode: MoveMode,
    cost: int = 0,
    *,
    source_id: UnitId | None = None,
) -> list[EventBase]:
    """把單位移到 ``dest`` 並結算抵達的後果（不檢查合法性與阻擋）。

    - ``source_id``：強制位移的推擊者；墜落與致命地形的傷害帶上這個來源（走進去時為 ``None``）。
    - ``walk``／``forced`` 往下落差達 ``fall_damage_min_drop`` 時墜落（``unit_fell``）。
    - 落入致命地形：``entered_deadly_terrain``（之後由觸發表處理死亡或精英傳送）。
    - 進入有 ``on_enter`` 的表面：``surface_entered``（套用狀態）；有檢定時擲骰
      （``check_rolled``，失敗的狀態由觸發表套用）。
    - 我方單位抵達源泉格：+1 源力，源泉消失（``source_changed``，Phase 3C-4a）。
    - 撤離勝利條件下，我方單位抵達出口格即離開戰場（``unit_escaped``）。
    """
    state = ctx.state
    from_pos = unit.pos
    drop = state.tile(from_pos.x, from_pos.y).height - state.tile(*dest).height
    unit.pos = Pos(x=dest[0], y=dest[1])
    if mode in ("walk", "dash"):
        unit.moved_this_turn = True  # 連段條件 moved_this_turn（Phase 3D-1；衝鋒算，3D-2）
    if mode in _ACTIVE_MOVES:  # 主動移動：面向移動方向（Phase 3D-8d；瞬步由呼叫端面向目標）
        _face_move(unit, (from_pos.x, from_pos.y), dest)
    events: list[EventBase] = [
        ctx.emit(
            UnitMoved, unit_id=unit.id, from_pos=from_pos, to_pos=unit.pos, mode=mode, cost=cost
        )
    ]
    if mode != "teleport":
        queue_trap_entry(ctx, unit, dest)  # 進入敵方陷阱格（主動或強制移動；傳送不算）
    note_unit_moved(ctx, unit, (from_pos.x, from_pos.y), dest)  # 持續區域（Phase 3D-5）
    detect_traps(ctx, unit)  # 感知的常駐數值：自動看見附近的敵方陷阱（Phase 3H-1）
    min_drop = ctx.core.fall_damage_min_drop
    if mode not in ("teleport", "teleported", "shadowstep") and drop >= min_drop:
        levels = drop - (min_drop - 1)
        events.append(
            ctx.emit(UnitFell, unit_id=unit.id, drop=drop, levels=levels, source_id=source_id)
        )
    if is_deadly(state, dest):
        terrain = state.tile(*dest).terrain
        events.append(
            ctx.emit(
                EnteredDeadlyTerrain,
                unit_id=unit.id,
                pos=unit.pos,
                terrain=terrain,
                source_id=source_id,
            )
        )
        return events
    events.extend(take_source_well(ctx, unit))  # 我方進入源泉格（Phase 3C-4a；傳送也算）
    objective = state.objective
    if (
        objective.kind == "escape"
        and unit.team is Team.ALLY
        and not unit.is_summon  # 召喚物不能撤離（Phase 3D-4a）
        and dest in objective.tiles
    ):
        events.extend(escape_unit(ctx, unit))
        return events
    events.extend(enter_surface(ctx, unit))
    return events


def enter_surface(ctx: Ctx, unit: UnitState) -> list[EventBase]:
    """``unit`` 所在格表面的進入效果：``surface_entered``（套用狀態），有檢定時擲骰
    （``check_rolled``）。走進表面、被推進表面，以及表面出現在腳下時都會呼叫。"""
    surface = ctx.state.tile(*unit.xy).surface
    if surface is Surface.NONE or is_flying(unit):  # 會飛的單位不受地面表面影響（3-33e2b）
        return []
    definition = ctx.rules.surface_def(surface)
    if definition.on_enter is None:
        return []
    events: list[EventBase] = [
        ctx.emit(SurfaceEntered, unit_id=unit.id, pos=unit.pos, surface=surface)
    ]
    check = definition.on_enter.check
    if check is not None:
        roll = ctx.check_d20()
        modifier = ability_modifier(ctx, effective_attribute(ctx.rules, unit, check.attr))
        total = roll + modifier
        events.append(
            ctx.emit(
                CheckRolled,
                unit_id=unit.id,
                reason=f"surface:{surface.value}",
                attr=check.attr,
                roll=roll,
                modifier=modifier,
                total=total,
                dc=check.dc,
                success=total >= check.dc,
                fail_status=check.fail_status,
            )
        )
    return events


@register_effect("move_unit")
def _move_unit(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, MoveUnitEffect)
    state = ctx.state
    unit = state.units.get(effect.unit_id)
    if unit is None or not unit.alive:
        return []
    dx, dy = effect.dest
    dest = Pos(x=max(dx, 0), y=max(dy, 0))
    if not state.in_bounds(dx, dy):
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="out_of_bounds")]
    if unit.has_tag(IMMOVABLE) and effect.mode in ("forced", "teleported"):  # 石像（3-33e2a）
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="immovable")]
    occupant = state.unit_at(dx, dy)
    if occupant is not None and occupant.id != unit.id and effect.mode != "walk":
        return [ctx.emit(MoveBlocked, unit_id=unit.id, to_pos=dest, reason="occupied")]
    return arrive(ctx, unit, (dx, dy), effect.mode, effect.cost)


def apply_status(ctx: Ctx, effect: ApplyStatusEffect) -> list[EventBase]:
    """施加狀態（重複施加時刷新持續時間，不疊加）。"""
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.alive:
        return []
    events: list[EventBase] = []
    status_id = effect.status_id
    duration = effect.duration
    if duration is None:
        duration = ctx.rules.status_def(status_id).duration  # 轉換後持續時間沿用原效果
    if status_id == CONCEALED and prevents_concealment(ctx.rules, unit):  # 被揭露：不能再隱蔽
        return [
            ctx.emit(EffectFizzled, effect_kind="apply_status", pos=unit.pos, reason="revealed")
        ]
    converted = status_id if effect.self_paid else boss_converted_status(ctx.rules, unit, status_id)
    if converted != status_id:  # Boss 硬控轉換：所有來源一致（技能路徑已先轉換，這裡不會再轉）
        events.append(
            ctx.emit(
                StatusConverted,
                target_id=unit.id,
                from_status=status_id,
                to_status=converted,
                source_id=effect.source_id,
            )
        )
        status_id = converted
    definition = ctx.rules.status_def(status_id)
    existing = unit.get_status(status_id)
    instance = StatusInstance(
        status_id=status_id,
        remaining=duration,
        source_id=effect.source_id,
        amount=effect.amount,
        skill_id=effect.skill_id,
        dormant=effect.self_paid
        and (definition.skip_turn or definition.blocks_spells)
        and ctx.state.active_unit == unit.id,  # 自暈／自我沉默：本回合照常，回合結束才生效
        cost_status=effect.self_paid,  # 代價狀態：淨化與驅散移除不了（#62）
    )
    if definition.stance:  # 同時只能有一個姿態：先移除其他姿態（2E-2）
        for old in stance_status_ids(ctx.rules, unit):
            if old != status_id:
                unit.statuses = [s for s in unit.statuses if s.status_id != old]
                events.append(
                    ctx.emit(StatusRemoved, target_id=unit.id, status_id=old, reason="replaced")
                )
    if definition.attack_element is not None:  # 同時只能有一個附魔：後施放的覆蓋先施放的（3I-6）
        for other in unit.statuses:
            if (
                other.status_id != status_id
                and ctx.rules.status_def(other.status_id).attack_element is not None
            ):
                unit.statuses = [s for s in unit.statuses if s.status_id != other.status_id]
                events.append(
                    ctx.emit(
                        StatusRemoved,
                        target_id=unit.id,
                        status_id=other.status_id,
                        reason="replaced",
                    )
                )
                break
    # 重複施加：不疊加，剩餘回合取較長者（None＝永久最長），見 docs/design/06-技能.md 6.6
    if (
        existing is not None
        and _outlasts(existing.remaining, duration)
        and not definition.redirects_damage  # 新的連結一律取代舊的（連結者與比例都可能不同）
    ):
        instance = StatusInstance(
            status_id=status_id,
            remaining=existing.remaining,
            source_id=existing.source_id,
            amount=existing.amount,
            skill_id=existing.skill_id,
            cost_status=existing.cost_status,
        )
    others = [s for s in unit.statuses if s.status_id != status_id]
    unit.statuses = sorted([*others, instance], key=lambda s: s.status_id)
    if (
        definition.control_group is not None and not effect.self_paid
    ):  # 控制遞減：同類別在 R + control_dr_rounds 輪結束前
        unit.control_dr[definition.control_group] = ctx.state.round + ctx.core.control_dr_rounds
    events.append(
        ctx.emit(
            StatusApplied,
            target_id=unit.id,
            status_id=status_id,
            duration=instance.remaining,
            refreshed=existing is not None,
            source_id=effect.source_id,
        )
    )
    return events


def _outlasts(old: int | None, new: int | None) -> bool:
    """舊狀態的剩餘回合是否嚴格長於新的持續時間（None＝永久）。"""
    if old is None:
        return new is not None
    return new is not None and old > new


@register_effect("apply_status")
def _apply_status(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, ApplyStatusEffect)
    return apply_status(ctx, effect)


@register_effect("remove_status")
def _remove_status(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    assert isinstance(effect, RemoveStatusEffect)
    unit = ctx.state.units.get(effect.target_id)
    if unit is None or not unit.has_status(effect.status_id):
        return []
    unit.statuses = [s for s in unit.statuses if s.status_id != effect.status_id]
    return [
        ctx.emit(StatusRemoved, target_id=unit.id, status_id=effect.status_id, reason=effect.reason)
    ]


@register_effect("swap_units")
def _swap_units(ctx: Ctx, effect: EffectBase) -> list[EventBase]:
    """交換兩個單位的位置（Phase 3D-2）：兩格都要能讓對方站上去；各自結算抵達的後果。"""
    assert isinstance(effect, SwapUnitsEffect)
    state = ctx.state
    first = state.units.get(effect.unit_id)
    second = state.units.get(effect.other_id)
    if first is None or second is None or not first.alive or not second.alive:
        return []
    a_xy, b_xy = first.xy, second.xy
    if not (is_standable(state, a_xy) and is_standable(state, b_xy)):
        return [ctx.emit(EffectFizzled, effect_kind="swap", pos=None, reason="swap_blocked")]
    events = arrive(ctx, first, b_xy, "swap", source_id=effect.source_id)
    events += arrive(ctx, second, a_xy, "swap", source_id=effect.source_id)
    return events
