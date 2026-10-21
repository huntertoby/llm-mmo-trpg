// 部件說明框的狀態與位置（Phase 3-18a）：滑鼠移上去顯示、點一下釘住、點外面或 Esc 關閉（觸控也能用）。
// 純函式，不碰 DOM；`PartTip.tsx` 負責接事件與量測。

export interface TipState {
  /** 滑鼠在部件上。 */
  hover: boolean;
  /** 點一下釘住。 */
  pinned: boolean;
}

export type TipEvent = "enter" | "leave" | "click" | "escape" | "outside";

export const TIP_CLOSED: TipState = { hover: false, pinned: false };

export function tipReduce(state: TipState, event: TipEvent): TipState {
  switch (event) {
    case "enter":
      return { ...state, hover: true };
    case "leave":
      return { ...state, hover: false };
    case "click":
      // 釘住時再點一下取消；沒釘住就釘住（觸控沒有滑過，點一下就顯示）
      return { hover: state.hover, pinned: !state.pinned };
    case "escape":
    case "outside":
      return TIP_CLOSED;
  }
}

export const tipVisible = (state: TipState): boolean => state.hover || state.pinned;

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * 說明框的位置（`position: fixed` 用的 left／top）：優先放在部件上方並水平置中，放不下就改放下方，
 * 再用視窗邊界夾住，不可超出視窗。
 */
export function tipPlacement(
  anchor: Box,
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  gap = 6,
  margin = 4,
): { left: number; top: number } {
  const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(v, Math.max(lo, hi)));
  let top = anchor.top - size.height - gap;
  if (top < margin) top = anchor.top + anchor.height + gap;
  const left = anchor.left + anchor.width / 2 - size.width / 2;
  return {
    left: clamp(left, margin, viewport.width - size.width - margin),
    top: clamp(top, margin, viewport.height - size.height - margin),
  };
}
