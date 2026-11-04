// 6V-3／6V-4 只換外觀：火表面（火苗＋焦痕）、室內後牆掛件、附魔台發光環（慢轉）、荒原祭壇黑曜岩石板、
// 主城廣場裝飾與許願池噴水。全部確定性；會動的（附魔環、噴水）減少動態時停在第 0 毫秒；來源不新增 Math.random。
import { describe, expect, it } from "vitest";
import { drawTile, fireTongue, scorchMarks, type TileArtSpec } from "./terrainArt";
import { SHIMMER, surfaceShimmer } from "./surfaceAnim";

// 沒有 @types/node：用變數名載入 node:fs（vitest 在 node 環境執行；來源掃描用）
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
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

function calls(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  const m = mockCtx();
  fn(m.ctx);
  return m.calls;
}

const NO = { n: false, s: false, w: false, e: false };
function spec(over: Partial<TileArtSpec> = {}): TileArtSpec {
  return { region: "", look: "", terrain: "stone", x: 2, y: 3, height: 0, surface: "none", surfSame: NO, lip: NO, wallFace: false, blocked: false, tint: null, ...over };
}

describe("火表面（6V-3）", () => {
  it("同一格畫兩次一樣、不同格不一樣（只看格子座標雜湊）", () => {
    const a = calls((c) => drawTile(c, spec({ surface: "fire" })));
    expect(a).toEqual(calls((c) => drawTile(c, spec({ surface: "fire" }))));
    expect(a).not.toEqual(calls((c) => drawTile(c, spec({ surface: "fire", x: 7 }))));
  });

  it("有黑底焦痕（深色不規則斑塊）與煙燻暈", () => {
    const got = calls((c) => drawTile(c, spec({ surface: "fire" })));
    expect(got).toContain("fillStyle=rgba(20,12,8,0.82)");
    expect(got.some((x) => x.startsWith("stop(0,rgba(18,10,6"))).toBe(true);
    // 焦斑是 8 點多邊形：至少 2 塊 → 至少 14 個 lineTo
    const scorch = calls((c) => {
      let i = 0;
      scorchMarks(c, () => ((i = (i * 7 + 3) % 10), i / 10));
    });
    expect(scorch.filter((x) => x.startsWith("lineTo(")).length).toBeGreaterThanOrEqual(14);
  });

  it("火苗是彎曲的火舌（貝茲曲線、三層色、兩側小火舌），不是三角錐", () => {
    const got = calls((c) => fireTongue(c, 26, 44, 16, 0.4));
    expect(got.filter((x) => x.startsWith("bezierCurveTo(")).length).toBe(6); // 3 層 × 左右
    expect(got.filter((x) => x.startsWith("quadraticCurveTo(")).length).toBeGreaterThanOrEqual(8);
    for (const c of ["fillStyle=rgba(214,58,20,0.95)", "fillStyle=#ff8a1e", "fillStyle=#ffe07a", "fillStyle=rgba(226,72,24,0.9)"]) expect(got).toContain(c);
    // 尖端往 lean 那一側偏：最外層的尖端 x > 底部中心
    const tipCall = got.find((x) => x.startsWith("bezierCurveTo("))!;
    const nums = tipCall.slice(14, -1).split(",").map(Number);
    expect(nums[4]).toBeGreaterThan(26);
    const fire = calls((c) => drawTile(c, spec({ surface: "fire" })));
    const tongues = fire.filter((x) => x === "fillStyle=#ffe07a").length;
    expect(tongues).toBeGreaterThanOrEqual(2);
    expect(tongues).toBeLessThanOrEqual(3);
  });

  it("火光閃動照舊是時間 → 相位的確定性函式（減少動態時 SurfaceAnimator 不登記，畫面靜止）", () => {
    expect(surfaceShimmer("fire", 3, 4, 1234)).toEqual(surfaceShimmer("fire", 3, 4, 1234));
    expect(surfaceShimmer("fire", 3, 4, 0)).not.toEqual(surfaceShimmer("fire", 3, 4, SHIMMER.fireMs / 3));
  });
});

describe("來源掃描", () => {
  it("6V-3／6V-4 動到的畫法檔沒有 Math.random(", () => {
    const files = ["terrainArt.ts"];
    for (const f of files) {
      const src = readFileSync(new URL(`./${f}`, import.meta.url), "utf8")
        .split("\n")
        .filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("*"))
        .join("\n");
      expect(src, f).not.toMatch(/Math\.random\(/);
    }
  });
});
