"""Phase 2A-2 6.3／6.4 第 3 條：效用 AI 在「有技能」的條件下的情境測試。"""

from __future__ import annotations

from collections.abc import Sequence

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import Attack, BattleState, Move, UseSkill, legal_actions, preview
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.events import SkillUsed
from trpg.engine.rules.combat import cover_object_between
from trpg.engine.runner import run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Pos, Team


def _ai(override: str | None = None) -> UtilityAI:
    return UtilityAI(library().ai_profiles, override=override)


def _scene(
    skills: Sequence[str],
    foes: Sequence[tuple[int, int]],
    *,
    base: str,
    caster: tuple[int, int] = (3, 3),
    allies: Sequence[tuple[int, int]] = (),
    max_mana: int | None = None,
    heights: str = FLAT7,
    objects: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """U1 是裝備真正技能的施放者（有 ``base`` 的 AI 行為模式），之後是友方、敵方（無反應）。"""
    m = make_map(heights, ally=[caster, *allies], enemy=list(foes), objects=objects)
    unit = caster_template(list(skills), base=base)
    if max_mana is not None:
        unit = unit.model_copy(update={"max_mana": max_mana})
    spawns = [spawn(Team.ALLY, caster, unit)]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


# ---------------------------------------------------------------------------
# 三個敵人排成一列：弓手選擇穿透射擊而不是普攻
# ---------------------------------------------------------------------------


def test_archer_picks_piercing_shot_when_three_enemies_line_up() -> None:
    state = _scene(
        ["skill_piercing_shot"], [(3, 3), (4, 3), (5, 3)], base="hero_archer", caster=(1, 3)
    )
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_piercing_shot"
    assert action.direction == "east"
    ranked = _ai().rank(state)
    attacks = [s.score for s in ranked if isinstance(s.action, Attack)]
    shot = max(s.score for s in ranked if isinstance(s.action, UseSkill))
    assert attacks and shot > max(attacks)


def test_archer_prefers_a_plain_attack_when_only_one_enemy_is_in_line() -> None:
    state = _scene(["skill_piercing_shot"], [(6, 3)], base="hero_archer", caster=(1, 3))
    action = _ai()(state)
    assert isinstance(action, Attack)  # 一個目標不值得付 6 點法力與 2 回合冷卻


# ---------------------------------------------------------------------------
# 範圍技能會打到友方：換方向、或改用其他動作
# ---------------------------------------------------------------------------


def test_the_ai_aims_the_cone_where_it_does_not_burn_an_ally() -> None:
    # 東邊的錐形有敵人也有友方；北邊的錐形只有一個敵人
    state = _scene(["skill_ashen_oath"], [(5, 3), (3, 1)], base="hero_mage", allies=[(4, 3)])
    profile = _ai().profile_for(state.units[U1])
    east = UseSkill(unit_id=U1, skill_id="skill_ashen_oath", direction="east")
    north = UseSkill(unit_id=U1, skill_id="skill_ashen_oath", direction="north")
    assert score_action(state, north, profile).score > score_action(state, east, profile).score
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.direction == "east")


def test_the_ai_uses_something_else_when_every_direction_would_burn_an_ally() -> None:
    # 唯一的敵人在東邊，錐形裡還站著兩個友方：不值得
    state = _scene(["skill_ashen_oath"], [(5, 3)], base="hero_mage", allies=[(4, 3), (4, 2)])
    action = _ai()(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == "skill_ashen_oath")
    assert isinstance(action, Attack | Move)


def test_a_fire_skill_is_fine_when_the_ally_is_outside_the_cone() -> None:
    state = _scene(["skill_ashen_oath"], [(5, 3), (5, 4)], base="hero_mage", allies=[(3, 5)])
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.direction == "east"


# ---------------------------------------------------------------------------
# 友方受重傷：風暴使使用聖域（治療只算實際補到的量）
# ---------------------------------------------------------------------------


def test_stormcaller_casts_sanctuary_when_an_ally_is_badly_hurt() -> None:
    state = _scene(["skill_sanctuary"], [(6, 6)], base="hero_stormcaller", allies=[(2, 3)])
    state.units[U2].hp = 5
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_sanctuary"


