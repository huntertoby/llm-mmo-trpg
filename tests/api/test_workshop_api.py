"""技能工坊 API 與「裝上試玩」（Phase 3F-1 驗收 1–6）。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import store_of
from tests.skillgen.workshop_walks import DISPLACE, STRIKE, walk_draft
from trpg.cli.battle import cmd_replay
from trpg.engine.runner import BattleLog
from trpg.shared.types import Team
from trpg.skillgen.draft import build_skill
from trpg.skillgen.skill_yaml import skill_from_yaml

CHARGE = walk_draft(DISPLACE)
"""衝鋒＋傷害＋擊退（武器技，近戰；3F-2 驗收的例子）。"""


def test_options_endpoint_walks_the_steps(client: TestClient) -> None:
    empty = client.post("/api/workshop/options", json={"skill": {}}).json()
    assert empty["next_step"] == "skeleton"
    skeletons = [c["value"] for c in empty["steps"][0]["fields"][0]["choices"]]
    assert "strike" in skeletons and "displace" in skeletons
    partial = {k: v for k, v in CHARGE.items() if k not in ("effects", "cost", "rarity")}
    body = client.post("/api/workshop/options", json={"skill": partial}).json()
    assert body["next_step"] == "effects"
    effects = body["steps"][-1]
    assert effects["name_zh"] == "效果"
    choices = {c["value"]: c for c in effects["fields"][0]["choices"]}
    assert {"dash", "damage", "push"} <= set(choices)
    push = {p["field"]: p for p in choices["push"]["params"]}
    assert (push["distance"]["min"], push["distance"]["max"]) == (1, 2)
    assert choices["push"]["name_zh"] == "推擊" and choices["push"]["description_zh"]


def test_check_endpoint_returns_budget_rarity_and_card(client: TestClient) -> None:
    body = client.post("/api/workshop/check", json={"skill": CHARGE}).json()
    assert body["legal"] is True and body["problems"] == []
    assert body["budget"]["verdict"] == "ok"
    assert body["budget"]["ratio_text"].endswith("%")
    assert body["minimum_rarity"] == "rare"
    assert body["card"]["name_zh"] == "衝鋒擊退"
    assert body["card"]["effect_ids"] == ["dash", "damage", "push"]
    bad = client.post("/api/workshop/check", json={"skill": {**CHARGE, "rarity": "common"}}).json()
    assert bad["legal"] is False
    assert any(p["rule"] == "rarity.primitive" for p in bad["problems"])


def test_check_endpoint_returns_an_icon_even_for_partial_drafts(client: TestClient) -> None:
    full = client.post("/api/workshop/check", json={"skill": CHARGE}).json()
    assert full["icon"]["partial"] is False
    assert full["icon"] == full["card"]["icon"]
    assert [e["type"] for e in full["icon"]["segments"][0]["effects"]] == ["dash", "damage", "push"]
    empty = client.post("/api/workshop/check", json={"skill": {}}).json()
    assert empty["card"] is None and empty["icon"]["partial"] is True
    assert empty["icon"]["segments"][0]["shape_id"] is None
    half = {k: v for k, v in CHARGE.items() if k in ("skeleton", "shape")}
    icon = client.post("/api/workshop/check", json={"skill": half}).json()["icon"]
    assert icon["partial"] is True and icon["segments"][0]["shape_id"] == "single"


def test_random_endpoint_is_deterministic_and_legal(client: TestClient) -> None:
    request = {"seed": 42, "tier": 2, "skeleton": "strike"}
    first = client.post("/api/workshop/random", json=request).json()
    second = client.post("/api/workshop/random", json=request).json()
    assert first == second
    assert first["skill"]["skeleton"] == "strike" and first["skill"]["tier"] == 2
    assert first["check"]["legal"] is True
    again = client.post("/api/workshop/check", json={"skill": first["skill"]}).json()
    assert again["legal"] is True
    other = client.post("/api/workshop/random", json={"seed": 43}).json()
    assert other["skill"] != first["skill"]
    bad = client.post("/api/workshop/random", json={"seed": 1, "skeleton": "nope"})
    assert bad.status_code == 422


def test_export_yaml_reloads_as_the_same_skill(client: TestClient) -> None:
    body = client.post("/api/workshop/export", json={"skill": STRIKE_DRAFT}).json()
    assert body["legal"] is True and body["problems"] == []
    skill = skill_from_yaml(body["yaml"])
    assert body["filename"] == f"{skill.id}.yaml"
    assert skill.provenance.origin == "workshop"
    original = build_skill(STRIKE_DRAFT)
    assert skill == original.model_copy(
        update={"provenance": original.provenance.model_copy(update={"origin": "workshop"})}
    )
    broken = client.post("/api/workshop/export", json={"skill": {"skeleton": "strike"}})
    assert broken.status_code == 422


STRIKE_DRAFT = walk_draft(STRIKE)


def test_arena_lists_the_training_range_first(client: TestClient) -> None:
    arena = client.get("/api/workshop/arena").json()
    assert arena["default_map"] == "training_range"
    assert arena["maps"][0]["id"] == "training_range" and arena["maps"][0]["name_zh"] == "靶場"
    assert [o["id"] for o in arena["opponents"]] == ["dummy", "fighting"]
    assert arena["opponents"][0]["enemies"] == ["木樁", "木樁", "木樁"]
    general = [m["id"] for m in client.get("/api/maps").json()]
    assert "training_range" not in general


def _create(client: TestClient, **extra: Any) -> Any:
    body = {
        "map_id": "training_range",
        "seed": 3,
        "hero_build": "build_charger",
        "ally_builds": [],
        **extra,
    }
    return client.post("/api/battles", json=body)


def test_try_out_a_custom_skill_cast_it_and_replay_the_log(
    client: TestClient, tmp_path: Path
) -> None:
    response = _create(client, custom_skills=[CHARGE], replace_skills=["skill_bull_rush"])
    assert response.status_code == 201, response.text
    body = response.json()
    battle_id = body["battle_id"]
    session = store_of(client).get(battle_id)
    custom_id = build_skill(CHARGE).id
    hero = session.state.units[session.hero_id]
    assert custom_id in hero.skills and "skill_bull_rush" not in hero.skills
    dummy = next(
        u
        for u in session.state.units.values()
        if u.template_id == "training_dummy" and u.xy == (6, 4)
    )
    # 先走到木樁附近（衝鋒射程 4），再對它施放自訂技能
    moves = [a for a in body["legal_actions"] if a["type"] == "move"]
    move = min(moves, key=lambda a: abs(a["path"][-1]["x"] - 6) + abs(a["path"][-1]["y"] - 4))
    body = client.post(f"/api/battles/{battle_id}/actions", json=move).json()
    cast = next(
        a
        for a in body["legal_actions"]
        if a["type"] == "use_skill" and a["skill_id"] == custom_id and a["target_id"] == dummy.id
    )
    body = client.post(f"/api/battles/{battle_id}/actions", json=cast).json()
    events = [e for step in body["steps"] for e in step["events"]]
    assert any(e["type"] == "skill_used" and e["skill_id"] == custom_id for e in events)
    assert any(e["type"] == "unit_dashed" for e in events)
    log_text = client.get(f"/api/battles/{battle_id}/log").text
    log = BattleLog.model_validate_json(log_text)
    assert custom_id in log.setup.ruleset.skills.by_id()
    path = tmp_path / "workshop.json"
    path.write_text(log_text, encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()


def test_illegal_custom_skills_are_rejected_in_chinese(client: TestClient) -> None:
    weak = {**CHARGE, "cost": {"cooldown": 6, "stamina": 40}}
    response = _create(client, custom_skills=[weak], replace_skills=["skill_bull_rush"])
    assert response.status_code == 422
    assert "不合法" in response.json()["detail"] and "過弱" in response.json()["detail"]
    broken = {**CHARGE, "effects": [{"type": "damage", "dice": "2d6"}]}
    response = _create(client, custom_skills=[broken], replace_skills=["skill_bull_rush"])
    assert response.status_code == 422
    assert "武器技的傷害骰來自武器" in response.json()["detail"]


def test_equipment_limits_are_checked(client: TestClient) -> None:
    full = _create(client, custom_skills=[CHARGE])
    assert full.status_code == 422
    assert full.json()["detail"] == "主動技能超過欄位上限：7 個（上限 6）"
    unknown = _create(client, custom_skills=[CHARGE], replace_skills=["skill_fire_bolt"])
    assert unknown.status_code == 422 and "沒有裝備要替換的技能" in unknown.json()["detail"]
    spell = {**CHARGE, "category": "spell", "weapon_req": "focus", "scaling_attr": "int"}
    spell["effects"] = [
        {"type": "dash"},
        {"type": "damage", "dice": "2d6", "element": "fire"},
        {"type": "push", "distance": 2},
    ]
    wrong_weapon = _create(client, custom_skills=[spell], replace_skills=["skill_bull_rush"])
    assert wrong_weapon.status_code == 422
    assert "需要法器" in wrong_weapon.json()["detail"]


def _enemy_templates(client: TestClient, battle_id: str) -> list[str]:
    state = store_of(client).get(battle_id).state
    return [u.template_id for u in state.units_sorted() if u.team is Team.ENEMY]


def test_training_range_opponents(client: TestClient) -> None:
    default = _create(client)
    assert default.status_code == 201
    assert _enemy_templates(client, default.json()["battle_id"]) == ["training_dummy"] * 3
    fighting = _create(client, opponents="fighting")
    templates = _enemy_templates(client, fighting.json()["battle_id"])
    assert templates == ["training_dummy"] * 3 + ["bandit", "bandit"]
    unknown = _create(client, opponents="dragon")
    assert unknown.status_code == 422 and "未知的對手" in unknown.json()["detail"]
    elsewhere = client.post(
        "/api/battles",
        json={
            "map_id": "open_plain",
            "seed": 1,
            "hero_build": "build_charger",
            "opponents": "dummy",
        },
    )
    assert elsewhere.status_code == 422 and "只有靶場" in elsewhere.json()["detail"]


TELEPORT_CONE: dict[str, Any] = {
    "skeleton": "displace",
    "name_zh": "瞬移斬",
    "kind": "active",
    "ap_cost": 2,
    "category": "weapon",
    "weapon_req": "melee",
    "scaling_attr": "str",
    "tier": 1,
    "shape": {"type": "ground_tile", "range": 4},
    "effects": [{"type": "teleport"}],
    "followup": {
        "skeleton": "area",
        "shape": {"type": "cone", "size": 2},
        "effects": [{"type": "damage", "multiplier_permille": 900}],
    },
    "cost": {"stamina": 12, "cooldown": 3},
    "rarity": "rare",
}
"""瞬移 → 錐形打擊（3F-3b 驗收 2）。"""


def test_the_workshop_builds_teleport_then_cone_through_the_api(client: TestClient) -> None:
    # 選項：位移技能出現「動作段」步驟，一步步展開
    partial = {k: v for k, v in TELEPORT_CONE.items() if k not in ("followup", "cost", "rarity")}
    body = client.post("/api/workshop/options", json={"skill": partial}).json()
    assert body["next_step"] is None or body["next_step"] == "rarity"
    step = next(s for s in body["steps"] if s["id"] == "followup")
    assert step["name_zh"] == "第二段" and step["complete"] is True  # 可省略（3F-4b 改名）
    assert [f["field"] for f in step["fields"]] == ["followup.when"]
    started = {**partial, "followup": {"skeleton": "area"}}
    body = client.post("/api/workshop/options", json={"skill": started}).json()
    assert body["next_step"] == "followup"
    assert [f["field"] for f in body["steps"][-1]["fields"]] == [
        "followup.when",  # 3F-4b：沒有 when 的舊草稿視為「位移 → 動作」
        "followup.skeleton",
        "followup.shape",
    ]
    # 檢查：兩段明細與稀有度
    check = client.post("/api/workshop/check", json={"skill": TELEPORT_CONE}).json()
    assert check["legal"] is True and check["problems"] == []
    assert [s["label"] for s in check["budget"]["segments"]] == ["位移段", "動作段"]
    assert check["budget"]["composite_tax_permille"] == 150
    assert check["card"]["followup"] and check["minimum_rarity"] == "rare"
    common = client.post(
        "/api/workshop/check", json={"skill": {**TELEPORT_CONE, "rarity": "common"}}
    ).json()
    assert common["legal"] is False


def test_try_out_teleport_then_cone_and_cast_it(client: TestClient) -> None:
    response = _create(client, custom_skills=[TELEPORT_CONE], replace_skills=["skill_decoy_swap"])
    assert response.status_code == 201, response.text
    body = response.json()
    battle_id = body["battle_id"]
    custom_id = build_skill(TELEPORT_CONE).id
    moves = [a for a in body["legal_actions"] if a["type"] == "move"]
    move = min(moves, key=lambda a: abs(a["path"][-1]["x"] - 6) + abs(a["path"][-1]["y"] - 4))
    body = client.post(f"/api/battles/{battle_id}/actions", json=move).json()
    combos = [
        a
        for a in body["legal_actions"]
        if a["type"] == "use_skill" and a["skill_id"] == custom_id and a.get("followup_target")
    ]
    assert combos
    best = max(
        combos,
        key=lambda a: len(
            client.post(f"/api/battles/{battle_id}/preview", json=a).json()["targets"]
        ),
    )
    body = client.post(f"/api/battles/{battle_id}/actions", json=best).json()
    events = [e for step in body["steps"] for e in step["events"]]
    assert any(e["type"] == "skill_followup" for e in events)
