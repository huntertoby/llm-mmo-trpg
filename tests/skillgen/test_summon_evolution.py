"""Phase 3-33f2：召喚技能的三支分歧進化（加深、橋接、數量型）——產物合法、同階預算、確定性、
各支的內容與進化後的召喚結果。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import caster_template, library, make_map, make_setup, spawn
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_summon_f2 import (
    BLAST,
    COOLDOWN,
    DURATION,
    INHERIT,
    MARK,
    MEND,
    loadout,
    sacrifice,
)
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import skill_reference_problems
from trpg.content.skills import SkillDef, rarity_rank
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import UnitSummoned
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import state_to_json
from trpg.shared.types import Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import Evolution, EvolutionRequest, evolution_options
from trpg.skillgen.summon_evolution import is_summon_skill, summon_evolution_options
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

FIRE_SPIRIT = "skill_summon_fire_spirit"
GOLEM = "skill_summon_golem"
SKELETON = "skill_raise_skeleton"
WALL = "skill_summon_earth_wall"
PLANT_TOTEM = "skill_plant_totem"


def _summon_skills() -> list[SkillDef]:
    return [s for _, s in sorted(library().skills.items()) if is_summon_skill(s)]


def _options(skill_id: str, usage: SkillUsage | None = None, **held: int) -> tuple[Evolution, ...]:
    lib = library()
    request = EvolutionRequest(lib.skills[skill_id], usage or SkillUsage(), held, 5)
    return evolution_options(lib, request)


def _spec(skill: SkillDef):  # type: ignore[no-untyped-def]
    return next(e for e in skill.effects if e.type == "summon")


def test_summon_skills_use_the_summon_evolution_path() -> None:
    assert len(_summon_skills()) >= 17
    lib = library()
    for skill in _summon_skills():
        request = EvolutionRequest(skill, SkillUsage(), {}, 1)
        assert evolution_options(lib, request) == summon_evolution_options(lib, request)


def test_fire_spirit_gets_all_three_branches() -> None:
    deepen, bridge, count = _options(FIRE_SPIRIT)
    assert (deepen.branch, bridge.branch, count.branch) == ("deepen", "bridge", "count")
    assert deepen.template == "summon_deepen" and count.template == "summon_count"


def test_deepen_raises_hp_and_adds_a_small_trait_by_role() -> None:
    table = library().evolution.summon
    deepen = _options(FIRE_SPIRIT)[0]
    spec = _spec(deepen.skill)
    assert spec.max_hp_permille == table.deepen_hp_permille
    assert spec.trait == table.traits["ranged"]  # 火靈是遠程：銳利
    assert spec.count in (None, 1) and spec.power_permille is None and spec.infusion is None
    assert deepen.skill.name_zh == "強化・召喚火靈"
    golem = _options(GOLEM)[0]
    assert _spec(golem.skill).trait == table.traits["melee"]
    wall = _options(WALL)[0]
    assert _spec(wall.skill).trait == table.traits["static"]


def test_bridge_adds_a_second_infusion_keyword_the_skill_really_carries() -> None:
    lib = library()
    bridge = _options(FIRE_SPIRIT, SkillUsage(partner_makes={"prone": 3}))[1]
    spec = _spec(bridge.skill)
    assert bridge.branch == "bridge" and bridge.keyword == spec.infusion == "prone"
    assert spec.infusion in lib.ruleset.core.summon_infusions
    exclusive = derive_keywords(bridge.skill, lib.keywords, exclusive_only=True).all()
    assert "prone" in exclusive and "ignite" in exclusive  # 保留自己的點燃，多一個倒下
    assert bridge.skill.id == f"{FIRE_SPIRIT}_evo_summon_bridge_prone"
    assert bridge.skill.name_zh == "崩倒・召喚火靈"


def test_bridge_never_repeats_a_keyword_the_skill_already_has() -> None:
    for option in _options(FIRE_SPIRIT, SkillUsage(partner_makes={"ignite": 5})):
        assert option.keyword != "ignite"


def test_bridge_falls_back_to_the_summons_role_without_any_usage() -> None:
    bridge = _options(GOLEM)[1]
    table = library().ruleset.core.summon_infusions
    assert "melee" in table[bridge.keyword or ""].roles  # 近戰召喚物優先近戰灌注


def test_count_summons_two_at_sixty_percent() -> None:
    count = _options(FIRE_SPIRIT)[2]
    spec = _spec(count.skill)
    assert (spec.count, spec.power_permille) == (2, 600)
    assert count.skill.name_zh == "雙生・召喚火靈"
    assert spec.max_hp_permille is None and spec.infusion is None


def test_static_summons_skip_the_branches_that_make_no_sense() -> None:
    # 圖騰（光環）沒有數量型；土牆不攻擊所以沒有橋接
    assert [o.branch for o in _options(PLANT_TOTEM)] == ["deepen"]
    assert [o.branch for o in _options(WALL)] == ["deepen", "count"]


def test_every_evolution_is_legal_and_within_the_same_tier_budget() -> None:
    lib = library()
    usages = [SkillUsage(), SkillUsage(partner_makes={"wet": 2}, target_keywords={"marked": 2})]
    checked = 0
    for skill in _summon_skills():
        base = _spec(skill)
        for usage in usages:
            for option in evolution_options(lib, EvolutionRequest(skill, usage, {"charged": 1}, 3)):
                evolved = option.skill
                assert validate_skill(evolved, lib) == [], evolved.id
                assert Fraction(7, 10) <= skill_budget(evolved, lib).ratio <= 1, evolved.id
                assert evolved.tier == skill.tier and evolved.kind == skill.kind
                assert evolved.rarity == skill.rarity  # 稀有度不加強度
                assert evolved.ap_cost == skill.ap_cost
                assert evolved.provenance.parents == (skill.id,) and evolved.id != skill.id
                spec = _spec(evolved)
                assert spec.unit == base.unit  # 還是同一種召喚物
                assert 1 <= (spec.duration or 0) <= (base.duration or 0)  # 只會縮短，不會變長
                checked += 1
    assert checked >= 40


def test_most_summon_skills_have_all_three_branches() -> None:
    skills = _summon_skills()
    full = [s for s in skills if len(_options(s.id)) == 3]
    assert len(full) >= len(skills) // 2


def test_same_request_gives_the_same_options() -> None:
    usage = SkillUsage(partner_makes={"wet": 1})
    assert _options(FIRE_SPIRIT, usage) == _options(FIRE_SPIRIT, usage)


def test_budget_counts_the_extra_content() -> None:
    lib = library()
    base = skill_budget(lib.skills[FIRE_SPIRIT], lib).total
    deepen, bridge, count = _options(FIRE_SPIRIT)
    # 加深、橋接都比原本值錢（先不管為了放進預算縮短了持續輪數）；數量型是原本的約 1.2 倍
    for option in (deepen, bridge, count):
        spec, original = _spec(option.skill), _spec(lib.skills[FIRE_SPIRIT])
        if spec.duration == original.duration:
            assert skill_budget(option.skill, lib).total > base, option.template


def test_summon_traits_in_the_evolution_table_exist() -> None:
    lib = library()
    table = lib.evolution.summon
    assert set(table.traits.values()) <= set(lib.ruleset.core.summon_traits)


def test_unknown_trait_or_infusion_is_rejected_by_the_library_check() -> None:
    lib = library()
    deepen = _options(FIRE_SPIRIT)[0].skill
    broken = deepen.model_copy(
        update={"effects": (_spec(deepen).model_copy(update={"trait": "no_such_trait"}),)}
    )
    problems = skill_reference_problems(broken, lib.ruleset, lib.skills)
    assert any("召喚物小特性" in p for p in problems)
    wet = _options(FIRE_SPIRIT)[1].skill
    broken = wet.model_copy(
        update={"effects": (_spec(wet).model_copy(update={"infusion": "no_such_keyword"}),)}
    )
    problems = skill_reference_problems(broken, lib.ruleset, lib.skills)
    assert any("灌注關鍵字" in p for p in problems)


@pytest.mark.parametrize("skill_id", [FIRE_SPIRIT, GOLEM])
def test_evolved_skills_are_ordinary_skills_with_a_valid_rarity(skill_id: str) -> None:
    for option in _options(skill_id):
        assert rarity_rank(option.skill.rarity) >= rarity_rank("rare")


def test_a_battle_with_evolved_summon_skills_and_summon_gear_replays_identically() -> None:
    """三支進化與召喚詞條都是確定的：初始狀態 ＋ 動作列表重播得到同一個終局（3-33f2）。"""
    lib = library()
    request = EvolutionRequest(lib.skills["skill_summon_fire_spirit"], SkillUsage(), {}, 3)
    options = evolution_options(lib, request)
    assert [o.branch for o in options] == ["deepen", "bridge", "count"]
    evolved = [o.skill for o in options]
    gear: dict[str, list[tuple[str, int | None]]] = {
        "off_hand": [COOLDOWN, DURATION],
        "neck": [sacrifice(), BLAST],
        "ring_1": [MEND],
        "main_hand": [MARK, INHERIT],
    }
    m = make_map(FLAT7, ally=[(0, 3)], enemy=[(5, 3), (5, 4)])
    template = caster_template([s.id for s in evolved])
    owner = spawn(Team.ALLY, (0, 3), template, "scepter", skills=None)
    owner = owner.model_copy(update={"equipment": loadout(gear)})
    foes = [spawn(Team.ENEMY, xy, "bandit") for xy in ((5, 3), (5, 4))]
    setup = make_setup(m, [owner, *foes], skills=evolved, max_rounds=10)
    run = run_battle(setup, 11, UtilityAI(lib.ai_profiles))
    again = replay(setup, 11, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump_json() for e in again.events] == [e.model_dump_json() for e in run.events]
    assert len([e for e in run.events if isinstance(e, UnitSummoned)]) >= 2
