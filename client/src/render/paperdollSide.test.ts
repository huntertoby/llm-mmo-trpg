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
