"""Phase 5A-ART：敵人外觀資料（`docs/art/敵人外觀.md` 第 3 節、Phase5計畫第 42 節）。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.battle import CreatureLook, DollLook
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_enemies import EnemyVariantDef, apply_variant

# 第 3 節「第 4 段補充」的單位 ID 對照表（＋第 2 節的雲嶺野獸、源晶造物、陣眼石靈）。
CREATURES: dict[str, dict[str, Any]] = {
    "ember_lizard": {"body": "lizard", "material": "magma", "size": "small"},
    "heart_ember_lizard": {"body": "lizard", "material": "magma", "size": "small"},
    "frost_ember_lizard": {
        "body": "lizard",
        "material": "magma",
        "element": "ice",
        "size": "small",
    },
    "lava_beetle": {"body": "crawler", "variant": "beetle", "material": "magma"},
    "fire_dust_bat": {"body": "flyer", "variant": "bat", "material": "magma"},
    "magma_slug": {"body": "ooze", "material": "magma", "traits": ("core",)},
    "lava_tortoise": {"body": "shell", "material": "magma", "traits": ("volcano",)},
    "scorched_colossus": {
        "body": "golem",
        "material": "stone",
        "tint": "#5a4e48",
        "element": "fire",
        "traits": ("core",),
    },
    "furnace_matriarch": {
        "body": "lizard",
        "material": "magma",
        "size": "large",
        "traits": ("brood", "core"),
    },
    "sulfur_beast": {
        "body": "boar",
        "material": "fur",
        "tint": "#8a7a3a",
        "element": "poison",
        "traits": ("smoke",),
    },
    "molten_lord": {
        "body": "crawler",
        "variant": "beetle",
        "material": "magma",
        "size": "large",
        "traits": ("lava_pool",),
    },
    "ashen_heart": {
        "body": "wisp",
        "material": "crystal",
        "element": "fire",
        "size": "huge",
        "traits": ("core",),
        "status_traits": {"molten_shell": ("crust",)},
    },
    "molten_wraith": {"body": "wraith", "material": "mist", "element": "fire"},
    "rift_crystal_golem": {"body": "golem", "material": "crystal", "element": "lightning"},
    "rift_shard_lord": {
        "body": "golem",
        "material": "crystal",
        "size": "huge",
        "traits": ("core",),
    },
    "rift_pillar_mist": {"body": "pylon", "material": "crystal", "element": "wind"},
    "rift_pillar_thunder": {"body": "pylon", "material": "crystal", "element": "lightning"},
    "rift_pillar_fire": {"body": "pylon", "material": "crystal", "element": "fire"},
    "ash_hound": {"body": "hound", "material": "magma"},
    "mist_wolf": {"body": "hound", "material": "fur", "tint": "#c8ccd0", "traits": ("mist",)},
    "mountain_leopard": {"body": "feline", "material": "fur", "traits": ("spots",)},
    "stoneback_bear": {
        "body": "bear",
        "material": "fur",
        "element": "earth",
        "traits": ("stone_back",),
    },
    "thunder_hawk": {
        "body": "flyer",
        "variant": "bird",
        "material": "fur",
        "tint": "#c8d8f0",
        "element": "lightning",
        "traits": ("sparks",),
    },
    "mist_wraith": {"body": "wraith", "material": "mist", "element": "shadow"},
    "shard_golem": {"body": "golem", "material": "crystal", "element": "lightning"},
    "sect_array_stone": {"body": "pylon", "material": "stone"},
    "sect_summit_array_stone": {"body": "pylon", "material": "stone"},
}
BOSSES = ("ashen_heart", "rift_shard_lord", "sect_mist_lock_master")
SECTS = (
    "sect_acolyte",
    "sect_swordsman",
    "sect_talisman_caster",
    "sect_alchemist",
    "sect_warrior_monk",
    "sect_array_disciple",
    "sect_mist_swordsman",
    "sect_mist_walker",
    "sect_crane_archer",
    "sect_puppeteer",
    "sect_steward",
    "sect_mist_lock_master",
)


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.mark.parametrize("unit_id", sorted(CREATURES))
def test_creature_table(library: ContentLibrary, unit_id: str) -> None:
    doll = library.units[unit_id].doll
    assert doll is not None and doll.creature is not None
    assert doll.creature == CreatureLook.model_validate(CREATURES[unit_id])


def test_heart_lizard_matches_ember_lizard(library: ContentLibrary) -> None:
    assert library.units["heart_ember_lizard"].doll == library.units["ember_lizard"].doll


def test_bosses_have_legendary_glow_and_only_bosses(library: ContentLibrary) -> None:
    glowing = sorted(
        u.id
        for u in library.units.values()
        if u.doll is not None and u.doll.rarity is not None and "boss" not in u.tags
    )
    # 舊的 roguelite 頭目（bandit_boss 等）沿用既有的史詩外光
    assert all(u.startswith("bandit_") for u in glowing), glowing
    for unit_id in BOSSES:
        doll = library.units[unit_id].doll
        assert doll is not None and doll.rarity == "legendary"


@pytest.mark.parametrize("unit_id", SECTS)
def test_sects_have_humanoid_dolls(library: ContentLibrary, unit_id: str) -> None:
    doll = library.units[unit_id].doll
    assert doll is not None and doll.creature is None
    body = doll.gear["body"]
    assert body.kind == "robe" or (unit_id == "sect_warrior_monk" and body.kind == "bare")


def test_sect_parts(library: ContentLibrary) -> None:
    alchemist = library.units["sect_alchemist"].doll
    assert alchemist is not None
    assert alchemist.gear["body"].apron == "#e8dcc0"
    assert alchemist.gear["back"].kind == "gourd"
    assert alchemist.main_kind == "whisk"
    steward = library.units["sect_steward"].doll
    assert steward is not None and steward.affixes == ("regen",) and steward.beard
    master = library.units["sect_mist_lock_master"].doll
    assert master is not None and master.traits == ("mist",)
    assert master.gear["off_hand"].kind == "sword"


def test_affix_looks_reach_doll(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    assert library.world_enemies is not None
    looks = {a.id: a.look for a in library.world_enemies.affixes}
    assert looks == {
        "regenerating": "regen",
        "mist_veiled": "mist_hidden",
        "heart_linked": "linked",
        "berserk": "berserk",
        "blazing": "blazing",
        "hard_shelled": "hardshell",
    }
    lord = catalog.with_affix(library.units["molten_lord"], "hard_shelled")
    assert lord.doll is not None and lord.doll.affixes == ("hardshell",)
    assert lord.doll.creature == library.units["molten_lord"].doll.creature  # type: ignore[union-attr]
    # 套兩次同一個外觀不重複
    again = catalog.with_affix(lord, "hard_shelled")
    assert again.doll is not None and again.doll.affixes == ("hardshell",)


def test_affix_without_doll_adds_nothing(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    bare = library.units["mist_wolf"].model_copy(update={"doll": None})
    assert catalog.with_affix(bare, "berserk").doll is None


def test_variant_doll_overrides_base(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    thunder = catalog.template("thunder_talisman_caster")
    assert thunder.doll is not None
    assert thunder.doll.gear["body"].color == "#3c4248"
    assert thunder.doll.traits == ("sparks",)
    beetle = catalog.template("thunder_shell_beetle")
    assert beetle.doll is not None and beetle.doll.creature is not None
    assert beetle.doll.creature.element == "lightning"
    # 沒寫 doll 的變體沿用 base
    gunner = catalog.template("ashen_gunner")
    assert gunner.doll == library.units["bandit_archer"].doll


def test_variant_without_doll_keeps_base() -> None:
    base = load_library().units["sect_alchemist"]
    variant = EnemyVariantDef.model_validate(
        {
            "id": "x_alchemist",
            "base": "sect_alchemist",
            "name_zh": "測試",
            "theme": "fire",
            "skill_swaps": {base.skills[0]: "skill_fire_bolt"},
        }
    )
    assert apply_variant(base, variant).doll == base.doll


def test_summon_creature_written_into_template(library: ContentLibrary) -> None:
    whelp = library.ruleset.summons.by_id()["summon_ember_whelp"].template
    assert whelp.doll is not None and whelp.doll.creature is not None
    assert whelp.doll.creature.model_dump(exclude_defaults=True) == {
        "body": "lizard",
        "material": "magma",
        "size": "tiny",
    }
    assert whelp.look is not None and whelp.look.body == "beast"  # 舊前端的退回照舊
    wolf = library.ruleset.summons.by_id()["summon_war_wolf"].template
    assert wolf.doll is None


def test_creature_schema_accepts_unknown_values_but_checks_format() -> None:
    look = CreatureLook.model_validate(
        {"body": "dragon_unknown", "material": "lava_unknown", "size": "giant", "traits": ["nope"]}
    )
    assert look.body == "dragon_unknown"
    for bad in (
        {"body": "Bad Body"},
        {"body": "hound", "tint": "red"},
        {"body": "hound", "traits": ["X"]},
        {"body": "hound", "status_traits": {"Bad": ["crust"]}},
        {"body": "hound", "color": "#ffffff"},
    ):
        with pytest.raises(ValidationError):
            CreatureLook.model_validate(bad)


def test_doll_skin_optional_and_new_fields() -> None:
    doll = DollLook.model_validate(
        {
            "creature": {"body": "hound"},
            "hair": "bun",
            "gear": {"back": {"kind": "gourd", "material": "wood"}},
        }
    )
    assert doll.skin == "#f1c9a5"
    with pytest.raises(ValidationError):
        DollLook.model_validate({"gear": {"tail": {"kind": "x", "material": "wood"}}})
