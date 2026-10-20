"""build × 地圖矩陣（Phase 2C-3 5.4、5.6-5、5.6-6）：排名、類型平均、兩條標準與確定性。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.sim.matrix import (
    MapInfo,
    RawCell,
    assemble_matrix,
    format_matrix,
    matrix_specs,
    run_matrix,
    top_count,
)

BUILDS = ("a", "b", "c", "d", "e", "f")
MAPS = (
    MapInfo(map_id="m1", archetype="forest"),
    MapInfo(map_id="m2", archetype="swamp"),
    MapInfo(map_id="m3", archetype="swamp"),
)


def _cell(build: str, map_id: str, archetype: str, wins: int, dpr: float, **kw: float) -> RawCell:
    return RawCell(
        build_id=build,
        map_id=map_id,
        archetype=archetype,
        battles=10,
        completed=10,
        ally_wins=wins,
        draws=0,
        hero_dpr=dpr,
        hero_survival=kw.get("survival", 1.0),
        rounds_mean=kw.get("rounds", 5.0),
    )


def _matrix(wins: dict[str, tuple[int, int, int]], dpr: dict[str, tuple[float, float, float]]):  # type: ignore[no-untyped-def]
    raw = []
    for b in BUILDS:
        for info, w, d in zip(MAPS, wins[b], dpr[b], strict=True):
            raw.append(_cell(b, info.map_id, info.archetype, w, d))
    return assemble_matrix(BUILDS, MAPS, raw, range(10))


# 勝率（10 場）：每張地圖的名次由勝率決定，平手比 DPR
WINS = {
    "a": (9, 8, 2),
    "b": (8, 3, 3),
    "c": (7, 9, 9),
    "d": (4, 5, 7),
    "e": (4, 4, 4),
    "f": (1, 1, 1),
}
DPR = {
    "a": (10.0, 5.0, 5.0),
    "b": (9.0, 5.0, 5.0),
    "c": (8.0, 5.0, 5.0),
    "d": (7.0, 6.0, 6.0),
    "e": (7.5, 7.0, 7.0),  # 與 d 在 m1 同為 4 勝：DPR 高者（e 7.5）排前面
    "f": (1.0, 1.0, 1.0),
}


def test_top_is_the_first_third_of_the_builds() -> None:
    assert [top_count(n) for n in (1, 2, 3, 5, 6, 9)] == [1, 1, 1, 1, 2, 3]


def test_ranks_within_each_map_use_win_rate_then_hero_dpr() -> None:
    report = _matrix(WINS, DPR)
    m1 = {c.build_id: c for c in report.cells if c.map_id == "m1"}
    assert [m1[b].rank for b in BUILDS] == [1, 2, 3, 5, 4, 6]  # d 與 e 同為 4 勝 → e 的 DPR 較高
    assert [b for b in BUILDS if m1[b].top] == ["a", "b"]  # 前 2 名
    assert m1["a"].win_rate == 0.9 and m1["a"].hero_dpr == 10.0


def test_ties_in_win_rate_and_dpr_fall_back_to_build_order() -> None:
    raw = [_cell(b, "m1", "forest", 5, 3.0) for b in BUILDS]
    report = assemble_matrix(BUILDS, [MAPS[0]], raw, [0])
    assert [c.rank for c in report.cells] == [1, 2, 3, 4, 5, 6]


def test_an_archetype_with_two_maps_averages_its_values_before_ranking() -> None:
    report = _matrix(WINS, DPR)
    swamp = {c.build_id: c for c in report.archetype_cells if c.archetype == "swamp"}
    assert swamp["a"].maps == ("m2", "m3")
    assert swamp["a"].win_rate == pytest.approx((0.8 + 0.2) / 2)
    assert swamp["c"].win_rate == pytest.approx(0.9)
    assert swamp["d"].hero_dpr == pytest.approx(6.0)
    # swamp 平均勝率：a 50%、b 30%、c 90%、d 60%、e 40%、f 10%
    assert [b for b, c in sorted(swamp.items(), key=lambda kv: kv[1].rank)] == [
        "c",
        "d",
        "a",
        "e",
        "b",
        "f",
    ]
    assert {b for b in BUILDS if swamp[b].top} == {"c", "d"}


def test_standard_one_fails_when_a_build_is_top_in_every_archetype() -> None:
    # c 在 swamp 第 1；讓 c 在 forest 也進前 2 → c 在所有類型都前段
    wins = dict(WINS, a=(1, 8, 2), c=(9, 9, 9), b=(8, 3, 3))
    report = _matrix(wins, DPR)
    assert report.standards.always_top == ("c",)
    assert not report.standards.no_build_always_top


def test_standard_two_lists_builds_that_are_never_top() -> None:
    report = _matrix(WINS, DPR)
    top_somewhere = {c.build_id for c in report.archetype_cells if c.top}
    assert top_somewhere == {"a", "b", "c", "d"}
    assert report.standards.never_top == ("e", "f")
    assert not report.standards.every_build_top_somewhere
    assert report.standards.no_build_always_top  # 沒有 build 兩種類型都前段


def test_both_standards_pass_when_every_build_is_top_in_exactly_one_archetype() -> None:
    infos = [
        MapInfo(map_id="m1", archetype="forest"),
        MapInfo(map_id="m2", archetype="swamp"),
        MapInfo(map_id="m3", archetype="corridor"),
    ]
    # 每個類型的前 2 名（6 個 build → 前段 2 名）：forest a、b；swamp c、d；corridor e、f
    leaders = {"m1": ("a", "b"), "m2": ("c", "d"), "m3": ("e", "f")}
    raw = [
        _cell(b, info.map_id, info.archetype, 8 if b in leaders[info.map_id] else 2, 1.0)
        for info in infos
        for b in BUILDS
    ]
    report = assemble_matrix(BUILDS, infos, raw, [0])
    assert report.standards.archetypes == 3 and report.standards.top_count == 2
    assert report.standards.always_top == () and report.standards.never_top == ()
    assert report.standards.no_build_always_top and report.standards.every_build_top_somewhere
    text = format_matrix(report)
    assert "1. 沒有任何 build 在所有地圖類型都排名前段：通過" in text
    assert "2. 每個 build 至少在一種地圖類型排名前段：通過" in text


def test_a_single_archetype_marks_standard_one_as_reference_only() -> None:
    raw = [_cell(b, "m1", "forest", 9 - i, 1.0) for i, b in enumerate(BUILDS)]
    report = assemble_matrix(BUILDS, [MAPS[0]], raw, [0])
    assert report.standards.always_top == ("a", "b")
    assert "標準 1 僅供參考" in format_matrix(report)


def test_text_report_lists_ranks_matrices_and_both_standards() -> None:
    report = _matrix(WINS, DPR)
    text = format_matrix(report)
    for fragment in (
        "## m1（forest）",
        "## 勝率矩陣",
        "## build 英雄 DPR 矩陣",
        "## 排名矩陣",
        "## 6.8 標準檢查",
        "不通過：e、f",
    ):
        assert fragment in text
    assert "| 1* | a | 90.0% | 10.00 |" in text
    assert text == format_matrix(report)


def test_specs_put_the_build_hero_first_then_the_companions_against_the_encounter() -> None:
    lib = library()
    specs = matrix_specs(lib, ["build_push"], ["open_plain"], [0, 1])
    (build, map_id, spec) = specs[0]
    assert (build, map_id, spec.seeds) == ("build_push", "open_plain", (0, 1))
    ally = [u.template.id for u in spec.setup.units if u.team.value == "ally"]
    enemy = [u.template.id for u in spec.setup.units if u.team.value == "enemy"]
    assert ally == ["build_push", "sim_companion_fighter", "sim_companion_archer"]
    encounter = lib.map("open_plain").encounter
    assert encounter is not None and enemy == list(encounter.enemies)
    hero = spec.setup.units[0].template
    assert hero.skills[:3] == ("skill_gale_kick", "skill_leap_slam", "skill_charged_cleave")
    with pytest.raises(ValueError, match="未知的 build"):
        matrix_specs(lib, ["nope"], ["open_plain"], [0])


def test_a_real_matrix_is_deterministic_and_independent_of_jobs() -> None:
    lib = library()
    args = (lib, ["build_push", "build_ranged"], ["open_plain"], [0, 1])
    first = run_matrix(*args, jobs=1)
    again = run_matrix(*args, jobs=1)
    parallel = run_matrix(*args, jobs=2)
    assert first == again == parallel
    assert format_matrix(first) == format_matrix(parallel)
    cell = first.cell("build_push", "open_plain")
    assert cell.battles == 2 and cell.completed == 2 and cell.errors == 0
    assert 0.0 <= cell.hero_survival <= 1.0 and cell.rank in (1, 2)


def test_matrix_cli_output_is_identical_between_runs_and_jobs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["sim", "matrix", "--builds", "build_fire,build_tank", "--maps", "open_plain"]
    outputs = []
    for jobs in ("1", "1", "2"):
        assert main([*argv, "--seeds", "2", "--jobs", jobs]) == 0
        captured = capsys.readouterr()
        outputs.append(captured.out)
        assert "執行時間" in captured.err and "執行時間" not in captured.out
    assert outputs[0] == outputs[1] == outputs[2]
    assert "build_fire" in outputs[0] and "## 6.8 標準檢查" in outputs[0]


def test_matrix_cli_rejects_unknown_builds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sim", "matrix", "--builds", "nope", "--maps", "open_plain", "--seeds", "1"]) == 2
    assert "未知的 build" in capsys.readouterr().err
