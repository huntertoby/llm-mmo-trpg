"""6L-2：大世界 LLM 入口的背景預先生成（``trpg.api.world_pregen``）。全部用 Mock 與假時鐘，
不需網路；計時只在 API 層，世界引擎不讀時間。"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from tests.api.test_offer_prefetch import OPPORTUNITY, _at_altar
from tests.world.helpers import NOON, hero, make_world
from trpg.api.llm_source import MockLlmProvider
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.api.world_pregen import (
    FLASH_LIMIT,
    Generators,
    WorldPregen,
    predicted_requests,
    provider_generators,
)
from trpg.content.library import ContentLibrary
from trpg.roguelite.state import FlashLlmRecord
from trpg.skillgen.flash_state import acquire
from trpg.world.actions import EventSolveAction, FlashAction
from trpg.world.generated import (
    FlashGen,
    FlashGenRequest,
    OfferGen,
    OfferGenRequest,
    StoryGen,
    StoryGenRequest,
)
from trpg.world.replay import replay
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState
from trpg.world.step import new_character


class FakeClock:
    """每問一次前進 ``step`` 秒（等待迴圈很快就會超過 10 秒）。"""

    def __init__(self, step: float = 1.0) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


class Recorder:
    """假的生成函式：記下呼叫、同時進行的最大數；``gate`` 給了就等它才回。"""

    def __init__(self, gate: threading.Event | None = None) -> None:
        self.calls: list[str] = []
        self.gate = gate
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def _enter(self, key: str) -> None:
        with self._lock:
            self.calls.append(key)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        if self.gate is not None:
            self.gate.wait(timeout=30)

    def _leave(self) -> None:
        with self._lock:
            self.active -= 1

    def flash(self, _library: ContentLibrary, request: FlashGenRequest) -> FlashGen:
        self._enter(request.key)
        self._leave()
        return FlashGen(key=request.key, record=FlashLlmRecord(tag=request.key, source="llm"))

    def story(self, _library: ContentLibrary, request: StoryGenRequest) -> StoryGen:
        self._enter(request.key)
        self._leave()
        return StoryGen(key=request.key, skill=request.skill.id)

    def offer(self, _library: ContentLibrary, request: OfferGenRequest) -> OfferGen:
        self._enter(request.key)
        self._leave()
        return OfferGen(key=request.key)

    def generators(self) -> Generators:
        return Generators(flash=self.flash, story=self.story, offer=self.offer)


FLASHABLE = "skill_frost_shackle"  # FL-1a：hero.skills[0] 戰歌已沒有閃現選項（蓄力不再只多冷卻）


def _town_char(library: ContentLibrary, character_id: str = "alice") -> CharacterState:
    char = new_character(library, character_id, hero(library), region="cloud_ridge")
    flash = {s: acquire(s).model_copy(update={"used": True}) for s in char.hero.skills}
    return char.model_copy(update={"flash": flash, "insight": 6})


def test_prefetch_then_serve_once(library: ContentLibrary) -> None:
    """機遇一出現就排進佇列；引擎要的時候直接拿、只呼叫一次；拿過的從暫存區拿掉。"""
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    world, char = make_world(), _at_altar(library)
    try:
        pregen.prefetch(library, world, char)
        pregen.drain(timeout=60)
        (request,) = [
            r for r in predicted_requests(library, world, char) if r.kind == "complete_offer"
        ]
        supply = pregen.supplier(library)
        got = supply(request)
        assert isinstance(got, OfferGen) and got.key == request.key
        assert rec.calls == [request.key]
        assert pregen.pending(char.character_id) == 0
        supply(request)  # 再要一次＝重新排（暫存區已經沒有）
        assert len(rec.calls) == 2
    finally:
        pregen.shutdown()


def test_late_result_waits_then_falls_back(library: ContentLibrary) -> None:
    """沒趕上：等，超過 10 秒（假時鐘）改回 ``None``（引擎改給組合器版）；等待提示回 timeout。"""
    gate = threading.Event()
    rec = Recorder(gate)
    pregen = WorldPregen(
        rec.generators(), enabled=lambda: True, clock=FakeClock(), poll_seconds=0.001
    )
    world, char = make_world(), _at_altar(library)
    try:
        (request,) = predicted_requests(library, world, char)
        out = pregen.wait(char.character_id, "complete_offer", request, library=library)
        assert out.status == "timeout" and out.waited_s >= 10
        # 第一次等待起算的 10 秒已過：引擎拿的時候不再多等
        assert pregen.supplier(library)(request) is None
    finally:
        gate.set()
        pregen.shutdown()


def test_ready_result_wait_status(library: ContentLibrary) -> None:
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    world, char = make_world(), _at_altar(library)
    try:
        pregen.prefetch(library, world, char)
        assert pregen.wait(char.character_id, "complete_offer").status == "ready"
        assert pregen.wait(char.character_id, "flash").status == "none"
    finally:
        pregen.shutdown()


def test_model_off_does_nothing(library: ContentLibrary) -> None:
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: False)
    world, char = make_world(), _at_altar(library)
    pregen.prefetch(library, world, char)
    (request,) = predicted_requests(library, world, char)
    assert pregen.supplier(library)(request) is None
    assert pregen.wait(char.character_id, "complete_offer").status == "off"
    assert rec.calls == []


def test_single_queue_and_limits(library: ContentLibrary) -> None:
    """同一時間只有一個 LLM 請求；閃現每個角色最多預先生成 FLASH_LIMIT 招。"""
    char = _town_char(library)
    requests = predicted_requests(library, make_world(), char)
    flashes = [r for r in requests if r.kind == "flash"]
    assert 1 <= len(flashes) <= FLASH_LIMIT
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    try:
        pregen.prefetch(library, make_world(), char)
        pregen.prefetch(library, make_world(), _at_altar(library, "bob"))
        pregen.drain(timeout=60)
        assert len(rec.calls) == len(flashes) + 1
        assert rec.max_active == 1
    finally:
        pregen.shutdown()


def test_unused_results_dropped(library: ContentLibrary) -> None:
    """預測換了（事件處理完）就丟掉這個角色沒用到的。"""
    rec = Recorder()
    pregen = WorldPregen(rec.generators(), enabled=lambda: True)
    char = _at_altar(library)
    try:
        pregen.prefetch(library, make_world(), char)
        pregen.drain(timeout=60)
        assert pregen.wait(char.character_id, "complete_offer").status == "ready"
        pregen.prefetch(library, make_world(), char.model_copy(update={"pending_event": None}))
        assert pregen.wait(char.character_id, "complete_offer").status == "none"
    finally:
        pregen.shutdown()


def test_generator_error_falls_back(library: ContentLibrary) -> None:
    """生成函式出錯（例如驗證失敗、連線中斷）＝``None``，引擎降級。"""

    def boom(_library: ContentLibrary, _request: OfferGenRequest) -> OfferGen:
        raise RuntimeError("模型掛了")

    pregen = WorldPregen(Generators(offer=boom), enabled=lambda: True)
    world, char = make_world(), _at_altar(library)
    try:
        (request,) = predicted_requests(library, world, char)
        assert pregen.supplier(library)(request) is None
    finally:
        pregen.shutdown()


# ---------------------------------------------------------------------------
# WorldStore：日誌記下來源；重播只讀日誌
# ---------------------------------------------------------------------------


def _store(library: ContentLibrary, tmp_path: Path, *chars: CharacterState) -> WorldStore:
    store = WorldStore(library, SessionStore(library), tmp_path, clock=lambda: NOON, prefetch=False)
    folder = tmp_path / "chars"
    folder.mkdir(parents=True, exist_ok=True)
    for char in chars:
        (folder / f"{char.character_id}.json").write_text(
            dumps_char(char), encoding="utf-8", newline="\n"
        )
    return store


def test_store_logs_sources_and_replays_without_llm(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """三個入口（這裡是閃現與機遇）都經過 LLM 生成函式、日誌標上來源；重播只讀日誌。"""
    town = _town_char(library, "c1")
    altar = _at_altar(library, "c2")
    store = _store(library, tmp_path, town, altar)
    calls: list[str] = []
    gens = provider_generators(MockLlmProvider())
    assert gens.flash is not None and gens.offer is not None
    flash_gen, offer_gen = gens.flash, gens.offer

    def flash(lib: ContentLibrary, request: FlashGenRequest) -> FlashGen:
        calls.append("flash")
        return flash_gen(lib, request)

    def offer(lib: ContentLibrary, request: OfferGenRequest) -> OfferGen:
        calls.append("offer")
        return offer_gen(lib, request)

    store.pregen = WorldPregen(Generators(flash=flash, offer=offer), enabled=lambda: True)
    skill = FLASHABLE
    start = store.world()
    try:
        store.character("c1")
        store.character("c2")
        store.pregen.drain(timeout=600)
        flashed = store.act("c1", FlashAction(skill=skill))
        solved = store.act("c2", EventSolveAction(solution=OPPORTUNITY))
    finally:
        store.pregen.shutdown()
    assert "flash" in calls and "offer" in calls
    entries = store.entries()
    flash_entry = next(e for e in entries if e.character_id == "c1")
    offer_entry = next(e for e in entries if e.character_id == "c2")
    assert [g.kind for g in flash_entry.generated] == ["flash"]
    gen = flash_entry.generated[0]
    assert isinstance(gen, FlashGen) and gen.record.source in {"llm", "partial"}
    assert [g.kind for g in offer_entry.generated] == ["complete_offer"]
    # 重播：完全不呼叫 LLM（生成函式換成會報錯的），結果和當時相同
    monkeypatch.setattr("trpg.api.world_pregen.WorldPregen._run", _never_run)
    result = replay(library, start, {"c1": town, "c2": altar}, entries)
    assert result.characters["c1"].pending_flash == flashed.char.pending_flash
    assert result.characters["c2"].pending_offers == solved.char.pending_offers


def _never_run(*_args: object) -> None:
    raise AssertionError("重播不可以呼叫 LLM")


def test_store_without_pregen_still_records_fallback(
    library: ContentLibrary, tmp_path: Path
) -> None:
    """模型關閉（沒有預先生成）：照常可以玩，日誌記下降級的來源。"""
    store = _store(library, tmp_path, _town_char(library, "c1"))
    skill = FLASHABLE
    outcome = store.act("c1", FlashAction(skill=skill))
    assert outcome.char.pending_flash is not None
    (entry,) = store.entries()
    gen = entry.generated[0]
    assert isinstance(gen, FlashGen) and gen.record.source == "template"
