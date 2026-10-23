import { describe, expect, it } from "vitest";
import { buildDrawModel } from "../battle/drawModel";
import { smallView } from "../battle/testFixtures";
import { DEFAULT_THEME, lookKey, lookValue, mistLevel, pickThemed, themeKey, themeOf, waterTintOf } from "./regionArt";
import { drawMistTile } from "./cloudRidgeTerrain";
import { drawFlammableMark, drawObject, objectArtKey, OBJECT_DRAW, type ObjectArtSpec } from "./objectArt";
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
    { region: "", look: "wall=marble,floor=lava" },
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

// ---- 3-37b 雲嶺 ----

const TERRAINS = Object.keys(TERRAIN_DRAW);
const OBJECTS = Object.keys(OBJECT_DRAW);
const RESKINNED_OBJECTS = ["crate", "low_wall", "stone_pillar", "oil_barrel", "fallen_log", "grass", "wooden_bridge", "dead_tree", "thin_ice"];
const SKILL_OBJECTS = ["ice_wall", "thorn_wall", "earth_wall", "rubble"];
const CLOUD = { region: "cloud_ridge", look: "" };

/** 預設主題下「沒有表面」的格子呼叫數（用來切出表面疊上去的那一段）。 */
function plainTileCalls(): number {
  const m = mockCtx();
  drawTile(m.ctx, tileSpec({ surface: "none" }));
  return m.calls.length;
}

