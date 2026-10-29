"""Phase 3W-9b：升階重配修正（06 6.34.9「升階時重算」，3W-9 定的三點）。

- 點數固定的狀態／表面白板升階時放大效果本身（狀態加持續回合、表面加格數），不補傷害，比例進窗；
- 升降地形先放大格數（照角色階級表：2 階 4～6 格、3 階 7 格以上），放大到上限仍不到 70% 才補落石；
- 重配維持升階前的預算比例（不再重新抽 75～95%）；預算分數不低於升階前。
"""

from __future__ import annotations

from fractions import Fraction
from itertools import pairwise

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.events import StatusApplied, SurfaceChanged, TerrainChanged
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.state import BattleState
from trpg.narrative.skills import skill_card
from trpg.shared.types import Pos, Team, UnitId
from trpg.skillgen.budget import skill_budget, zone_cell_count
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.skill_tier import retier, retier_report
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
CASTER = UnitId("unit_0001")

FIXED_STATUS = ("venom", "kindle", "mark_target")
FIXED_SURFACE = ("frost_patch", "toxic_pool")
FIXED_PASSIVE = ("venom_touch", "ember_touch")
FIXED_REACTION = ("venom_retort", "veil_retort")
"""06 6.34.9 列的點數固定白板：淬毒、點燃、烙印、凝冰、毒沼、毒觸、點燃觸、毒反擊、隱蔽反擊。"""

_KIND = {
    **dict.fromkeys(FIXED_STATUS + FIXED_SURFACE, "active"),
    **dict.fromkeys(FIXED_PASSIVE, "passive"),
    **dict.fromkeys(FIXED_REACTION, "reaction"),
}


def _ladder(first: SkillDef) -> list[SkillDef]:
    second = retier(LIB, first, 2)
    return [first, second, retier(LIB, second, 3)]


def _recipe_ladder(recipe: str, seed: int, weapon_class: str | None = None) -> list[SkillDef]:
    kind = _KIND[recipe]
    return _ladder(
        compose_whiteboard(
            seed, kind=kind, recipe_id=recipe, tier=1, library=LIB, weapon_class=weapon_class
        )
    )


def _window() -> tuple[Fraction, Fraction]:
    rules = LIB.budget
    return Fraction(rules.min_ratio_permille, 1000), Fraction(rules.max_ratio_permille, 1000)


def _durations(skill: SkillDef) -> list[int | None]:
    return [e.duration for e in skill.effects if e.type in ("apply_status", "create_surface")]


# ---------------------------------------------------------------------------
# 1. 點數固定的狀態／表面白板：放大效果本身
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("recipe", sorted(_KIND))
@pytest.mark.parametrize("seed", [0, 1])
def test_fixed_blanks_scale_the_effect_itself(recipe: str, seed: int) -> None:
    ladder = _recipe_ladder(recipe, seed)
    first = ladder[0]
    low, high = _window()
    for tier, skill in enumerate(ladder, start=1):
        assert skill.tier == tier
        assert [e.type for e in skill.effects] == [e.type for e in first.effects]  # 不補傷害
        assert validate_skill(skill, LIB) == [], (recipe, tier)
        assert low <= skill_budget(skill, LIB).ratio <= high, (recipe, tier)
    for before, after in pairwise(ladder):
        assert budget_power(after, LIB) >= budget_power(before, LIB)
        # 持續回合只增不減
        for old, new in zip(_durations(before), _durations(after), strict=True):
            assert old is None or (new is not None and new >= old), (recipe, old, new)


@pytest.mark.parametrize("recipe", FIXED_SURFACE)
def test_surfaces_grow_their_cells(recipe: str) -> None:
    """表面加格數（十字 5 格 → 方陣 9 格；3×3 要 2 階），格數只增不減。"""
    ladder = _recipe_ladder(recipe, 0)
    cells = [zone_cell_count(s, LIB) for s in ladder]
    assert cells == sorted(cells) and cells[-1] > cells[0], cells
    for skill in ladder[1:]:
        assert skill.shape.type in LIB.budget.retier_growth.area_shapes


