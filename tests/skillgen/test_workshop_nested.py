"""工坊開放一層巢狀效果（Phase 3-48d，規格第 54 節）。

四種有子效果的原語（消耗狀態的 then、賭注的 win／lose、持續區域的 effects、傷害的 on_kill）：
選項只在巢狀那一層出現、子效果不再巢狀、工坊產生的 YAML 通過驗證器、預算算得出來，
載入後實戰中子效果真的會觸發。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, no_reactions
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from tests.skillgen.workshop_walks import STRIKE, walk_draft
from trpg.content.skills import SkillDef
from trpg.engine.events import ApRefunded, DamageDealt, GambleRolled, Healed, ZoneTriggered
from trpg.engine.state import StatusInstance
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_fill import fill_fields
from trpg.skillgen.option_models import Choice, FieldSpec
from trpg.skillgen.option_nested import NESTED_PARAMS
from trpg.skillgen.options import draft_options
from trpg.skillgen.skill_yaml import skill_from_yaml, skill_to_yaml
from trpg.skillgen.validate import validate_skill

LIB = library()
KEYS = (
    "skeleton",
    "kind",
    "category",
    "weapon_req",
    "scaling_attr",
    "tier",
    "ap_cost",
    "name_zh",
    "shape",
    "effects",
    "condition",
    "cost",
    "rarity",
)

# 每種巢狀原語的「工坊草稿」範本（取自內建示範技能的欄位，效果由測試自己填）
TEMPLATES = {
    "consume_status": "skill_detonate_burning",
    "zone": "skill_fire_wall",
    "gamble": "skill_blood_sacrifice",
    "damage": "skill_ash_harvest",
}


def _draft(template: str, effects: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    skill = LIB.skills[template].model_dump(mode="json", exclude_none=True)
    draft: dict[str, Any] = {k: skill[k] for k in KEYS if k in skill}
    draft["effects"] = effects
    draft.update(over)
    return draft


def _weapon_draft(effects: list[dict[str, Any]]) -> dict[str, Any]:
    draft: dict[str, Any] = walk_draft(STRIKE)
    draft["effects"] = effects
    return draft


def _effects_step_choices(draft: dict[str, Any]) -> dict[str, Choice]:
    step = next(s for s in draft_options(draft, LIB).steps if s.id == "effects")
    return {str(c.value): c for c in step.fields[0].choices}


def _nested(choice: Choice, name: str) -> FieldSpec:
    return next(p for p in choice.params if p.field == name)


def _built(draft: dict[str, Any]) -> SkillDef:
    """工坊的流程：檢查 → 匯出 YAML → 驗證器 → 換成測試用 ID。"""
    result = check_draft(draft, LIB)
    assert result.legal, [p.message_zh for p in result.problems]
    assert result.budget is not None and result.budget.total > 0
    assert result.skill is not None
    skill = skill_from_yaml(skill_to_yaml(SkillDef.model_validate(result.skill)))
    assert validate_skill(skill, LIB) == []
    return skill.model_copy(update={"id": SID})


# ---------------------------------------------------------------------------
# 選項
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("owner", "field"), sorted(NESTED_PARAMS))
def test_nested_levels_offer_choices_and_only_one_level(owner: str, field: str) -> None:
    template = TEMPLATES[owner]
    choices = _effects_step_choices(_draft(template, LIB.skills[template].model_dump()["effects"]))
    spec = _nested(choices[owner], field)
    assert spec.type == "effects" and spec.choices and spec.max_count == 2
    assert not spec.later and not choices[owner].later
    for sub in spec.choices:  # 子效果不再巢狀
        assert all(p.type != "effects" for p in sub.params), sub.value
        assert not any(p.later for p in sub.params)


def _options_of(owner: str) -> dict[str, Choice]:
    template = TEMPLATES[owner]
    return _effects_step_choices(_draft(template, LIB.skills[template].model_dump()["effects"]))


def test_nested_choice_types_match_the_rules() -> None:
    then = _nested(_options_of("consume_status")["consume_status"], "then")
    assert [c.value for c in then.choices] == ["damage", "heal", "shield", "apply_status"]
    win = _nested(_options_of("gamble")["gamble"], "win")
    assert [c.value for c in win.choices][-2:] == ["damage_multiplier", "self_damage_of_hit"]
    kill = _nested(_options_of("damage")["damage"], "on_kill")
    assert [c.value for c in kill.choices][:2] == ["refund_ap", "refund_cooldown"]
    sub = {c.value: c for c in _nested(_options_of("zone")["zone"], "effects").choices}
    assert "affects" not in {p.field for p in sub["damage"].params}  # 對象由區域決定
    assert {"explode", "scaling", "on_kill"}.isdisjoint(p.field for p in sub["damage"].params)


def test_the_consume_status_skeleton_is_buildable_for_players() -> None:
    draft = _draft(
        TEMPLATES["consume_status"], LIB.skills[TEMPLATES["consume_status"]].model_dump()["effects"]
    )
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "effects")
    assert any("消耗狀態" in n for n in step.notes_zh)
    assert "consume_status" in _effects_step_choices(draft)


# ---------------------------------------------------------------------------
# 行為一致：工坊的草稿 → YAML → 驗證器 → 預算 → 實戰
# ---------------------------------------------------------------------------


def test_consume_status_then_fires_in_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.engine.test_passive_triggers import always  # noqa: PLC0415

    always(monkeypatch)
    effects = [
        {
            "type": "consume_status",
            "status": "burning",
            "scale": "remaining_rounds",
            "then": [{"type": "damage", "dice": "3d6", "element": "fire"}],
        }
    ]
    skill = _built(_draft(TEMPLATES["consume_status"], effects))
    state = battle(skill, [(5, 3)])
    state.units[U2].statuses = [StatusInstance("burning", 2, U1)]
    result = cast(state, target_id=U2)
    assert not result.state.units[U2].has_status("burning")
    assert [e.target_id for e in of(result, DamageDealt)] == [U2]


def test_zone_effects_fire_in_battle() -> None:
    effects = [
        {
            "type": "zone",
            "anchor": "moving",
            "speed": 1,
            "when": "both",
            "duration": 2,
            "affects": "enemies",
            "surface": "fire",
            "effects": [{"type": "damage", "dice": "1d6", "element": "fire"}],
        }
    ]
    skill = _built(_draft(TEMPLATES["zone"], effects))
    state = battle(skill, [(5, 3)], heights="\n".join(["0000000"] * 7))
    state = hit_with(state)
    result = cast(state, direction="east")
    assert [e.unit_id for e in of(result, ZoneTriggered)] == [U2]
    assert [e.target_id for e in of(result, DamageDealt)] == [U2]


def test_gamble_branches_fire_in_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.engine.test_gamble import script_randint  # noqa: PLC0415

    effects = [
        {"type": "damage", "multiplier_permille": 1200},
        {
            "type": "gamble",
            "chance_permille": 600,
            "win": [{"type": "damage_multiplier", "damage_multiplier_permille": 2000}],
            "lose": [{"type": "self_damage_of_hit", "self_damage_permille_of_hit": 300}],
        },
    ]
    skill = _built(_draft(TEMPLATES["gamble"], effects))
    state = battle(skill, [(4, 3)], base="hero_fighter")
    script_randint(monkeypatch, [19, 900, 3, 4, 5, 6])
    lost = cast(state, target_id=U2)
    (rolled,) = of(lost, GambleRolled)
    assert not rolled.success
    assert [e.cause for e in of(lost, DamageDealt)] == ["attack", "backlash"]
    script_randint(monkeypatch, [19, 100, 3, 4, 5, 6])
    won = cast(state, target_id=U2)
    assert of(won, GambleRolled)[0].success
    assert [e.cause for e in of(won, DamageDealt)] == ["attack"]
    assert of(won, DamageDealt)[0].multiplier_permille == 2400  # 1200 × 2


def test_on_kill_effects_fire_in_battle() -> None:
    effects = [
        {
            "type": "damage",
            "multiplier_permille": 1500,
            "on_kill": [
                {"type": "refund_ap", "amount": 1},
                {"type": "heal", "dice": "1d4"},
            ],
        }
    ]
    skill = _built(_weapon_draft(effects))
    state = hit_with(battle(skill, [(4, 3, no_reactions("bandit", max_hp=1))], base="hero_fighter"))
    state.units[U1].hp = 1
    result = cast(state, target_id=U2)
    assert len(of(result, ApRefunded)) == 1
    assert of(result, Healed) and of(result, Healed)[0].target_id == U1


# ---------------------------------------------------------------------------
# 每個子效果選項都能組出合法的技能（驗證器不會因為選項本身退回）
# ---------------------------------------------------------------------------


def _fill_into(owner: str, field: str, sub: Choice) -> dict[str, Any]:
    template = TEMPLATES[owner]
    base = LIB.skills[template].model_dump(mode="json", exclude_none=True)["effects"]
    filled = fill_fields(sub.params)
    assert filled is not None
    item = {"type": str(sub.value), **filled}
    out: list[dict[str, Any]] = []
    for effect in base:
        patched = dict(effect)
        if effect["type"] == owner:
            patched[field] = [item]
            if owner == "gamble":
                patched.pop("lose" if field == "win" else "win", None)
        out.append(patched)
    return _draft(template, out)


@pytest.mark.parametrize(("owner", "field"), sorted(NESTED_PARAMS))
def test_every_sub_effect_choice_is_accepted_by_the_schema(owner: str, field: str) -> None:
    template = TEMPLATES[owner]
    choices = _effects_step_choices(_draft(template, LIB.skills[template].model_dump()["effects"]))
    for sub in _nested(choices[owner], field).choices:
        result = check_draft(_fill_into(owner, field, sub), LIB)
        assert not [p for p in result.problems if p.rule == "schema"], (sub.value, result.problems)
