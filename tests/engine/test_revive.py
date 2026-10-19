"""復活（Phase 3D-8b，``docs/phases/Phase3D計畫.md`` 8.2、8.4）：射程、原格被占、沒有空格、每場
一次、召喚物不能被復活、事件、倒下時移除的狀態不恢復、驗證（每場一次或冷卻 ≥ 4）、預覽、視圖、AI
與重播。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import give_turn, library, make_skill
from tests.engine.skill_helpers import SID, U1, U2, U3, battle, cast, of
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, UseSkill, preview, state_from_json, state_to_json
from trpg.engine.battle import legal_actions
from trpg.engine.effects import run_effects
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import UnitRevived
from trpg.engine.skills.revive import revive_landing, revive_target_problem
from trpg.engine.state import StatusInstance
from trpg.engine.view import project_for
from trpg.narrative.events import describe_event
from trpg.narrative.skills import skill_card
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

SINGLE4: dict[str, Any] = {"type": "single", "range": 4}


def revive_skill(permille: int = 300, **fields: Any) -> SkillDef:
    data = make_skill(SID, SINGLE4, [{"type": "revive", "hp_permille": permille}]).model_dump(
        mode="json"
    )
    data.update(skeleton="aura", cost={"mana": 0, "uses_per_battle": 1}, **fields)
    return SkillDef.model_validate(data)


def downed_state(skill: SkillDef | None = None, ally: tuple[int, int] = (4, 3)) -> BattleState:
    """U1 施放者（拿到回合）、U2 倒下的友方、U3 敵人。"""
    state = battle(skill or revive_skill(), [(6, 6)], allies=[ally])
    return run_effects(
        state, [DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False)]
    ).state


def reopen(state: BattleState) -> BattleState:
    """回到施放者的回合（結算後輪到別人時用）。"""
    return give_turn(state, U1)


# ---------------------------------------------------------------------------
# 基本結算
# ---------------------------------------------------------------------------


def test_revive_brings_a_downed_ally_back_on_the_same_tile_with_a_share_of_the_hp() -> None:
    state = downed_state()
    assert state.units[U2].downed and state.unit_at(4, 3) is None  # 倒下的單位不占格子
    result = cast(state, target_id=U2)
    (event,) = of(result, UnitRevived)
    unit = result.state.units[U2]
    assert not unit.downed and unit.alive and unit.revived
    assert unit.hp == max(1, unit.max_hp * 300 // 1000) == event.hp
    assert unit.xy == (4, 3) and event.pos == event.from_pos == Pos(x=4, y=3)
    assert event.unit_id == U2 and event.source_id == U1 and event.skill_id == SID
    assert result.state.unit_at(4, 3) is unit


def test_the_revived_unit_returns_to_its_place_in_the_initiative_order() -> None:
    state = downed_state()
    assert U2 not in state.turn_order
    for initiative, expected_before in ((99, U1), (-99, None)):
        s = state.clone()
        s.units[U2].initiative = initiative
        order = cast(s, target_id=U2).state.turn_order
        assert U2 in order and len(order) == len(set(order)) == 3
        if expected_before is not None:
            assert order.index(U2) < order.index(expected_before)  # 先攻最高：排在最前面
        else:
            assert order[-1] == U2  # 先攻最低：排在最後
    # 輪到的仍然是施放者（插在他前面時目前位置跟著往後移）
    s = state.clone()
    s.units[U2].initiative = 99
    after = cast(s, target_id=U2).state
    assert after.active_unit == U1 and after.turn_order[after.turn_pos] == U1


def test_the_hp_is_at_least_one() -> None:
    state = downed_state(revive_skill(100))
    state.units[U2].max_hp = 3
    assert cast(state, target_id=U2).state.units[U2].hp == 1


def test_revive_does_not_restore_what_was_removed_when_the_unit_went_down() -> None:
    state = battle(revive_skill(), [(6, 6)], allies=[(4, 3)])
    stance = next(s.id for s in library().ruleset.statuses.statuses if s.stance)
    state.units[U2].statuses = [StatusInstance(stance, None, U2), StatusInstance("poison", 3, U3)]
    downed = run_effects(
        state, [DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False)]
    ).state
    assert not downed.units[U2].has_status(stance)  # 倒下時姿態被移除
    revived = cast(downed, target_id=U2).state.units[U2]
    assert not revived.has_status(stance)  # 復活後不會恢復


def test_the_revived_unit_can_act_in_a_later_turn() -> None:
    state = downed_state()
    revived = cast(state, target_id=U2).state
    assert revived.units[U2].alive and U2 in revived.turn_order
    assert revived.units[U2].hp > 0


# ---------------------------------------------------------------------------
# 選取：射程、對象
# ---------------------------------------------------------------------------


def test_the_target_must_be_in_range() -> None:
    state = downed_state(ally=(0, 3))  # 距離 3，射程 4：可以
    assert cast(state, target_id=U2).state.units[U2].alive
    far = downed_state(revive_skill(), ally=(0, 0))  # 距離 6
    with pytest.raises(IllegalActionError, match="射程"):
        cast(far, target_id=U2)


def test_a_standing_ally_or_a_downed_enemy_is_not_a_target() -> None:
    state = battle(revive_skill(), [(6, 6), (6, 5)], allies=[(4, 3)])
    with pytest.raises(IllegalActionError, match="沒有倒下"):
        cast(state, target_id=U2)
    downed_foe = run_effects(
        state, [DamageEffect(target_id=U3, mode="lethal", apply_element_mod=False)]
    ).state
    with pytest.raises(IllegalActionError, match="只能復活友方"):
        cast(downed_foe, target_id=U3)


def test_the_selections_list_only_the_downed_allies() -> None:
    alive = battle(revive_skill(), [(6, 6)], allies=[(4, 3)])
    assert [a for a in legal_actions(alive) if isinstance(a, UseSkill) and a.skill_id == SID] == []
    downed = downed_state()
    found = [a for a in legal_actions(downed) if isinstance(a, UseSkill) and a.skill_id == SID]
    assert [a.target_id for a in found] == [U2]


def test_a_summon_cannot_be_revived() -> None:
    state = downed_state()
    state.units[U2].owner_id = U1  # 召喚物（有召喚者）
    assert "召喚物" in (revive_target_problem(state, state.units[U1], state.units[U2]) or "")
    with pytest.raises(IllegalActionError, match="召喚物不能被復活"):
        cast(state, target_id=U2)


def test_each_unit_can_be_revived_only_once_per_battle() -> None:
    skill = revive_skill()
    data = skill.model_dump(mode="json")
    data["cost"] = {"mana": 0}  # 不限次數，才能測「同一個單位」的限制
    skill = SkillDef.model_validate(data)
    state = downed_state(skill)
    once = reopen(cast(state, target_id=U2).state)
    again = run_effects(
        once, [DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False)]
    ).state
    assert again.units[U2].downed and again.units[U2].revived
    with pytest.raises(IllegalActionError, match="已經被復活過"):
        cast(reopen(again), target_id=U2)


def test_the_skill_itself_is_limited_to_one_use_per_battle() -> None:
    state = battle(revive_skill(), [(6, 6)], allies=[(4, 3), (2, 3)])
    both = run_effects(
        state,
        [
            DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False),
            DamageEffect(target_id=U3, mode="lethal", apply_element_mod=False),
        ],
    ).state
    after = reopen(cast(both, target_id=U2).state)
    assert after.units[U1].skill_uses[SID] == 1 and after.units[U3].downed
    with pytest.raises(IllegalActionError):
        cast(after, target_id=U3)


# ---------------------------------------------------------------------------
# 原格被占、沒有空格
# ---------------------------------------------------------------------------


def _occupy(state: BattleState, unit_id: str, xy: tuple[int, int]) -> None:
    state.units[unit_id].pos = Pos(x=xy[0], y=xy[1])  # type: ignore[index]


def test_when_the_original_tile_is_taken_the_unit_stands_on_the_nearest_free_tile() -> None:
    state = downed_state()
    _occupy(state, U3, (4, 3))  # 敵人站到倒下友方的格子上
    assert revive_landing(state, state.units[U2]) == (4, 2)  # 距離 1：依 (y, x) 先 y 較小者
    result = cast(state, target_id=U2)
    (event,) = of(result, UnitRevived)
    assert (event.from_pos, event.pos) == (Pos(x=4, y=3), Pos(x=4, y=2))
    assert result.state.units[U2].xy == (4, 2)
    assert "原位置被占用" in (describe_event(event, result.state) or "")


def test_ties_between_free_tiles_follow_the_fixed_order() -> None:
    state = downed_state()
    _occupy(state, U3, (4, 3))
    state.units[U1].pos = Pos(x=4, y=2)  # 施放者占住 (4, 2)
    assert revive_landing(state, state.units[U2]) == (
        3,
        3,
    )  # (3,3)、(5,3)、(4,4) 同距：y 小者先、再 x 小者


def test_without_a_free_tile_in_the_landing_radius_the_skill_cannot_be_cast() -> None:
    state = downed_state()
    _occupy(state, U3, (4, 3))
    core = state.ruleset.core.model_copy(update={"revive_landing_radius": 0})
    state.ruleset = state.ruleset.model_copy(update={"core": core})
    assert revive_landing(state, state.units[U2]) is None
    with pytest.raises(IllegalActionError, match="沒有可以站起來的空格"):
        cast(state, target_id=U2)
    assert [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID] == []


def test_a_deadly_or_blocked_original_tile_also_moves_the_unit() -> None:
    skill = revive_skill()
    state = battle(skill, [(6, 6)], allies=[(4, 3)])
    state = run_effects(
        state, [DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False)]
    ).state
    tile = state.tile(4, 3)
    from dataclasses import replace  # noqa: PLC0415

    state.set_tile(4, 3, replace(tile, terrain="lava"))
    landing = revive_landing(state, state.units[U2])
    assert landing is not None and landing != (4, 3)


# ---------------------------------------------------------------------------
# 驗證、預覽、視圖、文字
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


def test_schema_rejects_the_wrong_shape_and_other_targets() -> None:
    base = revive_skill().model_dump(mode="json")
    with pytest.raises(ValueError, match="single"):
        SkillDef.model_validate({**base, "shape": {"type": "square3", "range": 4}})
    with pytest.raises(ValueError, match="hp_permille"):
        SkillDef.model_validate({**base, "effects": [{"type": "revive"}]})
    with pytest.raises(ValueError, match="affects: self"):
        SkillDef.model_validate(
            {
                **base,
                "effects": [
                    {"type": "revive", "hp_permille": 300},
                    {"type": "heal", "dice": "1d6", "affects": "allies"},
                ],
            }
        )
    with pytest.raises(ValueError, match="revive"):
        SkillDef.model_validate({**base, "effects": [{"type": "revive", "hp_permille": 300}] * 2})
    enemies = SkillDef.model_validate(
        {**base, "effects": [{"type": "revive", "hp_permille": 300, "affects": "enemies"}]}
    )
    assert any("不能搭配 affects" in p for p in _problems(enemies))
    too_high = SkillDef.model_validate({**base, "effects": [{"type": "revive", "hp_permille": 50}]})
    assert any("100–1000" in p for p in _problems(too_high))


def test_revive_needs_once_per_battle_or_a_long_cooldown() -> None:
    lib = library()
    base = lib.skills["skill_resurrection"].model_dump(mode="json")

    def violations(cost: dict[str, Any]) -> list[str]:
        skill = SkillDef.model_validate({**base, "cost": cost})
        return [v.rule for v in validate_skill(skill, lib)]

    assert "cap.revive_cost" not in violations({"mana": 8, "uses_per_battle": 1})
    assert "cap.revive_cost" not in violations({"mana": 8, "cooldown": 4})
    assert "cap.revive_cost" in violations({"mana": 8, "cooldown": 3})
    assert "cap.revive_cost" in violations({"mana": 8})


def test_the_preview_shows_the_revive() -> None:
    state = downed_state()
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert [e.unit_id for e in p.min_events if isinstance(e, UnitRevived)] == [U2]


def test_the_view_marks_the_downed_unit_that_can_be_revived() -> None:
    state = downed_state()
    view = project_for(state, Team.ALLY)
    by_id = {u.id: u for u in view.units}
    assert by_id[U2].downed and by_id[U2].revivable and not by_id[U1].revivable
    revived = cast(state, target_id=U2).state
    again = run_effects(
        revived, [DamageEffect(target_id=U2, mode="lethal", apply_element_mod=False)]
    ).state
    assert not {u.id: u for u in project_for(again, Team.ALLY).units}[U2].revivable


def test_the_log_and_the_skill_card_describe_the_revive() -> None:
    state = downed_state()
    result = cast(state, target_id=U2)
    (event,) = of(result, UnitRevived)
    text = describe_event(event, result.state) or ""
    assert "重新站了起來" in text and "HP" in text
    card = skill_card(library(), library().skills["skill_resurrection"])
    assert "站起來" in str(card)


def test_the_state_round_trips_with_a_revived_unit() -> None:
    result = cast(downed_state(), target_id=U2)
    again = state_from_json(state_to_json(result.state))
    assert again.units[U2].revived and state_to_json(again) == state_to_json(result.state)


def test_the_demo_skill_is_valid_in_budget_and_equipped() -> None:
    lib = library()
    skill = lib.skills["skill_resurrection"]
    assert validate_skill(skill, lib) == [] and skill_budget(skill, lib).ok
    assert "skill_resurrection" in lib.builds.by_id()["build_healer"].hero.skills


# ---------------------------------------------------------------------------
# AI 與整場重播
# ---------------------------------------------------------------------------


def test_the_ai_revives_a_downed_ally_when_it_can() -> None:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415

    state = downed_state()
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == SID and action.target_id == U2
    # 沒有倒下的友方時不會施放
    alive = battle(revive_skill(), [(6, 6)], allies=[(4, 3)])
    other = UtilityAI(library().ai_profiles)(alive)
    assert not (isinstance(other, UseSkill) and other.skill_id == SID)


def test_a_battle_with_a_reviver_replays_exactly() -> None:
    from tests.engine.test_zone_ai import _run  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run("build_healer", "open_plain", 4)
    again = replay(setup, 4, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
