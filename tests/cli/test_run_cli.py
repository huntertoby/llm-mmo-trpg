"""``trpg run new|auto|show``（Phase 3-5a）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.roguelite.helpers import VICTORY, full_run, library
from trpg.cli.main import main
from trpg.roguelite import RunSave, auto_play, new_run, write_save


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_run_new_writes_a_save_and_show_reads_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "4", "--build", "build_push", "--attrs", "str=3,con=1"]
    code, out, _ = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    saves = list(tmp_path.glob("run-*.json"))
    assert len(saves) == 1
    assert str(saves[0]) in out
    assert "力量 13" in out and "體質 11" in out
    assert "第 6 場 Boss" in out
    raw = json.loads(saves[0].read_text(encoding="utf-8"))
    assert raw["format"] == "trpg-run/7"
    assert raw["run"]["seed"] == 4
    code, shown, _ = _run(["run", "show", str(saves[0])], capsys)
    assert code == 0
    assert "trpg-run/7" in shown and "build_push" in shown and "目前：戰鬥" in shown


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--build", "build_nobody"], "未知的 build"),
        (["--build", "build_push", "--attrs", "str=1"], "必須分配 4 點"),
    ],
)
def test_run_new_rejects_bad_input(
    argv: list[str], message: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(["run", "new", "--seed", "1", *argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 2
    assert message in err


def test_bad_attrs_format_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["run", "new", "--seed", "1", "--build", "x", "--attrs", "strong"], capsys)
    assert code == 2
    assert "--attrs" in err


@pytest.mark.slow
def test_run_auto_is_deterministic_and_matches_the_library_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    build, seed = VICTORY
    argv = ["run", "auto", "--seed", str(seed), "--build", build]
    code, first, _ = _run(argv, capsys)
    assert code == 0
    _, second, _ = _run(argv, capsys)
    assert first == second
    assert "結果：勝利（6/6 場）" in first
    assert first.count("營火（第") == 2
    assert f"經驗 {full_run(*VICTORY).xp}" in first.splitlines()[-1]


def test_run_auto_from_a_mid_battle_save_finishes_the_same(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lib = library()
    run, battle = auto_play(
        lib,
        new_run(lib, *VICTORY),
        stop=lambda r, b: b is not None and b.index == 2 and len(b.steps) >= 10,
    )
    assert battle is not None
    path = write_save(tmp_path, RunSave(run_id="mid", run=run, battle=battle.to_saved()))
    code, out, _ = _run(
        ["run", "auto", "--from", str(path), "--save", "--save-dir", str(tmp_path)], capsys
    )
    assert code == 0
    assert "從存檔接續" in out
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["battle"] is None
    assert saved["run"] == json.loads(full_run(*VICTORY).model_dump_json())


def test_run_auto_needs_exactly_one_of_seed_and_from(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["run", "auto"], capsys)
    assert code == 2
    assert "--seed 或 --from" in err


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(10))  # 每個種子一個測試，平行時分散到各 worker
def test_run_auto_ten_seeds_without_exceptions(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0, err
    assert out.splitlines()[-1].startswith("結果：")


# ---------------------------------------------------------------------------
# Phase 3-24b2：新開局（武器 ＋ 關鍵字）、開發者起始包、沒有指定時以種子抽
# ---------------------------------------------------------------------------


def test_run_new_with_weapon_and_keywords(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "4", "--weapon", "bow", "--keywords", "marked,ignite"]
    code, out, _ = _run([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    assert "弓（bow）＋標記、點燃" in out
    raw = json.loads(next(tmp_path.glob("run-*.json")).read_text(encoding="utf-8"))
    start = raw["run"]["start"]
    assert start == {"weapon": "bow", "keywords": ["marked", "ignite"], "dev_pack": None}


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--weapon", "bow", "--keywords", "marked"], "2 個不同的關鍵字"),
        (["--dev-pack", "dev_nobody"], "未知的開發者起始包"),
        (["--dev-pack", "dev_blaze", "--build", "build_push"], "只能擇一"),
    ],
)
def test_run_new_rejects_bad_starts(
    argv: list[str], message: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run(["run", "new", "--seed", "1", *argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 2
    assert message in err


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.slow
def test_run_auto_without_a_start_draws_weapon_and_keywords(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """驗收：``trpg run auto`` 3 個種子能跑完（沒有指定開局時以種子抽武器與 2 個關鍵字）。"""
    code, out, _ = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0
    first = out.splitlines()[0]
    assert first.startswith(f"一輪：種子 {seed}，") and "＋" in first
    assert out.splitlines()[-1].startswith("結果：")


@pytest.mark.parametrize("seed", [1, 2])
@pytest.mark.slow
def test_run_auto_spends_skill_points_and_shows_levels(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """Phase 3-26a：``trpg run auto`` 升級時花技能點，進度與存檔列出技能等級。"""
    code, out, _ = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0
    assert "技能點升級：" in out and " Lv." in out
    assert out.splitlines()[-1].startswith("結果：")


@pytest.mark.parametrize(
    "seed", [3, 5]
)  # 3-33e1／e2a／e2b：種子 1、4 的一輪不再進化；3I-1、3I-3 改用 4、5；3J-4b 開局池改變，4 改為 3
@pytest.mark.slow
def test_run_auto_reaches_a_branching_evolution(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """Phase 3-26b：``trpg run auto`` 跑到至少一次分歧進化，進度印出進化前後的技能。"""
    code, out, _ = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0
    lines = [line for line in out.splitlines() if "分歧進化：" in line]
    # 3-51：新方向可能抽到基礎技能，第一次進化不一定是加深：任何一行是加深即可
    assert (
        lines
        and all("_evo_" in line for line in lines)
        and any("（加深）" in line for line in lines)
    )


def test_run_auto_with_a_dev_pack(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["run", "auto", "--seed", "1", "--dev-pack", "dev_tidestorm"], capsys)
    assert code == 0
    assert "〔起始包 dev_tidestorm〕" in out and "潮雷" not in out