def test_control_statuses_keep_the_composer_cap() -> None:
    """控制類狀態（移動、心智、硬控）的持續不放大，照組合器的上限。"""
    statuses = LIB.ruleset.statuses.by_id()
    for recipe in sorted(_KIND):
        for skill in _recipe_ladder(recipe, 0):
            for effect in skill.effects:
                status = statuses.get(effect.status or "")
                if status is not None and status.control_group is not None:
                    assert effect.duration is None or effect.duration <= LIB.composer.duration.cap


def _battle(skill: SkillDef, seed: int = 0) -> BattleState:
    """7×7 空地圖：敵人站在中心（射程 0 的技能由施放者站在中心、敵人在旁邊），輪到施放者。"""
    reach = skill.shape.range if isinstance(skill.shape.range, int) else 3
    caster = (3 - min(reach, 3), 3)
    enemy = (3, 3) if reach else (4, 3)
    m = make_map("\n".join(["0000000"] * 7), ally=[caster], enemy=[enemy])
    spawns = [
        spawn(Team.ALLY, caster, caster_template([skill])),
        spawn(Team.ENEMY, enemy, no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[skill], seed=seed), "unit_0001")


def _cast(skill: SkillDef, seed: int = 0) -> list[object]:
    """對中心格施放，回傳事件。"""
    battle = _battle(skill, seed)
    action = UseSkill(unit_id=CASTER, skill_id=skill.id, target_pos=Pos(x=3, y=3))
    return list(resolve(battle, action).events)


@pytest.mark.parametrize("recipe", FIXED_SURFACE)
def test_surface_card_numbers_equal_the_engine(recipe: str) -> None:
    """卡片上的回合數與形狀就是實戰：表面蓋滿形狀的每一格、剩餘回合等於卡片數字。"""
    for skill in _recipe_ladder(recipe, 0, "focus"):
        effect = skill.effects[0]
        assert effect.duration is not None
        card = skill_card(LIB, skill)
        assert any(f"{effect.duration} 回合" in line for line in card.effects), card.effects
        changed = [e for e in _cast(skill) if isinstance(e, SurfaceChanged) and e.cause == "effect"]
        assert len(changed) == zone_cell_count(skill, LIB)
        battle = _battle(skill)
        bonus = attribute_perk(battle.ruleset, battle.units[CASTER], "surface_duration")  # 智力
        assert {e.remaining for e in changed} == {effect.duration + bonus}


@pytest.mark.parametrize("recipe", ["venom", "kindle"])
def test_status_card_numbers_equal_the_engine(recipe: str) -> None:
    for skill in _recipe_ladder(recipe, 0, "focus"):
        effect = skill.effects[0]
        card = skill_card(LIB, skill)
        assert any(f"{effect.duration} 回合" in line for line in card.effects), card.effects
        applied = []
        for seed in range(12):  # 目標可能抵抗：換種子直到施加成功
            applied = [e for e in _cast(skill, seed) if isinstance(e, StatusApplied)]
            if applied:
                break
        assert applied and {e.duration for e in applied} == {effect.duration}


# ---------------------------------------------------------------------------
# 2. 升降地形：格數照角色階級表，放大到上限仍不到 70% 才補落石
# ---------------------------------------------------------------------------

TERRAIN_SOURCES = ("skill_sinkhole", "skill_raise_perch", "skill_earth_collapse")


def _terrain_sources() -> list[SkillDef]:
    sources = [LIB.skills[s] for s in TERRAIN_SOURCES]
    sources += [compose_whiteboard(s, keyword="high_ground", tier=1, library=LIB) for s in range(3)]
    return sources


