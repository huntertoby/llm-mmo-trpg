// 背包格子（UI-E3；docs/art/全遊戲一致性巡檢.md #7、偷懶自查 G2、hud.png C 案）：只整理顯示，規則都在後端。
// - 物品格：6 欄 × 5 列（上限 30 格）。背包裡的每一筆（裝備每件、物品每種）佔一格，照伺服器的順序；
//   剩下的空格＝上限 − 已用格數（一種物品超過疊數時伺服器算多格，畫面上仍只畫一格，空格照伺服器的格數少畫）。
// - 腰包：照 `pouch_max` 畫一排格子。
// - 點一格＝選取，詳情（裝備卡＋換上、物品說明＋使用）畫在格子下方；預設選第一格有東西的。
import type { WorldBagItem, WorldInventory } from "../api/types";

/** 物品格的欄數（hud.png C 案；任務：6×5）。 */
export const BAG_COLS = 6;
/** 伺服器沒有上限時畫的列數。 */
export const BAG_ROWS = 5;

export type BagCell = { kind: "thing"; key: string; row: WorldBagItem; where: "bag" | "pouch" } | { kind: "empty"; key: string };

/** 一格的選取鍵：`bag:<物品>`、`pouch:<物品>`（同一種物品可能同時在背包與腰包）。 */
export function cellKey(where: "bag" | "pouch", item: string): string {
  return `${where}:${item}`;
}

/** 物品格：背包每一筆一格，後面補空格到上限（至少補滿目前這一列，格子不會缺角）。 */
export function bagCells(inventory: WorldInventory): BagCell[] {
  const things: BagCell[] = inventory.bag.map((row) => ({ kind: "thing", key: cellKey("bag", row.item), row, where: "bag" }));
  const max = inventory.slots_max > 0 ? inventory.slots_max : BAG_COLS * BAG_ROWS;
  const free = Math.max(0, max - inventory.slots_used);
  const total = things.length + free;
  const padded = Math.ceil(Math.max(total, 1) / BAG_COLS) * BAG_COLS;
  const empties: BagCell[] = Array.from({ length: padded - things.length }, (_, i) => ({ kind: "empty", key: `empty:${i}` }));
  return [...things, ...empties];
}

/** 腰包格：帶的東西一格一種，補到 `pouch_max`。 */
export function pouchCells(inventory: WorldInventory): BagCell[] {
  const things: BagCell[] = inventory.pouch.map((row) => ({ kind: "thing", key: cellKey("pouch", row.item), row, where: "pouch" }));
  const empties: BagCell[] = Array.from({ length: Math.max(0, inventory.pouch_max - things.length) }, (_, i) => ({ kind: "empty", key: `pouch-empty:${i}` }));
  return [...things, ...empties];
}

/** 選取的那一格（找不到時退回第一格有東西的；都沒有為 `null`）。 */
export function pickedCell(cells: readonly BagCell[], picked: string | null): Extract<BagCell, { kind: "thing" }> | null {
  const things = cells.filter((c): c is Extract<BagCell, { kind: "thing" }> => c.kind === "thing");
  return things.find((c) => c.key === picked) ?? things[0] ?? null;
}

/** 物品格上的名字（沒有物品圖示前的小牌；超過 4 個字截成 3 字＋「…」，全名在滑過的說明卡）。 */
export function tileName(name: string): string {
  const chars = [...name.replace(/（.*?）/g, "")];
  return chars.length > 4 ? `${chars.slice(0, 3).join("")}…` : chars.join("");
}

/** 滑過一格的說明：名字、種類、個數。 */
export function cellHint(row: WorldBagItem): string {
  return row.gear === true ? `${row.name_zh}・${row.kind_zh}` : `${row.name_zh}・${row.kind_zh}・×${row.count}`;
}
