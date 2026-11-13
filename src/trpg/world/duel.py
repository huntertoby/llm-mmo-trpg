"""精英單挑（RG-2，#162，09 9.6.6；``docs/phases/PhaseRG計畫.md`` 2.2）。

- **提出**：遇敵時（:func:`offer_duel`，:func:`~trpg.world.solutions.make_encounter` 呼叫）陣容
  排最前的精英帶 ``duel: true``（遭遇表地點的固定精英、懸賞、遭遇變化的 ``elite``）→
  ``EncounterResult.duel`` 記成 ``offered``。只看內容，不耗亂數（陣容本來就由 ``battle_seed``
  衍生）。
- **回應**：``duel_choice`` 動作（:func:`choose_duel`）只在 ``offered`` 時可送，改成 ``accepted`` 或
  ``declined``；**還沒選就開打＝拒絕**（照原本全隊打）。撤退照常。
- **組場**（:func:`fielded_lineup`，:func:`~trpg.world.battle.prepare_battle` 用）：接受＝只有主角對
  精英本人——傭兵、影子、劇情夥伴不上場，陣容的其他敵人與第三方不上場；戰鬥中召出的召喚物照常。
- **獎勵**：兩邊完全一樣（設計原話「補師QQ」）——經驗、金錢、掉落、精英必掉、懸賞都照整個陣容算
  （掉材料的成員見 :func:`trpg.world.loot.roll_loot` 的 ``duel``）。
"""

from __future__ import annotations

from collections.abc import Collection

from trpg.content.library import ContentLibrary
from trpg.world.actions import DuelChoiceAction, DuelChosenEvent, WorldEvent
from trpg.world.encounters import EncounterLineup, roll_lineup
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, EncounterResult

__all__ = ["choose_duel", "duel_accepted", "fielded_lineup", "offer_duel"]


def offer_duel(
    library: ContentLibrary, encounter: EncounterResult, flags: Collection[str]
) -> EncounterResult:
    """遇敵時判定精英是否提出單挑（見模組說明）；``flags``＝角色的劇情旗標（遭遇變化看它）。
    賽季 Boss、沒有遭遇表的地點一律不提。"""
    if encounter.season_boss is not None:
        return encounter
    table = library.world_encounters.get(encounter.region)
    if table is None or encounter.location not in table.location_by_id():
        return encounter
    if not roll_lineup(library, encounter, flags).duel:
        return encounter
    return encounter.model_copy(update={"duel": "offered"})


def duel_accepted(encounter: EncounterResult, lineup: EncounterLineup) -> bool:
    """這場打一對一：玩家接受了，而且陣容仍是會提出單挑的精英（內容改掉時退回全隊打）。"""
    return encounter.duel == "accepted" and lineup.duel


def fielded_lineup(lineup: EncounterLineup) -> EncounterLineup:
    """一對一實際上場的陣容：只有排最前的精英，沒有第三方。"""
    return lineup.model_copy(update={"members": lineup.members[:1], "third": ()})


def choose_duel(
    char: CharacterState, action: DuelChoiceAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """``duel_choice`` 動作：回應精英的單挑（只在 ``offered`` 時）。"""
    encounter = char.pending_encounter
    if encounter is None:
        raise WorldActionError("目前沒有遭遇")
    if encounter.duel is None:
        raise WorldActionError("這場遭遇沒有人提出單挑")
    if encounter.duel != "offered":
        raise WorldActionError("已經回應過單挑了")
    choice = "accepted" if action.accept else "declined"
    updated = encounter.model_copy(update={"duel": choice})
    event = DuelChosenEvent(location=encounter.location, accepted=action.accept)
    return char.model_copy(update={"pending_encounter": updated}), (event,)
