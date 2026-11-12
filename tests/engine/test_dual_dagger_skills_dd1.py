"""DD-1：雙匕首的武器技也打兩下（#153，``docs/design/08-裝備.md`` 8.11）。

每列一條規則句、實際跑引擎：單體武器技每個傷害效果打兩下（每下套技能倍率、各用一次武器的傷害骰與
屬性加成）、各自擲命中暴擊、背刺兩下都吃、第一下打倒就不打第二下、命中時的觸發每下各一次、附加
效果只結算一次（第一個命中的那下；兩下都沒中不結算）、非單體形狀與法術不受影響、打部位時兩下打
同一個部位；預覽與效用 AI 的估值算兩下。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

import pytest

from tests.engine.helpers import caster_template, library, make_skill, no_reactions, with_rolls
from tests.engine.skill_helpers import SID, U1, U2, battle, cast
from tests.engine.test_boss_parts_pb1 import BOSS, HERO, arena
from tests.engine.test_weapons_ranged import weapon
from trpg.content.battle import WeaponDef
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, preview, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.ai.utility.scoring import score_action
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    Healed,
    PartBroken,
    PartDamaged,
    StatusSaveRolled,
    UnitMoved,
)
from trpg.engine.skills.targeting import skill_strikes
from trpg.shared.rng import Rng

HIT, MISS = 15, 1
DIE = 2
"""非 d20 的骰子一律 2（雙匕首 1d3）。"""

DAMAGE: dict[str, Any] = {"type": "damage", "multiplier_permille": 1500}
HEX: dict[str, Any] = {"type": "apply_status", "status": "vulnerable", "duration": 1}
PUSH: dict[str, Any] = {"type": "push", "distance": 1}


def skill_of(
    effects: Sequence[Mapping[str, Any]],
    *,
    shape: Mapping[str, Any] | None = None,
    category: str = "weapon",
) -> SkillDef:
    return make_skill(
        SID,
        shape or {"type": "single", "range": 1},
        effects,
        category=category,
        weapon_req="any" if category == "spell" else "melee",
    )


def duel(
    skill: SkillDef,
    *,
    w: WeaponDef | None = None,
    foe_hp: int = 200,
    facing: str = "east",
    base: str = "hero_fighter",
) -> BattleState:
    """U1 站 (3, 3) 拿雙匕首（或 ``w``），U2 在 (4, 3) 朝 ``facing``（朝東時 U1 在它背後）。"""
    foe = no_reactions(max_hp=foe_hp, resist={})
    state = battle(skill, [(4, 3, foe)], caster=(3, 3), base=base)
    state.units[U1].weapon = w or library().weapons["dual_dagger"]
    state.units[U2].facing = facing  # type: ignore[assignment]
    return state


def d20s(monkeypatch: pytest.MonkeyPatch, values: Sequence[int], rest: int = 10) -> None:
    """接下來的 d20 依序是 ``values``（用完是 ``rest``），其他骰子一律 :data:`DIE`。"""
    seq: Iterator[int] = iter(values)
    monkeypatch.setattr(
        Rng, "roll", lambda self, sides: next(seq, rest) if sides == 20 else min(DIE, sides)
    )


def mine[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind) and getattr(e, "source_id", U1) == U1]


def rolls(events: Sequence[EventBase]) -> list[AttackRolled]:
    return [e for e in events if isinstance(e, AttackRolled) and e.attacker_id == U1]


# ---------------------------------------------------------------------------
# 1. 打兩下：每下套技能倍率、各用一次傷害骰與屬性加成、各自擲命中暴擊
# ---------------------------------------------------------------------------

STRIKES = [
    # (說明, d20 序列, (擲命中次數, 傷害次數))
    ("兩下都中", [HIT, HIT], (2, 2)),
    ("第一下中、第二下沒中", [HIT, MISS], (2, 1)),
    ("第一下沒中、第二下中", [MISS, HIT], (2, 1)),
    ("兩下都沒中", [MISS, MISS], (2, 0)),
]


@pytest.mark.parametrize(("name", "seq", "counts"), STRIKES)
def test_a_single_weapon_skill_strikes_twice_with_dual_daggers(
    name: str, seq: list[int], counts: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill_of([DAMAGE]))
    d20s(monkeypatch, seq)
    events = cast(state, target_id=U2).events
    rolled, dealt = rolls(events), mine(events, DamageDealt)
    assert (len(rolled), len(dealt)) == counts, name
    assert [r.hit for r in rolled] == [d == HIT for d in seq], name
    assert all(r.skill_id == SID for r in rolled)
    for d in dealt:  # 每一下都套技能倍率、各擲一次武器的骰子、吃同樣的屬性加成
        assert d.multiplier_permille == dealt[0].multiplier_permille
        assert d.multiplier_permille >= 1500 * 9 // 10
        assert d.rolls == (DIE,)
        assert d.scaled_permille == dealt[0].scaled_permille > 0


def test_each_strike_rolls_its_own_crit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(skill_of([DAMAGE]))
    d20s(monkeypatch, [20, HIT])
    events = cast(state, target_id=U2).events
    assert [r.crit for r in rolls(events)] == [True, False]
    assert [len(d.rolls) for d in mine(events, DamageDealt)] == [2, 1]  # 暴擊多擲一組


def test_the_second_strike_is_skipped_when_the_first_one_kills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = duel(skill_of([DAMAGE]), foe_hp=1)
    d20s(monkeypatch, [HIT, HIT])
    events = cast(state, target_id=U2).events
    assert len(rolls(events)) == 1 and len(mine(events, DamageDealt)) == 1


@pytest.mark.parametrize(("facing", "backstab"), [("east", True), ("west", False)])
def test_backstab_applies_to_both_strikes(
    facing: str, *, backstab: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill_of([DAMAGE]), facing=facing)
    d20s(monkeypatch, [HIT, HIT])
    rolled = rolls(cast(state, target_id=U2).events)
    assert len(rolled) == 2 and all((r.backstab > 0) is backstab for r in rolled)


def test_backstab_first_only_weapons_backstab_on_the_first_strike_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    w = weapon("dual_dagger", backstab_first_only=True)
    state = duel(skill_of([DAMAGE]), w=w, facing="east")
    d20s(monkeypatch, [HIT, HIT])
    assert [r.backstab > 0 for r in rolls(cast(state, target_id=U2).events)] == [True, False]


def test_every_damage_effect_strikes_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(skill_of([DAMAGE, {"type": "damage"}]))
    d20s(monkeypatch, [HIT, HIT])
    events = cast(state, target_id=U2).events
    assert len(rolls(events)) == 2 and len(mine(events, DamageDealt)) == 4


@pytest.mark.parametrize("strikes", [1, 2, 3])
def test_the_number_of_strikes_follows_the_weapon_data(
    strikes: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill_of([DAMAGE]), w=weapon("dual_dagger", strikes=strikes))
    d20s(monkeypatch, [HIT] * strikes)
    events = cast(state, target_id=U2).events
    assert len(rolls(events)) == len(mine(events, DamageDealt)) == strikes


# ---------------------------------------------------------------------------
# 2. 命中時的觸發每一下各一次（吸血跟著每一下的傷害）
# ---------------------------------------------------------------------------


def test_on_hit_effects_follow_every_strike(monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(skill_of([{**DAMAGE, "lifesteal_permille": 500}]))
    state.units[U1].hp = 1
    d20s(monkeypatch, [HIT, HIT])
    events = cast(state, target_id=U2).events
    healed = [e for e in events if isinstance(e, Healed) and e.target_id == U1]
    assert len(mine(events, DamageDealt)) == 2 and len(healed) == 2


# ---------------------------------------------------------------------------
# 3. 附加效果只結算一次：第一個命中的那下；兩下都沒中不結算
# ---------------------------------------------------------------------------

EXTRAS = [
    # (說明, d20 序列, 附加效果結算次數, 結算在第幾下之後（擲命中的序號）)
    ("兩下都中：第一下結算", [HIT, HIT], 1, 0),
    ("第一下沒中、第二下中：第二下結算", [MISS, HIT], 1, 1),
    ("第一下中、第二下沒中：第一下結算", [HIT, MISS], 1, 0),
    ("兩下都沒中：不結算", [MISS, MISS], 0, None),
]


@pytest.mark.parametrize(("name", "seq", "times", "after"), EXTRAS)
def test_a_status_rider_resolves_once_on_the_first_hit(
    name: str, seq: list[int], times: int, after: int | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill_of([DAMAGE, HEX]))
    d20s(monkeypatch, seq)
    events = cast(state, target_id=U2).events
    saves = [e for e in events if isinstance(e, StatusSaveRolled)]
    assert len(saves) == times, name
    if after is not None:
        rolled = rolls(events)
        assert rolled[after].seq < saves[0].seq, name
        if after + 1 < len(rolled):
            assert saves[0].seq < rolled[after + 1].seq, name


@pytest.mark.parametrize(("seq", "times"), [([HIT, HIT], 1), ([MISS, HIT], 1), ([MISS, MISS], 0)])
def test_a_push_rider_resolves_once(
    seq: list[int], times: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill_of([DAMAGE, PUSH]))
    d20s(monkeypatch, seq)
    events = cast(state, target_id=U2).events
    pushed = [e for e in events if isinstance(e, UnitMoved) and e.unit_id == U2]
    assert len(pushed) == times


# ---------------------------------------------------------------------------
# 4. 不受影響：非單體形狀、法術、其他武器、被動觸發
# ---------------------------------------------------------------------------

UNAFFECTED = [
    ("非單體形狀（十字）", skill_of([DAMAGE], shape={"type": "cross", "range": 3})),
    ("法術", skill_of([{"type": "damage", "dice": "1d6", "element": "fire"}], category="spell")),
]


@pytest.mark.parametrize(("name", "skill"), UNAFFECTED)
def test_other_shapes_and_spells_strike_once(
    name: str, skill: SkillDef, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = duel(skill)
    assert skill_strikes(state.units[U1], skill) == 1, name
    d20s(monkeypatch, [HIT, HIT])
    action: dict[str, Any] = {"target_id": U2}
    if skill.shape.type != "single":
        action = {"target_pos": state.units[U2].pos}
    events = cast(state, **action).events
    assert len([r for r in rolls(events) if r.target_id == U2]) == 1, name
    assert len([d for d in mine(events, DamageDealt) if d.target_id == U2]) == 1, name


def test_other_weapons_strike_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = duel(skill_of([DAMAGE]), w=library().weapons["one_handed_sword"])
    d20s(monkeypatch, [HIT, HIT])
    events = cast(state, target_id=U2).events
    assert len(rolls(events)) == 1 and len(mine(events, DamageDealt)) == 1


# ---------------------------------------------------------------------------
# 5. 部位（PB-1a R5）：兩下打同一個部位；第一下打破就打本體
# ---------------------------------------------------------------------------

STAB = skill_of([DAMAGE])


def part_arena() -> BattleState:
    hero = caster_template([STAB], base="hero_fighter")
    return arena(hero=hero, hero_weapon="dual_dagger", rule_skills=[STAB])


@pytest.mark.parametrize(("part_hp", "damaged", "broken"), [(1000, 2, 0), (1, 1, 1)])
def test_both_strikes_hit_the_declared_part(part_hp: int, damaged: int, broken: int) -> None:
    state = with_rolls(part_arena(), [(20, 15), (20, 15)])
    state.units[BOSS].part_hp["head"] = part_hp
    action = UseSkill(unit_id=HERO, skill_id=SID, target_id=BOSS, target_part="head")
    events = resolve(state, action).events
    dealt = [e for e in events if isinstance(e, DamageDealt) and e.target_id == BOSS]
    hurt = of_kind(events, PartDamaged)
    assert len(dealt) == 2
    assert [h.part_id for h in hurt] == ["head"] * damaged
    assert len(of_kind(events, PartBroken)) == broken


def of_kind[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 6. 預覽與 AI 估值算兩下
# ---------------------------------------------------------------------------


def test_the_preview_counts_both_strikes() -> None:
    skill = skill_of([DAMAGE])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    double = preview(duel(skill), action)
    single = preview(duel(skill, w=weapon("dual_dagger", strikes=1)), action)
    (two,), (one,) = double.targets, single.targets
    assert two.damage is not None and one.damage is not None
    assert two.damage.expected == 2 * one.damage.expected
    assert two.damage.maximum == 2 * one.damage.maximum  # 最多後果：兩下都暴擊
    assert two.damage.minimum == one.damage.minimum  # 最少後果：後面那下同普攻，失手
    assert len(mine(list(double.min_events), DamageDealt)) == 1
    assert len(mine(list(double.max_events), DamageDealt)) == 2


def test_the_utility_ai_values_the_second_strike() -> None:
    skill = skill_of([DAMAGE])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    state = duel(skill)
    profile = UtilityAI(library().ai_profiles).profile_for(state.units[U1])
    double = score_action(duel(skill), action, profile).score
    single = score_action(duel(skill, w=weapon("dual_dagger", strikes=1)), action, profile).score
    assert double > single


def test_the_original_skill_state_is_not_touched() -> None:
    state = duel(skill_of([DAMAGE, HEX]))
    before = state.clone()
    cast(state, target_id=U2)
    assert state.units[U2].hp == before.units[U2].hp and state.rng_state == before.rng_state