describe("雲嶺換皮", () => {
  it("7 種地形都換了畫法（呼叫序列與預設不同），任何邊組合都畫得出來", () => {
    expect(TERRAINS).toHaveLength(7);
    for (const terrain of TERRAINS) {
      const ref = mockCtx();
      drawTile(ref.ctx, tileSpec({ terrain, wallFace: true }));
      const got = mockCtx();
      expect(() => drawTile(got.ctx, tileSpec({ terrain, wallFace: true, ...CLOUD }))).not.toThrow();
      expect(got.calls, terrain).not.toEqual(ref.calls);
      for (const lip of [{ n: false, s: false, w: false, e: false }, { n: true, s: true, w: true, e: true }]) {
        expect(() => drawTile(mockCtx().ctx, tileSpec({ terrain, lip, ...CLOUD }))).not.toThrow();
      }
    }
  });

  it("9 種物件都換了畫法；技能產生的物件（冰牆、荊棘叢、土牆、倒塌物）與預設完全一樣", () => {
    for (const kind of RESKINNED_OBJECTS) {
      const ref = mockCtx();
      drawObject(ref.ctx, objSpec({ kind, hpStage: 1 }));
      const got = mockCtx();
      expect(() => drawObject(got.ctx, objSpec({ kind, hpStage: 1, ...CLOUD }))).not.toThrow();
      expect(got.calls, kind).not.toEqual(ref.calls);
    }
    for (const kind of SKILL_OBJECTS) {
      const ref = mockCtx();
      drawObject(ref.ctx, objSpec({ kind, hpStage: 1, turnsLeft: 1 }));
      const got = mockCtx();
      drawObject(got.ctx, objSpec({ kind, hpStage: 1, turnsLeft: 1, ...CLOUD }));
      expect(got.calls, kind).toEqual(ref.calls);
    }
    expect(OBJECTS).toEqual(expect.arrayContaining([...RESKINNED_OBJECTS, ...SKILL_OBJECTS]));
  });

  it("功能特徵保留：可燃小火苗獨立成貼圖、受損仍有裂痕（薄冰自己畫裂痕）、橋可橫可直", () => {
    const plain = mockCtx();
    drawObject(plain.ctx, objSpec({ kind: "crate", flammable: false, ...CLOUD }));
    const burnable = mockCtx();
    drawObject(burnable.ctx, objSpec({ kind: "crate", flammable: true, ...CLOUD }));
    // 3-38：小火苗是獨立貼圖，不再畫進物件貼圖
    expect(burnable.calls).toEqual(plain.calls);
    expect(objectArtKey(objSpec({ kind: "crate", flammable: true }))).toBe(objectArtKey(objSpec({ kind: "crate", flammable: false })));
    const mark = mockCtx();
    drawFlammableMark(mark.ctx);
    expect(mark.calls.length).toBeGreaterThan(3);
    const hurt = mockCtx();
    drawObject(hurt.ctx, objSpec({ kind: "crate", flammable: false, hpStage: 2, ...CLOUD }));
    expect(hurt.calls.length).toBeGreaterThan(plain.calls.length);
    const h = mockCtx();
    drawObject(h.ctx, objSpec({ kind: "wooden_bridge", vertical: false, ...CLOUD }));
    const v = mockCtx();
    drawObject(v.ctx, objSpec({ kind: "wooden_bridge", vertical: true, ...CLOUD }));
    expect(v.calls).not.toEqual(h.calls);
    for (const hpStage of [0, 1, 2] as const) {
      expect(() => drawObject(mockCtx().ctx, objSpec({ kind: "thin_ice", hpStage, ...CLOUD }))).not.toThrow();
    }
  });

  it("牆比單位高：有立面的牆比沒立面的多畫一段", () => {
    const base = mockCtx();
    drawTile(base.ctx, tileSpec({ terrain: "wall", wallFace: false, ...CLOUD }));
    const face = mockCtx();
    drawTile(face.ctx, tileSpec({ terrain: "wall", wallFace: true, ...CLOUD }));
    expect(face.calls.length).toBeGreaterThan(base.calls.length);
  });

  it("look 覆寫生效：canyon_rock（牆）、plank_walk 與 paddy（地板）各自換畫法，且優先於區域", () => {
    const calls = (over: Partial<TileArtSpec>): string[] => {
      const m = mockCtx();
      drawTile(m.ctx, tileSpec(over));
      return m.calls;
    };
    expect(calls({ terrain: "wall", look: "wall=canyon_rock" })).not.toEqual(calls({ terrain: "wall" }));
    expect(calls({ terrain: "wall", ...CLOUD, look: "wall=canyon_rock" })).toEqual(calls({ terrain: "wall", look: "wall=canyon_rock" }));
    for (const floor of ["plank_walk", "paddy"]) {
      for (const terrain of ["stone", "grass", "dirt"]) {
        const look = `floor=${floor}`;
        expect(calls({ terrain, look }), `${floor}/${terrain}`).not.toEqual(calls({ terrain }));
        expect(calls({ terrain, region: "cloud_ridge", look })).toEqual(calls({ terrain, look }));
      }
    }
    // 牆不受 floor 覆寫影響；地板不受 wall 覆寫影響
    expect(calls({ terrain: "wall", look: "floor=paddy" })).toEqual(calls({ terrain: "wall" }));
    expect(calls({ terrain: "stone", look: "wall=canyon_rock" })).toEqual(calls({ terrain: "stone" }));
    // 快取鍵區分
    expect(tileArtKey(tileSpec({ look: "floor=paddy" }))).not.toBe(tileArtKey(tileSpec({ look: "floor=plank_walk" })));
  });

  it("water_tint 只換水面底色，水面反光線與其他表面不變", () => {
    expect(waterTintOf("water_tint=green")).toBe("#4f9a62");
    expect(waterTintOf("floor=paddy,water_tint=green")).toBe("#4f9a62");
    expect(waterTintOf("water_tint=purple")).toBeUndefined();
    expect(waterTintOf("")).toBeUndefined();
    expect(lookValue("a=b,water_tint=green", "water_tint")).toBe("green");
    expect(lookValue("a=b", "c")).toBeUndefined();
    const surface = (name: string, look: string): string[] => {
      const m = mockCtx();
      drawTile(m.ctx, tileSpec({ surface: name, look }));
      return m.calls;
    };
    const plain = surface("water", "");
    const green = surface("water", "water_tint=green");
    expect(green).not.toEqual(plain);
    expect(green.length).toBe(plain.length); // 只有顏色不同，繪圖呼叫的數量與順序相同
    expect(surface("water", "water_tint=purple")).toEqual(plain); // 不認得的值 → 預設水色
    expect(surface("fire", "water_tint=green")).toEqual(surface("fire", ""));
  });

  it("表面在雲嶺與預設完全一樣（疊在地形之後的那一段呼叫序列相同）", () => {
    const base = plainTileCalls();
    for (const surface of ["fire", "ice", "poison", "holy", "darkness", "smoke", "oil", "water"]) {
      const ref = mockCtx();
      drawTile(ref.ctx, tileSpec({ surface }));
      const got = mockCtx();
      drawTile(got.ctx, tileSpec({ surface, ...CLOUD }));
      const refTail = ref.calls.slice(base - 3); // 表面（S）＋格線（3 個呼叫）；地形與高度明暗在前
      expect(refTail.length).toBeGreaterThan(3);
      expect(got.calls.slice(-refTail.length), surface).toEqual(refTail);
    }
  });

  it("薄霧：只有雲嶺有；霧天比平常濃；其他區域與未知區域沒有", () => {
    const normal = mistLevel("cloud_ridge", "");
    const fog = mistLevel("cloud_ridge", "fog");
    expect(normal?.level).toBe("normal");
    expect(fog?.level).toBe("fog");
    expect(fog!.alpha).toBeGreaterThan(normal!.alpha);
    expect(mistLevel("cloud_ridge", "rain")).toEqual(normal);
    for (const region of ["", "crystal_crown", "nowhere", "constructor"]) expect(mistLevel(region, "fog")).toBeNull();
    for (const x of [0, 3, 9]) expect(() => drawMistTile(mockCtx().ctx, x, 2, 0.4)).not.toThrow();
  });

  it("buildDrawModel 帶出天氣", () => {
    expect(buildDrawModel(smallView(), "unit_0001").weather).toBe("");
    expect(buildDrawModel({ ...smallView(), weather_id: "fog", weather_name_zh: "霧" }, "unit_0001").weather).toBe("fog");
  });
});
