// Phase 5A-ART7：魔導樞市、霜潮海境換皮（docs/phases/Phase5計畫.md 第 43.0、43.2 節）。寫法比照 regionArt4.test.ts。
// 預設畫法（region 空字串）的雜湊鎖在 regionArt4.test.ts，這段加表後仍要通過。
import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, mistLevel } from "./regionArt";
import { ARCANE_LINE, arcaneLineAt } from "./arcaneTerrain";
import { ARCANE_RAIL_RISE } from "./arcaneObjects";
import { FROST_OUTLINE_WIDTH } from "./frostTerrain";
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
const ARC = { region: "arcane_hub", look: "" };
const FRO = { region: "frost_tide", look: "" };
const NO_LIP = { n: false, s: false, w: false, e: false };
const ALL_LIP = { n: true, s: true, w: true, e: true };
const SURFACES = ["fire", "ice", "poison", "holy", "darkness", "smoke", "oil", "water"];

/** 這段呼叫序列裡，最後一次 `prop=` 設定之後的值序列（例：所有 lineWidth）。 */
const setValues = (calls: readonly string[], prop: string): string[] => calls.filter((c) => c.startsWith(`${prop}=`)).map((c) => c.slice(prop.length + 1));

function commonChecks(region: { region: string; look: string }, objects: readonly string[]): void {
  it("7 種地形都換了畫法，任何邊組合都畫得出來；未知 ID 退回預設", () => {
    expect(TERRAINS).toHaveLength(7);
    for (const terrain of TERRAINS) {
      expect(Object.hasOwn(REGION_TERRAIN_DRAW[region.region]!, terrain), terrain).toBe(true);
      expect(tileCalls({ terrain, wallFace: true, ...region }), terrain).not.toEqual(tileCalls({ terrain, wallFace: true }));
      for (const lip of [NO_LIP, ALL_LIP]) expect(() => tileCalls({ terrain, lip, ...region })).not.toThrow();
    }
    expect(tileCalls({ terrain: "brand_new", ...region })).toEqual(tileCalls({ terrain: "brand_new" }));
    expect(objCalls({ kind: "brand_new", ...region })).toEqual(objCalls({ kind: "brand_new" }));
  });

  it("物件換了畫法；技能物件與預設完全一樣", () => {
    for (const kind of objects) {
      expect(Object.hasOwn(REGION_OBJECT_DRAW[region.region]!, kind), kind).toBe(true);
      expect(objCalls({ kind, hpStage: 1, ...region }), kind).not.toEqual(objCalls({ kind, hpStage: 1 }));
      for (const vertical of [false, true]) for (const joinL of [false, true]) expect(() => objCalls({ kind, vertical, joinL, joinR: !joinL, ...region })).not.toThrow();
    }
    for (const kind of SKILL_OBJECTS) {
      expect(objCalls({ kind, hpStage: 1, turnsLeft: 1, ...region }), kind).toEqual(objCalls({ kind, hpStage: 1, turnsLeft: 1 }));
    }
  });

  it("功能特徵：牆有立面時多畫一段、油桶有危險記號、橋可橫可直、受損有裂痕、位置固定", () => {
    expect(tileCalls({ terrain: "wall", wallFace: true, ...region }).length).toBeGreaterThan(tileCalls({ terrain: "wall", wallFace: false, ...region }).length);
    expect(objCalls({ kind: "oil_barrel", ...region })).toContain("fillStyle=#ffd23a");
    expect(objCalls({ kind: "wooden_bridge", vertical: true, ...region })).not.toEqual(objCalls({ kind: "wooden_bridge", vertical: false, ...region }));
    expect(objCalls({ kind: "crate", hpStage: 2, ...region }).length).toBeGreaterThan(objCalls({ kind: "crate", hpStage: 0, ...region }).length);
    expect(tileCalls({ x: 3, y: 4, ...region })).toEqual(tileCalls({ x: 3, y: 4, ...region }));
  });

  it("深淵有崖線（相接的邊多畫一段）；岩漿保留紅橘", () => {
    expect(tileCalls({ terrain: "chasm", lip: ALL_LIP, ...region }).length).toBeGreaterThan(tileCalls({ terrain: "chasm", lip: NO_LIP, ...region }).length);
    const lava = tileCalls({ terrain: "lava", ...region });
    expect(lava[0]).toMatch(/^fillStyle=#(e0400a|d04010)$/);
    expect(lava).toContain("stop(0,#ffb030)");
  });

  it("表面與預設完全一樣（疊在地形之後的那一段呼叫序列相同）；不加區域薄霧", () => {
    const base = tileCalls({ surface: "none" }).length;
    for (const surface of SURFACES) {
      const ref = tileCalls({ surface });
      const refTail = ref.slice(base - 3);
      expect(tileCalls({ surface, ...region }).slice(-refTail.length), surface).toEqual(refTail);
    }
    expect(mistLevel(region.region, "fog")).toBeNull();
  });
}

describe("魔導樞市換皮", () => {
  commonChecks(ARC, RESKINNED_OBJECTS);

  it("晶能線：2 寬、模糊 6、半透明；約 1/3 的格子有，位置用格子座標雜湊", () => {
    expect(ARCANE_LINE.width).toBe(2);
    expect(ARCANE_LINE.blur).toBe(6);
    expect(ARCANE_LINE.alpha).toBeLessThan(1);
    let lit = 0;
    const N = 21;
    for (let x = 0; x < N; x++) {
      for (let y = 0; y < N; y++) {
        const calls = tileCalls({ x, y, ...ARC });
        const has = calls.includes("shadowBlur=6");
        expect(has).toBe(arcaneLineAt(x, y));
        if (has) {
          lit++;
          expect(calls).toContain("lineWidth=2");
          expect(calls).toContain("strokeStyle=rgba(74,224,208,0.55)");
        }
      }
    }
    expect(lit / (N * N)).toBeGreaterThan(0.25);
    expect(lit / (N * N)).toBeLessThanOrEqual(0.38);
  });

  it("冷卻槽：#2a7a9a 液體加黃銅邊；熔爐槽有鐵框", () => {
    const hole = tileCalls({ terrain: "ice_hole", ...ARC });
    expect(hole).toContain("fillStyle=#2a7a9a");
    expect(hole).toContain("strokeStyle=#b08a4a");
    expect(tileCalls({ terrain: "lava", ...ARC })).toContain("strokeStyle=#5a5248");
  });

  it("沙包矮牆：欄杆是細線（≤ 1.2 寬），最高不超過矮牆頂上 6 單位", () => {
    expect(ARCANE_RAIL_RISE).toBeLessThanOrEqual(6);
    for (const joinL of [false, true]) {
      const calls = objCalls({ kind: "low_wall", joinL, ...ARC });
      const def = objCalls({ kind: "low_wall", joinL });
      // 欄杆在矮牆之後畫：只多了一段細線，矮牆本體換的是色盤
      const tail = calls.slice(def.length);
      expect(setValues(tail, "lineWidth").every((w) => Number(w) <= 1.2)).toBe(true);
      const capY = 52 * 0.3;
      const ys = tail
        .filter((c) => c.startsWith("moveTo(") || c.startsWith("lineTo("))
        .map((c) => Number(c.slice(c.indexOf(",") + 1, -1)));
      expect(ys.length).toBeGreaterThan(0);
      expect(Math.min(...ys)).toBeGreaterThanOrEqual(capY - 6);
    }
  });

  it("格柵板依耐久變化（薄冰不套通用裂痕）", () => {
    const stages = ([0, 1, 2] as const).map((hpStage) => objCalls({ kind: "thin_ice", hpStage, ...ARC }));
    expect(stages[1]).not.toEqual(stages[0]);
    expect(stages[2]).not.toEqual(stages[1]);
  });
});

describe("霜潮海境換皮", () => {
  const FROST_OBJECTS = RESKINNED_OBJECTS.filter((k) => k !== "thin_ice");
  commonChecks(FRO, FROST_OBJECTS);

  it("薄冰（主場）同預設：不在表內，每個耐久級距都和預設完全一樣", () => {
    expect(Object.hasOwn(REGION_OBJECT_DRAW.frost_tide!, "thin_ice")).toBe(false);
    for (const hpStage of [0, 1, 2] as const) expect(objCalls({ kind: "thin_ice", hpStage, ...FRO })).toEqual(objCalls({ kind: "thin_ice", hpStage }));
  });

  it("物件一律 2px 深色外框", () => {
    expect(FROST_OUTLINE_WIDTH).toBe(2);
    for (const kind of FROST_OBJECTS) {
      const calls = objCalls({ kind, ...FRO });
      expect(calls, kind).toContain("strokeStyle=#18222a");
      expect(calls.some((c, i) => c === "strokeStyle=#18222a" && calls.slice(i - 3, i + 4).some((d) => d === "lineWidth=2" || d === "lineWidth=4.6")), kind).toBe(true);
    }
    expect(Object.keys(OBJECT_DRAW)).toContain("thin_ice");
  });

  it("冰崖：和其他地形相接的邊畫 2px 深色外框，相連的冰崖不畫", () => {
    const edged = tileCalls({ terrain: "wall", lip: ALL_LIP, ...FRO });
    const inner = tileCalls({ terrain: "wall", lip: NO_LIP, ...FRO });
    expect(edged).toContain("strokeStyle=#18222a");
    expect(edged.filter((c) => c.startsWith("moveTo(")).length).toBeGreaterThan(inner.filter((c) => c.startsWith("moveTo(")).length);
  });

  it("冰窟是深色的水（冰白外框只在相接的邊）；深海溝有沙色崖線", () => {
    const hole = tileCalls({ terrain: "ice_hole", lip: ALL_LIP, ...FRO });
    expect(hole[0]).toBe("fillStyle=#1e3a5a");
    expect(hole).toContain("fillStyle=#e8f6ff");
    expect(tileCalls({ terrain: "chasm", lip: ALL_LIP, ...FRO })).toContain("fillStyle=#c8b88a");
  });

  it("熱泉多兩團白蒸氣", () => {
    const lava = tileCalls({ terrain: "lava", ...FRO });
    expect(lava.filter((c) => c === "stop(0,rgba(240,240,235,0.45))")).toHaveLength(2);
  });
});
