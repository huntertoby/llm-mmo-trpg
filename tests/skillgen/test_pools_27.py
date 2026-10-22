"""關鍵字池補齊第二批與挑釁怒吼（Phase 3-27，``docs/phases/Phase3計畫.md`` 29 節）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_setup
from tests.engine.test_weapons_24a2 import armed, dice, foe, kinds, weapon
from trpg.engine import BattleState, UseSkill, resolve, start_battle
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId
from trpg.skillgen.keywords import derive_keywords, is_starter_skill
from trpg.skillgen.validate import validate_skill

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")

KEYWORDS = (
    "ignite",
    "wet",
    "charged",
    "frozen",
    "prone",
    "collision",
    "marked",
    "high_ground",
    "concealed",
    "summon",
)

# 技能 -> (武器, 關鍵字池, 讓條件成立的布置)
NEW_SKILLS: dict[str, tuple[str, str, str]] = {
    "trample": ("one_handed_sword", "prone", "prone"),
    "ground_finish": ("one_handed_sword", "prone", "prone"),
    "gravity_crush": ("lightning_staff", "prone", "prone"),
    "tide_cleave": ("one_handed_sword", "wet", "water"),
    "ripple_shot": ("bow", "wet", "water"),
    "hunters_strike": ("one_handed_sword", "marked", "marked"),
    "pinpoint_shot": ("bow", "marked", "marked"),
    "plunging_strike": ("one_handed_sword", "high_ground", "high"),
    "downdraft": ("one_handed_sword", "high_ground", "high"),
    "pinning_shot": ("bow", "collision", "collided"),
    "veiled_shot": ("bow", "concealed", "self_concealed"),
    "glacier_offering": ("one_handed_sword", "summon", ""),
}


def _users(keyword: str, *, starter: bool) -> list[str]:
    lib = library()
    return [
        sid
        for sid, skill in sorted(lib.skills.items())
        if skill.kind == "active"
        and (not starter or is_starter_skill(skill))
        and keyword in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    ]


@pytest.mark.parametrize("keyword", KEYWORDS)
def test_every_pool_has_three_exclusive_active_exploiters(keyword: str) -> None:
    assert len(_users(keyword, starter=True)) >= 3
    assert len(_users(keyword, starter=False)) >= 3


@pytest.mark.parametrize("name", sorted(NEW_SKILLS))
def test_every_new_skill_passes_validation_and_budget(name: str) -> None:
    lib = library()
    skill = lib.skills[f"skill_{name}"]
    assert validate_skill(skill, lib) == []
    assert skill.tier == 1 and skill.kind == "active" and is_starter_skill(skill)
    _, pool, _ = NEW_SKILLS[name]
    assert pool in derive_keywords(skill, lib.keywords, exclusive_only=True).uses


def test_taunting_roar_is_ap_1_cooldown_2_and_still_marks() -> None:
    lib = library()
    roar = lib.skills["skill_taunting_roar"]
    assert roar.ap_cost == 1 and roar.cost.cooldown == 2
    marked = [e for e in roar.effects if e.type == "apply_status" and e.status == "marked"]
    assert len(marked) == 1 and marked[0].duration == 1
    assert validate_skill(roar, lib) == []
    assert "marked" in derive_keywords(roar, lib.keywords, exclusive_only=True).makes


_HEIGHTS = "\n".join(["000000000"] * 5)
_HIGH = "\n".join(["110000000"] * 5)


def _scene(name: str, setup: str, *, lit: bool) -> BattleState:
    weapon_id, _, _ = NEW_SKILLS[name]
    ranged = weapon_id == "bow"
    caster = weapon_id == "lightning_staff"
    skill = f"skill_{name}"
    attacker_at, foe_at = ((1, 2), (4, 2)) if ranged else ((1, 2), (2, 2))
    hero = "hero_archer" if ranged else ("hero_mage" if caster else "hero_fighter")
    surfaces = [(*foe_at, "water")] if lit and setup == "water" else []
    heights = _HIGH if lit and setup == "high" else _HEIGHTS
    m = make_map(heights, None, ally=[attacker_at], enemy=[foe_at], surfaces=surfaces)
    spawns = [
        armed(Team.ALLY, attacker_at, weapon(weapon_id), base=hero, skills=[skill]),
        foe(foe_at),
    ]
    state = give_turn(start_battle(make_setup(m, spawns), 0), U1)
    state.units[U1].mana = 99
    if lit and setup in ("prone", "marked"):
        state.units[U2].statuses = [StatusInstance(status_id=setup, remaining=3, source_id=None)]
    if lit and setup == "collided":
        state.units[U2].collided_round = state.round
    if lit and setup == "self_concealed":
        state.units[U1].statuses = [StatusInstance(status_id="concealed", remaining=3)]
    return state


def _damage(state: BattleState, name: str) -> int:
    res = resolve(state, UseSkill(unit_id=U1, skill_id=f"skill_{name}", target_id=U2))
    return sum(e.amount for e in kinds(res.events, DamageDealt))


@pytest.mark.parametrize("name", [n for n, v in sorted(NEW_SKILLS.items()) if v[2]])
def test_the_bonus_only_applies_when_the_condition_holds(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch, d20=19, die=3)
    _, _, setup = NEW_SKILLS[name]
    plain = _damage(_scene(name, setup, lit=False), name)
    lit = _damage(_scene(name, setup, lit=True), name)
    assert plain > 0 and lit > plain


@pytest.mark.parametrize("name", [n for n, v in sorted(NEW_SKILLS.items()) if v[2]])
def test_the_ai_scores_the_new_skill_best_when_the_condition_holds(name: str) -> None:
    """條件成立時，技能是（不含瞄準這種準備動作的）最高分動作。"""
    state = _scene(name, NEW_SKILLS[name][2], lit=True)
    ranked = UtilityAI(library().ai_profiles).rank(state)
    best = max((s for s in ranked if s.action.type != "aim"), key=lambda s: s.score)
    assert isinstance(best.action, UseSkill) and best.action.skill_id == f"skill_{name}"
