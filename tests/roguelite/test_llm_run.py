"""Phase 4-L6：run 的 LLM 生成開關、紀錄、存檔往返、舊存檔相容、重播不呼叫 LLM。"""

from __future__ import annotations

import json

from tests.roguelite.helpers import library
from trpg.content.skills import SkillDef
from trpg.llm.candidate_source import mock_naming_client, name_attempt
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
    assert json.loads(text)["format"] == "trpg-run/9"
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
    assert back.format == "trpg-run/9" and not back.run.llm and back.run.llm_log == ()


def test_full_run_with_mock_llm_is_deterministic() -> None:
    first = _run(True)
    second = _run(True)
    with use_proposer(_Counting()):
        a, _ = auto_play(lib, first)
    with use_proposer(_Counting()):
        b, _ = auto_play(lib, second)
    assert a == b and a.ended
    assert a.llm_log


# -- Phase 4-L7：命名與敘事 -----------------------------------------------------


def _naming_proposer(counter: list[str]):  # type: ignore[no-untyped-def]
    """Mock 提議（手寫技能轉成的提議）＋ Mock 命名；記錄命名被呼叫時的技能 ID。"""

    base = _Counting()
    taken: set[str] = set()

    def namer(skill: SkillDef, seed: int):  # type: ignore[no-untyped-def]
        counter.append(skill.id)
        return mock_naming_client(lib, skill, seed)

    def propose(request: ProposalRequest, ctx: ProposalContext, seed: int) -> LlmAttempt:
        attempt = base(request, ctx, seed)
        return name_attempt(attempt, namer, lib, request, seed=seed, taken=taken, max_attempts=3)

    return propose


def test_generated_names_and_narrative_are_recorded_and_replay_is_silent() -> None:
    calls: list[str] = []
    run = _run(True)
    with use_proposer(_naming_proposer(calls)):
        offer = make_offer(lib, run, "level_up")
    named = [t for t in offer.tags if t.llm is not None and t.llm.name_source is not None]
    assert named, "至少有一個 LLM 候選成功並命名"
    assert len(calls) == len(named) and all(t.llm.name_attempts >= 1 for t in named if t.llm)
    for tag, skill in zip(offer.tags, offer.candidates, strict=True):
        if tag.llm is not None and tag.llm.name_source == "llm":
            assert skill.narrative.cast_flavor.startswith("碎界的低鳴")
    run = run.model_copy(update=offer_updates(run, offer))
    text = dumps_save(RunSave(run_id="llm2", run=run))
    back = loads_save(text)
    assert back.run.llm_log == run.llm_log and calls and len(calls) == len(named)
    assert any(r.name_source for r in back.run.llm_log)


def test_full_run_with_naming_is_deterministic() -> None:
    first: list[str] = []
    second: list[str] = []
    with use_proposer(_naming_proposer(first)):
        a, _ = auto_play(lib, _run(True))
    with use_proposer(_naming_proposer(second)):
        b, _ = auto_play(lib, _run(True))
    assert a == b and first == second


def test_old_format_8_save_without_naming_fields_is_readable() -> None:
    run = new_run(lib, "build_push", 1)
    raw = json.loads(dumps_save(RunSave(run_id="old8", run=run)))
    raw["format"] = "trpg-run/8"
    assert loads_save(json.dumps(raw)).format == "trpg-run/9"
