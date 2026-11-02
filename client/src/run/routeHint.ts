// 創角時「關鍵字與屬性不搭」的提示（BAL-19g，06 6.27.3，#110）：後端依武器與選的關鍵字算出哪些屬性跟得上
// （`fits`）與提示文字；這裡只判斷配點後的最高屬性在不在 `fits` 裡。只提示、不擋。
import type { AttributeId, RouteHint } from "../api/types";
import { ATTRIBUTES, allocationTotal, type Allocation } from "./flow";

/** 配點後的最高屬性；同分取六屬性順序在前的（和後端 `top_attribute` 相同）。 */
export function topAttribute(base: Readonly<Record<AttributeId, number>>, alloc: Allocation): AttributeId {
  let best: AttributeId = "str";
  let value = -Infinity;
  for (const a of ATTRIBUTES) {
    const v = (base[a.id] ?? 0) + (alloc[a.id] ?? 0);
    if (v > value) {
      best = a.id;
      value = v;
    }
  }
  return best;
}

/** 要顯示的提示文字；還沒配點、沒有提示或最高屬性跟得上時為 `null`。 */
export function routeHintText(
  hint: RouteHint | null | undefined,
  base: Readonly<Record<AttributeId, number>>,
  alloc: Allocation,
): string | null {
  if (hint == null || allocationTotal(alloc) === 0) return null;
  return hint.fits.includes(topAttribute(base, alloc)) ? null : hint.text_zh;
}
