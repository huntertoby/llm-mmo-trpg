// 逐步播放計畫（純函式）：回應的 `steps` → 一格一格的畫面。
// 每一步的順序固定為：標示行動中的單位 → 該步的移動動畫 → 技能特效（蓄力與飛行，等到命中）→
// 畫該步的 `view` → 地圖回饋 → 加入該步的紀錄 → 停頓。
// 最後一定以 `res.view` 為準（播放只是過場）。
import type { BattleResponse, BattleView } from "../api/types";
import { movePlan, type MoveAnim } from "./animation";
import { feedbackFor, type FeedbackItem } from "./feedback";
import { logLines, type LogLine } from "./log";
import { unitNames } from "./units";
import { isEmptyVfx, scaleVfx, vfxFor, VFX_TIMING, type StepVfx, type VfxCards } from "./vfx";

export type PlaySpeed = "slow" | "normal" | "fast" | "skip";

/** 顯示順序：慢、正常、快、略過。 */
export const PLAY_SPEEDS: readonly PlaySpeed[] = ["slow", "normal", "fast", "skip"];

/** 慢速的時間倍率（正常的 2 倍時間；動畫、地圖回饋與停頓都用它）。 */
export const SLOW_FACTOR = 2;

/** 動畫時間的倍率：慢 ＝ 2 倍；快 ＝ 一半；略過不播動畫。 */
export const SPEED_SCALE: Readonly<Record<PlaySpeed, number>> = { slow: SLOW_FACTOR, normal: 1, fast: 0.5, skip: 0 };
/** 地圖回饋（浮動數字、連線）的基準時間（毫秒），乘上 `SPEED_SCALE`。 */
export const FEEDBACK_MS = 1000;

/** 每個 AI 動作之後的停頓（毫秒）。 */
export const AI_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { slow: 500 * SLOW_FACTOR, normal: 500, fast: 150, skip: 0 };
/** AI 純移動之後的停頓（動畫本身已佔時間）。 */
export const MOVE_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { slow: 150 * SLOW_FACTOR, normal: 150, fast: 0, skip: 0 };
/** 主角自己的動作之後的停頓（短）。 */
export const HERO_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { slow: 150 * SLOW_FACTOR, normal: 150, fast: 0, skip: 0 };

export interface Frame {
  /** 行動中的單位；開場那一步為 `null`。 */
  actorId: string | null;
  moves: MoveAnim[];
  /** 地圖上的回饋項目（略過時為空）。 */
  feedback: FeedbackItem[];
  /** 回饋項目顯示的時間（毫秒，已依速度縮放）。 */
  feedbackMs: number;
  /** 技能特效（Phase 3-12；時間已依速度縮放）；沒有特效或略過時為 `null`。 */
  vfx: StepVfx | null;
  /** 命中後爆發與粒子的時間（毫秒，已依速度縮放）。 */
  vfxImpactMs: number;
  view: BattleView;
  lines: LogLine[];
  pauseMs: number;
}

export interface PlaybackPlan {
  initialView: BattleView;
  frames: Frame[];
  finalView: BattleView;
}

export type PlayOp =
  | { op: "mark"; unitId: string | null }
  | { op: "move"; anim: MoveAnim }
  | { op: "vfx"; vfx: StepVfx; impactMs: number }
  | { op: "view"; view: BattleView }
  | { op: "feedback"; items: FeedbackItem[]; durationMs: number }
  | { op: "log"; lines: LogLine[] }
  | { op: "pause"; ms: number };

function pauseFor(stepType: string | undefined, actorId: string | null, heroId: string, speed: PlaySpeed): number {
  if (actorId === null || stepType === "end_turn") return 0;
  if (actorId === heroId) return HERO_PAUSE_MS[speed];
  // 純移動的步驟已有移動動畫的時間，停頓縮短（一個單位常有「移動、攻擊、移動」好幾步）。
  return stepType === "move" ? MOVE_PAUSE_MS[speed] : AI_PAUSE_MS[speed];
}

function stepVfx(events: readonly Record<string, unknown>[], view: BattleView, cards: VfxCards, scale: number): StepVfx | null {
  const vfx = vfxFor(events, view, cards);
  return isEmptyVfx(vfx) ? null : scaleVfx(vfx, scale);
}

/** `cards`：技能 ID → 技能卡（推導技能特效的形狀用；缺的技能以影響的格子推斷）。 */
export function playbackPlan(res: BattleResponse, heroId: string, speed: PlaySpeed, cards: VfxCards = {}): PlaybackPlan {
  if (speed === "skip" || res.steps.length === 0) {
    const lines = logLines(res.steps, unitNames(res.view));
    const frames: Frame[] =
      res.steps.length === 0
        ? []
        : [{ actorId: null, moves: [], feedback: [], feedbackMs: 0, vfx: null, vfxImpactMs: 0, view: res.view, lines, pauseMs: 0 }];
    return { initialView: res.initial_view, frames, finalView: res.view };
  }
  const frames = res.steps.map<Frame>((step) => ({
    actorId: step.actor_id,
    moves: movePlan([step], SPEED_SCALE[speed]),
    feedback: feedbackFor(step.events, step.view),
    feedbackMs: Math.round(FEEDBACK_MS * SPEED_SCALE[speed]),
    vfx: stepVfx(step.events, step.view, cards, SPEED_SCALE[speed]),
    vfxImpactMs: Math.round(VFX_TIMING.impact * SPEED_SCALE[speed]),
    view: step.view,
    lines: logLines([step], unitNames(step.view)),
    pauseMs: pauseFor(step.step?.type, step.actor_id, heroId, speed),
  }));
  return { initialView: res.initial_view, frames, finalView: res.view };
}

/** 一格畫面要依序做的事。 */
export function frameOps(frame: Frame): PlayOp[] {
  const ops: PlayOp[] = [{ op: "mark", unitId: frame.actorId }];
  for (const anim of frame.moves) ops.push({ op: "move", anim });
  if (frame.vfx !== null) ops.push({ op: "vfx", vfx: frame.vfx, impactMs: frame.vfxImpactMs });
  ops.push({ op: "view", view: frame.view });
  if (frame.feedback.length > 0) ops.push({ op: "feedback", items: frame.feedback, durationMs: frame.feedbackMs });
  if (frame.lines.length > 0) ops.push({ op: "log", lines: frame.lines });
  if (frame.pauseMs > 0) ops.push({ op: "pause", ms: frame.pauseMs });
  return ops;
}

/** 從第 `from` 格開始的所有紀錄（中途按「略過」時一次補上）。 */
export function remainingLines(plan: PlaybackPlan, from: number): LogLine[] {
  return plan.frames.slice(from).flatMap((f) => f.lines);
}
