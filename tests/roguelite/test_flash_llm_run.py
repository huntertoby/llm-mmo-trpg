"""Phase 3W-5：閃現出題接上 3W-7 的 LLM 變化提議（只用 Mock）、舊存檔轉換。"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import cache

import pytest
from pydantic import BaseModel

from tests.roguelite.helpers import library
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_source
from trpg.roguelite import (
    RunSave,
    RunState,
    apply_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_run,
)
from trpg.roguelite.auto import AutoStop
from trpg.roguelite.flashes import comparable_run, problem_of
from trpg.roguelite.llm_hook import FlashSourceFactory, use_flash_source
from trpg.roguelite.state import CampfireNode, FlashChoice, FlashPickChoice, GearOfferNode
from trpg.skillgen.flash import FlashOptionSource

BUILD = "build_fire"
SEED = 6


def _stop_at(kind: type[object]) -> AutoStop:
    return lambda run, _battle: isinstance(run.node, kind)


@cache
def _gear() -> RunState:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, SEED), stop=_stop_at(GearOfferNode))
    return run


def _mock() -> FlashSourceFactory:
    return lambda sink: mock_flash_source(library(), sink=sink)


def _ready(run: RunState) -> str:
    return next(s for s in run.hero.skills if problem_of(library(), run, s) is None)


def test_with_llm_on_the_flash_offer_asks_the_model_and_logs_it() -> None:
    run = _gear().model_copy(update={"llm": True})
    with use_flash_source(_mock()):
        opened = apply_choice(library(), run, FlashChoice(skill=_ready(run)))
    assert len(opened.flash_llm_log) == 1
    record = opened.flash_llm_log[0]
    assert record.tag.startswith(f"flash/{_ready(run)}/1/0")
    assert record.source == "llm" and record.wanted == 4 and record.accepted
    offer = opened.pending_flash.offer  # type: ignore[union-attr]
    keys = [o.variation.key() for o in offer.options]
    assert [v.key() for v in record.accepted] == keys[: len(record.accepted)]
    # 存檔往返；比對時排除耗時
    back = loads_save(dumps_save(RunSave(run_id="l", run=opened))).run
    assert comparable_run(back) == comparable_run(opened)
    slow = opened.model_copy(
        update={"flash_llm_log": (record.model_copy(update={"seconds": 9.5}),)}
    )
    assert comparable_run(slow) == comparable_run(opened) and slow != opened


def test_llm_off_or_no_source_uses_the_templates() -> None:
    off = _gear()
    with use_flash_source(_mock()):
        plain = apply_choice(library(), off, FlashChoice(skill=_ready(off)))
    assert plain.flash_llm_log == ()
    on = off.model_copy(update={"llm": True})
    alone = apply_choice(library(), on, FlashChoice(skill=_ready(on)))
    assert alone.flash_llm_log == ()
    assert alone.pending_flash == plain.pending_flash  # 沒有來源時和關閉逐字相同


class _Exploding:
    """被呼叫就失敗的來源工廠：證明選擇與重播不會再請 LLM。"""

    def __call__(self, sink: Callable[[BaseModel], None]) -> FlashOptionSource:
        raise AssertionError("不應該呼叫 LLM")


def test_picking_and_replaying_a_saved_offer_never_calls_the_model() -> None:
    run = _gear().model_copy(update={"llm": True})
    with use_flash_source(_mock()):
        opened = apply_choice(library(), run, FlashChoice(skill=_ready(run)))
    loaded = loads_save(dumps_save(RunSave(run_id="r", run=opened))).run
    with use_flash_source(_Exploding()):
        picked = apply_choice(library(), loaded, FlashPickChoice(pick=0))
        direct = apply_choice(library(), opened, FlashPickChoice(pick=0))
    assert comparable_run(picked) == comparable_run(direct)


@pytest.mark.slow
def test_a_full_auto_run_with_the_mock_source_is_replayable() -> None:
    lib = library()

    def final() -> RunState:
        start = new_run(lib, BUILD, SEED).model_copy(update={"llm": True})
        with use_flash_source(_mock()):
            run, _ = auto_play(lib, start)
        return run

    a, b = final(), final()
    assert a.flash_llm_log and comparable_run(a) == comparable_run(b)
    assert all(isinstance(r.seconds, float) for r in a.flash_llm_log)


def test_llm_flash_source_class_is_what_the_mock_builds() -> None:
    assert isinstance(_mock()(lambda _r: None), LlmFlashSource)


# ---------------------------------------------------------------------------
# 舊存檔轉換（/11 → /12）
# ---------------------------------------------------------------------------


def _old(run: RunState, **extra: object) -> str:
    raw = json.loads(dumps_save(RunSave(run_id="old", run=run)))
    raw["format"] = "trpg-run/11"
    body = raw["run"]
    for key in ("insight", "flash", "flash_bases", "pending_flash", "complete_offers_done"):
        body.pop(key, None)
    body.pop("flash_llm_log", None)
    body.update(extra)
    return json.dumps(raw)


def test_old_saves_turn_skill_points_into_insight_by_wins() -> None:
    run = _gear()
    first = run.hero.skills[0]
    text = _old(
        run,
        skill_points=4,
        skill_levels={first: 3},
        evolutions={},
    )
    save = loads_save(text)
    wins = sum(1 for r in run.history if r.won and not r.boss)
    assert save.format == "trpg-run/13"
    assert save.run.insight == wins == 1  # 照新規則重算：每贏一場 1 點，技能點作廢
    assert save.run.flash == {} and save.run.hero.skills == run.hero.skills
    assert "skill_levels" not in json.loads(dumps_save(save))["run"]


def test_old_campfire_saves_drop_the_reroll_offer() -> None:
    camp = _gear().model_copy(update={"node": CampfireNode(after_battle=3)})
    raw = json.loads(_old(camp))
    raw["run"]["node"] = {"kind": "campfire", "after_battle": 3, "rerolls_left": 1, "offer": None}
    save = loads_save(json.dumps(raw))
    assert save.run.node == CampfireNode(after_battle=3)
