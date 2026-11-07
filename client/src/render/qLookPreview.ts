// QK-6：建角頁與主城「外觀與種族」的人物預覽，Q 版即時畫在畫布上（不再轉成圖片）。
// 依畫布的 CSS 大小與 devicePixelRatio 取樣，Q 版小人（頭頂約 −52 單位、腳底 0）撐滿畫布高度，地上影子同戰場。
import type { DollSpec } from "./appearance";
import { canStamp, qStampLocal } from "./qStamp";
import { GAME_HOOKS, qUnitOf } from "./qSpec";

export type PreviewFacing = "south" | "east" | "west" | "north";

/** 預覽框的單位範圍：頭頂上方留到 −56（兔耳、高帽），腳底下留 4（影子）。 */
export const Q_PREVIEW_BOX = { top: -56, bottom: 4, halfW: 26 } as const;

/** 單位 → 畫布像素的縮放（CSS 像素）：以高度撐滿、寬度不超出。 */
export function qPreviewScale(cssW: number, cssH: number): number {
  const { top, bottom, halfW } = Q_PREVIEW_BOX;
  return Math.max(0.1, Math.min(cssH / (bottom - top), cssW / (2 * halfW)));
}

/** 在畫布上畫 Q 版預覽（會重設畫布大小）。沒有 DOM 時什麼都不做，回傳 false。 */
export function drawQLookPreview(cv: HTMLCanvasElement, spec: DollSpec, facing: PreviewFacing, cssW: number, cssH: number, dpr = 1): boolean {
  if (!canStamp()) return false;
  const ctx = cv.getContext("2d");
  if (ctx === null) return false;
  const r = Math.max(1, Math.min(4, dpr));
  cv.width = Math.round(cssW * r);
  cv.height = Math.round(cssH * r);
  const k = qPreviewScale(cssW, cssH);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.scale(r, r);
  ctx.translate(cssW / 2, cssH - Q_PREVIEW_BOX.bottom * k);
  ctx.scale(k, k);
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.beginPath();
  ctx.ellipse(0, 0, 11.2, 2.1, 0, 0, Math.PI * 2);
  ctx.fill();
  const view = facing === "north" ? "back" : facing === "south" ? "front" : "side";
  qStampLocal(ctx, qUnitOf(spec), view, facing === "west", GAME_HOOKS, null);
  return true;
}
