"""``/api/world`` 的成長動作與顯示（Phase 5A-7；``docs/phases/Phase5計畫.md`` 13.2、13.5）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.test_world_api import FixedClock, _act, _create, _finish_battle, _ok
from tests.world.helpers import NOON, with_rules
from tests.world.test_oath import SAMPLE
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.content.library import ContentLibrary
from trpg.skillgen.flash_state import acquire
from trpg.world.save import dumps_world, write_atomic
from trpg.world.state import NextBattleMod, WorldState

SEASON_SEED = 20261103


@pytest.fixture(scope="module")
def calm(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 0, "per_level_permille": 0})


@pytest.fixture(scope="module")
def ambush(library: ContentLibrary) -> ContentLibrary:
    return with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})


@pytest.fixture(scope="module")
def sworn(calm: ContentLibrary) -> ContentLibrary:
    return dataclasses.replace(calm, world_oaths=SAMPLE)


def _client(library: ContentLibrary, saves: Path) -> TestClient:
    app = create_app(library, save_dir=saves)
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = FixedClock()
    # 固定賽季種子，讓這個檔案的結果確定
    world = WorldState(season_id="s1", season_seed=SEASON_SEED, season_start=NOON)
    write_atomic(saves / "world" / "world.json", dumps_world(world))
    return TestClient(app)


def _store(client: TestClient) -> WorldStore:
    store = client.app.state.world  # type: ignore[attr-defined]
    assert isinstance(store, WorldStore)
    return store


def _patch(client: TestClient, cid: str, **fields: Any) -> None:
    """測試用：直接改角色快照（略過要打很多場才拿得到的狀態）。"""
    store = _store(client)
    with store.lock:
        char = store.character(cid).model_copy(update=fields)
        store._save_char(char)


def _used(client: TestClient, cid: str, insight: int = 4) -> str:
    """把第一招標成「先上場用過」並給靈感點，回傳技能 ID。"""
    skill: str = _store(client).character(cid).hero.skills[0]
    _patch(
        client,
        cid,
        flash={skill: acquire(skill).model_copy(update={"used": True})},
        insight=insight,
    )
    return skill


@pytest.fixture
def calm_client(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(calm, tmp_path / "saves") as c:
        yield c


@pytest.fixture
def oath_client(sworn: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    with _client(sworn, tmp_path / "saves") as c:
        yield c


@pytest.fixture
def no_oath_client(calm: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    """沒有 ``world/oaths.yaml`` 的內容庫（5C-3 起內容資料夾有誓約模板）。"""
    with _client(dataclasses.replace(calm, world_oaths=None), tmp_path / "saves") as c:
        yield c


def _post(client: TestClient, cid: str, **action: Any) -> Any:
    return client.post(f"/api/world/characters/{cid}/actions", json=action)


# ---------------------------------------------------------------------------
# 打贏一場：經驗、升級、靈感、最近一次戰鬥
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def won(ambush: ContentLibrary, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """打贏一場的角色（換種子直到打贏；賽季種子固定所以結果確定）。"""
    saves = tmp_path_factory.mktemp("won") / "saves"
    assert ambush.world_rules is not None
    first_xp = ambush.world_rules.hero_growth.level_thresholds[0]
    with _client(ambush, saves) as client:
        for seed in range(8):
            cid = _create(client, seed=seed)["character"]["character_id"]
            _patch(client, cid, xp=first_xp - 1)  # 差 1 點升 2 級
            # 5C-2 起雇 0 名＝獨行
            _act(client, cid, kind="hire", mercenaries=["merc_tiebi", "merc_huichun"])
            _act(client, cid, kind="travel", to="ferry_steps")
            opened = _ok(client.post(f"/api/world/characters/{cid}/battle"))
            _finish_battle(client, opened["battle"], ambush)
            first = _ok(client.get(f"/api/world/characters/{cid}"))
            if any("打贏" in e for e in first["events"]):
                again = _ok(client.get(f"/api/world/characters/{cid}"))
                return {"first": first, "again": again, "first_xp": first_xp}
    raise AssertionError("8 個角色都沒打贏")  # pragma: no cover


def test_win_writes_back_xp_level_and_last_battle(won: dict[str, Any]) -> None:
    first, again = won["first"], won["again"]
    char = first["character"]
    assert char["xp"] == won["first_xp"] - 1 + 100 and char["level"] == 2
    assert char["attribute_points"] == 2 and char["insight"] == 2
    assert first["growth"]["insight"] == 2
    assert first["hero"]["insight"] == 2
    assert any(e.startswith("升到 2 級") and "靈感點 2" in e for e in first["events"])
    line = first["last_battle_zh"]
    assert line is not None and "打贏了" in line and "升到 2 級" in line
    # 重新整理：事件句子只給第一次，最近一次戰鬥還在
    assert again["events"] == []
    assert again["last_battle_zh"] == line


# ---------------------------------------------------------------------------
# 配點與重配
# ---------------------------------------------------------------------------


def test_allocate_and_respec(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    _patch(calm_client, cid, attribute_points=2)
    view = _ok(calm_client.get(f"/api/world/characters/{cid}"))
    assert view["growth"]["can_allocate"] is True
    con = view["hero"]["attributes"]["con"]
    preview = _ok(
        calm_client.post(
            f"/api/world/characters/{cid}/allocation-preview", json={"attributes": {"con": 2}}
        )
    )
    assert "最大 HP" in preview["summary_zh"]
    too_many = _post(calm_client, cid, kind="allocate", attributes={"con": 3})
    assert too_many.status_code == 422
    done = _act(calm_client, cid, kind="allocate", attributes={"con": 2})
    assert done["hero"]["attributes"]["con"] == con + 2
    assert done["character"]["attribute_points"] == 0
    assert done["character"]["max_hp"] == preview["hp"]
    assert any(e.startswith("分配屬性點：體質 ＋2") for e in done["events"])
    # 重配：野外不行、小鎮可以
    _act(calm_client, cid, kind="travel", to="ferry_steps")
    wild = _post(calm_client, cid, kind="respec")
    assert wild.status_code == 422
    assert "城鎮與營火" in wild.json()["detail"]
    _act(calm_client, cid, kind="travel", to="mist_ferry")
    back = _act(calm_client, cid, kind="respec")
    assert back["character"]["attribute_points"] == 2
    assert any(e.startswith("重配屬性") for e in back["events"])


# ---------------------------------------------------------------------------
# 閃現、待選、溶掉
# ---------------------------------------------------------------------------


def test_flash_needs_town_or_camp(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    skill = _used(calm_client, cid)
    out = _act(calm_client, cid, kind="travel", to="ferry_steps")
    assert out["growth"]["at_service"] is False
    assert out["growth"]["can_spend"] is False
    assert out["growth"]["blocked_zh"] == "這裡不是城鎮或營火"
    assert "只在城鎮與營火" in out["growth"]["service_zh"]
    reply = _post(calm_client, cid, kind="flash", skill=skill)
    assert reply.status_code == 422


def test_flash_pending_blocks_then_pick(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    skill = _used(calm_client, cid)
    view = _ok(calm_client.get(f"/api/world/characters/{cid}"))
    assert view["growth"]["can_spend"] is True
    flash = next(f for f in view["hero"]["flash"] if f["skill_id"] == skill)
    assert flash["can_flash"] is True
    preview = _ok(
        calm_client.post(
            f"/api/world/characters/{cid}/flash-preview", json={"skill": skill, "slot": None}
        )
    )
    assert preview["problem_zh"] is None and preview["nth"] == 1
    offered = _act(calm_client, cid, kind="flash", skill=skill)
    pending = offered["pending_flash"]
    assert pending is not None and pending["skill_id"] == skill and pending["options"]
    assert offered["growth"]["pending"] is True
    assert offered["growth"]["blocked_zh"] == "先選完閃現的變化"
    assert offered["character"]["insight"] == 3
    assert any("一定要選一個" in e for e in offered["events"])
    # 待選時：地點不能走、服務關閉、其他動作 422
    assert all(
        loc["blocked_zh"] == "先選完閃現的變化"
        for loc in offered["map"]["locations"]
        if loc["adjacent"]
    )
    assert offered["here"]["can_rest"] is False and offered["here"]["can_loadout"] is False
    assert _post(calm_client, cid, kind="rest").status_code == 422
    assert _post(calm_client, cid, kind="travel", to="ferry_steps").status_code == 422
    picked = _act(calm_client, cid, kind="flash_pick", pick=0)
    assert picked["pending_flash"] is None
    new_skill = picked["character"]["skills"][0]["id"]
    assert new_skill != skill
    assert any(e.startswith("選好變化") for e in picked["events"])


def test_dissolve_refunds(calm_client: TestClient) -> None:
    cid = _create(calm_client)["character"]["character_id"]
    skill = _used(calm_client, cid)
    _act(calm_client, cid, kind="flash", skill=skill)
    picked = _act(calm_client, cid, kind="flash_pick", pick=0)
    new_skill = picked["character"]["skills"][0]["id"]
    flash = next(f for f in picked["hero"]["flash"] if f["skill_id"] == new_skill)
    out = _act(calm_client, cid, kind="dissolve", skill=new_skill)
    assert out["character"]["insight"] == picked["character"]["insight"] + flash["dissolve_refund"]
    assert any(e.startswith("溶掉") for e in out["events"])


# ---------------------------------------------------------------------------
# 誓約
# ---------------------------------------------------------------------------


def test_oath_unavailable_without_templates(no_oath_client: TestClient) -> None:
    calm_client = no_oath_client
    view = _create(calm_client)
    cid = view["character"]["character_id"]
    oath = view["oath"]
    assert oath["available"] is False
    assert oath["unavailable_zh"] == "尚未開放"
    assert oath["can_swear"] is False and oath["swear_problem_zh"] == "尚未開放"
    reply = _post(
        calm_client, cid, kind="swear_oath", proposal={"template": "no_items", "params": {}}
    )
    assert reply.status_code == 422


def test_oath_swear_release_and_cooldown(oath_client: TestClient) -> None:
    view = _create(oath_client)
    cid = view["character"]["character_id"]
    assert view["oath"]["available"] is True
    assert [t["id"] for t in view["oath"]["templates"]] == [
        "no_items",
        "melee_kills",
        "one_element",
    ]
    assert view["oath"]["templates"][1]["params"][0] == {
        "id": "n",
        "kind": "int",
        "choices": [],
        "min": 1,
        "max": 2,
        "name_zh": "",
        "choice_names_zh": {},
    }
    llm = _post(
        oath_client,
        cid,
        kind="swear_oath",
        source="llm",
        proposal={"template": "no_items", "params": {}},
    )
    assert llm.status_code == 422
    bad = _post(
        oath_client, cid, kind="swear_oath", proposal={"template": "melee_kills", "params": {}}
    )
    assert bad.status_code == 422
    sworn = _act(
        oath_client,
        cid,
        kind="swear_oath",
        player_text="我絕不後退",
        proposal={"template": "one_element", "params": {"element": "fire"}},
    )
    current = sworn["oath"]["current"]
    assert current["name_zh"] == "只用某一種元素的技能造成傷害"
    assert current["difficulty_zh"] == "難" and current["params_zh"] == "element：fire"
    assert sworn["oath"]["can_swear"] is False and sworn["oath"]["can_release"] is True
    assert any(e.startswith("立誓：") for e in sworn["events"])
    released = _act(oath_client, cid, kind="release_oath")
    assert released["oath"]["current"] is None
    assert released["oath"]["cooldown_zh"] is not None
    assert released["oath"]["swear_problem_zh"] == "解除誓約後 1 天內不能再立誓"
    assert any("1 天內不能再立誓" in e for e in released["events"])


# ---------------------------------------------------------------------------
# 下一場修正與開場說明
# ---------------------------------------------------------------------------


def test_next_battle_and_opening_lines(ambush: ContentLibrary, tmp_path: Path) -> None:
    with _client(ambush, tmp_path / "saves") as client:
        cid = _create(client)["character"]["character_id"]
        mods = (
            NextBattleMod(kind="debuff", status="poison", source="test"),
            NextBattleMod(kind="reinforce", source="test"),
        )
        _patch(client, cid, next_battle=mods)
        view = _ok(client.get(f"/api/world/characters/{cid}"))
        lines = view["next_battle_zh"]
        assert len(lines) == 2
        assert "下一場開場：主角帶〔" in lines[0] and "2 回合" in lines[0]
        assert "增援 1 名" in lines[1]
        met = _act(client, cid, kind="travel", to="ferry_steps")
        encounter = met["encounter"]
        assert encounter["hero_statuses"][0]["id"] == "poison"
        assert encounter["hero_statuses"][0]["rounds"] == 2
        opening = encounter["opening_zh"]
        assert any("開場狀態" in s and "不擲抵抗" in s for s in opening)
        if encounter["reinforcements"]:
            assert any("增援" in s for s in opening)
        if encounter["first_team"] == "enemy":
            assert any(s.startswith("敵方先手") for s in opening)
