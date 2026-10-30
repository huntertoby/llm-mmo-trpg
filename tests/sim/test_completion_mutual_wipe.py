"""BAL-4c：完成度檢查把「雙方同時全滅」視為合法結束，輪數上限的平手仍算 ``draw`` 異常。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import library
from trpg.sim import completion
from trpg.sim.batch import MUTUAL_WIPE_DETAIL, BatchReport, BatchSpec, BattleOutcome, build_report
from trpg.sim.completion import CompletionConfig, format_completion, run_completion
from trpg.sim.metrics import BattleMetrics, metrics_from_events


def _metrics(seed: int, *, end_reason: str | None) -> BattleMetrics:
    return metrics_from_events(
        seed=seed,
        units=[],
        events=[],
        bounds=None,
        ap_spent={},
        winner=None,
        rounds=6,
        actions=10,
        end_reason=end_reason,
    )


def test_metrics_flag_mutual_wipe_only_for_eliminate_draws() -> None:
    assert _metrics(0, end_reason="eliminate").mutual_wipe
    assert not _metrics(0, end_reason="round_limit").mutual_wipe
    assert not _metrics(0, end_reason=None).mutual_wipe
    # 不進序列化：JSON 報表與夾具不變
    assert "mutual_wipe" not in _metrics(0, end_reason="eliminate").model_dump()


def test_batch_report_labels_the_mutual_wipe_draw() -> None:
    outcomes = [
        BattleOutcome(0, metrics=_metrics(0, end_reason="eliminate")),
        BattleOutcome(1, metrics=_metrics(1, end_reason="round_limit")),
    ]
    draw = build_report("x", outcomes).anomaly("draw")
    assert draw is not None
    assert draw.seeds == (0, 1)
    assert draw.details == {0: MUTUAL_WIPE_DETAIL}


def test_completion_counts_mutual_wipe_as_legal_but_round_limit_draw_as_anomaly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_batches(specs: Sequence[BatchSpec], *, jobs: int = 1) -> list[BatchReport]:
        outcomes = [
            BattleOutcome(0, metrics=_metrics(0, end_reason="eliminate")),
            BattleOutcome(1, metrics=_metrics(1, end_reason="round_limit")),
        ]
        return [build_report(spec.name, outcomes) for spec in specs]

    monkeypatch.setattr(completion, "run_batches", fake_run_batches)
    report = run_completion(library(), ("open_plain",), [0, 1], configs=[CompletionConfig()])
    assert [(a.kind, a.seed) for a in report.anomalies] == [("draw", 1)]
    assert [(a.kind, a.seed) for a in report.mutual_wipes] == [("draw", 0)]
    assert report.cell(CompletionConfig(), "open_plain").anomalies == 1
    text = format_completion(report)
    assert "draw 1 —— 未通過" in text
    assert "同歸於盡（雙方同時全滅，合法結束、不算異常）1 場：(無指揮官, open_plain, 0)" in text


def test_completion_with_only_mutual_wipes_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_batches(specs: Sequence[BatchSpec], *, jobs: int = 1) -> list[BatchReport]:
        outcomes = [BattleOutcome(0, metrics=_metrics(0, end_reason="eliminate"))]
        return [build_report(spec.name, outcomes) for spec in specs]

    monkeypatch.setattr(completion, "run_batches", fake_run_batches)
    report = run_completion(library(), ("open_plain",), [0], configs=[CompletionConfig()])
    assert report.clean
    assert "draw 0 —— 通過" in format_completion(report)
