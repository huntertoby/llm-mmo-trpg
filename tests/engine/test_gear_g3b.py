"""裝備詞條的授予動作（第 9 類）、授予反應（第 10 類）與改變規則（第 11 類）（Phase 3G-G3b）。

涵蓋：每條詞條一組測試（`affix_act_grapple`、`affix_act_smoke`、`affix_act_shield_wall`、
`affix_react_ranged_block`、`affix_react_guard_ally`、`affix_react_double_overwatch`、
`affix_rule_fire_mends`、`affix_rule_move_any_object`、`affix_rule_bleeding_wake`）、授予的技能與反應
在卸下裝備時消失、反應暫停點、改變規則只作用在持有者（不影響其他單位與全域預覽）、同時生效的規則
改變最多 1 個、檢視（來自裝備）、預覽與 AI、重播。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7
from tests.engine.test_gear import Rolls
from tests.engine.test_gear import _loadout as _plain_loadout
from trpg.cli.main import main as cli_main
from trpg.content.equipment import (
    ActionAffix,
    Loadout,
    ReactionAffix,
    RuleAffix,
    loadout_problems,
)
from trpg.content.library import _affix_reference_problems
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    Interact,
    Move,
    SetReactionMode,
    UseSkill,
    legal_actions,
    preview,
    resolve,
    resume,
)
from trpg.engine.activations import activation_problem, active_rule_change
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    AttackIntercepted,
    DamageDealt,
    EventBase,
    Healed,
    ObjectMoved,
    ReactionDeclined,
    ReactionTriggered,
    RuleChangeTriggered,
    StatusApplied,
    StatusResisted,
    SurfaceChanged,
)
from trpg.engine.gear import build_gear
from trpg.engine.gear_reactions import extra_uses_left, gear_reaction_rules
from trpg.engine.setup import BattleSetupError
from trpg.engine.skill_triggers import reset_round_counts
from trpg.engine.state import state_from_json, state_to_json
from trpg.engine.view import project_for
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Pos, Team, UnitId

U1, U2, U3, U4 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003"), UnitId("unit_0004")

GRAPPLE = ("affix_act_grapple", None)
SMOKE = ("affix_act_smoke", None)
WALL = ("affix_act_shield_wall", None)
RANGED_BLOCK = ("affix_react_ranged_block", None)
GUARD = ("affix_react_guard_ally", None)
DOUBLE_OW = ("affix_react_double_overwatch", None)
FIRE_MENDS = ("affix_rule_fire_mends", None)
MOVE_ANY = ("affix_rule_move_any_object", None)
WAKE = ("affix_rule_bleeding_wake", None)

WIDE = "\n".join(["0" * 14] * 5)
FIRE_ALL = make_skill(  # 測試專用：火焰傷害連隊友一起打（content 裡沒有這樣的技能）
    "skill_t_fire_all",
    {"type": "square3", "range": 4},
    [{"type": "damage", "dice": "2d4", "element": "fire", "affects": "all"}],
)


def _loadout(slots: Mapping[str, Rolls]) -> Loadout:
    """測試用裝備快照；掛了改變規則詞條的物品是傳說物品。"""
    plain = _plain_loadout(slots)
    legendary = {a for rolls in slots.values() for a, _ in rolls if "_rule_" in a}
    return Loadout(
        items=tuple(
            e.model_copy(
                update={
                    "item": e.item.model_copy(
                        update={
                            "legendary": any(a.affix.id in legendary for a in e.affixes),
                            "tags": ("shield",) if e.slot == "off_hand" else (),
                        }
                    )
                }
            )
            for e in plain.items
        )
    )


def of_type[T: EventBase](events: Sequence[EventBase], kind: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def always(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 1) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def scene(
    slots: Mapping[str, Rolls],
    *,
    foes: Sequence[tuple[int, int]] = ((3, 0),),
    allies: Sequence[tuple[int, int]] = (),
    reactions: bool = False,
    foe_base: str = "bandit",
) -> BattleState:
    """U1（穿裝備的我方戰士，(0, 0)）、其後的我方隊友（沒有裝備）、再來是敵人；U1 拿到回合。"""
    m = make_map(FLAT7, ally=[(0, 0), *allies], enemy=list(foes))
    tmpl = template("hero_fighter") if reactions else no_reactions("hero_fighter")
    hero = spawn(Team.ALLY, (0, 0), tmpl).model_copy(update={"equipment": _loadout(slots)})
    mates = [spawn(Team.ALLY, xy, no_reactions("hero_fighter")) for xy in allies]
    enemies = [spawn(Team.ENEMY, xy, no_reactions(foe_base, max_hp=999)) for xy in foes]
    return give_turn(make_state(m, [hero, *mates, *enemies]), U1)


def skill_actions(state: BattleState, skill_id: str) -> list[UseSkill]:
    return [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == skill_id]


# ---------------------------------------------------------------------------
# 內容（載入時檢查）
# ---------------------------------------------------------------------------


def test_nine_whitelist_affixes_load_and_reference_existing_things() -> None:
    lib = library()
    keyword_ids = frozenset(lib.ruleset.keywords.ids())
    for affix_id, kind in (
        (GRAPPLE[0], ActionAffix),
        (SMOKE[0], ActionAffix),
        (WALL[0], ActionAffix),
        (RANGED_BLOCK[0], ReactionAffix),
        (GUARD[0], ReactionAffix),
        (DOUBLE_OW[0], ReactionAffix),
        (FIRE_MENDS[0], RuleAffix),
        (MOVE_ANY[0], RuleAffix),
        (WAKE[0], RuleAffix),
    ):
        affix = lib.affixes[affix_id]
        assert isinstance(affix, kind)
        assert not _affix_reference_problems(affix, lib.ruleset, lib.weapons, keyword_ids)


def test_library_rejects_bad_action_and_reaction_references() -> None:
    lib = library()
    keyword_ids = frozenset(lib.ruleset.keywords.ids())

    def problems(affix: Any) -> list[str]:
        return _affix_reference_problems(affix, lib.ruleset, lib.weapons, keyword_ids)

    grapple, ranged, guard = (lib.affixes[a] for a in (GRAPPLE[0], RANGED_BLOCK[0], GUARD[0]))
    assert isinstance(grapple, ActionAffix)
    assert isinstance(ranged, ReactionAffix) and isinstance(guard, ReactionAffix)
    assert problems(grapple.model_copy(update={"skill": "skill_no_such"}))
    passive = next(s.id for s in lib.ruleset.skills.skills if s.kind == "passive")
    assert problems(grapple.model_copy(update={"skill": passive}))  # 被動技不是「動作」
    assert problems(ranged.model_copy(update={"event": "enemy_leaves_adjacent"}))
    assert problems(ranged.model_copy(update={"reaction": "no_such_reaction"}))
    assert problems(guard.model_copy(update={"range": None}))
    assert problems(guard.model_copy(update={"reaction": "block"}))


def test_gear_skills_are_content_with_the_stated_costs() -> None:
    skills = library().ruleset.skills.by_id()
    grapple = skills["skill_gear_grapple"]
    assert (grapple.ap_cost, grapple.cost.cooldown) == (1, 3)
    assert grapple.shape.type == "single" and grapple.shape.range == 4
    assert [(e.type, e.distance) for e in grapple.effects] == [("pull", 2)]
    smoke = skills["skill_gear_smoke_bomb"]
    assert (smoke.ap_cost, smoke.cost.cooldown) == (1, 4)
    assert smoke.shape.type == "square3" and smoke.shape.range == 3
    assert [(e.type, e.surface, e.duration) for e in smoke.effects] == [
        ("create_surface", "smoke", 2)
    ]
    wall = skills["skill_gear_shield_wall"]
    assert (wall.ap_cost, wall.cost.cooldown) == (1, 3)
    assert [(e.type, e.duration) for e in wall.effects] == [("create_obstacle", 2)]


# ---------------------------------------------------------------------------
# 第 9 類 授予動作
# ---------------------------------------------------------------------------


def test_grapple_is_granted_by_gear_and_lost_without_it() -> None:
    worn = scene({"hands": [GRAPPLE]}, foes=[(4, 0)])
    assert "skill_gear_grapple" in worn.units[U1].skills
    assert skill_actions(worn, "skill_gear_grapple")
    bare = scene({}, foes=[(4, 0)])  # 卸下裝備：技能與動作都沒有
    assert "skill_gear_grapple" not in bare.units[U1].skills
    assert not skill_actions(bare, "skill_gear_grapple")


def test_grant_does_not_duplicate_a_skill_the_unit_already_has() -> None:
    m = make_map(FLAT7, ally=[(0, 0)], enemy=[(3, 0)])
    base = no_reactions("hero_fighter").model_copy(update={"skills": ("skill_gear_grapple",)})
    hero = spawn(Team.ALLY, (0, 0), base).model_copy(
        update={"equipment": _loadout({"hands": [GRAPPLE]})}
    )
    state = make_state(m, [hero, spawn(Team.ENEMY, (3, 0), no_reactions("bandit"))])
    assert state.units[U1].skills.count("skill_gear_grapple") == 1


def test_grapple_pulls_a_target_in_range_two_tiles_and_goes_on_cooldown() -> None:
    state = scene({"hands": [GRAPPLE]}, foes=[(4, 0)])
    action = UseSkill(unit_id=U1, skill_id="skill_gear_grapple", target_id=U2)
    assert action in legal_actions(state)
    after = resolve(state, action).state
    assert after.units[U2].xy == (2, 0)  # 4 格外拉近 2 格
    assert after.units[U1].ap == state.units[U1].ap - 1
    assert after.units[U1].cooldowns["skill_gear_grapple"] == 3
    assert action not in legal_actions(after)  # 冷卻中


def test_grapple_cannot_reach_beyond_four_tiles() -> None:
    state = scene({"hands": [GRAPPLE]}, foes=[(5, 0)])
    assert not skill_actions(state, "skill_gear_grapple")


def test_smoke_bomb_makes_smoke_for_two_rounds() -> None:
    state = scene({"hands": [SMOKE]}, foes=[(6, 6)])
    at = Pos(x=3, y=0)
    action = UseSkill(unit_id=U1, skill_id="skill_gear_smoke_bomb", target_pos=at)
    assert action in legal_actions(state)
    result = resolve(state, action)
    made = {e.pos for e in of_type(result.events, SurfaceChanged) if e.after == "smoke"}
    assert made >= {Pos(x=2, y=0), Pos(x=3, y=0), Pos(x=4, y=0)}  # 半徑 1（3×3）
    assert all(
        e.remaining == 2 for e in of_type(result.events, SurfaceChanged) if e.after == "smoke"
    )
    assert result.state.units[U1].cooldowns["skill_gear_smoke_bomb"] == 4
    too_far = UseSkill(unit_id=U1, skill_id="skill_gear_smoke_bomb", target_pos=Pos(x=4, y=0))
    assert too_far not in legal_actions(state)  # 3 格外


def test_shield_wall_raises_a_temporary_obstacle_in_front() -> None:
    state = scene({"off_hand": [WALL]}, foes=[(6, 6)])
    action = UseSkill(unit_id=U1, skill_id="skill_gear_shield_wall", target_pos=Pos(x=1, y=0))
    assert action in legal_actions(state)
    after = resolve(state, action).state
    wall = after.object_at(1, 0)
    assert wall is not None and wall.kind == "earth_wall"
    assert wall.expires_in is not None  # 暫時障礙（2 回合）
    assert after.units[U1].cooldowns["skill_gear_shield_wall"] == 3
    far = UseSkill(unit_id=U1, skill_id="skill_gear_shield_wall", target_pos=Pos(x=2, y=0))
    assert far not in legal_actions(state)  # 前方 1 格以外不行


def test_granted_skills_are_listed_with_their_equipment_source() -> None:
    state = scene({"hands": [GRAPPLE, SMOKE], "off_hand": [WALL]})
    mine = project_for(state, Team.ALLY).units[0]
    assert {(g.skill_id, g.slot, g.affix_id) for g in mine.gear_skills} == {
        ("skill_gear_grapple", "hands", GRAPPLE[0]),
        ("skill_gear_smoke_bomb", "hands", SMOKE[0]),
        ("skill_gear_shield_wall", "off_hand", WALL[0]),
    }
    assert all(g.item_name_zh and g.slot_zh and g.name_zh for g in mine.gear_skills)
    assert {g.skill_id for g in mine.gear_skills} <= set(mine.skills)
    enemy_view = project_for(state, Team.ENEMY)  # 敵方看不到
    assert next(u for u in enemy_view.units if u.id == U1).gear_skills == ()


def test_same_granting_affix_on_two_items_grants_the_skill_once() -> None:
    state = scene({"hands": [GRAPPLE], "off_hand": [GRAPPLE]})
    assert state.units[U1].skills.count("skill_gear_grapple") == 1
    assert len(project_for(state, Team.ALLY).units[0].gear_skills) == 1


def test_preview_of_a_granted_skill_shows_cost_and_effect() -> None:
    state = scene({"hands": [GRAPPLE]}, foes=[(4, 0)])
    action = UseSkill(unit_id=U1, skill_id="skill_gear_grapple", target_id=U2)
    pv = preview(state, action)
    assert pv.ap_cost == 1
    assert pv.affected_units == (U2,)
    assert pv.reach == 4


def test_ai_ranks_a_granted_skill_among_its_candidates() -> None:
    state = scene({"hands": [GRAPPLE]}, foes=[(4, 0)])
    ranked = UtilityAI(library().ai_profiles, override="brute").rank(state)
    assert any(
        isinstance(s.action, UseSkill) and s.action.skill_id == "skill_gear_grapple" for s in ranked
    )


def test_ai_uses_the_granted_skill_to_drag_an_enemy_into_lava() -> None:
    """AI 真的會用授予的技能：把殘血的敵人拉進岩漿（路徑上的 (1, 0)、(2, 0) 是岩漿）。"""
    rows = ["." + "~~" + "...."] + ["." * 7] * 6
    terrain = "\n".join(rows)
    m = make_map(FLAT7, terrain, ally=[(0, 0)], enemy=[(3, 0)])
    hero = spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter")).model_copy(
        update={"equipment": _loadout({"hands": [GRAPPLE]})}
    )
    foe = spawn(Team.ENEMY, (3, 0), no_reactions("bandit", max_hp=20))
    state = give_turn(make_state(m, [hero, foe]), U1)
    state.units[U1].move_points = 0
    state.units[U1].ran_this_turn = True
    chosen = UtilityAI(library().ai_profiles, override="brute")(state)
    assert isinstance(chosen, UseSkill) and chosen.skill_id == "skill_gear_grapple"
    assert chosen.target_id == U2
    assert not resolve(state, chosen).state.units[U2].alive


# ---------------------------------------------------------------------------
# 第 10 類 授予反應：被遠程攻擊也可以格擋
# ---------------------------------------------------------------------------


def _archer_duel(slots: Mapping[str, Rolls]) -> BattleState:
    """敵方弓手在 (4, 0)，U1 在 (0, 0) 穿裝備、有預設反應；輪到敵人（U2）。"""
    state = scene(slots, foes=[(4, 0)], foe_base="bandit_archer", reactions=True)
    return give_turn(state, U2)


def test_block_by_default_does_not_trigger_against_ranged(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(_archer_duel({}), Attack(unit_id=U2, target_id=U1))
    assert not of_type(result.events, ReactionTriggered)


def test_ranged_block_lets_the_owner_block_ranged_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    plain = resolve(_archer_duel({}), Attack(unit_id=U2, target_id=U1))
    result = resolve(_archer_duel({"off_hand": [RANGED_BLOCK]}), Attack(unit_id=U2, target_id=U1))
    assert [e.reaction for e in of_type(result.events, ReactionTriggered)] == ["block"]
    blocked = of_type(result.events, DamageDealt)[0].amount
    assert blocked < of_type(plain.events, DamageDealt)[0].amount  # 傷害減半


def test_ranged_block_keeps_working_against_melee(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene({"off_hand": [RANGED_BLOCK]}, foes=[(1, 0)], reactions=True)
    result = resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U1))
    assert [e.reaction for e in of_type(result.events, ReactionTriggered)] == ["block"]  # 只一次


def test_ranged_block_only_changes_its_owner() -> None:
    state = scene({"off_hand": [RANGED_BLOCK]}, allies=[(1, 0)], foes=[(5, 0)], reactions=True)
    assert any(r.when.event == "targeted_by_attack" for r in state.units[U1].reactions)
    assert state.units[U2].reactions == ()  # 隊友沒有裝備，反應規則不變


def test_ranged_block_rule_shows_as_coming_from_gear() -> None:
    owner = project_for(_archer_duel({"off_hand": [RANGED_BLOCK]}), Team.ALLY).units[0]
    blocks = [r for r in owner.reaction_rules if r.reaction == "block"]
    assert {r.event for r in blocks} >= {"targeted_by_melee", "targeted_by_attack"}
    assert all("遠程" in r.gear_source_zh and r.gear_source_zh for r in blocks)
    bare = project_for(_archer_duel({}), Team.ALLY).units[0]
    assert all(r.gear_source_zh == "" for r in bare.reaction_rules)  # 不穿就沒有「來自裝備」


def test_ranged_block_follows_the_mode_of_the_existing_block_rule() -> None:
    rules = library().ruleset
    gear = build_gear(_loadout({"off_hand": [RANGED_BLOCK]}), rules.equipment)
    existing = tuple(r.model_copy(update={"mode": "prompt"}) for r in rules.reactions.default_rules)
    added = gear_reaction_rules(gear, rules, existing)
    assert [(r.reaction, r.when.event, r.mode) for r in added] == [
        ("block", "targeted_by_attack", "prompt")
    ]
    assert gear_reaction_rules(gear, rules, (*existing, *added)) == ()  # 已有同事件就不重複


def test_ranged_block_pauses_for_a_decision_in_prompt_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """反應暫停點：詢問模式下被遠程攻擊時結算暫停；接受後格擋、拒絕後不格擋。"""
    always(monkeypatch)
    state = _archer_duel({"off_hand": [RANGED_BLOCK]})
    owner = state.units[U1]
    owner.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in owner.reactions)
    first = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert first.pending is not None
    assert (first.pending.reaction, first.pending.unit_id) == ("block", U1)
    accepted = resume(first.state, Decision(unit_id=U1, accept=True))
    assert accepted.pending is None
    assert [e.reaction for e in of_type(accepted.events, ReactionTriggered)] == ["block"]
    declined = resume(first.state, Decision(unit_id=U1, accept=False))
    assert of_type(declined.events, ReactionDeclined)
    assert not of_type(declined.events, ReactionTriggered)
    assert (
        of_type(accepted.events, DamageDealt)[0].amount
        < of_type(declined.events, DamageDealt)[0].amount
    )


def test_set_reaction_mode_switches_the_gear_rule_too() -> None:
    state = _archer_duel({"off_hand": [RANGED_BLOCK]})
    after = resolve(
        give_turn(state, U1), SetReactionMode(unit_id=U1, reaction="block", mode="prompt")
    ).state
    assert {r.mode for r in after.units[U1].reactions if r.reaction == "block"} == {"prompt"}


# ---------------------------------------------------------------------------
# 第 10 類 授予反應：替隊友承受
# ---------------------------------------------------------------------------


def _guard_scene(
    slots: Mapping[str, Rolls], mate: tuple[int, int] = (2, 0), reactions: bool = True
) -> BattleState:
    """U1 穿護衛裝備 (0, 0)；隊友 U2 在 ``mate``；敵方弓手 U3 在 (4, 0)；輪到敵人。"""
    state = scene(
        slots, foes=[(4, 0)], allies=[mate], reactions=reactions, foe_base="bandit_archer"
    )
    return give_turn(state, U3)


def test_guard_ally_redirects_an_attack_on_a_teammate_within_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(_guard_scene({"body": [GUARD]}), Attack(unit_id=U3, target_id=U2))
    (redirected,) = of_type(result.events, AttackIntercepted)
    assert (redirected.guardian_id, redirected.target_id) == (U1, U2)
    assert not redirected.guard
    damage = of_type(result.events, DamageDealt)
    assert damage and all(e.target_id == U1 for e in damage)  # 全部由持有者承受
    assert [e.reaction for e in of_type(result.events, ReactionTriggered)] == ["redirect_damage"]


def test_guard_ally_does_not_trigger_beyond_its_range(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _guard_scene({"body": [GUARD]}, mate=(3, 0))  # 距離 3 > 2
    result = resolve(state, Attack(unit_id=U3, target_id=U2))
    assert not of_type(result.events, AttackIntercepted)


def test_guard_ally_does_not_trigger_when_the_owner_is_attacked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(_guard_scene({"body": [GUARD]}), Attack(unit_id=U3, target_id=U1))
    assert not of_type(result.events, AttackIntercepted)


def test_guard_ally_is_once_per_round_and_resets_each_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    first = resolve(_guard_scene({"body": [GUARD]}), Attack(unit_id=U3, target_id=U2))
    assert of_type(first.events, AttackIntercepted)
    again = first.state
    again.units[U3].ap = 3
    again.units[U1].reactions_used = 0  # 就算還有反應次數，詞條本身每輪只能 1 次
    second = resolve(again, Attack(unit_id=U3, target_id=U2))
    assert not of_type(second.events, AttackIntercepted)
    assert second.state.units[U1].gear_round_counts[GUARD[0]] == 1
    reset_round_counts(iter(second.state.units.values()))  # 下一輪開始
    third_state = second.state
    third_state.units[U3].ap = 3
    third = resolve(third_state, Attack(unit_id=U3, target_id=U2))
    assert of_type(third.events, AttackIntercepted)


def test_guard_ally_pauses_for_a_decision_and_can_be_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """反應暫停點：詢問模式下結算暫停；拒絕後攻擊仍打在隊友身上、詞條次數沒有用掉。"""
    always(monkeypatch)
    state = _guard_scene({"body": [GUARD]})
    guard = state.units[U1]
    guard.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in guard.reactions)
    first = resolve(state, Attack(unit_id=U3, target_id=U2))
    assert first.pending is not None and first.pending.reaction == "redirect_damage"
    assert (first.pending.unit_id, first.pending.trigger_unit_id) == (U1, U3)
    declined = resume(first.state, Decision(unit_id=U1, accept=False))
    assert not of_type(declined.events, AttackIntercepted)
    assert all(e.target_id == U2 for e in of_type(declined.events, DamageDealt))
    assert GUARD[0] not in declined.state.units[U1].gear_round_counts
    accepted = resume(first.state, Decision(unit_id=U1, accept=True))
    assert of_type(accepted.events, AttackIntercepted)


def test_guard_ally_off_mode_never_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _guard_scene({"body": [GUARD]})
    guard = state.units[U1]
    guard.reactions = tuple(r.model_copy(update={"mode": "off"}) for r in guard.reactions)
    result = resolve(state, Attack(unit_id=U3, target_id=U2))
    assert result.pending is None and not of_type(result.events, AttackIntercepted)


def test_guard_ally_shows_in_the_reaction_settings_as_gear() -> None:
    owner = project_for(_guard_scene({"body": [GUARD]}), Team.ALLY).units[0]
    rule = next(r for r in owner.reaction_rules if r.reaction == "redirect_damage")
    assert rule.mode == "auto" and rule.name_zh and rule.trigger_zh
    assert "護衛鎖甲" not in rule.gear_source_zh  # 測試物品的名字是「測試body」
    assert rule.gear_source_zh.startswith("測試body：")


def test_guard_ally_is_gone_without_the_gear() -> None:
    state = _guard_scene({})
    assert all(r.reaction != "redirect_damage" for r in state.units[U1].reactions)


def test_guard_ally_preview_redirects_too() -> None:
    """預覽走同一個結算流程：預覽對隊友的攻擊，傷害落在持有者身上。"""
    state = _guard_scene({"body": [GUARD]})
    pv = preview(state, Attack(unit_id=U3, target_id=U2))
    assert pv.max_events is not None
    hits = [e for e in pv.max_events if isinstance(e, DamageDealt)]
    assert hits and all(e.target_id == U1 for e in hits)


# ---------------------------------------------------------------------------
# 第 10 類 授予反應：監視射擊每輪可以觸發 2 次
# ---------------------------------------------------------------------------


def _watch(slots: Mapping[str, Rolls]) -> BattleState:
    """U1（弓手，已經施放監視）在 (1, 2)；敵人 U2 在 (11, 2)，輪到 U2。"""
    m = make_map(WIDE, None, ally=[(1, 2)], enemy=[(11, 2)])
    archer = caster_template(["skill_overwatch"], base="hero_archer")
    hero = spawn(Team.ALLY, (1, 2), archer).model_copy(update={"equipment": _loadout(slots)})
    state = give_turn(
        make_state(m, [hero, spawn(Team.ENEMY, (11, 2), no_reactions(max_hp=999))]), U1
    )
    state = resolve(state, UseSkill(unit_id=U1, skill_id="skill_overwatch")).state
    return give_turn(state, U2)


def _walk(state: BattleState, *path: tuple[int, int]) -> Any:
    start = state.units[U2].pos
    return resolve(state, Move(unit_id=U2, path=(start, *(Pos(x=x, y=y) for x, y in path))))


def _shots(result: Any) -> int:
    return sum(
        1 for e in of_type(result.events, ReactionTriggered) if e.reaction == "overwatch_shot"
    )


def test_overwatch_fires_once_per_round_without_the_gear(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _watch({})
    assert extra_uses_left(state.units[U1], "overwatch_shot") == 0
    result = _walk(state, (10, 2), (9, 2), (8, 2), (7, 2))
    assert _shots(result) == 1
    assert not result.state.units[U1].has_status("overwatch")


def test_double_overwatch_fires_twice_then_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _watch({"head": [DOUBLE_OW]})
    assert extra_uses_left(state.units[U1], "overwatch_shot") == 1
    result = _walk(state, (10, 2), (9, 2), (8, 2), (7, 2), (6, 2))
    assert _shots(result) == 2
    after = result.state.units[U1]
    assert not after.has_status("overwatch")  # 用完最後一次才結束
    assert extra_uses_left(after, "overwatch_shot") == 0
    assert after.reactions_used == 1  # 額外次數不佔一般的反應次數


def test_double_overwatch_keeps_the_status_after_the_first_shot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = _watch({"head": [DOUBLE_OW]})
    result = _walk(state, (10, 2), (9, 2))  # 第一次射擊
    assert _shots(result) == 1
    assert result.state.units[U1].has_status("overwatch")


def test_double_overwatch_extra_use_comes_back_each_round(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = _walk(_watch({"head": [DOUBLE_OW]}), (10, 2), (9, 2), (8, 2))
    state = result.state
    assert extra_uses_left(state.units[U1], "overwatch_shot") == 0
    reset_round_counts(iter(state.units.values()))
    assert extra_uses_left(state.units[U1], "overwatch_shot") == 1


def test_double_overwatch_does_not_give_other_reactions_extra_uses() -> None:
    state = _watch({"head": [DOUBLE_OW]})
    assert extra_uses_left(state.units[U1], "block") == 0
    assert extra_uses_left(state.units[U2], "overwatch_shot") == 0  # 其他單位不受影響


# ---------------------------------------------------------------------------
# 第 11 類 改變規則：只作用在持有者
# ---------------------------------------------------------------------------


def arena(
    slots: Mapping[str, Rolls],
    *,
    foes: Sequence[tuple[int, int]] = ((6, 6),),
    allies: Sequence[tuple[int, int]] = (),
    objects: Sequence[tuple[int, int, str]] = (),
    holder: tuple[int, int] = (3, 3),
) -> BattleState:
    """U1 持有者（穿裝備的我方戰士，HP 200）；之後依序是 ``foes``（敵人，HP 200）與 ``allies``
    （沒有裝備的友方戰士，HP 200）。"""
    m = make_map(FLAT7, None, ally=[holder, *allies], enemy=list(foes), objects=list(objects))
    first = spawn(Team.ALLY, holder, no_reactions("hero_fighter", max_hp=200)).model_copy(
        update={"equipment": _loadout(slots)}
    )
    spawns = [first]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_fighter", max_hp=200)) for xy in allies]
    return give_turn(make_state(m, spawns), U1)


def _hit(
    state: BattleState, source: UnitId, target: UnitId, element: Element = Element.FIRE
) -> list[EventBase]:
    ctx = Ctx(state.clone())
    execute(ctx, [DamageEffect(target_id=target, source_id=source, element=element, flat=10)])
    return ctx.events


def test_fire_mends_heals_allies_hit_by_the_holders_fire() -> None:
    state = arena({"neck": [FIRE_MENDS]}, allies=[(2, 3)])
    state.units[U3].hp = 150
    events = _hit(state, U1, U3)
    assert not of_type(events, DamageDealt)
    (trig,) = of_type(events, RuleChangeTriggered)
    (healed,) = of_type(events, Healed)
    assert (trig.kind, trig.other_id, trig.amount) == ("element_heals_allies", U3, 10)
    assert (healed.target_id, healed.amount, healed.hp_after) == (U3, 10, 160)
    assert trig.skill_id == "skill_gear_rule_fire_mends"


def test_fire_mends_is_not_active_without_the_gear() -> None:
    state = arena({}, allies=[(2, 3)])
    assert active_rule_change(state, state.units[U1]) is None
    events = _hit(state, U1, U3)
    assert of_type(events, DamageDealt) and not of_type(events, Healed)


def test_fire_mends_still_burns_enemies_the_holder_and_other_elements() -> None:
    state = arena({"neck": [FIRE_MENDS]}, allies=[(2, 3)])
    assert of_type(_hit(state, U1, U2), DamageDealt)  # 敵人
    assert of_type(_hit(state, U1, U1), DamageDealt)  # 自己不算友方
    assert of_type(_hit(state, U1, U3, Element.ICE), DamageDealt)  # 不是火焰


def test_fire_mends_only_applies_to_the_holders_own_fire() -> None:
    """其他單位（敵人、沒有裝備的隊友）的火焰照常傷到隊友；持有者的規則不改變他們的結算。"""
    state = arena({"neck": [FIRE_MENDS]}, allies=[(2, 3), (4, 4)])
    assert of_type(_hit(state, U2, U3), DamageDealt)  # 敵人的火打隊友
    assert of_type(_hit(state, U4, U3), DamageDealt)  # 沒有裝備的隊友的火打隊友
    assert active_rule_change(state, state.units[U3]) is None
    assert active_rule_change(state, state.units[U4]) is None
    assert active_rule_change(state, state.units[U2]) is None


def test_fire_mends_does_not_change_other_units_results_at_all() -> None:
    """全域不受影響：同一個非持有者的結算，持有者穿不穿裝備，事件逐筆相同。"""
    with_gear = arena({"neck": [FIRE_MENDS]}, allies=[(2, 3), (4, 4)])
    without = arena({}, allies=[(2, 3), (4, 4)])
    for state in (with_gear, without):
        state.units[U3].hp = 150
    a = [e.model_dump_json() for e in _hit(with_gear, U4, U3)]
    b = [e.model_dump_json() for e in _hit(without, U4, U3)]
    assert a == b
    c = [e.model_dump_json() for e in _hit(with_gear, U2, U3)]
    d = [e.model_dump_json() for e in _hit(without, U2, U3)]
    assert c == d


def _mage_with_ally(slots: Mapping[str, Rolls]) -> BattleState:
    """U1 法師（爆破）在 (0, 0)，隊友 U2（HP 100／200）在 (2, 0)，敵人 U3 在 (3, 0)。"""
    m = make_map(FLAT7, ally=[(0, 0), (2, 0)], enemy=[(3, 0)])
    mage = spawn(Team.ALLY, (0, 0), caster_template([FIRE_ALL], base="hero_mage"))
    mate = spawn(Team.ALLY, (2, 0), no_reactions("hero_fighter", max_hp=200))
    spawns = [mage.model_copy(update={"equipment": _loadout(slots)}), mate]
    spawns.append(spawn(Team.ENEMY, (3, 0), no_reactions(max_hp=200)))
    state = give_turn(make_state(m, spawns, skills=[FIRE_ALL]), U1)
    state.units[U2].hp = 100
    return state


def test_fire_mends_preview_shows_the_heal_only_for_the_holder() -> None:
    """預覽走同一個結算流程：持有者的火焰技預覽顯示對隊友的治療；沒有裝備的預覽是傷害。"""
    action = UseSkill(unit_id=U1, skill_id=FIRE_ALL.id, target_pos=Pos(x=3, y=0))
    mends = preview(_mage_with_ally({"neck": [FIRE_MENDS]}), action)
    healed = [e for e in mends.max_events if isinstance(e, Healed)]
    assert [e.target_id for e in healed] == [U2] and healed[0].amount > 0
    assert not any(isinstance(e, DamageDealt) and e.target_id == U2 for e in mends.max_events)
    plain = preview(_mage_with_ally({}), action)
    assert not any(isinstance(e, Healed) for e in plain.max_events)
    assert any(isinstance(e, DamageDealt) and e.target_id == U2 for e in plain.max_events)


def test_fire_mends_ai_scores_the_ally_hit_as_a_heal_not_friendly_fire() -> None:
    """AI 評分走預覽的結果：同一個火焰範圍技，持有者的分數比沒有裝備時高（隊友是被治療）。"""
    action = UseSkill(unit_id=U1, skill_id=FIRE_ALL.id, target_pos=Pos(x=3, y=0))

    def score(slots: Mapping[str, Rolls]) -> Any:
        ranked = UtilityAI(library().ai_profiles, override="brute").rank(_mage_with_ally(slots))
        return next(s.score for s in ranked if s.action == action)

    assert score({"neck": [FIRE_MENDS]}) > score({})


def _wall_arena(slots: Mapping[str, Rolls], kind: str = "earth_wall") -> BattleState:
    return arena(slots, objects=[(4, 3, kind)], allies=[(3, 4)])


def _push(state: BattleState, unit: UnitId = U1) -> Interact:
    obj = state.object_at(4, 3)
    assert obj is not None
    return Interact(unit_id=unit, object_id=obj.id)


def test_move_any_object_lets_the_holder_push_an_earth_wall_from_the_start() -> None:
    state = _wall_arena({"neck": [MOVE_ANY]})
    assert _push(state) in legal_actions(state)
    result = resolve(state, _push(state))
    (trig,) = of_type(result.events, RuleChangeTriggered)
    (moved,) = of_type(result.events, ObjectMoved)
    assert trig.kind == "push_any_object" and trig.object_id == moved.object_id
    assert (moved.from_pos, moved.to_pos) == (Pos(x=4, y=3), Pos(x=5, y=3))


def test_move_any_object_is_off_without_the_gear() -> None:
    state = _wall_arena({})
    assert _push(state) not in legal_actions(state)
    with pytest.raises(IllegalActionError, match="土牆無法推動"):
        resolve(state, _push(state))


@pytest.mark.parametrize("kind", ["low_wall", "fallen_log", "rubble"])
def test_move_any_object_pushes_other_blocking_objects(kind: str) -> None:
    state = _wall_arena({"neck": [MOVE_ANY]}, kind)
    assert of_type(resolve(state, _push(state)).events, ObjectMoved)


def test_move_any_object_does_not_let_other_units_push() -> None:
    """持有者的隊友（沒有裝備）仍然推不動土牆。"""
    state = give_turn(_wall_arena({"neck": [MOVE_ANY]}), U3)
    assert active_rule_change(state, state.units[U3]) is None
    assert _push(state, U3) not in legal_actions(state)
    with pytest.raises(IllegalActionError, match="土牆無法推動"):
        resolve(state, _push(state, U3))


def test_move_any_object_does_not_move_floor_objects() -> None:
    state = arena({"neck": [MOVE_ANY]}, objects=[(4, 3, "wooden_bridge")])
    assert not any(isinstance(a, Interact) for a in legal_actions(state))


def _stroll(state: BattleState, unit: UnitId, *path: tuple[int, int]) -> Any:
    start = state.units[unit].pos
    return resolve(state, Move(unit_id=unit, path=(start, *(Pos(x=x, y=y) for x, y in path))))


def test_bleeding_wake_marks_each_adjacent_enemy_once_per_move() -> None:
    state = arena({"neck": [WAKE]}, foes=[(4, 2), (6, 6)], allies=[(2, 1)])
    result = _stroll(state, U1, (3, 2), (3, 1), (3, 0))
    triggered = of_type(result.events, RuleChangeTriggered)
    assert [(t.kind, t.other_id) for t in triggered] == [("pass_through_apply", U2)]
    outcome = of_type(result.events, StatusApplied) + of_type(result.events, StatusResisted)
    assert [e.target_id for e in outcome] == [U2]
    assert all(e.status_id == "bleed" for e in outcome)


def test_bleeding_wake_is_off_without_the_gear() -> None:
    state = arena({}, foes=[(4, 2)])
    assert not of_type(_stroll(state, U1, (3, 2), (3, 1)).events, RuleChangeTriggered)


def test_bleeding_wake_does_not_apply_to_other_units_movement() -> None:
    """隊友（沒有裝備）走過敵人身邊不會留下血痕。"""
    state = give_turn(arena({"neck": [WAKE]}, foes=[(4, 2)], allies=[(2, 1)]), U3)
    result = _stroll(state, U3, (3, 1), (3, 2))
    assert not of_type(result.events, RuleChangeTriggered)
    assert not of_type(result.events, StatusApplied)


def test_bleeding_wake_respects_the_trigger_depth_limit() -> None:
    state = arena({"neck": [WAKE]}, foes=[(4, 2)])
    state.ruleset = state.ruleset.model_copy(
        update={"core": state.ruleset.core.model_copy(update={"max_trigger_depth": 0})}
    )
    result = _stroll(state, U1, (3, 2))
    assert not of_type(result.events, RuleChangeTriggered)
    assert not of_type(result.events, StatusApplied) and not of_type(result.events, StatusResisted)


# ---------------------------------------------------------------------------
# 第 11 類：同時生效最多 1 個
# ---------------------------------------------------------------------------


def _loadout_problems(slots: Mapping[str, Rolls]) -> list[str]:
    rules = library().ruleset.equipment
    return loadout_problems(_loadout(slots), library().weapons["one_handed_sword"], rules)


def test_two_different_rule_affixes_fail_the_loadout_check() -> None:
    problems = _loadout_problems({"neck": [FIRE_MENDS], "ring_1": [WAKE]})
    assert any("改變規則類詞條全身最多 1 個" in p for p in problems)


def test_the_same_rule_affix_on_two_items_counts_once() -> None:
    problems = _loadout_problems({"neck": [FIRE_MENDS], "ring_1": [FIRE_MENDS]})
    assert not any("改變規則" in p for p in problems)
    state = arena({"neck": [FIRE_MENDS], "ring_1": [FIRE_MENDS]})
    change = active_rule_change(state, state.units[U1])
    assert change is not None and change.rule.id == "fire_mends_allies"


def test_a_gear_rule_blocks_activating_a_legendary_rule_change() -> None:
    state = arena({"neck": [FIRE_MENDS]})
    skill = state.ruleset.skill_def("skill_mountain_mover")
    problem = activation_problem(state, state.units[U1], skill)
    assert problem is not None and "已有生效中的規則改變" in problem


def test_setup_rejects_two_rule_affixes() -> None:
    with pytest.raises(BattleSetupError, match="改變規則類詞條全身最多 1 個"):
        arena({"neck": [FIRE_MENDS], "ring_1": [WAKE]})


# ---------------------------------------------------------------------------
# 序列化、確定性、重播
# ---------------------------------------------------------------------------


def test_granted_things_survive_serialization() -> None:
    state = scene({"hands": [GRAPPLE], "body": [GUARD], "off_hand": [RANGED_BLOCK]}, reactions=True)
    again = state_from_json(state_to_json(state))
    assert again.units[U1].skills == state.units[U1].skills
    assert again.units[U1].reactions == state.units[U1].reactions
    assert state_to_json(again) == state_to_json(state)


def test_g3b_gear_battle_log_json_and_replay(tmp_path: Path) -> None:
    """鉤盾戰士與哨兵弓手一起打，紀錄可重播（含授予的技能與反應）。"""
    log = tmp_path / "g3b.json"
    args = [
        "battle",
        "--map",
        "test_flat_6x6",
        "--allies",
        "gear_tester_g3b,gear_tester_g3b_sentinel",
        "--enemies",
        "bandit,bandit",
        "--seed",
        "3",
        "--log-json",
        str(log),
    ]
    assert cli_main(args) == 0
    assert cli_main(["battle", "replay", str(log)]) == 0
    text = log.read_text(encoding="utf-8")
    assert "skill_gear_" in text or "redirect_damage" in text or "overwatch_shot" in text
