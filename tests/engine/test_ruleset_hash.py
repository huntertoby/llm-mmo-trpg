"""規則包雜湊與戰鬥紀錄的重播前檢查（Phase 3T-2，``docs/phases/戰鬥紀錄格式變更.md``）。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.engine.runner import LOG_FORMAT, BattleLog, log_replay_problem, run_battle
from trpg.engine.setup import build_setup
from trpg.sim.lineup import default_lineup


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def log(library: ContentLibrary) -> BattleLog:
    allies, enemies = default_lineup(library, "open_plain")
    setup = build_setup(library, "open_plain", allies, enemies, max_rounds=10)
    return run_battle(setup, 3).to_log()


def test_hash_is_stable_sha256(library: ContentLibrary) -> None:
    first = hash_ruleset(library.ruleset)
    assert first == hash_ruleset(library.ruleset)
    assert len(first) == 64 and int(first, 16) >= 0


def test_new_log_carries_matching_hash(log: BattleLog) -> None:
    assert log.format == LOG_FORMAT
    assert log.ruleset_hash == hash_ruleset(log.setup.ruleset)
    assert log_replay_problem(log) is None


def test_hash_survives_json_roundtrip(log: BattleLog) -> None:
    """寫成 JSON 再讀回，內嵌規則包的雜湊不變（否則每個存下來的紀錄都會被拒絕）。"""
    again = BattleLog.model_validate_json(log.model_dump_json())
    assert log_replay_problem(again) is None


def test_old_format_is_rejected_with_chinese_reason(log: BattleLog) -> None:
    old = log.model_copy(update={"format": "trpg-battle-log/85", "ruleset_hash": None})
    problem = log_replay_problem(old)
    assert problem is not None and "舊格式的紀錄無法重播" in problem


def test_missing_and_wrong_hash_are_rejected(log: BattleLog) -> None:
    missing = log.model_copy(update={"ruleset_hash": None})
    assert "缺少 ruleset_hash" in (log_replay_problem(missing) or "")
    wrong = log.model_copy(update={"ruleset_hash": "0" * 64})
    assert "規則包雜湊不符" in (log_replay_problem(wrong) or "")
