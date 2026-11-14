// 冷卻井打破的推算（CW-1；移植需求 docs/art/冷卻井-移植需求.md 第 4 節、第 6 節第 5、7 條）。純函式：
// - 「這次重畫有哪口井被打破」：前一次畫面有、這一次沒有的 `cooling_well` 物件（只看畫面資料，重播時同樣推得出；
//   讀檔、重連後的第一張畫面沒有「前一次」，所以讀檔後不留碎屑——碎屑只是裝飾，移植需求第 6 節第 5 條允許）。
// - 「哪些新水是那口井漏出來的」：同一次重畫新出現的水，在井的 3×3 內（切比雪夫距離 ≤ 1）。
import type { DrawModel } from "../battle/drawModel";
import { sameBoard, type SurfaceChange } from "./surfaceAnim";

export const COOLING_WELL = "cooling_well";

export interface WellPos {
  x: number;
  y: number;
}

/** 前一次畫面有、這一次沒有的冷卻井（照 (y, x) 排序）；不是同一張地圖時沒有。 */
export function brokenWells(prev: DrawModel, next: DrawModel): WellPos[] {
  if (!sameBoard(prev, next)) return [];
  const still = new Set(next.objects.filter((o) => o.kind === COOLING_WELL).map((o) => o.id));
  return prev.objects
    .filter((o) => o.kind === COOLING_WELL && !still.has(o.id))
    .map((o) => ({ x: o.x, y: o.y }))
    .sort((a, b) => a.y - b.y || a.x - b.x);
}

/** 這個表面變化是不是 `wells` 其中一口井漏出來的水；是的話回傳那口井（多口同時破時取 (y, x) 最小、最近的）。 */
export function spillSource(c: SurfaceChange, wells: readonly WellPos[]): WellPos | null {
  if (c.kind !== "appear" || c.after !== "water") return null;
  let best: WellPos | null = null;
  let bestD = Number.POSITIVE_INFINITY;
  for (const w of wells) {
    const d = Math.max(Math.abs(w.x - c.x), Math.abs(w.y - c.y));
    if (d <= 1 && d < bestD) {
      best = w;
      bestD = d;
    }
  }
  return best;
}
