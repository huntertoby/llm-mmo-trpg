// 狀態圖示的框（Phase QI-3a A1：由 `statusIcon.ts` 原樣搬出，值與行為不變；`statusIcon.ts` re-export，既有 import 不用改）。
// 拆出來的理由：Q 版狀態圖樣 `qIcon/status.ts` 要用狀態的框，又不能 import `statusIcon.ts`（QI-3b 起 `statusIcon.ts` 要 import `qIcon/status.ts`，會循環）。
// 注意：`qIcon/skills.ts` re-export 的 `framePath` 是 `skillGlyphs.ts` 的**技能**框，不是這個。
import { statusLook } from "../battle/glossary";
import type { Ctx } from "./skillGlyphs";

const TAU = Math.PI * 2;

export type Polarity = "buff" | "debuff" | "neutral";

/** 外框色。 */
export const FRAME_COLOR: Readonly<Record<Polarity, string>> = { buff: "#3fbf6a", debuff: "#e04848", neutral: "#c8a048" };
/** 框裡的深底色（框線之前先填）。 */
export const STATUS_BASE_BG = "rgba(12,12,16,0.88)";

export const isPolarity = (p: string | undefined): p is Polarity => p === "buff" || p === "debuff" || p === "neutral";

/** 狀態的極性：沒有資料或不認得 → neutral。 */
export function polarityOf(id: string | null | undefined): Polarity {
  const p = id == null ? undefined : statusLook(id)?.polarity;
  return isPolarity(p) ? p : "neutral";
}

/** 外框形狀：buff 圓、debuff 圓角方、neutral（含姿態）六角。邊長約 2r。 */
export function framePath(ctx: Ctx, pol: Polarity, r: number): void {
  ctx.beginPath();
  if (pol === "buff") ctx.arc(0, 0, r, 0, TAU);
  else if (pol === "debuff") ctx.roundRect(-r * 0.9, -r * 0.9, r * 1.8, r * 1.8, r * 0.35);
  else for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * r, Math.sin((i / 6) * TAU + TAU / 12) * r);
  ctx.closePath();
}
