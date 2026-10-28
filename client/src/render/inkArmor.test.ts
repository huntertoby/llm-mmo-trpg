// Phase C-2a：其餘防具與副手的 C 畫法 — 確定性、四方向、各形制、顏色照 itemColors、不認得的值退回預設、側面副手位置。
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "./appearance";
import { drawInkBodyArmor, drawInkHand, drawInkHeadgearMore, drawFootDetail, footTop } from "./inkArmor";
import { drawInkKiteSide, drawInkOffhand } from "./inkOffhand";
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

afterEach(() => vi.restoreAllMocks());

const BODY: GearItem[] = [{ kind: "mail", form: "chain", material: "steel" }, { kind: "mail", form: "scale", material: "iron" }, { kind: "coat", form: "travel", material: "leather" }, { kind: "coat", form: "cape", color: "#7a2f3a" }];
const HEAD: GearItem[] = [{ kind: "wide_hat", material: "leather" }, { kind: "cap", material: "leather" }, { kind: "cap", form: "fur", material: "leather" }, { kind: "bandana", material: "cloth" }, { kind: "crown", material: "gold" }, { kind: "horned_helm", material: "steel" }, { kind: "greathelm", material: "steel" }];
const HANDS: GearItem[] = [{ kind: "gloves", form: "plain", material: "cloth" }, { kind: "gloves", form: "fingerless", material: "leather" }, { kind: "gloves", form: "long", material: "leather" }, { kind: "gauntlets", form: "plate", material: "steel" }, { kind: "gauntlets", form: "mail", material: "iron" }, { kind: "bracers", form: "leather", material: "leather" }, { kind: "bracers", form: "ring", material: "copper" }];
const FEET: GearItem[] = [{ kind: "shoes", form: "slipper", material: "cloth" }, { kind: "shoes", form: "wrapped", material: "cloth" }, { kind: "iron_boots", form: "plain", material: "iron" }, { kind: "iron_boots", form: "sabaton", material: "steel" }];
const OFF: GearItem[] = [{ kind: "shield_kite", form: "kite", material: "iron" }, { kind: "shield_kite", form: "tower", material: "wood" }, { kind: "tome", form: "book", material: "leather" }, { kind: "tome", form: "scroll", material: "cloth" }, { kind: "orb", form: "ball", material: "crystal", element: "ice" }, { kind: "orb", form: "floating", material: "crystal", element: "fire" }];

