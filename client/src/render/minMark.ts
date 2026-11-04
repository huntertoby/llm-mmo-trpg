// 6F-9（美術 PM 6F-8 檢查第 2 節第 1 點：800 寬地圖縮到 65% 時，腳邊狀態圖示只剩約 4px 像一個藍點、高度標記「▲1」約 6px）：
// 這兩種標記有最小的畫面尺寸，地圖縮小時不再跟著縮（反向放大節點）；地圖夠大時（1600 寬 128%）倍率是 1，和原本一樣。
//
// 純函式；`BattleRenderer` 在建立節點與 `setScale` 時呼叫 `applyMarkScale`。

import type { Container, Text } from "pixi.js";

/** 狀態圖示畫出來的圖案（`paintStatusIcon` 的大小 ＝ 方框 − 2）在畫面上至少幾 px。 */
export const MIN_STATUS_GLYPH_PX = 10;
/** 高度標記的數字字級在畫面上至少幾 px（同樣的原則：和狀態圖示一樣 10px）。 */
export const MIN_HEIGHT_BADGE_FONT_PX = 10;

/** 腳邊狀態列節點的標籤（`unitSprite.statusRow`）。 */
export const STATUS_ROW_LABEL = "status-row";
/** 高度標記節點的標籤（`BattleRenderer.drawBadges`）。 */
export const HEIGHT_BADGE_LABEL = "height-badge";

/**
 * 標記的反向放大倍率：`base` 是世界座標的大小（px），`boardScale` 是地圖在畫面上的縮放；
 * 畫面上的大小 `base × boardScale` 小於 `min` 時放大到剛好 `min`，否則 1（不縮小）。
 */
export function minMarkScale(base: number, min: number, boardScale: number): number {
  if (!(boardScale > 0) || !(base > 0)) return 1;
  return Math.max(1, min / (base * boardScale));
}

/** 節點上記錄的基準：`base` 世界大小、`min` 畫面下限。 */
export interface MarkSpec {
  base: number;
  min: number;
}

const specs = new WeakMap<Container, MarkSpec>();
const texts = new WeakMap<Container, Text[]>();

/** 登記一個要保持最小尺寸的標記節點（`texts` 是裡面的文字，放大時要跟著提高解析度才不會糊）。 */
export function registerMark(node: Container, spec: MarkSpec, inner: Text[] = []): void {
  specs.set(node, spec);
  texts.set(node, inner);
}

/** 登記過的基準（測試用）。 */
export function markSpecOf(node: Container): MarkSpec | undefined {
  return specs.get(node);
}

/**
 * 依地圖縮放設定標記的倍率；`resolution` 是畫布的解析度（裝置像素比 × 縮放），文字的解析度 ＝ 它 × 倍率。
 * 沒登記過的節點不動。回傳倍率。
 */
export function applyMarkScale(node: Container, boardScale: number, resolution: number): number {
  const spec = specs.get(node);
  if (spec === undefined) return 1;
  const k = minMarkScale(spec.base, spec.min, boardScale);
  node.scale.set(k);
  for (const t of texts.get(node) ?? []) {
    if (!t.destroyed) t.resolution = Math.max(1, resolution * k);
  }
  return k;
}

/** 一個單位圖層裡的腳邊狀態列（直接子節點；沒有就 `null`）。 */
export function statusRowOf(unit: Container): Container | null {
  return (unit.children.find((n) => n.label === STATUS_ROW_LABEL) as Container | undefined) ?? null;
}
