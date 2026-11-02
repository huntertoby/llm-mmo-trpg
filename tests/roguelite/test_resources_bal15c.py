"""BAL-15c：一輪狀態的法力／耐力基礎和戰鬥中一致（舊存檔依武器大類補上），以及 #84 回歸：
主角的法力跨場延續，隊友與敵人每場開場法力滿。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.engine import begin_battle
from trpg.roguelite import dumps_save, loads_save, new_run, upgrade_save
from trpg.roguelite.progress import battle_setup, hero_unit_id
from trpg.roguelite.save import RunSave, fill_resource_base
from trpg.roguelite.state import RunState


def _old_run(build: str = "build_fire") -> RunState:
    """BAL-15b 以前的 build 開局存檔：主角範本沒寫耐力與法力基礎。"""
    run = new_run(library(), build, 3)
    hero = run.hero.model_copy(update={"stamina": None, "max_mana": None})
    return run.model_copy(update={"hero": hero})


def test_old_save_hero_gets_the_weapon_class_base() -> None:
    lib = library()
    core = lib.ruleset.core
    old = _old_run()
    assert old.max_stamina_in(core) == core.resources.max_for(
        "stamina", core.default_stamina, old.hero.attributes
    )  # 修正前：一輪狀態用 default_stamina，戰鬥中依武器大類
    fixed = fill_resource_base(lib, old)
    wclass = lib.weapons[old.hero.weapon].weapon_class
    base = core.resources.class_base[wclass]
    assert (fixed.hero.stamina, fixed.hero.max_mana) == (base.stamina, base.mana)
    assert fixed.max_stamina_in(core) == core.template_max_resource("stamina", old.hero, wclass)
    assert fixed.max_mana_in(core) == core.template_max_resource("mana", old.hero, wclass)
    assert fill_resource_base(lib, fixed) is fixed  # 已經有寫：原樣


def test_upgrade_save_fills_the_base_and_new_runs_already_match() -> None:
    lib = library()
    new = new_run(lib, "build_fire", 3)
    assert fill_resource_base(lib, new) is new
    loaded = upgrade_save(lib, loads_save(dumps_save(RunSave(run_id="old", run=_old_run()))))
    assert loaded.run.hero.stamina == new.hero.stamina
    assert loaded.run.hero.max_mana == new.hero.max_mana


def test_only_the_hero_carries_mana_between_battles() -> None:
    """#84：法力只在營火回滿只管跨場延續的主角；隊友與敵人每場新上場，開場法力滿。"""
    lib = library()
    run = new_run(lib, "build_fire", 3).model_copy(update={"mana": 0})
    state = begin_battle(battle_setup(lib, run), run.plan[0].seed).state
    hero = hero_unit_id(state)
    assert state.units[hero].mana == 0
    others = [u for u in state.units_sorted() if u.id != hero]
    assert {u.team for u in others} == {"ally", "enemy"}
    for unit in others:
        assert unit.mana == unit.max_mana > 0
