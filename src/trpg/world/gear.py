"""大世界的裝備：主角換裝、傭兵與影子的裝備（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.4）。

- **主角**：``CharacterState.equipment``（空＝範本的裝備）；背包裡的裝備在 ``CharacterState.gear``。
  ``equip`` 動作在城鎮或營火（同換技能）照 roguelite 的 :func:`~trpg.roguelite.gear.equip` 換上
  （主手只換同大類、雙手武器收起副手、戒指先放空的），換下的放回背包（代決 5D2-7）。
- **回收**（20.1）在 :func:`trpg.world.economy.gear_price`。
- **傭兵**（20.5）：``mercenary_gear.slots`` 裡範本沒穿的欄位穿系統裝備（稀有、物品等級＝主角等級、
  詞條關鍵字＝底稿 build 的關鍵字）；亂數由傭兵、欄位、等級決定，每個人都一樣（#87）。
- **影子**（20.5、#87）：存影子時帶 ``equipment``；借用時物品等級超過招募者等級的那件不穿
  （代決 5D2-10）。

純函式：不讀時間、不呼叫 LLM；傭兵裝備的亂數由 ``fnv1a64`` 衍生，不耗角色亂數。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.battle import UnitTemplate
from trpg.content.equipment import ItemDef, Loadout, resolve_loadout
from trpg.content.item_gen import downscale_item, generate_item_retrying
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.gear import equip_swap, target_slot, worn_items
from trpg.roguelite.state import RunState
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.economy_actions import EquipAction, ItemEquippedEvent
from trpg.world.errors import WorldActionError
from trpg.world.growth import as_run, at_service
from trpg.world.inventory import room_problem
from trpg.world.loot import loot_rules
from trpg.world.resonance import apply_resonance
from trpg.world.state import CharacterState

__all__ = [
    "apply_equip",
    "equip_problem",
    "gear_run",
    "hero_loadout",
    "item_loadout",
    "mercenary_equipment",
    "shadow_equipment",
    "worn_gear",
]

_MERC_CACHE_LIMIT = 1024
"""內容庫上傭兵裝備快取（``ContentLibrary.mercenary_gear_cache``）的上限：滿了就清空。"""


def item_loadout(library: ContentLibrary, items: Mapping[str, ItemDef]) -> Loadout:
    """欄位 → 物品的裝備快照（同 roguelite：用欄位名當臨時物品 ID）。"""
    if not items:
        return Loadout()
    return resolve_loadout({slot: slot for slot in items}, dict(items), library.affixes)


def _run(char: CharacterState) -> RunState:
    update = {"equipment": dict(char.equipment), "backpack": char.gear}
    return as_run(char).model_copy(update=update)


def gear_run(char: CharacterState) -> RunState:
    """角色的裝備換成一輪的狀態（API 顯示裝備卡與比較用；5D-4）。"""
    return _run(char)


def worn_gear(library: ContentLibrary, char: CharacterState) -> dict[str, ItemDef]:
    """主角目前穿戴的物品（欄位 → 物品；``equipment`` 空時是範本的裝備）。"""
    return dict(worn_items(library, _run(char)))


def hero_loadout(library: ContentLibrary, char: CharacterState) -> Loadout:
    """主角開戰用的裝備快照：``equipment`` 非空就用它，否則範本的裝備；再加上 2 件共鳴的詞條
    （Phase 5D-3，:mod:`trpg.world.resonance`）。"""
    if char.equipment:
        loadout = item_loadout(library, char.equipment)
    else:
        loadout = library.loadout_of(char.hero)
    weapon = library.weapons.get(char.hero.weapon)
    if weapon is None:
        return loadout
    return apply_resonance(library, loadout, weapon)[0]


# ---------------------------------------------------------------------------
# 換裝
# ---------------------------------------------------------------------------


def equip_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """不能換裝的原因（城鎮或營火、沒有遭遇）；可以時為 ``None``。"""
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if not at_service(library, char):
        return "只有城鎮與營火能換裝備"
    return None


def apply_equip(
    library: ContentLibrary, char: CharacterState, action: EquipAction
) -> tuple[CharacterState, tuple[ItemEquippedEvent, ...]]:
    """``equip`` 動作（見模組說明）；不合法拋 :class:`WorldActionError`（狀態不變）。"""
    problem = equip_problem(library, char)
    if problem is not None:
        raise WorldActionError(f"不能換裝備：{problem}")
    item = next((g for g in char.gear if g.id == action.item), None)
    if item is None:
        raise WorldActionError(f"背包裡沒有這件裝備：{action.item}")
    run = _run(char)
    try:
        slot = target_slot(library, run, item, action.slot)
        done, taken_off = equip_swap(library, run, item, slot, from_backpack=True)
    except ChoiceError as exc:
        raise WorldActionError(str(exc)) from exc
    # 換下的比換上的多（雙手武器收起副手）：背包要有空格（5D-R1）
    if len(done.backpack) > len(char.gear):
        room = room_problem(library, char.bag, len(done.backpack))
        if room is not None:
            raise WorldActionError(f"不能換裝備：{room}")
    removed = tuple(g.name_zh for g in taken_off)
    char = char.model_copy(
        update={"hero": done.hero, "equipment": dict(done.equipment), "gear": done.backpack}
    )
    event = ItemEquippedEvent(slot=slot, item=item.id, name_zh=item.name_zh, removed=removed)
    return char, (event,)


# ---------------------------------------------------------------------------
# 傭兵與影子（20.5）
# ---------------------------------------------------------------------------


def _build_keywords(library: ContentLibrary, template: UnitTemplate) -> tuple[str, ...]:
    found: dict[str, None] = {}
    for skill_id in template.skills:
        skill = library.skills.get(skill_id)
        if skill is not None:
            found.update(dict.fromkeys(derive_keywords(skill, library.keywords).all()))
    return tuple(found)


def mercenary_equipment(
    library: ContentLibrary, merc_id: str, template: UnitTemplate, level: int
) -> dict[str, ItemDef]:
    """傭兵這個等級穿的裝備（範本的裝備＋空欄位的系統裝備；20.5）。沒有掉落規則時只有範本的。

    亂數 ``merc_gear:{傭兵}:{欄位}:{等級}``：每個人看到的同一名傭兵裝備都一樣。"""
    base: dict[str, ItemDef] = {e.slot: e.item for e in library.loadout_of(template).items}
    rules = loot_rules(library)
    if rules is None or library.item_gen is None:
        return base
    item_level = max(1, min(level, rules.gear.max_item_level))
    cache = library.mercenary_gear_cache
    key = (merc_id, item_level)
    cached = cache.get(key)
    if cached is not None:
        return {**cached, **base}
    keywords = _build_keywords(library, template)
    extra: dict[str, ItemDef] = {}
    for slot in rules.mercenary_gear.ordered_slots():
        if slot in base:
            continue
        rng = Rng(fnv1a64(f"merc_gear:{merc_id}:{slot}:{item_level}".encode()))
        item = generate_item_retrying(
            library, rng, slot, rules.mercenary_gear.rarity, item_level, keywords=keywords
        )
        if item is not None:
            extra[slot] = item.model_copy(update={"id": f"item_merc_{merc_id}_{slot}"})
    if len(cache) >= _MERC_CACHE_LIMIT:
        cache.clear()
    cache[key] = extra
    return {**extra, **base}


def shadow_equipment(
    library: ContentLibrary, equipment: Mapping[str, ItemDef], recruiter_level: int
) -> dict[str, ItemDef]:
    """影子借用時穿的裝備：物品等級超過招募者等級的壓到招募者等級後照穿（20.5、#87；5D-2b 玩法 PM
    代決，取代 5D2-10 的整件不穿）。詞條數值照物品等級規則縮（:func:`downscale_item`）。"""
    return {
        slot: downscale_item(library, item, recruiter_level) for slot, item in equipment.items()
    }
