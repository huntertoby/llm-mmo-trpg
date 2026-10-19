"""撞擊（Phase 3C-3a 5.0）：被強制位移的單位因障礙提前停下時，每少走 1 格受一次撞擊傷害。"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.battle import Dice
from trpg.engine import BattleState, Shove, UseSkill, legal_actions, preview, resolve
from trpg.engine import modifiers as mods
from trpg.engine.effects import PushEffect, run_effects
from trpg.engine.events import (
    Collided,
    DamageDealt,
    EventBase,
    ObjectDamaged,
    UnitFell,
    UnitMoved,
)
from trpg.engine.skills.conditions import Subject
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
ROW = "0000000"
FLAT = "\n".join([ROW] * 7)
FOE = (2, 3)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def collisions(events: Sequence[EventBase]) -> list[DamageDealt]:
    return [e for e in of(events, DamageDealt) if e.cause == "collision"]


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4) -> None:
    """d20 一律 19（命中、不暴擊）、其他骰子一律 ``die``（撞擊傷害固定）。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(die, sides))


def arena(
    *,
    foe: tuple[int, int] = FOE,
    terrain: str | None = None,
    heights: str = FLAT,
    objects: Sequence[tuple[int, int, str]] = (),
    second: tuple[int, int] | None = None,
) -> BattleState:
    """U1 我方戰士（在 (0, 0)）；U2 敵人（不反應、HP 200）；``second`` 為另一個敵人 U3。"""
    enemies = [foe] + ([] if second is None else [second])
    m = make_map(heights, terrain, ally=[(0, 0)], enemy=enemies, objects=objects)
    spawns = [spawn(Team.ALLY, (0, 0), "hero_fighter")]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in enemies]
    return give_turn(make_state(m, spawns), U1)


def east(distance: int, **kw: object) -> PushEffect:
    return PushEffect(source_id=U1, target_id=U2, direction=(1, 0), distance=distance, **kw)  # type: ignore[arg-type]


def terrain_with(char: str, x: int, y: int = 3) -> str:
    rows = ["." * 7 for _ in range(7)]
    rows[y] = rows[y][:x] + char + rows[y][x + 1 :]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# 撞到什麼
# ---------------------------------------------------------------------------


def test_pushed_into_a_wall_two_tiles_short_takes_two_collision_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(terrain=terrain_with("#", 3))
    result = run_effects(state, [east(2)])
    (hit,) = of(result.events, Collided)
    assert (hit.unit_id, hit.obstacle, hit.shortfall, hit.source_id) == (U2, "wall", 2, U1)
    assert result.state.units[U2].xy == FOE  # 第一步就被擋住
    damage = collisions(result.events)
    assert [(d.target_id, d.source_id, d.amount, d.element.value) for d in damage] == [
        (U2, U1, 4, "physical"),
        (U2, U1, 4, "physical"),
    ]
    assert result.state.units[U2].hp == 200 - 8


def test_one_tile_short_is_one_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = run_effects(arena(terrain=terrain_with("#", 4)), [east(2)])
    (hit,) = of(result.events, Collided)
    assert (hit.shortfall, hit.obstacle) == (1, "wall")
    assert result.state.units[U2].xy == (3, 3)
    assert len(collisions(result.events)) == 1


def test_map_edge_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = run_effects(arena(foe=(6, 3)), [east(1)])
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall) == ("edge", 1)
    assert len(collisions(result.events)) == 1


def test_hitting_another_unit_hurts_both_and_credits_the_pusher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(second=(3, 3))
    result = run_effects(state, [east(2)])
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.other_id, hit.shortfall) == ("unit", U3, 2)
    damage = collisions(result.events)
    assert sorted((d.target_id, d.source_id) for d in damage) == [(U2, U1)] * 2 + [(U3, U1)] * 2
    assert result.state.units[U3].hp == 200 - 8 and result.state.units[U2].hp == 200 - 8


def test_hitting_a_breakable_object_damages_the_object_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = run_effects(arena(objects=[(3, 3, "stone_pillar")]), [east(1)])
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.object_id) == ("object", "obj_0001")
    (dealt,) = collisions(result.events)
    (obj,) = of(result.events, ObjectDamaged)
    assert dealt.amount == 4 and (obj.cause, obj.amount, obj.source_id) == ("collision", 4, U1)
    assert hit.object_id is not None and result.state.objects[hit.object_id].hp == 60 - 4


