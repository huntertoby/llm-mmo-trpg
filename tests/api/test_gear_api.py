"""裝備測試介面的 API（Phase 3G-G4）：目錄、驗證（含中文原因）、套用到靶場戰鬥。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from trpg.cli.battle import cmd_replay
from trpg.engine.runner import BattleLog

BUILD = "build_charger"


def _check(client: TestClient, equipment: dict[str, Any], build: str = BUILD) -> dict[str, Any]:
    res = client.post("/api/gear/check", json={"hero_build": build, "equipment": equipment})
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


def _custom(*affixes: dict[str, Any], name: str = "測試物", **extra: Any) -> dict[str, Any]:
    return {"custom": {"name_zh": name, "affixes": list(affixes), **extra}}


def test_catalog_lists_slots_items_and_the_whitelist(client: TestClient) -> None:
    body = client.get("/api/gear/catalog").json()
    assert [s["slot"] for s in body["slots"]][:2] == ["main_hand", "off_hand"]
    assert len(body["slots"]) == 9
    assert len(body["affixes"]) == 34
    assert {a["category_number"] for a in body["affixes"]} == set(range(1, 12))
    strength = next(a for a in body["affixes"] if a["id"] == "affix_attr_str")
    assert (strength["value_min"], strength["value_max"]) == (1, 4)
    assert body["max_affixes_per_item"] == 4 and body["max_cost_affixes"] == 2
    sword = next(i for i in body["items"] if i["id"] == "item_test_sword")
    assert sword["appearance"]["kind"] == "sword" and sword["affixes"][0]["text_zh"] == "力量 +2"


def test_check_empty_loadout_is_legal_and_has_no_gear(client: TestClient) -> None:
    body = _check(client, {})
    assert body["legal"] is True and body["hero"]["equipment"] == []
    assert body["hero"]["gear_totals"] == []


def test_check_test_items_returns_hero_with_bonus_sources(client: TestClient) -> None:
    base = _check(client, {})["hero"]
    body = _check(
        client,
        {
            "head": {"item_id": "item_test_helm"},
            "ring_1": {"item_id": "item_test_ring_str"},
            "ring_2": {"item_id": "item_test_ring_hp"},
        },
    )
    assert body["legal"] is True, body
    hero = body["hero"]
    assert [e["slot"] for e in hero["equipment"]] == ["head", "ring_1", "ring_2"]
    assert hero["max_hp"] > base["max_hp"]
    totals = {t["key"]: t for t in hero["gear_totals"]}
    assert "max_hp" in totals and totals["max_hp"]["value"] > 0
    assert totals["max_hp"]["sources_zh"] and "來自裝備" in totals["max_hp"]["note_zh"]


def test_diminishing_is_shown_in_sources_and_conditions_are_labelled(client: TestClient) -> None:
    swift = {"affix": "affix_cost_swift"}
    low_hp = {"affix": "affix_cond_low_hp_damage", "value": 150}
    body = _check(
        client,
        {
            "feet": _custom(swift, name="疾風靴"),
            "body": _custom(swift, name="疾風衣"),
            "neck": _custom(low_hp, name="殘血項鍊"),
        },
    )
    assert body["legal"] is True, body
    totals = {t["key"]: t for t in body["hero"]["gear_totals"]}
    move = totals["move"]
    assert move["before_cap"] >= move["value"] > 0
    assert any("遞減" in s for s in move["sources_zh"])  # 第二條的權重只剩 50%
    cond = next(t for t in body["hero"]["gear_totals"] if t["condition_zh"])
    assert cond["value"] == 150 and "條件成立時才生效" in cond["note_zh"]


def test_damage_cap_is_marked_as_truncated(client: TestClient) -> None:
    low_hp = {"affix": "affix_cond_low_hp_damage", "value": 150}
    items = {
        "neck": _custom(low_hp, name="項鍊"),
        "ring_1": _custom(low_hp, {"affix": "affix_cost_glass"}, name="戒指甲"),
        "ring_2": _custom(low_hp, name="戒指乙"),
        "main_hand": _custom(
            low_hp, {"affix": "affix_cost_glass"}, name="玻璃劍", weapon="one_handed_sword"
        ),
    }
    body = _check(client, items)
    assert body["legal"] is True, body
    damage = [t for t in body["hero"]["gear_totals"] if t["key"].startswith("damage_permille")]
    assert damage and all(t["value"] <= 500 for t in damage)
    assert any(t["capped"] and "截斷" in t["note_zh"] for t in damage)


def test_illegal_custom_items_report_chinese_reasons(client: TestClient) -> None:
    five = ({"affix": f"affix_attr_{a}", "value": 1} for a in ("str", "dex", "con", "int", "wis"))
    cases: list[tuple[dict[str, Any], str]] = [
        ({"head": _custom({"affix": "affix_attr_str", "value": 9})}, "超出範圍"),
        ({"head": _custom({"affix": "affix_made_up", "value": 1})}, "不在白名單"),
        ({"ring_1": _custom({"affix": "affix_act_shield_wall"})}, "戒指"),
        ({"head": _custom(*five)}, "詞條最多 4 條"),
        ({"head": _custom()}, "至少要掛 1 條詞條"),
        ({"head": _custom({"affix": "affix_rule_fire_mends"})}, "傳說"),
        (
            {
                "feet": _custom({"affix": "affix_cost_swift"}, name="甲"),
                "body": _custom({"affix": "affix_cost_blood"}, name="乙"),
                "neck": _custom({"affix": "affix_cost_glass"}, name="丙"),
            },
            "代價型詞條全身最多 2 條",
        ),
        (
            {
                "main_hand": {"item_id": "item_test_hammer"},
                "off_hand": {"item_id": "item_test_shield"},
            },
            "副手被占用",
        ),
        (
            {
                "ring_1": {"item_id": "item_test_ring_str"},
                "ring_2": {"item_id": "item_test_ring_str"},
            },
            "同一枚戒指",
        ),
        ({"head": {"item_id": "item_test_boots"}}, "只能放"),
        ({"head": {"item_id": "item_not_there"}}, "未知的物品"),
    ]
    for equipment, expected in cases:
        body = _check(client, equipment)
        assert body["legal"] is False and body["hero"] is None, (equipment, body)
        assert any(expected in p for p in body["problems"]), (expected, body["problems"])
        assert not any("custom_" in p for p in body["problems"]), body["problems"]


def test_choice_needs_exactly_one_source(client: TestClient) -> None:
    both = {"head": {"item_id": "item_test_helm", "custom": {"name_zh": "x"}}}
    res = client.post("/api/gear/check", json={"hero_build": BUILD, "equipment": both})
    assert res.status_code == 422


def test_battle_creation_applies_equipment_to_the_hero(client: TestClient) -> None:
    body = {
        "map_id": "training_range",
        "seed": 3,
        "hero_build": BUILD,
        "ally_builds": [],
        "equipment": {
            "head": {"item_id": "item_test_helm"},
            "neck": _custom({"affix": "affix_max_hp", "value": 16}, name="健壯項鍊"),
        },
    }
    res = client.post("/api/battles", json=body)
    assert res.status_code == 201, res.text
    data = res.json()
    hero = next(u for u in data["initial_view"]["units"] if u["id"] == data["hero_id"])
    assert [e["slot"] for e in hero["equipment"]] == ["head", "neck"]
    assert hero["equipment"][1]["name_zh"] == "健壯項鍊"
    assert any(t["key"] == "max_hp" for t in hero["gear_totals"])
    # 快照內嵌在戰鬥設定，所以紀錄可以重播
    setup = store_of(client).get(data["battle_id"]).setup
    assert setup.units[0].equipment.item_in("neck") is not None


def test_battle_creation_rejects_illegal_equipment_with_reasons(client: TestClient) -> None:
    body = {
        "map_id": "training_range",
        "seed": 3,
        "hero_build": BUILD,
        "equipment": {"head": _custom({"affix": "affix_attr_str", "value": 9}, name="壞帽")},
    }
    res = client.post("/api/battles", json=body)
    assert res.status_code == 422
    assert "超出範圍" in res.json()["detail"] and "壞帽" in res.json()["detail"]


def test_main_hand_weapon_item_swaps_the_hero_weapon(client: TestClient) -> None:
    sword = _check(client, {"main_hand": {"item_id": "item_test_sword"}})
    assert sword["legal"] is True, sword
    assert sword["hero"]["weapon_id"] == "one_handed_sword"
    bow = _check(client, {"main_hand": {"item_id": "item_test_bow"}})
    assert bow["legal"] is False
    assert any("主手換成" in p for p in bow["problems"])


def test_custom_gear_battle_log_replays(client: TestClient, tmp_path: Path) -> None:
    glass = {"affix": "affix_cost_glass"}
    body = {
        "map_id": "training_range",
        "seed": 11,
        "hero_build": BUILD,
        "ally_builds": [],
        "equipment": {
            "main_hand": _custom(
                glass, {"affix": "affix_attr_str", "value": 3}, weapon="one_handed_sword"
            ),
            "neck": _custom({"affix": "affix_max_hp", "value": 12}, name="健壯項鍊"),
        },
    }
    created = client.post("/api/battles", json=body)
    assert created.status_code == 201, created.text
    battle_id = created.json()["battle_id"]
    end = client.post(
        f"/api/battles/{battle_id}/actions",
        json={"type": "end_turn", "unit_id": created.json()["hero_id"]},
    )
    assert end.status_code == 200, end.text
    log_text = client.get(f"/api/battles/{battle_id}/log").text
    log = BattleLog.model_validate_json(log_text)
    assert log.setup.units[0].equipment.item_in("neck") is not None  # 快照內嵌，重播不讀資料檔
    path = tmp_path / "gear.json"
    path.write_text(log_text, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()
