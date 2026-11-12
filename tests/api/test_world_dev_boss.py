"""開發用 Boss 戰入口（Phase 6F-3）：``POST /api/world/characters/{id}/dev-boss``。

- 開發模式＋``TRPG_DEV_ROUTES=1``：雲頂觀的霧鎖真人直接開打（正式的 Boss 陣容與地圖）。
- 不碰世界：角色存檔、世界日誌、進行中的戰鬥都不變（主線限制照舊）。
- 沒設環境變數 404；開發模式關時不掛載。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON
from trpg.api.app import create_app
from trpg.api.world import SEASON_ID, WorldStore
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings
from trpg.world.save import dumps_world, write_atomic
from trpg.world.state import WorldState

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}
CHARGE_SEASON_SEED = 20261104
CHARGE_CHARACTER_ID = "c_0000b055"
"""``ai_until=charge`` 測試用的世界種子與角色 ID（這一組等得到 Boss 蓄力、畫面也看得到）。"""
CHARGE_PARTY = ("merc_tiebi", "merc_huichun")
"""挑上面那組種子時的隊伍（OB-7 前新角色的預設：賽倫＋回春）。"""


def _client(library: ContentLibrary, saves: Path, *, dev_mode: bool) -> TestClient:
    settings = AccountSettings(dev_mode=dev_mode)
    app = create_app(library, save_dir=saves, accounts=settings)
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON  # 遭遇陣容照時間抽：固定時鐘，ai_until 才每次都等得到 Boss 蓄力
    return TestClient(app)


@pytest.fixture
def dev(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(library, tmp_path / "saves", dev_mode=True) as c:
        yield c


def _create(client: TestClient) -> dict[str, Any]:
    reply = client.post("/api/world/characters", json=START)
    assert reply.status_code == 201, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _names(battle: dict[str, Any]) -> list[str]:
    return [str(u.get("name_zh", "")) for u in battle["view"]["units"]]


def test_dev_boss_opens_the_real_boss_fight_without_touching_the_world(
    dev: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    before = dev.get(f"/api/world/characters/{cid}").json()
    log = tmp_path / "saves" / "world" / "log.jsonl"
    log_before = log.read_text(encoding="utf-8") if log.exists() else ""
    reply = dev.post(f"/api/world/characters/{cid}/dev-boss", params={"level": 6})
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert data["title_zh"] == "開發：雲頂觀"
    assert any("霧鎖真人" in n for n in _names(data["battle"]))
    # 世界不變：日誌、角色的地點與遭遇
    after = dev.get(f"/api/world/characters/{cid}").json()
    assert (log.read_text(encoding="utf-8") if log.exists() else "") == log_before
    assert after["character"] == before["character"]
    assert [loc["id"] for loc in after["map"]["locations"] if loc["current"]] == [
        loc["id"] for loc in before["map"]["locations"] if loc["current"]
    ]
    assert after["encounter"] is None
    # 這場戰鬥照一般的 /api/battles 操作
    bid = data["battle"]["battle_id"]
    assert dev.get(f"/api/battles/{bid}").status_code == 200
    json.dumps(data)  # 可序列化


def test_dev_boss_needs_the_env_flag(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRPG_DEV_ROUTES", raising=False)
    cid = _create(dev)["character"]["character_id"]
    assert dev.post(f"/api/world/characters/{cid}/dev-boss").status_code == 404


def test_dev_boss_is_not_mounted_outside_dev_mode(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    with _client(library, tmp_path / "saves", dev_mode=False) as locked:
        reply = locked.post("/api/world/characters/c1/dev-boss")
        assert reply.status_code in (401, 403, 404, 405)
        assert reply.status_code != 200


def test_dev_boss_rejects_towns(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    reply = dev.post(
        f"/api/world/characters/{cid}/dev-boss",
        params={"location": "mist_ferry", "region": "cloud_ridge"},
    )
    assert reply.status_code in (409, 422), reply.text


def test_dev_boss_rehearses_to_the_boss_charge(
    dev: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ai_until=charge``：AI 代打到 Boss 蓄力中、輪到主角（截圖 Boss 大招用）；還是不碰世界。"""
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    # 這場戰鬥的陣容與亂數照「世界種子＋角色 ID」算，兩個在 API 層都刻意每次隨機
    # （``secrets``）：約一半的組合 AI 代打到結束都等不到蓄力（端點回 422），另有約 5% 停下時
    # 霧鎖真人正隱蔽著、主角不相鄰，畫面照 #144 藏起狀態（``hidden_info``），看不到蓄力。
    # 所以兩個都固定成一組等得到、也看得到蓄力的值，每次走同一場。
    store = dev.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    world = WorldState(season_id=SEASON_ID, season_seed=CHARGE_SEASON_SEED, season_start=NOON)
    write_atomic(tmp_path / "saves" / "world" / "world.json", dumps_world(world))
    monkeypatch.setattr(store, "_new_id", lambda: CHARGE_CHARACTER_ID)
    cid = _create(dev)["character"]["character_id"]
    assert cid == CHARGE_CHARACTER_ID
    assert store.world().season_seed == CHARGE_SEASON_SEED
    # OB-7（#154）：新角色的預設隊伍改成只帶賽倫；這組種子是在「賽倫＋回春」下挑的，雇回原本的隊伍
    hired = dev.post(
        f"/api/world/characters/{cid}/actions",
        json={"kind": "hire", "mercenaries": list(CHARGE_PARTY)},
    )
    assert hired.status_code == 200, hired.text
    reply = dev.post(
        f"/api/world/characters/{cid}/dev-boss", params={"level": 8, "ai_until": "charge"}
    )
    assert reply.status_code == 200, reply.text
    battle = reply.json()["battle"]
    assert battle["awaiting"] == "action"
    boss = next(u for u in battle["view"]["units"] if "霧鎖真人" in u["name_zh"])
    assert "charging" in [s.get("status_id") for s in boss["statuses"]]
    assert dev.get(f"/api/world/characters/{cid}").json()["encounter"] is None


