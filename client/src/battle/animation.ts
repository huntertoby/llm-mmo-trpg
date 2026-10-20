// 事件播放計畫（純函式）：`steps` → 依序的移動動畫。其他事件先不做動畫；播放完以 `view` 為準。
import { asEvent, isUnitMoved, type MoveMode, type Pos, type StepOut } from "../api/types";

export interface MoveAnim {
  unitId: string;
  from: Pos;
  to: Pos;
  mode: MoveMode;
  /** 毫秒（已依播放速度縮放）。 */
  durationMs: number;
  /** `slide` 滑動到新格；`fade` 原地淡出、在新格淡入（傳送、交換）。 */
  style: MoveStyle;
}

export type MoveStyle = "slide" | "fade";

/** 位移的表現：推、拉、衝鋒、跳躍用滑動，傳送、交換用淡出淡入（Phase 3-9a）。 */
export const MOVE_STYLE: Readonly<Record<MoveMode, MoveStyle>> = {
  walk: "slide",
  forced: "slide",
  dash: "slide",
  leap: "slide",
  teleport: "fade",
  teleported: "fade",
  swap: "fade",
  shadowstep: "fade",
};

export const MOVE_DURATION_MS: Readonly<Record<MoveMode, number>> = {
  walk: 140,
  forced: 70,
  teleport: 260, // 淡出再淡入
  teleported: 260, // 被傳送他人（Phase 3D-2b）
  dash: 60, // 衝鋒每一步：比步行快
  leap: 220, // 跳躍：一次跳到落點
  swap: 260, // 交換位置：兩個單位依序淡出淡入
  shadowstep: 200, // 瞬步（Phase 3D-8d）：淡出後出現在目標身旁
};

/** `scale`：播放速度的時間倍率（正常 1、快 0.5；0 ＝ 不播動畫）。 */
export function movePlan(steps: readonly StepOut[], scale = 1): MoveAnim[] {
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
        durationMs: Math.round(MOVE_DURATION_MS[event.mode] * scale),
        style: MOVE_STYLE[event.mode],
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