describe("其餘防具與副手的 C 畫法（C-2a）", () => {
  it("每種形制四方向都畫得出來、重畫完全相同、不用 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    const slots: Array<[keyof DollSpec["gear"], GearItem[]]> = [["body", BODY], ["head", HEAD], ["hands", HANDS], ["feet", FEET], ["off_hand", OFF]];
    for (const [slot, items] of slots) {
      for (const it of items) {
        for (const f of FACINGS) {
          const spec = withGear({ [slot]: it });
          const a = run(spec, f);
          expect(a.length).toBeGreaterThan(50);
          expect(run(spec, f)).toEqual(a);
        }
      }
    }
    expect(rnd).not.toHaveBeenCalled();
  });

  it("身體：mail、coat 走 C 畫法；其他 kind 回傳 false；顏色照 itemColors", () => {
    const { ctx, calls } = recorder();
    for (const it of BODY) expect(drawInkBodyArmor(ctx, it, "front", itemColors)).toBe(true);
    expect(drawInkBodyArmor(ctx, { kind: "robe" }, "front", itemColors)).toBe(false);
    expect(drawInkBodyArmor(ctx, { kind: "???" }, "front", itemColors)).toBe(false);
    expect(fills(calls)).toContain(itemColors(BODY[0]!)[0]);
    // 鱗甲與鎖甲紋路不同
    const a = recorder();
    const b = recorder();
    drawInkBodyArmor(a.ctx, BODY[0]!, "front", itemColors);
    drawInkBodyArmor(b.ctx, { ...BODY[0]!, form: "scale" }, "front", itemColors);
    expect(a.calls).not.toEqual(b.calls);
  });

  it("頭：七種 kind 三個方向；角盔側面兩支角（遠側暗 30%）；不認得的 kind 回傳 false", () => {
    for (const it of HEAD) for (const v of ["front", "back", "side"] as const) {
      const { ctx, calls } = recorder();
      expect(drawInkHeadgearMore(ctx, it, v, itemColors)).toBe(true);
      expect(calls.length).toBeGreaterThan(10);
    }
    const { ctx, calls } = recorder();
    expect(drawInkHeadgearMore(ctx, { kind: "helmet" }, "front", itemColors)).toBe(false);
    expect(calls).toEqual([]);
    const s = recorder();
    drawInkHeadgearMore(s.ctx, { kind: "horned_helm", material: "steel" }, "side", itemColors);
    const f = fills(s.calls);
    expect(f.indexOf("#a7a18f")).toBeGreaterThanOrEqual(0);
    expect(f.indexOf("#a7a18f")).toBeLessThan(f.indexOf("#efe6cc"));
  });

  it("手：手套、護手用裝備色，臂甲、露指手套露膚色；沒有裝備、不認得的 kind 退回預設", () => {
    const skin = "#eab48a";
    const hand = (h: GearItem | undefined): string[] => {
      const { ctx, calls } = recorder();
      drawInkHand(ctx, h, "h", 0, 0, 0.3, skin, itemColors);
      return fills(calls);
    };
    expect(hand(undefined)).toEqual(expect.arrayContaining([skin]));
    expect(hand(HANDS[0]!)).toContain(itemColors(HANDS[0]!)[0]);
    expect(hand(HANDS[0]!)).not.toContain(skin);
    expect(hand(HANDS[5]!)).toContain(skin); // 臂甲：手露膚色
    expect(hand(HANDS[1]!)).toContain(skin); // 露指
    expect(hand({ kind: "gauntlets", form: "plate", material: "steel" })).not.toContain(skin);
    expect(() => hand({ kind: "???", form: "???", material: "???", color: "bad" })).not.toThrow();
    // 長手套、護手有袖口（多畫東西）
    expect(hand(HANDS[2]!).length).toBeGreaterThan(hand(HANDS[0]!).length);
  });

  it("腳：shoes 低、iron_boots 高；綁腿與鐵靴細節；沒有鞋靴不畫", () => {
    expect(footTop(FEET[0])).toBe(-3.4);
    expect(footTop(FEET[2])).toBe(-9);
    expect(footTop({ kind: "boots" })).toBeUndefined();
    expect(footTop(undefined)).toBeUndefined();
    for (const view of ["front", "back", "side"] as const) {
      const none = recorder();
      drawFootDetail(none.ctx, undefined, view, itemColors);
      expect(none.calls).toEqual([]);
      for (const it of [FEET[1]!, FEET[2]!]) {
        const { ctx, calls } = recorder();
        drawFootDetail(ctx, it, view, itemColors);
        expect(calls.length).toBeGreaterThan(0);
      }
    }
  });

  it("副手：鳶盾、塔盾、書、法球；法球光暈用元素色；不認得的形制退回預設；其他 kind 回傳 false", () => {
    for (const it of OFF) for (const side of [false, true]) {
      const { ctx, calls } = recorder();
      const ok = drawInkOffhand(ctx, it, 9, -23.2, side, itemColors);
      expect(ok).toBe(true);
      // 側面的鳶盾由 drawInkKiteSide 畫（身體之前），這裡不畫
      if (!(side && it.kind === "shield_kite")) expect(calls.length).toBeGreaterThan(5);
    }
    const ice = recorder();
    drawInkOffhand(ice.ctx, { kind: "orb", element: "ice", material: "crystal" }, 0, 0, false, itemColors);
    const fire = recorder();
    drawInkOffhand(fire.ctx, { kind: "orb", element: "fire", material: "crystal" }, 0, 0, false, itemColors);
    expect(fills(ice.calls)).not.toEqual(fills(fire.calls));
    for (const bad of [{ kind: "tome", form: "???", material: "???" }, { kind: "orb", form: "???", element: "nope" }, { kind: "shield_kite", form: "???", color: "bad" }]) {
      expect(() => drawInkOffhand(recorder().ctx, bad, 0, 0, false, itemColors)).not.toThrow();
    }
    expect(drawInkOffhand(recorder().ctx, { kind: "shield_round" }, 0, 0, false, itemColors)).toBe(false);
    expect(drawInkKiteSide(recorder().ctx, { kind: "tome" }, itemColors)).toBe(false);
  });

  it("側面書、法球畫在身體之後、往前移到身體外並暗 25%；盾邊畫在身體之後、頭之前", () => {
    const tome = recorder();
    drawInkOffhand(tome.ctx, { kind: "tome", color: "#c04040" }, 5.6, -27, true, itemColors);
    expect(fills(tome.calls)).toContain("#903030"); // 暗 25%
    const spec = withGear({ off_hand: { kind: "shield_round", color: "#2f5fae" } });
    const calls = run(spec, "east");
    const fs = fills(calls);
    expect(fs).toContain("#2f5fae");
    // 盾邊（藍）在身體色之後、頭膚色之前
    const skin = spec.look.skin ?? "#eab48a";
    expect(fs.indexOf("#2f5fae")).toBeLessThan(fs.lastIndexOf(skin));
  });

  it("正面斧頭、匕首照驗收翻轉與外斜：成對時副手鏡像也朝外", () => {
    const axeDual = withGear({ main_hand: { kind: "axe", material: "steel" }, off_hand: { kind: "axe", material: "steel" } });
    const scales = run(axeDual, "south").filter((c) => c === "scale(-1.00,1.00)").length;
    const single = run(withGear({ main_hand: { kind: "axe", material: "steel" } }), "south").filter((c) => c === "scale(-1.00,1.00)").length;
    // 主手翻轉（大刃朝外＝畫面左）；副手原本鏡像（朝內），翻轉後抵銷＝大刃朝外（畫面右）
    expect([scales, single]).toEqual([1, 1]);
  });
});
