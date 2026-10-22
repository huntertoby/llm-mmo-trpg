"""``trpg skills budget`` 與 ``trpg content check`` 的預算驗證（Phase 2B-2 4.7；驗收 1、6）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tests.engine.helpers import PROJECT_ROOT
from trpg.cli.main import main
from trpg.content.loader import CONTENT_DIR_ENV


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_budget_for_one_skill_prints_the_breakdown(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["skills", "budget", "skill_ashen_oath"], capsys)
    assert code == 0
    assert "灰燼誓約（skill_ashen_oath）  階級 T2" in out
    assert "damage" in out and "形狀 ×1.6" in out  # 錐形 3
    assert "create_surface" in out and "fire 3×1" in out
    assert "raw ＝ 16.00" in out and "total ＝ raw × 條件 × 協同 ＝ 16.00" in out
    assert "tier_budget 18 × AP 係數 1.00 × (1000 + 折抵 160‰) ÷ 1000 ＝ 20.88" in out
    assert "冷卻 2 回合 +100‰、法力 12 +60‰" in out
    assert "比例 ＝ total ÷ 可用預算 ＝ 76.6%" in out and "→ 合格" in out
    assert "驗證：通過" in out


def test_budget_shows_conditions_and_synergies(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["skills", "budget", "skill_cinder_burst"], capsys)
    assert code == 0 and "條件 ×0.85" in out
    code, out, _ = _run(["skills", "budget", "skill_execute"], capsys)
    assert code == 0 and "技能條件倍率 ×0.85" in out


def test_budget_all_lists_every_skill(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["skills", "budget", "--all"], capsys)
    assert code == 0
    assert "技能預算總表（共 178 個" in out and "通過 178 個，違規 0 個。" in out
    for skill_id in sorted(p.stem for p in (PROJECT_ROOT / "content/skills").glob("*.yaml")):
        assert skill_id in out


def test_budget_needs_an_id_or_all(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["skills", "budget"], capsys)
    assert code == 2 and "--all" in err
    code, _, err = _run(["skills", "budget", "skill_nope"], capsys)
    assert code == 1 and "找不到技能" in err


def test_content_check_passes_with_the_shipped_skills(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["content", "check"], capsys)
    assert code == 0 and "178 個技能通過預算與結構驗證" in out


def test_content_check_fails_on_a_skill_that_breaks_the_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    path = root / "skills" / "skill_cleave.yaml"
    data = yaml.safe_load(path.read_text("utf-8"))
    data["effects"][0]["multiplier_permille"] = 4000  # 超預算
    data["cost"] = {"mana": 4}  # 錐形 2 沒有冷卻仍可，但再加一個互斥違規：
    data["shape"] = {"type": "cone", "size": 4}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv(CONTENT_DIR_ENV, str(root))
    code, _, err = _run(["content", "check"], capsys)
    assert code == 1
    assert "技能違規" in err and "skill_cleave" in err
    assert "exclusion.no_cooldown_big_area" in err and "budget.over" in err and "%" in err


def test_budget_shows_when_the_allowance_is_capped(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """折抵加總超過 total_cap 時，單一技能與總表都要顯示截斷（Phase 2C-1 3.1）。"""
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    path = content / "skills" / "skill_bone_crusher.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["cost"] = {"mana": 40, "cooldown": 6, "uses_per_battle": 1}  # 150 + 300 + 400 ＝ 850
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv(CONTENT_DIR_ENV, str(content))
    _, out, _ = _run(["skills", "budget", "skill_bone_crusher"], capsys)
    assert "代價折抵 +850‰ → 上限 +500‰" in out
    assert "折抵 500‰" in out
    _, out, _ = _run(["skills", "budget", "--all"], capsys)
    assert "+850→500" in out
