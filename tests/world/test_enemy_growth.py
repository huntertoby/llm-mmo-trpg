"""敵人依地點建議等級成長（Phase 5A-4 追加 A；``docs/phases/Phase5計畫.md`` 9.3 第 6 項）。"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import make_encounter
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute, Team
from trpg.world.battle import enemy_level, grow_enemy, prepare_battle
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]


def test_tier_table_follows_7_6(library: ContentLibrary) -> None:
    assert library.world_rules is not None
    growth = library.world_rules.enemy_growth
    assert [growth.tier_for(lv) for lv in range(1, 12)] == [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]


def test_level_one_is_the_template(library: ContentLibrary) -> None:
    template = library.units["sect_swordsman"]
    assert grow_enemy(library, template, 1) == (template, ())


def test_level_five_growth(library: ContentLibrary) -> None:
    template = library.units["sect_swordsman"]
    grown, extra = grow_enemy(library, template, 5)
    assert grown.level == 5
    # 最高屬性（力量 14）＋ 2 × 4
    assert grown.attributes[Attribute.STR] == template.attributes[Attribute.STR] + 8
    for attr in (Attribute.DEX, Attribute.CON, Attribute.INT, Attribute.WIS, Attribute.WIL):
        assert grown.attributes[attr] == template.attributes[attr]
    # HP ＋ 基礎 × 5% × 4
    assert grown.max_hp == template.max_hp + template.max_hp * 50 * 4 // 1000
    # 1 階技能升到 2 階：<原 ID>_t2，反應規則跟著改名
    extra_ids = {s.id for s in extra}
    for old, new in zip(template.skills, grown.skills, strict=True):
        if library.skills[old].tier < 2:
            assert new == f"{old}_t2"
            assert new in extra_ids
        else:
            assert new == old
    assert all(s.tier == 2 for s in extra)
    # 反應技跟著改名（持劍弟子在 5A-M1 拿掉挺身而出，改看護法武僧）
    monk = library.units["sect_warrior_monk"]
    grown, _ = grow_enemy(library, monk, 5)
    assert grown.reactions is not None
    assert monk.reactions is not None
    reactions = {r.reaction for r in grown.reactions}
    assert "skill_stand_firm_t2" in reactions
    assert "skill_stand_firm" not in reactions


def test_level_eight_is_tier_three(library: ContentLibrary) -> None:
    _, extra = grow_enemy(library, library.units["mist_wolf"], 8)
    assert extra
    assert all(s.tier == 3 and s.id.endswith("_t3") for s in extra)


def test_ties_go_to_first_attribute(library: ContentLibrary) -> None:
    template = UnitTemplate.model_validate(
        {
            "id": "flat_unit",
            "name_zh": "平",
            "attributes": {a.value: 10 for a in Attribute},
            "max_hp": 20,
            "weapon": "dagger",
        }
    )
    grown, extra = grow_enemy(library, template, 3)
    assert extra == ()
    assert grown.attributes[Attribute.STR] == 14
    assert sum(grown.attributes.values()) == 60 + 4


def test_enemy_level_uses_level_min(library: ContentLibrary) -> None:
    assert enemy_level(library, make_encounter("north_slope", level=5)) == 4
    assert enemy_level(library, make_encounter("sword_tomb", level=5)) == 5
    assert enemy_level(library, make_encounter("bamboo_path", level=2)) == 1


def test_battle_enemies_are_grown(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = make_encounter("sword_tomb", seed=3, level=5, battle_map="ruined_fort")
    char = make_char(location="sword_tomb", pending_encounter=encounter)
    prepared = prepare_battle(library, char)
    assert prepared.enemy_level == 5
    enemies = [u for u in prepared.setup.units if u.team is Team.ENEMY]
    assert enemies
    known = prepared.setup.ruleset.skills.by_id()
    for spawn in enemies:
        assert spawn.template.level == 5
        assert all(s in known for s in spawn.template.skills)
        assert all(known[s].tier >= 2 for s in spawn.template.skills)
