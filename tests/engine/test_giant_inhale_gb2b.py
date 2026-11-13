"""GB-2b：灰燼之心的吸氣「4 格內」（19.2.3 R7，量法照 05 5.12.4 第 2 點 R2）。

內建 ``skill_heart_inhale`` 改成範圍光環半徑 4：離巨人最近佔格曼哈頓距離 ≤ 4 的單位往最近佔格拉
1 格，5 格外不動；後段方陣 1d10 照舊。巨人用 GB-1b 的合成 3×3（中心 (6, 6)，佔 x 5–7、y 5–7）。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import give_turn, library, template
from tests.engine.test_giant_gb1b import always_19, arena, at, giant
from trpg.engine import BattleState, UseSkill, resolve

INHALE = "skill_heart_inhale"


def _inhale(
    monkeypatch: pytest.MonkeyPatch, heroes: list[tuple[int, int]]
) -> tuple[BattleState, Any]:
    always_19(monkeypatch)
    fighter = template("hero_fighter", reactions=[], max_hp=99)
    state = arena([(x, y, fighter) for x, y in heroes], giant_skills=[INHALE])
    g = giant(state)
    result = resolve(give_turn(state, g.id), UseSkill(unit_id=g.id, skill_id=INHALE))
    return state, result


def test_r7_inhale_pulls_everyone_within_four_of_the_body(monkeypatch: pytest.MonkeyPatch) -> None:
    # 都是曼哈頓 4：(6, 11) 到南排 (6, 7)；(9, 9) 到角落 (7, 7)；(1, 6) 到西排 (5, 6)
    state, result = _inhale(monkeypatch, [(6, 11), (9, 9), (1, 6)])
    after = result.state.units
    assert after[at(state, (6, 11)).id].xy == (6, 10)
    assert after[at(state, (9, 9)).id].xy == (8, 9)  # 斜向同距離取 x 軸
    assert after[at(state, (1, 6)).id].xy == (2, 6)


def test_r7_five_away_is_not_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    # (6, 12)：曼哈頓 5；(10, 9)：離 (7, 7) 曼哈頓 5
    state, result = _inhale(monkeypatch, [(6, 12), (10, 9)])
    after = result.state.units
    assert after[at(state, (6, 12)).id].xy == (6, 12)
    assert after[at(state, (10, 9)).id].xy == (10, 9)


def test_inhale_content_is_a_radius_four_aura() -> None:
    skill = library().skills[INHALE]
    assert skill.shape.type == "allies_in_radius"
    assert skill.shape.radius == 4
    assert skill.followup is not None
    assert skill.followup.when == "after_gather"
