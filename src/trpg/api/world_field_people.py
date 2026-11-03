"""實地地圖上的人（Phase 6B-4；21.5、21.7）：NPC 頭上的好感表情與「！」、站在城裡的朋友（影子）。

- **好感**：照 :func:`trpg.world.affinity.rank_of`（5 級，9.6.11 #116）。
- **「！」**（玩法 PM 未定細節，開發 PM 規格「有新傳聞或可接任務」；最保守的解讀）：
  - ``quest``：這位 NPC 給的任務還沒接、開始條件成立、對方沒有敵視；或聊天內容裡有指向還沒接的任務的
    入口（``quest_entry``）。
  - ``rumor``：今天（6 點刷新）還沒和他聊過，而且他依目前好感聊得出傳聞（``rumor``）。
  - 兩種都有時顯示 ``quest``。
- **朋友**：其他角色在這個城鎮存的影子（#102：城鎮整備時存），只在城鎮的主地圖（不是室內）。
  位置＝從入口走得到、沒有出口／門／傳送石／設施／事件點的可站格裡，依主人 ID 的 FNV-1a 雜湊取一格；
  撞到別的朋友就往後找下一格。依主人 ID 排序處理，同樣的地圖與朋友名單一定得到同樣的位置（確定性）。

純顯示、不改狀態、不耗亂數。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from trpg.api.world_field_schemas import FieldFriendView, FieldGearLookView, FieldHeroView
from trpg.content.appearance import derive_keywords
from trpg.content.battle import UnitTemplate
from trpg.content.equipment import Loadout
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.world_quests import AffinityRank
from trpg.engine.view import AppearanceView
from trpg.shared.rng import fnv1a64
from trpg.world.affinity import affinity_rules, rank_of, talk_entries
from trpg.world.calendar import day_of
from trpg.world.field import FieldGrid
from trpg.world.gear import item_loadout
from trpg.world.quests import condition_holds, quest_table
from trpg.world.state import CharacterState, ShadowSnapshot, WorldState

__all__ = [
    "ALERT_ZH",
    "TOWN_FRIENDS_MAX",
    "NpcMark",
    "friend_cells",
    "friends_here",
    "look_of",
    "npc_marks",
]

TOWN_FRIENDS_MAX: Final = 8
"""一張城鎮圖最多站幾位朋友（依主人 ID 取前幾位）。"""

ALERT_ZH: Final[Mapping[str, str]] = {"quest": "有任務可以接", "rumor": "有新的傳聞"}

type Alert = Literal["quest", "rumor"]
type XY = tuple[int, int]


class NpcMark:
    """一位 NPC 頭上的東西：好感級別與「！」。"""

    __slots__ = ("alert", "rank", "rank_zh")

    def __init__(self, rank: AffinityRank, rank_zh: str, alert: Alert | None) -> None:
        self.rank = rank
        self.rank_zh = rank_zh
        self.alert = alert


def _quest_alert(
    library: ContentLibrary, world: WorldState | None, char: CharacterState, npc: str, now: int
) -> bool:
    """這位 NPC 有沒有可以接的任務（給任務的人是他、還沒接、開始條件成立、沒有敵視）。"""
    for entry in talk_entries(library, char, npc):
        quest = entry.quest
        if entry.kind == "quest_entry" and quest is not None and char.quest_state(quest) is None:
            return True
    if world is None or rank_of(library, char, npc) == "hostile":
        return False
    table = quest_table(library, char.region)
    if table is None:
        return False
    for defn in table.quests:
        if defn.giver != npc or char.quest_state(defn.id) is not None:
            continue
        if all(condition_holds(library, world, char, c, events=(), now=now) for c in defn.start):
            return True
    return False


def _rumor_alert(library: ContentLibrary, char: CharacterState, npc: str, now: int) -> bool:
    if char.talk_days.get(npc) == day_of(library, now):
        return False
    return any(e.kind == "rumor" for e in talk_entries(library, char, npc))


def npc_marks(
    library: ContentLibrary,
    world: WorldState | None,
    char: CharacterState,
    npcs: Sequence[str],
    now: int,
) -> dict[str, NpcMark]:
    """``npcs`` 每一位的好感級別與「！」（見模組說明）。"""
    names = {r.id: r.name_zh for r in affinity_rules(library).ranks}
    out: dict[str, NpcMark] = {}
    for npc in npcs:
        rank = rank_of(library, char, npc)
        alert: Alert | None = None
        if _quest_alert(library, world, char, npc, now):
            alert = "quest"
        elif _rumor_alert(library, char, npc, now):
            alert = "rumor"
        out[npc] = NpcMark(rank, names.get(rank, rank), alert)
    return out


# ---------------------------------------------------------------------------
# 外觀
# ---------------------------------------------------------------------------


def look_of(library: ContentLibrary, hero: UnitTemplate, loadout: Loadout) -> FieldHeroView:
    """紙娃娃外觀（同戰鬥 ``UnitView`` 的 ``doll_look``、武器、種族外觀與裝備外觀；純顯示）。"""
    weapon = library.weapons.get(hero.weapon)
    race = None
    if hero.race is not None:
        try:
            race = library.ruleset.race_def(hero.race).look
        except KeyError:
            race = None
    gear = tuple(
        FieldGearLookView(
            slot=e.slot,
            appearance=AppearanceView(
                kind=e.item.kind,
                form=e.item.form,
                material=e.item.material,
                dye=e.item.dye,
                style=e.item.style,
                rarity=e.item.rarity or ("legendary" if e.item.legendary else "common"),
                keywords=derive_keywords(a.affix for a in e.affixes),
            ),
        )
        for e in loadout.items
    )
    return FieldHeroView(
        template_id=hero.id,
        doll_look=hero.doll,
        weapon_id=hero.weapon,
        weapon_class="melee" if weapon is None else weapon.weapon_class,
        race_look=race,
        equipment=gear,
    )


# ---------------------------------------------------------------------------
# 朋友
# ---------------------------------------------------------------------------


def _reserved(found: FieldMapDef) -> set[XY]:
    """朋友不站的格子：入口、出口、門、傳送石、設施、營火、事件點、情境物件。"""
    cells = {found.entry}
    cells |= {c for e in found.exits for c in e.at}
    cells |= {d.at for d in found.doors}
    cells |= {s.at for s in found.teleport_stones}
    cells |= {f.at for f in found.facilities}
    cells |= {s.at for s in (*found.campfires, *found.event_spots, *found.situation_objects)}
    return cells


def friend_cells(
    found: FieldMapDef, grid: FieldGrid, owners: Sequence[str], max_climb: int
) -> dict[str, XY]:
    """每位朋友站的格子（見模組說明；``owners`` 依 ID 排序處理，格子不夠時後面的不放）。"""
    reserved = _reserved(found)
    spots = sorted(
        (c for c in grid.reachable(found.entry, max_climb) if c not in reserved),
        key=lambda c: (c[1], c[0]),
    )
    out: dict[str, XY] = {}
    taken: set[XY] = set()
    for owner in sorted(owners):
        if len(taken) >= len(spots):
            break
        i = fnv1a64(owner.encode("utf-8")) % len(spots)
        while spots[i] in taken:
            i = (i + 1) % len(spots)
        taken.add(spots[i])
        out[owner] = spots[i]
    return out


def _snapshot_loadout(library: ContentLibrary, snap: ShadowSnapshot) -> Loadout:
    if snap.equipment:
        return item_loadout(library, snap.equipment)
    return library.loadout_of(snap.hero)


def friends_here(
    library: ContentLibrary,
    world: WorldState | None,
    char: CharacterState,
    found: FieldMapDef,
    grid: FieldGrid,
) -> tuple[FieldFriendView, ...]:
    """站在這張城鎮圖上的朋友（見模組說明；不是城鎮、室內、沒有世界狀態＝空）。"""
    if world is None or found.is_interior or not _is_town(library, found):
        return ()
    snaps = sorted(
        (
            s.snapshot
            for s in world.shadows
            if s.snapshot.owner != char.character_id
            and s.snapshot.region == found.region
            and s.snapshot.location == found.place
        ),
        key=lambda s: s.owner,
    )[:TOWN_FRIENDS_MAX]
    climb = library.ruleset.core.max_climb_height
    cells = friend_cells(found, grid, [s.owner for s in snaps], climb)
    return tuple(
        FieldFriendView(
            owner=s.owner,
            name_zh=s.hero.name_zh,
            level=s.level,
            x=cells[s.owner][0],
            y=cells[s.owner][1],
            look=look_of(library, s.hero, _snapshot_loadout(library, s)),
        )
        for s in snaps
        if s.owner in cells
    )


def _is_town(library: ContentLibrary, found: FieldMapDef) -> bool:
    world_map = library.world_maps.get(found.region)
    loc = None if world_map is None else world_map.location_by_id().get(found.place)
    return loc is not None and loc.kind == "town"
