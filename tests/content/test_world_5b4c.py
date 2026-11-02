"""5B-4c 的資料欄位與檢查（``docs/phases/Phase5計畫.md`` 21.3～21.8）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.world.helpers import make_encounter
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_enemies import ELITE_TAG
from trpg.content.world_events import SolutionDef
from trpg.world.encounters import elite_kinds, lineup_templates, roll_lineup


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


# ---------------------------------------------------------------------------
# 懸賞精英的指定詞綴（21.3）
# ---------------------------------------------------------------------------


def test_data_elite_may_take_affix_on_elite_template(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    captain = library.units["bandit_captain"]
    assert catalog.affix_problem(captain, "heart_linked") is not None  # 隨機混精英照舊不行
    assert catalog.affix_problem(captain, "heart_linked", allow_elite=True) is None
    assert catalog.applicable_affixes(captain, ("heart_linked",)) == []
    # 其他限制照舊：限近戰的詞綴不能套到弓手
    archer = library.units["sect_crane_archer"]
    assert catalog.affix_problem(archer, "berserk", allow_elite=True) is not None


def test_affix_on_elite_keeps_hp(library: ContentLibrary) -> None:
    catalog = library.enemy_catalog()
    captain = library.units["bandit_captain"]
    linked = catalog.with_affix(captain, "heart_linked")
    assert linked.id == "bandit_captain_heart_linked"
    assert linked.name_zh.startswith("連心的")
    assert linked.max_hp == captain.max_hp  # 已是精英：HP 不再乘（代決 5B4c-3）
    assert ELITE_TAG in linked.tags
    wolf = library.units["mist_wolf"]
    assert catalog.with_affix(wolf, "berserk").max_hp == wolf.max_hp * 1500 // 1000


def test_bounty_elites_in_cloud_ridge(library: ContentLibrary) -> None:
    fort = make_encounter("cliff_gang_fort", seed=3)
    risen = roll_lineup(library, fort, ("scarface_rises",))
    assert risen.members[0].unit == "bandit_captain"
    assert risen.members[0].affix == "heart_linked"  # 疤面＝連心的（18.7.4）
    assert [m.unit for m in risen.members[1:]] == ["bandit", "mist_wolf", "mist_wolf"]
    templates = lineup_templates(library, risen)
    assert templates[0].name_zh == "連心的盜賊隊長"
    assert elite_kinds(library, risen) == ("bandit_captain",)  # 首殺的種類照範本
    gate = make_encounter("mist_temple_gate", seed=3)
    traitor = roll_lineup(library, gate, ("temple_traitor_strikes",))
    assert (traitor.members[0].unit, traitor.members[0].affix) == ("sect_steward", "mist_veiled")
    slope = library.world_encounters["cloud_ridge"].location_by_id()["north_slope"]
    assert slope.elite is not None
    assert (slope.elite.unit, slope.elite.affix) == ("mist_wolf", "berserk")  # 北坡狼王＝狂暴的


# ---------------------------------------------------------------------------
# 戰鬥解法的勝利條件（21.5）
# ---------------------------------------------------------------------------


def test_objective_only_on_combat() -> None:
    assert SolutionDef(kind="combat", objective="escape").objective == "escape"
    with pytest.raises(ValidationError, match="objective"):
        SolutionDef(kind="parley", objective="defend")


def test_cloud_ridge_combat_objectives(library: ContentLibrary) -> None:
    table = library.world_event_content.events["cloud_ridge"]
    found = {
        s.number: o.objective
        for s in table.skeletons
        for o in s.solutions
        if o.kind == "combat" and o.objective is not None
    }
    assert found == {2: "escape", 7: "defend", 8: "defend", 14: "escape"}
