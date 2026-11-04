"""任意動作的分支推演（Phase 7 前置，:mod:`trpg.engine.branching`）與檢定覆寫（``CheckOverride``）。

- ``CheckOverride`` 只能用在預覽；``check_d20``／``opposed_d20`` 的覆寫語意與
  ``min``／``max`` 相同。
- 非移動動作的分支：推人進冰面（``surface``）；移動踩陷阱的抵抗（``status_save``）與冰面組合。
- 分支上限與截斷；確定性（相同輸入相同預覽、不動 ``rng_state``）。
- 行為一致：每個分支的檢定結果、位置與狀態，都有某個種子的實際結算走得到。
- 新舊路徑預覽一致：``preview_path`` 的分支＝ 6E-2b／6P-1 的舊分支清單（隨機 120 組情境）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn
from trpg.engine import BattleState, Move, resolve
from trpg.engine.actions import Action, Shove
from trpg.engine.battle import simulate_branch, simulate_preview
from trpg.engine.branching import ActionPreview, PreviewBranch, preview_action
from trpg.engine.context import CheckKind, CheckOverride, Ctx
from trpg.engine.events import CheckRolled, EventBase, ManeuverRolled, StatusSaveRolled
from trpg.engine.ids import PRONE
from trpg.engine.results import ResolveResult
from trpg.engine.state import TrapState, state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")

type XY = tuple[int, int]


def _pos(path: Sequence[XY]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in path)


def _trap(state: BattleState, xy: XY, skill: str = "skill_bear_trap") -> BattleState:
    s = state.clone()
    owner = next(u.id for u in s.units.values() if u.team is Team.ENEMY)
    s.traps = [
        *s.traps,
        TrapState(
            owner_id=owner,
            team=Team.ENEMY,
            pos=Pos(x=xy[0], y=xy[1]),
            skill_id=skill,
            remaining=3,
            attributes=tuple((a, 10) for a in Attribute),
            revealed_to=(Team.ALLY,),
        ),
    ]
    return s


def _shove_state(seed: int = 0) -> BattleState:
    """英雄在 (1, 0)、盜賊在 (2, 0)，盜賊身後 (3, 0) 是冰：推過去要擲冰面檢定（被推進表面）。"""
    m = make_map("00000\n00000", surfaces=[(3, 0, "ice")], ally=[(1, 0)], enemy=[(2, 0)])
    spawns = [spawn(Team.ALLY, (1, 0), "hero_fighter"), spawn(Team.ENEMY, (2, 0), "bandit")]
    return give_turn(make_state(m, spawns, seed=seed), U1)


def _ice_trap_state(seed: int = 0) -> BattleState:
    """(1, 0) 是冰、(2, 1) 是看得見的捕獸夾（傷害＋定身，定身要擲抵抗）。"""
    m = make_map("000000\n000000\n000000", surfaces=[(1, 0, "ice")], enemy=[(5, 2)])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (5, 2), "bandit")]
    return _trap(give_turn(make_state(m, spawns, seed=seed), U1), (2, 1))


_ICE_TRAP_PATH = _pos(((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)))


# ---------------------------------------------------------------------------
# CheckOverride
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override",
    [CheckOverride(), CheckOverride.of(rest="best"), CheckOverride.worst_at(0, ("status_save",))],
)
def test_check_override_is_blocked_in_formal_resolution(override: CheckOverride) -> None:
    with pytest.raises(ValueError, match="check_override"):
        Ctx(_shove_state(), check_override=override)
    assert Ctx(_shove_state(), preview="min", check_override=override).check_override is override


def test_check_override_follows_min_max_d20_semantics() -> None:
    """``best``＝``min`` 的結果、``worst``＝``max`` 的結果；依規則的種類與 reason 計數。"""
    override = CheckOverride.of(("status_save",), reason="status:root", outcomes=("worst",))
    ctx = Ctx(_shove_state(), preview="min", check_override=override)
    assert ctx.opposed_d20("status_save", "status:stun") == 1  # reason 不符：照 min
    assert ctx.opposed_d20("status_save", "status:root") == 20  # 第 0 次：worst
    assert ctx.opposed_d20("status_save", "status:root") == 1  # 之後照 min
    assert ctx.check_d20("surface", "surface:ice") == 20  # 種類不符：照 min
    assert [(c.kind, c.outcome, c.forced) for c in ctx.check_log] == [
        ("status_save", "best", False),
        ("status_save", "worst", True),
        ("status_save", "best", False),
        ("surface", "best", False),
    ]
    best = Ctx(_shove_state(), preview="max", check_override=CheckOverride.of(rest="best"))
    assert best.check_d20("slide", "surface:ice") == 20
    assert best.opposed_d20("contest", "contest:trip") == 1
    plain = Ctx(_shove_state(), preview="max")
    assert (plain.check_d20("surface", "x"), plain.opposed_d20("status_save", "y")) == (1, 20)


def test_formal_resolution_does_not_log_checks_and_previews_do_not_touch_rng() -> None:
    state = _ice_trap_state(3)
    before = state_to_json(state)
    first = resolve(state, Move(unit_id=U1, path=_ICE_TRAP_PATH))
    a = preview_action(state, Move(unit_id=U1, path=_ICE_TRAP_PATH))
    b = preview_action(state, Move(unit_id=U1, path=_ICE_TRAP_PATH))
    assert state_to_json(state) == before
    assert _dump(a) == _dump(b)  # 相同輸入、相同預覽
    again = resolve(state, Move(unit_id=U1, path=_ICE_TRAP_PATH))
    assert repr(first.events) == repr(again.events)
    assert state_to_json(first.state) == state_to_json(again.state)


# ---------------------------------------------------------------------------
# 非移動動作的分支
# ---------------------------------------------------------------------------


def test_shove_into_ice_branches_on_the_pushed_units_check() -> None:
    p = preview_action(_shove_state(), Shove(unit_id=U1, target_id=U2))
    assert not p.certain and not p.truncated
    kinds = {(c.kind, c.reason, c.unit_id) for b in p.branches for c in b.checks}
    assert kinds == {("surface", "surface:ice", U2)}
    prone = {b.result.state.units[U2].has_status(PRONE) for b in p.branches}
    assert prone == {True, False}
    by_key = {(b.mode, b.worst): b for b in p.branches[2:]}
    assert sorted(by_key, key=repr) == sorted([("max", ()), ("min", (0,)), ("max", (0,))], key=repr)
    assert by_key["min", (0,)].result.state.units[U2].has_status(PRONE)
    assert not by_key["max", ()].result.state.units[U2].has_status(PRONE)
    assert all(b.result.state.units[U2].xy == (3, 0) for b in p.branches)  # 推擊本身視為成功


def test_move_through_ice_and_trap_covers_every_combination() -> None:
    """冰面（slide）× 陷阱抵抗（status_save）：舊的路徑預覽只分冰面，這裡兩種都分。"""
    p = preview_action(_ice_trap_state(), Move(unit_id=U1, path=_ICE_TRAP_PATH))
    combos = {_check_outcomes(b) for b in p.branches}
    assert {("slide", "best"), ("status_save", "worst")} in combos  # 過了冰、被定身
    assert {("slide", "best"), ("status_save", "best")} in combos  # 過了冰、抵抗成功
    assert {("slide", "worst")} in combos  # 冰面滑倒（沒走到陷阱）
    stops = {b.result.state.units[U1].xy for b in p.branches}
    assert stops == {(2, 2), (2, 1), (2, 0)}


def test_branches_are_reachable_by_real_resolution() -> None:
    """每個分支的檢定結果、單位位置與狀態，都有某個種子的實際結算走得到。"""
    cases: list[tuple[Callable[[int], BattleState], Action]] = [
        (_shove_state, Shove(unit_id=U1, target_id=U2)),
        (_ice_trap_state, Move(unit_id=U1, path=_ICE_TRAP_PATH)),
    ]
    for build, action in cases:
        p = preview_action(build(0), action)
        real = {_signature(resolve(build(seed), action)) for seed in range(200)}
        for branch in p.branches:
            assert _signature(branch.result) in real, (branch.mode, branch.worst)


# ---------------------------------------------------------------------------
# 分支上限
# ---------------------------------------------------------------------------


def test_branch_limit_truncates_in_order() -> None:
    state, move = _ice_trap_state(), Move(unit_id=U1, path=_ICE_TRAP_PATH)
    full = preview_action(state, move)
    assert not full.truncated and len(full.branches) > 4
    cut = preview_action(state, move, limit=3)
    assert cut.truncated and len(cut.branches) == 2 + 3
    assert _dump(cut) == _dump(full)[:5]  # 照「最差次數少的先」的順序保留前段
    assert [len(b.worst or ()) for b in full.branches[2:]] == sorted(
        len(b.worst or ()) for b in full.branches[2:]
    )
    extremes = preview_action(state, move, limit=0)
    assert extremes.truncated and extremes.results == extremes.results[:2]
    assert len(extremes.branches) == 2  # 兩個極端一定在


def test_certain_action_has_no_branches() -> None:
    state = _ice_trap_state()
    p = preview_action(state, Move(unit_id=U1, path=_pos(((0, 0), (0, 1)))))
    assert p.certain and not p.truncated and p.low is p.high and len(p.branches) == 2


# ---------------------------------------------------------------------------
# 新舊路徑預覽一致：preview_path 用 kinds=("slide",) 的分支＝ 6E-2b／6P-1 的舊分支清單
# ---------------------------------------------------------------------------


def _legacy_branches(state: BattleState, move: Move) -> list[ResolveResult]:
    """舊的路徑預覽（6E-2b／6P-1）的分支：最少、最多後果；最少後果擲了 N 次（移動者的）滑行檢定
    時，再加全部通過 × 最多後果，與第 k 次失敗 × 最少／最多後果。"""
    low, high = simulate_preview(state, move)
    if low is high:
        return [low, high]
    n = sum(
        isinstance(e, CheckRolled) and e.slide and e.unit_id == move.unit_id for e in low.events
    )
    if n == 0:
        return [low, high]
    slide: tuple[CheckKind, ...] = ("slide",)
    out = [
        low,
        high,
        simulate_branch(state, move, "max", override=CheckOverride.of(slide, rest="best"))[0],
    ]
    for k in range(n):
        out.append(simulate_branch(state, move, override=CheckOverride.worst_at(k, slide))[0])
        failed = CheckOverride.worst_at(k, slide, rest="best")
        out.append(simulate_branch(state, move, "max", override=failed)[0])
    return out


def _random_move(i: int) -> tuple[BattleState, Move]:
    r = Rng(i)
    w, h = 6, 3
    tiles = [(x, y) for y in range(h) for x in range(w) if (x, y) != (0, 0)]
    tiles = r.shuffled(tiles)
    enemy = tiles[0]
    surfaces = [
        (x, y, r.choice(("ice", "ice", "oil", "water"))) for x, y in tiles[1 : r.randint(2, 6)]
    ]
    m = make_map("\n".join("0" * w for _ in range(h)), surfaces=surfaces, enemy=[enemy])
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, enemy, "bandit")]
    state = give_turn(make_state(m, spawns, seed=i), U1)
    for xy in tiles[6 : 6 + r.randint(0, 2)]:
        state = _trap(state, xy, r.choice(("skill_bear_trap", "skill_venom_pit")))
    path = [(0, 0)]
    for _ in range(r.randint(2, 6)):
        x, y = path[-1]
        dx, dy = r.choice(((1, 0), (0, 1), (1, 0), (0, -1)))
        nxt = (min(max(x + dx, 0), w - 1), min(max(y + dy, 0), h - 1))
        if nxt != enemy and nxt not in path:
            path.append(nxt)
    return state, Move(unit_id=U1, path=_pos(path))


def test_path_preview_branches_match_the_legacy_branches() -> None:
    compared = with_ice = 0
    for i in range(400):
        state, move = _random_move(i)
        try:
            legacy = _legacy_branches(state, move)
        except IllegalActionError:  # 不合法的隨機路徑：新舊都要拋出
            with pytest.raises(IllegalActionError):
                preview_action(state, move, kinds=("slide",))
            continue
        new = preview_action(state, move, kinds=("slide",)).results
        assert [_dump_result(r) for r in new] == [_dump_result(r) for r in legacy], i
        compared += 1
        with_ice += len(legacy) > 2
        if compared >= 120 and with_ice >= 20:
            break
    assert compared >= 120 and with_ice >= 20


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _dump_result(r: ResolveResult) -> tuple[str, str]:
    return repr(r.events), state_to_json(r.state)


def _dump(p: ActionPreview) -> list[tuple[str, object, str, str]]:
    return [(b.mode, b.worst, *_dump_result(b.result)) for b in p.branches]


def _check_outcomes(branch: PreviewBranch) -> frozenset[tuple[str, str]]:
    return frozenset((c.kind, c.outcome) for c in branch.checks)


def _check_results(events: Sequence[EventBase]) -> tuple[tuple[str, bool], ...]:
    """實際結算與預覽共用的檢定結果（守方的角度：``True`` 為守方有利）。推擊本身不算。"""
    out: list[tuple[str, bool]] = []
    for e in events:
        if isinstance(e, CheckRolled):
            out.append((e.reason, e.success))
        elif isinstance(e, StatusSaveRolled):
            out.append((f"status:{e.status_id}", not e.applied))
        elif isinstance(e, ManeuverRolled) and e.skill_id is not None:
            out.append((f"contest:{e.maneuver}", not e.success))
    return tuple(out)


def _signature(r: ResolveResult) -> tuple[object, ...]:
    units = tuple(
        (u.id, u.xy, u.alive, tuple(sorted(s.status_id for s in u.statuses)))
        for u in r.state.units_sorted()
    )
    shoved = tuple(
        e.success for e in r.events if isinstance(e, ManeuverRolled) and e.skill_id is None
    )
    return units, _check_results(r.events), shoved
