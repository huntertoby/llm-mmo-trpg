// 頭目部位的頭頂小格與人物外觀旗標（PB-1e；美術移植需求 docs/art/頭目部位-移植需求.md 2.2、2.3、3.4、3.6）。純函式：不碰 Pixi、DOM。
// - 頭頂部位小格：HP 條正下方、共用黑底；三條照 18.2.3 的順序（拂塵｜氣海｜長劍）、寬度不變（都在 HP 條的 38.4 之內），只往下長。
//   800 寬（地圖縮放小）只放大高度：條高畫面 ≥ 2 px、「×」≥ 4 px（樣張 `STRIP.MIN_BAR_PX`、`MIN_X_PX`）。
// - 人物外觀旗標（`dollPartsOf`）：拂塵剪短、劍斷、氣海露出時的氣旋或破了的裂痕；破壞演出的前三格（部位還在、白閃／裂紋、碎塊在空中）
//   由繪製器暫時蓋過（`PartFx`），演出播完回到伺服器給的樣子。
import type { DollParts } from "../render/appearance";
import type { PartView } from "../api/types";
import { TILE_SIZE } from "./geometry";
import { partBarState, type PartBarState } from "./partMenu";

const T = TILE_SIZE;
/** HP 條（`unitSprite.ts hpBar`）：寬、上緣（相對格子中心）、高。 */
export const HP_W = T * 0.8;
export const HP_Y = T * 0.36;
export const HP_H = 5;

/** 部位條（模型 px；樣張 `bossParts.js STRIP`）。 */
export const STRIP = { gapTop: 0.8, h: 2.6, pad: 0.8, gap: 1.6, xSize: 5.6, MIN_BAR_PX: 2, MIN_X_PX: 4 } as const;
/** 打叉的線寬（模型 px）：1600 寬（地圖 1.31）時 1.5，地圖越小越粗（樣張 `hud` 的 k）。 */
export const STRIP_X_LINE = 1.5;
export const STRIP_X_INK = 1.2;
/** 樣張量線寬時的基準縮放（1600×900 的雲頂觀）。 */
const STRIP_X_BASE_SCALE = 1.31;

/** 部位條的顏色（美術移植需求 2.2）。 */
export const STRIP_COLOR = { ok: 0xf2e6c8, empty: 0x4a4252, broken: 0x5a1a1a, hidden: 0x0e0e14, x: 0xff5a4a, ink: 0x16121a } as const;

/**
 * 18.2.3「部位」表的順序（頭頂、外觀用）；不認得的部位排在後面、照 ID。
 * GB-4b：灰燼之心 3×3（19 19.2.3）照由北到南、左到右：熔岩噴口｜殼縫｜核心（美術移植需求第 7 節第 2 條）。
 */
export const PART_ORDER: readonly string[] = ["whisk", "dantian", "sword", "vent", "shell_seam", "core"];

