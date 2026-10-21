// 特效配色的查表（3-18b）：元素、支援、水、通用預設走 `battle/vfxPalette`；`status:<id>`（無傷害技能依施加的
// 狀態上色）取技能部件庫的狀態色（`skillParts.statusColor`），與技能圖示、狀態列用同一份顏色。
import { colorVfx, elementVfx, statusOfVfxKey, type ElementVfx } from "../battle/vfxPalette";
import { statusColor } from "./skillParts";

export function paletteOf(key: string): ElementVfx {
  const status = statusOfVfxKey(key);
  return status === null ? elementVfx(key) : colorVfx(statusColor(status));
}
