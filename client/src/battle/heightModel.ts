// 高度表現（Phase 3-14，方案 A）：由繪製模型推導「懸崖線」與單位底座（純函式；Pixi 只負責照著畫）。
// 側面、投影、崖面已改畫進地形貼圖（3-16a，見 render/artSpecs.ts）。
// 這些全是繪圖裝飾；點選、預覽與 `clientToTile` 仍以格子頂面為準，不受影響。
import type { DrawModel, TileDraw } from "./drawModel";
import { tileAt } from "./drawModel";

/** 高度差達此值的邊緣畫懸崖線。 */
export const CLIFF_MIN_DIFF = 2;

export type Side = "south" | "east" | "west" | "north";

/** 懸崖線：高格 (x, y) 的某一邊鄰格低 ≥ 2。 */
export interface CliffEdge {
  x: number;
  y: number;
  side: Side;
  diff: number;
}

export interface HeightDecor {
  cliffs: CliffEdge[];
}

const STEPS: ReadonlyArray<{ side: Side; dx: number; dy: number }> = [
  { side: "south", dx: 0, dy: 1 },
  { side: "east", dx: 1, dy: 0 },
  { side: "west", dx: -1, dy: 0 },
  { side: "north", dx: 0, dy: -1 },
];

/** 只有能站立的格子（非深淵、岩漿等阻擋地形）參與高度比較；牆與阻擋地形不畫懸崖線。 */
function standable(t: TileDraw | undefined): t is TileDraw {
  return t !== undefined && !t.blocked;
}

function neighbor(model: DrawModel, t: TileDraw, dx: number, dy: number): TileDraw | undefined {
  const x = t.x + dx;
  const y = t.y + dy;
  if (x < 0 || y < 0 || x >= model.width || y >= model.height) return undefined;
  return tileAt(model, { x, y });
}

/** 推導整張地圖的懸崖線；順序依格子由上到下、由左到右，結果確定。 */
export function heightDecor(model: DrawModel): HeightDecor {
  const out: HeightDecor = { cliffs: [] };
  for (const t of model.tiles) {
    if (!standable(t)) continue;
    for (const step of STEPS) {
      const n = neighbor(model, t, step.dx, step.dy);
      if (!standable(n)) continue;
      const diff = t.height - n.height;
      if (diff >= CLIFF_MIN_DIFF) out.cliffs.push({ x: t.x, y: t.y, side: step.side, diff });
    }
  }
  return out;
}

/** 單位底座陰影的大小係數（0 ＝ 不畫）：站在高處（高度 ≥ 1）才有，越高越大。 */
export function pedestalScale(height: number): number {
  if (height <= 0) return 0;
  return 0.6 + 0.12 * Math.min(3, height);
}