# ---- QK-9b：開場朝向、開場召喚物／形態、傳送到某區城鎮（都只在開發模式＋TRPG_DEV_ROUTES=1）----

FIELD = {"location": "north_slope", "region": "cloud_ridge"}


def _hero(battle: dict[str, Any]) -> dict[str, Any]:
    allies = [u for u in battle["view"]["units"] if u["team"] == "ally" and not u.get("owner_id")]
    return min(allies, key=lambda u: str(u["id"]))


@pytest.mark.parametrize("facing", ["north", "east", "south", "west"])
def test_dev_boss_opening_facing(
    dev: TestClient, monkeypatch: pytest.MonkeyPatch, facing: str
) -> None:
    """``facing``：照指定朝向排起始位置，主角開場就面向那邊、第一個敵人在那個方向；不碰世界。"""
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    before = dev.get(f"/api/world/characters/{cid}").json()["character"]
    reply = dev.post(f"/api/world/characters/{cid}/dev-boss", params={**FIELD, "facing": facing})
    assert reply.status_code == 200, reply.text
    battle = reply.json()["battle"]
    hero = _hero(battle)
    assert hero["facing"] == facing
    dx, dy = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}[facing]
    hx, hy = hero["pos"]["x"], hero["pos"]["y"]
    foes = [
        (u["pos"]["x"] - hx, u["pos"]["y"] - hy)
        for u in battle["view"]["units"]
        if u["team"] == "enemy"
    ]
    assert foes and all(x * dx + y * dy > 0 for x, y in foes)  # 敵人全在那一側
    assert dev.get(f"/api/world/characters/{cid}").json()["character"] == before


