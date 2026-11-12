"""PR-2a 的行為一致測試（``docs/phases/PhasePR-2計畫.md``「行為一致測試」A 組）。

靶場測試模式（#147）的後端接線：開局試打、正式選定畫面的試打、工坊師傅的「靶場試玩」都是測試模式
（``BattleView.practice``），其他戰鬥不是；試打不回寫世界；一角色一場、離開就刪；能不能開由
:func:`trpg.world.opening.practice_problem` 決定（畫面與端點同一個函式）。

一律實際打 API（``/api/world/...``、``/api/battles/...``）或跑引擎；世界種子與角色 ID 固定（不依賴
``secrets``，上手筆記第四節第 15 點）。
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import ClientFactory
from tests.api.test_opening_flash import _flash, _used
from tests.world.helpers import NOON, hero, make_encounter, with_rules
from tests.world.test_gear import _item
from trpg.api.app import create_app
from trpg.api.sessions import SessionStore
from trpg.api.world import SEASON_ID, WorldStore
from trpg.api.world_newcomer_view import PRACTICE_SEEN
from trpg.content.library import ContentLibrary
from trpg.engine.rewrites import ap_cap
from trpg.engine.runner import BattleLog, log_replay_problem
from trpg.engine.view import project_for
from trpg.roguelite.offers import make_offer
from trpg.server.account_config import AccountSettings
from trpg.server.accounts import AccountStore
from trpg.shared.types import Team
from trpg.world.battle import hero_spawn
from trpg.world.common import capital_name, world_map_of
from trpg.world.growth import as_run, world_library
from trpg.world.league import LeagueMatchSpec, match_setup
from trpg.world.opening import (
    PRACTICE_BUSY_ZH,
    PRACTICE_CLASS_ZH,
    PRACTICE_PICK_ZH,
    own_practice,
    practice_problem,
    practice_seed,
)
from trpg.world.save import WORLD_RULES_VERSION, dumps_char, dumps_world, write_atomic
from trpg.world.state import (
    CharacterState,
    NextBattleMod,
    OathState,
    PendingOffer,
    WorldState,
)
from trpg.world.step import new_character

pytestmark = pytest.mark.capital_spawn  # 正式的出生地：主城（#125）

SEASON_SEED = 20261112
NEW = {"name": "小靶", "seed": 7, "race": "human"}
PICK = {"weapon": "bow", "keywords": ["ignite", "charged"]}
"""開局已結束的角色（舊流程建角）：弓＋兩招關鍵字起始技能。"""
PILL = "item_hp_potion_small"


# ---------------------------------------------------------------------------
# 共用
# ---------------------------------------------------------------------------


def _fixed_ids(store: WorldStore, tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """世界種子與角色 ID 固定（建角順序決定 ID）。"""
    world = WorldState(season_id=SEASON_ID, season_seed=SEASON_SEED, season_start=NOON)
    write_atomic(tmp / "world" / "world.json", dumps_world(world))
    ids: Iterator[str] = iter(f"c_pr2a{n:04d}" for n in range(1, 100))
    monkeypatch.setattr(store, "_new_id", lambda: next(ids))
    assert store.world().season_seed == SEASON_SEED


@pytest.fixture
def client(
    field_library: ContentLibrary,
    make_client: ClientFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    made = make_client(calm, clock=lambda: NOON)
    _fixed_ids(_store(made), tmp_path / "saves", monkeypatch)
    return made


def _ok(reply: Any, status: int = 200) -> dict[str, Any]:
    assert reply.status_code == status, reply.text
    data: dict[str, Any] = reply.json()
    return data


def _store(client: TestClient) -> WorldStore:
    app: Any = client.app
    store = app.state.world
    assert isinstance(store, WorldStore)
    return store


def _view(client: TestClient, cid: str) -> dict[str, Any]:
    return _ok(client.get(f"/api/world/characters/{cid}"))


def _act(client: TestClient, cid: str, body: dict[str, Any]) -> dict[str, Any]:
    return _ok(client.post(f"/api/world/characters/{cid}/actions", json=body))


def _patch(client: TestClient, cid: str, **updates: Any) -> CharacterState:
    store = _store(client)
    char = store.character(cid).model_copy(update=updates)
    store._save_char(char)
    return char


def _pick_class(client: TestClient) -> str:
    """建角（正式流程）：停在主城工坊靶場、還在選大類。"""
    return str(
        _ok(client.post("/api/world/characters", json=NEW), 201)["character"]["character_id"]
    )


def _starter(client: TestClient) -> str:
    """選了遠程大類（入門期，人在主城）。"""
    cid = _pick_class(client)
    _act(client, cid, {"kind": "opening_class", "weapon_class": "ranged"})
    return cid


def _chosen(client: TestClient) -> str:
    """正式選定之後（4 級前；直接改階段，人在主城）。"""
    cid = _starter(client)
    opening = _store(client).character(cid).opening
    assert opening is not None
    _patch(
        client,
        cid,
        opening=opening.model_copy(
            update={"stage": "chosen", "weapon": "bow", "keywords": ("ignite", "charged")}
        ),
    )
    return cid


def _done(client: TestClient) -> str:
    """開局已結束（舊流程建角：弓＋關鍵字起始技能），人在主城。"""
    body = {**NEW, **PICK}
    return str(
        _ok(client.post("/api/world/characters", json=body), 201)["character"]["character_id"]
    )


def _snapshot(client: TestClient, cid: str) -> tuple[str, str, int, str]:
    store = _store(client)
    world_file = store.root / "world" / "world.json"
    return (
        dumps_char(store.character(cid)),
        dumps_world(store.world()),
        len(store.entries()),
        world_file.read_text(encoding="utf-8") if world_file.is_file() else "",
    )


def _send(client: TestClient, battle: dict[str, Any], kind: str) -> dict[str, Any]:
    """送第一個 ``kind`` 型的合法動作（主角的）。"""
    action = next((a for a in battle["legal_actions"] if a["type"] == kind), None)
    assert action is not None, f"沒有合法的 {kind}：{[a['type'] for a in battle['legal_actions']]}"
    return _ok(client.post(f"/api/battles/{battle['battle_id']}/actions", json=action))


FIVE = ("use_skill", "attack", "move", "use_skill", "attack")
"""放招、普攻、走路共 5 個動作（A1、A9）。"""


def _play_five(client: TestClient, battle: dict[str, Any]) -> dict[str, Any]:
    for kind in FIVE:
        battle = _send(client, battle, kind)
        assert battle["view"]["practice"] is True and battle["view"]["max_rounds"] is None
    return battle


def _open(client: TestClient, cid: str, entry: str) -> dict[str, Any]:
    if entry == "practice":
        return _ok(client.post(f"/api/world/characters/{cid}/range/practice"))
    return _ok(client.post(f"/api/world/characters/{cid}/range/trial", json={"weapon": "bow"}))


ENTRIES = {
    "pick_class_trial": (_pick_class, "trial"),
    "choice_screen_trial": (_starter, "trial"),
    "own_practice": (_done, "practice"),
}
"""三種靶場入口：選大類的 ``range/trial``、正式選定畫面（入門期）的 ``range/trial``、
工坊師傅的 ``range/practice``。"""


# ---------------------------------------------------------------------------
# A1 試打不回寫世界、A2 只有靶場是測試模式（靶場那一半）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_a1_a2_range_entries_are_sandboxed_test_mode(client: TestClient, entry: str) -> None:
    make, kind = ENTRIES[entry]
    cid = make(client)
    before = _snapshot(client, cid)
    out = _open(client, cid, kind)
    battle = out["battle"]
    assert battle["view"]["practice"] is True and battle["view"]["max_rounds"] is None
    _play_five(client, battle)
    assert _snapshot(client, cid) == before  # 角色存檔、世界快照、日誌行數、世界檔都不變
    assert _view(client, cid)["battle_id"] is None


# ---------------------------------------------------------------------------
# A2 其他戰鬥都不是測試模式
# ---------------------------------------------------------------------------


def test_a2_world_encounter_is_not_test_mode(client: TestClient) -> None:
    cid = _done(client)
    _patch(client, cid, pending_encounter=make_encounter("ferry_steps"))
    out = _ok(client.post(f"/api/world/characters/{cid}/battle"))
    view = out["battle"]["view"]
    assert view["practice"] is False
    assert view["max_rounds"] == _store(client).library.world_rules.battle.max_rounds  # type: ignore[union-attr]


def test_a2_workshop_3f_is_not_test_mode(client: TestClient) -> None:
    body = {"map_id": "training_range", "seed": 3, "hero_build": "build_charger"}
    out = _ok(client.post("/api/battles", json=body), 201)
    assert out["view"]["practice"] is False and out["view"]["max_rounds"] is not None


def test_a2_roguelite_run_battle_is_not_test_mode(client: TestClient) -> None:
    run_id = _ok(client.post("/api/runs", json={"build": "build_fire", "seed": 6}), 201)["run_id"]
    out = _ok(client.post(f"/api/runs/{run_id}/battle"))
    assert out["battle"]["view"]["practice"] is False
    assert out["battle"]["view"]["max_rounds"] is not None


def test_a2_league_match_is_not_test_mode(field_library: ContentLibrary) -> None:
    season = field_library.world_season
    assert season is not None and season.league is not None
    rules = season.league
    a = new_character(field_library, "a", hero(field_library), region="cloud_ridge")
    b = new_character(field_library, "b", hero(field_library), region="cloud_ridge")
    spawns = {
        "a": (hero_spawn(field_library, a, a.hp), ()),
        "b": (hero_spawn(field_library, b, b.hp), ()),
    }
    spec = LeagueMatchSpec(
        id="m0001", a="a", b="b", map="open_plain", seed_index=0, seed=1, ally="a"
    )
    setup = match_setup(field_library, rules, spawns, spec)
    assert setup.practice is None and setup.max_rounds == rules.max_rounds
    session, _ = SessionStore(field_library).open(setup, spec.seed)
    view = project_for(session.state, Team.ALLY)
    assert view.practice is False and view.max_rounds == rules.max_rounds


# ---------------------------------------------------------------------------
# A3 測試模式規則真的經過 API 生效
# ---------------------------------------------------------------------------


def _hero_unit(battle: dict[str, Any]) -> dict[str, Any]:
    return next(u for u in battle["view"]["units"] if u["id"] == battle["hero_id"])


def test_a3_test_mode_rules_through_the_api(client: TestClient) -> None:
    cid = _done(client)
    library = _store(client).library
    char = _store(client).character(cid)
    skills = {s.id: s for s in char.generated_skills} | dict(library.skills)
    battle = _ok(client.post(f"/api/world/characters/{cid}/range/practice"))["battle"]
    bid, hero_id = battle["battle_id"], battle["hero_id"]
    # 預覽：對木樁普攻必中
    attack = next(a for a in battle["legal_actions"] if a["type"] == "attack")
    preview = _ok(client.post(f"/api/battles/{bid}/preview", json=attack))
    assert preview["hit_permille"] == 1000
    # 放一招有冷卻的技能：冷卻歸零、HP／AP／法力為滿、自動過一輪（主角沒有 end_turn）
    cast = next(
        a
        for a in battle["legal_actions"]
        if a["type"] == "use_skill" and (skills[a["skill_id"]].cost.cooldown or 0) > 0
    )
    round_before = battle["view"]["round"]
    after = _ok(client.post(f"/api/battles/{bid}/actions", json=cast))
    me = _hero_unit(after)
    assert all(v == 0 for v in me["cooldowns"].values())
    assert me["hp"] == me["max_hp"] and me["mana"] == me["max_mana"]
    assert me["ap"] == ap_cap(library.ruleset.core)
    assert after["view"]["round"] == round_before + 1
    hero_steps = [s["step"] for s in after["steps"] if s["actor_id"] == hero_id and s["step"]]
    assert all(s["type"] != "end_turn" for s in hero_steps)
    # 普攻：再過一輪
    hit = _send(client, after, "attack")
    assert hit["view"]["round"] == round_before + 2
    assert all(s["step"]["type"] != "end_turn" for s in hit["steps"] if s["actor_id"] == hero_id)
    # 走路：不過輪
    walked = _send(client, hit, "move")
    assert walked["view"]["round"] == hit["view"]["round"]


# ---------------------------------------------------------------------------
# A4 自己的技能與裝備
# ---------------------------------------------------------------------------


def test_a4_own_skills_and_gear(client: TestClient) -> None:
    cid = _done(client)
    store = _store(client)
    library = store.library
    body = _item(library, "body")
    oath = OathState(template="oath_no_items", difficulty="easy", sworn_at=NOON)
    mods = (NextBattleMod(kind="debuff", status="poison", source="test"),)
    char = _patch(
        client,
        cid,
        equipment={"body": body},
        pouch={PILL: 2},
        oath=oath,
        next_battle=mods,
        hp=1,
        mana=0,
        stamina=0,
    )
    trial = own_practice(library, char)
    [spawn] = [u for u in trial.setup.units if u.team is Team.ALLY]
    real = hero_spawn(library, char, char.hp)  # 實戰的出場函式（不帶腰包道具）
    assert spawn.template.skills == real.template.skills
    assert spawn.equipment == real.equipment and spawn.equipment.items  # hero_loadout（含共鳴）
    assert spawn.opening_statuses == () and real.opening_statuses == ("poison",)
    assert (spawn.hp, spawn.mana, spawn.stamina) == (None, None, None)  # 給滿
    assert trial.setup.oath is None and trial.setup.practice is not None
    assert len(trial.setup.units) == 1 + len(library.world_newcomer.range.dummies)  # type: ignore[union-attr]
    assert trial.seed == practice_seed(cid) == own_practice(library, char).seed
    out = _ok(client.post(f"/api/world/characters/{cid}/range/practice"))
    names = {s.id: s.name_zh for s in char.generated_skills} | {
        k: v.name_zh for k, v in library.skills.items()
    }
    assert out["skills_zh"] == [names[s] for s in real.template.skills]
    assert out["demo"] is False and out["title_zh"] == "靶場試玩：" + library.weapons["bow"].name_zh
    me = _hero_unit(out["battle"])
    assert me["hp"] == me["max_hp"] and not me["statuses"]
    after = store.character(cid)
    assert after.next_battle == mods and after.pouch == {PILL: 2} and after.oath == oath


# ---------------------------------------------------------------------------
# A5 能不能開（畫面與端點同一個函式）
# ---------------------------------------------------------------------------


def _flashing(client: TestClient, cid: str) -> CharacterState:
    """身上有待選的閃現（用世界層的閃現產生真的選項，再搬到主城）。"""
    library = _store(client).library
    other = _used(new_character(library, "flasher", hero(library), region="cloud_ridge"))
    pending = _flash(library, other).pending_flash
    char = _store(client).character(cid)
    first = char.hero.skills[0]
    assert pending is not None
    return _patch(client, cid, pending_flash=pending.model_copy(update={"skill": first}))


def _offering(client: TestClient, cid: str) -> CharacterState:
    """身上有待選的三選一（任務給的技能三選一；組法同 ``test_opportunity_offer_view``）。"""
    library = _store(client).library
    char = _store(client).character(cid)
    offer = make_offer(world_library(library), as_run(char, seed=1), "level_up")
    pending = PendingOffer(
        quest="storm_altar", step="opportunity", offer=offer, source="opportunity"
    )
    return _patch(client, cid, pending_offers=(pending,))


def _in_battle(client: TestClient, cid: str) -> None:
    _patch(client, cid, pending_encounter=make_encounter("ferry_steps"))
    _ok(client.post(f"/api/world/characters/{cid}/battle"))


def _in_town(client: TestClient, cid: str) -> None:
    town = world_map_of(_store(client).library, "cloud_ridge").town
    _patch(client, cid, region="cloud_ridge", location=town)


CASES: dict[str, tuple[Any, Any, str | None]] = {
    "done_in_capital": (_done, None, None),
    "starter_in_capital": (_starter, None, None),
    "chosen_in_capital": (_chosen, None, None),
    "pick_class": (_pick_class, None, PRACTICE_CLASS_ZH),
    "in_misty_town": (_done, _in_town, "place"),
    "in_battle": (_done, _in_battle, PRACTICE_BUSY_ZH),
    "pending_encounter": (
        _done,
        lambda c, i: _patch(c, i, pending_encounter=make_encounter("ferry_steps")),
        PRACTICE_BUSY_ZH,
    ),
    "pending_flash": (_done, _flashing, PRACTICE_PICK_ZH),
    "pending_offer": (_done, _offering, PRACTICE_PICK_ZH),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_a5_screen_and_endpoint_agree(client: TestClient, case: str) -> None:
    make, setup, expected = CASES[case]
    cid = make(client)
    if setup is not None:
        setup(client, cid)
    library = _store(client).library
    view = _view(client, cid)
    workshop = view["workshop"]
    reply = client.post(f"/api/world/characters/{cid}/range/practice")
    in_battle = view["battle_id"] is not None
    problem = practice_problem(library, _store(client).character(cid), in_battle=in_battle)
    if expected == "place":
        assert workshop is None  # 不在主城：沒有師傅選單
        assert problem is not None and capital_name(library) in problem
        assert reply.status_code == 422 and reply.json()["detail"] == problem
        return
    assert workshop is not None
    assert workshop["practice_available"] is (expected is None) is (problem is None)
    if expected is None:
        assert reply.status_code == 200, reply.text
        assert workshop["practice_blocked_zh"] is None
    else:
        assert workshop["practice_blocked_zh"] == expected == problem
        assert reply.status_code == 422 and reply.json()["detail"] == expected


# ---------------------------------------------------------------------------
# A6 「新」小牌
# ---------------------------------------------------------------------------


def test_a6_new_badge_follows_hints_seen(client: TestClient) -> None:
    cid = _done(client)
    store = _store(client)
    first = _view(client, cid)["workshop"]
    assert first["practice_new"] is True and first["seen_id"] == PRACTICE_SEEN == "range:practice"
    lines = len(store.entries())
    seen = _act(client, cid, {"kind": "hint_seen", "ids": [first["seen_id"]]})
    assert seen["workshop"]["practice_new"] is False
    assert len(store.entries()) == lines + 1  # 既有動作，照常寫一筆日誌
    reset = _act(client, cid, {"kind": "hints_reset"})
    assert reset["workshop"]["practice_new"] is True
    assert WORLD_RULES_VERSION == 25


# ---------------------------------------------------------------------------
# A7 一角色一場
# ---------------------------------------------------------------------------


def test_a7_one_sandbox_per_character(client: TestClient) -> None:
    cid = _done(client)
    other = _done(client)
    store = _store(client)
    mine = _open(client, cid, "practice")["battle"]["battle_id"]
    theirs = _open(client, other, "practice")["battle"]["battle_id"]
    count = len(store.battles)
    second = _open(client, cid, "practice")["battle"]["battle_id"]
    assert client.get(f"/api/battles/{mine}").status_code == 404
    assert len(store.battles) == count  # 換一場不增加
    assert _ok(client.get(f"/api/battles/{second}"))["battle_id"] == second
    assert client.delete(f"/api/world/characters/{cid}/range/trial").status_code == 204
    assert client.get(f"/api/battles/{second}").status_code == 404
    assert len(store.battles) == count - 1
    assert (
        client.delete(f"/api/world/characters/{cid}/range/trial").status_code == 204
    )  # 沒有也 204
    assert _ok(client.get(f"/api/battles/{theirs}"))["battle_id"] == theirs  # 別人的不受影響


def test_a7_trial_and_practice_share_the_slot(client: TestClient) -> None:
    """開局試打（``range/trial``）和靶場試玩共用「一角色一場」。"""
    cid = _starter(client)
    trial = _open(client, cid, "trial")["battle"]["battle_id"]
    practice = _open(client, cid, "practice")["battle"]["battle_id"]
    assert client.get(f"/api/battles/{trial}").status_code == 404
    again = _open(client, cid, "trial")["battle"]["battle_id"]
    assert client.get(f"/api/battles/{practice}").status_code == 404
    assert client.delete(f"/api/world/characters/{cid}/range/trial").status_code == 204
    assert client.get(f"/api/battles/{again}").status_code == 404


def _login(client: TestClient, name: str) -> dict[str, str]:
    app: Any = client.app
    accounts = app.state.accounts
    assert isinstance(accounts, AccountStore)
    password = secrets.token_urlsafe(12)
    accounts.create(name, password)
    reply = client.post("/api/auth/login", json={"username": name, "password": password})
    assert reply.status_code == 200, reply.text
    return {"Authorization": f"Bearer {reply.json()['token']}"}


def test_a7_other_accounts_cannot_open_or_delete(
    field_library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    app = create_app(calm, save_dir=tmp_path / "saves", accounts=AccountSettings(dev_mode=False))
    with TestClient(app) as client:
        store = _store(client)
        store.clock = lambda: NOON
        _fixed_ids(store, tmp_path / "saves", monkeypatch)
        alice, bob = _login(client, "alice"), _login(client, "bob")
        cid = _ok(client.post("/api/world/characters", json={**NEW, **PICK}, headers=alice), 201)[
            "character"
        ]["character_id"]
        url = f"/api/world/characters/{cid}/range"
        battle = _ok(client.post(f"{url}/practice", headers=alice))["battle"]["battle_id"]
        assert client.post(f"{url}/practice", headers=bob).status_code == 404
        assert client.delete(f"{url}/trial", headers=bob).status_code == 404
        assert client.get(f"/api/battles/{battle}", headers=bob).status_code == 404
        assert _ok(client.get(f"/api/battles/{battle}", headers=alice))["battle_id"] == battle
        assert client.delete(f"{url}/trial", headers=alice).status_code == 204
        assert client.get(f"/api/battles/{battle}", headers=alice).status_code == 404


# ---------------------------------------------------------------------------
# A8 技能工坊（3F）不受影響
# ---------------------------------------------------------------------------


def test_a8_workshop_3f_keeps_cooldowns_and_end_turn(client: TestClient) -> None:
    library = _store(client).library
    body = {"map_id": "training_range", "seed": 3, "hero_build": "build_charger"}
    battle = _ok(client.post("/api/battles", json=body), 201)
    cast = next(
        a
        for a in battle["legal_actions"]
        if a["type"] == "use_skill" and (library.skills[a["skill_id"]].cost.cooldown or 0) > 0
    )
    after = _ok(client.post(f"/api/battles/{battle['battle_id']}/actions", json=cast))
    me = _hero_unit(after)
    assert me["cooldowns"].get(cast["skill_id"], 0) > 0
    assert after["view"]["round"] == battle["view"]["round"]  # 沒結束回合就不換輪
    assert any(a["type"] == "end_turn" for a in after["legal_actions"])


# ---------------------------------------------------------------------------
# A9 重播
# ---------------------------------------------------------------------------


def test_a9_practice_log_replays(client: TestClient, tmp_path: Path) -> None:
    cid = _done(client)
    battle = _open(client, cid, "practice")["battle"]
    _play_five(client, battle)
    session = _store(client).battles.get(battle["battle_id"])
    path = tmp_path / "practice.json"
    path.write_text(session.to_log().model_dump_json(), encoding="utf-8")
    log = BattleLog.model_validate_json(path.read_text(encoding="utf-8"))
    assert log.setup.practice is not None and len(log.actions) >= len(FIVE)
    assert log_replay_problem(log) is None
    assert json.loads(path.read_text(encoding="utf-8"))["final_state"] is not None


# ---------------------------------------------------------------------------
# A10 地名與文字
# ---------------------------------------------------------------------------


def test_a10_workshop_text_matches_the_final_strings(client: TestClient) -> None:
    cid = _done(client)
    library = _store(client).library
    workshop = _view(client, cid)["workshop"]
    capital = capital_name(library)
    assert capital == "樞島"
    assert workshop["title_zh"] == f"{capital}工坊・靶場與改造"
    assert workshop["capital_zh"] == capital
    assert workshop["line"] == {
        "speaker_zh": "工坊師傅",
        "text_zh": "木樁隨你打，打壞了我再釘。試試你現在的本事。",
    }
    assert (workshop["practice_zh"], workshop["practice_note_zh"]) == (
        "靶場試玩",
        "用你現在的技能與裝備打木樁，不耗任何資源",
    )
    assert (workshop["rework_zh"], workshop["rework_note_zh"]) == ("改造技能", "之後開放")
    assert workshop["footer_zh"] == "靶場裡技能沒有冷卻，每次出手後自動過一輪，資源立刻補滿。"
    assert workshop["speaker"]["name_zh"] == "工坊師傅" and workshop["speaker"]["portrait"]
    # 不能開的三句（定稿逐字）
    assert PRACTICE_BUSY_ZH == "先處理眼前的事，再來打木樁"
    assert PRACTICE_PICK_ZH == "先把新招選好，再來打木樁"
    assert PRACTICE_CLASS_ZH == "先在靶場選好大類，按「確定出發」"
    # 主城「靶場」物件說明卡、工坊師傅點了開選單
    spots = {s.id: s for s in library.outdoor_map("capital", "capital").situation_objects}  # type: ignore[union-attr]
    assert spots["training_range"].note_zh == "工坊靶場：找工坊師傅打木樁，試試你現在的技能與裝備。"
    assert spots["workshop_master"].panel == "workshop"
