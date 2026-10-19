"""高變異、超載與縮放（Phase 3D-7b）在網頁 API：預覽附上傷害範圍與暴擊率，技能卡片描述爆骰、
暴擊範圍、縮放與超載。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.api.test_gamble_api import BODY, _post, _skill

WILD = "skill_wild_blade"
RAGE = "skill_berserker_rage"


def _to_turn(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/battles", json=BODY)
    assert reply.status_code == 201, reply.text
    battle: dict[str, Any] = reply.json()
    foes = [(u["pos"]["x"], u["pos"]["y"]) for u in battle["view"]["units"] if u["team"] == "enemy"]

    def gap(action: dict[str, Any]) -> int:
        end = action["path"][-1]
        return int(min(abs(end["x"] - x) + abs(end["y"] - y) for x, y in foes))

    moves = [a for a in battle["legal_actions"] if a["type"] == "move"]
    battle = _post(client, battle["battle_id"], "actions", min(moves, key=gap))
    assert _skill(battle, WILD) and _skill(battle, RAGE)
    return battle


def test_the_preview_shows_the_damage_range_and_the_wider_crit_chance(client: TestClient) -> None:
    battle = _to_turn(client)
    wild = _post(client, battle["battle_id"], "preview", _skill(battle, WILD)[0])
    rage = _post(client, battle["battle_id"], "preview", _skill(battle, RAGE)[0])
    wild_target, rage_target = wild["targets"][0], rage["targets"][0]
    assert wild_target["crit_permille"] > rage_target["crit_permille"]  # 暴擊範圍 17–20
    damage = wild_target["damage"]
    assert damage["maximum"] > damage["minimum"] >= 1  # 爆骰讓最大值遠高於一般
    assert rage_target["damage"]["maximum"] >= rage_target["damage"]["minimum"]


def test_skill_cards_describe_the_new_mechanics(client: TestClient) -> None:
    wild = client.get(f"/api/skills/{WILD}").json()
    assert "爆骰" in wild["effects"][0] and "暴擊範圍 17–20" in wild["effects"][0]
    rage = client.get(f"/api/skills/{RAGE}").json()
    assert "你每少 10% 最大 HP，傷害 +8%（最多 +80%）" in rage["effects"][0]
    sniper = client.get("/api/skills/skill_sniper_shot").json()
    assert "與目標每距 1 格，傷害 +8%（最多 +40%）" in sniper["effects"][0]
    surge = client.get("/api/skills/skill_overcurrent").json()
    assert "超載" in surge["effects"][1] and "累積到 5 層時" in surge["effects"][1]
