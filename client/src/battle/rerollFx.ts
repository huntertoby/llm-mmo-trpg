// SK-3 重擲的戰鬥演出（AR-SK3；純函式）：事件 → 演出描述，時間 t（毫秒）→ 這一刻骰子層的樣子。
// 美術：docs/art/SK-3-美術.md 第 2 節、第 5.2 節、第 8 節（第 2 版＋N1：比較箭頭一律米白）；樣張 docs/art/sample/sk3Mechanics.js、
// sk3-mechanics.html 的 `rerollTop`。移植需求 docs/art/SK-3-移植需求.md 第 1 節第 2、3、4、6 項。
// 不讀時鐘、不用亂數：骰面閃換是固定序列；「採用」給事件的 `kept`（取較差時可能落在第一次）。
// 位置一律是模型像素、相對擲骰者格子中心（往下為正）；畫面下限照地圖縮放（`MK`）。
import { asEvent, type EventBase } from "../api/types";
import { TILE_SIZE } from "./geometry";

const T = TILE_SIZE;

/** 一次重擲：`rollerId` 擲骰的人（攻擊者）、`reactorId` 付代價的反應者；`first`／`second` 兩次的自然骰；`keptFirst` 算數的是第一次；`better` 取較好（隊友讓你重擲）。 */
export interface RerollFx {
  rollerId: string;
  reactorId: string;
  first: number;
  second: number;
  keptFirst: boolean;
  better: boolean;
}

/** 演出長度（未縮放）：0–1250 擲、敲、換、比較，1250–1450 淡出。 */
export const REROLL_MS = 1450;
/** 現行浮字「重擲！」延到這一刻才出（美術 PM 裁定，SK-3-美術.md 5.2 第 3 點）。 */
export const REROLL_FLOAT_AT_MS = 1250;
/** 骰子外接半徑（模型 px）與畫面下限（畫面 px）。 */
export const DIE_R = 11;
export const DIE_MIN_PX = 9;
/** 「採用」的字級（模型 px）與畫面下限（畫面 px）。 */
export const ADOPT_PX = 12;
export const ADOPT_MIN_PX = 10;
/** 採用的那顆放大 1.1、金環半徑 1.2R。 */
export const KEEP_K = 1.1;
export const RING_K = 1.2;
/** 上一排血條的下緣（相對擲骰者格子中心；HP 條在 c.y＋0.36T、高 5）。 */
export const UPPER_HP_BOTTOM = -T + T * 0.36 + 5;
/** 新骰子轉動時的骰面（固定序列，每 60 ms 換一個）。 */
export const FLICK: readonly number[] = [7, 13, 4, 16, 9, 11, 3, 15, 6, 12];

const str = (v: unknown): string | null => (typeof v === "string" ? v : null);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** 這一步的重擲（照事件順序）。欄位不齊的事件略過。 */
export function rerollFxOf(raw: readonly Record<string, unknown>[]): RerollFx[] {
  const out: RerollFx[] = [];
  for (const e of raw.map(asEvent)) {
    if (e.type !== "attack_rerolled") continue;
    const f = rerollOf(e);
    if (f !== null) out.push(f);
  }
  return out;
}

function rerollOf(e: EventBase): RerollFx | null {
  const rollerId = str(e.attacker_id), reactorId = str(e.unit_id), first = num(e.first_natural), second = num(e.second_natural);
  if (rollerId === null || reactorId === null || first === null || second === null) return null;
  return { rollerId, reactorId, first, second, keptFirst: e.kept === "first", better: e.keep === "better" };
}

/** 骰子的畫面下限倍率：骰子半徑 ≥ 9 畫面 px（1600 寬 1.00、800 寬約 1.54）。 */
export function dieMK(mapScale: number): number {
  return mapScale > 0 ? Math.max(1, DIE_MIN_PX / (DIE_R * mapScale)) : 1;
}

/** 骰子整組的「上半徑」：採用時的金環外框（R × 1.1 × 1.2 ＋ 外框線寬的一半）。 */
export const envelope = (mk: number): number => DIE_R * mk * KEEP_K * RING_K + 2.1 * mk;

/**
 * 骰子中心相對擲骰者格子中心的 y：整組上緣收在 `top` 再往下 1 模型 px。
 * 一般單位 `top`＝上一排血條下緣（1600 寬 −8.1、800 寬＋0.9，同樣張 `dieDy`）；巨型單位、頭目由呼叫端給頭頂（`unitTopY`，移植需求第 6 項）。
 */
export function dieDy(mk: number, top: number = UPPER_HP_BOTTOM): number {
  return top + 1 + envelope(mk);
}

