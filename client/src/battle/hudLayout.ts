// 戰鬥版 HUD 版面 A 的版面數值（Phase 6A-4e，純函式）：四角 HUD 疊在戰場上，地圖可用區域扣掉上方行動順序列與底部列。
// 底部列（技能列＋回合操作）的高度隨內容變，由畫面量好後經 CSS 變數 `--hud-bottom` 傳給戰場、紀錄與縮放鈕。
import type { CSSProperties } from "react";

/** 還沒量到底部列時先用的高度（技能列一排＋回合操作）。 */
export const HUD_BOTTOM_FALLBACK = 160;

/** 底部列高度的 CSS 變數；`null`（還沒量到）用預設值。 */
export function hudInsetStyle(bottomHeight: number | null): CSSProperties {
  const h = bottomHeight === null || !(bottomHeight > 0) ? HUD_BOTTOM_FALLBACK : Math.ceil(bottomHeight);
  return { "--hud-bottom": `${h}px` } as CSSProperties;
}

export interface HudBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** 排版煙霧檢查用的 HUD 區塊名稱（`.bhud-hero` 等）。 */
export const HUD_BLOCKS = ["hero", "order", "status", "tools", "skills", "turn", "log"] as const;
export type HudBlockId = (typeof HUD_BLOCKS)[number];

const TOL = 1.5;

/** 區塊在視窗內（容許子像素誤差）。 */
export function insideViewport(b: HudBox, width: number, height: number): boolean {
  return b.left >= -TOL && b.top >= -TOL && b.right <= width + TOL && b.bottom <= height + TOL;
}

/** 兩個區塊重疊超過 2px（兩個方向都超過才算）。 */
export function overlaps(a: HudBox, b: HudBox): boolean {
  const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
  const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
  return x > 2 && y > 2;
}

/** 量到的 HUD 區塊：缺少的、出畫面的、互相重疊的，各列一句；全部正常為空陣列。 */
export function hudLayoutIssues(blocks: Partial<Record<HudBlockId, HudBox | null>>, width: number, height: number): string[] {
  const out: string[] = [];
  const present: [HudBlockId, HudBox][] = [];
  for (const id of HUD_BLOCKS) {
    const b = blocks[id];
    if (b == null) {
      out.push(`找不到 ${id}`);
      continue;
    }
    present.push([id, b]);
    if (!insideViewport(b, width, height)) out.push(`${id} 出畫面`);
  }
  for (let i = 0; i < present.length; i++) {
    for (let j = i + 1; j < present.length; j++) {
      const [ia, a] = present[i] as [HudBlockId, HudBox];
      const [ib, b] = present[j] as [HudBlockId, HudBox];
      if (overlaps(a, b)) out.push(`${ia} 與 ${ib} 重疊`);
    }
  }
  return out;
}
