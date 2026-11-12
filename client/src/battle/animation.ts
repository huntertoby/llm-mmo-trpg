// 事件播放計畫（純函式）：`steps` → 依序的移動動畫。其他事件先不做動畫；播放完以 `view` 為準。
import type { PrimitiveClipId } from "../render/skillClips";
import type { DashRoute, LeapArc } from "../render/skillVariants";
import { asEvent, isUnitMoved, type MoveMode, type Pos, type StepOut, type UnitMovedEvent } from "../api/types";

export interface MoveAnim {
  unitId: string;
  from: Pos;
  to: Pos;
  mode: MoveMode;
  /** 毫秒（已依播放速度縮放）。 */
  durationMs: number;
  /** `slide` 滑動到新格；`fade` 原地淡出、在新格淡入（傳送、交換）。 */
  style: MoveStyle;
  /** 位移途中的身體片段（6N-2：衝刺、跳躍、傳送、被推、被拉…；`render/skillClips.ts`）；沒有＝照舊。 */
  clip?: PrimitiveClipId;
  /** 技能變體（6N-8）：衝刺的路線（`dash_lean`）；沒有＝直線。起訖格不變。 */
  route?: DashRoute;
  /** 技能變體（6N-8）：跳躍的弧度（`leap_air`）；沒有＝原本的低弧。起訖格不變。 */
  hop?: LeapArc;
  /** CB-2b：異形施放者的傳送：這段位移播異形的閃現片段（`durationMs` 已是片段長度）。 */
  creatureBlink?: true;
  /** BAL-21c：閃現片段整段都在終點播（頭目的瞬步殘影）；沒有＝CB-2b 的前半原地淡出、後半新格淡入。 */
  creatureBlinkAt?: "to";
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
  slide: "slide",
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
  slide: 70, // 冰面滑行的一格（#123；平常由走路動畫的滑行片段播）
};

/** 一個 `unit_moved` → 位移動畫；`scale`：播放速度的時間倍率（正常 1、快 0.5；0 ＝ 不播動畫）。 */
export function moveAnimOf(event: UnitMovedEvent, scale = 1): MoveAnim {
  return {
    unitId: event.unit_id,
    from: event.from_pos,
    to: event.to_pos,
    mode: event.mode,
    durationMs: Math.round(MOVE_DURATION_MS[event.mode] * scale),
    style: MOVE_STYLE[event.mode],
    // 6R-1c：沒有技能卡的跳躍（種族技「獸躍」）也播跳躍片段（離地弧度），不再平移滑過去；技能的跳躍由 `placeMotions` 照原語換成同一個片段
    ...(event.mode === "leap" ? { clip: "leap_air" as const } : {}),
  };
}

/** 所有位移各自一段（戰鬥播放的走路改用 `walkAnim.ts` 的逐格時間軸，見 6A-4d）。 */
export function movePlan(steps: readonly StepOut[], scale = 1): MoveAnim[] {
  const plan: MoveAnim[] = [];
  for (const step of steps) {
    for (const raw of step.events) {
      const event = asEvent(raw);
      if (isUnitMoved(event)) plan.push(moveAnimOf(event, scale));
    }
  }
  return plan;
}

/** 線性內插（`t` 0–1）。 */
/**
 * 移動動畫途中單位該放在哪一排的圖層（戰場由北往南一排一排畫，南邊的排蓋住北邊）：取單位當下跨過的兩排中
 * **較南** 的那一排，腳下的地板與崖面才不會蓋住人（使用者回報「移動中陷進地板」）。`t` 為 0～1。
 */
export function rowDuringMove(fromY: number, toY: number, t: number): number {
  const k = Math.max(0, Math.min(1, t));
  return Math.ceil(fromY + (toY - fromY) * k - 1e-9);
}

export function lerpPos(from: { x: number; y: number }, to: { x: number; y: number }, t: number) {
  const k = Math.max(0, Math.min(1, t));
  return { x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k };
}
