// 戰場上的顏色圖例（Phase 3-5c-2）：複合技能（位移 → 動作）的第二段範圍是紫色，沒有說明就看不懂。
import { HIGHLIGHT } from "./glossary";
import type { Overlay } from "./scenePreview";
import type { ActionMode } from "./targeting";

export interface LegendEntry {
  /** 色塊顏色（0xRRGGBB）。 */
  color: number;
  label: string;
}

/** 目前畫面上需要說明的顏色：複合技能預覽或兩段選取中才有。 */
export function legendEntries(overlays: readonly Overlay[], mode: ActionMode | null): LegendEntry[] {
  const hasSecond = overlays.some((o) => o.kind === "followup_area");
  const composing = mode?.targets.composite != null;
  if (!hasSecond && !composing) return [];
  return [
    { color: HIGHLIGHT.attack, label: "可選的落點或目標" },
    { color: HIGHLIGHT.preview, label: "第一段（位移）影響的格子" },
    { color: HIGHLIGHT.followup, label: "第二段（動作）的範圍" },
  ];
}

export function cssColor(color: number): string {
  return `#${color.toString(16).padStart(6, "0")}`;
}
