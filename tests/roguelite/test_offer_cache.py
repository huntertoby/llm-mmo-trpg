"""PERF-3：``make_offer`` 的結果快取（:class:`~trpg.roguelite.offers.OfferCache`）。"""

from __future__ import annotations

import dataclasses
import threading

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.roguelite import offers
from trpg.roguelite.offers import (
    OfferCache,
    make_offer,
    observe_complete,
    offer_key,
    using_offer_cache,
)
from trpg.roguelite.start import new_run
from trpg.roguelite.state import RunState, SkillOffer


def _run(seed: int = 1) -> RunState:
    return new_run(library(), "build_fire", seed).model_copy(update={"offers_made": 2})


def _boom(*_args: object, **_kwargs: object) -> SkillOffer:
    raise AssertionError("應該從快取拿")


def test_hit_returns_identical_offer(monkeypatch: pytest.MonkeyPatch) -> None:
    lib = library()
    run = _run()
    plain = make_offer(lib, run, "level_up")
    cache = OfferCache()
    with using_offer_cache(cache):
        first = make_offer(lib, run, "level_up")
        monkeypatch.setattr(offers, "_compute_offer", _boom)
        second = make_offer(lib, run, "level_up")
    assert second is first
    assert first.model_dump_json() == plain.model_dump_json()
    assert len(cache) == 1


def test_key_covers_inputs() -> None:
    lib = library()
    run = _run()
    base = offer_key(lib, run, "complete")
    assert base is not None
    assert base == offer_key(lib, run, "complete")
    others = {
        offer_key(lib, run, "level_up"),
        offer_key(lib, run, "complete", tier_bonus=1),
        offer_key(lib, run, "complete", region_keywords=("wet",)),
        offer_key(lib, run.model_copy(update={"offers_made": 3}), "complete"),
        offer_key(lib, _run(seed=2), "complete"),
        offer_key(lib, run, "complete", pinned_keyword="charged"),  # 5B-4d
    }
    assert base not in others
    assert len(others) == 6
    # 不影響候選的欄位（經驗、生命）不進鍵
    assert offer_key(lib, run.model_copy(update={"xp": run.xp + 5}), "complete") == base


def test_llm_and_observer_bypass_cache() -> None:
    lib = library()
    run = _run()
    assert offer_key(lib, run.model_copy(update={"llm": True}), "level_up") is None
    cache = OfferCache()
    seen: list[tuple[SkillDef, SkillDef]] = []
    with using_offer_cache(cache), observe_complete(lambda a, b: seen.append((a, b))):
        make_offer(lib, run, "complete")
    assert len(cache) == 0
    assert len(seen) == 3


def test_waits_for_inflight_and_recovers_from_failure() -> None:
    lib = library()
    run = _run()
    key = offer_key(lib, run, "level_up")
    assert key is not None
    cache = OfferCache()
    future = cache.reserve(lib, key)
    assert future is not None
    assert cache.reserve(lib, key) is None  # 已有人在算
    sentinel = make_offer(lib, _run(seed=9), "level_up")
    got: list[SkillOffer] = []

    def worker() -> None:
        with using_offer_cache(cache):
            got.append(make_offer(lib, run, "level_up"))

    thread = threading.Thread(target=worker)
    thread.start()
    cache.finish(key, future, sentinel)  # 另一個執行緒算完：等的人拿到同一個結果
    thread.join(timeout=60)
    assert got == [sentinel]
    # 失敗：移除這筆，之後的人自己算
    other = offer_key(lib, run, "complete")
    assert other is not None
    failed = cache.reserve(lib, other)
    assert failed is not None
    cache.finish(other, failed, None, RuntimeError("x"))
    assert not cache.has(lib, other)
    assert cache.get(lib, other) is None


def test_cache_is_bounded_and_library_checked() -> None:
    lib = library()
    cache = OfferCache(limit=2)
    for name in ("a", "b", "c"):
        future = cache.reserve(lib, name)
        assert future is not None
        cache.finish(name, future, make_offer(lib, _run(), "level_up"))
    assert len(cache) == 2
    assert not cache.has(lib, "a")
    assert cache.done(lib, "c")
    other = dataclasses.replace(lib)
    assert not cache.has(other, "c")  # 不同的內容庫物件不共用
