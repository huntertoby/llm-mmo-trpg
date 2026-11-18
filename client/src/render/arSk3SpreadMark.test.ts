// AR-SK3：AR-SK2 驗收的小修 1（「+N」角標膠囊不被孢子壓到）與裁定 4（畫面上的框邊長 ≥14 px 時改用狀態卡的排法）。
import { describe, expect, it } from "vitest";
import { moreCapBox, ROW_ICON_FEET, SUMMON_MORE_DX_MAX, SUMMON_MORE_AT } from "./rowLayout";
import { fieldUsesCardLayout, headSporeRight, spreadMark, SPORE_HEAD } from "./spreadMark";

interface Arc { x: number; y: number; r: number }
function fakeCtx(k: number, out: Arc[]): CanvasRenderingContext2D {
  const m = { a: k, b: 0, c: 0, d: k, e: 0, f: 0, inverse: () => ({ a: 1 / k, b: 0, c: 0, d: 1 / k, e: 0, f: 0 }) };
  const noop = () => undefined;
  return new Proxy({} as Record<string, unknown>, {
    get: (_t, p) => (p === "getTransform" ? () => m : p === "arc" ? (x: number, y: number, r: number) => out.push({ x, y, r }) : noop),
    set: () => true,
  }) as unknown as CanvasRenderingContext2D;
}

describe("裁定 4：戰場記號的排法看畫面上的框邊長", () => {
  it("框 9 模型 px：1600 寬（1.31）頭頂排法；縮放約 1.56 以上換狀態卡排法；800 寬放大後（0.53×1.75）仍是頭頂", () => {
    expect(fieldUsesCardLayout(ROW_ICON_FEET, 1.31)).toBe(false);
    expect(fieldUsesCardLayout(ROW_ICON_FEET, 0.53 * 1.75)).toBe(false);
    expect(fieldUsesCardLayout(ROW_ICON_FEET, 14 / 9 - 0.01)).toBe(false);
    expect(fieldUsesCardLayout(ROW_ICON_FEET, 14 / 9)).toBe(true);
    expect(fieldUsesCardLayout(ROW_ICON_FEET, 2)).toBe(true);
  });
  it("狀態卡排法時孢子、小點的大小是畫面 px（2.2、1.1），而且仍在框頂外緣之上", () => {
    const S = 2, arcs: Arc[] = [];
    spreadMark(fakeCtx(4, arcs), ROW_ICON_FEET - 2, S, 4 / S);
    expect((ROW_ICON_FEET - 2) * S).toBeGreaterThanOrEqual(SPORE_HEAD);
    const spore = arcs[3] as Arc, dot = arcs[1] as Arc;
    expect(spore.r * S).toBeCloseTo(2.2, 6);
    expect(dot.r * S).toBeCloseTo(1.1, 6);
    const top = -(0.45 * 9 + Math.max(1.5, 9 * S * 0.09) / S / 2);
    for (const a of arcs) expect(a.y + a.r).toBeLessThanOrEqual(top + 1e-9);
  });
});

describe("小修 1：第 2 個圖示有記號時「+N」角標膠囊讓到孢子外面", () => {
  it("讓開之後膠囊左緣在孢子（含小點、外框色）的右邊；原本的位置會碰到", () => {
    const right = headSporeRight(ROW_ICON_FEET);
    const sporeDx = right + 0.5 - ROW_ICON_FEET / 2 + SUMMON_MORE_DX_MAX;
    expect(moreCapBox(0, SUMMON_MORE_AT.dx).l).toBeLessThan(right); // 改前：疊到
    expect(moreCapBox(0, SUMMON_MORE_DX_MAX).l).toBeLessThan(right); // 改前最右也疊到
    expect(moreCapBox(0, sporeDx).l).toBeGreaterThanOrEqual(right);
  });
  it("孢子右緣照實際畫的位置算（真的畫一次量 arc）", () => {
    const arcs: Arc[] = [];
    spreadMark(fakeCtx(2, arcs), ROW_ICON_FEET - 2, 1, 2);
    const maxR = Math.max(...arcs.map((a) => a.x + a.r));
    expect(headSporeRight(ROW_ICON_FEET)).toBeGreaterThanOrEqual(maxR);
    expect(headSporeRight(ROW_ICON_FEET) - maxR).toBeLessThan(1.5);
  });
});
