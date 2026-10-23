"""Phase 3-48f：賭注專用效果的玩家文字、擊殺時效果的有益狀態限制。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from tests.skillgen.test_workshop_48d import _nested, _options_of, _weapon_draft
from trpg.content.skills import SkillDef
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.validate import validate_skill

LIB = library()


def _harmful() -> str:
    return next(s.id for s in LIB.ruleset.statuses.statuses if not s.beneficial and s.budget_points)


def _on_kill_effects(status: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "damage",
            "multiplier_permille": 1500,
            "on_kill": [{"type": "apply_status", "status": status, "duration": 2}],
        }
    ]


def test_gamble_special_effects_use_player_units() -> None:
    win = _nested(_options_of("gamble")["gamble"], "win")
    by_value = {str(c.value): c for c in win.choices}
    mult = by_value["damage_multiplier"].params[0]
    assert (mult.name_zh, mult.display) == ("倍率", "multiplier")
    assert "×2＝加倍" in by_value["damage_multiplier"].description_zh
    back = by_value["self_damage_of_hit"].params[0]
    assert (back.name_zh, back.display) == ("反噬比例（%）", "percent")
    assert "HP 至少留 1" in by_value["self_damage_of_hit"].description_zh
    for choice in (by_value["damage_multiplier"], by_value["self_damage_of_hit"]):
        assert "‰" not in choice.description_zh
        assert all("‰" not in p.name_zh for p in choice.params)


def test_refund_ap_is_called_ap_everywhere() -> None:
    kill = _nested(_options_of("damage")["damage"], "on_kill")
    refund = next(c for c in kill.choices if c.value == "refund_ap")
    assert refund.name_zh == "返還 AP" and "行動點" not in refund.description_zh


def test_on_kill_rejects_harmful_status_with_reason() -> None:
    draft = _weapon_draft(_on_kill_effects(_harmful()))
    result = check_draft(draft, LIB)
    assert not result.legal
    assert any("擊殺時效果" in p.message_zh and "有益" in p.message_zh for p in result.problems)


def test_on_kill_beneficial_status_is_not_flagged() -> None:
    good = next(
        s.id
        for s in LIB.ruleset.statuses.statuses
        if s.beneficial and s.budget_points and not s.stance
    )
    result = check_draft(_weapon_draft(_on_kill_effects(good)), LIB)
    assert not any("擊殺時效果" in p.message_zh for p in result.problems)


def test_validator_rule_catches_yaml_and_proposals() -> None:
    base = LIB.skills["skill_ash_harvest"].model_dump(mode="json", exclude_none=True)
    effects = _on_kill_effects(_harmful())
    effects[0].pop("multiplier_permille")
    effects[0].update(dice="2d6", element="fire")
    skill = SkillDef.model_validate({**base, "effects": effects})
    assert "on_kill.beneficial" in {v.rule for v in validate_skill(skill, LIB)}


def test_no_builtin_skill_breaks_the_on_kill_rule() -> None:
    bad = [
        sid
        for sid, skill in LIB.skills.items()
        if any(v.rule == "on_kill.beneficial" for v in validate_skill(skill, LIB))
    ]
    assert bad == []
