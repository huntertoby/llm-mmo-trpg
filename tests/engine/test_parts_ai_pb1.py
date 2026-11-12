"""PB-1b：頭目部位的 AI（``PhasePB-1計畫.md`` 第 5 節；R8、R9、T13；05 5.12.2 第 11 點）。

隊友與影子照破壞效果的價值挑部位（能封下一招或能打斷蓄力時優先），否則打本體；同分本體優先；召喚物
不打部位；頭目背後部位快破時「背對攻擊者」多扣分；沒有部位的場面候選清單逐字不變。實際跑效用 AI。
"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import give_turn, library, make_map, make_setup, spawn, template
from trpg.content.battle import UnitTemplate
from trpg.content.environment import AiProfileTable, PartAiRules
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, legal_actions
from trpg.engine.actions import Attack, UseSkill
from trpg.engine.ai.parts import guard_back_extra, part_score, picks_parts
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.ai.utility.position import position_value
from trpg.engine.battle import start_battle
from trpg.engine.events import PartDamaged
from trpg.engine.preview import preview
from trpg.engine.setup import with_phase_assets
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId

HERO = UnitId("unit_0001")
MASTER = UnitId("unit_0002")
MASTER_ID = "sect_mist_lock_master"
FLAT = "\n".join(["0000000"] * 7)
PHASE = {"sword_array": 0, "mist_lock": 1, "return_to_one": 2}


def master(**overrides: object) -> UnitTemplate:
    return template(MASTER_ID, reactions=(), **overrides)


def arena(
    hero_at: tuple[int, int] = (2, 3),
    *,
    phase: str = "sword_array",
    hero: str = "hero_fighter",
    boss: UnitTemplate | None = None,
    second: tuple[int, int] | None = None,
) -> BattleState:
    lib = library()
    extra = [] if second is None else [second]
    setup = make_setup(
        make_map(FLAT, ally=[hero_at, *extra], enemy=[(3, 3)]),
        [
            spawn(Team.ALLY, hero_at, template(hero, reactions=())),
            spawn(Team.ENEMY, (3, 3), boss or master(max_hp=120)),
            *(spawn(Team.ALLY, xy, template(hero, reactions=())) for xy in extra),
        ],
    )
    state = give_turn(start_battle(with_phase_assets(lib, setup), 0), HERO)
    state.units[MASTER].facing = "west"
    state.units[MASTER].phase_index = PHASE[phase]
    return state


def ai(**parts: int) -> UtilityAI:
    table = library().ai_profiles
    if parts:
        rules = table.parts.model_copy(update=parts)
        table = table.model_copy(update={"parts": rules})
    return UtilityAI(table, override="brute")


def attacks(state: BattleState, policy: UtilityAI) -> list[tuple[str | None, Fraction]]:
    """``rank`` 裡對真人的普攻（本體與部位變體）依清單順序。"""
    return [
        (s.action.target_part, s.score)
        for s in policy.rank(state)
        if isinstance(s.action, Attack) and s.action.target_id == MASTER
    ]


def test_the_value_table_has_placeholder_values() -> None:
    rules = library().ai_profiles.parts
    assert rules == PartAiRules(
        seal_skill=8,
        interrupt_charge=10,
        stat_down=4,
        control=6,
        stop_mechanic=8,
        priority_bonus=6,
        guard_back_bonus=3,
        near_break_permille=500,
    )
    brute = library().ai_profiles.by_id()["brute"].weights
    assert (brute.guard_back_bonus, brute.near_break_permille) == (3, 500)


def test_variants_follow_the_body_in_part_id_order() -> None:
    state = arena((4, 3), phase="return_to_one")
    assert [p for p, _ in attacks(state, ai())] == [None, "dantian", "sword", "whisk"]


def test_a_charging_boss_makes_the_sword_the_pick_when_it_can_break() -> None:
    state = arena(phase="return_to_one")
    boss = state.units[MASTER]
    boss.statuses.append(StatusInstance(status_id=CHARGING, skill_id="skill_charged_cleave"))
    boss.part_hp["sword"] = 1
    choice = ai()(state)
    assert isinstance(choice, Attack | UseSkill)
    assert (choice.target_id, choice.target_part) == (MASTER, "sword")


def test_a_nearly_broken_whisk_is_picked_while_mist_shift_is_ready() -> None:
    state = arena(phase="mist_lock")
    boss = state.units[MASTER]
    boss.part_hp["whisk"] = 1
    assert "skill_mist_shift" in boss.skills
    boss.mana = 99
    choice = ai()(state)
    assert isinstance(choice, Attack | UseSkill)
    assert (choice.target_id, choice.target_part) == (MASTER, "whisk")


def test_priority_needs_the_next_skill_or_a_charge() -> None:
    state = arena(phase="mist_lock")
    boss = state.units[MASTER]
    boss.part_hp["whisk"] = 1
    boss.mana = 99
    rules = library().ai_profiles.parts
    action = Attack(unit_id=HERO, target_id=MASTER, target_part="whisk")
    p = preview(state, action)
    ready = part_score(state, action, p.min_events, p.max_events, rules)
    assert ready == rules.seal_skill + rules.priority_bonus
    boss.cooldowns["skill_mist_shift"] = 2  # 冷卻中：不是「下一招」，只剩價值 × 進度
    p = preview(state, action)
    assert part_score(state, action, p.min_events, p.max_events, rules) == rules.seal_skill


def test_progress_is_part_damage_over_remaining_hp() -> None:
    state = arena(phase="mist_lock")
    rules = library().ai_profiles.parts
    action = Attack(unit_id=HERO, target_id=MASTER, target_part="whisk")
    p = preview(state, action)
    remaining = state.units[MASTER].part_hp["whisk"]
    dealt = sum(e.amount for e in p.min_events if isinstance(e, PartDamaged))
    assert 0 < dealt < remaining
    expected = rules.seal_skill * Fraction(dealt, remaining)
    assert part_score(state, action, p.min_events, p.max_events, rules) == expected


def test_no_reachable_part_means_the_body() -> None:
    state = arena(phase="sword_array")  # 劍陣：只露出拂塵
    state.units[MASTER].broken_parts = ("whisk",)
    assert [p for p, _ in attacks(state, ai())] == [None]
    choice = ai()(state)
    assert getattr(choice, "target_part", None) is None


def test_ties_keep_the_body() -> None:
    state = arena(phase="return_to_one")
    zero = ai(seal_skill=0, interrupt_charge=0, stat_down=0, stop_mechanic=0, priority_bonus=0)
    ranked = attacks(state, zero)
    body = ranked[0]
    assert body[0] is None
    assert any(part is not None and score == body[1] for part, score in ranked[1:])
    choice = zero(state)
    assert getattr(choice, "target_part", None) is None


def test_summons_and_enemies_never_pick_parts() -> None:
    state = arena()
    assert picks_parts(state, state.units[HERO])
    state.units[HERO].owner_id = MASTER  # 召喚物（R9）
    assert not picks_parts(state, state.units[HERO])
    assert not picks_parts(state, state.units[MASTER])


def test_the_boss_guards_its_back_when_the_dantian_is_nearly_broken() -> None:
    # 真人面向最近的英雄（西邊的 unit_0001），另一名近戰英雄站在他背後（東邊）
    state = arena((2, 3), phase="return_to_one", second=(4, 3))
    weights = ai().profile_for(state.units[MASTER]).weights
    boss = state.units[MASTER]
    full = position_value(state, MASTER, weights)
    assert guard_back_extra(boss, weights) == 0
    boss.part_hp["dantian"] = boss.part_hp["dantian"] // 2
    assert guard_back_extra(boss, weights) == weights.guard_back_bonus
    assert position_value(state, MASTER, weights) == full - weights.guard_back_bonus
    boss.broken_parts = ("dantian",)
    assert guard_back_extra(boss, weights) == 0


def test_the_ai_is_deterministic_with_parts() -> None:
    state = arena(phase="return_to_one")
    state.units[MASTER].part_hp["sword"] = 3
    first = [(s.action, s.score) for s in ai().rank(state)]
    second = [(s.action, s.score) for s in ai().rank(state.clone())]
    assert first == second


def test_scenes_without_parts_rank_exactly_as_before() -> None:
    lib = library()
    setup = make_setup(
        make_map(FLAT, ally=[(2, 3)], enemy=[(3, 3)]),
        [
            spawn(Team.ALLY, (2, 3), template("hero_fighter", reactions=())),
            spawn(Team.ENEMY, (3, 3), template("bandit", reactions=())),
        ],
    )
    state = give_turn(start_battle(with_phase_assets(lib, setup), 0), HERO)
    legal = legal_actions(state)
    ranked = ai().rank(state)
    assert all(s.action in legal and getattr(s.action, "target_part", None) is None for s in ranked)
    table = lib.ai_profiles
    off = table.model_copy(update={"parts": PartAiRules.model_validate({})})
    assert isinstance(off, AiProfileTable)
    other = UtilityAI(off, override="brute").rank(state)
    assert [(s.action, s.score) for s in ranked] == [(s.action, s.score) for s in other]
