"""BAL-4 難度與法力旋鈕：預設 ＝ 現行行為、副本不動原 library、縮放的整數運算、確定性。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library, scale_mana_cost
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.shared.types import Attribute
from trpg.sim.batch import map_spec, run_batches
from trpg.sim.difficulty import NEUTRAL, Difficulty, enemy_roster, scale_int, with_difficulty
from trpg.sim.difficulty_sweep import KNOB_NAMES, SINGLE_GRID, parse_combo, sweep_csv


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _mana_skill_id(library: ContentLibrary) -> str:
    roster = {s for i in enemy_roster(library) for s in library.units[i].skills}
    return next(
        s.id for s in library.ruleset.skills.skills if s.cost.mana >= 5 and s.id not in roster
    )


def test_neutral_returns_same_library(library: ContentLibrary) -> None:
    assert with_difficulty(library, NEUTRAL) is library
    assert NEUTRAL.label == "baseline"


def test_content_values_are_adopted_and_enter_ruleset_hash(library: ContentLibrary) -> None:
    """BAL-4b：採用的數值是正式欄位（寫在 content），會進序列化與規則包雜湊。"""
    core = library.ruleset.core
    assert (core.enemy_damage_permille, core.boss_damage_permille) == (1200, 1000)
    assert core.boss_escort_damage_permille == 1200
    assert core.ally_mana_cost_permille == 800
    assert core.resources.mana_cap_permille == 1400
    assert "boss_escort_damage_permille" in core.model_dump(mode="json")
    d = Difficulty(enemy_damage=900)
    assert hash_ruleset(with_difficulty(library, d).ruleset) != hash_ruleset(library.ruleset)


def test_escort_templates_default_to_enemy_values(library: ContentLibrary) -> None:
    """Boss 戰護衛／援軍是獨立範本（``*_guard``，帶 boss_escort 標籤），預設與一般敵人同值。"""
    lair = library.maps["bandit_lair"]
    assert lair.encounter is not None
    guards = [e for e in lair.encounter.enemies if e != "bandit_warlord"]
    assert guards and all("boss_escort" in library.units[e].tags for e in guards)
    assert set(library.roguelite.boss.enemies) == set(lair.encounter.enemies)
    for guard in guards:
        assert library.units[guard].max_hp == library.units[guard.removesuffix("_guard")].max_hp
    other = with_difficulty(library, Difficulty(escort_hp=1500, escort_damage=800))
    for guard in guards:  # 護衛旋鈕只動護衛，不動同型的一般敵人
        assert other.units[guard].max_hp == scale_int(library.units[guard].max_hp, 1500)
        plain = guard.removesuffix("_guard")
        assert other.units[plain].max_hp == library.units[plain].max_hp
    assert other.ruleset.core.boss_escort_damage_permille == 960
    assert other.ruleset.core.enemy_damage_permille == 1200


def test_copy_leaves_original_untouched(library: ContentLibrary) -> None:
    skill_id = _mana_skill_id(library)
    before_hp = library.units["bandit_warlord"].max_hp
    before_mana = library.ruleset.skill_def(skill_id).cost.mana
    d = Difficulty(1400, 1200, 800, 1200, 800, 1400)
    other = with_difficulty(library, d)
    assert other is not library
    assert library.units["bandit_warlord"].max_hp == before_hp
    assert library.ruleset.skill_def(skill_id).cost.mana == before_mana
    assert library.ruleset.core.enemy_damage_permille == 1200
    assert library.ruleset.core.boss_damage_permille == 1000
    assert library.ruleset.core.ally_mana_cost_permille == 800
    assert library.ruleset.core.resources.mana_cap_permille == 1400


def test_hp_scaling_splits_boss_and_enemy(library: ContentLibrary) -> None:
    other = with_difficulty(library, Difficulty(enemy_hp=1200, boss_hp=900))
    for template_id in enemy_roster(library):
        template = library.units[template_id]
        permille = 1200
        if "boss" in template.tags:
            permille = 900
        elif "boss_escort" in template.tags:
            permille = 1000  # 護衛有自己的旋鈕（escort_hp），不跟著 enemy_hp
        assert other.units[template_id].max_hp == max(1, scale_int(template.max_hp, permille))
    assert other.units["bandit_warlord"].max_hp == scale_int(
        library.units["bandit_warlord"].max_hp, 900
    )
    summons = [i for i, t in library.units.items() if t.summon]
    assert all(other.units[i].max_hp == library.units[i].max_hp for i in summons)
    assert "bandit_warlord" in enemy_roster(library)
    assert all(not library.units[i].summon for i in enemy_roster(library))


def test_scale_int_rounds_half_up() -> None:
    assert scale_int(10, 1000) == 10
    assert scale_int(15, 900) == 14  # 13.5 → 14
    assert scale_int(7, 800) == 6  # 5.6 → 6
    assert scale_int(5, 1200) == 6


def test_mana_cost_scaling_applies_to_base_and_added_skills(library: ContentLibrary) -> None:
    skill_id = _mana_skill_id(library)
    base = library.ruleset.skill_def(skill_id)
    other = with_difficulty(library, Difficulty(mana_cost=800))
    # 旋鈕在 content 值上再乘：已縮放的費用再乘 0.8
    assert other.ruleset.skill_def(skill_id).cost.mana == scale_int(base.cost.mana, 800)
    assert other.skills[skill_id] == library.skills[skill_id]  # library.skills 保持原始值
    # 加入的技能（一輪的生成技能走 with_skills）依「絕對」倍率（800 × 800 ＝ 640）從原始費用縮放
    raw = library.skills[skill_id]
    clone = raw.model_copy(update={"id": "skill_bal4_clone"})
    assert other.ruleset.core.ally_mana_cost_permille == 640
    added = other.ruleset.with_skills([clone])
    assert added.skill_def("skill_bal4_clone").cost.mana == scale_int(raw.cost.mana, 640)
    assert added.skill_def("skill_bal4_clone").cost.stamina == base.cost.stamina
    # content 倍率（800）：with_skills 也縮放
    content_added = library.ruleset.with_skills([clone]).skill_def("skill_bal4_clone")
    assert content_added.cost.mana == scale_int(raw.cost.mana, 800)


def test_scale_mana_cost_keeps_minimum_one_and_identity() -> None:
    lib = load_library()
    skill = next(s for s in lib.ruleset.skills.skills if s.cost.mana == 1)
    assert scale_mana_cost(skill, 100).cost.mana == 1
    assert scale_mana_cost(skill, 1000) is skill
    free = next(s for s in lib.ruleset.skills.skills if s.cost.mana == 0)
    assert scale_mana_cost(free, 800) is free


def test_mana_cap_scales_only_mana(library: ContentLibrary) -> None:
    attrs = {a: 10 for a in Attribute}
    base = library.ruleset.core.resources
    other = with_difficulty(library, Difficulty(mana_cap=1400)).ruleset.core.resources
    assert base.max_for("mana", 20, attrs) == 28  # content：×1.4
    assert other.max_for("mana", 20, attrs) == 39  # 1400 × 1400‰ ＝ 1960‰：39.2 → 39
    assert other.max_for("stamina", 20, attrs) == base.max_for("stamina", 20, attrs)


def test_damage_knob_changes_battle_and_neutral_is_unchanged(library: ContentLibrary) -> None:
    seeds = (0, 1)

    def win_and_rounds(lib: ContentLibrary) -> tuple[float, float]:
        rep = run_batches([map_spec(lib, "open_plain", seeds)], jobs=1)[0]
        return rep.ally_win_rate, rep.rounds_mean

    base = win_and_rounds(library)
    assert win_and_rounds(with_difficulty(library, NEUTRAL)) == base
    assert win_and_rounds(with_difficulty(library, Difficulty(enemy_damage=1000))) == base
    hard = with_difficulty(library, Difficulty(enemy_damage=3000, enemy_hp=1400))
    result = win_and_rounds(hard)
    assert result == win_and_rounds(hard)  # 確定性
    assert result != base
    assert result[0] <= base[0]


def test_parse_combo_and_csv_header() -> None:
    d = parse_combo("enemy_hp=1200, boss_hp=900")
    assert (d.enemy_hp, d.boss_hp, d.mana_cap) == (1200, 900, 1000)
    assert parse_combo("").label == "baseline"
    with pytest.raises(ValueError):
        parse_combo("nope=1")
    assert set(SINGLE_GRID) == set(KNOB_NAMES)
    assert sweep_csv([]).splitlines()[0].startswith(",".join(KNOB_NAMES))
