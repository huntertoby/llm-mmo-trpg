// 把內容放進 `PopupFrame slots` 的上（`head`）或下（`foot`）固定區插槽（FL-1b：選變體的標頭與確定列）。
// 不是彈出層：插槽在同一個框裡（`ui-popup-head`／`ui-popup-foot`），只是不跟著捲動區捲。PopupFrame 本身不用 portal
// （`floatCardRule.test.ts` UI-E2），所以 portal 放在這個檔。插槽還沒掛上時不畫（下一次重繪就到位）。
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import type { PopupSlots } from "./PopupFrame";

export function PopupSlot({ slots, where, children }: { slots: PopupSlots; where: "head" | "foot"; children: ReactNode }) {
  const el = slots[where];
  return el === null ? null : createPortal(children, el);
}
