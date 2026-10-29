"""一輪的測試模式（Phase 3-39）：戰後回滿、挑的裝備進戰鬥、存檔相容、不合法裝備、正式模式不變。"""

from __future__ import annotations

import json

import pytest

from tests.roguelite.helpers import library
from trpg.roguelite import (
    ChoiceError,
    RunSave,
    RunState,
    auto_play,
    dumps_save,
    loads_save,
    new_keyword_run,
)
from trpg.roguelite.battle import ActiveBattle
from trpg.roguelite.progress import battle_setup, hero_unit_id
from trpg.roguelite.state import BattleNode, EndedNode

WEAPON = "one_handed_sword"
KEYWORDS = ("ignite", "prone")
GEAR = {"main_hand": "item_test_sword", "body": "item_test_armor", "ring_1": "item_test_ring_hp"}


def _run(seed: int = 3, **kwargs: object) -> RunState:
    return new_keyword_run(library(), WEAPON, KEYWORDS, seed, **kwargs)  # type: ignore[arg-type]


def _after_battles(run: RunState) -> list[tuple[RunState, RunState]]:
    """AI 代打一輪，回傳每場「打贏後」的（戰前, 戰後）一輪狀態。"""
    pairs: list[tuple[RunState, RunState]] = []

    def on_node(before: RunState, after: RunState) -> None:
        if isinstance(before.node, BattleNode) and before.battles_done < after.battles_done:
            pairs.append((before, after))

    auto_play(library(), run, on_node=on_node)
    return pairs


def test_default_run_is_not_test_mode() -> None:
    run = _run()
    assert run.test_mode is False
    assert run.test_equipment == {}


def test_test_mode_refills_hp_and_mana_after_every_won_battle() -> None:
    lib = library()
    core = lib.ruleset.core
    pairs = _after_battles(_run(test_mode=True))
    assert pairs
    for _, after in pairs:
        # 回滿到戰鬥中的實際上限（含裝備；3K-2 起戰後會拿到裝備，所以可能高於一輪算的上限）
        assert after.hp >= after.max_hp_in(core)
        assert after.mana >= after.max_mana_in(core)
    # 歷程仍記錄打完當下的真實剩餘（不是回滿後的數字）
    last = pairs[-1][1]
    assert any(r.hp < last.max_hp_in(core) or r.mana < last.max_mana_in(core) for r in last.history)


def test_test_mode_refills_to_the_gear_inclusive_maximum() -> None:
    """裝備加最大 HP 時，回滿是回到戰鬥中的實際上限（下一場開戰時是滿的）。"""
    lib = library()
    pairs = _after_battles(_run(test_mode=True, test_equipment=GEAR))
    _, after = pairs[0]
    assert after.hp > after.max_hp_in(lib.ruleset.core)
    if isinstance(after.node, BattleNode):
        state = ActiveBattle(lib, after).state
        hero = next(u for u in state.units_sorted() if u.id == hero_unit_id(state))
        assert hero.hp == hero.max_hp


def test_normal_mode_does_not_refill_between_battles() -> None:
    lib = library()
    core = lib.ruleset.core
    pairs = _after_battles(_run())
    assert any(
        a.hp < a.max_hp_in(core) or a.mana < a.max_mana_in(core)
        for b, a in pairs
        if a.battles_done == 1
    )


def test_test_mode_does_not_change_the_rng_streams() -> None:
    """亂數只由種子衍生：測試模式與正式模式的安排、起始技能相同。"""
    normal, test = _run(), _run(test_mode=True)
    assert normal.plan == test.plan
    assert normal.hero == test.hero
    assert normal.generated_skills == test.generated_skills


def test_test_equipment_enters_the_battle() -> None:
    lib = library()
    run = _run(test_mode=True, test_equipment=GEAR)
    assert run.test_equipment == GEAR
    assert run.hero.equipment == {}  # 範本本身不改，由一輪的設定取代
    setup = battle_setup(lib, run)
    hero = setup.units[0]
    assert {e.slot: e.item.id for e in hero.equipment.items} == GEAR
    plain = battle_setup(lib, _run(test_mode=True)).units[0]
    assert plain.equipment.items == ()


def test_test_equipment_replaces_the_template_equipment() -> None:
    lib = library()
    run = _run(test_mode=True, test_equipment={"body": "item_test_armor"})
    hero = battle_setup(lib, run).units[0]
    assert [e.slot for e in hero.equipment.items] == ["body"]


def test_run_with_equipment_plays_to_the_end_and_replays_the_same() -> None:
    run = _run(test_mode=True, test_equipment=GEAR)
    first, _ = auto_play(library(), run)
    second, _ = auto_play(library(), run)
    assert first == second
    assert isinstance(first.node, EndedNode)
    assert first.test_mode and first.test_equipment == GEAR


@pytest.mark.parametrize(
    ("equipment", "match"),
    [
        ({"body": "item_nope"}, "未知的物品"),
        ({"cape": "item_test_armor"}, "未知的裝備欄位"),
        ({"head": "item_test_armor"}, "只能放"),
        ({"main_hand": "item_test_hammer"}, "必須和單位的武器"),
        ({"ring_1": "item_test_ring_hp", "ring_2": "item_test_ring_hp"}, "同一枚戒指"),
    ],
)
def test_illegal_test_equipment_is_rejected_in_chinese(
    equipment: dict[str, str], match: str
) -> None:
    with pytest.raises(ChoiceError, match=match):
        _run(test_mode=True, test_equipment=equipment)


def test_equipment_requires_test_mode() -> None:
    with pytest.raises(ChoiceError, match="只能在測試模式"):
        _run(test_equipment={"body": "item_test_armor"})


def test_save_roundtrip_keeps_test_mode_and_equipment() -> None:
    run = _run(test_mode=True, test_equipment=GEAR)
    loaded = loads_save(dumps_save(RunSave(run_id="t1", run=run)))
    assert loaded.run == run
    assert loaded.run.test_mode is True
    assert loaded.run.test_equipment == GEAR


def test_old_save_without_the_fields_still_loads() -> None:
    """3-39 之前的存檔沒有 test_mode／test_equipment：照常讀取，視為正式模式（格式不升號）。"""
    raw = json.loads(dumps_save(RunSave(run_id="old", run=_run())))
    del raw["run"]["test_mode"], raw["run"]["test_equipment"]
    loaded = loads_save(json.dumps(raw))
    assert loaded.format == "trpg-run/10"
    assert loaded.run.test_mode is False
    assert loaded.run.test_equipment == {}
