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
    assert raw["format"] == "trpg-run/13"
    assert raw["run"]["seed"] == 4
    code, shown, _ = _run(["run", "show", str(saves[0])], capsys)
    assert code == 0
    assert "trpg-run/13" in shown and "build_push" in shown and "目前：戰鬥" in shown


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


@pytest.mark.parametrize("seed", [3, 2])  # BAL-4b 數值改變後，原本的 1 換成 3
@pytest.mark.slow
def test_run_auto_flashes_and_shows_flash_counts(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """Phase 3W-5：``trpg run auto`` 每贏一場得到靈感點並閃現，進度列出閃現前後與已閃次數。"""
    code, out, _ = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0
    assert "閃現（第 1 次" in out and " 已閃 1 次" in out and "；靈感 " in out
    assert "技能點" not in out and " Lv." not in out
    assert out.splitlines()[-1].startswith("結果：")


# 3W-5：取代 3-26b 的分歧進化測試（3W-fix 的 xfail）。AI 把點數集中在閃過最多次的技能，第 3 次是
# 大變化；中段與 Boss 前各一次完整技能三選一；有還沒重閃過調整欄的完整技能時保留 1 點到營火重閃。
# 種子 1～8 中 3、6 會練到第 3 次大變化（其他種子的主角常在某場沒放出那招，不能連閃）。
@pytest.mark.parametrize("seed", [3, 13])  # BAL-4b：6 → 7；BAL-4c 合併後 7 → 13
@pytest.mark.slow
def test_run_auto_reaches_a_major_flash_a_complete_skill_and_a_reflash(
    seed: int, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = _run(["run", "auto", "--seed", str(seed)], capsys)
    assert code == 0
    lines = out.splitlines()
    major = [line for line in lines if "閃現（第 3 次" in line]
    assert major and all(
        "_fl_" in line and "・" in line for line in major
    )  # 大變化改名「前綴・原名」
    assert any("完整技能三選一：選 " in line and "〔完整技能〕" in line for line in lines)
    assert any(line.strip().startswith("重閃：") and "〔完整技能〕" in line for line in lines)


def test_run_auto_with_a_dev_pack(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["run", "auto", "--seed", "1", "--dev-pack", "dev_tidestorm"], capsys)
    assert code == 0
    assert "〔起始包 dev_tidestorm〕" in out and "潮雷" not in out


def test_run_auto_with_llm_mock_is_replayable(capsys: pytest.CaptureFixture[str]) -> None:
    """Phase 4-L6：--llm-mock 跑完整一輪，印出 LLM 提議摘要，同種子兩次輸出一致。"""
    argv = ["run", "auto", "--seed", "3", "--llm-mock"]
    code, first, _ = _run(argv, capsys)
    assert code == 0 and "LLM 提議：" in first and "退回" in first
    assert "LLM 閃現提議：" in first  # 3W-5：閃現出題接上 3W-7 的變化提議（Mock）
    code, second, _ = _run(argv, capsys)
    assert second == first
    code, plain, _ = _run(["run", "auto", "--seed", "3"], capsys)
    assert code == 0 and "LLM 提議" not in plain
