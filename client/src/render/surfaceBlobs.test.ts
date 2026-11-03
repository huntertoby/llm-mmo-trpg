import { describe, expect, it } from "vitest";
import { buildDrawModel } from "../battle/drawModel";
import { smallView, tile } from "../battle/testFixtures";
import type { TileView } from "../api/types";
import { tileArtSpec } from "./artSpecs";
import { TRAP_HALO_RX, TRAP_HALO_RY, drawTrapPad } from "./fieldFx";
import { ALL_CORNERS, BLOB_T, blobEdges, blobShape, MAX_INSET, type BlobShape, type Corners } from "./surfaceBlobs";
import { drawTile, surfaceShape, type Sides } from "./terrainArt";

const T = BLOB_T;
const NONE: Sides = { n: false, s: false, w: false, e: false };
const NO_DIAG: Corners = { nw: false, ne: false, se: false, sw: false };
const EPS = 1e-9;

function inTile(shape: BlobShape): boolean {
  return shape.points.every((p) => p.x >= -EPS && p.x <= T + EPS && p.y >= -EPS && p.y <= T + EPS);
}

/** 一排地表格的繪製模型（`rows[y][x]` 為表面 ID，"none" 為沒有）。 */
function surfaceModel(rows: string[][]) {
  const tiles: TileView[] = [];
  rows.forEach((row, y) => row.forEach((surface, x) => tiles.push(tile(x, y, { surface: surface as TileView["surface"] }))));
  const view = { ...smallView(), width: rows[0]!.length, height: rows.length, tiles, objects: [], units: [], traps: [] };
  return buildDrawModel(view, "unit_0001");
}

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
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

describe("地表併塊幾何（6A-4a）", () => {
  it("單獨一格：四邊內縮 0 < d ≤ 5，四角是圓角，所有點都在格子內", () => {
    const shape = blobShape(3, 4, NONE, NO_DIAG);
    expect(inTile(shape)).toBe(true);
    expect(shape.full).toBe(false);
    for (const p of shape.points) {
      const d = Math.min(p.x, p.y, T - p.x, T - p.y);
      expect(d).toBeGreaterThan(0); // 不貼格子邊
    }
    // 每條邊中點附近的點：內縮 ≤ 5
    const mid = shape.points.filter((p) => Math.abs(p.x - T / 2) < 6 || Math.abs(p.y - T / 2) < 6);
    expect(mid.length).toBeGreaterThan(0);
    for (const p of mid) expect(Math.min(p.x, p.y, T - p.x, T - p.y)).toBeLessThanOrEqual(MAX_INSET);
    // 圓角：格子的四個角落 6 單位內沒有點
    for (const [cx, cy] of [
      [0, 0],
      [T, 0],
      [T, T],
      [0, T],
    ] as const) {
      expect(shape.points.some((p) => Math.hypot(p.x - cx, p.y - cy) < 6)).toBe(false);
    }
    expect(blobEdges(shape)).toHaveLength(1); // 一整圈外緣
  });

  it("四鄰與斜鄰都是同種：整格填滿、沒有外緣", () => {
    const shape = blobShape(5, 5, { n: true, s: true, w: true, e: true }, ALL_CORNERS);
    expect(shape.full).toBe(true);
    expect(shape.points.map((p) => [p.x, p.y])).toEqual([
      [0, 0],
      [T, 0],
      [T, T],
      [0, T],
    ]);
    expect(blobEdges(shape)).toEqual([]);
  });

  it("接縫補滿：和同種鄰格相接的那條邊整條貼齊格子邊界", () => {
    const east = blobShape(2, 2, { ...NONE, e: true }, NO_DIAG);
    const onRight = east.points.filter((p) => Math.abs(p.x - T) < EPS);
    expect(onRight).toHaveLength(2);
    const ys = onRight.map((p) => p.y).sort((a, b) => a - b);
    expect(ys[0]!).toBeLessThanOrEqual(MAX_INSET);
    expect(ys[1]!).toBeGreaterThanOrEqual(T - MAX_INSET);
    // 接縫那段不描邊
    const seam = east.points.findIndex((p) => Math.abs(p.x - T) < EPS && !p.edge);
    expect(seam).toBeGreaterThanOrEqual(0);
  });

  it("相鄰同種的兩格：共用邊界兩端的外緣內縮量相同（接得起來）", () => {
    const a = blobShape(4, 7, { ...NONE, e: true }, NO_DIAG);
    const b = blobShape(5, 7, { ...NONE, w: true }, NO_DIAG);
    const right = a.points.filter((p) => Math.abs(p.x - T) < EPS).map((p) => p.y).sort((p, q) => p - q);
    const left = b.points.filter((p) => Math.abs(p.x) < EPS).map((p) => p.y).sort((p, q) => p - q);
    expect(left).toEqual(right);
  });

  it("內凹角：兩邊是接縫但斜鄰不是同種時，角落留一小塊（≤ 5 單位）", () => {
    const sides = { n: true, s: true, w: true, e: true };
    const shape = blobShape(1, 1, sides, { ...ALL_CORNERS, nw: false });
    expect(inTile(shape)).toBe(true);
    expect(shape.points.some((p) => p.x === 0 && p.y === 0)).toBe(false);
    const notch = shape.points.filter((p) => p.x < 6 && p.y < 6);
    expect(notch.length).toBeGreaterThan(0);
    for (const p of notch) expect(Math.max(p.x, p.y)).toBeLessThanOrEqual(MAX_INSET);
    expect(blobEdges(shape)).toHaveLength(1);
  });

  it("任何四鄰／斜鄰組合：點都在格子內，露出的邊內縮 ≤ 5", () => {
    for (let m = 0; m < 256; m++) {
      const same: Sides = { n: !!(m & 1), e: !!(m & 2), s: !!(m & 4), w: !!(m & 8) };
      const diag: Corners = { nw: !!(m & 16), ne: !!(m & 32), se: !!(m & 64), sw: !!(m & 128) };
      for (const [x, y] of [
        [0, 0],
        [7, 3],
        [11, 11],
      ] as const) {
        const shape = blobShape(x, y, same, diag);
        expect(inTile(shape)).toBe(true);
        // 露出的那一側：邊中段的點離該側 ≤ 5
        const side = (k: "n" | "e" | "s" | "w", dist: (p: { x: number; y: number }) => number, along: (p: { x: number; y: number }) => number) => {
          if (same[k]) return;
          const pts = shape.points.filter((p) => Math.abs(along(p) - T / 2) < 4 && dist(p) < T / 4);
          expect(pts.length, `${m} ${k}`).toBeGreaterThan(0);
          for (const p of pts) expect(dist(p)).toBeLessThanOrEqual(MAX_INSET);
        };
        side("n", (p) => p.y, (p) => p.x);
        side("s", (p) => T - p.y, (p) => p.x);
        side("w", (p) => p.x, (p) => p.y);
        side("e", (p) => T - p.x, (p) => p.y);
      }
    }
  });

  it("雜湊固定：同一格每次結果相同；不同格起伏不同", () => {
    const a = blobShape(3, 9, NONE, NO_DIAG);
    expect(blobShape(3, 9, NONE, NO_DIAG)).toEqual(a);
    expect(blobShape(4, 9, NONE, NO_DIAG)).not.toEqual(a);
  });
});

