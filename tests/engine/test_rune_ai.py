"""刻印的 AI（Phase 3-23）：先刻再引——有讀取技能才刻、刻在敵人會停留的格子、讀取技能對符文加分。"""

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
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import BattleState, UseSkill
from trpg.engine.ai.rune import has_rune_reader, rune_gains
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.effects import InscribeEffect, run_effects
from trpg.engine.events import RuneInscribed
from trpg.engine.preview import preview
from trpg.shared.types import Element, Team


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _scene(skills: Sequence[str], foes: Sequence[tuple[int, int]]) -> BattleState:
    caster = (1, 3)
    m = make_map(FLAT7, ally=[caster], enemy=list(foes))
    unit = caster_template(list(skills), base="hero_mage").model_copy(update={"max_mana": 99})
    spawns = [spawn(Team.ALLY, caster, unit)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def test_only_units_with_a_reader_skill_want_to_inscribe() -> None:
    with_reader = _scene(["skill_thunder_sigil", "skill_rune_thunderbolt"], [(5, 3)])
    without = _scene(["skill_thunder_sigil"], [(5, 3)])
    assert has_rune_reader(with_reader, with_reader.units[U1])
    assert not has_rune_reader(without, without.units[U1])
    ai = _ai()
    ranked = ai.rank(without)
    assert not [s for s in ranked if getattr(s.action, "skill_id", None) == "skill_thunder_sigil"]


def test_the_ai_inscribes_before_it_reads() -> None:
    # 敵人遠在射程外且不會移動：有讀取技能（咒雷）時，AI 先在敵人附近刻雷紋
    state = _scene(["skill_thunder_sigil", "skill_rune_thunderbolt"], [(5, 3)])
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_thunder_sigil"
    assert action.target_pos is not None
    # 刻的位置在敵人身邊（距離 ≤ 2），不是離敵人很遠的地方
    assert abs(action.target_pos.x - 5) + abs(action.target_pos.y - 3) <= 2


def test_rune_gains_are_larger_closer_to_the_enemy() -> None:
    state = _scene(["skill_thunder_sigil", "skill_rune_thunderbolt"], [(5, 3)])
    profile = _ai().profile_for(state.units[U1])

    def gain(xy: tuple[int, int]) -> int:
        events = run_effects(
            state,
            [InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, element=Element.LIGHTNING)],
        ).events
        assert [e for e in events if isinstance(e, RuneInscribed)]
        return int(rune_gains(state, state.units[U1], events, profile))

    assert gain((5, 3)) > gain((4, 3)) > gain((3, 3)) > gain((1, 5)) == 0


def test_reading_skill_scores_higher_when_the_target_stands_on_an_own_rune() -> None:
    state = _scene(["skill_rune_thunderbolt"], [(4, 3)])
    action = UseSkill(unit_id=U1, skill_id="skill_rune_thunderbolt", target_id=U2)
    profile = _ai().profile_for(state.units[U1])
    plain = score_action(state, action, profile).score
    marked = run_effects(
        state,
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(4, 3), element=Element.LIGHTNING)],
    ).state
    on_rune = score_action(marked, action, profile).score
    assert on_rune > plain
    # 預覽本身反映條件追加的傷害（加分是在傷害之外的額外鼓勵）
    assert preview(marked, action).targets[0].damage != preview(state, action).targets[0].damage


def test_detonation_is_attractive_when_enemies_stand_on_runes() -> None:
    state = _scene(["skill_rune_burst"], [(3, 3)])
    action = UseSkill(unit_id=U1, skill_id="skill_rune_burst")
    profile = _ai().profile_for(state.units[U1])
    empty = score_action(state, action, profile).score
    marked = run_effects(
        state,
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=(3, 3), element=Element.FIRE)],
    ).state
    assert score_action(marked, action, profile).score > empty


def test_ai_decisions_with_runes_are_deterministic() -> None:
    state = _scene(["skill_thunder_sigil", "skill_rune_thunderbolt", "skill_rune_burst"], [(5, 3)])
    assert _ai()(state) == _ai()(state)
