"""遇敵卡每一名敵人的外觀與階級標記（UI-E3b）：``EncounterEnemyView.look``、``rank``。

- ``look`` 格式同實地地圖人物的 ``FieldHeroView``（範本、``doll_look``、武器、裝備外觀），照開戰時的
  範本（已套精英詞綴）與裝備。
- ``rank``：範本帶 ``boss`` 標籤＝``boss``；精英範本或套了詞綴＝``elite``；其餘 ``normal``。
- 只是顯示用欄位：不改規則、不進存檔。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON, with_rules
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.api.world_presenter import _encounter_enemy
from trpg.content.library import ContentLibrary
from trpg.engine.setup import UnitSpawn
from trpg.shared.types import Team

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


def _spawn(library: ContentLibrary, name: str, affix: str | None = None) -> UnitSpawn:
    catalog = library.enemy_catalog()
    template = catalog.template(name)
    if affix is not None:
        template = catalog.with_affix(template, affix)
    return UnitSpawn(
        template=template,
        weapon=library.weapons[template.weapon],
        equipment=library.loadout_of(template),
        team=Team.ENEMY,
    )


@pytest.mark.parametrize(
    ("name", "affix", "rank"),
    [
        ("bandit", None, "normal"),
        ("ash_hound", None, "normal"),
        ("bandit", "regenerating", "elite"),
        ("bandit_captain", None, "elite"),
        ("bandit_boss", None, "boss"),
        ("ashen_heart", None, "boss"),
    ],
)
def test_rank_marks_normal_elite_and_boss(
    library: ContentLibrary, name: str, affix: str | None, rank: str
) -> None:
    view = _encounter_enemy(library, library.enemy_catalog(), _spawn(library, name, affix), affix)
    assert view.rank == rank
    assert view.elite is (rank != "normal")


def test_look_matches_the_battle_template(library: ContentLibrary) -> None:
    spawn = _spawn(library, "bandit_boss")
    view = _encounter_enemy(library, library.enemy_catalog(), spawn, None)
    assert view.look is not None
    assert view.look.template_id == "bandit_boss"
    assert view.look.doll_look == spawn.template.doll
    assert view.look.doll_look is not None
    assert view.look.doll_look.rarity == "epic"  # 頭目外光照 doll 的 rarity
    assert view.look.weapon_id == spawn.template.weapon


def test_look_of_a_creature_keeps_creature_fields(library: ContentLibrary) -> None:
    view = _encounter_enemy(library, library.enemy_catalog(), _spawn(library, "ash_hound"), None)
    assert view.look is not None
    assert view.look.doll_look is not None
    creature = view.look.doll_look.creature
    assert creature is not None
    assert creature.body == "hound"


def test_affixed_elite_look_carries_the_affix_look(library: ContentLibrary) -> None:
    spawn = _spawn(library, "bandit", "regenerating")
    view = _encounter_enemy(library, library.enemy_catalog(), spawn, "regenerating")
    assert view.look is not None
    assert view.look.doll_look is not None
    assert "regen" in view.look.doll_look.affixes
    assert view.affix_zh == "再生的"


# ---------------------------------------------------------------------------
# API：遇敵卡的每一名都帶外觀
# ---------------------------------------------------------------------------


@pytest.fixture
def ambush_client(library: ContentLibrary, tmp_path: Path) -> Iterator[TestClient]:
    ambush = with_rules(library, encounter={"base_permille": 1000, "max_permille": 1000})
    app = create_app(ambush, save_dir=tmp_path / "saves")
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    with TestClient(app) as c:
        yield c


def test_encounter_api_sends_look_and_rank_for_every_enemy(ambush_client: TestClient) -> None:
    made = ambush_client.post("/api/world/characters", json=START)
    assert made.status_code == 201, made.text
    cid = made.json()["character"]["character_id"]
    met = ambush_client.post(
        f"/api/world/characters/{cid}/actions", json={"kind": "travel", "to": "ferry_steps"}
    )
    assert met.status_code == 200, met.text
    enemies: list[dict[str, Any]] = met.json()["encounter"]["enemies"]
    assert enemies
    for e in enemies:
        assert e["rank"] in {"normal", "elite", "boss"}
        assert (e["rank"] != "normal") is e["elite"]
        assert e["look"] is not None
        assert e["look"]["template_id"]
        assert "doll_look" in e["look"]
        assert "weapon_class" in e["look"]
    # 重新讀取（從存檔的遭遇重算畫面）得到同樣的外觀與階級：確定性、不需要另存
    char = ambush_client.get(f"/api/world/characters/{cid}").json()
    assert char["encounter"]["enemies"] == enemies
