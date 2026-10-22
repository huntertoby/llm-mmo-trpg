"""CLI 輸出快照（Phase 3-1 3.4）：描述模組搬家後 CLI 輸出必須逐字不變。

快照存 SHA-256（戰鬥紀錄很長，逐字比對用雜湊即可）；刻意改變輸出時以
``UPDATE_CLI_SNAPSHOTS=1 uv run pytest tests/cli/test_output_snapshots.py`` 重新產生，
並在報告中說明原因。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from trpg.cli.main import main

SNAPSHOT_FILE = Path(__file__).parent / "snapshots" / "cli_output_hashes.json"

BATTLES: dict[str, list[str]] = {
    "battle_open_plain_trapper_7": [
        "battle", "--map", "open_plain", "--seed", "7", "--ally-build", "build_trapper",
    ],
    "battle_oil_depot_fire_7": [
        "battle", "--map", "oil_depot", "--seed", "7", "--ally-build", "build_fire",
    ],
    "battle_frozen_lake_push_3": [
        "battle", "--map", "frozen_lake", "--seed", "3", "--ally-build", "build_push",
    ],
    "battle_bridge_guardian_11": [
        "battle", "--map", "bridge_chasm", "--seed", "11", "--ally-build", "build_guardian",
    ],
    "battle_swamp_striker_5": [
        "battle", "--map", "swamp", "--seed", "5", "--ally-build", "build_striker",
    ],
    "battle_halls_storm_9": [
        "battle", "--map", "narrow_halls", "--seed", "9", "--ally-build", "build_storm",
    ],
    "battle_default_flat_42": ["battle", "--map", "test_heights_8x8", "--seed", "42"],
}  # fmt: skip


def _capture(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    code = main(argv)
    assert code == 0
    return capsys.readouterr().out


def _skill_ids(capsys: pytest.CaptureFixture[str]) -> list[str]:
    out = _capture(["skills", "list"], capsys)
    return sorted(line.split()[0] for line in out.splitlines() if line.startswith("  skill_"))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _current(capsys: pytest.CaptureFixture[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    listing = _capture(["skills", "list"], capsys)
    result["skills_list"] = _digest(listing)
    shown = "".join(_capture(["skills", "show", sid], capsys) for sid in _skill_ids(capsys))
    result["skills_show_all"] = _digest(shown)
    for name, argv in BATTLES.items():
        result[name] = _digest(_capture(argv, capsys))
    return result


@pytest.mark.slow
def test_cli_output_matches_the_recorded_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    current = _current(capsys)
    if os.environ.get("UPDATE_CLI_SNAPSHOTS") == "1":
        SNAPSHOT_FILE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    recorded = json.loads(SNAPSHOT_FILE.read_text())
    assert current == recorded
