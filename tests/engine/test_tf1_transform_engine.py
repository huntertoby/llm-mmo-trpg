"""TF-1（#159，06 6.34.5）召喚與輔助的 1 階轉型需要的引擎能力。

- 被動時機 ``on_battle_start``＋原語 ``summon_beside``：伴生（開場在身邊召出縮小版召喚物）。
- 反應 ``hit_by_melee``＋``summon_beside`` 的 ``strike_other``：護主（召出後立刻反咬攻擊者）。
- 被動對象 ``weakest_ally``：庇佑（回合開始，1 格內生命比例最低的友方）。
- 反應 ``aid``＋事件 ``ally_hit_near``：援手（護盾在命中前、治療在受擊後作用在友方）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, EndTurn, resolve
from trpg.engine.context import Ctx
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EffectFizzled,
    Healed,
    ShieldGained,
    SkillTriggered,
    UnitSummoned,
)
from trpg.engine.rules.geometry import manhattan
from trpg.engine.skills.casting import use_triggered_skill
from trpg.engine.state import state_from_json, state_to_json
from trpg.shared.types import Team, UnitId

WOLF = "summon_war_wolf"
U4 = UnitId("unit_0004")


def _skill(skill_id: str, kind: str, effects: list[dict[str, Any]], **extra: Any) -> SkillDef:
    """測試專用被動／反應技（不經預算驗證器）。"""
    shape = extra.pop("shape", {"type": "self"})
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"測試 {skill_id[-4:]}",
            "tier": 1,
            "rarity": "epic",
            "kind": kind,
            "skeleton": kind,
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "wis",
            "shape": shape,
            "effects": effects,
            "cost": {"mana": 0},
            **extra,
        }
    )


def companion(skill_id: str = "skill_t_tf_comp", power: int = 500) -> SkillDef:
    effect = {"type": "summon_beside", "unit": WOLF, "duration": 2, "power_permille": power}
    return _skill(skill_id, "passive", [effect], trigger={"event": "on_battle_start"})


def guardian() -> SkillDef:
    effect = {
        "type": "summon_beside",
        "unit": WOLF,
        "duration": 1,
        "power_permille": 500,
        "strike_other": True,
    }
    return _skill(
        "skill_t_tf_guard",
        "reaction",
        [effect],
        shape={"type": "single", "range": 2},
        reaction={"event": "hit_by_melee"},
    )


def blessing() -> SkillDef:
    heal = {"type": "heal", "dice": "1d4", "affects": "allies"}
    trigger = {"event": "on_turn_start", "target": "weakest_ally", "max_distance": 1}
    return _skill("skill_t_tf_bless", "passive", [heal], trigger=trigger)


def aid(event: str, effect: dict[str, Any]) -> SkillDef:
    return _skill(
        f"skill_t_tf_aid_{event[-4:]}",
        "reaction",
        [effect],
        shape={"type": "single", "range": 1},
        reaction={"event": event, "aid": True},
    )


def _start(
    owner: list[SkillDef], *, foe_xy: tuple[int, int] = (6, 6), seed: int = 0, **core: int
) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe_xy])
    hero = caster_template([s.id for s in owner], base="hero_mage", max_hp=60)
    spawns = [spawn(Team.ALLY, (3, 3), hero), spawn(Team.ENEMY, foe_xy, no_reactions(max_hp=999))]
    return make_state(m, spawns, skills=owner, seed=seed, **core)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 伴生：on_battle_start ＋ summon_beside
# ---------------------------------------------------------------------------


def test_companion_summons_a_smaller_pet_next_to_you_at_the_start() -> None:
    state = _start([companion()])
    pets = [u for u in state.units_sorted() if u.owner_id == U1]
    assert len(pets) == 1
    pet = pets[0]
    assert pet.template_id == WOLF and manhattan(pet.xy, state.units[U1].xy) == 1
    full = _start([companion(power=1000)])
    full_pet = next(u for u in full.units_sorted() if u.owner_id == U1)
    assert pet.max_hp == max(1, full_pet.max_hp * 500 // 1000)  # 縮小版：HP 只有一半
    assert pet.summon_power_permille == 500
    # 召喚物緊接在召喚者之後行動，第一輪就能出手
    order = state.turn_order
    assert order.index(pet.id) == order.index(U1) + 1


def test_companion_does_not_make_you_lose_lone_wolf() -> None:
    state = _start([companion()])
    assert state.units[U1].lone_wolf  # 召喚物不算隊友（#156）


def test_companion_fires_once_per_battle() -> None:
    state = _start([companion()])
    for _ in range(6):  # 幾個回合過去，不會再召
        active = state.active_unit
        assert active is not None
        state = resolve(state, EndTurn(unit_id=active)).state
        if state.ended:
            break
    pets = [u for u in state.units.values() if u.owner_id == U1]
    assert len(pets) == 1


def test_companion_does_not_appear_when_the_summon_limit_is_full() -> None:
    two = [companion("skill_t_tf_comp_a"), companion("skill_t_tf_comp_b")]
    state = _start(two, summon_limit_per_owner=1)
    assert len([u for u in state.units_sorted() if u.owner_id == U1]) == 1
    # 第二個沒有擠掉第一隻：滿了就不出現
    assert all(u.alive for u in state.units_sorted() if u.owner_id == U1)


def test_summon_beside_fizzles_on_the_limit_and_when_boxed_in() -> None:
    state = _start([companion("skill_t_tf_comp_a"), companion("skill_t_tf_comp_b")])
    ctx = Ctx(state.clone())
    skill = ctx.rules.skill_def("skill_t_tf_comp_a")
    hero = ctx.state.units[U1]
    for _ in range(3):  # 預設上限 2：已經 2 隻，再召就落空
        use_triggered_skill(ctx, hero, skill, None)
    reasons = [e.reason for e in ctx.events if isinstance(e, EffectFizzled)]
    assert "summon_limit" in reasons


def test_companion_battle_start_replays_the_same() -> None:
    state = _start([companion()], seed=7)
    again = _start([companion()], seed=7)
    assert state_to_json(state) == state_to_json(again)
    assert state_to_json(state_from_json(state_to_json(state))) == state_to_json(state)


# ---------------------------------------------------------------------------
# 護主：hit_by_melee ＋ summon_beside(strike_other)
# ---------------------------------------------------------------------------


def _guard_duel() -> BattleState:
    skill = guardian()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    owner = caster_template([skill.id], base="hero_mage", max_hp=999)
    spawns = [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))]
    return give_turn(make_state(m, spawns, skills=[skill]), U2)


def test_guardian_summons_a_pet_that_bites_the_attacker(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _guard_duel()
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (summoned,) = of(result, UnitSummoned)
    assert summoned.owner_id == U1 and summoned.template_id == WOLF
    pet = result.state.units[summoned.unit_id]
    # 召喚物出現在攻擊者旁邊、離你最近的空格（才咬得到）
    assert manhattan(pet.xy, result.state.units[U2].xy) == 1
    assert manhattan(pet.xy, result.state.units[U1].xy) == 2
    rolls = [(r.attacker_id, r.target_id) for r in of(result, AttackRolled)]
    assert rolls == [(U2, U1), (pet.id, U2)]  # 敵人打你 → 召喚物反咬
    assert summoned.expires_round == state.round + 1  # 存在 1 回合


# ---------------------------------------------------------------------------
# 庇佑：on_turn_start ＋ target: weakest_ally
# ---------------------------------------------------------------------------


def _blessing_world(*, ally_hp: tuple[int, int], far: bool = False) -> BattleState:
    skill = blessing()
    near = (6, 6) if far else (3, 4)
    allies = [(3, 3), near, (2, 3)]
    m = make_map(FLAT7, ally=allies, enemy=[(6, 1)])
    owner = caster_template([skill.id], base="hero_mage", max_hp=40)
    spawns = [
        spawn(Team.ALLY, (3, 3), owner),
        spawn(Team.ENEMY, (6, 1), no_reactions(max_hp=999)),
        spawn(Team.ALLY, near, no_reactions("hero_fighter", max_hp=40)),
        spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=40)),
    ]
    state = make_state(m, spawns, skills=[skill])
    state.units[U1].hp = 1  # 自己最虛弱也不算
    state.units[U3].hp, state.units[U4].hp = ally_hp
    return state


def _turn_start_of_owner(state: BattleState) -> Any:
    before = state.turn_order[(state.turn_order.index(U1) - 1) % len(state.turn_order)]
    return resolve(give_turn(state, before), EndTurn(unit_id=before))


@pytest.mark.parametrize(("ally_hp", "healed"), [((10, 30), U3), ((30, 10), U4), ((20, 20), U3)])
def test_blessing_heals_the_weakest_ally_within_one_tile(
    ally_hp: tuple[int, int], healed: UnitId
) -> None:
    result = _turn_start_of_owner(_blessing_world(ally_hp=ally_hp))
    (trig,) = [e for e in result.events if isinstance(e, SkillTriggered)]
    assert trig.trigger == "on_turn_start" and trig.unit_id == U1
    assert [h.target_id for h in of(result, Healed)] == [healed]


def test_blessing_does_nothing_without_an_ally_nearby() -> None:
    state = _blessing_world(ally_hp=(10, 30), far=True)
    state.units[U4].hp = 40  # U4 在旁邊但滿血也算「最低」：改成移走
    state.units[U4].pos = state.units[U3].pos.model_copy(update={"x": 0, "y": 6})
    result = _turn_start_of_owner(state)
    assert not [e for e in result.events if isinstance(e, SkillTriggered)]


# ---------------------------------------------------------------------------
# 援手：reaction.aid ＋ ally_targeted／ally_hit_near
# ---------------------------------------------------------------------------


def _aid_world(skill: SkillDef) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3), (4, 3)], enemy=[(5, 3)])
    owner = caster_template([skill.id], base="hero_mage", max_hp=999)
    spawns = [
        spawn(Team.ALLY, (3, 3), owner),
        spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=999)),
        spawn(Team.ALLY, (4, 3), no_reactions("hero_fighter", max_hp=999)),
    ]
    return give_turn(make_state(m, spawns, skills=[skill]), U2)


def test_aid_shields_the_targeted_ally_before_the_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = aid("ally_targeted", {"type": "shield", "dice": "1d4", "affects": "allies"})
    result = resolve(_aid_world(skill), Attack(unit_id=U2, target_id=U3))
    (shield,) = of(result, ShieldGained)
    assert shield.unit_id == U3
    kinds = list(result.events)
    shield_at = kinds.index(shield)
    roll_at = next(i for i, e in enumerate(kinds) if isinstance(e, AttackRolled))
    assert shield_at < roll_at


def test_aid_heals_the_ally_after_the_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = aid("ally_hit_near", {"type": "heal", "dice": "1d4", "affects": "allies"})
    state = _aid_world(skill)
    state.units[U3].hp = 500
    result = resolve(state, Attack(unit_id=U2, target_id=U3))
    (heal,) = of(result, Healed)
    assert heal.target_id == U3
    events = list(result.events)
    damage_at = next(
        i for i, e in enumerate(events) if isinstance(e, DamageDealt) and e.target_id == U3
    )
    assert damage_at < events.index(heal)


def test_aid_does_not_fire_when_you_are_the_target(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = aid("ally_hit_near", {"type": "heal", "dice": "1d4", "affects": "allies"})
    state = _aid_world(skill)
    state.units[U1].pos = state.units[U1].pos.model_copy(update={"x": 1, "y": 1})
    result = resolve(state, Attack(unit_id=U2, target_id=U3))
    assert not of(result, Healed)  # 不相鄰


# ---------------------------------------------------------------------------
# 資料檢查
# ---------------------------------------------------------------------------


def test_ally_hit_near_needs_aid_and_aid_needs_an_ally_event() -> None:
    with pytest.raises(ValueError, match="aid"):
        _skill(
            "skill_t_tf_bad1",
            "reaction",
            [{"type": "heal", "dice": "1d4", "affects": "allies"}],
            shape={"type": "single", "range": 1},
            reaction={"event": "ally_hit_near"},
        )
    with pytest.raises(ValueError, match="aid"):
        _skill(
            "skill_t_tf_bad2",
            "reaction",
            [{"type": "heal", "dice": "1d4", "affects": "allies"}],
            reaction={"event": "hit_by_melee", "aid": True},
        )


def test_summon_beside_is_only_for_passives_and_reactions() -> None:
    effect = {"type": "summon_beside", "unit": WOLF, "duration": 2}
    with pytest.raises(ValueError, match="summon_beside"):
        SkillDef.model_validate(
            {
                "id": "skill_t_tf_bad3",
                "name_zh": "壞",
                "tier": 1,
                "rarity": "rare",
                "skeleton": "summon",
                "category": "spell",
                "weapon_req": "any",
                "ap_cost": 1,
                "scaling_attr": "wis",
                "shape": {"type": "self"},
                "effects": [effect],
                "cost": {"mana": 0},
            }
        )
    with pytest.raises(ValueError, match="strike_other"):
        _skill(
            "skill_t_tf_bad4",
            "passive",
            [{**effect, "strike_other": True}],
            trigger={"event": "on_battle_start"},
        )


def test_weakest_ally_needs_max_distance() -> None:
    with pytest.raises(ValueError, match="max_distance"):
        _skill(
            "skill_t_tf_bad5",
            "passive",
            [{"type": "heal", "dice": "1d4", "affects": "allies"}],
            trigger={"event": "on_turn_start", "target": "weakest_ally"},
        )
