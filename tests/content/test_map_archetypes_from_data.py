"""地圖類型清單從資料讀（Phase WL-2）：類型寫在 ``content/map_archetypes.yaml``，地圖檔與區域的
``map_pool`` 只能填清單裡的 ID；不認得的類型由載入器擋下（中文訊息）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.engine.helpers import library
from trpg.content.library import load_library
from trpg.content.maps import MapArchetypeTable
from trpg.shared.errors import ContentError

CONTENT = Path(__file__).resolve().parents[2] / "content"


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    return root


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def test_the_archetype_order_comes_from_the_data_file() -> None:
    data = yaml.safe_load((CONTENT / "map_archetypes.yaml").read_text(encoding="utf-8"))
    assert library().map_archetypes.ids() == tuple(a["id"] for a in data["archetypes"])
    assert library().map_archetypes.ids() == (  # 和原本的 ARCHETYPES 逐字相同
        "bridge_chasm",
        "oil_depot",
        "swamp",
        "ruined_heights",
        "forest",
        "corridor",
        "open_plain",
        "frozen_lake",
        "test",
        "training",
        "boss",
    )


def test_every_map_and_region_pool_uses_a_listed_archetype() -> None:
    lib = library()
    ids = set(lib.map_archetypes.ids())
    assert {m.archetype for m in lib.maps.values()} <= ids
    assert lib.regions is not None
    assert {a for r in lib.regions.regions for a in r.map_pool} <= ids


def test_duplicate_archetypes_are_rejected() -> None:
    with pytest.raises(ValueError, match="地圖類型重複：swamp"):
        MapArchetypeTable.model_validate({"archetypes": [{"id": "swamp"}, {"id": "swamp"}]})


def test_an_unknown_map_archetype_is_rejected_in_chinese(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root / "maps" / "swamp.yaml", "archetype: swamp", "archetype: volcano")
    with pytest.raises(ContentError, match="未知的地圖類型 'volcano'（可用：bridge_chasm、") as err:
        load_library(root)
    assert err.value.path == root / "maps" / "swamp.yaml"


def test_an_unknown_region_pool_archetype_is_rejected_in_chinese(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root / "regions.yaml", "map_pool: [open_plain,", "map_pool: [volcano,")
    message = "區域 cloud_ridge 的 map_pool：未知的地圖類型 'volcano'"
    with pytest.raises(ContentError, match=message):
        load_library(root)
