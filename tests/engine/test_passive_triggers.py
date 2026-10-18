"""Phase 2E-1 3.9：被動技能的觸發（觸發時機、次數限制、深度上限、狀態限制、條件、預覽與重播）。"""

from __future__ import annotations

from collections.abc import Sequence
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
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, EndTurn, Move, UseSkill, preview, resolve
from trpg.engine.effects import PushEffect, run_effects
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    Healed,
    SkillTriggered,
    StatusApplied,
    TriggerLimitReached,
    TurnEnded,
    TurnStarted,
    UnitMoved,
)
from trpg.engine.state import StatusInstance
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

_DAMAGE = {"type": "damage", "dice": "1d4", "element": "physical", "affects": "enemies"}
_HEAL_SELF = {"type": "heal", "dice": "1d4", "affects": "self"}


def passive(
    skill_id: str,
    event: str,
    *,
    target: str = "other",
    effects: Sequence[dict[str, Any]] | None = None,
    n: int | None = None,
    max_per_round: int = 1,
    max_distance: int | None = None,
    cost: dict[str, Any] | None = None,
    condition: dict[str, Any] | None = None,
) -> SkillDef:
    """測試專用被動技能（不經驗證器，不放在 ``content/``）。"""
    spec: dict[str, Any] = {"event": event, "target": target, "max_per_round": max_per_round}
    if n is not None:
        spec["n"] = n
    if max_distance is not None:
        spec["max_distance"] = max_distance
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"被動 {skill_id[-4:]}",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": list(effects or ([_DAMAGE] if target == "other" else [_HEAL_SELF])),
            "condition": condition,
            "trigger": spec,
            "cost": cost or {"mana": 0},
        }
    )


def scene(
    owner: Sequence[SkillDef | str],
    foe: Sequence[SkillDef | str] = (),
    *,
    owner_xy: tuple[int, int] = (3, 3),
    foe_xy: tuple[int, int] = (4, 3),
    foe_hp: int | None = 999,
    owner_hp: int | None = 999,
    foe_base: str = "bandit",
    owner_base: str = "hero_fighter",
) -> BattleState:
    """U1（我方戰士）與 U2（敵人）；U1 拿到回合。兩邊的 HP 預設很高，避免被打倒。"""
    defs = list({s.id: s for s in (*owner, *foe) if isinstance(s, SkillDef)}.values())
    m = make_map(FLAT7, ally=[owner_xy], enemy=[foe_xy])
    fighter = caster_template(owner, base=owner_base, max_hp=owner_hp or 60)
    enemy = no_reactions(
        foe_base, max_mana=99, skills=[s if isinstance(s, str) else s.id for s in foe]
    )
    if foe_hp is not None:
        enemy = enemy.model_copy(update={"max_hp": foe_hp})
    state = make_state(
        m, [spawn(Team.ALLY, owner_xy, fighter), spawn(Team.ENEMY, foe_xy, enemy)], skills=defs
    )
    return give_turn(state, U1)


