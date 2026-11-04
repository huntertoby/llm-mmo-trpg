// 6F-10（美術 PM 6F-9 檢查第 2 節第 3 點：選取面板寫「19 個」、技能列寫「19 格」）：可選數量的量詞。
// 指格子（落點、目標格、攀跳的紫色格）一律「格」；指單位、物件一律「個」。純函式。

/** 格子的數量：「19 格」。 */
export function tileCount(n: number): string {
  return `${n} 格`;
}

/** 單位或物件的數量：「2 個」。 */
export function unitCount(n: number): string {
  return `${n} 個`;
}

/**
 * 紅框可選的數量：只有格子時「N 格」，只有單位／物件時「N 個」，兩種都有時「N 個目標、M 格」。
 * 兩種都是 0 時「0 個」（不會發生在有可選目標的模式上）。
 */
export function pickCountText(units: number, tiles: number): string {
  if (tiles > 0 && units > 0) return `${units} 個目標、${tileCount(tiles)}`;
  if (tiles > 0) return tileCount(tiles);
  return unitCount(units);
}

/** 複合技能第 1 段的鍵（`p:x,y` ＝ 落點格、`u:id` ＝ 單位）分成單位數與格子數。 */
export function splitCompositeKeys(keys: Iterable<string>): { units: number; tiles: number } {
  let units = 0;
  let tiles = 0;
  for (const k of keys) {
    if (k.startsWith("p:")) tiles += 1;
    else units += 1;
  }
  return { units, tiles };
}
