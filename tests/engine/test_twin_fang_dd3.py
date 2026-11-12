"""DD-3：雙牙改成「兩下都咬中就中毒」（#158，``docs/design/08-裝備.md`` 8.11）。

每列一條規則句、實際跑引擎（正式內容的 ``skill_twin_fang``）：只剩一個傷害效果；拿雙匕首、兩下都
命中同一個目標時，第二下命中之後上「中毒」一次；第一下就打倒、任一下沒中、任一下被守護者攔下、沒拿
雙匕首都不成立。條件 ``all_strikes_hit`` 只能寫在效果上、不在 ``any_of`` 裡、LLM 提議與新技能
（非內建）不能用。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3
from tests.engine.test_dual_dagger_skills_dd1 import HIT, MISS, d20s, mine, rolls
from tests.engine.test_intercept import scene
from tests.engine.test_passive_triggers import always
from trpg.content.library import skill_reference_problems
from trpg.content.loader import parse_yaml
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import BattleState, preview, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.events import (
    AttackIntercepted,
    DamageDealt,
    EventBase,
    StatusApplied,
    StatusSaveRolled,
)
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.shared.types import Team

FANG = "skill_twin_fang"


def fang() -> SkillDef:
    return library().skills[FANG]


def duel(weapon: str = "dual_dagger", foe_hp: int = 300) -> BattleState:
    """U1（拿 ``weapon``、裝備雙牙）在 (3, 3)，U2 在 (4, 3)。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    hero = caster_template([FANG], base="hero_fighter")
    foe = no_reactions(max_hp=foe_hp, resist={})
    state = make_state(
        m, [spawn(Team.ALLY, (3, 3), hero, weapon, skills=None), spawn(Team.ENEMY, (4, 3), foe)]
    )
    state = give_turn(state, U1)
    state.units[U1].stamina = 99
    return state


def bite(state: BattleState) -> list[EventBase]:
    return resolve(state, UseSkill(unit_id=U1, skill_id=FANG, target_id=U2)).events


def poison_saves(events: Sequence[EventBase]) -> list[StatusSaveRolled]:
    return [e for e in events if isinstance(e, StatusSaveRolled) and e.status_id == "poison"]


def test_twin_fang_keeps_one_damage_effect_and_a_conditioned_poison() -> None:
    skill = fang()
    assert [e.type for e in skill.effects] == ["damage", "apply_status"]
    poison = skill.effects[1]
    assert poison.status == "poison" and poison.condition is not None
    assert poison.condition.type == "all_strikes_hit"
    raw = parse_yaml((library().root / "skills" / f"{FANG}.yaml").read_text(encoding="utf-8"))
    assert poison.duration == raw["effects"][1]["duration"]  # 數值工坊調的值，讀現值


CASES = [
    # (說明, d20 序列, 擲中毒抵抗次數)
    ("兩下都中：中毒一次", [HIT, HIT], 1),
    ("第一下中、第二下沒中：不中毒", [HIT, MISS], 0),
    ("第一下沒中、第二下中：不中毒", [MISS, HIT], 0),
    ("兩下都沒中：不中毒", [MISS, MISS], 0),
]


@pytest.mark.parametrize(("name", "seq", "times"), CASES)
def test_poison_needs_both_strikes_to_hit(
    name: str, seq: list[int], times: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel()
    d20s(monkeypatch, seq, rest=20)  # 抵抗判定擲 20：施加成功
    events = bite(state)
    assert [r.hit for r in rolls(events)] == [s == HIT for s in seq], name
    saves = poison_saves(events)
    assert len(saves) == times, name
    if times:
        last_damage = mine(events, DamageDealt)[-1]
        assert last_damage.seq < saves[0].seq  # 第二下命中之後才結算
        applied = [e for e in events if isinstance(e, StatusApplied) and e.status_id == "poison"]
        assert len(applied) == 1 and applied[0].target_id == U2


def test_no_poison_when_the_first_strike_kills(monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(foe_hp=1)
    d20s(monkeypatch, [HIT, HIT], rest=1)
    events = bite(state)
    assert len(rolls(events)) == 1 and poison_saves(events) == []


@pytest.mark.parametrize("weapon", ["dagger", "one_handed_sword"])
def test_no_poison_without_dual_daggers(weapon: str, monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(weapon)
    d20s(monkeypatch, [HIT, HIT], rest=1)
    events = bite(state)
    assert len(rolls(events)) == 1 and poison_saves(events) == []


def test_no_poison_when_a_guardian_steps_in(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(attacker_skills=(FANG,))
    state.units[U1].weapon = library().weapons["dual_dagger"]
    state.units[U1].stamina = 99
    events = resolve(state, UseSkill(unit_id=U1, skill_id=FANG, target_id=U2)).events
    assert any(isinstance(e, AttackIntercepted) for e in events)
    assert poison_saves(events) == []
    assert all(r.target_id == U3 for r in rolls(events)[1:])  # 之後幾下打守護者


def test_the_max_preview_shows_the_poison_and_the_min_preview_does_not() -> None:
    view = preview(duel(), UseSkill(unit_id=U1, skill_id=FANG, target_id=U2))
    assert poison_saves(list(view.max_events))
    assert not poison_saves(list(view.min_events))


def test_the_condition_never_holds_outside_a_cast() -> None:
    state = duel()
    spec = ConditionSpec(type="all_strikes_hit")
    target = state.units[U2]
    assert not condition_met(state, state.units[U1], spec, Subject(target, target.xy))


def test_all_strikes_hit_only_goes_on_an_effect() -> None:
    lib = library()

    def problems(skill: SkillDef) -> list[str]:
        return skill_reference_problems(skill, lib.ruleset, lib.skills)

    skill = fang()
    assert problems(skill) == []
    outer = skill.model_copy(update={"condition": ConditionSpec(type="all_strikes_hit")})
    assert any("只能寫在效果的 condition" in p for p in problems(outer))
    either = ConditionSpec(
        type="wielding_weapon",
        weapon="dual_dagger",
        any_of=(ConditionSpec(type="all_strikes_hit"),),
    )
    effects = (skill.effects[0], skill.effects[1].model_copy(update={"condition": either}))
    mixed = skill.model_copy(update={"effects": effects})
    assert any("any_of" in p for p in problems(mixed))
