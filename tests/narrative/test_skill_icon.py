"""``trpg.narrative.skill_icon`` 的測試（Phase 3-17）：技能定義 → 組裝式圖示資料。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE, walk_draft
from trpg.narrative.skill_icon import ELEMENT_IDS, SkillIcon, icon_of, skill_icon
from trpg.narrative.skills import skill_card
from trpg.skillgen.random_composer import compose_random_skill

LIB = library()
RANDOM_SEEDS = range(50)


def _icon(skill_id: str) -> SkillIcon:
    return skill_icon(LIB.skills[f"skill_{skill_id}"])


def test_every_library_skill_derives_a_valid_icon() -> None:
    shape_ids = {s.id for s in LIB.ruleset.shapes.shapes}
    for skill in LIB.skills.values():
        icon = skill_icon(skill)
        assert icon.kind == skill.kind and icon.rarity == skill.rarity
        assert icon.weapon_req == skill.weapon_req
        assert not icon.partial or skill.kind == "modifier"
        assert len(icon.segments) == (2 if skill.followup is not None else 1)
        assert (icon.link is None) == (skill.followup is None)
        for seg in icon.segments:
            assert seg.shape_id in shape_ids
            assert seg.skeleton is not None
        assert set(icon.elements) <= set(ELEMENT_IDS)
        assert SkillIcon.model_validate_json(icon.model_dump_json()) == icon
        assert skill_card(LIB, skill).icon == icon


def test_random_composer_skills_all_derive_icons() -> None:
    for seed in RANDOM_SEEDS:
        skill = compose_random_skill(seed, library=LIB)
        icon = skill_icon(skill)
        assert icon == icon_of(skill.model_dump(mode="json", exclude_none=True))
        assert SkillIcon.model_validate(icon.model_dump(mode="json")) == icon
        assert len(icon.segments) == (2 if skill.followup is not None else 1)


def test_composite_skills_have_two_segments_and_a_link() -> None:
    leap = _icon("leap_slam")
    assert len(leap.segments) == 2 and leap.link == "after_move"
    assert leap.segments[0].skeleton == "displace"
    spiral = _icon("death_spiral")
    assert len(spiral.segments) == 2 and spiral.link == "on_kill"
    assert all(s.effects for s in spiral.segments)
    parry = _icon("parry_riposte")
    assert parry.link == "delayed" and "delay" in parry.costs


def test_kind_specific_fields() -> None:
    assert _icon("ember_brand").kind == "passive" and _icon("ember_brand").trigger is not None
    assert _icon("riposte").kind == "reaction" and _icon("riposte").trigger == "hit_by_melee"
    assert _icon("bulwark_stance").kind == "stance"
    shove = _icon("burning_shove")
    assert shove.kind == "modifier" and shove.modifier is not None
    assert {c.key for c in shove.modifier.changes} >= {"add_element"}
    assert "source" in _icon("kindred_flame").costs
    assert _icon("fire_bolt").costs == ()  # 法力與冷卻不算特殊代價


def test_elements_come_from_effects_then_tags() -> None:
    assert _icon("fire_bolt").elements[:1] == ("fire",)
    tagged = icon_of({"tags": ["control", "ice", "fire"], "effects": [{"type": "damage"}]})
    assert tagged.elements == ("ice",)
    two = icon_of(
        {"effects": [{"type": "damage", "element": "fire"}, {"type": "damage", "element": "ice"}]}
    )
    assert two.elements == ("fire", "ice")
    assert icon_of({}).elements == ()


def test_effect_status_surface_and_condition_are_kept() -> None:
    icon = icon_of(
        {
            "shape": {"type": "cone", "size": 2},
            "effects": [
                {"type": "apply_status", "status": "burning"},
                {"type": "create_surface", "surface": "fire"},
                {"type": "damage", "condition": {"type": "from_behind"}},
            ],
        }
    )
    effects = icon.segments[0].effects
    assert (effects[0].status, effects[1].surface, effects[2].condition) == (
        "burning",
        "fire",
        "from_behind",
    )
    assert icon.condition is not None and icon.condition.id == "from_behind"  # 取第一個效果上的條件
    own = icon_of({"condition": {"type": "target_has_status", "status": "frozen"}, "effects": []})
    assert own.condition is not None and own.condition.status == "frozen"


def test_costs_list_only_the_special_ones_in_a_stable_order() -> None:
    icon = icon_of(
        {
            "cost": {"mana": 2, "cooldown": 3, "source": 1, "stacks": 2, "uses_per_battle": 1},
            "effects": [{"type": "gamble"}],
            "activation": "timed",
        }
    )
    assert icon.costs == ("source", "gamble", "stacks", "once", "delay")
    assert icon_of({"cost": {"on_miss": [{"type": "damage"}]}}).costs == ("self",)
    assert icon_of({"cost": {"self_status": {"status": "weaken", "duration": 2}}}).costs == (
        "self",
    )
    assert icon_of({"activation": "battle"}).costs == ("once",)


def test_unknown_primitives_statuses_surfaces_and_conditions_pass_through() -> None:
    icon = icon_of(
        {
            "kind": "wizard",
            "rarity": "mythic",
            "weapon_req": "pointy",
            "shape": {"type": "tesseract", "range": "weapon"},
            "condition": {"type": "moon_is_full"},
            "effects": [
                {"type": "teleport_to_moon"},
                {"type": "apply_status", "status": "glitter"},
                {"type": "create_surface", "surface": "jelly"},
            ],
        }
    )
    assert (icon.kind, icon.rarity, icon.weapon_req) == ("active", "common", "any")
    seg = icon.segments[0]
    assert seg.shape_id == "tesseract" and seg.range is None
    assert [e.type for e in seg.effects] == ["teleport_to_moon", "apply_status", "create_surface"]
    assert seg.effects[1].status == "glitter" and seg.effects[2].surface == "jelly"
    assert icon.condition is not None and icon.condition.id == "moon_is_full"


def test_garbage_input_never_raises() -> None:
    junk: list[dict[str, Any]] = [
        {},
        {"effects": "damage", "shape": 3, "cost": [], "followup": 7, "modifiers": {"a": 1}},
        {"effects": [None, 1, {"type": 5}, {"type": "damage", "condition": "x"}], "tags": 5},
        {"followup": {}, "kind": None, "trigger": [], "reaction": "x"},
        {"kind": "modifier", "modifiers": [None, {"applies_to": 3, "change": [1]}]},
        {"modifiers": [{"applies_to": {"skill_tags": ["push"]}, "change": {"x": object()}}]},
    ]
    for d in junk:
        icon = icon_of(d)
        assert SkillIcon.model_validate(icon.model_dump(mode="json")) == icon


def test_workshop_drafts_get_more_parts_with_every_step() -> None:
    for walk in (STRIKE, DISPLACE, MODIFIER):
        draft: dict[str, Any] = {}
        sizes: list[int] = []
        for _step, picks in walk:
            draft.update(picks)
            icon = icon_of(draft)
            sizes.append(
                int(icon.segments[0].skeleton is not None)
                + int(icon.segments[0].shape_id is not None)
                + len(icon.segments[0].effects)
                + int(icon.modifier is not None)
                + int(icon.rarity != "common")
            )
        assert sizes == sorted(sizes) and sizes[-1] > sizes[0]
        final = icon_of(walk_draft(walk))
        assert not final.partial or walk is MODIFIER


def test_client_fixture_is_current() -> None:
    from tests.narrative.icon_fixture import FIXTURE_PATH, render

    saved = FIXTURE_PATH.read_text(encoding="utf-8")
    assert saved == render(), "重產：uv run python -m tests.narrative.icon_fixture"


def test_workshop_draft_partial_flag() -> None:
    assert icon_of({}).partial
    assert icon_of({"skeleton": "strike", "shape": {"type": "single"}}).partial
    done = icon_of(walk_draft(STRIKE))
    assert not done.partial and done.segments[0].shape_id == "single"
    assert [e.type for e in done.segments[0].effects] == ["damage", "knock_prone"]