def _summoner(dev: TestClient, keywords: list[str], weapon: str, opening: str) -> dict[str, Any]:
    """起始技能照種子從關鍵字池抽：換種子直到抽到做得到的技能（端點本身回 422）。"""
    for seed in range(12):
        body = {**START, "weapon": weapon, "keywords": keywords, "seed": seed}
        cid = dev.post("/api/world/characters", json=body).json()["character"]["character_id"]
        reply = dev.post(
            f"/api/world/characters/{cid}/dev-boss",
            params={**FIELD, "opening": opening, "facing": "east"},
        )
        if reply.status_code == 200:
            data: dict[str, Any] = reply.json()
            return data
        assert reply.status_code in (409, 422), reply.text
    raise AssertionError(f"12 個種子都做不到 {opening}")


def test_dev_boss_opening_summon(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    battle = _summoner(dev, ["summon", "ignite"], "totem_staff", "summon")["battle"]
    assert battle["awaiting"] == "action"
    hero = _hero(battle)
    assert any(u.get("owner_id") == hero["id"] for u in battle["view"]["units"]), hero
    assert battle["view"]["active_unit"] == hero["id"]


def test_dev_boss_opening_form(dev: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    battle = _summoner(dev, ["form", "prone"], "one_handed_sword", "form")["battle"]
    hero = _hero(battle)
    assert hero.get("form") is not None
    assert battle["view"]["active_unit"] == hero["id"]


def test_dev_boss_opening_rejects_both_modes(
    dev: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    reply = dev.post(
        f"/api/world/characters/{cid}/dev-boss",
        params={**FIELD, "opening": "summon", "ai_until": "last"},
    )
    assert reply.status_code in (409, 422)
    # 火焰法杖＋點燃、標記：沒有召喚技，回 422（不開戰）
    reply = dev.post(f"/api/world/characters/{cid}/dev-boss", params={**FIELD, "opening": "summon"})
    assert reply.status_code in (409, 422)


def test_dev_teleport_moves_to_the_region_town(
    dev: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``dev-teleport``：直接搬到灰燼荒原的城鎮（主線還沒開也可以）；正式的傳送照舊不行。"""
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    cid = _create(dev)["character"]["character_id"]
    real = dev.post(
        f"/api/world/characters/{cid}/actions", json={"kind": "teleport", "region": "ashen_waste"}
    )
    assert real.status_code in (409, 422), real.text  # 正式遊戲：主線限制照舊
    assert "ashen_waste" in real.text or "傳送" in real.text or "去過" in real.text
    reply = dev.post(f"/api/world/characters/{cid}/dev-teleport", params={"region": "ashen_waste"})
    assert reply.status_code == 200, reply.text
    view = reply.json()
    assert view["map"]["region"] == "ashen_waste" or view["character"]["region"] == "ashen_waste"
    store = dev.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    char = store.character(cid)
    assert char.region == "ashen_waste"
    assert char.location == store.library.world_maps["ashen_waste"].town
    bad = dev.post(f"/api/world/characters/{cid}/dev-teleport", params={"region": "nowhere"})
    assert bad.status_code in (404, 409, 422)


def test_dev_teleport_needs_flag_and_dev_mode(
    dev: TestClient, library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TRPG_DEV_ROUTES", raising=False)
    cid = _create(dev)["character"]["character_id"]
    assert (
        dev.post(
            f"/api/world/characters/{cid}/dev-teleport", params={"region": "ashen_waste"}
        ).status_code
        == 404
    )
    monkeypatch.setenv("TRPG_DEV_ROUTES", "1")
    with _client(library, tmp_path / "locked", dev_mode=False) as locked:
        reply = locked.post(
            "/api/world/characters/c1/dev-teleport", params={"region": "ashen_waste"}
        )
        assert reply.status_code in (401, 403, 404, 405)
        paths = {getattr(r, "path", "") for r in locked.app.routes}  # type: ignore[attr-defined]
        assert not any("dev-teleport" in p or "dev-boss" in p for p in paths)
