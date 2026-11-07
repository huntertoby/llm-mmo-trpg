"""QK-8：盜賊三套的區域外觀（`content/ui/region_dolls.yaml`）與 NPC 頭像的身分道具欄位（#145）。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.loader import load_content_file
from trpg.content.region_dolls import RegionDollTable
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.content.world_events import NpcCardTable, NpcPortrait

DOLL_FILE = PROJECT_ROOT / "content" / "ui" / "region_dolls.yaml"
UNITS = PROJECT_ROOT / "content" / "units"
NPCS = PROJECT_ROOT / "content" / "world" / "npcs"


def test_the_table_loads_and_is_registered() -> None:
    table = load_content_file(DOLL_FILE, RegionDollTable)
    assert sorted(table.regions) == ["ashen_waste", "cloud_ridge"]
    assert "2 區" in table.summary()
    assert any(
        f.relative_path == "ui/region_dolls.yaml" and f.model is RegionDollTable
        for f in KNOWN_CONTENT_FILES
    )


def test_templates_exist_and_cliff_wears_douli() -> None:
    table = load_content_file(DOLL_FILE, RegionDollTable)
    enemies = PROJECT_ROOT / "content" / "world" / "enemies.yaml"
    variants = {v["id"] for v in yaml.safe_load(enemies.read_text("utf-8"))["variants"]}
    units = {p.stem for p in UNITS.glob("*.yaml")}
    for region, rows in table.regions.items():
        for template in rows:
            assert template in units or template in variants, f"{region}/{template}"
    for template, doll in table.regions["cloud_ridge"].items():
        assert doll.gear["head"].kind == "douli", template
    assert table.doll_for("cloud_ridge", "bandit") is not None
    assert table.doll_for("capital", "bandit") is None
    assert table.doll_for(None, "bandit") is None


@pytest.mark.parametrize(
    ("doll", "msg"),
    [
        ({"main_kind": "axe"}, "武器照範本"),
        ({"creature": {"body": "hound"}}, "creature"),
    ],
)
def test_rejects_weapons_and_creatures(doll: dict[str, Any], msg: str) -> None:
    with pytest.raises(ValidationError, match=msg):
        RegionDollTable.model_validate({"regions": {"cloud_ridge": {"bandit": doll}}})


def test_portrait_takes_held_item_and_element() -> None:
    gear = {
        "main_hand": {"kind": "staff", "material": "wood", "element": "fire"},
        "waist": {"kind": "apron", "trim": "#b07a48"},
        "back": {"kind": "mailbag"},
    }
    p = NpcPortrait.model_validate({"gear": gear})
    assert p.gear["main_hand"].element == "fire"
    with pytest.raises(ValidationError):
        NpcPortrait.model_validate({"gear": {"tail": {"kind": "x"}}})


def test_identity_items_145_are_in_npc_cards() -> None:
    cards = {}
    for path in sorted(NPCS.glob("*.yaml")):
        table = load_content_file(path, NpcCardTable)
        cards.update({c.id: c for c in table.npcs})
    ids: tuple[str, ...] = ("daoist_qingya", "hunter_ayue", "mistlock_master", "scarface")
    ids += ("smith_shi", "smith_lu", "greybeard", "priestess_helin", "overseer_scar")
    held = {}
    for k in ids:
        portrait = cards[k].portrait
        assert portrait is not None
        held[k] = portrait.gear["main_hand"].kind
    assert held == {
        "daoist_qingya": "whisk",
        "hunter_ayue": "bow",
        "mistlock_master": "sword",
        "scarface": "saber",
        "smith_shi": "hammer",
        "smith_lu": "hammer",
        "greybeard": "staff",
        "priestess_helin": "staff",
        "overseer_scar": "hammer",
    }
    master = cards["mistlock_master"].portrait
    assert master is not None
    assert master.gear["off_hand"].kind == "whisk" and "head" not in master.gear
    for smith in ("smith_shi", "smith_lu"):
        portrait = cards[smith].portrait
        assert portrait is not None
        apron = portrait.gear["waist"]
        assert apron.kind == "apron" and apron.material == "leather"
