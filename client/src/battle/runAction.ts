// 跑步（Phase 3-20，玩法 #22；純函式）：行動面板「跑步」按鈕的狀態與原因，以及跑步預覽的移動範圍。
// 合法時引擎的 `legal_actions` 有 `run`；不合法時原因來自 API 的 `run_option`（已經跑過了、被定身、AP 不足）。
import type { Pos, PreviewOut, RunOption } from "../api/types";
import type { ActionMode } from "./targeting";

export interface RunButton {
  /** 可以按（有合法的跑步動作）。 */
  enabled: boolean;
  /** 不能按的原因（中文）；可以按時 `null`。 */
  reason: string | null;
}

const FALLBACK_REASON = "目前不能跑步";

/** 按鈕狀態：有跑步模式就能按；否則灰掉，原因取 `run_option.reason`（沒有資料時用通用說明）。 */
export function runButton(mode: ActionMode | null, option: RunOption | null | undefined): RunButton {
  if (mode !== null) return { enabled: true, reason: null };
  return { enabled: false, reason: option?.reason ?? FALLBACK_REASON };
}

/** 滑過「跑步」時的預覽：跑完之後本回合能走到的格子（不是跑步預覽時為空）。 */
export function runRangeTiles(preview: PreviewOut | null): Pos[] {
  if (preview === null || preview.action.type !== "run") return [];
  return (preview.run_range ?? []).map(([x, y]) => ({ x: x as number, y: y as number }));
}
