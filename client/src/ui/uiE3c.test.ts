// UI-E3c（美術 PM 退回，docs/art/UI-E3與UI-E4檢查.md 第 3 節）：花費行的「・」、浮動卡優先方向等。
import { describe, expect, it } from "vitest";
import { floatPlacement } from "./floatCard";
import { costPieces, costPiecesTrailing } from "./skillCost";
import { readFile, SRC_DIR } from "../test/sourceScan";

describe("必修 2：技能面板的花費行，「・」留在上一段的行尾", () => {
  it("每段（除了最後一段）以「・」結尾，沒有一段以「・」開頭", () => {
    const pieces = costPiecesTrailing({ parts: ["AP 2", "法力 5", "冷卻 2"], more: false });
    expect(pieces).toEqual(["AP 2・", "法力 5・", "冷卻 2"]);
    expect(pieces.some((p) => p.startsWith("・"))).toBe(false);
  });

  it("有段被拿掉時最後一段加「…」；只有一段時不加「・」", () => {
    expect(costPiecesTrailing({ parts: ["AP 2", "冷卻 2"], more: true })).toEqual(["AP 2・", "冷卻 2…"]);
    expect(costPiecesTrailing({ parts: ["AP 1"], more: false })).toEqual(["AP 1"]);
  });

  it("接起來的字和戰鬥底列（`costPieces`）完全一樣", () => {
    for (const fit of [
      { parts: ["AP 2", "法力 5", "冷卻 2"], more: false },
      { parts: ["AP 2", "冷卻 2"], more: true },
    ]) {
      expect(costPiecesTrailing(fit).join("")).toBe(costPieces(fit).join(""));
    }
  });
});

describe("小修 5：浮動卡 `prefer`（技能面板的技能卡優先開在下方）", () => {
  const view = { width: 800, height: 600 };
  const size = { width: 300, height: 200 };

  it("不給 `prefer` 時照舊預設上方", () => {
    expect(floatPlacement({ left: 100, top: 300, width: 60, height: 40 }, size, view).side).toBe("above");
  });

  it("`prefer=below`：下方放得下就開在下方，貼齊觸發元素", () => {
    const p = floatPlacement({ left: 100, top: 300, width: 60, height: 40 }, size, view, "start", 4, "below");
    expect(p).toEqual({ left: 100, top: 340, side: "below" });
  });

  it("`prefer=below`：下方放不下、上方放得下就翻到上方", () => {
    const p = floatPlacement({ left: 100, top: 450, width: 60, height: 40 }, size, view, "start", 4, "below");
    expect(p).toEqual({ left: 100, top: 250, side: "above" });
  });

  it("`prefer=below`：兩邊都放不下選空間大的一邊，且不超出視窗", () => {
    const tall = { width: 300, height: 500 };
    const p = floatPlacement({ left: 100, top: 200, width: 40, height: 40 }, tall, view, "start", 4, "below");
    expect(p.side).toBe("below");
    expect(p.top).toBeGreaterThanOrEqual(4);
    expect(p.top + tall.height).toBeLessThanOrEqual(view.height - 4);
  });
});

describe("小修 5：只有技能面板的 SkillTile 用 `prefer=below`", () => {
  it("HudPanels 的兩處 SkillTile 都傳 below；SkillTile 預設仍是上方", () => {
    const hud = readFile(SRC_DIR, "world/HudPanels.tsx");
    const tile = readFile(SRC_DIR, "ui/SkillTile.tsx");
    expect(hud.match(/<SkillTile[\s\S]*?\/>/g)?.every((t) => t.includes('prefer="below"'))).toBe(true);
    expect(tile).toContain('prefer = "above"');
    expect(tile).toContain("prefer={prefer}");
  });
});
