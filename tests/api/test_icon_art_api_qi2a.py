"""API 帶出 Q 版主圖代碼 ``icon.art``（Phase QI-2a，T-A10）。

技能卡、變奏卡、``/api/workshop/check`` 的圖示都有 ``art``，而且等於
:func:`~trpg.narrative.skill_icon_art.derive_art` 用內容庫上的表算出的值。
"""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, STRIKE, walk_draft
from trpg.api.skill_cards import skill_card
from trpg.narrative.skill_icon_art import derive_art, icon_art_rules


def test_skill_cards_and_variant_cards_carry_art() -> None:
    lib = library()
    rules = icon_art_rules(lib)
    seen_variants = 0
    for skill_id in sorted(lib.skills):
        skill = lib.skills[skill_id]
        card = skill_card(lib, skill)
        want = derive_art(skill.model_dump(mode="json"), rules)
        assert card.icon.art == want, skill_id
        for spec, variant in zip(skill.variants, card.variants, strict=True):
            form = skill.variant_form(spec.id)
            assert variant.icon.art == derive_art(form.model_dump(mode="json"), rules), spec.id
            seen_variants += 1
    assert seen_variants > 0


def test_skill_card_uses_the_library_tables() -> None:
    """正式呼叫處吃內容庫上的表：允許清單換成空的，``icon_prop`` 就退回推導（D3 的同一條路）。"""
    lib = library()
    skill = lib.skills["skill_armor_breaker"]
    art = skill_card(lib, skill).icon.art
    assert art is not None and art.prop == "w:hammer"
    bare = replace(lib, icon_props=lib.icon_props.model_copy(update={"props": ()}))
    other = skill_card(bare, skill).icon.art
    assert other is not None and other.prop != "w:hammer"


def test_workshop_check_icon_has_art(client: TestClient) -> None:
    lib = library()
    rules = icon_art_rules(lib)
    for walk in (STRIKE, DISPLACE):
        draft = walk_draft(walk)
        body = client.post("/api/workshop/check", json={"skill": draft}).json()
        art = derive_art(draft, rules).model_dump(mode="json")
        assert body["icon"]["art"] == art
        assert body["card"]["icon"]["art"]["prop"]  # 組好的技能卡也帶（由組好的技能推導）
