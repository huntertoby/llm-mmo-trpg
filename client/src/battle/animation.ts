// 事件播放計畫（純函式）：`steps` → 依序的移動動畫。其他事件先不做動畫；播放完以 `view` 為準。
import { asEvent, isUnitMoved, type MoveMode, type Pos, type StepOut } from "../api/types";

export interface MoveAnim {
  unitId: string;
  from: Pos;
  to: Pos;
  mode: MoveMode;
  /** 毫秒；`teleport` 為 0（直接出現在新位置）。 */
  durationMs: number;
}

export const MOVE_DURATION_MS: Readonly<Record<MoveMode, number>> = {
  walk: 140,
  forced: 70,
  teleport: 0,
};

export function movePlan(steps: readonly StepOut[]): MoveAnim[] {
  const plan: MoveAnim[] = [];
  for (const step of steps) {
    for (const raw of step.events) {
      const event = asEvent(raw);
      if (!isUnitMoved(event)) continue;
      plan.push({
        unitId: event.unit_id,
        from: event.from_pos,
        to: event.to_pos,
        mode: event.mode,
        durationMs: MOVE_DURATION_MS[event.mode],
      });
    }
  }
  return plan;
}

/** 線性內插（`t` 0–1）。 */
export function lerpPos(from: { x: number; y: number }, to: { x: number; y: number }, t: number) {
  const k = Math.max(0, Math.min(1, t));
  return { x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k };
}
