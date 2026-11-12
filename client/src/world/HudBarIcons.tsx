// HUD 功能列的 8 個圖示（Phase 6A-4f 定稿；QI-5 換 Q 版）：I 背包、K 技能、G 成長、J 任務、Y 影子、N 留言、R 潛行（#120 21.4 取代趕路）、M 地圖。
// QI-5（docs/art/Q版小圖示-HUD移植需求.md）：改畫 Q 版 canvas（畫法 `render/qIcon/hud.ts`，經 `render/hudIcon.ts` 快取）。
// 淺色圓底（RT-3b：所有工具列圖示一律墊同一個圓底，半徑 15.5/48）照留、畫在畫布最底層；圖樣佔 74%，可以畫到圓底外面（需求 3 第 1 點）。
// 畫布寬高＝顯示 × 2、CSS 不縮放。舊的墨線 SVG（`Ink`／`Line`／`smoothPath`）QI-5 已刪。
import { BAR_ICON_ID } from "../render/hudIcon";
import { BACKING, BACKING_EDGE, BACKING_R } from "../render/qIcon/hud";
import { HudGlyph } from "../ui/HudGlyph";

export type HudBarKey = "I" | "K" | "G" | "J" | "Y" | "N" | "R" | "M";

/** 潛行圖示的淺色圓底（6F-7）。 */
export const SNEAK_MOON = BACKING;
/** RT-3b：所有工具列圖示的淺色圓底（和 6F-7 的潛行月光同色）、細框與半徑（48 格畫布，圓在 8～40 之內）。 */
export const HUD_BACKING = SNEAK_MOON;
export const HUD_BACKING_EDGE = BACKING_EDGE;
export const HUD_BACKING_R = BACKING_R;

const NAME: Record<HudBarKey, string> = { I: "背包", K: "技能", G: "成長", J: "任務", Y: "影子", N: "留言", R: "潛行", M: "地圖" };

/** 樣張的順序：I K G J Y N R M。 */
export const HUD_BAR_ORDER: readonly HudBarKey[] = ["I", "K", "G", "J", "Y", "N", "R", "M"];

export function hudBarName(key: HudBarKey): string {
  return NAME[key];
}

/** 功能列的圖示（Q 版 canvas，`size`＝顯示邊長：功能列鈕 35、影子 27、地圖 23、說明卡標題 24）。 */
export function HudBarIcon({ k, size = 25 }: { k: HudBarKey; size?: number }) {
  return <HudGlyph id={BAR_ICON_ID[k]} px={size} className="hud-icon hud-bar-icon" data={{ "data-bar-icon": k }} />;
}
