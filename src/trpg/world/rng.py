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
    "STREAM_CHECK",
    "STREAM_EVENT",
    "STREAM_FIELD",
    "STREAM_LINEUP",
    "STREAM_REVEAL",
    "STREAM_SPOT",
    "STREAM_TRAVEL",
    "derive_seed",
    "draw",
    "peek",
    "region_seed",
    "spawn_seed",
]

STREAM_TRAVEL: Final = "travel"
"""遇敵擲骰。"""
STREAM_BATTLE: Final = "battle"
"""遭遇的戰鬥地圖與戰鬥種子。"""
STREAM_REVEAL: Final = "reveal"
"""隱藏地點的感知判定。"""
STREAM_EVENT: Final = "event"
"""事件出現擲骰與骨架挑選（Phase 5B-1）。"""
STREAM_CHECK: Final = "check"
"""情境判定的 d20（Phase 5B-2；一律擲兩顆）。"""
STREAM_SPOT: Final = "spot"
"""地圖上的事件「！」放在哪個事件點（Phase 6C-5；候選超過一個時才抽）。"""
STREAM_FIELD: Final = "field"
"""實地地圖上看得見的敵人（Phase 6C-1）：每進一個有實地地圖的地點抽 1 次，決定這一趟每隊的巡邏起點
與駐守朝向（:mod:`trpg.world.field_enemies`；陣容 6C-R2 改用 :func:`spawn_seed`）。"""
STREAM_LINEUP: Final = "lineup"
"""實地地圖上一隊敵人的陣容（Phase 6C-R2，:func:`spawn_seed`；不是角色的串流，沒有計數）。"""


def derive_seed(season_seed: int, character_id: str, stream: str, counter: int) -> int:
    """``fnv1a64("{season_seed}:{character_id}:{stream}:{counter}")``（64 位元）。"""
    return fnv1a64(f"{season_seed}:{character_id}:{stream}:{counter}".encode())


def region_seed(season_seed: int, region: str, stream: str, counter: int) -> int:
    """全區共用的種子（天氣）：角色段是 ``@<region>``。"""
    return derive_seed(season_seed, f"@{region}", stream, counter)


def spawn_seed(season_seed: int, region: str, location: str, spawn: int, generation: int) -> int:
    """實地地圖上第 ``spawn`` 隊的陣容種子（32 位元；Phase 6C-R2）：所有角色共用，只看世界種子、
    (區域, 地點, 隊伍索引) 與重生世代（:meth:`~trpg.world.state.WorldState.spawn_generation`），所以
    多人同場時同一隊的陣容一致。角色段是 ``@<region>/<location>/<spawn>``（角色 ID 不會以 ``@``
    開頭）。"""
    owner = f"@{region}/{location}/{spawn}"
    return Rng(derive_seed(season_seed, owner, STREAM_LINEUP, generation)).next_u32()


def peek(season_seed: int, char: CharacterState, stream: str) -> Rng:
    """``char`` 在 ``stream`` 的下一個亂數產生器（不改計數；:func:`draw` 用的就是這一個）。"""
    counter = char.rng_counters.get(stream, 0)
    return Rng(derive_seed(season_seed, char.character_id, stream, counter))


def draw(season_seed: int, char: CharacterState, stream: str) -> tuple[Rng, CharacterState]:
    """取 ``char`` 在 ``stream`` 的下一個亂數產生器（:func:`peek`），回傳它與計數 +1 後的角色。"""
    counter = char.rng_counters.get(stream, 0)
    rng = peek(season_seed, char, stream)
    counters = dict(sorted({**char.rng_counters, stream: counter + 1}.items()))
    return rng, char.model_copy(update={"rng_counters": counters})
