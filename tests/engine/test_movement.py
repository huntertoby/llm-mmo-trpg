"""移動、爬升、墜落與路徑（驗收條件 6）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, spawn, template
from trpg.engine import Attack, BattleState, Move, legal_actions, resolve
from trpg.engine.battle import _move_interrupted
from trpg.engine.context import Ctx
from trpg.engine.effects import ApplyStatusEffect, MoveUnitEffect, run_effects
from trpg.engine.events import DamageDealt, StatusRemoved, UnitFell, UnitMoved, UnitStoodUp
from trpg.engine.rules.movement import find_path, reachable_tiles
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1 = UnitId("unit_0001")


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _solo(
    heights: str, pos: tuple[int, int], terrain: str | None = None, **core: Any
) -> BattleState:
    m = make_map(heights, terrain)
    w = len(heights.strip().split("\n")[0])
    h = len(heights.strip().split("\n"))
    hero = spawn(Team.ALLY, pos, template("hero_fighter", max_hp=100))
    foe = spawn(Team.ENEMY, (w - 1, h - 1), "bandit")
    return give_turn(make_state(m, [hero, foe], **core), "unit_0001")


def _move(state: BattleState, *cells: tuple[int, int]) -> BattleState:
    return resolve(state, Move(unit_id=UnitId("unit_0001"), path=tuple(P(*c) for c in cells))).state


def test_climb_costs_extra() -> None:
    state = _solo("01100\n00000", (0, 0))
    s = _move(state, (0, 0), (1, 0), (2, 0), (3, 0))
    # 往上 1 層：1 + 1；同高 1；往下 1
    assert s.units[U1].move_points == 5 - (2 + 1 + 1)
    assert s.units[U1].pos == P(3, 0)


def test_two_levels_up_is_impassable() -> None:
    state = _solo("02000\n00000", (0, 0))
    with pytest.raises(IllegalActionError, match="高度差過大"):
        _move(state, (0, 0), (1, 0))
    assert P(1, 0) not in reachable_tiles(state, UnitId("unit_0001"))


def test_climb_two_levels_in_two_steps() -> None:
    state = _solo("01200\n00000", (0, 0))
    s = _move(state, (0, 0), (1, 0), (2, 0))
    assert s.units[U1].move_points == 1


@pytest.mark.parametrize(
    ("heights", "drop", "levels", "damage"),
    [
        ("10000\n00000", 1, 0, 0),  # 落差 1：不受傷
        ("20000\n00000", 2, 1, 10),  # 落差 2 → 1 層 → 10%
        ("30000\n00000", 3, 2, 20),  # 落差 3 → 2 層 → 20%
    ],
)
def test_fall_damage(heights: str, drop: int, levels: int, damage: int) -> None:
    state = _solo(heights, (0, 0))
    result = resolve(state, Move(unit_id=UnitId("unit_0001"), path=(P(0, 0), P(1, 0))))
    fell = [e for e in result.events if isinstance(e, UnitFell)]
    dealt = [e for e in result.events if isinstance(e, DamageDealt)]
    if levels == 0:
        assert not fell and not dealt
        return
    assert fell[0].drop == drop and fell[0].levels == levels
    assert dealt[0].cause == "fall" and dealt[0].amount == damage
    assert result.state.units[U1].hp == 100 - damage


def test_fall_damage_capped_at_30_percent() -> None:
    # 每層 20% 時，落差 3（2 層）＝ 40% → 上限 30%
    state = _solo("30000\n00000", (0, 0), fall_damage_permille_per_level=200)
    result = resolve(state, Move(unit_id=UnitId("unit_0001"), path=(P(0, 0), P(1, 0))))
    dealt = next(e for e in result.events if isinstance(e, DamageDealt))
    assert dealt.amount == 30


def test_forced_move_down_cliff_also_falls() -> None:
    state = _solo("30000\n00000", (0, 0))
    result = run_effects(state, [MoveUnitEffect(unit_id=UnitId("unit_0001"), dest=(1, 0))])
    assert any(isinstance(e, UnitFell) for e in result.events)
    assert result.state.units[U1].hp == 80


def test_cannot_pass_enemy_can_pass_ally() -> None:
    m = make_map("0000")
    hero = spawn(Team.ALLY, (0, 0), "hero_fighter")
    friend = spawn(Team.ALLY, (1, 0), "hero_mage")
    foe = spawn(Team.ENEMY, (3, 0), "bandit")
    state = give_turn(make_state(m, [hero, friend, foe]), "unit_0001")
    s = _move(state, (0, 0), (1, 0), (2, 0))  # 穿過友方
    assert s.units[U1].pos == P(2, 0)
    with pytest.raises(IllegalActionError, match="不能停在已有單位的格子"):
        _move(state, (0, 0), (1, 0))

    blocked = give_turn(
        make_state(m, [hero, spawn(Team.ENEMY, (1, 0), "bandit"), foe]), "unit_0001"
    )
    with pytest.raises(IllegalActionError, match="被敵方單位 盜賊1 阻擋"):
        _move(blocked, (0, 0), (1, 0), (2, 0))
    assert reachable_tiles(blocked, UnitId("unit_0001")) == {}


def test_cannot_enter_chasm_or_lava() -> None:
    state = _solo("00000\n00000", (0, 0), terrain="0x~00".replace("0", ".") + "\n.....")
    with pytest.raises(IllegalActionError, match="無法進入深淵"):
        _move(state, (0, 0), (1, 0))
    reach = reachable_tiles(state, UnitId("unit_0001"))
    assert P(1, 0) not in reach and P(2, 0) not in reach


def test_move_validation_messages() -> None:
    state = _solo("00000\n00000", (0, 0))
    with pytest.raises(IllegalActionError, match="路徑必須從目前位置"):
        _move(state, (1, 0), (2, 0))
    with pytest.raises(IllegalActionError, match="路徑不連續"):
        _move(state, (0, 0), (2, 0))
    with pytest.raises(IllegalActionError, match="超出地圖範圍"):
        _move(state, (0, 0), (0, 1), (0, 2))
    with pytest.raises(IllegalActionError, match="路徑至少要移動一格"):
        _move(state, (0, 0))
    with pytest.raises(IllegalActionError, match="移動點數不足：需要 6，剩餘 5"):
        _move(state, (0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (2, 1), (1, 1))


def test_move_is_split_around_attack() -> None:
    m = make_map("00000\n00000")
    hero = spawn(Team.ALLY, (0, 0), "hero_fighter")
    foe = spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=500))
    state = give_turn(make_state(m, [hero, foe]), "unit_0001")
    s = _move(state, (0, 0), (1, 0))
    s = resolve(s, Attack(unit_id=UnitId("unit_0001"), target_id=UnitId("unit_0002"))).state
    s = _move(s, (1, 0), (1, 1), (2, 1))
    assert s.units[U1].move_points == 2
    assert s.units[U1].ap == 2


def test_find_path_is_deterministic_with_fixed_tie_break() -> None:
    state = _solo("00000\n00000\n00000\n00000", (0, 0))  # 敵人在 (4, 3)
    uid = UnitId("unit_0001")
    path = find_path(state, uid, P(2, 2))
    # 同成本時依「上、右、下、左」的發現順序：先往右走到底再往下
    assert path == [P(0, 0), P(1, 0), P(2, 0), P(2, 1), P(2, 2)]
    assert all(find_path(state, uid, P(2, 2)) == path for _ in range(5))
    # legal_actions 的代表路徑與 find_path 一致
    moves = [a for a in legal_actions(state) if isinstance(a, Move) and a.dest == P(2, 2)]
    assert [list(m.path) for m in moves] == [path]
    # 有單位的格子、目前位置、超出點數的格子：None
    assert find_path(state, uid, P(4, 3)) is None
    assert find_path(state, uid, P(0, 0)) is None
    assert find_path(state, uid, P(4, 2)) is None  # 成本 6 > 5
    assert find_path(state, uid, P(4, 2), unlimited=True) is not None


def test_reachable_respects_budget_and_is_sorted() -> None:
    state = _solo("0000000\n0000000", (0, 0))
    reach = reachable_tiles(state, UnitId("unit_0001"))
    assert all(cost <= 5 for cost in reach.values())
    assert P(5, 0) in reach and P(6, 0) not in reach
    keys = list(reach)
    assert keys == sorted(keys, key=lambda p: (p.y, p.x))


def test_prone_stand_up_costs_half_movement() -> None:
    state = _solo("000000\n000000", (0, 0))
    state = run_effects(
        state, [ApplyStatusEffect(target_id=UnitId("unit_0001"), status_id="prone")]
    ).state
    reach = reachable_tiles(state, UnitId("unit_0001"))
    assert max(reach.values()) == 2  # 速度 5，站起消耗 ceil(2.5) = 3
    result = resolve(state, Move(unit_id=UnitId("unit_0001"), path=(P(0, 0), P(1, 0), P(2, 0))))
    assert any(isinstance(e, UnitStoodUp) and e.cost == 3 for e in result.events)
    assert any(isinstance(e, StatusRemoved) and e.reason == "stood_up" for e in result.events)
    unit = result.state.units[U1]
    assert not unit.has_status("prone") and unit.move_points == 0
    with pytest.raises(IllegalActionError, match="移動點數不足：需要 6，剩餘 5"):
        resolve(state, Move(unit_id=UnitId("unit_0001"), path=(P(0, 0), P(1, 0), P(2, 0), P(3, 0))))
    # 只站起來
    stand = Move(unit_id=UnitId("unit_0001"), path=(P(0, 0),))
    assert stand in legal_actions(state)
    only = resolve(state, stand)
    assert only.state.units[U1].move_points == 2
    assert not any(isinstance(e, UnitMoved) for e in only.events)


# ---------------------------------------------------------------------------
# Phase 2F-1 3.3：_do_move 的通用中斷條件
# ---------------------------------------------------------------------------
#
# 舊版只在「有陷阱、且事件清單裡出現 TrapTriggered」時才檢查定身／暈眩，不管單位這一步結束後
# 的實際位置是不是真的等於預期格。_move_interrupted 把它換成一個通用條件：位置偏離預期格
# （途中被推離），或單位定身／暈眩／倒地／死亡／逃離。
#
# 待 PM 決定：規格要求的新測試是「陷阱附帶推擊」。但推擊效果的方向是以範圍技能的原點（中心
# 格型即中心格）往外算（trpg.engine.skills.primitives.displacement._displace_direction）；
# 「enter」陷阱觸發時，踩中它的單位必定剛好站在陷阱格——也就是推擊的原點本身，位移向量恒為
# (0, 0)，不會產生任何推擊（這是既有、刻意的設計：以中心為準的範圍技能不能把站在中心上的
# 目標推開自己；
# 也確認過：合法的 Move 不可能走進致命地形讓引擎的「精英傳送到安全格」機制間接產生位移，
# 因為 plan_move／is_standable 一開始就不允許規劃這種路徑步）。因此沒有辦法用合法的技能組合
# 讓陷阱推開「踩中它」的單位本身；底下直接測試 _move_interrupted 這段通用條件本身（覆蓋「被
# 推離預期格」「定身」「暈眩」「死亡」四種中斷原因，以及正常情況不中斷），作為等價的驗證。
# 是否要新增一個不以中心為原點的陷阱推擊效果，留給 PM 決定。


def _move_scene() -> tuple[BattleState, Ctx]:
    state = _solo("00000\n00000", (0, 0))
    ctx = Ctx(state.clone())
    return state, ctx


def test_move_interrupted_is_false_when_the_unit_arrived_as_planned() -> None:
    _, ctx = _move_scene()
    unit = ctx.state.units[U1]
    unit.pos = P(1, 0)
    assert not _move_interrupted(ctx, unit, (1, 0))


def test_move_interrupted_is_true_when_pushed_off_the_planned_step() -> None:
    """位置不等於這一步的預期格（例如被某個效果推離）：中止，不會被下一步拉回原路徑。"""
    _, ctx = _move_scene()
    unit = ctx.state.units[U1]
    unit.pos = P(1, 1)  # 這一步原本預期走到 (1, 0)，但實際位置是 (1, 1)
    assert _move_interrupted(ctx, unit, (1, 0))


def test_move_interrupted_is_true_when_rooted_or_stunned() -> None:
    state, ctx = _move_scene()
    unit = ctx.state.units[U1]
    unit.pos = P(1, 0)
    rooted = run_effects(
        state, [ApplyStatusEffect(target_id=U1, status_id="root", duration=1)]
    ).state
    ctx.state.units[U1].statuses = rooted.units[U1].statuses
    assert _move_interrupted(ctx, unit, (1, 0))


def test_move_interrupted_is_true_when_downed_or_escaped() -> None:
    _, ctx = _move_scene()
    unit = ctx.state.units[U1]
    unit.pos = P(1, 0)
    unit.downed = True
    unit.hp = 0
    assert _move_interrupted(ctx, unit, (1, 0))