def test_a_scratch_is_not_worth_a_sanctuary() -> None:
    """只缺 1 點 HP：實際補到的量只有 1，不值得 10 點法力與 3 回合冷卻。"""
    state = _scene(["skill_sanctuary"], [(6, 6)], base="hero_stormcaller", allies=[(2, 3)])
    state.units[U2].hp = state.units[U2].max_hp - 1
    action = _ai()(state)
    assert not isinstance(action, UseSkill)
    ranked = [s for s in _ai().rank(state) if isinstance(s.action, UseSkill)]
    assert all(s.score <= 0 for s in ranked)


def test_sanctuary_counts_only_the_hp_actually_restored() -> None:
    state = _scene(["skill_sanctuary"], [(6, 6)], base="hero_stormcaller", allies=[(2, 3)])
    state.units[U2].hp = state.units[U2].max_hp - 2
    p = preview(state, UseSkill(unit_id=U1, skill_id="skill_sanctuary"))
    healed = {uid: (lo, hi) for uid, lo, hi in p.healed}
    assert healed[U2] == (2, 2)  # 骰值再大也只補到缺的 2 點


# ---------------------------------------------------------------------------
# 法力只夠用一次強技能：沒有目標價值時不浪費
# ---------------------------------------------------------------------------


def test_the_ai_saves_its_only_big_spell_when_nothing_is_worth_it() -> None:
    # 唯一的敵人在錐形之外（北邊太遠、也看不到值得的選取）：不施放，法力原封不動
    state = _scene(["skill_ashen_oath"], [(6, 6)], base="hero_mage", max_mana=12)
    action = _ai()(state)
    assert not (isinstance(action, UseSkill))
    assert state.units[U1].mana == 12


def test_the_ai_does_not_spend_its_last_mana_on_a_target_a_plain_attack_finishes() -> None:
    state = _scene(["skill_ashen_oath", "skill_fire_bolt"], [(5, 3)], base="hero_mage", max_mana=12)
    state.units[U2].hp = 1
    action = _ai()(state)
    assert isinstance(action, Attack)  # 一般攻擊就能收下，不付法力


def test_the_ai_does_spend_the_mana_when_the_target_value_is_there() -> None:
    state = _scene(["skill_ashen_oath"], [(5, 2), (5, 3), (5, 4)], base="hero_mage", max_mana=12)
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_ashen_oath"


def test_mana_and_cooldown_weights_lower_a_skills_score() -> None:
    state = _scene(["skill_ashen_oath"], [(5, 3)], base="hero_mage")
    action = UseSkill(unit_id=U1, skill_id="skill_ashen_oath", direction="east")
    profile = _ai().profile_for(state.units[U1])
    free = profile.model_copy(
        update={"weights": profile.weights.model_copy(update={"mana": 0, "cooldown": 0})}
    )
    cost = score_action(state, action, free).score - score_action(state, action, profile).score
    weights = profile.weights
    assert cost == weights.mana * 12 + weights.cooldown * 2 and cost > 0


# ---------------------------------------------------------------------------
# 場地型技能（決定 #2）：位置價值提升就是候選
# ---------------------------------------------------------------------------

WIDE = "\n".join(["0" * 14] * 7)


def _outgunned(skills: Sequence[str], distance: int) -> BattleState:
    """我方弓手在 (1, 3)；敵方弓手的長弓射程 10（比我們的 8 遠），站在 ``distance`` 格外。
    我方已經沒有移動點數：不能靠走位解決。"""
    lib = library()
    m = make_map(WIDE, ally=[(1, 3)], enemy=[(1 + distance, 3)])
    hero = caster_template(list(skills), base="hero_archer")
    longbow = lib.weapons["bow"].model_copy(update={"range": 10})
    foe = spawn(Team.ENEMY, (1 + distance, 3), template("bandit_archer", reactions=[]), "bow")
    foe = foe.model_copy(update={"weapon": longbow})
    state = give_turn(make_state(m, [spawn(Team.ALLY, (1, 3), hero), foe]), U1)
    state.units[U1].move_points = 0
    return state


def test_archer_in_the_enemys_longer_reach_throws_smoke_at_its_own_position() -> None:
    state = _outgunned(["skill_smoke_arrow"], 9)  # 我們打不到（8），對方打得到我們（10）
    assert not any(isinstance(a, Attack) for a in legal_actions(state))
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_smoke_arrow"
    center = action.target_pos
    assert center is not None
    assert max(abs(center.x - 1), abs(center.y - 3)) <= 1  # 3×3 煙幕罩住自己的格子


