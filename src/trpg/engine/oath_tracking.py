"""誓約的追蹤與違反判定（Phase R3 自 :mod:`trpg.engine.oaths` 抽出；只看事件與狀態，不結算效果）。

:class:`OathSetup`、:class:`OathTracker`（戰鬥狀態的一部分）、:func:`observe_oath`
（:meth:`~trpg.engine.context.Ctx.emit` 的掛鉤）與 :func:`oath_warning`（預覽）都在這裡，所以
``state``／``context`` 可以在模組頂端匯入它們而不經過效果佇列。開場與收尾（要結算效果的
:func:`~trpg.engine.oaths.open_oath`、:func:`~trpg.engine.oaths.settle_oath`）留在
:mod:`trpg.engine.oaths`，該模組也照舊轉出本模組的名稱。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.world_oaths import OathCheck
from trpg.engine.events import (
    AttackRolled,
    BattleEnded,
    DamageDealt,
    EventBase,
    OathBroken,
    ReactionTriggered,
    SkillUsed,
    StatusApplied,
    TurnEnded,
    TurnStarted,
    UnitDowned,
    UnitMoved,
)
from trpg.shared.types import Surface, UnitId

if TYPE_CHECKING:
    from trpg.engine.context import Ctx
    from trpg.engine.state import BattleState, UnitState

__all__ = [
    "BREACH_TEXT",
    "ELEMENT_EXEMPT_CAUSES",
    "VOLUNTARY_MOVES",
    "OathSetup",
    "OathTracker",
    "breach_oath",
    "oath_warning",
    "observe_oath",
]

VOLUNTARY_MOVES = frozenset({"walk", "dash", "leap", "shadowstep"})
"""算「主動移動」的 ``unit_moved`` 模式（不含強制位移、被傳送、交換）。"""

ELEMENT_EXEMPT_CAUSES = frozenset({"fall", "collision", "topple", "deadly_terrain", "backlash"})
"""「只用某一種元素造成傷害」不算的傷害原因（墜落、撞擊、推倒、致命地形、反噬）。"""


class OathSetup(BaseModel):
    """帶著誓約開戰（``BattleSetup.oath``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit: int = Field(default=0, ge=0)
    """帶誓約的單位在 ``BattleSetup.units`` 的索引（大世界的主角是 0）。"""
    template: str
    """誓約模板 ID（只是紀錄，給 ``oath_broken`` 用）。"""
    check: OathCheck
    """已填好參數的判定。"""
    bonus_status: str | None = None
    """開場掛上的加成狀態（依難度查表）；``None``＝沒有加成。"""
    penalty_status: str | None = None
    """違反時施加的破誓狀態；``None``＝沒有懲罰狀態。"""
    penalty_rounds: int = Field(default=2, ge=1)
    start_penalty_rounds: int = Field(default=0, ge=0)
    """開場就帶著的破誓回合數（5C-3b：上一場戰鬥結束才判出的違反，破誓帶到這一場開場；加成照常）。"""
    label_zh: str = ""
    """誓約的中文名（給「會違反誓約」的警告用）。"""


@dataclass(frozen=True, slots=True)
class OathTracker:
    """戰鬥中的誓約進度（``BattleState.oath``；不可變，改變時換新的）。"""

    holder: UnitId
    setup: OathSetup
    broken: bool = False
    """已經違反（之後不再判定）。"""
    pending: bool = False
    """剛違反、還沒執行後果（等這次結算收尾）。"""
    attacked: bool = False
    """這個回合攻擊過了（``attack_each_turn``）。"""
    turns: int = 0
    """自己開始過幾個回合（``no_move_first_turn``）。"""
    melee_kills: int = 0
    applied: int = 0
    """施加指定狀態的次數（``min_status_applied``）。"""


def breach_oath(state: BattleState) -> None:
    """記下誓約剛被違反（``pending``；收尾時 :func:`~trpg.engine.oaths.settle_oath` 才執行）。"""
    tracker = state.oath
    if tracker is not None and not tracker.broken and not tracker.pending:
        state.oath = dataclasses.replace(tracker, pending=True)


# ---------------------------------------------------------------------------
# 戰鬥中的判定
# ---------------------------------------------------------------------------


def observe_oath(ctx: Ctx, event: EventBase) -> None:
    """``Ctx.emit`` 的掛鉤：依事件更新誓約進度、判定違反（只記下，收尾才執行）。"""
    tracker = ctx.state.oath
    if tracker is None or tracker.broken or tracker.pending:
        return
    if isinstance(event, BattleEnded):
        _judge_at_end(ctx, tracker)
        return
    updated, broken = _judge(ctx, tracker, event)
    if updated is not tracker:
        ctx.state.oath = updated
    if broken:
        breach_oath(ctx.state)