describe("繪製模型 → 併塊（6A-4a）", () => {
  it("相鄰同種合併、異種不合併；斜鄰旗標", () => {
    const m = surfaceModel([
      ["ice", "ice", "oil"],
      ["none", "ice", "none"],
    ]);
    const at = (x: number, y: number) => tileArtSpec(m, m.tiles.find((t) => t.x === x && t.y === y)!);
    expect(at(0, 0).surfSame).toEqual({ n: false, s: false, w: false, e: true });
    expect(at(1, 0).surfSame).toEqual({ n: false, s: true, w: true, e: false }); // 東邊是油：不合併
    expect(at(2, 0).surfSame).toEqual(NONE);
    expect(at(1, 1).surfDiag).toEqual({ nw: true, ne: false, se: false, sw: false });
    // 冰與油相鄰：兩邊各自內縮，不接在一起
    const ice = surfaceShape(at(1, 0));
    const oil = surfaceShape(at(2, 0));
    expect(ice.points.some((p) => Math.abs(p.x - T) < EPS)).toBe(false);
    expect(oil.points.some((p) => Math.abs(p.x) < EPS)).toBe(false);
    // 冰與冰相鄰：接縫貼齊
    expect(surfaceShape(at(0, 0)).points.some((p) => Math.abs(p.x - T) < EPS)).toBe(true);
  });

  it("各種表面（含未知）在任何鄰格組合下都畫得出來；不畫格線", () => {
    const m = surfaceModel([
      ["ice", "oil", "fire", "water", "poison"],
      ["holy", "darkness", "smoke", "none", "none"],
    ]);
    for (const t of m.tiles) {
      const { ctx, calls } = mockCtx();
      expect(() => drawTile(ctx, tileArtSpec(m, t))).not.toThrow();
      expect(calls.some((c) => c.startsWith("strokeRect("))).toBe(false);
      const unknown = mockCtx();
      expect(() => drawTile(unknown.ctx, { ...tileArtSpec(m, t), surface: "brand_new_surface" })).not.toThrow();
    }
  });

  it("貼圖快取鍵包含斜鄰旗標", async () => {
    const { tileArtKey } = await import("./terrainArt");
    const m = surfaceModel([["ice"]]);
    const spec = tileArtSpec(m, m.tiles[0]!);
    expect(tileArtKey({ ...spec, surfDiag: NO_DIAG })).not.toBe(tileArtKey({ ...spec, surfDiag: ALL_CORNERS }));
  });
});

describe("陷阱的淡紅虛線圈（6A-4a）", () => {
  it("虛線圈在格子內，我方與敵方都畫", () => {
    expect(26 - TRAP_HALO_RX).toBeGreaterThanOrEqual(0);
    expect(26 + TRAP_HALO_RX).toBeLessThanOrEqual(T);
    expect(28 - TRAP_HALO_RY).toBeGreaterThanOrEqual(0);
    expect(28 + TRAP_HALO_RY).toBeLessThanOrEqual(T);
    for (const mine of [true, false]) {
      const { ctx, calls } = mockCtx();
      drawTrapPad(ctx, { mine, trigger: "enter", color: "#ff0000" });
      expect(calls).toContain(`ellipse(26.000,28.000,${TRAP_HALO_RX.toFixed(3)},${TRAP_HALO_RY.toFixed(3)},0.000,0.000,${(Math.PI * 2).toFixed(3)})`);
      expect(calls.some((c) => c.startsWith("setLineDash(object"))).toBe(true);
    }
  });
});
