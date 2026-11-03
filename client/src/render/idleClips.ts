// 待機片段（Phase 6M-4；需求 docs/art/動畫移植需求.md 第 5 節，樣張 docs/art/sample/anim.js 的 CLIP.idle）。
// 全部是純函式：（單位 ID、待機時鐘毫秒）→ 呼吸起伏與偶爾的小動作。不用 Math.random()、不讀時間；
// 相位用單位 ID 的 FNV-1a 雜湊錯開（不用內建 hash，字串順序固定），同一個 ID、同一個時間永遠得到同一個畫面。
// - 呼吸：起伏 0.5（虛擬像素，頭頂的位移），週期 1.6 秒。用小人貼圖以腳底為軸的垂直縮放做，不換貼圖、腳不離地。
// - 小動作：每人 7～11 秒一次、每次 1.2 秒（左右張望／伸懶腰二選一，依雜湊與第幾次輪流）；
//   強度量化成 4 級，同樣的裝備與朝向共用貼圖（每人最多 8 張）。
import { quantizePose } from "./motionClips";
import { scalePose, type InkPose } from "./inkPose";

/** 呼吸週期（毫秒）。 */
export const BREATH_MS = 1600;
/** 呼吸起伏（虛擬像素；頭頂往上的最大位移）。 */
export const BREATH_PX = 0.5;
/** 頭頂離腳底的高度（虛擬像素；同 inkDoll 的 DOLL_HEAD_TOP）：呼吸的縮放 ＝ 起伏 ÷ 身高。 */
export const BREATH_HEIGHT = 53;
/** 小動作的長度（毫秒）。 */
export const FIDGET_MS = 1200;
/** 小動作的間隔下限、範圍（毫秒）：每人 7～11 秒一次。 */
export const FIDGET_EVERY_MIN = 7000;
export const FIDGET_EVERY_SPAN = 4000;
/** 小動作強度的量化級數。 */
export const FIDGET_LEVELS = 4;

export type FidgetId = "glance" | "stretch";
export const FIDGET_IDS: readonly FidgetId[] = ["glance", "stretch"];

/** 小動作的最大姿勢（側面欄位與正面、背面欄位都給；畫的時候照朝向取用）。 */
export const FIDGETS: Readonly<Record<FidgetId, Readonly<InkPose>>> = {
  // 左右張望：重心換腳、手輕擺
  glance: Object.freeze({ lean: -0.06, arm: 0.25, armF: -0.2, armL: 1.2, armR: -1, liftR: 1.2 }),
  // 伸懶腰：雙手往上抬、身體往上拉
  stretch: Object.freeze({ lean: -0.1, arm: -0.8, elbow: -0.5, armF: -0.6, elbowF: -0.4, bob: -0.6, armL: -3.5, armR: -3.5 }),
};

/** FNV-1a 32 位元雜湊（無號）；確定性，跨執行相同。 */
export function idHash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return h >>> 0;
}

/** 這個人的呼吸相位（0～1）。 */
export function breathPhase(id: string): number {
  return (idHash(id) % 1000) / 1000;
}

/** 呼吸在 `ms` 時頭頂往上的位移（虛擬像素，0～BREATH_PX 之間來回；t ＝ 0、相位 0 時 ＝ 0）。 */
export function breathAt(id: string, ms: number): number {
  const u = ms / BREATH_MS + breathPhase(id);
  return BREATH_PX * 0.5 * (1 - Math.cos(u * Math.PI * 2));
}

/** 呼吸的垂直縮放倍率（以腳底為軸；1 ＝ 不變）。 */
export function breathScale(id: string, ms: number): number {
  return 1 + breathAt(id, ms) / BREATH_HEIGHT;
}

/** 這個人兩次小動作的間隔（毫秒）與第一次的偏移。 */
export function fidgetSchedule(id: string): { every: number; offset: number } {
  const h = idHash(id);
  const every = FIDGET_EVERY_MIN + ((h >>> 10) % FIDGET_EVERY_SPAN);
  return { every, offset: (h >>> 3) % every };
}

/** `ms` 時的小動作：哪一個、強度（已量化，0 ＝ 沒有）。 */
export function fidgetAt(id: string, ms: number): { id: FidgetId; level: number } | null {
  if (!(ms >= 0)) return null;
  const { every, offset } = fidgetSchedule(id);
  const local = ms + every - offset; // 第一次在 offset 毫秒之後
  const n = Math.floor(local / every);
  const into = local - n * every;
  if (n < 1 || into >= FIDGET_MS) return null;
  const k = Math.sin((into / FIDGET_MS) * Math.PI);
  const level = Math.round(k * FIDGET_LEVELS) / FIDGET_LEVELS;
  if (level <= 0) return null;
  const which = FIDGET_IDS[((idHash(id) >>> 16) + n) % FIDGET_IDS.length]!;
  return { id: which, level };
}

/** 一個人在 `ms` 時的待機畫面：呼吸縮放、小動作的骨架姿勢（沒有時 `null`，照站好的貼圖）與快取鍵。 */
export interface IdleFrame {
  scaleY: number;
  pose: InkPose | null;
  /** 姿勢的識別（換貼圖用；沒有小動作時 ""）。 */
  key: string;
}

export function idleFrame(id: string, ms: number): IdleFrame {
  const f = fidgetAt(id, ms);
  if (f === null) return { scaleY: breathScale(id, ms), pose: null, key: "" };
  return { scaleY: breathScale(id, ms), pose: quantizePose(scalePose(FIDGETS[f.id], f.level)), key: `${f.id}:${f.level}` };
}
