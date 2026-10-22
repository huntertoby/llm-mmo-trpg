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
  smoke: "#dcdfe6",
  holy: "#ffe58a",
  darkness: "#3b1f4f",
  wood: "#b77f3f",
  woodDark: "#6e4620",
  woodMid: "#8f5f2c",
  rock: "#a8a49a",
  rockDark: "#6c685f",
  cliff: "#5b4a3a",
  iceWall: "#9fe0ff",
  thorn: "#4f7a2a",
  bush: "#3f6e2a",
} as const;

/** 陣營底圈（填色／外框；Pixi 數字色）：我方、敵方、召喚。 */
export const RING = {
  ally: { fill: 0x2f6fd0, stroke: 0xa9ccff },
  enemy: { fill: 0xc63b3b, stroke: 0xffb3a8 },
  summon: { fill: 0x1f9e8f, stroke: 0x8ff0e2 },
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

// ---- 裝備圖示色票（Phase 3G-G5a；來源：docs/art/裝備外觀移植需求.md 第 2 節）----

/** 圖示描邊色。 */
export const GEAR_INK = "#16181d";

/** 材質 `[主色, 暗色]`；`shine`：銀，加 1.4px 白色亮線。 */
export const GEAR_MATERIAL: Readonly<Record<string, { c: readonly [string, string]; shine?: boolean }>> = {
  iron: { c: ["#7a828b", "#474c52"] },
  steel: { c: ["#a9b6c6", "#6d7a8a"] },
  copper: { c: ["#b06a3c", "#6e3e20"] },
  silver: { c: ["#e8edf2", "#a8b0ba"], shine: true },
  gold: { c: ["#e8bb48", "#9c7420"] },
  wood: { c: ["#a06a36", "#6a4420"] },
  leather: { c: ["#8a5a32", "#5e3b1f"] },
  cloth: { c: ["#8a8f99", "#5d6168"] },
  bone: { c: ["#e9e3cf", "#a8a08a"] },
  crystal: { c: ["#b8a8ff", "#7a68c8"] },
};

/** 染色（暗色＝染色混黑 35%）。 */
export const GEAR_DYE: Readonly<Record<string, string>> = {
  red: "#b83a3a",
  blue: "#3a5fb8",
  green: "#3f8a4a",
  purple: "#7a4ab0",
  black: "#33363d",
  white: "#e6e6e0",
  brown: "#7a5232",
  gold: "#d9a83a",
};

/** 關鍵字（id 同 skill_keywords.yaml）：`tint` ＝ 元素，主色混入 40%、暗色混入 25%。 */
export const GEAR_KEYWORD: Readonly<Record<string, { c: string; tint?: boolean }>> = {
  ignite: { c: "#ff6a1a", tint: true },
  wet: { c: "#4aa8ff", tint: true },
  charged: { c: "#fff36b", tint: true },
  frozen: { c: "#8fe3ff", tint: true },
  prone: { c: "#e0b080" },
  collision: { c: "#ff9a4a" },
  marked: { c: "#d06aff" },
  high_ground: { c: "#ffe9a8" },
  concealed: { c: "#a0a0c8" },
  summon: { c: "#7dffb0" },
};

/** 稀有度外框色。 */
export const GEAR_RARITY: Readonly<Record<string, string>> = {
  common: "#8a8f99",
  uncommon: "#5fd05f",
  rare: "#4f9dff",
  epic: "#b06cff",
  legendary: "#ffbf3a",
};
