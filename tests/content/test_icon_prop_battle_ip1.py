"""行為一致：``icon_prop`` 只影響圖示（Phase IP-1，06 6.36：拿掉這個欄位，戰鬥結果必須完全相同）。

每個填了 ``icon_prop`` 的技能裝在一個單位身上（敵人專用招裝在敵方），同種子各跑兩場：原內容的規則包
vs 拿掉全部 ``icon_prop`` 的規則包。步驟、事件序列、最終狀態逐筆相同；另外確認原內容那場的戰鬥紀錄
能通過重播驗證（``icon_prop`` 不讓重播失敗），以及規則包雜湊會因內容改變（報告寫明）。
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library, make_map, make_setup, spawn
from trpg.content.equipment import resolve_loadout
from trpg.content.library import Ruleset
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import BattleSetup
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import SkillUsed
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.engine.runner import BattleRun, log_replay_problem, replay, run_battle
from trpg.shared.types import Team

SEEDS = (1, 2)

_WEAPON_OF_REQ = {
    "melee": "one_handed_sword",
    "ranged": "bow",
    "focus": "fire_staff",
    "any": "fire_staff",
}


def _icon_skills() -> list[SkillDef]:
    return sorted((s for s in library().skills.values() if s.icon_prop), key=lambda s: s.id)


def _stripped(ruleset: Ruleset) -> Ruleset:
    skills = tuple(s.model_copy(update={"icon_prop": None}) for s in ruleset.skills.skills)
    return ruleset.model_copy(update={"skills": SkillTable(skills=skills)})


def _weapon(skill: SkillDef) -> str:
    """技能能用的武器：限定武器時取第一件在武器表裡的（副手限定的招退回大類預設、另裝副手）。"""
    weapons = library().weapons
    found = [w for w in skill.weapon_only if w in weapons]
    return found[0] if found else _WEAPON_OF_REQ[skill.weapon_req]


def _setup(skill: SkillDef) -> BattleSetup:
    open_map = make_map("000000\n000000\n000000\n000000", ally=[(1, 1)], enemy=[(4, 2), (4, 1)])
    user_team = Team.ENEMY if skill.enemy_only else Team.ALLY
    other = Team.ALLY if user_team == Team.ENEMY else Team.ENEMY
    pos_user, pos_other = ((4, 2), (1, 1)) if skill.enemy_only else ((1, 1), (4, 2))
    user = spawn(user_team, pos_user, "bandit", _weapon(skill), skills=[skill.id])
    offhands = [w for w in skill.weapon_only if w in library().offhands]
    if offhands and not any(w in library().weapons for w in skill.weapon_only):
        lib = library()
        item = f"item_offhand_{offhands[0]}"
        loadout = resolve_loadout({"off_hand": item}, lib.items, lib.affixes)
        user = user.model_copy(update={"equipment": loadout})
    units = [
        user,
        spawn(other, pos_other, "bandit"),
        spawn(other, (4, 1) if not skill.enemy_only else (1, 2), "bandit"),
    ]
    return make_setup(open_map, units, max_rounds=6)


def _run(setup: BattleSetup, seed: int) -> BattleRun:
    return run_battle(setup, seed, UtilityAI(library().ai_profiles))


def _trace(run: BattleRun) -> dict[str, Any]:
    """步驟、事件與最終狀態。最終狀態內嵌規則包，比對前一律換成拿掉 ``icon_prop`` 的版本（兩邊只差
    在內嵌的技能定義上的這個欄位，其餘逐欄相同）。"""
    log = run.to_log().model_dump(mode="json")
    final = dict(log["final_state"])
    final["ruleset"] = _stripped(run.state.ruleset).model_dump(mode="json")
    return {"actions": log["actions"], "events": log["events"], "final_state": final}


@cache
def _pair(skill_id: str, seed: int) -> tuple[BattleRun, BattleRun]:
    setup = _setup(library().skills[skill_id])
    plain = setup.model_copy(update={"ruleset": _stripped(setup.ruleset)})
    return _run(setup, seed), _run(plain, seed)


@pytest.mark.parametrize("skill_id", [s.id for s in _icon_skills()])
def test_removing_icon_prop_gives_identical_battles(skill_id: str) -> None:
    for seed in SEEDS:
        with_prop, without = _pair(skill_id, seed)
        assert _trace(with_prop) == _trace(without), (skill_id, seed)


def test_identity_battles_actually_cast_icon_prop_skills() -> None:
    """一致測試要真的放到招才有意義：效用 AI 在這個小場地至少放出 10 招（IP-1 實測 11 招；其餘要
    條件（倒地、冰凍、層數）或是被動／修正型，不發 ``SkillUsed``，但仍在規則包裡、仍比對一致）。"""
    used: set[str] = set()
    for skill in _icon_skills():
        for seed in SEEDS:
            run, _ = _pair(skill.id, seed)
            names = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
            if skill.id in names:
                used.add(skill.id)
    assert len(used) >= 10, sorted(used)


def test_ruleset_hash_changes_but_replay_still_verifies() -> None:
    """規則包內嵌技能全文，所以雜湊會因 ``icon_prop`` 不同；紀錄照樣能重播（內嵌的就是當時的）。"""
    skill = library().skills["skill_armor_breaker"]
    setup = _setup(skill)
    assert hash_ruleset(setup.ruleset) != hash_ruleset(_stripped(setup.ruleset))
    run = _run(setup, SEEDS[0])
    log = run.to_log()
    assert log_replay_problem(log) is None
    again = replay(log.setup, log.seed, log.actions)
    assert _trace(again) == _trace(run)
