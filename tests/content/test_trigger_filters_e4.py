"""E4（#175，08 8.29 E4）：觸發篩選欄位 ``element``、``attack_kind``、``source``、``reaction`` 的
schema（被動技能的 ``TriggerSpec`` 與裝備的 ``TriggerAffix`` 共用一套檢查）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import TriggerAffix
from trpg.content.skills import TRIGGER_FILTER_TIMINGS, TriggerSpec
from trpg.shared.types import Element

_EFFECT = {"type": "apply_status", "status": "burning", "duration": 1}


def _affix(**fields: object) -> TriggerAffix:
    base: dict[str, object] = {
        "id": "affix_test_e4",
        "category": "trigger",
        "name_zh": "測試",
        "slots": ["body"],
        "trigger": "on_hit",
        "effects": [_EFFECT],
    }
    return TriggerAffix.model_validate(base | fields)


def test_new_filters_default_to_none_and_are_not_dumped() -> None:
    spec = TriggerSpec(event="on_hit")
    assert (spec.element, spec.attack_kind, spec.source, spec.reaction) == (None,) * 4
    dumped = spec.model_dump()
    assert not {"element", "attack_kind", "source", "reaction"} & set(dumped)
    affix = _affix()
    assert not {"element", "attack_kind", "source", "reaction"} & set(affix.model_dump())


def test_existing_content_has_no_new_filter() -> None:
    lib = library()
    for skill in lib.skills.values():
        t = skill.trigger
        if t is not None:
            assert (t.element, t.attack_kind, t.source, t.reaction) == (None,) * 4, skill.id
    for affix in lib.affixes.values():
        if isinstance(affix, TriggerAffix):
            got = (affix.element, affix.attack_kind, affix.source, affix.reaction)
            assert got == (None,) * 4, affix.id


@pytest.mark.parametrize("event", sorted(TRIGGER_FILTER_TIMINGS["element"]))
def test_element_filter_is_allowed_on_damage_timings(event: str) -> None:
    spec = TriggerSpec(event=event, element=Element.FIRE)
    assert spec.element is Element.FIRE
    assert spec.model_dump()["element"] == "fire"
    assert _affix(trigger=event, element="fire").element is Element.FIRE


@pytest.mark.parametrize("event", ["on_turn_start", "on_kill", "on_move", "on_collision"])
def test_filters_are_rejected_on_other_timings(event: str) -> None:
    for field, value in (("element", "fire"), ("attack_kind", "melee"), ("source", "skill")):
        with pytest.raises(ValidationError, match=f"{field} 篩選只能搭配"):
            TriggerSpec.model_validate({"event": event, field: value})
        with pytest.raises(ValidationError, match=f"{field} 篩選只能搭配"):
            _affix(trigger=event, **{field: value})


def test_block_timing_takes_kind_and_source_but_not_element() -> None:
    assert "on_block" in TRIGGER_FILTER_TIMINGS["attack_kind"]
    assert "on_block" not in TRIGGER_FILTER_TIMINGS["element"]


def test_reaction_filter_needs_source_reaction() -> None:
    spec = TriggerSpec(event="on_hit", source="reaction", reaction="opportunity_attack")
    assert spec.reaction == "opportunity_attack"
    with pytest.raises(ValidationError, match="source: reaction"):
        TriggerSpec(event="on_hit", reaction="opportunity_attack")
    with pytest.raises(ValidationError, match="source: reaction"):
        _affix(source="attack", reaction="opportunity_attack")


def test_unknown_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        TriggerSpec.model_validate({"event": "on_hit", "attack_kind": "thrown"})
    with pytest.raises(ValidationError):
        TriggerSpec.model_validate({"event": "on_hit", "source": "trap"})
    with pytest.raises(ValidationError):
        TriggerSpec.model_validate({"event": "on_hit", "element": "water"})


def test_melee_only_keeps_its_old_rule() -> None:
    assert _affix(trigger="on_damaged", melee_only=True).melee_only
    with pytest.raises(ValidationError, match="melee_only"):
        _affix(trigger="on_hit", melee_only=True)
