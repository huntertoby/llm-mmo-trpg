"""定時炸彈（Phase 3D-8b，``docs/phases/Phase3D計畫.md`` 8.2、8.4）：附加、環境回合倒數、移動後在新
位置爆炸、目標倒下仍爆炸、淨化移除而驅散不移除、環境預告（倒數與爆炸範圍）、元素與表面互動、
schema、預算、文字、AI 與重播。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_skill, no_reactions
from tests.engine.skill_helpers import SID, U1, U2, U3, U4, battle, cast, hit_with, of
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, EndTurn, UseSkill, resolve, state_from_json, state_to_json
from trpg.engine import telegraph as make_telegraph
from trpg.engine.context import Ctx
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import CleanseEffect, DamageEffect
from trpg.engine.environment import run_environment
from trpg.engine.events import (
    BombExploded,
    BombTicked,
    DamageDealt,
    EffectFizzled,
    EventBase,
    StatusApplied,
    StatusRemoved,
    SurfaceChanged,
    UnitDowned,
)
from trpg.engine.resources import dispelled_buffs
from trpg.engine.state import StatusInstance
from trpg.engine.view import project_for
from trpg.narrative.events import describe_event
from trpg.narrative.skills import skill_card
from trpg.narrative.telegraph import bomb_text, change_text
from trpg.shared.types import Pos, Surface, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

BOMB: dict[str, Any] = {
    "type": "delayed_damage",
    "dice": "3d6",
    "element": "fire",
    "rounds": 2,
    "radius": 1,
}


def bomb_skill(**changes: Any) -> SkillDef:
    effect = {**BOMB, **changes}
    data = make_skill(
        SID,
        {"type": "single", "range": 6},
        [effect],
        ap_cost=2,
        cost={"mana": 0, "cooldown": 2},
    ).model_dump(mode="json")
    data["skeleton"] = "control"
    return SkillDef.model_validate(data)


def tank(xy: tuple[int, int], hp: int = 500) -> tuple[int, int, Any]:
    return (*xy, no_reactions("bandit", max_hp=hp))


def bombed(
    *,
    foes: list[Any] | None = None,
    allies: list[tuple[int, int]] | None = None,
    carrier: str | None = None,
) -> BattleState:
    """施放炸彈符之後的戰場：U1 施放者 (3, 3)，之後是 ``allies``、``foes``；炸彈綁在 ``carrier``
    （預設第一個敵人）身上。"""
    state = battle(bomb_skill(), foes or [tank((5, 3))], allies=allies or [])
    foe = carrier or f"unit_000{2 + len(allies or [])}"
    return cast(hit_with(state, [(6, 3)] * 6), target_id=foe).state


def environment(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    """對狀態複本執行一次環境回合（炸彈倒數與爆炸）。"""
    ctx = Ctx(state.clone())
    run_environment(ctx)
    return ctx.state, ctx.events


# ---------------------------------------------------------------------------
# 附加
# ---------------------------------------------------------------------------


def test_the_skill_binds_a_time_bomb_to_the_hit_enemy() -> None:
    state = battle(bomb_skill(), [tank((5, 3))])
    result = cast(hit_with(state, [(6, 3)]), target_id=U2)
    (applied,) = of(result, StatusApplied)
    assert applied.status_id == "time_bomb" and applied.duration == 2
    status = result.state.units[U2].get_status("time_bomb")
    assert status is not None
    assert (status.remaining, status.source_id, status.skill_id) == (2, U1, SID)
    assert of(result, DamageDealt) == []  # 附加時沒有傷害


def test_a_miss_binds_nothing() -> None:
    from tests.engine.helpers import with_rolls  # noqa: PLC0415

    state = with_rolls(battle(bomb_skill(), [tank((5, 3))]), [(20, 1)])
    result = cast(state, target_id=U2)
    assert not result.state.units[U2].has_status("time_bomb")


def test_a_carrier_cannot_be_bombed_again() -> None:
    state = bombed()
    again = cast(_ready(state), target_id=U2)
    assert [e.reason for e in of(again, EffectFizzled)] == ["already_bombed"]
    assert again.state.units[U2].get_status("time_bomb").remaining == 2  # type: ignore[union-attr]


def _ready(state: BattleState) -> BattleState:
    from tests.engine.helpers import give_turn  # noqa: PLC0415

    s = give_turn(state, U1)
    s.units[U1].cooldowns.clear()
    return hit_with(s, [(6, 3)])


# ---------------------------------------------------------------------------
# 倒數與爆炸
# ---------------------------------------------------------------------------


def test_the_countdown_ticks_every_environment_turn_and_then_explodes() -> None:
    state = bombed(allies=[(2, 3)], foes=[tank((5, 3)), tank((5, 4)), tank((6, 6))], carrier=U3)
    first, events = environment(state)
    (tick,) = [e for e in events if isinstance(e, BombTicked)]
    assert (tick.unit_id, tick.remaining, tick.radius) == (U3, 1, 1)
    assert first.units[U3].get_status("time_bomb").remaining == 1  # type: ignore[union-attr]
    assert not any(isinstance(e, BombExploded) for e in events)
    second, events = environment(first)
    (blast,) = [e for e in events if isinstance(e, BombExploded)]
    assert (blast.unit_id, blast.cause, blast.element.value) == (U3, "timer", "fire")
    assert blast.pos == Pos(x=5, y=3) and blast.radius == 1
    assert {(p.x, p.y) for p in blast.tiles} == {(5, 3), (4, 3), (6, 3), (5, 2), (5, 4)}
    assert not second.units[U3].has_status("time_bomb")
    removed = [e for e in events if isinstance(e, StatusRemoved) and e.status_id == "time_bomb"]
    assert [e.reason for e in removed] == ["expired"]


def test_the_blast_hurts_everyone_in_range_friend_or_foe_and_nobody_outside() -> None:
    # 攜帶者 U3 在 (5, 3)；友方 U2 (4, 3) 與敵人 U4 (5, 4) 在半徑內；施放者 U1 (3, 3) 距離 2、
    # 敵人 U5 (6, 6) 更遠，都在半徑外
    state = battle(
        bomb_skill(),
        [tank((5, 3)), tank((5, 4)), tank((6, 6))],
        allies=[(4, 3)],
    )
    state = cast(hit_with(state, [(6, 3)]), target_id=U3).state  # 炸彈綁在 U3 (5, 3)
    once, _ = environment(state)
    final, events = environment(once)
    hurt = {e.target_id: e for e in events if isinstance(e, DamageDealt)}
    assert set(hurt) == {U2, U3, U4}  # 友方 U2、攜帶者 U3、敵人 U4
    assert all(e.cause == "explosion" and e.element.value == "fire" for e in hurt.values())
    assert final.units[U1].hp == final.units[U1].max_hp  # 施放者在 2 格外
    assert final.units[U2].hp < final.units[U2].max_hp  # 友方（隊友）也會受傷


def test_the_caster_is_hurt_too_when_standing_in_the_blast() -> None:
    state = battle(bomb_skill(), [tank((4, 3))])  # 攜帶者緊鄰施放者
    state = cast(hit_with(state, [(6, 3)]), target_id=U2).state
    once, _ = environment(state)
    _, events = environment(once)
    assert U1 in {e.target_id for e in events if isinstance(e, DamageDealt)}


def test_the_damage_is_the_dice_plus_half_the_scaling_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.engine.skill_helpers import script_rolls  # noqa: PLC0415

    state = battle(bomb_skill(radius=0), [tank((5, 3))])
    state = cast(hit_with(state, [(6, 3)]), target_id=U2).state
    once, _ = environment(state)
    script_rolls(monkeypatch, [3, 4, 5])
    _, events = environment(once)
    (hit,) = [e for e in events if isinstance(e, DamageDealt)]
    attr = state.units[U1].attributes
    from trpg.shared.types import Attribute  # noqa: PLC0415

    bonus = attr[Attribute.INT] // 2
    assert hit.rolls == (3, 4, 5) and hit.base_amount == 12 + bonus


def test_the_bomb_explodes_where_the_carrier_stands_after_it_moves() -> None:
    state = bombed(foes=[tank((5, 3)), tank((6, 5))], carrier=U2)
    once, _ = environment(state)
    moved = once.clone()
    moved.units[U2].pos = Pos(x=1, y=5)  # 攜帶者走到別處
    moved.units[U3].pos = Pos(x=1, y=6)  # 旁邊的另一名敵人
    final, events = environment(moved)
    (blast,) = [e for e in events if isinstance(e, BombExploded)]
    assert blast.pos == Pos(x=1, y=5)
    assert U3 in {e.target_id for e in events if isinstance(e, DamageDealt)}
    assert final.units[U3].hp < final.units[U3].max_hp


def test_a_carrier_that_goes_down_explodes_at_once_where_it_fell() -> None:
    state = battle(bomb_skill(), [tank((5, 3)), tank((5, 4))], allies=[(4, 3)])
    state = cast(hit_with(state, [(6, 3)]), target_id=U3).state  # 炸彈綁在 U3 (5, 3)
    result = run_effects(
        state, [DamageEffect(target_id=U3, mode="lethal", apply_element_mod=False)]
    )
    blasts = of(result, BombExploded)
    assert [(b.unit_id, b.cause, b.pos) for b in blasts] == [(U3, "downed", Pos(x=5, y=3))]
    index = {type(e).__name__: i for i, e in enumerate(result.events)}
    assert index["UnitDowned"] < index["BombExploded"]
    after = result.events[index["BombExploded"] :]
    hurt = {e.target_id for e in after if isinstance(e, DamageDealt)}
    assert U3 not in hurt and {U2, U4} <= hurt  # 倒下的攜帶者不算受傷者；鄰近單位受傷
    assert not result.state.units[U3].has_status("time_bomb")
    removed = [e for e in of(result, StatusRemoved) if e.status_id == "time_bomb"]
    assert [e.reason for e in removed] == ["downed"]
    # 之後的環境回合不會再爆炸
    _, events = environment(result.state)
    assert not any(isinstance(e, BombExploded) for e in events)


def test_a_blast_that_downs_another_carrier_sets_off_its_bomb_too() -> None:
    state = battle(bomb_skill(), [tank((5, 3)), tank((6, 3), hp=1), tank((6, 6))])
    s = cast(hit_with(state, [(6, 3)]), target_id=U2).state
    s = cast(_ready(s), target_id=U3).state
    s.units[U2].statuses = [StatusInstance("time_bomb", 1, U1, skill_id=SID)]  # 這輪爆炸
    s.units[U3].statuses = [StatusInstance("time_bomb", 2, U1, skill_id=SID)]  # 還有 2 輪
    _, events = environment(s)
    blasts = [(e.unit_id, e.cause) for e in events if isinstance(e, BombExploded)]
    assert blasts == [(U2, "timer"), (U3, "downed")]
    assert [e.unit_id for e in events if isinstance(e, UnitDowned)] == [U3]


# ---------------------------------------------------------------------------
# 淨化與驅散
# ---------------------------------------------------------------------------


def test_cleanse_removes_the_bomb_and_nothing_explodes() -> None:
    state = bombed()
    result = run_effects(state, [CleanseEffect(target_id=U2)])
    assert not result.state.units[U2].has_status("time_bomb")
    once, _ = environment(result.state)
    _, events = environment(once)
    assert not any(isinstance(e, (BombExploded, BombTicked)) for e in events)


def test_dispel_does_not_remove_the_bomb() -> None:
    state = bombed()
    ctx = Ctx(state.clone())
    assert dispelled_buffs(ctx, ctx.state.units[U2], "all") == []
    status = library().ruleset.status_def("time_bomb")
    assert status.polarity == "debuff" and not status.beneficial


# ---------------------------------------------------------------------------
# 元素與表面
# ---------------------------------------------------------------------------


def test_a_fire_blast_ignites_oil_on_the_surrounding_tiles() -> None:
    state = battle(bomb_skill(), [tank((5, 3))], surfaces=((5, 4, "oil"),))
    state = cast(hit_with(state, [(6, 3)]), target_id=U2).state
    once, _ = environment(state)
    final, events = environment(once)
    assert final.tile(5, 4).surface is Surface.FIRE
    assert any(isinstance(e, SurfaceChanged) and e.pos == Pos(x=5, y=4) for e in events)


# ---------------------------------------------------------------------------
# 環境預告
# ---------------------------------------------------------------------------


def test_the_telegraph_lists_the_countdown_and_the_blast_area() -> None:
    state = bombed(foes=[tank((5, 3)), tank((5, 4))])
    forecast = make_telegraph(state)
    (info,) = forecast.bombs
    assert (info.unit_id, info.remaining, info.radius, info.explodes) == (U2, 2, 1, False)
    assert {(p.x, p.y) for p in info.tiles} == {(5, 3), (4, 3), (6, 3), (5, 2), (5, 4)}
    assert not any(c.kind == "bomb_exploded" for c in forecast.changes)
    assert "還要 2 次環境回合爆炸" in bomb_text(state, info)


def test_the_telegraph_matches_the_real_environment_turn_when_the_bomb_goes_off() -> None:
    state = bombed(foes=[tank((5, 3)), tank((5, 4))])
    once, _ = environment(state)
    forecast = make_telegraph(once)
    (info,) = forecast.bombs
    assert info.explodes and info.remaining == 1
    (blast,) = [c for c in forecast.changes if c.kind == "bomb_exploded"]
    assert blast.unit_id == U2 and blast.amount == 1 and len(blast.tiles) == 5
    assert {c.unit_id for c in forecast.changes if c.kind == "unit_damaged"} >= {U2, U3}
    assert "將在" in change_text(once, blast) and "爆炸" in change_text(once, blast)
    _, events = environment(once)
    assert [e.model_dump(exclude={"seq"}) for e in events] == [
        e.model_dump(exclude={"seq"}) for e in forecast.events
    ]


def test_the_real_turn_flow_counts_down_once_per_round() -> None:
    state = bombed()
    start_round = state.round
    s = state
    explosions: list[tuple[int, str]] = []
    for _ in range(40):
        if s.ended or s.round > start_round + 2:
            break
        r = resolve(s, EndTurn(unit_id=s.active_unit))  # type: ignore[arg-type]
        explosions += [(e.round, e.cause) for e in r.events if isinstance(e, BombExploded)]
        s = r.state
    assert explosions == [(start_round + 1, "timer")]  # 第二次環境回合（rounds: 2）爆炸


# ---------------------------------------------------------------------------
# 視圖、文字
# ---------------------------------------------------------------------------


def test_the_view_shows_the_countdown_and_the_blast_radius() -> None:
    state = bombed()
    view = project_for(state, Team.ALLY)
    unit = next(u for u in view.units if u.id == U2)
    (status,) = [s for s in unit.statuses if s.status_id == "time_bomb"]
    assert (status.remaining, status.blast_radius, status.source_id) == (2, 1, U1)


def test_the_log_and_the_skill_card_describe_the_bomb() -> None:
    state = bombed()
    once, ticks = environment(state)
    _, events = environment(once)
    (tick,) = [e for e in ticks if isinstance(e, BombTicked)]
    (blast,) = [e for e in events if isinstance(e, BombExploded)]
    assert "還剩 1 輪" in (describe_event(tick, once) or "")
    assert "爆炸了" in (describe_event(blast, once) or "")
    card = str(skill_card(library(), library().skills["skill_time_bomb_rune"]))
    assert "定時炸彈" in card and "環境回合" in card


def test_the_state_round_trips_with_a_bomb() -> None:
    state = bombed()
    again = state_from_json(state_to_json(state))
    status = again.units[U2].get_status("time_bomb")
    assert status is not None and status.skill_id == SID
    assert state_to_json(again) == state_to_json(state)


# ---------------------------------------------------------------------------
# schema、預算
# ---------------------------------------------------------------------------


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


def test_schema_requires_every_parameter_and_a_spell() -> None:
    base = bomb_skill().model_dump(mode="json")
    for name in ("dice", "element", "rounds", "radius"):
        effect = {k: v for k, v in BOMB.items() if k != name}
        with pytest.raises(ValueError, match="delayed_damage"):
            SkillDef.model_validate({**base, "effects": [effect]})
    weapon = {**base, "category": "weapon", "weapon_req": "melee", "scaling_attr": "str"}
    with pytest.raises(ValueError, match="法術技"):
        SkillDef.model_validate(weapon)
    with pytest.raises(ValueError, match="最多一個"):
        SkillDef.model_validate({**base, "effects": [BOMB, BOMB]})


def test_parameter_ranges_and_targets_are_checked_across_files() -> None:
    assert _problems(bomb_skill()) == []
    for field, value in (("rounds", 4), ("radius", 3)):
        with pytest.raises(ValueError):
            bomb_skill(**{field: value})
    allies = bomb_skill(affects="allies")
    assert any("不能搭配 affects" in p for p in _problems(allies))
    area = bomb_skill()
    data = area.model_dump(mode="json")
    data["shape"] = {"type": "square3", "range": 5}
    assert any("只能搭配形狀" in p for p in _problems(SkillDef.model_validate(data)))


def test_the_budget_scales_with_the_dice_and_the_radius() -> None:
    lib = library()
    small = skill_budget(bomb_skill(radius=0), lib)
    big = skill_budget(bomb_skill(radius=2), lib)
    assert small.total < skill_budget(bomb_skill(radius=1), lib).total < big.total
    rules = lib.budget
    expected = 10.5 * (rules.delayed_damage_base_targets_permille + 400 * 1) / 1000
    assert float(skill_budget(bomb_skill(radius=1), lib).effects[0].points) == pytest.approx(
        expected
    )


def test_the_demo_skill_is_valid_in_budget_and_equipped() -> None:
    lib = library()
    skill = lib.skills["skill_time_bomb_rune"]
    assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
    assert "skill_time_bomb_rune" in lib.builds.by_id()["build_bomber"].hero.skills


# ---------------------------------------------------------------------------
# AI 與整場重播
# ---------------------------------------------------------------------------


def test_the_ai_plants_the_bomb_on_a_cluster_but_not_next_to_its_own_side() -> None:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415

    ai = UtilityAI(library().ai_profiles)

    def plants(state: BattleState) -> bool:
        action = ai(state)
        return isinstance(action, UseSkill) and action.skill_id == SID

    cluster = battle(bomb_skill(), [tank((5, 3)), tank((5, 4)), tank((6, 3))])
    assert plants(cluster)
    friendly = battle(bomb_skill(), [tank((5, 3))], allies=[(4, 3), (6, 3), (5, 2), (5, 4)])
    assert not plants(friendly)


def test_a_battle_with_a_bomber_replays_exactly() -> None:
    from tests.engine.test_zone_ai import _run  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run("build_bomber", "open_plain", 4)
    again = replay(setup, 4, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
