// 程式繪製美術的色票（Phase 3-16a；來源：美術 PM 的 docs/art/移植需求.md 第 1 節）。
// 整體偏低彩度，讓陣營色與特效跳出來。元件只引用這裡的鍵，不寫死色碼，之後整組換色只改這個檔。

import { MATERIAL } from "./material";

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
  fire: "#ff6a1a",
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

// ---- 裝備圖示色票（Phase 3G-G5a；來源：docs/art/裝備外觀移植需求.md 第 2 節）----

/** 圖示描邊色。 */
export const GEAR_INK = "#16181d";

/** 材質 `[主色, 暗色]`；`shine`：銀，加 1.4px 白色亮線。 */
export const GEAR_MATERIAL: Readonly<Record<string, { c: readonly [string, string]; shine?: boolean }>> = Object.fromEntries(
  Object.entries(MATERIAL).map(([id, c]) => [id, id === "silver" ? { c, shine: true } : { c }]),
);

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

/** 稀有度外框色。 */
export const GEAR_RARITY: Readonly<Record<string, string>> = {
  common: "#8a8f99",
  uncommon: "#5fd05f",
  rare: "#4f9dff",
  epic: "#b06cff",
  legendary: "#ffbf3a",
};
