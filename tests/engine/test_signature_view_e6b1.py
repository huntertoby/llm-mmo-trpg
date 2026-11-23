"""E6-b1 第 4 項：檢視層寫出因為名額標灰的原因（08 8.27、8.30 第 4 點，#180）。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from tests.engine.test_gear_g3b import FIRE_MENDS, WAKE
from tests.engine.test_signature_cap_e6b1 import _battle, grant
from tests.engine.test_signature_limits_e6b1 import _arena
from trpg.content.equipment import EquippedAffix
from trpg.engine.state import BattleState
from trpg.engine.view import (
    RULE_LIMITED_ZH,
    SIGNATURE_LIMITED_ZH,
    AffixLineView,
    project_for,
)
from trpg.shared.types import Team, UnitId

U1 = UnitId("unit_0001")


def lines(state: BattleState, viewer: Team = Team.ALLY) -> dict[str, AffixLineView]:
    me = next(u for u in project_for(state, viewer).units if u.id == U1)
    return {f"{s.slot}:{a.affix_id}": a for s in me.equipment for a in s.affixes}


def test_rule_wording_names_the_slot_of_the_active_rule() -> None:
    assert RULE_LIMITED_ZH.format(slot="項鍊") == "和項鍊的改寫規則衝突，沒有效果"
    found = lines(_arena({"neck": [FIRE_MENDS], "ring_1": [WAKE]}))
    greyed = found[f"ring_1:{WAKE[0]}"]
    assert not greyed.active and greyed.weight_permille == 0
    assert greyed.off_zh == "和項鍊的改寫規則衝突，沒有效果"
    assert greyed.duplicate_of is None
    kept = found[f"neck:{FIRE_MENDS[0]}"]
    assert kept.active and kept.off_zh is None


OVER: Mapping[str, Sequence[EquippedAffix]] = {
    "main_hand": [grant("skill_gear_grapple", "affix_t_a", "action")],
    "off_hand": [grant("skill_gear_smoke_bomb", "affix_t_b", "action")],
    "body": [grant("skill_gear_shield_wall", "affix_t_c", "action")],
    "neck": [grant("skill_gear_grapple", "affix_t_a", "action")],  # 同 id 的第 2 份
}


def test_signature_wording() -> None:
    expected = "身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選"
    assert SIGNATURE_LIMITED_ZH.format(n=3) == expected
    found = lines(_battle(OVER, team=Team.ALLY))
    greyed = found["neck:affix_t_a"]
    assert not greyed.active
    assert greyed.off_zh == expected
    assert greyed.duplicate_of is None  # 同 id 的第 2 份是被名額擋下，不是重複
    assert all(found[k].active and found[k].off_zh is None for k in found if k != "neck:affix_t_a")


def test_other_team_sees_the_same_lines() -> None:
    """守則 14：裝備欄照現有的顯示規則（敵我都看得到同樣的詞條行）。"""
    state = _battle(OVER, team=Team.ALLY)
    assert lines(state, Team.ENEMY) == lines(state, Team.ALLY)


def test_no_limits_means_no_reason() -> None:
    three = {k: v for k, v in OVER.items() if k != "neck"}
    assert all(line.off_zh is None for line in lines(_battle(three, team=Team.ALLY)).values())
