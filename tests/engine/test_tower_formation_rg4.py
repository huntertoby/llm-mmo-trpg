"""RG-4：塔盾詞條「護陣」（#163，``docs/design/08-裝備.md`` 8.11「塔盾詞條『護陣』」）。

每列一條規則句、實際跑引擎：和帶護陣的單位相鄰（上下左右）的隊友（不含自己、不分遠近）被遠程攻擊
時，攻擊者命中 −``shield_formation_hit_penalty``；判定和敵方盾兵同一套（``guard_between``）——繞到
側面、不相鄰、近戰、攻擊者站得夠高都擋不到；和半掩護、盾兵、塔盾、其他護陣不疊加、取最高。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    spawn,
    template,
)
from trpg.content.affix_names import resolve_affix_name
from trpg.content.equipment import AffixRoll, ItemDef, Loadout, resolve_loadout
from trpg.engine import Action, Attack, BattleState, EndTurn, legal_actions, preview, resolve
from trpg.engine.events import AttackRolled
from trpg.engine.ids import SHIELD_FORMATION
from trpg.engine.rules.combat import half_cover, holds_formation
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import UnitSpawn
from trpg.engine.state import state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.types import Pos, Team, UnitId

SHOOTER, WARD, HOLDER, OTHER = (UnitId(f"unit_000{i}") for i in range(1, 5))
FORMATION = "affix_trait_tower_formation"
ROW = "0" * 10
PENALTY = library().ruleset.core.shield_formation_hit_penalty


def formation_shield() -> ItemDef:
    """塔盾本體加上護陣（走一般的裝備快照 → 戰鬥裝備狀態路徑）。"""
    tower = library().items["item_offhand_tower_shield"]
    return tower.model_copy(
        update={"id": "item_test_formation_shield", "affixes": (AffixRoll(affix=FORMATION),)}
    )


def loadout(*, formation: bool = True) -> Loadout:
    lib = library()
    item = formation_shield() if formation else lib.items["item_offhand_tower_shield"]
    return resolve_loadout({"off_hand": item.id}, {**lib.items, item.id: item}, lib.affixes)


def holding(s: UnitSpawn, *, formation: bool = True) -> UnitSpawn:
    return s.model_copy(update={"equipment": loadout(formation=formation)})


def scene(
    shooter: tuple[int, int] = (1, 4),
    *,
    holder_at: tuple[int, int] = (5, 4),
    weapon: str = "bow",
    ward: str = "hero_fighter",
    heights: Sequence[str] | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    other: UnitSpawn | None = None,
    **core: int,
) -> BattleState:
    """SHOOTER（敵方）在 ``shooter``；WARD（我方，預設近戰的戰士）在 (6, 4)；HOLDER（我方，拿帶
    護陣的塔盾）在 ``holder_at``；OTHER（選填）。"""
    rows = "\n".join(heights or [ROW] * 9)
    ally: list[tuple[int, int]] = [(6, 4), holder_at]
    if other is not None and other.position is not None:
        ally.append(other.position)
    m = make_map(rows, ally=ally, enemy=[shooter], objects=objects)
    spawns = [
        spawn(Team.ENEMY, shooter, template("hero_archer", reactions=[]), weapon, skills=()),
        spawn(Team.ALLY, (6, 4), template(ward, reactions=[], max_hp=300)),
        holding(
            spawn(Team.ALLY, holder_at, template("hero_fighter", reactions=[], max_hp=300)),
        ),
    ]
    if other is not None:
        spawns.append(other)
    state = make_state(m, spawns)
    if core:
        rs = state.ruleset
        state.ruleset = rs.model_copy(update={"core": rs.core.model_copy(update=core)})
    return give_turn(state, SHOOTER)


def cover_of(state: BattleState, target: UnitId = WARD) -> tuple[int, UnitId | None, str | None]:
    found = half_cover(state, state.units[SHOOTER], state.units[target])
    return (0, None, None) if found is None else (found.penalty, found.unit_id, found.kind)


def test_the_formation_affix_is_on_the_holder_only() -> None:
    state = scene()
    assert holds_formation(state.units[HOLDER])
    assert not holds_formation(state.units[WARD])


def test_an_adjacent_ally_is_covered_against_a_ranged_attack() -> None:
    state = scene()
    assert cover_of(state) == (PENALTY, HOLDER, SHIELD_FORMATION)
    result = resolve(state, Attack(unit_id=SHOOTER, target_id=WARD))
    (roll,) = [e for e in result.events if isinstance(e, AttackRolled)]
    assert roll.cover == -PENALTY and roll.cover_unit_id == HOLDER and roll.cover_formation
    assert roll.cover_object_id is None
    text = describe_event(roll, result.state) or ""
    assert "盾陣" in text and "的盾陣擋住" in text and "盾兵掩護" not in text
    assert "cover_formation" in roll.model_dump_json()


def test_the_preview_names_the_formation_holder() -> None:
    p = preview(scene(), Attack(unit_id=SHOOTER, target_id=WARD))
    assert any(
        note.startswith(f"盾陣 −{PENALTY}：被 ") and "的盾陣擋住" in note for note in p.notes
    )


def test_a_ranged_ally_is_covered_too() -> None:
    """盾兵只護遠程同伴；護陣護所有隊友（遠程也算）。"""
    assert cover_of(scene(ward="hero_archer"))[:2] == (PENALTY, HOLDER)


def test_the_holder_is_not_covered_by_its_own_formation() -> None:
    """持盾者自己由塔盾本體護（同半掩護的懲罰、沒有單位來源），不算護陣。"""
    state = scene(shooter=(1, 4), holder_at=(5, 4))
    state.units[WARD].pos = Pos(x=6, y=6)  # 隊友離開：持盾者旁邊沒有別人
    penalty, unit, kind = cover_of(state, HOLDER)
    assert unit is None and kind == "tower_shield"
    assert penalty == state.ruleset.core.half_cover_hit_penalty


def test_an_ally_two_tiles_away_is_not_covered() -> None:
    assert cover_of(scene(holder_at=(4, 4)))[0] == 0


def test_shooting_from_the_side_goes_around_the_formation() -> None:
    assert cover_of(scene(shooter=(6, 0)))[0] == 0


def test_the_holder_behind_the_ally_does_not_cover() -> None:
    assert cover_of(scene(holder_at=(7, 4)))[0] == 0


def test_enemies_next_to_the_holder_are_not_covered() -> None:
    """只護隊友：敵方單位站在持盾者旁邊不算。"""
    state = scene()
    state.units[WARD].team = Team.ENEMY
    assert cover_of(state)[0] == 0


@pytest.mark.parametrize("weapon", ["spear", "one_handed_sword"])
def test_melee_attacks_ignore_the_formation(weapon: str) -> None:
    state = scene(shooter=(4, 4), holder_at=(6, 5), weapon=weapon)
    state.units[HOLDER].pos = Pos(x=5, y=4)
    assert cover_of(state)[0] == 0


def test_shooting_from_two_layers_above_ignores_the_formation() -> None:
    rows = ["0000000000"] * 4 + ["2200000000"] + ["0000000000"] * 4
    assert cover_of(scene(heights=rows))[0] == 0


def test_one_layer_above_uses_the_half_cover_height_rule() -> None:
    """RG-5b（玩法PM交接 4.1.7 第 1 條）：高度照半掩護，持盾者算 1 層高，攻擊者只高 1 層仍擋得到
    （撤回 RG-5 的「高 1 層無視」，回到 RG-4 的共用判定）。"""
    rows = ["0000000000"] * 4 + ["1100000000"] + ["0000000000"] * 4
    assert cover_of(scene(heights=rows))[0] == PENALTY


def test_two_formations_count_once() -> None:
    second = holding(spawn(Team.ALLY, (6, 3), template("hero_fighter", reactions=[], max_hp=300)))
    state = scene(shooter=(1, 3), other=second)
    state.units[OTHER].pos = Pos(x=6, y=3)
    found = half_cover(state, state.units[SHOOTER], state.units[WARD])
    assert found is not None and found.penalty == PENALTY and found.kind == SHIELD_FORMATION
    result = resolve(state, Attack(unit_id=SHOOTER, target_id=WARD))
    (roll,) = [e for e in result.events if isinstance(e, AttackRolled)]
    assert roll.cover == -PENALTY


def test_formation_and_a_cover_object_count_once_and_take_the_higher() -> None:
    if "half_cover" not in library().ruleset.object_def("crate").tags:
        pytest.skip("crate 不是半掩護物件")
    state = scene(holder_at=(6, 5), objects=[(5, 4, "crate")])
    state.units[HOLDER].pos = Pos(x=6, y=3)  # 物件在正前方、持盾者在上方（朝攻擊者那一側）
    state.units[SHOOTER].pos = Pos(x=1, y=2)
    found = half_cover(state, state.units[SHOOTER], state.units[WARD])
    assert (
        found is not None and found.penalty == PENALTY and found.object_id is not None
    )  # 同分照舊
    higher = scene(
        holder_at=(6, 5),
        objects=[(5, 4, "crate")],
        shield_formation_hit_penalty=PENALTY + 1,
    )
    higher.units[HOLDER].pos = Pos(x=6, y=3)
    higher.units[SHOOTER].pos = Pos(x=1, y=2)
    found = half_cover(higher, higher.units[SHOOTER], higher.units[WARD])
    assert found is not None and found.penalty == PENALTY + 1 and found.unit_id == HOLDER


def test_formation_and_a_shield_guard_count_once_and_take_the_higher() -> None:
    guard = spawn(
        Team.ALLY,
        (6, 3),
        template("sect_shield_disciple", reactions=[], max_hp=300),
    )
    common = {"ward": "hero_archer", "shooter": (1, 2), "other": guard}
    state = scene(**common)  # type: ignore[arg-type]
    assert cover_of(state) == (PENALTY, OTHER, "shield_guard")  # 同分照舊算盾兵
    up = scene(**common, shield_formation_hit_penalty=PENALTY + 2)  # type: ignore[arg-type]
    assert cover_of(up) == (PENALTY + 2, HOLDER, SHIELD_FORMATION)
    guard_up = scene(**common, shield_guard_hit_penalty=PENALTY + 3)  # type: ignore[arg-type]
    assert cover_of(guard_up) == (PENALTY + 3, OTHER, "shield_guard")


def test_zero_penalty_turns_the_formation_off() -> None:
    assert cover_of(scene(shield_formation_hit_penalty=0))[0] == 0


def test_a_plain_tower_shield_does_not_guard_allies() -> None:
    state = scene()
    state.units[HOLDER].gear = state.units[HOLDER].gear.__class__(
        offhand=library().offhands["tower_shield"]
    )
    assert cover_of(state)[0] == 0


def test_the_card_text_follows_the_workshop_value() -> None:
    lib = library()
    raw = lib.affixes[FORMATION].model_copy(
        update={"name_zh": "x −{core.shield_formation_hit_penalty}"}
    )
    core = lib.ruleset.core.model_copy(update={"shield_formation_hit_penalty": 3})
    rs = lib.ruleset.model_copy(update={"core": core})
    assert resolve_affix_name(raw, rs).name_zh == "x −3"
    assert f"−{PENALTY}" in lib.affixes[FORMATION].name_zh


@settings(max_examples=25, deadline=None)
@given(x=st.integers(min_value=0, max_value=9), y=st.integers(min_value=0, max_value=8))
def test_without_the_affix_cover_never_comes_from_a_unit(x: int, y: int) -> None:
    """性質：持盾者拿沒有護陣的塔盾時，任何位置射擊都不會有單位提供掩護。"""
    if (x, y) in {(6, 4), (5, 4)}:
        return
    state = scene()
    holder = state.units[HOLDER]
    holder.gear = holder.gear.__class__(offhand=holder.gear.offhand)
    state.units[SHOOTER].pos = Pos(x=x, y=y)
    found = half_cover(state, state.units[SHOOTER], state.units[WARD])
    assert found is None or found.unit_id is None


def _shoot_the_ward(state: BattleState) -> Action:
    """敵方打得到 WARD 就打、否則結束回合；我方一律結束回合（只為了產生帶護陣的步驟）。"""
    actions = legal_actions(state)
    if state.active is not None and state.active.team is Team.ENEMY:
        for action in actions:
            if isinstance(action, Attack) and action.target_id == WARD:
                return action
    return next(a for a in actions if isinstance(a, EndTurn))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_a_battle_with_the_formation_replays_identically(seed: int) -> None:
    m = make_map("\n".join([ROW] * 9), ally=[(6, 4), (5, 4)], enemy=[(1, 4)])
    spawns = [
        spawn(Team.ENEMY, (1, 4), template("hero_archer", reactions=[], max_hp=300), "bow"),
        spawn(Team.ALLY, (6, 4), template("hero_fighter", reactions=[], max_hp=300)),
        holding(spawn(Team.ALLY, (5, 4), template("hero_fighter", reactions=[], max_hp=300))),
    ]
    setup = make_setup(m, spawns, max_rounds=3)
    run = run_battle(setup, seed, _shoot_the_ward)
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump_json() for e in again.events] == [e.model_dump_json() for e in run.events]
    rolls = [e for e in run.events if isinstance(e, AttackRolled)]
    assert rolls and all(r.cover_formation and r.cover == -PENALTY for r in rolls)
