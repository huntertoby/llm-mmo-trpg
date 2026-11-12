// Phase 3-24a2：弩（輕、重、連弩）與火槍（燧發、獵槍、狙擊）的造型——外觀表、快取鍵與紙娃娃／小圖示的繪製資料。
import { describe, expect, it } from "vitest";
import { type Facing } from "../api/types";
import { dollKey, KNOWN_KINDS, weaponLook, type DollSpec } from "./appearance";
import { resolveDollT } from "./testDolls";
import { weaponLookEntry } from "../battle/glossary";
import { drawInkWeaponAlone } from "./inkWeapons";
import { drawFigure, itemColors } from "./paperdoll";
import { weaponIconDef, weaponIconItem } from "./weaponIcon";

const iconDiag = (weaponId: string, cls: string): boolean | undefined => weaponIconDef(weaponIconItem(weaponId, cls))?.meta.diag;

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
const base = { team: "ally", summon: false } as const;

const CROSSBOWS = ["light", "heavy", "repeater"] as const;
const LONGGUNS = ["flintlock", "hunting", "sniper"] as const;

function drawn(kind: string, form: string, material: string): string[] {
  const { ctx, calls } = mockCtx();
  drawInkWeaponAlone(ctx as unknown as Parameters<typeof drawInkWeaponAlone>[0], { kind, material, form }, itemColors);
  return calls;
}

describe("武器外觀表（Phase 3-24a2）", () => {
  it("弩與火槍都有自己的造型，不再退回畫弓", () => {
    expect(weaponLookEntry("crossbow")).toMatchObject({ look: { kind: "crossbow", material: "wood" }, two_handed: true });
    expect(weaponLookEntry("longgun")).toMatchObject({ look: { kind: "longgun", material: "steel" }, two_handed: true });
    expect(KNOWN_KINDS.main_hand).toEqual(expect.arrayContaining(["crossbow", "longgun"]));
    // 武器大類退回仍是弓；但這兩個 id 認得，不會走退回
    expect(weaponLook("crossbow", "ranged").kind).toBe("crossbow");
    expect(weaponLook("longgun", "ranged").kind).toBe("longgun");
    expect(weaponLook("mystery", "ranged").kind).toBe("bow");
  });

  it("紙娃娃主手依武器 id，雙手武器副手留空，形制進快取鍵", () => {
    const look = (id: string) => resolveDollT({ ...base, template: "hero_fighter", weaponId: id }).gear;
    expect(look("crossbow").main_hand).toMatchObject({ kind: "crossbow", form: "light" });
    expect(look("longgun").main_hand).toMatchObject({ kind: "longgun", form: "flintlock" });
    expect(look("crossbow").off_hand).toBeUndefined();
    expect(look("longgun").off_hand).toBeUndefined();
    const spec = (form: string): DollSpec => ({ look: { skin: "#fff", hair: "long" }, gear: { main_hand: { kind: "crossbow", material: "wood", form } } });
    const keys = CROSSBOWS.map((f) => dollKey(spec(f), "south", false));
    expect(new Set(keys).size).toBe(3);
  });

  it("武器小圖示畫的是同一件主手（不是弓）", () => {
    expect(weaponIconItem("crossbow", "ranged")).toMatchObject({ kind: "crossbow", form: "light" });
    expect(weaponIconItem("longgun", "ranged")).toMatchObject({ kind: "longgun", form: "flintlock" });
  });
});

describe("弩與火槍的繪製資料", () => {
  it("三種弩（輕、重、連弩）的畫法各不相同、確定性，也不同於弓", () => {
    const [light, heavy, repeater] = CROSSBOWS.map((f) => drawn("crossbow", f, "wood"));
    expect(light!.length).toBeGreaterThan(10);
    expect(new Set([light!.join("|"), heavy!.join("|"), repeater!.join("|")]).size).toBe(3);
    expect(drawn("crossbow", "light", "wood")).toEqual(light);
    expect(light!.join("|")).not.toBe(drawn("bow", "", "wood").join("|"));
  });

  it("三種火槍（燧發、獵槍、狙擊）的畫法各不相同、確定性，也不同於弓", () => {
    const [flint, hunting, sniper] = LONGGUNS.map((f) => drawn("longgun", f, "steel"));
    expect(flint!.length).toBeGreaterThan(10);
    expect(new Set([flint!.join("|"), hunting!.join("|"), sniper!.join("|")]).size).toBe(3);
    expect(drawn("longgun", "sniper", "steel")).toEqual(sniper);
    expect(flint!.join("|")).not.toBe(drawn("bow", "", "wood").join("|"));
  });

  it("材質改變會改變顏色（火槍的槍身取材質色）", () => {
    expect(drawn("longgun", "hunting", "steel").join("|")).not.toBe(drawn("longgun", "hunting", "iron").join("|"));
    expect(drawn("crossbow", "light", "wood").join("|")).not.toBe(drawn("crossbow", "light", "iron").join("|"));
  });

  it("每種形制 × 4 朝向的紙娃娃都畫得出來、不丟例外", () => {
    for (const [kind, forms, material] of [
      ["crossbow", CROSSBOWS, "wood"],
      ["longgun", LONGGUNS, "steel"],
    ] as const) {
      for (const form of forms) {
        for (const facing of FACINGS) {
          const spec: DollSpec = { look: { skin: "#f0c8a0", hair: "short" }, gear: { main_hand: { kind, material, form } } };
          const { ctx, calls } = mockCtx();
          expect(() => drawFigure(ctx, spec, facing)).not.toThrow();
          expect(calls.length).toBeGreaterThan(30);
        }
      }
    }
  });

  it("不認得的形制退回預設形制、不丟例外", () => {
    expect(() => drawn("crossbow", "weird", "wood")).not.toThrow();
    expect(() => drawn("longgun", "weird", "steel")).not.toThrow();
  });
});

