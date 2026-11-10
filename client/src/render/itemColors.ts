// 裝備顏色解析：paperdoll（C 畫法）與 qSpec（Q 版）共用，獨立成檔以解開兩者的執行期環（PERF-4b S3）。
import { elementTint, type GearItem } from "./appearance";
import { mix } from "./color";
import { MATERIAL } from "./material";

function darker(c: string, f = 0.68): string {
  return mix(c, "#000000", 1 - f);
}

/** 一件裝備的 [主色, 暗色]：指定顏色或材質色（不認得 → 布料色），有元素時混入元素色 45%。 */
export function itemColors(item: GearItem): [string, string] {
  const base = MATERIAL[item.material ?? "cloth"] ?? MATERIAL.cloth!;
  let [main, dark]: [string, string] = item.color !== undefined ? [item.color, darker(item.color)] : [base[0], base[1]];
  const tint = elementTint(item.element);
  if (tint !== undefined) {
    main = mix(main, tint, 0.45);
    dark = mix(dark, tint, 0.3);
  }
  return [main, dark];
}
