"""風元素補強（Phase 3-54a）的事件敘述：吹送與區域擴散。"""

from __future__ import annotations

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, battle, cast, of
from trpg.engine.events import SurfaceBlown
from trpg.narrative.events import describe_event


def test_blow_and_blocked_blow_are_described() -> None:
    skill = make_skill(SID, {"type": "line", "size": 2}, [{"type": "blow_surface", "distance": 2}])
    state = battle(skill, surfaces=((4, 3, "oil"), (5, 3, "fire")), foes=[(0, 0)])
    result = cast(state, direction="east")
    texts = [describe_event(e, result.state) or "" for e in of(result, SurfaceBlown)]
    assert texts == ["  ≋ (5, 3) 的火焰被風吹到 (6, 3)", "  ≋ (4, 3) 的油被風吹到 (6, 3)"]
