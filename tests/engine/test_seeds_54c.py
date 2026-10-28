"""風、毒、神聖種子技能與「清除表面」（Phase 3-54c，06 6.33，#56／#59／#63／#64）。

行為一致測試：清除表面 × 表面種類 × 對象（友方腳下／全部）；清風不觸發擴散、不觸發互動表；
破邪聖光實際清掉毒與黑暗表面；每招內建種子技能的卡片數字＝實戰；含清風與吹送的整場重播。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

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
from tests.engine.skill_helpers import FLAT7, SID, U1, battle, hit_with, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, resolve
from trpg.engine.battle import begin_battle
from trpg.engine.events import (
    DamageDealt,
    SkillUsed,
    SurfaceBlown,
    SurfaceChanged,
    ZoneExpanded,
)
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.runner import apply_step, replay
from trpg.engine.state import state_to_json
from trpg.narrative.skills import skill_card
from trpg.shared.types import Pos, Surface, Team

ALL_SURFACES = [s.value for s in Surface if s is not Surface.NONE]
DEFAULT_CLEARED = {"smoke", "poison"}
SQUARE = {"type": "square3", "range": 4}


def real_battle(
    skill_id: str,
    foes: Sequence[tuple[int, int]] = (),
    *,
    allies: Sequence[tuple[int, int]] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
    objects: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """施放者 U1 在 (3,3)，裝備內容庫裡的真實種子技能（不另外加進規則集）。"""
    foe_xy = list(foes) or [(6, 6)]
    m = make_map(FLAT7, ally=[(3, 3), *allies], enemy=foe_xy, objects=objects, surfaces=surfaces)
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill_id]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foe_xy]
    return give_turn(make_state(m, spawns), U1)


def surfaces(state: BattleState) -> dict[tuple[int, int], Surface]:
    return {
        (x, y): state.tile(x, y).surface
        for y in range(state.height)
        for x in range(state.width)
        if state.tile(x, y).surface is not Surface.NONE
    }


def clear_skill(affects: str, surface: str | None = None) -> SkillDef:
    spec: dict[str, Any] = {"type": "clear_surface", "affects": affects}
    if surface is not None:
        spec["surface"] = surface
    return make_skill(SID, SQUARE, [spec])


def _cast_center(state: BattleState, skill_id: str = SID) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, target_pos=Pos(x=3, y=3)))


# 施放者 (3,3)，友方 (4,3)（站著的格子），敵人 (2,3)；範圍是以 (3,3) 為中心的 3x3。
ALLY_TILE, FOE_TILE, EMPTY_TILE = (4, 3), (2, 3), (3, 2)


@pytest.mark.parametrize("surface", ALL_SURFACES)
@pytest.mark.parametrize("affects", ["allies", "tiles"])
@pytest.mark.parametrize("named", [False, True])
def test_clear_surface_by_kind_and_target(surface: str, affects: str, named: bool) -> None:
    skill = clear_skill(affects, surface if named else None)
    cells = (ALLY_TILE, FOE_TILE, EMPTY_TILE)
    state = battle(
        skill,
        foes=[FOE_TILE],
        allies=[ALLY_TILE],
        surfaces=tuple((x, y, surface) for x, y in cells),
    )
    result = _cast_center(state)
    cleared_kind = (surface in DEFAULT_CLEARED) if not named else True
    reach = {ALLY_TILE} if affects == "allies" else set(cells)
    expected = {xy for xy in cells if not (cleared_kind and xy in reach)}
    assert set(surfaces(result.state)) == expected
    assert all(s is Surface(surface) for s in surfaces(result.state).values())
    changed = [e for e in of(result, SurfaceChanged) if e.cause == "clear"]
    assert len(changed) == len(cells) - len(expected)


def test_clear_surface_only_clears_the_named_kind() -> None:
    state = battle(
        clear_skill("tiles", "fire"),
        foes=[(6, 6)],
        surfaces=((2, 2, "fire"), (3, 2, "poison"), (4, 2, "smoke")),
    )
    assert surfaces(_cast_center(state).state) == {(3, 2): Surface.POISON, (4, 2): Surface.SMOKE}


def test_clear_surface_does_nothing_outside_the_area() -> None:
    state = battle(clear_skill("tiles"), foes=[(6, 6)], surfaces=((0, 0, "poison"),))
    assert surfaces(_cast_center(state).state) == {(0, 0): Surface.POISON}


# ---------------------------------------------------------------------------
# 不帶元素、不觸發互動表、不觸發風的擴散
# ---------------------------------------------------------------------------


def test_clear_surface_touches_nothing_else() -> None:
    """清除火焰表面：不查互動表、不帶元素，所以不會引爆格上的易爆物，也不傷害站著的單位。"""
    state = battle(
        clear_skill("tiles", "fire"),
        foes=[FOE_TILE],
        allies=[ALLY_TILE],
        objects=((EMPTY_TILE[0], EMPTY_TILE[1], "oil_barrel"),),
        surfaces=((EMPTY_TILE[0], EMPTY_TILE[1], "fire"), (ALLY_TILE[0], ALLY_TILE[1], "fire")),
    )
    result = _cast_center(state)
    assert surfaces(result.state) == {}
    assert not of(result, DamageDealt)
    kinds = {type(e).__name__ for e in result.events}
    assert not kinds & {"ObjectDestroyed", "ZoneExpanded", "SurfaceBlown", "DamageDealt"}


def test_clearing_breeze_is_not_a_wind_skill_and_never_spreads() -> None:
    """清風：技能沒有風元素的傷害效果，不觸發擴散、吹送或風壓；表面是被直接移除的。"""
    skill = library().skills["skill_clearing_breeze"]
    assert not any(e.type in ("damage", "blow_surface", "push") for e in skill.effects)
    state = real_battle(
        skill.id,
        foes=[(0, 0)],
        allies=[ALLY_TILE],
        surfaces=((4, 3, "poison"), (3, 2, "poison"), (3, 4, "fire"), (5, 3, "smoke")),
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=3, y=3)))
    assert surfaces(result.state) == {
        (3, 2): Surface.POISON,
        (3, 4): Surface.FIRE,
        (5, 3): Surface.SMOKE,
    }
    assert not of(result, ZoneExpanded) and not of(result, SurfaceBlown)
    assert {e.cause for e in of(result, SurfaceChanged)} == {"clear"}


def test_clearing_breeze_clears_smoke_and_poison_under_allies_only() -> None:
    """清風（友方腳下）：施放者與友方腳下的煙霧和毒被清掉，敵人腳下與空地的不動，其他表面不動。"""
    skill = library().skills["skill_clearing_breeze"]
    state = real_battle(
        skill.id,
        foes=[(2, 4)],
        allies=[(4, 4)],
        surfaces=(
            (3, 3, "poison"),  # 施放者腳下
            (4, 4, "smoke"),  # 友方腳下
            (2, 4, "poison"),  # 敵人腳下
            (3, 2, "smoke"),  # 空地
            (4, 3, "oil"),  # 空地、不在清單
        ),
    )
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=3, y=3)))
    left = surfaces(result.state)
    assert left == {(2, 4): Surface.POISON, (3, 2): Surface.SMOKE, (4, 3): Surface.OIL}


# ---------------------------------------------------------------------------
# 破邪聖光、聖光印地
# ---------------------------------------------------------------------------


def test_purging_light_purifies_poison_and_darkness_on_the_cross() -> None:
    skill = library().skills["skill_purging_light"]
    state = real_battle(
        skill.id,
        foes=[(5, 3)],
        surfaces=(
            (4, 3, "poison"),  # 十字內（沒有單位）
            (5, 2, "darkness"),  # 十字內
            (5, 3, "poison"),  # 十字中心，敵人腳下
            (5, 4, "fire"),  # 十字內、不會被神聖清除
            (6, 6, "poison"),  # 十字外
        ),
    )
    result = resolve(
        hit_with(state), UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=5, y=3))
    )
    assert surfaces(result.state) == {(5, 4): Surface.FIRE, (6, 6): Surface.POISON}
    assert of(result, DamageDealt)  # 敵人受到神聖傷害


def test_holy_ground_leaves_a_holy_surface() -> None:
    skill = library().skills["skill_holy_ground"]
    state = real_battle(skill.id, foes=[(6, 6)])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=5, y=3)))
    tile = result.state.tile(5, 3)
    caster = result.state.unit(U1)
    bonus = attribute_perk(result.state.ruleset, caster, "surface_duration")  # 智力加成（3H-1）
    assert (tile.surface, tile.surface_remaining) == (Surface.HOLY, 5 + bonus)


# ---------------------------------------------------------------------------
# 種子技能的數字：卡片寫的＝實戰
# ---------------------------------------------------------------------------

SEEDS = [
    *("wind_blade", "air_burst", "gust_blow", "tempest", "hurricane_push", "clearing_breeze"),
    *("venom_blade", "poison_mist", "marrow_thorn", "venom_detonation", "corrosion", "venom_pit"),
    *("purging_light", "holy_ground"),
]


def test_there_are_fourteen_seed_skills_with_the_listed_elements() -> None:
    lib = library()
    skills = [lib.skills[f"skill_{s}"] for s in SEEDS]
    assert len(skills) == 14
    wind = [s for s in skills if "wind" in s.tags]
    poison = [s for s in skills if "poison" in s.tags or s.id == "skill_marrow_thorn"]
    holy = [s for s in skills if "holy" in s.tags]
    assert (len(wind), len(poison), len(holy)) == (6, 6, 2)


@pytest.mark.parametrize("name", SEEDS)
def test_card_numbers_match_the_skill_data(name: str) -> None:
    """卡片文字（敘事層）寫出每個效果的骰子、持續回合與距離，與技能資料同一個數字。"""
    lib = library()
    skill = lib.skills[f"skill_{name}"]
    text = "\n".join(skill_card(lib, skill).effects)
    for spec in skill.effects:
        if spec.dice is not None:
            assert str(spec.dice) in text, (name, spec.dice)
        if spec.distance is not None:
            assert f"{spec.distance} 格" in text, (name, spec.distance)
        if spec.duration is not None and spec.type == "create_surface":
            assert f"{spec.duration} 回合" in text, (name, spec.duration)
        if spec.type == "damage" and spec.multiplier_permille is not None:
            assert f"×{spec.multiplier_permille / 1000:g}" in text, (name, text)


def test_wind_seeds_use_the_3_54ab_mechanics_on_the_card() -> None:
    lib = library()

    def card(name: str) -> str:
        return "\n".join(skill_card(lib, lib.skills[f"skill_{name}"]).effects)

    assert "往風向擴大 2 格" in card("tempest")
    assert "風壓：撞擊傷害 +50%" in card("hurricane_push")
    assert "風壓：撞擊傷害 +50%" in card("air_burst")
    assert "吹走 3 格" in card("gust_blow")
    assert "煙霧、毒" in card("clearing_breeze")


def test_tempest_spreads_poison_by_two_tiles_like_the_card_says() -> None:
    skill = library().skills["skill_tempest"]
    state = real_battle(skill.id, foes=[(5, 3)], surfaces=((5, 3, "poison"),))
    result = resolve(
        hit_with(state), UseSkill(unit_id=U1, skill_id=skill.id, target_pos=Pos(x=5, y=3))
    )
    # 範圍 4..6：風向由施放者往東；毒表面往東擴大 2 格（受地圖邊界限制）
    assert Surface.POISON in {s for s in surfaces(result.state).values()}
    assert len(surfaces(result.state)) >= 2


def test_gust_blow_moves_the_poison_three_tiles_downwind() -> None:
    skill = library().skills["skill_gust_blow"]
    state = real_battle(skill.id, foes=[(0, 0)], surfaces=((4, 3, "poison"),))
    result = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, direction="east"))
    assert surfaces(result.state) == {(6, 3): Surface.POISON}  # 4 + 3 超過地圖邊，停在 (6, 3)
    assert len(of(result, SurfaceBlown)) == 1


# ---------------------------------------------------------------------------
# 整場重播（用到清風與吹送）
# ---------------------------------------------------------------------------


def test_a_battle_with_clearing_breeze_and_gust_blow_replays_identically() -> None:
    """四個單位都帶清風與吹送；每個單位在自己的回合先清風、再吹送（腳本化的步驟，不靠 AI 挑選）。
    「初始狀態＋步驟列表」重播得到同一個最終狀態。"""
    lib = library()
    kit = [lib.skills["skill_clearing_breeze"], lib.skills["skill_gust_blow"]]
    flat = "\n".join(["000000000"] * 9)
    poison = [(x, y, "poison") for x in (1, 2, 3) for y in (2, 3, 4)]
    m = make_map(
        flat,
        ally=[(1, 3), (2, 5)],
        enemy=[(7, 3), (7, 5)],
        surfaces=[*poison, (4, 4, "smoke"), (5, 3, "oil")],
    )
    spawns = [
        spawn(Team.ALLY, (1, 3), caster_template(kit, max_hp=60)),
        spawn(Team.ALLY, (2, 5), caster_template(kit, max_hp=60)),
        spawn(Team.ENEMY, (7, 3), caster_template(kit, max_hp=80)),
        spawn(Team.ENEMY, (7, 5), caster_template(kit, max_hp=80)),
    ]
    setup = make_setup(m, spawns, max_rounds=12)
    result = begin_battle(setup, 11)
    state, steps = result.state, []
    for _ in range(4):
        unit = state.active
        assert unit is not None
        for action in (
            UseSkill(
                unit_id=unit.id,
                skill_id="skill_clearing_breeze",
                target_pos=Pos(x=unit.xy[0], y=unit.xy[1]),
            ),
            UseSkill(unit_id=unit.id, skill_id="skill_gust_blow", direction="east"),
            EndTurn(unit_id=unit.id),
        ):
            steps.append(action)
            state = apply_step(state, action).state
    again = replay(setup, 11, steps)
    assert state_to_json(again.state) == state_to_json(state)
    used = {e.skill_id for e in again.events if isinstance(e, SkillUsed)}
    assert used == {"skill_clearing_breeze", "skill_gust_blow"}
    assert any(isinstance(e, SurfaceChanged) and e.cause == "clear" for e in again.events)
    assert any(isinstance(e, SurfaceBlown) for e in again.events)
