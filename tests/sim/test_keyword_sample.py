"""``trpg sim keywords``：關鍵字組合抽樣（Phase 3-24b2，06 6.27.6）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.roguelite.start import default_start
from trpg.sim.keyword_sample import format_samples, keyword_samples, run_samples


def test_samples_are_deterministic_and_use_the_new_start() -> None:
    lib = library()
    maps = ["open_plain", "swamp"]
    a = keyword_samples(lib, samples=3, seed_start=5, maps=maps)
    b = keyword_samples(lib, samples=3, seed_start=5, maps=maps)
    assert [(s.weapon, s.keywords, s.skills, s.map_id) for s in a] == [
        (s.weapon, s.keywords, s.skills, s.map_id) for s in b
    ]
    for sample in a:
        assert (sample.weapon, sample.keywords) == default_start(lib, sample.seed)
        assert len(sample.keywords) == 2 and len(sample.skills) == 2
        assert sample.map_id in maps
        hero = sample.spec.setup.units[0]
        assert hero.template.weapon == sample.weapon


def test_small_sampling_runs_and_reports() -> None:
    lib = library()
    results = run_samples(keyword_samples(lib, samples=2, seed_start=0, maps=["open_plain"]))
    assert all(r.report.battles == 1 and r.report.completed == 1 for r in results)
    text = format_samples(lib, results)
    assert "合計：2 個樣本、2 場" in text and "依關鍵字：" in text
    assert not any(p.label_zh in text for p in lib.dev_starters.packs)


def test_cli_sim_keywords(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["sim", "keywords", "--samples", "2", "--maps", "open_plain", "--jobs", "1"])
    out = capsys.readouterr().out
    assert code == 0
    assert "關鍵字組合抽樣" in out and "合計：2 個樣本" in out
