"""新地圖類型只寫資料（Phase WL-2 第 4 項）。

測試把正式內容複製一份，只改資料：

- ``map_archetypes.yaml`` 加兩種類型：一般的 ``dunes``（沒有 ``role``），和不進抽選的
  ``sealed``（``in_random_pool: false``）；
- 各加一張地圖（``sand_dunes`` 照 ``open_plain``、``sealed_vault`` 照 ``swamp``，只換 id 與類型）；
- ``sand_dunes`` 放進 roguelite 的地圖池，``dunes`` 放進雲嶺的區域地圖池。

不改任何程式：新類型要能載入、驗證、抽選、開戰；``sealed`` 不會被抽到，放進地圖池會被擋下。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from tests.world.helpers import make_encounter
from trpg.api.sessions import playable_maps
from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary, load_library
from trpg.roguelite.start import make_plan
from trpg.shared.errors import ContentError
from trpg.sim.batch import map_spec, run_batches
from trpg.world.battle import encounter_map

CONTENT = Path(__file__).resolve().parents[2] / "content"
NEW_TYPE = "dunes"
SEALED_TYPE = "sealed"
NEW_MAP = "sand_dunes"
SEALED_MAP = "sealed_vault"


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def _copy_map(root: Path, source: str, new_id: str, archetype: str) -> None:
    data = yaml.safe_load((root / "maps" / f"{source}.yaml").read_text(encoding="utf-8"))
    data.update(id=new_id, archetype=archetype, name_zh=f"測試{new_id}")
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    (root / "maps" / f"{new_id}.yaml").write_text(text, encoding="utf-8", newline="")


def _content_with_new_types(root: Path) -> Path:
    shutil.copytree(CONTENT, root)
    with (root / "map_archetypes.yaml").open("a", encoding="utf-8", newline="") as f:
        f.write(f"  - id: {NEW_TYPE}\n  - id: {SEALED_TYPE}\n    in_random_pool: false\n")
    _copy_map(root, "open_plain", NEW_MAP, NEW_TYPE)
    _copy_map(root, "swamp", SEALED_MAP, SEALED_TYPE)
    _edit(root / "roguelite.yaml", "map_pool: [", f"map_pool: [{NEW_MAP}, ")
    _edit(root / "regions.yaml", "map_pool: [open_plain,", f"map_pool: [{NEW_TYPE}, open_plain,")
    return root


@pytest.fixture(scope="module")
def new_library(tmp_path_factory: pytest.TempPathFactory) -> ContentLibrary:
    return load_library(_content_with_new_types(tmp_path_factory.mktemp("wl2") / "content"))


def test_new_archetypes_load_in_data_order(new_library: ContentLibrary) -> None:
    table = new_library.map_archetypes
    assert table.ids()[-2:] == (NEW_TYPE, SEALED_TYPE)
    assert table.in_random_pool(NEW_TYPE) and not table.in_random_pool(SEALED_TYPE)
    assert table.get(NEW_TYPE) is not None and table.get(NEW_TYPE).role is None  # type: ignore[union-attr]
    assert new_library.map(NEW_MAP).archetype == NEW_TYPE
    assert new_library.map(SEALED_MAP).archetype == SEALED_TYPE


def test_the_roguelite_draws_the_new_archetype(new_library: ContentLibrary) -> None:
    plans = [make_plan(new_library, seed) for seed in range(30)]
    drawn = {p.map_id for plan in plans for p in plan}
    assert NEW_MAP in drawn
    assert SEALED_MAP not in drawn
    for plan in plans:  # 同一輪地圖類型仍不重複
        types = [new_library.map(p.map_id).archetype for p in plan[:-1]]
        assert len(set(types)) == len(types)


def test_the_world_draws_the_new_archetype_from_the_region_pool(
    new_library: ContentLibrary,
) -> None:
    drawn = {
        encounter_map(new_library, make_encounter("old_pine_altar", seed=seed, level=3)).id
        for seed in range(60)
    }
    assert NEW_MAP in drawn
    assert SEALED_MAP not in drawn


def test_default_lists_treat_the_new_archetype_as_ordinary(new_library: ContentLibrary) -> None:
    sim_maps = default_sim_maps(new_library)
    assert NEW_MAP in sim_maps and SEALED_MAP not in sim_maps
    assert NEW_MAP in playable_maps(new_library)  # 沒有 role：一般地圖列表照常列


def test_a_battle_on_the_new_archetype_plays_through(new_library: ContentLibrary) -> None:
    (report,) = run_batches([map_spec(new_library, NEW_MAP, (0, 1))], jobs=1)
    assert report.anomaly("exception") is None
    assert report.completed == 2


@pytest.mark.parametrize(
    ("file", "old", "new", "message"),
    [
        (
            "roguelite.yaml",
            "map_pool: [",
            f"map_pool: [{SEALED_MAP}, ",
            f"不進抽選的地圖類型（in_random_pool: false）不能進地圖池：{SEALED_MAP}",
        ),
        (
            "regions.yaml",
            f"map_pool: [{NEW_TYPE},",
            f"map_pool: [{SEALED_TYPE}, {NEW_TYPE},",
            f"區域 cloud_ridge 的 map_pool 不可含 {SEALED_TYPE}",
        ),
    ],
)
def test_the_sealed_archetype_cannot_enter_a_random_pool(
    tmp_path: Path, file: str, old: str, new: str, message: str
) -> None:
    root = _content_with_new_types(tmp_path / "content")
    _edit(root / file, old, new)
    with pytest.raises(ContentError, match=re.escape(message)):
        load_library(root)
