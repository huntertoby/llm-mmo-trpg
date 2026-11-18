"""SK-3b 第 4 項：示範技能 4 招（玩法交接 4.1.30 第 5 點，名稱玩法 PM 定）。

- 被動「餘燼共鳴」：你造的燃燒被利用時 +1 專注（借小護盾當核心）。
- 被動「潮引」：你造的水被利用時回 1 法力（借小護盾當核心）。
- 反應「命運偏折」：敵人擲中你時，逼他重擲取較差的。
- 反應「幸運低語」：身旁隊友擲失手時，讓他重擲取較好的。
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.engine.helpers import give_turn, library
from tests.engine.skill_helpers import U1, U2, U3
from tests.engine.test_exploit_sk3b import BURNING, ON_WATER, cond_skill, scene, use, with_status
from tests.engine.test_passive_triggers import always
from tests.engine.test_reroll_sk3 import HIT, MISS, d20s, of, rolled
from tests.engine.test_reroll_sk3 import scene as reroll_scene
from trpg.engine import Attack, resolve
from trpg.engine.events import AttackRerolled, SkillTriggered
from trpg.shared.types import Surface
from trpg.skillgen.validate import validate_skill

DEMOS = ("skill_ember_resonance", "skill_tidal_draw", "skill_fate_deflect", "skill_lucky_whisper")


@pytest.mark.parametrize("skill_id", DEMOS)
def test_the_demo_skills_pass_the_validator(skill_id: str) -> None:
    lib = library()
    assert validate_skill(lib.skills[skill_id], lib) == []


def test_the_names_are_the_ones_the_design_pm_chose() -> None:
    names = [library().skills[s].name_zh for s in DEMOS]
    assert names == ["餘燼共鳴", "潮引", "命運偏折", "幸運低語"]


def test_ember_resonance_gives_focus_when_your_burning_is_exploited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    demo = library().skills["skill_ember_resonance"]
    result = use(with_status(scene(cond_skill(BURNING), [demo]), U3))
    fired = [e for e in result.events if isinstance(e, SkillTriggered)]
    assert [(e.unit_id, e.skill_id) for e in fired] == [(U3, demo.id)]
    assert result.state.units[U3].stacks.get("focus") == 1


def test_tidal_draw_restores_mana_when_your_water_is_exploited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    demo = library().skills["skill_tidal_draw"]
    state = scene(cond_skill(ON_WATER), [demo])
    state = state.clone()
    tile = state.tile(4, 3)
    state.set_tile(4, 3, replace(tile, surface=Surface.WATER, surface_creator=U3))
    state.units[U3].mana = 0
    result = use(state)
    fired = [e for e in result.events if isinstance(e, SkillTriggered)]
    assert [(e.unit_id, e.skill_id) for e in fired] == [(U3, demo.id)]
    assert result.state.units[U3].mana == 1


def test_fate_deflect_forces_the_enemy_to_keep_the_worse_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = library().skills["skill_fate_deflect"]
    state = reroll_scene(defender=demo)
    d20s(monkeypatch, [HIT, MISS])
    result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U1))
    (rerolled,) = of(result.events, AttackRerolled)
    assert (rerolled.unit_id, rerolled.keep, rerolled.kept) == (U1, "worse", "second")
    assert rolled(result.events) == [(MISS, False)]


def test_lucky_whisper_lets_an_ally_keep_the_better_roll(monkeypatch: pytest.MonkeyPatch) -> None:
    demo = library().skills["skill_lucky_whisper"]
    state = reroll_scene(demo)
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (rerolled,) = of(result.events, AttackRerolled)
    assert (rerolled.unit_id, rerolled.keep, rerolled.kept) == (U3, "better", "second")
    assert rolled(result.events) == [(HIT, True)]
