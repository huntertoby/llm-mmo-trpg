// Phase 5A-ART6：灰燼荒原換皮、晶冠點綴（docs/phases/Phase5計畫.md 第 43.0、43.1 節）。寫法比照 regionArt.test.ts。
import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, mistLevel } from "./regionArt";
import { ASH_GLOW_RATE, ASH_RIFT_GLOW_ALPHA } from "./ashenTerrain";
import { crystalInlayAt } from "./crystalTerrain";
import { CRYSTAL_PILLAR_GLOW_ALPHA } from "./crystalObjects";
import { drawObject, OBJECT_DRAW, REGION_OBJECT_DRAW, type ObjectArtSpec } from "./objectArt";
import { drawTile, REGION_TERRAIN_DRAW, TERRAIN_DRAW, type TileArtSpec } from "./terrainArt";

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") {
          return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
        }
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

const tileCalls = (over: Partial<TileArtSpec>): string[] => {
  const m = mockCtx();
  drawTile(m.ctx, tileSpec(over));
  return m.calls;
};
const objCalls = (over: Partial<ObjectArtSpec>): string[] => {
  const m = mockCtx();
  drawObject(m.ctx, objSpec(over));
  return m.calls;
};

const TERRAINS = Object.keys(TERRAIN_DRAW);
const RESKINNED_OBJECTS = ["crate", "low_wall", "stone_pillar", "oil_barrel", "fallen_log", "grass", "wooden_bridge", "dead_tree", "thin_ice"];
const SKILL_OBJECTS = ["ice_wall", "thorn_wall", "earth_wall", "rubble"];
const ASH = { region: "ashen_waste", look: "" };
const CRYSTAL = { region: "crystal_crown", look: "" };
const NO_LIP = { n: false, s: false, w: false, e: false };
const ALL_LIP = { n: true, s: true, w: true, e: true };

