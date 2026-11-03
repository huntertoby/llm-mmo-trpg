// 背包滿了：戰後結算選要丟哪件（Phase 5D-2b；玩法 PM 2026-11-03 代決，不做暫存區）。
// 新拿到的（pending_loot.items）和背包裡原本的（inventory.bag）都可以丟；放不放得下由後端判定。
import type { WorldAction, WorldBagItem } from "../api/types";

/** 每一列的鍵：新拿到的與背包裡原本的分開（同一種材料兩邊都可能有）。 */
export type LootSide = "new" | "bag";
export type LootDraft = Record<string, number>;

export function draftKey(side: LootSide, item: string): string {
  return `${side}:${item}`;
}

/** 把勾選與個數換成 `loot_choose` 動作（個數 0 的不送；同一種物品兩邊的個數相加）。 */
export function lootChooseAction(draft: LootDraft, rows: { side: LootSide; item: WorldBagItem }[]): WorldAction {
  const dropItems: Record<string, number> = {};
  const dropGear: string[] = [];
  for (const { side, item } of rows) {
    const n = draft[draftKey(side, item.item)] ?? 0;
    if (n <= 0) continue;
    if (item.gear === true) dropGear.push(item.item);
    else dropItems[item.item] = (dropItems[item.item] ?? 0) + Math.min(n, item.count);
  }
  return { kind: "loot_choose", drop_items: dropItems, drop_gear: dropGear };
}
