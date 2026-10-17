"""``preview`` 對技能的預測與實際結算一致（docs/phases/Phase2A計畫.md 5.5 第 7 條）。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4, script_rolls
from trpg.engine import BattleState, UseSkill, preview, resolve, state_to_json
from trpg.engine.events import AttackRolled, DamageDealt, Healed
from trpg.engine.preview import outcomes
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Team

ASHEN = "skill_ashen_oath"
FIRE_BOLT = "skill_fire_bolt"
CHAIN = "skill_chain_lightning"
SANCTUARY = "skill_sanctuary"


def _state(
    skills: list[str],
    foes: list[tuple[int, int]],
    *,
    base: str = "hero_mage",
    caster: tuple[int, int] = (1, 3),
    allies: list[tuple[int, int]] | None = None,
    objects: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    allies = allies or []
    m = make_map(FLAT7, ally=[caster, *allies], enemy=foes, objects=objects)
    spawns = [spawn(Team.ALLY, caster, caster_template(skills, base=base))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def _expected_hit_chance(roll: AttackRolled) -> Fraction:
    bonus = roll.total - roll.natural
    wins = sum(
        1 for nat in range(1, 21) if nat == 20 or (nat != 1 and nat + bonus >= roll.target_number)
    )
    return Fraction(wins, 20)


def test_preview_of_a_single_target_skill_brackets_the_actual_damage() -> None:
    state = _state([FIRE_BOLT], [(4, 3)])
    action = UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2)
    before = state_to_json(state)
    p = preview(state, action)
    assert state_to_json(state) == before  # 不修改狀態、不消耗亂數
    (target,) = p.targets
    assert target.unit_id == U2 and not target.ally and target.damage is not None
    low = resolve(with_rolls(state, [(20, 19), (8, 1), (8, 1)]), action)
    high = resolve(with_rolls(state, [(20, 20), (8, 8), (8, 8), (8, 8), (8, 8)]), action)
    (low_dmg,) = [e for e in low.events if isinstance(e, DamageDealt) and e.cause == "attack"]
    (high_dmg,) = [e for e in high.events if isinstance(e, DamageDealt) and e.cause == "attack"]
    assert low_dmg.amount == target.damage.minimum
    assert high_dmg.amount == target.damage.maximum
    assert target.damage.minimum < target.damage.expected_if_hit < target.damage.maximum
    roll = next(e for e in low.events if isinstance(e, AttackRolled))
    assert target.hit_chance == _expected_hit_chance(roll)
    assert target.crit_chance == Fraction(1, 20) if target.hit_chance == 1 else True
    assert p.affected_tiles == ((4, 3),) and p.affected_units == (U2,)


def test_preview_expected_damage_matches_exhaustive_enumeration() -> None:
    state = _state([FIRE_BOLT], [(4, 3)])
    action = UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2)
    (target,) = preview(state, action).targets
    assert target.damage is not None
    assert target.damage.expected == target.damage.expected_if_hit * target.hit_chance
    # 2d8 + 智力 × 0.5：命中（不暴擊）的期望值 = (9 + 智力 × 0.5)，暴擊為 2 倍骰（18 + …）
    attr = state.units[U1].attributes["int"]  # type: ignore[index]
    flat = Fraction(attr, 2)
    crit_share = target.crit_chance / target.hit_chance
    expected = (1 - crit_share) * (9 + flat) + crit_share * (18 + flat)
    assert abs(target.damage.expected_if_hit - expected) < 1  # 每顆骰各自無條件捨去 ≤ 1


def test_preview_of_an_area_skill_lists_every_target_tile_and_the_explosion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(
        [ASHEN],
        [(2, 3), (3, 2), (2, 4)],
        objects=((3, 3, "oil_barrel"),),
    )
    action = UseSkill(unit_id=U1, skill_id=ASHEN, direction="east")
    p = preview(state, action)
    assert [t.unit_id for t in p.targets] == [U2, U3]  # (2, 4) 不在錐形內
    cone = {(2, 3), (3, 2), (3, 3), (3, 4), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5)}
    assert cone <= set(p.affected_tiles)
    assert U4 in p.affected_units  # 爆炸波及的單位
    assert any(o.kind == "object_exploded" for o in p.certain)  # 傷害物件不需要擲骰
    # 實際結算（命中、最小骰）的結果包含全部「確定」的連鎖；任何結果都不超出「確定＋可能」
    script_rolls(monkeypatch, [19, 19] + [1] * 20)
    low = resolve(state, action)
    assert set(p.certain) <= set(outcomes(list(low.events)))
    script_rolls(monkeypatch, [20, 20] + [6] * 20)
    high = resolve(state, action)
    assert set(outcomes(list(high.events))) <= set(p.certain) | set(p.possible)
    first = next(e for e in low.events if isinstance(e, DamageDealt) and e.cause == "attack")
    expected = next(t for t in p.targets if t.unit_id == first.target_id).damage
    assert expected is not None and first.amount == expected.minimum


def test_preview_of_a_chain_skill_covers_the_whole_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state([CHAIN], [(4, 3), (4, 4), (5, 3), (6, 6)], base="hero_stormcaller")
    action = UseSkill(unit_id=U1, skill_id=CHAIN, target_id=U2)
    p = preview(state, action)
    assert [t.unit_id for t in p.targets] == [U2, U3, U4]
    assert set(p.affected_units) == {U2, U3, U4}
    script_rolls(monkeypatch, [19, 19, 19] + [1] * 20)
    actual = resolve(state, action)
    hits = {
        e.target_id: e.amount
        for e in actual.events
        if isinstance(e, DamageDealt) and e.cause == "attack"
    }
    assert hits == {t.unit_id: t.damage.minimum for t in p.targets if t.damage}


def test_preview_of_a_heal_reports_the_range_per_ally() -> None:
    state = _state([SANCTUARY], [(6, 6)], base="hero_stormcaller", allies=[(2, 3)])
    state.units[U2].hp = 5
    action = UseSkill(unit_id=U1, skill_id=SANCTUARY)
    p = preview(state, action)
    assert not p.targets  # 友方與自己不擲骰
    (entry,) = [h for h in p.healed if h[0] == U2]
    low = resolve(with_rolls(state, [(6, 1), (6, 1)]), action)
    healed_low = next(e.amount for e in low.events if isinstance(e, Healed) and e.target_id == U2)
    assert healed_low == entry[1]
    assert entry[1] <= entry[2]


def test_preview_rejects_illegal_skill_actions() -> None:
    state = _state([FIRE_BOLT], [(6, 6)])
    with pytest.raises(IllegalActionError, match="目標超出射程"):
        preview(state, UseSkill(unit_id=U1, skill_id=FIRE_BOLT, target_id=U2))
    with pytest.raises(IllegalActionError, match="沒有裝備"):
        preview(state, UseSkill(unit_id=U1, skill_id=ASHEN, direction="east"))