/** 第一次的骰子退到哪（相對骰子原位）：往左 30、往下 2（× MK）。 */
export const oldOff = (mk: number): { x: number; y: number } => ({ x: -30 * mk, y: 2 * mk });
/** 新骰子跳起來最多多高：不超過採用時的上緣。 */
export const jumpMax = (mk: number): number => envelope(mk) - DIE_R * mk;
/** 「採用」的字級（模型 px）：12，畫面下限 10 px。 */
export const adoptPx = (mapScale: number): number => (mapScale > 0 ? Math.max(ADOPT_PX, ADOPT_MIN_PX / mapScale) : ADOPT_PX);

export const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
export const ease = (t: number): number => {
  const u = clamp(t);
  return u * u * (3 - 2 * u);
};
export const span = (t: number, a: number, b: number): number => clamp((t - a) / (b - a));
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/** 一顆骰子這一刻的樣子（位置相對骰子原位；`k` 縮放、`sy` 落地壓扁、`a` 透明、`dim` 灰、`ring` 金環、`cross` 紅斜槓、`flash` 白閃，都是 0～1）。 */
export interface DieState {
  x: number;
  y: number;
  k: number;
  sy: number;
  rot: number;
  face: number;
  dim: boolean;
  ring: number;
  cross: number;
  flash: number;
  a: number;
}

/** 這一刻整組骰子層的樣子（`null`＝不畫）。 */
export interface RerollFrame {
  /** 整組的透明度（1250–1450 淡出）。 */
  fade: number;
  /** 反應者腳下光圈（0～1；0、1 不畫）。 */
  pulse: number;
  /** 引線長到哪（0～1）與它的透明度。 */
  beam: number;
  beamA: number;
  /** 敲一下的短金線（0～1；0、1 不畫）。 */
  knock: number;
  old: DieState;
  fresh: DieState | null;
  /** 比較箭頭：透明度、朝上（點數變大）。 */
  cmpA: number;
  cmpUp: boolean;
  /** 「採用」：畫在哪一顆（舊＝第一次）、透明度。 */
  adoptOld: boolean;
  adoptA: number;
}

/** 照樣張 `rerollTop` 的時間軸（第 2 版＋N1）。`mk`＝畫面下限倍率。 */
export function rerollFrame(t: number, f: RerollFx, mk: number): RerollFrame {
  const fade = 1 - span(t, 1250, 1450);
  const off = oldOff(mk);
  const firstKept = f.keptFirst, kg = ease(span(t, 960, 1080));
  const pop = t < 160 ? (t < 110 ? 1.15 * ease(span(t, 0, 110)) : lerp(1.15, 1, span(t, 110, 160))) : 1;
  const back = ease(span(t, 560, 660));
  const oldKept = firstKept && t > 940;
  const oldCross = !firstKept && t > 960 ? ease(span(t, 960, 1060)) : 0;
  const oldK = pop * lerp(1, 0.84, back) * (oldKept ? lerp(1, KEEP_K / 0.84, kg) : 1);
  const old: DieState = {
    x: off.x * back + 0, // ＋0：不出 −0
    y: off.y * back,
    k: oldK,
    sy: 1,
    rot: 0,
    face: f.first,
    dim: back > 0.5 && !oldKept,
    ring: oldKept ? kg : 0,
    cross: oldCross,
    flash: t > 440 && t < 600 ? Math.sin(span(t, 440, 600) * Math.PI) * 0.5 : 0,
    a: oldCross > 0 ? 1 - 0.3 * oldCross : 1,
  };
  let fresh: DieState | null = null;
  if (t > 580) {
    const p = span(t, 580, 860), land = span(t, 860, 940), jump = Math.sin(p * Math.PI) * jumpMax(mk);
    const newCross = firstKept && t > 960 ? ease(span(t, 960, 1060)) : 0;
    fresh = {
      x: 0,
      y: -jump,
      k: (0.5 + 0.5 * ease(span(t, 580, 660))) * (!firstKept && t > 940 ? 1 + (KEEP_K - 1) * kg : 1),
      sy: t < 860 ? 1 : 1 - 0.2 * Math.sin(land * Math.PI),
      rot: t < 860 ? ease(p) * Math.PI * 4 : 0,
      face: t < 860 ? (FLICK[Math.floor((t - 580) / 60) % FLICK.length] as number) : f.second,
      dim: newCross > 0.5,
      ring: !firstKept ? kg : 0,
      cross: newCross,
      flash: 0,
      a: newCross > 0 ? 1 - 0.3 * newCross : 1,
    };
  }
  return {
    fade,
    pulse: span(t, 260, 560),
    beam: ease(span(t, 280, 470)),
    beamA: 1 - span(t, 560, 700),
    knock: span(t, 440, 600),
    old,
    fresh,
    cmpA: t > 940 ? span(t, 940, 1020) : 0,
    cmpUp: f.second > f.first,
    adoptOld: firstKept,
    adoptA: t > 960 ? kg : 0,
  };
}