def test_a_step_up_blocks_like_a_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    heights = "\n".join(["0000000"] * 3 + ["0010000"] + ["0000000"] * 3)
    heights = heights.replace("0010000", "0001000")
    result = run_effects(arena(heights=heights), [east(1)])
    (hit,) = of(result.events, Collided)
    assert hit.obstacle == "wall"


# ---------------------------------------------------------------------------
# 不算撞擊
# ---------------------------------------------------------------------------


def test_falling_into_deadly_terrain_is_not_a_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = run_effects(arena(terrain=terrain_with("x", 3)), [east(2)])
    assert of(result.events, Collided) == []
    assert collisions(result.events) == []


def test_falling_down_a_ledge_is_not_a_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    rows = ["0000000"] * 7
    rows[3] = "0200000"  # 敵人站在 (1, 3)，高 2；往東的 (2, 3) 高 0（落差 2）
    result = run_effects(arena(foe=(1, 3), heights="\n".join(rows)), [east(1)])
    assert of(result.events, UnitFell)
    assert of(result.events, Collided) == []
    assert collisions(result.events) == []


def test_a_free_push_has_no_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = run_effects(arena(), [east(2)])
    assert result.state.units[U2].xy == (4, 3)
    assert of(result.events, Collided) == []


# ---------------------------------------------------------------------------
# 強化撞擊、超過上限
# ---------------------------------------------------------------------------


def test_collision_dice_replace_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = run_effects(
        arena(terrain=terrain_with("#", 3)), [east(1, collision_dice=Dice(count=2, sides=6))]
    )
    (dealt,) = collisions(result.events)
    assert dealt.rolls == (4, 4) and dealt.amount == 8


def test_the_core_dice_can_be_changed() -> None:
    assert library().ruleset.core.collision_damage_dice == Dice(count=1, sides=6)


def test_push_distance_over_the_cap_becomes_collision_damage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """颶風踢（推 2 格，已達上限）＋重踏（+1）：多出的 1 格改為一次撞擊，就算沒撞到東西。"""
    always(monkeypatch)
    hero = template("hero_fighter", reactions=[], skills=["skill_gale_kick", "skill_heavy_stomp"])
    m = make_map(FLAT, ally=[(1, 3)], enemy=[FOE])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))]
        ),
        U1,
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2))
    assert result.state.units[U2].xy == (4, 3)  # 距離仍是 2 格（上限）
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall, hit.source_id) == ("excess", 1, U1)
    assert len(collisions(result.events)) == 1
    # 推完之後才結算：撞擊在移動事件之後
    order = [type(e) for e in result.events]
    assert order.index(Collided) > max(i for i, t in enumerate(order) if t is UnitMoved)
    use = mods.skill_use(library().skills["skill_gale_kick"])
    hero_unit = state.units[U1]
    assert mods.displace_split(state, hero_unit, use, Subject(None, FOE), 2) == (2, 1)
    assert mods.displace_split(state, hero_unit, use, Subject(None, FOE), 1) == (2, 0)


def test_basic_shove_collides_too() -> None:
    """基本動作的推擊也適用：推 2 格，第二步被牆擋住，少走 1 格。"""
    hero = template("hero_fighter", reactions=[], skills=["skill_heavy_stomp"])
    m = make_map(FLAT, terrain_with("#", 4), ally=[(1, 3)], enemy=[FOE])
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))],
        ),
        U1,
    )
    result = resolve(with_rolls(state, [(20, 20)]), Shove(unit_id=U1, target_id=U2))
    assert result.state.units[U2].xy == (3, 3)
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall) == ("wall", 1)
    assert len(collisions(result.events)) == 1


# ---------------------------------------------------------------------------
# 基本推擊貼牆撞擊（Phase 3C-3b 5.4）
# ---------------------------------------------------------------------------

SHOVER = (1, 3)
PUSHED = (2, 3)


