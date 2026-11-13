"""雲嶺敵人範本、元素變體與精英詞綴（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.2、7.3）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.battle import ReactionRule, UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_enemies import (
    EliteAffixDef,
    EnemyVariantDef,
    WorldEnemies,
    apply_affix,
    apply_variant,
    world_enemies_problems,
)
from trpg.shared.errors import ContentError

CLOUD_RIDGE_UNITS = (
    "sect_acolyte",
    "sect_swordsman",
    "sect_talisman_caster",
    "sect_alchemist",
    "sect_warrior_monk",
    "sect_array_disciple",
    "sect_mist_walker",
    "sect_crane_archer",
    "sect_puppeteer",
    "sect_array_stone",
    "sect_steward",
    "mist_wolf",
    "mountain_leopard",
    "stoneback_bear",
    "thunder_hawk",
    "mist_wraith",
    "shard_golem",
)
VARIANTS = (
    "thunder_talisman_caster",
    "frost_crane_archer",
    "water_alchemist",
    # 5F-5a：灰燼荒原
    "thunder_shell_beetle",
    "scorched_stoneback",
    "ashen_gunner",
    "forge_scar",
    "horned_zealot",
)
AFFIXES = ("regenerating", "mist_veiled", "heart_linked", "berserk", "blazing", "hard_shelled")


def test_cloud_ridge_units_loaded(library: ContentLibrary) -> None:
    for unit_id in CLOUD_RIDGE_UNITS:
        template = library.units[unit_id]
        assert not template.summon
        assert template.doll is not None  # 外觀：5A-ART4（tests/content/test_enemy_looks.py）
    sect = [u for u in CLOUD_RIDGE_UNITS if u.startswith("sect_")]
    assert all("sect" in library.units[u].tags for u in sect)
    assert library.units["sect_steward"].tags.count("elite") == 1
    assert "ranged" in library.units["sect_talisman_caster"].tags
    assert library.units["sect_array_stone"].speed == 0
    assert library.units["sect_array_stone"].ai_profile == "idle"
    assert "flying" in library.units["thunder_hawk"].tags


def test_variants_and_affixes_loaded(library: ContentLibrary) -> None:
    enemies = library.world_enemies
    assert enemies is not None
    assert tuple(v.id for v in enemies.variants) == VARIANTS
    assert tuple(a.id for a in enemies.affixes) == AFFIXES
    assert enemies.summary() == "8 種元素變體、6 種精英詞綴"
    rel = [p.relative_to(library.root).as_posix() for p, _ in library.files]
    assert "world/enemies.yaml" in rel


def test_apply_variant(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    thunder = catalog.template("thunder_talisman_caster")
    base = library.units["sect_talisman_caster"]
    assert thunder.id == "thunder_talisman_caster"
    assert thunder.name_zh == "雷符師"
    assert thunder.weapon == "lightning_staff"
    # RG-1（#162）：寒鎖換成瞄準預告的定身符
    assert thunder.skills == ("skill_binding_talisman", "skill_static_palm")
    assert base.skills == ("skill_binding_talisman", "skill_hush")  # 5A-4 追加 B：純控制
    assert thunder.max_hp == base.max_hp
    assert thunder.tags == base.tags
    frost = catalog.template("frost_crane_archer")
    assert frost.weapon == "bow"
    assert "skill_frost_feather" in frost.skills  # CB-2a：無條件緩速
    assert "skill_rng_hawkeye_mark" not in frost.skills


def test_apply_variant_swaps_reaction_rule() -> None:
    base = UnitTemplate.model_validate(
        {
            "id": "base_unit",
            "name_zh": "底",
            "attributes": {a: 10 for a in ("str", "dex", "con", "int", "wis", "wil")},
            "max_hp": 10,
            "weapon": "dagger",
            "skills": ["skill_rx_slip_away"],
            "reactions": [{"reaction": "skill_rx_slip_away", "when": {"event": "hit_by_attack"}}],
        }
    )
    variant = EnemyVariantDef(
        id="v",
        base="base_unit",
        name_zh="變",
        theme="ice",
        skill_swaps={"skill_rx_slip_away": "skill_reflex_ward"},
    )
    result = apply_variant(base, variant)
    assert result.skills == ("skill_reflex_ward",)
    assert result.reactions is not None
    assert result.reactions[0].reaction == "skill_reflex_ward"
    with pytest.raises(ValueError, match="沒有裝備"):
        apply_variant(base, variant.model_copy(update={"skill_swaps": {"skill_x": "skill_y"}}))


def test_apply_affix(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    wolf = library.units["mist_wolf"]
    berserk = catalog.with_affix(wolf, "berserk")
    assert berserk.id == "mist_wolf_berserk"
    assert berserk.name_zh == "狂暴的霧狼"
    assert "elite" in berserk.tags
    assert berserk.tags == tuple(sorted(berserk.tags))
    assert berserk.max_hp == wolf.max_hp * 1500 // 1000
    assert berserk.skills == (*wolf.skills, "skill_berserker_rage")
    assert berserk.reactions == wolf.reactions  # 沒有加反應規則就不展開預設


def test_apply_affix_expands_default_reactions(library: ContentLibrary) -> None:
    rule = ReactionRule.model_validate(
        {"reaction": "skill_rx_slip_away", "when": {"event": "hit_by_attack"}}
    )
    affix = EliteAffixDef(
        id="slippery",
        name_zh="滑溜的",
        add_skills=("skill_rx_slip_away",),
        add_reactions=(rule,),
    )
    wolf = library.units["mist_wolf"]
    assert wolf.reactions is None
    defaults = library.ruleset.reactions.default_rules
    slippery = apply_affix(wolf, affix, defaults)
    assert slippery.reactions is not None
    assert slippery.reactions[: len(defaults)] == defaults
    assert slippery.reactions[-1].reaction == "skill_rx_slip_away"
    catalog = library.enemy_catalog()
    walker = library.units["sect_mist_walker"]
    assert walker.reactions is not None
    regen = catalog.with_affix(walker, "regenerating")
    assert regen.reactions == walker.reactions


def test_mist_veiled_is_opening_concealment(library: ContentLibrary) -> None:
    """5A-M1：霧隱的＝開場隱蔽 1 回合，不加反應；#149 起多帶一招霧遁。"""
    wolf = library.units["mist_wolf"]
    veiled = library.enemy_catalog().with_affix(wolf, "mist_veiled")
    assert veiled.reactions is None
    assert veiled.skills == (*wolf.skills, "skill_mist_shift")
    assert [(o.status, o.duration) for o in veiled.opening_statuses] == [("concealed", 1)]