def always(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 1) -> None:
    """d20 一律 ``d20``、其他骰子一律 ``die``（命中、不暴擊，傷害最小）。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def triggered(events: Sequence[EventBase]) -> list[SkillTriggered]:
    return [e for e in events if isinstance(e, SkillTriggered)]


def attack(state: BattleState, unit: UnitId = U1, target: UnitId = U2) -> Any:
    return resolve(state, Attack(unit_id=unit, target_id=target))


def renew(state: BattleState, unit: str = U1) -> BattleState:
    return give_turn(state, unit)


# ---------------------------------------------------------------------------
# 觸發時機（3.9 第 1 項）
# ---------------------------------------------------------------------------


def test_on_hit_triggers_after_the_damage_and_targets_the_unit_that_was_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = attack(scene([passive("skill_t_hit", "on_hit")]))
    fired = triggered(result.events)
    assert [(e.unit_id, e.trigger, e.other_id, e.trigger_depth) for e in fired] == [
        (U1, "on_hit", U2, 1)
    ]
    damages = of(result, DamageDealt)
    assert [(d.source_id, d.target_id) for d in damages] == [(U1, U2), (U1, U2)]
    order = [type(e) for e in result.events]
    assert order.index(DamageDealt) < order.index(SkillTriggered)  # 傷害結算之後


def test_on_hit_does_not_trigger_on_a_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=1)
    result = attack(scene([passive("skill_t_hit", "on_hit")]))
    assert not triggered(result.events)


def test_on_crit_only_triggers_on_a_critical_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = passive("skill_t_crit", "on_crit")
    always(monkeypatch, d20=19)
    assert not triggered(attack(scene([skill])).events)
    always(monkeypatch, d20=20)
    fired = triggered(attack(scene([skill])).events)
    assert [e.trigger for e in fired] == ["on_crit"]


def test_on_natural_20_triggers_on_a_natural_20_but_not_on_a_19(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = passive("skill_t_n20", "on_natural_20")
    always(monkeypatch, d20=19)
    assert not triggered(attack(scene([skill])).events)
    always(monkeypatch, d20=20)
    fired = triggered(attack(scene([skill])).events)
    assert [(e.trigger, e.other_id) for e in fired] == [("on_natural_20", U2)]


def test_on_kill_triggers_when_the_holders_damage_downs_a_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = passive("skill_t_kill", "on_kill", target="self")
    healthy = attack(scene([skill], foe_hp=999))
    assert not triggered(healthy.events)
    state = scene([skill], foe_hp=1)
    state.units[U1].hp = 10
    result = attack(state)
    assert [(e.trigger, e.other_id) for e in triggered(result.events)] == [("on_kill", U2)]
    assert [h.target_id for h in of(result, Healed)] == [U1]


def test_on_kill_with_target_other_has_no_effect_on_the_fallen_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_kill", "on_kill")], foe_hp=1)
    result = attack(state)
    assert [e.trigger for e in triggered(result.events)] == ["on_kill"]
    assert len(of(result, DamageDealt)) == 1  # 只有擊倒的那一下


def test_on_damaged_triggers_for_the_unit_that_was_hurt_and_targets_the_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_dmg", "on_damaged")])
    result = attack(give_turn(state, U2), U2, U1)
    fired = triggered(result.events)
    assert [(e.unit_id, e.other_id) for e in fired] == [(U1, U2)]
    assert [(d.source_id, d.target_id) for d in of(result, DamageDealt)] == [(U2, U1), (U1, U2)]


def test_on_damaged_also_triggers_for_damage_without_a_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = passive("skill_t_dmg", "on_damaged", target="self")
    state = scene([skill])
    state.units[U1].hp = 10
    from trpg.engine.effects import DamageEffect  # noqa: PLC0415

    result = run_effects(state, [DamageEffect(target_id=U1, cause="effect", flat=3, min_damage=1)])
    assert [e.trigger for e in triggered(result.events)] == ["on_damaged"]


def test_on_damaged_does_not_trigger_when_that_damage_downs_the_holder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_dmg", "on_damaged")], owner_hp=1)
    state.units[U1].hp = 1
    result = attack(give_turn(state, U2), U2, U1)
    assert not triggered(result.events)


def test_on_turn_start_triggers_after_the_turn_start_effects() -> None:
    skill = passive("skill_t_ts", "on_turn_start", target="self")
    state = scene([skill])
    state.units[U1].hp = 10
    state.units[U1].statuses = [StatusInstance("poison", 2, U2)]
    result = resolve(give_turn(state, U2), EndTurn(unit_id=U2))
    kinds = [type(e) for e in result.events]
    assert kinds.index(TurnStarted) < kinds.index(DamageDealt) < kinds.index(SkillTriggered)
    assert [e.trigger for e in triggered(result.events)] == ["on_turn_start"]


def test_on_turn_end_triggers_before_the_turn_ends() -> None:
    skill = passive("skill_t_te", "on_turn_end", target="self")
    state = scene([skill])
    state.units[U1].hp = 10
    result = resolve(state, EndTurn(unit_id=U1))
    kinds = [type(e) for e in result.events]
    assert kinds.index(SkillTriggered) < kinds.index(TurnEnded)
    assert [e.trigger for e in triggered(result.events)] == ["on_turn_end"]


def test_on_move_triggers_once_per_move_action_not_per_step_and_not_on_forced_moves() -> None:
    skill = passive("skill_t_mv", "on_move", target="self")
    state = scene([skill], owner_xy=(1, 3), foe_xy=(6, 6))
    state.units[U1].hp = 10
    path = tuple(Pos(x=x, y=3) for x in (1, 2, 3))
    result = resolve(state, Move(unit_id=U1, path=path))
    assert len(of(result, UnitMoved)) == 2
    kinds = [type(e) for e in result.events]
    assert [e.trigger for e in triggered(result.events)] == ["on_move"]
    assert kinds.index(SkillTriggered) > max(i for i, k in enumerate(kinds) if k is UnitMoved)
    forced = run_effects(
        state, [PushEffect(source_id=U2, target_id=U1, direction=(1, 0), distance=1)]
    )
    assert not triggered(forced.events)


def test_every_n_hits_triggers_on_the_second_and_fourth_hit_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_n", "every_n_hits", n=2, max_per_round=3)])
    fired_on_hit: list[bool] = []
    for _ in range(4):
        result = attack(renew(state))
        state = result.state
        fired_on_hit.append(bool(triggered(result.events)))
    assert fired_on_hit == [False, True, False, True]


def test_every_n_hits_counts_only_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene([passive("skill_t_n", "every_n_hits", n=2, max_per_round=3)])
    always(monkeypatch, d20=1)
    state = attack(renew(state)).state  # 失手不計
    always(monkeypatch)
    assert not triggered((result := attack(renew(state))).events)  # 第 1 次命中
    assert triggered(attack(renew(result.state)).events)  # 第 2 次命中


# ---------------------------------------------------------------------------
# 次數限制（第 2 項）與深度上限（第 3、4 項）
# ---------------------------------------------------------------------------


def test_max_per_round_limits_triggers_and_resets_each_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_hit", "on_hit", max_per_round=1)])
    first = attack(state)
    second = attack(first.state)
    assert len(triggered(first.events)) == 1 and not triggered(second.events)
    after_turn = resolve(second.state, EndTurn(unit_id=U1)).state  # U2 的回合
    new_round = resolve(after_turn, EndTurn(unit_id=U2)).state
    assert new_round.round == 2 and new_round.active_unit == U1
    assert new_round.units[U1].trigger_counts == {}
    assert len(triggered(attack(new_round).events)) == 1


def test_max_per_round_two_allows_two_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene([passive("skill_t_hit", "on_hit", max_per_round=2)])
    first = attack(state)
    second = attack(first.state)
    third = attack(second.state)
    assert [len(triggered(r.events)) for r in (first, second, third)] == [1, 1, 0]


def test_trigger_chains_stop_at_depth_three_with_a_limit_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    echo = passive("skill_t_echo", "on_damaged", max_per_round=3)
    result = attack(scene([echo], [echo]))
    assert [(e.unit_id, e.trigger_depth) for e in triggered(result.events)] == [
        (U2, 1),
        (U1, 2),
        (U2, 3),
    ]
    limits = of(result, TriggerLimitReached)
    assert [(e.unit_id, e.depth) for e in limits] == [(U1, 4)]
    assert result.state.active_unit == U1  # 結算正常結束，回合沒有被打斷


def test_a_limited_trigger_does_not_spend_its_use(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    echo = passive("skill_t_echo", "on_damaged", max_per_round=3)
    result = attack(scene([echo], [echo]))
    assert result.state.units[U1].trigger_counts == {"skill_t_echo": 1}
    assert result.state.units[U2].trigger_counts == {"skill_t_echo": 2}


# ---------------------------------------------------------------------------
# 持有者狀態與代價（第 5 項）
# ---------------------------------------------------------------------------


def _hit_scene(**costs: Any) -> BattleState:
    return scene([passive("skill_t_hit", "on_hit", cost=costs or None)])


def test_a_silenced_stunned_or_dead_holder_does_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    assert triggered(attack(_hit_scene()).events)
    silenced = _hit_scene()
    silenced.units[U1].statuses = [StatusInstance("silenced", 2, U2)]
    assert not triggered(attack(silenced).events)
    stunned = _hit_scene()
    stunned.units[U1].statuses = [StatusInstance("stun", 1, U2)]
    assert not triggered(attack(stunned).events)


def test_a_holder_downed_by_the_same_attack_does_not_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(
        [passive("skill_t_hit", "on_hit", target="self")],
        [passive("skill_t_foe", "on_damaged")],
        foe_hp=1,
    )
    result = attack(state)
    assert [e.unit_id for e in triggered(result.events)] == [U1]  # U2 倒下，不觸發


def test_not_enough_mana_means_no_trigger_and_triggering_pays_the_mana(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    poor = _hit_scene(mana=5)
    poor.units[U1].mana = 4
    assert not triggered(attack(poor).events)
    rich = _hit_scene(mana=5)
    rich.units[U1].mana = 7
    result = attack(rich)
    assert triggered(result.events)[0].mana_after == 2 and result.state.units[U1].mana == 2


def test_cooldown_blocks_the_next_trigger_until_it_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(
        [passive("skill_t_hit", "on_hit", max_per_round=3, cost={"mana": 0, "cooldown": 2})]
    )
    first = attack(state)
    assert triggered(first.events) and first.state.units[U1].cooldowns == {"skill_t_hit": 2}
    assert not triggered(attack(first.state).events)  # 冷卻中


# ---------------------------------------------------------------------------
# 條件與距離（第 6 項）
# ---------------------------------------------------------------------------


def _armed(
    *skill_ids: str, foe_marked: bool = False, foe_xy: tuple[int, int] = (4, 3)
) -> BattleState:
    state = scene(list(skill_ids), foe_xy=foe_xy)
    if foe_marked:
        state.units[U2].statuses = [StatusInstance("marked", 2, U1)]
    return state


def test_mark_detonation_uses_the_condition_on_the_unit_that_was_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    plain = attack(_armed("skill_mark_detonation"))
    assert not triggered(plain.events)
    marked = attack(_armed("skill_mark_detonation", foe_marked=True))
    assert [(e.skill_id, e.other_id) for e in triggered(marked.events)] == [
        ("skill_mark_detonation", U2)
    ]
    detonation = [d for d in of(marked, DamageDealt) if d.element.value == "shadow"]
    assert len(detonation) == 1 and detonation[0].source_id == U1


def test_thorn_skin_only_answers_attackers_within_its_max_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    near = scene(["skill_thorn_skin"], foe_xy=(4, 3))
    result = attack(give_turn(near, U2), U2, U1)
    assert [e.skill_id for e in triggered(result.events)] == ["skill_thorn_skin"]
    far = scene(["skill_thorn_skin"], foe_xy=(5, 3), foe_base="bandit_archer")
    result = attack(give_turn(far, U2), U2, U1)
    assert not triggered(result.events)  # 遠程攻擊者在 2 格外


def test_second_wind_needs_the_holder_to_be_below_half_hp() -> None:
    state = scene(["skill_second_wind"])
    healthy = resolve(give_turn(state, U2), EndTurn(unit_id=U2))
    assert not triggered(healthy.events)
    state.units[U1].hp = 20
    hurt = resolve(give_turn(state, U2), EndTurn(unit_id=U2))
    assert [e.skill_id for e in triggered(hurt.events)] == ["skill_second_wind"]


def test_ember_brand_burns_the_unit_that_was_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = attack(_armed("skill_ember_brand"))
    applied = of(result, StatusApplied)
    assert [(a.target_id, a.status_id, a.source_id) for a in applied] == [(U2, "burning", U1)]


# ---------------------------------------------------------------------------
# 預覽（第 7 項）
# ---------------------------------------------------------------------------


def test_preview_includes_the_triggered_status_and_matches_the_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _armed("skill_ember_brand")
    action = Attack(unit_id=U1, target_id=U2)
    shown = preview(state, action)
    assert any(o.kind == "status" and o.detail == "burning" for o in shown.certain)
    always(monkeypatch)  # 命中、不暴擊、傷害骰最小 ＝ 預覽的 min
    actual = resolve(state, action)

    def summary(events: Sequence[EventBase]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for e in events:
            if isinstance(e, DamageDealt):
                out.append((e.type, f"{e.source_id}>{e.target_id}:{e.amount}"))
            elif isinstance(e, SkillTriggered | StatusApplied):
                out.append((e.type, e.model_dump_json(exclude={"seq"})))
        return out

    assert summary(shown.min_events) == summary(actual.events)
    assert shown.min_state.units[U2].hp == actual.state.units[U2].hp


def test_preview_does_not_change_the_state_or_consume_trigger_counts() -> None:
    state = _armed("skill_ember_brand")
    before = state.units[U1].trigger_counts.copy()
    preview(state, Attack(unit_id=U1, target_id=U2))
    assert state.units[U1].trigger_counts == before and state.units[U1].mana == 99


# ---------------------------------------------------------------------------
# 技能施放也會觸發
# ---------------------------------------------------------------------------


def test_skills_that_hit_also_trigger_on_hit_after_the_whole_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    bolt = "skill_hex_bolt"  # 傷害＋標記
    state = scene([bolt, "skill_mark_detonation"], foe_xy=(5, 3), owner_base="hero_mage")
    result = resolve(state, UseSkill(unit_id=U1, skill_id=bolt, target_id=U2))
    # 咒印飛彈的標記在整個技能結算完之後才輪到「標記引爆」，所以第一次施放就引爆
    assert [e.skill_id for e in triggered(result.events)] == ["skill_mark_detonation"]
    kinds = [type(e) for e in result.events]
    assert kinds.index(SkillTriggered) > max(i for i, k in enumerate(kinds) if k is StatusApplied)


def test_library_passives_are_valid_epic_passive_skills() -> None:
    lib = library()
    for sid in (
        "skill_ember_brand",
        "skill_second_wind",
        "skill_thorn_skin",
        "skill_mark_detonation",
    ):
        skill = lib.skills[sid]
        assert skill.kind == "passive" and skill.rarity == "epic" and skill.trigger is not None


def test_events_render_in_traditional_chinese(monkeypatch: pytest.MonkeyPatch) -> None:
    from trpg.cli.render import describe_event  # noqa: PLC0415

    always(monkeypatch)
    state = scene([passive("skill_text", "on_hit", target="self")])
    result = attack(state)
    fired = triggered(result.events)
    assert fired
    text = describe_event(fired[0], result.state)
    assert text is not None and "被動「" in text and "命中時" in text and "深度 1" in text
    limit = TriggerLimitReached(seq=0, round=1, unit_id=U1, skill_id="skill_text", depth=4)
    text = describe_event(limit, result.state)
    assert text is not None and "觸發深度達到上限" in text
