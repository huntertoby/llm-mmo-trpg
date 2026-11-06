// 範圍技畫在地圖內（Phase 6F-6，巡檢 bug 13：聖光爆發的光柱畫在地圖外的深色邊和頂列 HUD 下方）。純函式。
// - 範圍預覽（移動格、施放範圍、影響範圍、目標框…）：地圖外的格子不畫；
// - 地上的特效（範圍每格的爆發與閃光、聖光的光柱、落在目標格的片段特效）：裁在地圖的矩形內（`mapClipRect`），
//   跟著人的特效（蓄力、刀光、飛行物、受擊、浮動字）不裁，最上面一排的人頭頂照舊看得到。
import type { Pos } from "../api/types";
import { tileLift, type HeightGrid } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";

/** 這一格在地圖內。 */
export function insideMap(grid: { width: number; height: number }, p: Pos): boolean {
  return p.x >= 0 && p.y >= 0 && p.x < grid.width && p.y < grid.height;
}

/** 只留地圖內的格子（順序不變）。 */
export function clipTiles<T extends { x: number; y: number }>(grid: { width: number; height: number }, tiles: readonly T[]): T[] {
  return tiles.filter((p) => insideMap(grid, p));
}

/** 範圍預覽裡跟格子有關的欄位（`BattleRenderer.Highlights` 的子集）。 */
export interface TileHighlights {
  moves: readonly Pos[];
  attacks: readonly Pos[];
  preview: readonly Pos[];
  picked: readonly Pos[];
  directions: readonly { pos: Pos }[];
  telegraph: readonly { pos: Pos }[];
  range?: readonly Pos[];
}

/** 範圍預覽只畫地圖內的格子（移動、目標、影響範圍、施放範圍、方向、選好的物件、環境預告）。 */
export function clipHighlights<H extends TileHighlights>(grid: { width: number; height: number }, h: H): H {
  const at = <T extends { pos: Pos }>(xs: readonly T[]) => xs.filter((m) => insideMap(grid, m.pos));
  return {
    ...h,
    moves: clipTiles(grid, h.moves),
    attacks: clipTiles(grid, h.attacks),
    preview: clipTiles(grid, h.preview),
    picked: clipTiles(grid, h.picked),
    directions: at(h.directions),
    telegraph: at(h.telegraph),
    ...(h.range === undefined ? {} : { range: clipTiles(grid, h.range) }),
  };
}

/**
 * 地上特效的裁切矩形（世界座標，同 `tileOrigin`）：左右、下緣 ＝ 地圖邊；上緣 ＝ 第一排最高那格抬高後的頂面
 * （平地是 0）。畫布上方給頭頂預留的那一條（`topReserve`）不算地圖。
 */
export function mapClipRect(grid: HeightGrid, tile = TILE_SIZE): { x: number; y: number; width: number; height: number } {
  let lift = 0;
  for (let x = 0; x < grid.width; x++) lift = Math.max(lift, tileLift(grid.tiles?.[x]?.height ?? 0));
  return { x: 0, y: lift === 0 ? 0 : -lift, width: grid.width * tile, height: grid.height * tile + lift };
}
