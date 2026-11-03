"""各區天氣（Phase 5A-2；09 9.6.10 #104、05 5.1「各區天氣傾向」、5.7 天氣 4 種）。

每區各自有天氣，每半天換一次；同一區所有人看到相同的天氣。天氣不存狀態：由賽季種子、區域與半天
序號衍生，依 ``content/world/rules.yaml`` 的權重抽（白天、夜晚各一組）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.clock import day_phase, half_day_index
from trpg.world.errors import WorldError
from trpg.world.rng import region_seed
from trpg.world.state import WorldState

__all__ = ["STREAM_WEATHER", "weather_at"]

STREAM_WEATHER = "weather"


def _weighted(rng: Rng, weights: tuple[tuple[str, int], ...]) -> str:
    total = sum(w for _, w in weights)
    pick = rng.randint(0, total - 1)
    for item, weight in weights:
        if pick < weight:
            return item
        pick -= weight
    raise AssertionError("權重總和計算錯誤")  # pragma: no cover


def weather_at(library: ContentLibrary, world: WorldState, region: str, now: int) -> str:
    """``region`` 在 ``now`` 的天氣 ID（``weather.yaml``）。"""
    rules = library.world_rules
    if rules is None:
        raise WorldError("內容庫沒有 world/rules.yaml，無法決定天氣")
    weights = rules.weather_for(region).for_phase(day_phase(now))
    rng = Rng(region_seed(world.season_seed, region, STREAM_WEATHER, half_day_index(now)))
    return _weighted(rng, weights)
