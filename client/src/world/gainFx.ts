// 升級與拿到物品的介面動畫要播什麼（Phase 6N-10；動畫方案 2.8，純函式）：比較前後兩次伺服器畫面，只讀不改。
// - 升級：同一個角色的等級變高 → 主角腳下一道光柱、HUD 的 Lv 數字翻動。
// - 拿到物品：背包＋腰包＋身上裝備的數量（依物品 ID 加總）變多 → 物品圖示飛進背包圖示。
//   放進腰包、穿上、脫下只是換位置，總數不變，不算拿到；賣掉、用掉是變少，也不播。
import type { WorldInventory, WorldView } from "../api/types";
import type { GearLook } from "../render/gearIcon";
import { hasItemIcon } from "../render/itemIcon";

export interface Gain {
  item: string;
  name: string;
  gear: boolean;
  count: number;
  /** 染料顏色、稀有材料（物品 view 的 `color`、`rare`；QI-7 物品圖示用）。 */
  color?: string | null;
  rare?: boolean | null;
}

/** 一次最多飛幾個（一口氣拿到很多時只飛前幾個，其餘的照樣進背包）。 */
export const MAX_FLY = 3;

interface Total {
  n: number;
  name: string;
  gear: boolean;
  color: string | null;
  rare: boolean | null;
}

function totals(inv: WorldInventory): Map<string, Total> {
  const out = new Map<string, Total>();
  const add = (item: string, n: number, name: string, gear: boolean, color: string | null = null, rare: boolean | null = null) => {
    const cur = out.get(item);
    out.set(item, { n: (cur?.n ?? 0) + n, name: cur?.name ?? name, gear: cur?.gear ?? gear, color: cur?.color ?? color, rare: cur?.rare ?? rare });
  };
  for (const b of [...inv.bag, ...inv.pouch]) add(b.item, b.count, b.name_zh, b.gear, b.color ?? null, b.rare ?? null);
  for (const s of inv.equipment ?? []) if (s.item != null) add(s.item.id, 1, s.item.name_zh, true);
  return out;
}

/** 前後兩份背包之間多出來的物品（依物品 ID 排序，最多 `MAX_FLY` 個）；任一份沒有時不播。 */
export function gainedItems(prev: WorldInventory | null | undefined, next: WorldInventory | null | undefined): Gain[] {
  if (prev == null || next == null) return [];
  const a = totals(prev);
  const out: Gain[] = [];
  for (const [item, t] of [...totals(next)].sort(([x], [y]) => (x < y ? -1 : x > y ? 1 : 0))) {
    const more = t.n - (a.get(item)?.n ?? 0);
    if (more > 0) out.push({ item, name: t.name, gear: t.gear, count: more, ...(t.color !== null ? { color: t.color } : {}), ...(t.rare !== null ? { rare: t.rare } : {}) });
  }
  return out.slice(0, MAX_FLY);
}

/**
 * 飛行圖示要畫什麼：裝備用 `gearIcon` 的實際圖示（6Q-1；外觀從同一份背包找）；物品畫自己的 Q 版圖示（QI-7，`qIcon/items.ts` 表裡有的，
 * 或有染料顏色的）；其他用通用圖示（`gain_item` 布袋、`gain_gear` 劍）。
 */
export type GainIconChoice = { kind: "gear"; look: GearLook; slot: string | null } | { kind: "item"; item: string; color: string | null; rare: boolean | null } | { kind: "generic"; gear: boolean };

/**
 * 物品：表裡有圖示（或有染料顏色）就畫自己的，否則通用布袋。
 * 裝備找外觀：先看身上穿的（`equipment`），再看背包的裝備卡（`gear_cards`），依物品 ID 比對。
 * 兩邊都找不到（舊畫面、資料不齊）時退回通用的劍。
 */
export function gainIconOf(inv: WorldInventory | null | undefined, gain: Pick<Gain, "item" | "gear" | "color" | "rare">): GainIconChoice {
  if (!gain.gear) return hasItemIcon(gain.item, gain.color) ? { kind: "item", item: gain.item, color: gain.color ?? null, rare: gain.rare ?? null } : { kind: "generic", gear: false };
  if (inv == null) return { kind: "generic", gear: true };
  for (const s of inv.equipment ?? []) {
    if (s.item != null && s.item.id === gain.item && s.item.appearance != null) return { kind: "gear", look: s.item.appearance, slot: s.slot };
  }
  for (const c of inv.gear_cards ?? []) {
    if (c.item.id === gain.item && c.item.appearance != null) return { kind: "gear", look: c.item.appearance, slot: c.slot };
  }
  return { kind: "generic", gear: true };
}

/** 升級了：同一個角色、等級變高（換角色、第一次載入不算）。回傳新的等級，沒升級＝`null`。 */
export function levelUp(prev: WorldView | null | undefined, next: WorldView): number | null {
  if (prev == null) return null;
  const a = prev.character;
  const b = next.character;
  if (a.character_id !== b.character_id) return null;
  return b.level > a.level ? b.level : null;
}

/** 動畫長度（毫秒）：光柱、物品飛行（第 i 個晚 120 毫秒出發）、Lv 翻動。 */
export const PILLAR_MS = 1400;
export const FLY_MS = 750;
export const FLY_STAGGER_MS = 120;
export const FLIP_MS = 520;

/** 物品飛行的路徑：從起點拋物線飛到背包（t 0→1；中間往上拱 `arc` 像素），最後縮小。 */
export function flyAt(from: { x: number; y: number }, to: { x: number; y: number }, t: number, arc = 60): { x: number; y: number; scale: number; alpha: number } {
  const u = Math.max(0, Math.min(1, t));
  const e = u * u * (3 - 2 * u); // smoothstep
  return {
    x: from.x + (to.x - from.x) * e,
    y: from.y + (to.y - from.y) * e - arc * 4 * u * (1 - u),
    scale: u < 0.15 ? 0.6 + (u / 0.15) * 0.6 : 1.2 - 0.6 * ((u - 0.15) / 0.85),
    alpha: u < 0.9 ? 1 : 1 - (u - 0.9) / 0.1,
  };
}
