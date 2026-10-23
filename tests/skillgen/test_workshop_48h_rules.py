"""Phase 3-48h：違規的選項事前停用（驗證器與選項同源）、對象預設值、陷阱說明、變奏代號。

重點是「行為一致」：隨機草稿 × 每個對象／狀態選項，「選項顯示可用」⇔「選了之後完整驗證器
（`validate_skill`）不報這類規則」。
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.skillgen.draft import DraftError, build_skill
from trpg.skillgen.option_fill import variants
from trpg.skillgen.option_effect_rules import PAIR_RULES, sensible_affects
from trpg.skillgen.option_models import Choice
from trpg.skillgen.option_player import fill_placeholders
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import EFFECT_PARAM_RULES, validate_skill

LIB = library()
AURA_SELF: dict[str, Any] = {
    "skeleton": "aura",
    "kind": "active",
    "category": "spell",
    "weapon_req": "any",
    "scaling_attr": "wis",
    "tier": 1,
    "ap_cost": 2,
    "shape": {"type": "self"},
}


def _effects_choices(options: Any) -> tuple[Choice, ...]:
    step = next(s for s in options.steps if s.id == "effects")
    return next(f for f in step.fields if f.field == "effects").choices


def _choice(options: Any, primitive: str) -> Choice:
    return next(c for c in _effects_choices(options) if c.value == primitive)


def _param(choice: Choice, name: str) -> dict[str, Choice]:
    spec = next(p for p in choice.params if p.field == name)
    return {str(c.value): c for c in spec.choices}


def _reason(choice: Choice) -> str | None:
    value = choice.info.get("unavailable_zh")
    return value if isinstance(value, str) else None


# ---------------------------------------------------------------------------
# 使用者的案例：自身形狀 ＋ 光環骨架 ＋ 暈眩／免死
# ---------------------------------------------------------------------------


def test_self_aura_blocks_enemy_targets_and_hard_control_with_plain_reasons() -> None:
    options = draft_options(AURA_SELF, LIB)
    statuses = _param(_choice(options, "apply_status"), "status")
    stun = _reason(statuses["stun"])
    assert stun is not None and "單體" in stun and "形狀" in stun  # 說明怎麼改
    assert _reason(statuses["rallied"]) is None
    assert _reason(statuses["burning"]) is not None  # 光環的核心效果只能是有益狀態
    heal = _param(_choice(options, "heal"), "affects")
    assert _reason(heal["allies"]) is None
    damage = _choice(options, "damage")
    assert _reason(damage) is not None  # 自身形狀的光環沒有任何合理的對象可以打


def test_stun_needs_cooldown_four_and_the_hint_says_where_to_fix_it() -> None:
    draft = {**AURA_SELF, "skeleton": "control", "shape": {"type": "single", "range": 3}}
    draft["cost"] = {"mana": 3, "cooldown": 1}
    options = draft_options(draft, LIB)
    stun = _reason(_param(_choice(options, "apply_status"), "status")["stun"])
    assert stun is not None and "冷卻" in stun and "4" in stun and "代價" in stun
    draft["cost"] = {"mana": 3, "cooldown": 4}
    again = _param(_choice(draft_options(draft, LIB), "apply_status"), "status")["stun"]
    assert _reason(again) is None


def test_cost_step_marks_the_cooldown_floor_when_a_hard_control_is_chosen() -> None:
    draft = {
        **AURA_SELF,
        "skeleton": "control",
        "shape": {"type": "single", "range": 3},
        "effects": [{"type": "apply_status", "status": "stun", "affects": "enemies"}],
        "condition": None,
    }
    draft.pop("condition")
    options = draft_options(draft, LIB)
    cost = next((s for s in options.steps if s.id == "cost"), None)
    assert cost is not None
    cooldown = next(f for f in cost.fields if f.field == "cost.cooldown")
    assert cooldown.min == 4 and "4" in cooldown.description_zh


# ---------------------------------------------------------------------------
# 1a：對象預設值與自動修正建議
# ---------------------------------------------------------------------------


def test_buff_status_defaults_to_self_or_allies_and_harmful_to_enemies() -> None:
    draft = {**AURA_SELF, "effects": [{"type": "apply_status", "status": "rallied"}]}
    fixes = draft_options(draft, LIB).effect_fixes
    assert [(f.index, f.value) for f in fixes] == [(0, "self")]  # 自身形狀 → 自己
    ranged = {**draft, "shape": {"type": "allies_in_radius", "radius": 2}}
    assert [(f.index, f.value) for f in draft_options(ranged, LIB).effect_fixes] == [(0, "allies")]
    harmful = {
        **AURA_SELF,
        "skeleton": "control",
        "shape": {"type": "single", "range": 3},
        "cost": {"mana": 3, "cooldown": 4},
        "effects": [{"type": "apply_status", "status": "slow"}],
    }
    assert draft_options(harmful, LIB).effect_fixes == ()  # 預設的敵方本來就合法


def test_shape_change_makes_a_chosen_target_illegal_and_a_fix_is_suggested() -> None:
    draft = {
        **AURA_SELF,
        "skeleton": "area",
        "shape": {"type": "self"},
        "effects": [{"type": "damage", "dice": "1d6", "element": "fire", "affects": "enemies"}],
    }
    fixes = draft_options(draft, LIB).effect_fixes
    assert len(fixes) == 1 and fixes[0].index == 0
    assert fixes[0].value is None  # 傷害沒有合理的合法對象：不亂改，由檢查說明
    assert fixes[0].reason_zh != ""


def test_a_legal_choice_is_never_overridden() -> None:
    draft = {**AURA_SELF, "effects": [{"type": "apply_status", "status": "rallied", "affects": "self"}]}
    assert draft_options(draft, LIB).effect_fixes == ()


# ---------------------------------------------------------------------------
# 行為一致：隨機草稿 × 每個選項
# ---------------------------------------------------------------------------

_SINGLE_RULES = frozenset(EFFECT_PARAM_RULES) - PAIR_RULES
_ASSUMED_STRIP = ("id", "name_zh", "provenance", "narrative", "schema_version", "variants")


def _draft_from(seed: int) -> dict[str, Any] | None:
    skill = compose_random_skill(seed, library=LIB)
    data = json.loads(skill.model_dump_json(exclude_none=True))
    for key in _ASSUMED_STRIP:
        data.pop(key, None)
    if data.get("kind") == "modifier" or data.get("followup") is not None:
        return None
    effects = data.get("effects", [])[: seed % 3]
    data["effects"] = effects
    if not effects:
        data.pop("effects")
    data.pop("trap", None)
    data.pop("condition", None)
    cost = dict(data.get("cost") or {})
    cost["cooldown"] = (seed * 7) % 6 + 1  # 代價已填：冷卻是明確的值
    data["cost"] = cost
    data["rarity"] = "epic"
    return data


def _full_rules(draft: dict[str, Any], effects: list[dict[str, Any]]) -> list[str] | None:
    try:
        skill = build_skill(draft, {"effects": effects})
    except DraftError:
        return None
    violations = validate_skill(skill, LIB)
    if any(v.rule == "reference" for v in violations):
        return None
    return [v.rule for v in violations if v.rule in EFFECT_PARAM_RULES]


def _oracle_blocked(
    draft: dict[str, Any], context: list[dict[str, Any]], candidate: dict[str, Any]
) -> bool | None:
    alone = _full_rules(draft, [candidate])
    after = _full_rules(draft, [*context, candidate])
    before = _full_rules(draft, context) if context else []
    if alone is None or after is None or before is None:
        return None
    if any(rule in _SINGLE_RULES for rule in alone):
        return True
    gained = Counter(r for r in after if r in PAIR_RULES) - Counter(r for r in before if r in PAIR_RULES)
    return bool(gained)


def _compare(seed: int) -> Counter[bool] | None:
    """一個隨機草稿的每個對象／狀態選項：選項停用與完整驗證器的判斷必須一致；回傳
    ``{停用: 次數, 可用: 次數}``（草稿不適用時為 ``None``）。"""
    draft = _draft_from(seed)
    if draft is None:
        return None
    options = draft_options(draft, LIB)
    if not any(s.id == "effects" for s in options.steps):
        return None
    context = [dict(e) for e in draft.get("effects", [])]
    checked: Counter[bool] = Counter()
    for choice in _effects_choices(options):
        fills = variants(choice)
        if not fills:
            continue
        base = fills[0]
        names = [p.field for p in choice.params if p.field in ("affects", "status") and p.type == "choice"]
        for name in names:
            for value, item in _param(choice, name).items():
                candidate = {**base, name: value}
                if name == "status":
                    affects = _param(choice, "affects") if "affects" in names else {}
                    legal = {v for v, c in affects.items() if _reason(c) is None}
                    status_good = bool(item.info.get("beneficial"))
                    prog = next(
                        (
                            side
                            for side in sensible_affects(
                                LIB.ruleset.primitives.by_id()[str(choice.value)],
                                str(draft["shape"]["type"]),
                                beneficial=status_good,
                            )
                            if side in legal
                        ),
                        None,
                    )
                    if prog is not None:
                        candidate["affects"] = prog
                expected = _oracle_blocked(draft, context, candidate)
                if expected is None:
                    continue
                shown_blocked = _reason(item) is not None
                assert shown_blocked == expected, (
                    f"seed {seed} {choice.value}.{name}={value}：選項停用={shown_blocked}，"
                    f"驗證器擋={expected}"
                )
                checked[shown_blocked] += 1
    return checked


@pytest.mark.parametrize("seed", range(14))
def test_option_availability_matches_the_full_validator(seed: int) -> None:
    if _compare(seed) is None:
        pytest.skip("修正、複合技能，或前面的步驟沒完成")


def test_the_comparison_sees_both_blocked_and_available_options() -> None:
    total: Counter[bool] = Counter()
    for seed in range(6):
        total += _compare(seed) or Counter()
    assert total[True] > 10 and total[False] > 50, total


# ---------------------------------------------------------------------------
# 5b 陷阱、5d 變奏代號與說明句
# ---------------------------------------------------------------------------

TRAP: dict[str, Any] = {
    "skeleton": "trap",
    "kind": "active",
    "category": "spell",
    "weapon_req": "any",
    "scaling_attr": "dex",
    "tier": 1,
    "ap_cost": 2,
    "shape": {"type": "ground_tile", "range": 4},
    "effects": [{"type": "place_trap"}],
    "trap": {"trigger": "enter", "rounds": 3, "shape": "single"},
}


def _trap_field(options: Any) -> Any:
    step = next(s for s in options.steps if s.id == "effects")
    return next(f for f in step.fields if f.field == "trap")


def test_trap_settings_explain_what_resolves_when_stepped_on() -> None:
    empty = _trap_field(draft_options(TRAP, LIB)).description_zh
    assert "請新增一個效果" in empty and "踩到後" in empty
    with_damage = {**TRAP, "effects": [{"type": "place_trap"}, {"type": "damage", "dice": "1d6", "element": "fire"}]}
    text = _trap_field(draft_options(with_damage, LIB)).description_zh
    assert "踩到後會結算" in text and "傷害" in text


def test_trap_target_is_a_tile_not_self() -> None:
    options = draft_options(TRAP, LIB)
    affects = _param(_choice(options, "place_trap"), "affects")
    assert [c.name_zh for c in affects.values()] == ["格子"]


def test_validator_asks_for_an_effect_after_stepping_on_the_trap() -> None:
    skill = build_skill(TRAP, {"rarity": "rare", "cost": {"mana": 4, "cooldown": 2}})
    rules = [v.rule for v in validate_skill(skill, LIB)]
    assert "trap.effects" in rules
    for builtin in ("skill_bear_trap", "skill_cinder_mine"):
        assert "trap.effects" not in [v.rule for v in validate_skill(LIB.skills[builtin], LIB)]


def test_trap_card_sentence_names_the_effect_that_resolves() -> None:
    from trpg.narrative.skills import skill_card  # noqa: PLC0415

    card = skill_card(LIB, LIB.skills["skill_bear_trap"])
    line = next(e for e in card.effects if "陷阱" in e)
    assert "敵人踩到時" in line and "傷害" in line and "定身" in line


def test_variant_codename_is_auto_generated_and_hidden_in_player_mode() -> None:
    draft = {
        **AURA_SELF,
        "skeleton": "strike",
        "kind": "active",
        "category": "weapon",
        "weapon_req": "melee",
        "scaling_attr": "str",
        "shape": {"type": "single", "range": 1},
        "effects": [{"type": "damage", "dice": "1d8", "affects": "enemies"}],
        "cost": {"stamina": 2, "cooldown": 1},
        "rarity": "epic",
    }
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "variants")
    variants_field = next(f for f in step.fields if f.field == "variants")
    code = next(f for f in variants_field.fields if f.field == "id")
    assert code.auto_generated and code.required
    assert not next(f for f in variants_field.fields if f.field == "name_zh").auto_generated


def test_placeholders_follow_the_core_rules() -> None:
    core = LIB.ruleset.core
    text = fill_placeholders("最多 {rune_max_rounds}（{summon_traits}）", LIB)
    assert str(core.rune_max_rounds) in text
    assert all(t.name_zh in text for t in core.summon_traits.values())
    assert "{" not in text


def test_player_text_has_the_rewritten_sentences() -> None:
    texts = {e.id: e.player for e in LIB.workshop_text.texts}
    assert "替隊友擋下" in texts["原語.intercept"] and "替身" not in texts["原語.intercept"]
    gamble = texts["原語.gamble"]
    assert "乘上倍率" in gamble and "加倍" not in gamble and "硬控（暈眩、冰凍）" in gamble
    assert "有益狀態" in texts["原語.damage.on_kill"]
    assert "{rune_max_rounds}" in texts["原語.inscribe"]
    assert LIB.ruleset.primitives.by_id()["grant_ap"].name_zh == "給予 AP"
    assert LIB.ruleset.statuses.by_id()["undying"].name_zh == "免死"
