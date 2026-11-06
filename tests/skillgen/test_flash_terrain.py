"""Phase 3W-2b 第 3 點：地形變化模板（4～6 格 2 階、7 格以上 3 階，#58）。

行為一致：套用結果的形狀格數落在模板範圍、通過驗證器（含地形格數的稀有度門檻）、預算比例在窗內；
放進戰鬥真的改了那麼多格的高度。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1
from trpg.content.skills import ShapeSpec, SkillDef
from trpg.engine import UseSkill, resolve
from trpg.engine.events import TerrainChanged
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_derive import apply_variation, at_tier
from trpg.skillgen.flash_offer import FlashRequest, UsageSource
from trpg.skillgen.flash_ops import cell_count
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

MID = "terrain_mid"
WIDE = "terrain_wide"


def _terrain_skill(primitive: str, shape: dict[str, object] | None = None) -> SkillDef:
    """內容裡的升降地形技能，形狀換成 ``shape``（預設單格）。"""
    source = library().skills["skill_sinkhole"]
    effects = [source.effects[0].model_copy(update={"type": primitive})]
    return source.model_copy(
        update={
            "shape": ShapeSpec.model_validate(shape or {"type": "ground_tile", "range": 4}),
            "effects": tuple(effects),
        }
    )


def _variations(template_id: str) -> list[Variation]:
    template = library().flash.minor_template(template_id)
    assert template is not None
    return [
        Variation(source="minor", template=template_id, category="area", shape=shape)
        for shape in template.shapes
    ]


def _apply(skill: SkillDef, variation: Variation, tier: int, bonus: int = 40) -> SkillDef | None:
    return apply_variation(library(), at_tier(skill, tier), variation, bonus=bonus, rng=Rng(2))


def test_templates_are_in_the_data_with_the_decided_tiers_and_bands() -> None:
    table = library().flash
    mid, wide = table.minor_template(MID), table.minor_template(WIDE)
    assert mid is not None and wide is not None
    assert (mid.min_tier, mid.min_cells, mid.max_cells) == (2, 4, 6)
    assert (wide.min_tier, wide.min_cells, wide.max_cells) == (3, 7, None)
    lib = library()
    for template in (mid, wide):
        for shape in template.shapes:
            cells = cell_count(shape, lib)
            assert cells is not None and cells >= (template.min_cells or 1)
            assert template.max_cells is None or cells <= template.max_cells


@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_mid_template_grows_a_single_tile_to_four_to_six_cells(primitive: str) -> None:
    lib = library()
    skill = _terrain_skill(primitive)
    assert cell_count(skill.shape, lib) == 1
    done = [_apply(skill, v, 2) for v in _variations(MID)]
    made = [d for d in done if d is not None]
    assert made, "2 階的 4～6 格地形變化做不出來"
    for result in made:
        cells = cell_count(result.shape, lib)
        assert cells is not None and 4 <= cells <= 6
        assert validate_skill(result, lib) == []  # 含 #58 地形格數的稀有度門檻
        report = skill_budget(result, lib)
        assert report.min_ratio <= report.ratio <= report.max_ratio
        assert {e.type for e in result.effects} >= {primitive}


@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_wide_template_reaches_seven_or_more_cells_at_tier_three(primitive: str) -> None:
    lib = library()
    skill = _terrain_skill(primitive)
    made = [d for v in _variations(WIDE) if (d := _apply(skill, v, 3)) is not None]
    assert made, "3 階的 7 格以上地形變化做不出來"
    for result in made:
        cells = cell_count(result.shape, lib)
        assert cells is not None and cells >= 7
        assert result.rarity in ("epic", "legendary")  # #58：7 格以上最低史詩
        assert validate_skill(result, lib) == []
        report = skill_budget(result, lib)
        assert report.min_ratio <= report.ratio <= report.max_ratio


def test_templates_only_apply_to_terrain_skills_and_only_grow() -> None:
    lib = library()
    bolt = next(
        s for s in sorted(lib.skills.values(), key=lambda s: s.id) if s.id.endswith("fire_bolt")
    )
    for variation in (*_variations(MID), *_variations(WIDE)):
        assert _apply(bolt, variation, 3) is None
    # 已經夠大的地形技能不會被「縮小」或原地不動
    big = _terrain_skill("raise_terrain", {"type": "square3", "range": 4})
    for variation in _variations(MID):
        assert _apply(big, variation, 3) is None


def test_offers_respect_the_role_tier() -> None:
    lib = library()
    skill = _terrain_skill("lower_terrain")
    source = UsageSource()
    for tier, expected in ((1, set()), (2, {MID}), (3, {MID, WIDE})):
        request = FlashRequest(at_tier(skill, tier), acquire(skill.id), SkillUsage(), 5, tier=tier)
        found = {
            v.template
            for v in source.ranked(lib, request, "area", at_tier(skill, tier))
            if v.template in (MID, WIDE)
        }
        assert found == expected, (tier, found)


@pytest.mark.parametrize(("template_id", "tier"), [(MID, 2), (WIDE, 3)])
def test_card_matches_the_battle_number_of_changed_tiles(template_id: str, tier: int) -> None:
    """卡片（形狀格數）＝實戰：放進戰鬥施放，改了高度的格數就是形狀的格數（空曠平地）。"""
    lib = library()
    skill = _terrain_skill("raise_terrain")
    result = next(
        d for v in _variations(template_id) if (d := _apply(skill, v, tier, bonus=40)) is not None
    )
    cells = cell_count(result.shape, lib)
    played = result.model_copy(update={"id": "skill_t_terrain_flash"})
    m = make_map(FLAT7, ally=[(3, 6)], enemy=[(6, 0)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (3, 6), caster_template([played], max_hp=99)),
                spawn(Team.ENEMY, (6, 0), no_reactions(max_hp=99)),
            ],
            skills=[played],
        ),
        U1,
    )
    outcome = resolve(state, UseSkill(unit_id=U1, skill_id=played.id, target_pos=Pos(x=3, y=3)))
    changed = [e for e in outcome.events if isinstance(e, TerrainChanged)]
    assert cells is not None
    if result.shape.type == "allies_in_radius":  # 以施放者為中心，邊緣會被地圖切掉
        assert 1 <= len(changed) <= cells
    else:
        assert len(changed) == cells
    assert all(e.height_after == e.height_before + 1 for e in changed)
