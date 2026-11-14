"""GB-3：巨型頭目的 AI（``docs/phases/PhaseGB計畫.md`` 第 7 節、T17、T18；GB-1c 待決 6）。

每條一個固定場面比分數（不比機率、不量勝率）。合成巨人沿用 GB-1c 的競技場：中心 (6, 6)、佔
x 5～7、y 5～7、朝南；殼縫 (5, 6)、(7, 6)，噴口北排 y 5，核心 (6, 6)（第 2 階段起露出）。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    spawn,
    spawn_giant,
    template,
)
from tests.engine.test_giant_parts_gb1c import (
    GIANT_ID,
    SPLASH,
    arena,
    breathing,
    giant,
    giant_boss,
    hero,
    splash_skill,
)
from trpg.content.environment import AiProfileTable, AiWeights
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, legal_actions
from trpg.engine.actions import Attack, EndTurn, UseSkill
from trpg.engine.ai.leader import far_from_leader_extra, far_target_extra, leader_of
from trpg.engine.ai.parts import (
    behind_spot,
    giant_part_spot_extra,
    guard_face_extra,
    silent_behind_extra,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.ai.utility.position import position_value
from trpg.engine.ai.utility.scoring import score_action
from trpg.engine.battle import start_battle
from trpg.engine.rules.facing import is_behind
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import build_setup, with_phase_assets
from trpg.engine.state import StatusInstance, UnitState, state_to_json
from trpg.shared.types import Pos, Team, UnitId

INHALE = "skill_charged_cleave"
WEST_SEAM = (4, 6)
"""貼著西殼縫 (5, 6) 的格子。"""
FRONT = (6, 8)
"""前殼（南排中間）正南方一格：只貼著本體（第 2 階段起核心 ``any_face`` 也算）。"""

# 噴口不加護甲（GB-1c 的 PARTS 噴口 armor_bonus 30，命中率太低不好比）；其他照 GB-1c
AI_PARTS: tuple[dict[str, Any], ...] = (
    {
        "id": "core",
        "name_zh": "核心",
        "tiles": [[0, 0]],
        "melee_from": "any_face",
        "exposed_in": ["breath"],
        "on_break": [
            {"type": "interrupt_charge"},
            {"type": "seal_skill", "skill": INHALE, "rounds": 2},
        ],
    },
    {
        "id": "seam",
        "name_zh": "殼縫",
        "tiles": [[-1, 0], [1, 0]],
        "counts_as_behind": True,
        "on_break": [{"type": "stop_mechanic", "status": "molten_shell"}],
    },
    {
        "id": "vent",
        "name_zh": "噴口",
        "tiles": [[-1, -1], [0, -1], [1, -1]],
        "reach": "ranged",
        "on_break": [{"type": "seal_skill", "skill": SPLASH}],
    },
)


def boss() -> Any:
    return giant_boss(AI_PARTS)


def field(allies: Sequence[tuple[int, int, str]]) -> BattleState:
    return arena(allies, boss=boss())


def weights_of(state: BattleState, unit: UnitState, **update: int) -> AiWeights:
    w = UtilityAI(library().ai_profiles).profile_for(unit).weights
    return w.model_copy(update=update) if update else w


def gain(state: BattleState, xy: tuple[int, int], key: str, value: int = 7) -> Fraction:
    """站在 ``xy`` 的英雄的位置價值：權重 ``key`` 為 ``value`` 與 0 的差。"""
    unit = hero(state, xy)
    on = weights_of(state, unit, **{key: value})
    off = weights_of(state, unit, **{key: 0})
    return position_value(state, unit.id, on) - position_value(state, unit.id, off)


def table_with(**weights: int) -> AiProfileTable:
    lib_table = library().ai_profiles
    profiles = tuple(
        p.model_copy(update={"weights": p.weights.model_copy(update=weights)})
        for p in lib_table.profiles
    )
    return lib_table.model_copy(update={"profiles": profiles})


# ---------------------------------------------------------------------------
# 內容：價值表與殼縫餘燼蜥的行為模式
# ---------------------------------------------------------------------------


def test_placeholder_weights_are_filled_into_every_profile() -> None:
    table = library().ai_profiles
    assert (table.parts.guard_face_bonus, table.parts.giant_spot_bonus) == (3, 6)
    for profile in table.profiles:
        assert profile.weights.guard_face_bonus == 3
        assert profile.weights.giant_spot_bonus == 6
        expected = 3 if profile.id == "ember_brood" else 0
        assert profile.weights.prefer_far_from_leader == expected


def test_only_the_heart_ember_lizard_uses_ember_brood() -> None:
    lib = library()
    users = sorted(u.id for u in lib.units.values() if u.ai_profile == "ember_brood")
    assert users == ["heart_ember_lizard"]
    brood = lib.ai_profiles.by_id()["ember_brood"].weights
    brute = lib.ai_profiles.by_id()["brute"].weights
    assert brood.model_copy(update={"prefer_far_from_leader": 0}) == brute


# ---------------------------------------------------------------------------
# GB-1c 待決 6：背後估值吃殼縫
# ---------------------------------------------------------------------------


def test_the_seam_counts_as_behind_for_the_ai() -> None:
    state = field([(*WEST_SEAM, "hero_fighter"), (*FRONT, "hero_fighter")])
    g = giant(state)
    assert behind_spot(WEST_SEAM, g) and behind_spot((8, 6), g)
    assert not behind_spot(FRONT, g)
    assert not behind_spot((4, 5), g)  # 貼著噴口格那一排（北排的西側），不是殼縫
    g.broken_parts = ("seam",)
    assert not behind_spot(WEST_SEAM, g)  # 殼縫破了：打那一格是本體，不算背後


def test_one_tile_units_keep_is_behind() -> None:
    state = field([(*WEST_SEAM, "hero_fighter")])
    unit = hero(state, WEST_SEAM)
    for xy in [(3, 6), (5, 6), (4, 5), (4, 7), (2, 2)]:
        assert behind_spot(xy, unit) == is_behind(xy, unit)


@pytest.mark.parametrize(("xy", "expected"), [(WEST_SEAM, 7), (FRONT, 0)])
def test_backstab_and_circle_back_read_the_seam(xy: tuple[int, int], expected: int) -> None:
    state = field([(*xy, "hero_fighter")])
    assert gain(state, xy, "backstab") == expected
    assert gain(state, xy, "circle_back_bonus") == expected


def test_circle_back_stops_when_the_seam_breaks() -> None:
    state = field([(*WEST_SEAM, "hero_fighter")])
    giant(state).broken_parts = ("seam",)
    assert gain(state, WEST_SEAM, "circle_back_bonus") == 0
    assert gain(state, WEST_SEAM, "backstab") == 0


def test_silent_behind_reads_the_seam() -> None:
    silent = template("hero_fighter", skills=["skill_silent_step"], reactions=())
    for xy, expected in ((WEST_SEAM, 5), (FRONT, 0)):
        state = arena([(*xy, silent)], boss=boss(), weapon="dagger")
        unit = hero(state, xy)
        w = weights_of(state, unit, silent_behind=5)
        assert silent_behind_extra(state, unit, w, [giant(state)]) == expected


# ---------------------------------------------------------------------------
# 第 7 節第 2 點：隊友的部位站位（giant_spot_bonus）
# ---------------------------------------------------------------------------


def test_melee_next_to_the_seam_gets_the_spot_bonus() -> None:
    state = field([(*WEST_SEAM, "hero_fighter"), (*FRONT, "hero_fighter")])
    assert gain(state, WEST_SEAM, "giant_spot_bonus") == 7
    assert gain(state, FRONT, "giant_spot_bonus") == 0  # 第 1 階段：前殼是本體、核心還沒露出


def test_the_core_opens_every_face_in_phase_two() -> None:
    state = breathing(field([(*FRONT, "hero_fighter")]))
    assert gain(state, FRONT, "giant_spot_bonus") == 7


def test_ranged_gets_the_spot_bonus_where_it_can_shoot_the_vent() -> None:
    state = field([(6, 12, "hero_archer"), (12, 12, "hero_archer")])
    assert gain(state, (6, 12), "giant_spot_bonus") == 7  # 噴口 (6, 5) 距離 7 ≤ 弓 8；身體不擋
    assert gain(state, (12, 12), "giant_spot_bonus") == 0  # 最近的噴口格 (7, 5) 距離 12


def test_ranged_ignores_the_seam_and_melee_ignores_the_vent() -> None:
    state = field([(4, 4, "hero_fighter"), (*WEST_SEAM, "hero_archer")])
    assert gain(state, (4, 4), "giant_spot_bonus") == 0  # 近戰貼著噴口格 (5, 4)？不相鄰（斜角）
    archer = hero(state, WEST_SEAM)
    w = weights_of(state, archer)
    assert giant_part_spot_extra(state, archer, w, [giant(state)]) == w.giant_spot_bonus  # 噴口


def test_broken_vent_gives_ranged_no_spot() -> None:
    state = field([(6, 12, "hero_archer")])
    giant(state).broken_parts = ("vent",)
    assert gain(state, (6, 12), "giant_spot_bonus") == 0


def test_enemies_and_summons_never_get_the_spot_bonus() -> None:
    state = field([(*WEST_SEAM, "hero_fighter")])
    unit = hero(state, WEST_SEAM).clone()
    unit.team = Team.ENEMY
    w = weights_of(state, unit)
    assert giant_part_spot_extra(state, unit, w, [giant(state)]) == 0


# ---------------------------------------------------------------------------
# 第 7 節第 1 點：隊友挑部位
# ---------------------------------------------------------------------------


def _attacks(state: BattleState, unit: UnitState) -> dict[str | None, Fraction]:
    policy = UtilityAI(library().ai_profiles)
    return {
        s.action.target_part: s.score
        for s in policy.rank(give_turn(state, unit.id))
        if isinstance(s.action, Attack) and s.action.target_id == giant(state).id
    }


def test_melee_at_the_seam_hits_the_seam() -> None:
    state = field([(*WEST_SEAM, "hero_fighter")])
    scores = _attacks(state, hero(state, WEST_SEAM))
    assert set(scores) == {None, "seam"}
    assert scores["seam"] > scores[None]


def test_the_core_is_the_pick_while_the_heart_charges() -> None:
    state = breathing(field([(*FRONT, "hero_fighter")]))
    g = giant(state)
    g.statuses.append(StatusInstance(status_id=CHARGING, skill_id=INHALE))
    g.part_hp["core"] = 1
    scores = _attacks(state, hero(state, FRONT))
    assert set(scores) == {None, "core"}
    assert scores["core"] > scores[None]


def test_ranged_breaks_the_vent_when_the_splash_is_ready() -> None:
    state = field([(6, 12, "hero_archer")])
    giant(state).part_hp["vent"] = 1
    scores = _attacks(state, hero(state, (6, 12)))
    assert set(scores) == {None, "seam", "vent"}  # 殼縫 reach any，遠程看得到也能打
    assert scores["vent"] == max(scores.values())


# ---------------------------------------------------------------------------
# T18：巨型頭目護面
# ---------------------------------------------------------------------------


def test_guard_face_counts_victims_next_to_a_nearly_broken_part() -> None:
    state = field([(*WEST_SEAM, "hero_fighter"), (*FRONT, "hero_fighter")])
    g = giant(state)
    w = weights_of(state, g)
    seam_hero, front_hero = hero(state, WEST_SEAM), hero(state, FRONT)
    assert guard_face_extra(state, g, w, (seam_hero, front_hero)) == 0  # 還沒快破
    g.part_hp["seam"] = 1
    assert guard_face_extra(state, g, w, (seam_hero, front_hero)) == w.guard_face_bonus
    assert guard_face_extra(state, g, w, (front_hero,)) == 0
    g.broken_parts = ("seam",)
    assert guard_face_extra(state, g, w, (seam_hero,)) == 0


def test_a_nearly_broken_core_guards_every_face() -> None:
    state = breathing(field([(*FRONT, "hero_fighter")]))
    g = giant(state)
    g.part_hp["core"] = 1
    w = weights_of(state, g)
    assert guard_face_extra(state, g, w, (hero(state, FRONT),)) == w.guard_face_bonus


def test_guard_face_raises_the_boss_attack_score_by_bonus_times_hit() -> None:
    state = field([(*WEST_SEAM, "hero_fighter")])
    g = giant(state)
    g.part_hp["seam"] = 1
    state = give_turn(state, g.id)
    target = hero(state, WEST_SEAM)
    action = next(
        a
        for a in legal_actions(state)
        if isinstance(a, Attack) and a.target_id == target.id and a.target_part is None
    )
    profile = UtilityAI(library().ai_profiles).profile_for(giant(state))
    on = score_action(state, action, profile)
    off_profile = profile.model_copy(
        update={"weights": profile.weights.model_copy(update={"guard_face_bonus": 0})}
    )
    off = score_action(state, action, off_profile)
    assert on.preview is not None and on.preview.hit_chance is not None
    assert on.score - off.score == on.preview.hit_chance * profile.weights.guard_face_bonus


# ---------------------------------------------------------------------------
# T17：殼縫餘燼蜥追離頭目遠的人
# ---------------------------------------------------------------------------

NEAR, FAR, LIZARD = (8, 6), (10, 6), (9, 6)


def lizard_field() -> BattleState:
    rows = "\n".join("0" * 13 for _ in range(13))
    m = make_map(rows, ally=[NEAR, FAR], enemy=[(6, 6), LIZARD]).model_copy(
        update={"giant_facing": {GIANT_ID: "south"}}
    )
    spawns = [
        spawn_giant(Team.ENEMY, (6, 6), boss()),
        spawn(Team.ENEMY, LIZARD, template("heart_ember_lizard", reactions=())),
        spawn(Team.ALLY, NEAR, template("hero_fighter", reactions=())),
        spawn(Team.ALLY, FAR, template("hero_fighter", reactions=())),
    ]
    state = start_battle(make_setup(m, spawns, skills=[splash_skill()]), 0)
    state.units[hero(state, NEAR).id].facing = "east"  # 兩人都面向蜥蜴：沒有背刺差
    state.units[hero(state, FAR).id].facing = "west"
    lizard = hero(state, LIZARD)
    return give_turn(state, lizard.id)


def test_the_leader_is_the_boss_of_the_same_team() -> None:
    state = lizard_field()
    lizard = hero(state, LIZARD)
    leader = leader_of(state, lizard)
    assert leader is not None and leader.footprint == 3
    assert leader_of(state, hero(state, NEAR)) is None  # 我方沒有頭目


def test_the_lizard_prefers_the_hero_far_from_the_heart() -> None:
    state = lizard_field()
    lizard = hero(state, LIZARD)
    near, far = hero(state, NEAR), hero(state, FAR)
    w = weights_of(state, lizard)
    assert far_target_extra(state, lizard, w, (near,)) == 3 * 1  # (8, 6) 到最近佔格 (7, 6)
    assert far_target_extra(state, lizard, w, (far,)) == 3 * 3
    assert far_target_extra(state, lizard, w, (near, far)) == 3 * 3  # 取最遠的一名
    scores = {
        s.action.target_id: s.score
        for s in UtilityAI(library().ai_profiles).rank(state)
        if isinstance(s.action, Attack)
    }
    assert scores[far.id] > scores[near.id]
    policy = UtilityAI(table_with(prefer_far_from_leader=0))
    plain = {
        s.action.target_id: s.score for s in policy.rank(state) if isinstance(s.action, Attack)
    }
    assert plain[far.id] == plain[near.id]  # 沒有這個權重時兩邊同分：差來自 T17


def test_the_position_term_follows_the_farthest_reachable_hero() -> None:
    state = lizard_field()
    lizard = hero(state, LIZARD)
    w = weights_of(state, lizard)
    enemies = [hero(state, NEAR), hero(state, FAR)]
    assert far_from_leader_extra(state, lizard, w, enemies) == 3 * 3
    moved = lizard.clone()
    moved.pos = Pos(x=8, y=7)  # 只貼著近的那一名
    assert far_from_leader_extra(state, moved, w, enemies) == 3 * 1
    assert far_from_leader_extra(state, hero(state, NEAR), w, [lizard]) == 0  # 沒有頭目


# ---------------------------------------------------------------------------
# 沒有巨型單位的場面逐字不變；確定性
# ---------------------------------------------------------------------------


def test_scenes_without_giants_rank_exactly_as_before() -> None:
    lib = library()
    flat = "\n".join(["0000000"] * 7)
    setup = make_setup(
        make_map(flat, ally=[(2, 3)], enemy=[(3, 3), (5, 5)]),
        [
            spawn(Team.ALLY, (2, 3), template("hero_fighter", reactions=())),
            spawn(Team.ENEMY, (3, 3), template("sect_mist_lock_master", reactions=())),
            spawn(Team.ENEMY, (5, 5), template("bandit", reactions=())),
        ],
    )
    state = start_battle(with_phase_assets(lib, setup), 0)
    off = table_with(guard_face_bonus=0, giant_spot_bonus=0, prefer_far_from_leader=0)
    for uid in sorted(state.units):
        s = give_turn(state, uid)
        on_rank = UtilityAI(lib.ai_profiles, override="brute").rank(s)
        off_rank = UtilityAI(off, override="brute").rank(s)
        assert [(r.action, r.score) for r in on_rank] == [(r.action, r.score) for r in off_rank]
    # 一般單位用 ember_brood（有權重、但陣營沒有頭目）：分數也和莽夫一樣
    s = give_turn(state, UnitId("unit_0001"))
    brood = UtilityAI(lib.ai_profiles, override="ember_brood").rank(s)
    brute = UtilityAI(lib.ai_profiles, override="brute").rank(s)
    assert [(r.action, r.score) for r in brood] == [(r.action, r.score) for r in brute]


def test_the_giant_ai_is_deterministic() -> None:
    state = field([(*WEST_SEAM, "hero_fighter"), (6, 12, "hero_archer")])
    giant(state).part_hp["seam"] = 1
    for uid in sorted(state.units):
        s = give_turn(state, uid)
        first = [(r.action, r.score) for r in UtilityAI(library().ai_profiles).rank(s)]
        again = [(r.action, r.score) for r in UtilityAI(library().ai_profiles).rank(s.clone())]
        assert first == again


# ---------------------------------------------------------------------------
# 熔心坑：巨型頭目自己的選招與站位（GB-2 待決 6）
# ---------------------------------------------------------------------------


def pit() -> BattleState:
    lib = library()
    enc = lib.map("molten_heart_pit").encounter
    assert enc is not None
    setup = build_setup(lib, "molten_heart_pit", enc.allies, enc.enemies)
    return start_battle(setup, 1)


def test_the_heart_measures_its_bolt_from_the_nearest_tile() -> None:
    state = pit()
    heart = next(u for u in state.units_sorted() if u.footprint == 3)
    mage = next(u for u in state.units_sorted() if u.template_id == "hero_mage")
    mage.pos = Pos(x=5, y=9)  # 到最近佔格 (5, 4) 5 格＝火球射程；到中心格 6 格
    state = give_turn(state, heart.id)
    ranked = UtilityAI(library().ai_profiles).rank(state)
    bolts = [
        s
        for s in ranked
        if isinstance(s.action, UseSkill)
        and s.action.skill_id == "skill_fire_bolt"
        and s.action.target_id == mage.id
    ]
    assert bolts and bolts[0].score > 0
    assert not isinstance(UtilityAI(library().ai_profiles)(state), EndTurn)


def test_molten_heart_pit_finishes_and_replays() -> None:
    lib = library()
    enc = lib.map("molten_heart_pit").encounter
    assert enc is not None
    setup = build_setup(lib, "molten_heart_pit", enc.allies, enc.enemies, max_rounds=30)
    run = run_battle(setup, 1, UtilityAI(lib.ai_profiles))
    assert run.state.ended
    again = replay(setup, 1, run.actions)
    assert again.events == run.events
    assert state_to_json(again.state) == state_to_json(run.state)
