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
from trpg.content.world_quests import (
    EVENT_CONDITION_KINDS,
    AnyOf,
    QuestDef,
    QuestStepDef,
    StepReward,
    WinBattle,
)
from trpg.world.state import CharacterState, EncounterResult

__all__ = [
    "FIGHT_ZH",
    "FLASH_ZH",
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
    "stuck_conditions",
]

STARTER_STEPS: Final = 2
"""入門期的新手任務步數（21.5 第 2、3、7 點「用入門配備打新手第 1、2 步」「戰鬥只開放新手第 1、2
步」）。只有這一份：:mod:`trpg.world.opening_choice` 從這裡匯入（那邊匯入 ``quests``、
``quests`` 要用這個模組，所以不能反過來）。"""

FIGHT_ZH: Final = "先完成新手任務，再找葛蘭選定武器與關鍵字，才能打這場"
"""入門期不能打的戰鬥（玩法 PM 定稿「限制：其他戰鬥」）。"""
FLASH_ZH: Final = "到 {level} 級才能閃現"
"""開局還沒結束的角色不能閃現（玩法 PM 定稿「限制：閃現」；``{level}``＝開局結束的等級）。"""
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


def _starter_fights(library: ContentLibrary, region: str) -> frozenset[tuple[str | None, str]]:
    """新手任務前 :data:`STARTER_STEPS` 步要打贏的（地點, 陣容）（步驟的 ``win_battle`` 條件）。"""
    table = library.world_quests.quests.get(region)
    out: set[tuple[str | None, str]] = set()
    for quest in () if table is None else table.quests:
        if quest.kind != "starter":
            continue
        for step in quest.steps[:STARTER_STEPS]:
            for condition in step.when:
                leaves = condition.conditions if isinstance(condition, AnyOf) else (condition,)
                out |= {
                    (leaf.location, leaf.group)
                    for leaf in leaves
                    if isinstance(leaf, WinBattle) and leaf.group is not None
                }
    return frozenset(out)


def _starter_encounter(library: ContentLibrary, encounter: EncounterResult) -> bool:
    """這場遭遇是碰到新手任務前幾步的固定戰（實地地圖上的接觸，地點與陣容對得上任務條件；看任務
    資料而不是地圖，沒有實地地圖的內容庫也認得）。"""
    contact = encounter.contact
    if contact is None:
        return False
    fights = _starter_fights(library, encounter.region)
    return (encounter.location, contact.group) in fights or (None, contact.group) in fights


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


def stuck_conditions(step: QuestStepDef) -> tuple[int, ...]:
    """給招的步驟裡「選定後可能再也達不成」的條件（``when`` 的索引；21.5 第 9 點 OB-4 補充：這類步驟
    整步等正式選定才結算，完成條件不能只靠入門期當下發生一次的事件）。

    一個條件只要有一個葉節點是狀態型（到某地、持有線頭、好感度、旗標…，選定後下一個動作會重新
    檢查），或是 ``win_battle``（入門期打不到，不會先發生），就算過；只剩情境判定、聊天、成長這類
    當下發生的事件就列出來。不給招的步驟＝空。內容檢查用（``tests/world/test_opening_limits.py``）。"""
    if step.reward.offer is None and step.reward.story_skill is None:
        return ()
    out: list[int] = []
    for index, condition in enumerate(step.when):
        leaves = condition.conditions if isinstance(condition, AnyOf) else (condition,)
        if all(leaf.kind in EVENT_CONDITION_KINDS - {"win_battle"} for leaf in leaves):
            out.append(index)
    return tuple(out)
