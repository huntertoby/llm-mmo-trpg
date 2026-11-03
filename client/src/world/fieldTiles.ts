// 實地地圖的靜態地形快取（6C-R3）：世界畫面的 `field` 只帶 `tiles_hash` 與 `open_cells`，地形另外向
// `GET /api/world/fields/{map_id}?h=…` 取一次，依雜湊存在記憶體裡；之後同一張圖（內容沒變）不再下載。
import type { FieldView, WorldView } from "../api/types";

type Tiles = FieldView["tiles"];

/** 取靜態地形（`client.ts` 傳 `GET /api/world/fields/{map_id}?h=…`）。 */
export type TilesFetcher = (mapId: string, hash: string) => Promise<{ hash: string; tiles: Tiles }>;

const cache = new Map<string, Tiles>();

/** 測試用：清掉快取。 */
export function clearTilesCache(): void {
  cache.clear();
}

/** 快取裡的地形數（測試用）。 */
export function cachedTilesCount(): number {
  return cache.size;
}

/** 靜態地形套上這個角色站得上去的格子（已發現的隱藏門）。 */
export function withOpenCells(tiles: Tiles, open: readonly (readonly number[])[]): Tiles {
  if (open.length === 0) return tiles;
  const keys = new Set(open.map(([x, y]) => `${x},${y}`));
  return tiles.map((t) => (keys.has(`${t.x},${t.y}`) ? { ...t, walkable: true } : t));
}

/** 世界畫面的 `field` 沒帶地形時補上（依 `tiles_hash` 快取）；已經帶了或沒有實地地圖就原樣回傳。 */
export async function hydrateField(view: WorldView, fetchTiles: TilesFetcher): Promise<WorldView> {
  const field = view.field;
  if (field == null || field.tiles.length > 0 || !field.tiles_hash) return view;
  let tiles = cache.get(field.tiles_hash);
  if (tiles === undefined) {
    const got = await fetchTiles(field.map_id, field.tiles_hash);
    tiles = got.tiles;
    cache.set(got.hash, tiles);
    cache.set(field.tiles_hash, tiles);
  }
  return { ...view, field: { ...field, tiles: withOpenCells(tiles, field.open_cells ?? []) } };
}
