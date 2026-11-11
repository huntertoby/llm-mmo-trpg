"""入門期的戰鬥閘與活動限制（Phase OB-4，#150；21 21.5 第 7、9 點）。

**入門期**＝``char.opening is not None`` 而且還沒正式選定（``stage`` 不是 ``chosen``，
:func:`in_starter_period`）。已完成開局的舊角色（``opening is None``）、已正式選定的角色都不受這裡
任何判斷影響。

- **敵人**：新手任務（``kind: starter``）前 :data:`STARTER_STEPS` 步的固定戰以外，實地地圖上的隊伍
  「不顯示、不接觸」（:func:`spawn_hidden`；畫面清單與接觸判定共用
  :func:`trpg.world.field_enemies._shown`，所以一定一致）；節點移動的遇敵機率歸 0
  （:func:`trpg.world.step._travel_to`，擲骰照擲、亂數消耗不變）。
- **開戰**：``fight`` 只收上面那兩步固定戰的遭遇（:func:`fight_problem`，開局閘門的規則）。
- **事件解法與機遇**：戰鬥解法、機遇（給招）擋下（:func:`solution_problem`）；交涉、放棄、情境判定
  （不開戰也不給招）照常。入門期不出機遇保底、也不記「遇過機遇」（:func:`trpg.world.events`），
  保底留到正式選定之後。
- **情境物件**：``use: encounter`` 的物件（Boss 門）擋下（:func:`spot_problem`）。
- **任務**：可以接；給招的步驟（三選一、劇情技能）先不結算，等正式選定（:func:`holds_step`；新手任務
  前 :data:`STARTER_STEPS` 步的三選一照 OB-2 延後，不在此列）。

被擋的原因文字集中在這個模組（OB-5／6 會再調）。本模組只依賴內容與狀態，不匯入其他世界邏輯
（``quests``、``solutions``、``field_things`` 都要用它）。
"""

from __future__ import annotations

from typing import Final

from trpg.content.fields import FieldSpawn, SpotUse
from trpg.content.library import ContentLibrary
from trpg.content.world_events import SolutionKind
from trpg.content.world_quests import QuestDef, StepReward
from trpg.world.state import CharacterState, EncounterResult

__all__ = [
    "FIGHT_ZH",
    "OBJECT_ZH",
    "SOLUTION_ZH",
    "STARTER_STEPS",
    "fight_problem",
    "holds_step",
    "in_starter_period",
    "solution_problem",
    "spawn_hidden",
    "spot_problem",
    "starter_spawn",
]

STARTER_STEPS: Final = 2
"""入門期開放戰鬥的新手任務步數（21.5 第 7 點「戰鬥只開放新手第 1、2 步」）。和
:data:`trpg.world.opening_choice.STARTER_STEPS` 同值（測試檢查；那邊匯入 ``quests``，這裡不能反過來
匯入它）。"""

FIGHT_ZH: Final = "入門期只能打新手任務前兩步的戰鬥，找葛蘭選定武器後就能打"
SOLUTION_ZH: Final[dict[SolutionKind, str]] = {
    "combat": "入門期不能用戰鬥解決事件，找葛蘭選定武器後就能打",
    "opportunity": "入門期還不能領機遇的技能，找葛蘭選定武器後再來",
}
"""入門期擋下的事件解法種類 → 原因（其餘種類照常）。"""
OBJECT_ZH: Final = "入門期還不能挑戰這裡的對手，找葛蘭選定武器後再來"


def in_starter_period(char: CharacterState) -> bool:
    """入門期：開局還沒正式選定（含還在選大類的 ``pick_class``）。"""
    return char.opening is not None and char.opening.stage != "chosen"


def _starter_steps(quest: QuestDef | None) -> tuple[str, ...]:
    """新手任務前 :data:`STARTER_STEPS` 步的步驟 ID；不是新手任務＝空。"""
    if quest is None or quest.kind != "starter":
        return ()
    return tuple(step.id for step in quest.steps[:STARTER_STEPS])


def starter_spawn(library: ContentLibrary, region: str, spawn: FieldSpawn) -> bool:
    """這一隊是新手任務前 :data:`STARTER_STEPS` 步的固定戰（``until_quest`` 指到新手任務、
    ``until_step`` 是前幾步）。"""
    if spawn.until_quest is None or spawn.until_step is None:
        return False
    quest = library.world_quests.quest(region, spawn.until_quest)
    return spawn.until_step in _starter_steps(quest)


def spawn_hidden(
    library: ContentLibrary, char: CharacterState, region: str, spawn: FieldSpawn
) -> bool:
    """入門期不顯示、不接觸的隊伍（21.5 第 9 點「入門期的敵人」）。"""
    return in_starter_period(char) and not starter_spawn(library, region, spawn)


def _starter_encounter(library: ContentLibrary, encounter: EncounterResult) -> bool:
    contact = encounter.contact
    found = None if contact is None else library.field_maps.get(contact.map)
    if contact is None or found is None or contact.spawn >= len(found.spawns):
        return False
    return starter_spawn(library, encounter.region, found.spawns[contact.spawn])


def fight_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """入門期不能打目前這場遭遇的原因（只開放新手任務前兩步的固定戰）；能打、沒有遭遇、不在入門期
    ＝``None``。"""
    encounter = char.pending_encounter
    if encounter is None or not in_starter_period(char):
        return None
    return None if _starter_encounter(library, encounter) else FIGHT_ZH


def solution_problem(char: CharacterState, kind: SolutionKind) -> str | None:
    """入門期不能用這種事件解法的原因（會開戰的戰鬥解法、會給招的機遇）；其餘＝``None``。"""
    return SOLUTION_ZH.get(kind) if in_starter_period(char) else None


def spot_problem(char: CharacterState, use: SpotUse) -> str | None:
    """入門期不能用這個情境物件的原因（``encounter``＝直接開戰）；其餘＝``None``。"""
    return OBJECT_ZH if use == "encounter" and in_starter_period(char) else None


def holds_step(char: CharacterState, quest: QuestDef, index: int, reward: StepReward) -> bool:
    """入門期先不結算的任務步驟（21.5 第 9 點「給招的獎勵要等正式選定」）：獎勵有三選一或劇情技能的
    步驟。新手任務前 :data:`STARTER_STEPS` 步不算（三選一照 OB-2 延後）。``index``＝步驟在任務裡的
    索引（從 0）。"""
    if not in_starter_period(char):
        return False
    if reward.offer is None and reward.story_skill is None:
        return False
    return not (quest.kind == "starter" and index < STARTER_STEPS)
