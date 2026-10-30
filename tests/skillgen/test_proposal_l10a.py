"""Phase 4-L10a：4-L9 真模型評估後的 schema、錯誤路徑修正。不需要網路與模型。"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from tests.skillgen.helpers import effect_branches
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    VARIANT_CONDITIONS,
    ZONE_CASTER_SHAPES,
    SkillDef,
    SkillRuleError,
    error_path_of,
    granted_skill_problems,
)
from trpg.skillgen.proposal import (
    ACTIVE_ONLY_FIELDS,
    CATEGORIES,
    TOP_ONLY_DAMAGE_PARAMS,
    WEAPON_REQ_BY_CATEGORY,
    WEAPON_REQ_DOC,
    ZONE_AFFECTS,
    ProposalContext,
    ProposalModels,
    _proposal_path,
    _rule_error,
    _skill_path,
    build_proposal_models,
    evaluate_proposal,
    grantable_skills,
    proposal_from_skill,
)


@cache
def _lib() -> ContentLibrary:
    return library()


def _data(skill_id: str) -> dict[str, Any]:
    return _lib().skills[skill_id].model_dump(mode="json", exclude_defaults=True)


def _skill_error(data: dict[str, Any]) -> tuple[str, str]:
    """``SkillDef`` 驗證失敗 → （提議的錯誤路徑、訊息）。"""
    with pytest.raises(ValidationError) as info:
        SkillDef.model_validate(data)
    error = info.value.errors(include_url=False)[0]
    message = str(error["msg"]).removeprefix("Value error, ")
    return _skill_path(error, "", message), message


# -- A1：巢狀效果的錯誤帶完整路徑 ------------------------------------------------


def test_error_path_of_finds_nested_paths() -> None:
    assert error_path_of("effects[0]（damage）：x") == "effects[0]"
    assert error_path_of("cost.on_miss[1]（damage）：x") == "cost.on_miss[1]"
    assert error_path_of("effects[0].then[1]（damage）：x") == "effects[0].then[1]"
    assert error_path_of("effects[2]（gamble）.win[0]（damage）：x") == "effects[2].win[0]"
    assert error_path_of("cost.on_miss[1].status：反噬") == "cost.on_miss[1].status"
    assert error_path_of("followup.effects[0]（push）：x") == "followup.effects[0]"
    assert error_path_of("沒有路徑") == ""


def test_backlash_flag_error_points_at_cost_on_miss() -> None:
    data = _data("skill_fire_arrow")
    data["cost"] = {
        **data["cost"],
        "on_miss": [{"type": "damage", "dice": "1d4", "element": "fire", "explode": True}],
    }
    path, message = _skill_error(data)
    assert path == "cost_on_miss[0]"
    assert message.startswith("cost.on_miss[0]（damage）")


def test_then_flag_error_points_at_then() -> None:
    data = _data("skill_detonate_burning")
    data["effects"][0]["then"][0]["explode"] = True
    path, message = _skill_error(data)
    assert path == "effects[0].then[0]"
    assert "只能用在技能自己的傷害效果" in message


def test_gamble_branch_error_points_at_branch() -> None:
    data = _data("skill_fire_arrow")
    data["category"], data["weapon_req"] = "spell", "focus"
    data["cost"] = {"mana": 4}
    data["effects"] = [
        {"type": "damage", "dice": "1d6", "element": "fire"},
        {
            "type": "gamble",
            "chance_permille": 500,
            "win": [
                {
                    "type": "damage",
                    "dice": "1d4",
                    "element": "fire",
                    "scaling": {
                        "by": "missing_hp_10pct",
                        "per_step_permille": 50,
                        "cap_permille": 200,
                    },
                }
            ],
        },
    ]
    path, _ = _skill_error(data)
    assert path == "effects[1].win[0]"


def test_variant_effect_error_points_at_variant() -> None:
    data = _data("skill_tidal_spear")
    data["variants"] = [
        {
            "id": "v1",
            "name_zh": "測試",
            "when": {"caster_high_ground": True},
            "add_effect": {"type": "damage", "element": "ice"},
        }
    ]
    path, message = _skill_error(data)
    assert path == "variants[0].add_effect"
    assert message.startswith("變奏「測試」")


def test_variant_replace_main_damage_points_at_index() -> None:
    data = _data("skill_tidal_spear")
    data["variants"] = [
        {
            "id": "v1",
            "name_zh": "測試",
            "when": {"caster_high_ground": True},
            "replace_effect": {
                "index": 0,
                "effect": {"type": "damage", "dice": "1d4", "element": "ice"},
            },
        }
    ]
    path, _ = _skill_error(data)
    assert path == "variants[0].replace_effect.index"


def test_rule_paths_are_translated_to_proposal_paths() -> None:
    skill = _lib().skills["skill_tidal_spear"]
    assert _proposal_path("cost.on_miss[1].status") == "cost_on_miss[1].status"
    assert _proposal_path("variants.high_tide.when", skill) == "variants[1].when"
    assert _proposal_path("variants.tide_pierce.shape.type", skill) == "variants[0].shape.type"
    error = _rule_error("reference", "variants.high_tide.cost.on_miss[0].status：反噬…", skill)
    assert error.path == "cost_on_miss[0].status"
    error = _rule_error(
        "variant.tide_pierce.skeleton.secondary_count", "水中貫穿：骨架 combo：附帶效果最多", skill
    )
    assert error.path == "variants[0]"


def test_skill_rule_error_is_value_error() -> None:
    assert issubclass(SkillRuleError, ValueError)


# -- A2／A3／A4：schema 收緊 -----------------------------------------------------


@cache
def _models() -> ProposalModels:
    return build_proposal_models(_lib(), rarity="rare")


@cache
def _schema() -> dict[str, Any]:
    return _models().json_schema()


def _proposal(skill_id: str, **changes: Any) -> dict[str, Any]:
    data = proposal_from_skill(_lib().skills[skill_id], _lib())
    data.update(changes)
    return data


def _proposal_errors(
    data: dict[str, Any], models: ProposalModels | None = None
) -> list[tuple[str, str]]:
    result = evaluate_proposal(data, models or _models(), _lib(), ProposalContext(2, "rare"))
    return [(e.path, e.code) for e in result.errors if e.stage == "proposal"]


def test_nested_damage_has_no_top_only_flags() -> None:
    defs = _schema()["$defs"]
    for name in ("NestedEffect_damage", "BacklashEffect_damage"):
        assert set(TOP_ONLY_DAMAGE_PARAMS).isdisjoint(defs[name]["properties"]), name
    branches = effect_branches(_schema(), "Effect_damage")
    top = set().union(*(set(m["properties"]) for m in branches))
    assert {"explode", "scaling", "split_heal"} <= top


def test_backlash_status_excludes_unsafe_statuses() -> None:
    unsafe = _lib().ruleset.unsafe_backlash_statuses()
    assert {"bleed", "burning", "stun"} <= unsafe
    enum = _schema()["$defs"]["BacklashEffect_apply_status"]["properties"]["status"]["enum"]
    assert enum and unsafe.isdisjoint(enum)


def test_backlash_flag_is_rejected_by_schema() -> None:
    backlash = [{"type": "damage", "element": "fire", "explode": True}]
    data = _proposal("skill_fire_arrow", cost_on_miss=backlash)
    assert ("cost_on_miss[0].explode", "extra_forbidden") in _proposal_errors(data)


def test_reaction_branch_requires_reaction_and_drops_active_only_fields() -> None:
    defs = _schema()["$defs"]
    branch = defs["SkillProposal_reaction"]
    assert "reaction" in branch["required"]
    assert set(ACTIVE_ONLY_FIELDS).isdisjoint(branch["properties"])
    assert branch["properties"]["kind"] == {"const": "reaction", "type": "string"}
    main = defs["SkillProposal"]
    assert "reaction" not in main["properties"]
    assert "reaction" not in main["properties"]["kind"]["enum"]
    assert {"cost_overdraft", "cost_on_miss", "variants"} <= set(main["properties"])
    assert _proposal_errors(_proposal("skill_riposte", cost_overdraft=True)) == [
        ("cost_overdraft", "extra_forbidden")
    ]
    data = _proposal("skill_riposte")
    del data["reaction"]
    assert _proposal_errors(data) == [("reaction", "missing")]
    assert not _proposal_errors(_proposal("skill_riposte"))


def test_kind_error_lists_all_kinds_of_the_layout() -> None:
    data = _proposal("skill_fire_arrow", kind="modifier")
    result = evaluate_proposal(data, _models(), _lib(), ProposalContext(1, "common"))
    kind = next(e for e in result.errors if e.path == "kind")
    assert "reaction" in kind.allowed and "active" in kind.allowed


def test_weapon_req_documents_category_pairing() -> None:
    defs = _schema()["$defs"]
    assert defs["WeaponReq"]["description"] == WEAPON_REQ_DOC
    assert defs["WeaponReq"]["enum"] == ["melee", "ranged", "focus", "any"]


def test_category_split_lists_only_paired_weapon_req() -> None:
    models = build_proposal_models(_lib(), rarity="rare", split_category=True)
    defs = models.json_schema()["$defs"]
    for category, values in WEAPON_REQ_BY_CATEGORY.items():
        branch = defs[f"SkillProposal_{category}"]
        assert branch["properties"]["weapon_req"]["enum"] == list(values)
    data = _proposal("skill_fire_arrow", weapon_req="any")
    result = evaluate_proposal(data, models, _lib(), ProposalContext(1, "common"))
    error = next(e for e in result.errors if e.path == "weapon_req")
    assert error.code == "literal_error" and error.allowed == ("melee", "ranged")
    data = _proposal("skill_fire_arrow", category="magic")
    result = evaluate_proposal(data, models, _lib(), ProposalContext(1, "common"))
    assert next(e for e in result.errors if e.path == "category").allowed == CATEGORIES


def test_variant_when_is_exactly_one_condition_with_known_surfaces() -> None:
    defs = _schema()["$defs"]
    branches = [defs[str(i["$ref"]).rsplit("/", 1)[-1]] for i in defs["VariantWhen"]["oneOf"]]
    assert [b["required"] for b in branches] == [[c] for c in VARIANT_CONDITIONS]
    surface = defs["When_caster_surface"]["properties"]["caster_surface"]["items"]
    assert surface["enum"] == [s.id.value for s in _lib().ruleset.surfaces.surfaces]
    base = _proposal("skill_tidal_spear")

    def with_when(when: dict[str, Any]) -> list[tuple[str, str]]:
        return _proposal_errors({**base, "variants": [{**base["variants"][1], "when": when}]})

    assert not with_when({"caster_high_ground": True})
    two = with_when({"caster_high_ground": True, "caster_adjacent_blocker": True})
    assert two == [("variants[0].when.caster_adjacent_blocker", "extra_forbidden")]
    crystal = with_when({"caster_surface": ["crystal"]})
    assert crystal == [("variants[0].when.caster_surface[0]", "literal_error")]


def test_inscribe_needs_exactly_one_of_element_and_tag() -> None:
    base = _proposal("skill_ember_trail")
    effect = base["effects"][0]
    both = {**base, "effects": [{**effect, "tag": "fire"}]}
    assert ("effects[0].tag", "extra_forbidden") in _proposal_errors(both)
    neither = {**base, "effects": [{"type": "inscribe"}]}
    assert ("effects[0].element", "missing") in _proposal_errors(neither)
    assert not _proposal_errors({**base, "effects": [{"type": "inscribe", "tag": "fire"}]})


def test_split_heal_requires_affects_all() -> None:
    branches = effect_branches(_schema(), "Effect_damage")
    heal = next(b for b in branches if "split_heal" in b["properties"])
    assert heal["properties"]["affects"]["const"] == "all"
    assert {"split_heal", "affects"} <= set(heal["required"])
    plain = next(b for b in branches if "split_heal" not in b["properties"])
    assert "explode" in plain["properties"]
    data = _proposal("skill_fire_arrow")
    data["effects"] = [{"type": "damage", "element": "fire", "split_heal": True}]
    assert ("effects[0].affects", "missing") in _proposal_errors(data)


def test_zone_affects_required_and_anchor_decides_shapes() -> None:
    defs = _schema()["$defs"]
    caster = defs["SkillProposal_zone_caster"]
    refs = caster["properties"]["shape"].get("oneOf", [caster["properties"]["shape"]])
    shapes = {str(i["$ref"]).removeprefix("#/$defs/Shape_") for i in refs}
    assert shapes and shapes <= set(ZONE_CASTER_SHAPES)
    zone = defs["Effect_zone_caster"]
    assert zone["properties"]["anchor"]["const"] == "caster"
    assert "affects" in zone["required"]
    assert zone["properties"]["affects"]["enum"] == list(ZONE_AFFECTS)
    base = _proposal("skill_fire_wall")
    assert not _proposal_errors(dict(base))
    wrong = {**base, "effects": [{**base["effects"][0], "anchor": "caster"}]}  # 錐形＋跟隨
    errors = _proposal_errors(wrong)
    assert errors and all(path.startswith("shape") for path, _ in errors), errors
    effect = {k: v for k, v in base["effects"][0].items() if k != "affects"}
    assert ("effects[0].affects", "missing") in _proposal_errors({**base, "effects": [effect]})


def test_shadowstep_landing_decides_shape() -> None:
    base = _proposal("skill_shadow_ambush")
    assert not _proposal_errors(dict(base))
    effects = [{**base["effects"][0], "landing": "behind"}, *base["effects"][1:]]
    errors = _proposal_errors({**base, "effects": effects})
    assert errors and all(path.startswith("shape") for path, _ in errors), errors


def test_grant_skill_lists_grantable_skills() -> None:
    ids = grantable_skills(_lib())
    assert "skill_flight" in ids and ids == tuple(sorted(ids))
    branch = _schema()["$defs"]["Effect_grant_skill"]["properties"]["skill"]
    assert branch["enum"] == list(ids)
    primitives = _lib().ruleset.primitives.by_id()
    probe = _lib().skills["skill_wing_gift"]
    for skill_id in ids:
        effects = tuple(e.model_copy(update={"skill": skill_id}) for e in probe.effects)
        grant = probe.model_copy(update={"effects": effects})
        assert not granted_skill_problems(grant, _lib().skills, primitives), skill_id
    data = _proposal("skill_wing_gift")
    data["effects"][0]["skill"] = "skill_id_placeholder"
    assert ("effects[0].skill", "literal_error") in _proposal_errors(data)


def test_error_paths_never_contain_branch_tags() -> None:
    data = _proposal("skill_riposte", cost_overdraft=True)
    data["effects"] = [{"type": "inscribe", "element": "fire", "tag": "x"}]
    result = evaluate_proposal(data, _models(), _lib(), ProposalContext(1, "rare"))
    assert result.errors and all("~" not in e.path for e in result.errors)
