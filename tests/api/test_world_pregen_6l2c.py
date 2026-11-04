"""6L-2c：閃現預先生成的鍵不含用法統計（玩法 PM 決定）。全部用 Mock 與假生成函式，不需網路。

- 每打完一場用法統計都會變；暫存區的鍵不含它，連打很多場也只生成一次。
- 同一招同一次出題最多一個生成中的請求；已經在生成或做好的不重開。
- 第一次閃現（#132）仍然在渡口戰後就開始生成。
- 按下時給出去的是預先生成的那一份（鍵改成按下那一刻的鍵），日誌記下它，重播只讀日誌。
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from tests.api.test_world_pregen import Recorder, _never_run, _store, _town_char
from tests.api.test_world_pregen_6l2b import _after_ferry_fight
from tests.world.helpers import make_world
from trpg.api.world_pregen import WorldPregen, flash_wait_request
from trpg.content.library import ContentLibrary
from trpg.roguelite.state import FlashChoice
from trpg.skillgen.usage import SkillUsage
from trpg.world.actions import FlashAction
from trpg.world.generated import FlashGen, FlashGenRequest, flash_pregen_key
from trpg.world.replay import replay
from trpg.world.state import CharacterState, WorldState


def _fought(char: CharacterState, fights: int) -> CharacterState:
    """又打了 ``fights`` 場：每招的用法統計都多了（只改統計，其他不變）。"""
    usage = {
        s: SkillUsage(uses=2 * fights, targets=3 * fights, distance=fights, kills=fights)
        for s in char.hero.skills
    }
    return char.model_copy(update={"skill_usage": usage})


def _request(
    library: ContentLibrary, char: CharacterState, skill: str, world: WorldState | None = None
) -> FlashGenRequest:
    world = make_world() if world is None else world
    request = flash_wait_request(library, world, char, FlashChoice(skill=skill))
    assert request is not None
    return request


def test_five_fights_generate_once(library: ContentLibrary) -> None:
    """連打 5 場：按下時的請求鍵每場都換，但暫存區的鍵不變，每招只生成 1 次。"""
    world, town = make_world(), _town_char(library)
    skill = town.hero.skills[0]
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        keys = set()
        for fights in range(1, 6):
            char = _fought(town, fights)
            pregen.prefetch(library, world, char)
            pregen.drain(timeout=60)
            keys.add(_request(library, char, skill).key)
        assert len(keys) == 5  # 統計確實每場都變（舊的鍵會重做 5 次）
        assert len(rec.calls) == len(set(rec.calls))  # 每招只生成 1 次
        first = _request(library, _fought(town, 1), skill)
        assert rec.calls.count(first.key) == 1  # 統計只在開始生成時讀一次：用第 1 場後的那份
        last = _request(library, _fought(town, 5), skill)
        got = pregen.supplier(library)(last)
        assert isinstance(got, FlashGen) and got.key == last.key  # 鍵改成按下那一刻的
        assert got.record.tag == first.key  # 內容是第 1 場後開始生成的那一份
        assert rec.calls.count(first.key) == 1 and last.key not in rec.calls
    finally:
        pregen.shutdown()


def test_one_request_per_skill_while_generating(library: ContentLibrary) -> None:
    """生成中又打了一場：不重開；按下時等那一個做完、直接用它。"""
    gate = threading.Event()
    rec = Recorder(gate)
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    world, town = make_world(), _town_char(library)
    skill = town.hero.skills[0]
    try:
        pregen.prefetch(library, world, _fought(town, 1))
        queued = pregen.pending(town.character_id)
        assert queued >= 1
        for fights in range(2, 5):
            pregen.prefetch(library, world, _fought(town, fights))
            assert pregen.pending(town.character_id) == queued  # 同一招不會多一個請求
        later = _request(library, _fought(town, 4), skill)
        slot = flash_pregen_key(town.character_id, later.request)
        assert sum(1 for k in pregen._entries if k == (town.character_id, slot)) == 1
        gate.set()
        got = pregen.supplier(library)(later)
        assert isinstance(got, FlashGen) and got.key == later.key
        pregen.drain(timeout=60)
        assert rec.max_active == 1
        assert len(rec.calls) == queued == len(set(rec.calls))
    finally:
        gate.set()
        pregen.shutdown()


def test_first_flash_starts_after_ferry_fight(library: ContentLibrary) -> None:
    """#132：渡口戰後（還在野外）就開始生成；再打一場、回城按下，用的是同一份、不重做。"""
    world, field = make_world(), _fought(_after_ferry_fight(library), 1)
    skill = field.hero.skills[0]
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        pregen.prefetch(library, world, field)
        pregen.drain(timeout=60)
        started = len(rec.calls)
        assert started >= 1
        town = _fought(field, 2).model_copy(update={"location": "mist_ferry"})
        pregen.prefetch(library, world, town)
        pressed = _request(library, town, skill)
        got = pregen.supplier(library)(pressed)
        assert isinstance(got, FlashGen) and got.key == pressed.key
        assert len(rec.calls) == started
    finally:
        pregen.shutdown()


def test_press_uses_pregen_and_replay_reads_log(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """生成開始後統計變了：按下時用預先生成的那一份，日誌記下它（鍵是按下那一刻的），重播不呼叫
    LLM、結果相同。"""
    town = _fought(_town_char(library, "c1"), 3)
    store = _store(library, tmp_path, town)
    rec = Recorder()
    store.pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    skill = town.hero.skills[0]
    start = store.world()
    try:
        store.pregen.prefetch(library, start, _fought(town, 1))  # 前幾場後就開始生成
        store.pregen.drain(timeout=60)
        before = list(rec.calls)
        store.character("c1")  # 讀進來（統計已是第 3 場後）：不重做
        flashed = store.act("c1", FlashAction(skill=skill))
    finally:
        store.pregen.shutdown()
    assert rec.calls == before
    (entry,) = store.entries()
    (gen,) = entry.generated
    pressed = _request(library, town, skill, start)
    assert isinstance(gen, FlashGen) and gen.key == pressed.key
    assert gen.record.source == "llm"  # 預先生成的那一份（假生成函式標成 llm）
    assert gen.record.tag == _request(library, _fought(town, 1), skill, start).key
    monkeypatch.setattr("trpg.api.world_pregen.WorldPregen._run", _never_run)
    result = replay(library, start, {"c1": town}, store.entries())
    assert result.characters["c1"].pending_flash == flashed.char.pending_flash
    assert result.characters["c1"] == flashed.char
