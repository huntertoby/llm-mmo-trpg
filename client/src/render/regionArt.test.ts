import { describe, expect, it } from "vitest";
import { buildDrawModel } from "../battle/drawModel";
import { smallView } from "../battle/testFixtures";
import { DEFAULT_THEME, lookKey, pickThemed, themeKey, themeOf } from "./regionArt";
import { drawObject, objectArtKey, OBJECT_DRAW, type ObjectArtSpec } from "./objectArt";
import { drawTile, tileArtKey, TERRAIN_DRAW, type TileArtSpec } from "./terrainArt";
import { objectArtSpec, tileArtSpec } from "./artSpecs";

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

const tileSpec = (over: Partial<TileArtSpec> = {}): TileArtSpec => ({
  ...DEFAULT_THEME,
  terrain: "stone",
  x: 1,
  y: 2,
  height: 1,
  surface: "none",
  surfSame: { n: false, s: false, w: false, e: false },
  lip: { n: true, s: false, w: false, e: true },
  wallFace: false,
  blocked: false,
  tint: null,
  ...over,
});

const objSpec = (over: Partial<ObjectArtSpec> = {}): ObjectArtSpec => ({
  ...DEFAULT_THEME,
  kind: "crate",
  x: 2,
  y: 3,
  joinL: false,
  joinR: false,
  vertical: false,
  flammable: true,
  turnsLeft: null,
  hpStage: 0,
  ...over,
});

describe("區域主題欄位", () => {
  it("lookKey 正規化：鍵排序、略過非字串、空 → 空字串", () => {
    expect(lookKey({ wall: "canyon_rock", floor: "paddy" })).toBe("floor=paddy,wall=canyon_rock");
    expect(lookKey({})).toBe("");
    expect(lookKey(null)).toBe("");
    expect(lookKey(undefined)).toBe("");
    expect(lookKey({ a: 3 })).toBe("");
  });

  it("themeOf：缺漏 → 預設", () => {
    expect(themeOf({})).toEqual(DEFAULT_THEME);
    expect(themeOf({ region: null, look: null })).toEqual(DEFAULT_THEME);
    expect(themeOf({ region: "cloud_ridge", look: { floor: "paddy" } })).toEqual({ region: "cloud_ridge", look: "floor=paddy" });
  });

  it("buildDrawModel 帶出 region 與 look", () => {
    const plain = buildDrawModel(smallView(), "unit_0001");
    expect(plain.region).toBe("");
    expect(plain.look).toBe("");
    const themed = buildDrawModel({ ...smallView(), region: "cloud_ridge", look: { floor: "paddy" } }, "unit_0001");
    expect(themed.region).toBe("cloud_ridge");
    expect(themed.look).toBe("floor=paddy");
    // 規格與快取鍵跟著走
    const tile = themed.tiles[0]!;
    expect(tileArtSpec(themed, tile).region).toBe("cloud_ridge");
    expect(tileArtKey(tileArtSpec(themed, tile))).not.toBe(tileArtKey(tileArtSpec(plain, plain.tiles[0]!)));
  });

  it("快取鍵區分 region 與 look（格子與物件）", () => {
    const t = tileSpec();
    expect(tileArtKey({ ...t, region: "cloud_ridge" })).not.toBe(tileArtKey(t));
    expect(tileArtKey({ ...t, look: "wall=canyon_rock" })).not.toBe(tileArtKey(t));
    expect(tileArtKey({ ...t, region: "cloud_ridge" })).not.toBe(tileArtKey({ ...t, region: "frost_tide" }));
    const o = objSpec();
    expect(objectArtKey({ ...o, region: "cloud_ridge" })).not.toBe(objectArtKey(o));
    expect(objectArtKey({ ...o, look: "floor=paddy" })).not.toBe(objectArtKey(o));
    expect(themeKey({ region: "a", look: "b=c" })).toBe("a~b=c");
  });

  it("objectArtSpec 帶主題；省略 → 預設", () => {
    const o = { id: "o", kind: "crate", x: 0, y: 0, name: "", glyph: "", fill: 0, flammable: false, burning: false, expiresIn: null, floor: false, hpRatio: null };
    expect(objectArtSpec(o, new Map()).region).toBe("");
    expect(objectArtSpec(o, new Map(), { region: "cloud_ridge", look: "" }).region).toBe("cloud_ridge");
  });
});

describe("pickThemed", () => {
  const f = (): void => undefined;
  const g = (): void => undefined;
  const regions = { cloud_ridge: { wall: f } };
  const looks = { "floor=paddy": { stone: g } };

  it("區域表、look 表命中；look 優先", () => {
    expect(pickThemed({ region: "cloud_ridge", look: "" }, "wall", regions, looks)).toBe(f);
    expect(pickThemed({ region: "", look: "floor=paddy" }, "stone", regions, looks)).toBe(g);
    expect(pickThemed({ region: "cloud_ridge", look: "floor=paddy" }, "stone", regions, looks)).toBe(g);
  });

  it("查不到（預設、未知區域、未知 look、不是自己的屬性）→ undefined", () => {
    expect(pickThemed(DEFAULT_THEME, "wall", regions, looks)).toBeUndefined();
    expect(pickThemed({ region: "nowhere", look: "" }, "wall", regions, looks)).toBeUndefined();
    expect(pickThemed({ region: "cloud_ridge", look: "" }, "stone", regions, looks)).toBeUndefined();
    expect(pickThemed({ region: "", look: "wall=marble" }, "wall", regions, looks)).toBeUndefined();
    expect(pickThemed({ region: "constructor", look: "" }, "name", regions, looks)).toBeUndefined();
    expect(pickThemed({ region: "cloud_ridge", look: "" }, "constructor", regions, looks)).toBeUndefined();
  });
});

describe("未知的區域與 look 照預設畫（既有地圖畫面不變）", () => {
  const themes = [
    { region: "nowhere", look: "" },
    { region: "cloud_ridge", look: "" }, // 3-37a：雲嶺還沒有畫法表
    { region: "", look: "wall=marble,floor=paddy" },
    { region: "constructor", look: "toString=x" },
  ];

  it("每種地形（含未知）× 主題 ＝ 預設主題的繪圖呼叫", () => {
    for (const terrain of [...Object.keys(TERRAIN_DRAW), "brand_new_terrain"]) {
      const ref = mockCtx();
      drawTile(ref.ctx, tileSpec({ terrain, surface: "fire", wallFace: true }));
      for (const theme of themes) {
        const got = mockCtx();
        expect(() => drawTile(got.ctx, tileSpec({ terrain, surface: "fire", wallFace: true, ...theme }))).not.toThrow();
        expect(got.calls).toEqual(ref.calls);
      }
    }
  });

  it("每種物件（含未知）× 主題 ＝ 預設主題的繪圖呼叫", () => {
    for (const kind of [...Object.keys(OBJECT_DRAW), "brand_new_object"]) {
      const ref = mockCtx();
      drawObject(ref.ctx, objSpec({ kind, hpStage: 1 }));
      for (const theme of themes) {
        const got = mockCtx();
        expect(() => drawObject(got.ctx, objSpec({ kind, hpStage: 1, ...theme }))).not.toThrow();
        expect(got.calls).toEqual(ref.calls);
      }
    }
  });
});
