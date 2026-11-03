"""6C-R2 重構不改行為：同一組實地地圖動作在重構前後逐字一致。

走的是測試專用的凍結地圖（:func:`tests.world.helpers.with_test_fields`）：霧渡鎮進出酒館、踩傳送石、
走出口到渡口石階、潛行、碰到駐守、撤退、走回霧渡鎮。每一步記下事件、角色與世界（JSON），整串的
SHA-256 要等於重構前（6C-R1 合併後的 ``680b2d38``）用同一支腳本算出的值。

例外：陣容種子（``lineup_seed``）6C-R2 改由世界種子衍生（另見
``tests/world/test_field_lineup_seed.py``），比較前一律遮掉。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tests.world.helpers import NOON, hero, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import RetreatAction, WorldAction
from trpg.world.errors import WorldActionError
from trpg.world.field_actions import SneakAction, WalkAction
from trpg.world.state import CharacterState, FieldPos, WorldState
from trpg.world.step import new_character, world_step

type XY = tuple[int, int]

BEFORE_6CR2 = "36e633b374e4caffdac4d2ae276db0306c9f6d4c5d9bdd26e06df46b4964edcc"
"""重構前（``680b2d38``）同一串動作的 SHA-256（遮掉 ``lineup_seed``）。"""


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


def _masked(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: (None if k == "lineup_seed" else _masked(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_masked(v) for v in data]
    return data


def run(library: ContentLibrary) -> list[Any]:
    """照 :func:`script` 走一遍（不合法的動作記下錯誤訊息、狀態不變）。"""
    world: WorldState = make_world()
    char: CharacterState = new_character(library, "alice", hero(library), region="cloud_ridge")
    char = char.model_copy(update={"field": FieldPos(map="mist_ferry", x=11, y=9)})
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
    return _masked(out)


def digest(library: ContentLibrary) -> str:
    text = json.dumps(run(library), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_field_ctx_refactor_keeps_replay(field_library: ContentLibrary) -> None:
    assert digest(field_library) == BEFORE_6CR2


def test_script_covers_the_hooks(field_library: ContentLibrary) -> None:
    """這串動作真的走過了門、出口、傳送石、潛行、碰敵與撤退（不是一路報錯）。"""
    steps = run(field_library)
    assert not any("error" in s for s in steps), [s.get("error") for s in steps]
    kinds = [e["kind"] for s in steps for e in s["events"]]
    for kind in ("field_entered", "teleport_stone_unlocked", "sneak_started", "traveled"):
        assert kind in kinds, kind
    assert any(
        e["kind"] == "encounter" and e["result"]["contact"] is not None
        for s in steps
        for e in s["events"]
    )
