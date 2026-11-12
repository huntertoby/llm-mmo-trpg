"""劇情夥伴（Phase 5C-3；09 9.6.9 #97、9.6.11 5C-2 代決；``docs/phases/Phase5計畫.md`` 24.3）。

- **誰該在隊**：進行中（已接、未完成）任務的 ``companion``（任務 ID 排序、去重）；任務寫了
  ``companion_after`` 時那一步完成才算（OB-7，#154：阿岳渡口石階打完才入隊）。
- **加入**（:func:`sync_companions`，每個世界動作之後）：隊友（傭兵＋影子）還有空位就直接加入；已滿
  就 **替掉出場順序第 2 名**，替下的成員記在 ``companion_bench``。
- **離隊**：任務都結束 → 拿掉；``companion_bench`` 有紀錄、隊伍有空位就還原到原本的位置。玩家自己
  ``hire`` 過（:mod:`trpg.world.party` 清掉 ``companion_bench``）就不還原。
- **出場**（:func:`companion_spawns`）：底稿 build 的英雄範本換成夥伴的 ID 與名字，技能照欄位上限；
  排在傭兵、影子之後；照主角等級成長由 :func:`trpg.world.battle.grow_allies` 做。
- **好感度**（:func:`companion_win_affinity`，18.7.6）：打贏一場、隊伍有夥伴 → 夥伴的 NPC
  ``affinity_per_win``，同一天累計不超過 ``affinity_daily_cap``。

純函式：不讀時間（``now`` 由呼叫端給）、不擲骰。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import CompanionDef
from trpg.content.world_quests import QuestDef
from trpg.engine.setup import UnitSpawn
from trpg.shared.types import Team
from trpg.world.actions import CompanionJoinedEvent, CompanionLeftEvent, WorldEvent
from trpg.world.affinity import change_affinity
from trpg.world.calendar import day_of
from trpg.world.errors import WorldError
from trpg.world.state import CharacterState, CompanionAffinity, CompanionBench

__all__ = [
    "companion_defs",
    "companion_spawns",
    "companion_win_affinity",
    "free_slots",
    "member_names",
    "sync_companions",
    "wanted_companions",
]


def _companions(library: ContentLibrary) -> dict[str, CompanionDef]:
    table = library.world_mercenaries
    return {} if table is None else table.companion_by_id()


def _max_hired(library: ContentLibrary) -> int:
    table = library.world_mercenaries
    return 2 if table is None else table.max_hired


def _quest_defs(library: ContentLibrary) -> dict[str, QuestDef]:
    found: dict[str, QuestDef] = {}
    for region in sorted(library.world_quests.quests):
        for quest in library.world_quests.quests[region].quests:
            found[quest.id] = quest
    return found


def _joined_yet(quest: QuestDef, steps_done: int) -> bool:
    """任務的 ``companion_after``（OB-7，#154）：那一步完成了才加入；沒寫＝接任務就加入。"""
    if quest.companion_after is None:
        return True
    index = next(i for i, s in enumerate(quest.steps) if s.id == quest.companion_after)
    return steps_done > index


def wanted_companions(library: ContentLibrary, char: CharacterState) -> tuple[tuple[str, str], ...]:
    """該在隊的夥伴與帶他的任務：進行中任務的 ``companion``（任務 ID 排序、取每名夥伴的第一個）。"""
    defs = _quest_defs(library)
    known = _companions(library)
    wanted: dict[str, str] = {}
    for state in char.quests:  # 已依任務 ID 排序
        quest = defs.get(state.quest)
        if state.done or quest is None or quest.companion is None:
            continue
        if not _joined_yet(quest, state.steps_done):
            continue
        if quest.companion in known and quest.companion not in wanted:
            wanted[quest.companion] = quest.id
    return tuple(wanted.items())


def free_slots(library: ContentLibrary, char: CharacterState) -> int:
    """傭兵＋影子還能選幾名（隊友位扣掉夥伴佔的）。"""
    return max(0, _max_hired(library) - len(char.companions))


def member_names(library: ContentLibrary, char: CharacterState) -> dict[str, str]:
    """隊伍成員 ID → 名字（傭兵、影子主人、夥伴；事件句子用）。"""
    names: dict[str, str] = {}
    table = library.world_mercenaries
    if table is not None:
        names.update((m.id, m.name_zh) for m in table.mercenaries)
        names.update((c.id, c.name_zh) for c in table.companions)
    names.update((s.owner, s.hero.name_zh) for s in char.shadows)
    for bench in char.companion_bench:
        if bench.shadow is not None:
            names[bench.shadow.owner] = bench.shadow.hero.name_zh
    return names


