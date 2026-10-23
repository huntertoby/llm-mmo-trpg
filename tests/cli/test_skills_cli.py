"""技能的 CLI：戰鬥紀錄、回合標頭、``trpg skills list/show``、重播（2A-1 驗收條件 9）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_oil_depot_battle_uses_at_least_three_different_skills_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "oil_depot.json"
    code, out, _ = _run(
        ["battle", "--map", "oil_depot", "--seed", "42", "--log-json", str(log)], capsys
    )
    assert code == 0 and "勝方：" in out
    used = set(re.findall(r"施放「(.+?)」", out))
    assert len(used) >= 3, used
    assert re.search(r"施放「.+?」（AP \d(，法力 \d+)?(，冷卻 \d 回合)?）→ 影響 \d+ 格", out)
    assert re.search(r"（AP 3，移動 \d+，法力 \d+/\d+）", out)  # 回合標頭顯示法力
    assert re.search(r"以「.+?」攻擊 .+?：d20=", out)  # 命中擲骰看得出技能
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["format"] == "trpg-battle-log/62"
    assert any(a.get("type") == "use_skill" for a in data["actions"])
    assert any(e["type"] == "skill_used" for e in data["events"])
    code, replayed, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replayed


def test_skills_list_is_a_table_of_every_skill(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["skills", "list"], capsys)
    assert code == 0
    lines = out.splitlines()
    total = len(library().skills)
    assert f"技能（共 {total} 個）" in lines[0]
    header = lines[1].split()
    assert header[:4] == ["ID", "名稱", "骨架", "AP"]
    assert sum(1 for line in lines if re.match(r"\s+skill_\w+\s", line)) == total
    assert "灰燼誓約" in out and "法力 12，冷卻 2 回合" in out


def test_skills_show_prints_the_full_content_and_an_effect_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _ = _run(["skills", "show", "skill_ashen_oath"], capsys)
    assert code == 0
    assert out.splitlines()[0] == "灰燼誓約（skill_ashen_oath）"
    assert "骨架 area" in out and "縮放屬性 智力" in out
    assert "形狀 錐形（大小 3）" in out
    assert "2d6＋智力加成的火焰傷害（敵方）" in out
    assert "生成「火焰」表面 2 回合（影響的格子）" in out
    assert "代價 AP 2，法力 12，冷卻 2 回合" in out


def test_skills_show_unknown_id(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["skills", "show", "skill_nope"], capsys)
    assert code == 1 and "找不到技能" in err


def test_content_check_includes_skill_files(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["content", "check"], capsys)
    assert code == 0
    assert "skill_shapes.yaml" in out and "skill_primitives.yaml" in out
    assert "skills/skill_ashen_oath.yaml" in out


def test_skills_random_prints_yaml_and_the_budget_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["skills", "random", "--seed", "5", "--tier", "3", "--skeleton", "area"])
    out = capsys.readouterr().out
    assert code == 0
    assert "id: skill_rand_5" in out and "tier: 3" in out and "skeleton: area" in out
    assert "效果點數" in out and "比例 ＝ total ÷ 可用預算" in out and "驗證：通過" in out


def test_skills_random_count_runs_consecutive_seeds_and_is_reproducible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["skills", "random", "--seed", "40", "--count", "3", "--rarity", "epic"]) == 0
    first = capsys.readouterr().out
    assert [f"# 種子 {n}" in first for n in (40, 41, 42)] == [True, True, True]
    assert first.count("驗證：通過") == 3 and "rarity: epic" in first
    assert main(["skills", "random", "--seed", "40", "--count", "3", "--rarity", "epic"]) == 0
    assert capsys.readouterr().out == first


def test_skills_random_reports_impossible_parameters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["skills", "random", "--seed", "1", "--skeleton", "displace", "--rarity", "common"])
    captured = capsys.readouterr()
    assert code == 1 and "錯誤" in captured.err and "displace" in captured.err
    assert main(["skills", "random", "--seed", "1", "--tier", "9"]) == 2


def test_skills_show_displays_dual_scaling_and_mastery(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 2H-2：雙屬性顯示各 50%；專精顯示加成內容，指定單位時標示是否生效。"""
    _, out, _ = _run(["skills", "show", "skill_arcane_blade"], capsys)
    assert "縮放屬性 力量 50%＋智力 50%" in out
    assert "4d8＋力量／智力加成的雷電傷害" in out
    _, out, _ = _run(["skills", "show", "skill_shatter_blast"], capsys)
    assert "專精加成 施放距離 +1（智力為最高屬性時生效）" in out
    _, out, _ = _run(["skills", "show", "skill_dread_gaze", "--unit", "build_warlock"], capsys)
    assert "專精加成 施加的狀態持續 +1 回合（意志為最高屬性，生效中）" in out
    _, out, _ = _run(["skills", "show", "skill_dread_gaze", "--unit", "build_healer"], capsys)
    assert "意志不是最高屬性，未生效" in out
