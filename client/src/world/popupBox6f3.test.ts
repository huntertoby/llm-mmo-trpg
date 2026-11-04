// 6F-3（美術 PM 一致性巡檢 #10、實機巡檢 bug 6）：背包、技能、NPC 面板、遇敵卡不蓋到四角的 HUD。
import { describe, expect, it } from "vitest";
import { HUD_BLOCKS, hudLayout, popupBox, type HudBlock, type Rect } from "./hud";

const SIZES = [
  [1600, 900],
  [1040, 624],
  [800, 600],
] as const;

/** 彈窗會碰到的 HUD（提示在左下，彈窗下緣停在功能列上方；提示是暫時的，另外檢查不蓋到主角卡）。 */
const AVOID: readonly HudBlock[] = HUD_BLOCKS.filter((id) => id !== "toasts");

function overlaps(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width - 0.5 && b.left < a.left + a.width - 0.5 && a.top < b.top + b.height - 0.5 && b.top < a.top + a.height - 0.5;
}

describe("彈窗避開四角的 HUD", () => {
  for (const [w, h] of SIZES) {
    for (const mates of [0, 2]) {
      for (const collapsed of [false, true]) {
        it(`${w}×${h}、隊友 ${mates}、追蹤${collapsed ? "收合" : "展開"}：面板與遇敵卡都不蓋 HUD`, () => {
          const layout = hudLayout(w, h, { mates, narrow: w < 900, collapsed });
          for (const want of [720, 460 * layout.scale]) {
            const box = popupBox(layout, want);
            const rect: Rect = { left: (w - box.maxWidth) / 2, top: box.top, width: box.maxWidth, height: box.maxHeight };
            expect(box.maxWidth).toBeLessThanOrEqual(want);
            expect(box.maxWidth).toBeGreaterThan(250);
            expect(rect.top + rect.height).toBeLessThanOrEqual(layout.blocks.bar.top);
            for (const id of AVOID) {
              const b = layout.blocks[id];
              if (b.width <= 0 || b.height <= 0) continue;
              expect(overlaps(rect, b), `${id}`).toBe(false);
            }
          }
        });
      }
    }
  }

  it("上緣在主角卡下方（血條看得到）", () => {
    const layout = hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false });
    const hero = layout.blocks.hero;
    expect(popupBox(layout, 720).top).toBeGreaterThanOrEqual(hero.top + hero.height);
  });
});
