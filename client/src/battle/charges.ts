// 裝備充能（Phase 3G-G3a）：HUD 與單位資訊顯示層數，滿足啟動需求時提示可以從「更多動作」啟動。
import type { ChargeView } from "../api/types";

/** 層數的格子：依裝備版上限一格一層，已累積的為 `true`（HUD 畫成實心）。 */
export function chargePips(charge: Pick<ChargeView, "stacks" | "max_stacks">): boolean[] {
  return Array.from({ length: Math.max(0, charge.max_stacks) }, (_, i) => i < charge.stacks);
}

/** 一行文字：`靜電 2/3（啟動：3 層＋1 AP）`；層數足夠時改為「可啟動」。 */
export function chargeText(charge: ChargeView): string {
  const cost = `${charge.cost_stacks} 層${charge.cost_ap > 0 ? `＋${charge.cost_ap} AP` : ""}`;
  const base = `${charge.stack_name_zh} ${charge.stacks}/${charge.max_stacks}`;
  return charge.ready ? `${base}（可啟動：${cost}）` : `${base}（啟動：${cost}）`;
}

/** 啟動按鈕在哪裡的提示（HUD 滑過文字）。 */
export function chargeHint(charge: ChargeView): string {
  const target = charge.needs_target ? "，啟動時選一個射程內的敵人" : "";
  return `${chargeText(charge)}${target}。從「更多動作」選單啟動。`;
}
