// 整格抬高的繪圖幾何（Phase 3-19；純函式，不碰 Pixi，方便測試）：崖面的地層線、遮擋剪影的虛線、
// 升降時的碎土與塵土粒子。外觀依 docs/art/3-18倒地與高度.md 第 3、5 節。
import { RAISE } from "../battle/elevation";

export type Pt = { x: number; y: number };

/** 崖面漸層的上下色（第 5 節第 2 條）、崖頂亮唇、外側暗線。 */
export const CLIFF_TOP = 0x6b5236;
export const CLIFF_BOTTOM = 0x4a3824;
export const RIM = { color: 0xfff8d7, alpha: 0.8 } as const;
export const EDGE = { color: 0x19120a, alpha: 0.85 } as const;
/** 碎土粒子的顏色（第 3 節）。 */
export const DIRT = 0x8a6a48;

/** 兩個 0xRRGGBB 顏色的線性插值。 */
export function mixColor(a: number, b: number, t: number): number {
  const k = Math.max(0, Math.min(1, t));
  const ch = (shift: number) => Math.round(((a >> shift) & 0xff) * (1 - k) + ((b >> shift) & 0xff) * k);
  return (ch(16) << 16) | (ch(8) << 8) | ch(0);
}

/** 崖面上每一階的 1px 暗線位置（相對崖頂；高 `lift` 像素的崖面每 RAISE 一條，不含頂與底）。 */
export function strataLines(lift: number): number[] {
  const out: number[] = [];
  for (let y = RAISE; y < lift - 0.5; y += RAISE) out.push(y);
  return out;
}

/** 橢圓上 `n` 個點（閉合路徑，不重複第一點）。 */
export function ellipsePoints(cx: number, cy: number, rx: number, ry: number, n = 32): Pt[] {
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    return { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry };
  });
}

/**
 * 沿著折線（`closed` 時首尾相連）切出虛線：每段 `dash` 長、間隔 `gap`。回傳每一小段的起訖點；
 * 段落跨過轉角時在轉角切開（短線段之間的轉角很小，看不出來）。
 */
export function dashSegments(points: readonly Pt[], closed: boolean, dash = 3, gap = 2): Array<[Pt, Pt]> {
  const out: Array<[Pt, Pt]> = [];
  if (points.length < 2 || dash <= 0) return out;
  const path = closed ? [...points, points[0] as Pt] : [...points];
  let pos = 0; // 目前在「虛線＋間隔」週期中的位置
  const period = dash + Math.max(0, gap);
  for (let i = 1; i < path.length; i += 1) {
    const a = path[i - 1] as Pt;
    const b = path[i] as Pt;
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    let s = 0;
    while (s < len) {
      const inDash = pos < dash;
      const step = Math.min(len - s, inDash ? dash - pos : period - pos);
      if (inDash && step > 0) {
        const p0 = { x: a.x + ((b.x - a.x) * s) / len, y: a.y + ((b.y - a.y) * s) / len };
        const p1 = { x: a.x + ((b.x - a.x) * (s + step)) / len, y: a.y + ((b.y - a.y) * (s + step)) / len };
        out.push([p0, p1]);
      }
      s += step;
      pos = (pos + step) % period;
    }
  }
  return out;
}

/**
 * 遮擋剪影的輪廓（相對腳底；`size` ＝ 格子邊長）：身體一個橢圓、頭一個圓，大小貼近紙娃娃。
 * 回傳兩條閉合路徑。
 */
export function silhouetteLoops(feetX: number, feetY: number, size: number): Pt[][] {
  const k = size / 48;
  return [ellipsePoints(feetX, feetY - 13 * k, 10 * k, 13 * k, 36), ellipsePoints(feetX, feetY - 32 * k, 7 * k, 7 * k, 24)];
}

/** 一顆升降粒子在進度 `t`（0–1）時的位置、大小與透明度。 */
export interface DustBit {
  x: number;
  y: number;
  size: number;
  alpha: number;
}

/** 碎土粒子數：6～8 顆（依格子座標固定，不用亂數）。 */
export function dirtCount(x: number, y: number): number {
  return 6 + ((x * 7 + y * 3) % 3);
}

/**
 * 升起時的碎土（相對格子頂面左上角，`size` ＝ 格子邊長）：從頂面左、右、下緣往外噴出再落下。
 * `i` 是第幾顆、`n` 是總數；位置確定（相同輸入相同結果）。
 */
export function dirtBit(i: number, n: number, t: number, size: number): DustBit {
  const side = i % 3; // 0 左緣、1 右緣、2 下緣
  const u = (i + 0.5) / Math.max(1, n);
  const start =
    side === 0 ? { x: 0, y: size * (0.3 + 0.6 * u) } : side === 1 ? { x: size, y: size * (0.3 + 0.6 * u) } : { x: size * (0.15 + 0.7 * u), y: size };
  const vx = side === 0 ? -1 : side === 1 ? 1 : (u - 0.5) * 1.4;
  const k = Math.max(0, Math.min(1, t));
  const reach = size * 0.45;
  return {
    x: start.x + vx * reach * k,
    y: start.y - size * 0.35 * k + size * 0.6 * k * k, // 先往上噴、再落下
    size: 2 + (i % 2),
    alpha: 1 - k,
  };
}

/** 下降結束時的塵土圈：半徑由格子一半長到 0.9 格，透明度淡出。 */
export function dustRing(t: number, size: number): { radius: number; alpha: number } {
  const k = Math.max(0, Math.min(1, t));
  return { radius: size * (0.5 + 0.4 * k), alpha: 0.55 * (1 - k) };
}
