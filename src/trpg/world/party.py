"""隊伍與系統傭兵（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22）。

- **雇用**（09 9.6.9 #97）：一隊 3 人＝主角＋最多 ``max_hired`` 名傭兵；免費、只在城鎮且沒有遭遇時
  選（出城前選好、野外不能換）。``hire`` 整組換成新的清單（空＝不帶傭兵）。
- **出場**（:func:`party_spawns`）：傭兵的戰鬥單位＝底稿 build 的英雄範本，ID 與名字換成傭兵的
  （代決 5C1-6）；照主角等級成長由 :func:`trpg.world.battle.grow_allies` 做（5A-SIM2，同標準隊友）。
  沒有傭兵時 ``prepare_battle`` 照舊用標準隊友（代決 5C1-2）。

純函式：不讀時間、不擲骰。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import MercenaryDef, MercenaryTable
from trpg.engine.setup import UnitSpawn
from trpg.shared.types import Team
from trpg.world.actions import HireAction, PartyChangedEvent, WorldEvent
from trpg.world.common import here
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.state import CharacterState

__all__ = ["hire", "hire_problem", "mercenary_table", "party_mercenaries", "party_spawns"]


def mercenary_table(library: ContentLibrary) -> MercenaryTable:
    """傭兵名單；內容庫沒有 ``world/mercenaries.yaml`` 時拋 :class:`WorldActionError`。"""
    table = library.world_mercenaries
    if table is None:
        raise WorldActionError("內容庫沒有系統傭兵名單")
    return table


def hire_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """現在不能雇用（換傭兵）的理由；可以時為 ``None``。"""
    if library.world_mercenaries is None:
        return "沒有系統傭兵名單"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if here(library, char).kind != "town":
        return "出城前在城鎮選好，野外不能換"
    return None


def hire(
    library: ContentLibrary, char: CharacterState, action: HireAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """``hire`` 動作：在城鎮把隊伍的傭兵整組換成 ``action.mercenaries``（免費）。"""
    table = mercenary_table(library)
    problem = hire_problem(library, char)
    if problem is not None:
        raise WorldActionError(f"不能雇用傭兵：{problem}")
    chosen = action.mercenaries
    if len(chosen) > table.max_hired:
        raise WorldActionError(f"最多帶 {table.max_hired} 名傭兵（收到 {len(chosen)} 名）")
    if len(set(chosen)) != len(chosen):
        raise WorldActionError("同一名傭兵不能雇兩次")
    known = table.by_id()
    unknown = [m for m in chosen if m not in known]
    if unknown:
        raise WorldActionError(f"沒有這名傭兵：{', '.join(unknown)}")
    char = char.model_copy(update={"mercenaries": chosen})
    return char, (PartyChangedEvent(mercenaries=chosen),)


def party_mercenaries(library: ContentLibrary, char: CharacterState) -> tuple[MercenaryDef, ...]:
    """隊伍裡的傭兵定義（依出場順序）。名單不見了或傭兵被移除時拋 :class:`WorldError`
    （內容錯誤，不是玩家的動作錯）。"""
    if not char.mercenaries:
        return ()
    table = library.world_mercenaries
    if table is None:
        raise WorldError("內容庫沒有系統傭兵名單，但角色帶著傭兵")
    known = table.by_id()
    missing = [m for m in char.mercenaries if m not in known]
    if missing:
        raise WorldError(f"傭兵名單沒有：{', '.join(missing)}")
    return tuple(known[m] for m in char.mercenaries)


def party_spawns(library: ContentLibrary, char: CharacterState) -> tuple[UnitSpawn, ...]:
    """隊伍傭兵的出場設定（1 級基準，還沒照主角等級成長；依出場順序）。"""
    builds = library.builds.by_id()
    spawns: list[UnitSpawn] = []
    for merc in party_mercenaries(library, char):
        template = builds[merc.build].hero.model_copy(
            update={"id": merc.id, "name_zh": merc.name_zh}
        )
        spawns.append(
            UnitSpawn(
                template=template,
                weapon=library.weapon_of(template),
                equipment=library.loadout_of(template),
                team=Team.ALLY,
            )
        )
    return tuple(spawns)
