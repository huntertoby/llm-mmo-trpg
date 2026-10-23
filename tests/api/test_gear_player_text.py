"""裝備測試的限制原因不露英文代號（Phase 3-48b，玩法決定 #44）。"""

from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient

_ENGLISH = re.compile(r"hammer|shield|melee|ranged|focus|longgun")


def _problems(client: TestClient, equipment: dict[str, Any]) -> str:
    res = client.post(
        "/api/gear/check", json={"hero_build": "build_charger", "equipment": equipment}
    )
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return "；".join(body["problems"])


def test_weapon_limited_affix_names_the_weapon_in_chinese(client: TestClient) -> None:
    sword = {
        "name_zh": "測試劍",
        "weapon": "one_handed_sword",
        "affixes": [{"affix": "affix_trait_hammer_knockback"}],
    }
    text = _problems(client, {"main_hand": {"custom": sword}})
    assert "只能出現在 錘 上" in text
    assert not _ENGLISH.search(text)


def test_shield_tag_is_chinese(client: TestClient) -> None:
    offhand = {"name_zh": "測試盾", "affixes": [{"affix": "affix_act_shield_wall"}]}
    text = _problems(client, {"off_hand": {"custom": offhand}})
    assert "需要物品標籤：盾" in text
    assert not _ENGLISH.search(text)
