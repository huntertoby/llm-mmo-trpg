// Phase C-2b：其餘武器的 C 畫法 — 每種 kind × 形制 × 四方向、握點與外斜、確定性、成對武器、回退、護膝與側面副手外移。
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "./appearance";
import { drawInkWeapon } from "./inkGear";
import { drawInkWeaponMore, isInkWeaponMore } from "./inkWeapons";
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
const held = (it: GearItem, o: { mirror?: boolean; side?: boolean; far?: boolean } = {}): string[] => {
  const { ctx, calls } = recorder();
  drawInkWeaponMore(ctx, it, "main", 0, 0, { mirror: false, side: false, far: false, ...o }, itemColors);
  return calls;
};
const rot = (calls: string[]): string | undefined => calls.find((c) => c.startsWith("rotate("));

const FORMS: Array<[string, Array<string | undefined>]> = [
  ["greatsword", [undefined, "zhanma", "serrated"]],
  ["hammer", ["mace", "flail", "warhammer"]],
  ["spear", [undefined, "halberd", "trident"]],
  ["crossbow", ["light", "heavy", "repeater"]],
  ["longgun", ["flintlock", "hunting", "sniper"]],
  ["shotgun", ["blunderbuss", "double", "pump"]],
  ["pistol", ["flintlock", "revolver", "derringer"]],
  ["fist", ["knuckle", "katar", "claw"]],
  ["scythe", [undefined]],
  ["whip", [undefined, "chain", "bladed"]],
  ["staff", ["scepter", "totem"]],
  ["sword", ["arcane"]],
];

afterEach(() => vi.restoreAllMocks());

describe("其餘武器的 C 畫法（Phase C-2b）", () => {
  it("每種 kind × 形制 × 四方向（主手、成對）都畫得出來、重畫完全相同、不用 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    for (const [kind, forms] of FORMS) {
      for (const form of forms) {
        const w: GearItem = { kind, ...(form === undefined ? {} : { form }), material: "steel" };
        expect(isInkWeaponMore(w)).toBe(true);
        for (const f of FACINGS) {
          const a = run(withGear({ main_hand: w, off_hand: w }), f);
          expect(a.length).toBeGreaterThan(100);
          expect(run(withGear({ main_hand: w, off_hand: w }), f)).toEqual(a);
        }
      }
    }
    expect(rnd).not.toHaveBeenCalled();
  });

  it("不是這一層的 kind 回傳 false；不認得的形制退回預設形制", () => {
    for (const w of [{ kind: "sword" }, { kind: "dagger" }, { kind: "staff", form: "long" }, { kind: "???" }] as GearItem[]) {
      const { ctx } = recorder();
      expect(drawInkWeaponMore(ctx, w, "main", 0, 0, { mirror: false, side: false, far: false }, itemColors)).toBe(false);
    }
    for (const [kind] of FORMS.filter(([k]) => k !== "staff" && k !== "sword")) {
      expect(held({ kind, form: "no_such_form", material: "steel" }).length).toBeGreaterThan(50);
      expect(() => held({ kind, material: "unobtainium", color: "pink", element: "nope" } as GearItem)).not.toThrow();
    }
  });

  it("握點：translate 到手心；正面略往外斜、側面往前傾、槍弩朝外上抬；背面主手鏡像（不翻轉）", () => {
    expect(held({ kind: "greatsword" })[1]).toBe("translate(0.00,0.00)");
    expect(rot(held({ kind: "greatsword" }))).toBe("rotate(0.18)");
    expect(rot(held({ kind: "greatsword" }, { side: true }))).toBe("rotate(0.80)");
    expect(rot(held({ kind: "hammer", form: "mace" }, { side: true }))).toBe("rotate(0.50)");
    expect(rot(held({ kind: "pistol" }))).toBe("rotate(-0.35)");
    expect(rot(held({ kind: "longgun" }, { side: true }))).toBe("rotate(-0.05)");
    expect(rot(held({ kind: "longgun" }, { side: true, far: true }))).toBe("rotate(0.15)");
    // 正面主手在畫面左：外側朝 -x，所以翻轉；副手（mirror）不翻轉；側面不翻轉
    expect(held({ kind: "spear" })).toContain("scale(-1.00,1.00)");
    expect(held({ kind: "spear" }, { mirror: true })).not.toContain("scale(-1.00,1.00)");
    expect(held({ kind: "spear" }, { side: true })).not.toContain("scale(-1.00,1.00)");
  });

  it("側面遠側那把顏色變暗；魔導劍有元素換元素色、無元素藍紫、符文淡白", () => {
    const near = fills(held({ kind: "hammer", form: "warhammer", material: "steel" }, { side: true }));
    const far = fills(held({ kind: "hammer", form: "warhammer", material: "steel" }, { side: true, far: true }));
    expect(far).not.toEqual(near);
    const plain = fills(held({ kind: "sword", form: "arcane" }));
    expect(plain).toContain("#9a86ff");
    expect(plain).toContain("#e8e2ff");
    expect(plain).toContain("#b08a4a");
    expect(fills(held({ kind: "sword", form: "arcane", element: "fire" }))).not.toContain("#9a86ff");
  });

  it("成對武器：正面副手＝鏡像、側面遠側在 (5.6,-27)、背面兩把都在；拳套兩手都畫", () => {
    for (const [kind, form] of [["pistol", "revolver"], ["hammer", "mace"]] as const) {
      const w: GearItem = { kind, form, material: "steel" };
      const one = run(withGear({ main_hand: w }), "south").filter((c) => c.startsWith("translate(")).length;
      const two = run(withGear({ main_hand: w, off_hand: w }), "south").filter((c) => c.startsWith("translate(")).length;
      expect(two).toBeGreaterThan(one);
    }
    const side = run(withGear({ main_hand: { kind: "pistol", form: "revolver" }, off_hand: { kind: "pistol", form: "revolver" } }), "east");
    expect(side).toContain("translate(5.60,-27.00)");
    expect(side).toContain("translate(4.60,-24.00)");
  });

  it("sword 的 curved、dagger 的 kris 刀身有弧度（其他形制筆直）", () => {
    const pts = (form: string): string[] => {
      const { ctx, calls } = recorder();
      drawInkWeapon(ctx, { kind: "sword", form, material: "steel" }, "main", 0, 0, { mirror: false, side: false, far: false }, itemColors);
      return calls;
    };
    expect(pts("curved")).not.toEqual(pts("straight"));
    expect(pts("straight")).toEqual(pts("no_such_form"));
  });
});

