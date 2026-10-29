// Phase 3T-4c：短武器圖示造型只在小圖示模式生效；非圖示模式（小人、戰場）的畫法位元不變。
import { describe, expect, it } from "vitest";
import type { GearItem } from "./appearance";
import { drawInkWeapon } from "./inkGear";
import { drawInkWeaponMore } from "./inkWeapons";
import { withIconMode } from "./inkStyle";
import { itemColors } from "./paperdoll";

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

const OPT = { mirror: true, side: false, far: false, back: true };
const draw = (it: GearItem, icon: boolean): string[] => {
  const r = recorder();
  const run = (): void => {
    drawInkWeapon(r.ctx, it, "t", 0, 0, OPT, itemColors) || drawInkWeaponMore(r.ctx, it, "t", 0, 0, OPT, itemColors);
  };
  if (icon) withIconMode(r.ctx, { lineScale: 1, headScale: 1.5 }, run);
  else run();
  return r.calls;
};
const hash = (xs: string[]): string => {
  let h = 2166136261;
  for (const ch of xs.join("|")) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
  return h.toString(16);
};

const M = (kind: string, rest: Partial<GearItem> = {}): GearItem => ({ kind, material: "steel", ...rest });
const CASES: readonly (readonly [string, GearItem])[] = [
  ["dagger", M("dagger")], ["pistol", M("pistol")], ["revolver", M("pistol", { form: "revolver" })], ["fist", M("fist")], ["knuckle", M("fist", { form: "knuckle" })],
  ["shotgun", M("shotgun")], ["double", M("shotgun", { form: "double" })], ["spear", M("spear")], ["halberd", M("spear", { form: "halberd" })], ["flail", M("hammer", { form: "flail" })],
];
/** 3T-4c 之前（151abc1e）非圖示模式的畫法雜湊。 */
const BASELINE: Readonly<Record<string, string>> = {
  dagger: "aa289fd", pistol: "997df133", revolver: "5d651bf5", fist: "7b60c79", knuckle: "df0451a",
  shotgun: "e46b76d2", double: "587721d5", spear: "685716d5", halberd: "7dfe7062", flail: "2eb3565c",
};

describe("3T-4c 短武器圖示", () => {
  it("非圖示模式（小人、戰場）的畫法與改版前相同", () => {
    const got = Object.fromEntries(CASES.map(([id, it]) => [id, hash(draw(it, false))]));
    expect(got).toEqual(BASELINE);
  });

  it("圖示模式的畫法與非圖示模式不同，矛頭、戟、連枷球放大", () => {
    for (const [id, it] of CASES) expect(hash(draw(it, true)), id).not.toBe(hash(draw(it, false)));
    expect(draw(M("spear"), true)).toContain("scale(1.500,1.500)");
    expect(draw(M("spear"), false)).not.toContain("scale(1.500,1.500)");
  });

  it("拳套圖示沒有尖刺：4 指節＋方塊＋握孔共 6 個填色形狀", () => {
    const fills = draw(M("fist"), true).filter((c) => c.startsWith("fill("));
    expect(fills.length).toBeGreaterThanOrEqual(6);
  });
});
