"""E6-a1：招牌標記（08 8.27、8.30，#169、#180）。"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import SIGNATURE_KINDS, ActionAffix, AffixDef
from trpg.content.library.gear_checks import _action_problems

_ADAPTER: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)


def _skill_of_kind(kind: str) -> str:
    lib = library()
    return next(s.id for _, s in sorted(lib.skills.items()) if s.kind == kind)


def _action(skill: str, signature: str | None) -> AffixDef:
    data: dict[str, object] = {
        "id": "affix_test_sig_action",
        "name_zh": "解鎖測試招",
        "category": "action",
        "slots": ["weapon"],
        "skill": skill,
    }
    if signature is not None:
        data["signature"] = signature
    return _ADAPTER.validate_python(data)


def test_five_signature_kinds() -> None:
    assert SIGNATURE_KINDS == ("action", "reaction", "terrain", "behavior", "rule")


def test_signature_omitted_when_empty() -> None:
    lib = library()
    for affix in lib.affixes.values():
        assert affix.signature is None
        assert "signature" not in affix.model_dump()
        assert "signature" not in affix.model_dump_json()


def test_signature_round_trips() -> None:
    affix = _action(_skill_of_kind("active"), "action")
    assert affix.signature == "action"
    assert affix.model_dump()["signature"] == "action"
    assert _ADAPTER.validate_python(affix.model_dump()) == affix


@pytest.mark.parametrize(
    ("category", "signature"),
    [("action", "terrain"), ("action", "rule"), ("reaction", "action"), ("stat", "action")],
)
def test_signature_must_match_category(category: str, signature: str) -> None:
    data: dict[str, object] = {
        "id": "affix_test_sig",
        "name_zh": "x",
        "category": category,
        "slots": ["weapon"],
        "signature": signature,
    }
    extra: dict[str, dict[str, object]] = {
        "action": {"skill": "skill_x"},
        "reaction": {"mode": "grant", "reaction": "redirect_damage", "range": 1},
        "stat": {"stat": "move", "value": {"min": 1, "max": 1}, "name_zh": "移動 +{n}"},
    }
    data.update(extra[category])
    with pytest.raises(ValidationError, match="招牌"):
        _ADAPTER.validate_python(data)


def test_unknown_signature_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        _action(_skill_of_kind("active"), "legend")


@pytest.mark.parametrize(
    ("signature", "kind"),
    [("action", "active"), ("behavior", "modifier"), ("reaction", "reaction")],
)
def test_granted_skill_kind_matches_signature(signature: str, kind: str) -> None:
    lib = library()
    good = _action(_skill_of_kind(kind), signature)
    assert isinstance(good, ActionAffix)
    assert _action_problems(good, lib.ruleset) == []
    other = "passive" if kind != "passive" else "active"
    bad = _action(_skill_of_kind(other), signature)
    assert isinstance(bad, ActionAffix)
    assert any("招牌" in p for p in _action_problems(bad, lib.ruleset))


def test_action_affix_without_signature_unchanged() -> None:
    lib = library()
    plain = _action(_skill_of_kind("passive"), None)
    assert isinstance(plain, ActionAffix)
    assert _action_problems(plain, lib.ruleset) == []
