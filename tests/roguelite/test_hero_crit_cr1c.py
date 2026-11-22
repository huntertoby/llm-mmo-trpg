"""一輪中主角面板的暴擊傷害（CR-1c，``docs/design/05-戰鬥.md`` 5.4.2 第 8 點）：和戰鬥中的單位卡
同一套字、同一個引擎函式；後端從主角的武器、裝備、種族、技能組出最小的戰鬥狀態來算
（:mod:`trpg.roguelite.hero_crit`）。主角自己的面板，修正技寫技能名。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import library
from tests.engine.test_crit_race_cr1 import _passive
from trpg.api.run_presenter import hero_out
from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.races import RaceDef, RacePassive
from trpg.content.skills import SkillDef
from trpg.engine import begin_battle
from trpg.engine import modifiers as mods
from trpg.engine.crit_damage import crit_damage_permille
from trpg.engine.skills.conditions import Subject
from trpg.roguelite import RunState, battle_setup, new_run
from trpg.roguelite.progress import hero_unit_id

MOD = "skill_cr1c_crit_mastery"


def _modifier(change: int) -> SkillDef:
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    data.update(
        id=MOD,
        name_zh="暴擊專精",
        modifiers=[
            {"applies_to": {"all_attacks": True}, "change": {"crit_damage_permille": change}}
        ],
    )
    return SkillDef.model_validate(data)


def _helm(crit: int) -> ItemDef:
    data: dict[str, Any] = library().items["item_test_helm"].model_dump(mode="json")
    data["affixes"] = [{"affix": "affix_crit_damage", "value": crit}]
    return ItemDef.model_validate(data)


def _setup(
    monkeypatch: pytest.MonkeyPatch,
    *,
    weapon: int | None = None,
    gear: int = 0,
    race: int = 0,
    modifier: int | None = None,
) -> tuple[ContentLibrary, RunState]:
    lib = library()
    run = new_run(lib, "build_fire", 0)
    own = lib.weapons[run.hero.weapon].model_copy(
        update={"crit_permille": weapon, "name_zh": "戰斧"}
    )
    lib = replace(lib, weapons={**lib.weapons, run.hero.weapon: own})
    hero = run.hero
    update: dict[str, Any] = {}
    if modifier is not None:
        update["generated_skills"] = (*run.generated_skills, _modifier(modifier))
        # 被動欄有上限：只留主動技，再放這招修正技（開戰的裝備檢查要過）
        actives = tuple(s for s in hero.skills if lib.ruleset.skill_def(s).slot_kind == "active")
        hero = hero.model_copy(update={"skills": (*actives, MOD)})
    if race:
        hero = hero.model_copy(update={"race": "human"})
        original = Ruleset.race_def

        def race_def(self: Ruleset, race_id: str) -> RaceDef:
            passive = RacePassive.model_validate(_passive(crit_damage_permille=race))
            return original(self, race_id).model_copy(update={"passive": passive})

        monkeypatch.setattr(Ruleset, "race_def", race_def)
    if gear:
        update["equipment"] = {"head": _helm(gear)}
    return lib, run.model_copy(update={**update, "hero": hero})


def _panel(lib: ContentLibrary, run: RunState) -> tuple[int | None, str | None]:
    out = hero_out(lib, run)
    return out.crit_damage_permille, out.crit_damage_detail_zh


def test_two_hundred_percent_is_shown_too(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _panel(*_setup(monkeypatch)) == (2000, "武器「戰斧」200%（全身上限 300%）")


def test_not_capped_lists_every_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """設計的例子：武器 200%・詞條 +10%・種族 +25%・修正技 +25% ＝ 260%（修正技寫技能名）。"""
    lib, run = _setup(monkeypatch, gear=100, race=250, modifier=250)
    assert _panel(lib, run) == (
        2600,
        "武器「戰斧」200%・詞條 +10%・種族 +25%・修正技「暴擊專精」+25%（全身上限 300%）",
    )


def test_capped_at_the_top(monkeypatch: pytest.MonkeyPatch) -> None:
    lib, run = _setup(monkeypatch, weapon=2500, modifier=1000)
    assert _panel(lib, run) == (3000, "武器「戰斧」250%・修正技「暴擊專精」+100%・頂到上限 300%")


def test_raised_to_the_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    lib, run = _setup(monkeypatch, weapon=1500, race=-300)
    assert _panel(lib, run) == (1500, "武器「戰斧」150%・種族 -30%・最低 150%")


def test_the_panel_equals_the_battle_multiplier(monkeypatch: pytest.MonkeyPatch) -> None:
    """面板的倍率＝開戰後主角普攻結算用的倍率（同一份範本、裝備、技能）。"""
    lib, run = _setup(monkeypatch, weapon=2500, gear=100, race=250, modifier=-300)
    state = begin_battle(battle_setup(lib, run), 0).state
    hero = state.units[hero_unit_id(state)]
    foe = next(u for u in state.units_sorted() if u.team is not hero.team)
    attack = crit_damage_permille(state, hero, use=mods.ATTACK, subject=Subject(foe, foe.xy))
    assert _panel(lib, run)[0] == attack == 2550
