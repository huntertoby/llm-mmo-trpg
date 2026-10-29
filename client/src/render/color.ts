// 共用調色函式（Phase 3T-4）：render/ 底下所有檔案的混色、加亮、加暗都用這裡，不要各寫一份。
// 一律只認 `#rrggbb`；其他格式（rgb()、色名）原樣回傳，不出錯。

const HEX = /^#[0-9a-f]{6}$/i;

/** 是不是 `#rrggbb`。 */
export const isHex = (c: string): boolean => HEX.test(c);

/** `#rrggbb` → [r, g, b]（0–255）。 */
export function hexRgb(h: string): [number, number, number] {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** 兩色混合（`t` ＝ b 的比例）；任一個不是 `#rrggbb` 時原樣回傳 `a`。 */
export function mix(a: string, b: string, t: number): string {
  if (!HEX.test(a) || !HEX.test(b)) return a;
  const [r1, g1, b1] = hexRgb(a);
  const [r2, g2, b2] = hexRgb(b);
  const m = (x: number, y: number): number => Math.round(x * (1 - t) + y * t);
  return `#${((m(r1, r2) << 16) | (m(g1, g2) << 8) | m(b1, b2)).toString(16).padStart(6, "0")}`;
}

/** 與黑色混合（暗 t）。 */
export const darken = (c: string, t: number): string => mix(c, "#000000", t);
/** 與白色混合（亮 t）。 */
export const lighten = (c: string, t: number): string => mix(c, "#ffffff", t);

/** 把亮度乘上 `f`，回傳 CSS 顏色（`rgb(r,g,b)`，`f` 大於 1 變亮）。 */
export function shade(h: string, f: number): string {
  const [r, g, b] = hexRgb(h);
  const c = (v: number): number => Math.max(0, Math.min(255, Math.round(v)));
  return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
}

export function rgba(h: string, a: number): string {
  const [r, g, b] = hexRgb(h);
  return `rgba(${r},${g},${b},${a})`;
}

/** Pixi 的數字顏色 → `#rrggbb`。 */
export function numToHex(n: number): string {
  return `#${(n & 0xffffff).toString(16).padStart(6, "0")}`;
}