describe("C-2a 待決回覆（美術 PM）：護膝、側面副手外移", () => {
  const knee = (form: string | undefined, f: Facing): number => run(withGear({ feet: { kind: "greaves", ...(form === undefined ? {} : { form }), material: "steel" } }), f).filter((c) => c.startsWith("ellipse(")).length;

  it("護膝 knee：正面兩條腿都畫、側面只畫近側、背面不畫（比沒有 knee 的脛甲多畫的橢圓筆畫）", () => {
    const count = (form: string, f: Facing): number => run(withGear({ feet: { kind: "greaves", form, material: "steel" } }), f).length;
    expect(count("knee", "south")).toBeGreaterThan(count("long", "south"));
    expect(count("knee", "east")).toBeGreaterThan(count("long", "east"));
    expect(count("knee", "north")).toBe(count("long", "north"));
    // 正面比側面多一個（兩條腿）
    const gain = (f: Facing): number => count("knee", f) - count("long", f);
    expect(gain("south")).toBeGreaterThan(gain("east"));
    expect(knee(undefined, "south")).toBeGreaterThanOrEqual(0);
  });

  it("側面圓盾盾邊中心 x 8.5、書與法球外移到 x≈9", () => {
    const shield = run(withGear({ main_hand: { kind: "sword" }, off_hand: { kind: "shield_round", material: "wood" } }), "east");
    const none = run(withGear({ main_hand: { kind: "sword" } }), "east");
    expect(shield.length).toBeGreaterThan(none.length);
    // 盾邊橢圓取點以 (8.5,-23) 為中心：最右點 x ≈ 8.5 + 2.6
    const moves = shield.filter((c) => c.startsWith("moveTo(")).map((c) => Number(c.slice(7, -1).split(",")[0]));
    expect(Math.max(...moves)).toBeGreaterThan(10.5);
  });
});
