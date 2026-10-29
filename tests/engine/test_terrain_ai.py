"""純地形技能的 AI（Phase 3T-5）：隆起／下陷的收益、無收益不施放、坑旁推擊、整場重播。

地面高度為 0 的格子降不下去，所以場景預設是高度 1 的平地（``HILL``）。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import SID, U1
from trpg.content.skills import SkillDef
from trpg.engine import Action, BattleSetup, BattleState, UseSkill
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.events import TerrainChanged
from trpg.engine.runner import replay, run_battle
from trpg.shared.types import Pos, Team

HILL = "\n".join(["1111111"] * 7)
CROSS = {"type": "cross", "range": 5}
SQUARE = {"type": "square3", "range": 5}
COST = {"mana": 2}


def _skill(effect: str, shape: dict[str, object] = SQUARE) -> SkillDef:
    return make_skill(SID, shape, [{"type": effect, "amount": 1, "affects": "tiles"}], cost=COST)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _scene(
    skill: SkillDef,
    *,
    foes: Sequence[tuple[int, int]] = (),
    allies: Sequence[tuple[int, int]] = (),
    heights: str = HILL,
    extra_skills: Sequence[str] = (),
    caster: tuple[int, int] = (1, 3),
) -> BattleState:
    far = list(foes) or [(6, 0)]
    m = make_map(heights, ally=[caster, *allies], enemy=far)
    unit = caster_template([skill, *extra_skills], base="hero_mage")
    spawns = [spawn(Team.ALLY, caster, unit)]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in far]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def _score(state: BattleState, at: tuple[int, int]) -> int:
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=at[0], y=at[1]))
    profile = _ai().profile_for(state.units[U1])
    return int(score_action(state, action, profile).score)


def _offers(state: BattleState) -> bool:
    """AI 的候選中有沒有分數為正的這個地形技能選取。"""
    return any(
        getattr(s.action, "skill_id", None) == SID and s.score > 0 for s in _ai().rank(state)
    )


# ---------------------------------------------------------------------------
# 表格：隆起／下陷 × 有收益／無收益
# ---------------------------------------------------------------------------

# (效果, 敵人, 友方, 目標格, 有收益)
CASES = [
    ("lower_terrain", [(4, 3)], [], (4, 3), True),  # 下陷：敵人被降低
    ("lower_terrain", [(6, 0)], [], (4, 3), False),  # 下陷：範圍內沒有單位
    ("lower_terrain", [(6, 0)], [(4, 3)], (4, 3), False),  # 下陷：只有友方被降低
    ("raise_terrain", [(6, 0)], [(4, 3)], (4, 3), True),  # 隆起：友方被抬高
    ("raise_terrain", [(6, 0)], [], (4, 3), False),  # 隆起：範圍內沒有單位
    ("raise_terrain", [(4, 3)], [], (4, 3), False),  # 隆起：只有敵人被抬高
]


@pytest.mark.parametrize(("effect", "foes", "allies", "at", "gain"), CASES)
def test_terrain_skills_are_cast_only_when_someone_benefits(
    effect: str,
    foes: list[tuple[int, int]],
    allies: list[tuple[int, int]],
    at: tuple[int, int],
    gain: bool,
) -> None:
    state = _scene(_skill(effect), foes=foes, allies=allies)
    assert _offers(state) is gain
    assert (_score(state, at) > 0) is gain


def test_a_friend_standing_in_the_blast_makes_it_worse() -> None:
    alone = _scene(_skill("lower_terrain"), foes=[(4, 3)])
    with_friend = _scene(_skill("lower_terrain"), foes=[(4, 3)], allies=[(5, 3)])
    assert _score(alone, (4, 3)) > _score(with_friend, (4, 3))


def test_ground_that_cannot_move_gives_no_gain() -> None:
    flat = _scene(_skill("lower_terrain"), foes=[(4, 3)], heights="\n".join(["0000000"] * 7))
    assert not _offers(flat)  # 高度 0 降不下去：沒有 terrain_changed，也就沒有收益


# ---------------------------------------------------------------------------
# 坑：把敵人推進去
# ---------------------------------------------------------------------------


def _pit_map(enemy_height: str) -> str:
    """第 3 列：(3,3) 高 1 的格子是之後的坑，(4,3) 站著敵人。"""
    flat = ["0000000"] * 7
    flat[3] = f"000{1}{enemy_height}00"
    return "\n".join(flat)


def test_a_pit_beside_a_high_enemy_is_worth_digging_only_with_a_push_skill() -> None:
    heights = _pit_map("3")  # 敵人高 3、坑 1 → 十字一起降：敵人 2、坑 0，落差 2 ≥ 墜落門檻
    lower = _skill("lower_terrain", CROSS)
    without = _scene(lower, foes=[(4, 3)], heights=heights)
    with_push = _scene(lower, foes=[(4, 3)], heights=heights, extra_skills=["skill_hurricane_push"])
    assert _score(with_push, (3, 3)) > _score(without, (3, 3))


def test_no_pit_value_when_the_drop_stays_below_the_fall_threshold() -> None:
    heights = _pit_map("2")  # 降完敵人 1、坑 0，落差只有 1
    lower = _skill("lower_terrain", CROSS)
    without = _scene(lower, foes=[(4, 3)], heights=heights)
    with_push = _scene(lower, foes=[(4, 3)], heights=heights, extra_skills=["skill_hurricane_push"])
    assert _score(with_push, (3, 3)) == _score(without, (3, 3))


# ---------------------------------------------------------------------------
# 內容：大地崩陷、整場重播
# ---------------------------------------------------------------------------


def _earth_setup() -> tuple[BattleSetup, int]:
    m = make_map(HILL, ally=[(1, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template(["skill_earth_collapse"], base="hero_mage")),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=60)),
    ]
    return make_setup(m, spawns, max_rounds=6), 5


def test_the_real_earth_collapse_is_a_scored_candidate_against_a_nearby_enemy() -> None:
    setup, _seed = _earth_setup()
    state = give_turn(make_state(setup.map, list(setup.units)), U1)
    ranked = _ai().rank(state)
    scores = [
        s.score for s in ranked if getattr(s.action, "skill_id", None) == "skill_earth_collapse"
    ]
    assert scores and max(scores) > 0


def test_an_ai_battle_that_casts_the_earth_collapse_replays_identically() -> None:
    lib = library()
    setup, seed = _earth_setup()
    ai = UtilityAI(lib.ai_profiles)

    def prefer_collapse(state: BattleState) -> Action:
        """法師有正分的大地崩陷選取時就施放（其餘照效用 AI）：鎖住「施放過」這件事。"""
        best = max(
            (
                s
                for s in ai.rank(state)
                if getattr(s.action, "skill_id", None) == "skill_earth_collapse" and s.score > 0
            ),
            key=lambda s: s.score,
            default=None,
        )
        return best.action if best is not None else ai(state)

    run = run_battle(setup, seed, prefer_collapse)
    assert [e for e in run.events if isinstance(e, TerrainChanged)], "應該施放過大地崩陷"
    again = replay(setup, seed, run.actions)
    assert again.state.rng_state == run.state.rng_state
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
