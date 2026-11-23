"""程式需要的地圖用途（QF-5，WL-2 裁定 4；做法照 WL-1 b 的骨架檢查）。

清單是 :data:`trpg.content.maps.CODE_REQUIRED_ROLES`：每種用途至少要有一個地圖類型標這個 ``role``，
缺了載入時用中文擋下（不是等到用的時候才 IndexError 或檢查訊息奇怪）。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import get_args

import pytest

from tests.engine.helpers import library
from trpg.content.library import load_library
from trpg.content.maps import CODE_REQUIRED_ROLES, MapArchetypeTable, MapRole
from trpg.shared.errors import ContentError

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
SRC = ROOT / "src" / "trpg"


def test_every_code_required_role_is_in_the_data() -> None:
    table = library().map_archetypes
    assert all(table.role_ids(role) for role in CODE_REQUIRED_ROLES)
    assert all(why for why in CODE_REQUIRED_ROLES.values())


def test_the_list_covers_every_role_the_code_asks_for() -> None:
    """程式裡 ``has_role(…, "x")``／``role_ids("x")``／``role_label("x")`` 的用途都要在清單裡。"""
    lookup = re.compile(r"""(?:has_role\([^)]*?|role_ids\(|role_label\()\s*["'](\w+)["']""")
    found = {
        m.group(1)
        for path in sorted(SRC.rglob("*.py"))
        for m in lookup.finditer(path.read_text(encoding="utf-8"))
    }
    assert found  # 掃得到東西（不是空集合造成的假通過）
    assert found <= set(CODE_REQUIRED_ROLES), sorted(found - set(CODE_REQUIRED_ROLES))
    assert set(CODE_REQUIRED_ROLES) <= set(get_args(MapRole.__value__))


@pytest.mark.parametrize("role", sorted(CODE_REQUIRED_ROLES))
def test_a_missing_role_is_rejected_in_chinese(role: MapRole) -> None:
    rows = [{"id": r, "role": r} for r in CODE_REQUIRED_ROLES if r != role]
    with pytest.raises(ValueError, match=f"缺少程式需要的地圖用途（role）：{role}（") as err:
        MapArchetypeTable.model_validate({"archetypes": [{"id": "swamp"}, *rows]})
    assert CODE_REQUIRED_ROLES[role] in str(err.value)  # 訊息寫出程式哪裡要它


def test_removing_a_role_from_the_data_file_stops_the_content_load(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    path = root / "map_archetypes.yaml"
    text = path.read_text(encoding="utf-8")
    assert "    role: training\n" in text
    path.write_text(text.replace("    role: training\n", "", 1), encoding="utf-8", newline="")
    with pytest.raises(ContentError, match="缺少程式需要的地圖用途（role）：training（"):
        load_library(root)