def _judge(ctx: Ctx, tracker: OathTracker, event: EventBase) -> tuple[OathTracker, bool]:  # noqa: PLR0911 — 依事件種類分派
    holder = tracker.holder
    if isinstance(event, SkillUsed):
        return tracker, event.unit_id == holder and _skill_breaks(ctx, tracker, event)
    if isinstance(event, AttackRolled):
        if event.attacker_id == holder and not tracker.attacked:
            return dataclasses.replace(tracker, attacked=True), False
        return tracker, False
    if isinstance(event, DamageDealt):
        return _on_damage(ctx, tracker, event)
    if isinstance(event, UnitMoved):
        return tracker, event.unit_id == holder and _move_breaks(ctx, tracker, event)
    if isinstance(event, TurnStarted):
        if event.unit_id != holder:
            return tracker, False
        return dataclasses.replace(tracker, attacked=False, turns=tracker.turns + 1), False
    if isinstance(event, TurnEnded):
        return tracker, event.unit_id == holder and _turn_end_breaks(ctx, tracker)
    if isinstance(event, ReactionTriggered):
        return tracker, event.unit_id == holder and tracker.setup.check.kind == "forbid_reaction"
    if isinstance(event, UnitDowned):
        return tracker, _ally_down_breaks(ctx, tracker, event)
    if isinstance(event, StatusApplied):
        check = tracker.setup.check
        if (
            check.kind == "min_status_applied"
            and event.source_id == holder
            and event.status_id == check.status
        ):
            return dataclasses.replace(tracker, applied=tracker.applied + 1), False
    return tracker, False


def _skill_breaks(ctx: Ctx, tracker: OathTracker, event: SkillUsed) -> bool:
    check = tracker.setup.check
    if check.kind not in ("forbid_skill_tag", "forbid_skill_category", "forbid_skill_tag_until_hp"):
        return False
    skill = ctx.rules.skill_def(event.skill_id)
    if check.kind == "forbid_skill_category":
        return skill.category == check.category
    if not set(skill.tags) & set(check.tags):
        return False
    if check.kind == "forbid_skill_tag":
        return True
    unit = ctx.state.units[tracker.holder]
    return unit.hp * 1000 >= unit.max_hp * check.hp_permille


def _on_damage(ctx: Ctx, tracker: OathTracker, event: DamageDealt) -> tuple[OathTracker, bool]:
    holder = tracker.holder
    if event.source_id != holder:
        return tracker, False
    check = tracker.setup.check
    updated = tracker
    if event.cause == "attack" and not tracker.attacked:
        updated = dataclasses.replace(updated, attacked=True)
    if check.kind == "min_melee_kills" and _melee_kill(ctx, holder, event):
        updated = dataclasses.replace(updated, melee_kills=updated.melee_kills + 1)
    broken = (
        check.kind == "damage_element_only"
        and event.amount > 0
        and event.cause not in ELEMENT_EXEMPT_CAUSES
        and str(event.element) != check.element
    )
    return updated, broken


def _melee_kill(ctx: Ctx, holder: UnitId, event: DamageDealt) -> bool:
    """自己 ``cause: attack`` 的傷害讓敵人 HP 歸零，而且自己的武器是近戰。"""
    if event.cause != "attack" or event.hp_after > 0 or event.hp_before <= 0:
        return False
    units = ctx.state.units
    me, target = units.get(holder), units.get(event.target_id)
    if me is None or target is None or target.team is me.team:
        return False
    return me.weapon.range <= ctx.core.melee_height_limit_max_range


def _move_breaks(ctx: Ctx, tracker: OathTracker, event: UnitMoved) -> bool:
    if event.mode not in VOLUNTARY_MOVES:
        return False
    kind = tracker.setup.check.kind
    if kind == "no_move_first_turn":
        return tracker.turns == 1 and ctx.state.active_unit == tracker.holder
    if kind != "no_retreat":
        return False
    me = ctx.state.units[tracker.holder]
    enemies = [u for u in ctx.state.units_sorted() if u.alive and u.team is not me.team]
    if not enemies:
        return False
    before = _nearest(enemies, (event.from_pos.x, event.from_pos.y))
    after = _nearest(enemies, (event.to_pos.x, event.to_pos.y))
    return after > before


