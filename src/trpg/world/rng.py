"""世界亂數的衍生（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.4、6.5）。

每次擲骰都用一個新的 :class:`~trpg.shared.rng.Rng`，種子是
``fnv1a64(f"{season_seed}:{character_id}:{stream}:{counter}")``；``counter`` 是該角色該串流已用的
次數（存在 :attr:`CharacterState.rng_counters`）。不用內建 ``hash()``（字串 hash 每次執行不同）。

天氣是全區共用（#104），角色段改成 ``@<region>``（角色 ID 照 ``ID_PATTERN`` 不會以 ``@`` 開頭，
不會撞到），計數用 :func:`~trpg.world.clock.half_day_index`（代決 5A2-7）。
"""

from __future__ import annotations

from typing import Final

from trpg.shared.rng import Rng, fnv1a64
from trpg.world.state import CharacterState

__all__ = [
    "STREAM_BATTLE",
    "STREAM_REVEAL",
    "STREAM_TRAVEL",
    "derive_seed",
    "draw",
    "region_seed",
]

STREAM_TRAVEL: Final = "travel"
"""遇敵擲骰。"""
STREAM_BATTLE: Final = "battle"
"""遭遇的戰鬥地圖與戰鬥種子。"""
STREAM_REVEAL: Final = "reveal"
"""隱藏地點的感知判定。"""


def derive_seed(season_seed: int, character_id: str, stream: str, counter: int) -> int:
    """``fnv1a64("{season_seed}:{character_id}:{stream}:{counter}")``（64 位元）。"""
    return fnv1a64(f"{season_seed}:{character_id}:{stream}:{counter}".encode())


def region_seed(season_seed: int, region: str, stream: str, counter: int) -> int:
    """全區共用的種子（天氣）：角色段是 ``@<region>``。"""
    return derive_seed(season_seed, f"@{region}", stream, counter)


def draw(season_seed: int, char: CharacterState, stream: str) -> tuple[Rng, CharacterState]:
    """取 ``char`` 在 ``stream`` 的下一個亂數產生器，回傳它與計數 +1 後的角色。"""
    counter = char.rng_counters.get(stream, 0)
    rng = Rng(derive_seed(season_seed, char.character_id, stream, counter))
    counters = dict(sorted({**char.rng_counters, stream: counter + 1}.items()))
    return rng, char.model_copy(update={"rng_counters": counters})
