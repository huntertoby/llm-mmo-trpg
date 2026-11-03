// 6C-R3：世界畫面的實地地形依雜湊快取、套上已發現的隱藏門。6D-R1：只用回傳的 hash 存快取、合併同時
// 請求、失敗重試一次後請伺服器直接帶地形。
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { FieldView, WorldView } from "../api/types";
import { cachedTilesCount, clearTilesCache, hydrateField, withOpenCells } from "./fieldTiles";

type Tiles = FieldView["tiles"];

const TILES: Tiles = [
  { x: 0, y: 0, height: 0, terrain: "stone", surface: "none", walkable: true },
  { x: 1, y: 0, height: 0, terrain: "wall", surface: "none", walkable: false },
];
const DOOR = { x: 1, y: 0, height: 1, terrain: "dirt", surface: "none", walkable: true };

function view(field: Partial<FieldView> | null): WorldView {
  const f = field === null ? null : ({ map_id: "m", tiles: [], tiles_hash: "h1", open_cells: [], ...field } as FieldView);
  return { character: { character_id: "c1" }, field: f } as unknown as WorldView;
}

describe("hydrateField", () => {
  beforeEach(() => clearTilesCache());

  it("同一個雜湊只下載一次", async () => {
    const fetch = vi.fn(async () => ({ hash: "h1", tiles: TILES }));
    const a = await hydrateField(view({}), fetch);
    const b = await hydrateField(view({}), fetch);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("c1", "m", "h1");
    expect(a.field?.tiles).toEqual(TILES);
    expect(b.field?.tiles).toEqual(TILES);
    expect(cachedTilesCount()).toBe(1);
  });

  it("雜湊不同就重新下載", async () => {
    const fetch = vi.fn(async (_c: string, _m: string, h: string) => ({ hash: h, tiles: TILES }));
    await hydrateField(view({}), fetch);
    await hydrateField(view({ tiles_hash: "h2" }), fetch);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("只用伺服器回傳的 hash 存快取", async () => {
    const fetch = vi.fn(async () => ({ hash: "h2", tiles: TILES }));
    const got = await hydrateField(view({ tiles_hash: "h1" }), fetch);
    expect(got.field?.tiles).toEqual(TILES);
    expect(cachedTilesCount()).toBe(1);
    await hydrateField(view({ tiles_hash: "h2" }), fetch); // 回傳的 h2 命中快取
    expect(fetch).toHaveBeenCalledTimes(1);
    await hydrateField(view({ tiles_hash: "h1" }), fetch); // 請求的 h1 沒存
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("同時的請求合併成一個", async () => {
    let release: (v: { hash: string; tiles: Tiles }) => void = () => {};
    const fetch = vi.fn(() => new Promise<{ hash: string; tiles: Tiles }>((r) => (release = r)));
    const both = Promise.all([hydrateField(view({}), fetch), hydrateField(view({}), fetch)]);
    release({ hash: "h1", tiles: TILES });
    const [a, b] = await both;
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(a.field?.tiles).toEqual(TILES);
    expect(b.field?.tiles).toEqual(TILES);
  });

  it("失敗時重試一次", async () => {
    const fetch = vi
      .fn<(c: string, m: string, h: string) => Promise<{ hash: string; tiles: Tiles }>>()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({ hash: "h1", tiles: TILES });
    const inline = vi.fn(async () => view({ tiles: TILES }));
    const got = await hydrateField(view({}), fetch, inline);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(inline).not.toHaveBeenCalled();
    expect(got.field?.tiles).toEqual(TILES);
  });

  it("重試仍失敗就請伺服器直接帶地形", async () => {
    const fetch = vi.fn(async () => {
      throw new Error("network");
    });
    const full = view({ tiles: TILES });
    const inline = vi.fn(async () => full);
    expect(await hydrateField(view({}), fetch, inline)).toBe(full);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(inline).toHaveBeenCalledWith("c1");
    expect(cachedTilesCount()).toBe(0);
    await expect(hydrateField(view({}), fetch)).rejects.toThrow("取不到");
  });

  it("已發現的隱藏門蓋上真地形（快取裡的不變）", async () => {
    const fetch = vi.fn(async () => ({ hash: "h1", tiles: TILES }));
    const got = await hydrateField(view({ open_cells: [DOOR] }), fetch);
    expect(got.field?.tiles[1]).toEqual(DOOR);
    const again = await hydrateField(view({}), fetch);
    expect(again.field?.tiles[1]?.terrain).toBe("wall");
    expect(again.field?.tiles[1]?.walkable).toBe(false);
  });

  it("已經帶地形或沒有實地地圖時原樣回傳", async () => {
    const fetch = vi.fn(async () => ({ hash: "h1", tiles: TILES }));
    const inline = view({ tiles: TILES });
    expect(await hydrateField(inline, fetch)).toBe(inline);
    const none = view(null);
    expect(await hydrateField(none, fetch)).toBe(none);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("withOpenCells 沒有格子時回傳同一份", () => {
    expect(withOpenCells(TILES, [])).toBe(TILES);
  });
});
