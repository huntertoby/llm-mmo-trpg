// 物品的 Q 版小圖示（Phase QI-7，第⑥批；畫法在 `qIcon/items.ts`）：畫布快取與「這一列畫哪個圖示」。
// 遊戲端的 `ui/ItemIcon` 經這裡拿畫布：畫布邊長＝顯示 × `ICON_RES`，CSS 不縮放（上手筆記第四節第 19 點）。
// 染料顏色、稀有標記是後端物品 view 的選用欄位 `color`、`rare`（開發 PM 定需求第 5 節第 1、2 點選 (a)）。
import { ICON_RES } from "./qIcon/core";
import * as QI from "./qIcon/items";

export type ItemIconFrame = QI.ItemFrame;
export interface ItemIconOpt { frame?: ItemIconFrame; color?: string | null; rare?: boolean | null }

/** 這個物品（與後端給的顏色）有沒有 Q 版圖示（表裡沒有的 id：背包格退回名字小牌、清單列留 24 空位、飛行用 `gain_item`）。 */
export const hasItemIcon = (id: string, color?: string | null): boolean => QI.hasItemIcon(id, color);

/** 快取鍵：圖示 id、顯示邊長、內部解析度、框、染料色、稀有。 */
export const itemIconKey = (id: string, px: number, res: number = ICON_RES, opt: ItemIconOpt = {}): string => [id, px, res, opt.frame ?? "", opt.color ?? "", opt.rare == null ? "" : String(opt.rare)].join("|");

const CACHE_LIMIT = 256;
const cache = new Map<string, HTMLCanvasElement>();
/** 一個物品圖示的畫布（含框；`qIcon/items.ts` 的 `canvas`），同鍵共用一張。表裡沒有（也沒有染料色）時 null。 */
export function itemIconCanvas(id: string, px: number, res: number = ICON_RES, opt: ItemIconOpt = {}): HTMLCanvasElement | null {
  if (!QI.hasItemIcon(id, opt.color)) return null;
  const key = itemIconKey(id, px, res, opt);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const cv = QI.canvas(id, px, res, opt);
  if (cache.size >= CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(key, cv);
  return cv;
}
export function clearItemIconCache(): void {
  cache.clear();
}

/** 飛進背包的圖示 id：表裡有的物品畫自己的（或有染料色），其他物品 `gain_item`、沒外觀的裝備 `gain_gear`。 */
export const gainItemIconId = (item: string, gear: boolean, color?: string | null): string => (gear ? "gain_gear" : QI.hasItemIcon(item, color) ? item : "gain_item");
