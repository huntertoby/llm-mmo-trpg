// 飾件不能壓到內容（UI-E1b；美術 PM 2026-11-05 的通用規則，不分框的大小；docs/archive/art/UI-E1檢查.md D、E）：
// `.rt-frame` 的四角飾件畫在外框 `::after` 的背景上（邊長 18px、離內緣 2px；小框 70%），飾件所在的四個正方形裡
// 不能有文字、按鈕、輸入框、圖示、資源條。這裡是純函式（vitest 測），layoutSmoke 在瀏覽器裡量出各框與內容的矩形後呼叫。
// 圓形的內容（頭像）照內切圓算：圓沒碰到飾件的正方形就不算壓到。
import { CORNER_AT, CORNER_INSET, CORNER_SIZE, type CornerAt } from "./regionCorners";
import { SMALL_CORNER_SCALE } from "./smallFrames";

export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface Borders {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface CornerItem {
  rect: Rect;
  /** 圓形內容（頭像）：照內切圓判斷。 */
  round?: boolean;
  label: string;
}

/** 重疊多少才算壓到（CSS 像素；子像素與反鋸齒）。 */
export const CORNER_TOL = 1;

const NAMES: Readonly<Record<CornerAt, string>> = { tl: "左上", tr: "右上", bl: "左下", br: "右下" };

/** 飾件的邊長：小框（`data-rt-small`）是 70%。 */
export const cornerSize = (small: boolean): number => (small ? Math.round(CORNER_SIZE * SMALL_CORNER_SCALE * 10) / 10 : CORNER_SIZE);

/** 一個框的四個飾件正方形（飾件畫在內緣＝外框扣掉邊框，再往內 2px）。 */
export function cornerZones(frame: Rect, border: Borders, size: number, inset = CORNER_INSET): Record<CornerAt, Rect> {
  const l = frame.left + border.left + inset;
  const t = frame.top + border.top + inset;
  const r = frame.right - border.right - inset;
  const b = frame.bottom - border.bottom - inset;
  return {
    tl: { left: l, top: t, right: l + size, bottom: t + size },
    tr: { left: r - size, top: t, right: r, bottom: t + size },
    bl: { left: l, top: b - size, right: l + size, bottom: b },
    br: { left: r - size, top: b - size, right: r, bottom: b },
  };
}

/** 兩個矩形的重疊寬、高（沒重疊時為負）。 */
function overlap(a: Rect, b: Rect): { x: number; y: number } {
  return { x: Math.min(a.right, b.right) - Math.max(a.left, b.left), y: Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) };
}

/** 內切圓有沒有伸進正方形超過 `tol`（圓心到正方形的最近點距離 < 半徑 − tol）。 */
function circleHits(zone: Rect, box: Rect, tol: number): boolean {
  const r = Math.min(box.right - box.left, box.bottom - box.top) / 2;
  const cx = (box.left + box.right) / 2;
  const cy = (box.top + box.bottom) / 2;
  const nx = Math.max(zone.left, Math.min(cx, zone.right));
  const ny = Math.max(zone.top, Math.min(cy, zone.bottom));
  return Math.hypot(cx - nx, cy - ny) < r - tol;
}

/** 一個內容有沒有壓到某個飾件正方形。 */
export function hitsZone(zone: Rect, item: CornerItem, tol = CORNER_TOL): boolean {
  const o = overlap(zone, item.rect);
  if (o.x <= tol || o.y <= tol) return false;
  return item.round === true ? circleHits(zone, item.rect, tol) : true;
}

/** 純函式：一個框的四角各壓到哪些內容（「右上 × HP 條」）；空陣列＝沒有。 */
export function cornerClashes(zones: Record<CornerAt, Rect>, items: readonly CornerItem[], tol = CORNER_TOL): string[] {
  const out: string[] = [];
  for (const at of CORNER_AT) {
    for (const item of items) if (hitsZone(zones[at], item, tol)) out.push(`${NAMES[at]} × ${item.label}`);
  }
  return out;
}

/** 把內容矩形裁到捲動區／裁切容器的可見範圍裡（捲到框外的字看不到，不算壓到）；完全看不到時 `null`。 */
export function clipRect(r: Rect, clips: readonly Rect[]): Rect | null {
  let out = r;
  for (const c of clips) {
    out = { left: Math.max(out.left, c.left), top: Math.max(out.top, c.top), right: Math.min(out.right, c.right), bottom: Math.min(out.bottom, c.bottom) };
    if (out.right - out.left <= 0 || out.bottom - out.top <= 0) return null;
  }
  return out;
}
