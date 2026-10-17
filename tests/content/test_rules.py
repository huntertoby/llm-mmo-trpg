"""命中修正對照表與核心規則資料的測試。"""

from __future__ import annotations

import importlib.util
import sys
from fractions import Fraction
from pathlib import Path
from types import ModuleType

import pytest

from trpg.content.loader import load_content_file
from trpg.content.rules import HIT_TABLE_SCALE, CoreRules, HitTable, compute_hit_thresholds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = PROJECT_ROOT / "content" / "rules"


def _load_script() -> ModuleType:
    path = PROJECT_ROOT / "scripts" / "gen_hit_table.py"
    spec = importlib.util.spec_from_file_location("gen_hit_table", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gen_hit_table", module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def core() -> CoreRules:
    return load_content_file(RULES_DIR / "core.yaml", CoreRules)


@pytest.fixture(scope="module")
def table() -> HitTable:
    return load_content_file(RULES_DIR / "hit_table.yaml", HitTable)


def exact_modifier(ratio: Fraction, slope: int, cap: int) -> int:
    """以 Fraction 精確計算 clamp(round(slope × log2(ratio)), ±cap)。

    ``round(slope·log2 r) ≥ k`` ⇔ ``slope·log2 r ≥ k − ½`` ⇔ ``r^(2·slope) ≥ 2^(2k − 1)``。
    （r 為有理數時 ``slope·log2 r`` 不會恰為半整數，因此沒有平手問題。）
    """
    power = ratio ** (2 * slope)
    best = -cap
    for k in range(-cap + 1, cap + 1):
        if power >= Fraction(2) ** (2 * k - 1):
            best = k
    return best


def test_core_rules_defaults(core: CoreRules) -> None:
    # docs/phases/Phase1計畫.md 3.5 的預設值
    assert core.ap_per_turn == 3
    assert core.ap_carry_max == 1
    assert core.hit_target == 11
    assert core.hit_slope == 4
    assert core.hit_mod_cap == 8
    assert core.proficiency == 2
    assert core.height_hit_bonus == 2
    assert core.basic_attack_attr_multiplier_permille == 300
    assert core.fall_damage_permille_per_level == 100
    assert core.fall_damage_cap_permille == 300
    assert core.deadly_terrain_elite_permille == 300
    assert core.element_mod_floor_permille == 250
    assert core.defend_defense_bonus_permille == 250
    assert core.move_climb_extra_cost == 1
    assert core.max_chain_depth == 3


def test_hit_table_matches_core(core: CoreRules, table: HitTable) -> None:
    assert (table.slope, table.cap, table.scale) == (core.hit_slope, core.hit_mod_cap, 1_000_000)


def test_hit_table_matches_high_precision_recomputation(table: HitTable) -> None:
    assert table.thresholds == compute_hit_thresholds(table.slope, table.cap, table.scale)


@pytest.mark.parametrize(("slope", "cap"), [(4, 8), (3, 6), (5, 10), (1, 3)])
def test_thresholds_are_exact_ceilings(slope: int, cap: int) -> None:
    """每個整數門檻 T 都滿足 (T−1)/S < 2^((2k−1)/(2·slope)) ≤ T/S（以 Fraction 精確驗證）。"""
    scale = HIT_TABLE_SCALE
    for t in compute_hit_thresholds(slope, cap, scale):
        target = Fraction(2) ** (2 * t.mod - 1)
        upper = Fraction(t.min_ratio_scaled, scale) ** (2 * slope)
        lower = Fraction(t.min_ratio_scaled - 1, scale) ** (2 * slope)
        assert lower < target <= upper, t


def test_generated_file_is_up_to_date(table: HitTable) -> None:
    script = _load_script()
    expected = script.render_hit_table(table.slope, table.cap)
    assert (RULES_DIR / "hit_table.yaml").read_text(encoding="utf-8") == expected


def test_gen_script_check_mode(capsys: pytest.CaptureFixture[str]) -> None:
    script = _load_script()
    assert script.main(["--check"]) == 0
    assert "最新" in capsys.readouterr().out


def test_gen_script_writes_new_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = _load_script()
    (tmp_path / "rules").mkdir()
    core_text = (RULES_DIR / "core.yaml").read_text(encoding="utf-8")
    (tmp_path / "rules" / "core.yaml").write_text(
        core_text.replace("hit_slope: 4", "hit_slope: 3"), encoding="utf-8"
    )
    assert script.main(["--content-dir", str(tmp_path), "--check"]) == 1
    assert script.main(["--content-dir", str(tmp_path)]) == 0
    capsys.readouterr()
    new_table = load_content_file(tmp_path / "rules" / "hit_table.yaml", HitTable)
    assert new_table.slope == 3
    assert new_table.thresholds == compute_hit_thresholds(3, 8)


def test_modifier_matches_exact_formula_on_grid(table: HitTable) -> None:
    for attack in range(1, 61):
        for defense in range(1, 61):
            expected = exact_modifier(Fraction(attack, defense), table.slope, table.cap)
            assert table.modifier(attack, defense) == expected, (attack, defense)


@pytest.mark.parametrize(
    ("attack", "defense", "expected"),
    [
        (10, 10, 0),
        (20, 10, 4),
        (40, 10, 8),
        (100, 1, 8),
        (5, 10, -4),
        (25, 100, -8),
        (1, 100, -8),
        (0, 10, -8),
        (-3, 10, -8),
    ],
)
def test_modifier_plan_table(table: HitTable, attack: int, defense: int, expected: int) -> None:
    # docs/專案計畫.md 5.4 的命中率表
    assert table.modifier(attack, defense) == expected


def test_modifier_with_fractional_defense(table: HitTable) -> None:
    # 防禦值 16 × 1.25 = 20：攻擊 20 vs 防禦 20 → 0
    assert table.modifier(20 * 1000, 16 * 1250) == 0
    assert table.modifier(20, 16) == exact_modifier(Fraction(20, 16), 4, 8)


def test_modifier_rejects_zero_defense(table: HitTable) -> None:
    with pytest.raises(ValueError):
        table.modifier(10, 0)


def test_hit_table_shape_validation() -> None:
    good = compute_hit_thresholds(4, 8)
    with pytest.raises(ValueError, match="mod"):
        HitTable(slope=4, cap=8, scale=HIT_TABLE_SCALE, thresholds=good[1:])
    shuffled = (good[0].model_copy(update={"min_ratio_scaled": 10**9}), *good[1:])
    with pytest.raises(ValueError, match="遞增"):
        HitTable(slope=4, cap=8, scale=HIT_TABLE_SCALE, thresholds=shuffled)


def test_compute_rejects_bad_parameters() -> None:
    with pytest.raises(ValueError):
        compute_hit_thresholds(0, 8)
