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

/** 「圖例」彈出面板的固定說明（Phase 3-8）：戰場上常見的顏色與標記。 */
export const BASE_LEGEND: readonly LegendEntry[] = [
  { color: HIGHLIGHT.move, label: "可移動的格子" },
  { color: HIGHLIGHT.attack, label: "可攻擊／可選的目標（紅框）" },
  { color: HIGHLIGHT.preview, label: "預覽的影響範圍" },
  { color: HIGHLIGHT.direction, label: "方向格（附箭頭）；黃圈＝行動中的單位" },
  { color: HIGHLIGHT.hero, label: "白圈＝主角" },
  { color: HIGHLIGHT.trigger, label: "反應詢問的觸發者（洋紅雙框）" },
  { color: HIGHLIGHT.followup, label: "複合技能第二段的範圍" },
  { color: HIGHLIGHT.summon, label: "召喚物（菱形）與圖騰光環" },
  { color: HIGHLIGHT.exit, label: "出口格「出」：我方單位走上去即撤離（撤離任務）" },
  { color: HIGHLIGHT.point, label: "守點格「守」：守住指定回合數（守點任務）" },
  { color: HIGHLIGHT.well, label: "源泉格「源」：走上去源力 +1" },
  { color: HIGHLIGHT.deadly, label: "致命地形（叉叉）" },
  { color: HIGHLIGHT.burning, label: "燃燒中的物件" },
  { color: HIGHLIGHT.trap, label: "我方陷阱 ^（被揭露的敵方陷阱 × 為紅色）" },
  { color: HIGHLIGHT.zone_harmful, label: "有害的持續區域" },
  { color: HIGHLIGHT.zone_helpful, label: "有益的持續區域" },
  { color: HIGHLIGHT.zone_neutral, label: "不影響我方的持續區域（虛線、淡底色）" },
];

export function cssColor(color: number): string {
  return `#${color.toString(16).padStart(6, "0")}`;
}
