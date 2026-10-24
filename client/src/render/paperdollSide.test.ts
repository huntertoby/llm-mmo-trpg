// Phase 3S-1：真側面（第三套畫法）— 各方向 × 各裝備 kind（含未知）× 有／沒有裝備都畫得出來；朝西是朝東的鏡像。
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import { KNOWN_KINDS, type DollSpec, type GearSlot } from "./appearance";
import { drawFigure } from "./paperdoll";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
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
const run = (spec: DollSpec, f: Facing): string[] => {
  const { ctx, calls } = mockCtx();
  drawFigure(ctx, spec, f);
  return calls;
};
const SLOTS = Object.keys(KNOWN_KINDS) as GearSlot[];
const MIRROR = "scale(-1.00,1.00)";

describe("真側面（3S-1）", () => {
  it("每個欄位 × 每種 kind（含未知）× 4 方向 × 有／沒有裝備都不出錯", () => {
    for (const slot of SLOTS) {
      for (const kind of [...KNOWN_KINDS[slot], "weird_kind"]) {
        for (const look of [{ skin: "#fff" }, { skin: "#e8c8a0", hair: "long" as const, skull: true }, { skin: "#e8c8a0", hair: "short" as const }]) {
          const spec: DollSpec = { look, gear: { [slot]: { kind, material: "steel", element: "fire", form: "tower" } } };
          for (const f of FACINGS) expect(() => run(spec, f)).not.toThrow();
        }
      }
    }
    for (const f of FACINGS) expect(() => run({ look: { skin: "#e8c8a0" }, gear: {} }, f)).not.toThrow();
  });

  it("每個範本、各種主手武器朝東西都畫得出來", () => {
    for (const t of [...Object.keys(UNIT_DOLLS), "brand_new"]) {
      for (const w of ["one_handed_sword", "bow", "fire_staff", "dagger", "crossbow"]) {
        const spec = resolveDollT({ team: "enemy", summon: false, template: t, weaponId: w });
        for (const f of ["east", "west"] as const) expect(run(spec, f).length).toBeGreaterThan(20);
      }
    }
  });

  it("朝西是朝東的鏡像：呼叫序列相同，只多一次 scale(-1, 1)", () => {
    for (const t of Object.keys(UNIT_DOLLS)) {
      const spec = resolveDollT({ team: "enemy", summon: false, template: t, weaponId: "bow" });
      const east = run(spec, "east");
      const west = run(spec, "west");
      expect(west.filter((c) => c === MIRROR)).toHaveLength(1);
      expect(west.filter((c) => c !== MIRROR)).toEqual(east);
    }
  });

  it("側面和正面、背面是不同的畫法", () => {
    const spec = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
    expect(run(spec, "east")).not.toEqual(run(spec, "south"));
    expect(run(spec, "east")).not.toEqual(run(spec, "north"));
  });
});

describe("真側面：頭部裝備、盾、披風（3S-2）", () => {
  const HEADS = [...KNOWN_KINDS.head, "weird_kind"];
  const OFFS = [...KNOWN_KINDS.off_hand, "weird_kind"];
  const CAPE = { kind: "cape", material: "cloth" };
  const skin = { skin: "#e8c8a0" };

  it("每種頭部 kind（含未知）× 4 方向 × 有／沒有盾與披風都不出錯", () => {
    for (const kind of HEADS) {
      for (const form of [undefined, "fur", "tower"]) {
        for (const withExtra of [false, true]) {
          const gear: DollSpec["gear"] = { head: { kind, form, material: "steel" } };
          if (withExtra) {
            gear.off_hand = { kind: "shield_round", material: "iron" };
            gear.cloak = CAPE;
          }
          for (const f of FACINGS) expect(() => run({ look: { ...skin, hair: "long" }, gear }, f)).not.toThrow();
        }
      }
    }
  });

  it("每種副手（含未知、塔盾）× 披風 × 4 方向不出錯；披風有畫出東西", () => {
    for (const kind of OFFS) {
      for (const form of [undefined, "tower", "floating"]) {
        const spec: DollSpec = { look: skin, gear: { off_hand: { kind, form, material: "iron" }, cloak: CAPE } };
        for (const f of FACINGS) expect(() => run(spec, f)).not.toThrow();
      }
    }
    expect(run({ look: skin, gear: { cloak: CAPE } }, "east")).not.toEqual(run({ look: skin, gear: {} }, "east"));
  });

  it("每種已知頭部 kind 的側面都和正面不同，朝西是朝東的鏡像", () => {
    for (const kind of KNOWN_KINDS.head) {
      const spec: DollSpec = { look: skin, gear: { head: { kind, material: "steel" } } };
      const east = run(spec, "east");
      expect(east).not.toEqual(run(spec, "south"));
      expect(run(spec, "west").filter((c) => c !== MIRROR)).toEqual(east);
    }
  });

  it("角盔：兩支角都往後彎，遠側那支較暗", () => {
    const horned = run({ look: skin, gear: { head: { kind: "horned_helm", material: "steel" } } }, "east");
    expect(horned).toContain("fillStyle=#efe6cc"); // 近側角
    expect(horned).toContain("fillStyle=#a7a18f"); // 遠側角（暗 30%）
    expect(horned.indexOf("fillStyle=#a7a18f")).toBeLessThan(horned.indexOf("fillStyle=#efe6cc")); // 遠側先畫
  });
});
