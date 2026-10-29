"""4-L5：提議的重試迴圈、退回、統計（全部用 MockLLMClient，不需網路）。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from trpg.content.library import ContentLibrary
from trpg.llm import (
    LLMBadResponse,
    LLMTimeout,
    LLMUnavailable,
    MockLLMClient,
    OpenAICompatClient,
)
from trpg.llm import propose as propose_module
from trpg.llm.client import ChatMessage
from trpg.llm.config import load_llm_config
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.llm.propose import (
    AttemptRecord,
    ProposalOutcome,
    ProposalStats,
    propose_skill,
)
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.composer_tuning import tuning_bounds
from trpg.skillgen.proposal import ProposalContext, proposal_from_skill
from trpg.skillgen.proposal_budget import evaluate_with_repair
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError
from trpg.skillgen.random_composer import default_library

STRIKE = ProposalRequest(1, "common", skeleton="strike")
CTX = ProposalContext(1, "common")
BAD_JSON = "這不是 JSON"
BAD_SHAPE = json.dumps({"kind": "active", "skeleton": "strike"})


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def _proposal_text(library: ContentLibrary, skill_id: str) -> str:
    return json.dumps(proposal_from_skill(library.skills[skill_id], library), ensure_ascii=False)


def _ticks() -> Iterator[float]:
    value = 0.0
    while True:
        yield value
        value += 0.5


def _clock() -> Any:
    ticks = _ticks()
    return lambda: next(ticks)


def _user(call: list[ChatMessage]) -> str:
    return next(m["content"] for m in call if m["role"] == "user")


def test_bad_bad_good(library: ContentLibrary) -> None:
    good = _proposal_text(library, "skill_fire_arrow")
    client = MockLLMClient([BAD_JSON, BAD_SHAPE, good])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3, clock=_clock())
    assert outcome.source == "llm" and outcome.attempts == 3 and outcome.reason is None
    assert outcome.codes[0] == ("json_invalid",)
    assert outcome.codes[1] and outcome.codes[2] == ()
    assert outcome.seconds == pytest.approx(1.5)
    assert client.schemas[0] is not None
    second, third = _user(client.calls[1]), _user(client.calls[2])
    assert "<previous_proposal>" in second and "這不是 JSON" in second
    assert "json_invalid" in second and "<errors>" in second
    assert "<previous_proposal>" in third and BAD_SHAPE in third
    for code in outcome.codes[1]:
        assert code in third
    assert "<previous_proposal>" not in _user(client.calls[0])


def test_bad_three_times_falls_back_to_composer(library: ContentLibrary) -> None:
    client = MockLLMClient([BAD_JSON, BAD_SHAPE, BAD_JSON])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert outcome.source == "composer" and outcome.attempts == 3
    assert outcome.reason is not None and "用盡 3 次" in outcome.reason
    assert outcome.skill.skeleton == "strike" and outcome.skill.rarity == "common"
    assert len(client.calls) == 3


def test_unavailable_falls_back_immediately(library: ContentLibrary) -> None:
    client = MockLLMClient([LLMUnavailable("連不上"), _proposal_text(library, "skill_fire_arrow")])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert len(client.calls) == 1 and outcome.attempts == 1
    assert outcome.source == "composer" and outcome.codes == (("llm.unavailable",),)
    assert outcome.reason is not None and outcome.reason.startswith("llm.unavailable")


def test_timeout_and_bad_response_count_as_attempts(library: ContentLibrary) -> None:
    good = _proposal_text(library, "skill_fire_arrow")
    client = MockLLMClient([LLMTimeout("逾時"), LLMBadResponse("壞"), good])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert outcome.source == "llm" and outcome.attempts == 3
    assert outcome.codes == (("llm.timeout",), ("llm.bad_response",), ())


def test_subset_error_falls_back_without_calling(
    library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_subset(*_: Any, **__: Any) -> Any:
        raise SubsetError("測試：沒有可用結構")

    monkeypatch.setattr(propose_module, "build_proposal_prompt", no_subset)
    client = MockLLMClient([])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert client.calls == [] and outcome.attempts == 0
    assert outcome.source == "composer"
    assert outcome.reason is not None and outcome.reason.startswith("subset.unavailable")


def test_budget_weak_only_is_fixed_without_llm(library: ContentLibrary) -> None:
    """最小補值下只剩 ``budget.weak`` 的提議：預算器補完就通過，不回 LLM。"""
    client = MockLLMClient([_proposal_text(library, "skill_fire_arrow")])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert outcome.source == "llm" and len(client.calls) == 1
    low, high = tuning_bounds(library)
    assert low <= skill_budget(outcome.skill, library).ratio <= high


def test_no_cooldown_big_area_filled_by_engine(library: ContentLibrary) -> None:
    skill = library.skills["skill_blinding_dark"]
    # 3W-9：3×3 要角色 2 階才在選單裡；這裡只驗修補機制，照手寫技能自己的 1 階驗證（來源手寫）
    request = ProposalRequest(2, skill.rarity, skeleton=skill.skeleton)
    ctx = ProposalContext(skill.tier, skill.rarity, origin="builtin")
    client = MockLLMClient([_proposal_text(library, "skill_blinding_dark")])
    outcome = propose_skill(client, library, request, ctx, seed=3)
    assert outcome.source == "llm" and len(client.calls) == 1
    assert outcome.records[0].repaired == ("exclusion.no_cooldown_big_area",)
    assert outcome.skill.cost.cooldown == 1


def test_numbers_come_from_budget_filler(library: ContentLibrary) -> None:
    text = _proposal_text(library, "skill_fire_arrow")
    first = propose_skill(MockLLMClient([text]), library, STRIKE, CTX, seed=8)
    again = propose_skill(MockLLMClient([text]), library, STRIKE, CTX, seed=8)
    assert first.skill == again.skill
    models = build_proposal_prompt(library, STRIKE).models
    direct = evaluate_with_repair(text, models, library, CTX, seed=8).result.skill
    assert direct == first.skill  # 數值就是預算器（同提議、同 seed）的結果
    assert "multiplier_permille" not in text and "ap_cost" not in text  # 提議本身沒有數值
    assert first.skill.effects[0].multiplier_permille is not None
    assert first.skill.provenance.created_by == "llm"


@pytest.mark.parametrize(
    "wrap",
    [
        lambda t: f"```json\n{t}\n```",
        lambda t: f"<think>先想一下</think>\n{t}",
        lambda t: f"<think>想</think>```\n{t}\n```",
    ],
)
def test_wrapped_responses_still_parse(library: ContentLibrary, wrap: Any) -> None:
    client = MockLLMClient([wrap(_proposal_text(library, "skill_fire_arrow"))])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3)
    assert outcome.source == "llm" and outcome.attempts == 1


def test_max_attempts_from_config(library: ContentLibrary) -> None:
    assert load_llm_config(env={}).max_retries == 3
    client = MockLLMClient([BAD_JSON, BAD_JSON])
    outcome = propose_skill(client, library, STRIKE, CTX, seed=3, max_attempts=2)
    assert outcome.attempts == 2 and outcome.source != "llm"


# ---- 統計 ----


def _outcome(library: ContentLibrary, source: str, codes: list[tuple[str, ...]]) -> ProposalOutcome:
    records = tuple(AttemptRecord(c, 1.0) for c in codes)
    return ProposalOutcome(library.skills["skill_fire_arrow"], source, records)  # type: ignore[arg-type]


def test_stats_and_alert(library: ContentLibrary) -> None:
    outcomes = [
        _outcome(library, "llm", [()]),
        _outcome(library, "llm", [("budget.over",), ()]),
        _outcome(library, "llm", [()]),
        _outcome(library, "llm", [()]),
        _outcome(library, "composer", [("json_invalid",)] * 3),
    ]
    stats = ProposalStats.of(outcomes[:4])
    assert stats.total == 4 and stats.first_pass == 3 and stats.fallbacks == 0
    assert not stats.alert
    stats.add(outcomes[4])
    assert stats.first_pass_permille == 600
    assert stats.fallback_permille == 200 and not stats.alert  # 等於 20% 不提醒
    assert stats.mean_attempts == pytest.approx(8 / 5)
    assert stats.mean_seconds == pytest.approx(8 / 5)
    assert stats.codes == {"budget.over": 1, "json_invalid": 3}
    assert dict(stats.sources) == {"llm": 4, "composer": 1}
    stats.add(_outcome(library, "pool", [("llm.unavailable",)]))
    assert stats.fallback_permille == 333 and stats.alert
    text = "\n".join(stats.summary_lines())
    assert "退回率" in text and "提醒" in text and "pool 1" in text
    assert ProposalStats().summary_lines()[0].endswith("0")


# ---------------------------------------------------------------------------
# 4-L5b：先修可修的、再回報其餘；版型與骨架結構進 prompt
# ---------------------------------------------------------------------------


def test_mixed_errors_engine_repairs_cooldown_first(library: ContentLibrary) -> None:
    """可修（沒有冷卻的大範圍）與不可修（骨架不合）混在一起：引擎先補冷卻，回給 LLM 的錯誤
    只剩不可修的；第二次 LLM 改對後通過。"""
    skill = library.skills["skill_blinding_dark"]
    request = ProposalRequest(2, skill.rarity)  # 3×3 要角色 2 階（3W-9；同上）
    ctx = ProposalContext(skill.tier, skill.rarity, origin="builtin")
    good = proposal_from_skill(skill, library)
    bad = {**good, "skeleton": "strike"}
    client = MockLLMClient([json.dumps(bad, ensure_ascii=False), json.dumps(good)])
    outcome = propose_skill(client, library, request, ctx, seed=3)
    assert outcome.source == "llm" and outcome.attempts == 2
    first = outcome.records[0]
    assert "exclusion.no_cooldown_big_area" in first.repaired
    assert "exclusion.no_cooldown_big_area" not in first.codes
    assert first.codes  # 不可修的錯誤照樣回報
    feedback = _user(client.calls[1])
    assert "no_cooldown_big_area" not in feedback.split("<errors>")[1]


def test_charge_through_form_in_prompt_and_schema(library: ContentLibrary) -> None:
    """帶 charge_through 的提議走自己的版型：available 有它的說明、形狀只有 ground_tile。"""
    request = ProposalRequest(2, "rare", skeleton="displace")  # 衝鋒穿越要角色 2 階（3W-9）
    prompt = build_proposal_prompt(library, request)
    layouts = dict(prompt.models.layouts)
    assert "charge_through" in layouts and "ground_tile" in layouts["charge_through"]
    user = _user(prompt.messages)
    assert "charge_through" in user and '"layouts"' in user
    shape = prompt.json_schema["$defs"]["SkillProposal_charge_through"]["properties"]["shape"]
    assert shape == {"$ref": "#/$defs/Shape_ground_tile"}
    rush = _proposal_text(library, "skill_bull_rush")
    assert json.loads(rush)["layout"] == "charge_through"
    outcome = propose_skill(
        MockLLMClient([rush]), library, request, ProposalContext(2, "rare"), seed=3
    )
    assert outcome.source == "llm" and outcome.skill.shape.type == "ground_tile"


def test_common_request_status_enum_excludes_rare_statuses(library: ContentLibrary) -> None:
    prompt = build_proposal_prompt(library, STRIKE)
    status = prompt.json_schema["$defs"]["Effect_apply_status"]["properties"]["status"]["enum"]
    rare = {s.id for s in library.ruleset.statuses.statuses if s.min_rarity != "common"}
    assert rare and rare.isdisjoint(status)


@pytest.mark.llm
def test_real_model_propose_one(library: ContentLibrary) -> None:
    r"""真模型（需先用 F:\WSL\start.bat 啟動，連接埠與 config/llm.toml 一致）：一個題目跑完整
    流程，結果是 ``llm`` 或退回皆可，只驗流程不丟例外。
    執行：``uv run pytest -m llm tests/llm/test_propose.py``。"""
    config = load_llm_config()
    client = OpenAICompatClient(config)
    request = ProposalRequest(1, "rare", keywords=("ignite",))
    try:
        outcome = propose_skill(
            client,
            library,
            request,
            ProposalContext(1, "rare"),
            seed=1,
            max_attempts=config.max_retries,
        )
    finally:
        client.close()
    assert outcome.source in ("llm", "composer", "pool", "workshop")
    assert 1 <= outcome.attempts <= config.max_retries
