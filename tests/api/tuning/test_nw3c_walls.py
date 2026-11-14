"""NW-3c：造牆 HP 提示擴大到組合器抽得到的牆（玩法 PM 交接 4.1.15 第 1、3、4 點）。

提示範圍＝手寫技能檔寫明的物件 ∪ 組合器的造牆候選（``blocks_move`` 且非 ``explosive``，再拿掉
``skill_composer.yaml`` 的排除清單）；冷卻井被排除，所以不掛提示。提示字照 4.1.14 不變。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trpg.api.tuning.objects import obstacle_objects, read_data
from trpg.api.tuning.service import TuningService
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.skillgen.composer_parts import obstacle_candidates

CONTENT = bundled_content_dir()
WALLS_ZH = "造牆技能會放出這個物件。改 HP 會讓那些技能變強或變弱，技能預算不會跟著算。"
"""4.1.14 的提示字（逐字；測試另寫一份）。"""


@pytest.fixture
def read_service(tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    """讀專案內建 ``content/`` 的服務（**不寫回**）。"""
    service = TuningService(bundled_content_dir(), tmp_path / "saves", content_library)
    service.git = None
    return service


def test_composer_walls_are_in_the_hint(read_service: TuningService) -> None:
    library = read_service.library
    assert library is not None
    walls = obstacle_objects(CONTENT, read_service.table, library)
    composer = set(obstacle_candidates(library))
    assert composer <= walls
    # 手寫技能沒用到、只有組合器會抽的牆也掛提示（木箱、石柱、矮牆、倒木、枯樹、倒塌物）
    assert {"crate", "stone_pillar", "low_wall", "fallen_log", "dead_tree", "rubble"} <= walls
    assert "cooling_well" not in walls
    assert "oil_barrel" not in walls  # 會爆炸的不當牆


def test_cooling_well_form_field_has_no_notice(read_service: TuningService) -> None:
    data = read_data(CONTENT / "objects.yaml")
    detail = read_service.object("object", "objects")
    notices = {f.path: f.notice_zh for f in detail.fields}
    index = {o["id"]: i for i, o in enumerate(data["objects"])}
    assert notices[f"objects[{index['cooling_well']}].max_hp"] is None
    assert notices[f"objects[{index['crate']}].max_hp"] == WALLS_ZH
    assert notices[f"objects[{index['earth_wall']}].max_hp"] == WALLS_ZH
