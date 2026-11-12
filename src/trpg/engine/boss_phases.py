"""Boss 的階段（Phase 5F-2，``docs/phases/Phase5計畫.md`` 34；09 9.6.8、18.2.3）。

單位的 ``phases``（由範本帶入，第 1 項是開場階段）依觸發條件進入：每次結算收尾
（:func:`trpg.engine.turns.finish_resolution`）檢查，存活的單位符合下一個階段的觸發就進入它——
``hp_below``：HP ≤ ``最大 HP × permille‰``；``tag_down``（Phase 5F-3）：同陣營帶 ``tag`` 的單位
已倒下 ``count`` 名以上（賽季 Boss 的源晶柱）；``round_at``（5F-3）：目前輪數 ≥ ``round``。
一次符合多個時依序進入每一個。``phase_index`` 只增不減，
所以每個階段整場只觸發一次（被治療回門檻以上也不退回、不再觸發）。預覽（AI 估值）不檢查。

進入一個階段的順序：``boss_phase_changed`` → 移除狀態 → 換技能組（冷卻只保留新技能組裡的技能）→
換行為模式 → 回復法力（``mana_restore``，BAL-21a；預設不回復，有回復才發
``resource_restored``）→ 施加狀態（不擲抵抗，同開場狀態）→ 改天氣（``weather_changed``，相同時
不發）→ 改格子
（``ChangeTileEffect``，地圖外的略過）→ 召喚（``SpawnUnitEffect``，和 Boss 同陣營；``at`` 省略時以
Boss 當下的位置為目的地，由效果改到最近的安全格）。正在蓄力的強招不受影響（蓄力記在狀態上）。

不取用亂數；多個 Boss 依單位 ID 順序。
"""

from __future__ import annotations

from trpg.content.battle import BossPhase, HpBelowTrigger, RoundTrigger, TagDownTrigger
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    ChangeTileEffect,
    EffectBase,
    RemoveStatusEffect,
    SpawnUnitEffect,
)
from trpg.engine.events import BossPhaseChanged, ResourceRestored, WeatherChanged
from trpg.engine.state import BattleState, UnitState

__all__ = ["CLEAR_WEATHER", "check_boss_phases", "next_phase"]

CLEAR_WEATHER = "clear"
"""晴朗的天氣 ID（設定的 ``weather`` 為 ``None`` 時等同晴朗）。"""


def next_phase(unit: UnitState) -> BossPhase | None:
    """``unit`` 的下一個階段（沒有時為 ``None``）。"""
    index = unit.phase_index + 1
    return unit.phases[index] if index < len(unit.phases) else None


def _reached(state: BattleState, unit: UnitState, phase: BossPhase) -> bool:
    trigger = phase.trigger
    match trigger:
        case None:  # 開場階段（schema 保證只在第 1 項）
            return False
        case HpBelowTrigger():
            return unit.hp * 1000 <= unit.max_hp * trigger.permille
        case TagDownTrigger():  # 5F-3：同陣營、帶標籤、已倒下的單位數
            down = sum(
                1
                for u in state.units.values()
                if u.team is unit.team and u.downed and u.has_tag(trigger.tag)
            )
            return down >= trigger.count
        case RoundTrigger():  # 5F-3：第 N 輪起
            return state.round >= trigger.round


def check_boss_phases(ctx: Ctx) -> None:
    """檢查所有帶階段的存活單位，跌破門檻就依序進入新階段（見模組說明）。"""
    if ctx.preview is not None or ctx.state.ended:
        return
    for unit in ctx.state.units_sorted():
        if not unit.phases:
            continue
        while (
            unit.alive
            and (phase := next_phase(unit)) is not None
            and _reached(ctx.state, unit, phase)
        ):
            _enter(ctx, unit, phase)


def _enter(ctx: Ctx, unit: UnitState, phase: BossPhase) -> None:
    trigger = phase.trigger
    assert trigger is not None
    unit.phase_index += 1
    ctx.emit(
        BossPhaseChanged,
        unit_id=unit.id,
        phase=unit.phase_index + 1,
        total=len(unit.phases),
        phase_id=phase.id,
        name_zh=phase.name_zh,
        text_zh=phase.text_zh,
        trigger=trigger.kind,
        permille=trigger.permille if isinstance(trigger, HpBelowTrigger) else None,
        condition_zh=trigger.condition_zh,
        hp=unit.hp,
        max_hp=unit.max_hp,
        skills=phase.skills,
    )
    removes: list[EffectBase] = [
        RemoveStatusEffect(target_id=unit.id, status_id=s, reason="removed")
        for s in phase.remove_statuses
        if unit.has_status(s)
    ]
    if removes:
        execute(ctx, removes)
    if phase.skills is not None:
        unit.skills = phase.skills
        unit.cooldowns = {k: v for k, v in unit.cooldowns.items() if k in phase.skills}
    if phase.ai_profile is not None:
        unit.ai_profile = phase.ai_profile
    _restore_mana(ctx, unit, phase)
    for opening in phase.add_statuses:
        execute(
            ctx,
            [
                ApplyStatusEffect(
                    target_id=unit.id,
                    status_id=opening.status,
                    source_id=unit.id,
                    duration=opening.duration,
                )
            ],
        )
    _change_weather(ctx, unit, phase)
    state = ctx.state
    tiles: list[EffectBase] = [
        ChangeTileEffect(pos=t.at, height=t.height, terrain=t.terrain, surface=t.surface)
        for t in phase.tiles
        if 0 <= t.at[0] < state.width and 0 <= t.at[1] < state.height
    ]
    if tiles:
        execute(ctx, tiles)
    spawns: list[EffectBase] = []
    for spawn in phase.spawns:
        at = unit.xy if spawn.at is None else spawn.at
        spawns += [
            SpawnUnitEffect(pos=at, template_id=spawn.template, team=unit.team)
            for _ in range(spawn.count)
        ]
    if spawns:
        execute(ctx, spawns)


def _restore_mana(ctx: Ctx, unit: UnitState, phase: BossPhase) -> None:
    """``mana_restore``（BAL-21a）：回復法力，不超過最大法力；有實際回復才發 ``resource_restored``
    （來源是頭目自己）。沒填或法力已滿時什麼都不做（不發 ``effect_fizzled``）。"""
    if phase.mana_restore is None:
        return
    gained = min(phase.mana_restore, unit.max_mana - unit.mana)
    if gained <= 0:
        return
    unit.mana += gained
    ctx.emit(
        ResourceRestored,
        unit_id=unit.id,
        source_id=unit.id,
        resource="mana",
        amount=gained,
        mana_after=unit.mana,
        skill_ids=(),
    )


def _change_weather(ctx: Ctx, unit: UnitState, phase: BossPhase) -> None:
    if phase.weather is None:
        return
    state = ctx.state
    before = None if state.weather is None else state.weather.id
    if (before or CLEAR_WEATHER) == phase.weather:
        return
    weather = state.phase_weathers.get(phase.weather)
    if weather is None:  # 設定沒放這個天氣（沒經過 with_phase_assets）：不改，同召喚範本缺少時落空
        return
    state.weather = weather
    ctx.emit(
        WeatherChanged,
        before=before,
        after=weather.id,
        after_name_zh=weather.name_zh,
        source_id=unit.id,
    )