def _nearest(enemies: list[UnitState], xy: tuple[int, int]) -> int:
    # 量到最近佔格（GB-1b；state.py 匯入本模組，所以不能匯入 rules.footprint，照它的算法寫）
    return min(
        _gap(u.xy[0], xy[0], u.footprint) + _gap(u.xy[1], xy[1], u.footprint) for u in enemies
    )


def _gap(center: int, at: int, footprint: int) -> int:
    return max(abs(center - at) - footprint // 2, 0)


def _turn_end_breaks(ctx: Ctx, tracker: OathTracker) -> bool:
    kind = tracker.setup.check.kind
    if kind == "attack_each_turn":
        return not tracker.attacked
    if kind not in ("end_turn_high", "end_turn_off_surface"):
        return False
    me = ctx.state.units[tracker.holder]
    if not me.alive:
        return False
    tile = ctx.state.tile(*me.xy)
    if kind == "end_turn_high":
        return tile.height < 1
    return tile.surface is not Surface.NONE


def _ally_down_breaks(ctx: Ctx, tracker: OathTracker, event: UnitDowned) -> bool:
    if tracker.setup.check.kind != "protect_allies" or event.unit_id == tracker.holder:
        return False
    units = ctx.state.units
    me, fallen = units.get(tracker.holder), units.get(event.unit_id)
    return me is not None and fallen is not None and fallen.team is me.team and not fallen.is_summon


def _judge_at_end(ctx: Ctx, tracker: OathTracker) -> None:
    """戰鬥結束時判定「每場至少……」；沒達到就發 ``oath_broken``（``at_end``，沒有效果）。"""
    check = tracker.setup.check
    if check.kind == "min_melee_kills":
        failed = tracker.melee_kills < check.count
    elif check.kind == "min_status_applied":
        failed = tracker.applied < check.count
    else:
        return
    if not failed:
        return
    ctx.state.oath = dataclasses.replace(tracker, broken=True)
    ctx.emit(
        OathBroken,
        unit_id=tracker.holder,
        template=tracker.setup.template,
        check=check.kind,
        at_end=True,
    )


# ---------------------------------------------------------------------------
# 按下前的警告（5C-3b；06 6.26「會違反誓約的動作按下前先警告」）
# ---------------------------------------------------------------------------

BREACH_TEXT: dict[str, str] = {
    "forbid_skill_tag": "這招的類型是誓約禁止的",
    "forbid_skill_category": "這招的類別是誓約禁止的",
    "forbid_skill_tag_until_hp": "HP 還沒低於門檻就用了誓約禁止的招式",
    "no_retreat": "這個動作會讓你離最近的敵人更遠",
    "attack_each_turn": "這個回合還沒有攻擊就結束回合",
    "end_turn_high": "結束回合時不在高處",
    "damage_element_only": "這個動作會造成誓約限定以外的元素傷害",
    "forbid_reaction": "打開反應設定，之後觸發反應就違反",
    "protect_allies": "這個動作會讓隊友倒下",
    "no_move_first_turn": "第 1 個回合不能主動移動",
    "end_turn_off_surface": "結束回合時站在地面效果上",
}
"""各判定種類的違反原因（沒列的種類，例如戰鬥結束才判的，不會在按下前警告）。"""


def oath_warning(
    before: BattleState, action: object, simulated: tuple[BattleState, ...]
) -> str | None:
    """``action`` 會違反誓約時的中文原因，否則 ``None``（由引擎判定，不靠前端猜）。

    ``simulated`` 是預覽模擬（最少、最多後果）之後的戰鬥狀態：最少後果的模擬就違反＝「會違反」，
    只有最多後果的模擬違反＝「可能會違反」。另外 ``forbid_reaction`` 的持有者打開反應設定
    （``set_reaction_mode`` 不是 ``off``）也警告。
    """
    tracker = before.oath
    if tracker is None or tracker.broken or tracker.pending:
        return None
    kind = tracker.setup.check.kind
    reason = BREACH_TEXT.get(kind)
    if reason is None:
        return None
    certain = any(_breached(s) for s in simulated[:1])
    possible = any(_breached(s) for s in simulated[1:])
    if (
        kind == "forbid_reaction"
        and getattr(action, "type", None) == "set_reaction_mode"
        and getattr(action, "mode", "off") != "off"
    ):
        certain = True
    if not certain and not possible:
        return None
    name = tracker.setup.label_zh or tracker.setup.template
    lead = "會" if certain else "可能會"
    return (
        f"{lead}違反誓約「{name}」：{reason}。"
        f"違反的後果：本場加成移除，並受到破誓 {tracker.setup.penalty_rounds} 回合。"
    )


def _breached(state: BattleState) -> bool:
    return state.oath is not None and (state.oath.broken or state.oath.pending)