def _band(tier: int) -> int:
    """角色階級 ``tier`` 的升降地形格數下限（``terrain_area`` 表；1 階沒有下限）。"""
    table = LIB.budget.min_character_tier.terrain_area
    return max((t.min_cells for t in table if t.tier <= tier), default=1)


def _tier_of_cells(cells: int) -> int:
    table = LIB.budget.min_character_tier.terrain_area
    return max((t.tier for t in table if cells >= t.min_cells), default=1)


@pytest.mark.parametrize("chain", [False, True])
def test_terrain_cells_follow_the_tier_table(chain: bool) -> None:
    for source in _terrain_sources():
        prev = source
        for tier in (2, 3):
            done = retier(LIB, prev if chain else source, tier)
            cells = zone_cell_count(done, LIB)
            # 照表：升階後的格數至少到這一階的下限，而且不縮小
            assert cells >= _band(tier), (source.id, tier, cells)
            assert cells >= zone_cell_count(prev, LIB)
            # 白板（從零產生）不超過角色階級
            if source.provenance.origin != "builtin":
                assert _tier_of_cells(cells) <= tier
            report = retier_report(LIB, prev, done)
            assert report.in_window and not report.problems, (source.id, tier)
            assert report.after >= report.before
            prev = done


def test_rocks_only_when_the_biggest_area_is_still_weak() -> None:
    """1 AP 的隆地：3 階的方陣靠冷卻就進窗，不補落石；2 階的十字加冷卻仍超過上限，加 1 AP 後不到
    70%，才補落石。"""
    board = compose_whiteboard(0, keyword="high_ground", tier=1, library=LIB)
    third = retier(LIB, board, 3)
    assert third.shape.type == "square3" and [e.type for e in third.effects] == ["raise_terrain"]
    second = retier(LIB, board, 2)
    assert second.shape.type == "cross"
    assert [e.type for e in second.effects] == ["raise_terrain", "damage"]


def test_terrain_card_and_engine_cover_the_grown_area() -> None:
    board = compose_whiteboard(0, keyword="high_ground", tier=1, library=LIB)
    for skill in _ladder(board):
        changed = [e for e in _cast(skill) if isinstance(e, TerrainChanged)]
        assert len(changed) == zone_cell_count(skill, LIB)
        assert skill_card(LIB, skill).shape.startswith(
            LIB.ruleset.shapes.by_id()[skill.shape.type].name_zh
        )


# ---------------------------------------------------------------------------
# 3. 重配維持升階前的比例
# ---------------------------------------------------------------------------

RATIO_SLACK = Fraction(10, 100)
"""比例差的容許範圍：骰子與持續回合是一格一格的（低階被動一格約 7%），所以比 ``target_tolerance``
（5%）寬。"""


def _all_recipes() -> list[tuple[str, str, int, bool]]:
    rules = LIB.composer.whiteboard
    out = []
    for kind in ("active", "passive", "reaction"):
        for recipe in getattr(rules, kind):
            start = recipe.creation_tier or recipe.min_tier
            if start < 3:
                out.append((kind, recipe.id, start, recipe.creation_tier is not None))
    return out


@pytest.mark.parametrize(("kind", "recipe", "start", "starter"), _all_recipes())
def test_retier_keeps_the_ratio(kind: str, recipe: str, start: int, starter: bool) -> None:
    low, high = _window()
    first = compose_whiteboard(
        0, kind=kind, recipe_id=recipe, tier=start, library=LIB, starter=starter
    )
    prev = first
    for tier in range(start + 1, 4):
        done = retier(LIB, prev, tier)
        before = min(max(skill_budget(prev, LIB).ratio, low), high)
        after = skill_budget(done, LIB).ratio
        assert low <= after <= high, (recipe, tier, float(after))
        assert abs(after - before) <= RATIO_SLACK, (recipe, tier, float(before), float(after))
        assert budget_power(done, LIB) >= budget_power(prev, LIB)
        prev = done
