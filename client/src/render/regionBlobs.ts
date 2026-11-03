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
  /** 外緣顏色（預設同 `color`）。 */
  edgeColor?: number;
  /** 外緣虛線 [實線長, 空白長]（6C-8 實地地圖的敵人視野）；省略＝實線。 */
  dash?: readonly [number, number];
}

type Pt = { x: number; y: number };

/**
 * 把一條折線切成虛線段（6C-8）：從起點開始「實線 `on`、空白 `off`」交替，跨過轉角時接著量；回傳每段實線的折線。
 * `on`、`off` 不是正數時原樣回傳整條（實線）。
 */
export function dashRun(run: readonly Pt[], on: number, off: number): Pt[][] {
  if (!(on > 0) || !(off > 0) || run.length < 2) return run.length >= 2 ? [run.map((p) => ({ ...p }))] : [];
  const out: Pt[][] = [];
  let cur: Pt[] | null = [{ ...run[0]! }];
  let left = on; // 這一段（實線或空白）還剩多長
  let drawing = true;
  for (let i = 1; i < run.length; i++) {
    let a = run[i - 1]!;
    const b = run[i]!;
    let len = Math.hypot(b.x - a.x, b.y - a.y);
    while (len > 1e-9) {
      const step = Math.min(left, len);
      const t = step / len;
      const p = { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
      if (drawing) cur!.push(p);
      a = p;
      len -= step;
      left -= step;
      if (left <= 1e-9) {
        if (drawing) {
          out.push(cur!);
          cur = null;
        } else cur = [{ ...p }];
        drawing = !drawing;
        left = drawing ? on : off;
      }
    }
  }
  if (drawing && cur !== null && cur.length >= 2) out.push(cur);
  return out;
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
      for (const edge of blobEdges(shape)) {
        for (const run of r.dash === undefined ? [edge] : dashRun(edge, r.dash[0], r.dash[1])) {
          const [first, ...rest] = run;
          if (first === undefined) continue;
          g.moveTo(o.x + first.x, o.y + first.y);
          for (const p of rest) g.lineTo(o.x + p.x, o.y + p.y);
        }
      }
    }
    g.stroke({ width: 2, color: r.edgeColor ?? r.color, alpha: r.edge ?? 0.8, cap: r.dash === undefined ? "butt" : "round" });
    g.beginPath();
  }
}
