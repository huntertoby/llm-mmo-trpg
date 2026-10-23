// Phase 3-18b：矮牆改畫（docs/art/矮牆.md）。
import { describe, expect, it } from "vitest";
import { drawObject, type ObjectArtSpec } from "./objectArt";
import { ART_T } from "./terrainArt";

interface Rec {
  fills: Array<{ style: string; rect: number[] }>;
  strokes: number;
  moves: number[][];
}

function record(spec: Partial<ObjectArtSpec>): Rec {
  const rec: Rec = { fills: [], strokes: 0, moves: [] };
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: number[]) => {
        if (prop === "fillRect") rec.fills.push({ style: String(target.fillStyle), rect: args });
        if (prop === "stroke") rec.strokes += 1;
        if (prop === "moveTo") rec.moves.push(args);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  drawObject(ctx, { kind: "low_wall", x: 0, y: 0, joinL: false, joinR: false, vertical: false, flammable: false, turnsLeft: null, hpStage: 0, ...spec });
  return rec;
}

describe("矮牆", () => {
  it("暖色石塊：壓頂石 #d8c7a2、亮邊 #f2e6c8、正面 #86704f", () => {
    const styles = record({}).fills.map((f) => f.style);
    expect(styles).toEqual(expect.arrayContaining(["#d8c7a2", "#f2e6c8", "#86704f", "rgba(0,0,0,0.42)"]));
  });

  it("單獨一格左右各內縮 4px；相連的一側畫到格邊", () => {
    const body = (r: Rec): [number, number, number] => r.fills.find((f) => f.style === "#86704f")!.rect as [number, number, number];
    const [x, , w] = body(record({}));
    expect([x, w]).toEqual([4, ART_T - 8]);
    const [xl, , wl] = body(record({ joinL: true }));
    expect([xl, xl + wl]).toEqual([0, ART_T - 4]);
    const [xr, , wr] = body(record({ joinR: true }));
    expect([xr, xr + wr]).toEqual([4, ART_T]);
    const [xb, , wb] = body(record({ joinL: true, joinR: true }));
    expect([xb, wb]).toEqual([0, ART_T]);
  });
});
