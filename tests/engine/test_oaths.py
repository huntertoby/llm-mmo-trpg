"""誓約的戰鬥判定（Phase 5C-3；``trpg.engine.oaths``，``docs/phases/Phase5計畫.md`` 24.6）。

- 開場掛上加成；違反時（只違反一次）移除加成、施加破誓 2 回合並發 ``oath_broken``。
- 戰鬥結束時才判的種類（每場至少……）沒達到 → ``oath_broken``（``at_end``，沒有效果）。
- 行為一致（規則句實際跑引擎）：自動對戰的事件裡第一個違反的事件之後才有 ``oath_broken``。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.content.world_oaths import OathCheck
from trpg.engine import EndTurn, build_setup, resolve
from trpg.engine.actions import Action, Move, SetReactionMode
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle, legal_actions
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    OathBroken,
    ReactionModeSet,
    ReactionTriggered,
    SkillUsed,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
)
from trpg.engine.oaths import ELEMENT_EXEMPT_CAUSES, OathSetup
from trpg.engine.preview import preview
from trpg.engine.runner import run_battle
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

BONUS = "oath_bonus_medium"
PENALTY = "oath_broken"


def _setup(check: OathCheck | None, allies: Sequence[str] = DEMO_ALLIES) -> BattleSetup:
    setup = build_setup(library(), "test_flat_6x6", allies, DEMO_ENEMIES, max_rounds=30)
    if check is None:
        return setup
    oath = OathSetup(
        template="oath_test",
        check=check,
        bonus_status=BONUS,
        penalty_status=PENALTY,
        penalty_rounds=2,
    )
    return setup.model_copy(update={"oath": oath})


def _holder(state: BattleState) -> UnitId:
    assert state.oath is not None
    return state.oath.holder


def _to_holder_turn(state: BattleState) -> BattleState:
    """其他單位一律結束回合，直到輪到帶誓約的單位。"""
    holder = _holder(state)
    for _ in range(50):
        if state.active_unit == holder:
            return state
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    raise AssertionError("輪不到帶誓約的單位")


def _broken(events: Sequence[EventBase]) -> list[OathBroken]:
    return [e for e in events if isinstance(e, OathBroken)]


def test_bonus_applied_at_open_and_none_without_oath() -> None:
    plain = begin_battle(_setup(None), 1).state
    assert plain.oath is None
    assert not any(u.has_status(BONUS) for u in plain.units_sorted())
    state = begin_battle(_setup(OathCheck(kind="attack_each_turn")), 1).state
    holder = state.units[_holder(state)]
    assert holder.team is Team.ALLY and holder.has_status(BONUS)
    status = holder.get_status(BONUS)
    assert status is not None and status.remaining is None  # 不倒數
    others = [u for u in state.units_sorted() if u.id != holder.id]
    assert not any(u.has_status(BONUS) for u in others)


@pytest.mark.parametrize("kind", ["attack_each_turn", "end_turn_high"])
def test_ending_turn_breaks_once(kind: str) -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind=kind)), 2).state)  # type: ignore[arg-type]
    holder = _holder(state)
    result = resolve(state, EndTurn(unit_id=holder))
    (broken,) = _broken(result.events)
    assert (broken.unit_id, broken.check, broken.at_end) == (holder, kind, False)
    unit = result.state.units[holder]
    assert not unit.has_status(BONUS)
    penalty = unit.get_status(PENALTY)
    assert penalty is not None and penalty.remaining == 2
    removed = [e for e in result.events if isinstance(e, StatusRemoved) and e.status_id == BONUS]
    assert removed and removed[0].seq > broken.seq
    again = resolve(_to_holder_turn(result.state), EndTurn(unit_id=holder))
    assert not _broken(again.events)  # 同一場只違反一次


def test_end_turn_off_surface_kept_on_plain_ground() -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind="end_turn_off_surface")), 2).state)
    result = resolve(state, EndTurn(unit_id=_holder(state)))
    assert not _broken(result.events)
    assert result.state.units[_holder(state)].has_status(BONUS)


def _moves(state: BattleState, holder: UnitId) -> list[Move]:
    return [
        a
        for a in legal_actions(state)
        if isinstance(a, Move) and a.unit_id == holder and len(a.path) == 2
    ]


def _nearest(state: BattleState, xy: tuple[int, int], team: Team) -> int:
    return min(
        abs(u.xy[0] - xy[0]) + abs(u.xy[1] - xy[1])
        for u in state.units_sorted()
        if u.alive and u.team is not team
    )


def test_no_move_first_turn() -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind="no_move_first_turn")), 3).state)
    holder = _holder(state)
    move = _moves(state, holder)[0]
    result = resolve(state, move)
    (broken,) = _broken(result.events)
    assert broken.check == "no_move_first_turn"


def test_no_retreat_breaks_only_when_moving_away() -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind="no_retreat")), 3).state)
    holder = _holder(state)
    team = state.units[holder].team
    here = _nearest(state, state.units[holder].xy, team)
    closer = [
        m for m in _moves(state, holder) if _nearest(state, (m.dest.x, m.dest.y), team) < here
    ]
    assert closer
    stepped = resolve(state, closer[0])
    assert not _broken(stepped.events)
    moved = stepped.state
    there = _nearest(moved, moved.units[holder].xy, team)
    away = [m for m in _moves(moved, holder) if _nearest(moved, (m.dest.x, m.dest.y), team) > there]
    assert away
    assert _broken(resolve(moved, away[0]).events)


def test_solo_breaks_at_open_with_allies_only() -> None:
    with_allies = begin_battle(_setup(OathCheck(kind="solo")), 1)
    (broken,) = _broken(with_allies.events)
    holder = with_allies.state.units[broken.unit_id]
    assert not holder.has_status(BONUS) and holder.has_status(PENALTY)
    alone = begin_battle(_setup(OathCheck(kind="solo"), allies=DEMO_ALLIES[:1]), 1)
    assert not _broken(alone.events)
    assert alone.state.units[_holder(alone.state)].has_status(BONUS)


@pytest.mark.parametrize(
    "check",
    [
        OathCheck(kind="min_melee_kills", count=99),
        OathCheck(kind="min_status_applied", status="burning", count=99),
    ],
)
def test_at_end_checks_record_without_effect(check: OathCheck) -> None:
    run = run_battle(_setup(check), 4)
    assert run.state.ended
    (broken,) = _broken(run.events)
    assert broken.at_end and broken.check == check.kind
    after = [e for e in run.events if e.seq > broken.seq]
    assert not any(isinstance(e, StatusApplied) and e.status_id == PENALTY for e in after)


def test_at_end_reached_is_kept() -> None:
    run = run_battle(_setup(OathCheck(kind="min_melee_kills", count=0)), 4)
    assert not _broken(run.events)


# ---------------------------------------------------------------------------
# 行為一致：自動對戰的事件裡，第一個違反的事件之後才有 oath_broken（每種戰鬥中判定）
# ---------------------------------------------------------------------------

Oracle = Callable[[BattleState, UnitId, EventBase], bool]


def _skill_oracle(test: Callable[[set[str], str], bool]) -> Oracle:
    def oracle(state: BattleState, holder: UnitId, event: EventBase) -> bool:
        if not isinstance(event, SkillUsed) or event.unit_id != holder:
            return False
        skill = state.ruleset.skill_def(event.skill_id)
        return test(set(skill.tags), skill.category)

    return oracle


def _element_oracle(state: BattleState, holder: UnitId, event: EventBase) -> bool:
    return (
        isinstance(event, DamageDealt)
        and event.source_id == holder
        and event.amount > 0
        and event.cause not in ELEMENT_EXEMPT_CAUSES
        and str(event.element) != "fire"
    )


def _ally_oracle(state: BattleState, holder: UnitId, event: EventBase) -> bool:
    if not isinstance(event, UnitDowned) or event.unit_id == holder:
        return False
    unit = state.units.get(event.unit_id)
    return unit is not None and unit.team is Team.ALLY and not unit.is_summon


MAGE = 2
"""``DEMO_ALLIES`` 裡的法師（會用法術技能）；0 是戰士（會用武器技）。"""

CASES: list[tuple[OathCheck, int, Oracle]] = [
    (
        OathCheck(kind="forbid_skill_tag", tags=("fire",)),
        MAGE,
        _skill_oracle(lambda t, _c: "fire" in t),
    ),
    (
        OathCheck(kind="forbid_skill_tag_until_hp", tags=("fire",), hp_permille=500),
        MAGE,
        _skill_oracle(lambda t, _c: "fire" in t),  # 法師整場 HP 都在一半以上時第一次用就違反
    ),
    (
        OathCheck(kind="forbid_skill_category", category="spell"),
        MAGE,
        _skill_oracle(lambda _t, c: c == "spell"),
    ),
    (
        OathCheck(kind="forbid_skill_category", category="weapon"),
        0,
        _skill_oracle(lambda _t, c: c == "weapon"),
    ),
    (OathCheck(kind="damage_element_only", element="fire"), 0, _element_oracle),
    (OathCheck(kind="protect_allies"), 0, _ally_oracle),
]


@pytest.mark.parametrize(
    ("check", "unit", "oracle"), CASES, ids=[f"{c.kind}-{i}" for i, (c, _u, _o) in enumerate(CASES)]
)
@pytest.mark.parametrize("seed", [0, 6])
def test_auto_battle_breaks_after_first_violation(
    check: OathCheck, unit: int, oracle: Oracle, seed: int
) -> None:
    setup = _setup(check)
    assert setup.oath is not None
    setup = setup.model_copy(update={"oath": setup.oath.model_copy(update={"unit": unit})})
    policy = UtilityAI(library().ai_profiles)
    run = run_battle(setup, seed, policy)
    state = run.state
    holder = _holder(state)
    first = next((e for e in run.events if oracle(state, holder, e)), None)
    broken = _broken(run.events)
    assert first is not None, "這組測試要真的違反"
    assert len(broken) == 1 and broken[0].seq > first.seq
    assert not broken[0].at_end
    again = run_battle(setup, seed, policy)  # 確定性
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


# ---------------------------------------------------------------------------
# 5C-3b：帶到下一場的破誓、不使用反應自動關閉、按下前警告
# ---------------------------------------------------------------------------


def _with(check: OathCheck, **update: object) -> BattleSetup:
    setup = _setup(check)
    assert setup.oath is not None
    return setup.model_copy(update={"oath": setup.oath.model_copy(update=update)})


def test_start_penalty_applies_at_open_and_bonus_stays() -> None:
    opened = begin_battle(_with(OathCheck(kind="attack_each_turn"), start_penalty_rounds=2), 1)
    holder = opened.state.units[_holder(opened.state)]
    assert holder.has_status(BONUS)  # 下一場的誓約加成照常
    penalty = holder.get_status(PENALTY)
    assert penalty is not None and penalty.remaining == 2
    assert not _broken(opened.events)  # 開場帶的破誓不是這場的違反
    assert opened.state.oath is not None and not opened.state.oath.broken


def test_no_reactions_oath_turns_reactions_off_at_open() -> None:
    plain = begin_battle(_setup(None), 1).state
    assert any(r.mode != "off" for u in plain.units_sorted() for r in u.reactions)
    opened = begin_battle(_setup(OathCheck(kind="forbid_reaction")), 1)
    holder = opened.state.units[_holder(opened.state)]
    assert holder.reactions and all(r.mode == "off" for r in holder.reactions)
    assert any(isinstance(e, ReactionModeSet) for e in opened.events)
    others = [u for u in opened.state.units_sorted() if u.id != holder.id]
    assert any(r.mode != "off" for u in others for r in u.reactions)  # 只關持有者


def test_turning_reactions_back_on_warns_and_setting_itself_is_not_a_breach() -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind="forbid_reaction")), 1).state)
    holder = state.units[_holder(state)]
    action = SetReactionMode(unit_id=holder.id, reaction=holder.reactions[0].reaction, mode="auto")
    warning = preview(state, action).oath_warning
    assert warning is not None and warning.startswith("會違反誓約")
    assert preview(state, EndTurn(unit_id=holder.id)).oath_warning is None
    reopened = resolve(state, action).state
    assert reopened.oath is not None and not reopened.oath.broken


def test_preview_warns_before_the_violation_and_matches_the_real_result() -> None:
    state = _to_holder_turn(begin_battle(_setup(OathCheck(kind="attack_each_turn")), 2).state)
    end = EndTurn(unit_id=_holder(state))
    warning = preview(state, end).oath_warning
    assert warning is not None and warning.startswith("會違反誓約「oath_test」")
    assert _broken(resolve(state, end).events)  # 引擎的警告與真正結算一致
    quiet = begin_battle(_setup(None), 2).state
    assert quiet.active_unit is not None
    assert preview(quiet, EndTurn(unit_id=quiet.active_unit)).oath_warning is None
    broken = resolve(state, end).state  # 已經違反：不再警告
    assert preview(_to_holder_turn(broken), end).oath_warning is None


def test_reactions_stay_off_in_auto_battle_and_reopening_then_triggering_breaks() -> None:
    inner = UtilityAI(library().ai_profiles)
    triggered = 0
    for seed in range(6):
        setup = _setup(OathCheck(kind="forbid_reaction"))
        quiet = run_battle(setup, seed, inner)
        assert not _broken(quiet.events)  # 反應設定被關掉，不會觸發
        holder = _holder(quiet.state)
        assert not any(
            isinstance(e, ReactionTriggered) and e.unit_id == holder for e in quiet.events
        )

        def reopen(state: BattleState, holder: UnitId = holder) -> Action:
            unit = state.units[holder]
            for rule in unit.reactions:
                if rule.mode == "off":
                    return SetReactionMode(unit_id=holder, reaction=rule.reaction, mode="auto")
            return inner(state)

        run = run_battle(setup, seed, inner, controllers={holder: reopen})
        first = next(
            (e for e in run.events if isinstance(e, ReactionTriggered) and e.unit_id == holder),
            None,
        )
        broken = _broken(run.events)
        if first is None:
            assert not broken
            continue
        triggered += 1
        assert len(broken) == 1 and broken[0].seq > first.seq
    assert triggered > 0, "這組測試要真的有觸發反應的情形"
