"""Phase 4-L3：``required_when``（取代驗證器寫死的規則）與觸發 ``params`` 與既有驗證一致。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.skills import (
    PrimitiveParam,
    RequiredWhen,
    SkillDef,
    TriggerSpec,
    param_required_for,
)
from trpg.shared.types import Surface
from trpg.skillgen.validate import validate_skill

# ---------------------------------------------------------------------------
# required_when
# ---------------------------------------------------------------------------


def test_required_when_schema() -> None:
    with pytest.raises(ValidationError):
        RequiredWhen()
    with pytest.raises(ValidationError):
        RequiredWhen(category="spell", unless_filled="tag")
    with pytest.raises(ValidationError):
        PrimitiveParam(type="dice", required_when=RequiredWhen(category="spell"))


def test_shipped_required_when_is_exactly_the_old_hardcoded_pair() -> None:
    found = {
        (p.id, name): spec.required_when
        for p in library().ruleset.primitives.primitives
        for name, spec in p.params.items()
        if spec.required_when is not None
    }
    assert found == {
        ("damage", "dice"): RequiredWhen(category="spell"),
        ("inscribe", "element"): RequiredWhen(unless_filled="tag"),
    }


def _spec(primitive: str, name: str) -> PrimitiveParam:
    return library().ruleset.primitive_def(primitive).params[name]


@pytest.mark.parametrize(
    ("category", "expected"),
    [("spell", True), ("weapon", False)],
)
def test_damage_dice_required_by_category(category: str, expected: bool) -> None:
    spec = _spec("damage", "dice")
    assert param_required_for(spec, category=category, sibling_filled=lambda _: False) is expected


@pytest.mark.parametrize(("tag_filled", "expected"), [(False, True), (True, False)])
def test_inscribe_element_unless_tag(tag_filled: bool, expected: bool) -> None:
    spec = _spec("inscribe", "element")
    got = param_required_for(spec, category="spell", sibling_filled=lambda n: tag_filled)
    assert got is expected


def _skill(skill_id: str, **changes: Any) -> SkillDef:
    data = library().skills[skill_id].model_dump(mode="json")
    data.update(changes)
    return SkillDef.model_validate(data)


def test_validator_follows_required_when() -> None:
    lib = library()
    missing = "缺少必要參數 element"

    def messages(skill_id: str, effect: dict[str, Any]) -> list[str]:
        return [v.message for v in validate_skill(_skill(skill_id, effects=[effect]), lib)]

    # 符文有元素或標籤其中一個即可（YAML：unless_filled: tag）
    assert not any(
        missing in m
        for m in messages(
            "skill_thunder_sigil", {"type": "inscribe", "element": "lightning", "duration": 2}
        )
    )
    assert not any(
        missing in m
        for m in messages("skill_hunt_sigil", {"type": "inscribe", "tag": "hunt", "duration": 5})
    )
    # 兩者都沒有：SkillDef 自己的 schema 檢查先擋下（跨檔案檢查是第二道防線）
    with pytest.raises(ValidationError):
        messages("skill_hunt_sigil", {"type": "inscribe", "duration": 5})


# ---------------------------------------------------------------------------
# 觸發 params 與 TriggerSpec 一致
# ---------------------------------------------------------------------------

_SAMPLE: dict[str, Any] = {
    "n": 2,
    "tag": "fire",
    "status": "burning",
    "surface": Surface.FIRE,
}


def _trigger_ok(event: str, **fields: Any) -> bool:
    try:
        TriggerSpec(event=event, **fields)
    except ValidationError:
        return False
    return True


def test_trigger_params_match_trigger_spec() -> None:
    triggers = library().ruleset.skill_triggers.triggers
    declared = {name for t in triggers for name in t.params}
    assert declared == {"n", "tag", "status", "surface"}
    for trig in triggers:
        required = {n: _SAMPLE[n] for n, spec in trig.params.items() if spec.required}
        assert _trigger_ok(trig.id, **required), trig.id
        for name, spec in trig.params.items():
            # 必填的缺了會被拒；選填的省略沒事
            without = {k: v for k, v in required.items() if k != name}
            assert _trigger_ok(trig.id, **without) is (not spec.required), (trig.id, name)
            assert _trigger_ok(trig.id, **{**required, name: _SAMPLE[name]}), (trig.id, name)
        for name in sorted(declared - set(trig.params)):
            # 這個時機沒有宣告的參數，TriggerSpec 也不收
            assert not _trigger_ok(trig.id, **{**required, name: _SAMPLE[name]}), (trig.id, name)


def test_every_n_range_matches_trigger_spec() -> None:
    spec = next(t for t in library().ruleset.skill_triggers.triggers if t.id == "every_n_hits")
    n = spec.params["n"]
    assert (n.min, n.max) == (2, 3)
    assert _trigger_ok("every_n_hits", n=3)
    assert not _trigger_ok("every_n_hits", n=4)
