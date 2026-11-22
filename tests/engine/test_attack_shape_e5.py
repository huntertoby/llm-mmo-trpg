"""普攻變 2 格直線（E5，#175，08 8.29 E5 第 3～6 點；``attack_shape: line``）。

用測試內容：修正技 ``skill_t_line``（普攻變形，可再加一條普攻改火元素）。內容裡沒有人用
``attack_shape``，所以現有戰鬥不受影響（另由不變比對證明）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_setup, no_reactions, spawn
from tests.engine.test_gear_g2 import _spawn
from tests.engine.test_gear_skills_e1 import loadout
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, preview, resolve, start_battle
from trpg.engine.attack_shapes import (
    WEAPON_PROBLEM_ZH,
    attack_line_tiles,
    attack_shape_state,
    suits_line,
)
from trpg.engine.context import Ctx
from trpg.engine.events import AttackRolled, DamageDealt, EventBase, GearTriggered
from trpg.engine.reactions import perform_unit_attack
from trpg.engine.reshape_gate import gate_key
from trpg.engine.state import state_to_json
from trpg.engine.view import project_for
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Team, UnitId
from trpg.skillgen.budget import skill_budget

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
LINE_SKILL = "skill_t_line"
ROW = "\n".join(["00000"] * 3)


def line_skill(*, fire: bool = False, skill_id: str = LINE_SKILL) -> SkillDef:
    """測試用修正技：普攻變 2 格直線（``fire``：再加一條普攻改成火元素）。"""
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    rules: list[dict[str, Any]] = [
        {"applies_to": {"actions": ["attack"]}, "change": {"attack_shape": "line"}}
    ]
    if fire:
        rules.append({"applies_to": {"actions": ["attack"]}, "change": {"add_element": "fire"}})
    data.update(id=skill_id, name_zh="測試直線", modifiers=rules)
    return SkillDef.model_validate(data)


def scene(
    foes: Sequence[tuple[int, int]],
    *,
    weapon: str | None = None,
    allies: Sequence[tuple[int, int]] = (),
    gear: Mapping[str, list[tuple[str, int | None]]] | None = None,
    extra_skills: Sequence[str] = (),
    fire: bool = False,
    seed: int = 0,
) -> BattleState:
    """主角 U1 在 (0, 1)，帶 ``skill_t_line``；之後依序是 ``allies``、``foes``（HP 999）。"""
    skill = line_skill(fire=fire)
    hero = _spawn(gear or {}, weapon=weapon, skills=(LINE_SKILL, *extra_skills))
    tmpl = hero.template.model_copy(update={"skills": (LINE_SKILL, *extra_skills)})
    # 換武器時 spawn 會清掉技能，所以補回去
    hero = hero.model_copy(update={"position": (0, 1), "template": tmpl})
    spawns = [hero]
    spawns += [spawn(Team.ALLY, xy, no_reactions("bandit", max_hp=999)) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions("bandit", max_hp=999)) for xy in foes]
    m = make_map(ROW, ally=[(0, 1), *allies], enemy=list(foes))
    return give_turn(start_battle(make_setup(m, spawns, skills=[skill]), seed), U1)


@pytest.fixture
def always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """d20 一律 19（命中、不暴擊），其他骰子一律 1。"""

    def roll(self: Rng, sides: int) -> int:
        return 19 if sides == 20 else 1

    monkeypatch.setattr(Rng, "roll", roll)


def damaged(events: Sequence[EventBase]) -> list[UnitId]:
    return [e.target_id for e in events if isinstance(e, DamageDealt) and e.source_id == U1]


def attack(state: BattleState, target: UnitId = U2) -> list[EventBase]:
    return list(resolve(state, Attack(unit_id=U1, target_id=target)).events)


# ---------------------------------------------------------------------------
# 直線本身
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_hit")
def test_line_hits_the_target_and_the_enemy_behind() -> None:
    state = scene([(1, 1), (2, 1)])
    events = attack(state)
    assert damaged(events) == [U2, U3]
    rolled = [e.target_id for e in events if isinstance(e, AttackRolled)]
    assert rolled == [U2, U3]  # 每個目標各自擲命中


@pytest.mark.usefixtures("always_hit")
def test_line_stops_after_two_cells() -> None:
    state = scene([(1, 1), (2, 1), (3, 1)])
    assert damaged(attack(state)) == [U2, U3]


@pytest.mark.usefixtures("always_hit")
def test_line_follows_the_target_direction() -> None:
    state = scene([(0, 2), (0, 0), (1, 1)])
    # 主角 (0,1)；目標在南邊 (0,2)，直線往南出界只剩 1 格：只打目標
    assert damaged(attack(state)) == [U2]
    assert attack_line_tiles(state, state.units[U1], state.units[U2]) == ((0, 2),)


@pytest.mark.usefixtures("always_hit")
def test_allies_on_the_line_are_not_hurt() -> None:
    state = scene([(1, 1)], allies=[(2, 1)])
    events = attack(state, U3)
    assert damaged(events) == [U3]
    assert not [e for e in events if isinstance(e, AttackRolled) and e.target_id == U2]


def test_line_is_not_blocked_by_an_ally_between_cells() -> None:
    """長度 2：目標格之後只有 1 格；隊友在那格不受傷，也不會讓直線停下（停只看出界與牆）。"""
    state = scene([(1, 1)], allies=[(2, 1)])
    assert attack_line_tiles(state, state.units[U1], state.units[U3]) == ((1, 1), (2, 1))


def test_preview_shows_both_cells_even_when_empty() -> None:
    state = scene([(1, 1)])
    shown = preview(state, Attack(unit_id=U1, target_id=U2))
    assert {(1, 1), (2, 1)} <= set(shown.affected_tiles)
    assert any("普攻直線" in n for n in shown.notes)


def test_plain_attack_preview_tiles_are_unchanged() -> None:
    """沒有變形規則時，普攻預覽的影響格與說明照舊（不加直線的格子）。"""
    state = scene([(1, 1)])
    state.units[U1].skills = ()
    shown = preview(state, Attack(unit_id=U1, target_id=U2))
    assert (2, 1) not in shown.affected_tiles
    assert not any("普攻直線" in n for n in shown.notes)


# ---------------------------------------------------------------------------
# 武器限制
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("weapon", "ok"),
    [
        ("one_handed_sword", True),
        ("dual_dagger", True),
        ("greatsword", True),
        ("spear", False),
        ("whip", False),
        ("bow", False),
        ("crossbow", False),
        ("fire_staff", False),
    ],
)
def test_only_melee_reach_one_weapons_qualify(weapon: str, ok: bool) -> None:
    assert suits_line(library().weapons[weapon]) is ok


@pytest.mark.usefixtures("always_hit")
def test_ranged_weapon_cannot_use_it_and_is_greyed() -> None:
    state = scene([(1, 1), (2, 1)], weapon="bow")
    shaped = attack_shape_state(state, state.units[U1])
    assert shaped.shape is None and shaped.problem == "weapon"
    assert damaged(attack(state)) == [U2]
    notes = preview(state, Attack(unit_id=U1, target_id=U2)).notes
    assert f"普攻變形沒有效果：{WEAPON_PROBLEM_ZH}" in notes


def test_gear_view_greys_the_skill_with_a_ranged_weapon() -> None:
    for weapon, off in (("bow", WEAPON_PROBLEM_ZH), ("one_handed_sword", None)):
        hero = spawn(Team.ALLY, (0, 1), no_reactions("hero_fighter"), weapon)
        hero = hero.model_copy(update={"equipment": loadout({"body": [LINE_SKILL]})})
        foe = spawn(Team.ENEMY, (1, 1), no_reactions("bandit", max_hp=999))
        m = make_map(ROW, ally=[(0, 1)], enemy=[(1, 1)])
        setup = make_setup(m, [hero, foe], skills=[line_skill()])
        gates = {gate_key(LINE_SKILL, "attack"): 800}  # 裝備授予的要過預算閘門（E5）
        setup = setup.model_copy(
            update={"ruleset": setup.ruleset.model_copy(update={"reshape_gates": gates})}
        )
        state = start_battle(setup, 0)
        view = project_for(state, Team.ALLY).units
        me = next(u for u in view if u.id == U1)
        assert [g.off_zh for g in me.gear_skills] == [off]
        lines = [a for slot in me.equipment for a in slot.affixes if a.category == "action"]
        assert [a.off_zh for a in lines] == [off]


# ---------------------------------------------------------------------------
# 只改主動普攻
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_hit")
@pytest.mark.parametrize(("primary", "reaction", "hits"), [(True, False, 2), (False, True, 1)])
def test_reaction_attacks_stay_single(primary: bool, reaction: bool, hits: int) -> None:
    state = scene([(1, 1), (2, 1)])
    ctx = Ctx(state.clone())
    attacker, target = ctx.state.units[U1], ctx.state.units[U2]
    perform_unit_attack(ctx, attacker, target, primary=primary, reaction=reaction)
    assert len(damaged(ctx.events)) == hits


# ---------------------------------------------------------------------------
# 打中多人時的計數（8.29 E5 第 6 點）
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("always_hit")
def test_added_element_applies_to_everyone_on_the_line() -> None:
    state = scene([(1, 1), (2, 1)], fire=True)
    elements = [
        e.element for e in attack(state) if isinstance(e, DamageDealt) and e.source_id == U1
    ]
    assert elements == [Element.FIRE, Element.FIRE]


@pytest.mark.usefixtures("always_hit")
def test_every_n_hits_counts_once_per_attack() -> None:
    state = scene([(1, 1), (2, 1)], extra_skills=("skill_twin_strike",))
    after = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].hits_landed == 1  # 打中 2 人只 +1（雙連電擊 n=2 不會因此觸發）


@pytest.mark.usefixtures("always_hit")
def test_combo_counts_once_and_follows_the_first_target() -> None:
    state = scene([(1, 1), (2, 1)], gear={"main_hand": [("affix_attack_combo", 3)]})
    after = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].attack_hits_landed == 1


@pytest.mark.usefixtures("always_hit")
def test_cleave_fires_once_from_the_first_target() -> None:
    state = scene([(1, 1), (2, 1), (1, 2)], gear={"main_hand": [("affix_attack_cleave", None)]})
    events = attack(state)
    fired = [e for e in events if isinstance(e, GearTriggered) and e.trigger == "attack_cleave"]
    assert len(fired) == 1
    assert fired[0].other_id in (U3, U4)  # 第一個目標 (1,1) 旁邊的另一個敵人


# ---------------------------------------------------------------------------
# 預算、確定性
# ---------------------------------------------------------------------------


def test_budget_prices_the_line_attack() -> None:
    report = skill_budget(line_skill(), library())
    rows = [e for e in report.effects if e.type == "modifier.attack_shape"]
    assert len(rows) == 1 and rows[0].points > 0


def test_same_seed_same_result() -> None:
    state = scene([(1, 1), (2, 1)], seed=7)
    first = resolve(state, Attack(unit_id=U1, target_id=U2))
    second = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]
    assert state_to_json(first.state) == state_to_json(second.state)
