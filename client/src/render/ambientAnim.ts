// 環境動態的時間軸（Phase 6N-10；動畫方案 2.7、需求 docs/art/動畫移植需求第二批.md 第 9 節）。
// 全部是純函式：（種子字串、毫秒）→ 擺幅、亮度、位置。不用 Math.random()、不讀時鐘；種子用 inkStyle.seedOf（FNV-1a）。
// 只動畫面，不改地圖資料：營火與燈籠的火苗閃動、光暈呼吸；草叢、竹叢、酒旗依風向擺；冰洞的水波、雲嶺的薄霧慢慢飄。
// 換貼圖的只有酒旗（4 格，量化），其他都是 Pixi 節點的縮放、斜切、透明度與位移，不新增貼圖。
import { seedOf } from "./inkStyle";
import type { Wind } from "./ambientModel";

const TAU = Math.PI * 2;

/** 0～1 的相位（同一個種子永遠一樣）。 */
export function phaseOf(seed: string): number {
  return (seedOf(seed) % 1000) / 1000;
}

// ---- 草、竹、旗：依風向擺 ----------------------------------------------------

/** 草叢擺動的週期（毫秒）。 */
export const SWAY_MS = 2600;
/** 平均往下風傾的角度、來回的擺幅（弧度，乘上風力）。 */
export const SWAY_LEAN = 0.035;
export const SWAY_SWING = 0.045;

/** 這一叢草在 `ms` 時的斜切角（弧度；正 ＝ 頂端往東）。往下風傾斜、來回擺，每叢相位錯開。 */
export function swayAt(seed: string, ms: number, wind: Wind, strength: number): number {
  const p = phaseOf(`sway:${seed}`);
  const u = ms / SWAY_MS + p;
  // 兩個頻率疊起來，看起來像一陣一陣的風，不是整齊的節拍器
  const swing = 0.75 * Math.sin(u * TAU) + 0.25 * Math.sin(u * TAU * 2.3 + p * TAU);
  return wind * strength * (SWAY_LEAN + SWAY_SWING * swing);
}

/** 酒旗的格數（量化：同一張圖的旗子共用 4 張貼圖）。 */
export const FLAG_FRAMES = 4;
/** 酒旗每格的時間（毫秒）。 */
export const FLAG_FRAME_MS = 170;

/** 酒旗在 `ms` 時的第幾格（0～FLAG_FRAMES-1）；風力大時翻得快一點。 */
export function flagFrame(seed: string, ms: number, strength: number): number {
  const step = FLAG_FRAME_MS / Math.max(0.5, strength);
  const n = Math.floor(ms / step + phaseOf(`flag:${seed}`) * FLAG_FRAMES);
  return ((n % FLAG_FRAMES) + FLAG_FRAMES) % FLAG_FRAMES;
}

/** 酒旗第 `frame` 格的布面波形：沿著旗面 0→1，往風向的垂直位移（-1～1）。畫貼圖時用。 */
export function flagWave(frame: number, along: number): number {
  return Math.sin((along * 1.6 - frame / FLAG_FRAMES) * TAU) * along;
}

// ---- 營火、燈籠：火苗閃動、光暈呼吸 -------------------------------------------

/** 光暈呼吸的週期（毫秒）。 */
export const GLOW_MS = 1800;

export interface Flicker {
  /** 火苗的縮放（寬、高）。 */
  sx: number;
  sy: number;
  /** 火苗頂端往風向偏（斜切弧度）。 */
  skew: number;
  /** 光暈的透明度與縮放。 */
  glow: number;
  glowScale: number;
}

/** 火苗在 `ms` 時的樣子：三個不成整數比的正弦疊起來（看起來不規則，但完全確定）。燈籠的火小、閃得輕（`small`）。 */
export function flickerAt(seed: string, ms: number, small = false): Flicker {
  const p = phaseOf(`fire:${seed}`) * TAU;
  const n = 0.5 * Math.sin((ms / 310) * TAU + p) + 0.3 * Math.sin((ms / 530) * TAU + 2 * p) + 0.2 * Math.sin((ms / 170) * TAU + 3 * p);
  const breath = Math.sin((ms / GLOW_MS) * TAU + p);
  const k = small ? 0.4 : 1;
  return {
    sx: 1 - 0.06 * k * n,
    sy: 1 + 0.16 * k * n,
    skew: 0.08 * k * Math.sin((ms / 700) * TAU + p),
    glow: (small ? 0.42 : 0.5) + 0.14 * breath + 0.05 * n,
    glowScale: 1 + 0.06 * breath,
  };
}

// ---- 水波、薄霧：慢慢飄 --------------------------------------------------------

/** 水波一圈的時間（毫秒）；同一格兩圈錯開半個週期。 */
export const RIPPLE_MS = 2600;

export interface Ripple {
  /** 圈的大小（相對最大半徑 0.25～1）與透明度。 */
  scale: number;
  alpha: number;
}

export function ripplesAt(seed: string, ms: number): Ripple[] {
  const p = phaseOf(`ripple:${seed}`);
  return [0, 0.5].map((off) => {
    const u = (((ms / RIPPLE_MS + p + off) % 1) + 1) % 1;
    return { scale: 0.25 + 0.75 * u, alpha: 0.5 * Math.sin(u * Math.PI) };
  });
}

/** 薄霧一團漂過整張圖的速度（格／秒）。 */
export const MIST_SPEED = 0.18;

export interface MistWisp {
  /** 中心（格；可以在圖外，畫面會切掉）。 */
  x: number;
  y: number;
  alpha: number;
}

/** 薄霧的團數：每 48 格一團，3～12 團。 */
export function mistCount(width: number, height: number): number {
  return Math.max(3, Math.min(12, Math.round((width * height) / 48)));
}

/**
 * 第 `i` 團霧在 `ms` 時的位置：照風向慢慢漂，出了圖從另一邊回來（左右各多 2 格的跑道）；上下輕輕起伏。
 * 起點、列、速度差都從「場景鍵:序號」的雜湊來。
 */
export function mistAt(key: string, i: number, ms: number, wind: Wind, width: number, height: number): MistWisp {
  const h = seedOf(`mist:${key}:${i}`);
  const lane = width + 4;
  const speed = MIST_SPEED * (0.7 + ((h >>> 8) % 7) / 10);
  const start = ((h >>> 4) % 1000) / 1000;
  const x = (((start * lane + wind * speed * (ms / 1000)) % lane) + lane) % lane - 2;
  const row = ((h >>> 16) % 1000) / 1000;
  const y = row * height + 0.3 * Math.sin((ms / 7000) * TAU + start * TAU);
  const alpha = 0.1 + 0.05 * Math.sin((ms / 9000) * TAU + row * TAU);
  return { x, y, alpha };
}
