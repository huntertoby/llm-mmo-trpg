"""戰鬥掉落（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.4；20.2、M1、8.26.2）。

- **材料**：陣容的敵方成員在戰鬥結束時倒下就掉；第三方要「被我方擊倒」（倒下前最後一次受到傷害的
  來源是我方單位，含我方召喚物；玩法 PM 2026-11-03、代決 5D2-3）。精英必掉 1 份（詞綴的稀有材料 >
  家族材料 > 通用料），一般敵人 ``material_permille`` 掉 1 份（家族材料〔區域的優先，其次
  各區共用的，例：盜賊各區掉焦鐵，5D-2b〕，沒有家族的掉通用料）。
- **裝備**：陣容的每名精英必掉 1 件、``elite_epic_permille`` 史詩（20.2；5D-2b 玩法 PM 代決，取代
  5D2-4 的一場 1 件）；沒有精英時 ``battle_permille`` 掉 1 件；物品等級＝地點建議等級（敵人等級），
  詞條偏向該區關鍵字（20.2）。
- **進背包**：材料先、裝備後，依掉落順序逐份放；放不下的留給戰後結算（``pending_loot``），玩家選要
  丟哪件（新拿到的、原本的都可以；5D-2b 玩法 PM 代決，取代 5D2-6 的不撿，不做暫存區）。

- **主手的武器大類**（6T-1a，08 8.13 #135）：野外一般戰鬥 50% 和主角同大類、精英 75%，其餘依全服
  在線角色的武器大類比例（:mod:`trpg.world.weapon_mix`）；區域 Boss、懸賞一律同大類。大類的亂數是
  裝備亂數的 ``fork("main_hand")``（不推進原本的串流，其他掉落照舊）。

亂數：``Rng(fnv1a64(f"{battle_seed}:loot"))``（材料依敵人順序抽，裝備用 ``fork("gear")``；
第 2 名起的精英用 ``fork("gear/<序號>")``，所以只有 1 名精英的場次和之前一樣）；
不耗角色亂數，不讀時間、不呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from trpg.content.equipment import ItemDef
from trpg.content.item_budget import Rarity
from trpg.content.item_gen import generate_item_retrying
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPES, SlotType
from trpg.content.world_loot import LootRules
from trpg.engine.events import DamageDealt, EventBase, UnitDowned
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Team, UnitId
from trpg.world.actions import WorldEvent
from trpg.world.economy_actions import (
    LootAbandonedEvent,
    LootChooseAction,
    LootChosenEvent,
    LootGainedEvent,
)
from trpg.world.encounters import EncounterLineup, LineupMember
from trpg.world.errors import WorldActionError
from trpg.world.inventory import bag_capacity, remove_gear, slots_over, slots_used
from trpg.world.state import CharacterState, LootSummary, PendingLoot, WeaponMix
from trpg.world.weapon_mix import DropKind, main_hand_class, weapon_class_of

__all__ = [
    "LootRoll",
    "add_loot",
    "boss_bonus_units",
    "choose_loot",
    "loot_rules",
    "roll_loot",
    "third_downed_by_allies",
]


def loot_rules(library: ContentLibrary) -> LootRules | None:
    """掉落規則；內容庫沒有 ``world/loot.yaml`` 時為 ``None``（掉落與系統裝備關閉）。"""
    return library.world_loot


@dataclass(frozen=True)
class LootRoll:
    """一場戰鬥掉的東西（還沒放進背包）：材料（依掉落順序，每份 1 個）與裝備（每名精英 1 件，
    沒有精英時最多 1 件）。"""

    materials: tuple[str, ...] = ()
    gear: tuple[ItemDef, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return not self.materials and not self.gear


# ---------------------------------------------------------------------------
# 誰倒下、誰打倒的
# ---------------------------------------------------------------------------


def _unit_ids(setup: BattleSetup) -> tuple[UnitId, ...]:
    """設定順序的單位 ID（引擎依序配發 ``unit_0001`` 起）。"""
    return tuple(UnitId(f"unit_{i:04d}") for i in range(1, len(setup.units) + 1))


def third_downed_by_allies(state: BattleState, events: Sequence[EventBase]) -> frozenset[UnitId]:
    """倒下前最後一次受到傷害的來源是我方單位（含我方召喚物）的單位（代決 5D2-3）。"""
    last_source: dict[UnitId, UnitId | None] = {}
    downed_by_ally: set[UnitId] = set()
    for event in events:
        if isinstance(event, DamageDealt):
            last_source[event.target_id] = event.source_id
        elif isinstance(event, UnitDowned):
            source = last_source.get(event.unit_id)
            unit = None if source is None else state.units.get(source)
            if unit is not None and unit.team is Team.ALLY:
                downed_by_ally.add(event.unit_id)
            else:
                downed_by_ally.discard(event.unit_id)
    return frozenset(downed_by_ally)


def _dropping_members(
    setup: BattleSetup,
    lineup: EncounterLineup,
    state: BattleState,
    events: Sequence[EventBase],
    *,
    duel: bool = False,
) -> list[LineupMember]:
    """會掉材料的陣容成員（依陣容順序：敵方、第三方）。精英單挑（RG-2，``duel``）打贏時照整個敵方
    陣容算（和拒絕單挑、全隊打贏時一樣；第三方沒上場、不掉）。"""
    if duel:
        return list(lineup.members)
    ids = _unit_ids(setup)
    enemy_ids = [uid for uid, s in zip(ids, setup.units, strict=True) if s.team is Team.ENEMY]
    third_ids = [uid for uid, s in zip(ids, setup.units, strict=True) if s.team is Team.THIRD]
    by_allies = third_downed_by_allies(state, events)
    found: list[LineupMember] = []
    for member, uid in zip(lineup.members, enemy_ids, strict=False):
        unit = state.units.get(uid)
        if unit is not None and unit.downed:
            found.append(member)
    for member, uid in zip(lineup.third, third_ids, strict=False):
        unit = state.units.get(uid)
        if unit is not None and unit.downed and uid in by_allies:
            found.append(member)
    return found


# ---------------------------------------------------------------------------
# 抽掉落
# ---------------------------------------------------------------------------


def _is_elite(library: ContentLibrary, member: LineupMember) -> bool:
    catalog = library.enemy_catalog()
    return member.affix is not None or catalog.is_elite(catalog.template(member.unit))


def _material_of(
    rules: LootRules, region: str, member: LineupMember, level: int, *, elite: bool
) -> str:
    loot = rules.region(region)
    if elite and member.affix is not None and member.affix in loot.elite_affixes:
        return loot.elite_affixes[member.affix]
    return rules.family_material(region, member.unit) or rules.generic_material(level)


def _weighted(rng: Rng, weights: dict[Rarity, int]) -> Rarity:
    order: list[Rarity] = ["common", "uncommon", "rare", "epic"]
    pool = [(r, weights.get(r, 0)) for r in order if weights.get(r, 0) > 0]
    roll = rng.randint(0, sum(w for _, w in pool) - 1)
    for rarity, weight in pool:
        if roll < weight:
            return rarity
        roll -= weight
    raise AssertionError("unreachable")


def _gear_parts(library: ContentLibrary, char: CharacterState) -> list[SlotType]:
    """能掉的物品種類：主角武器是雙手或成對時不出副手（同 roguelite 三選一）。"""
    weapon = library.weapons[char.hero.weapon]
    main = char.equipment.get("main_hand")
    blocked = weapon.two_handed or weapon.paired or (main is not None and main.paired)
    return [t for t in SLOT_TYPES if not (t == "offhand" and blocked)]


def _roll_gear(
    library: ContentLibrary,
    rules: LootRules,
    char: CharacterState,
    rng: Rng,
    *,
    region: str,
    level: int,
    elite: bool,
    forced: Rarity | None = None,
    fixed: bool = False,
    mix: WeaponMix | None = None,
) -> tuple[ItemDef, ...]:
    gear = rules.gear
    if elite:
        epic = rng.randint(0, 999) < gear.elite_epic_permille
        rarity: Rarity = "epic" if epic else _weighted(rng, gear.battle_weights)
        if forced is not None:  # 區域 Boss 的保底（5F-3）：亂數照抽，稀有度換掉
            rarity = forced
    elif rng.randint(0, 999) < gear.battle_permille:
        rarity = _weighted(rng, gear.battle_weights)
    else:
        return ()
    if library.item_gen is None:
        return ()
    parts = _gear_parts(library, char)
    part = parts[rng.randint(0, len(parts) - 1)]
    item_level = max(1, min(level, gear.max_item_level))
    weapon_class = weapon_class_of(library, char)
    if part == "weapon":  # 6T-1a（#135）：別大類的主手
        kind: DropKind = "fixed" if fixed else ("elite" if elite else "field")
        weapon_class = main_hand_class(
            gear.main_hand, mix, weapon_class, kind=kind, rng=rng.fork("main_hand")
        )
    item = generate_item_retrying(
        library,
        rng,
        part,
        rarity,
        item_level,
        weapon_class=weapon_class if part == "weapon" else None,
        keywords=rules.region(region).keywords,
    )
    return () if item is None else (item,)


def roll_loot(
    library: ContentLibrary,
    char: CharacterState,
    *,
    setup: BattleSetup,
    lineup: EncounterLineup,
    state: BattleState,
    events: Sequence[EventBase],
    seed: int,
    level: int,
    boss_bonus: frozenset[str] = frozenset(),
    fixed_class: bool = False,
    mix: WeaponMix | None = None,
    duel: bool = False,
) -> LootRoll:
    """打贏一場掉的東西（見模組說明）；沒有掉落規則時為空。``level`` 是地點建議等級（敵人等級）。

    ``boss_bonus``（Phase 5F-3）：這場拿保底掉落的區域 Boss（單位 ID）——材料換成 Boss 材料、
    裝備換成保底稀有度；亂數照常消耗（其他掉落和沒有保底時一樣）。

    ``fixed_class``（6T-1a）：區域 Boss、懸賞的戰鬥，主手一律同大類；``mix`` 是世界今天的主手大類
    比例（:attr:`~trpg.world.state.WorldState.weapon_mix`）。"""
    rules = loot_rules(library)
    if rules is None:
        return LootRoll()
    rng = Rng(fnv1a64(f"{seed}:loot".encode()))
    materials: list[str] = []
    for member in _dropping_members(setup, lineup, state, events, duel=duel):
        elite = _is_elite(library, member)
        if elite or rng.randint(0, 999) < rules.material_permille:
            materials.append(_material_of(rules, lineup.region, member, level, elite=elite))
            if member.unit in boss_bonus:
                materials[-1] = rules.bosses[member.unit].material
    elite_members = [m for m in lineup.members if _is_elite(library, m)]
    elites = len(elite_members)
    gear: list[ItemDef] = []
    for n in range(max(1, elites)):  # 每名精英 1 件（20.2、5D-2b）；沒有精英時照一般掉落抽 1 次
        boss = elite_members[n].unit if elites and elite_members[n].unit in boss_bonus else None
        gear += _roll_gear(
            library,
            rules,
            char,
            rng.fork("gear" if n == 0 else f"gear/{n + 1}"),
            region=lineup.region,
            level=level,
            elite=elites > 0,
            forced=None if boss is None else rules.bosses[boss].gear_rarity,
            fixed=fixed_class,
            mix=mix,
        )
    return LootRoll(materials=tuple(materials), gear=tuple(gear))


def boss_bonus_units(
    library: ContentLibrary, char: CharacterState, lineup: EncounterLineup, today: int
) -> frozenset[str]:
    """這場能拿保底掉落的區域 Boss：陣容裡列在 ``bosses``、角色這個刷新日還沒拿過的（5F-3）。"""
    rules = loot_rules(library)
    if rules is None:
        return frozenset()
    return frozenset(
        m.unit
        for m in lineup.members
        if m.unit in rules.bosses and char.boss_drop_days.get(m.unit) != today
    )


# ---------------------------------------------------------------------------
# 進背包
# ---------------------------------------------------------------------------


def _unique_id(item: ItemDef, taken: set[str]) -> ItemDef:
    """背包裡已經有同 ID 的裝備時加序號（產生器的 ID 是 32 位元亂數，極少撞到）。"""
    if item.id not in taken:
        return item
    n = 2
    while f"{item.id}_{n}" in taken:
        n += 1
    return item.model_copy(update={"id": f"{item.id}_{n}"})


def _abandon(char: CharacterState) -> tuple[CharacterState, list[WorldEvent]]:
    """上一場沒決定的戰利品留在原地（5D-2b：只留最近一場，不做暫存區）。"""
    pending = char.pending_loot
    if pending is None:
        return char, []
    event = LootAbandonedEvent(
        materials=dict(pending.materials), gear_names=tuple(g.name_zh for g in pending.gear)
    )
    return char.model_copy(update={"pending_loot": None}), [event]


def add_loot(
    library: ContentLibrary, char: CharacterState, roll: LootRoll
) -> tuple[CharacterState, LootSummary | None, list[WorldEvent]]:
    """把掉落逐份放進背包（材料先、裝備後）；放不下的留給戰後結算選要丟哪件（5D-2b，取代代決
    5D2-6 的不撿）。上一場還沒決定的先留在原地。"""
    char, events = _abandon(char)
    if roll.empty:
        return char, None, events
    cap = bag_capacity(library)
    slots = 10**9 if cap is None else cap  # 沒有經濟規則：沒有格數上限
    bag = dict(char.bag)
    gear = list(char.gear)
    got: dict[str, int] = {}
    over: dict[str, int] = {}
    for item in roll.materials:
        trial = {**bag, item: bag.get(item, 0) + 1}
        if slots_used(library, trial, len(gear)) <= slots:
            bag = trial
            got[item] = got.get(item, 0) + 1
        else:
            over[item] = over.get(item, 0) + 1
    taken = {g.id for g in gear} | {g.id for g in char.equipment.values()}
    got_gear: list[ItemDef] = []
    over_gear: list[ItemDef] = []
    for dropped in roll.gear:
        piece = _unique_id(dropped, taken)
        taken.add(piece.id)
        if slots_used(library, bag, len(gear)) + 1 <= slots:
            gear.append(piece)
            got_gear.append(piece)
        else:
            over_gear.append(piece)
    pending = PendingLoot(materials=over, gear=tuple(over_gear))
    char = char.model_copy(
        update={
            "bag": dict(sorted(bag.items())),
            "gear": tuple(gear),
            "pending_loot": None if pending.empty else pending,
        }
    )
    summary = LootSummary(materials=got, gear=tuple(g.name_zh for g in got_gear))
    events.append(
        LootGainedEvent(
            materials=dict(sorted(got.items())),
            gear=tuple(g.id for g in got_gear),
            gear_names=tuple(g.name_zh for g in got_gear),
            pending_materials=dict(pending.materials),
            pending_gear_names=tuple(g.name_zh for g in over_gear),
        )
    )
    return char, summary, events


# ---------------------------------------------------------------------------
# 戰後結算：背包滿了選要丟哪件（5D-2b）
# ---------------------------------------------------------------------------


def _drop_items(
    library: ContentLibrary,
    bag: dict[str, int],
    pending: dict[str, int],
    drops: Mapping[str, int],
) -> None:
    """先丟新拿到的，再丟背包裡的（就地修改）。"""
    for item, count in sorted(drops.items()):
        if count <= 0:
            raise WorldActionError("丟掉的個數至少 1")
        found = library.world_economy.items.get(item)
        name = item if found is None else found.name_zh
        if count > pending.get(item, 0) + bag.get(item, 0):
            raise WorldActionError(f"{name}沒有那麼多")
        from_pending = min(count, pending.get(item, 0))
        for counts, n in ((pending, from_pending), (bag, count - from_pending)):
            left = counts.get(item, 0) - n
            if left > 0:
                counts[item] = left
            else:
                counts.pop(item, None)


def _drop_gear(
    gear: Sequence[ItemDef], pending: list[ItemDef], drops: Sequence[str]
) -> tuple[list[str], list[str]]:
    """丟掉指定的裝備：新拿到的就地從 ``pending`` 拿掉；回傳丟掉的名稱與背包裡要丟的 ID（呼叫者用
    :func:`~trpg.world.inventory.remove_gear` 拿掉，連同改動紀錄）。"""
    if len(set(drops)) != len(drops):
        raise WorldActionError("同一件裝備只能丟一次")
    names: list[str] = []
    from_bag: list[str] = []
    for gear_id in drops:
        piece = next((g for g in pending if g.id == gear_id), None)
        if piece is not None:
            pending.remove(piece)
            names.append(piece.name_zh)
            continue
        piece = next((g for g in gear if g.id == gear_id), None)
        if piece is None:
            raise WorldActionError("背包裡沒有這件裝備（穿戴中的不能丟）")
        names.append(piece.name_zh)
        from_bag.append(gear_id)
    return names, from_bag


def choose_loot(
    library: ContentLibrary, char: CharacterState, action: LootChooseAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """戰後結算：丟掉選的（新拿到的或背包裡的），剩下的戰利品收進背包；放不下就拒絕。"""
    loot = char.pending_loot
    if loot is None:
        raise WorldActionError("沒有等著決定的戰利品")
    bag = dict(char.bag)
    pending_items = dict(loot.materials)
    pending_gear = list(loot.gear)
    _drop_items(library, bag, pending_items, action.drop_items)
    dropped_gear, from_bag = _drop_gear(char.gear, pending_gear, action.drop_gear)
    for item, count in pending_items.items():
        bag[item] = bag.get(item, 0) + count
    char = remove_gear(char, from_bag)
    gear = (*char.gear, *pending_gear)
    short = slots_over(library, bag, len(gear))
    if short > 0:
        raise WorldActionError(f"背包還是放不下：還差 {short} 格")
    char = char.model_copy(
        update={"bag": dict(sorted(bag.items())), "gear": gear, "pending_loot": None}
    )
    event = LootChosenEvent(
        dropped_items=dict(sorted(action.drop_items.items())),
        dropped_gear_names=tuple(dropped_gear),
        materials=dict(sorted(pending_items.items())),
        gear=tuple(g.id for g in pending_gear),
        gear_names=tuple(g.name_zh for g in pending_gear),
    )
    return char, (event,)
