"""系統傭兵名單（Phase 5C-1；``docs/phases/Phase5計畫.md`` 21.2）。"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_mercenaries import MERCENARY_ROLES, MercenaryTable
from trpg.shared.errors import ContentError

ROSTER = {
    "merc_qingfeng": ("青鋒", "damage", "build_striker"),
    "merc_chuanyun": ("穿雲", "damage", "build_ranged"),
    "merc_chiyan": ("赤焰", "damage", "build_fire"),
    "merc_tiebi": ("鐵壁", "guardian", "build_tank"),
    "merc_panshi": ("磐石", "guardian", "build_guardian"),
    "merc_huichun": ("回春", "support", "build_healer"),
    "merc_qingyin": ("清音", "support", "build_support"),
    "merc_jinglei": ("驚雷", "control", "build_storm"),
    "merc_fuying": ("伏影", "control", "build_trapper"),
}
"""9.6.11 #117 的名單（暫名、定位、底稿）。"""


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_roster_matches_design(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    assert table.max_hired == 2  # #97
    assert {m.id: (m.name_zh, m.role, m.build) for m in table.mercenaries} == ROSTER
    counts = Counter(m.role for m in table.mercenaries)
    assert all(counts[r] >= 2 for r in MERCENARY_ROLES)  # 9.6.8
    builds = library.builds.by_id()
    for merc in table.mercenaries:
        build = builds[merc.build]
        assert not build.blank
        assert not build.reference


def _table(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "max_hired": 2,
        "mercenaries": [
            {"id": k, "name_zh": n, "title_zh": "x", "role": r, "build": b}
            for k, (n, r, b) in ROSTER.items()
        ],
    }
    data.update(updates)
    return data


def test_schema_rejects_duplicates_and_missing_roles() -> None:
    MercenaryTable.model_validate(_table())
    dup = _table()
    dup["mercenaries"].append(dict(dup["mercenaries"][0]))
    with pytest.raises(ValidationError, match="重複"):
        MercenaryTable.model_validate(dup)
    few = _table()
    few["mercenaries"] = [m for m in few["mercenaries"] if m["id"] != "merc_fuying"]
    with pytest.raises(ValidationError, match="控制"):
        MercenaryTable.model_validate(few)
    with pytest.raises(ValidationError):
        MercenaryTable.model_validate(_table(max_hired=3))


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    return root


def _write(root: Path, data: dict[str, Any]) -> None:
    path = root / "world" / "mercenaries.yaml"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


def test_loader_checks_builds(tmp_path: Path, library: ContentLibrary) -> None:
    root = _copy_content(tmp_path, library)
    data = _table()
    data["mercenaries"][0]["build"] = "build_nobody"
    _write(root, data)
    with pytest.raises(ContentError, match="build_nobody"):
        load_library(root)
    blank = next(b.id for b in library.builds.builds if b.blank)
    data["mercenaries"][0]["build"] = blank
    _write(root, data)
    with pytest.raises(ContentError, match="白板"):
        load_library(root)
    (root / "world" / "mercenaries.yaml").unlink()
    assert load_library(root).world_mercenaries is None
