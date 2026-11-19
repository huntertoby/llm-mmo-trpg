// AP-2 預支的施放演出 `borrow_pull`（AR-AP2；純函式）：時間 t（毫秒）→ 這一刻「下回合的那格」、菱形、光圈的樣子。
// 美術：docs/art/AP-2-美術.md 第 4 節（時間表）、5.3；樣張 docs/art/sample/ap2Borrow.js 的 `slotAt`／`borrowFx`。移植需求 docs/art/AP-2-移植需求.md 第 1 節第 4 項。
// 照 SK-3 的先例（`rerollFx.ts`）拆檔：這裡只算位置與時間軸，畫法在 `render/borrowEffects.ts`。
// 不讀時鐘、不用亂數。位置一律是模型像素、相對施放者格子中心（往下為正）；`dir`＝面向（東＋1、西−1）；畫面下限照地圖縮放（`MK`）。
import { TILE_SIZE } from "./geometry";
import { clamp, ease, lerp, span, UPPER_HP_BOTTOM } from "./rerollFx";
import type { SkillRow } from "./skillSequence";

const T = TILE_SIZE;

/** 演出長度（未縮放）：同現行給予 AP 的拍肩 `shoulder_tap`。 */
export const BORROW_MS = 320;
/** AP 列的菱形與紅斜線在演出的這一刻開始淡入（菱形到胸口；美術 PM 裁定 4，AP-2-美術.md 第 9 節）。 */
export const BORROW_AP_FADE_AT_MS = 215;
/** 時間點（毫秒）：那格浮出、菱形被拉出來、紅斜線、到胸口的光圈、那格淡出。 */
export const BORROW_TIMES = { slotIn: [0, 90], pull: [100, 230], slash: [150, 220], arrive: [215, 320], slotOut: [230, 320], gemOut: [260, 320] } as const;
/** 菱形半對角、那格半徑（模型 px）與菱形的畫面下限（半對角，畫面 px：畫面上直徑 9 px，同 AP 列的菱形）。 */
export const GEM_R = 5;
export const SLOT_R = 6.5;
export const MIN_GEM_PX = 4.5;
/** 腳底（`unitSprite.FEET`＝T×0.23）與胸口（遊戲端 `skillLayer.chest()`：腳底往上 T×0.35＝16.8）相對格子中心。 */
const FEET = T * 0.23;
export const CHEST_DY = FEET - T * 0.35;
/** 胸口往面向偏幾 px。 */
export const CHEST_DX = 3;

/** 畫面下限倍率：菱形半對角 ≥ 4.5 畫面 px（1600 寬 1.00、800 寬約 1.70）。 */
export function borrowMK(mapScale: number): number {
  return mapScale > 0 ? Math.max(1, MIN_GEM_PX / (GEM_R * mapScale)) : 1;
}

/** 「下回合的那格」相對施放者格子中心：胸口前方 17＋(MK−1)×8、格子中心往上 9；整顆上緣不高於上一排血條下緣再往下 1。 */
export function slotAt(dir: 1 | -1, mk: number): { x: number; y: number } {
  const rOut = (SLOT_R + 1.9) * mk;
  return { x: dir * (17 + (mk - 1) * 8), y: Math.max(-9, UPPER_HP_BOTTOM + 1 + rOut) };
}

/** 胸口（菱形飛到的地方）相對施放者格子中心。 */
export const chestAt = (dir: 1 | -1): { x: number; y: number } => ({ x: dir * CHEST_DX, y: CHEST_DY });

/** 這一刻的演出（`k` 縮放、`a` 透明、`slash` 紅斜線畫到哪、`arrive` 光圈的進度；都是 0～1，0 或 1 的光圈不畫）。 */
export interface BorrowFrame {
  slot: { x: number; y: number; k: number; a: number; slash: number };
  gem: { x: number; y: number; k: number; a: number };
  arrive: { x: number; y: number; p: number };
}

/** 照樣張 `borrowFx` 的時間軸；超出 0～320 回 `null`（不畫）。 */
export function borrowFrame(t: number, mk: number, dir: 1 | -1): BorrowFrame | null {
  if (t < 0 || t > BORROW_MS) return null;
  const TM = BORROW_TIMES;
  const s = slotAt(dir, mk), chest = chestAt(dir);
  const sIn = ease(span(t, ...TM.slotIn)), sOut = span(t, ...TM.slotOut);
  const sk = t < TM.slotIn[1] ? 0.6 + 0.4 * sIn : 1;
  const p = ease(span(t, ...TM.pull));
  /* 短弧：從那格往施放者胸口，中點往上拱 6×MK（不往下穿過身體） */
  const mx = (s.x + chest.x) / 2, my = Math.min(s.y, chest.y) - 6 * mk, u = 1 - p;
  const gx = u * u * s.x + 2 * u * p * mx + p * p * chest.x, gy = u * u * s.y + 2 * u * p * my + p * p * chest.y;
  const arr = span(t, ...TM.arrive);
  /* 在那格裡是 0.72（框看得到），拉出來長到 1；到胸口縮到 0.65 */
  const gk = (t < TM.pull[0] ? 0.72 * (0.6 + 0.4 * sIn) : lerp(0.72, 1, ease(span(t, TM.pull[0], 170)))) * (1 - 0.35 * ease(arr));
  return {
    slot: { x: s.x, y: s.y, k: sk, a: sIn * (1 - sOut), slash: ease(span(t, ...TM.slash)) },
    gem: { x: gx, y: gy, k: gk, a: clamp((t < 40 ? sIn * 1.6 : 1) * (1 - ease(span(t, ...TM.gemOut))), 0, 1) },
    arrive: { x: chest.x, y: chest.y, p: arr },
  };
}

/**
 * AP 列淡入要延後多久（AR-AP2 第 5 項；美術 PM 裁定 4）：`rows`＝這一步的身體片段（時間已照播放速度縮放）、`viewAtMs`＝畫面更新
 * （AP 列換成預支後的樣子）在同一個時間原點的哪一刻。對齊演出 215 ms（菱形到胸口）；畫面更新已經過了 215 ms 就等到演出結束（320 ms）之後。
 * 這一步沒有預支的演出時 0（照現行，畫面更新就淡入）。
 */
export function borrowApDelayMs(rows: readonly Pick<SkillRow, "clip" | "recover" | "startMs" | "ms">[] | undefined, viewAtMs: number): number {
  const r = rows?.find((x) => x.clip === "borrow_pull" && !x.recover);
  if (r === undefined) return 0;
  const k = r.ms / BORROW_MS, at = r.startMs + BORROW_AP_FADE_AT_MS * k;
  if (viewAtMs <= at) return Math.round(at - viewAtMs);
  return Math.max(0, Math.round(r.startMs + r.ms - viewAtMs));
}
