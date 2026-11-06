"""BAL-19g：創角時關鍵字與屬性不搭的提示（06 6.27.3，#110；只提示、不擋）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from trpg.api.attribute_text import keyword_supply, route_hint
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute as A


def _ok(reply: Any) -> Any:
    assert reply.status_code in (200, 201), reply.text
    return reply.json()


def test_sword_with_spell_keywords_hints_mind_attributes(library: ContentLibrary) -> None:
    """設計的例子：力量最高卻選雷、暗——關鍵字多半是法術，建議心智屬性或有武器技的關鍵字。"""
    sword = library.weapons["one_handed_sword"]
    hint = route_hint(library, sword, ("charged", "concealed"))
    assert hint is not None
    assert hint.lean == "spell"
    assert A.STR not in hint.fits
    assert all(a in (A.INT, A.WIS, A.WIL) for a in hint.fits)
    assert hint.text_zh.startswith("你選的關鍵字多半是法術，建議配一些點到心智屬性")
    assert hint.text_zh.endswith("或選有武器技的關鍵字")


def test_sword_with_weapon_keywords_fits_strength(library: ContentLibrary) -> None:
    sword = library.weapons["one_handed_sword"]
    hint = route_hint(library, sword, ("prone", "collision"))
    assert hint is not None
    assert hint.lean == "weapon"
    assert A.STR in hint.fits  # 力量最高時前端不顯示
    assert "或選有法術的關鍵字" in hint.text_zh


def test_focus_weapon_does_not_suggest_weapon_skills(library: ContentLibrary) -> None:
    scepter = library.weapons["scepter"]
    hint = route_hint(library, scepter, ("summon", "ignite"))
    assert hint is not None
    assert A.WIS not in hint.fits  # 權杖感知最高、選召喚＋點燃：對不上
    assert "武器技" not in hint.text_zh  # 法器拿不到武器技


def test_supply_respects_weapon_and_keywords(library: ContentLibrary) -> None:
    staff = library.weapons["fire_staff"]
    supply = keyword_supply(library, staff, ("ignite",))
    assert supply
    assert all(s.category != "weapon" for s in supply)  # 法器拿不到武器技
    assert route_hint(library, staff, ()) is None
    assert route_hint(library, None, ("ignite",)) is None


def test_start_preview_returns_the_hint_and_creation_is_not_blocked(client: TestClient) -> None:
    body = {"weapon": "one_handed_sword", "seed": 3, "keywords": ["charged", "concealed"]}
    preview = _ok(client.post("/api/runs/start-preview", json=body))
    hint = preview["route_hint"]
    assert hint is not None and "str" not in hint["fits"] and hint["text_zh"]
    created = _ok(client.post("/api/runs", json={**body, "attributes": {"str": 4}}))
    assert created["hero"]["attributes"]["str"] == 14  # 只提示，不擋
    none = _ok(
        client.post(
            "/api/runs/start-preview",
            json={"weapon": "one_handed_sword", "seed": 3, "keywords": []},
        )
    )
    assert none["route_hint"] is None
