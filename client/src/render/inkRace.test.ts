// Phase 3R-3b：種族外觀（耳、角、尾、膚色）與頭部裝備衝突規則。
import { describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec, GearItem, Look } from "./appearance";
import { COVERS, coverOf, drawBeastEarsBeforeHat, drawEarsAfterHat, drawEarsUnder, drawInkHorns, drawInkTail, drawSideEarBeforeHat, hatAdjust, raceLookToLook, type EarCtx } from "./inkRace";
import raceLooks from "./fixtures/raceLooks.json";
import { drawFigure } from "./paperdoll";
import { resolveDoll } from "./appearance";
import { resolveDollT } from "./testDolls";

function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
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

const LOOKS = raceLooks as Record<string, Record<string, unknown>>;
const RACES = Object.keys(LOOKS);
const hat = (kind: string): GearItem => ({ kind, material: "cloth" });
const ears = (look: Look, view: EarCtx["view"], head?: GearItem): EarCtx => ({ look, view, head, headColor: "#5a4a7a" });
const count = (fn: (c: CanvasRenderingContext2D) => void): number => {
  const { ctx, calls } = recorder();
  fn(ctx);
  return calls.length;
};
const VIEWS = ["front", "back", "side"] as const;
const hero = (race: string, head?: GearItem, extra: Partial<DollSpec["gear"]> = {}): DollSpec => {
  const s = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword", raceLook: LOOKS[race] });
  return { ...s, gear: { ...s.gear, ...extra, ...(head === undefined ? {} : { head }) } };
};

describe("種族外觀的欄位對照（3R-3b）", () => {
  it("10 族的 look（駝峰／底線對照）帶出膚色、髮、耳、角、尾", () => {
    const fox = raceLookToLook(LOOKS["fox"]);
    expect(fox).toMatchObject({ skin: "#f1d0b0", hair: "short", hairColor: "#d8762a", ears: "beast", tail: "fox" });
    const fiend = raceLookToLook(LOOKS["fiend"]);
    expect(fiend).toMatchObject({ horns: "curved", hornColor: "#3a2a2a", tail: "demon" });
    expect(raceLookToLook(LOOKS["elf"])).toMatchObject({ ears: "pointed" });
    expect(raceLookToLook(LOOKS["scalefolk"])).toMatchObject({ ears: "fin", eyes: "#103030" });
    expect(raceLookToLook(LOOKS["dragonkin"])).toMatchObject({ horns: "dragon", tail: "dragon", scaleColor: "#c8402a" });
  });

  it("不認得的值＝沒有，不報錯（空、null、亂值、壞顏色）", () => {
    expect(raceLookToLook(null)).toEqual({});
    expect(raceLookToLook(undefined)).toEqual({});
    const odd = raceLookToLook({ skin: "red", ears: "wings", horns: 3, tail: "snake", hair: "afro", hair_color: "#12", horn_color: null });
    expect(odd).toEqual({});
  });

  it("resolveDoll：有種族外觀時疊上膚色與部件，保留裝備；召喚物與骷髏不套用；沒有就不變", () => {
    const base = resolveDoll({ template: "hero_fighter", team: "ally", summon: false });
    const raced = resolveDoll({ template: "hero_fighter", team: "ally", summon: false, raceLook: LOOKS["fiend"] });
    expect(raced.look.skin).toBe("#b07a7a");
    expect(raced.look.horns).toBe("curved");
    expect(raced.gear).toEqual(base.gear);
    expect(resolveDoll({ template: "hero_fighter", team: "ally", summon: false, raceLook: null }).look).toEqual(base.look);
    const sum = resolveDoll({ template: "summon_x", team: "ally", summon: true, raceLook: LOOKS["fiend"] });
    expect(sum.look.horns).toBeUndefined();
  });
});

