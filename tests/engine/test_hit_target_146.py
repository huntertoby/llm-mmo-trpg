"""#146 命中門檻 8（Phase CB-1）：實際跑引擎的邊界表格與預覽一致性。

攻擊、技能攻擊、控制對抗、戰技對抗都讀 ``core.hit_target``：總值 7 失敗、8 成功；自然 1 必失手、
自然 20 必命中；引擎窮舉 d20 的成功率要和預覽顯示的一模一樣。
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of, script_rolls
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, Shove, Trip, UseSkill, preview, resolve
from trpg.engine.events import AttackRolled, ManeuverRolled, StatusSaveRolled
from trpg.shared.types import Team

TARGET = 8
BOUNDARY = [(TARGET - 1, False), (TARGET, True)]
FLAT3 = "000\n000\n000"
SINGLE = {"type": "single", "range": 5}
HIT_DIE = 19  # 技能的命中骰（必中且不暴擊），後面接抵抗骰


def _natural_for(total: int, modifier: int, proficiency: int) -> int:
    """要讓總值剛好是 ``total`` 的自然骰（必須避開必中、必失手的 1 與 20）。"""
    natural = total - modifier - proficiency
    assert 1 < natural < 20, f"總值 {total} 要自然骰 {natural}，碰到必中或必失手"
    return natural


def test_content_uses_the_new_target() -> None:
    assert library().ruleset.core.hit_target == TARGET


# ---------------------------------------------------------------------------
# 攻擊（普攻）
# ---------------------------------------------------------------------------


def _attack_state(*, attacker: dict[str, int] | None = None, dex: int | None = None) -> BattleState:
    m = make_map(FLAT3)
    target = no_reactions() if dex is None else no_reactions(attributes={"dex": dex})
    hero = "hero_fighter" if attacker is None else template("hero_fighter", attributes=attacker)
    return give_turn(
        make_state(m, [spawn(Team.ALLY, (0, 1), hero), spawn(Team.ENEMY, (1, 1), target)]), U1
    )


def _swing(state: BattleState, natural: int) -> AttackRolled:
    result = resolve(with_rolls(state, [(20, natural)]), Attack(unit_id=U1, target_id=U2))
    (rolled,) = of(result, AttackRolled)
    assert rolled.natural == natural
    return rolled


@pytest.mark.parametrize("dex", [None, 20, 40], ids=["same_level", "harder", "hardest"])
@pytest.mark.parametrize(("total", "hits"), BOUNDARY)
def test_attack_boundary(dex: int | None, total: int, hits: bool) -> None:
    state = _attack_state(dex=dex)
    probe = _swing(state, 10)
    rolled = _swing(state, _natural_for(total, probe.hit_modifier, probe.proficiency))
    assert rolled.total == total
    assert rolled.target_number == TARGET
    assert rolled.hit is hits


def test_attack_natural_one_misses_even_above_the_target() -> None:
    rolled = _swing(_attack_state(attacker={"str": 500}), 1)
    assert rolled.total >= TARGET and not rolled.hit


def test_attack_natural_twenty_hits_at_the_lowest_modifier() -> None:
    rolled = _swing(_attack_state(dex=500), 20)
    assert rolled.hit_modifier == -library().ruleset.core.hit_mod_cap
    assert rolled.hit


# ---------------------------------------------------------------------------
# 技能攻擊
# ---------------------------------------------------------------------------


def _damage_skill() -> SkillDef:
    return make_skill(SID, SINGLE, [{"type": "damage", "dice": "1d4", "element": "fire"}])


def _strike(state: BattleState, natural: int) -> AttackRolled:
    result = cast(with_rolls(state, [(20, natural)]), target_id=U2)
    (rolled,) = of(result, AttackRolled)
    return rolled


@pytest.mark.parametrize(("total", "hits"), BOUNDARY)
def test_skill_attack_boundary(total: int, hits: bool) -> None:
    state = battle(_damage_skill(), [(5, 3)])
    probe = _strike(state, 10)
    rolled = _strike(state, _natural_for(total, probe.hit_modifier, probe.proficiency))
    assert (rolled.total, rolled.target_number, rolled.hit) == (total, TARGET, hits)


# ---------------------------------------------------------------------------
# 控制對抗（狀態抵抗）
# ---------------------------------------------------------------------------


def _control_state(strength: int | None = None) -> BattleState:
    """施放者 U1（法師，智力 16）對盜賊 U2 定身；抵抗屬性是力量。"""
    skill = make_skill(SID, SINGLE, [{"type": "apply_status", "status": "root"}])
    foe = no_reactions() if strength is None else no_reactions(attributes={"str": strength})
    return battle(skill, [(5, 3, foe)])


def _save(state: BattleState, natural: int, monkeypatch: pytest.MonkeyPatch) -> StatusSaveRolled:
    script_rolls(monkeypatch, [HIT_DIE, natural])
    (save,) = of(cast(state, target_id=U2), StatusSaveRolled)
    assert save.natural == natural
    return save


@pytest.mark.parametrize("strength", [None, 24], ids=["normal", "resistant"])
@pytest.mark.parametrize(("total", "applied"), BOUNDARY)
def test_control_boundary(
    strength: int | None, total: int, applied: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _control_state(strength)
    probe = _save(state, 10, monkeypatch)
    save = _save(state, _natural_for(total, probe.modifier, probe.proficiency), monkeypatch)
    assert (save.total, save.target_number, save.applied) == (total, TARGET, applied)


def test_control_natural_one_fails_even_above_the_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = _save(_control_state(1), 1, monkeypatch)
    assert save.total >= TARGET and not save.applied


def test_control_natural_twenty_succeeds_at_the_lowest_modifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = _save(_control_state(500), 20, monkeypatch)
    assert save.modifier == -library().ruleset.core.hit_mod_cap
    assert save.applied


# ---------------------------------------------------------------------------
# 戰技對抗（推擊、絆倒）
# ---------------------------------------------------------------------------

type Maneuver = Callable[..., Shove | Trip]
MANEUVERS: list[tuple[Maneuver, str]] = [(Shove, "str"), (Trip, "dex")]


def _maneuver_state(attr: str, value: int | None = None) -> BattleState:
    target = no_reactions() if value is None else no_reactions(attributes={attr: value})
    m = make_map("0000\n0000\n0000")
    return give_turn(
        make_state(
            m, [spawn(Team.ALLY, (0, 1), "hero_fighter"), spawn(Team.ENEMY, (1, 1), target)]
        ),
        U1,
    )


def _contest(state: BattleState, action: Maneuver, natural: int) -> ManeuverRolled:
    result = resolve(with_rolls(state, [(20, natural)]), action(unit_id=U1, target_id=U2))
    (rolled,) = of(result, ManeuverRolled)
    assert rolled.natural == natural
    return rolled


@pytest.mark.parametrize(("action", "attr"), MANEUVERS, ids=["shove", "trip"])
@pytest.mark.parametrize(("total", "success"), BOUNDARY)
def test_maneuver_boundary(action: Maneuver, attr: str, total: int, success: bool) -> None:
    state = _maneuver_state(attr)
    probe = _contest(state, action, 10)
    rolled = _contest(state, action, _natural_for(total, probe.modifier, probe.proficiency))
    assert (rolled.total, rolled.target_number, rolled.success) == (total, TARGET, success)


@pytest.mark.parametrize(("action", "attr"), MANEUVERS, ids=["shove", "trip"])
def test_maneuver_natural_one_fails_even_above_the_target(action: Maneuver, attr: str) -> None:
    rolled = _contest(_maneuver_state(attr, 1), action, 1)
    assert rolled.total >= TARGET and not rolled.success


@pytest.mark.parametrize(("action", "attr"), MANEUVERS, ids=["shove", "trip"])
def test_maneuver_natural_twenty_succeeds_at_the_lowest_modifier(
    action: Maneuver, attr: str
) -> None:
    rolled = _contest(_maneuver_state(attr, 500), action, 20)
    assert rolled.modifier == -library().ruleset.core.hit_mod_cap
    assert rolled.success


# ---------------------------------------------------------------------------
# 預覽與引擎一致：窮舉 d20，引擎實際算出的成功率＝預覽顯示的成功率
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dex", [None, 20, 40], ids=["same_level", "harder", "hardest"])
def test_preview_matches_engine_for_attack(dex: int | None) -> None:
    state = _attack_state(dex=dex)
    wins = sum(_swing(state, n).hit for n in range(1, 21))
    shown = preview(state, Attack(unit_id=U1, target_id=U2)).hit_chance
    assert shown == Fraction(wins, 20)


def test_preview_matches_engine_for_skill_attack() -> None:
    state = battle(_damage_skill(), [(5, 3)])
    wins = sum(_strike(state, n).hit for n in range(1, 21))
    (target,) = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets
    assert target.hit_chance == Fraction(wins, 20)


@pytest.mark.parametrize("strength", [None, 24], ids=["normal", "resistant"])
def test_preview_matches_engine_for_control(
    strength: int | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _control_state(strength)
    (target,) = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).targets
    (chance,) = target.status_chances
    wins = sum(_save(state, n, monkeypatch).applied for n in range(1, 21))
    assert chance.apply_chance == Fraction(wins, 20)


@pytest.mark.parametrize(("action", "attr"), MANEUVERS, ids=["shove", "trip"])
@pytest.mark.parametrize("value", [None, 24], ids=["normal", "resistant"])
def test_preview_matches_engine_for_maneuver(
    action: Maneuver, attr: str, value: int | None
) -> None:
    state = _maneuver_state(attr, value)
    wins = sum(_contest(state, action, n).success for n in range(1, 21))
    assert preview(state, action(unit_id=U1, target_id=U2)).hit_chance == Fraction(wins, 20)
