"""BS-3：影纏的「接下來 2 回合」是 2 個完整的自己回合（``docs/design/06-技能.md`` 6.21.1「BS-1 後的
細節」第 1 點）。

資料上的持續值是 3（施放那回合結束先扣 1），之後兩個自己的回合都有無聲、第二個回合結束才消失；
技能說明與預覽仍寫「2 回合」。
"""

from __future__ import annotations

from tests.engine.helpers import give_turn, library, with_rolls
from tests.engine.skill_helpers import U1, U2, of
from tests.engine.test_facing_backstab import duel, rolled
from trpg.engine import Attack, EndTurn, UseSkill, preview, resolve
from trpg.engine.events import SkillGrantExpired
from trpg.engine.grants import granted_remaining
from trpg.engine.state import BattleState
from trpg.narrative.skills import skill_card

SILENT = "skill_silent_step"
BIND = "skill_shadow_bind"


def _cast() -> BattleState:
    state = duel((4, 3), foe_facing="west", weapon="dagger", skills=(BIND,))
    action = UseSkill(unit_id=U1, skill_id=BIND, target_id=U2)
    return resolve(with_rolls(state, [(20, 10)]), action).state


def _end_own_turn(state: BattleState) -> BattleState:
    return resolve(give_turn(state, U1), EndTurn(unit_id=U1)).state


def _silent_attack_from_behind(state: BattleState) -> str | None:
    s = give_turn(state, U1)
    s.units[U2].facing = "west"
    result = resolve(with_rolls(s, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    return rolled(result)[0].no_turn


def test_shadow_bind_lasts_two_full_own_turns_after_the_cast() -> None:
    state = _cast()
    assert granted_remaining(state.units[U1], SILENT) == 3
    state = _end_own_turn(state)  # 施放那回合結束
    for remaining in (2, 1):  # 之後兩個完整的自己回合都有無聲
        assert granted_remaining(state.units[U1], SILENT) == remaining
        assert _silent_attack_from_behind(state) == "silent"
        state = _end_own_turn(state)
    assert granted_remaining(state.units[U1], SILENT) is None
    assert _silent_attack_from_behind(state) is None


def test_the_grant_expires_at_the_end_of_the_second_full_turn() -> None:
    state = _end_own_turn(_end_own_turn(_cast()))
    last = resolve(give_turn(state, U1), EndTurn(unit_id=U1))
    assert [e.skill_id for e in of(last, SkillGrantExpired)] == [SILENT]


def test_the_card_and_the_preview_still_say_two_rounds() -> None:
    lib = library()
    text = str(skill_card(lib, lib.skills[BIND]).model_dump())
    assert "接下來 2 回合獲得「無聲步」" in text
    assert "持續 3 輪" not in text
    state = duel((4, 3), foe_facing="west", weapon="dagger", skills=(BIND,))
    view = preview(state, UseSkill(unit_id=U1, skill_id=BIND, target_id=U2))
    assert [(g.skill_id, g.duration) for g in view.grants] == [(SILENT, 2)]


def test_other_grants_keep_their_data_duration_in_the_card() -> None:
    lib = library()
    text = str(skill_card(lib, lib.skills["skill_wing_spread"]).model_dump())
    assert "持續 3 輪" in text
