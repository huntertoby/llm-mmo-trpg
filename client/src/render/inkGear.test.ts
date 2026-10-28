// Phase C-1b：C 畫風的頭部裝備與手持物 — 確定性、四方向握點、圓盾三面、杖頭元素色、回退、不認得的值。
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "./appearance";
import { drawInkHeadgear, drawInkWeapon, isInkHeadgear, isInkWeapon, STAFF_GLOW } from "./inkGear";
import { drawFigure, itemColors } from "./paperdoll";
import { resolveDollT } from "./testDolls";

function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a)).join(",")})`);
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

const FACINGS: Facing[] = ["south", "north", "east", "west"];
const base = (): DollSpec => resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
const withGear = (gear: DollSpec["gear"]): DollSpec => ({ ...base(), gear });
const run = (spec: DollSpec, f: Facing): string[] => {
  const { ctx, calls } = recorder();
  drawFigure(ctx, spec, f);
  return calls;
};
const fills = (calls: string[]): string[] => calls.filter((c) => c.startsWith("fillStyle=#")).map((c) => c.slice(10));
const draw = (it: GearItem, o: { mirror?: boolean; side?: boolean; far?: boolean } = {}): string[] => {
  const { ctx, calls } = recorder();
  drawInkWeapon(ctx, it, "main", 0, 0, { mirror: false, side: false, far: false, ...o }, itemColors);
  return calls;
};

afterEach(() => vi.restoreAllMocks());

describe("C 畫風的頭部裝備與手持物（C-1b）", () => {
  it("樣張畫過的 kind 走 C 畫法，其餘（含魔導劍、權杖、圖騰杖、大盾）回傳 false 由現行畫法接手", () => {
    for (const k of ["helmet", "hood", "wizard_hat"]) expect(isInkHeadgear({ kind: k })).toBe(true);
    for (const k of ["horned_helm", "greathelm", "cap", "wide_hat", "crown", "bandana", "???"]) expect(isInkHeadgear({ kind: k })).toBe(false);
    for (const k of ["sword", "dagger", "axe", "staff", "bow", "shield_round"]) expect(isInkWeapon({ kind: k })).toBe(true);
    for (const k of ["greatsword", "hammer", "spear", "crossbow", "longgun", "pistol", "shotgun", "fist", "scythe", "whip", "tome", "orb", "shield_kite", "???"]) expect(isInkWeapon({ kind: k })).toBe(false);
    expect(isInkWeapon({ kind: "sword", form: "arcane" })).toBe(false);
    expect(isInkWeapon({ kind: "staff", form: "scepter" })).toBe(false);
    expect(isInkWeapon({ kind: "staff", form: "totem" })).toBe(false);
    const { ctx, calls } = recorder();
    expect(drawInkHeadgear(ctx, { kind: "greathelm" }, "front", itemColors)).toBe(false);
    expect(drawInkWeapon(ctx, { kind: "hammer" }, "main", 0, 0, { mirror: false, side: false, far: false }, itemColors)).toBe(false);
    expect(calls).toEqual([]);
  });

  it("每種 C 畫法：同一件重畫完全相同、不用 Math.random、不同 key 不同", () => {
    const rnd = vi.spyOn(Math, "random");
    for (const kind of ["sword", "dagger", "axe", "staff", "bow"]) {
      for (const side of [false, true]) expect(draw({ kind, material: "steel" }, { side })).toEqual(draw({ kind, material: "steel" }, { side }));
    }
    for (const kind of ["helmet", "hood", "wizard_hat"]) {
      for (const view of ["front", "back", "side"] as const) {
        const a = recorder();
        const b = recorder();
        drawInkHeadgear(a.ctx, { kind, material: "iron" }, view, itemColors);
        drawInkHeadgear(b.ctx, { kind, material: "iron" }, view, itemColors);
        expect(a.calls).toEqual(b.calls);
        expect(a.calls.length).toBeGreaterThan(10);
      }
    }
    expect(rnd).not.toHaveBeenCalled();
    const k1 = recorder();
    const k2 = recorder();
    drawInkWeapon(k1.ctx, { kind: "sword" }, "main", 0, 0, { mirror: false, side: false, far: false }, itemColors);
    drawInkWeapon(k2.ctx, { kind: "sword" }, "off", 0, 0, { mirror: false, side: false, far: false }, itemColors);
    expect(k1.calls).not.toEqual(k2.calls);
  });

  it("握點：武器在手的位置（translate），正面豎直，側面劍／匕首傾 0.75、斧 0.6，法杖與弓直立", () => {
    const rot = (calls: string[]): string | undefined => calls.find((c) => c.startsWith("rotate("));
    for (const kind of ["sword", "dagger"]) {
      expect(rot(draw({ kind }))).toBe("rotate(0.00)");
      expect(rot(draw({ kind }, { side: true }))).toBe("rotate(0.75)");
    }
    expect(rot(draw({ kind: "axe" }, { side: true }))).toBe("rotate(0.60)");
    for (const kind of ["staff", "bow"]) {
      expect(rot(draw({ kind }, { side: true }))).toBeUndefined();
    }
    const { ctx, calls } = recorder();
    drawInkWeapon(ctx, { kind: "sword" }, "main", -9, -23.2, { mirror: false, side: false, far: false }, itemColors);
    expect(calls[1]).toBe("translate(-9.00,-23.20)");
  });

  it("成對武器：鏡像在 translate 之後 scale(-1,1)；遠側那把顏色變暗", () => {
    expect(draw({ kind: "dagger" }, { mirror: true })).toContain("scale(-1.00,1.00)");
    expect(draw({ kind: "dagger" })).not.toContain("scale(-1.00,1.00)");
    const near = fills(draw({ kind: "sword", material: "steel" }, { side: true }));
    const far = fills(draw({ kind: "sword", material: "steel" }, { side: true, far: true }));
    expect(far).not.toEqual(near);
  });

  it("法杖杖頭光暈用元素色（預設 #8fe3ff）；不認得的元素退回預設", () => {
    const fire = draw({ kind: "staff", element: "fire" }).join("|");
    const none = draw({ kind: "staff" }).join("|");
    const weird = draw({ kind: "staff", element: "nope" }).join("|");
    expect(none).toContain(`fillStyle=${STAFF_GLOW}`);
    expect(weird).toBe(none);
    expect(fire).not.toContain(`fillStyle=${STAFF_GLOW}`);
    expect(fire).not.toBe(none);
  });

  it("整合：主手武器四方向都畫得出來（有墨線），背面主手鏡像、副手不鏡像；側面成對武器遠側先畫", () => {
    for (const kind of ["sword", "dagger", "axe", "staff", "bow"]) {
      for (const f of FACINGS) {
        const without = run(withGear({}), f).length;
        expect(run(withGear({ main_hand: { kind, material: "steel" } }), f).length).toBeGreaterThan(without + 20);
      }
    }
    const pair = withGear({ main_hand: { kind: "dagger", material: "steel" }, off_hand: { kind: "dagger", material: "steel" } });
    expect(run(pair, "south")).toContain("scale(-1.00,1.00)");
    for (const f of FACINGS) expect(run(pair, f).length).toBeGreaterThan(run(withGear({ main_hand: pair.gear.main_hand! }), f).length);
  });

  it("圓盾：正面圓面、側面一條邊、背面木色＋皮帶；塔盾仍走現行畫法", () => {
    const shield = withGear({ off_hand: { kind: "shield_round", material: "wood", color: "#2f5fae" } });
    expect(fills(run(shield, "south"))).toContain("#2f5fae");
    expect(fills(run(shield, "east"))).toContain("#2f5fae");
    expect(fills(run(shield, "north"))).not.toContain("#2f5fae");
    expect(fills(run(shield, "north"))).toContain("#a06a36");
    const tower = withGear({ off_hand: { kind: "shield_kite", form: "tower", material: "iron" } });
    for (const f of FACINGS) expect(() => run(tower, f)).not.toThrow();
  });

  it("頭部裝備三方向：頭盔、兜帽、尖帽用 C 畫法的色（指定顏色）；尖帽帽頂高過一般頭頂", () => {
    for (const kind of ["helmet", "hood", "wizard_hat"]) {
      for (const f of FACINGS) {
        const spec = withGear({ head: { kind, color: "#445566" } });
        expect(fills(run(spec, f))).toContain("#445566");
      }
    }
    const lowest = (calls: string[]): number => Math.min(...calls.filter((c) => c.startsWith("quadraticCurveTo")).flatMap((c) => c.slice(16, -1).split(",").map(Number).filter((n) => n < 0)));
    expect(lowest(run(withGear({ head: { kind: "wizard_hat", color: "#445566" } }), "south"))).toBeLessThan(-66);
  });

  it("不認得的材質、顏色、形制、元素 → 預設外觀，不報錯", () => {
    const weird: GearItem[] = [
      { kind: "sword", material: "nope", color: "red", form: "x", element: "nope" },
      { kind: "dagger", material: "nope" },
      { kind: "axe", form: "x" },
      { kind: "staff", form: "x", element: "nope", color: "bad" },
      { kind: "bow", material: "nope" },
      { kind: "shield_round", material: "nope", color: "bad", trim: "bad" },
    ];
    const heads: GearItem[] = ["helmet", "hood", "wizard_hat"].map((kind) => ({ kind, material: "nope", color: "bad", form: "x", trim: "bad" }));
    for (const f of FACINGS) {
      for (const w of weird) {
        expect(() => run(withGear({ main_hand: w }), f)).not.toThrow();
        expect(() => run(withGear({ off_hand: w }), f)).not.toThrow();
      }
      for (const h of heads) expect(() => run(withGear({ head: h }), f)).not.toThrow();
    }
  });
});
