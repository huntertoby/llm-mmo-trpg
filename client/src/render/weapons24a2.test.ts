// Phase 3-24a2：弩（輕、重、連弩）與火槍（燧發、獵槍、狙擊）的造型——外觀表、快取鍵與紙娃娃／小圖示的繪製資料。
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import { dollKey, KNOWN_KINDS, weaponLook, type DollSpec } from "./appearance";
import { resolveDollT } from "./testDolls";
import { weaponLookEntry } from "../battle/glossary";
import { drawInkWeaponAlone } from "./inkWeapons";
import { drawFigure, itemColors } from "./paperdoll";
import { weaponIconItem } from "./weaponIcon";

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
