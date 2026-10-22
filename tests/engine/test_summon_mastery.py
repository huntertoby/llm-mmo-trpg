"""召喚專精（Phase 3-33f1，``docs/design/06-技能.md`` 6.29.4）與召喚物依定位的 HP 係數。

- 群召：同時上限 2 → 3、持續 +1 輪，代價自己造成的傷害 −20%。
- 精英召喚：召喚物 HP 與傷害 +50%、持續 +2 輪，代價同時上限 2 → 1。
- 兩者與普攻精通互斥（``exclusive_group: mastery``，``skill_slot_problems`` 擋）；3 隻是硬上限。
- 範本的 ``role`` 對照 ``core.summon_role_hp_permille`` 決定 HP 係數。
"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef, skill_slot_problems
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine import modifiers as mods
from trpg.engine.events import UnitSummoned
from trpg.engine.skills.conditions import Subject
from trpg.roguelite.offers import equip_problems
from trpg.shared.types import Pos, Team, UnitId

SUMMON = "skill_t_summon"
SWARM = "skill_summon_swarm"
ELITE = "skill_summon_elite"
MASTERY = "skill_attack_mastery"
TILES = [(2, 3), (2, 4), (2, 2), (1, 3)]


@cache
def library() -> ContentLibrary:
    return load_library()


def real(skill_id: str) -> SkillDef:
    return library().skills[skill_id]


def arena(mastery: str | None, *, duration: int = 2) -> BattleState:
    skill = make_skill(
        SUMMON,
        {"type": "ground_tile", "range": 4},
        [{"type": "summon", "unit": "summon_skeleton_warrior", "duration": duration}],
    ).model_copy(update={"tags": ("summon",)})
    mods_: list[SkillDef] = [] if mastery is None else [real(mastery)]
    m = make_map(FLAT7, ally=[(0, 3)], enemy=[(6, 6)])
    spawns = [
        spawn(Team.ALLY, (0, 3), caster_template([skill, *mods_])),
        spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=200)),
    ]
    state = make_state(m, spawns, skills=[skill])
    state = give_turn(state, U1)
    state.units[U1].ap = 9  # 一回合連放多次
    return state


def cast(state: BattleState, count: int) -> tuple[BattleState, list[UnitId]]:
    """連續施放 ``count`` 次召喚，回傳最後的狀態與依序召喚出的單位。"""
    made: list[UnitId] = []
    for x, y in TILES[:count]:
        result = resolve(state, UseSkill(unit_id=U1, skill_id=SUMMON, target_pos=Pos(x=x, y=y)))
        state = result.state
        made += [UnitId(e.unit_id) for e in result.events if isinstance(e, UnitSummoned)]
    return state, made


def alive_summons(state: BattleState) -> list[UnitId]:
    return [u.id for u in state.units.values() if u.owner_id == U1 and u.alive and not u.dismissed]


def role_hp(state: BattleState) -> int:
    """骷髏（近戰定位）：範本 20 HP ＋ 施放者屬性修正的成長 3，再 × 定位係數。"""
    return 23 * state.ruleset.core.summon_role_hp_permille["melee"] // 1000


# ---------------------------------------------------------------------------
# 互斥
# ---------------------------------------------------------------------------


def test_masteries_are_mutually_exclusive_with_a_chinese_message() -> None:
    slots = library().ruleset.core.skill_slots
    for pair in ((SWARM, ELITE), (SWARM, MASTERY), (ELITE, MASTERY)):
        problems = skill_slot_problems([real(s) for s in pair], slots)
        assert any("只能擇一" in p for p in problems), pair
    for single in (SWARM, ELITE, MASTERY):
        assert skill_slot_problems([real(single)], slots) == []


def test_masteries_are_mutually_exclusive_when_equipping_in_a_run() -> None:
    problems = equip_problems(library(), [real(SWARM), real(MASTERY)])
    assert problems and "群召" in problems[0] and "普攻精通" in problems[0]


# ---------------------------------------------------------------------------
# 群召
# ---------------------------------------------------------------------------


def test_without_mastery_the_limit_is_two() -> None:
    state, made = cast(arena(None), 3)
    assert len(made) == 3 and len(alive_summons(state)) == 2


def test_swarm_raises_the_limit_to_three_and_stops_at_the_hard_cap() -> None:
    state, made = cast(arena(SWARM), 4)
    assert len(made) == 4
    assert len(alive_summons(state)) == 3  # 3 隻是硬上限，第 4 隻擠掉最舊的
    assert made[0] not in alive_summons(state)


def test_swarm_adds_one_round_of_duration() -> None:
    plain, [a] = cast(arena(None), 1)
    swarm, [b] = cast(arena(SWARM), 1)
    assert swarm.units[b].summon_expires_round == (plain.units[a].summon_expires_round or 0) + 1


def test_swarm_cuts_your_own_damage_by_twenty_percent_but_not_the_summons() -> None:
    plain, [a] = cast(arena(None), 1)
    state, [made] = cast(arena(SWARM), 1)
    foe = state.units[next(u.id for u in state.units.values() if u.team is Team.ENEMY)]
    assert mods.damage_permille(state, state.units[U1], mods.ATTACK, Subject(foe, foe.xy)) == 800
    assert state.units[made].summon_bonus_permille == plain.units[a].summon_bonus_permille


# ---------------------------------------------------------------------------
# 精英召喚
# ---------------------------------------------------------------------------


def test_elite_drops_the_limit_to_one() -> None:
    state, made = cast(arena(ELITE), 2)
    assert len(made) == 2 and alive_summons(state) == [made[1]]


def test_elite_gives_hp_damage_and_two_extra_rounds() -> None:
    plain, [a] = cast(arena(None), 1)
    elite, [b] = cast(arena(ELITE), 1)
    assert elite.units[b].max_hp == role_hp(elite) * 3 // 2
    assert elite.units[b].summon_bonus_permille == plain.units[a].summon_bonus_permille + 500
    assert elite.units[b].summon_expires_round == (plain.units[a].summon_expires_round or 0) + 2


def test_duration_bonus_is_added_after_the_max_duration_cap() -> None:
    plain, [a] = cast(arena(None, duration=4), 1)
    elite, [b] = cast(arena(ELITE, duration=4), 1)
    cap = plain.ruleset.core.summon_max_duration
    assert plain.units[a].summon_expires_round == plain.round + cap
    assert elite.units[b].summon_expires_round == elite.round + cap + 2


# ---------------------------------------------------------------------------
# 定位係數
# ---------------------------------------------------------------------------


def test_every_summon_template_has_a_role_with_a_known_coefficient() -> None:
    core = library().ruleset.core
    for entry in library().ruleset.summons.summons:
        assert entry.template.role is not None, entry.template.id
        assert entry.template.role in {*core.summon_role_hp_permille, "ranged"}, entry.template.id


def test_melee_and_immobile_summons_are_tougher_than_ranged_ones() -> None:
    table = library().ruleset.core.summon_role_hp_permille
    assert table["melee"] > table["ranged"] and table["totem"] > table["ranged"]
    assert table["ranged"] == 1000  # 遠程靈維持
    assert table["scout"] > table["ranged"]  # 鷹隼係數 2.4×（玩法 PM，3-33f1 驗收）；脆弱來自基礎 HP 低


def test_role_coefficient_scales_the_summons_hp() -> None:
    state, [made] = cast(arena(None), 1)
    assert state.units[made].max_hp == role_hp(state)
    assert state.units[made].max_hp > 23
