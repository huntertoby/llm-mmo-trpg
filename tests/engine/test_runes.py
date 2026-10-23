"""刻印（Phase 3-23）：放置、持續與移除、上限、條件讀取、引爆、預算、示範技能與重播。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import Attack, BattleState, EndTurn, UseSkill, resolve, telegraph
from trpg.engine.effects import DamageEffect, InscribeEffect, run_effects
from trpg.engine.events import AttackRolled, DamageDealt, EventBase, RuneInscribed, RuneRemoved
from trpg.engine.runes import has_own_rune, own_runes, own_runes_at, runes_at
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.narrative.skill_icon import icon_of
from trpg.shared.types import Element, Pos, Team, UnitId, rune_name
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

U3, U4 = UnitId("unit_0003"), UnitId("unit_0004")


def _inscribe_skill(shape: dict[str, object] | None = None, **spec: object) -> SkillDef:
    effect: dict[str, object] = {"type": "inscribe", "element": "lightning"}
    effect.update(spec)
    return make_skill(SID, shape or {"type": "ground_tile", "range": 5}, [effect])


def _finish_round(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    events: list[EventBase] = []
    start = state.round
    while state.round == start and not state.ended:
        assert state.active_unit is not None
        r = resolve(state, EndTurn(unit_id=state.active_unit))
        state, events = r.state, events + r.events
    return state, events


def _rune_at(state: BattleState, xy: tuple[int, int], owner: UnitId = U1) -> bool:
    return has_own_rune(state, owner, xy)


# ---------------------------------------------------------------------------
# 放置
# ---------------------------------------------------------------------------


def test_inscribe_places_a_rune_with_default_duration_and_both_teams_see_it() -> None:
    state = battle(_inscribe_skill(), foes=[(6, 3)])
    result = cast(state, target_pos=Pos(x=5, y=3))
    (event,) = of(result, RuneInscribed)
    assert (event.owner_id, (event.pos.x, event.pos.y)) == (U1, (5, 3))
    assert (event.element, event.tag, event.remaining) == (Element.LIGHTNING, None, 3)
    (rune,) = result.state.runes
    assert (rune.id, rune.team, rune.xy, rune.remaining) == (1, Team.ALLY, (5, 3), 3)
    for team in (Team.ALLY, Team.ENEMY):  # 敵我都看得到
        (view,) = project_for(result.state, team).runes
        assert (view.owner_id, view.name_zh, view.remaining) == (U1, "雷紋", 3)
    assert rune_name(None, "hunt") == "符紋"  # 查不到刻印單字時不拼英文（3-41a）
    assert rune_name(None, "hunt", {"hunt": "獵"}) == "獵紋"


def test_inscribe_covers_every_tile_of_the_shape_and_takes_explicit_duration() -> None:
    skill = _inscribe_skill({"type": "cross", "range": 4}, duration=2)
    result = cast(battle(skill, foes=[(6, 6)]), target_pos=Pos(x=3, y=1))
    cells = sorted(r.xy for r in result.state.runes)
    assert cells == [(2, 1), (3, 0), (3, 1), (3, 2), (4, 1)]
    assert {r.remaining for r in result.state.runes} == {2}


def test_inscribe_does_nothing_on_unstandable_tiles() -> None:
    m = make_map("0000\n0000", ally=[(0, 0)], enemy=[(3, 1)], objects=[(2, 0, "stone_pillar")])
    state = make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (3, 1))])
    out = run_effects(
        state,
        [
            InscribeEffect(
                source_id=U1, team=Team.ALLY, pos=(2, 0), element=Element.FIRE, duration=None
            )
        ],
    )
    assert not out.state.runes
    assert [type(e).__name__ for e in out.events] == ["EffectFizzled"]


def test_same_cell_is_refreshed_and_other_owners_runes_coexist() -> None:
    state = battle(_inscribe_skill(), foes=[(6, 3)])
    state = cast(state, target_pos=Pos(x=5, y=3)).state
    again = run_effects(
        state,
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(5, 3), tag="hunt", duration=5)],
    )
    removed = of_events(again.events, RuneRemoved)
    assert [(r.reason, r.element) for r in removed] == [("replaced", Element.LIGHTNING)]
    (rune,) = again.state.runes
    assert (rune.id, rune.tag, rune.element, rune.remaining) == (2, "hunt", None, 5)
    foe = run_effects(
        again.state,
        [InscribeEffect(source_id=U2, team=Team.ENEMY, pos=(5, 3), element=Element.FIRE)],
    ).state
    assert [r.owner_id for r in runes_at(foe, (5, 3))] == [U1, U2]  # 同格不同施放者並存


def of_events[E: EventBase](events: list[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 持續與移除
# ---------------------------------------------------------------------------


def test_runes_count_down_each_environment_round_and_expire() -> None:
    state = cast(battle(_inscribe_skill(), foes=[(6, 3)]), target_pos=Pos(x=5, y=3)).state
    state, events = _finish_round(state)
    assert [r.remaining for r in state.runes] == [2]
    assert not of_events(events, RuneRemoved)
    state, _ = _finish_round(state)
    assert [r.remaining for r in state.runes] == [1]
    state, events = _finish_round(state)
    (gone,) = of_events(events, RuneRemoved)
    assert (gone.reason, gone.rune_id, gone.owner_id) == ("expired", 1, U1)
    assert not state.runes


def test_runes_outlive_a_fallen_caster_until_they_expire() -> None:
    state = cast(
        battle(_inscribe_skill(), foes=[(6, 3)], allies=[(0, 0)]), target_pos=Pos(x=5, y=3)
    ).state
    state = run_effects(
        state, [DamageEffect(source_id=U2, target_id=U1, mode="lethal", cause="effect")]
    ).state
    assert not state.units[U1].alive and not state.ended
    state, _ = _finish_round(state)
    assert [(r.owner_id, r.remaining) for r in state.runes] == [(U1, 2)]


def test_per_owner_limit_evicts_the_oldest_rune() -> None:
    state = battle(_inscribe_skill(), foes=[(6, 6)])
    cells = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)]
    events: list[EventBase] = []
    for xy in cells:
        out = run_effects(
            state, [InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, element=Element.FIRE)]
        )
        state, events = out.state, events + out.events
    limit = library().ruleset.core.rune_limit_per_owner
    assert limit == 6
    assert sorted(r.xy for r in state.runes) == sorted(cells[1:])  # 最舊的 (0, 0) 被擠掉
    (evicted,) = [e for e in of_events(events, RuneRemoved)]
    assert (evicted.reason, evicted.rune_id, (evicted.pos.x, evicted.pos.y)) == ("limit", 1, (0, 0))
    # 別的施放者不受影響、也不被擠掉
    other = run_effects(
        state, [InscribeEffect(source_id=U2, team=Team.ENEMY, pos=(0, 1), tag="x")]
    ).state
    assert len(own_runes(other, U1)) == 6 and len(own_runes(other, U2)) == 1


# ---------------------------------------------------------------------------
# 讀取：條件 on_own_rune
# ---------------------------------------------------------------------------


def _rune_arena(foe_owner: UnitId = U1, element: Element = Element.LIGHTNING) -> BattleState:
    state = battle(_inscribe_skill(), foes=[(5, 3)])
    team = state.units[foe_owner].team
    return run_effects(
        state, [InscribeEffect(source_id=foe_owner, team=team, pos=(5, 3), element=element)]
    ).state


def _holds(state: BattleState, **cond: object) -> bool:
    caster = state.units[U1]
    return condition_met(
        state,
        caster,
        ConditionSpec.model_validate({"type": "on_own_rune", **cond}),
        Subject(state.unit_at(5, 3), (5, 3)),
    )


def test_on_own_rune_condition_checks_the_targets_tile() -> None:
    state = _rune_arena()
    assert _holds(state)
    assert not condition_met(
        state,
        state.units[U1],
        ConditionSpec.model_validate({"type": "on_own_rune"}),
        Subject(None, (4, 3)),
    )
    # 沒有單位的格子也成立（格子條件）
    assert condition_met(
        state,
        state.units[U1],
        ConditionSpec.model_validate({"type": "on_own_rune"}),
        Subject(None, (5, 3)),
    )


def test_on_own_rune_element_and_tag_filters() -> None:
    state = _rune_arena()
    assert _holds(state, element="lightning")
    assert not _holds(state, element="fire")
    assert not _holds(state, tag="hunt")
    tagged = run_effects(
        state, [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(5, 3), tag="hunt")]
    ).state  # 同格重刻：取代為標籤符文
    assert _holds(tagged, tag="hunt") and not _holds(tagged, element="lightning")
    assert own_runes_at(tagged, U1, (5, 3), tag="hunt")


def test_someone_elses_rune_does_not_count() -> None:
    state = _rune_arena(foe_owner=U2)
    assert runes_at(state, (5, 3)) and not _rune_has(state)
    assert not _holds(state)


def _rune_has(state: BattleState) -> bool:
    return _rune_at(state, (5, 3), U1)


def test_conditional_effect_in_a_skill_only_fires_on_own_rune() -> None:
    lib = library()
    bolt = lib.skills["skill_rune_thunderbolt"].model_copy(update={"id": SID})

    def run(state: BattleState) -> int:
        state = with_rolls(state, [(20, 15), (8, 4), (8, 4), (8, 4)])
        result = resolve(state, UseSkill(unit_id=U1, skill_id=bolt.id, target_id=U2))
        return len([e for e in of(result, DamageDealt) if e.cause == "attack"])

    plain = battle(bolt, foes=[(5, 3)])
    assert run(plain) == 1
    with_rune = run_effects(
        plain,
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(5, 3), element=Element.LIGHTNING)],
    ).state
    assert run(with_rune) == 2
    fire = run_effects(
        plain, [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(5, 3), element=Element.FIRE)]
    ).state
    assert run(fire) == 1  # 元素篩選：火紋不算
    theirs = run_effects(
        plain,
        [InscribeEffect(source_id=U2, team=Team.ENEMY, pos=(5, 3), element=Element.LIGHTNING)],
    ).state
    assert run(theirs) == 1  # 別人的符文不算


def test_modifier_passive_boosts_damage_on_own_rune() -> None:
    def multiplier(with_rune: bool) -> int:
        hero = template("hero_fighter", reactions=[], max_mana=99, skills=["skill_rune_resonance"])
        m = make_map("0000\n0000", ally=[(0, 0)], enemy=[(1, 0)])
        state = give_turn(
            make_state(
                m,
                [
                    spawn(Team.ALLY, (0, 0), hero),
                    spawn(Team.ENEMY, (1, 0), no_reactions(max_hp=200)),
                ],
            ),
            U1,
        )
        if with_rune:
            state = run_effects(
                state, [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(1, 0), tag="x")]
            ).state
        result = resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2))
        return next(e for e in of(result, DamageDealt) if e.cause == "attack").multiplier_permille

    assert multiplier(False) == 1000
    assert multiplier(True) == 1150


# ---------------------------------------------------------------------------
# 讀取：消耗型 detonate_runes
# ---------------------------------------------------------------------------


def _burst_skill() -> SkillDef:
    return make_skill(
        SID,
        {"type": "allies_in_radius", "radius": 3},
        [{"type": "detonate_runes", "dice": "1d6"}],
    )


def test_detonate_removes_own_runes_in_range_and_hits_enemies_standing_on_them() -> None:
    state = battle(_burst_skill(), foes=[(4, 3), (5, 3)], allies=[(3, 4)])
    for xy, owner, team, element in (
        ((4, 3), U1, Team.ALLY, Element.FIRE),  # 敵人站在上面 → 傷害（元素取符文）
        ((3, 4), U1, Team.ALLY, Element.FIRE),  # 友方站在上面 → 只移除、不傷害
        ((3, 2), U1, Team.ALLY, Element.LIGHTNING),  # 沒有單位 → 只移除
        ((5, 3), U4, Team.ENEMY, Element.FIRE),  # 別人的符文 → 不動
        ((0, 0), U1, Team.ALLY, Element.FIRE),  # 範圍外 → 不動
    ):
        state = run_effects(
            state, [InscribeEffect(source_id=owner, team=team, pos=xy, element=element)]
        ).state
    result = cast(state)
    removed = of(result, RuneRemoved)
    assert sorted((r.reason, (r.pos.x, r.pos.y)) for r in removed) == [
        ("detonated", (3, 2)),
        ("detonated", (3, 4)),
        ("detonated", (4, 3)),
    ]
    hurt = [e for e in of(result, DamageDealt)]
    assert [(e.target_id, e.element, e.cause) for e in hurt] == [(U3, Element.FIRE, "effect")]
    assert sorted((r.owner_id, r.xy) for r in result.state.runes) == [(U1, (0, 0)), (U4, (5, 3))]
    assert not [e for e in result.events if isinstance(e, AttackRolled)]  # 自動命中


def test_detonate_with_no_runes_is_harmless() -> None:
    result = cast(battle(_burst_skill(), foes=[(4, 3)]))
    assert not of(result, DamageDealt) and not of(result, RuneRemoved)


def test_detonate_element_override_and_all_affects_spare_the_caster() -> None:
    skill = make_skill(
        SID,
        {"type": "allies_in_radius", "radius": 3},
        [{"type": "detonate_runes", "dice": "1d6", "element": "shadow", "affects": "all"}],
    )
    state = battle(skill, foes=[(4, 3)], allies=[(3, 4)])
    for xy in ((4, 3), (3, 4), (3, 3)):
        state = run_effects(
            state, [InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, tag="t")]
        ).state
    result = cast(state)
    hurt = sorted((e.target_id, e.element) for e in of(result, DamageDealt))
    assert hurt == [(U2, Element.SHADOW), (UnitId("unit_0003"), Element.SHADOW)]
    assert not result.state.runes  # 施放者自己腳下的符文也被引爆，但他不受傷


# ---------------------------------------------------------------------------
# 預算與示範技能
# ---------------------------------------------------------------------------


def test_inscribe_budget_scales_with_duration() -> None:
    lib = library()
    permille = lib.budget.inscribe_duration_permille
    assert list(permille) == sorted(permille) and permille[2] == 1000  # 預設 3 輪 ＝ 基礎
    for n in (1, 2, 3, 4, 5):
        skill = _inscribe_skill(duration=n)
        e = skill_budget(skill, lib).effects[0]
        assert e.points == Fraction(5 * permille[n - 1], 1000) * e.range  # 3-49 射程係數
    default = skill_budget(_inscribe_skill(), lib).effects[0]
    assert default.points == 5 * default.range  # 省略 duration ＝ 預設輪數 3


def test_detonate_budget_uses_dice_average_and_shape_multiplier() -> None:
    lib = library()
    points = skill_budget(_burst_skill(), lib).effects[0].points
    shape = Fraction(2200, 1000)  # allies_in_radius 半徑 3
    assert points == Fraction(7, 2) * Fraction(lib.budget.detonate_runes_permille, 1000) * shape


def test_demo_skills_pass_budget_and_validation() -> None:
    lib = library()
    demo = (
        "skill_thunder_sigil",
        "skill_ember_trail",
        "skill_hunt_sigil",
        "skill_rune_thunderbolt",
        "skill_rune_burst",
        "skill_rune_resonance",
    )
    for sid in demo:
        assert validate_skill(lib.skills[sid], lib) == [], sid
        assert skill_budget(lib.skills[sid], lib).ok, sid
    inscribers = [
        s for s in demo if lib.skills[s].effects and lib.skills[s].effects[0].type == "inscribe"
    ]
    assert len(inscribers) == 3
    readers = [s for s in demo if s not in inscribers]
    assert len(readers) == 3 and "skill_rune_burst" in readers  # 讀取 3 招，含 1 招消耗


def test_icon_of_derives_rune_parts() -> None:
    lib = library()
    sigil = icon_of(lib.skills["skill_thunder_sigil"].model_dump(mode="json", exclude_none=True))
    assert [e.type for e in sigil.segments[0].effects] == ["inscribe"]
    assert sigil.elements == ("lightning",)
    bolt = icon_of(lib.skills["skill_rune_thunderbolt"].model_dump(mode="json", exclude_none=True))
    assert bolt.condition is not None and bolt.condition.id == "on_own_rune"
    assert [e.condition for e in bolt.segments[0].effects] == [None, "on_own_rune"]
    burst = icon_of(lib.skills["skill_rune_burst"].model_dump(mode="json", exclude_none=True))
    assert [e.type for e in burst.segments[0].effects] == ["detonate_runes"]


# ---------------------------------------------------------------------------
# 確定性與序列化
# ---------------------------------------------------------------------------


def test_same_inputs_replay_identically_and_state_roundtrips() -> None:
    def run() -> tuple[str, list[dict[str, object]]]:
        state = cast(
            battle(_inscribe_skill({"type": "cross", "range": 4}), foes=[(6, 3)]),
            target_pos=Pos(x=3, y=1),
        ).state
        out: list[dict[str, object]] = []
        for _ in range(3):
            state, events = _finish_round(state)
            out += [e.model_dump(exclude={"seq"}) for e in events]
        return state_to_json(state), out

    assert run() == run()
    state = cast(battle(_inscribe_skill(), foes=[(6, 3)]), target_pos=Pos(x=5, y=3)).state
    restored = state_from_json(state_to_json(state))
    assert restored.runes == state.runes and restored.next_rune_id == state.next_rune_id


def test_telegraph_does_not_mutate_the_state() -> None:
    state = cast(battle(_inscribe_skill(), foes=[(6, 3)]), target_pos=Pos(x=5, y=3)).state
    before = state_to_json(state)
    telegraph(state)
    assert state_to_json(state) == before
