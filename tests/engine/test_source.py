"""源力（Phase 3C-4a 6.1）：開場值、上限、源泉格、擊殺精英、花費與戰鬥結果。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    Move,
    UseSkill,
    battle_result,
    legal_actions,
    resolve,
    start_battle,
    state_from_json,
    state_to_json,
)
from trpg.engine.events import SkillUsed, SourceChanged
from trpg.engine.setup import UnitSpawn
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

LEGEND_ID = "skill_t_legend"


def legendary(source: int = 1, **over: Any) -> SkillDef:
    """測試用傳說技能：自己獲得 1 AP，花 ``source`` 點源力、冷卻 2。"""
    data: dict[str, Any] = {
        "id": LEGEND_ID,
        "name_zh": "測試傳說",
        "tier": 1,
        "rarity": "legendary",
        "skeleton": "aura",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": 1,
        "scaling_attr": "wis",
        "shape": {"type": "self"},
        "effects": [{"type": "grant_ap", "amount": 1, "affects": "self"}],
        "cost": {"cooldown": 2, "source": source},
    }
    data.update(over)
    return SkillDef.model_validate(data)


def _spawns(ally_source: int | None, enemy_source: int | None) -> list[UnitSpawn]:
    ally = spawn(Team.ALLY, (0, 0)).model_copy(update={"source": ally_source})
    enemy = spawn(Team.ENEMY, (5, 5)).model_copy(update={"source": enemy_source})
    return [ally, enemy]


@pytest.mark.parametrize(
    ("given", "expected"),
    [(None, 1), (0, 1), (1, 1), (2, 2), (3, 3), (5, 3)],
)
def test_starting_source_uses_the_floor_and_the_cap(given: int | None, expected: int) -> None:
    m = make_map("000000\n" * 5 + "000000", enemy=[(5, 5)])
    state = start_battle(make_setup(m, _spawns(given, 3)), 0)
    ally, enemy = state.units_sorted()
    assert ally.source == expected
    assert enemy.source == 0  # 敵人一律 0（保底只套用在我方）


def test_the_floor_and_cap_come_from_core_rules() -> None:
    m = make_map("000000\n" * 5 + "000000", enemy=[(5, 5)])
    setup = make_setup(m, _spawns(None, None), source_min_at_start=2, source_max=4)
    assert start_battle(setup, 0).units_sorted()[0].source == 2
    setup = make_setup(m, _spawns(9, None), source_min_at_start=0, source_max=4)
    assert start_battle(setup, 0).units_sorted()[0].source == 4


def _well_state(wells: list[tuple[int, int]], *, ally_source: int | None = None) -> BattleState:
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(5, 3)])
    m = m.model_copy(update={"source_wells": tuple(wells)})
    ally = spawn(Team.ALLY, (1, 3), no_reactions("hero_fighter")).model_copy(
        update={"source": ally_source}
    )
    state = make_state(m, [ally, spawn(Team.ENEMY, (5, 3), no_reactions())])
    return give_turn(state, U1)


def test_an_ally_entering_a_well_gains_one_source_and_the_well_disappears() -> None:
    state = _well_state([(2, 3), (2, 6)])
    assert state.source_wells == ((2, 3), (2, 6))
    result = resolve(state, Move(unit_id=U1, path=(Pos(x=1, y=3), Pos(x=2, y=3))))
    (event,) = [e for e in result.events if isinstance(e, SourceChanged)]
    assert (event.unit_id, event.before, event.after, event.reason) == (U1, 1, 2, "well")
    assert event.pos == Pos(x=2, y=3)
    assert result.state.units[U1].source == 2
    assert result.state.source_wells == ((2, 6),)


def test_a_well_walked_through_counts_and_a_full_unit_still_takes_it() -> None:
    state = _well_state([(2, 3)], ally_source=3)
    path = (Pos(x=1, y=3), Pos(x=2, y=3), Pos(x=3, y=3))
    result = resolve(state, Move(unit_id=U1, path=path))
    (event,) = [e for e in result.events if isinstance(e, SourceChanged)]
    assert (event.before, event.after) == (3, 3)  # 上限 3，不會超過
    assert result.state.units[U1].source == 3 and result.state.source_wells == ()


def test_an_enemy_does_not_take_a_well() -> None:
    state = _well_state([(4, 3)])
    state = give_turn(state, U2)
    result = resolve(state, Move(unit_id=U2, path=(Pos(x=5, y=3), Pos(x=4, y=3))))
    assert not [e for e in result.events if isinstance(e, SourceChanged)]
    assert result.state.source_wells == ((4, 3),)
    assert result.state.units[U2].source == 0


def test_source_wells_survive_serialization_and_replay_state() -> None:
    state = _well_state([(2, 3)])
    again = state_from_json(state_to_json(state))
    assert again.source_wells == ((2, 3),) and again.units[U1].source == 1


def _elite_scene(tags: tuple[str, ...]) -> BattleState:
    m = make_map(FLAT7, ally=[(2, 3)], enemy=[(3, 3)])
    foe = no_reactions(max_hp=1, tags=list(tags))
    hero = no_reactions("hero_fighter")
    state = make_state(m, [spawn(Team.ALLY, (2, 3), hero), spawn(Team.ENEMY, (3, 3), foe)])
    return give_turn(state, U1)


def test_downing_an_elite_gives_the_killer_one_source(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(_elite_scene(("elite",)), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].downed
    (event,) = [e for e in result.events if isinstance(e, SourceChanged)]
    assert (event.unit_id, event.reason, event.other_id, event.after) == (U1, "kill_elite", U2, 2)


def test_downing_a_normal_enemy_gives_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(_elite_scene(()), Attack(unit_id=U1, target_id=U2))
    assert result.state.units[U2].downed
    assert not [e for e in result.events if isinstance(e, SourceChanged)]


def test_only_bandit_boss_is_an_elite_in_content() -> None:
    elites = sorted(u.id for u in library().units.values() if "elite" in u.tags)
    assert elites == ["bandit_boss"]


def _legend_state(source: int | None, skill: SkillDef | None = None) -> BattleState:
    skill = skill or legendary()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(6, 6)])
    caster = spawn(Team.ALLY, (3, 3), caster_template([skill], base="hero_fighter")).model_copy(
        update={"source": source}
    )
    state = make_state(m, [caster, spawn(Team.ENEMY, (6, 6), no_reactions())], skills=[skill])
    return give_turn(state, U1)


def test_casting_a_legendary_spends_source() -> None:
    state = _legend_state(2)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=LEGEND_ID))
    (used,) = [e for e in result.events if isinstance(e, SkillUsed)]
    (spent,) = [e for e in result.events if isinstance(e, SourceChanged)]
    assert used.source == 1 and spent.seq > used.seq
    assert (spent.before, spent.after, spent.reason, spent.skill_id) == (2, 1, "skill", LEGEND_ID)
    assert result.state.units[U1].source == 1


def test_not_enough_source_is_rejected_in_chinese() -> None:
    state = _legend_state(1, legendary(source=2))
    assert not any(isinstance(a, UseSkill) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="源力不足：需要 2，目前 1"):
        resolve(state, UseSkill(unit_id=U1, skill_id=LEGEND_ID))


def test_battle_result_reports_remaining_source_for_allies() -> None:
    state = _legend_state(3)
    after = resolve(state, UseSkill(unit_id=U1, skill_id=LEGEND_ID)).state
    result = battle_result(after)
    assert [(a.unit_id, a.source) for a in result.allies] == [(U1, 2)]
    assert result.source_of(U1) == 2
    assert result.source_of("nobody") is None
    assert result.hp_of(U1) == after.units[U1].hp
    assert result.mana_of(U1) == after.units[U1].mana
    assert result.source_of_template(after.units[U1].template_id) == 2
    assert result.source_of_template("nobody") is None


def test_battle_result_template_lookup_rejects_two_units_of_one_template() -> None:
    state = _legend_state(3)
    result = battle_result(state)
    twin = result.allies[0].model_copy(update={"unit_id": "unit_0099"})
    doubled = result.model_copy(update={"allies": (*result.allies, twin)})
    with pytest.raises(ValueError, match="請以單位 ID 查詢"):
        doubled.source_of_template(twin.template_id)
    assert doubled.source_of("unit_0099") == twin.source  # 以單位 ID 查沒有歧義


def test_shipped_maps_with_source_wells() -> None:
    lib = library()
    with_wells = sorted(m.id for m in lib.maps.values() if m.source_wells)
    assert with_wells == ["dark_forest", "ruined_fort"]
    terrain = lib.ruleset.terrain.by_id()
    for map_id in with_wells:
        m = lib.map(map_id)
        assert len(m.source_wells) == 2
        assert all(terrain[m.tile_terrain(x, y)].walkable for x, y in m.source_wells)


def test_source_well_placement_is_validated() -> None:
    base = make_map(FLAT7, ally=[(1, 3)], enemy=[(5, 3)], objects=[(4, 4, "crate")])
    data = base.model_dump(mode="json")
    for wells, message in (
        ([[9, 9]], "超出地圖範圍"),
        ([[4, 4]], "與物件重疊"),
        ([[1, 3]], "在起始區內"),
        ([[2, 2], [2, 2]], "重複"),
    ):
        with pytest.raises(ValueError, match=message):
            type(base).model_validate({**data, "source_wells": wells})


def test_elite_template_helper_keeps_tags() -> None:
    assert "elite" in template("bandit_boss").tags