export function partOrder<T extends { id: string }>(parts: readonly T[]): T[] {
  const rank = (id: string): number => {
    const i = PART_ORDER.indexOf(id);
    return i < 0 ? PART_ORDER.length : i;
  };
  return [...parts].sort((a, b) => rank(a.id) - rank(b.id) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/** 畫法資料裡的一個部位（`UnitDraw.parts`）。 */
export interface PartDraw {
  id: string;
  broken: boolean;
  exposed: boolean;
  bar: PartBarState;
  /** GB-4b：近戰打這個部位算從背後（`PartView.counts_as_behind`，灰燼之心的殼縫）；其他部位沒有這個欄位（鍵不變）。 */
  behind?: true;
}

/** 伺服器的部位 → 畫法資料（照 18.2.3 的順序；拿不到血量＝未露出）。 */
export function partDraws(parts: readonly PartView[] | null | undefined): PartDraw[] {
  return partOrder(parts ?? []).map((p) => ({ id: p.id, broken: p.broken, exposed: p.exposed, bar: partBarState(p), ...(p.counts_as_behind === true ? { behind: true as const } : {}) }));
}

/** 破壞演出中繪製器暫時蓋過的樣子：`flash`／`crack`＝部位還在（白閃、裂紋），`fly`＝已經斷了、碎塊還在空中（地上還沒有掉落物）。 */
export type PartFxK = "flash" | "crack" | "fly";
export interface PartFx {
  part: string;
  k: PartFxK;
  /**
   * GB-4b：巨型頭目（3×3）的破壞演出第幾格（0 命中、1 裂開、2 斷開、3 落地；`qBossGiant` 的 `fx.k`）。
   * 霧鎖真人（1 格）沒有這個欄位：第 4 格（落地）起就回到伺服器的樣子；巨型頭目第 4 格還有自己的畫法，播完才回去。
   */
  frame?: 0 | 1 | 2 | 3;
  /** GB-4b：殼縫被打中的那一側（`attack_rolled.hit_tile` 在中心格的西 −1、東 1）。 */
  side?: -1 | 1;
  /** GB-4b：這次殼縫破時熔殼還在（第 1 階段）：殼片跟著第 3、4 格彈起、飛走。 */
  shed?: boolean;
}

/** GB-4b：巨型頭目破壞演出的第幾格 → `PartFx`（霧鎖真人同一組 k：flash、crack、fly；第 4 格也是 fly）。第 5 格（定格）＝`null`。 */
export function giantBreakFxOf(part: string, frame: number, side: -1 | 1, shed: boolean): PartFx | null {
  if (frame < 0 || frame > 3) return null;
  const k: PartFxK = frame === 0 ? "flash" : frame === 1 ? "crack" : "fly";
  return { part, k, frame: frame as 0 | 1 | 2 | 3, side, shed };
}

/** 演出中這個部位要不要當成「還沒破」畫。 */
const intact = (id: string, fx: PartFx | null | undefined): boolean => fx != null && fx.part === id && fx.k !== "fly";

/**
 * 人物外觀旗標：拂塵、長劍破了＝剪短、劍斷；氣海破了＝裂痕，露出（還沒破）＝氣旋。沒有部位或什麼都不用畫時 `null`
 * （`DollSpec` 不帶 `parts`，貼圖鍵與畫法和沒有部位的單位相同）。
 */
export function dollPartsOf(parts: readonly PartDraw[] | undefined, fx?: PartFx | null): DollParts | null {
  if (parts === undefined || parts.length === 0) return null;
  const out: DollParts = {};
  for (const p of parts) {
    const broken = p.broken && !intact(p.id, fx);
    if (p.id === "whisk" && broken) out.whisk = true;
    else if (p.id === "sword" && broken) out.sword = true;
    else if (p.id === "dantian") {
      if (broken) out.dantian = "crack";
      else if (p.exposed || intact(p.id, fx)) out.dantian = "qi";
    }
  }
  if (fx != null && fx.k !== "fly" && parts.some((p) => p.id === fx.part)) out.fx = { part: fx.part, k: fx.k };
  return Object.keys(out).length === 0 ? null : out;
}

/** 地上的掉落物（剪下的拂塵毛、斷下的劍尖）：破了而且不在演出前三格。 */
export function debrisOf(parts: readonly PartDraw[] | undefined, fx?: PartFx | null): { whisk: boolean; sword: boolean } {
  const down = (id: string): boolean => (parts ?? []).some((p) => p.id === id && p.broken) && !(fx != null && fx.part === id);
  return { whisk: down("whisk"), sword: down("sword") };
}

/** 頭頂部位小格的排法（模型 px、相對格子中心）。`boardScale`＝地圖在畫面上的縮放。 */
export interface StripLayout {
  /** 條高。 */
  h: number;
  /** 「×」的大小。 */
  xs: number;
  /** 每條寬。 */
  w: number;
  /** 第一條的上緣。 */
  top: number;
  /** 黑底的下緣（條下面再 0.8 黑）。 */
  bottom: number;
  /** 第一條的左緣。 */
  x0: number;
  /** 「×」線寬的倍率。 */
  k: number;
}

export function stripLayout(n: number, boardScale: number): StripLayout {
  const s = boardScale > 0 ? boardScale : 1;
  const h = Math.max(STRIP.h, STRIP.MIN_BAR_PX / s);
  const xs = Math.max(STRIP.xSize, STRIP.MIN_X_PX / s);
  const inner = HP_W - 2 * STRIP.pad;
  const m = Math.max(1, n);
  const w = (inner - (m - 1) * STRIP.gap) / m;
  const top = HP_Y + HP_H + STRIP.gapTop;
  return { h, xs, w, top, bottom: top + h + STRIP.pad, x0: -HP_W / 2 + STRIP.pad, k: Math.max(1, 1 / s / STRIP_X_BASE_SCALE) };
}

/** 頭頂小格每一條的狀態：看不到資訊（隱蔽）時全部「未露出」；演出中斷掉的那一條先畫成空槽，落地時才換成「×」。 */
export function stripBars(parts: readonly PartDraw[], hiddenInfo: boolean, fx?: PartFx | null): PartBarState[] {
  return parts.map((p) => {
    if (hiddenInfo) return { kind: "hidden" };
    // GB-4b：巨型頭目第 4 格（落地）就換成「×」（移植需求 5.5 第 5 條，同段 1）
    if (fx != null && fx.part === p.id && p.broken && (fx.frame ?? 0) < 3) return { kind: "ok", hp: 0, max: 1 };
    return p.bar;
  });
}

/** 南邊那一格有站著的單位：頭目整組 HUD 改掛 `hudTop`（美術移植需求 3.4）。只看有部位的單位。 */
export function partHudUp(u: { x: number; y: number; parts?: readonly PartDraw[] | undefined }, units: ReadonlyArray<{ x: number; y: number; downed: boolean }>): boolean {
  if (u.parts === undefined || u.parts.length === 0) return false;
  return units.some((o) => o.x === u.x && o.y === u.y + 1 && !o.downed);
}
