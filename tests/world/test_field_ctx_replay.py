"""6C-R2 重構不改行為：同一組實地地圖動作在重構前後逐字一致。

走的是測試專用的凍結地圖（:func:`tests.world.helpers.with_test_fields`）：霧渡鎮進出酒館、踩傳送石、
走出口到渡口石階、潛行、碰到駐守、撤退、走回霧渡鎮。每一步記下事件、角色與世界（JSON），整串的
SHA-256 要等於重構前（6C-R1 合併後的 ``680b2d38``）用同一支腳本算出的值。

例外：陣容種子（``lineup_seed``）6C-R2 改由世界種子衍生（另見
``tests/world/test_field_lineup_seed.py``），連同跟著升版的存檔版號（``format``）與重生世代
（``wins``），比較前一律遮掉。

**6C-R3**（6C-R2 待決 6）：不再綁正式內容。除了凍結的實地地圖，這串動作會讀到的大世界內容也換成
``tests/world/frozen_replay/`` 的凍結複本（2026-11-04 正式內容的 JSON）：大世界規則、雲嶺的地點圖、
遭遇表、事件骨架與事件規則、任務，以及主角範本。凍結時的雜湊和正式內容算出的相同（仍是
``BEFORE_6CR2``）。還綁著正式內容的只剩戰鬥規則包（地形、物件、核心數值）與敵人範本（陣容名稱）。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import EncounterTable
from trpg.content.world_events import EventRules, EventSkeletonTable
from trpg.content.world_map import LocationMapDef
from trpg.content.world_quests import QuestTable
from trpg.content.world_rules import WorldRules
from trpg.world.actions import RetreatAction, WorldAction
from trpg.world.errors import WorldActionError
from trpg.world.field_actions import SneakAction, WalkAction
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]

BEFORE_6CR2 = "d2aedac47c76eb039169e9ffeb022221631653004516091b65e2d83c5ec73144"
"""重構前（``680b2d38``）同一串動作的 SHA-256（遮掉 ``lineup_seed``）。"""

FROZEN = Path(__file__).resolve().parent / "frozen_replay"
REGION = "cloud_ridge"


def _frozen[M: BaseModel](model: type[M], name: str) -> M:
    return model.model_validate(json.loads((FROZEN / f"{name}.json").read_text(encoding="utf-8")))


def frozen_hero() -> UnitTemplate:
    return _frozen(UnitTemplate, "hero")


def frozen_library(library: ContentLibrary) -> ContentLibrary:
    """``library``（已換上凍結的實地地圖）再換上凍結的大世界內容片段（6C-R3）。"""
    events = dataclasses.replace(
        library.world_event_content,
        events={REGION: _frozen(EventSkeletonTable, "events")},
        rules=_frozen(EventRules, "event_rules"),
    )
    quests = dataclasses.replace(
        library.world_quests, quests={REGION: _frozen(QuestTable, "quests")}
    )
    return dataclasses.replace(
        library,
        world_rules=_frozen(WorldRules, "world_rules"),
        world_maps={**library.world_maps, REGION: _frozen(LocationMapDef, "world_map")},
        world_encounters={
            **library.world_encounters,
            REGION: _frozen(EncounterTable, "encounters"),
        },
        world_event_content=events,
        world_quests=quests,
    )


@pytest.fixture(scope="module")
def replay_library(field_library: ContentLibrary) -> ContentLibrary:
    return frozen_library(field_library)


def _row(xs: range, y: int) -> list[XY]:
    return [(x, y) for x in xs]


def script() -> list[WorldAction]:
    """霧渡鎮（入口 (11, 9)）→ 酒館 → 傳送石 → 渡口石階 → 潛行、碰敵、撤退 → 回霧渡鎮。"""
    to_tavern = [*_row(range(10, 2, -1), 9), (3, 8), (3, 7), (3, 6), (3, 5)]
    to_stone = [*_row(range(4, 13), 6), (12, 7), (12, 8)]
    return [
        WalkAction(path=tuple(to_tavern)),
        WalkAction(path=((4, 7),)),  # 酒館的出口 → 門外 (3, 6)
        WalkAction(path=tuple(to_stone)),
        WalkAction(path=tuple(_row(range(13, 24), 8))),  # 東側石階頂 → 渡口石階
        WalkAction(path=(*_row(range(2, 9), 8), (8, 7), (9, 7))),  # 碰到中段平台 (9, 6) 的駐守
        RetreatAction(),  # 回到進圖的格子 (1, 8)
        SneakAction(),
        WalkAction(path=((1, 9), *_row(range(2, 13), 9))),  # 潛行：視野減半
        WalkAction(path=tuple(_row(range(11, -1, -1), 9))),  # 石階底的出口 → 霧渡鎮
    ]


MASKED = frozenset({"lineup_seed", "format", "wins"})
"""陣容種子變更（6C-R2）動到的欄位：比較前遮掉。"""
DROPPED = frozenset(
    {
        "generations",
        "came_from",
        "enemy_facing",
        "hints_seen",
        "hints_off",
        "level_seen",
        "skill_regions",
        "gear_origin",
        "mailbox",
        "trades",
        "weapon_mix",
        "characters",
        "free_race_change_used",
        "look_range",
        "opening",
    }
)
"""凍結之後才加的欄位（6D-R2：重生世代 ``FieldVisit.generations``；6E-3：接觸點的前一格
``came_from``；6E-3b：敵方帶頭的朝向 ``enemy_facing``；6F-4：提示紀錄 ``hints_seen``、
``hints_off``、
``level_seen``；6L-2：技能的取得界域 ``skill_regions``；6T-1a：裝備來歷 ``gear_origin``、信箱
``mailbox``、交易帳 ``trades``、主手大類比例 ``weapon_mix``、上線紀錄的 ``characters``；6R-1：
免費換種族 ``free_race_change_used``；QK-6a：敵人範本的外觀範圍 ``look_range``；TR-1：未完成
開局 ``opening``）：比較前拿掉。"""


def _masked(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: (None if k in MASKED else _masked(v)) for k, v in data.items() if k not in DROPPED
        }
    if isinstance(data, list):
        return [_masked(v) for v in data]
    return data


FROZEN_PARTY = ("merc_tiebi", "merc_huichun")
"""凍結當時新角色預設帶的傭兵（OB-7 起內容只帶賽倫）。"""


def run(library: ContentLibrary) -> list[Any]:
    """照 :func:`script` 走一遍（不合法的動作記下錯誤訊息、狀態不變）。"""
    world: WorldState = make_world()
    char: CharacterState = new_character(library, "alice", frozen_hero(), region=REGION)
    # OB-7（#154）：新角色的 default_party 改成只帶賽倫；傭兵名單不在凍結內容裡，凍結當時的預設
    # （賽倫＋回春）在這裡寫死，比對只看世界規則的程式
    char = char.model_copy(
        update={"field": FieldPos(map="mist_ferry", x=11, y=9), "mercenaries": FROZEN_PARTY}
    )
    out: list[Any] = []
    for k, action in enumerate(script()):
        try:
            result = world_step(library, world, char, action, NOON + k)
        except WorldActionError as exc:
            out.append({"error": str(exc)})
            continue
        world, char = result.world, result.char
        out.append(
            {
                "events": [e.model_dump(mode="json") for e in result.events],
                "char": char.model_dump(mode="json"),
                "world": world.model_dump(mode="json"),
            }
        )
    masked: list[Any] = _masked(out)
    return masked


def digest(library: ContentLibrary) -> str:
    text = json.dumps(run(library), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_field_ctx_refactor_keeps_replay(replay_library: ContentLibrary) -> None:
    assert digest(replay_library) == BEFORE_6CR2


def test_script_covers_the_hooks(replay_library: ContentLibrary) -> None:
    """這串動作真的走過了門、出口、傳送石、潛行、碰敵與撤退（不是一路報錯）。"""
    steps = run(replay_library)
    assert not any("error" in s for s in steps), [s.get("error") for s in steps]
    kinds = [e["kind"] for s in steps for e in s["events"]]
    for kind in ("field_entered", "teleport_stone_unlocked", "sneak_started", "traveled"):
        assert kind in kinds, kind
    assert any(
        e["kind"] == "encounter" and e["result"]["contact"] is not None
        for s in steps
        for e in s["events"]
    )


def test_replay_ignores_official_world_content(field_library: ContentLibrary) -> None:
    """正式內容的大世界規則、事件或遭遇表改了，這支比對不受影響（6C-R2 待決 6）。"""
    changed = with_rules(field_library, encounter={"base_permille": 999})
    changed = dataclasses.replace(
        changed,
        world_encounters={},
        world_event_content=dataclasses.replace(changed.world_event_content, events={}),
    )
    assert digest(frozen_library(changed)) == BEFORE_6CR2
