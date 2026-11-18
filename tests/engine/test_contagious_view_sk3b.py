"""SK-3b 第 7 項（AR-SK2 待決 1）：狀態視圖輸出「會擴散」（``StatusView.contagious``）。

只有帶會擴散的狀態有 ``contagious: true``；其他狀態的 JSON 不多任何鍵（既有快照逐字不變）。"""

from __future__ import annotations

import json

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U2, battle
from trpg.engine.state import StatusInstance
from trpg.engine.view import project_for
from trpg.shared.types import Team


def _statuses(team: Team) -> list[dict[str, object]]:
    state = battle(
        make_skill(SID, {"type": "single", "range": 5}, [{"type": "contagion"}]), [(5, 3)]
    )
    unit = state.units[U2]
    unit.statuses = [
        StatusInstance("burning", 2, None, contagious=True),
        StatusInstance("poison", 2, None),
    ]
    view = json.loads(project_for(state, team).model_dump_json())
    (target,) = [u for u in view["units"] if u["id"] == U2]
    return list(target["statuses"])


def test_only_the_contagious_status_carries_the_flag() -> None:
    burning, poison = _statuses(Team.ALLY)
    assert burning["status_id"] == "burning" and burning["contagious"] is True
    assert poison["status_id"] == "poison" and "contagious" not in poison


def test_both_teams_see_the_flag() -> None:
    assert _statuses(Team.ENEMY)[0]["contagious"] is True
