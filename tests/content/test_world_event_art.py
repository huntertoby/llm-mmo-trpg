"""事件卡插圖的場景欄位（Phase 6C-ART2；``docs/art/Phase6剩餘美術移植需求.md`` 第 3 節）。

``art`` 是只畫的選填欄位：只接受 10 種已知的場景 ID；不寫照舊（前端照選項圖示挑）。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_events import EVENT_ART_IDS, EventSkeletonDef

SCENES = (
    "ambush",
    "chest",
    "stele",
    "altar",
    "villager",
    "caravan",
    "trap",
    "camp",
    "anomaly",
    "friend",
)


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _skeleton(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "test_event",
        "number": 1,
        "who_zh": "誰",
        "want_zh": "想要",
        "stakes_zh": "賭注",
        "locations": ["ferry_steps"],
        "solutions": [{"kind": "combat"}],
    }
    data.update(updates)
    return data


def test_known_ids_are_the_ten_scenes() -> None:
    assert EVENT_ART_IDS == SCENES


@pytest.mark.parametrize("art", SCENES)
def test_known_art_accepted(art: str) -> None:
    assert EventSkeletonDef.model_validate(_skeleton(art=art)).art == art


def test_art_optional() -> None:
    assert EventSkeletonDef.model_validate(_skeleton()).art is None


@pytest.mark.parametrize("art", ["dragon", "Ambush", "", "stele ", 3])
def test_unknown_art_rejected(art: object) -> None:
    with pytest.raises(ValidationError):
        EventSkeletonDef.model_validate(_skeleton(art=art))


def test_every_skeleton_has_art(library: ContentLibrary) -> None:
    events = library.world_event_content.events
    assert sorted(events) == ["ashen_waste", "cloud_ridge"]
    for region, table in events.items():
        missing = [s.id for s in table.skeletons if s.art is None]
        assert missing == [], f"{region} 沒寫 art：{missing}"


def test_mapping_samples(library: ContentLibrary) -> None:
    """對照表抽查（報告第 3 節）：伏擊、商隊、祭壇、古碑各一。"""
    events = library.world_event_content.events
    cloud = events["cloud_ridge"].skeleton_by_id()
    ashen = events["ashen_waste"].skeleton_by_id()
    assert cloud["gang_toll"].art == "ambush"
    assert cloud["shard_convoy"].art == "caravan"
    assert cloud["storm_altar"].art == "altar"
    assert ashen["noon_altar"].art == "altar"
    assert ashen["fortress_stele"].art == "stele"
