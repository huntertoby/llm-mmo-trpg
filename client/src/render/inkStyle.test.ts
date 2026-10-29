// Phase C-1a：C 手繪墨線畫法層 — 確定性（同 key 同點、不同 key 不同點、不用 Math.random）、ink／stroke 的畫法結構。
import { afterEach, describe, expect, it, vi } from "vitest";
import { dot, ellPts, ink, INK, lcg, seedOf, shadow, stroke, withShadeDir, wobble, type Pt } from "./inkStyle";

function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(4) : String(a))).join(",")})`);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const SQUARE: Pt[] = [[-5, -10], [5, -10], [5, 0], [-5, 0]];

afterEach(() => vi.restoreAllMocks());

describe("seedOf／lcg（確定性）", () => {
  it("FNV-1a：已知值、同字串同種子、不同字串不同種子", () => {
    expect(seedOf("")).toBe(2166136261);
    expect(seedOf("a")).toBe(0xe40c292c);
    expect(seedOf("leg-1")).toBe(seedOf("leg-1"));
    expect(seedOf("leg-1")).not.toBe(seedOf("leg-far"));
  });

  it("lcg 同種子同序列，值在 [0,1)", () => {
    const a = lcg(seedOf("x"));
    const b = lcg(seedOf("x"));
    for (let i = 0; i < 50; i++) {
      const v = a();
      expect(v).toBe(b());
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it("wobble：同 key 兩次取點完全相同、不同 key 不同", () => {
    const pts = ellPts(0, 0, 5, 4, 12);
    expect(wobble(pts, lcg(seedOf("head")), 0.7)).toEqual(wobble(pts, lcg(seedOf("head")), 0.7));
    expect(wobble(pts, lcg(seedOf("head")), 0.7)).not.toEqual(wobble(pts, lcg(seedOf("torso")), 0.7));
  });
});

describe("ink／stroke", () => {
  it("同 key 兩次畫完全相同（不閃）、不同 key 不同；全程不呼叫 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    const run = (key: string): string[] => {
      const { ctx, calls } = recorder();
      ink(ctx, key, SQUARE, "#8a8f99");
      stroke(ctx, `${key}-s`, [[0, 0], [3, 1], [6, 0]], 0.5);
      return calls;
    };
    expect(run("torso-front")).toEqual(run("torso-front"));
    expect(run("torso-front")).not.toEqual(run("torso-side"));
    expect(rnd).not.toHaveBeenCalled();
  });

  it("畫法結構：水彩填色（偏移 0.45,0.35、透明度 0.94、35% 深色邊）→ 排線（裁在形狀內）→ 墨線畫兩次（w 與 0.45w）", () => {
    const { ctx, calls } = recorder();
    ink(ctx, "k", SQUARE, "#336699");
    expect(calls[0]).toBe("save()");
    expect(calls[1]).toBe("translate(0.4500,0.3500)");
    expect(calls).toContain("globalAlpha=0.94");
    expect(calls).toContain("fillStyle=#336699");
    expect(calls).toContain("globalAlpha=0.35");
    expect(calls).toContain("strokeStyle=rgba(0,0,0,0.55)");
    const clip = calls.indexOf("clip()");
    expect(clip).toBeGreaterThan(calls.indexOf("fill()")); // 排線在填色之後
    expect(calls).toContain("strokeStyle=rgba(43,30,22,0.42)");
    expect(calls).toContain("lineWidth=0.35");
    expect(calls.indexOf(`strokeStyle=${INK}`)).toBeGreaterThan(clip); // 墨線在排線之後
    const widths = calls.filter((c) => c.startsWith("lineWidth=")).map((c) => c.slice(10));
    expect(widths.slice(-2)).toEqual(["0.85", String(0.85 * 0.45)]);
    expect(calls.filter((c) => c === "stroke()").length).toBe(4); // 溢色邊 ＋ 排線 ＋ 墨線×2
  });

  it("opt：shade:false 不排線、line:false 不描墨線、sharp 不用曲線、w 改線寬", () => {
    const base = recorder();
    ink(base.ctx, "k", SQUARE, "#fff");
    const noShade = recorder();
    ink(noShade.ctx, "k", SQUARE, "#fff", { shade: false });
    expect(noShade.calls).not.toContain("clip()");
    expect(base.calls).toContain("clip()");
    const noLine = recorder();
    ink(noLine.ctx, "k", SQUARE, "#fff", { line: false });
    expect(noLine.calls).not.toContain(`strokeStyle=${INK}`);
    const sharp = recorder();
    ink(sharp.ctx, "k", SQUARE, "#fff", { sharp: true });
    expect(sharp.calls.some((c) => c.startsWith("quadraticCurveTo"))).toBe(false);
    expect(sharp.calls.some((c) => c.startsWith("lineTo"))).toBe(true);
    expect(base.calls.some((c) => c.startsWith("quadraticCurveTo"))).toBe(true);
    const wide = recorder();
    ink(wide.ctx, "k", SQUARE, "#fff", { w: 2 });
    expect(wide.calls).toContain("lineWidth=2");
  });

  it("暗面方向：正面排線偏右、側面／背面偏左（斜線起點 x 不同）；預設 1，withShadeDir 結束後還原（不依賴呼叫順序）", () => {
    const hatchX = (calls: string[]): number => Number((calls.slice(calls.indexOf("clip()")).find((c) => c.startsWith("moveTo(")) ?? "").slice(7).split(",")[0]);
    const first = (dir: 1 | -1 | null): number => {
      const { ctx, calls } = recorder();
      const draw = (): void => ink(ctx, "k", SQUARE, "#fff", { line: false });
      if (dir === null) draw();
      else withShadeDir(ctx, dir, draw);
      return hatchX(calls);
    };
    expect(first(1)).toBeGreaterThan(first(-1));
    expect(first(null)).toBe(first(1));
    // 同一個畫布：內層用完還原成外層，外層用完回到預設
    const { ctx, calls } = recorder();
    withShadeDir(ctx, -1, () => withShadeDir(ctx, 1, () => undefined));
    ink(ctx, "k", SQUARE, "#fff", { line: false });
    expect(hatchX(calls)).toBe(first(1));
  });

  it("太小的形狀（寬或高 ≤ 3）不畫排線", () => {
    const { ctx, calls } = recorder();
    ink(ctx, "k", ellPts(0, 0, 1.5, 1.5, 8), "#fff");
    expect(calls).not.toContain("clip()");
  });
});

describe("影子與小物件", () => {
  it("影子是一排短斜線（moveTo／lineTo 成對），不是橢圓", () => {
    const { ctx, calls } = recorder();
    shadow(ctx);
    expect(calls.some((c) => c.startsWith("ellipse"))).toBe(false);
    const moves = calls.filter((c) => c.startsWith("moveTo")).length;
    expect(moves).toBeGreaterThanOrEqual(6);
    expect(calls.filter((c) => c.startsWith("lineTo")).length).toBe(moves);
    const again = recorder();
    shadow(again.ctx);
    expect(again.calls).toEqual(calls);
  });

  it("dot 畫一個橢圓", () => {
    const { ctx, calls } = recorder();
    dot(ctx, 1, 2, 3, 4, "#abc");
    expect(calls.some((c) => c.startsWith("ellipse(1.0000,2.0000,3.0000,4.0000"))).toBe(true);
  });
});
