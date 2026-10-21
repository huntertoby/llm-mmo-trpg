// 高度表現（Phase 3-14，方案 A）：由繪製模型推導「側面、懸崖線、投影、底座」（純函式；Pixi 只負責照著畫）。
// 這些全是繪圖裝飾，畫在相鄰的較低格上方；點選、預覽與 `clientToTile` 仍以格子頂面為準，不受影響。
import type { DrawModel, TileDraw } from "./drawModel";
import { tileAt } from "./drawModel";

/** 每一層高度差的側面厚度（模型像素），及上限。 */
export const SIDE_PX_PER_LEVEL = 6;
export const SIDE_MAX_PX = 18;
/** 高度差達此值的邊緣畫懸崖線。 */
export const CLIFF_MIN_DIFF = 2;
/** 高台投影到東側較低鄰格的寬度（每層高度差，模型像素）及上限。 */
export const SHADOW_PX_PER_LEVEL = 4;
export const SHADOW_MAX_PX = 12;

export type Side = "south" | "east" | "west" | "north";

/** 高格往下（南）畫的側面：畫在 (x, y+1) 那一格頂端，高 `thickness`。 */
export interface SideFace {
  x: number;
  y: number;
  diff: number;
  thickness: number;
  /** 這個高格的高度（決定側面顏色深淺）。 */
  height: number;
}

/** 懸崖線：高格 (x, y) 的某一邊鄰格低 ≥ 2。 */
export interface CliffEdge {
  x: number;
  y: number;
  side: Side;
  diff: number;
}

/** 高台投影到較低鄰格：畫在 (x, y) 的靠 `from` 那側。 */
export interface Shadow {
  x: number;
  y: number;
  from: Side;
  width: number;
}

export interface HeightDecor {
  sides: SideFace[];
  cliffs: CliffEdge[];
  shadows: Shadow[];
}

const STEPS: ReadonlyArray<{ side: Side; dx: number; dy: number }> = [
  { side: "south", dx: 0, dy: 1 },
  { side: "east", dx: 1, dy: 0 },
  { side: "west", dx: -1, dy: 0 },
  { side: "north", dx: 0, dy: -1 },
];

/** 只有能站立的格子（非深淵、岩漿等阻擋地形）參與高度比較；牆與阻擋地形不畫側面。 */
function standable(t: TileDraw | undefined): t is TileDraw {
  return t !== undefined && !t.blocked;
}

function neighbor(model: DrawModel, t: TileDraw, dx: number, dy: number): TileDraw | undefined {
  const x = t.x + dx;
  const y = t.y + dy;
  if (x < 0 || y < 0 || x >= model.width || y >= model.height) return undefined;
  return tileAt(model, { x, y });
}

export function sideThickness(diff: number): number {
  return Math.min(SIDE_MAX_PX, Math.max(0, diff) * SIDE_PX_PER_LEVEL);
}

export function shadowWidth(diff: number): number {
  return Math.min(SHADOW_MAX_PX, Math.max(0, diff) * SHADOW_PX_PER_LEVEL);
}

/** 推導整張地圖的高度裝飾；順序依格子由上到下、由左到右，結果確定。 */
export function heightDecor(model: DrawModel): HeightDecor {
  const out: HeightDecor = { sides: [], cliffs: [], shadows: [] };
  for (const t of model.tiles) {
    if (!standable(t)) continue;
    for (const step of STEPS) {
      const n = neighbor(model, t, step.dx, step.dy);
      if (!standable(n)) continue;
      const diff = t.height - n.height;
      if (diff <= 0) continue;
      if (step.side === "south") out.sides.push({ x: t.x, y: t.y, diff, thickness: sideThickness(diff), height: t.height });
      if (diff >= CLIFF_MIN_DIFF) out.cliffs.push({ x: t.x, y: t.y, side: step.side, diff });
      if (step.side === "east") out.shadows.push({ x: n.x, y: n.y, from: "west", width: shadowWidth(diff) });
    }
  }
  return out;
}

/** 單位底座陰影的大小係數（0 ＝ 不畫）：站在高處（高度 ≥ 1）才有，越高越大。 */
export function pedestalScale(height: number): number {
  if (height <= 0) return 0;
  return 0.6 + 0.12 * Math.min(3, height);
}
