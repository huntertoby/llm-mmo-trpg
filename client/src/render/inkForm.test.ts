// Phase 3J-5：形態外觀（C 畫風）— 10 種 × 四方向 × 倒地、主色、元素、光環、不認得的 id、頭頂狀態列上移、美術 PM 小修（彎刀、護膝）。
import { Texture } from "pixi.js";
import { afterEach, describe, expect, it, vi } from "vitest";
import formsYaml from "../../../content/forms.yaml?raw";
import { parse } from "yaml";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { DollSpec, GearItem } from "./appearance";
import type { ArtTextures } from "./artTextures";
import {
  drawForm,
  drawFormAura,
  FORM_ARTS,
  FORM_AURA_NEUTRAL,
  FORM_HERO_FALLBACK,
  FORM_LOOKS,
  formArtOf,
  formAuraColor,
  formAuraRadius,
  formHeroColor,
  formKey,
  formRowRise,
  formScale,
  mixColor,
} from "./inkForm";
import { drawInkWeapon, lighten } from "./inkGear";
import { drawFigure, DOLL_SCALE, itemColors } from "./paperdoll";
import { resolveDollT } from "./testDolls";
import { buildUnitSprite, Pulses } from "./unitSprite";

/** 記錄所有呼叫的假 Canvas 2D。 */
function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : Array.isArray(a) ? `[${a.join(",")}]` : typeof a)).join(",")})`);
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
const IDS = Object.keys(FORM_ARTS);
const draw = (id: string, hero = "#4f7fbf", element: string | null = null, facing: Facing = "east", downed = false): string[] => {
  const { ctx, calls } = recorder();
  expect(drawForm(ctx, id, hero, element, facing, downed)).toBe(true);
  return calls;
};
const fills = (calls: string[]): string[] => calls.filter((c) => c.startsWith("fillStyle=#")).map((c) => c.slice(10));

afterEach(() => vi.restoreAllMocks());

describe("形態資料與外觀 id", () => {
  it("forms.yaml 的每個形態外觀 id 都有畫法；10 種都畫得出來", () => {
    const forms = (parse(formsYaml) as { forms: Array<{ id: string; look: string }> }).forms;
    expect(forms).toHaveLength(10);
    for (const f of forms) expect(formArtOf(f.look), f.look).not.toBeNull();
    expect(new Set(Object.values(FORM_LOOKS))).toEqual(new Set(IDS));
    expect(IDS).toHaveLength(10);
  });

  it("大小倍率照樣張（formArt.js）", () => {
    const size = Object.fromEntries(IDS.map((id) => [id, FORM_ARTS[id]?.size]));
    expect(size).toEqual({ bear: 1.3, cat: 1.25, roc: 1.2, demon: 1.2, giant: 1.45, avatar: 1.2, shadow: 1.2, treant: 1.3, werewolf: 1.25, dragon: 1.5 });
  });

  it("不認得的外觀 id、空字串、null → null（呼叫端退回原角色紙娃娃＋光環）", () => {
    for (const look of ["form_unknown", "", null, undefined, "bear", "__proto__", "constructor"]) expect(formArtOf(look), String(look)).toBeNull();
    const { ctx } = recorder();
    expect(drawForm(ctx, "nope", "#4f7fbf", null, "east", false)).toBe(false);
    expect(drawForm(ctx, "toString", "#4f7fbf", null, "east", false)).toBe(false);
  });
});

describe("10 種形態的畫法（C 畫風 ink）", () => {
  it("每種 × 四方向 × 站立／倒地都畫得出來、有墨線與填色、不報錯", () => {
    for (const id of IDS) {
      for (const f of FACINGS) {
        for (const downed of [false, true]) {
          const calls = draw(id, "#a83030", id === "avatar" || id === "dragon" ? "ice" : null, f, downed);
          expect(calls.filter((c) => c.startsWith("fill(")).length, `${id} ${f} ${String(downed)}`).toBeGreaterThan(5);
          expect(calls.some((c) => c.startsWith("strokeStyle=#2b1e16")), `${id} 墨線`).toBe(true);
        }
      }
    }
  });

  it("確定性：重畫完全相同、不用 Math.random()", () => {
    const rnd = vi.spyOn(Math, "random");
    for (const id of IDS) expect(draw(id, "#2a4a8a", "fire")).toEqual(draw(id, "#2a4a8a", "fire"));
    expect(rnd).not.toHaveBeenCalled();
  });

  it("西與北是左右鏡像（scale(-1,1)）、東與南不鏡像；倒地會旋轉、站立有影子", () => {
    for (const id of IDS) {
      expect(draw(id, "#4f7fbf", null, "west").some((c) => c === "scale(-1.00,1.00)"), id).toBe(true);
      expect(draw(id, "#4f7fbf", null, "north").some((c) => c === "scale(-1.00,1.00)"), id).toBe(true);
      expect(draw(id, "#4f7fbf", null, "east").some((c) => c === "scale(-1.00,1.00)"), id).toBe(false);
      expect(draw(id, "#4f7fbf", null, "south").some((c) => c === "scale(-1.00,1.00)"), id).toBe(false);
      expect(draw(id, "#4f7fbf", null, "east", true).some((c) => c.startsWith("rotate(")), id).toBe(true);
      expect(draw(id, "#4f7fbf", null, "east", false).some((c) => c.startsWith("rotate(")), id).toBe(false);
    }
  });

  it("帶主角主色：換主色就換顏色（10 種都有用到 hero）", () => {
    for (const id of IDS) {
      const a = draw(id, "#c8402a").join("|");
      const b = draw(id, "#2a8a4a").join("|");
      expect(a, id).not.toBe(b);
    }
    // 熊的毛色混主色 30%、背紋是主色
    const bear = fills(draw("bear", "#4f7a3a"));
    expect(bear).toContain(mixColor("#6a4a32", "#4f7a3a", 0.3));
  });

  it("元素化身與龍吃元素：火／冰／雷畫出不同顏色；沒有或不認得的元素用火", () => {
    for (const id of ["avatar", "dragon"]) {
      const fire = draw(id, "#4f7fbf", "fire").join("|");
      const ice = draw(id, "#4f7fbf", "ice").join("|");
      const lightning = draw(id, "#4f7fbf", "lightning").join("|");
      expect(new Set([fire, ice, lightning]).size, id).toBe(3);
      expect(draw(id, "#4f7fbf", null).join("|"), id).toBe(fire);
      expect(draw(id, "#4f7fbf", "plasma").join("|"), id).toBe(fire);
    }
    expect(fills(draw("avatar", "#4f7fbf", "ice"))).toContain("#8fe3ff");
    expect(fills(draw("dragon", "#4f7fbf", "lightning"))).toContain("#ffe14a");
  });

  it("不是 #rrggbb 的主色不出錯（混色原樣回傳）", () => {
    expect(() => draw("bear", "red")).not.toThrow();
    expect(mixColor("red", "#ffffff", 0.5)).toBe("red");
  });
});

describe("主角主色與光環", () => {
  it("主色：身體裝備 color → 披風 color → 陣營藍；壞值跳過", () => {
    expect(formHeroColor("#112233", "#445566")).toBe("#112233");
    expect(formHeroColor(undefined, "#445566")).toBe("#445566");
    expect(formHeroColor("nope", "#445566")).toBe("#445566");
    expect(formHeroColor(undefined, undefined)).toBe(FORM_HERO_FALLBACK);
    expect(formHeroColor("rgb(1,2,3)", "")).toBe(FORM_HERO_FALLBACK);
  });

  it("光環色：火／冰／雷用元素色、無元素與不認得的元素 #9a86ff", () => {
    expect(formAuraColor("fire")).toBe("#ff7a1a");
    expect(formAuraColor("ice")).toBe("#8fe3ff");
    expect(formAuraColor("lightning")).toBe("#ffe14a");
    for (const e of [null, undefined, "", "plasma", "shadow"]) expect(formAuraColor(e), String(e)).toBe(FORM_AURA_NEUTRAL);
    expect(FORM_AURA_NEUTRAL).toBe("#9a86ff");
  });

  it("手繪光環：虛線 2.4／1.6、線寬 1.1、18% 同色填色", () => {
    const { ctx, calls } = recorder();
    drawFormAura(ctx, "#ff7a1a", 20);
    expect(calls).toContain("setLineDash([2.4,1.6])");
    expect(calls).toContain("lineWidth=1.1");
    expect(calls).toContain("strokeStyle=#ff7a1a");
    expect(calls).toContain("globalAlpha=0.18");
    expect(calls).toContain("fillStyle=#ff7a1a");
    expect(calls.filter((c) => c.startsWith("ellipse(")).length).toBe(1);
    // 橢圓 ry ＝ 0.3 rx
    expect(calls.find((c) => c.startsWith("ellipse("))).toBe("ellipse(0.00,0.00,20.00,6.00,0.00,0.00,6.28)");
  });

  it("光環半徑：認得的形態 16 × size × 縮放；不認得的用預設 20 × 小人縮放", () => {
    const bear = formArtOf("form_bear");
    expect(bear).not.toBeNull();
    expect(formAuraRadius("form_bear", DOLL_SCALE)).toBeCloseTo(16 * 1.3 * 0.6 * 1.3, 6);
    expect(formAuraRadius("nope", DOLL_SCALE)).toBeCloseTo(20 * DOLL_SCALE, 6);
  });
});

describe("體型：縮放與頭頂狀態列上移", () => {
  it("形態縮放 ＝ 0.6 × min(size, 1.3)；龍與巨人封頂", () => {
    expect(formScale(FORM_ARTS.dragon!)).toBeCloseTo(0.78, 6);
    expect(formScale(FORM_ARTS.giant!)).toBeCloseTo(0.78, 6);
    expect(formScale(FORM_ARTS.roc!)).toBeCloseTo(0.72, 6);
  });

  it("狀態列：矮的形態不下移（0）、比小人高的（樹人、龍、狼人）往上移；不認得的 0", () => {
    const rise = (look: string): number => formRowRise(look, 48, DOLL_SCALE);
    expect(rise("form_bear")).toBe(0);
    expect(rise("form_cat")).toBe(0);
    for (const look of ["form_treant", "form_dragon", "form_werewolf"]) expect(rise(look), look).toBeGreaterThan(0);
    expect(rise("form_treant")).toBeGreaterThan(rise("form_werewolf"));
    expect(rise("nope")).toBe(0);
    expect(rise("")).toBe(0);
  });

  it("貼圖快取鍵含畫法、主色、元素、朝向、姿勢", () => {
    const keys = new Set([
      formKey("bear", "#111111", null, "east", false),
      formKey("bear", "#222222", null, "east", false),
      formKey("bear", "#111111", "fire", "east", false),
      formKey("bear", "#111111", null, "west", false),
      formKey("bear", "#111111", null, "east", true),
      formKey("cat", "#111111", null, "east", false),
    ]);
    expect(keys.size).toBe(6);
    expect(formKey("bear", "#111111", "plasma", "east", false)).toBe(formKey("bear", "#111111", null, "east", false));
  });
});

describe("單位畫法：形態取代紙娃娃、不認得的退回", () => {
  function fakeArt(): { art: ArtTextures; used: string[] } {
    const used: string[] = [];
    const art = {
      form: (id: string, hero: string, element: string | null | undefined) => (used.push(`form:${id}:${hero}:${String(element)}`), Texture.WHITE),
      figure: () => (used.push("figure"), Texture.WHITE),
      summon: () => (used.push("summon"), Texture.WHITE),
      formAura: (color: string) => (used.push(`aura:${color}`), Texture.WHITE),
    } as unknown as ArtTextures;
    return { art, used };
  }
  const view = (over: Partial<ReturnType<typeof unit>>): BattleView =>
    ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, over)], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
  const unitDraw = (over: Partial<ReturnType<typeof unit>>): UnitDraw => buildDrawModel(view(over), "unit_0001").units[0]!;
  const formView = (look: string, element: string | null): NonNullable<ReturnType<typeof unit>["form"]> => ({ form_id: "x", name_zh: "x", category: "physical", look, element, natural_weapon_zh: "", effects_zh: [], upkeep_zh: "" });

  it("drawModel：UnitView.form → UnitDraw.form（外觀 id 與元素）；沒有形態為 null", () => {
    expect(unitDraw({}).form).toBeNull();
    expect(unitDraw({ form: formView("form_dragon", "ice") }).form).toEqual({ look: "form_dragon", element: "ice" });
    expect(unitDraw({ form: formView("form_bear", null) }).form).toEqual({ look: "form_bear", element: null });
  });

  it("有形態：畫形態貼圖（不是紙娃娃）、帶光環；元素色光環", () => {
    const { art, used } = fakeArt();
    buildUnitSprite(art, new Pulses(), unitDraw({ template_id: "hero_fighter", form: formView("form_dragon", "ice") }));
    expect(used.some((u) => u.startsWith("form:dragon:"))).toBe(true);
    expect(used).not.toContain("figure");
    expect(used).toContain("aura:#8fe3ff");
    expect(used.find((u) => u.startsWith("form:"))?.endsWith(":ice")).toBe(true);
  });

  it("主色取自單位身體裝備的 color、沒有時取披風、再沒有用陣營藍（不是紙娃娃的預設色就是陣營藍）", () => {
    const { art, used } = fakeArt();
    buildUnitSprite(art, new Pulses(), unitDraw({ template_id: "hero_fighter", form: formView("form_bear", null), equipment: [{ slot: "body", appearance: { kind: "robe", dye: "red" } }] as never }));
    expect(used.find((u) => u.startsWith("form:"))).toBe("form:bear:#b83a3a:null");
    const b = fakeArt();
    buildUnitSprite(b.art, new Pulses(), unitDraw({ template_id: "no_such_template", form: formView("form_bear", null) }));
    expect(b.used.find((u) => u.startsWith("form:"))).toMatch(/^form:bear:#[0-9a-f]{6}:null$/);
  });

  it("不認得的形態 id：退回原角色紙娃娃＋光環，不報錯", () => {
    for (const look of ["form_unknown", ""]) {
      const { art, used } = fakeArt();
      expect(() => buildUnitSprite(art, new Pulses(), unitDraw({ template_id: "hero_fighter", form: formView(look, null) }))).not.toThrow();
      expect(used, look).toContain("figure");
      expect(used.some((u) => u.startsWith("form:"))).toBe(false);
      expect(used).toContain("aura:#9a86ff");
    }
  });

  it("沒有形態：照舊畫紙娃娃、沒有光環", () => {
    const { art, used } = fakeArt();
    buildUnitSprite(art, new Pulses(), unitDraw({ template_id: "hero_fighter" }));
    expect(used).toEqual(["figure"]);
  });

  it("形態貼圖畫不出來（沒有 DOM）時退回紙娃娃，不報錯", () => {
    const art = { form: () => null, figure: () => Texture.WHITE, formAura: () => null, summon: () => null } as unknown as ArtTextures;
    expect(() => buildUnitSprite(art, new Pulses(), unitDraw({ template_id: "hero_fighter", form: formView("form_bear", null) }))).not.toThrow();
  });
});

// ---- 美術 PM 小修（C-2b 驗收）----

/** 追蹤變換矩陣的假 Canvas：回傳畫出的所有路徑點（轉成畫面座標）。 */
function pointRecorder(): { ctx: CanvasRenderingContext2D; pts: () => Array<[number, number]> } {
  type M = [number, number, number, number, number, number];
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  const pts: Array<[number, number]> = [];
  const mul = (a: M, b: M): M => [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5]];
  const add = (x: number, y: number): void => void pts.push([m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]);
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...a: number[]) => {
        if (prop === "save") stack.push([...m]);
        else if (prop === "restore") m = stack.pop() ?? m;
        else if (prop === "translate") m = mul(m, [1, 0, 0, 1, a[0] ?? 0, a[1] ?? 0]);
        else if (prop === "scale") m = mul(m, [a[0] ?? 1, 0, 0, a[1] ?? 1, 0, 0]);
        else if (prop === "rotate") m = mul(m, [Math.cos(a[0] ?? 0), Math.sin(a[0] ?? 0), -Math.sin(a[0] ?? 0), Math.cos(a[0] ?? 0), 0, 0]);
        else if (prop === "moveTo" || prop === "lineTo") add(a[0] ?? 0, a[1] ?? 0);
        else if (prop === "quadraticCurveTo") add(a[2] ?? 0, a[3] ?? 0);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, pts: () => pts };
}

describe("美術 PM 小修（3J-5 第 5 點）", () => {
  const base = (): DollSpec => resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
  // 刀尖的畫面 x（相對手的位置）：直劍與彎刀的差就是彎的方向與量
  const tipX = (form: string, o: { mirror: boolean; side: boolean; back?: boolean }): number => {
    const { ctx, pts } = pointRecorder();
    drawInkWeapon(ctx, { kind: "sword", material: "steel", form }, "t", 0, 0, { far: false, ...o }, itemColors);
    const top = pts().reduce((m, p) => (p[1] < m[1] ? p : m));
    return top[0];
  };
  const bend = (o: { mirror: boolean; side: boolean; back?: boolean }): number => tipX("curved", o) - tipX("straight", o);

  it("正面彎刀往外彎：主手（畫面左）刀身往畫面左、副手（鏡像，畫面右）往畫面右；不再往頭那邊彎", () => {
    expect(bend({ mirror: false, side: false })).toBeLessThan(-0.5);
    expect(bend({ mirror: true, side: false })).toBeGreaterThan(0.5);
  });

  it("側面彎刀不動：仍往前（+x）彎", () => {
    expect(bend({ mirror: false, side: true })).toBeGreaterThan(0.5);
  });

  it("背面不動（彎刀方向與 3J-5 前相同）", () => {
    // 背面主手 mirror ＝ true、back ＝ true：沿用原本往 +x（再被鏡像）的彎法
    expect(bend({ mirror: true, side: false, back: true })).toBeLessThan(-0.5);
    expect(bend({ mirror: false, side: false, back: true })).toBeGreaterThan(0.5);
  });

  const kneeFills = (body: GearItem | undefined, f: Facing): string[] => {
    const spec = base();
    const gear: DollSpec["gear"] = { ...spec.gear, feet: { kind: "greaves", form: "knee", material: "steel" } };
    if (body === undefined) delete gear.body;
    else gear.body = body;
    const { ctx, calls } = recorder();
    drawFigure(ctx, { ...spec, gear }, f);
    return fills(calls);
  };
  const steel = itemColors({ kind: "greaves", form: "knee", material: "steel" })[0];

  it("板甲腿的護膝比鋼色亮 35%（保留墨線）；其他腿不變", () => {
    const light = lighten(steel, 0.35);
    expect(light).not.toBe(steel);
    for (const f of ["south", "east"] as const) {
      expect(kneeFills({ kind: "plate", material: "steel" }, f), f).toContain(light);
      expect(kneeFills({ kind: "leather", material: "leather" }, f), f).not.toContain(light);
      expect(kneeFills(undefined, f), f).not.toContain(light);
    }
    // 背面不畫護膝
    expect(kneeFills({ kind: "plate", material: "steel" }, "north")).not.toContain(light);
  });
});