def _join(
    library: ContentLibrary, char: CharacterState, companion: str, quest: str
) -> tuple[CharacterState, WorldEvent]:
    mercs, shadows = list(char.mercenaries), list(char.shadows)
    members = len(mercs) + len(shadows)
    bench = list(char.companion_bench)
    replaced: str | None = None
    ai = dict(char.party_ai)
    if members + len(char.companions) >= _max_hired(library) and members > 0:
        position = min(1, members - 1)  # 替掉出場順序第 2 名（只有 1 名時替掉那 1 名）
        if position < len(mercs):
            replaced = mercs.pop(position)
            entry = CompanionBench(mercenary=replaced, ai=ai.pop(replaced, None), position=position)
        else:
            snapshot = shadows.pop(position - len(mercs))
            replaced = snapshot.owner
            entry = CompanionBench(shadow=snapshot, ai=ai.pop(replaced, None), position=position)
        bench.append(entry)
    names = member_names(library, char)
    char = char.model_copy(
        update={
            "mercenaries": tuple(mercs),
            "shadows": tuple(shadows),
            "party_ai": ai,
            "companions": (*char.companions, companion),
            "companion_bench": tuple(bench),
        }
    )
    event = CompanionJoinedEvent(
        companion=companion,
        quest=quest,
        replaced=replaced,
        replaced_name=None if replaced is None else names.get(replaced, replaced),
    )
    return char, event


def _leave(
    library: ContentLibrary, char: CharacterState, companion: str
) -> tuple[CharacterState, WorldEvent]:
    companions = tuple(c for c in char.companions if c != companion)
    mercs, shadows = list(char.mercenaries), list(char.shadows)
    bench = list(char.companion_bench)
    ai = dict(char.party_ai)
    restored: str | None = None
    names = member_names(library, char)
    room = _max_hired(library) - len(companions) - len(mercs) - len(shadows)
    if bench and room > 0:
        entry = bench.pop()
        restored = entry.member_id
        if entry.mercenary is not None:
            mercs.insert(min(entry.position, len(mercs)), entry.mercenary)
        elif entry.shadow is not None:
            shadows.insert(max(0, entry.position - len(mercs)), entry.shadow)
        if entry.ai is not None:
            ai[restored] = entry.ai
    if not companions:
        bench = []  # 夥伴都走了：還原不了的就不再還原
    char = char.model_copy(
        update={
            "mercenaries": tuple(mercs),
            "shadows": tuple(shadows),
            "party_ai": ai,
            "companions": companions,
            "companion_bench": tuple(bench),
        }
    )
    event = CompanionLeftEvent(
        companion=companion,
        restored=restored,
        restored_name=None if restored is None else names.get(restored, restored),
    )
    return char, event


def sync_companions(
    library: ContentLibrary, char: CharacterState
) -> tuple[CharacterState, list[WorldEvent]]:
    """依進行中的任務讓夥伴加入或離隊（見模組說明）；沒有變化時原樣回傳、沒有事件。"""
    wanted = wanted_companions(library, char)
    wanted_ids = [c for c, _q in wanted]
    events: list[WorldEvent] = []
    for companion in [c for c in char.companions if c not in wanted_ids]:
        char, event = _leave(library, char, companion)
        events.append(event)
    for companion, quest in wanted:
        if companion not in char.companions:
            char, event = _join(library, char, companion, quest)
            events.append(event)
    return char, events


def companion_defs(library: ContentLibrary, char: CharacterState) -> tuple[CompanionDef, ...]:
    """隊伍裡的夥伴定義（加入順序）；名單不見了時拋 :class:`WorldError`（內容錯誤）。"""
    known = _companions(library)
    missing = [c for c in char.companions if c not in known]
    if missing:
        raise WorldError(f"劇情夥伴名單沒有：{', '.join(missing)}")
    return tuple(known[c] for c in char.companions)


def companion_spawns(library: ContentLibrary, char: CharacterState) -> tuple[UnitSpawn, ...]:
    """夥伴的出場設定（1 級基準，還沒照主角等級成長；加入順序）。"""
    # 延後匯入：party 匯入本模組（hire 的隊友位上限）
    from trpg.world.party import slot_capped  # noqa: PLC0415

    builds = library.builds.by_id()
    spawns: list[UnitSpawn] = []
    for companion in companion_defs(library, char):
        base = builds[companion.build].hero
        update: dict[str, object] = {"id": companion.id, "name_zh": companion.name_zh}
        if companion.ai_profile is not None:  # 打法（阿岳＝弓手，遠程保持距離；5C-3b）
            update["ai_profile"] = companion.ai_profile
        template = slot_capped(library, base).model_copy(update=update)
        spawns.append(
            UnitSpawn(
                template=template,
                weapon=library.weapon_of(template),
                equipment=library.loadout_of(template),
                team=Team.ALLY,
            )
        )
    return tuple(spawns)


def companion_win_affinity(
    library: ContentLibrary, char: CharacterState, now: int
) -> tuple[CharacterState, list[WorldEvent]]:
    """帶夥伴打贏一場：夥伴的 NPC 好感度 +``affinity_per_win``（每天累計不超過上限，18.7.6）。"""
    today = day_of(library, now)
    events: list[WorldEvent] = []
    for companion in companion_defs(library, char):
        if companion.affinity_per_win <= 0:
            continue
        record = char.companion_affinity.get(companion.id)
        gained = 0 if record is None or record.day != today else record.gained
        delta = min(companion.affinity_per_win, companion.affinity_daily_cap - gained)
        if delta <= 0:
            continue
        char, event = change_affinity(
            library, char, companion.npc, delta, f"companion_win:{companion.id}"
        )
        records = dict(char.companion_affinity)
        records[companion.id] = CompanionAffinity(day=today, gained=gained + delta)
        char = char.model_copy(update={"companion_affinity": dict(sorted(records.items()))})
        events.append(event)
    return char, events
