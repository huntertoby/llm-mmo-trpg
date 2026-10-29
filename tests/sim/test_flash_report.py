"""閃現模擬報表與 AI 策略（Phase 3W-8）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import build_parser, main
from trpg.roguelite.auto import FLASH_POLICIES
from trpg.sim.flash_report import FlashPick, RunMetrics, format_flash_report, simulate_run

SEED = 3


def _pick(**changes: object) -> FlashPick:
    base: dict[str, object] = {
        "nth": 1,
        "kind": "flash",
        "source": "minor",
        "category": "area",
        "template": "area_plus",
        "focused": False,
        "cost": 1,
        "ratio_permille": 900,
    }
    return FlashPick(**{**base, **changes})  # type: ignore[arg-type]


def _run(policy: str, seed: int, **changes: object) -> RunMetrics:
    base: dict[str, object] = {
        "policy": policy,
        "seed": seed,
        "victory": True,
        "boss_reached": True,
        "boss_won": True,
        "battles_won": 6,
        "curve": ((1, 1, 0), (2, 2, 0)),
        "picks": (_pick(), _pick(nth=3, source="transform", category="trigger")),
        "skill_flashes": (0, 3),
        "complete_skills": 1,
        "complete_offers": 2,
        "complete_gains": (130, None),
        "leftover": 1,
    }
    return RunMetrics(**{**base, **changes})  # type: ignore[arg-type]


def test_report_has_every_section_and_is_stable() -> None:
    results = [_run("none", 0), _run("all", 0, picks=(_pick(focused=True, cost=2),))]
    text = format_flash_report(results)
    for heading in (
        "## 概況",
        "## 靈感點曲線",
        "## 每招閃現次數分布",
        "### 練滿 3 次以上的招數",
        "## 閃現後預算比例",
        "## 模板與類別分布",
        "### 轉型占全部閃現的比例",
        "## 完整技能與溶掉／傳承",
    ):
        assert heading in text
    assert "策略 2 種 × 種子 1 個（0–0） ＝ 2 輪" in text
    assert text == format_flash_report(results)
    assert "| none | 1 | 100.0% | 100.0% |" in text


def test_report_handles_no_flashes() -> None:
    quiet = _run("none", 0, picks=(), skill_flashes=(0, 0), complete_gains=(), curve=())
    assert "## 概況" in format_flash_report([quiet])


def test_flash_policy_option_is_parsed_with_none_as_default() -> None:
    parser = build_parser()
    assert parser.parse_args(["run", "auto", "--seed", "1"]).flash_policy == "none"
    chosen = parser.parse_args(["run", "auto", "--seed", "1", "--flash-policy", "all"])
    assert chosen.flash_policy == "all"
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "auto", "--seed", "1", "--flash-policy", "nope"])
    assert tuple(FLASH_POLICIES) == ("none", "all", "mixed")


def test_sim_flash_rejects_an_unknown_policy(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sim", "flash", "--policies", "nope", "--seeds", "1", "--jobs", "1"]) == 2
    assert "--policies" in capsys.readouterr().err


@pytest.mark.slow
def test_policies_differ_in_focus_and_each_run_is_deterministic() -> None:
    lib = library()
    plain = simulate_run(lib, "none", SEED)
    focused = simulate_run(lib, "all", SEED)
    mixed = simulate_run(lib, "mixed", SEED)
    assert plain.picks
    assert not any(p.focused for p in plain.picks)
    assert all(p.focused for p in focused.picks if p.kind == "flash")
    assert mixed.picks
    assert simulate_run(lib, "all", SEED) == focused  # 同種子同策略必得同結果
    assert plain.curve
    assert plain.curve[0][0] == 1
    text = format_flash_report([plain, focused, mixed])
    assert text == format_flash_report([plain, focused, mixed])
