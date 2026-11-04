"""大世界的開發用戰鬥入口（Phase 6F-3）：Boss 戰直接開打，給實戰截圖與驗收用。

- 只在開發模式（``config/server.toml`` 的 ``dev_mode``，``dev_router`` 才掛）**而且**環境變數
  ``TRPG_DEV_ROUTES=1`` 時可用，否則 404（同 roguelite 的 ``dev-advance``）。前端只在 ``?dev=1``
  顯示按鈕。
- **不碰世界**：用角色存檔的複本（換到 Boss 地點、可選等級）照正式的
  :func:`~trpg.world.battle.prepare_battle` 組出戰鬥設定，在戰鬥工作階段表開一場；不寫世界
  日誌、角色存檔，打完也不回寫（同循環賽重播，不登記成角色進行中的戰鬥）。所以正式遊戲的主線
  限制（霧牆、世界事件）照舊，一般玩家碰不到。
- 戰鬥本身就是正式的大世界 Boss 戰（同一個陣容、Boss 地圖、階段與蓄力招），播放走既有戰鬥畫面。
- ``ai_until``（截圖用）：先讓效用 AI 連主角一起代打，停在指定的那一刻、輪到主角時，再交給畫面
  （``charge``＝Boss 蓄力中，主角結束回合就看得到 Boss 放大招；``last``＝敵人只剩一名而且 HP 不到
  一成半，下一擊多半就是最後一擊）。代打的步驟用存檔重播的方式還原（同 roguelite 讀檔），
  結果和照順序打
  完全一樣。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from trpg.api.sessions import BattleSession, StepRecord
from trpg.api.world import WorldStore
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.runner import advance
from trpg.engine.state import BattleState
from trpg.shared.types import Team
from trpg.world.battle import prepare_battle
from trpg.world.common import max_hp, max_mana, world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.solutions import make_encounter

__all__ = ["DevBattle", "dev_boss_battle"]

MAX_DEV_LEVEL = 20
"""開發入口可指定的最高等級（只改複本）。"""

type AiUntil = Literal["charge", "last"]
_LOW_PERMILLE = 150


def _hero_turn(state: BattleState) -> bool:
    active = state.active_unit
    return (
        active is not None
        and state.units[active].team is Team.ALLY
        and active == min(u.id for u in state.units.values() if u.team is Team.ALLY)
    )


def _boss_charging(state: BattleState) -> bool:
    return any(
        u.alive and "boss" in u.tags and u.get_status("charging") is not None
        for u in state.units.values()
        if u.team is Team.ENEMY
    )


def _last_foe_low(state: BattleState) -> bool:
    foes = [u for u in state.living_units() if u.team is Team.ENEMY and not u.is_summon]
    return len(foes) == 1 and foes[0].hp * 1000 <= _LOW_PERMILLE * foes[0].max_hp


_STOPS: dict[str, Callable[[BattleState], bool]] = {"charge": _boss_charging, "last": _last_foe_low}


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
    ai_until: AiUntil | None = None,
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
        title = f"開發：{target.name_zh}"
        if ai_until is None:
            battle, records = store.battles.open(prepared.setup, prepared.seed)
            return DevBattle(title_zh=title, battle=battle, records=records)
        want = _STOPS[ai_until]
        opening = begin_battle(prepared.setup, prepared.seed)
        policy = CommandedAI(UtilityAI(library.ai_profiles), {})
        state, _, steps = advance(
            opening.state,
            opening.pending,
            policy,
            stop=lambda st, pending: pending is None and _hero_turn(st) and want(st),
        )
        if state.ended:
            raise WorldActionError(f"AI 代打到結束都沒有出現「{ai_until}」的時刻（換等級再試）")
        battle, records = store.battles.open(prepared.setup, prepared.seed, restore=(steps, []))
        return DevBattle(title_zh=title, battle=battle, records=records)
