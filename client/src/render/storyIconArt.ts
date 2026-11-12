// 事件卡與情境判定的小圖示（Phase 6C-ART3 起；QI-6 換成 Q 版第⑧批，畫法在 `qIcon/event.ts`，需求 docs/art/Q版小圖示-事件卡移植需求.md）。
// 框不動：選項、其他、六屬性是深底（CHIP_BG）加圖示色的圓環（線寬 max(1.2, 6%)），圖樣裁在圓環內緣；d20 沒有框。
// 依大小畫成離屏圖（畫布＝顯示 × dpr，圖樣對齊整數裝置像素）、轉成圖片網址快取（和 portrait.ts 同做法）；沒有 DOM 時回傳 null。
// QI-6 拿掉的舊墨線畫法：SOLUTION_ART、MISC_ART、ATTR_ART、drawD20、drawChip（沒有其他呼叫處）。
import type { Ctx } from "./artDraw";
import * as QE from "./qIcon/event";
import type { AttrKey, SolutionIcon } from "../world/narration";

/** 圓環裡的深底（框不動）。 */
export const CHIP_BG = QE.CHIP_BG;
/** d20 平常的顏色、大成功（金）、大失敗（灰）。 */
export const D20_COLOR = { normal: "#f2e6c8", crit: "#ffe08a", fumble: "#c8c0b8" } as const;
/** 64px 以上才寫點數（需求：64 寫點數，28 以下不寫字）。 */
export const D20_TEXT_MIN = 29;
/** d20 點數的字高、外圈色、外圈寬（6Q-1；QI-6 起常數放在 `qIcon/event.ts`，值不變）。 */
export const D20_FONT_PX = QE.D20_FONT_PX;
export const D20_HALO = QE.D20_HALO;
export const D20_HALO_W = QE.D20_HALO_W;

export type MiscIcon = "clue" | "model_off" | "narrator" | "info" | "thread";

/** 圓環色（`qIcon/event.ts` 的 ICON 表，現行原值；框不動）。 */
export const ringOf = (id: SolutionIcon | MiscIcon | AttrKey): string => QE.ICON[id]?.ring ?? "";

/** d20 該不該寫字：只有大圖（29px 以上）才寫。 */
export const d20ShowsValue = (size: number): boolean => size >= D20_TEXT_MIN;

/** 擲骰用的那顆的顏色：自然 20 金、自然 1 灰，其他照結果色。 */
export function usedDieColor(face: number, outcomeColor: string): string {
  if (face === 20) return D20_COLOR.crit;
  if (face === 1) return D20_COLOR.fumble;
  return outcomeColor;
}

export type StoryIconSpec =
  | { kind: "solution"; icon: SolutionIcon }
  | { kind: "misc"; icon: MiscIcon }
  | { kind: "attr"; attr: AttrKey }
  | { kind: "d20"; value?: number | string; color?: string };

/** 畫一個圖示到 ctx（左上角在原點、大小 size；ctx 每單位 res 個裝置像素、原點在整數像素上）。 */
export function drawStoryIcon(c: Ctx, spec: StoryIconSpec, size: number, res = 2): void {
  switch (spec.kind) {
    case "solution":
    case "misc":
      QE.paint(c, spec.icon, size, res);
      return;
    case "attr":
      QE.paint(c, spec.attr, size, res);
      return;
    case "d20":
      QE.paint(c, "d20", size, res, { color: spec.color ?? D20_COLOR.normal, value: d20ShowsValue(size) ? spec.value : undefined });
      return;
  }
}

/** 快取鍵（種類、圖示、大小、d20 的點數與顏色；小 d20 不寫字，點數不進鍵）。 */
export function storyIconKey(spec: StoryIconSpec, size: number): string {
  switch (spec.kind) {
    case "solution":
    case "misc":
      return `${spec.kind}|${spec.icon}|${size}`;
    case "attr":
      return `attr|${spec.attr}|${size}`;
    case "d20":
      return `d20|${d20ShowsValue(size) ? String(spec.value ?? "") : ""}|${spec.color ?? D20_COLOR.normal}|${size}`;
  }
}

const cache = new Map<string, string>();

/** 圖示的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。畫布＝size × dpr（Q 版圖樣照這個解析度出圖、對齊整數裝置像素）。 */
export function storyIconUrl(spec: StoryIconSpec, size: number, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${storyIconKey(spec, size)}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = Math.ceil(size * dpr);
  c.height = Math.ceil(size * dpr);
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawStoryIcon(ctx, spec, size, dpr);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}

/** 快取裡的張數（測試用）。 */
export const storyIconCacheSize = (): number => cache.size;
