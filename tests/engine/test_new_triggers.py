"""新觸發時機（Phase 3C-3a 5.1）：``on_cast_tag``、``on_status_applied``、``on_collision``。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, script_rolls
from tests.engine.test_passive_triggers import _HEAL_SELF, always, passive, scene, triggered
from trpg.content.skills import SkillDef, TriggerSpec
from trpg.engine import BattleState, Move, UseSkill, resolve
from trpg.engine.effects import PushEffect, run_effects
from trpg.engine.events import (
    Collided,
    DamageDealt,
    EventBase,
    Healed,
    SkillTriggered,
    StatusApplied,
    StatusResisted,
    TriggerLimitReached,
)
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

_ADD_FIRE_TAG = SkillDef.model_validate(
    {
        "id": "skill_t_add_fire",
        "name_zh": "測試修正",
        "tier": 1,
        "rarity": "epic",
        "kind": "modifier",
        "skeleton": "modifier",
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "int",
        "shape": {"type": "self"},
        "effects": [],
        "modifiers": [
            {"applies_to": {"all_skills": True}, "change": {"add_tags": ["fire"]}},
        ],
    }
)


def mk(
    skill_id: str,
    event: str,
    *,
    tag: str | None = None,
    status: str | None = None,
    target: str = "other",
    effects: Sequence[dict[str, Any]] | None = None,
    max_per_round: int = 1,
) -> SkillDef:
    """測試專用被動技能（含新時機的 ``tag``、``status`` 參數）。"""
    spec: dict[str, Any] = {"event": event, "target": target, "max_per_round": max_per_round}
    spec |= {k: v for k, v in (("tag", tag), ("status", status)) if v is not None}
    base = passive(skill_id, "on_hit", target=target, effects=effects)
    return base.model_copy(update={"trigger": TriggerSpec.model_validate(spec)})


def sc(owner: Sequence[SkillDef | str], foe: Sequence[SkillDef | str] = ()) -> BattleState:
    """U1 是法師（可以施放法術技）、U2 是敵人。"""
    return scene(owner, foe, owner_base="hero_mage")


def burn_skill(
    skill_id: str = "skill_t_burn", status: str = "burning", tags: Sequence[str] = ()
) -> SkillDef:
    skill = make_skill(
        skill_id,
        {"type": "single", "range": 3},
        [{"type": "apply_status", "status": status, "duration": 2, "affects": "enemies"}],
    )
    return skill.model_copy(update={"tags": tuple(tags)})


def fire_skill(skill_id: str = "skill_t_fire", tags: Sequence[str] = ("fire",)) -> SkillDef:
    skill = make_skill(
        skill_id,
        {"type": "single", "range": 3},
        [{"type": "damage", "dice": "1d4", "element": "fire", "affects": "enemies"}],
    )
    return skill.model_copy(update={"tags": tuple(tags)})


def cast(state: BattleState, skill: SkillDef) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2))


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# on_cast_tag
# ---------------------------------------------------------------------------


def _cast_tag_passive(tag: str = "fire") -> SkillDef:
    return mk("skill_t_cast", "on_cast_tag", tag=tag, target="self", effects=[_HEAL_SELF])


def test_on_cast_tag_triggers_after_the_tagged_skill_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    spell = fire_skill()
    state = sc([spell, _cast_tag_passive()])
    state.units[U1].hp = 10
    result = cast(state, spell)
    (fired,) = triggered(result.events)
    assert (fired.unit_id, fired.trigger, fired.other_id, fired.trigger_depth) == (
        U1,
        "on_cast_tag",
        None,
        1,
    )
    order = [e.seq for e in result.events]
    damage = of(result.events, DamageDealt)
    assert damage and fired.seq > max(d.seq for d in damage) and order == sorted(order)
    assert [h.target_id for h in of(result.events, Healed)] == [U1]  # 效果作用在持有者


def test_on_cast_tag_ignores_other_tags_and_untagged_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    ice = fire_skill("skill_t_ice", tags=("ice",))
    plain = fire_skill("skill_t_plain", tags=())
    state = sc([ice, plain, _cast_tag_passive("fire")])
    assert triggered(cast(state, ice).events) == []
    assert triggered(cast(state, plain).events) == []


def test_on_cast_tag_is_not_triggered_by_a_basic_attack_or_by_another_units_cast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    spell = fire_skill()
    # 持有者是敵人 U2；我方 U1 施放火焰技不會讓它觸發
    state = sc([spell], [_cast_tag_passive()])
    assert triggered(cast(state, spell).events) == []


def test_on_cast_tag_sees_tags_added_by_modifier_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    plain = fire_skill("skill_t_plain", tags=())
    state = sc([plain, _ADD_FIRE_TAG, _cast_tag_passive("fire")])
    assert [e.trigger for e in triggered(cast(state, plain).events)] == ["on_cast_tag"]


# ---------------------------------------------------------------------------
# on_status_applied
# ---------------------------------------------------------------------------


def _status_passive(status: str | None = "burning", skill_id: str = "skill_t_applied") -> SkillDef:
    return mk(skill_id, "on_status_applied", status=status)


def test_on_status_applied_triggers_and_targets_the_unit_that_got_the_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    burn = burn_skill()
    result = cast(sc([burn, _status_passive()]), burn)
    assert of(result.events, StatusApplied)
    (fired,) = triggered(result.events)
    assert (fired.unit_id, fired.trigger, fired.other_id, fired.trigger_depth) == (
        U1,
        "on_status_applied",
        U2,
        1,
    )
    assert [d.target_id for d in of(result.events, DamageDealt)] == [U2]


def test_on_status_applied_without_a_status_filter_accepts_any_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    slow = burn_skill("skill_t_slow", "slow")
    result = cast(sc([slow, _status_passive(None)]), slow)
    assert [e.trigger for e in triggered(result.events)] == ["on_status_applied"]


def test_on_status_applied_ignores_other_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    slow = burn_skill("skill_t_slow", "slow")
    result = cast(sc([slow, _status_passive("burning")]), slow)
    assert of(result.events, StatusApplied) and triggered(result.events) == []


def test_on_status_applied_does_not_trigger_when_the_status_is_resisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slow = burn_skill("skill_t_slow", "slow")  # 緩速有抵抗判定（敏捷）；燃燒沒有
    state = sc([slow, _status_passive("slow")])
    script_rolls(monkeypatch, [19, 1, 1, 1, 1, 1])  # 命中，抵抗判定擲出自然 1
    result = cast(state, slow)
    assert of(result.events, StatusResisted), "測試前提：狀態被抵抗了"
    assert of(result.events, StatusApplied) == [] and triggered(result.events) == []


def test_on_status_applied_ignores_statuses_the_holder_puts_on_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    self_slow = make_skill(
        "skill_t_selfslow",
        {"type": "self"},
        [{"type": "apply_status", "status": "slow", "duration": 2, "affects": "self"}],
    )
    result = resolve(
        sc([self_slow, _status_passive(None)]), UseSkill(unit_id=U1, skill_id=self_slow.id)
    )
    assert of(result.events, StatusApplied) and triggered(result.events) == []


def test_on_status_applied_ignores_statuses_applied_by_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    burn = burn_skill()
    state = sc([burn], [_status_passive()])  # 持有者是被施加的敵人 U2
    assert triggered(cast(state, burn).events) == []


# ---------------------------------------------------------------------------
# on_collision
# ---------------------------------------------------------------------------


def _wall_scene(
    owner: Sequence[SkillDef | str] = (), foe: Sequence[SkillDef | str] = ()
) -> BattleState:
    """U1 在 (3, 3)、U2 在 (4, 3)，(6, 3) 是牆：往東推 U2 兩格，第二步被擋。"""
    rows = ["." * 7 for _ in range(7)]
    rows[3] = "......#"
    defs = list({s.id: s for s in (*owner, *foe) if isinstance(s, SkillDef)}.values())
    m = make_map(FLAT7, "\n".join(rows), ally=[(3, 3)], enemy=[(4, 3)])
    fighter = caster_template(owner, base="hero_fighter", max_hp=999)
    enemy = no_reactions(
        "bandit", max_mana=99, skills=[s if isinstance(s, str) else s.id for s in foe]
    )
    enemy = enemy.model_copy(update={"max_hp": 999})
    state = make_state(
        m, [spawn(Team.ALLY, (3, 3), fighter), spawn(Team.ENEMY, (4, 3), enemy)], skills=defs
    )
    return give_turn(state, U1)


def _push(source: UnitId, distance: int = 2) -> PushEffect:
    return PushEffect(source_id=source, target_id=U2, direction=(1, 0), distance=distance)


def test_on_collision_triggers_for_the_unit_that_caused_the_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    owner = mk("skill_t_collide", "on_collision")
    result = run_effects(_wall_scene([owner]), [_push(U1)])
    (hit,) = of(result.events, Collided)
    assert hit.shortfall == 1
    (fired,) = triggered(result.events)
    assert (fired.unit_id, fired.trigger, fired.other_id, fired.trigger_depth) == (
        U1,
        "on_collision",
        U2,
        1,
    )
    effect_damage = [d for d in of(result.events, DamageDealt) if d.cause != "collision"]
    assert [d.target_id for d in effect_damage] == [U2]
    collision_seq = max(d.seq for d in of(result.events, DamageDealt) if d.cause == "collision")
    assert fired.seq > collision_seq  # 撞擊傷害結算之後才觸發


def test_on_collision_does_not_trigger_when_someone_else_pushed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    owner = mk("skill_t_collide", "on_collision")
    result = run_effects(_wall_scene([owner]), [_push(U2)])  # 來源是被推的 U2 自己
    assert of(result.events, Collided) and triggered(result.events) == []
    result = run_effects(
        _wall_scene([owner]), [PushEffect(target_id=U2, direction=(1, 0), distance=2)]
    )
    assert of(result.events, Collided) and triggered(result.events) == []  # 沒有來源


def test_on_collision_does_not_trigger_without_a_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    owner = mk("skill_t_collide", "on_collision")
    result = run_effects(_wall_scene([owner]), [_push(U1, distance=1)])  # (5, 3) 是空的
    assert of(result.events, Collided) == [] and triggered(result.events) == []


def test_on_collision_does_not_trigger_when_an_active_move_is_blocked_or_walks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    owner = mk("skill_t_collide", "on_collision")
    state = _wall_scene([owner])
    with pytest.raises(IllegalActionError):
        resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=4, y=3))))  # 被敵人擋住
    walked = resolve(state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=3, y=2))))
    assert of(walked.events, Collided) == [] and triggered(walked.events) == []


def test_on_collision_triggers_for_the_excess_collision_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    owner = mk("skill_t_collide", "on_collision")
    state = _wall_scene([owner])
    effect = PushEffect(
        source_id=U1, target_id=U2, direction=(1, 0), distance=1, extra_collisions=1
    )
    result = run_effects(state, [effect])
    assert [e.obstacle for e in of(result.events, Collided)] == ["excess"]
    assert [e.trigger for e in triggered(result.events)] == ["on_collision"]


# ---------------------------------------------------------------------------
# 互相觸發停在深度上限
# ---------------------------------------------------------------------------


def test_two_passives_that_trigger_each_other_stop_at_the_depth_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A（施加燃燒 → 施加緩速）與 B（施加緩速 → 施加燃燒）互相觸發：深度 1、2、3 結算，第 4 層
    被擋下並發出 ``TriggerLimitReached``，戰鬥不會卡住。"""
    always(monkeypatch)
    effect_slow = {"type": "apply_status", "status": "slow", "duration": 2, "affects": "enemies"}
    effect_burn = {"type": "apply_status", "status": "burning", "duration": 2, "affects": "enemies"}
    a = mk(
        "skill_t_a", "on_status_applied", status="burning", effects=[effect_slow], max_per_round=3
    )
    b = mk("skill_t_b", "on_status_applied", status="slow", effects=[effect_burn], max_per_round=3)
    burn = burn_skill()
    result = cast(sc([burn, a, b]), burn)
    fired = triggered(result.events)
    assert [(e.skill_id, e.trigger_depth) for e in fired] == [
        ("skill_t_a", 1),
        ("skill_t_b", 2),
        ("skill_t_a", 3),
    ]
    (limit,) = of(result.events, TriggerLimitReached)
    assert (limit.skill_id, limit.depth) == ("skill_t_b", 4)
    assert all(isinstance(e, SkillTriggered | EventBase) for e in result.events)
