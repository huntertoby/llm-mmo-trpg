"""BAL-3 全面基線報表：極小參數能跑完、欄位齊全、確定性（與 ``jobs`` 無關）、偏離排序。"""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path

import pytest

from trpg.cli.sim import default_sim_maps
from trpg.content.library import load_library
from trpg.sim.baseline import (
    SECTIONS,
    BaselineResult,
    BaselineSizes,
    Row,
    Target,
    format_baseline,
    rows_csv,
    run_baseline,
    top_deviations,
)

pytestmark = pytest.mark.slow

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "balance_baseline.py"
_CSV_HEADER = [
    "section", "item", "value", "unit", "n", "target", "status", "deviation", "note",
]  # fmt: skip


def _tiny() -> BaselineSizes:
    spec = importlib.util.spec_from_file_location("balance_baseline_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tiny: BaselineSizes = module.TINY
    return tiny


@pytest.fixture(scope="module")
def tiny_result() -> BaselineResult:
    library = load_library()
    return run_baseline(library, default_sim_maps(library), _tiny(), jobs=1)


def test_every_section_has_rows_and_the_csv_has_all_columns(tiny_result: BaselineResult) -> None:
    assert tiny_result.sections == SECTIONS
    for section in SECTIONS:
        assert any(r.section == section for r in tiny_result.rows), section
    parsed = list(csv.reader(io.StringIO(rows_csv(tiny_result))))
    assert parsed[0] == _CSV_HEADER
    assert len(parsed) == len(tiny_result.rows) + 1
    assert all(len(line) == len(_CSV_HEADER) for line in parsed)


def test_markdown_lists_the_top_deviations_and_every_section(tiny_result: BaselineResult) -> None:
    text = format_baseline(tiny_result)
    assert "## 偏離最大的前 10 項" in text
    for title in ("一、示範地圖", "二、Boss 戰", "三、build 矩陣", "七、一輪"):
        assert title in text
    assert "✓" in text or "⚠" in text


def test_tiny_run_is_deterministic_and_independent_of_jobs(tiny_result: BaselineResult) -> None:
    library = load_library()
    sizes = _tiny()
    again = run_baseline(library, default_sim_maps(library), sizes, jobs=2)
    assert format_baseline(again) == format_baseline(tiny_result)
    assert rows_csv(again) == rows_csv(tiny_result)


def test_deviation_is_zero_inside_the_target_and_ranked_by_distance() -> None:
    win = Target(35, 65, 30, "35–65%")
    inside = Row("maps", "a", 50.0, "%", 10, win)
    low = Row("maps", "b", 20.0, "%", 10, win)
    high = Row("maps", "c", 95.0, "%", 10, win)
    info = Row("run", "d", 3.0, "場", 10, None)
    assert inside.status == "✓" and inside.deviation == 0
    assert low.status == "⚠" and high.status == "⚠" and info.status == "—"
    assert [r.item for r in top_deviations([inside, low, high, info])] == ["c", "b"]
    assert top_deviations([inside, low, high, info], 1)[0].item == "c"
