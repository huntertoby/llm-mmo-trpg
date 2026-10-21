"""Phase 3-15：格子資訊卡的靜態說明（地形、表面、物件）。"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from trpg.content.environment import OBJECT_TAGS, ObjectDef
from trpg.content.library import ContentLibrary, load_library
from trpg.narrative.tile_info import (
    OBJECT_TAG_TEXT,
    OUTCOME_TEXT,
    TERM_DEADLY,
    object_rules,
    surface_rules,
    terrain_rules,
    unknown_terms,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _object(library: ContentLibrary, id_: str) -> str:
    obj = next(o for o in library.ruleset.objects.objects if o.id == id_)
    return "\n".join(object_rules(obj, library))


def _surface(library: ContentLibrary, id_: str) -> str:
    s = next(s for s in library.ruleset.surfaces.surfaces if s.id.value == id_)
    return "\n".join(surface_rules(s, library))


def test_every_terrain_surface_object_has_rules(library: ContentLibrary) -> None:
    rs = library.ruleset
    for t in rs.terrain.terrain:
        assert terrain_rules(t, rs), t.id
    for s in rs.surfaces.surfaces:
        assert surface_rules(s, library), s.id
    for o in rs.objects.objects:
        assert object_rules(o, library), o.id


def test_all_object_tags_have_text() -> None:
    assert set(OBJECT_TAGS) <= set(OBJECT_TAG_TEXT)


def test_unknown_terms_is_a_warning_not_an_error(library: ContentLibrary) -> None:
    unknown = unknown_terms(library)
    for item in unknown:
        warnings.warn(f"沒有中文對照：{item}", stacklevel=1)
    assert unknown == ()  # 目前內容全部都有對照


def test_unknown_tag_shows_its_raw_name(library: ContentLibrary) -> None:
    fake = ObjectDef.model_construct(
        id="fake",
        name_zh="假物",
        glyph="f",
        max_hp=None,
        tags=("mystery_tag",),
        explosion=None,
        spill=None,
    )
    assert object_rules(fake, library) == ("mystery_tag",)
    ops = {x.op for r in library.ruleset.interactions.rules for x in r.then}
    assert ops <= set(OUTCOME_TEXT)


def test_terrain_texts(library: ContentLibrary) -> None:
    rs = library.ruleset
    by_id = rs.terrain.by_id()
    assert terrain_rules(by_id["stone"], rs) == ("可通行",)
    chasm = "".join(terrain_rules(by_id["chasm"], rs))
    assert TERM_DEADLY in chasm and "不可通行" in chasm
    assert "擋視線" in "".join(terrain_rules(by_id["wall"], rs))


def test_ice_water_oil_smoke(library: ContentLibrary) -> None:
    ice = _surface(library, "ice")
    assert "敏捷檢定" in ice and "滑倒" in ice and "火焰：變成水" in ice and "之後變成水" in ice
    water = _surface(library, "water")
    assert "雷電：沿相連的水" in water and "冰霜：變成冰" in water
    oil = _surface(library, "oil")
    assert "可燃" in oil and "火焰：變成火焰" in oil
    smoke = _surface(library, "smoke")
    assert "擋視線" in smoke and "隱蔽" in smoke and "風：消失" in smoke


def test_crate_pillar_barrel_ice_wall(library: ContentLibrary) -> None:
    crate = _object(library, "crate")
    for word in ("可推動", "半掩護", "可燃", "可被穿透", "風：被推動"):
        assert word in crate
    pillar = _object(library, "stone_pillar")
    assert "可推倒" in pillar and "擋視線" in pillar and "風：被推倒" in pillar
    barrel = _object(library, "oil_barrel")
    assert "碰火爆炸" in barrel and "3×3" in barrel and "漏出油" in barrel
    assert "火焰：爆炸" in barrel
    assert "點燃" not in barrel  # 同一次觸及只套用第一條規則（爆炸）
    wall = _object(library, "ice_wall")
    assert "遇火融化" in wall and "火焰：融化消失" in wall


def test_legend_uses_the_same_terms(library: ContentLibrary) -> None:
    legend = (ROOT / "client/src/battle/legend.ts").read_text(encoding="utf-8")
    assert TERM_DEADLY in legend
    chasm = library.ruleset.terrain.by_id()["chasm"]
    assert TERM_DEADLY in "".join(terrain_rules(chasm, library.ruleset))
