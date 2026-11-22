"""E3：數值型地形規則同參數時取較強的那條（08 8.29 E2 補充；開發 PM 2026-11-22 補定）。

比的是實際值：裝備給的移動加成先截到裝備移動合計上限再比。裝備較強 → 裝備那條生效、角色面板註明種族
那條被蓋過；種族較強或一樣強 → 裝備那條標灰。兩件裝備之間同一套比法，一樣強時排在前面的生效。
``trail_surface``：同一種表面時 ``duration`` 長的較強；表面不同時排在前面的生效。
"""

from __future__ import annotations

from tests.engine.race_helpers import U1, race_state
from tests.engine.test_unit_rules_e2 import lines, move_stat, terrain, wear
from trpg.content.equipment import EquippedAffix
from trpg.engine import BattleState
from trpg.engine.rules.race import reveal_radius, slip_immune, surface_move_bonus
from trpg.engine.rules.unit_rules import (
    classify_sources,
    effective_strength,
    first_source,
    race_override_zh,
    rule_sources,
)
from trpg.engine.view import project_for
from trpg.shared.types import Surface, Team


def _swim(affix_id: str, surfaces: list[str], amount: int, name: str = "") -> EquippedAffix:
    return terrain(
        affix_id,
        name or f"站在{'、'.join(surfaces)}上，移動 +{amount}",
        rule="surface_move_bonus",
        surfaces=surfaces,
        amount=amount,
    )


def _race_note(state: BattleState) -> str | None:
    view = project_for(state, Team.ALLY)
    me = next(u for u in view.units if u.id == U1)
    assert me.race is not None
    return me.race.passive_overridden_zh


def test_stronger_gear_overrides_the_race_on_the_shared_key() -> None:
    state = race_state("scalefolk")
    unit = wear(state, {"feet": [_swim("affix_t_swim2", ["water"], 2, "水上移動 +2")]})
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 2
    assert surface_move_bonus(state.ruleset, unit, Surface.ICE) == 1  # 冰照舊是種族的 +1
    assert slip_immune(state.ruleset, unit, Surface.ICE)
    line = lines(state)["feet:affix_t_swim2"]
    assert line.active and line.duplicate_of is None and line.overlap_zh is None
    assert _race_note(state) == "水的部分被腳的「水上移動 +2」蓋過"


def test_gear_covering_every_key_overrides_the_whole_race_rule() -> None:
    state = race_state("scalefolk")
    unit = wear(state, {"feet": [_swim("affix_t_swim2", ["water", "ice"], 2, "水冰移動 +2")]})
    overlaps = classify_sources(rule_sources(state.ruleset, unit))
    assert overlaps[0].full and overlaps[1].covered == ()
    assert surface_move_bonus(state.ruleset, unit, Surface.ICE) == 2
    assert _race_note(state) == "被腳的「水冰移動 +2」蓋過"
    assert race_override_zh(state.ruleset, unit) == "被腳的「水冰移動 +2」蓋過"


def test_equal_strength_keeps_the_race_and_greys_the_gear() -> None:
    state = race_state("scalefolk")
    unit = wear(state, {"feet": [_swim("affix_t_swim1", ["water", "ice"], 1)]})
    assert classify_sources(rule_sources(state.ruleset, unit))[1].full
    assert not lines(state)["feet:affix_t_swim1"].active
    assert _race_note(state) is None


def test_compared_after_the_gear_move_cap() -> None:
    # 數值詞條已給 +2：靴子 +2 截完是 0，比種族的 +1 弱 → 種族生效、靴子標灰，結果維持 +1
    state = race_state("scalefolk")
    boots = _swim("affix_t_swim2", ["water", "ice"], 2)
    unit = wear(state, {"feet": [boots], "body": [move_stat(2)]})
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 1
    strength = effective_strength(state.ruleset, unit)
    overlaps = classify_sources(rule_sources(state.ruleset, unit), strength)
    assert not overlaps[0].covered and overlaps[1].full
    line = lines(state)["feet:affix_t_swim2"]
    assert not line.active and line.duplicate_of == "種族被動「流線身形」"
    assert _race_note(state) is None
    # 只剩 1 點額度：截完 +1，和種族一樣強 → 種族生效
    state = race_state("scalefolk")
    unit = wear(state, {"feet": [boots], "body": [move_stat(1)]})
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 1
    assert not lines(state)["feet:affix_t_swim2"].active


def test_two_pieces_of_gear_stronger_wins_tie_keeps_the_earlier_slot() -> None:
    state = race_state(None)
    weak = _swim("affix_t_swim1", ["water"], 1, "水上移動 +1")
    strong = _swim("affix_t_swim2", ["water"], 2, "水上移動 +2")
    unit = wear(state, {"feet": [weak], "ring_1": [strong]})
    assert surface_move_bonus(state.ruleset, unit, Surface.WATER) == 2
    shown = lines(state)
    assert shown["ring_1:affix_t_swim2"].active
    feet = shown["feet:affix_t_swim1"]
    assert not feet.active and feet.duplicate_of == "戒指 1的水上移動 +2"
    state = race_state(None)
    other = _swim("affix_t_swim1b", ["water"], 1, "水上也移動 +1")
    unit = wear(state, {"feet": [weak], "ring_1": [other]})
    shown = lines(state)
    assert shown["feet:affix_t_swim1"].active and not shown["ring_1:affix_t_swim1b"].active


def test_trail_surface_longer_duration_wins_only_for_the_same_surface() -> None:
    state = race_state(None)
    short = terrain("affix_t_frost1", "霜行 1", rule="trail_surface", surfaces=["ice"], duration=1)
    long = terrain("affix_t_frost2", "霜行 2", rule="trail_surface", surfaces=["ice"], duration=2)
    unit = wear(state, {"feet": [short], "ring_1": [long]})
    found = first_source(state.ruleset, unit, "trail_surface")
    assert found is not None and found.rule.duration == 2
    state = race_state(None)
    fire = terrain("affix_t_ember", "火行", rule="trail_surface", surfaces=["fire"], duration=2)
    unit = wear(state, {"feet": [short], "ring_1": [fire]})
    found = first_source(state.ruleset, unit, "trail_surface")
    assert found is not None and found.rule.surfaces == (Surface.ICE,)  # 表面不同：前面的生效
    assert not lines(state)["ring_1:affix_t_ember"].active


def test_radius_rule_takes_the_stronger_source() -> None:
    state = race_state(None)
    near = terrain("affix_t_sense1", "靈覺 1", rule="detect_hidden_nearby", radius=1)
    far = terrain("affix_t_sense2", "靈覺 2", rule="detect_hidden_nearby", radius=2)
    unit = wear(state, {"feet": [near], "ring_1": [far]})
    assert reveal_radius(state.ruleset, unit) == 2


def test_no_override_note_without_gear() -> None:
    state = race_state("scalefolk")
    assert _race_note(state) is None
    assert race_override_zh(state.ruleset, state.units[U1]) is None
