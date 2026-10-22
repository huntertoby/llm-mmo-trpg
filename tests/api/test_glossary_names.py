"""Phase 3E-2e：glossary 的效果／條件／觸發名稱與武器外觀、FieldSpec 旗標、單位外觀欄位。"""

from __future__ import annotations

import re
from typing import get_args

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from trpg.content.battle import ReactionWhen
from trpg.content.library import ContentLibrary
from trpg.skillgen.option_models import FieldSpec

_FORBIDDEN = re.compile(r"Phase|[a-z]+_[a-z_]+|\d+-\d+")


def _glossary(client: TestClient) -> dict[str, list[dict[str, object]]]:
    data: dict[str, list[dict[str, object]]] = client.get("/api/glossary").json()
    return data


def test_glossary_has_every_primitive_condition_and_trigger(
    client: TestClient, library: ContentLibrary
) -> None:
    data = _glossary(client)
    rules = library.ruleset
    names = {e["id"]: e["name_zh"] for e in data["effects"]}
    assert names == {p.id: p.name_zh for p in rules.primitives.primitives}
    assert {e["id"]: e["name_zh"] for e in data["conditions"]} == {
        c.id: c.name_zh for c in rules.conditions.conditions
    }
    trigger_ids = {e["id"] for e in data["triggers"]}
    assert {t.id for t in rules.skill_triggers.triggers} <= trigger_ids


def test_every_reaction_event_has_a_name() -> None:
    events = {e.id for e in library().ruleset.reactions.events}
    assert set(get_args(ReactionWhen.model_fields["event"].annotation)) <= events


def test_effect_descriptions_are_the_player_text_and_have_no_identifiers(
    client: TestClient, library: ContentLibrary
) -> None:
    by_id = {p.id: p for p in library.ruleset.primitives.primitives}
    for entry in _glossary(client)["effects"]:
        primitive = by_id[str(entry["id"])]
        assert primitive.player_description, primitive.id
        assert entry["description_zh"] == primitive.player_description
        assert not _FORBIDDEN.search(primitive.player_description), primitive.id


def test_weapon_looks_come_from_the_weapon_table(
    client: TestClient, library: ContentLibrary
) -> None:
    looks = {e["id"]: e for e in client.get("/api/glossary").json()["weapon_looks"]}
    assert set(looks) == {w.id for w in library.weapons.values() if w.look is not None}
    assert looks["fire_staff"]["look"] == {
        "kind": "staff",
        "material": "wood",
        "element": "fire",
        "form": None,
    }
    assert looks["greatsword"]["two_handed"] is True


def test_field_spec_flags_follow_the_field_path() -> None:
    def spec(field: str, type_: str = "choice") -> FieldSpec:
        return FieldSpec.model_validate({"field": field, "name_zh": "x", "type": type_})

    assert spec("shape").card and spec("shape").object_choice
    assert spec("followup.shape").card and spec("followup.shape").object_choice
    assert spec("kind").card and not spec("kind").object_choice
    assert not spec("scaling_attr").card
    assert not spec("shape", "int").card
    dumped = spec("condition").model_dump(mode="json")
    assert dumped["card"] is True and dumped["object_choice"] is True
    assert FieldSpec.model_validate(dumped) == spec("condition")


def test_unit_views_carry_the_doll_look(client: TestClient) -> None:
    reply = client.post(
        "/api/battles", json={"map_id": "open_plain", "seed": 3, "hero_build": "build_fire"}
    )
    view = reply.json()["view"]
    dolls = {u["template_id"]: u["doll_look"] for u in view["units"]}
    assert dolls["sim_companion_fighter"] is not None
    assert dolls["sim_companion_fighter"]["gear"]["body"]["kind"] == "mail"
    assert dolls["build_fire"] is None