def shove_scene(
    *,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    second: tuple[int, int] | None = None,
    shover: tuple[int, int] = SHOVER,
    foe: tuple[int, int] = PUSHED,
) -> BattleState:
    """U1 我方戰士在 ``shover`` 推 U2（不反應、HP 200）；``second`` 為 U3（擋在身後）。"""
    enemies = [foe] + ([] if second is None else [second])
    m = make_map(FLAT, terrain, ally=[shover], enemy=enemies, objects=objects)
    spawns = [spawn(Team.ALLY, shover, "hero_fighter")]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in enemies]
    return give_turn(make_state(m, spawns), U1)


WIN = [(20, 20)]  # 對抗：推擊者大成功
LOSE = [(20, 1), (20, 20)]  # 推擊者擲 1、目標擲 20


def shove(state: BattleState, rolls: list[tuple[int, int]] = WIN) -> Any:
    return resolve(with_rolls(state, rolls), Shove(unit_id=U1, target_id=U2))


def test_shove_against_a_wall_is_legal_and_the_target_takes_one_collision() -> None:
    state = shove_scene(terrain=terrain_with("#", 3))
    assert Shove(unit_id=U1, target_id=U2) in legal_actions(state)
    result = shove(state)
    assert result.state.units[U2].xy == PUSHED  # 不移動
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall, hit.unit_id, hit.source_id) == ("wall", 1, U2, U1)
    (damage,) = collisions(result.events)
    assert damage.target_id == U2 and damage.source_id == U1
    assert of(result.events, UnitMoved) == []


def test_shove_against_a_unit_hurts_both() -> None:
    result = shove(shove_scene(second=(3, 3)))
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall, hit.other_id) == ("unit", 1, U3)
    assert sorted(d.target_id for d in collisions(result.events)) == [U2, U3]
    assert result.state.units[U2].xy == PUSHED


def test_shove_against_an_object_and_a_breakable_object() -> None:
    wall = shove(shove_scene(objects=[(3, 3, "earth_wall")]))
    (hit,) = of(wall.events, Collided)
    assert (hit.obstacle, hit.shortfall) == ("object", 1)
    assert len(collisions(wall.events)) == 1
    pillar = shove(shove_scene(objects=[(3, 3, "stone_pillar")]))
    assert [d.target_id for d in collisions(pillar.events)] == [U2]
    assert [o.cause for o in of(pillar.events, ObjectDamaged)] == ["collision"]


def test_shove_at_the_map_edge() -> None:
    state = shove_scene(shover=(5, 3), foe=(6, 3))
    assert Shove(unit_id=U1, target_id=U2) in legal_actions(state)
    result = shove(state)
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall) == ("edge", 1)
    assert result.state.units[U2].xy == (6, 3)
    assert len(collisions(result.events)) == 1


def test_a_failed_contest_does_not_collide() -> None:
    result = shove(shove_scene(terrain=terrain_with("#", 3)), LOSE)
    assert of(result.events, Collided) == [] and collisions(result.events) == []
    assert result.state.units[U2].xy == PUSHED


def test_a_halved_distance_of_zero_is_still_illegal() -> None:
    """其他不合法原因不變：steadfast 把 1 格減半成 0 格仍然「推不動」。"""
    steady = no_reactions(max_hp=200, tags=["steadfast"])
    m = make_map(FLAT, terrain_with("#", 3), ally=[SHOVER], enemy=[PUSHED])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, SHOVER, "hero_fighter"), spawn(Team.ENEMY, PUSHED, steady)]
        ),
        U1,
    )
    assert Shove(unit_id=U1, target_id=U2) not in legal_actions(state)
    with pytest.raises(IllegalActionError, match="推不動"):
        resolve(state, Shove(unit_id=U1, target_id=U2))


def test_the_shove_preview_shows_the_collision_damage() -> None:
    p = preview(shove_scene(terrain=terrain_with("#", 3)), Shove(unit_id=U1, target_id=U2))
    ((unit, low, high),) = p.collisions
    assert unit == U2 and 1 <= low <= high <= 6


def test_the_shove_preview_against_a_unit_lists_both_victims() -> None:
    p = preview(shove_scene(second=(3, 3)), Shove(unit_id=U1, target_id=U2))
    assert sorted(unit for unit, _, _ in p.collisions) == [U2, U3]


