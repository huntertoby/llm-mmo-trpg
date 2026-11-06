"""新手前 10 分鐘的 API（Phase 6F-4；#129、#133、6F-2b）。

- 開局預覽多了 ``links``（兩招的觸發關係）、``recommended``／``recommended_zh``（推薦配法）。
- 大世界建角照推薦配法自動配好（不用自己配點）。
- 世界畫面多了 ``hints``（提示紀錄，記在角色身上）與 ``level_up``；三個提示動作走一般的動作端點。
- 6F-2b 的四句定稿文字。
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.world.helpers import NOON, with_rules
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute

START = {"name": "阿霧", "weapon": "dagger", "keywords": ["frozen", "concealed"], "seed": 0}


@pytest.fixture
def client(field_library: ContentLibrary, make_client: ClientFactory) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    return make_client(calm, clock=lambda: NOON)


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def test_start_preview_links_and_recommended(client: TestClient) -> None:
    body = {"weapon": "lightning_staff", "keywords": ["wet", "charged"], "seed": 0}
    preview = _ok(client.post("/api/runs/start-preview", json=body))
    assert sum(preview["recommended"].values()) == 4
    assert preview["recommended_zh"]
    for link in preview["links"]:
        assert link["text_zh"] == (
            f"{link['maker_zh']}製造{link['keyword']['name_zh']} → "
            f"{link['user_zh']}利用{link['keyword']['name_zh']}"
        )
    one = _ok(client.post("/api/runs/start-preview", json={**body, "keywords": ["wet"]}))
    assert one["links"] == []  # 選滿兩個才有


def test_world_character_is_auto_allocated(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    attrs = view["hero"]["attributes"]
    spent = {a: v - 10 for a, v in attrs.items() if v != 10}
    assert sum(spent.values()) == 4
    assert view["hero"].get("attribute_points", 0) == 0
    assert view["hints"] == {"seen": [], "off": False}
    assert view["level_up"] is None


def test_hint_actions_round_trip(client: TestClient) -> None:
    view = _ok(client.post("/api/world/characters", json=START), 201)
    cid = view["character"]["character_id"]
    url = f"/api/world/characters/{cid}/actions"
    seen = _ok(client.post(url, json={"kind": "hint_seen", "ids": ["opening", "move_attack"]}))
    assert seen["hints"] == {"seen": ["move_attack", "opening"], "off": False}
    off = _ok(client.post(url, json={"kind": "hints_off"}))
    assert off["hints"]["off"] is True
    reset = _ok(client.post(url, json={"kind": "hints_reset"}))
    assert reset["hints"] == {"seen": [], "off": False}


def test_final_texts_6f2b(field_library: ContentLibrary) -> None:
    newcomer = field_library.world_newcomer
    assert newcomer is not None
    assert newcomer.guide_capital_how_zh == "走到中央廣場的傳送陣，或按 M 選雲嶺的霧渡鎮"
    hints = {h.id: h.text_zh for h in newcomer.battle_hints}
    assert hints["ice_surface"] == "冰面很滑：踏上第一格要過敏捷判定，失敗會一路滑出去再倒地"
    assert hints["lethal_terrain"] == ("深淵、岩漿、冰窟是致命地形：被推進去會直接倒下，別背對它站")
    assert newcomer.reflash_lesson[0].text_zh == (
        "閃過的變化不滿意，可以重閃其中一次換成別的變化：要花靈感，但不用先上場"
    )
    assert newcomer.mentor_npc == "gran"
    assert set(newcomer.attribute_notes) == set(Attribute)
