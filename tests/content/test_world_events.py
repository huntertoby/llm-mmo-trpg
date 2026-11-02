"""事件骨架、線頭、NPC 人設卡與事件規則（Phase 5B-1；``docs/phases/Phase5計畫.md`` 8.7）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_events import (
    EventSkeletonDef,
    EventSkeletonTable,
    NpcCardTable,
    SolutionDef,
    npc_card_problems,
    world_event_problems,
)
from trpg.shared.errors import ContentError


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def events(library: ContentLibrary) -> EventSkeletonTable:
    return library.world_event_content.events["cloud_ridge"]


@pytest.fixture(scope="module")
def npcs(library: ContentLibrary) -> NpcCardTable:
    return library.world_event_content.npcs["cloud_ridge"]


def _skeleton(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "test_event",
        "number": 1,
        "who_zh": "誰",
        "want_zh": "想要",
        "obstacle_zh": "阻礙",
        "stakes_zh": "賭注",
        "locations": ["ferry_steps"],
        "solutions": [{"kind": "combat"}],
    }
    data.update(updates)
    return data


def _table(*skeletons: dict[str, Any]) -> dict[str, Any]:
    return {"region": "cloud_ridge", "skeletons": list(skeletons) or [_skeleton()]}


def _problems(library: ContentLibrary, table: dict[str, Any]) -> list[str]:
    content = library.world_event_content
    return world_event_problems(
        EventSkeletonTable.model_validate(table),
        world_map=library.world_maps["cloud_ridge"],
        npcs=content.npcs["cloud_ridge"],
        weather_ids=library.weather,
        thread_ids=content.events["cloud_ridge"].thread_ids(),
    )


# ---------------------------------------------------------------------------
# 雲嶺內容
# ---------------------------------------------------------------------------


def test_cloud_ridge_events_loaded(events: EventSkeletonTable) -> None:
    assert len(events.skeletons) == 22  # 5B-4b：骨架 22「渡婆婆的往事」
    assert sorted(s.number for s in events.skeletons) == list(range(1, 23))
    assert len(events.thread_ids()) == 19  # 骨架 22 的暗門是別的骨架的線頭（shared_threads）
    assert "22 個事件骨架" in events.summary()


def test_cloud_ridge_npcs_loaded(npcs: NpcCardTable) -> None:
    assert len(npcs.npcs) == 8
    by_id = npcs.npc_by_id()
    assert by_id["granny_du"].location == "mist_ferry"
    assert by_id["mistlock_master"].location == "cloud_summit"
    assert by_id["frost_chime"].location == "crane_cliff"
    assert all(n.secret_zh for n in npcs.npcs)


def test_event_rules_loaded(library: ContentLibrary) -> None:
    rules = library.world_event_content.rules
    assert rules is not None
    assert rules.frequency.per_step_permille == 150
    assert rules.frequency.max_permille == 600
    assert rules.threads.personal_limit == 5
    assert rules.threads.expire_seconds == 3 * 24 * 3600


def test_cloud_ridge_cross_file_clean(
    library: ContentLibrary, events: EventSkeletonTable, npcs: NpcCardTable
) -> None:
    world_map = library.world_maps["cloud_ridge"]
    assert npc_card_problems(npcs, world_map=world_map) == []
    assert (
        world_event_problems(
            events,
            world_map=world_map,
            npcs=npcs,
            weather_ids=library.weather,
            thread_ids=events.thread_ids(),
        )
        == []
    )


def test_cloud_ridge_details_follow_18_4(events: EventSkeletonTable) -> None:
    by_id = events.skeleton_by_id()
    threads = events.thread_by_id()
    assert threads["foxfire_guide"].hints_location == "crane_cliff"
    assert threads["scarface_grudge"].npc == "scarface"
    assert threads["scarface_grudge"].on_expire_zh
    assert threads["temple_traitor"].on_expire_zh
    world = {t.id for t in threads.values() if t.scope == "world"}
    assert world == {"wraiths_from_rift", "shards_to_ashen"}
    assert by_id["storm_altar"].day_phase == "night"
    assert by_id["storm_altar"].weather == ("rain",)
    assert by_id["lantern_patrol"].day_phase == "night"
    assert by_id["storm_altar"].threads == ()
    assert by_id["poison_spring"].threads == ()
    kinds = {sol.kind for s in events.skeletons for sol in s.solutions}
    assert kinds == {"combat", "situation", "parley", "abandon", "opportunity"}


def test_files_listed(library: ContentLibrary) -> None:
    names = {path.as_posix().split("content/")[-1] for path, _ in library.files}
    assert {
        "world/events/cloud_ridge.yaml",
        "world/npcs/cloud_ridge.yaml",
        "world/event_rules.yaml",
    } <= names


# ---------------------------------------------------------------------------
# 單檔驗證
# ---------------------------------------------------------------------------


def test_minimal_table_valid() -> None:
    table = EventSkeletonTable.model_validate(_table())
    assert table.skeletons[0].id == "test_event"


@pytest.mark.parametrize(
    "solution",
    [
        {"kind": "situation"},
        {"kind": "situation", "attributes": ["str", "str"]},
        {"kind": "situation", "attributes": ["str", "dex", "con", "int"]},
        {"kind": "combat", "attributes": ["str"]},
        {"kind": "situation", "attributes": ["luck"]},
    ],
)
def test_bad_solution(solution: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SolutionDef.model_validate(solution)


def test_situation_solution_valid() -> None:
    sol = SolutionDef.model_validate({"kind": "situation", "attributes": ["wis", "int"]})
    assert len(sol.attributes) == 2


@pytest.mark.parametrize(
    "updates",
    [
        {"locations": []},
        {"locations": ["ferry_steps", "ferry_steps"]},
        {"locations": ["Bad-ID"]},
        {"solutions": []},
        {"weather": ["rain", "rain"]},
        {"day_phase": "dusk"},
        {"follows": ["own_thread"], "threads": [{"id": "own_thread", "text_zh": "x"}]},
        {"threads": [{"id": "t", "text_zh": "x", "scope": "galaxy"}]},
        {"number": 0},
        {"stakes_zh": ""},
    ],
)
def test_bad_skeleton(updates: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EventSkeletonDef.model_validate(_skeleton(**updates))


def test_duplicate_ids_in_table() -> None:
    with pytest.raises(ValidationError, match="ID 重複"):
        EventSkeletonTable.model_validate(_table(_skeleton(), _skeleton(number=2)))
    with pytest.raises(ValidationError, match="編號重複"):
        EventSkeletonTable.model_validate(_table(_skeleton(), _skeleton(id="other")))
    thread = {"id": "same", "text_zh": "x"}
    with pytest.raises(ValidationError, match="線頭 ID 重複"):
        EventSkeletonTable.model_validate(
            _table(_skeleton(threads=[thread]), _skeleton(id="other", number=2, threads=[thread]))
        )


def test_duplicate_npc_ids() -> None:
    npc = {
        "id": "a",
        "name_zh": "甲",
        "location": "mist_ferry",
        "personality_zh": "x",
        "speech_zh": "y",
    }
    with pytest.raises(ValidationError, match="NPC ID 重複"):
        NpcCardTable.model_validate({"region": "cloud_ridge", "npcs": [npc, npc]})


# ---------------------------------------------------------------------------
# 跨檔案
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"locations": ["nowhere"]}, "沒有地點 nowhere"),
        ({"weather": ["blizzard"]}, "未知的天氣 blizzard"),
        ({"npcs": ["nobody"]}, "未知的 NPC nobody"),
        ({"follows": ["no_thread"]}, "未知的線頭 no_thread"),
        ({"threads": [{"id": "t1", "text_zh": "x", "npc": "nobody"}]}, "未知的 NPC nobody"),
        ({"threads": [{"id": "t1", "text_zh": "x", "hints_location": "nowhere"}]}, "沒有地點"),
        (
            {"threads": [{"id": "t1", "text_zh": "x", "hints_location": "herb_valley"}]},
            "quest_clue",
        ),
        (
            # 丹爐洞是隱藏地點，但只能由情境判定發現（沒有 quest_clue）
            {"threads": [{"id": "t1", "text_zh": "x", "hints_location": "elixir_cave"}]},
            "quest_clue",
        ),
    ],
)
def test_cross_file_problems(
    library: ContentLibrary, updates: dict[str, Any], message: str
) -> None:
    problems = _problems(library, _table(_skeleton(**updates)))
    assert any(message in p for p in problems), problems


def test_follows_known_thread_ok(library: ContentLibrary) -> None:
    assert _problems(library, _table(_skeleton(follows=["scarface_grudge"]))) == []


def test_missing_world_map(library: ContentLibrary) -> None:
    table = EventSkeletonTable.model_validate(_table())
    problems = world_event_problems(
        table, world_map=None, npcs=None, weather_ids=library.weather, thread_ids=()
    )
    assert any("地點圖" in p for p in problems)


def test_npc_unknown_location(library: ContentLibrary) -> None:
    npcs = NpcCardTable.model_validate(
        {
            "region": "cloud_ridge",
            "npcs": [
                {
                    "id": "a",
                    "name_zh": "甲",
                    "location": "nowhere",
                    "personality_zh": "x",
                    "speech_zh": "y",
                }
            ],
        }
    )
    problems = npc_card_problems(npcs, world_map=library.world_maps["cloud_ridge"])
    assert problems == ["NPC a：cloud_ridge 沒有地點 nowhere"]


# ---------------------------------------------------------------------------
# 載入
# ---------------------------------------------------------------------------


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def _edit_yaml(path: Path, edit: Any) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8", newline="\n")


def test_bad_event_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "events" / "cloud_ridge.yaml"
    _edit_yaml(path, lambda d: d["skeletons"][0].update(locations=["nowhere"]))
    with pytest.raises(ContentError, match="nowhere"):
        load_library(content)


def test_bad_npc_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "npcs" / "cloud_ridge.yaml"
    _edit_yaml(path, lambda d: d["npcs"][0].update(location="nowhere"))
    with pytest.raises(ContentError, match="nowhere"):
        load_library(content)


def test_file_name_must_match_region(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    events_dir = content / "world" / "events"
    (events_dir / "cloud_ridge.yaml").rename(events_dir / "misty.yaml")
    with pytest.raises(ContentError, match="檔名必須與 region 相同"):
        load_library(content)


def test_ids_unique_across_regions(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    events_dir = content / "world" / "events"
    source = events_dir / "cloud_ridge.yaml"
    other = events_dir / "ashen_waste.yaml"
    shutil.copy(source, other)
    _edit_yaml(other, lambda d: d.update(region="ashen_waste"))
    with pytest.raises(ContentError, match="重複"):
        load_library(content)


def test_without_world_event_files(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world" / "events")
    shutil.rmtree(content / "world" / "npcs")
    (content / "world" / "event_rules.yaml").unlink()
    shutil.rmtree(content / "world" / "situations")  # 5B-2：情境模板要有骨架
    shutil.rmtree(content / "world" / "quests")  # 5B-4：任務與聊天內容要有 NPC 與骨架
    shutil.rmtree(content / "world" / "social")
    lib = load_library(content)
    assert lib.world_event_content.events == {}
    assert lib.world_event_content.npcs == {}
    assert lib.world_event_content.rules is None


def test_events_without_npc_file(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world" / "npcs")
    with pytest.raises(ContentError, match="未知的 NPC acolyte_xiaolian"):
        load_library(content)


def test_loading_twice_is_identical(library: ContentLibrary) -> None:
    again = load_library()
    a = library.world_event_content
    b = again.world_event_content
    assert a.events["cloud_ridge"].model_dump() == b.events["cloud_ridge"].model_dump()
    assert a.npcs["cloud_ridge"].model_dump() == b.npcs["cloud_ridge"].model_dump()
