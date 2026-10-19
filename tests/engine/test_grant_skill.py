"""Phase 3D-8c：暫時獲得技能 ``grant_skill``（``docs/phases/Phase3D計畫.md`` 8.3.1、
``docs/design/06-技能.md`` 6.20）。

獲得、期滿消失（含冷卻紀錄）、重新施放只刷新、不佔欄位、schema 拒絕傳說／改寫規則型／自己、存讀與
重播、視圖與預覽、AI。
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.engine.helpers import (
    PROJECT_ROOT,
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U3, of
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.library import load_library
from trpg.content.skills import SkillDef, granted_skill_problems
from trpg.engine import (
    BattleState,
    EndTurn,
    UseSkill,
    legal_actions,
    preview,
    resolve,
)
from trpg.engine.events import (
    EffectFizzled,
    SkillCooldownChanged,
    SkillGranted,
    SkillGrantExpired,
    UnitMoved,
)
from trpg.engine.state import GrantedSkill, state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.shared.errors import ContentError, IllegalActionError
from trpg.shared.types import Pos, Team
from trpg.skillgen.budget import skill_budget

SPREAD = "skill_wing_spread"
GIFT = "skill_wing_gift"
FLIGHT = "skill_flight"
GRANTER = "skill_t_granter"
TIMED = "skill_t_timed"  # 測試用的被給技能：有冷卻


def timed_skill() -> SkillDef:
    """被給技能（測試）：1 AP 的自我強化，冷卻 2。"""
    return SkillDef.model_validate(
        {
            "id": TIMED,
            "name_zh": "測試暫時技",
            "tier": 1,
            "rarity": "rare",
            "skeleton": "aura",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": 1,
            "scaling_attr": "wis",
            "shape": {"type": "self"},
            "effects": [{"type": "apply_status", "status": "defending", "affects": "self"}],
            "cost": {"mana": 0, "cooldown": 2, "uses_per_battle": 2},
        }
    )


def granter_skill(
    skill_id: str = GRANTER, *, granted: str = TIMED, shape: str = "self"
) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": "測試給技能",
            "tier": 1,
            "rarity": "rare",
            "skeleton": "aura",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": 1,
            "scaling_attr": "wis",
            "shape": {"type": shape, "range": 4} if shape == "single" else {"type": shape},
            "effects": [
                {
                    "type": "grant_skill",
                    "skill": granted,
                    "duration": 3,
                    "affects": "self" if shape == "self" else "allies",
                }
            ],
            "cost": {"mana": 0},
        }
    )


def world(
    equipped: list[str] | None = None,
    *,
    extra: list[SkillDef] | None = None,
    ally_skills: list[str] | None = None,
    turn: str = U1,
) -> BattleState:
    """U1（弓手，裝備 ``equipped``）在 (2, 3)、U3（友方戰士）在 (4, 3)、U2（敵人）在 (6, 6)。"""
    m = make_map(FLAT7, ally=[(2, 3), (4, 3)], enemy=[(6, 6)])
    hero = caster_template(equipped or [SPREAD, GIFT], base="hero_archer")
    friend = caster_template(ally_skills or [], base="hero_fighter")
    spawns = [
        spawn(Team.ALLY, (2, 3), hero),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=999)),
        spawn(Team.ALLY, (4, 3), friend),
    ]
    return give_turn(make_state(m, spawns, skills=extra or []), turn)


def cast(state: BattleState, skill_id: str, **fields: Any) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


def fly_to(state: BattleState, x: int, y: int, unit: str = U1) -> Any:
    return resolve(
        state,
        UseSkill(unit_id=unit, skill_id=FLIGHT, target_pos=Pos(x=x, y=y)),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# 資料與 schema
# ---------------------------------------------------------------------------


def test_the_demo_skills_and_build_exist() -> None:
    lib = library()
    assert lib.skills[SPREAD].effects[0].skill == FLIGHT
    assert lib.skills[GIFT].effects[0].affects == "allies"
    winged = lib.builds.by_id()["build_winged"].hero.skills
    assert SPREAD in winged and GIFT in winged
    assert all(FLIGHT not in b.hero.skills for b in lib.builds.builds)  # 被給的技能不佔欄位


def problems(skill: SkillDef, extra: dict[str, SkillDef] | None = None) -> list[str]:
    lib = library()
    skills = {**lib.skills, **(extra or {})}
    return granted_skill_problems(skill, skills, lib.ruleset.primitives.by_id())


def test_granted_skill_checks_accept_the_demo_skills() -> None:
    assert problems(library().skills[SPREAD]) == []
    assert problems(library().skills[GIFT]) == []


@pytest.mark.parametrize(
    ("granted", "reason"),
    [
        ("skill_time_surge", "傳說"),  # 傳說（同時含改寫規則型原語）
        ("skill_undying_oath", "改寫規則型"),  # 改寫規則型原語 cheat_death
        ("skill_riposte", "主動技能"),  # 反應技
        ("skill_steady_breath", "主動技能"),  # 被動
        ("skill_bulwark_stance", "主動技能"),  # 姿態
        (SPREAD, "grant_skill"),  # 另一個 grant_skill 技能
        ("skill_nope", "未知"),
    ],
)
def test_the_schema_rejects_bad_granted_skills(granted: str, reason: str) -> None:
    found = problems(granter_skill(granted=granted))
    assert found and any(reason in p for p in found), found


def test_a_skill_cannot_grant_itself() -> None:
    with pytest.raises(ValueError, match="自己"):  # SkillDef 自己的檢查就拒絕
        granter_skill(granted=GRANTER)


def test_grant_skill_needs_skill_and_duration_and_an_active_skill() -> None:
    base = granter_skill().model_dump()
    bad_effect = {"type": "grant_skill", "duration": 3}
    with pytest.raises(ValueError, match="skill"):
        SkillDef.model_validate({**base, "effects": [bad_effect]})
    over = {"type": "grant_skill", "skill": FLIGHT, "duration": 9, "affects": "self"}
    with pytest.raises(ValueError, match="最多"):
        SkillDef.model_validate({**base, "effects": [over]})
    passive = {**base, "kind": "passive", "ap_cost": None, "trigger": {"event": "on_turn_end"}}
    with pytest.raises(ValueError, match="只能用在主動技能"):
        SkillDef.model_validate(passive)


def test_loading_content_rejects_a_grant_of_a_legendary_skill(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    bad = yaml.safe_load((root / "skills" / f"{SPREAD}.yaml").read_text(encoding="utf-8"))
    bad["id"] = "skill_bad_grant"
    bad["effects"][0]["skill"] = "skill_time_surge"
    (root / "skills" / "skill_bad_grant.yaml").write_text(
        yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ContentError, match="傳說"):
        load_library(root)


def test_the_budget_of_a_grant_is_the_granted_points_times_the_expected_uses() -> None:
    lib = library()
    flight = skill_budget(lib.skills[FLIGHT], lib).total
    permille = lib.budget.grant_skill_expected_uses_per_round_permille
    report = skill_budget(lib.skills[SPREAD], lib)
    assert report.total == flight * permille * 3 / 1000
    assert report.ok


# ---------------------------------------------------------------------------
# 獲得、倒數、期滿
# ---------------------------------------------------------------------------


def test_casting_grants_the_skill_without_using_a_slot() -> None:
    state = world()
    before = state.units[U1].skills
    result = cast(state, SPREAD)
    granted = of(result, SkillGranted)
    assert [(e.unit_id, e.source_id, e.skill_id, e.duration, e.refreshed) for e in granted] == [
        (U1, U1, FLIGHT, 3, False)
    ]
    unit = result.state.units[U1]
    assert unit.granted_skills == (GrantedSkill(FLIGHT, 3),)
    assert unit.skills == before and unit.all_skills == (*before, FLIGHT)


def test_the_granted_skill_shows_up_in_legal_actions_and_works() -> None:
    state = cast(world(), SPREAD).state
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == FLIGHT]
    assert actions  # 飛行有可選的落點
    result = fly_to(state, 5, 3)
    assert of(result, UnitMoved)[0].to_pos == Pos(x=5, y=3)
    assert result.state.units[U1].xy == (5, 3)


def test_without_the_grant_the_unit_cannot_use_the_skill() -> None:
    state = world()
    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == FLIGHT]
    with pytest.raises(IllegalActionError, match="沒有裝備"):
        fly_to(state, 5, 3)


def end_turn(state: BattleState, unit_id: str = U1) -> BattleState:
    """結束 ``unit_id`` 的回合，之後把回合還給它（保持測試單純）。"""
    return give_turn(resolve(give_turn(state, unit_id), EndTurn(unit_id=unit_id)).state, unit_id)  # type: ignore[arg-type]


def test_the_duration_counts_down_at_the_holders_turn_end_and_expires() -> None:
    state = cast(world(), SPREAD).state
    assert state.units[U1].granted_skills[0].remaining == 3
    state = end_turn(state)
    assert state.units[U1].granted_skills[0].remaining == 2
    state = end_turn(state)
    assert state.units[U1].granted_skills[0].remaining == 1
    result = resolve(give_turn(state, U1), EndTurn(unit_id=U1))
    assert [(e.unit_id, e.skill_id) for e in of(result, SkillGrantExpired)] == [(U1, FLIGHT)]
    assert result.state.units[U1].granted_skills == ()
    assert result.state.units[U1].all_skills == result.state.units[U1].skills


def test_expiry_clears_the_cooldown_and_use_records() -> None:
    state = world([GRANTER], extra=[timed_skill(), granter_skill()])
    state = cast(state, GRANTER).state
    used = resolve(state, UseSkill(unit_id=U1, skill_id=TIMED)).state
    assert used.units[U1].cooldowns.get(TIMED) == 2 and used.units[U1].skill_uses.get(TIMED) == 1
    for _ in range(3):
        used = end_turn(used)
    assert used.units[U1].granted_skills == ()
    assert TIMED not in used.units[U1].cooldowns and TIMED not in used.units[U1].skill_uses


def test_recasting_only_refreshes_the_remaining_rounds() -> None:
    state = cast(world(), SPREAD).state
    state = end_turn(end_turn(state))
    assert state.units[U1].granted_skills == (GrantedSkill(FLIGHT, 1),)
    state.units[U1].cooldowns.clear()  # 展翼的冷卻不是這個測試的重點
    result = cast(state, SPREAD)
    granted = of(result, SkillGranted)
    assert [e.refreshed for e in granted] == [True]
    assert result.state.units[U1].granted_skills == (GrantedSkill(FLIGHT, 3),)  # 沒有疊成兩個


def test_granting_a_friend_counts_down_on_the_friends_turn_not_the_casters() -> None:
    state = world()
    result = cast(state, GIFT, target_id=U3)
    assert [(e.unit_id, e.source_id) for e in of(result, SkillGranted)] == [(U3, U1)]
    state = result.state
    assert state.units[U3].granted_skills == (GrantedSkill(FLIGHT, 3),)
    assert state.units[U1].granted_skills == ()
    state = end_turn(state, U1)  # 施放者結束回合：友方的輪數不變
    assert state.units[U3].granted_skills == (GrantedSkill(FLIGHT, 3),)
    state = end_turn(state, U3)
    assert state.units[U3].granted_skills == (GrantedSkill(FLIGHT, 2),)
    # 友方可以用被給的技能
    assert [a for a in legal_actions(give_turn(state, U3)) if isinstance(a, UseSkill)]


def test_granting_a_skill_the_target_already_equips_fizzles() -> None:
    state = world([GIFT], ally_skills=[FLIGHT])
    result = cast(state, GIFT, target_id=U3)
    assert of(result, SkillGranted) == []
    assert [e.reason for e in of(result, EffectFizzled)] == ["already_equipped"]
    assert result.state.units[U3].granted_skills == ()


def test_a_granted_skill_follows_its_own_cooldown_rules() -> None:
    state = world([GRANTER], extra=[timed_skill(), granter_skill()])
    state = cast(state, GRANTER).state
    after = resolve(state, UseSkill(unit_id=U1, skill_id=TIMED))
    assert [(e.skill_id, e.remaining) for e in of(after, SkillCooldownChanged)] == [(TIMED, 2)]
    again = [
        a
        for a in legal_actions(give_turn(after.state, U1))
        if isinstance(a, UseSkill) and a.skill_id == TIMED
    ]
    assert again == []  # 冷卻中


# ---------------------------------------------------------------------------
# 存讀、視圖、預覽、重播
# ---------------------------------------------------------------------------


def test_the_state_round_trips_through_json_with_granted_skills() -> None:
    state = cast(world(), SPREAD).state
    restored = state_from_json(state_to_json(state))
    assert restored.units[U1].granted_skills == (GrantedSkill(FLIGHT, 3),)
    assert state_to_json(restored) == state_to_json(state)
    # 存讀之後倒數照常
    assert end_turn(restored).units[U1].granted_skills == (GrantedSkill(FLIGHT, 2),)


def test_clone_copies_granted_skills() -> None:
    state = cast(world(), SPREAD).state
    copy = state.clone()
    assert copy.units[U1].granted_skills == state.units[U1].granted_skills


def test_the_view_lists_granted_skills_for_the_own_team_only() -> None:
    state = cast(world(), SPREAD).state
    own = next(u for u in project_for(state, Team.ALLY).units if u.id == U1)
    assert [(g.skill_id, g.name_zh, g.remaining) for g in own.granted_skills] == [
        (FLIGHT, "飛行", 3)
    ]
    assert own.skills == state.units[U1].skills  # 欄位裡的技能不含暫時技能
    foe_view = next(u for u in project_for(state, Team.ENEMY).units if u.id == U1)
    assert foe_view.granted_skills == ()


def test_the_preview_lists_the_grant() -> None:
    pv = preview(world(), UseSkill(unit_id=U1, skill_id=SPREAD))
    assert [(g.unit_id, g.skill_id, g.name_zh, g.duration, g.refreshed) for g in pv.grants] == [
        (U1, FLIGHT, "飛行", 3, False)
    ]


def test_ai_battle_with_wings_replays(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "wings.json"
    argv = ["battle", "--map", "open_plain", "--seed", "2", "--ally-build", "build_winged"]
    assert main([*argv, "--log-json", str(log)]) == 0
    text = capsys.readouterr().out
    assert "暫時獲得技能「飛行」" in text and "施放「飛行」" in text
    assert "暫時獲得的技能「飛行」期滿消失了" in text and "［暫時技能：飛行 剩" in text
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()