def test_the_ai_scores_a_wall_shove_higher_than_a_shove_in_the_open() -> None:
    """貼牆推擊的預覽有撞擊傷害，AI 的評分比空地推擊高。"""
    from trpg.engine.ai.utility import UtilityAI, score_action  # noqa: PLC0415

    def shove_score(terrain: str | None) -> object:
        state = shove_scene(terrain=terrain)
        profile = UtilityAI(library().ai_profiles).profile_for(state.units[U1])
        return score_action(state, Shove(unit_id=U1, target_id=U2), profile).score

    assert shove_score(terrain_with("#", 3)) > shove_score(None)  # type: ignore[operator]


def test_gale_kick_into_a_wall_deals_collision_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    hero = template("hero_fighter", reactions=[], skills=["skill_gale_kick"])
    m = make_map(FLAT, terrain_with("#", 3), ally=[(1, 3)], enemy=[FOE])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))]
        ),
        U1,
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2))
    (hit,) = of(result.events, Collided)
    assert (hit.obstacle, hit.shortfall) == ("wall", 2)
    assert len(collisions(result.events)) == 2


def test_battering_ram_uses_its_own_collision_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    hero = template("hero_fighter", reactions=[], skills=["skill_battering_ram"], max_mana=99)
    m = make_map(FLAT, terrain_with("#", 3), ally=[(1, 3)], enemy=[FOE])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))]
        ),
        U1,
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_battering_ram", target_id=U2))
    hits = collisions(result.events)
    assert [d.rolls for d in hits] == [(4, 4), (4, 4)]  # 少走 2 格，每次 2d6


# ---------------------------------------------------------------------------
# 預覽與重播
# ---------------------------------------------------------------------------


def test_preview_shows_the_possible_collision_damage() -> None:
    hero = template("hero_fighter", reactions=[], skills=["skill_gale_kick"])
    m = make_map(FLAT, terrain_with("#", 3), ally=[(1, 3)], enemy=[FOE])
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))]
        ),
        U1,
    )
    p = preview(state, UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2))
    ((unit, low, high),) = p.collisions
    assert unit == U2 and 2 <= high <= 12 and low <= high  # 兩次 1d6（最多 12）


def test_preview_without_a_collision_is_empty() -> None:
    state = arena(foe=(0, 1))
    assert preview(state, Shove(unit_id=U1, target_id=U2)).collisions == ()


def test_ai_battles_with_collisions_are_deterministic_and_replay(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """build_push 在 oil_depot（種子 3）的戰鬥裡出現撞擊；同種子重跑結果相同、重播一致。"""
    log = tmp_path / "collision.json"
    argv = ["battle", "--map", "oil_depot", "--seed", "3", "--ally-build", "build_push"]
    assert main(argv) == 0
    first = capsys.readouterr().out
    assert "次撞擊" in first and "撞擊物理傷害" in first
    assert main(argv) == 0
    assert capsys.readouterr().out == first  # 同種子、同輸入，結果逐字相同
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    assert '"collided"' in log.read_text(encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(log, out) == 0
    assert "重播驗證通過" in out.getvalue()


def test_ai_scores_a_push_into_a_wall_higher_than_the_same_push_in_the_open() -> None:
    """AI 的位移評分把預期撞擊傷害算進去（預覽的事件含 ``DamageDealt.cause == "collision"``）。"""
    from trpg.engine.ai.utility import UtilityAI, score_action  # noqa: PLC0415

    def kick_score(terrain: str | None) -> object:
        hero = template("hero_fighter", reactions=[], skills=["skill_gale_kick"])
        m = make_map(FLAT, terrain, ally=[(1, 3)], enemy=[FOE])
        state = give_turn(
            make_state(
                m,
                [spawn(Team.ALLY, (1, 3), hero), spawn(Team.ENEMY, FOE, no_reactions(max_hp=200))],
            ),
            U1,
        )
        profile = UtilityAI(library().ai_profiles).profile_for(state.units[U1])
        action = UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2)
        return score_action(state, action, profile).score

    assert kick_score(terrain_with("#", 3)) > kick_score(None)  # type: ignore[operator]
