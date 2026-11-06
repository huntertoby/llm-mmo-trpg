// 入口畫面的背景場景（UI-E1；docs/art/sample/home-v2.html）：直接用大世界圖第 2 版的畫法（`worldMapPainter`），
// 只貼天空、浮島本體、浮橋與雲（不貼字牌、傳送鈕、標題、圖例、外框）。第一季開放的雲嶺、荒原彩色，
// 其他三區照遊戲裡一樣去色纏雲。純資料，沒有亂數。
import { ISLAND_GEO, type AtlasArtIsland, type AtlasScene } from "./worldMapArt";

/** 第一季開放的區（彩色）；其他區畫成未開放（去色、纏雲）。 */
export const ENTRY_OPEN_REGIONS: readonly string[] = ["cloud_ridge", "ashen_waste"];

/** 背景上的各區（不含主城），照 `ISLAND_GEO` 的鍵排序（確定性）。 */
export const ENTRY_REGIONS: readonly string[] = Object.keys(ISLAND_GEO)
  .filter((r) => r !== "capital")
  .sort();

function island(region: string, open: boolean): AtlasArtIsland {
  const geo = ISLAND_GEO[region];
  if (geo === undefined) throw new Error(`沒有 ${region} 的浮島位置`);
  return { region, name: "", status: open ? "open" : "later", current: false, canTeleport: false, town: "", level: "", condition: "", geo };
}

/** 入口畫面的場景（每次相同）。 */
export function entryScene(): AtlasScene {
  return {
    capital: island("capital", true),
    islands: ENTRY_REGIONS.map((r) => island(r, ENTRY_OPEN_REGIONS.includes(r))),
  };
}

/** 等比「蓋滿」視窗時畫布的像素大小（邏輯 1280×860；最長邊上限 `maxPx`，避免大螢幕畫太大張）。 */
export function coverPixels(vw: number, vh: number, logicalW: number, logicalH: number, dpr: number, maxPx = 2600): { w: number; h: number } {
  if (vw <= 0 || vh <= 0) return { w: 0, h: 0 };
  let s = Math.max(vw / logicalW, vh / logicalH) * Math.max(1, dpr);
  s = Math.min(s, maxPx / Math.max(logicalW, logicalH));
  return { w: Math.round(logicalW * s), h: Math.round(logicalH * s) };
}
