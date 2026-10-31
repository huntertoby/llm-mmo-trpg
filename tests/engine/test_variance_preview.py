"""高變異、超載與縮放的預覽、AI 與文字（Phase 3D-7b，``docs/phases/Phase3D計畫.md`` 7.3）：
預覽的傷害範圍與暴擊率、爆骰的期望值、技能卡片與戰鬥紀錄的文字。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from tests.engine.test_variance import damage, script_randint, spell, surge_skill
from trpg.engine import UseSkill, preview, state_to_json
from trpg.engine.events import DamageDealt, OverloadTriggered
from trpg.engine.preview import DamageRange, TargetPreview
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary, scaling_text, skill_card


def preview_of(effects: list[dict[str, Any]], **fields: Any) -> TargetPreview:
    state = battle(spell(*effects, **fields), [(5, 3)])
    return preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets[0]


def range_of(effects: list[dict[str, Any]], **fields: Any) -> DamageRange:
    found = preview_of(effects, **fields).damage
    assert found is not None
    return found


# ---------------------------------------------------------------------------
# 預覽：傷害範圍與暴擊率
# ---------------------------------------------------------------------------


def test_an_exploding_die_widens_the_damage_range_and_raises_the_expectation() -> None:
    plain = range_of([damage("1d6")])
    boom = range_of([damage("1d6", explode=True)])
    assert boom.minimum == plain.minimum  # 沒有擲到最大值就不爆骰
    assert boom.maximum - plain.maximum >= 12  # 最大：6 + 6 + 6 = 18，比單顆最大值多 12 點
    assert boom.expected_if_hit > plain.expected_if_hit


def test_the_exploding_expectation_follows_the_exact_distribution() -> None:
    """預覽的期望值依爆骰分布精確計算：每點骰子傷害相同，所以「期望值差」除以骰子期望值差
    （301/72 − 7/2）就是每點骰子的傷害；它必須和不爆骰時推得的每點骰子傷害一致。"""
    plain = range_of([damage("1d6")])
    boom = range_of([damage("1d6", explode=True)])
    per_die = (boom.expected_if_hit - plain.expected_if_hit) / (Fraction(301, 72) - Fraction(7, 2))
    # 不爆骰：期望值 ＝ 7/2 × per_die ＋ 屬性加成，而屬性加成不為負
    assert per_die > 0 and plain.expected_if_hit >= Fraction(7, 2) * per_die


def test_a_wider_crit_range_raises_the_preview_crit_chance() -> None:
    plain = preview_of([damage()])
    wide = preview_of([damage()], crit_range=17)
    assert wide.crit_chance >= plain.crit_chance * 3  # 自然 17–20 暴擊對自然 20


def test_the_preview_damage_includes_the_discount_and_the_scaling() -> None:
    plain = range_of([damage("1d6")])
    cut = range_of([damage("1d6")], damage_permille=750)
    assert cut.maximum < plain.maximum
    scaling = {"by": "distance", "per_step_permille": 100, "cap_permille": 800}
    more = range_of([damage("1d6", scaling=scaling)])
    assert more.maximum > plain.maximum and more.expected_if_hit > plain.expected_if_hit


def test_the_preview_does_not_change_the_state() -> None:
    state = battle(spell(damage(explode=True), crit_range=17), [(5, 3)])
    before = state_to_json(state)
    preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert state_to_json(state) == before


def test_the_demo_wild_blade_preview_has_a_higher_crit_chance_than_a_plain_weapon_skill() -> None:
    wild = library().skills["skill_wild_blade"].model_copy(update={"id": SID})
    plain = wild.model_copy(update={"crit_range": None})
    assert wild.crit_range == 17 and plain.crit_range is None
    chances = []
    for skill in (wild, plain):
        state = battle(skill, [(4, 3)], base="hero_fighter")
        target = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets[0]
        chances.append(target.crit_chance)
    assert chances[0] > chances[1]


# ---------------------------------------------------------------------------
# 文字
# ---------------------------------------------------------------------------


def test_the_wild_blade_card_describes_explosion_crit_range_and_discount() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_wild_blade"])
    (text,) = card.effects
    skill = lib.skills["skill_wild_blade"]
    base, discount = skill.effects[0].multiplier_permille, skill.damage_permille
    assert base is not None and discount is not None
    multiplier = base * discount / 1_000_000
    assert f"武器傷害 ×{multiplier:g}" in text
    assert "爆骰" in text and "最多再擲 2 次" in text
    assert "暴擊範圍 17–20" in text
    assert "gamble" in card.tags


def test_the_scaling_cards() -> None:
    lib = library()
    rage = lib.skills["skill_berserker_rage"].effects[0]
    assert scaling_text(rage) == "你每少 10% 最大 HP，傷害 +8%（最多 +80%）"
    sniper = lib.skills["skill_sniper_shot"].effects[0]
    assert scaling_text(sniper) == "與目標每距 1 格，傷害 +8%（最多 +40%）"
    sweep = lib.skills["skill_encircled_sweep"].effects[0]
    assert scaling_text(sweep) == "你每有 1 名相鄰的敵人，傷害 +10%（最多 +30%）"
    assert scaling_text(lib.skills["skill_whirlwind"].effects[0]) is None
    assert "你每少 10% 最大 HP" in effect_summary(lib, lib.skills["skill_berserker_rage"], rage)


def test_the_overload_card_explains_the_bonus_and_the_backlash() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_overcurrent"])
    text = card.effects[1]
    assert "累積 1 層「過載電流」" in text
    assert "每層傷害 +20%" in text and "累積到 5 層時" in text and "2d6" in text
    assert "不致命" in text and "並清空層數" in text


def test_the_battle_log_describes_the_burst_and_the_overload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(damage(explode=True)), [(5, 3)])
    charged = battle(surge_skill(), [(5, 3)])
    charged.units[U1].stacks["overload_surge"] = 4
    script_randint(monkeypatch, [19, 6, 6, 3, 19, 4, 3, 5])
    result = cast(state, target_id=U2)
    (hit,) = of(result, DamageDealt)
    text = describe_event(hit, result.state) or ""
    assert "［骰 6+6+3 ＋ 智力加成" in text and "爆骰 ×2" in text

    over = cast(charged, target_id=U2)
    (triggered,) = of(over, OverloadTriggered)
    assert "超載了" in (describe_event(triggered, over.state) or "")
    lines = [describe_event(e, over.state) or "" for e in over.events]
    assert any("超載清空：5 → 0 層" in line for line in lines)
    assert any("反噬雷電傷害" in line for line in lines)
