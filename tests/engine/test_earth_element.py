"""Phase 3-54d：大地元素判定（06 6.33，#64）——技能元素、大地限制、震波命中、大地種子。

表格測試：技能元素 × 原語（隆起、下陷、石膚、震波）的合法性（驗證器、工坊、組合器一致）；震波實際跑
引擎（命中／未命中、友方不擲、會飛、已倒地）；大地種子卡片數字＝實戰；含震地波與碎岩擊的整場重播。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import SID, U1, battle, cast, of, script_rolls
from trpg.content.skills import SkillDef, skill_elements
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt, SkillUsed, StatusApplied, TerrainChanged
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import StatusInstance, state_to_json
from trpg.narrative.skills import effect_summary, skill_card
from trpg.shared.types import Element, Pos, Team, UnitId
from trpg.skillgen.draft import build_skill
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

LIB = library()
FOE = UnitId("unit_0002")
LINE3 = {"type": "line", "size": 3}
EARTH_RULE = "exclusion.terrain_needs_earth"

# ---------------------------------------------------------------------------
# 技能元素
# ---------------------------------------------------------------------------


def _tagged(tags: tuple[str, ...], element: str | None = None) -> SkillDef:
    data = make_skill(SID, LINE3, [{"type": "shockwave"}]).model_dump(mode="json")
    data.update(tags=list(tags), element=element)
    return SkillDef.model_validate(data)


def test_skill_element_field_wins_over_everything_else() -> None:
    skill = _tagged((), "earth")
    assert skill_elements(skill) == {Element.EARTH}
    with_hit = skill.model_copy(
        update={
            "effects": (
                *skill.effects,
                make_skill(
                    SID, LINE3, [{"type": "damage", "dice": "1d6", "element": "fire"}]
                ).effects[0],
            )
        }
    )
    assert skill_elements(with_hit) == {Element.EARTH}  # 效果自己的元素不算


def test_without_the_field_the_first_non_physical_element_tag_is_used() -> None:
    assert skill_elements(_tagged(("earth", "spell"))) == {Element.EARTH}
    assert skill_elements(_tagged(("physical", "fire"))) == {Element.FIRE}
    assert skill_elements(_tagged(("fire", "earth"))) == {Element.FIRE}  # 多個元素標籤：取第一個
    assert skill_elements(_tagged(("physical", "melee"))) == frozenset()
    assert skill_elements(_tagged(())) == frozenset()


def test_effect_elements_never_decide_the_skill_element() -> None:
    skill = make_skill(SID, LINE3, [{"type": "damage", "dice": "1d6", "element": "earth"}])
    assert skill_elements(skill) == frozenset()


def test_the_element_field_must_agree_with_the_element_tags() -> None:
    base = make_skill(SID, LINE3, [{"type": "shockwave"}]).model_dump(mode="json")
    with pytest.raises(ValueError, match="不一致"):
        SkillDef.model_validate({**base, "tags": ["fire"], "element": "earth"})
    SkillDef.model_validate({**base, "tags": ["physical", "earth"], "element": "earth"})


# ---------------------------------------------------------------------------
# 合法性表格：技能元素 × 原語（驗證器、工坊、組合器一致）
# ---------------------------------------------------------------------------

_EARTH_ONLY: dict[str, tuple[list[dict[str, Any]], str]] = {
    "raise_terrain": ([{"type": "raise_terrain", "affects": "tiles"}], "control"),
    "lower_terrain": ([{"type": "lower_terrain", "affects": "tiles"}], "control"),
    "stoneskin": ([{"type": "apply_status", "status": "stoneskin", "affects": "allies"}], "aura"),
    "shockwave": (
        [{"type": "damage", "dice": "1d8", "element": "earth"}, {"type": "shockwave"}],
        "area",
    ),
}
_ELEMENTS = [None, *(e.value for e in Element if e is not Element.PHYSICAL)]


def _built(effects: list[dict[str, Any]], skeleton: str, element: str | None) -> SkillDef:
    shape: dict[str, Any] = (
        {"type": "line", "size": 3}
        if skeleton == "area"
        else {"type": "single", "range": 3}
        if skeleton == "aura"
        else {"type": "cross", "range": 3}
    )
    skill = make_skill(SID, shape, effects)
    return skill.model_copy(
        update={
            "skeleton": skeleton,
            "rarity": "epic",
            "element": None if element is None else Element(element),
            "cost": skill.cost.model_copy(update={"cooldown": 3}),
        }
    )


@pytest.mark.parametrize("element", _ELEMENTS)
@pytest.mark.parametrize("name", sorted(_EARTH_ONLY))
def test_validator_allows_earth_only_things_for_earth_skills(
    name: str, element: str | None
) -> None:
    effects, skeleton = _EARTH_ONLY[name]
    skill = _built(effects, skeleton, element)
    broken = EARTH_RULE in [v.rule for v in validate_skill(skill, LIB)]
    assert broken is (element != "earth")


def _step_choices(draft: dict[str, Any], step: str, field: str) -> Any:
    options = draft_options(draft, LIB)
    spec = next(s for s in options.steps if s.id == step)
    return next(f for f in spec.fields if f.field == field)


_DRAFT: dict[str, Any] = {
    "skeleton": "control",
    "kind": "active",
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "tier": 1,
    "ap_cost": 1,
    "shape": {"type": "cross", "range": 4},
}


@pytest.mark.parametrize("element", _ELEMENTS)
@pytest.mark.parametrize("primitive", ["raise_terrain", "lower_terrain"])
def test_workshop_greys_out_terrain_exactly_when_the_validator_would(
    primitive: str, element: str | None
) -> None:
    draft = {**_DRAFT, "effects": [], **({} if element is None else {"element": element})}
    choice = next(
        c for c in _step_choices(draft, "effects", "effects").choices if c.value == primitive
    )
    effects, skeleton = _EARTH_ONLY[primitive]
    validator_says_no = EARTH_RULE in [
        v.rule for v in validate_skill(_built(effects, skeleton, element), LIB)
    ]
    assert ("unavailable_zh" in choice.info) is validator_says_no
    if validator_says_no:
        assert "大地" in choice.info["unavailable_zh"]


@pytest.mark.parametrize("element", _ELEMENTS)
def test_workshop_greys_out_shockwave_and_stoneskin_like_the_validator(element: str | None) -> None:
    extra = {} if element is None else {"element": element}
    area = {**_DRAFT, "skeleton": "area", "shape": {"type": "line", "size": 3}, **extra}
    shock = next(
        c
        for c in _step_choices({**area, "effects": []}, "effects", "effects").choices
        if c.value == "shockwave"
    )
    assert ("unavailable_zh" in shock.info) is (element != "earth")
    aura = {**_DRAFT, "skeleton": "aura", "shape": {"type": "single", "range": 3}, **extra}
    apply = next(
        c
        for c in _step_choices({**aura, "effects": []}, "effects", "effects").choices
        if c.value == "apply_status"
    )
    status = next(p for p in apply.params if p.field == "status")
    skin = next(c for c in status.choices if c.value == "stoneskin")
    assert ("unavailable_zh" in skin.info) is (element != "earth")
    other = next(c for c in status.choices if c.value == "hasted")
    assert "unavailable_zh" not in other.info


def test_workshop_basics_step_offers_the_skill_element() -> None:
    field = _step_choices(dict(_DRAFT), "basics", "element")
    values = {c.value for c in field.choices}
    assert "earth" in values and "physical" not in values
    assert not field.required


def test_workshop_pure_terrain_skill_with_earth_passes_the_earth_rule() -> None:
    draft = {
        **_DRAFT,
        "element": "earth",
        "effects": [{"type": "lower_terrain", "affects": "tiles"}],
        "rarity": "rare",
    }
    skill = build_skill(draft)
    assert EARTH_RULE not in [v.rule for v in validate_skill(skill, LIB)]
    fire = build_skill({**draft, "element": "fire"})
    assert EARTH_RULE in [v.rule for v in validate_skill(fire, LIB)]


def test_the_composer_only_uses_earth_only_parts_for_the_earth_theme() -> None:
    seen = {"earth": 0, "other": 0}
    for seed in range(400):
        skill = compose_random_skill(seed, rarity="epic", category="spell", library=LIB)
        parts = {e.type for e in skill.effects} | {
            e.status for e in skill.effects if e.type == "apply_status"
        }
        if parts & {"raise_terrain", "lower_terrain", "shockwave", "stoneskin"}:
            earth = Element.EARTH in skill_elements(skill)
            seen["earth" if earth else "other"] += 1
            assert earth, (seed, skill.tags)
        assert EARTH_RULE not in [v.rule for v in validate_skill(skill, LIB)]
    assert seen["earth"] > 0 and seen["other"] == 0


# ---------------------------------------------------------------------------
# 震波命中（敵方先擲命中、未命中不倒地、命中後不擲對抗；友方不擲命中）
# ---------------------------------------------------------------------------


def _shock(affects: str | None = None) -> SkillDef:
    effect: dict[str, Any] = {"type": "shockwave"}
    if affects is not None:
        effect["affects"] = affects
    return make_skill(SID, LINE3, [effect])


def _prone(result: Any, unit: str) -> bool:
    return bool(result.state.units[UnitId(unit)].has_status("prone"))


def test_shockwave_on_enemies_rolls_to_hit_and_a_miss_stays_standing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(_shock(), foes=[(4, 3), (5, 3)])
    script_rolls(monkeypatch, [1, 19])  # 第一個敵人未命中（自然 1），第二個命中
    result = cast(state, direction="east")
    assert not _prone(result, "unit_0002")
    assert _prone(result, "unit_0003")
    assert not [e for e in result.events if type(e).__name__ == "ManeuverRolled"]


def test_shockwave_on_allies_does_not_roll_to_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_shock("allies"), allies=[(4, 3), (5, 3)], foes=[(6, 6)])
    script_rolls(monkeypatch, [])  # 任何一次擲骰都會讓測試失敗
    result = cast(state, direction="east")
    assert _prone(result, "unit_0002") and _prone(result, "unit_0003")


def test_shockwave_on_everyone_rolls_for_enemies_only(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_shock("all"), allies=[(4, 3)], foes=[(5, 3)])
    script_rolls(monkeypatch, [1])  # 只有敵人擲命中一次：自然 1 未命中
    result = cast(state, direction="east")
    assert _prone(result, "unit_0002")  # 友方照樣倒地
    assert not _prone(result, "unit_0003")


def test_shockwave_ignores_flying_and_already_prone_units(monkeypatch: pytest.MonkeyPatch) -> None:
    flier = no_reactions(tags=["flying"])
    state = battle(_shock(), foes=[(4, 3, flier), (5, 3), (6, 3)])
    state.units[UnitId("unit_0004")].statuses.append(StatusInstance("prone", None))
    script_rolls(monkeypatch, [19, 19, 19, 19])  # 攻擊倒地的目標有優勢：多擲一顆
    result = cast(state, direction="east")
    assert not _prone(result, "unit_0002")
    assert _prone(result, "unit_0003")
    prone_events = [e for e in of(result, StatusApplied) if e.status_id == "prone"]
    assert [e.target_id for e in prone_events] == [UnitId("unit_0003")]


# ---------------------------------------------------------------------------
# 大地種子：卡片數字＝實戰
# ---------------------------------------------------------------------------

SEEDS = ("skill_quake_wave", "skill_rock_smash")


@pytest.mark.parametrize("skill_id", SEEDS)
def test_seed_skills_are_valid_earth_skills(skill_id: str) -> None:
    skill = LIB.skills[skill_id]
    assert skill_elements(skill) == {Element.EARTH}
    assert skill.element is Element.EARTH
    assert validate_skill(skill, LIB) == []
    card = skill_card(LIB, skill)
    assert (card.element, card.element_id) == ("大地", "earth")


def _seed_battle(skill: SkillDef, foes: list[tuple[int, int]], **kw: Any) -> Any:
    from tests.engine.helpers import give_turn, make_state  # noqa: PLC0415

    m = make_map("\n".join(["0000000"] * 7), ally=[(3, 3)], enemy=foes)
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill], base=kw.get("base", "hero_mage")))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def test_quake_wave_card_matches_the_fight(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = LIB.skills["skill_quake_wave"]
    lines = [effect_summary(LIB, skill, e) for e in skill.effects]
    assert "1d8" in lines[0] and "大地" in lines[0]
    assert "震波" in lines[1] and "先命中" in lines[1]
    skill = skill.model_copy(update={"id": SID})
    state = _seed_battle(skill, [(4, 3), (5, 3), (3, 6)])
    script_rolls(monkeypatch, [19, 19, 4, 4])  # 兩個命中判定，再依序擲傷害骰
    result = cast(state, direction="east")
    hits = [e for e in of(result, DamageDealt)]
    assert {e.target_id for e in hits} == {UnitId("unit_0002"), UnitId("unit_0003")}
    assert all(e.element is Element.EARTH for e in hits)
    assert _prone(result, "unit_0002") and _prone(result, "unit_0003")
    assert not _prone(result, "unit_0004")  # 不在線上


def test_rock_smash_deals_half_again_to_prone_targets() -> None:
    skill = LIB.skills["skill_rock_smash"]
    card = skill_card(LIB, skill)
    assert "倒地" in card.effects[1]
    assert (skill.effects[0].multiplier_permille, skill.effects[1].multiplier_permille) == (
        1200,
        600,
    )
    skill = skill.model_copy(update={"id": SID})

    def total(prone: bool) -> int:
        from tests.engine.helpers import with_rolls  # noqa: PLC0415

        state = _seed_battle(skill, [(4, 3)], base="hero_fighter")
        if prone:
            state.units[FOE].statuses.append(StatusInstance("prone", None))
        state = with_rolls(state, [(20, 19)])
        result = cast(state, target_id=FOE)
        return sum(e.amount for e in of(result, DamageDealt) if e.target_id == FOE)

    standing, down = total(False), total(True)
    assert down > standing


# ---------------------------------------------------------------------------
# 純地形的大地技能（沒有傷害）：卡片＝實戰
# ---------------------------------------------------------------------------


def test_a_pure_terrain_earth_skill_lowers_exactly_the_nine_tiles_the_card_says() -> None:
    effect = {"type": "lower_terrain", "amount": 1, "affects": "tiles"}
    skill = make_skill(SID, {"type": "square3", "range": 4}, [effect])
    skill = skill.model_copy(update={"skeleton": "control", "element": Element.EARTH})
    lines = [effect_summary(LIB, skill, e) for e in skill.effects]
    assert lines == ["降低地形 1 層（影響的格子）"]
    assert (skill_card(LIB, skill).element, [e.type for e in skill.effects]) == (
        "大地",
        ["lower_terrain"],
    )
    heights = "\n".join(["1111111"] * 7)
    state = battle(skill, foes=[(6, 6)], heights=heights)
    result = cast(state, target_pos=Pos(x=3, y=1))
    lowered = {(c.pos.x, c.pos.y) for c in of(result, TerrainChanged)}
    assert lowered == {(x, y) for x in (2, 3, 4) for y in (0, 1, 2)}
    assert all(result.state.tile(x, y).height == 0 for x, y in lowered)
    assert result.state.tile(3, 3).height == 1  # 範圍外不變
    assert not of(result, DamageDealt)


# ---------------------------------------------------------------------------
# 重播：用到震地波與碎岩擊的整場戰鬥
# ---------------------------------------------------------------------------


def test_a_battle_with_quake_wave_and_rock_smash_replays_identically() -> None:
    kit = ["skill_quake_wave", "skill_rock_smash"]
    m = make_map("\n".join(["0000000"] * 7), ally=[(1, 3)], enemy=[(5, 3), (5, 4), (6, 2)])
    spawns = [
        spawn(
            Team.ALLY,
            (1, 3),
            caster_template([LIB.skills[s] for s in kit], base="hero_fighter"),
        )
    ]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in [(5, 3), (5, 4), (6, 2)]]
    setup = make_setup(m, spawns, max_rounds=12)
    run = run_battle(setup, 7, UtilityAI(LIB.ai_profiles))
    again = replay(setup, 7, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert {e.skill_id for e in run.events if isinstance(e, SkillUsed)} & set(kit)
