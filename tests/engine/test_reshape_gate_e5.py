"""裝備授予的行為改寫的預算閘門與彈射（E5，玩法交接 4.1.36 待決答覆 2；08 8.29 E5 第 1、2 點）。

測試內容：兩個只給測試用的修正技——彈射（``shape_to: chain``，套在所有技能）與普攻直線
（``attack_shape: line``），各配一條授予它的第 9 類詞條（複製 ``affix_act_grapple``）。
現有內容沒有裝備授予的變形修正技，所以閘門表是空的（另有測試鎖住）。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import give_turn, library, make_map, no_reactions, spawn
from tests.engine.skill_helpers import script_rolls
from tests.engine.test_gear_skills_e1 import loadout
from trpg.content.equipment import ActionAffix
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, legal_actions, preview, resolve, start_battle
from trpg.engine.attack_shapes import attack_shape_state
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.engine.modifiers import (
    ATTACK,
    ActiveRule,
    damage_permille,
    reshaped_skill,
    shaped_skill,
    skill_use,
)
from trpg.engine.reshape_gate import GATE_PROBLEM_ZH, gate_key
from trpg.engine.setup import BattleSetup
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import state_to_json
from trpg.engine.view import project_for
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.reshape_gate import (
    attack_gate_permille,
    gate_library,
    gate_ruleset,
    reshape_gates,
)

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
BOUNCE, LINE = "skill_t_bounce", "skill_t_line"
STRIKE = "skill_palm_strike"  # 單體近戰武器技：傷害 700‰＋自己累積氣（閘門會降傷）
PUSHY = "skill_gale_kick"  # 單體近戰：傷害 400‰＋推 2 格（推擊點數多，降到最低還超過）
ROW = "\n".join(["00000"] * 3)


def _modifier(skill_id: str, change: dict[str, Any], target: dict[str, Any]) -> SkillDef:
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    data.update(id=skill_id, name_zh=skill_id, modifiers=[{"applies_to": target, "change": change}])
    return SkillDef.model_validate(data)


MODS = (
    _modifier(BOUNCE, {"shape_to": "chain"}, {"all_skills": True}),
    _modifier(LINE, {"attack_shape": "line"}, {"actions": ["attack"]}),
)


def gear_library(*, min_permille: int | None = None, gated: bool = True) -> ContentLibrary:
    """內容庫＋兩個測試修正技與授予它們的詞條（``gated``：規則包填好閘門表）。"""
    lib = library()
    base = lib.affixes["affix_act_grapple"]
    assert isinstance(base, ActionAffix)
    affixes = dict(lib.affixes)
    for mod in MODS:
        affixes[f"affix_t_{mod.id}"] = base.model_copy(
            update={"id": f"affix_t_{mod.id}", "skill": mod.id}
        )
    budget = lib.budget
    if min_permille is not None:
        modifier = budget.modifier.model_copy(update={"reshape_gate_min_permille": min_permille})
        budget = budget.model_copy(update={"modifier": modifier})
    out = dataclasses.replace(
        lib,
        skills={**lib.skills, **{m.id: m for m in MODS}},
        affixes=affixes,
        budget=budget,
        ruleset=lib.ruleset.with_skills(MODS),
    )
    return gate_library(out) if gated else out


def scene(
    lib: ContentLibrary,
    *,
    gear: Sequence[str] = (BOUNCE,),
    learned: Sequence[str] = (),
    skills: Sequence[str] = (STRIKE,),
    weapon: str | None = None,
    foes: Sequence[tuple[int, int]] = ((1, 1), (2, 1)),
) -> BattleState:
    """主角 U1 在 (0, 1)：身體裝備授予 ``gear``，自己學了 ``learned`` 與 ``skills``。"""
    tmpl = no_reactions("hero_fighter", skills=(*skills, *learned))
    hero = spawn(Team.ALLY, (0, 1), tmpl, weapon)
    tmpl = hero.template.model_copy(update={"skills": (*skills, *learned)})
    hero = hero.model_copy(update={"template": tmpl, "equipment": loadout({"body": list(gear)})})
    spawns = [hero, *(spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=999)) for xy in foes)]
    m = make_map(ROW, ally=[(0, 1)], enemy=list(foes))
    setup = BattleSetup(map=m, ruleset=lib.ruleset, units=tuple(spawns))
    return give_turn(start_battle(setup, 0), U1)


def strike(state: BattleState, skill: str = STRIKE) -> UseSkill:
    return UseSkill(unit_id=U1, skill_id=skill, target_id=U2)


def gear_view(state: BattleState, key: str) -> Any:
    me = next(u for u in project_for(state, Team.ALLY).units if u.id == U1)
    return next(g for g in me.gear_skills if g.skill_id == key)


# ---------------------------------------------------------------------------
# 表本身
# ---------------------------------------------------------------------------


def test_real_content_has_no_gear_reshape_and_an_empty_table() -> None:
    lib = library()
    assert reshape_gates(lib.ruleset, lib) == {}
    assert gate_ruleset(lib.ruleset, lib) is lib.ruleset
    assert gate_library(lib) is lib
    assert "reshape_gates" not in lib.ruleset.model_dump(mode="json")


def test_gate_lowers_damage_to_just_fit_the_original_budget() -> None:
    lib = gear_library()
    p = lib.ruleset.reshape_gates[gate_key(BOUNCE, STRIKE)]
    assert lib.budget.modifier.reshape_gate_min_permille <= p < 1000
    skill = lib.ruleset.skill_def(STRIKE)
    rules = [ActiveRule(MODS[0], 0, MODS[0].modifiers[0])]
    chain = reshaped_skill(lib.ruleset, skill, rules, lib.budget.range_baseline)
    assert chain.shape.type == "chain"
    before = skill_budget(skill, lib).total
    after = skill_budget(chain, lib)
    damage = (
        after.total
        * sum((e.points for e in after.effects if e.type == "damage"), Fraction(0))
        / after.raw
    )
    assert after.total > before
    fits = after.total - damage * (1000 - p) / 1000
    one_more = after.total - damage * (1000 - (p + 1)) / 1000
    assert fits <= before < one_more  # p 是剛好不超過的最大整數


def test_gate_blocks_when_even_the_minimum_is_over() -> None:
    lib = gear_library()
    assert lib.ruleset.reshape_gates[gate_key(BOUNCE, PUSHY)] == 0
    tight = gear_library(min_permille=900)
    assert tight.ruleset.reshape_gates[gate_key(BOUNCE, STRIKE)] == 0  # 841 < 900


def test_attack_uses_the_basic_attack_reference() -> None:
    lib = gear_library()
    assert lib.ruleset.reshape_gates[gate_key(LINE, "attack")] == attack_gate_permille(lib)
    assert 500 <= attack_gate_permille(lib) < 1000


# ---------------------------------------------------------------------------
# 引擎：裝備授予的才過閘門
# ---------------------------------------------------------------------------


def test_gear_bounce_reduces_damage_and_keeps_the_chain() -> None:
    lib = gear_library()
    state = scene(lib)
    me = state.units[U1]
    chain = shaped_skill(state, me, lib.ruleset.skill_def(STRIKE))
    assert chain.shape.type == "chain"
    p = lib.ruleset.reshape_gates[gate_key(BOUNCE, STRIKE)]
    subject = Subject(state.units[U2], state.units[U2].xy)
    assert damage_permille(state, me, skill_use(chain), subject) == p
    assert damage_permille(state, me, ATTACK, subject) == 1000  # 普攻不受彈射影響
    assert gear_view(state, BOUNCE).off_zh is None


def test_gate_blocked_skill_is_not_reshaped_and_is_greyed() -> None:
    lib = gear_library()
    state = scene(lib, skills=(PUSHY,))
    me = state.units[U1]
    assert shaped_skill(state, me, lib.ruleset.skill_def(PUSHY)).shape.type == "single"
    view = gear_view(state, BOUNCE)
    assert view.off_zh == GATE_PROBLEM_ZH and view.note_zh is None
    both = scene(lib, skills=(STRIKE, PUSHY))
    view = gear_view(both, BOUNCE)
    assert view.off_zh is None
    assert view.note_zh == f"{GATE_PROBLEM_ZH}：{lib.ruleset.skill_def(PUSHY).name_zh}"


def test_missing_table_entry_counts_as_blocked() -> None:
    lib = gear_library(gated=False)  # 沒經過 gate_ruleset：表是空的
    state = scene(lib)
    assert (
        shaped_skill(state, state.units[U1], lib.ruleset.skill_def(STRIKE)).shape.type == "single"
    )
    assert gear_view(state, BOUNCE).off_zh == GATE_PROBLEM_ZH
    line = scene(lib, gear=(LINE,))
    shaped = attack_shape_state(line, line.units[U1])
    assert shaped.shape is None and shaped.problem == "gate"
    assert gear_view(line, LINE).off_zh == GATE_PROBLEM_ZH


def test_learned_modifier_skips_the_gate() -> None:
    """自己學的修正技（不是裝備授予）不過閘門：表是空的也照樣變形、不降傷。"""
    lib = gear_library(gated=False)
    state = scene(lib, gear=(), learned=(BOUNCE,))
    me = state.units[U1]
    chain = shaped_skill(state, me, lib.ruleset.skill_def(STRIKE))
    assert chain.shape.type == "chain"
    subject = Subject(state.units[U2], state.units[U2].xy)
    assert damage_permille(state, me, skill_use(chain), subject) == 1000


def test_gear_line_attack_takes_the_attack_gate() -> None:
    lib = gear_library()
    state = scene(lib, gear=(LINE,))
    shaped = attack_shape_state(state, state.units[U1])
    assert shaped.shape == "line"
    assert shaped.damage_permille == lib.ruleset.reshape_gates[gate_key(LINE, "attack")]
    blocked = scene(gear_library(min_permille=900), gear=(LINE,))
    assert attack_shape_state(blocked, blocked.units[U1]).problem == "gate"
    assert gear_view(blocked, LINE).off_zh == GATE_PROBLEM_ZH


# ---------------------------------------------------------------------------
# 彈射（08 8.29 E5 第 1 點）：照現有連鎖
# ---------------------------------------------------------------------------


def _second_hit(monkeypatch: pytest.MonkeyPatch, state: BattleState) -> list[DamageDealt]:
    action = strike(state)
    assert action in legal_actions(state)
    with monkeypatch.context() as m:
        script_rolls(m, [2, 19] + [1] * 30)  # 第一下沒中、第二下命中，傷害骰全 1
        result = resolve(state, action)
    rolled = [(e.target_id, e.hit) for e in result.events if isinstance(e, AttackRolled)]
    assert rolled == [(U2, False), (U3, True)]  # 第一下沒中照樣跳
    return [e for e in result.events if isinstance(e, DamageDealt) and e.source_id == U1]


def test_bounce_jumps_even_when_the_first_hit_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    lib = gear_library()
    gear = _second_hit(monkeypatch, scene(lib))
    learned = _second_hit(monkeypatch, scene(gear_library(gated=False), gear=(), learned=(BOUNCE,)))
    assert [e.target_id for e in gear] == [e.target_id for e in learned] == [U3]
    p = lib.ruleset.reshape_gates[gate_key(BOUNCE, STRIKE)]
    # 第二下照連鎖 75%（自己學的版本），裝備授予的再乘閘門的降傷
    assert abs(gear[0].multiplier_permille - learned[0].multiplier_permille * p // 1000) <= 1
    assert gear[0].multiplier_permille < learned[0].multiplier_permille


def test_bounce_preview_shows_the_chain() -> None:
    lib = gear_library()
    state = scene(lib)
    shown = preview(state, strike(state))
    assert {U2, U3} <= set(shown.affected_units)


def test_same_seed_same_result() -> None:
    lib = gear_library()
    state = scene(lib)
    first, second = resolve(state, strike(state)), resolve(state, strike(state))
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    assert state_to_json(first.state) == state_to_json(second.state)
