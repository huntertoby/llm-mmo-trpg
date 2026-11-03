"""戰鬥掉落（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.4；20.2、M1、8.26.2）。

- **材料**：陣容的敵方成員在戰鬥結束時倒下就掉；第三方要「被我方擊倒」（倒下前最後一次受到傷害的
  來源是我方單位，含我方召喚物；玩法 PM 2026-11-03、代決 5D2-3）。精英必掉 1 份（詞綴的稀有材料 >
  家族材料 > 通用料），一般敵人 ``material_permille`` 掉 1 份（家族材料〔區域的優先，其次各區共用的，
  例：盜賊各區掉焦鐵，5D-2b〕，沒有家族的掉通用料）。
- **裝備**：陣容的每名精英必掉 1 件、``elite_epic_permille`` 史詩（20.2；5D-2b 玩法 PM 代決，取代
  5D2-4 的一場 1 件）；沒有精英時 ``battle_permille`` 掉 1 件；物品等級＝地點建議等級（敵人等級），
  詞條偏向該區關鍵字（20.2）。
- **進背包**：材料先、裝備後，依掉落順序逐份放；放不下的不撿（代決 5D2-6）。

亂數：``Rng(fnv1a64(f"{battle_seed}:loot"))``（材料依敵人順序抽，裝備用 ``fork("gear")``；第 2 名起的
精英用 ``fork("gear/<序號>")``，所以只有 1 名精英的場次和之前一樣）；
不耗角色亂數，不讀時間、不呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from trpg.content.equipment import ItemDef
from trpg.content.item_budget import Rarity
from trpg.content.item_gen import ItemGenError, generate_item
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPES, SlotType
from trpg.content.world_loot import LootRules
from trpg.engine.events import DamageDealt, EventBase, UnitDowned
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Team, UnitId
from trpg.world.economy import bag_slots_used, economy_rules
from trpg.world.economy_actions import LootGainedEvent
from trpg.world.encounters import EncounterLineup, LineupMember
from trpg.world.gear import loot_rules
from trpg.world.state import CharacterState, LootSummary

__all__ = ["LootRoll", "add_loot", "roll_loot", "third_downed_by_allies"]


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
) -> list[LineupMember]:
    """會掉材料的陣容成員（依陣容順序：敵方、第三方）。"""
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
) -> tuple[ItemDef, ...]:
    gear = rules.gear
    if elite:
        epic = rng.randint(0, 999) < gear.elite_epic_permille
        rarity: Rarity = "epic" if epic else _weighted(rng, gear.battle_weights)
    elif rng.randint(0, 999) < gear.battle_permille:
        rarity = _weighted(rng, gear.battle_weights)
    else:
        return ()
    if library.item_gen is None:
        return ()
    parts = _gear_parts(library, char)
    part = parts[rng.randint(0, len(parts) - 1)]
    item_level = max(1, min(level, gear.max_item_level))
    weapon_class = library.weapons[char.hero.weapon].weapon_class
    for attempt in range(library.item_gen.offer_attempts):
        try:
            item = generate_item(
                library,
                rng.fork(f"try/{attempt}"),
                part,
                rarity,
                item_level,
                weapon_class=weapon_class if part == "weapon" else None,
                keywords=rules.region(region).keywords,
            )
        except ItemGenError:
            continue
        return (item,)
    return ()


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
) -> LootRoll:
    """打贏一場掉的東西（見模組說明）；沒有掉落規則時為空。``level`` 是地點建議等級（敵人等級）。"""
    rules = loot_rules(library)
    if rules is None:
        return LootRoll()
    rng = Rng(fnv1a64(f"{seed}:loot".encode()))
    materials: list[str] = []
    for member in _dropping_members(setup, lineup, state, events):
        elite = _is_elite(library, member)
        if elite or rng.randint(0, 999) < rules.material_permille:
            materials.append(_material_of(rules, lineup.region, member, level, elite=elite))
    elites = sum(1 for m in lineup.members if _is_elite(library, m))
    gear: list[ItemDef] = []
    for n in range(max(1, elites)):  # 每名精英 1 件（20.2、5D-2b）；沒有精英時照一般掉落抽 1 次
        gear += _roll_gear(
            library,
            rules,
            char,
            rng.fork("gear" if n == 0 else f"gear/{n + 1}"),
            region=lineup.region,
            level=level,
            elite=elites > 0,
        )
    return LootRoll(materials=tuple(materials), gear=tuple(gear))


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


def add_loot(
    library: ContentLibrary, char: CharacterState, roll: LootRoll
) -> tuple[CharacterState, LootSummary | None, list[LootGainedEvent]]:
    """把掉落逐份放進背包（材料先、裝備後）；放不下的不撿（代決 5D2-6）。"""
    if roll.empty:
        return char, None, []
    rules = economy_rules(library)
    slots = 10**9 if rules is None else rules.bag_slots
    bag = dict(char.bag)
    gear = list(char.gear)
    got: dict[str, int] = {}
    lost: dict[str, int] = {}
    for item in roll.materials:
        trial = {**bag, item: bag.get(item, 0) + 1}
        if bag_slots_used(library, trial) + len(gear) <= slots:
            bag = trial
            got[item] = got.get(item, 0) + 1
        else:
            lost[item] = lost.get(item, 0) + 1
    taken = {g.id for g in gear} | {g.id for g in char.equipment.values()}
    got_gear: list[ItemDef] = []
    lost_gear: list[str] = []
    for dropped in roll.gear:
        if bag_slots_used(library, bag) + len(gear) + 1 <= slots:
            piece = _unique_id(dropped, taken)
            taken.add(piece.id)
            gear.append(piece)
            got_gear.append(piece)
        else:
            lost_gear.append(dropped.name_zh)
    char = char.model_copy(update={"bag": dict(sorted(bag.items())), "gear": tuple(gear)})
    summary = LootSummary(
        materials=got,
        gear=tuple(g.name_zh for g in got_gear),
        lost_materials=lost,
        lost_gear=tuple(lost_gear),
    )
    event = LootGainedEvent(
        materials=dict(sorted(got.items())),
        gear=tuple(g.id for g in got_gear),
        gear_names=tuple(g.name_zh for g in got_gear),
        lost_materials=dict(sorted(lost.items())),
        lost_gear_names=tuple(lost_gear),
    )
    return char, summary, [event]
