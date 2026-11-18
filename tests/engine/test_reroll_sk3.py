"""新原語「重擲」（SK-3，#166，06 6.38 第 12 點；只限反應）。

- ``ally_missed_roll``：身旁隊友攻擊擲失手時，讓他重擲取較好的。
- ``enemy_hit_roll``：敵人擲中你時（傷害之前），逼他重擲取較差的。
每輪次數照反應規則；預覽列出可能的重擲（不真的重擲）。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3
from trpg.content.skills import SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    UseSkill,
    preview,
    resolve,
    resume,
    state_to_json,
)
from trpg.engine.events import (
    AttackRerolled,
    AttackRolled,
    DamageDealt,
    EventBase,
    ReactionDeclined,
    ReactionTriggered,
    SkillCooldownChanged,
)
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Team

HIT, MISS = 19, 1
REROLL_SKILL = "skill_t_reroll"


def reroll_skill(event: str, *, cooldown: int | None = None, mana: int = 0) -> SkillDef:
    cost: dict[str, Any] = {"mana": mana}
    if cooldown is not None:
        cost["cooldown"] = cooldown
    return SkillDef.model_validate(
        {
            "id": REROLL_SKILL,
            "name_zh": "測試重擲",
            "tier": 1,
            "rarity": "rare",
            "kind": "reaction",
            "skeleton": "reaction",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [{"type": "reroll"}],
            "reaction": {"event": event},
            "cost": cost,
        }
    )


def d20s(monkeypatch: pytest.MonkeyPatch, rolls: Sequence[int]) -> list[int]:
    """依序擲出 ``rolls``（用完後一律 10）；其他骰子取 1。回傳剩下沒用到的骰。"""
    queue = list(rolls)

    def roll(_self: Rng, sides: int) -> int:
        if sides == 20:  # noqa: PLR2004
            return queue.pop(0) if queue else 10
        return 1

    monkeypatch.setattr(Rng, "roll", roll)
    return queue


def scene(
    helper: SkillDef | None = None,
    *,
    defender: SkillDef | None = None,
    helper_xy: tuple[int, int] = (3, 4),
    prompt: bool = False,
) -> BattleState:
    """U1 我方戰士 (3, 3)、U2 敵人 (4, 3)、U3 我方隊友（帶 ``helper``）在 ``helper_xy``。
    ``defender``：U1 自己帶的重擲（敵人擲中你時）。"""
    skills = [s for s in (helper, defender) if s is not None]
    m = make_map(FLAT7, ally=[(3, 3), helper_xy], enemy=[(4, 3)])
    fighter = caster_template([] if defender is None else [defender], base="hero_fighter")
    if prompt and defender is not None:
        rule = {"reaction": defender.id, "when": {"event": "enemy_hit_roll"}, "mode": "prompt"}
        fighter = template(
            "hero_fighter", reactions=[rule], max_mana=99, skills=[defender.id], max_hp=999
        )
    supporter = caster_template([] if helper is None else [helper], base="hero_mage", max_hp=999)
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), fighter),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999)),
            spawn(Team.ALLY, helper_xy, supporter),
        ],
        skills=skills,
    )
    return give_turn(state, U1)


def of[T: EventBase](events: Sequence[EventBase], kind: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, kind)]


def rolled(events: Sequence[EventBase]) -> list[tuple[int, bool]]:
    return [(e.natural, e.hit) for e in of(events, AttackRolled)]


# ---------------------------------------------------------------------------
# 隊友擲失手時：取較好的
# ---------------------------------------------------------------------------


def test_an_ally_rerolls_your_miss_and_keeps_the_better_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (rerolled,) = of(result.events, AttackRerolled)
    assert (rerolled.unit_id, rerolled.attacker_id, rerolled.target_id) == (U3, U1, U2)
    assert (rerolled.keep, rerolled.first_natural, rerolled.second_natural) == ("better", 1, 19)
    assert (rerolled.first_hit, rerolled.second_hit, rerolled.kept) == (False, True, "second")
    assert rolled(result.events) == [(HIT, True)]
    assert rerolled.seq < of(result.events, AttackRolled)[0].seq
    assert of(result.events, DamageDealt)
    assert result.state.units[U3].reactions_used == 1


def test_a_worse_second_roll_keeps_the_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """取較好的：第二次一樣失手（總值更低）時留第一次。"""
    state = scene(reroll_skill("ally_missed_roll"))
    d20s(monkeypatch, [3, 1])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (rerolled,) = of(result.events, AttackRerolled)
    assert rerolled.kept == "first"
    assert rolled(result.events) == [(3, False)]


def test_a_hit_is_not_rerolled(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    d20s(monkeypatch, [HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not of(result.events, AttackRerolled)
    assert result.state.units[U3].reactions_used == 0


def test_a_helper_out_of_range_cannot_reroll(monkeypatch: pytest.MonkeyPatch) -> None:
    """``core.reroll_ally_range``（初值 1）：隔 2 格的隊友幫不上。"""
    state = scene(reroll_skill("ally_missed_roll"), helper_xy=(3, 5))
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not of(result.events, AttackRerolled)
    assert rolled(result.events) == [(MISS, False)]


def test_the_reroll_reaction_is_once_per_round(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    d20s(monkeypatch, [MISS, HIT, MISS])
    first = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert len(of(first.events, AttackRerolled)) == 1
    again = resolve(give_turn(first.state, U1), Attack(unit_id=U1, target_id=U2))
    assert not of(again.events, AttackRerolled)


def test_mana_and_cooldown_are_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = reroll_skill("ally_missed_roll", cooldown=2, mana=4)
    state = scene(skill)
    before = state.units[U3].mana
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert of(result.events, ReactionTriggered)
    assert result.state.units[U3].mana < before
    assert [e.remaining for e in of(result.events, SkillCooldownChanged)] == [2]


def test_skill_attacks_are_rerolled_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """技能的命中骰（``Cast.roll_one``）走同一個重擲。"""
    strike = make_skill(
        "skill_t_strike",
        {"type": "single", "range": 1},
        [{"type": "damage", "multiplier_permille": 1000}],
        category="weapon",
    )
    helper = reroll_skill("ally_missed_roll")
    m = make_map(FLAT7, ally=[(3, 3), (3, 4)], enemy=[(4, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([strike], base="hero_fighter")),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999)),
            spawn(Team.ALLY, (3, 4), caster_template([helper], max_hp=999)),
        ],
        skills=[strike, helper],
    )
    action = UseSkill(unit_id=U1, skill_id=strike.id, target_id=U2)
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(give_turn(state, U1), action)
    (rerolled,) = of(result.events, AttackRerolled)
    assert rerolled.kept == "second"
    assert [e.skill_id for e in of(result.events, AttackRolled)] == [strike.id]
    assert rolled(result.events) == [(HIT, True)]


# ---------------------------------------------------------------------------
# 敵人擲中你時：取較差的
# ---------------------------------------------------------------------------


def test_you_force_the_enemy_to_reroll_and_keep_the_worse(monkeypatch: pytest.MonkeyPatch) -> None:
    state = give_turn(scene(defender=reroll_skill("enemy_hit_roll")), U2)
    d20s(monkeypatch, [HIT, MISS])
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    (rerolled,) = of(result.events, AttackRerolled)
    assert (rerolled.unit_id, rerolled.attacker_id, rerolled.keep) == (U1, U2, "worse")
    assert rerolled.kept == "second"
    assert rolled(result.events) == [(MISS, False)]
    assert not [d for d in of(result.events, DamageDealt) if d.target_id == U1]


def test_an_enemy_miss_is_not_rerolled(monkeypatch: pytest.MonkeyPatch) -> None:
    state = give_turn(scene(defender=reroll_skill("enemy_hit_roll")), U2)
    d20s(monkeypatch, [MISS])
    result = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert not of(result.events, AttackRerolled)


def test_the_prompt_mode_pauses_and_can_be_declined() -> None:
    """暫停後 ``resume`` 從原狀態重跑整個動作：用戰鬥亂數（不換骰），第一顆 19、第二顆 1。"""
    state = give_turn(scene(defender=reroll_skill("enemy_hit_roll"), prompt=True), U2)
    state = with_rolls(state, [(20, HIT), (20, MISS)])
    paused = resolve(state, Attack(unit_id=U2, target_id=U1))
    assert paused.pending is not None and paused.pending.reaction == REROLL_SKILL
    assert not of(paused.events, AttackRolled)
    accepted = resume(paused.state, Decision(unit_id=U1, accept=True))
    assert of(accepted.events, AttackRerolled)
    assert rolled(accepted.events) == [(MISS, False)]
    declined = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert of(declined.events, ReactionDeclined)
    assert rolled(declined.events) == [(HIT, True)]


# ---------------------------------------------------------------------------
# 預覽、確定性、紀錄文字
# ---------------------------------------------------------------------------


def test_preview_lists_the_possible_rerolls_without_rolling() -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    before = state_to_json(state)
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert state_to_json(state) == before
    (info,) = p.rerolls
    assert (info.unit_id, info.skill_id, info.target_id, info.keep, info.auto) == (
        U3,
        REROLL_SKILL,
        U1,
        "better",
        True,
    )
    assert p.hit_chance is not None
    assert info.hit_chance == 1 - (1 - p.hit_chance) ** 2
    assert any("重擲" in n for n in p.notes)
    assert not [e for e in p.max_events if isinstance(e, AttackRerolled)]


def test_preview_against_a_defender_shows_the_worse_chance() -> None:
    state = give_turn(scene(defender=reroll_skill("enemy_hit_roll")), U2)
    p = preview(state, Attack(unit_id=U2, target_id=U1))
    (info,) = p.rerolls
    assert (info.unit_id, info.keep) == (U1, "worse")
    assert p.hit_chance is not None
    assert info.hit_chance == p.hit_chance**2
    assert info.hit_chance < p.hit_chance or p.hit_chance in (Fraction(0), Fraction(1))


def test_without_any_reroll_reaction_the_preview_has_none() -> None:
    p = preview(scene(), Attack(unit_id=U1, target_id=U2))
    assert p.rerolls == ()


def test_same_input_same_result() -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    results = [resolve(state, Attack(unit_id=U1, target_id=U2)) for _ in range(2)]
    dumps = [[e.model_dump(mode="json") for e in r.events] for r in results]
    assert dumps[0] == dumps[1]
    assert state_to_json(results[0].state) == state_to_json(results[1].state)


@pytest.mark.parametrize("seed", range(12))
def test_rerolls_are_deterministic_for_any_seed(seed: int) -> None:
    """不換骰：任何種子下，同一個狀態結算兩次逐字相同；有重擲時採用的骰照 keep 規則。"""
    state = scene(reroll_skill("ally_missed_roll"))
    state.rng_state = Rng(seed).get_state()
    a = resolve(state, Attack(unit_id=U1, target_id=U2))
    b = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert [e.model_dump(mode="json") for e in a.events] == [
        e.model_dump(mode="json") for e in b.events
    ]
    for r in of(a.events, AttackRerolled):
        best = max((r.first_hit, r.first_total), (r.second_hit, r.second_total))
        final = of(a.events, AttackRolled)[-1]
        assert (final.hit, final.total) == best


def test_the_log_line_describes_the_reroll(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene(reroll_skill("ally_missed_roll"))
    d20s(monkeypatch, [MISS, HIT])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (rerolled,) = of(result.events, AttackRerolled)
    line = describe_event(rerolled, result.state)
    assert "重擲" in line and "取較好的" in line and "採用第二次" in line


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------


def _iter_invalid() -> Iterator[tuple[dict[str, Any], str]]:
    base = reroll_skill("enemy_hit_roll").model_dump(mode="json", exclude_none=True)
    yield {**base, "reaction": {"event": "hit_by_attack"}}, "reroll 只能用在"
    yield (
        {**base, "effects": [{"type": "damage", "dice": "1d4", "element": "fire"}]},
        "必須有 reroll",
    )
    active = {**base, "kind": "active", "ap_cost": 1, "skeleton": "strike"}
    active.pop("reaction")
    yield active, "reroll"


@pytest.mark.parametrize(("data", "message"), list(_iter_invalid()))
def test_reroll_is_only_for_the_two_reaction_events(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(data)
