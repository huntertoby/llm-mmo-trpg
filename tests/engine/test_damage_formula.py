"""Phase ENG-1 S1：骰值傷害公式合一——實際結算與兩份預覽共用
:func:`~trpg.engine.rules.combat.rolled_damage_amount`。

- 表格測試實際跑引擎：對每個骰值總和各結算一次，用真正的 ``damage_dealt`` 算出期望值，與預覽的
  ``expected_if_hit`` 精確比對。普攻與技能各跑一輪；每一列都同時比對未暴擊與暴擊。
- 公式函式對改動前的兩種寫法逐一比對（hypothesis）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from itertools import product
from typing import Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    rng_state_for,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, UseSkill, preview, resolve
from trpg.engine.effects import handlers
from trpg.engine.events import DamageDealt
from trpg.engine.rules.combat import PERMILLE, PPM, raw_damage_permille, rolled_damage_amount
from trpg.engine.state import StatusInstance
from trpg.engine.weapon_traits import attack_dice
from trpg.shared.rng import RngState
from trpg.shared.types import Element, Team

SID = "skill_t_eng1"
Mode = Literal["attack", "skill"]
Check = Callable[[DamageDealt], bool]
MIN_DAMAGE_ROW = 50  # 高於這場所有可能的傷害，整張表都會落在最低傷害


@dataclass(frozen=True)
class Row:
    """一種傷害情境；``check`` 確認事件真的帶到這一列要測的因子（避免情境失效卻照樣通過）。"""

    name: str
    check: Check
    enemy_attacks: bool = False
    core: Mapping[str, int] = field(default_factory=dict)
    target_tags: tuple[str, ...] = ()
    target_statuses: tuple[StatusInstance, ...] = ()
    holder_status: str | None = None
    element_mod: int = 0
    weather_permille: int | None = None
    zero_taken: bool = False
    all_zero: bool = False


VULNERABLE = StatusInstance("vulnerable", 2)
ROWS = [
    Row("normal", lambda e: e.element_mod_ppm == PPM and e.status_ppm == PPM),
    Row("element", lambda e: e.element_mod_ppm == 1_500_000, element_mod=500),
    Row("weather", lambda e: e.weather_permille == 1200, weather_permille=200),
    Row(
        "multiplier",
        lambda e: e.multiplier_permille == 1500,
        enemy_attacks=True,
        core={"enemy_damage_permille": 1500},
    ),
    Row(
        "vulnerable",
        lambda e: e.status_ppm == 1_250_000,
        target_statuses=(VULNERABLE,),
    ),
    Row(
        "shield",
        lambda e: e.absorbed > 0,
        target_statuses=(StatusInstance("shielded", 2, None, 3),),
    ),
    Row(
        "min_damage",
        lambda e: e.amount == MIN_DAMAGE_ROW,
        core={"min_damage_on_hit": MIN_DAMAGE_ROW},
    ),
    Row(
        "ward_half",
        lambda e: e.ward_permille == 500 and e.amount > 0,
        target_tags=("mist_lock_core",),
        holder_status="summit_array_ward",
    ),
    Row(
        "ward_zero",
        lambda e: e.ward_permille == 0 and e.amount == 0,
        target_tags=("rift_core",),
        holder_status="rift_resonance",
        all_zero=True,
    ),
    Row(
        "ward_zero_vulnerable",
        lambda e: e.ward_permille == 0 and e.amount == 0,
        target_tags=("rift_core",),
        target_statuses=(VULNERABLE,),
        holder_status="rift_resonance",
        all_zero=True,
    ),
    Row(  # status_ppm == 0 不等於護陣 ×0：沒有護陣時仍要套最低傷害
        "status_zero_without_ward",
        lambda e: e.status_ppm == 0 and e.ward_permille == PERMILLE and e.amount == 1,
        zero_taken=True,
    ),
]


def _skill() -> SkillDef:
    """1d6 的火焰箭（骰面少，才能對每個骰值總和實際結算；暴擊 2d6）。"""
    bolt = library().skills["skill_fire_bolt"]
    spec = bolt.effects[0]
    assert spec.dice is not None
    dice = spec.dice.model_copy(update={"count": 1, "sides": 6})
    return bolt.model_copy(update={"id": SID, "effects": (spec.model_copy(update={"dice": dice}),)})


def _scene(mode: Mode, row: Row) -> tuple[BattleState, Attack | UseSkill]:
    """U1 攻擊 U2；U3 是遠處的護陣持有者（與 U2 同陣營）。"""
    skill = _skill()
    attacker = no_reactions("hero_fighter") if mode == "attack" else caster_template([skill])
    target_xy = (2, 3) if mode == "attack" else (4, 3)
    tags = list(row.target_tags)
    attacker_team, target_team = (
        (Team.ENEMY, Team.ALLY) if row.enemy_attacks else (Team.ALLY, Team.ENEMY)
    )
    spots = {attacker_team: [(1, 3)], target_team: [target_xy, (6, 6)]}
    state = make_state(
        make_map(FLAT7, ally=spots[Team.ALLY], enemy=spots[Team.ENEMY]),
        [
            spawn(attacker_team, (1, 3), attacker),
            spawn(target_team, target_xy, no_reactions("bandit", max_hp=200, tags=tags)),
            spawn(target_team, (6, 6), no_reactions("bandit", max_hp=200)),
        ],
        skills=[skill],
        **row.core,  # type: ignore[arg-type]  # 只放 rules/core.yaml 的整數覆寫
    )
    state = give_turn(state, U1)
    target = state.units[U2]
    target.statuses = [*target.statuses, *row.target_statuses]
    if row.holder_status is not None:
        holder = state.units[U3]
        holder.statuses = [*holder.statuses, StatusInstance(row.holder_status)]
    if row.element_mod:
        target.element_mods = {Element.PHYSICAL: row.element_mod, Element.FIRE: row.element_mod}
    if row.weather_permille is not None:
        mods = {Element.PHYSICAL: row.weather_permille, Element.FIRE: row.weather_permille}
        state.weather = (
            library().weather_def("rain").model_copy(update={"element_damage_permille": mods})
        )
    if mode == "attack":
        return state, Attack(unit_id=U1, target_id=U2)
    return state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)


@cache
def _rng_for(rolls: tuple[tuple[int, int], ...]) -> RngState:
    return rng_state_for(rolls)


def _dealt(
    state: BattleState, action: Attack | UseSkill, natural: int, sides: int, faces: tuple[int, ...]
) -> DamageDealt:
    """命中（``natural`` 20 為暴擊）、傷害骰擲出 ``faces`` 時，引擎實際的 ``damage_dealt``。"""
    rolled = state.clone()
    rolled.rng_state = _rng_for(((20, natural), *((sides, face) for face in faces)))
    (event,) = [
        e
        for e in resolve(rolled, action).events
        if isinstance(e, DamageDealt) and e.cause == "attack" and e.target_id == U2
    ]
    assert event.crit is (natural == 20)
    assert sum(event.rolls) == sum(faces)
    return event


def _outcomes(
    state: BattleState,
    action: Attack | UseSkill,
    natural: int,
    dice: tuple[int, int],
) -> dict[int, tuple[int, DamageDealt]]:
    """每個骰值總和 → （組合數, 引擎實際的事件）。"""
    count, sides = dice
    ways: dict[int, int] = {}
    sample: dict[int, tuple[int, ...]] = {}
    for faces in product(range(1, sides + 1), repeat=count):
        total = sum(faces)
        ways[total] = ways.get(total, 0) + 1
        sample.setdefault(total, faces)
    return {t: (ways[t], _dealt(state, action, natural, sides, sample[t])) for t in sorted(ways)}


def _mean(outcomes: Mapping[int, tuple[int, DamageDealt]]) -> Fraction:
    total = sum(n * (e.amount - e.absorbed) for n, e in outcomes.values())
    return Fraction(total, sum(n for n, _ in outcomes.values()))


def _damage_dice(state: BattleState, mode: Mode) -> tuple[int, int]:
    if mode == "attack":
        dice = attack_dice(state, state.units[U1], backstab=False)
        return dice.count, dice.sides
    return 1, 6


@pytest.mark.parametrize("mode", ["attack", "skill"])
@pytest.mark.parametrize("row", ROWS, ids=lambda r: r.name)
def test_preview_table_matches_engine(
    mode: Mode, row: Row, monkeypatch: pytest.MonkeyPatch
) -> None:
    if row.zero_taken:
        monkeypatch.setattr(handlers, "damage_taken_permille", lambda *_: 0)
    state, action = _scene(mode, row)
    p = preview(state, action)
    if mode == "attack":
        damage, hit, crit = p.damage, p.hit_chance, p.crit_chance
    else:
        (target,) = p.targets
        damage, hit, crit = target.damage, target.hit_chance, target.crit_chance
    assert damage is not None and hit is not None and crit is not None
    assert hit > 0 and crit > 0
    count, sides = _damage_dice(state, mode)
    normal = _outcomes(state, action, 19, (count, sides))
    crits = _outcomes(state, action, 20, (count * 2, sides))
    events = [e for _, e in (*normal.values(), *crits.values())]
    assert all(row.check(e) for e in events)
    expected = ((hit - crit) * _mean(normal) + crit * _mean(crits)) / hit
    assert damage.expected_if_hit == expected
    lowest, highest = normal[min(normal)][1], crits[max(crits)][1]
    assert damage.minimum == lowest.amount - lowest.absorbed
    assert damage.maximum == highest.amount - highest.absorbed
    if row.all_zero:  # 護陣 ×0：預覽與實際都是 0，不是最低傷害
        assert damage.expected_if_hit == 0 and damage.maximum == 0


_DIVISOR = PERMILLE * PPM * PERMILLE * PERMILLE * PPM
type _Args = tuple[int, int, int, int, int, int]  # raw, mod, weather, mult, status, minimum


def _legacy_engine(args: _Args, ward: int) -> int:
    """改動前 ``effects/handlers.py`` 的寫法。"""
    raw, mod, weather, mult, status, minimum = args
    return max(raw * mod * weather * mult * status // _DIVISOR, minimum) if ward > 0 else 0


def _legacy_preview(args: _Args) -> int:
    """改動前 ``preview.py`` 兩處的寫法（沒有護陣判斷）。"""
    raw, mod, weather, mult, status, minimum = args
    return max(raw * mod * weather * mult * status // _DIVISOR, minimum)


def _formula(args: _Args, ward: int) -> int:
    raw, mod, weather, mult, status, minimum = args
    return rolled_damage_amount(
        raw,
        mod_ppm=mod,
        weather=weather,
        multiplier=mult,
        status_ppm=status,
        ward=ward,
        min_damage=minimum,
    )


# 實際可能的範圍：太寬的話乘積多半落在最低傷害，比對不出捨去順序的差異
_RAW = st.integers(-5_000, 300_000)  # 撞擊的固定值修正可能是負的
_MOD = st.integers(250_000, 3_000_000)
_WEATHER = st.integers(500, 2000)
_MULT = st.integers(250, 5000)
_STATUS = st.one_of(st.just(0), st.integers(250_000, 6_000_000))
_MINIMUM = st.integers(0, 2)
_ARGS = st.tuples(_RAW, _MOD, _WEATHER, _MULT, _STATUS, _MINIMUM)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((1500, PPM, 1000, 1000, PPM, 1), 1),  # 1.5 捨去
        ((1500, 1_500_000, 1000, 1000, PPM, 1), 2),  # 1.5 × 1.5 = 2.25：不能先把基底捨成 1
        ((2_000_000, 1_000_500, 1000, 1000, PPM, 0), 2001),  # 元素修正的零頭不能先捨去
        ((1999, 1_250_000, 1200, 1100, 1_250_000, 1), 4),  # 4.1229…
        ((100, PPM, 1000, 1000, PPM, 1), 1),  # 0.1 → 最低傷害
        ((-1000, PPM, 1000, 1000, PPM, 1), 1),  # 負的基底 → 最低傷害
    ],
)
def test_formula_hand_computed_values(args: _Args, expected: int) -> None:
    """手算的固定值：表格測試的預覽與引擎共用公式，公式本身寫錯只有這裡與舊寫法比對抓得到。"""
    assert _formula(args, PERMILLE) == expected


@given(_ARGS, st.integers(0, 2000))
def test_formula_equals_legacy_engine(args: _Args, ward: int) -> None:
    assert _formula(args, ward) == _legacy_engine(args, ward)


@given(_ARGS, st.integers(1, 2000))
def test_formula_equals_legacy_preview_when_not_warded_to_zero(args: _Args, ward: int) -> None:
    assert _formula(args, ward) == _legacy_preview(args)


@given(st.integers(0, 300), st.integers(-60, 300), st.integers(0, 2_000_000))
def test_raw_damage_equals_legacy(roll_total: int, flat: int, scaled: int) -> None:
    assert raw_damage_permille(roll_total, flat, scaled) == (roll_total + flat) * 1000 + scaled


@given(_RAW, _MOD, _WEATHER, _MULT, _MINIMUM)
def test_ward_zero_ignores_min_damage_but_status_zero_does_not(
    raw: int, mod: int, weather: int, mult: int, minimum: int
) -> None:
    """``ward`` 才是 ×0 的判斷依據：``status_ppm == 0`` 而 ``ward > 0`` 時仍是最低傷害。"""
    args = {"mod_ppm": mod, "weather": weather, "multiplier": mult, "min_damage": minimum}
    assert rolled_damage_amount(raw, status_ppm=0, ward=0, **args) == 0
    assert rolled_damage_amount(raw, status_ppm=0, ward=PERMILLE, **args) == minimum
