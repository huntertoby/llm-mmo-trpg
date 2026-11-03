// 6C-R3：世界畫面的實地地形依雜湊快取、套上已發現的隱藏門。
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { FieldView, WorldView } from "../api/types";
import { cachedTilesCount, clearTilesCache, hydrateField, withOpenCells } from "./fieldTiles";

type Tiles = FieldView["tiles"];

const TILES: Tiles = [
  { x: 0, y: 0, height: 0, terrain: "stone", surface: "none", walkable: true },
  { x: 1, y: 0, height: 0, terrain: "stone", surface: "none", walkable: false },
];

function view(field: Partial<FieldView> | null): WorldView {
  const f = field === null ? null : ({ map_id: "m", tiles: [], tiles_hash: "h1", open_cells: [], ...field } as FieldView);
  return { field: f } as unknown as WorldView;
}

describe("hydrateField", () => {
  beforeEach(() => clearTilesCache());

  it("同一個雜湊只下載一次", async () => {
    const fetch = vi.fn(async () => ({ hash: "h1", tiles: TILES }));
    const a = await hydrateField(view({}), fetch);
    const b = await hydrateField(view({}), fetch);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("m", "h1");
    expect(a.field?.tiles).toEqual(TILES);
    expect(b.field?.tiles).toEqual(TILES);
    expect(cachedTilesCount()).toBe(1);
  });

  it("雜湊不同就重新下載", async () => {
    const fetch = vi.fn(async (_m: string, h: string) => ({ hash: h, tiles: TILES }));
    await hydrateField(view({}), fetch);
    await hydrateField(view({ tiles_hash: "h2" }), fetch);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("已發現的隱藏門套成站得上去（快取裡的不變）", async () => {
    const fetch = vi.fn(async () => ({ hash: "h1", tiles: TILES }));
    const got = await hydrateField(view({ open_cells: [[1, 0]] }), fetch);
    expect(got.field?.tiles[1]?.walkable).toBe(true);
    const again = await hydrateField(view({}), fetch);
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
