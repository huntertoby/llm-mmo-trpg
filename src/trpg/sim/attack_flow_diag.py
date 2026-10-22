"""普攻流診斷與新指標（Phase 3-32d，``docs/phases/Phase3計畫.md`` 35.4）。

從一場戰鬥的事件與「英雄回合開始時的狀態」推導（確定、可重播，不改任何規則）：

- **擊殺輪數**：Boss 倒下的輪、全部敵人倒下的輪（清場）；
- **傷害來源拆解**（英雄）：基礎普攻、連擊、分裂、精通、各技能、間接；暴擊命中另列（與其他欄重疊）；
- **打不出技能的回合**：英雄回合開始時沒有任何主動技能可用（法力不足或全部冷卻中）；
- **範圍技命中數**：每次使用技能時，被英雄打到的敵人數。

精通的占比是近似值：普攻（含連擊）命中的傷害 ``× m / (1000 + m)``，
``m`` 是英雄開場時的精通加成（‰）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from trpg.engine.battle import begin_battle
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    GearTriggered,
    RoundStarted,
    SkillUsed,
    TurnStarted,
    UnitDowned,
)
from trpg.engine.modifiers import acting_skill, empty_active_slots
from trpg.engine.results import ResolveResult
from trpg.engine.setup import BattleSetup
from trpg.engine.skills.targeting import resource_problem
from trpg.engine.state import BattleState, UnitState
from trpg.engine.strikes import STRIKE_CLEAVE, STRIKE_COMBO
from trpg.shared.types import Team

__all__ = ["FlowExtras", "FlowTrace", "analyze_flow", "hero_mastery_permille"]

_PERMILLE = 1000


@dataclass(frozen=True, slots=True)
class FlowExtras:
    """一場戰鬥的診斷與新指標（英雄 ＝ 該 build 的英雄）。"""

    has_boss: bool
    """敵方有 Boss。"""
    boss_kill_round: int | None
    """Boss 倒下的輪（1 起算）；沒有 Boss 或沒打倒為 ``None``。"""
    clear_round: int | None
    """敵方全部倒下的輪；沒有清場為 ``None``。"""
    hero_turns: int
    """英雄回合開始的次數（敵人還在場）。"""
    no_skill_turns: int
    """其中沒有任何主動技能可用的次數（``no_skill_mana`` ＋ ``no_skill_cooldown``）。"""
    no_skill_mana: int
    """沒有技能可用，且至少有一招是因為法力不足。"""
    no_skill_cooldown: int
    """沒有技能可用，且其餘是冷卻中（或每場次數用完）。"""
    damage_by_source: dict[str, int]
    """英雄的傷害來源：``basic``、``combo``、``cleave``、``mastery``、``skill:<id>``、``indirect``。"""
    crit_damage: int
    """英雄的暴擊命中傷害合計（與上面各欄重疊，只作參考）。"""
    attack_hits: int
    """英雄的普攻命中次數（含連擊多出的一下）。"""
    skill_uses: dict[str, tuple[int, int, int]]
    """技能 ID → （使用次數，命中判定涵蓋的敵人數合計，實際受傷的敵人數合計）。"""


class FlowTrace:
    """``run_battle(on_step=…)`` 的回呼：在英雄回合開始時判斷有沒有技能可用。"""

    def __init__(self, hero_template: str) -> None:
        self.hero_template = hero_template
        self.hero_turns = 0
        self.no_skill = 0
        self.no_skill_mana = 0
        self.no_skill_cooldown = 0

    def __call__(self, _step: object, result: ResolveResult) -> None:
        state = result.state
        for event in result.events:
            if isinstance(event, TurnStarted):
                unit = state.units.get(event.unit_id)
                if unit and unit.team is Team.ALLY and unit.template_id == self.hero_template:
                    self._inspect(state, unit)

    def _inspect(self, state: BattleState, hero: UnitState) -> None:
        if not hero.alive or not any(u.team is Team.ENEMY for u in state.living_units()):
            return
        self.hero_turns += 1
        problems: list[str | None] = []
        for sid in sorted(hero.all_skills):
            skill = acting_skill(state, hero, sid)
            if skill.is_actionable:
                problems.append(resource_problem(state, hero, skill))
        if any(p is None for p in problems):
            return
        self.no_skill += 1
        if any(p is not None and p.startswith("法力不足") for p in problems):
            self.no_skill_mana += 1
        else:
            self.no_skill_cooldown += 1


def hero_mastery_permille(setup: BattleSetup, hero_template: str, seed: int = 0) -> int:
    """英雄開場時，帶 ``empty_slots_cap`` 的普攻傷害加成合計（‰；沒有精通為 0）。"""
    state = begin_battle(setup, seed).state
    hero = next(
        u for u in state.units.values() if u.team is Team.ALLY and u.template_id == hero_template
    )
    empty = empty_active_slots(state, hero)
    total = 0
    for sid in hero.skills:
        for rule in state.ruleset.skill_def(sid).modifiers:
            cap = rule.empty_slots_cap
            if cap is None or "attack" not in rule.applies_to.actions:
                continue
            total += (rule.change.damage_permille or 0) * min(cap, empty)
    return total


class _Walker:
    """:func:`analyze_flow` 的逐事件累計。"""

    def __init__(
        self, hero_id: str, enemy_ids: frozenset[str], boss_ids: frozenset[str], mastery: int
    ) -> None:
        self.hero_id = hero_id
        self.enemy_ids = enemy_ids
        self.boss_ids = boss_ids
        self.mastery = mastery
        self.round = 0
        self.boss_round: int | None = None
        self.clear_round: int | None = None
        self.downed: set[str] = set()
        self.by_source: dict[str, int] = {}
        self.crit_damage = 0
        self.attack_hits = 0
        self.uses: dict[str, list[int]] = {}
        self.pending_cleave = False
        self.combo: str | None = None  # None／"roll"（等命中判定）／"hit"（下一筆傷害是連擊）
        self.skill_id: str | None = None
        self.hit_targets: set[str] = set()
        self.covered: set[str] = set()

    def add(self, key: str, amount: int) -> None:
        self.by_source[key] = self.by_source.get(key, 0) + amount

    def begin_step(self) -> None:
        self.skill_id = None
        self.hit_targets = set()
        self.covered = set()

    def end_step(self) -> None:
        if self.skill_id is not None:
            self.uses[self.skill_id][1] += len(self.covered)
            self.uses[self.skill_id][2] += len(self.hit_targets)

    def event(self, event: EventBase) -> None:
        if isinstance(event, RoundStarted):
            self.round += 1
        elif isinstance(event, UnitDowned):
            self._downed(event)
        elif isinstance(event, SkillUsed):
            if event.unit_id == self.hero_id and self.skill_id is None:
                self.skill_id = event.skill_id
                self.uses.setdefault(event.skill_id, [0, 0, 0])[0] += 1
        elif isinstance(event, GearTriggered):
            self._gear(event)
        elif isinstance(event, AttackRolled) and event.attacker_id == self.hero_id:
            if self.combo == "roll":
                self.combo = "hit" if event.hit else None
            if self.skill_id is not None and event.target_id in self.enemy_ids:
                self.covered.add(event.target_id)
        elif (
            isinstance(event, DamageDealt)
            and event.source_id == self.hero_id
            and event.target_id in self.enemy_ids
        ):
            self._damage(event)

    def _downed(self, event: UnitDowned) -> None:
        if event.unit_id not in self.enemy_ids:
            return
        self.downed.add(event.unit_id)
        if event.unit_id in self.boss_ids and self.boss_round is None:
            self.boss_round = max(1, self.round)
        if self.downed >= self.enemy_ids and self.clear_round is None:
            self.clear_round = max(1, self.round)

    def _gear(self, event: GearTriggered) -> None:
        if event.unit_id != self.hero_id:
            return
        if event.trigger == STRIKE_CLEAVE:
            self.pending_cleave = True
        elif event.trigger == STRIKE_COMBO:
            self.combo = "roll"

    def _damage(self, event: DamageDealt) -> None:
        dealt = event.hp_before - event.hp_after
        if event.cause != "attack":
            self.add("indirect", dealt)
            if self.skill_id is not None:
                self.hit_targets.add(event.target_id)
        elif self.skill_id is not None:
            self.add(f"skill:{self.skill_id}", dealt)
            self.hit_targets.add(event.target_id)
        elif self.pending_cleave:
            self.pending_cleave = False
            self.add("cleave", dealt)
        else:
            key = "basic"
            if self.combo == "hit":
                self.combo = None
                key = "combo"
            mastery = dealt * self.mastery // (_PERMILLE + self.mastery)
            self.add("mastery", mastery)
            self.add(key, dealt - mastery)
            self.attack_hits += 1
            if event.crit:
                self.crit_damage += dealt


def analyze_flow(
    events: Sequence[EventBase],
    bounds: Sequence[int],
    *,
    hero_id: str,
    enemy_ids: frozenset[str],
    boss_ids: frozenset[str],
    mastery_permille: int,
    trace: FlowTrace,
) -> FlowExtras:
    """由事件推導 :class:`FlowExtras`（``bounds`` 是 ``StepTrace.bounds``）。"""
    walker = _Walker(hero_id, enemy_ids, boss_ids, mastery_permille)
    edges = [0, *bounds]
    for lo, hi in pairwise(edges):
        walker.begin_step()
        for event in events[lo:hi]:
            walker.event(event)
        walker.end_step()
    return FlowExtras(
        has_boss=bool(boss_ids),
        boss_kill_round=walker.boss_round,
        clear_round=walker.clear_round,
        hero_turns=trace.hero_turns,
        no_skill_turns=trace.no_skill,
        no_skill_mana=trace.no_skill_mana,
        no_skill_cooldown=trace.no_skill_cooldown,
        damage_by_source=dict(sorted(walker.by_source.items())),
        crit_damage=walker.crit_damage,
        attack_hits=walker.attack_hits,
        skill_uses={k: (v[0], v[1], v[2]) for k, v in sorted(walker.uses.items())},
    )
