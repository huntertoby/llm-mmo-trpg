// 格子範圍的併塊畫法（Phase 6A-4g；docs/art/6A-4d至6M-3六段檢查.md 第 7 節第 4 項）：一組格子（例如實地地圖上敵人的視野）
// 照地表併塊（`surfaceBlobs.ts`）的幾何併成一塊——淡色填滿、只描露在外面的外緣，格子之間的接縫不描，也不畫格角徽章。
// `regionShapes` 是純函式（只看格子集合），`drawRegionBlobs` 把它畫進 Pixi 的 Graphics。
import type { Graphics } from "pixi.js";
import type { Pos } from "../api/types";
import { blobEdges, blobShape, type BlobShape } from "./surfaceBlobs";

export interface RegionMark {
  cells: readonly Pos[];
  color: number;
  /** 填色不透明度（預設 0.16）。 */
  fill?: number;
  /** 外緣不透明度（預設 0.8）。 */
  edge?: number;
}

export interface RegionCell {
  pos: Pos;
  shape: BlobShape;
}

const key = (x: number, y: number): string => `${x},${y}`;

/** 每一格的併塊形狀（四鄰、斜鄰是不是同一個範圍）；去重、依座標排序。`T` 是格子邊長。 */
export function regionShapes(cells: readonly Pos[], T: number): RegionCell[] {
  const set = new Set(cells.map((p) => key(p.x, p.y)));
  const has = (x: number, y: number) => set.has(key(x, y));
  return [...set]
    .map((k) => k.split(",").map(Number) as [number, number])
    .sort((a, b) => a[1] - b[1] || a[0] - b[0])
    .map(([x, y]) => ({
      pos: { x, y },
      shape: blobShape(
        x,
        y,
        { n: has(x, y - 1), e: has(x + 1, y), s: has(x, y + 1), w: has(x - 1, y) },
        { nw: has(x - 1, y - 1), ne: has(x + 1, y - 1), se: has(x + 1, y + 1), sw: has(x - 1, y + 1) },
        T,
      ),
    }));
}

/** 畫一組範圍：先把所有格子的形狀一次填色（同一個範圍只疊一層），再描外緣。`origin` 給格子左上角（含抬高）。 */
export function drawRegionBlobs(g: Graphics, regions: readonly RegionMark[], T: number, origin: (p: Pos) => { x: number; y: number }): void {
  for (const r of regions) {
    const shapes = regionShapes(r.cells, T);
    if (shapes.length === 0) continue;
    for (const { pos, shape } of shapes) {
      const o = origin(pos);
      g.poly(shape.points.flatMap((p) => [o.x + p.x, o.y + p.y]));
    }
    g.fill({ color: r.color, alpha: r.fill ?? 0.16 });
    g.beginPath();
    for (const { pos, shape } of shapes) {
      const o = origin(pos);
      for (const run of blobEdges(shape)) {
        const [first, ...rest] = run;
        if (first === undefined) continue;
        g.moveTo(o.x + first.x, o.y + first.y);
        for (const p of rest) g.lineTo(o.x + p.x, o.y + p.y);
      }
    }
    g.stroke({ width: 2, color: r.color, alpha: r.edge ?? 0.8 });
    g.beginPath();
  }
}
