"""裝備外觀清單（Phase 3G-G5a）：清單、預設、關鍵字推導、物品外觀欄位、前端 JSON 沒有過期。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.appearance import (
    AppearanceTable,
    appearance_export,
    appearance_json,
    derive_keywords,
    item_appearance_problems,
)
from trpg.content.equipment import AffixDef, ItemDef
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.slots import SLOT_TYPES
from trpg.engine.battle import start_battle
from trpg.engine.setup import build_setup
from trpg.engine.view import project_for
from trpg.shared.types import Team

ROOT = Path(__file__).resolve().parents[2]


def _table() -> AppearanceTable:
    return library().appearance or load_content_file(
        default_content_dir() / "equipment" / "appearance.yaml", AppearanceTable
    )


def _item(**fields: Any) -> ItemDef:
    base: dict[str, Any] = {"id": "item_x", "name_zh": "測試", "slot_type": "head"}
    return ItemDef.model_validate({**base, **fields})


# ---------------------------------------------------------------------------
# 清單
# ---------------------------------------------------------------------------


def test_table_covers_every_slot_type() -> None:
    table = _table()
    by_slot = Counter(k.slot_type for k in table.kinds)
    assert set(by_slot) == set(SLOT_TYPES)
    # 美術 PM 的清單（已排除 legacy 的 gun、gloves、bracelet）
    assert by_slot == {
        "weapon": 17,
        "offhand": 4,
        "body": 5,
        "head": 5,
        "hands": 4,
        "feet": 4,
        "neck": 2,
        "ring": 1,
    }
    assert len(table.kinds) == 42
    assert {"gun", "gloves", "bracelet"}.isdisjoint(k.id for k in table.kinds)


def test_table_values_match_the_art_spec() -> None:
    table = _table()
    assert len(table.materials) == 10 and len(table.dyes) == 8
    assert table.rarities == ("common", "uncommon", "rare", "epic", "legendary")
    assert table.styles == ("common",)
    assert table.max_keywords == 2
    assert set(table.element_keywords) == {"ignite", "wet", "charged", "frozen"}
    kinds = table.kind_by_id()
    assert kinds["dual_dagger"].paired and kinds["dual_pistol"].paired
    assert not kinds["dagger"].paired
    # 特例：頭冠預設金、頭巾預設布；臂環預設銅、皮臂甲只能皮
    circlet = kinds["circlet"]
    forms = {f.id: f for f in circlet.forms}
    assert circlet.form_default(forms["crown"]) == "gold"
    assert circlet.form_default(forms["bandana"]) == "cloth"
    assert "iron" not in circlet.form_materials(forms["bandana"])
    bracers = kinds["bracers"]
    bforms = {f.id: f for f in bracers.forms}
    assert bracers.form_default(bforms["ring"]) == "copper"
    assert bracers.form_materials(bforms["leather"]) == ("leather",)
    assert kinds["helmet"].default_material == "iron"
    assert "cloth" not in kinds["helmet"].materials


def test_table_keywords_are_the_24b1_keywords() -> None:
    lib = library()
    assert lib.appearance is not None
    assert set(lib.appearance.keywords) == set(lib.keywords.ids())


def test_table_rejects_bad_data() -> None:
    raw = json.loads(json.dumps(_table().model_dump(mode="json")))
    raw["kinds"][0]["default_material"] = "wood"  # 劍不能用木
    with pytest.raises(ValidationError):
        AppearanceTable.model_validate(raw)
    raw = json.loads(json.dumps(_table().model_dump(mode="json")))
    raw["keywords"].append("ignite")
    with pytest.raises(ValidationError):
        AppearanceTable.model_validate(raw)


# ---------------------------------------------------------------------------
# 物品外觀欄位
# ---------------------------------------------------------------------------


def test_every_authored_item_has_a_legal_look() -> None:
    table = _table()
    items = library().items.values()
    assert items
    for item in items:
        assert item.kind is not None, item.id  # 本專案的物品都寫明外觀
        assert item_appearance_problems(item, table) == [], item.id


def test_item_without_appearance_fields_is_fine() -> None:
    assert item_appearance_problems(_item(), _table()) == []


@pytest.mark.parametrize(
    ("fields", "needle"),
    [
        ({"kind": "no_such_kind"}, "未知的造型"),
        ({"kind": "sword"}, "屬於 weapon"),
        ({"kind": "helmet", "form": "no_such"}, "沒有形制"),
        ({"kind": "helmet", "material": "wood"}, "不在允許內"),
        ({"kind": "hood", "material": "cloth", "dye": "no_such"}, "未知的染色"),
        ({"kind": "helmet", "material": "iron", "dye": "red"}, "染色只對"),
        ({"style": "eastern"}, "未知的風格"),
        ({"rarity": "mythic"}, "未知的稀有度"),
        ({"form": "iron"}, "就要填 kind"),
    ],
)
def test_bad_item_look_is_reported(fields: dict[str, Any], needle: str) -> None:
    problems = item_appearance_problems(_item(**fields), _table())
    assert any(needle in p for p in problems), problems


def test_paired_flag_must_match_the_kind() -> None:
    item = _item(slot_type="weapon", weapon="dagger", kind="dual_dagger")
    assert any("paired" in p for p in item_appearance_problems(item, _table()))


# ---------------------------------------------------------------------------
# 關鍵字推導
# ---------------------------------------------------------------------------


def test_keywords_come_from_affixes() -> None:
    affixes = library().affixes

    def pick(*ids: str) -> list[AffixDef]:
        return [affixes[i] for i in ids]

    assert derive_keywords(pick("affix_kw_burn_duration")) == ("ignite",)
    # 詞條裡暫定的 shock 對照到 3-24b1 的 charged
    assert derive_keywords(pick("affix_kw_shock_area")) == ("charged",)
    assert derive_keywords(pick("affix_attack_lightning")) == ("charged",)
    assert derive_keywords(pick("affix_attack_mark")) == ("marked",)
    # 依詞條順序、去重、最多 2 個
    ids = ("affix_kw_prone_damage", "affix_kw_burn_duration", "affix_kw_shock_area")
    assert derive_keywords(pick(*ids)) == ("prone", "ignite")
    assert derive_keywords(pick("affix_kw_burn_duration", "affix_kw_burn_duration")) == ("ignite",)
    # 其他類別不產生關鍵字
    assert derive_keywords(pick("affix_attr_str", "affix_cost_glass", "affix_max_hp")) == ()


def test_derived_keywords_are_known_to_the_appearance_table() -> None:
    table = _table()
    for affix in library().affixes.values():
        for keyword in derive_keywords([affix]):
            assert keyword in table.keywords, (affix.id, keyword)


# ---------------------------------------------------------------------------
# API 與前端 JSON
# ---------------------------------------------------------------------------


def test_unit_view_carries_the_appearance() -> None:
    lib = library()
    state = start_battle(build_setup(lib, "test_flat_6x6", ["gear_tester"], ["bandit"]), 1)
    hero = next(u for u in project_for(state, Team.ENEMY).units if u.template_id == "gear_tester")
    by_slot = {e.slot: e.appearance for e in hero.equipment}
    assert by_slot["main_hand"].kind == "sword" and by_slot["main_hand"].material == "steel"
    assert by_slot["hands"].dye == "brown"
    assert by_slot["ring_2"].kind == "ring"
    assert all(a.rarity == "common" for a in by_slot.values())
    assert all(a.keywords == () for a in by_slot.values())


def test_client_json_is_up_to_date() -> None:
    table = _table()
    text = (ROOT / "client" / "src" / "render" / "gearAppearance.json").read_text(encoding="utf-8")
    assert text == appearance_json(table), (
        "client/src/render/gearAppearance.json 過期了：uv run python scripts/export_appearance.py"
    )
    assert json.loads(text) == appearance_export(table)
