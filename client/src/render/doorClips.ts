// 進出門、換地圖的片段（Phase 6M-4；需求 docs/art/動畫移植需求.md 第 4 節）。純函式：時間 → 小人的縮放、透明、位移與走路姿勢。
// 時間軸（和 6B-3 的畫面淡出淡入銜接；畫面淡出、淡入各 `STAGE_FADE_MS`，同 world.css 的 0.22 秒）：
//   離開：小人片段 `LEAVE_MS`；畫面在片段開始後 `FADE_LEAD_MS` 開始淡出 → 淡完才換地圖。
//   抵達：換好地圖後畫面淡入，同時小人播抵達片段 `ARRIVE_MS`。
//   總長 ＝ FADE_LEAD_MS ＋ STAGE_FADE_MS ＋ max(STAGE_FADE_MS, ARRIVE_MS) ＝ 80 ＋ 220 ＋ 220 ＝ 520 毫秒（≤ 600）。
// - 進門：轉身朝門（＝走進門格的方向），往門裡縮小（1 → 0.6）、往上移 6、淡出；出門：反過來（0.6 → 1、淡入）。
// - 邊緣出口：照走的方向再走半格並淡出；新地圖從對面入口外一格走進來一步並淡入（走路片段接續相位）。
import type { Facing } from "../api/types";
import { gaitPose, quantizePhase, quantizePose, tilePhase } from "./motionClips";
import type { InkPose } from "./inkPose";

export type TransitKind = "door" | "edge";

/** 畫面淡出／淡入的時間（毫秒；同 world.css `.world-field-stage` 的 transition 0.22s）。 */
export const STAGE_FADE_MS = 220;
/** 小人離開片段的長度。 */
export const LEAVE_MS = 200;
/** 畫面在離開片段開始後多久開始淡出（兩者重疊，不拉長總時間）。 */
export const FADE_LEAD_MS = 80;
/** 小人抵達片段的長度（和畫面淡入同時播）。 */
export const ARRIVE_MS = 220;
/** 進門縮小到的比例、往門裡（上）移的距離（模型像素）。 */
export const DOOR_SHRINK = 0.6;
export const DOOR_RISE = 6;
/** 邊緣出口走出去的距離（格）。 */
export const EDGE_OUT_TILES = 0.5;

/** 換地圖整段的時間（毫秒）：小人片段＋畫面淡出（重疊）＋畫面淡入（和抵達片段重疊）。 */
export function transitTotalMs(): number {
  return Math.max(LEAVE_MS, FADE_LEAD_MS + STAGE_FADE_MS) + Math.max(STAGE_FADE_MS, ARRIVE_MS);
}

const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const easeIn = (t: number): number => clamp(t) * clamp(t);
const easeOut = (t: number): number => 1 - (1 - clamp(t)) ** 2;

/** 方向 → 一格的位移。 */
export function facingStep(f: Facing): { x: number; y: number } {
  return f === "east" ? { x: 1, y: 0 } : f === "west" ? { x: -1, y: 0 } : f === "south" ? { x: 0, y: 1 } : { x: 0, y: -1 };
}

/** 片段某一刻的小人：縮放、透明、相對格子中心的位移（格為單位）、紙娃娃姿勢（`null` ＝ 站好）。 */
export interface TransitFrame {
  scale: number;
  alpha: number;
  /** 相對所在格中心的位移（格）。 */
  dx: number;
  dy: number;
  /** 往上的位移（模型像素）。 */
  rise: number;
  pose: InkPose | null;
}

/** 離開的片段（`u` 0～1）。 */
export function leaveFrame(kind: TransitKind, facing: Facing, u: number): TransitFrame {
  const k = clamp(u);
  if (kind === "door") {
    const e = easeIn(k);
    return { scale: 1 - (1 - DOOR_SHRINK) * e, alpha: 1 - e, dx: 0, dy: 0, rise: DOOR_RISE * e, pose: null };
  }
  const s = facingStep(facing);
  const pose = quantizePose(gaitPose(quantizePhase(tilePhase(0, k * EDGE_OUT_TILES * 2)), "walk"));
  return { scale: 1, alpha: 1 - easeIn(k), dx: s.x * EDGE_OUT_TILES * k, dy: s.y * EDGE_OUT_TILES * k, rise: 0, pose };
}

/** 抵達的片段（`u` 0～1）：出門＝從門裡長出來；邊緣入口＝從外面一格走進來一步。 */
export function arriveFrame(kind: TransitKind, facing: Facing, u: number): TransitFrame {
  const k = clamp(u);
  if (kind === "door") {
    const e = easeOut(k);
    return { scale: DOOR_SHRINK + (1 - DOOR_SHRINK) * e, alpha: e, dx: 0, dy: 0, rise: DOOR_RISE * (1 - e), pose: null };
  }
  const s = facingStep(facing);
  const pose = k >= 1 ? null : quantizePose(gaitPose(quantizePhase(tilePhase(1, k)), "walk"));
  return { scale: 1, alpha: easeOut(clamp(k * 2)), dx: -s.x * (1 - k) + 0, dy: -s.y * (1 - k) + 0, rise: 0, pose }; // +0：不要 -0
}
