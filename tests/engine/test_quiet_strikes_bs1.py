"""BS-1：連續背刺——隱蔽出手不轉向（B）＋「無聲」（C）（#157，``docs/design/06-技能.md`` 6.21.1、
``05-戰鬥.md`` 5.1「朝向與背刺」）。

每列一條規則句、實際跑引擎：一般近戰照常轉向；B 從隱蔽中出手（普攻、武器技）不轉向、出手後照舊
脫離隱蔽；C 無聲（修正規則 ``silent_strike``）手持匕首或雙匕首時普攻、武器技、反應攻擊不轉向，換別
的武器、形態中的天生武器不成立；只管自己的攻擊（隊友從正面打照轉、目標在自己回合出手照轉）；影纏
手持匕首類時給 2 回合無聲、拿別的武器不給；預覽與紀錄表達「背刺・無聲（不會轉身）」；AI 持有無聲時
留在背後加分。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import U1, U2, U3, of
from tests.engine.test_facing_backstab import conceal, duel, log_text, rolled
from tests.engine.test_intercept import scene
from tests.engine.test_passive_triggers import always
from trpg.engine import Attack, Move, ResolveResult, UseSkill, preview, resolve
from trpg.engine.ai.parts import silent_behind_extra
from trpg.engine.events import AttackIntercepted, EffectFizzled, SkillGranted, StatusRemoved
from trpg.engine.quiet_strikes import no_turn_reason
from trpg.engine.state import BattleState
from trpg.shared.types import Pos, Team, UnitId

SILENT = "skill_silent_step"
BIND = "skill_shadow_bind"
PINCER = "skill_pincer_strike"
"""一般的近戰武器技（單體）。"""


def silent_duel(weapon: str = "dagger", **kw: object) -> BattleState:
    """U1 在 U2 背後 (4, 3)（U2 朝西），裝備無聲步。"""
    skills = kw.pop("skills", (SILENT, PINCER))
    return duel((4, 3), foe_facing="west", weapon=weapon, skills=skills, **kw)  # type: ignore[arg-type]


def attack(
    state: BattleState, unit: UnitId = U1, target: UnitId = U2, natural: int = 10
) -> ResolveResult:
    return resolve(with_rolls(state, [(20, natural)]), Attack(unit_id=unit, target_id=target))


# ---------------------------------------------------------------------------
# 一般規則不變
# ---------------------------------------------------------------------------


def test_a_plain_melee_backstab_still_turns_the_target() -> None:
    result = attack(duel((4, 3), foe_facing="west", weapon="dagger"))
    assert rolled(result)[0].backstab == 2 and rolled(result)[0].no_turn is None
    assert result.state.units[U2].facing == "east"
    assert "不會轉身" not in log_text(result)


# ---------------------------------------------------------------------------
# B 從隱蔽中出手
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weapon", ["dagger", "one_handed_sword", "greatsword"])
def test_a_concealed_melee_attack_does_not_turn_the_target_with_any_weapon(weapon: str) -> None:
    state = conceal(duel((4, 3), foe_facing="west", weapon=weapon))
    result = attack(state)
    roll = rolled(result)[0]
    assert roll.ambush == 2 and roll.no_turn == "concealed"
    assert result.state.units[U2].facing == "west"  # 沒轉身：U1 還在背後
    assert not result.state.units[U1].has_status("concealed")  # 出手後照舊脫離隱蔽
    removed = [e for e in of(result, StatusRemoved) if e.target_id == U1]
    assert [e.reason for e in removed] == ["ambushed"]
    again = attack(give_turn(result.state, U1))  # 再打一次：沒有隱蔽，背刺之後照常轉身
    assert rolled(again)[0].backstab == 2 and rolled(again)[0].no_turn is None
    assert again.state.units[U2].facing == "east"


def test_a_concealed_weapon_skill_does_not_turn_the_target() -> None:
    state = conceal(duel((4, 3), foe_facing="west", weapon="one_handed_sword", skills=(PINCER,)))
    action = UseSkill(unit_id=U1, skill_id=PINCER, target_id=U2)
    result = resolve(with_rolls(state, [(20, 10)] * 3), action)
    assert {r.no_turn for r in rolled(result)} == {"concealed"}
    assert result.state.units[U2].facing == "west"


def test_concealed_enemies_also_attack_without_turning_their_target() -> None:
    state = give_turn(duel((4, 3), foe_facing="east", weapon="dagger"), U2)
    state.units[U1].facing = "east"  # U2 在 U1 背後
    state.units[U2].statuses.append(conceal(state).units[U1].statuses[-1])
    result = attack(state, unit=U2, target=U1)
    assert rolled(result, U2)[0].no_turn == "concealed"
    assert result.state.units[U1].facing == "east"


# ---------------------------------------------------------------------------
# C 無聲
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weapon", ["dagger", "dual_dagger"])
def test_silent_basic_attacks_keep_the_target_facing_away(weapon: str) -> None:
    state = silent_duel(weapon)
    first = attack(state)
    assert all(r.no_turn == "silent" and r.backstab == 2 for r in rolled(first))
    assert first.state.units[U2].facing == "west"
    second = attack(give_turn(first.state, U1))  # 留在背後：下一下還是背刺
    assert rolled(second)[0].backstab == 2
    assert "［背刺・無聲（不會轉身）］" in log_text(second)


@pytest.mark.parametrize("weapon", ["one_handed_sword", "spear", "greatsword"])
def test_silent_needs_a_dagger_class_weapon(weapon: str) -> None:
    result = attack(silent_duel(weapon))
    assert rolled(result)[0].no_turn is None
    assert result.state.units[U2].facing == "east"


def test_silent_weapon_skills_do_not_turn_the_target() -> None:
    state = silent_duel()
    action = UseSkill(unit_id=U1, skill_id=PINCER, target_id=U2)
    result = resolve(with_rolls(state, [(20, 10)] * 3), action)
    assert {r.no_turn for r in rolled(result)} == {"silent"}
    assert result.state.units[U2].facing == "west"


def test_silent_reaction_attacks_do_not_turn_the_target() -> None:
    # U2 從 U1 身邊走開：U1 的藉機攻擊（反應攻擊）帶無聲
    m = make_map("000000\n000000", ally=[(1, 0)], enemy=[(2, 0)])
    guard = template("hero_fighter", skills=[SILENT])
    mover = template("bandit", max_hp=300, reactions=[])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 0), guard, weapon="dagger", skills=None),
            spawn(Team.ENEMY, (2, 0), mover),
        ],
    )
    moving = give_turn(state, U2)
    path = (Pos(x=2, y=0), Pos(x=3, y=0), Pos(x=4, y=0))
    result = resolve(moving, Move(unit_id=U2, path=path))
    (opportunity,) = rolled(result)
    assert opportunity.no_turn == "silent"


def test_without_the_modifier_nobody_is_silent() -> None:
    state = duel((4, 3), foe_facing="west", weapon="dagger")
    assert no_turn_reason(state, state.units[U1]) is None
    silent = silent_duel()
    assert no_turn_reason(silent, silent.units[U1]) == "silent"
    passive = no_turn_reason(silent, silent.units[U1], modified=False)
    assert passive is None  # 被動、陷阱觸發不是「你的動作」


def test_silent_only_covers_its_holders_own_attacks() -> None:
    # 隊友 U3 從正面（西邊）打：U2 照常轉向 U3
    state = silent_duel(extra=((Team.ALLY, (2, 3)),))
    after = attack(state).state
    assert after.units[U2].facing == "west"
    teammate = attack(give_turn(after, U3), unit=U3)
    assert rolled(teammate, U3)[0].no_turn is None
    assert teammate.state.units[U2].facing == "west"  # 面向 (2, 3) 的 U3
    # 再讓 U3 從北邊打：U2 轉向北，U1 不再在背後
    north = silent_duel(extra=((Team.ALLY, (3, 2)),))
    turned = attack(give_turn(north, U3), unit=U3)
    assert turned.state.units[U2].facing == "north"


def test_the_target_still_turns_on_its_own_turn() -> None:
    state = silent_duel()
    after = attack(state).state
    assert after.units[U2].facing == "west"
    counter = attack(give_turn(after, U2), unit=U2, target=U1)  # 回頭打刺客：反制
    assert counter.state.units[U2].facing == "east"
    back = attack(give_turn(counter.state, U1))
    assert rolled(back)[0].backstab == 0  # 刺客得再繞背


def test_a_guardian_who_takes_a_silent_strike_does_not_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(attacker_skills=(SILENT,))
    state.units[U1].weapon = library().weapons["dagger"]
    state.units[U2].facing = "north"
    state.units[U3].facing = "south"
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert of(result, AttackIntercepted)
    assert result.state.units[U2].facing == "north"
    assert result.state.units[U3].facing == "south"


# ---------------------------------------------------------------------------
# 影纏：主動技能給 2 回合無聲
# ---------------------------------------------------------------------------


def test_shadow_bind_grants_silence_with_a_dagger() -> None:
    state = duel((4, 3), foe_facing="west", weapon="dagger", skills=(BIND,))
    action = UseSkill(unit_id=U1, skill_id=BIND, target_id=U2)
    result = resolve(with_rolls(state, [(20, 10)]), action)
    (granted,) = of(result, SkillGranted)
    assert (granted.skill_id, granted.duration) == (
        SILENT,
        3,
    )  # BS-3：資料持續值＝顯示的 2 回合 + 1
    # 影纏這一下本身還沒有無聲（施放當下還沒獲得）：U2 轉身
    assert result.state.units[U2].facing == "east"
    hunter = result.state.clone()
    hunter.units[U2].facing = "west"
    follow = attack(give_turn(hunter, U1))
    assert rolled(follow)[0].no_turn == "silent"
    assert follow.state.units[U2].facing == "west"


def test_shadow_bind_grants_nothing_without_a_dagger() -> None:
    state = duel((4, 3), foe_facing="west", weapon="one_handed_sword", skills=(BIND,))
    action = UseSkill(unit_id=U1, skill_id=BIND, target_id=U2)
    result = resolve(with_rolls(state, [(20, 10)]), action)
    assert not of(result, SkillGranted)
    assert result.state.units[U1].granted_skills == ()


def test_shadow_bind_fizzles_when_silent_step_is_equipped() -> None:
    state = duel((4, 3), foe_facing="west", weapon="dagger", skills=(BIND, SILENT))
    action = UseSkill(unit_id=U1, skill_id=BIND, target_id=U2)
    result = resolve(with_rolls(state, [(20, 10)]), action)
    assert [e.reason for e in of(result, EffectFizzled)] == ["already_equipped"]


# ---------------------------------------------------------------------------
# 預覽與紀錄
# ---------------------------------------------------------------------------


def test_the_preview_says_backstab_silent_does_not_turn() -> None:
    state = silent_duel()
    view = preview(state, Attack(unit_id=U1, target_id=U2))
    assert view.backstab == (U2,) and view.no_turn == (U2,)
    assert view.no_turn_reason == "silent"
    assert any(n.startswith("背刺・無聲（不會轉身）") for n in view.notes)
    hidden = preview(conceal(duel((3, 4), weapon="dagger")), Attack(unit_id=U1, target_id=U2))
    assert hidden.no_turn_reason == "concealed" and hidden.backstab == ()
    assert any(n.startswith("從隱蔽中出手（不會轉身）") for n in hidden.notes)
    plain = preview(duel((4, 3), weapon="dagger"), Attack(unit_id=U1, target_id=U2))
    assert plain.no_turn == () and plain.no_turn_reason is None


def test_the_no_turn_field_is_left_out_of_the_log_when_unset() -> None:
    result = attack(duel((4, 3), foe_facing="west", weapon="dagger"))
    dumped = rolled(result)[0].model_dump(mode="json")
    assert "no_turn" not in dumped
    silent = rolled(attack(silent_duel()))[0].model_dump(mode="json")
    assert silent["no_turn"] == "silent"


# ---------------------------------------------------------------------------
# AI：持有無聲時留在背後
# ---------------------------------------------------------------------------


def test_the_ai_values_staying_behind_when_silent() -> None:
    lib = library()
    weights = next(p for p in lib.ai_profiles.profiles if p.id == "brute").weights
    assert weights.silent_behind > 0
    state = silent_duel()
    foes = [u for u in state.living_units() if u.team is Team.ENEMY]
    assert silent_behind_extra(state, state.units[U1], weights, foes) == weights.silent_behind
    side = state.units[U1].clone()
    side.pos = Pos(x=3, y=4)
    assert silent_behind_extra(state, side, weights, foes) == 0
    sword = silent_duel("one_handed_sword")
    assert silent_behind_extra(sword, sword.units[U1], weights, foes) == 0
    plain = duel((4, 3), foe_facing="west", weapon="dagger")
    assert silent_behind_extra(plain, plain.units[U1], weights, foes) == 0
