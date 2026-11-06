// UI-E4 出口路牌（docs/art/全遊戲一致性巡檢.md #11、偷懶自查 G6）：路牌方向、插在哪一格、觸控兩下、只在滑過時有綠框。
import { describe, expect, it } from "vitest";
import type { Graphics } from "pixi.js";
import { arrowShape, drawExitFrame, drawExitGlow, drawExitSign, exitAtCell, exitDir, exitLabel, exitSigns, exitTap, GLOW_ALPHA, plankShape, signCell } from "./exitSign";

/** 記錄畫了什麼的假 Graphics（每個方法回傳自己，可以串接）。 */
function pen() {
  const calls: Array<{ m: string; a: unknown[] }> = [];
  const g: Record<string, unknown> = {};
  for (const m of ["rect", "roundRect", "ellipse", "poly", "moveTo", "lineTo", "fill", "stroke", "circle"]) {
    g[m] = (...a: unknown[]) => {
      calls.push({ m, a });
      return g;
    };
  }
  return { g: g as unknown as Graphics, calls };
}

const field = (over: Partial<Parameters<typeof exitSigns>[0]> = {}) => ({
  width: 12,
  height: 10,
  interior: false,
  exits: [
    { id: "east", cells: [[11, 4], [11, 5]] as [number, number][], to_name_zh: "渡口石階" },
    { id: "north", cells: [[6, 0]] as [number, number][], to_name_zh: "竹林小徑" },
  ],
  ...over,
});

describe("出口方向與路牌位置", () => {
  it("在地圖哪一邊就指哪一邊；不在邊上時照相對地圖中心", () => {
    expect(exitDir([[11, 4], [11, 5]], 12, 10)).toBe("e");
    expect(exitDir([[0, 3]], 12, 10)).toBe("w");
    expect(exitDir([[6, 0]], 12, 10)).toBe("n");
    expect(exitDir([[5, 9], [6, 9]], 12, 10)).toBe("s");
    expect(exitDir([[9, 5]], 12, 10)).toBe("e");
    expect(exitDir([[5, 1]], 12, 10)).toBe("n");
  });

  it("路牌插在出口依 (y, x) 排序的第一格；多格的出口只插一塊", () => {
    expect(signCell([[11, 5], [11, 4]])).toEqual({ x: 11, y: 4 });
    const signs = exitSigns(field());
    expect(signs.map((s) => [s.id, s.dir, s.sign, s.cells.length, s.bare])).toEqual([
      ["east", "e", { x: 11, y: 4 }, 2, false],
      ["north", "n", { x: 6, y: 0 }, 1, false],
    ]);
  });

  it("室內的出口標 bare（不畫路牌與光圈，門墊與入口光已經有），滑過照樣找得到", () => {
    const signs = exitSigns(field({ interior: true, exits: [{ id: "out", cells: [[3, 6]], to_name_zh: "霧渡鎮" }], width: 7, height: 7 }));
    expect(signs[0]?.bare).toBe(true);
    expect(signs[0]?.dir).toBe("s");
    expect(exitAtCell(signs, { x: 3, y: 6 })?.name).toBe("霧渡鎮");
    expect(exitAtCell(signs, { x: 2, y: 6 })).toBeNull();
    expect(exitAtCell(signs, null)).toBeNull();
  });
});

describe("出口說明字", () => {
  it("「往 地名」；地名已經是「往……」開頭時不重複", () => {
    expect(exitLabel("渡口石階")).toBe("往 渡口石階");
    expect(exitLabel("往灰燼荒原的渡口")).toBe("往灰燼荒原的渡口");
  });
});

describe("觸控：點一下先亮，再點一次才走", () => {
  const signs = exitSigns(field());
  it("觸控第一次點出口＝亮起（不走）；再點同一個出口＝照常走；點別的出口＝改亮那一個", () => {
    expect(exitTap(signs, { x: 11, y: 5 }, "touch", null)).toEqual({ arm: "east" });
    expect(exitTap(signs, { x: 11, y: 4 }, "touch", "east")).toEqual({ arm: null });
    expect(exitTap(signs, { x: 6, y: 0 }, "touch", "east")).toEqual({ arm: "north" });
  });
  it("滑鼠與觸控筆點了就走；點的不是出口也照常", () => {
    expect(exitTap(signs, { x: 11, y: 5 }, "mouse", null)).toEqual({ arm: null });
    expect(exitTap(signs, { x: 11, y: 5 }, "pen", null)).toEqual({ arm: null });
    expect(exitTap(signs, { x: 3, y: 3 }, "touch", null)).toEqual({ arm: null });
  });
});

describe("畫法", () => {
  it("木牌：東西向一頭尖、指向出口；南北向是方牌，箭頭畫在牌面上", () => {
    const east = plankShape("e", 30, 14);
    const west = plankShape("w", 30, 14);
    expect(Math.max(...east.filter((_, i) => i % 2 === 0))).toBe(15); // 尖端在右
    expect(east[4]).toBe(15);
    expect(west[4]).toBe(-15); // 尖端在左
    expect(plankShape("n", 30, 14)).toHaveLength(8);
    // 箭頭尖端：北向朝上（y 最小）、南向朝下
    const tipY = (pts: number[]) => pts.filter((_, i) => i % 2 === 1);
    expect(Math.min(...tipY(arrowShape("n", 10)))).toBeLessThan(-4);
    expect(Math.max(...tipY(arrowShape("s", 10)))).toBeGreaterThan(4);
  });

  it("路牌有墨線（深棕）與木色填色；光圈很淡（不像按鈕）；綠框只在滑過時畫", () => {
    const sign = pen();
    drawExitSign(sign.g, 0, 0, 48, "e");
    expect(sign.calls.filter((c) => c.m === "poly")).toHaveLength(2); // 木牌＋箭頭
    expect(sign.calls.some((c) => c.m === "stroke" && (c.a[0] as { color: number }).color === 0x281e14)).toBe(true);
    const glow = pen();
    drawExitGlow(glow.g, 0, 0, 48);
    expect(glow.calls.filter((c) => c.m === "ellipse")).toHaveLength(2);
    expect(Math.max(...GLOW_ALPHA)).toBeLessThanOrEqual(0.2);
    const frame = pen();
    drawExitFrame(frame.g, 0, 0, 48, 0x5ee08a);
    expect(frame.calls.filter((c) => c.m === "roundRect")).toHaveLength(2);
  });
});
