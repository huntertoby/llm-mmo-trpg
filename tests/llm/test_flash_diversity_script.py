"""閃現提議多樣性量測腳本（``scripts/eval_flash_diversity.py``）的 Mock 小測試。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from tests.engine.helpers import library
from trpg.llm.flash_propose import mock_flash_source

LIB = library()
_PATH = Path(__file__).resolve().parents[2] / "scripts" / "eval_flash_diversity.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("eval_flash_diversity", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["eval_flash_diversity"] = module
    spec.loader.exec_module(module)
    return module


def test_diversity_script_runs_on_the_mock_and_summarises(tmp_path: Path) -> None:
    script = _load()
    samples = script.build_samples(LIB, 1, 0, 1)
    groups = {s.group for s in samples}
    assert {"active_summon", "active_support", "passive", "reaction", "modifier"} <= groups
    assert any(g.startswith("after_to_") for g in groups)
    tasks = script.build_tasks(LIB, samples[:6], 1)
    assert {t.scenario for t in tasks} >= {"open", "focused", "major"}

    def make_source(sink):  # type: ignore[no-untyped-def]
        return mock_flash_source(LIB, sink=sink)

    csv_path = tmp_path / "out.csv"
    rows = script.run_all(LIB, tasks[:8], make_source, workers=2, csv_path=csv_path)
    assert len(rows) == 8
    assert csv_path.read_text(encoding="utf-8").startswith("group,skill")
    text = script.summarize(LIB, script.read_csv(csv_path))
    assert "## 各模板" in text and "## 轉型" in text
    # 轉型不在 LLM 的目錄內：Mock 不會提轉型
    assert all(not t.startswith("to_") for r in rows for t in script._split(r["proposed"]))
