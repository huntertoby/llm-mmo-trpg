// 實地地圖的靜態地形快取（6C-R3）：世界畫面的 `field` 只帶 `tiles_hash` 與 `open_cells`，地形另外向
// `GET /api/world/characters/{id}/fields/{map_id}?h=…` 取一次，依雜湊存在記憶體裡；之後同一張圖（內容沒變）
// 不再下載。6D-R1：只用伺服器回傳的 `hash` 存快取；同時的請求合併成一個；取地形失敗時重試一次，仍失敗
// 就請伺服器直接帶地形（`GET …/characters/{id}?with_tiles=1`）。
import type { FieldView, WorldView } from "../api/types";

type Tiles = FieldView["tiles"];
type Got = { hash: string; tiles: Tiles };

/** 取靜態地形（`client.ts` 傳 `GET /api/world/characters/{id}/fields/{map_id}?h=…`）。 */
export type TilesFetcher = (characterId: string, mapId: string, hash: string) => Promise<Got>;

/** 退路：請伺服器直接帶地形的整份世界畫面（`GET /api/world/characters/{id}?with_tiles=1`）。 */
export type InlineFetcher = (characterId: string) => Promise<WorldView>;

const cache = new Map<string, Tiles>();
const inflight = new Map<string, Promise<Got>>();

/** 測試用：清掉快取（含進行中的請求）。 */
export function clearTilesCache(): void {
  cache.clear();
  inflight.clear();
}

/** 快取裡的地形數（測試用）。 */
export function cachedTilesCount(): number {
  return cache.size;
}

/** 靜態地形蓋上這個角色看到的格子（已發現的隱藏門：靜態地形畫成牆，`open` 是真地形；6D-R1）。 */
export function withOpenCells(tiles: Tiles, open: FieldView["open_cells"]): Tiles {
  if (open == null || open.length === 0) return tiles;
  const byCell = new Map(open.map((t) => [`${t.x},${t.y}`, t]));
  return tiles.map((t) => byCell.get(`${t.x},${t.y}`) ?? t);
}

/** 同一張圖、同一個雜湊同時只發一個請求（6D-R1）。 */
function fetchShared(fetchTiles: TilesFetcher, characterId: string, mapId: string, hash: string): Promise<Got> {
  const key = `${mapId}\u0000${hash}`;
  const running = inflight.get(key);
  if (running !== undefined) return running;
  const started = fetchTiles(characterId, mapId, hash).finally(() => inflight.delete(key));
  inflight.set(key, started);
  return started;
}

/** 取靜態地形：失敗重試一次；仍失敗＝`null`。快取的鍵只用伺服器回傳的 `hash`。 */
async function loadTiles(
  fetchTiles: TilesFetcher,
  characterId: string,
  mapId: string,
  hash: string,
): Promise<Tiles | null> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const got = await fetchShared(fetchTiles, characterId, mapId, hash);
      cache.set(got.hash, got.tiles);
      return got.tiles;
    } catch {
      // 第一次失敗重試一次；第二次失敗交給退路
    }
  }
  return null;
}

/** 世界畫面的 `field` 沒帶地形時補上（依 `tiles_hash` 快取）；已經帶了或沒有實地地圖就原樣回傳。
 * 取不到地形且有 `fetchInline` 時，改請伺服器直接帶地形（回傳那一份畫面）。 */
export async function hydrateField(
  view: WorldView,
  fetchTiles: TilesFetcher,
  fetchInline?: InlineFetcher,
): Promise<WorldView> {
  const field = view.field;
  if (field == null || field.tiles.length > 0 || !field.tiles_hash) return view;
  const characterId = view.character.character_id;
  const tiles = cache.get(field.tiles_hash) ?? (await loadTiles(fetchTiles, characterId, field.map_id, field.tiles_hash));
  if (tiles === null) {
    if (fetchInline === undefined) throw new Error(`取不到實地地圖 ${field.map_id} 的地形`);
    return fetchInline(characterId);
  }
  return { ...view, field: { ...field, tiles: withOpenCells(tiles, field.open_cells) } };
}