// --- 原 weapons3i1.test.ts ---
describe("原 weapons3i1.test.ts", () => {
// Phase 3I-1：拳套、鐮刀、鞭——武器外觀表（glossary）、紙娃娃主手、武器小圖示（鐮刀與鞭斜放）。

const base = { team: "ally", summon: false } as const;

describe("第二批主武器的外觀（Phase 3I-1）", () => {
  it("拳套、鐮刀、鞭在外觀表裡有自己的 kind／form／material", () => {
    expect(weaponLookEntry("fist")).toMatchObject({ look: { kind: "fist", form: "knuckle", material: "iron" }, two_handed: true });
    expect(weaponLookEntry("scythe")).toMatchObject({ look: { kind: "scythe", form: "long", material: "iron" }, two_handed: true });
    expect(weaponLookEntry("whip")).toMatchObject({ look: { kind: "whip", form: "leather", material: "leather" }, two_handed: false });
    expect(weaponLook("whip", "melee").kind).toBe("whip");
  });

  it("紙娃娃主手依武器 id；雙手的鐮刀副手留空", () => {
    const look = (id: string) => resolveDollT({ ...base, template: "hero_fighter", weaponId: id }).gear;
    expect(look("fist").main_hand).toMatchObject({ kind: "fist", form: "knuckle" });
    expect(look("scythe").main_hand).toMatchObject({ kind: "scythe", form: "long" });
    expect(look("whip").main_hand).toMatchObject({ kind: "whip", form: "leather" });
    expect(look("scythe").off_hand).toBeUndefined();
  });

  it("武器小圖示：鐮刀與鞭斜放（美術 PM 小項），拳套直立", () => {
    expect(weaponIconItem("scythe", "melee")).toMatchObject({ kind: "scythe" });
    expect(iconDiag("scythe", "melee")).toBe(true);
    expect(iconDiag("whip", "melee")).toBe(true);
    expect(iconDiag("fist", "melee")).toBe(false); // 3T-4c：拳套（鐵拳）正面直立不斜放（QI-1a：看 Q 版 meta.diag）
  });
});
});

// --- 原 weapons3i4.test.ts ---
describe("原 weapons3i4.test.ts", () => {
// Phase 3I-4：雙匕首、霰彈槍、手槍、雙手槍——武器外觀表（glossary）、紙娃娃主手與副手、武器小圖示。

const base = { team: "ally", summon: false } as const;
const look = (id: string) => resolveDollT({ ...base, template: "hero_fighter", weaponId: id }).gear;

describe("第二批其他武器的外觀（Phase 3I-4）", () => {
  it("外觀表有自己的 kind／form／material，握法與資料一致", () => {
    expect(weaponLookEntry("dual_dagger")).toMatchObject({ look: { kind: "dual_dagger", form: "short", material: "iron" }, two_handed: false });
    expect(weaponLookEntry("shotgun")).toMatchObject({ look: { kind: "shotgun", form: "double" }, two_handed: true });
    expect(weaponLookEntry("pistol")).toMatchObject({ look: { kind: "pistol", form: "revolver" }, two_handed: false });
    expect(weaponLookEntry("dual_pistol")).toMatchObject({ look: { kind: "dual_pistol", form: "revolver" }, two_handed: false });
  });

  it("成對武器的紙娃娃：主手、副手各一把；霰彈槍雙手副手留空；手槍單手", () => {
    const dagger = look("dual_dagger");
    expect(dagger.main_hand).toMatchObject({ kind: "dagger" });
    expect(dagger.off_hand).toMatchObject({ kind: "dagger" });
    const pistols = look("dual_pistol");
    expect(pistols.main_hand).toMatchObject({ kind: "pistol" });
    expect(pistols.off_hand).toMatchObject({ kind: "pistol" });
    expect(look("shotgun").main_hand).toMatchObject({ kind: "shotgun" });
    expect(look("shotgun").off_hand).toBeUndefined();
    expect(look("pistol").main_hand).toMatchObject({ kind: "pistol" });
  });

  it("武器小圖示：成對武器保留成對造型、畫兩把（QI-1a；需求 3.2 第 10 點：不再換成單把）", () => {
    expect(weaponIconItem("dual_dagger", "melee")).toMatchObject({ kind: "dual_dagger", form: "short" });
    expect(weaponIconDef(weaponIconItem("dual_dagger", "melee"))?.meta.r).toMatchObject({ kind: "dual_dagger", form: "short" });
    expect(weaponIconItem("dual_pistol", "ranged")).toMatchObject({ kind: "dual_pistol", form: "revolver" });
    expect(weaponIconItem("shotgun", "ranged")).toMatchObject({ kind: "shotgun" });
  });
});
});
