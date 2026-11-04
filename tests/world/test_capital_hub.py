"""主城地點圖是內容檔（Phase 6D-R2）：``content/world/maps/capital.yaml``（``hub: true``）放在
``library.hub_maps``、不進區域清單；所有存取經 ``world_map_of``／``location_map``，主城的遭遇、
賽季 Boss 全滅、缺席畫面都不會 ``KeyError``。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.world.helpers import NOON, make_world
from trpg.api.absence_view import absence_summary
from trpg.api.world_presenter import world_view
from trpg.content.fields import FieldMapDef, FieldSpot
from trpg.content.library import ContentLibrary, _check_stele_regions, _load_world_maps
from trpg.content.world_map import LocationMapDef
from trpg.engine.battle import begin_battle
from trpg.engine.runner import apply_step
from trpg.shared.errors import ContentError
from trpg.shared.types import Team
from trpg.world.actions import BattleEndedEvent, FightAction
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.common import capital_map, here, world_map_of
from trpg.world.encounters import reinforce_lineup, roll_lineup
from trpg.world.errors import WorldError
from trpg.world.season_board import roll_season
from trpg.world.season_events import SeasonBossAction, SeasonBossFailedEvent
from trpg.world.state import CharacterState, EncounterResult, WorldState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
DAY10 = NOON + 9 * 24 * 3600


def _in_capital(make_char: MakeChar, **updates: object) -> CharacterState:
    return make_char(region="capital", location="capital", **updates)


def test_capital_map_is_content(library: ContentLibrary, field_library: ContentLibrary) -> None:
    hub = library.hub_maps["capital"]
    assert hub.hub and "capital" not in library.world_maps
    assert world_map_of(library, "capital") is hub is capital_map(library)
    assert library.location_map("capital") is hub
    (place,) = hub.locations
    assert (place.id, place.kind) == ("capital", "town") and hub.town == "capital"
    assert place.name_zh == field_library.field_maps["capital"].name_zh  # 樞島
    assert world_map_of(library, "cloud_ridge") is library.world_maps["cloud_ridge"]
    with pytest.raises(WorldError):
        world_map_of(library, "nowhere")


def test_hub_validation() -> None:
    town = {"id": "capital", "name_zh": "樞島", "kind": "town", "pos": {"x": 50, "y": 50}}
    base = {"region": "capital", "name_zh": "主城", "level_min": 1, "level_max": 1}
    ok = LocationMapDef.model_validate(
        {**base, "hub": True, "town": "capital", "locations": [town], "edges": []}
    )
    assert ok.hub
    extra = {**town, "id": "plaza"}
    with pytest.raises(ValidationError, match="樞紐"):
        LocationMapDef.model_validate(
            {
                **base,
                "hub": True,
                "town": "capital",
                "locations": [
                    town,
                    {**extra, "kind": "camp", "level_min": 1, "battle_maps": ["x"]},
                ],
                "edges": [["capital", "plaza"]],
            }
        )


def test_capital_file_must_be_hub(library: ContentLibrary, tmp_path: Path) -> None:
    source = Path("content/world/maps/capital.yaml").read_text(encoding="utf-8")
    (tmp_path / "capital.yaml").write_text(
        source.replace("hub: true", "hub: false"), encoding="utf-8"
    )
    with pytest.raises(ContentError, match="hub"):
        _load_world_maps(tmp_path, library.regions, library.maps, [])
    (tmp_path / "capital.yaml").write_text(source, encoding="utf-8")
    regional, hubs = _load_world_maps(tmp_path, library.regions, library.maps, [])
    assert regional == {} and set(hubs) == {"capital"}


def test_capital_encounter_has_no_key_error(library: ContentLibrary, make_char: MakeChar) -> None:
    """主城沒有遭遇表：抽陣容是 ``WorldError``（不是 ``KeyError``），增援原樣。"""
    char = _in_capital(make_char)
    assert here(library, char).kind == "town"
    encounter = EncounterResult(
        region="capital",
        location="capital",
        level=1,
        battle_map="rift_gate",
        battle_seed=1,
        weather="clear",
        day_phase="day",
        at=NOON,
    )
    with pytest.raises(WorldError):
        roll_lineup(library, encounter)


def _losing(library: ContentLibrary, world: WorldState, char: CharacterState) -> CharacterState:
    """主城挑戰賽季 Boss、一定打輸的角色（10 級、1 HP、沒有傭兵）。"""
    step = world_step(library, world, char, SeasonBossAction(), DAY10, actor="acc")
    assert step.char.pending_encounter is not None
    prepared = prepare_battle(library, step.char)
    state = begin_battle(prepared.setup, prepared.seed).state
    for s in auto_steps(library, step.char):
        state = apply_step(state, s).state
    assert state.winner is not Team.ALLY
    return step.char


def test_season_boss_wipe_in_capital(library: ContentLibrary, make_char: MakeChar) -> None:
    """在主城挑戰賽季 Boss 全滅：留在主城（6D-5 待決 4），畫面照常組得出來。"""
    world = make_world()
    char = _in_capital(make_char, level=10, hp=1, seal_key_sources=("summit_boss",))
    challenged = _losing(library, world, char)
    encounter = challenged.pending_encounter
    assert encounter is not None and (encounter.region, encounter.location) == ("capital",) * 2
    assert reinforce_lineup(library, encounter, prepare_battle(library, challenged).lineup, 2)
    view = world_view(library, world, challenged, DAY10)
    assert view is not None
    steps = auto_steps(library, challenged)
    done = world_step(library, world, challenged, FightAction(steps=steps), DAY10 + 60, actor="acc")
    assert any(isinstance(e, SeasonBossFailedEvent) for e in done.events)
    assert any(isinstance(e, BattleEndedEvent) for e in done.events)
    after = done.char
    assert after.pending_encounter is None
    assert (after.region, after.location) == ("capital", "capital")
    assert world_view(library, done.world, after, DAY10 + 120) is not None


def test_absence_view_in_capital(library: ContentLibrary, make_char: MakeChar) -> None:
    """缺席畫面（含「某地開放了」）在主城照常組得出來；主城不在區域清單裡。"""
    world, _ = roll_season(library, make_world(), NOON)
    world, _ = roll_season(library, world, NOON + 4 * 24 * 3600)  # 霧潮入侵失敗：渡口開放
    char = _in_capital(make_char, news_seen_at=NOON)
    view = absence_summary(library, world, char, NOON + 4 * 24 * 3600)
    assert "opened" in [i.kind for i in view.items]


def test_panel_and_stele_validation(field_library: ContentLibrary, tmp_path: Path) -> None:
    """panel／stele_region：只能填一個、use 必須是 note、只有主城可用、區域要存在。"""
    with pytest.raises(ValidationError, match="只能填一個"):
        FieldSpot(at=(1, 1), id="x", panel="board", stele_region="cloud_ridge")
    with pytest.raises(ValidationError, match="use 必須是 note"):
        FieldSpot(at=(1, 1), id="x", panel="board", use="event")
    with pytest.raises(ValidationError):
        FieldSpot.model_validate({"at": (1, 1), "id": "x", "panel": "nowhere"})
    ridge = field_library.field_maps["mist_ferry"]
    data = ridge.model_dump(mode="json")
    data["situation_objects"] = [{"at": list(ridge.entry), "id": "x", "panel": "board"}]
    with pytest.raises(ValidationError, match="只有主城可以用"):
        FieldMapDef.model_validate(data)
    capital = field_library.field_maps["capital"]
    bad = capital.model_copy(
        update={"situation_objects": (FieldSpot(at=(1, 1), id="x", stele_region="atlantis"),)}
    )
    with pytest.raises(ContentError, match="atlantis"):
        _check_stele_regions(tmp_path, {"capital": bad}, field_library.regions)
    _check_stele_regions(tmp_path, field_library.field_maps, field_library.regions)
