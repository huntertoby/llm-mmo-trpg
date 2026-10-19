// 格子 ↔ 像素的座標換算（純函式）。原點在左上角，x 向右、y 向下（與引擎相同）。
import type { Pos } from "../api/types";

export const TILE_SIZE = 52;

export interface GridSize {
  width: number;
  height: number;
}

export function posKey(p: Pos): string {
  return `${p.x},${p.y}`;
}

export function samePos(a: Pos, b: Pos): boolean {
  return a.x === b.x && a.y === b.y;
}

/** 格子左上角的像素座標。 */
export function tileOrigin(p: Pos, tile = TILE_SIZE): { x: number; y: number } {
  return { x: p.x * tile, y: p.y * tile };
}

/** 格子中心的像素座標。 */
export function tileCenter(p: Pos, tile = TILE_SIZE): { x: number; y: number } {
  return { x: p.x * tile + tile / 2, y: p.y * tile + tile / 2 };
}

/** 畫布上的點 → 格子；在格子範圍外回傳 `null`。 */
export function pixelToTile(px: number, py: number, grid: GridSize, tile = TILE_SIZE): Pos | null {
  if (px < 0 || py < 0) return null;
  const x = Math.floor(px / tile);
  const y = Math.floor(py / tile);
  if (x >= grid.width || y >= grid.height) return null;
  return { x, y };
}

export function canvasSize(grid: GridSize, tile = TILE_SIZE): { width: number; height: number } {
  return { width: grid.width * tile, height: grid.height * tile };
}
