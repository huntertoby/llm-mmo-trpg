"""經濟內容（Phase 5D-1；``content/world/economy.yaml``、``items.yaml``、``shops/``；
08 8.15、8.17、8.26.1）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_economy import (
    COARSE_MATERIAL,
    EconomyRules,
    WorldItemDef,
    WorldItemTable,
    load_world_economy,
)
from trpg.shared.errors import ContentError

REGIONS = {"cloud_ridge"}
NPCS = {"cloud_ridge": {"shopkeeper_liu"}}


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_cloud_ridge_economy(library: ContentLibrary) -> None:
    economy = library.world_economy
    rules = economy.rules
    assert rules is not None
    assert (rules.bag_slots, rules.pouch_slots) == (30, 3)  # 8.17
    assert rules.battle_gold.gold_for(elite=False, level=1) == 15
    assert rules.quest_coins.coins_for("starter_ferry", "starter") == 2
    shop = economy.shops["cloud_ridge"].shop_by_id()["shop_liu"]
    assert shop.npc == "shopkeeper_liu"
    assert shop.affinity is not None
    assert (shop.affinity.per_purchase, shop.affinity.daily_max) == (2, 4)  # 18.7.6
    kinds = {economy.items[s.item].kind for s in shop.stock}
    assert kinds == {"consumable", "material", "dye"}  # 8.26.1
    assert [s.item for s in shop.stock if economy.items[s.item].kind == "material"] == [
        COARSE_MATERIAL
    ]
    mist = shop.stock_of("item_mist_flask")
    assert mist is not None and mist.rank == "friendly"  # 8.26.1 例
    weekly = shop.weekly_of("item_green_bamboo")
    assert weekly is not None and (weekly.min, weekly.max) == (2, 4)
    assert economy.items["item_green_bamboo"].region == "cloud_ridge"  # 18.2.4 雲嶺特產
    # 道具技能：1 AP、每個用一次、帶 item 標籤、不進技能池
    for item in economy.items.values():
        if item.skill is not None:
            assert item.skill.ap_cost == 1 and item.skill.cost.uses_per_battle == 1
            assert "item" in item.skill.tags
            assert item.skill.id not in library.skills
    files = {p.relative_to(library.root).as_posix() for p, _ in library.files}
    assert {"world/economy.yaml", "world/items.yaml", "world/shops/cloud_ridge.yaml"} <= files


def _write(root: Path, rel: str, data: Any) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _content(library: ContentLibrary, tmp_path: Path) -> Path:
    root = tmp_path / "content"
    for rel in ("world/economy.yaml", "world/items.yaml", "world/shops/cloud_ridge.yaml"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(library.root / rel, root / rel)
    return root


def _load(root: Path) -> None:
    load_world_economy(root, [], regions=REGIONS, npcs_by_region=NPCS)


def _shops(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(
        (root / "world/shops/cloud_ridge.yaml").read_text("utf-8")
    )
    return data


def test_missing_files_are_empty(tmp_path: Path) -> None:
    economy = load_world_economy(tmp_path, [], regions=REGIONS, npcs_by_region=NPCS)
    assert economy.rules is None and economy.items == {} and economy.shops == {}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s["shops"][0].update(npc="granny_du"), "不在 cloud_ridge 的人設卡"),
        (
            lambda s: s["shops"][0]["stock"].append({"item": "item_nothing"}),
            "不在 world/items.yaml",
        ),
        (
            lambda s: s["shops"][0].update(weekly=[], stock=[{"item": "item_green_bamboo"}]),
            "只能賣粗料",
        ),
        (
            lambda s: s["shops"][0].update(
                stock=[], weekly=[{"item": "item_dye_ink", "min": 1, "max": 1}]
            ),
            "不是 cloud_ridge 的特產",
        ),
        (lambda s: s["shops"][0]["weekly"][0].update(min=5, max=2), "min 不可大於 max"),
        (lambda s: s["shops"][0]["stock"].append({"item": "item_spring_pill"}), "商品重複"),
        (lambda s: s.update(region="frost_tide"), "檔名必須與 region 相同"),
    ],
)
def test_bad_shops(library: ContentLibrary, tmp_path: Path, change: Any, message: str) -> None:
    root = _content(library, tmp_path)
    data = _shops(root)
    change(data)
    _write(root, "world/shops/cloud_ridge.yaml", data)
    with pytest.raises((ContentError, ValidationError), match=message):
        _load(root)


def test_shop_region_without_map(library: ContentLibrary, tmp_path: Path) -> None:
    root = _content(library, tmp_path)
    with pytest.raises(ContentError, match="沒有地點圖"):
        load_world_economy(root, [], regions=set(), npcs_by_region=NPCS)


def _item(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"id": "item_x", "name_zh": "X", "kind": "material", "price": 1}
    data.update(updates)
    return data


def test_item_rules(library: ContentLibrary) -> None:
    pill = library.world_economy.items["item_spring_pill"]
    assert pill.skill is not None
    skill = pill.skill.model_dump()
    with pytest.raises(ValidationError, match="只有消耗品有 skill"):
        WorldItemDef.model_validate(_item(kind="consumable"))
    with pytest.raises(ValidationError, match="只有消耗品有 skill"):
        WorldItemDef.model_validate(_item(skill=skill))
    with pytest.raises(ValidationError, match="只有消耗品能在野外使用"):
        WorldItemDef.model_validate(_item(field_hp_permille=100))
    with pytest.raises(ValidationError, match="只有染料有 color"):
        WorldItemDef.model_validate(_item(kind="dye"))
    no_tag = {**skill, "tags": ["support"]}
    with pytest.raises(ValidationError, match="標籤 item"):
        WorldItemDef.model_validate(_item(kind="consumable", skill=no_tag))
    twice = {**skill, "cost": {"mana": 0, "uses_per_battle": 2}}
    with pytest.raises(ValidationError, match="uses_per_battle 必須是 1"):
        WorldItemDef.model_validate(_item(kind="consumable", skill=twice))
    with pytest.raises(ValidationError, match="物品 ID 重複"):
        WorldItemTable.model_validate({"items": [_item(), _item()]})
    with pytest.raises(ValidationError, match="未知的任務種類"):
        EconomyRules.model_validate({"quest_coins": {"by_kind": {"boss": 1}}})
    assert EconomyRules().sell_price(5) == 2 and EconomyRules().sell_price(1) == 1


def test_item_region_must_exist(library: ContentLibrary, tmp_path: Path) -> None:
    root = _content(library, tmp_path)
    data = yaml.safe_load((root / "world/items.yaml").read_text("utf-8"))
    data["items"][0]["region"] = "nowhere"
    _write(root, "world/items.yaml", data)
    with pytest.raises(ContentError, match="區域 nowhere 沒有地點圖"):
        _load(root)
