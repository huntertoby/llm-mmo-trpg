"""被動技能的觸發分派（Phase 2E-1，``docs/phases/Phase2E計畫.md`` 3.3）。

做法：

1. **收集**：:meth:`~trpg.engine.context.Ctx.emit` 把每個事件交給 :func:`observe`；它看出
   ``attack_rolled``（命中、暴擊、自然 20、每命中 n 次）與 ``damage_dealt``（受傷、擊倒），
   為持有對應被動技能的單位記下一筆 :class:`Fired`。回合開始／結束與移動後由回合流程與移動
   動作直接呼叫 :func:`collect_turn_start`、:func:`collect_turn_end`、:func:`collect_move`。
2. **延後結算**：觸發不在事件發生當下結算，而是等一個效果佇列清空（:func:`settle`；施放技能與普攻
   則等整個技能／整次攻擊結束，見 :func:`holding`）。同一批依「事件順序 → 持有者單位 ID → 技能 ID」
   排序；觸發的效果以新的效果佇列結算，其間收集到的觸發 **深度 +1**，成為下一批。
3. **檢查**：持有者在場、沒有 ``skip_turn``、沒被沉默、每輪次數、另一方、距離、技能條件、代價；
   通過後若深度超過 ``max_trigger_depth`` 發出 ``trigger_limit_reached``（不付代價、不計次數），
   否則付代價、發出 ``skill_triggered`` 並結算技能效果（自動命中，歸給持有者）。

另一方倒下（``on_kill``）時，效果的對象清單是空的：傷害與狀態對倒下的單位無效，被動骨架沒有
以位置為準的效果（2E-1 的保守處理）。

修正規則的命中後效果（Phase 3C-2 ``on_hit_effects``）走同一套收集與延後結算：持有者的攻擊
（普攻或受修正的技能）命中時記下一筆 ``event`` 為 ``modifier_on_hit:<規則索引>`` 的 :class:`Fired`，
結算時檢查持有者在場、目標仍存活、規則條件（對目標）與深度，發出 ``skill_triggered``
（``trigger: modifier_on_hit``，沒有代價與每輪次數），再自動命中地結算效果。

裝備的觸發與充能詞條（Phase 3G-G3a，第 6、7 類）走同一套收集與延後結算：持有者身上生效中的
詞條依觸發時機（``trigger`` 或 ``gain_trigger``）加進 :class:`PassiveIndex`，收集時記一筆
``event`` 為 ``gear:<時機>`` 的 :class:`Fired`（``skill_id`` 放詞條 ID），結算在
:mod:`trpg.engine.gear.triggers`（每條每回合／每輪最多 1 次、深度檢查、充能累積）。

這個模組在載入時不匯入效果佇列與技能解譯器（它們反過來匯入 :mod:`trpg.engine.context`），
:func:`settle` 在呼叫時才延後匯入。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from trpg.content.equipment import AttackAffix, ChargeAffix, TriggerAffix
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.engine import modifiers, stack_gain
from trpg.engine.events import (
    AttackRolled,
    Collided,
    DamageDealt,
    EventBase,
    SkillCooldownChanged,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    TriggerLimitReached,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.gear.state import GearAffix
from trpg.engine.rules.combat import NATURAL_HIT
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.statuses import skip_turn_status
from trpg.engine.skills.casting import use_modifier_effects, use_triggered_skill
from trpg.engine.skills.conditions import Subject, condition_met, skill_condition_met
from trpg.engine.skills.targeting import PaidCost, pay_skill_cost, resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import UnitId

if TYPE_CHECKING:
    from trpg.engine.context import Ctx

__all__ = [
    "GEAR_ATTACK_RUNE",
    "GEAR_PREFIX",
    "MODIFIER_ON_HIT",
    "Fired",
    "PassiveIndex",
    "check_trigger_depth",
    "collect_cast",
    "collect_move",
    "collect_turn_end",
    "collect_turn_start",
    "holding",
    "observe",
    "redirect_fired",
    "reset_round_counts",
    "settle",
]

GEAR_PREFIX = "gear:"
"""裝備詞條的 ``Fired.event`` 前綴（``gear:<觸發時機>``；``Fired.skill_id`` 為詞條 ID）。"""

GEAR_ATTACK_RUNE = "attack_rune"
"""普攻符文詞條（Phase 3-31，``rune: detonate／inscribe``）的觸發時機名稱（``Fired.event`` 為
``gear:attack_rune``；``gear_triggered.trigger`` 也用它）。"""

_OBSERVED = frozenset(
    {"attack_rolled", "damage_dealt", "status_applied", "collided", "unit_moved", "unit_downed"}
)

MODIFIER_ON_HIT = "modifier_on_hit"
"""修正規則命中後效果的 ``SkillTriggered.trigger``（不是 ``skill_triggers.yaml`` 的時機）。"""
_MODIFIER_PREFIX = f"{MODIFIER_ON_HIT}:"


@dataclass(frozen=True, slots=True)
class Fired:
    """一筆待結算的觸發：``seq`` 是引起它的事件順序（直接呼叫時為當下的事件序號）。"""

    seq: int
    owner_id: UnitId
    skill_id: str
    event: str
    other_id: UnitId | None
    depth: int


class PassiveIndex:
    """戰鬥中所有單位裝備的被動技能，依觸發時機分組（單位 ID、技能 ID 排序）。

    ``on_hit_owners``：有命中後效果修正規則的單位（Phase 3C-2）。``by_gear_event``：裝備的觸發與
    充能詞條（Phase 3G-G3a），依觸發時機分組（單位 ID、詞條 ID 排序）。
    """

    __slots__ = ("any", "by_event", "by_gear_event", "by_unit", "on_hit_owners")

    def __init__(self, ctx: Ctx) -> None:
        self.by_event: dict[str, list[tuple[UnitId, SkillDef]]] = {}
        self.by_gear_event: dict[str, list[tuple[UnitId, GearAffix]]] = {}
        self.by_unit: dict[UnitId, list[SkillDef]] = {}
        owners: set[UnitId] = set()
        rules = ctx.rules
        for unit in ctx.state.units_sorted():
            for gear in unit.gear.active_affixes():
                affix = gear.affix
                if isinstance(affix, AttackAffix):
                    if affix.rune in ("detonate", "inscribe"):
                        owners.add(unit.id)  # 普攻命中後的符文效果（3-31）
                elif isinstance(affix, TriggerAffix):
                    self.by_gear_event.setdefault(affix.trigger, []).append((unit.id, gear))
                elif isinstance(affix, ChargeAffix):
                    self.by_gear_event.setdefault(affix.gain_trigger, []).append((unit.id, gear))
            for skill_id in sorted(unit.skills):
                skill = rules.skill_def(skill_id)
                if any(r.change.on_hit_effects for r in skill.modifiers):
                    owners.add(unit.id)
                if skill.trigger is None:
                    continue
                self.by_event.setdefault(skill.trigger.event, []).append((unit.id, skill))
                self.by_unit.setdefault(unit.id, []).append(skill)
        self.on_hit_owners = frozenset(owners)
        self.any = bool(self.by_event) or bool(owners) or bool(self.by_gear_event)

    def owners(self, event: str) -> list[tuple[UnitId, SkillDef]]:
        return self.by_event.get(event, [])

    def gear_owners(self, event: str) -> list[tuple[UnitId, GearAffix]]:
        return self.by_gear_event.get(event, [])


def _index(ctx: Ctx) -> PassiveIndex:
    index = ctx.passives
    if index is None:
        index = ctx.passives = PassiveIndex(ctx)
    return index


# ---------------------------------------------------------------------------
# 收集
# ---------------------------------------------------------------------------


def _fire(ctx: Ctx, seq: int, owner_id: UnitId, skill: SkillDef, other_id: UnitId | None) -> None:
    assert skill.trigger is not None
    ctx.fired.append(
        Fired(seq, owner_id, skill.id, skill.trigger.event, other_id, ctx.trigger_depth + 1)
    )


def _fire_gear(  # noqa: PLR0917
    ctx: Ctx,
    index: PassiveIndex,
    timing: str,
    seq: int,
    who: UnitId | None,
    other_id: UnitId | None,
    *,
    melee: bool = True,
    status: str | None = None,
    tag: str | None = None,
    surface: str | None = None,
    hits: int | None = None,
) -> None:
    """裝備詞條的收集：``who`` 身上以 ``timing`` 為時機的觸發與充能詞條各記一筆（觸發詞條的
    ``melee_only``、``status``、``tag``、``surface``、每第 n 次命中的篩選在這裡過濾）。"""
    if who is None:
        return
    for owner, gear in index.gear_owners(timing):
        if owner != who:
            continue
        affix = gear.affix
        if isinstance(affix, TriggerAffix) and (
            (affix.melee_only and not melee)
            or (affix.status is not None and affix.status != status)
            or (affix.tag is not None and affix.tag != tag)
            or (affix.surface is not None and affix.surface != surface)
            or (affix.n is not None and (hits is None or hits % affix.n != 0))
        ):
            continue
        ctx.fired.append(
            Fired(seq, owner, affix.id, f"{GEAR_PREFIX}{timing}", other_id, ctx.trigger_depth + 1)
        )


def observe(ctx: Ctx, event: EventBase) -> None:
    """``Ctx.emit`` 的掛鉤：看出需要觸發被動的事件。"""
    if getattr(event, "type", None) not in _OBSERVED:
        return
    if isinstance(event, UnitDowned):
        ctx.downed.append(event.unit_id)  # ally_downed 反應：等效果佇列清空後（settle）才處理
        _on_summon_downed(ctx, event)
        stack_gain.collect_downed(ctx, event)
        return
    if isinstance(event, AttackRolled):
        _on_attacked_charge(ctx, event)
        stack_gain.collect_attack(ctx, event)
    elif isinstance(event, DamageDealt):
        stack_gain.collect_damage(ctx, event)
    index = _index(ctx)
    if not index.any:
        return
    if isinstance(event, AttackRolled):
        if event.hit and event.attacker_id in index.on_hit_owners:
            _on_modified_hit(ctx, event)
        _on_attack(ctx, index, event)
    elif isinstance(event, DamageDealt):
        _on_damage(ctx, index, event)
    elif isinstance(event, StatusApplied):
        _on_status_applied(ctx, index, event)
    elif isinstance(event, Collided):
        _on_collision(ctx, index, event)
    elif isinstance(event, UnitMoved):
        _on_enter_surface(ctx, index, event)


def _on_summon_downed(ctx: Ctx, event: UnitDowned) -> None:
    """``on_summon_downed``（Phase 3-33f2，裝備詞條）：召喚物被打倒，召喚者身上的詞條各記一筆
    （另一方為倒下的召喚物）。時效到期、被獻祭、召喚者倒下而消失的召喚物不會有 ``unit_downed``。"""
    unit = ctx.state.units.get(event.unit_id)
    if unit is None or unit.owner_id is None:
        return
    index = _index(ctx)
    if index.gear_owners("on_summon_downed"):
        _fire_gear(ctx, index, "on_summon_downed", event.seq, unit.owner_id, unit.id)


def _on_attacked_charge(ctx: Ctx, event: AttackRolled) -> None:
    """被攻擊才釋放的延遲段（Phase 3F-4b）：記一筆，等這次攻擊結算完才釋放。"""
    from trpg.engine.delayed import DELAYED_RELEASE, attacked_release  # noqa: PLC0415

    skill = attacked_release(ctx.state, event)
    if skill is not None:
        ctx.fired.append(
            Fired(
                event.seq,
                event.target_id,
                skill.id,
                DELAYED_RELEASE,
                event.attacker_id,
                ctx.trigger_depth + 1,
            )
        )


def _on_attack(ctx: Ctx, index: PassiveIndex, event: AttackRolled) -> None:
    attacker = event.attacker_id
    if event.natural == NATURAL_HIT:
        for owner, skill in index.owners("on_natural_20"):
            if owner == attacker:
                _fire(ctx, event.seq, owner, skill, event.target_id)
        _fire_gear(ctx, index, "on_natural_20", event.seq, attacker, event.target_id)
    if not event.hit:
        return
    for owner, skill in index.owners("on_hit"):
        if owner == attacker:
            _fire(ctx, event.seq, owner, skill, event.target_id)
    _fire_gear(ctx, index, "on_hit", event.seq, attacker, event.target_id)
    if event.crit:
        for owner, skill in index.owners("on_crit"):
            if owner == attacker:
                _fire(ctx, event.seq, owner, skill, event.target_id)
        _fire_gear(ctx, index, "on_crit", event.seq, attacker, event.target_id)
    _count_hits(ctx, index, event)


def _count_hits(ctx: Ctx, index: PassiveIndex, event: AttackRolled) -> None:
    """``every_n_hits``：持有者累計的命中次數 +1（只有裝備了這類被動或裝備詞條的單位才累計），
    累計到 n 的倍數時觸發。"""
    attacker = event.attacker_id
    counters = [(o, s) for o, s in index.owners("every_n_hits") if o == attacker]
    gear_counters = [(o, g) for o, g in index.gear_owners("every_n_hits") if o == attacker]
    if not counters and not gear_counters:
        return
    unit = ctx.state.units[attacker]
    unit.hits_landed += 1
    for owner, skill in counters:
        assert skill.trigger is not None and skill.trigger.n is not None
        if unit.hits_landed % skill.trigger.n == 0:
            _fire(ctx, event.seq, owner, skill, event.target_id)
    if gear_counters:
        _fire_gear(
            ctx, index, "every_n_hits", event.seq, attacker, event.target_id, hits=unit.hits_landed
        )


def _cast_form(ctx: Ctx, caster_id: UnitId, skill_id: str) -> SkillDef:
    """這次攻擊所屬施放的型態（Phase 3E-2a）：最近一筆同施放者、同技能的 ``skill_used`` 帶有變奏
    時回傳變奏型態，否則是基礎型態——修正規則的比對（元素、標籤）要看實際施放的型態。"""
    skill = ctx.rules.skill_def(skill_id)
    if not skill.variants:
        return skill
    for past in reversed(ctx.events):
        if isinstance(past, SkillUsed) and past.unit_id == caster_id and past.skill_id == skill_id:
            return skill if past.variant is None else skill.variant_form(past.variant)
    return skill


def _on_modified_hit(ctx: Ctx, event: AttackRolled) -> None:
    """持有者的攻擊命中：套用在這次攻擊（普攻或技能）上的命中後效果規則各記一筆。"""
    state = ctx.state
    attacker = state.units[event.attacker_id]
    if event.skill_id is None:
        use = modifiers.ATTACK
    else:
        use = modifiers.skill_use(_cast_form(ctx, attacker.id, event.skill_id))
    if event.skill_id is None:  # 普攻的符文詞條（3-31；刻與引爆不會同時出現，依詞條 ID 排序）
        for gear in attacker.gear.active_affixes("attack"):
            affix = gear.affix
            assert isinstance(affix, AttackAffix)
            if affix.rune in ("detonate", "inscribe"):
                ctx.fired.append(
                    Fired(
                        event.seq,
                        attacker.id,
                        affix.id,
                        f"{GEAR_PREFIX}{GEAR_ATTACK_RUNE}",
                        event.target_id,
                        ctx.trigger_depth + 1,
                    )
                )
    for active in modifiers.on_hit_rules(state, attacker, use):
        ctx.fired.append(
            Fired(
                event.seq,
                attacker.id,
                active.skill.id,
                f"{_MODIFIER_PREFIX}{active.index}",
                event.target_id,
                ctx.trigger_depth + 1,
            )
        )


def _is_melee_damage(ctx: Ctx, event: DamageDealt) -> bool:
    """傷害是近戰攻擊造成的（裝備觸發的 ``melee_only``）：``attack`` 原因，且來源與目標的距離
    不超過 ``core.melee_height_limit_max_range``。"""
    source = None if event.source_id is None else ctx.state.units.get(event.source_id)
    target = ctx.state.units.get(event.target_id)
    if event.cause != "attack" or source is None or target is None:
        return False
    return manhattan(source.xy, target.xy) <= ctx.core.melee_height_limit_max_range


def _on_damage(ctx: Ctx, index: PassiveIndex, event: DamageDealt) -> None:
    if event.amount <= 0:
        return
    for owner, skill in index.owners("on_damaged"):
        if owner == event.target_id:
            _fire(ctx, event.seq, owner, skill, event.source_id)
    if index.gear_owners("on_damaged"):
        _fire_gear(
            ctx, index, "on_damaged", event.seq, event.target_id, event.source_id,
            melee=_is_melee_damage(ctx, event),
        )  # fmt: skip
    if event.hp_after <= 0 and event.source_id is not None and event.source_id != event.target_id:
        for owner, skill in index.owners("on_kill"):
            if owner == event.source_id:
                _fire(ctx, event.seq, owner, skill, event.target_id)
        _fire_gear(ctx, index, "on_kill", event.seq, event.source_id, event.target_id)


def _on_status_applied(ctx: Ctx, index: PassiveIndex, event: StatusApplied) -> None:
    """``on_status_applied``：持有者成功對其他單位施加狀態（抵抗成功不會產生 ``StatusApplied``；
    對自己施加的不算）。"""
    source = event.source_id
    if source is None or source == event.target_id:
        return
    for owner, skill in index.owners("on_status_applied"):
        assert skill.trigger is not None
        if owner == source and skill.trigger.status in (None, event.status_id):
            _fire(ctx, event.seq, owner, skill, event.target_id)
    _fire_gear(
        ctx, index, "on_status_applied", event.seq, source, event.target_id, status=event.status_id
    )


def _on_collision(ctx: Ctx, index: PassiveIndex, event: Collided) -> None:
    """``on_collision``：持有者造成的撞擊（來源歸給持有者；自己撞到自己不算）。"""
    source = event.source_id
    if source is None or source == event.unit_id:
        return
    for owner, skill in index.owners("on_collision"):
        if owner == source:
            _fire(ctx, event.seq, owner, skill, event.unit_id)
    _fire_gear(ctx, index, "on_collision", event.seq, source, event.unit_id)


def _on_enter_surface(ctx: Ctx, index: PassiveIndex, event: UnitMoved) -> None:
    """``on_enter_surface``：敵方單位步行或被強制位移進入持有者造出的表面（傳送不算；回合開始
    站在表面上、表面出現在腳下都不是「進入」，不會產生 ``UnitMoved``）。"""
    if event.mode in ("teleport", "teleported", "shadowstep"):
        return
    state = ctx.state
    tile = state.tile(event.to_pos.x, event.to_pos.y)
    creator_id = tile.surface_creator
    owners = index.owners("on_enter_surface")
    if creator_id is None or not (owners or index.gear_owners("on_enter_surface")):
        return
    creator = state.units.get(creator_id)
    mover = state.units.get(event.unit_id)
    if creator is None or mover is None or creator.team is mover.team:
        return
    for owner, skill in owners:
        assert skill.trigger is not None
        if owner == creator_id and skill.trigger.surface in (None, tile.surface):
            _fire(ctx, event.seq, owner, skill, mover.id)
    _fire_gear(
        ctx, index, "on_enter_surface", event.seq, creator_id, mover.id, surface=tile.surface.value
    )


def collect_cast(ctx: Ctx, caster: UnitState, skill: SkillDef) -> None:
    """``on_cast_tag``：持有者施放的技能（含修正規則加上的標籤）帶有 ``trigger.tag``，在該技能
    結算之後。被動觸發與陷阱觸發的效果不算施放，不會呼叫這裡。"""
    stack_gain.collect_cast(ctx, caster, skill)  # 聖能：施放治療或神聖技能（3-52）
    index = _index(ctx)
    if not index.any:
        return
    owned = index.owners("on_cast_tag")
    gear_owned = [(o, g) for o, g in index.gear_owners("on_cast_tag") if o == caster.id]
    if not gear_owned and not any(owner == caster.id for owner, _ in owned):
        return
    tags = modifiers.effective_tags(ctx.state, caster, skill)
    seq = ctx.state.next_event_seq
    for owner, passive in owned:
        assert passive.trigger is not None
        if owner == caster.id and passive.trigger.tag in tags:
            _fire(ctx, seq, owner, passive, None)
    for tag in sorted(tags):
        _fire_gear(ctx, index, "on_cast_tag", seq, caster.id, None, tag=tag)


def _collect_own(ctx: Ctx, unit: UnitState, event: str) -> None:
    index = _index(ctx)
    if not index.any:
        return
    seq = ctx.state.next_event_seq
    for owner, skill in index.owners(event):
        if owner == unit.id:
            _fire(ctx, seq, owner, skill, None)
    _fire_gear(ctx, index, event, seq, unit.id, None)


def collect_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """``on_turn_start``：回合開始，在狀態與表面的回合開始效果之後。"""
    _collect_own(ctx, unit, "on_turn_start")


def collect_turn_end(ctx: Ctx, unit: UnitState) -> None:
    """``on_turn_end``：回合結束，在狀態倒數之前。"""
    stack_gain.collect_turn_end(ctx, unit)  # 專注：這回合沒有移動（3-52）
    _collect_own(ctx, unit, "on_turn_end")


def collect_move(ctx: Ctx, unit: UnitState) -> None:
    """``on_move``：一次主動移動動作完成後。"""
    _collect_own(ctx, unit, "on_move")


def redirect_fired(ctx: Ctx, seq: int, old: UnitId, new: UnitId) -> None:
    """攔截（2E-2）：引起事件 ``seq`` 的攻擊已改為作用在 ``new``——還沒結算的觸發，另一方由 ``old``
    改為 ``new``（例如攻擊者的「命中時」被動，對象是實際挨打的守護者）。"""
    ctx.fired = [
        replace(f, other_id=new) if f.seq == seq and f.other_id == old else f for f in ctx.fired
    ]


def reset_round_counts(units: Iterator[UnitState]) -> None:
    """每輪開始：被動技能的本輪觸發次數歸零。"""
    for unit in units:
        if unit.trigger_counts:
            unit.trigger_counts = {}
        if unit.gear_round_counts:
            unit.gear_round_counts = {}


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


@contextmanager
def holding(ctx: Ctx) -> Iterator[None]:
    """括號內不結算觸發（施放技能、一次普攻），結束後一次結算。"""
    ctx.trigger_hold += 1
    try:
        yield
    finally:
        ctx.trigger_hold -= 1
    settle(ctx)


def settle(ctx: Ctx) -> None:
    """結算收集到的觸發（括號內或已在結算中時不做事）。"""
    if ctx.settling or ctx.trigger_hold or not (ctx.fired or ctx.downed):
        return
    ctx.settling = True
    try:
        while ctx.fired or ctx.downed:
            _settle_downed(ctx)
            batch = sorted(ctx.fired, key=lambda f: (f.seq, f.owner_id, f.skill_id))
            ctx.fired = []
            for fired in batch:
                if fired.event.startswith(stack_gain.STACK_GAIN_PREFIX):
                    stack_gain.resolve(ctx, fired)
                elif fired.event.startswith(GEAR_PREFIX):
                    _resolve_gear(ctx, fired)
                elif fired.event.startswith(_MODIFIER_PREFIX):
                    _resolve_on_hit(ctx, fired)
                elif fired.event == _DELAYED_RELEASE:
                    _resolve_delayed(ctx, fired)
                else:
                    _resolve_one(ctx, fired)
    finally:
        ctx.settling = False
        ctx.trigger_depth = 0


def _settle_downed(ctx: Ctx) -> None:
    """剛倒下的單位（依發生順序）：視野內的友方可以用 ``ally_downed`` 反應技反應。"""
    # 延後匯入：反應模組匯入本模組（check_trigger_depth、holding……）。
    from trpg.engine.reactions import ally_downed_reactions  # noqa: PLC0415

    while ctx.downed:
        downed = ctx.state.units.get(ctx.downed.pop(0))
        if downed is not None and not ctx.state.ended:
            ally_downed_reactions(ctx, downed)


def check_trigger_depth(ctx: Ctx, unit_id: UnitId, skill_id: str, depth: int) -> bool:
    """觸發深度是否在 ``max_trigger_depth`` 內；超過時發出 ``trigger_limit_reached`` 並回傳
    ``False``（不付代價、不計次數）。被動觸發、反應技與陷阱觸發共用（Phase 2F-1 3.1，取代
    ``reactions._skill_usable``、``skill_triggers._resolve_one``、``traps._trigger`` 三處重複）。
    """
    if depth > ctx.core.max_trigger_depth:
        ctx.emit(TriggerLimitReached, unit_id=unit_id, skill_id=skill_id, depth=depth)
        return False
    return True


def _usable(ctx: Ctx, owner: UnitState, skill: SkillDef) -> bool:
    """持有者目前能不能觸發這個被動：被動專屬條件（存活、沒有 skip_turn、每輪次數）之外的
    資源檢查（沉默、法力、冷卻、每場次數、HP、層數）與 :func:`~.targeting.skill_problem`、
    :func:`~.targeting.reaction_problem` 共用 :func:`~.targeting.resource_problem`
    （Phase 2F-1 3.1）。"""
    assert skill.trigger is not None
    if not owner.alive or skip_turn_status(ctx.rules, owner) is not None:
        return False
    if owner.trigger_counts.get(skill.id, 0) >= skill.trigger.max_per_round:
        return False
    return resource_problem(ctx.state, owner, skill) is None


def nearest_enemy(state: BattleState, owner: UnitState, max_distance: int) -> UnitState | None:
    """``max_distance`` 格（曼哈頓）內離 ``owner`` 最近的存活敵人；同距離取單位 ID 小的。"""
    best: tuple[int, str] | None = None
    found: UnitState | None = None
    for unit in state.units_sorted():
        if not unit.alive or unit.team is owner.team:
            continue
        distance = manhattan(owner.xy, unit.xy)
        if distance <= max_distance and (best is None or (distance, unit.id) < best):
            best, found = (distance, unit.id), unit
    return found


def _trigger_other(
    state: BattleState, fired: Fired, owner: UnitState, trigger: TriggerSpec
) -> UnitState | Literal[False] | None:
    """被動效果作用的另一方：``self`` 為 ``None``；``other`` 是該時機的另一方；``nearest_enemy``
    （3W-2b）是 ``max_distance`` 格內最近的敵人。找不到或太遠時回傳 ``False``（不觸發）。"""
    if trigger.target == "self":
        return None
    if trigger.target == "nearest_enemy":
        assert trigger.max_distance is not None
        return nearest_enemy(state, owner, trigger.max_distance) or False
    other = None if fired.other_id is None else state.units.get(fired.other_id)
    if other is None or (not other.alive and fired.event != "on_kill"):
        return False
    if trigger.max_distance is not None and manhattan(owner.xy, other.xy) > trigger.max_distance:
        return False
    return other


def _resolve_one(ctx: Ctx, fired: Fired) -> None:
    state = ctx.state
    if state.ended:
        return
    owner = state.units.get(fired.owner_id)
    skill = ctx.rules.skill_def(fired.skill_id)
    trigger = skill.trigger
    assert trigger is not None
    if owner is None or not _usable(ctx, owner, skill):
        return
    found = _trigger_other(state, fired, owner, trigger)
    if found is False:
        return
    other = found
    subject = owner if other is None else other
    if not skill_condition_met(state, owner, skill, [subject.xy]):
        return
    if not check_trigger_depth(ctx, owner.id, skill.id, fired.depth):
        return
    _pay(ctx, owner, skill, fired)
    ctx.trigger_depth = fired.depth
    use_triggered_skill(ctx, owner, skill, other)


def _resolve_gear(ctx: Ctx, fired: Fired) -> None:
    """裝備的觸發與充能詞條（Phase 3G-G3a）。"""
    from trpg.engine.gear.triggers import resolve_gear_fired  # noqa: PLC0415

    resolve_gear_fired(ctx, fired)


_DELAYED_RELEASE = "delayed_release"
"""與 :data:`trpg.engine.delayed.DELAYED_RELEASE` 相同（本模組載入時不匯入它）。"""


def _resolve_delayed(ctx: Ctx, fired: Fired) -> None:
    """被攻擊才釋放的延遲段（Phase 3F-4b）：觸發深度在上限內才釋放。"""
    from trpg.engine.delayed import resolve_attacked_release  # noqa: PLC0415

    owner = ctx.state.units.get(fired.owner_id)
    if ctx.state.ended or owner is None:
        return
    if not check_trigger_depth(ctx, owner.id, fired.skill_id, fired.depth):
        return
    ctx.trigger_depth = fired.depth
    resolve_attacked_release(ctx, owner, fired.skill_id)


def _resolve_on_hit(ctx: Ctx, fired: Fired) -> None:
    """修正規則的命中後效果：持有者在場、目標仍存活、規則條件（對目標）成立、深度未超過上限。
    沒有代價與每輪次數（預算以「每場使用次數」計算）。"""
    state = ctx.state
    owner = state.units.get(fired.owner_id)
    other = None if fired.other_id is None else state.units.get(fired.other_id)
    if state.ended or owner is None or not owner.alive or other is None or not other.alive:
        return
    skill = ctx.rules.skill_def(fired.skill_id)
    rule = skill.modifiers[int(fired.event.removeprefix(_MODIFIER_PREFIX))]
    effects = rule.change.on_hit_effects
    assert effects is not None
    if not condition_met(state, owner, rule.condition, Subject(other, other.xy)):
        return
    index = int(fired.event.removeprefix(_MODIFIER_PREFIX))
    if modifiers.rule_limit_reached(owner, modifiers.ActiveRule(skill, index, rule)):
        return  # 每回合 1 次（3-31）
    if not check_trigger_depth(ctx, owner.id, skill.id, fired.depth):
        return
    if rule.per_turn_limit is not None:
        key = modifiers.rule_limit_key(skill.id, index)
        owner.gear_turn_counts[key] = owner.gear_turn_counts.get(key, 0) + 1
    ctx.emit(
        SkillTriggered,
        unit_id=owner.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        trigger=MODIFIER_ON_HIT,
        other_id=other.id,
        trigger_depth=fired.depth,
        mana_after=owner.mana,
    )
    ctx.trigger_depth = fired.depth
    use_modifier_effects(ctx, owner, skill, effects, other)


def _pay(ctx: Ctx, owner: UnitState, skill: SkillDef, fired: Fired) -> None:
    paid: PaidCost = pay_skill_cost(owner, skill)
    owner.trigger_counts[skill.id] = owner.trigger_counts.get(skill.id, 0) + 1
    ctx.emit(
        SkillTriggered,
        unit_id=owner.id,
        skill_id=skill.id,
        name_zh=skill.name_zh,
        trigger=fired.event,
        other_id=fired.other_id,
        trigger_depth=fired.depth,
        mana=skill.cost.mana,
        mana_after=owner.mana,
        stamina=skill.cost.stamina,
        stamina_after=owner.stamina,
        hp_spent=paid.hp,
        cooldown=paid.cooldown,
    )
    if paid.cooldown is not None:
        ctx.emit(SkillCooldownChanged, unit_id=owner.id, skill_id=skill.id, remaining=paid.cooldown)
