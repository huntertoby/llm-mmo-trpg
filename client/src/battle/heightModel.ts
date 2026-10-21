// 高度表現的單位底座（Phase 3-14；純函式）。
// 3-19 起高度改為「整格抬高」（`battle/elevation.ts`）：A 方案的懸崖線、側面、投影已移除。

/** 單位底座陰影的大小係數（0 ＝ 不畫）：站在高處（高度 ≥ 1）才有，越高越大。 */
export function pedestalScale(height: number): number {
  if (height <= 0) return 0;
  return 0.6 + 0.12 * Math.min(3, height);
}
