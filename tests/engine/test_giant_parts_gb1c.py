"""GB-1c 巨型頭目的部位綁格與新機制（05 5.12.2 第 8 點、5.12.4 第 3 點、19 19.2.3「巨型頭目段 GB
補定的細節」、``PhaseGB計畫.md`` 5.3、5.5 第 10～14 列；R3～R6、T11、T12、T14～T16、#164）：實際跑
引擎，每列一條規則句（列名寫 D／R／T 編號）。合成巨人只在測試裡，不進 ``content/``。

場地：13×13 平地；巨人（敵方、朝南）中心 (6, 6)、佔 x 5～7、y 5～7。部位照灰燼之心的配置：
北排 3 格噴口（``ranged``）、中排東西 2 格殼縫（``counts_as_behind``）、中心核心（``any_face``、
第 2 階段才露出）、南排前殼（本體）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    giant_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    spawn,
    spawn_giant,
    template,
    with_rolls,
)
from trpg.content.battle import UnitTemplate
from trpg.content.parts import BossPart, check_part_tiles
from trpg.content.skills import CHARGING, SkillDef
from trpg.engine import BattleState, legal_actions, resolve
from trpg.engine.actions import Attack, UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.boss_phases import check_boss_phases
from trpg.engine.context import Ctx
from trpg.engine.delayed import charge_infos, release_at_turn_start
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.environment import run_environment, telegraph
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EffectFizzled,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    PartDamaged,
    SkillFollowup,
    SkillSealed,
    SurfaceChanged,
)
from trpg.engine.parts import PART_REASON_ZH, check_target_part, part_targets
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.skills.targeting import farthest_enemy, skill_problem
from trpg.engine.state import StatusInstance, UnitState, state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Surface, Team, UnitId

FLAT13 = "\n".join("0" * 13 for _ in range(13))
GIANT_ID = "test_giant"
INHALE = "skill_charged_cleave"  # 核心破掉時限時封住的招（用既有的蓄力招當替身）
SPLASH = "skill_t_gb1c_splash"

PHASES: tuple[dict[str, Any], ...] = (
    {"id": "shell", "name_zh": "殼"},
    {"id": "breath", "name_zh": "呼吸", "trigger": {"kind": "hp_below", "permille": 500}},
)

PARTS: tuple[dict[str, Any], ...] = (
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
        "armor_bonus": 30,
        "on_break": [{"type": "seal_skill", "skill": SPLASH}],
    },
)


def splash_skill(*, shape: dict[str, Any] | None = None) -> SkillDef:
    """熔岩濺落的 GB-2 寫法（R5、T15）：第一段不選格（自身護盾），延遲段落在最遠的敵人。"""
    return SkillDef.model_validate(
        {
            "id": SPLASH,
            "name_zh": "測試濺落",
            "tier": 1,
            "rarity": "rare",
            "kind": "active",
            "skeleton": "aura",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": 2,
            "scaling_attr": "int",
            "shape": shape or {"type": "self"},
            "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            "followup": {
                "when": "delayed",
                "release": "next_turn",
                "anchor": "farthest_enemy",
                "skeleton": "area",
                "shape": {"type": "square3", "range": 0},
                "effects": [{"type": "damage", "dice": "1d6", "element": "fire"}],
            },
            "cost": {"mana": 0},
        }
    )


def giant_boss(parts: Sequence[dict[str, Any]] = PARTS, **overrides: Any) -> UnitTemplate:
    data: dict[str, Any] = {
        "id": GIANT_ID,
        "skills": (INHALE, SPLASH),
        "reactions": (),
        "max_mana": 99,
        "phases": PHASES,
        "parts": list(parts),
    }
    data.update(overrides)
    return giant_template(**data)


def arena(
    allies: Sequence[tuple[int, int, UnitTemplate | str]],
    *,
    objects: tuple[tuple[int, int, str], ...] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
    terrain_walls: tuple[tuple[int, int], ...] = (),
    lava: tuple[tuple[int, int], ...] = (),
    skills: Sequence[SkillDef] = (),
    boss: UnitTemplate | None = None,
    weapon: str | None = None,
    seed: int = 0,
) -> BattleState:
    rows = [["."] * 13 for _ in range(13)]
    for x, y in terrain_walls:
        rows[y][x] = "#"
    for x, y in lava:
        rows[y][x] = "~"
    m = make_map(
        FLAT13,
        "\n".join("".join(r) for r in rows),
        ally=[(x, y) for x, y, _ in allies],
        enemy=[(6, 6)],
        objects=objects,
        surfaces=surfaces,
    ).model_copy(update={"giant_facing": {GIANT_ID: "south"}})
    spawns = [spawn_giant(Team.ENEMY, (6, 6), boss or giant_boss())]
    for x, y, t in allies:
        tmpl = template(t, reactions=()) if isinstance(t, str) else t
        spawns.append(spawn(Team.ALLY, (x, y), tmpl, weapon, skills=None))
    return start_battle(make_setup(m, spawns, skills=[splash_skill(), *skills]), seed)


def giant(state: BattleState) -> UnitState:
    return next(u for u in state.units_sorted() if u.footprint == 3)


def hero(state: BattleState, xy: tuple[int, int]) -> UnitState:
    found = state.unit_at(*xy)
    assert found is not None
    return found


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def reasons(state: BattleState, action: Attack | UseSkill) -> dict[str, str | None]:
    return {t.part_id: t.reason for t in part_targets(state, action)}


def breathing(state: BattleState) -> BattleState:
    s = state.clone()
    giant(s).phase_index = 1
    return s


def attack_from(state: BattleState, xy: tuple[int, int], part: str | None = None) -> Attack:
    return Attack(unit_id=hero(state, xy).id, target_id=giant(state).id, target_part=part)


# ---------------------------------------------------------------------------
# T11：內容檢查
# ---------------------------------------------------------------------------


def test_t11_giant_parts_need_tiles_inside_the_body_without_overlap() -> None:
    parts = tuple(BossPart.model_validate(p) for p in PARTS)
    assert check_part_tiles(parts, 3) == []
    untiled = (parts[0], parts[1].model_copy(update={"tiles": ()}))
    assert "部位 seam：佔多格的頭目的部位要有 tiles" in check_part_tiles(untiled, 3)[0]
    outside = (parts[0], parts[1].model_copy(update={"tiles": ((2, 0),)}))
    assert check_part_tiles(outside, 3) == ["部位 seam 的格子 (2, 0) 不在佔格內"]
    overlap = (parts[0], parts[1].model_copy(update={"tiles": ((0, 0),)}))
    assert check_part_tiles(overlap, 3) == ["部位 seam 的格子 (0, 0) 和部位 core 重疊"]
    assert (
        len(check_part_tiles(parts, 1)) == 3
    )  # 一格的頭目：tiles、melee_from、counts_as_behind 都不行
    with pytest.raises(ValueError, match="只有佔多格的頭目的部位能有"):
        template("bandit", tags=("boss",), parts=list(PARTS), skills=(INHALE, SPLASH))
    with pytest.raises(ValueError, match="tiles 不能重複"):
        BossPart.model_validate({**PARTS[1], "tiles": [[1, 0], [1, 0]]})


def test_t11_new_fields_are_not_serialised_when_unused() -> None:
    plain = BossPart.model_validate(
        {"id": "head", "name_zh": "頭", "on_break": [{"type": "seal_skill", "skill": INHALE}]}
    )
    assert set(plain.model_dump(mode="json")) == {
        "id",
        "name_zh",
        "hp_permille",
        "reach",
        "on_break",
    }
    assert "rounds" not in plain.model_dump(mode="json")["on_break"][0]


# ---------------------------------------------------------------------------
# 10. 可打條件（D12、R3、T12）：部位 × 近戰／遠程 × 位置
# ---------------------------------------------------------------------------

GRID: tuple[tuple[str, tuple[int, int], str | None, dict[str, str | None]], ...] = (
    # 近戰（單手劍）：貼著西側殼縫格
    (
        "hero_fighter",
        (4, 6),
        None,
        {"core": "not_exposed", "seam": None, "vent": "melee_cannot_reach"},
    ),
    # 近戰：貼著南排（前殼），殼縫不相鄰
    (
        "hero_fighter",
        (6, 8),
        None,
        {"core": "not_exposed", "seam": "not_adjacent_to_tile", "vent": "melee_cannot_reach"},
    ),
    # R3：站在噴口旁的地板（北排西端的西邊）的近戰也打不到噴口
    (
        "hero_fighter",
        (4, 5),
        None,
        {"core": "not_exposed", "seam": "not_adjacent_to_tile", "vent": "melee_cannot_reach"},
    ),
    # R3：拿矛（近戰、射程 2）也不行
    (
        "hero_fighter",
        (4, 5),
        "spear",
        {"core": "not_exposed", "seam": "not_adjacent_to_tile", "vent": "melee_cannot_reach"},
    ),
    # 遠程（弓，射程 8）從南邊：身體不擋打它自己的格子（D7），三個部位都打得到
    ("hero_archer", (6, 11), None, {"core": "not_exposed", "seam": None, "vent": None}),
)


@pytest.mark.parametrize(("who", "xy", "weapon", "expected"), GRID)
def test_d12_r3_part_reach_table(
    who: str, xy: tuple[int, int], weapon: str | None, expected: dict[str, str | None]
) -> None:
    state = arena([(*xy, who)], weapon=weapon)
    assert reasons(state, attack_from(state, xy)) == expected


def test_d18_the_core_shows_from_phase_two_and_melee_reaches_it_from_any_face() -> None:
    for xy in ((4, 6), (6, 8), (8, 6), (6, 4), (5, 4)):
        state = breathing(arena([(*xy, "hero_fighter")]))
        assert reasons(state, attack_from(state, xy))["core"] is None, xy
    state = breathing(arena([(6, 11, "hero_archer")]))
    assert reasons(state, attack_from(state, (6, 11)))["core"] is None


def test_d12_ranged_needs_the_part_tile_in_range() -> None:
    """射程 3 的單體從 (6, 10) 打得到本體（南排 (6, 7) 距離 3），殼縫、噴口（都 5 格）超出。"""
    bolt = make_skill(
        "skill_t_gb1c_bolt",
        {"type": "single", "range": 3},
        [{"type": "damage", "dice": "1d4", "element": "physical"}],
        weapon_req="any",
    )
    state = arena([(6, 10, caster_template([bolt]))], skills=[bolt])
    me = hero(state, (6, 10))
    action = UseSkill(unit_id=me.id, skill_id=bolt.id, target_id=giant(state).id)
    got = reasons(state, action)
    assert got["seam"] == "out_of_range_to_tile" and got["vent"] == "out_of_range_to_tile"
    assert check_target_part(state, action.model_copy(update={"target_part": "vent"})) == (
        f"不能打「噴口」：{PART_REASON_ZH['out_of_range_to_tile']}"
    )


def test_d12_ranged_needs_sight_to_the_part_tile() -> None:
    """從西邊 (2, 6) 射殼縫：牆 (3, 6) 擋住兩格殼縫的視線（弓的拋射越不過牆）。"""
    state = arena([(2, 6, "hero_archer")], terrain_walls=((3, 6),))
    got = reasons(state, attack_from(state, (2, 6)))
    assert got["seam"] == "no_sight_to_tile"
    assert PART_REASON_ZH["no_sight_to_tile"] == "看不到那一格"


def test_t12_broken_parts_and_the_front_shell_are_the_body() -> None:
    state = arena([(4, 6, "hero_fighter")])
    g = giant(state)
    g.broken_parts = ("seam",)
    assert reasons(state, attack_from(state, (4, 6)))["seam"] == "broken"
    with pytest.raises(IllegalActionError, match="已經破了"):
        resolve(give_turn(state, hero(state, (4, 6)).id), attack_from(state, (4, 6), "seam"))


def test_reason_texts() -> None:
    assert PART_REASON_ZH["melee_cannot_reach"] == "只有遠程才打得到"
    assert PART_REASON_ZH["not_adjacent_to_tile"] == "要貼著那一格才打得到"
    assert PART_REASON_ZH["out_of_range_to_tile"] == "那一格超出射程"


# ---------------------------------------------------------------------------
# 10. 打部位：打中的那一格、從背後（R4）、#164 範圍技防禦照本體
# ---------------------------------------------------------------------------


def _roll(state: BattleState, xy: tuple[int, int], part: str | None) -> tuple[AttackRolled, Any]:
    me = hero(state, xy)
    result = resolve(
        with_rolls(give_turn(state, me.id), [(20, 10), (8, 4)]), attack_from(state, xy, part)
    )
    (rolled,) = [e for e in of(result.events, AttackRolled) if e.attacker_id == me.id]
    return rolled, result


def test_r4_melee_on_the_seam_counts_as_behind() -> None:
    state = arena([(4, 6, "hero_fighter")])
    seam, result = _roll(state, (4, 6), "seam")
    body, _ = _roll(state, (4, 6), None)
    assert seam.backstab > 0 and body.backstab == 0
    assert seam.hit_tile == Pos(x=5, y=6)  # 打中的那一格是殼縫格
    assert [e.part_id for e in of(result.events, PartDamaged)] == ["seam"]


def test_r4_ranged_on_the_seam_is_not_a_backstab() -> None:
    state = arena([(6, 11, "hero_archer")])
    seam, _ = _roll(state, (6, 11), "seam")
    assert seam.backstab == 0 and seam.hit_tile == Pos(x=5, y=6)  # 同距離 (y, x) 小：西側
    vent, _ = _roll(state, (6, 11), "vent")
    assert vent.hit_tile == Pos(x=6, y=5)


def test_r4_the_from_behind_condition_holds_on_the_seam() -> None:
    stab = make_skill(
        "skill_t_gb1c_stab",
        {"type": "single", "range": "weapon"},
        [
            {"type": "damage", "multiplier_permille": 1000},
            {"type": "damage", "multiplier_permille": 1000, "condition": {"type": "from_behind"}},
        ],
        category="weapon",
    )
    tmpl = caster_template([stab], base="hero_fighter")
    state = arena([(4, 6, tmpl)], skills=[stab])
    me, g = hero(state, (4, 6)), giant(state)

    def hits(part: str | None) -> int:
        action = UseSkill(unit_id=me.id, skill_id=stab.id, target_id=g.id, target_part=part)
        result = resolve(with_rolls(give_turn(state, me.id), [(20, 10)]), action)
        return len([e for e in of(result.events, DamageDealt) if e.target_id == g.id])

    assert hits("seam") == 2 and hits(None) == 1


def test_164_an_area_hit_tile_on_a_part_still_uses_the_body_defence() -> None:
    """R1（#164）：範圍技打中的那一格落在噴口格，防禦也照本體（不套噴口的 armor_bonus），
    也不扣部位。"""
    square = make_skill(
        "skill_t_gb1c_sqre",
        {"type": "square3", "range": 6},
        [{"type": "damage", "dice": "1d4", "element": "physical"}],
        weapon_req="any",
    )

    def rolled(caster_xy: tuple[int, int], center: tuple[int, int]) -> AttackRolled:
        state = arena([(*caster_xy, caster_template([square]))], skills=[square])
        me = hero(state, caster_xy)
        action = UseSkill(
            unit_id=me.id, skill_id=square.id, target_pos=Pos(x=center[0], y=center[1])
        )
        result = resolve(with_rolls(give_turn(state, me.id), [(20, 10), (4, 3)]), action)
        assert not of(result.events, PartDamaged)
        (e,) = [e for e in of(result.events, AttackRolled) if e.target_id == giant(state).id]
        return e

    north = rolled((6, 0), (6, 4))
    south = rolled((6, 12), (6, 8))
    assert north.hit_tile == Pos(x=6, y=5) and south.hit_tile == Pos(x=6, y=7)
    assert north.defense_value_permille == south.defense_value_permille


# ---------------------------------------------------------------------------
# 11. 限時封招（T14）
# ---------------------------------------------------------------------------


def _break_core(state: BattleState) -> Ctx:
    ctx = Ctx(state.clone())
    g = giant(ctx.state)
    execute(
        ctx,
        [
            DamageEffect(
                target_id=g.id,
                source_id=UnitId("unit_0002"),
                cause="attack",
                flat=60,
                part_id="core",
            )
        ],
    )
    return ctx


def test_t14_a_timed_seal_lasts_two_rounds_and_survives_phase_changes() -> None:
    state = breathing(arena([(6, 11, "hero_archer")]))
    state.round = 5
    ctx = _break_core(state)
    g = giant(ctx.state)
    (sealed,) = of(ctx.events, SkillSealed)
    assert sealed.skill_id == INHALE and sealed.rounds == 2
    assert g.sealed_until == {INHALE: 7} and g.sealed_skills == ()
    inhale = ctx.state.ruleset.skill_def(INHALE)
    g.ap = 9
    for rnd, blocked in ((5, True), (6, True), (7, False), (8, False)):
        ctx.state.round = rnd
        problem = skill_problem(ctx.state, g, inhale)
        assert (problem is not None and "封住" in problem) is blocked, rnd
    ctx.state.round = 6  # 換階段不清
    g.phase_index = 0
    g.hp = 1
    check_boss_phases(ctx)
    assert g.phase_index == 1 and g.sealed_until == {INHALE: 7}
    text = describe_event(sealed, ctx.state)
    assert text is not None and "被封住 2 回合" in text


def test_t14_breaking_the_core_interrupts_the_charge() -> None:
    state = breathing(arena([(6, 11, "hero_archer")]))
    g = giant(state)
    g.statuses.append(StatusInstance(CHARGING, remaining=1, source_id=g.id, skill_id=INHALE))
    ctx = _break_core(state)
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]


def test_t14_a_permanent_seal_wins_over_a_timed_one() -> None:
    state = breathing(arena([(6, 11, "hero_archer")]))
    giant(state).sealed_skills = (INHALE,)
    ctx = _break_core(state)
    assert giant(ctx.state).sealed_until == {}


# ---------------------------------------------------------------------------
# 12. farthest_enemy（R5、T15）
# ---------------------------------------------------------------------------


def _cast(state: BattleState) -> Any:
    g = giant(state)
    return resolve(give_turn(state, g.id), UseSkill(unit_id=g.id, skill_id=SPLASH))


def test_r5_the_farthest_enemy_is_chosen_ties_by_y_then_x() -> None:
    # (6, 9) 離南排 2；(6, 12) 離南排 5；(0, 6) 離西欄 5（同距離 y 小的贏）
    state = arena([(6, 9, "hero_fighter"), (6, 12, "hero_fighter"), (0, 6, "hero_fighter")])
    found = farthest_enemy(state, giant(state))
    assert found is not None and found.xy == (0, 6)
    result = _cast(state)
    (charged,) = of(result.events, FollowupCharged)
    assert charged.anchored and charged.pos == Pos(x=0, y=6)
    assert charged.anchor_target_id == found.id
    assert len(charged.tiles) == 6  # (0, 6) 的 3×3 在地圖內的 6 格
    text = describe_event(charged, result.state)
    assert text is not None and "最遠的" in text


def test_r5_unseen_concealed_enemies_do_not_count_and_range_does_not_matter() -> None:
    state = arena([(6, 9, "hero_fighter"), (6, 12, "hero_fighter")])
    far = hero(state, (6, 12))
    far.statuses.append(StatusInstance("concealed", remaining=3, source_id=far.id))
    found = farthest_enemy(state, giant(state))
    assert found is not None and found.xy == (6, 9)
    near = hero(state, (6, 9))
    near.statuses.append(StatusInstance("concealed", remaining=3, source_id=near.id))
    assert farthest_enemy(state, giant(state)) == near  # 2 格內照得到
    near.pos = Pos(x=12, y=0)  # 遠到看不見：沒有可以落下的敵人
    assert farthest_enemy(state, giant(state)) is None
    g = giant(state)
    g.ap = 9
    problem = skill_problem(state, g, state.ruleset.skill_def(SPLASH))
    assert problem is not None and "找不到可以落下的敵人" in problem
    assert not [
        a for a in legal_actions(give_turn(state, g.id)) if getattr(a, "skill_id", None) == SPLASH
    ]


def test_t15_one_action_without_a_tile_and_target_pos_is_refused() -> None:
    state = arena([(6, 12, "hero_fighter")])
    g = giant(state)
    actions = [
        a for a in legal_actions(give_turn(state, g.id)) if getattr(a, "skill_id", None) == SPLASH
    ]
    assert actions == [UseSkill(unit_id=g.id, skill_id=SPLASH)]
    with pytest.raises(IllegalActionError):
        resolve(
            give_turn(state, g.id),
            UseSkill(unit_id=g.id, skill_id=SPLASH, target_pos=Pos(x=6, y=12)),
        )


def test_t15_farthest_needs_a_first_segment_without_a_tile() -> None:
    with pytest.raises(ValueError, match="第一段的形狀不能選格"):
        splash_skill(shape={"type": "square3", "range": 4})


def test_r5_the_landing_stays_when_the_enemy_walks_away() -> None:
    state = arena([(6, 9, "hero_fighter"), (6, 12, "hero_fighter")])
    after = _cast(state).state
    far = hero(after, (6, 12))
    far.pos = Pos(x=2, y=12)
    (info,) = charge_infos(after)
    assert info.anchored and info.pos == Pos(x=6, y=12)
    ctx = Ctx(after.clone())
    release_at_turn_start(ctx, giant(ctx.state))
    (follow,) = of(ctx.events, SkillFollowup)
    assert follow.origin == Pos(x=6, y=12)
    assert not [e for e in of(ctx.events, DamageDealt) if e.target_id == far.id]


# ---------------------------------------------------------------------------
# 13. 火地生長（R6 A、T16）
# ---------------------------------------------------------------------------

GROW_PHASES: tuple[dict[str, Any], ...] = (
    PHASES[0],
    {
        **PHASES[1],
        "tiles": [{"at": [x, 8], "surface": "fire"} for x in (5, 6, 7)],
        "grow_surface": {"surface": "fire", "max_rows": 4},
    },
)


def _grow_arena(**kw: Any) -> BattleState:
    state = arena(
        [(7, 9, "hero_fighter"), (0, 0, "hero_fighter")],
        boss=giant_boss(phases=GROW_PHASES),
        objects=((5, 10, "low_wall"),),
        **kw,
    )
    ctx = Ctx(state.clone())
    g = giant(ctx.state)
    g.hp = g.max_hp // 3
    check_boss_phases(ctx)  # 進第 2 階段：第 1 排火地由階段的 tiles 放
    return ctx.state


def _fire(state: BattleState) -> set[tuple[int, int]]:
    return {
        (x, y) for y in range(8, 13) for x in (5, 6, 7) if state.tile(x, y).surface is Surface.FIRE
    }


def test_r6_fire_grows_one_row_south_each_round_and_stops_at_obstacles() -> None:
    state = _grow_arena()
    assert _fire(state) == {(5, 8), (6, 8), (7, 8)}
    rounds = []
    for _ in range(5):
        ctx = Ctx(state.clone())
        run_environment(ctx)
        state = ctx.state
        rounds.append(sorted(_fire(state)))
        assert of(ctx.events, SurfaceChanged) or len(rounds) > 3
    # 西欄：(5, 9) 長出、(5, 10) 是矮牆停住；中欄長到第 4 排 (6, 11) 為止；東欄 (7, 9) 有人擋住
    assert rounds[0] == [(5, 8), (5, 9), (6, 8), (6, 9), (7, 8)]
    assert rounds[1] == [(5, 8), (5, 9), (6, 8), (6, 9), (6, 10), (7, 8)]
    assert (
        rounds[2]
        == rounds[3]
        == rounds[4]
        == [(5, 8), (5, 9), (6, 8), (6, 9), (6, 10), (6, 11), (7, 8)]
    )
    assert state.tile(6, 12).surface is Surface.NONE  # 最多 4 排
    assert state.tile(6, 11).surface_remaining is None  # 不會到期（同階段的 tiles）


def test_r6_water_and_lava_stop_the_growth_and_telegraph_shows_it() -> None:
    state = _grow_arena(surfaces=((6, 9, "water"),), lava=((5, 9),))
    tg = telegraph(state)
    grown = {(c.pos.x, c.pos.y) for c in tg.changes if c.kind == "surface" and c.pos is not None}
    assert grown.isdisjoint({(5, 9), (6, 9), (7, 9)})  # 岩漿、水、有人
    for _ in range(3):
        ctx = Ctx(state.clone())
        run_environment(ctx)
        state = ctx.state
    assert state.tile(6, 9).surface is Surface.WATER
    assert _fire(state) == {(5, 8), (6, 8), (7, 8)}


def test_r6_no_growth_outside_the_phase() -> None:
    state = arena([(7, 9, "hero_fighter")], boss=giant_boss(phases=GROW_PHASES))
    ctx = Ctx(state.clone())
    run_environment(ctx)
    assert _fire(ctx.state) == set()


# ---------------------------------------------------------------------------
# GB-1a 待決 2：倒地免疫的紀錄文字
# ---------------------------------------------------------------------------


def test_prone_immunity_has_a_log_line() -> None:
    state = arena([(6, 11, "hero_archer")])
    e = EffectFizzled(
        seq=0, round=1, effect_kind="status", pos=giant(state).pos, reason="immovable"
    )
    assert describe_event(e, state) == "  巨大的身軀紋風不動：擊不倒"


# ---------------------------------------------------------------------------
# 14. 確定性：同種子兩次相同、紀錄往返重播、clone 與 JSON 保留新欄位
# ---------------------------------------------------------------------------


def test_same_seed_same_battle_and_the_log_replays() -> None:
    m = make_map(FLAT13, ally=[(6, 11), (4, 6)], enemy=[(6, 6)]).model_copy(
        update={"giant_facing": {GIANT_ID: "south"}}
    )
    spawns = [
        spawn_giant(Team.ENEMY, (6, 6), giant_boss(max_hp=60, phases=GROW_PHASES)),
        spawn(Team.ALLY, (6, 11), template("hero_archer"), skills=None),
        spawn(Team.ALLY, (4, 6), template("hero_fighter"), skills=None),
    ]
    setup = make_setup(m, spawns, max_rounds=12, skills=[splash_skill()])
    policy = UtilityAI(library().ai_profiles)
    a, b = run_battle(setup, 3, policy), run_battle(setup, 3, policy)
    assert a.to_log().model_dump_json() == b.to_log().model_dump_json()
    log = BattleLog.model_validate_json(a.to_log().model_dump_json())
    again = replay(log.setup, log.seed, log.actions)
    assert again.events == a.events and state_to_json(again.state) == state_to_json(a.state)
    assert of(a.events, FollowupCharged)  # 有放到落在最遠敵人的招


def test_clone_and_json_keep_the_timed_seal() -> None:
    state = breathing(arena([(6, 11, "hero_archer")]))
    giant(state).sealed_until = {INHALE: 7}
    assert giant(state.clone()).sealed_until == {INHALE: 7}
    back = state_from_json(state_to_json(state))
    assert giant(back).sealed_until == {INHALE: 7}
    plain = arena([(6, 11, "hero_archer")])
    assert "sealed_until" not in state_to_json(plain)