describe("衝突規則（可玩種族評估.md 第 2 節）", () => {
  it("每種頭部裝備 kind 一個 covers 標記；沒戴不遮、沒登記的 kind 只蓋頭頂", () => {
    expect(COVERS["helmet"]).toEqual({ top: true, side: true });
    expect(COVERS["hood"]?.hood).toBe(true);
    expect(coverOf(undefined)).toEqual({});
    expect(coverOf(hat("mystery"))).toEqual({ top: true });
  });

  it("尖耳、鰭耳：戴頭盔、帽子伸出（正面畫）；戴兜帽藏起來", () => {
    for (const k of ["pointed", "fin"] as const) {
      const look: Look = { skin: "#fff", ears: k };
      for (const h of [undefined, hat("helmet"), hat("greathelm"), hat("horned_helm"), hat("wide_hat"), hat("wizard_hat"), hat("cap"), hat("crown")]) {
        expect(count((c) => drawEarsUnder(c, ears(look, "front", h)))).toBeGreaterThan(0);
      }
      expect(count((c) => drawEarsUnder(c, ears(look, "front", hat("hood"))))).toBe(0);
      expect(count((c) => drawEarsUnder(c, ears(look, "back", hat("hood"))))).toBe(0);
    }
  });

  it("尖耳側面：沒有蓋兩側的裝備先畫；頭盔則在頭盔之後畫（從兩側伸出）；兜帽不畫", () => {
    const look: Look = { skin: "#fff", ears: "pointed" };
    expect(count((c) => drawSideEarBeforeHat(c, ears(look, "side")))).toBeGreaterThan(0);
    expect(count((c) => drawSideEarBeforeHat(c, ears(look, "side", hat("helmet"))))).toBe(0);
    expect(count((c) => drawEarsAfterHat(c, ears(look, "side", hat("helmet"))))).toBeGreaterThan(0);
    expect(count((c) => drawEarsAfterHat(c, ears(look, "side", hat("hood"))))).toBe(0);
    expect(count((c) => drawEarsAfterHat(c, ears(look, "side", hat("wide_hat"))))).toBe(0);
  });

  it("獸耳：頭盔、角盔、寬帽、巫師帽藏起來；皮帽、頭巾從帽子穿出；兜帽多兩個凸起；沒戴、皇冠照畫", () => {
    const look: Look = { skin: "#fff", ears: "beast", hairColor: "#d8762a" };
    const total = (h?: GearItem, v: EarCtx["view"] = "front"): number => count((c) => { drawBeastEarsBeforeHat(c, ears(look, v, h)); drawEarsAfterHat(c, ears(look, v, h)); });
    for (const k of ["helmet", "greathelm", "horned_helm", "wide_hat", "wizard_hat"]) expect(total(hat(k))).toBe(0);
    for (const k of ["cap", "bandana", "hood"]) expect(total(hat(k))).toBeGreaterThan(0);
    expect(count((c) => drawBeastEarsBeforeHat(c, ears(look, "front", hat("cap"))))).toBe(0); // 小帽的耳朵在帽子之後畫（穿出）
    expect(total()).toBeGreaterThan(0);
    expect(total(hat("crown"))).toBeGreaterThan(0);
    expect(total(undefined, "side")).toBeGreaterThan(0);
  });

  it("角：永遠畫（所有頭部裝備、三個視角）；角盔改畫成一般頭盔、小帽變窄、寬帽與巫師帽抬高", () => {
    const look: Look = { skin: "#fff", horns: "curved" };
    for (const v of VIEWS) expect(count((c) => drawInkHorns(c, look, v))).toBeGreaterThan(0);
    expect(hatAdjust(look, hat("horned_helm")).item.kind).toBe("helmet");
    expect(hatAdjust(look, hat("cap")).sx).toBeLessThan(1);
    expect(hatAdjust(look, hat("crown")).sx).toBeLessThan(1);
    expect(hatAdjust(look, hat("wide_hat")).dy).toBeLessThan(0);
    expect(hatAdjust(look, hat("wizard_hat")).dy).toBeLessThan(0);
    expect(hatAdjust(look, hat("helmet"))).toEqual({ item: hat("helmet"), dy: 0, sx: 1 });
    // 沒有角：頭部裝備不調整，角盔照畫
    expect(hatAdjust({ skin: "#fff" }, hat("horned_helm")).item.kind).toBe("horned_helm");
    expect(hatAdjust({ skin: "#fff" }, hat("wide_hat")).dy).toBe(0);
  });

  it("尾巴：三個視角都畫；沒有尾巴不畫；不認得的值不畫", () => {
    for (const tail of ["fox", "scaled", "demon", "dragon"] as const) for (const v of VIEWS) expect(count((c) => drawInkTail(c, { skin: "#fff", tail }, v))).toBeGreaterThan(0);
    expect(count((c) => drawInkTail(c, { skin: "#fff" }, "front"))).toBe(0);
    expect(count((c) => drawInkTail(c, { skin: "#fff", tail: "snake" as never }, "front"))).toBe(0);
  });
});

describe("整隻小人：10 族 × 頭部裝備 × 四方向（全組合自測）", () => {
  const HEADS: Array<GearItem | undefined> = [undefined, ...Object.keys(COVERS).map(hat), hat("mystery_hat")];
  const FACINGS: Facing[] = ["south", "north", "east", "west"];

  it("不出錯、確定性（同一組畫兩次完全相同）、不呼叫 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    for (const r of RACES) {
      for (const h of HEADS) {
        for (const f of FACINGS) {
          const a = recorder();
          const b = recorder();
          drawFigure(a.ctx, hero(r, h), f);
          drawFigure(b.ctx, hero(r, h), f);
          expect(a.calls.length).toBeGreaterThan(20);
          expect(a.calls).toEqual(b.calls);
        }
      }
    }
    expect(rnd).not.toHaveBeenCalled();
    rnd.mockRestore();
  });

  it("有種族部件的畫法和人類不同；角魔背面披風之上畫尾巴（披風 → 尾巴的順序）", () => {
    const run = (s: DollSpec, f: Facing): string => {
      const { ctx, calls } = recorder();
      drawFigure(ctx, s, f);
      return calls.join("|");
    };
    for (const r of RACES.filter((x) => ["elf", "fox", "dragonkin", "fiend", "scalefolk"].includes(x))) {
      for (const f of ["south", "east"] as const) expect(run(hero(r), f)).not.toBe(run(hero("human"), f));
    }
    const cape: GearItem = { kind: "cape", color: "#a83030" };
    expect(run(hero("fiend", undefined, { cloak: cape }), "north")).not.toBe(run(hero("human", undefined, { cloak: cape }), "north"));
  });

  it("所有種族 × 未知值（亂 look）不出錯", () => {
    const weird: DollSpec = { look: { skin: "#abcdef", ears: "wings" as never, horns: "x" as never, tail: "y" as never }, gear: {} };
    for (const f of FACINGS) expect(() => drawFigure(recorder().ctx, weird, f)).not.toThrow();
  });
});
