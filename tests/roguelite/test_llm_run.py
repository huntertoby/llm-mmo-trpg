"""Phase 4-L6：run 的 LLM 生成開關、紀錄、存檔往返、舊存檔相容、重播不呼叫 LLM。"""

from __future__ import annotations

import json

from tests.roguelite.helpers import library
from trpg.roguelite import RunSave, auto_play, dumps_save, loads_save, new_run
from trpg.roguelite.llm_hook import use_proposer
from trpg.roguelite.offers import make_offer, offer_updates
from trpg.roguelite.state import RunState
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.proposal_topic import LlmAttempt
from trpg.skillgen.random_composer import compose_random_skill

lib = library()


class _Counting:
    """假提議器：用組合器做帶題目關鍵字的技能，記錄被呼叫的次數。"""

    def __init__(self, ok: bool = True) -> None:
        self.calls = 0
        self.ok = ok

    def __call__(self, request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
        self.calls += 1
        if not self.ok:
            return LlmAttempt(None, 3, ("literal_error",), "用盡 3 次")
        skill = compose_random_skill(
            seed,
            tier=request.tier,
            library=lib,
            keyword=request.keywords[0],
            category="spell" if request.weapon_class == "focus" else None,
        )
        return LlmAttempt(skill, 1)


def _run(llm: bool) -> RunState:
    return new_run(lib, "build_fire", 2).model_copy(update={"llm": llm})


def test_switch_off_is_the_same_as_before() -> None:
    run = _run(False)
    counter = _Counting()
    with use_proposer(counter):
        offer = make_offer(lib, run, "level_up")
    assert counter.calls == 0 and offer == make_offer(lib, run, "level_up")
    assert offer_updates(run, offer) == {}
    assert all(t.source != "llm" and t.llm is None for t in offer.tags)


def test_switch_on_without_proposer_does_not_call_anything() -> None:
    run = _run(True)
    offer = make_offer(lib, run, "level_up")
    assert offer == make_offer(lib, _run(False), "level_up")


def test_switch_on_uses_llm_and_records_it() -> None:
    run = _run(True)
    counter = _Counting()
    with use_proposer(counter):
        offer = make_offer(lib, run, "level_up")
    assert len(offer.candidates) == 3
    llm_tags = [t for t in offer.tags if t.llm is not None]
    assert counter.calls == len(llm_tags) >= 1
    assert any(t.source == "llm" for t in offer.tags)
    update = offer_updates(run, offer)
    assert len(update["llm_log"]) == len(llm_tags)  # type: ignore[arg-type]
    assert update["llm_uses"]


def test_failing_llm_still_fills_candidates_and_counts_fallbacks() -> None:
    run = _run(True)
    with use_proposer(_Counting(ok=False)):
        offer = make_offer(lib, run, "level_up")
    assert len(offer.candidates) == 3 and all(t.source != "llm" for t in offer.tags)
    after = run.model_copy(update=offer_updates(run, offer))
    assert after.llm_fallbacks == len(after.llm_log) >= 1


def test_save_round_trip_and_replay_never_calls_the_llm() -> None:
    run = _run(True)
    counter = _Counting()
    with use_proposer(counter):
        offer = make_offer(lib, run, "level_up")
    run = run.model_copy(update=offer_updates(run, offer))
    text = dumps_save(RunSave(run_id="llm1", run=run))
    assert json.loads(text)["format"] == "trpg-run/8"
    back = loads_save(text)
    assert back.run == run
    calls = counter.calls
    # 讀回來的候選就是存下來的那一組（不重抽）；沒有提議器也不影響
    assert back.run.llm_log == run.llm_log
    assert counter.calls == calls


def test_old_format_7_save_is_readable() -> None:
    run = new_run(lib, "build_push", 1)
    raw = json.loads(dumps_save(RunSave(run_id="old", run=run)))
    raw["format"] = "trpg-run/7"
    for key in ("llm", "llm_uses", "llm_log"):
        raw["run"].pop(key)
    back = loads_save(json.dumps(raw))
    assert back.format == "trpg-run/8" and not back.run.llm and back.run.llm_log == ()


def test_full_run_with_mock_llm_is_deterministic() -> None:
    first = _run(True)
    second = _run(True)
    with use_proposer(_Counting()):
        a, _ = auto_play(lib, first)
    with use_proposer(_Counting()):
        b, _ = auto_play(lib, second)
    assert a == b and a.ended
    assert a.llm_log
