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

/** 名字小牌每行最多幾個字（UI-E3c：11px 字、36px 寬的小牌放 3 個字）。 */
export const TILE_LINE_CHARS = 3;

/** 名字切成詞（`Intl.Segmenter` 的中文斷詞；沒有時每個字一段）。太長的詞再切成每段 `TILE_LINE_CHARS` 個字。 */
function tileWords(name: string): string[][] {
  const Seg = (Intl as unknown as { Segmenter?: new (l: string, o: { granularity: "word" }) => { segment(s: string): Iterable<{ segment: string }> } }).Segmenter;
  const words = Seg === undefined ? [...name] : [...new Seg("zh-Hant", { granularity: "word" }).segment(name)].map((s) => s.segment);
  const out: string[][] = [];
  for (const w of words) {
    const chars = [...w];
    for (let i = 0; i < chars.length; i += TILE_LINE_CHARS) out.push(chars.slice(i, i + TILE_LINE_CHARS));
  }
  return out.filter((w) => w.length > 0);
}

/**
 * 名字小牌的行（UI-E3c，美術 PM 決定 B：斷行不拆開詞，「小回復藥」→「小／回復藥」，不是「小回／復藥」）。
 * 最多 2 行、每行最多 3 個字，只在詞與詞之間換行；兩行都放得下時取最平均的斷點（一樣平均時第一行短）。
 * 放不下時第二行截斷加「…」（全名在滑過的說明卡）。括號裡的字（「（3 級）」）不畫。
 */
export function tileLines(name: string): string[] {
  const words = tileWords(name.replace(/（.*?）/g, ""));
  const total = words.reduce((n, w) => n + w.length, 0);
  if (total <= TILE_LINE_CHARS) return [words.flat().join("")];
  let best: number | null = null;
  let head = 0;
  for (let i = 1; i < words.length; i++) {
    head += words[i - 1]!.length;
    const tail = total - head;
    if (head > TILE_LINE_CHARS || tail > TILE_LINE_CHARS) continue;
    if (best === null || Math.abs(head - tail) < Math.abs(best - (total - best))) best = head;
  }
  const chars = words.flat();
  if (best !== null) return [chars.slice(0, best).join(""), chars.slice(best).join("")];
  // 兩行放不下：第一行裝滿整個詞，第二行剩下的截成 2 字＋「…」
  let first = 0;
  for (const w of words) {
    if (first + w.length > TILE_LINE_CHARS) break;
    first += w.length;
  }
  const rest = chars.slice(first);
  return [chars.slice(0, first).join(""), rest.length > TILE_LINE_CHARS ? `${rest.slice(0, TILE_LINE_CHARS - 1).join("")}…` : rest.join("")];
}

/** 滑過一格的說明：名字、種類、個數。`formZh`：裝備的外觀形制名（RG-8：雲紋碑盾、熔殼塔盾），有的話接在名字後面。 */
export function cellHint(row: WorldBagItem, formZh: string | null = null): string {
  if (row.gear !== true) return `${row.name_zh}・${row.kind_zh}・×${row.count}`;
  return formZh !== null ? `${row.name_zh}・${formZh}・${row.kind_zh}` : `${row.name_zh}・${row.kind_zh}`;
}
