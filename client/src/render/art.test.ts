import { describe, expect, it, vi } from "vitest";
import type { DrawModel, ObjectDraw, TileDraw } from "../battle/drawModel";
import { heightBadgeText, objectArtSpec, objectKinds, tileArtSpec } from "./artSpecs";
import { drawObject, hasObjectArt, OBJECT_DRAW, objectArtKey, type ObjectArtSpec } from "./objectArt";
import { drawTile, hasSurfaceArt, hasTerrainArt, tileArtKey, TERRAIN_DRAW, type TileArtSpec } from "./terrainArt";
import { PAL } from "./artPalette";
import { hash } from "./artRandom";

/** 記錄所有呼叫的假 Canvas 2D：任何方法都可以呼叫、任何屬性都可以設定。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

function tile(x: number, y: number, over: Partial<TileDraw> = {}): TileDraw {
  return {
    x,
    y,
    height: 0,
    fill: 0x888888,
    heightLabel: "0",
    terrain: "stone",
    surface: "none",
    terrainName: "",
    surfaceName: null,
    blocked: false,
    deadly: false,
    wall: false,
    ...over,
  };
}

function model(rows: Array<Array<Partial<TileDraw>>>, objects: ObjectDraw[] = []): DrawModel {
  const tiles: TileDraw[] = [];
  rows.forEach((row, y) => row.forEach((o, x) => tiles.push(tile(x, y, o))));
  return { width: rows[0]?.length ?? 0, height: rows.length, tiles, objects, units: [], traps: [], auras: [], zones: [], wells: [] };
}

function obj(kind: string, x: number, y: number): ObjectDraw {
  return { id: `${kind}${x}${y}`, kind, x, y, name: kind, glyph: "?", fill: 0x888888, flammable: false, burning: false, expiresIn: null, floor: false, hpRatio: null };
}

const CHASM = { terrain: "chasm", blocked: true, deadly: true };
const WALL = { terrain: "wall", blocked: true, wall: true };

describe("tileArtSpec（高度與鄰格）", () => {
  it("高度只影響頂面亮度：崖面、陰影、描邊不在貼圖規格裡（3-19 改由 Pixi 畫）", () => {
    const m = model([[{ height: 3 }], [{ height: 0 }]]);
    const spec = tileArtSpec(m, m.tiles[0]!);
    expect(spec.height).toBe(3);
    for (const gone of ["drop", "shadowN", "shadowW", "lowerW", "lowerE"]) expect(spec).not.toHaveProperty(gone);
  });

  it("牆：南鄰不是牆才畫立面；深淵：四鄰非深淵才有崖緣；地圖外視為同種", () => {
    const m = model([[WALL], [WALL], [{}]]);
    expect(tileArtSpec(m, m.tiles[0]!).wallFace).toBe(false);
    expect(tileArtSpec(m, m.tiles[1]!).wallFace).toBe(true);
    const c = model([[CHASM, {}]]);
    expect(tileArtSpec(c, c.tiles[0]!).lip).toEqual({ n: false, s: false, w: false, e: true });
  });

  it("表面連成一片：四鄰同種表面的旗標", () => {
    const m = model([[{ surface: "oil" }, { surface: "oil" }, { surface: "water" }]]);
    expect(tileArtSpec(m, m.tiles[0]!).surfSame).toEqual({ n: false, s: false, w: false, e: true });
    expect(tileArtSpec(m, m.tiles[1]!).surfSame.w).toBe(true);
    expect(tileArtSpec(m, m.tiles[1]!).surfSame.e).toBe(false);
  });

  it("未知地形用石地畫法並帶 glossary 色調；已知地形沒有色調", () => {
    const m = model([[{ terrain: "brand_new_terrain" }, { terrain: "lava" }]]);
    expect(hasTerrainArt("brand_new_terrain")).toBe(false);
    expect(tileArtSpec(m, m.tiles[0]!).tint).not.toBeNull();
    expect(tileArtSpec(m, m.tiles[1]!).tint).toBeNull();
  });

  it("高度徽章只在可站立且高度 > 0 時出現", () => {
    const flat = model([[{ height: 0 }, { height: 0 }]]);
    expect(heightBadgeText(flat, flat.tiles[0]!)).toBeNull();
    // 3×3 高台：只有邊緣格（與鄰格不同高）標高度，中心與平地不標
    const rows = [0, 1, 2].map((y) => [0, 1, 2, 3, 4].map((x) => ({ height: x >= 1 && x <= 3 && y >= 0 && y <= 2 ? 2 : 0 })));
    const m = model(rows);
    const at = (x: number, y: number): string | null => heightBadgeText(m, m.tiles.find((t) => t.x === x && t.y === y)!);
    expect(at(2, 1)).toBeNull();
    expect(at(1, 1)).toBe("2");
    expect(at(2, 2)).toBeNull(); // 地圖邊緣外不算鄰格
    expect(at(1, 0)).toBe("2");
    expect(at(0, 0)).toBeNull();
    const pit = model([[{ height: 2, ...CHASM }, {}]]);
    expect(heightBadgeText(pit, pit.tiles[0]!)).toBeNull();
  });
});

describe("tileArtKey", () => {
  it("相同規格相同鍵；座標、高度、表面、鄰格遮罩不同則鍵不同", () => {
    const m = model([[{ height: 1 }, {}], [{}, {}]]);
    const a = tileArtSpec(m, m.tiles[0]!);
    expect(tileArtKey(a)).toBe(tileArtKey({ ...a }));
    for (const change of [{ x: 5 }, { height: 3 }, { surface: "fire" }, { wallFace: true }, { tint: 1 }] as Array<Partial<TileArtSpec>>) {
      expect(tileArtKey({ ...a, ...change })).not.toBe(tileArtKey(a));
    }
  });
});

describe("程式繪製（假 Canvas）", () => {
  const base = tileArtSpec(model([[{}]]), tile(0, 0));
  const terrains = [...Object.keys(TERRAIN_DRAW), "brand_new_terrain"];
  const surfaces = ["none", "oil", "water", "fire", "ice", "poison", "holy", "darkness", "smoke", "brand_new_surface"];

  it("每種地形 × 每種表面（含未知）都畫得出來、不丟例外", () => {
    for (const terrain of terrains) {
      for (const surface of surfaces) {
        const { ctx, calls } = mockCtx();
        expect(() => drawTile(ctx, { ...base, terrain, surface, height: 2, wallFace: true, lip: { n: true, s: true, w: true, e: true }, tint: hasTerrainArt(terrain) ? null : 0xff00ff })).not.toThrow();
        expect(calls.length).toBeGreaterThan(5);
      }
    }
    expect(hasSurfaceArt("smoke")).toBe(true);
    expect(hasSurfaceArt("brand_new_surface")).toBe(false);
  });

  it("每種物件（含未知種類、可燃、相連、直向）都畫得出來", () => {
    const kinds = [...Object.keys(OBJECT_DRAW), "brand_new_object"];
    for (const kind of kinds) {
      for (const flammable of [false, true]) {
        const spec: ObjectArtSpec = { kind, x: 3, y: 4, joinL: true, joinR: false, vertical: true, flammable };
        const { ctx, calls } = mockCtx();
        expect(() => drawObject(ctx, spec)).not.toThrow();
        expect(calls.length).toBeGreaterThan(3);
      }
    }
    // 內建的 13 種物件都有畫法，未知的退回灰色六角形
    for (const k of ["wooden_bridge", "oil_barrel", "thin_ice", "stone_pillar", "grass", "crate", "earth_wall", "low_wall", "fallen_log", "dead_tree", "rubble", "ice_wall", "thorn_wall"]) {
      expect(hasObjectArt(k), k).toBe(true);
    }
    expect(hasObjectArt("brand_new_object")).toBe(false);
  });

  it("確定性：同規格畫兩次呼叫序列一致，不同座標不同；不使用 Math.random", () => {
    const spy = vi.spyOn(Math, "random");
    const run = (x: number): string[] => {
      const { ctx, calls } = mockCtx();
      drawTile(ctx, { ...base, terrain: "stone", x, y: 2 });
      return calls;
    };
    expect(run(1)).toEqual(run(1));
    expect(run(1)).not.toEqual(run(7));
    const o = (): string[] => {
      const { ctx, calls } = mockCtx();
      drawObject(ctx, { kind: "rubble", x: 2, y: 2, joinL: false, joinR: false, vertical: false, flammable: false });
      return calls;
    };
    expect(o()).toEqual(o());
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
    expect(hash(1, 2, 3)).toBe(hash(1, 2, 3));
  });

  it("色票鍵都是合法色碼", () => {
    for (const v of Object.values(PAL)) expect(v).toMatch(/^#[0-9a-f]{6}$/);
  });
});

describe("objectArtSpec（鄰格相依）", () => {
  it("矮牆左右相連、橋依鄰格決定方向、可燃旗標帶入", () => {
    const m = model([[{}, {}, {}], [{}, {}, {}], [{}, {}, {}]], [obj("low_wall", 0, 0), obj("low_wall", 1, 0), obj("wooden_bridge", 1, 1), obj("wooden_bridge", 1, 2)]);
    const kinds = objectKinds(m);
    const [w0, w1, b1, b2] = m.objects;
    expect(objectArtSpec(w0!, kinds)).toMatchObject({ joinL: false, joinR: true });
    expect(objectArtSpec(w1!, kinds)).toMatchObject({ joinL: true, joinR: false });
    expect(objectArtSpec(b1!, kinds).vertical).toBe(true);
    expect(objectArtSpec(b2!, kinds).vertical).toBe(true);
    expect(objectArtSpec({ ...w0!, flammable: true }, kinds).flammable).toBe(true);
    expect(objectArtKey(objectArtSpec(w0!, kinds))).not.toBe(objectArtKey(objectArtSpec(w1!, kinds)));
  });

  it("單獨的橋是橫向", () => {
    const m = model([[{}]], [obj("wooden_bridge", 0, 0)]);
    expect(objectArtSpec(m.objects[0]!, objectKinds(m)).vertical).toBe(false);
  });
});
