"""技能圖示資料帶出 ``icon_prop``（Phase IP-1，06 6.36，D5）：有填就帶、沒填照現行推導。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import DISPLACE, walk_draft
from trpg.api.skill_cards import skill_card
from trpg.narrative.skill_icon import icon_of, skill_icon


def test_skill_icon_carries_icon_prop_from_content() -> None:
    lib = library()
    for skill in lib.skills.values():
        icon = skill_icon(skill)
        assert icon.icon_prop == skill.icon_prop, skill.id
    assert skill_icon(lib.skills["skill_ember_bite"]).icon_prop == "summon:whelp"


def test_icon_without_prop_is_unchanged() -> None:
    """沒填的技能：``icon_prop`` 為 ``None`` 而且不輸出（其餘欄位照原本的推導）。"""
    skill = library().skills["skill_cleave"]
    dumped = skill_icon(skill).model_dump(mode="json")
    assert "icon_prop" not in dumped
    with_prop = skill.model_copy(update={"icon_prop": "w:axe"})
    other = skill_icon(with_prop).model_dump(mode="json")
    assert other.pop("icon_prop") == "w:axe"
    assert other == dumped  # 只影響圖示道具這一欄


def test_icon_of_tolerates_bad_icon_prop_values() -> None:
    assert icon_of({"icon_prop": 3}).icon_prop is None
    assert icon_of({"icon_prop": ""}).icon_prop is None
    assert icon_of({}).icon_prop is None


def test_skill_card_icon_and_variants_carry_icon_prop() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_armor_breaker"])
    assert card.icon.icon_prop == "w:hammer"


def test_workshop_check_ignores_draft_icon_prop(client: TestClient) -> None:
    """工坊草稿不帶 ``icon_prop``（D3 的保守延伸）：送了也不報錯、圖示照推導。"""
    draft = walk_draft(DISPLACE)
    plain = client.post("/api/workshop/check", json={"skill": draft}).json()
    tainted = client.post(
        "/api/workshop/check", json={"skill": {**draft, "icon_prop": "w:hammer"}}
    ).json()
    assert "icon_prop" not in tainted["icon"]
    assert tainted == plain
