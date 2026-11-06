// 高度標記「▲N」的畫法與規則（純函式）。
//
// 6F-18（美術 PM 6F-17 檢查第 2 節）：格子上有單位站著（沒倒下）時不畫「▲N」，所有寬度都一樣。
// 同一格要放徽章、狀態列、「+N」、「▲N」四樣東西，800 寬放不下（6F-14～6F-17 修了三段）。
// 高度照樣看得到：地形的高低差畫法不變、空格照舊畫「▲N」、單位浮動卡與目標說明寫「高地 ▲N」（`battle/elevation.heightNote`）。
// 6F-14～6F-17 為了站著的人移動標記、縮成角標的程式拿掉。
//
// 座標：標記節點的原點在格子左上角，整個節點放大 `k` 倍（`minMark.ts`）。

import type { Pos } from "../api/types";

/** 標記的底（圓角方框）：節點本地座標，放大前。 */
export const HEIGHT_MARK_BG = { x: 3, y: 3, w: 19, h: 13, r: 4 } as const;
/** 「▲」三角形的三個頂點（本地座標）。 */
export const HEIGHT_MARK_TRI = [6, 13, 9.5, 6, 13, 13] as const;
/** 數字的左上角（本地座標）。 */
export const HEIGHT_MARK_NUM = { x: 14, y: 4 } as const;

/** 6F-18：這一格可以畫「▲N」（沒有站著的單位；倒下的人躺著，照空格畫）。 */
export function markedTileFree(units: ReadonlyArray<Pos & { downed: boolean }>, t: Pos): boolean {
  return !units.some((u) => u.x === t.x && u.y === t.y && !u.downed);
}
