"""鐵匠與附魔台、共鳴的內容（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.2）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import load_content_file
from trpg.content.world_crafting import (
    CRAFTING_FILE,
    RESONANCE_FILE,
    CraftingRules,
    ResonanceRules,
    crafting_problems,
    resonance_problems,
)
from trpg.content.world_events import NpcCardTable
from trpg.shared.errors import ContentError


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _raw(library: ContentLibrary) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((library.root / CRAFTING_FILE).read_text("utf-8"))
    return data


def _problems(library: ContentLibrary, data: dict[str, Any]) -> list[str]:
    rules = CraftingRules.model_validate(data)
    locations = {
        r: {loc.id: loc.kind for loc in m.locations} for r, m in library.world_maps.items()
    }
    npcs = {
        r: {n.id: n.location for n in t.npcs} for r, t in library.world_event_content.npcs.items()
    }
    return crafting_problems(
        rules,
        locations=locations,
        npcs=npcs,
        items=library.world_economy.items,
        affixes=library.affixes,
        keywords={k.id for k in library.keywords.keywords},
    )


def test_cloud_ridge_loaded(library: ContentLibrary) -> None:
    rules = library.world_crafting
    assert rules is not None
    assert {s.kind for s in rules.stations} == {"smithy", "enchanter"}
    assert {h.name_zh for h in rules.hidden} == {"驚雷霧袍", "蒸汽護腕", "冰火雙生戒"}
    robe = rules.hidden_for(
        "body", ["item_talisman_ash", "item_thunder_feather", "item_mist_crystal"]
    )
    assert robe is not None and robe.affix == "affix_unique_thunder_mist"
    assert rules.craft.grade_cap == {"coarse": 3, "fine": 7, "superior": 10}
    assert library.world_resonance is not None and library.world_resonance.pieces == 2
    gen = library.item_gen
    assert gen is not None and {h.affix for h in rules.hidden} <= set(gen.unique_affixes)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["stations"][0].update(location="nowhere"), "沒有地點 nowhere"),
        (
            lambda d: d["stations"][0].update(npc="shopkeeper_liu", location="mist_temple_gate"),
            "不在",
        ),
        (lambda d: d["materials"].update(item_hp_potion_small={}), "不是 world/items.yaml 的材料"),
        (lambda d: d["materials"].update(item_coarse_material={}), "通用料不能當特色材料"),
        (
            lambda d: d["materials"]["item_mist_crystal"].update(leanings=["affix_nope"]),
            "未知的詞條",
        ),
        (lambda d: d["materials"]["item_mist_crystal"].update(resonance="nope"), "未知的關鍵字"),
        (lambda d: d["hidden"][0].update(affix="affix_unique_frostfire"), "不能掛在 body"),
        (lambda d: d["hidden"][0].update(materials=["item_coarse_material"]), "不是特色材料"),
    ],
)
def test_bad_crafting_data(library: ContentLibrary, mutate: Any, message: str) -> None:
    data = _raw(library)
    mutate(data)
    assert any(message in p for p in _problems(library, data))


def test_duplicate_hidden_rejected(library: ContentLibrary) -> None:
    data = _raw(library)
    data["hidden"].append({**data["hidden"][0], "id": "recipe_copy"})
    with pytest.raises(ValueError, match="組合相同"):
        CraftingRules.model_validate(data)


def test_bad_resonance_data(library: ContentLibrary) -> None:
    raw: dict[str, Any] = yaml.safe_load((library.root / RESONANCE_FILE).read_text("utf-8"))
    raw["resonances"][0]["keyword"] = "nope"
    raw["resonances"][1]["affixes"] = [{"affix": "affix_attr_str", "value": 99}]
    problems = resonance_problems(
        ResonanceRules.model_validate(raw),
        affixes=library.affixes,
        keywords={k.id for k in library.keywords.keywords},
    )
    assert any("未知的關鍵字" in p for p in problems)
    assert any("超出範圍" in p for p in problems)


def test_missing_files_turn_off(tmp_path: Path, library: ContentLibrary) -> None:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    (root / CRAFTING_FILE).unlink()
    (root / RESONANCE_FILE).unlink()
    bare = load_library(root)
    assert bare.world_crafting is None and bare.world_resonance is None


def test_bad_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    data = _raw(library)
    data["stations"][0]["region"] = "nowhere"
    (root / CRAFTING_FILE).write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")
    with pytest.raises(ContentError, match="沒有地點圖"):
        load_library(root)


# ---------------------------------------------------------------------------
# 5D-3b：隱藏配方的提示（20.4）與荒原的待接人設卡（19.5）
# ---------------------------------------------------------------------------


def test_hidden_recipe_hints(library: ContentLibrary) -> None:
    rules = library.world_crafting
    assert rules is not None
    tavern = rules.hints_at("ashen_waste", "ember_market", "tavern")
    assert [(h.name_zh, t.text_zh) for h, t in tavern] == [("蒸汽護腕", "霧與火相遇之處")]
    rumor = rules.hints_at("ashen_waste", source="rumor")
    assert [(h.name_zh, t.text_zh) for h, t in rumor] == [("冰火雙生戒", "冰與火在同一隻蜥蜴身上")]
    assert [h.name_zh for h, _ in rules.hints_at("cloud_ridge")] == ["驚雷霧袍"]
    assert "ashen_waste" not in library.world_maps  # 荒原地點圖到位時，提示的地點會被檢查


def test_hint_location_checked_when_map_exists(library: ContentLibrary) -> None:
    data = _raw(library)
    data["hidden"][0]["hints"][0]["location"] = "nowhere"
    assert any("提示的地點 nowhere" in p for p in _problems(library, data))


def test_pending_ashen_npc_card(library: ContentLibrary) -> None:
    table = load_content_file(library.root / "world/pending/ashen_waste.yaml", NpcCardTable)
    smith = table.npc_by_id()["smith_lu"]
    assert smith.name_zh == "爐叔" and smith.role_zh == "鐵匠"
    assert "ashen_waste" not in library.world_event_content.npcs  # 不接店、不載入
