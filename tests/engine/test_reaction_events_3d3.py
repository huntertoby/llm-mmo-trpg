"""Phase 3D-3 的四個新反應事件（``docs/phases/Phase3D計畫.md`` 3.2）。

- ``hit_by_spell``：被 ``category: spell`` 的技能命中、傷害結算之前；另一方是施放者。
- ``ally_downed``：視野內的友方倒下之後（等效果佇列清空）；另一方是倒下的友方。
- ``enemy_enters_adjacent``：敵人主動移動（步行、衝鋒、直線衝撞）進入相鄰格之後；強制位移不算。
- ``ally_targeted``：相鄰友方被敵人單體技能或普攻瞄準、命中判定之前；另一方是攻擊者。

每個事件都有觸發與不觸發的測試；同一組情境的詢問（``prompt``）、預覽與重播也在這裡。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

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
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_skills import reaction_skill
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.battle import UnitTemplate
from trpg.content.skills import SKILL_REACTION_EVENTS, SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    Move,
    ResolveResult,
    UseSkill,
    legal_actions,
    preview,
    resolve,
    resume,
)
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    ReactionDeclined,
    ReactionTriggered,
    ShieldGained,
    UnitDowned,
    UnitMoved,
)
from trpg.shared.types import Pos, Team, UnitId

COUNTERSPELL = "skill_counterspell"
GRIEF_RAGE = "skill_grief_rage"
AMBUSH = "skill_ambush_stab"
COVERING_FIRE = "skill_covering_fire"
FIRE_BOLT = "skill_fire_bolt"
GRAPPLE = "skill_grapple_arrow"
U4 = UnitId("unit_0004")


def world(
    units: Sequence[tuple[Team, tuple[int, int], UnitTemplate]],
    *,
    terrain: str | None = None,
    turn: UnitId = U2,
    skills: Sequence[SkillDef] = (),
) -> BattleState:
    """``units`` 依序是 U1、U2……；輪到 ``turn``。"""
    allies = [xy for team, xy, _ in units if team is Team.ALLY]
    foes = [xy for team, xy, _ in units if team is Team.ENEMY]
    m = make_map(FLAT7, terrain, ally=allies, enemy=foes)
    spawns = [spawn(team, xy, tmpl) for team, xy, tmpl in units]
    return give_turn(make_state(m, spawns, skills=skills), turn)


def index_of(events: Sequence[EventBase], kind: type[EventBase], **match: Any) -> int:
    """第一個符合欄位的事件在列表中的位置（找不到時失敗）。"""
    for i, e in enumerate(events):
        if isinstance(e, kind) and all(getattr(e, k) == v for k, v in match.items()):
            return i
    raise AssertionError(f"找不到 {kind.__name__} {match}")


def reactions(result: ResolveResult) -> list[ReactionTriggered]:
    return of(result, ReactionTriggered)


# ---------------------------------------------------------------------------
# 資料：事件清單、示範技能
# ---------------------------------------------------------------------------


def test_the_four_new_events_are_known_to_the_content_layer() -> None:
    assert set(SKILL_REACTION_EVENTS) >= {
        "hit_by_spell",
        "ally_downed",
        "enemy_enters_adjacent",
        "ally_targeted",
    }
    demos = {
        COUNTERSPELL: "hit_by_spell",
        GRIEF_RAGE: "ally_downed",
        AMBUSH: "enemy_enters_adjacent",
        COVERING_FIRE: "ally_targeted",
    }
    for skill_id, event in demos.items():
        skill = library().skills[skill_id]
        assert skill.kind == "reaction" and skill.reaction is not None
        assert skill.reaction.event == event


def test_an_ally_downed_reaction_must_be_a_self_shape() -> None:
    with pytest.raises(ValueError, match="ally_downed"):
        reaction_skill("skill_t_rx_bad_down", "ally_downed")  # 預設形狀是 single：另一方已經倒下


def test_equipped_reaction_skills_get_an_auto_rule_for_each_new_event() -> None:
    owner = caster_template([COUNTERSPELL], base="hero_mage")
    state = world([(Team.ALLY, (3, 3), owner), (Team.ENEMY, (6, 3), no_reactions())])
    assert [r.when.event for r in state.units[U1].reactions] == ["hit_by_spell"]


# ---------------------------------------------------------------------------
# hit_by_spell
# ---------------------------------------------------------------------------


def spell_duel(owner_skill: SkillDef | str = COUNTERSPELL, **owner: object) -> BattleState:
    """U1 持有反應技（法師，在 (3, 3)）；輪到 U2（敵方法師，裝備火焰箭，在 (5, 3)）。"""
    skills = [owner_skill]
    extra = [s for s in skills if isinstance(s, SkillDef)]
    return world(
        [
            (Team.ALLY, (3, 3), caster_template(skills, base="hero_mage", max_hp=999, **owner)),
            (Team.ENEMY, (5, 3), caster_template([FIRE_BOLT], base="hero_mage", max_hp=999)),
        ],
        skills=extra,
    )


def bolt(state: BattleState) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U2, skill_id=FIRE_BOLT, target_id=U1))


def test_hit_by_spell_fires_before_the_spell_damage_and_targets_the_caster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = spell_duel()
    hp_caster = state.units[U2].hp
    result = bolt(state)
    (trig,) = reactions(result)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U1, COUNTERSPELL, U2)
    events = result.events
    # 順序：命中判定 → 反應 → 反應的傷害（對施放者）→ 法術本身的傷害（對持有者）
    rolled = index_of(events, AttackRolled, attacker_id=U2, target_id=U1)
    reacted = index_of(events, ReactionTriggered)
    counter = index_of(events, DamageDealt, target_id=U2)
    spell = index_of(events, DamageDealt, target_id=U1)
    assert rolled < reacted < counter < spell
    assert result.state.units[U2].hp < hp_caster  # 反咒打到施放者
    assert result.state.units[U1].reactions_used == 1


def test_a_shield_reaction_is_up_before_the_spell_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    ward = reaction_skill(
        "skill_t_rx_spell_ward",
        "hit_by_spell",
        shape={"type": "self"},
        effects=[{"type": "shield", "dice": "2d6", "affects": "self"}],
    ).model_copy(update={"category": "spell", "weapon_req": "any", "scaling_attr": "wis"})
    result = bolt(spell_duel(ward))
    assert index_of(result.events, ShieldGained) < index_of(
        result.events, DamageDealt, target_id=U1
    )


def test_hit_by_spell_ignores_weapon_skills_basic_attacks_and_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    # 普攻（法杖）不是法術技
    state = spell_duel()
    swing = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert of(swing, DamageDealt) and not reactions(swing)
    # 武器技（category: weapon）不算法術
    blade = SkillDef.model_validate(
        {
            "id": "skill_t_weapon_hit",
            "name_zh": "測試劈砍",
            "tier": 1,
            "rarity": "common",
            "skeleton": "strike",
            "category": "weapon",
            "weapon_req": "ranged",
            "ap_cost": 1,
            "scaling_attr": "str",
            "shape": {"type": "single", "range": 5},
            "effects": [{"type": "damage", "multiplier_permille": 1000}],
            "cost": {"mana": 0},
        }
    )
    armed = world(
        [
            (Team.ALLY, (3, 3), caster_template([COUNTERSPELL], base="hero_mage", max_hp=999)),
            (Team.ENEMY, (5, 3), caster_template([blade], base="hero_archer", max_hp=999)),
        ],
        skills=[blade],
    )
    cut = resolve(armed, UseSkill(unit_id=U2, skill_id=blade.id, target_id=U1))
    assert of(cut, DamageDealt) and not reactions(cut)
    # 法術沒命中：沒有「被命中」
    always(monkeypatch, d20=1)
    missed = bolt(spell_duel())
    assert not of(missed, DamageDealt) and not reactions(missed)


def test_hit_by_spell_ask_the_player_with_prompt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    paused = bolt(prompt_state("hit_by_spell", COUNTERSPELL))
    assert paused.pending is not None
    assert (paused.pending.unit_id, paused.pending.reaction) == (U1, COUNTERSPELL)
    assert paused.pending.skill_id == COUNTERSPELL and paused.pending.trigger_unit_id == U2
    assert paused.pending.trigger_event_seq is not None
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert reactions(accepted) and accepted.pending is None
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert of(declined, ReactionDeclined) and not reactions(declined)
    assert of(declined, DamageDealt)  # 拒絕後法術照常結算


def prompt_state(event: str, skill: str) -> BattleState:
    """``spell_duel`` 的持有者規則改成 ``prompt``（網頁詢問模式）。"""
    state = spell_duel(skill)
    unit = state.units[U1]
    unit.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in unit.reactions)
    assert [r.when.event for r in unit.reactions] == [event]
    return state


# ---------------------------------------------------------------------------
# ally_downed
# ---------------------------------------------------------------------------


def downed_world(
    *,
    ally_hp: int = 1,
    terrain: str | None = None,
    owner_at: tuple[int, int] = (1, 3),
    foe_hp: int = 999,
) -> BattleState:
    """U1 持有悲憤（戰士）；U3（隊友弓手，HP ``ally_hp``）在 (5, 3)，被 U2（敵人，在 (6, 3)）盯上；
    輪到 U2。"""
    return world(
        [
            (Team.ALLY, owner_at, caster_template([GRIEF_RAGE], base="hero_fighter", max_hp=999)),
            (Team.ENEMY, (6, 3), no_reactions("bandit", max_hp=foe_hp)),
            (Team.ALLY, (5, 3), no_reactions("hero_archer", max_hp=ally_hp)),
        ],
        terrain=terrain,
    )


def test_ally_downed_fires_after_a_visible_ally_goes_down(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(downed_world(), Attack(unit_id=U2, target_id=U3))
    (trig,) = reactions(result)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U1, GRIEF_RAGE, U3)
    assert index_of(result.events, UnitDowned, unit_id=U3) < index_of(
        result.events, ReactionTriggered
    )
    owner = result.state.units[U1]
    assert any(s.status_id == "empowered" for s in owner.statuses)
    assert owner.reactions_used == 1


def test_ally_downed_ignores_enemies_itself_and_allies_that_survive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    # 倒下的是敵人（U3 反過來打倒 U2）：持有者的「友方」不是他
    state = downed_world(foe_hp=1)
    state = give_turn(state, U3)
    killed_foe = resolve(state, Attack(unit_id=U3, target_id=U2))
    assert of(killed_foe, UnitDowned) and not reactions(killed_foe)
    # 友方只是受傷
    hurt = resolve(downed_world(ally_hp=999), Attack(unit_id=U2, target_id=U3))
    assert not of(hurt, UnitDowned) and not reactions(hurt)
    # 持有者自己倒下：不是「友方」倒下
    solo = world(
        [
            (Team.ALLY, (3, 3), caster_template([GRIEF_RAGE], base="hero_fighter", max_hp=1)),
            (Team.ENEMY, (4, 3), no_reactions()),
        ]
    )
    self_down = resolve(solo, Attack(unit_id=U2, target_id=U1))
    assert of(self_down, UnitDowned) and not reactions(self_down)


def test_ally_downed_needs_the_owner_to_see_the_ally(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    rows = ["......."] * 7
    rows[3] = "...#..."  # 牆壁擋住 (1, 3) 看向 (5, 3) 的視線
    blocked = resolve(
        downed_world(terrain="\n".join(rows), owner_at=(1, 3)), Attack(unit_id=U2, target_id=U3)
    )
    assert of(blocked, UnitDowned) and not reactions(blocked)
    seen = resolve(downed_world(owner_at=(1, 3)), Attack(unit_id=U2, target_id=U3))
    assert reactions(seen)


def test_ally_downed_respects_the_reactions_per_round_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = world(
        [
            (Team.ALLY, (1, 3), caster_template([GRIEF_RAGE], base="hero_fighter", max_hp=999)),
            (Team.ENEMY, (6, 3), no_reactions("bandit", max_hp=999)),
            (Team.ALLY, (5, 3), no_reactions("hero_archer", max_hp=1)),
            (Team.ALLY, (6, 4), no_reactions("hero_archer", max_hp=1)),
        ]
    )
    first = resolve(state, Attack(unit_id=U2, target_id=U3))
    assert len(reactions(first)) == 1
    second = resolve(first.state, Attack(unit_id=U2, target_id=U4))
    assert of(second, UnitDowned) and not reactions(second)  # 每輪 1 次（已經用掉）


def test_ally_downed_is_asked_in_prompt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = downed_world()
    owner = state.units[U1]
    owner.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in owner.reactions)
    paused = resolve(state, Attack(unit_id=U2, target_id=U3))
    assert paused.pending is not None
    assert (paused.pending.unit_id, paused.pending.skill_id) == (U1, GRIEF_RAGE)
    assert paused.pending.trigger_unit_id == U3
    assert paused.pending.trigger_event_seq is not None  # 引發詢問的是倒下事件
    seq = paused.pending.trigger_event_seq
    downed = [e for e in paused.events if e.seq == seq]
    assert downed and isinstance(downed[0], UnitDowned)
    assert reactions(resume(paused.state, Decision(unit_id=U1, accept=True)))
    assert not reactions(resume(paused.state, Decision(unit_id=U1, accept=False)))


# ---------------------------------------------------------------------------
# enemy_enters_adjacent
# ---------------------------------------------------------------------------


def ambush_world(*, foe_hp: int = 999, foe_at: tuple[int, int] = (6, 3)) -> BattleState:
    """U1 持有迎頭痛擊（戰士，在 (3, 3)）；U2（敵人，在 ``foe_at``）的回合。"""
    return world(
        [
            (Team.ALLY, (3, 3), caster_template([AMBUSH], base="hero_fighter", max_hp=999)),
            (Team.ENEMY, foe_at, no_reactions("bandit", max_hp=foe_hp)),
        ]
    )


def walk(*cells: tuple[int, int], unit: UnitId = U2) -> Move:
    return Move(unit_id=unit, path=tuple(Pos(x=x, y=y) for x, y in cells))


def test_enemy_enters_adjacent_fires_when_a_walker_arrives_next_to_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(ambush_world(), walk((6, 3), (5, 3), (4, 3)))
    (trig,) = reactions(result)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U1, AMBUSH, U2)
    moved = index_of(result.events, UnitMoved, unit_id=U2, to_pos=Pos(x=4, y=3))
    assert moved < index_of(result.events, ReactionTriggered)  # 進入之後
    assert index_of(result.events, UnitMoved, unit_id=U2, to_pos=Pos(x=5, y=3)) < moved
    assert [r.attacker_id for r in of(result, AttackRolled)] == [U1]  # 反應對進入者出手
    assert result.state.units[U1].ap == ambush_world().units[U1].ap  # 不花 AP


def test_a_walker_that_stays_two_tiles_away_does_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(ambush_world(), walk((6, 3), (5, 3)))
    assert not reactions(result)


def test_the_reaction_can_kill_the_walker_before_he_takes_the_next_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, die=6)
    state = ambush_world(foe_hp=1)
    # 繞到持有者的另一側：進入 (4, 3) 時就倒下，之後的步數不會走
    result = resolve(state, walk((6, 3), (5, 3), (4, 3), (4, 4), (4, 5)))
    assert of(result, UnitDowned)
    destinations = [e.to_pos for e in of(result, UnitMoved) if e.unit_id == U2]
    assert destinations == [Pos(x=5, y=3), Pos(x=4, y=3)]


def test_allies_walking_next_to_the_owner_do_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = world(
        [
            (Team.ALLY, (3, 3), caster_template([AMBUSH], base="hero_fighter", max_hp=999)),
            (Team.ENEMY, (6, 6), no_reactions()),
            (Team.ALLY, (0, 3), no_reactions("hero_archer")),
        ],
        turn=U3,
    )
    result = resolve(state, walk((0, 3), (1, 3), (2, 3), unit=U3))
    assert not reactions(result)


def test_forced_movement_next_to_the_owner_does_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """強制位移不算「主動移動」：隊友的鉤索箭把敵人拉到持有者旁邊。"""
    always(monkeypatch)
    state = world(
        [
            (Team.ALLY, (2, 3), caster_template([AMBUSH], base="hero_fighter", max_hp=999)),
            (Team.ENEMY, (4, 2), no_reactions("bandit", max_hp=999)),
            (Team.ALLY, (1, 2), caster_template([GRAPPLE], base="hero_archer", max_hp=999)),
        ],
        turn=U3,
    )
    pull = resolve(state, UseSkill(unit_id=U3, skill_id=GRAPPLE, target_id=U2))
    landed = pull.state.units[U2]
    assert (landed.pos.x, landed.pos.y) == (2, 2)  # 被拉到持有者 (2, 3) 的旁邊
    assert not reactions(pull)


def test_a_dash_into_the_owners_reach_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    """衝鋒（``dash``）是主動移動：敵人衝到持有者的友方旁邊、也就進入持有者的相鄰格時觸發。"""
    always(monkeypatch)
    state = world(
        [
            (Team.ALLY, (4, 3), caster_template([AMBUSH], base="hero_fighter", max_hp=999)),
            (
                Team.ENEMY,
                (6, 3),
                caster_template(["skill_tiger_charge"], base="hero_fighter", max_hp=999),
            ),
            (Team.ALLY, (3, 2), no_reactions("hero_archer", max_hp=999)),
        ]
    )
    charge = resolve(state, UseSkill(unit_id=U2, skill_id="skill_tiger_charge", target_id=U3))
    assert [r.trigger_unit_id for r in reactions(charge)] == [U2]


def test_enemy_enters_adjacent_is_asked_in_prompt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = ambush_world()
    owner = state.units[U1]
    owner.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in owner.reactions)
    paused = resolve(state, walk((6, 3), (5, 3), (4, 3)))
    assert paused.pending is not None
    assert (paused.pending.unit_id, paused.pending.skill_id) == (U1, AMBUSH)
    assert paused.pending.trigger_unit_id == U2
    seq = paused.pending.trigger_event_seq
    assert seq is not None and isinstance(next(e for e in paused.events if e.seq == seq), UnitMoved)
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert reactions(accepted)
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert of(declined, ReactionDeclined) and not reactions(declined)
    # 拒絕後敵人照常走完
    assert (declined.state.units[U2].pos.x, declined.state.units[U2].pos.y) == (4, 3)


# ---------------------------------------------------------------------------
# ally_targeted
# ---------------------------------------------------------------------------


def targeted_world(
    *, foe_at: tuple[int, int] = (6, 3), ally_at: tuple[int, int] = (4, 3), foe_hp: int = 999
) -> BattleState:
    """U1 持有掩護射擊（弓手 (3, 3)）；U3（隊友戰士）在 ``ally_at``；U2（敵人）在 ``foe_at``。"""
    return world(
        [
            (Team.ALLY, (3, 3), caster_template([COVERING_FIRE], base="hero_archer", max_hp=999)),
            (Team.ENEMY, foe_at, no_reactions("bandit_archer", max_hp=foe_hp)),
            (Team.ALLY, ally_at, no_reactions("hero_fighter", max_hp=999)),
        ]
    )


def test_ally_targeted_fires_before_the_attack_is_rolled(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(targeted_world(), Attack(unit_id=U2, target_id=U3))
    (trig,) = reactions(result)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U1, COVERING_FIRE, U2)
    reacted = index_of(result.events, ReactionTriggered)
    assert reacted < index_of(result.events, AttackRolled, attacker_id=U2, target_id=U3)
    first_roll = of(result, AttackRolled)[0]
    assert (first_roll.attacker_id, first_roll.target_id) == (U1, U2)  # 先是反應的射擊


def test_ally_targeted_also_fires_for_a_single_target_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = world(
        [
            (Team.ALLY, (3, 3), caster_template([COVERING_FIRE], base="hero_archer", max_hp=999)),
            (Team.ENEMY, (6, 3), caster_template([FIRE_BOLT], base="hero_mage", max_hp=999)),
            (Team.ALLY, (4, 3), no_reactions("hero_fighter", max_hp=999)),
        ]
    )
    result = resolve(state, UseSkill(unit_id=U2, skill_id=FIRE_BOLT, target_id=U3))
    assert [r.reaction for r in reactions(result)] == [COVERING_FIRE]
    assert index_of(result.events, ReactionTriggered) < index_of(
        result.events, AttackRolled, attacker_id=U2
    )


def test_ally_targeted_needs_the_target_next_to_the_owner_and_not_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    far = resolve(targeted_world(ally_at=(5, 3), foe_at=(6, 3)), Attack(unit_id=U2, target_id=U3))
    assert not reactions(far)  # 被瞄準的隊友離持有者 2 格
    self_target = resolve(targeted_world(), Attack(unit_id=U2, target_id=U1))
    assert not reactions(self_target)  # 被瞄準的是持有者自己：那是 hit_by_*，不是 ally_targeted


def test_ally_targeted_ignores_area_skills_and_enemy_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    blast = SkillDef.model_validate(
        {
            "id": "skill_t_area_hit",
            "name_zh": "測試範圍術",
            "tier": 1,
            "rarity": "common",
            "skeleton": "area",
            "category": "spell",
            "weapon_req": "focus",
            "ap_cost": 1,
            "scaling_attr": "int",
            "shape": {"type": "square3", "range": 6},
            "effects": [{"type": "damage", "dice": "1d6", "element": "fire"}],
            "cost": {"mana": 0},
        }
    )
    state = world(
        [
            (Team.ALLY, (3, 3), caster_template([COVERING_FIRE], base="hero_archer", max_hp=999)),
            (Team.ENEMY, (6, 3), caster_template([blast], base="hero_mage", max_hp=999)),
            (Team.ALLY, (4, 3), no_reactions("hero_fighter", max_hp=999)),
        ],
        skills=[blast],
    )
    action = next(
        a
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.skill_id == blast.id and a.target_pos == Pos(x=4, y=3)
    )
    assert not reactions(resolve(state, action))  # 範圍技沒有「選為目標」的單位
    # 敵人（不是友方）被我方瞄準：持有者的敵人不反應
    own_turn = give_turn(targeted_world(), U1)
    shot = resolve(own_turn, Attack(unit_id=U1, target_id=U2))
    assert not [r for r in reactions(shot) if r.reaction == COVERING_FIRE]


def test_ally_targeted_that_downs_the_attacker_cancels_his_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, die=6)
    result = resolve(targeted_world(foe_hp=1), Attack(unit_id=U2, target_id=U3))
    assert of(result, UnitDowned)
    assert not [r for r in of(result, AttackRolled) if r.attacker_id == U2]  # 攻擊者沒機會出手


def test_ally_targeted_is_asked_in_prompt_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = targeted_world()
    owner = state.units[U1]
    owner.reactions = tuple(r.model_copy(update={"mode": "prompt"}) for r in owner.reactions)
    paused = resolve(state, Attack(unit_id=U2, target_id=U3))
    assert paused.pending is not None
    assert (paused.pending.unit_id, paused.pending.skill_id) == (U1, COVERING_FIRE)
    assert paused.pending.trigger_unit_id == U2
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert of(declined, ReactionDeclined)
    assert [r.attacker_id for r in of(declined, AttackRolled)] == [U2]  # 拒絕後攻擊照常進行
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert [r.attacker_id for r in of(accepted, AttackRolled)][:2] == [U1, U2]


# ---------------------------------------------------------------------------
# 預覽與重播
# ---------------------------------------------------------------------------


def test_previews_include_the_new_reactions() -> None:
    for state, action in (
        (spell_duel(), UseSkill(unit_id=U2, skill_id=FIRE_BOLT, target_id=U1)),
        (ambush_world(), walk((6, 3), (5, 3), (4, 3))),
        (targeted_world(), Attack(unit_id=U2, target_id=U3)),
        (downed_world(), Attack(unit_id=U2, target_id=U3)),
    ):
        pv = preview(state, action)
        assert any(isinstance(e, ReactionTriggered) for e in pv.max_events), action


@pytest.mark.parametrize(
    ("build", "map_id", "seed", "reaction"),
    [
        ("build_assassin", "open_plain", 1, "迎頭痛擊"),
        ("build_tank", "swamp", 0, "悲憤"),
        ("build_ranged", "narrow_halls", 0, "掩護射擊"),
    ],
)
def test_ai_battles_with_the_new_reactions_replay(
    build: str,
    map_id: str,
    seed: int,
    reaction: str,
    *,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AI 打整場：新反應被觸發，戰鬥紀錄重播一致（反應技的觸發與結算都是確定性的）。"""
    log = tmp_path / "reaction.json"
    argv = ["battle", "--map", map_id, "--seed", str(seed), "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    assert f"反應：「{reaction}」" in capsys.readouterr().out
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()