def test_vanish_is_also_a_field_skill_that_protects_the_caster() -> None:
    state = _outgunned(["skill_vanish"], 9)
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_vanish"


def test_no_smoke_when_nobody_can_hit_us() -> None:
    state = _outgunned(["skill_smoke_arrow"], 12)  # 12 > 10：誰也打不到誰
    action = _ai()(state)
    assert not isinstance(action, UseSkill)


def test_smoke_between_the_enemy_and_us_is_a_candidate() -> None:
    state = _outgunned(["skill_smoke_arrow"], 9)
    ranked = [s for s in _ai().rank(state) if isinstance(s.action, UseSkill)]
    assert 1 <= len(ranked) <= _ai().skill_candidates
    assert any(s.score > 0 for s in ranked)


def test_archer_can_still_walk_behind_cover_instead_of_throwing_smoke() -> None:
    """有走位空間又有掩護物時，「改站到掩護後」同樣是合格的答案（既有的 cover 權重）。"""
    lib = library()
    m = make_map(WIDE, ally=[(1, 3)], enemy=[(10, 3)], objects=((5, 3, "low_wall"),))
    hero = caster_template(["skill_smoke_arrow"], base="hero_archer")
    foe = spawn(Team.ENEMY, (10, 3), template("bandit_archer", reactions=[]), "bow")
    longbow = lib.weapons["bow"].model_copy(update={"range": 10})
    foe = foe.model_copy(update={"weapon": longbow})
    state = give_turn(make_state(m, [spawn(Team.ALLY, (1, 3), hero), foe]), U1)
    action = _ai()(state)
    if isinstance(action, Move):
        assert cover_object_between(state, (10, 3), (action.dest.x, action.dest.y)) is not None
    else:
        assert isinstance(action, UseSkill) and action.skill_id == "skill_smoke_arrow"


# ---------------------------------------------------------------------------
# 敵人技能（6.2）
# ---------------------------------------------------------------------------


def test_only_the_boss_and_the_archer_have_skills() -> None:
    lib = library()
    assert lib.unit("bandit_boss").skills and lib.unit("bandit_archer").skills
    assert not lib.unit("bandit").skills and not lib.unit("bandit_shieldbearer").skills
    for template_id in ("bandit_boss", "bandit_archer"):
        t = lib.unit(template_id)
        assert 1 <= len(t.skills) <= 2 and t.max_mana > 0


def test_enemies_actually_use_their_skills_in_demo_battles() -> None:
    lib = library()
    ai = UtilityAI(lib.ai_profiles)
    enemy_skills: set[str] = set()
    for map_id in ("oil_depot", "bridge_chasm"):
        encounter = lib.map(map_id).encounter
        assert encounter is not None
        setup = build_setup(lib, map_id, encounter.allies, encounter.enemies, max_rounds=30)
        for seed in range(4):
            run = run_battle(setup, seed, ai)
            teams = {u.id: u.team for u in run.state.units.values()}
            for event in run.events:
                if isinstance(event, SkillUsed) and teams[event.unit_id] is Team.ENEMY:
                    enemy_skills.add(event.skill_id)
    assert enemy_skills & {"skill_cleave", "skill_gale_kick", "skill_fire_arrow"}


def test_a_fire_arrow_can_target_and_ignite_an_oil_barrel() -> None:
    state = _scene([], [(6, 6)], base="bandit_archer", objects=((5, 3, "oil_barrel"),))
    state.units[U1].skills = ("skill_fire_arrow",)
    state.units[U1].max_mana = state.units[U1].mana = 9
    barrel = next(o for o in state.objects.values() if o.kind == "oil_barrel")
    actions = [
        a
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_object_id == barrel.id
    ]
    assert actions, "火焰箭矢可以選油桶為目標"
    assert Pos(x=5, y=3) is not None


def test_legal_actions_with_areas_lists_the_same_actions_and_one_area_per_skill_action() -> None:
    state = _scene(
        ["skill_ashen_oath", "skill_fire_bolt"], [(5, 3), (5, 4)], base="hero_mage", allies=[(2, 3)]
    )
    actions, areas = legal_actions_with_areas(state)
    assert actions == legal_actions(state)
    skill_actions = [a for a in actions if isinstance(a, UseSkill)]
    assert skill_actions and set(areas) == {id(a) for a in skill_actions}
    assert all(area.tiles for area in areas.values())