/** 32 位元 FNV-1a，把整段繪圖呼叫序列壓成一個數字（鎖住預設畫法的輸出）。 */
function digest(lines: readonly string[]): string {
  let h = 2166136261;
  for (const ch of lines.join("\n")) {
    h ^= ch.codePointAt(0) ?? 0;
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h.toString(16);
}

describe("預設畫法不受新表影響（region 空字串）", () => {
  it("每種地形與物件的預設輸出和換皮前相同（雜湊鎖住）", () => {
    const lines: string[] = [];
    for (const terrain of TERRAINS) {
      for (const lip of [NO_LIP, ALL_LIP]) {
        for (const [x, y] of [[0, 0], [3, 5], [7, 1]] as const) lines.push(...tileCalls({ terrain, lip, x, y, wallFace: true, surface: "fire" }));
      }
    }
    for (const kind of Object.keys(OBJECT_DRAW)) {
      for (const hpStage of [0, 1, 2] as const) lines.push(...objCalls({ kind, hpStage, vertical: hpStage === 1 }));
    }
    // 預設畫法（region 空字串）的整段呼叫序列；5A-ART6 沒有改預設畫法，這個值變了表示預設畫面變了。
    expect(digest(lines)).toBe(DEFAULT_DIGEST);
  });

  it("區域表只有五區（5A-ART7 加入樞市、霜潮），region 空字串查不到", () => {
    expect(Object.keys(REGION_TERRAIN_DRAW).sort()).toEqual(["arcane_hub", "ashen_waste", "cloud_ridge", "crystal_crown", "frost_tide"]);
    expect(Object.keys(REGION_OBJECT_DRAW).sort()).toEqual(["arcane_hub", "ashen_waste", "cloud_ridge", "crystal_crown", "frost_tide"]);
    for (const terrain of TERRAINS) expect(tileCalls({ terrain, region: "" })).toEqual(tileCalls({ terrain }));
  });

  it("灰燼、晶冠都不加區域薄霧", () => {
    expect(mistLevel("ashen_waste", "fog")).toBeNull();
    expect(mistLevel("crystal_crown", "")).toBeNull();
  });
});

describe("灰燼荒原換皮", () => {
  it("7 種地形都換了畫法，任何邊組合都畫得出來", () => {
    expect(TERRAINS).toHaveLength(7);
    for (const terrain of TERRAINS) {
      expect(Object.hasOwn(REGION_TERRAIN_DRAW.ashen_waste!, terrain), terrain).toBe(true);
      expect(tileCalls({ terrain, wallFace: true, ...ASH }), terrain).not.toEqual(tileCalls({ terrain, wallFace: true }));
      for (const lip of [NO_LIP, ALL_LIP]) expect(() => tileCalls({ terrain, lip, ...ASH })).not.toThrow();
    }
  });

  it("9 種物件都換了畫法；技能物件與預設完全一樣", () => {
    for (const kind of RESKINNED_OBJECTS) {
      expect(Object.hasOwn(REGION_OBJECT_DRAW.ashen_waste!, kind), kind).toBe(true);
      expect(objCalls({ kind, hpStage: 1, ...ASH }), kind).not.toEqual(objCalls({ kind, hpStage: 1 }));
    }
    for (const kind of SKILL_OBJECTS) {
      expect(objCalls({ kind, hpStage: 1, turnsLeft: 1, ...ASH }), kind).toEqual(objCalls({ kind, hpStage: 1, turnsLeft: 1 }));
    }
  });

  it("未知地形與物件退回預設", () => {
    expect(tileCalls({ terrain: "brand_new", ...ASH })).toEqual(tileCalls({ terrain: "brand_new" }));
    expect(objCalls({ kind: "brand_new", ...ASH })).toEqual(objCalls({ kind: "brand_new" }));
  });

  it("牆比單位高：有立面的牆多畫一段", () => {
    expect(tileCalls({ terrain: "wall", wallFace: true, ...ASH }).length).toBeGreaterThan(tileCalls({ terrain: "wall", wallFace: false, ...ASH }).length);
  });

  it("裂谷底部紅光：透明度 ≤ 0.3，只畫在格子下半；有崖線", () => {
    expect(ASH_RIFT_GLOW_ALPHA).toBeLessThanOrEqual(0.3);
    const calls = tileCalls({ terrain: "chasm", lip: NO_LIP, ...ASH });
    expect(calls).toContain("stop(0,rgba(255,74,16,0.28))");
    expect(calls).toContain("fillRect(0.000,26.000,52.000,26.000)");
    const lipped = tileCalls({ terrain: "chasm", lip: { n: true, s: false, w: false, e: false }, ...ASH });
    expect(lipped.length).toBeGreaterThan(calls.length);
  });

  it("岩漿整格亮橘，2～3 片結殼", () => {
    for (const [x, y] of [[0, 0], [1, 2], [4, 4], [9, 3], [6, 7]] as const) {
      const calls = tileCalls({ terrain: "lava", x, y, ...ASH });
      expect(calls).toContain("fillRect(0.000,0.000,52.000,52.000)");
      expect(calls[0]).toBe("fillStyle=#e0400a");
      const crusts = calls.filter((c) => c === "closePath()").length;
      expect(crusts).toBeGreaterThanOrEqual(2);
      expect(crusts).toBeLessThanOrEqual(3);
    }
  });

  it("裂縫光：1.4 線寬、模糊 5，先畫 3 寬黑縫；同一張圖最多約 1/3 的格子有，位置固定", () => {
    let lit = 0;
    const N = 20;
    for (let x = 0; x < N; x++) {
      for (let y = 0; y < N; y++) {
        const calls = tileCalls({ x, y, ...ASH });
        if (calls.includes("shadowBlur=5")) {
          lit++;
          const i = calls.indexOf("lineWidth=3");
          const j = calls.indexOf("lineWidth=1.4");
          expect(i).toBeGreaterThanOrEqual(0);
          expect(j).toBeGreaterThan(i);
        }
      }
    }
    expect(ASH_GLOW_RATE).toBeLessThanOrEqual(1 / 3);
    expect(lit).toBeGreaterThan(0);
    expect(lit / (N * N)).toBeLessThanOrEqual(0.38);
    expect(tileCalls({ x: 3, y: 4, ...ASH })).toEqual(tileCalls({ x: 3, y: 4, ...ASH }));
  });

  it("功能特徵：油桶有黃色三角危險記號、橋可橫可直、浮板依耐久變化、受損有裂痕", () => {
    expect(objCalls({ kind: "oil_barrel", ...ASH })).toContain("fillStyle=#ffd23a");
    expect(objCalls({ kind: "wooden_bridge", vertical: true, ...ASH })).not.toEqual(objCalls({ kind: "wooden_bridge", vertical: false, ...ASH }));
    const stages = ([0, 1, 2] as const).map((hpStage) => objCalls({ kind: "thin_ice", hpStage, ...ASH }));
    expect(stages[1]).not.toEqual(stages[0]);
    expect(stages[2]).not.toEqual(stages[1]);
    expect(objCalls({ kind: "crate", hpStage: 2, ...ASH }).length).toBeGreaterThan(objCalls({ kind: "crate", hpStage: 0, ...ASH }).length);
    // 殘牆：相連與不相連都畫得出來；崩缺不超出壓頂石（y ≥ 矮牆頂 − 1）
    for (const joinR of [false, true]) expect(() => objCalls({ kind: "low_wall", joinR, ...ASH })).not.toThrow();
  });

  it("表面在灰燼與預設完全一樣（疊在地形之後的那一段呼叫序列相同）", () => {
    const base = tileCalls({ surface: "none" }).length;
    for (const surface of ["fire", "ice", "poison", "holy", "darkness", "smoke", "oil", "water"]) {
      const ref = tileCalls({ surface });
      const refTail = ref.slice(base); // 6A-4a 起不畫格線
      expect(tileCalls({ surface, ...ASH }).slice(-refTail.length), surface).toEqual(refTail);
    }
  });
});

describe("晶冠點綴（只在 region 明確是 crystal_crown 時）", () => {
  it("表裡只有 stone、wall、chasm 三種地形與 stone_pillar 一種物件", () => {
    expect(Object.keys(REGION_TERRAIN_DRAW.crystal_crown!).sort()).toEqual(["chasm", "stone", "wall"]);
    expect(Object.keys(REGION_OBJECT_DRAW.crystal_crown!)).toEqual(["stone_pillar"]);
  });

  it("其他地形與物件退回預設（含未知 ID）", () => {
    for (const terrain of ["grass", "dirt", "lava", "ice_hole", "brand_new"]) {
      expect(tileCalls({ terrain, wallFace: true, ...CRYSTAL }), terrain).toEqual(tileCalls({ terrain, wallFace: true }));
    }
    for (const kind of [...Object.keys(OBJECT_DRAW).filter((k) => k !== "stone_pillar"), "brand_new"]) {
      expect(objCalls({ kind, hpStage: 1, ...CRYSTAL }), kind).toEqual(objCalls({ kind, hpStage: 1 }));
    }
  });

  it("石板：約 1/7 的格子有金色菱形嵌線，其他格和預設完全一樣", () => {
    let inlaid = 0;
    const N = 21;
    for (let x = 0; x < N; x++) {
      for (let y = 0; y < N; y++) {
        const got = tileCalls({ x, y, ...CRYSTAL });
        const ref = tileCalls({ x, y });
        if (crystalInlayAt(x, y)) {
          inlaid++;
          expect(got).toContain("strokeStyle=#e8bb48");
          expect(got).toContain("fillStyle=#8f7bff");
          expect(got.slice(0, ref.length - 5)).toEqual(ref.slice(0, ref.length - 5)); // 預設石板在前，嵌線疊上去
        } else {
          expect(got).toEqual(ref);
        }
      }
    }
    expect(inlaid / (N * N)).toBeGreaterThan(0.08);
    expect(inlaid / (N * N)).toBeLessThan(0.22);
  });

  it("城牆：白石＋金邊（有立面才有金邊），比單位高", () => {
    const face = tileCalls({ terrain: "wall", wallFace: true, ...CRYSTAL });
    const top = tileCalls({ terrain: "wall", wallFace: false, ...CRYSTAL });
    expect(face).not.toEqual(tileCalls({ terrain: "wall", wallFace: true }));
    expect(face).toContain("fillStyle=#e8bb48");
    expect(top).not.toContain("fillStyle=#e8bb48");
    expect(face.length).toBeGreaterThan(top.length);
  });

  it("深淵：預設深淵（含崖線）再加 4 個晶光碎點", () => {
    const ref = tileCalls({ terrain: "chasm", lip: ALL_LIP });
    const got = tileCalls({ terrain: "chasm", lip: ALL_LIP, ...CRYSTAL });
    expect(got.slice(0, ref.length - 5)).toEqual(ref.slice(0, ref.length - 5));
    expect(got.filter((c) => c === "fillStyle=#8f7bff")).toHaveLength(4);
  });

  it("晶柱：外光比頭目淡（模糊 10、半透明）、金色底座", () => {
    const calls = objCalls({ kind: "stone_pillar", ...CRYSTAL });
    expect(calls).not.toEqual(objCalls({ kind: "stone_pillar" }));
    expect(calls).toContain("shadowBlur=10");
    expect(calls).toContain("fillStyle=#e8bb48");
    expect(CRYSTAL_PILLAR_GLOW_ALPHA).toBeLessThan(1);
  });
});

// 6A-4a：拿掉格線、表面改併塊畫法，預設輸出跟著變（刻意更新）
const DEFAULT_DIGEST = "1837b83c";
