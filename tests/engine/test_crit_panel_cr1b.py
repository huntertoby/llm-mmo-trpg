"""角色面板的暴擊傷害（CR-1b，``docs/design/05-戰鬥.md`` 5.4.2 第 8 點，佇列 (v)）：數值區一律顯示
主手武器普攻套完上下限的最後倍率（200% 也顯示），「▸ 詳細」列出來源；被截掉時最後寫「頂到上限」或
「最低」。倍率和結算共用 :func:`trpg.engine.crit_damage.crit_damage_permille`；技能自帶倍率不算進
面板。敵方單位照現有的數值做法：看得到的才顯示（隱蔽中的敵人藏起來），技能名不給。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle
from tests.engine.test_crit_race_cr1 import _passive
from tests.engine.test_gear import _unit
from trpg.api.hidden_info import mask_view
from trpg.content.library import Ruleset
from trpg.content.races import RaceDef, RacePassive
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine import modifiers as mods
from trpg.engine.crit_damage import (
    crit_damage_breakdown,
    crit_damage_detail_zh,
    crit_damage_permille,
)
from trpg.engine.skills.conditions import Subject
from trpg.engine.view import project_for
from trpg.shared.types import Team

AFFIX = "affix_crit_damage"


def _modifier(change: int) -> SkillDef:
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    data.update(
        id=SID,
        name_zh="暴擊專精",
        modifiers=[
            {"applies_to": {"all_attacks": True}, "change": {"crit_damage_permille": change}}
        ],
    )
    return SkillDef.model_validate(data)


def _spell(**fields: Any) -> SkillDef:
    data = make_skill(
        SID, {"type": "single", "range": 5}, [{"type": "damage", "dice": "1d6", "element": "fire"}]
    ).model_dump(mode="json")
    data.update(fields)
    return SkillDef.model_validate(data)


def _state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    weapon: int | None = None,
    gear: int = 0,
    race: int = 0,
    modifier: int | None = None,
) -> BattleState:
    state = battle(_modifier(modifier) if modifier is not None else _spell(), [(4, 3)])
    unit = state.units[U1]
    unit.weapon = unit.weapon.model_copy(update={"crit_permille": weapon, "name_zh": "戰斧"})
    if gear:
        unit.gear = _unit({"main_hand": [(AFFIX, gear)]}).gear
    if race:
        unit.race = "human"
        original = Ruleset.race_def

        def race_def(self: Ruleset, race_id: str) -> RaceDef:
            passive = RacePassive.model_validate(_passive(crit_damage_permille=race))
            return original(self, race_id).model_copy(update={"passive": passive})

        monkeypatch.setattr(Ruleset, "race_def", race_def)
    return state


def _panel(state: BattleState, uid: str = U1) -> tuple[int | None, str | None]:
    view = project_for(state, Team.ALLY)
    unit = next(u for u in view.units if u.id == uid)
    return unit.crit_damage_permille, unit.crit_damage_detail_zh


def test_two_hundred_percent_is_shown_too(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _panel(_state(monkeypatch)) == (2000, "武器「戰斧」200%（全身上限 300%）")


def test_the_sources_are_listed_when_not_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    """設計的例子：武器 200%・詞條 +10%・種族 +25%・修正技 +25% ＝ 260%。"""
    state = _state(monkeypatch, gear=100, race=250, modifier=250)
    assert _panel(state) == (
        2600,
        "武器「戰斧」200%・詞條 +10%・種族 +25%・修正技「暴擊專精」+25%（全身上限 300%）",
    )


def test_capped_at_the_top(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(monkeypatch, weapon=2500, modifier=1000)
    assert _panel(state) == (3000, "武器「戰斧」250%・修正技「暴擊專精」+100%・頂到上限 300%")


def test_raised_to_the_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(monkeypatch, weapon=1500, race=-300)
    assert _panel(state) == (1500, "武器「戰斧」150%・種族 -30%・最低 150%")


def test_the_panel_uses_the_same_function_as_the_attack(monkeypatch: pytest.MonkeyPatch) -> None:
    """面板的倍率＝結算用的倍率（主手普攻；修正技的條件不看目標時）。"""
    state = _state(monkeypatch, weapon=2500, gear=100, race=250, modifier=-300)
    unit, target = state.units[U1], state.units[U2]
    attack = crit_damage_permille(state, unit, use=mods.ATTACK, subject=Subject(target, target.xy))
    assert _panel(state)[0] == attack == 2550


def test_a_skill_own_multiplier_is_not_in_the_panel(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(_spell(crit_permille=2500), [(4, 3)])
    assert _panel(state)[0] == 2000
    skill = state.ruleset.skill_def(SID)
    breakdown = crit_damage_breakdown(state, state.units[U1], skill=skill)
    assert breakdown.total == 2500  # 技能卡那招自己算（「技能自帶」一項）
    assert crit_damage_detail_zh(breakdown).endswith("技能自帶 +50%（全身上限 300%）")


def test_other_teams_get_the_number_without_skill_names(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(monkeypatch, modifier=250)
    breakdown = crit_damage_breakdown(
        state, state.units[U1], use=mods.ATTACK, subject=Subject(None, state.units[U1].xy)
    )
    assert crit_damage_detail_zh(breakdown, names=False) == (
        "武器「戰斧」200%・修正技 +25%（全身上限 300%）"
    )
    enemy = project_for(state, Team.ENEMY)
    unit = next(u for u in enemy.units if u.id == U1)
    assert unit.crit_damage_permille == 2250
    assert unit.crit_damage_detail_zh is not None and "暴擊專精" not in unit.crit_damage_detail_zh


def test_hidden_units_hide_it(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(monkeypatch)
    view = mask_view(project_for(state, Team.ALLY), frozenset({U2}))
    foe = next(u for u in view.units if u.id == U2)
    assert foe.crit_damage_permille is None and foe.crit_damage_detail_zh is None
    me = next(u for u in view.units if u.id == U1)
    assert me.crit_damage_permille == 2000
