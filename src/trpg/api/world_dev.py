"""大世界的開發用戰鬥入口（Phase 6F-3）：Boss 戰直接開打，給實戰截圖與驗收用。

- 只在開發模式（``config/server.toml`` 的 ``dev_mode``，``dev_router`` 才掛）**而且**環境變數
  ``TRPG_DEV_ROUTES=1`` 時可用，否則 404（同 roguelite 的 ``dev-advance``）。前端只在 ``?dev=1``
  顯示按鈕。
- **不碰世界**：用角色存檔的複本（換到 Boss 地點、可選等級）照正式的
  :func:`~trpg.world.battle.prepare_battle` 組出戰鬥設定，在戰鬥工作階段表開一場；不寫世界
  日誌、角色存檔，打完也不回寫（同循環賽重播，不登記成角色進行中的戰鬥）。所以正式遊戲的主線限制（霧牆、世界事件）照舊，一般玩家碰不到。
- 戰鬥本身就是正式的大世界 Boss 戰（同一個陣容、Boss 地圖、階段與蓄力招），播放走既有戰鬥畫面。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.api.sessions import BattleSession, StepRecord
from trpg.api.world import WorldStore
from trpg.world.battle import prepare_battle
from trpg.world.common import max_hp, max_mana, world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.solutions import make_encounter

__all__ = ["DevBattle", "dev_boss_battle"]

MAX_DEV_LEVEL = 20
"""開發入口可指定的最高等級（只改複本）。"""


@dataclass(frozen=True)
class DevBattle:
    title_zh: str
    battle: BattleSession
    records: list[StepRecord]


def dev_boss_battle(
    store: WorldStore,
    character_id: str,
    *,
    location: str,
    region: str | None = None,
    level: int | None = None,
) -> DevBattle:
    """``location``（``region`` 省略＝角色所在區）的遭遇直接開打；``level``＝複本的等級（省略＝照
    角色）。地點不存在、沒有遭遇（城鎮）或角色正在戰鬥時拋 :class:`WorldActionError`。"""
    with store.lock:
        synced = store.sync(character_id)
        if synced.battle is not None:
            raise WorldActionError("戰鬥進行中，先打完這場")
        char = synced.char
        where = char.region if region is None else region
        library = store.library
        target = world_map_of(library, where).location_by_id().get(location)
        if target is None:
            raise WorldActionError(f"{where} 沒有地點 {location}")
        if not target.battle_maps:
            raise WorldActionError(f"{target.name_zh}沒有戰鬥（城鎮或傳送點）")
        copy = char.model_copy(
            update={"region": where, "location": location, "field": None, "field_visit": None}
        )
        if level is not None:
            copy = copy.model_copy(update={"level": max(1, min(MAX_DEV_LEVEL, level))})
        copy = copy.model_copy(
            update={"hp": max_hp(library, copy), "mana": max_mana(library, copy), "fatigued": False}
        )
        encounter, copy = make_encounter(library, synced.world, copy, target, synced.now)
        copy = copy.model_copy(update={"pending_encounter": encounter})
        prepared = prepare_battle(library, copy)
        battle, records = store.battles.open(prepared.setup, prepared.seed)
        return DevBattle(title_zh=f"開發：{target.name_zh}", battle=battle, records=records)
