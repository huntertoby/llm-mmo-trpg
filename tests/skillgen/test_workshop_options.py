"""技能工坊的選項推導（Phase 3F-1 驗收 1）：``trpg.skillgen.options.draft_options``。"""

from __future__ import annotations

import re
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE, Walk
from trpg.content.library import ContentLibrary
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_conform import field_problems
from trpg.skillgen.option_models import Choice, DraftOptions, FieldSpec, StepOptions
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill


def _step(options: DraftOptions, step_id: str) -> StepOptions:
    return next(s for s in options.steps if s.id == step_id)


def _field(step: StepOptions, name: str) -> FieldSpec:
    return next(f for f in step.fields if f.field == name)


def _choice(field: FieldSpec, value: object) -> Choice:
    return next(c for c in field.choices if c.value == value)


def _key(value: object) -> object:
    return value.get("type") if isinstance(value, dict) else value


def _assert_picks_are_offered(step: StepOptions, picks: dict[str, Any]) -> None:
    """這一步填的每個值都在選項內（:func:`field_problems` 沒有問題），而且每個填的欄位都是這一步
    （或被選選項的參數）列出的欄位。"""
    assert field_problems(step.fields, picks) == []
    names = {f.field.split(".")[0] for f in step.fields}
    params = {
        p.field
        for f in step.fields
        for c in f.choices
        if c.value == _key(picks.get(f.field))
        for p in c.params
    }
    assert set(picks) <= names | params


@pytest.mark.parametrize(
    "walk", [STRIKE, DISPLACE, MODIFIER], ids=["strike", "displace", "modifier"]
)
def test_walking_the_options_step_by_step_builds_a_legal_skill(walk: Walk) -> None:
    lib = library()
    draft: dict[str, Any] = {}
    for step_id, picks in walk:
        options = draft_options(draft, lib)
        ids = [s.id for s in options.steps]
        assert step_id in ids  # 前面的步驟都完成了（條件、代價可省略，所以已經是完成狀態）
        assert all(s.complete for s in options.steps[: ids.index(step_id)])
        assert options.problems == ()
        _assert_picks_are_offered(_step(options, step_id), picks)
        draft.update(picks)
    final = draft_options(draft, lib)
    assert final.next_step is None and final.problems == ()
    result = check_draft(draft, lib)
    assert result.legal, result.problems
    assert result.budget is not None and result.budget.verdict == "ok"


def test_strike_options_offer_the_skeleton_shapes_and_primitives() -> None:
    lib = library()
    draft: dict[str, Any] = {}
    for _step_id, picks in STRIKE[:3]:
        draft.update(picks)
    effects = _field(_step(draft_options(draft, lib), "effects"), "effects")
    values = {c.value for c in effects.choices}
    strike = lib.skeletons["strike"]
    assert {"damage", "push", "pull", "knock_prone", "dash", "apply_status"} <= values
    assert values <= set(strike.core.primitives) | set(strike.secondary.primitives or ())
    assert _choice(effects, "damage").info["core"] is True
    assert _choice(effects, "push").info["secondary"] is True
    # 武器技的傷害不填骰子（用武器骰）
    assert "dice" not in {p.field for p in _choice(effects, "damage").params}


def test_reaction_options_follow_the_schema() -> None:
    """反應技不能用衝鋒等自身位移（schema 的檢查，以試組濾掉）；intercept 只給
    ally_hit_adjacent。"""
    lib = library()
    draft: dict[str, Any] = {
        "skeleton": "reaction",
        "kind": "reaction",
        "reaction": {"event": "hit_by_melee"},
        "category": "weapon",
        "weapon_req": "melee",
        "scaling_attr": "str",
        "tier": 2,
        "shape": {"type": "single", "range": 1},
    }
    values = {
        c.value for c in _field(_step(draft_options(draft, lib), "effects"), "effects").choices
    }
    assert "damage" in values and "push" in values
    assert "intercept" not in values
    draft["reaction"] = {"event": "ally_hit_adjacent"}
    draft["shape"] = {"type": "self"}
    values = {
        c.value for c in _field(_step(draft_options(draft, lib), "effects"), "effects").choices
    }
    assert "intercept" in values


def _int_params(choice: Choice) -> dict[str, tuple[int | None, int | None]]:
    return {p.field: (p.min, p.max) for p in choice.params if p.type == "int"}


def test_param_ranges_match_the_content_files() -> None:
    """原語、形狀、條件的參數範圍與 ``skill_primitives.yaml``、``skill_shapes.yaml``、
    ``skill_conditions.yaml`` 一致。"""
    lib = library()
    rules = lib.ruleset
    primitives = rules.primitives.by_id()
    checked = 0
    for walk in (STRIKE, DISPLACE):
        draft: dict[str, Any] = {}
        for _step_id, picks in walk[:4]:
            draft.update(picks)
        options = draft_options(draft, lib)
        for choice in _field(_step(options, "effects"), "effects").choices:
            yaml_params = primitives[str(choice.value)].params
            for name, (low, high) in _int_params(choice).items():
                spec = yaml_params[name]
                assert (low, high) == (spec.min, spec.max), (choice.value, name)
                checked += 1
        shapes = rules.shapes.by_id()
        for choice in _field(_step(options, "shape"), "shape").choices:
            for name, (low, high) in _int_params(choice).items():
                shape_param = shapes[str(choice.value)].params[name]
                assert (low, high) == (shape_param.min, shape_param.max)
                checked += 1
        conditions = rules.conditions.by_id()
        for choice in _field(_step(options, "condition"), "condition").choices:
            for name, (low, high) in _int_params(choice).items():
                spec = conditions[str(choice.value)].params[name]
                assert (low, high) == (spec.min, spec.max)
                checked += 1
    push = _choice(
        _field(
            _step(
                draft_options(dict(DISPLACE[0][1] | DISPLACE[1][1] | DISPLACE[2][1]), lib),
                "effects",
            ),
            "effects",
        ),
        "push",
    )
    assert _int_params(push)["distance"] == (1, 2)
    assert checked > 10


