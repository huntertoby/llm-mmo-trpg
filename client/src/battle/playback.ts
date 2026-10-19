// 逐步播放計畫（純函式）：回應的 `steps` → 一格一格的畫面。
// 每一步的順序固定為：標示行動中的單位 → 該步的移動動畫 → 畫該步的 `view` → 加入該步的紀錄 → 停頓。
// 最後一定以 `res.view` 為準（播放只是過場）。
import type { BattleResponse, BattleView } from "../api/types";
import { movePlan, type MoveAnim } from "./animation";
import { logLines, type LogLine } from "./log";
import { unitNames } from "./units";

export type PlaySpeed = "normal" | "fast" | "skip";

export const PLAY_SPEEDS: readonly PlaySpeed[] = ["normal", "fast", "skip"];

/** 每個 AI 動作之後的停頓（毫秒）。 */
export const AI_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { normal: 500, fast: 150, skip: 0 };
/** AI 純移動之後的停頓（動畫本身已佔時間）。 */
export const MOVE_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { normal: 150, fast: 0, skip: 0 };
/** 主角自己的動作之後的停頓（短）。 */
export const HERO_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { normal: 150, fast: 0, skip: 0 };

export interface Frame {
  /** 行動中的單位；開場那一步為 `null`。 */
  actorId: string | null;
  moves: MoveAnim[];
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
  | { op: "view"; view: BattleView }
  | { op: "log"; lines: LogLine[] }
  | { op: "pause"; ms: number };

function pauseFor(stepType: string | undefined, actorId: string | null, heroId: string, speed: PlaySpeed): number {
  if (actorId === null || stepType === "end_turn") return 0;
  if (actorId === heroId) return HERO_PAUSE_MS[speed];
  // 純移動的步驟已有移動動畫的時間，停頓縮短（一個單位常有「移動、攻擊、移動」好幾步）。
  return stepType === "move" ? MOVE_PAUSE_MS[speed] : AI_PAUSE_MS[speed];
}

export function playbackPlan(res: BattleResponse, heroId: string, speed: PlaySpeed): PlaybackPlan {
  if (speed === "skip" || res.steps.length === 0) {
    const lines = logLines(res.steps, unitNames(res.view));
    const frames: Frame[] =
      res.steps.length === 0
        ? []
        : [{ actorId: null, moves: [], view: res.view, lines, pauseMs: 0 }];
    return { initialView: res.initial_view, frames, finalView: res.view };
  }
  const frames = res.steps.map<Frame>((step) => ({
    actorId: step.actor_id,
    moves: movePlan([step]),
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
  ops.push({ op: "view", view: frame.view });
  if (frame.lines.length > 0) ops.push({ op: "log", lines: frame.lines });
  if (frame.pauseMs > 0) ops.push({ op: "pause", ms: frame.pauseMs });
  return ops;
}

/** 從第 `from` 格開始的所有紀錄（中途按「略過」時一次補上）。 */
export function remainingLines(plan: PlaybackPlan, from: number): LogLine[] {
  return plan.frames.slice(from).flatMap((f) => f.lines);
}
