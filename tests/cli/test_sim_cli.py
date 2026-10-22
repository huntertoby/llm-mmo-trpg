"""``trpg sim maps``（Phase 2C-1 3.5）：預設地圖、輸出確定性、``--jobs`` 無關、JSON。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.cli.sim import default_sim_maps


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_default_maps_are_the_non_test_maps_with_an_encounter() -> None:
    lib = library()
    maps = default_sim_maps(lib)
    assert maps == sorted(maps) and maps
    assert not any(m.startswith("test_") for m in maps)
    assert all(lib.map(m).encounter is not None for m in maps)
    assert {"bridge_chasm", "oil_depot", "swamp", "ruined_fort"} <= set(maps)


def test_sim_maps_prints_sections_and_timing_goes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, err = _run(["sim", "maps", "--maps", "oil_depot,swamp", "--seeds", "2"], capsys)
    assert code == 0
    assert out.startswith("批次模擬：效用 AI，種子 0–1（2 場／地圖）")
    assert "## oil_depot（2 場" in out and "## swamp（2 場" in out
    assert "秒" not in out and "執行時間" in err


@pytest.mark.xdist_group("sim_pool")
@pytest.mark.slow
def test_stdout_is_identical_across_runs_and_jobs(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["sim", "maps", "--maps", "oil_depot", "--seeds", "3", "--seed-start", "5"]
    _, first, _ = _run(argv, capsys)
    _, second, _ = _run(argv, capsys)
    _, parallel, _ = _run([*argv, "--jobs", "2"], capsys)
    assert first == second == parallel
    assert "種子 5–7" in first


def test_json_output_contains_every_map(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    code, _, err = _run(
        ["sim", "maps", "--maps", "swamp", "--seeds", "2", "--json", str(path)], capsys
    )
    assert code == 0 and str(path) in err
    data = json.loads(path.read_text("utf-8"))
    assert [r["name"] for r in data] == ["swamp"]
    assert data[0]["battles"] == 2 and "anomalies" in data[0]


def test_unknown_or_encounterless_maps_are_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["sim", "maps", "--maps", "nope", "--seeds", "1"], capsys)
    assert code == 1 and "nope" in err
    code, _, err = _run(["sim", "maps", "--maps", "test_flat_6x6", "--seeds", "1"], capsys)
    assert code == 2 and "encounter" in err
