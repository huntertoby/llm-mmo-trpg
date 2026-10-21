// 程式繪製美術的色票（Phase 3-16a；來源：美術 PM 的 docs/art/移植需求.md 第 1 節）。
// 整體偏低彩度，讓陣營色與特效跳出來。元件只引用這裡的鍵，不寫死色碼，之後整組換色只改這個檔。

export const PAL = {
  stone: "#8e8a80",
  stoneGap: "#6c685f",
  grass: "#6b9a4b",
  grassLight: "#8dbb62",
  grassDark: "#4f7a35",
  dirt: "#9a7650",
  dirtLight: "#b48f66",
  dirtDark: "#76593a",
  wallTop: "#5d554e",
  wallLine: "#3d3732",
  wallFace: "#2e2925",
  chasm: "#0d0d14",
  chasmLip: "#3b3742",
  lava: "#e2531d",
  lavaCrust: "#7c2a14",
  lavaGlow: "#ffd04a",
  deep: "#1c4a7c",
  deepLight: "#4f86c0",
  water: "#3a86d8",
  ice: "#d4f0ff",
  oil: "#211a10",
  fire: "#ff7a1a",
  poison: "#74c23c",
  smoke: "#b8b8c0",
  holy: "#fff1a8",
  darkness: "#3b1f4f",
  wood: "#b77f3f",
  woodDark: "#6e4620",
  woodMid: "#8f5f2c",
  rock: "#a8a49a",
  rockDark: "#6c685f",
  cliff: "#5b4a3a",
  iceWall: "#9fe0ff",
  thorn: "#4f7a2a",
} as const;

export type PalKey = keyof typeof PAL;

export function hexRgb(h: string): [number, number, number] {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** 把亮度乘上 `f`，回傳 CSS 顏色。 */
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
