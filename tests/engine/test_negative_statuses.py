"""Phase 2D-2 4.5：恐懼、沉默、致盲、被標記——規則、preview 與 mental 控制遞減。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of, script_rolls
from trpg.engine import Attack, EndTurn, Move, UseSkill, legal_actions, preview, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.control import plan_status
from trpg.engine.effects import ApplyStatusEffect, DamageEffect, run_effects
from trpg.engine.events import StatusRemoved
from trpg.engine.rules.combat import advantage_state, attack_problem
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.movement import reachable_tiles
from trpg.engine.rules.statuses import boss_converted_status
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

FIRE_BOLT = "skill_fire_bolt"
CRUSHER = "skill_bone_crusher"


def _scene(
    ally: str = "hero_fighter",
    *,
    ally_skills: list[str] | None = None,
    ally_xy: tuple[int, int] = (3, 3),
    foes: list[tuple[int, int]] | None = None,
) -> BattleState:
    """U1 我方（預設戰士）在 ``ally_xy``；敵人 U2、U3 依 ``foes``（沒有反應規則）。"""
    foes = foes or [(5, 3)]
    m = make_map(FLAT7, ally=[ally_xy], enemy=foes)
    tmpl = caster_template(ally_skills or [], base=ally)
    spawns = [spawn(Team.ALLY, ally_xy, tmpl)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def _give(state: BattleState, unit: UnitId, status: str, source: UnitId | None = None) -> None:
    state.units[unit].statuses = [StatusInstance(status, 2, source)]


# ---------------------------------------------------------------------------
# 恐懼
# ---------------------------------------------------------------------------


def test_feared_unit_cannot_step_closer_to_the_source() -> None:
    state = _scene()
    _give(state, U1, "feared", U2)
    source = state.units[U2].xy
    start = manhattan(state.units[U1].xy, source)
    tiles = reachable_tiles(state, U1)
    assert tiles  # 仍然可以往旁邊或遠處走
    # 每一格都能由「每一步距離不減」的路徑抵達，所以終點不會比起點更近
    assert all(manhattan((p.x, p.y), source) >= start for p in tiles)
    assert Pos(x=4, y=3) not in tiles and Pos(x=0, y=3) in tiles
    with pytest.raises(IllegalActionError, match="恐懼"):
        resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3))))
    # 繞一步再靠近也不行：每一步都要檢查
    with pytest.raises(IllegalActionError, match="恐懼"):
        resolve(
            state,
            Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=3, y=2), Pos(x=4, y=2))),
        )
    side = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=3, y=2))))
    assert side.state.units[U1].xy == (3, 2)


def test_fear_only_restricts_the_distance_to_its_own_source() -> None:
    state = _scene(foes=[(5, 3), (3, 5)])
    _give(state, U1, "feared", U2)
    tiles = reachable_tiles(state, U1)
    assert Pos(x=3, y=4) in tiles  # 靠近 U3 沒有限制，只要不靠近 U2


def test_feared_attacks_have_disadvantage_against_anyone() -> None:
    state = _scene(foes=[(4, 3), (3, 4)])
    for target in (U2, U3):
        assert advantage_state(state, state.units[U1], state.units[target]) == "none"
    _give(state, U1, "feared", U2)
    for target in (U2, U3):
        assert advantage_state(state, state.units[U1], state.units[target]) == "disadvantage"


def test_fear_is_removed_when_its_source_goes_down() -> None:
    state = _scene(foes=[(4, 3), (3, 4)])
    _give(state, U1, "feared", U2)
    result = run_effects(state, [DamageEffect(target_id=U2, source_id=U1, mode="lethal")])
    assert result.state.units[U1].get_status("feared") is None
    assert [(e.target_id, e.status_id, e.reason) for e in of(result, StatusRemoved)] == [
        (U1, "feared", "source_lost")
    ]


def test_reapplying_fear_changes_the_source() -> None:
    state = _scene(foes=[(4, 3), (3, 4)])
    _give(state, U1, "feared", U2)
    result = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id="feared", source_id=U3)])
    status = result.state.units[U1].get_status("feared")
    assert status is not None and status.source_id == U3


def test_a_cornered_feared_unit_can_still_end_its_turn() -> None:
    """只有兩格寬的走廊：唯一的出路是來源所在的格子；沒有任何合法移動，AI 照樣結束回合。"""
    m = make_map("00", ally=[(0, 0)], enemy=[(1, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter", skills=[])),
            spawn(Team.ENEMY, (1, 0), no_reactions()),
        ],
    )
    state = give_turn(state, U1)
    _give(state, U1, "feared", U2)
    actions = legal_actions(state)
    assert not [a for a in actions if isinstance(a, Move)]
    assert any(isinstance(a, EndTurn) for a in actions)
    assert UtilityAI(library().ai_profiles)(state) is not None  # 不丟例外、不僵住


def test_a_feared_ai_unit_never_proposes_a_move_toward_the_source() -> None:
    state = _scene(foes=[(5, 3)])
    _give(state, U1, "feared", U2)
    for action in legal_actions(state):
        if isinstance(action, Move):
            assert manhattan((action.path[-1].x, action.path[-1].y), (5, 3)) >= 2


# ---------------------------------------------------------------------------
# 沉默
# ---------------------------------------------------------------------------


def test_silence_blocks_spells_but_keeps_weapon_skills_and_basic_attacks() -> None:
    # 戰士：挑釁怒吼（法術技，任何武器）與碎骨重擊（武器技）
    state = _scene("hero_fighter", ally_skills=["skill_taunting_roar", CRUSHER], foes=[(4, 3)])

    def skill_ids(s: BattleState) -> set[str]:
        return {a.skill_id for a in legal_actions(s) if isinstance(a, UseSkill)}

    assert skill_ids(state) == {"skill_taunting_roar", CRUSHER}
    _give(state, U1, "silenced", U2)
    assert skill_ids(state) == {CRUSHER}  # 法術技被排除，武器技照常
    assert any(isinstance(a, Attack) for a in legal_actions(state))  # 基本攻擊照常
    with pytest.raises(IllegalActionError, match="沉默"):
        resolve(state, UseSkill(unit_id=U1, skill_id="skill_taunting_roar"))
    # 法師的法術技同樣被排除
    mage = _scene("hero_mage", ally_skills=[FIRE_BOLT], foes=[(4, 3)])
    assert skill_ids(mage) == {FIRE_BOLT}
    _give(mage, U1, "silenced", U2)
    assert skill_ids(mage) == set()


# ---------------------------------------------------------------------------
# 致盲
# ---------------------------------------------------------------------------


def test_blinded_attacks_are_capped_at_two_tiles_and_have_disadvantage() -> None:
    state = _scene("hero_mage", ally_skills=[FIRE_BOLT], foes=[(5, 3), (6, 3)])
    assert attack_problem(state, state.units[U1], state.units[U3]) is None
    _give(state, U1, "blinded", U2)
    assert attack_problem(state, state.units[U1], state.units[U2]) is None  # 距離 2
    assert "致盲" in (attack_problem(state, state.units[U1], state.units[U3]) or "")
    assert advantage_state(state, state.units[U1], state.units[U2]) == "disadvantage"
    targets = {
        (type(a).__name__, a.target_id)
        for a in legal_actions(state)
        if isinstance(a, Attack | UseSkill)
    }
    assert ("Attack", U3) not in targets and ("UseSkill", U3) not in targets
    assert ("Attack", U2) in targets and ("UseSkill", U2) in targets


def test_blinded_unit_still_walks_and_can_end_its_turn() -> None:
    state = _scene("hero_mage", ally_skills=[FIRE_BOLT], foes=[(6, 3)])
    _give(state, U1, "blinded", U2)
    actions = legal_actions(state)
    assert any(isinstance(a, Move) for a in actions) and any(
        isinstance(a, EndTurn) for a in actions
    )


# ---------------------------------------------------------------------------
# 被標記
# ---------------------------------------------------------------------------


def test_marked_targets_are_attacked_with_advantage() -> None:
    state = _scene("hero_archer", foes=[(5, 3)])
    assert advantage_state(state, state.units[U1], state.units[U2]) == "none"
    _give(state, U2, "marked", U1)
    assert advantage_state(state, state.units[U1], state.units[U2]) == "advantage"
    # 隱蔽的劣勢仍在，與優勢抵消
    state.units[U2].statuses = [
        StatusInstance("marked", 2, U1),
        StatusInstance("concealed", 2, None),
    ]
    assert advantage_state(state, state.units[U1], state.units[U2]) == "none"


def test_marked_concealed_targets_can_still_be_selected_at_range() -> None:
    state = _scene("hero_archer", foes=[(6, 3)])
    state.units[U2].statuses = [StatusInstance("concealed", 2, None)]
    assert "隱蔽" in (attack_problem(state, state.units[U1], state.units[U2]) or "")
    state.units[U2].statuses = [
        StatusInstance("concealed", 2, None),
        StatusInstance("marked", 2, U1),
    ]
    assert attack_problem(state, state.units[U1], state.units[U2]) is None


# ---------------------------------------------------------------------------
# preview 與實際一致
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("holder", "status", "expected"),
    [(U1, "feared", "disadvantage"), (U1, "blinded", "disadvantage"), (U2, "marked", "advantage")],
)
def test_preview_matches_the_roll_for_advantage_statuses(
    monkeypatch: pytest.MonkeyPatch, holder: UnitId, status: str, expected: str
) -> None:
    state = _scene("hero_archer", foes=[(4, 3)])
    plain_hit = preview(state, Attack(unit_id=U1, target_id=U2)).hit_chance
    _give(state, holder, status, U1 if holder == U2 else U2)
    hit = preview(state, Attack(unit_id=U1, target_id=U2)).hit_chance
    assert plain_hit is not None and hit is not None
    assert (hit < plain_hit) if expected == "disadvantage" else (hit > plain_hit)
    assert advantage_state(state, state.units[U1], state.units[U2]) == expected
    # 實際擲骰使用同一個優勢狀態：事件記錄的 advantage 與預測相同
    script_rolls(monkeypatch, [19, 19, 3, 3, 3])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    rolled = [e for e in result.events if getattr(e, "advantage", None) is not None]
    assert rolled and rolled[0].advantage == expected  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# mental 控制遞減與 Boss
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["feared", "silenced"])
def test_mental_statuses_use_the_mental_diminishing_window(status: str) -> None:
    state = _scene()
    target = state.units[U2]
    plain = plan_status(state, target, status)
    assert not plain.diminished
    target.control_dr = {"mental": state.round + 2}
    diminished = plan_status(state, target, status)
    attr = library().ruleset.status_def(status).save_attr
    assert attr is not None and diminished.diminished
    core = library().ruleset.core
    assert diminished.defense_value == plain.defense_value * core.control_dr_resist_permille // 1000
    # 其他類別的視窗不影響 mental，mental 的視窗也不影響 blinded（沒有控制類別）
    target.control_dr = {"movement": state.round + 2, "hard": state.round + 2}
    assert not plan_status(state, target, status).diminished
    target.control_dr = {"mental": state.round + 2}
    assert not plan_status(state, target, "blinded").diminished


def test_applying_a_mental_status_records_the_window() -> None:
    state = _scene()
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="feared", source_id=U1)])
    assert result.state.units[U2].control_dr == {"mental": state.round + 2}


@pytest.mark.parametrize("status", ["feared", "silenced"])
def test_bosses_do_not_convert_mental_statuses(status: str) -> None:
    rules = library().ruleset
    assert rules.status_def(status).control_group == "mental"
    boss = _scene().units[U2]
    boss.tags = (*boss.tags, "boss")
    assert boss_converted_status(rules, boss, status) == status
    assert not plan_status(_scene(), boss, status).converted
    assert boss_converted_status(rules, boss, "stun") == "slow"  # 對照：hard 仍然轉換


# ---------------------------------------------------------------------------
# AI：沉默只對有法術技的敵人有價值
# ---------------------------------------------------------------------------

HUSH = "skill_hush"


def _hush_score(foe_template_skills: list[str], mana: int = 99) -> Fraction:
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(4, 3)])
    foe = caster_template(foe_template_skills, base="hero_mage")
    foe = foe.model_copy(update={"max_mana": mana})
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 3), caster_template([HUSH], base="hero_mage")),
            spawn(Team.ENEMY, (4, 3), foe),
        ],
    )
    state = give_turn(state, U1)
    ranked = UtilityAI(library().ai_profiles).rank_all(state)
    return max(
        (s.score for s in ranked if isinstance(s.action, UseSkill) and s.action.skill_id == HUSH),
        default=Fraction(-1),
    )


def test_cunning_ai_silences_a_spellcaster_but_not_a_unit_without_spells() -> None:
    assert _hush_score([FIRE_BOLT]) > 0
    assert _hush_score([]) <= 0  # 沒有法術技：沉默毫無價值（技能還要扣法力與冷卻成本）
    assert _hush_score([FIRE_BOLT], mana=0) <= 0  # 法力不足以施放任何法術技，同樣無價值