def test_apply_affix_hp_floor() -> None:
    tiny = UnitTemplate.model_validate(
        {
            "id": "tiny",
            "name_zh": "小",
            "attributes": {a: 10 for a in ("str", "dex", "con", "int", "wis", "wil")},
            "max_hp": 1,
            "weapon": "dagger",
        }
    )
    affix = EliteAffixDef(id="a", name_zh="強的", hp_permille=1500)
    assert apply_affix(tiny, affix, ()).max_hp == 1


def test_affix_problem(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    archer = library.units["sect_crane_archer"]
    assert catalog.affix_problem(archer, "berserk") is not None  # 限近戰
    assert catalog.affix_problem(library.units["sect_steward"], "regenerating") is not None
    assert catalog.affix_problem(library.units["sect_array_stone"], "regenerating") is not None
    # 5A-M1：霧隱的只加開場隱蔽，霧行者、持劍弟子都能套
    assert catalog.affix_problem(library.units["sect_mist_walker"], "mist_veiled") is None
    assert catalog.affix_problem(library.units["sect_swordsman"], "mist_veiled") is None
    assert catalog.affix_problem(library.units["mist_wolf"], "berserk") is None
    assert catalog.applicable_affixes(archer, AFFIXES) == [
        "regenerating",
        "mist_veiled",
        "heart_linked",
    ]


def test_has_and_template(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    assert catalog.has("mist_wolf")
    assert catalog.has("water_alchemist")
    assert not catalog.has("summon_golem")  # 召喚物不能直接當敵人
    assert not catalog.has("nobody")
    with pytest.raises(KeyError):
        catalog.template("nobody")
    with pytest.raises(KeyError):
        catalog.affix("nobody")
    assert catalog.is_ranged(library.units["sect_talisman_caster"])
    assert catalog.is_ranged(library.units["bandit_archer"])
    assert not catalog.is_ranged(library.units["sect_alchemist"])


def _enemies(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "variants": [
            {
                "id": "v1",
                "base": "sect_talisman_caster",
                "name_zh": "變",
                "theme": "lightning",
                "skill_swaps": {"skill_binding_talisman": "skill_spark_chain"},  # RG-1 換招
            }
        ],
        "affixes": [{"id": "a1", "name_zh": "強的", "add_skills": ["skill_steady_breath"]}],
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    ("variant", "fragment"),
    [
        ({"skill_swaps": {}}, "沒有換武器也沒有換技能"),
        ({"id": "sect_talisman_caster"}, "不可等於 base"),
        ({"skill_swaps": {"skill_a": "skill_a"}}, "新舊相同"),
        ({"skill_swaps": {"skill_a": "skill_c", "skill_b": "skill_c"}}, "不可重複"),
        ({"skill_swaps": {"bad": "skill_c"}}, "skill_xxx"),
        ({"theme": "plasma"}, "theme"),
    ],
)
def test_variant_schema(variant: dict[str, Any], fragment: str) -> None:
    data = _enemies()
    data["variants"][0].update(variant)
    with pytest.raises(ValidationError, match=fragment):
        WorldEnemies.model_validate(data)


def test_schema_duplicates_and_stray_reaction() -> None:
    data = _enemies()
    data["affixes"].append(dict(data["affixes"][0]))
    with pytest.raises(ValidationError, match="詞綴 ID 重複"):
        WorldEnemies.model_validate(data)
    stray = {
        "id": "a2",
        "name_zh": "怪的",
        "add_reactions": [{"reaction": "skill_rx_slip_away", "when": {"event": "hit_by_attack"}}],
    }
    with pytest.raises(ValidationError, match="沒有加上的反應技"):
        WorldEnemies.model_validate(_enemies(affixes=[stray]))


@pytest.mark.parametrize(
    ("variant", "fragment"),
    [
        ({"base": "nobody"}, "未知的 base"),
        ({"base": "summon_golem"}, "未知的 base"),
        ({"skill_swaps": {"skill_cleave": "skill_spark_chain"}}, "base 沒有裝備"),
        ({"skill_swaps": {"skill_binding_talisman": "skill_nothing"}}, "未知的技能"),
        ({"weapon": "laser"}, "未知的武器"),
        ({"id": "mist_wolf"}, "ID 和單位範本重複"),
    ],
)
def test_cross_file_problems(
    library: ContentLibrary, variant: dict[str, Any], fragment: str
) -> None:
    data = _enemies()
    data["variants"][0].update(variant)
    enemies = WorldEnemies.model_validate(data)
    problems = world_enemies_problems(
        enemies,
        units={**library.units, **{s.id: s.template for s in library.ruleset.summons.summons}},
        weapons=library.weapons,
        skills=library.skills,
    )
    assert any(fragment in p for p in problems), problems


def test_unknown_affix_skill(library: ContentLibrary) -> None:
    enemies = WorldEnemies.model_validate(
        _enemies(affixes=[{"id": "a1", "name_zh": "強的", "add_skills": ["skill_nothing"]}])
    )
    problems = world_enemies_problems(
        enemies, units=library.units, weapons=library.weapons, skills=library.skills
    )
    assert problems == ["詞綴 a1：未知的技能 skill_nothing"]


def test_real_file_has_no_problems(library: ContentLibrary) -> None:
    assert library.world_enemies is not None
    problems = world_enemies_problems(
        library.world_enemies, units=library.units, weapons=library.weapons, skills=library.skills
    )
    assert problems == []


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def test_variant_breaking_unit_rules_is_rejected(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "enemies.yaml"
    # 弓的技能換到法杖上：套用後的範本武器不相容
    text = path.read_text(encoding="utf-8").replace(
        "weapon: lightning_staff\n    skill_swaps: {skill_hush: skill_static_palm}",
        "weapon: lightning_staff\n    skill_swaps: {skill_hush: skill_high_ground_shot}",
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    with pytest.raises(ContentError, match=r"enemies\.yaml"):
        load_library(content)


def test_without_enemies_file(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    (content / "world" / "enemies.yaml").unlink()
    shutil.rmtree(content / "world" / "encounters")
    lib = load_library(content)
    assert lib.world_enemies is None
    assert lib.world_encounters == {}
    assert not lib.enemy_catalog().has("water_alchemist")