def _fits(lib: ContentLibrary, data: dict[str, Any]) -> tuple[str | None, tuple[str, ...]]:
    options = draft_options(data, lib)
    return options.next_step, options.problems


def test_every_shipped_skill_fits_the_options() -> None:
    """選項不會漏掉合法的技能：內容庫的每個技能（含六種複合技能，3F-4b），每個欄位都在選項之內。"""
    lib = library()
    for skill_id, skill in sorted(lib.skills.items()):
        data = skill.model_dump(mode="json", exclude_none=True)
        assert _fits(lib, data) == (None, ()), skill_id


def test_random_skills_fit_the_options() -> None:
    lib = library()
    for seed in range(120):
        skill = compose_random_skill(seed, library=lib)
        data = skill.model_dump(mode="json", exclude_none=True)
        step, problems = _fits(lib, data)
        assert (step, problems) == (None, ()), seed


def test_values_outside_the_options_are_reported_in_chinese() -> None:
    lib = library()
    draft = {
        "skeleton": "strike",
        "kind": "active",
        "ap_cost": 5,
        "category": "weapon",
        "weapon_req": "focus",
        "scaling_attr": "str",
        "tier": 1,
        "shape": {"type": "cone", "size": 3},
        "effects": [
            {"type": "damage"},
            {"type": "push", "distance": 5, "affects": "tiles"},
            {"type": "heal", "dice": "2d6"},
        ],
    }
    problems = draft_options(draft, lib).problems
    assert "AP必須在 1–3，收到 5" in problems
    assert "武器需求不在可選範圍內（可選：近戰武器、遠程武器）" in problems
    assert "形狀不在可選範圍內（可選：單體、單位與落點）" in problems
    assert "第 2 個效果：距離（格）必須在 1–2，收到 5" in problems
    assert any(p.startswith("第 2 個效果：對象不在可選範圍內") for p in problems)
    assert any(p.startswith("第 3 個效果：效果不在可選範圍內") for p in problems)
    for p in problems:  # 玩家看不到欄位名、代號（玩法決定 #44）
        assert not re.search(r"[A-Za-z_]{3,}", p), p


def test_stale_scaling_attr_message_is_plain_chinese() -> None:
    """神聖傷害的法術技不能看意志：訊息用中文屬性名並說明原因，不露 draft／scaling_attr／wil。"""
    lib = library()
    draft = {
        "skeleton": "strike",
        "kind": "active",
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "wil",
        "tier": 1,
        "shape": {"type": "single"},
        "effects": [{"type": "damage", "element": "holy", "dice": "2d6"}],
    }
    result = check_draft(draft, lib)
    texts = [p.message_zh for p in result.problems]
    assert any("縮放屬性「意志」不在可選範圍內" in t and "只能看" in t for t in texts), texts
    for t in texts:
        assert "scaling_attr" not in t and "wil" not in t and "draft" not in t, t


def test_options_start_from_the_skeleton_and_are_deterministic() -> None:
    lib = library()
    empty = draft_options({}, lib)
    assert empty.next_step == "skeleton"
    assert [s.id for s in empty.steps] == ["skeleton"]
    skeletons = {c.value for c in empty.steps[0].fields[0].choices}
    assert skeletons == {s.id for s in lib.skeletons.values() if s.enabled}
    draft = dict(DISPLACE[0][1] | DISPLACE[1][1] | DISPLACE[2][1])
    assert draft_options(draft, lib) == draft_options(dict(draft), lib)


def test_rarity_step_derives_the_minimum_rarity() -> None:
    lib = library()
    draft: dict[str, Any] = {}
    for _step_id, picks in STRIKE[:-1]:
        draft.update(picks)
    rarity = _step(draft_options(draft, lib), "rarity")
    assert [c.value for c in _field(rarity, "rarity").choices] == ["rare", "epic"]
    assert "最低稀有度：稀有" in rarity.notes_zh
    assert "原語 knock_prone：至少稀有" in rarity.notes_zh


def test_legendary_source_is_offered_only_with_a_legendary_core() -> None:
    lib = library()
    draft: dict[str, Any] = {}
    for _step_id, picks in MODIFIER[:-1]:
        draft.update(picks)
    cost = {f.field for f in _step(draft_options(draft, lib), "cost").fields}
    assert {"cost.source", "activation"} <= cost
    plain: dict[str, Any] = {}
    for _step_id, picks in STRIKE[:-1]:
        plain.update(picks)
    assert "cost.source" not in {f.field for f in _step(draft_options(plain, lib), "cost").fields}
    paid = {**draft, "cost": {"source": 1}, "activation": "timed"}
    rarities = [
        c.value for c in _field(_step(draft_options(paid, lib), "rarity"), "rarity").choices
    ]
    assert rarities == ["legendary"]
