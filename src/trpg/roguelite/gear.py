"""戰後裝備三選一與換裝（Phase 3K-2，``docs/design/07-角色成長.md`` 7.1）。

- **候選**（:func:`make_gear_offer`）：每打贏一場一般戰鬥給 ``offer_size``（3）件裝備，
  **部位不重複**；主手武器只出和主角目前武器 **同大類** 的；主手是雙手或成對武器時不出副手。亂數由
  一輪的種子以標籤 ``gear/<場次>`` 衍生（同種子同候選，可重播）。稀有度依 ``rarity_weights``
  （40／25／20／13／2）抽，物品由 3K-1 的 :func:`~trpg.content.item_gen.generate_item` 產生
  （物品等級＝抽到當下的主角等級；稀有度不加強度）。穿不上的候選（例如傳說物品超過全身上限）重抽，
  最多 ``offer_attempts`` 次。
- **穿戴**（:func:`equip`）：直接換上，換下的進背包；主手換成別把武器時主角的武器跟著換（同大類），
  雙手或成對武器會把副手收進背包。穿戴一律過 :func:`~trpg.content.equipment.loadout_problems`。
- **目前裝備**（:func:`worn_items`、:func:`run_loadout`）：``RunState.equipment`` 非空就是全身裝備，
  否則用測試模式挑的裝備或範本的裝備（舊存檔與沒換過裝的一輪）。
- **AI 挑法**（:func:`auto_gear_pick`）：預算分數（詞條點數＋基礎加成＋基礎強度，``item_strength``）
  比該部位目前裝備高最多的那件；沒有比較高的就跳過。

純函式，亂數只用 :class:`~trpg.shared.rng.Rng`。
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction

from trpg.content.battle import WeaponDef
from trpg.content.equipment import ItemDef, Loadout, loadout_problems, resolve_loadout
from trpg.content.item_budget import item_strength
from trpg.content.item_gen import ItemGenError, WeaponClass, generate_item, roll_rarity
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPE_OF, SLOT_TYPES, SLOTS, SlotType
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.state import GearOfferNode, RunState
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, top_attribute

__all__ = [
    "auto_gear_pick",
    "current_item",
    "equip",
    "equip_notes",
    "gear_offer_node",
    "item_score",
    "make_gear_offer",
    "run_loadout",
    "take_gear",
    "target_slot",
    "worn_items",
]


def _base_items(library: ContentLibrary, run: RunState) -> dict[str, ItemDef]:
    """沒換過裝時的裝備：測試模式挑的裝備，否則範本的裝備。"""
    if run.test_equipment:
        loadout = resolve_loadout(run.test_equipment, library.items, library.affixes)
    else:
        loadout = library.loadout_of(run.hero)
    return {e.slot: e.item for e in loadout.items}


def worn_items(library: ContentLibrary, run: RunState) -> dict[str, ItemDef]:
    """目前穿戴的物品（欄位 → 物品；主手沒有物品時，主角的武器是沒有詞條的基礎武器，不列）。"""
    return dict(run.equipment) if run.equipment else _base_items(library, run)


def _loadout(library: ContentLibrary, items: dict[str, ItemDef]) -> Loadout:
    # 用欄位名當臨時物品 id，兩個欄位的物品 id 相同也不會互相蓋掉
    return resolve_loadout({slot: slot for slot in items}, items, library.affixes)


def run_loadout(library: ContentLibrary, run: RunState) -> Loadout:
    """主角這一輪的裝備快照（開戰與角色面板共用）：``RunState.equipment`` 非空就用它，否則測試模式
    挑的裝備，再否則範本的裝備。"""
    if run.equipment:
        return _loadout(library, run.equipment)
    if run.test_equipment:
        return resolve_loadout(run.test_equipment, library.items, library.affixes)
    return library.loadout_of(run.hero)


def item_score(library: ContentLibrary, item: ItemDef | None) -> Fraction:
    """預算分數：詞條點數＋基礎加成＋整件物品的基礎強度（武器基礎傷害、防具基礎防禦；3K-2b 的
    :func:`~trpg.content.item_budget.item_strength`）；
    沒有物品、或內容庫沒有產生器規則時為 0。"""
    if item is None or library.item_gen is None:
        return Fraction(0)
    try:
        return item_strength(library.item_gen, item, library.affixes, library.weapons)
    except KeyError:  # 沒有分類成立率的條件詞條：不計分
        return Fraction(0)


def _plain_weapon(weapon: WeaponDef) -> ItemDef:
    """主手沒有物品時，把主角原本的武器變成一件沒有詞條的物品（換下時進背包，營火可以換回）。"""
    look = weapon.look
    return ItemDef(
        id=f"base_{weapon.id}",
        name_zh=weapon.name_zh,
        slot_type="weapon",
        weapon=weapon.id,
        paired=weapon.paired,
        kind=None if look is None else look.kind,
        form=None if look is None else look.form,
        material=None if look is None else look.material,
        rarity="common",
    )


def target_slot(
    library: ContentLibrary, run: RunState, item: ItemDef, slot: str | None = None
) -> str:
    """物品要放的欄位：指定了就檢查種類；沒指定時單一欄位的種類直接用它，戒指先放空的、都有裝備時
    換掉預算分數較低的（相同取第一個）。"""
    slots = [s for s in SLOTS if SLOT_TYPE_OF[s] == item.slot_type]
    if slot is not None:
        if slot not in slots:
            raise ChoiceError(f"「{item.name_zh}」不能放進欄位 {slot}")
        return slot
    worn = worn_items(library, run)
    for candidate in slots:
        if candidate not in worn:
            return candidate
    return min(slots, key=lambda s: item_score(library, worn[s]))


def _remove_from_backpack(backpack: tuple[ItemDef, ...], item_id: str) -> list[ItemDef]:
    rest = list(backpack)
    for i, held in enumerate(rest):
        if held.id == item_id:
            del rest[i]
            return rest
    raise ChoiceError(f"背包裡沒有這件裝備：{item_id}")


def equip(
    library: ContentLibrary,
    run: RunState,
    item: ItemDef,
    slot: str | None = None,
    *,
    from_backpack: bool = False,
) -> RunState:
    """把 ``item`` 換上（見模組說明）；不合法時拋出 :class:`ChoiceError`（狀態不變）。
    ``from_backpack``：物品來自背包（換上時先從背包拿掉）。"""
    slot = target_slot(library, run, item, slot)
    hero = run.hero
    weapon = library.weapons[hero.weapon]
    worn = worn_items(library, run)
    backpack = _remove_from_backpack(run.backpack, item.id) if from_backpack else list(run.backpack)
    old = worn.get(slot)
    if slot == "main_hand":
        if item.weapon is None:
            raise ChoiceError(f"「{item.name_zh}」沒有武器資料，不能放進主手")
        new_weapon = library.weapons[item.weapon]
        if new_weapon.weapon_class != weapon.weapon_class:
            raise ChoiceError("主手只能換成同一大類的武器（近戰、遠程、法器）")
        old = old or _plain_weapon(weapon)
        weapon = new_weapon
        hero = hero.model_copy(update={"weapon": new_weapon.id})
    new = dict(worn)
    new[slot] = item
    if slot == "main_hand" and (weapon.two_handed or weapon.paired or item.paired):
        displaced = new.pop("off_hand", None)  # 雙手或成對武器占用副手：副手收進背包
        if displaced is not None:
            backpack.append(displaced)
    problems = loadout_problems(_loadout(library, new), weapon, library.ruleset.equipment)
    if problems:
        raise ChoiceError("；".join(problems))
    if old is not None:
        backpack.append(old)
    return run.model_copy(update={"hero": hero, "equipment": new, "backpack": tuple(backpack)})


# ---------------------------------------------------------------------------
# 戰後三選一
# ---------------------------------------------------------------------------


def _offer_parts(library: ContentLibrary, run: RunState) -> list[SlotType]:
    """能出的部位（物品種類）：主手是雙手或成對武器時不出副手。"""
    weapon = library.weapons[run.hero.weapon]
    main = worn_items(library, run).get("main_hand")
    blocked = weapon.two_handed or weapon.paired or (main is not None and main.paired)
    return [t for t in SLOT_TYPES if not (t == "offhand" and blocked)]


def make_gear_offer(
    library: ContentLibrary, run: RunState, battle_index: int
) -> tuple[ItemDef, ...]:
    """第 ``battle_index`` 場打贏後的裝備候選（見模組說明）。內容庫沒有產生器規則時為空。"""
    rules = library.item_gen
    if rules is None:
        return ()
    root = Rng(run.seed).fork(f"gear/{battle_index}")
    parts = root.fork("parts").shuffled(_offer_parts(library, run))[: rules.offer_size]
    weapon_class: WeaponClass = library.weapons[run.hero.weapon].weapon_class
    found: list[ItemDef] = []
    for i, part in enumerate(parts):
        for attempt in range(rules.offer_attempts):
            rng = root.fork(f"item/{i}/{attempt}")
            try:
                item = generate_item(
                    library,
                    rng,
                    part,
                    roll_rarity(library, rng),
                    run.level,
                    weapon_class=weapon_class if part == "weapon" else None,
                )
                equip(library, run, item)
            except (ItemGenError, ChoiceError):
                continue
            if all(item.id != other.id for other in found):
                found.append(item)
                break
    return tuple(found)


def gear_offer_node(
    library: ContentLibrary, run: RunState, battle_index: int
) -> GearOfferNode | None:
    """打贏第 ``battle_index`` 場後的裝備三選一節點；沒有任何候選時為 ``None``。"""
    candidates = make_gear_offer(library, run, battle_index)
    if not candidates:
        return None
    return GearOfferNode(after_battle=battle_index, candidates=candidates)


def take_gear(
    library: ContentLibrary, run: RunState, node: GearOfferNode, pick: int | None
) -> RunState:
    """套用三選一的選擇（``None`` ＝ 跳過；沒選的候選直接丟棄）。"""
    if pick is None:
        return run
    if not 0 <= pick < len(node.candidates):
        raise ChoiceError(f"沒有第 {pick} 件候選（共 {len(node.candidates)} 件）")
    return equip(library, run, node.candidates[pick])


def auto_gear_pick(library: ContentLibrary, run: RunState, node: GearOfferNode) -> int | None:
    """AI 代打的挑法：預算分數比「放進去會換掉的那個部位目前的裝備」高最多的候選（部位空著算 0
    分，所以空部位一定優先）；沒有比較高的就跳過。分數相同取索引小的。**不換武器**：主手候選的武器和
    主角現在的不同時略過（保守：技能是照現有武器挑的；玩家可以自己換）。"""
    worn = worn_items(library, run)
    best: tuple[Fraction, int] | None = None
    for index, item in enumerate(node.candidates):
        try:
            slot = target_slot(library, run, item)
            equip(library, run, item, slot)
        except ChoiceError:
            continue
        if slot == "main_hand" and item.weapon != run.hero.weapon:
            continue
        gain = item_score(library, item) - item_score(library, worn.get(slot))
        if gain > 0 and (best is None or gain > best[0]):
            best = (gain, index)
    return None if best is None else best[1]


def current_item(library: ContentLibrary, run: RunState, slot: str) -> ItemDef | None:
    """欄位目前的物品（顯示用）：主手沒有物品時是主角的基礎武器（沒有詞條）；空著為 ``None``。"""
    found = worn_items(library, run).get(slot)
    if found is None and slot == "main_hand":
        return _plain_weapon(library.weapons[run.hero.weapon])
    return found


def equip_notes(library: ContentLibrary, run: RunState, item: ItemDef, slot: str) -> list[str]:
    """換上 ``item`` 的連帶效果（卡片比較用）：主角的武器換了、副手收進背包。"""
    after = equip(library, run, item, slot)
    notes: list[str] = []
    if after.hero.weapon != run.hero.weapon:
        notes.append(f"主角的武器換成「{library.weapons[after.hero.weapon].name_zh}」")
    before_ids = {i.id for i in worn_items(library, run).values()}
    for held in after.backpack:
        if held.slot_type == "offhand" and held.id in before_ids:
            notes.append(f"副手「{held.name_zh}」被占用，收進背包")
    return notes


def _scaling_attrs(weapon: WeaponDef) -> tuple[Attribute, ...]:
    if weapon.secondary_scaling_attr is None:
        return (weapon.scaling_attr,)
    return (weapon.scaling_attr, weapon.secondary_scaling_attr)


def weapon_swap_prompt(
    library: ContentLibrary,
    run: RunState,
    item: ItemDef,
    slot: str,
    attributes: Mapping[Attribute, int],
) -> str | None:
    """換主手武器的提示（3K-2b，玩法 PM 回覆 07 7.1 #49）：換上後主角的武器縮放屬性和目前的不同時才
    回傳「這把看〔屬性〕，你目前最高的是〔屬性〕」，讓玩家確認換不換；屬性相同（或不是換武器）為
    ``None``。``attributes`` 是主角目前的有效屬性（判斷「最高」用）。"""
    if slot != "main_hand":
        return None
    new_weapon = equip(library, run, item, slot).hero.weapon
    if new_weapon == run.hero.weapon:
        return None
    old, new = library.weapons[run.hero.weapon], library.weapons[new_weapon]
    if set(_scaling_attrs(old)) == set(_scaling_attrs(new)):
        return None
    mine = "、".join(a.display_name for a in _scaling_attrs(new))
    return f"這把看{mine}，你目前最高的是{top_attribute(attributes).display_name}"
