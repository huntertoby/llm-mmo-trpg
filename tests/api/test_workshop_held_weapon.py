"""工坊武器技縮放屬性顯示手上武器（Phase 3-48b）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.skillgen.workshop_walks import DISPLACE, walk_draft

CHARGE = walk_draft(DISPLACE)


def _scaling_name(client: TestClient, weapon: str | None) -> str:
    body: dict[str, Any] = {"skill": CHARGE}
    if weapon is not None:
        body["weapon"] = weapon
    steps = client.post("/api/workshop/options", json=body).json()["steps"]
    fields = [f for s in steps for f in s["fields"] if f["field"] == "scaling_attr"]
    assert len(fields) == 1
    name: str = fields[0]["choices"][0]["name_zh"]
    return name


def test_options_scaling_shows_held_weapon(client: TestClient) -> None:
    generic = _scaling_name(client, None)
    assert generic.startswith("依手上武器而定")
    library = store_of(client).library
    melee = sorted(
        (w for w in library.weapons.values() if w.weapon_class == "melee"), key=lambda w: w.id
    )
    single = next(w for w in melee if w.secondary_scaling_attr is None)
    dual = next(w for w in melee if w.secondary_scaling_attr is not None)
    for weapon in (single, dual):
        text = _scaling_name(client, weapon.id)
        assert text == f"看手上武器（目前：{weapon.name_zh}＝{weapon.scaling_names_zh()}）"
        assert weapon.id not in text
    dual_text = _scaling_name(client, dual.id)
    assert "取較高" in dual_text or "取平均" in dual_text


def test_options_scaling_falls_back_when_weapon_does_not_fit(client: TestClient) -> None:
    generic = _scaling_name(client, None)
    library = store_of(client).library
    focus = next(w for w in library.weapons.values() if w.weapon_class == "focus")
    assert _scaling_name(client, focus.id) == generic  # 大類不合
    assert _scaling_name(client, "no_such_weapon") == generic  # 不認得


def test_gear_catalog_weapons_have_chinese_class_and_look(client: TestClient) -> None:
    weapons = client.get("/api/gear/catalog").json()["weapons"]
    assert {w["weapon_class_zh"] for w in weapons} <= {"近戰武器", "遠程武器", "法器"}
    staff = next(w for w in weapons if w["weapon_class"] == "focus")
    assert staff["look"]["kind"] == "staff"
