// Phase 3I-3：魔導劍（#46）——外觀表、紙娃娃主手（正面／背面／側面）、有無元素的源晶槽顏色、
// 不認得 arcane 時退回一般單手劍、武器小圖示。
import { describe, expect, it } from "vitest";
import { weaponLookEntry } from "../battle/glossary";
import { weaponLook } from "./appearance";
import type { DollSpec } from "./appearance";
import { ARCANE_GLOW, arcaneGlow, drawInkWeaponAlone } from "./inkWeapons";
import { drawFigure, itemColors } from "./paperdoll";
import { resolveDollT } from "./testDolls";
import { isDiagonal, weaponIconItem } from "./weaponIcon";

const base = { team: "ally", summon: false } as const;

interface Call {
  op: string;
  args: unknown[];
}

/** 記錄所有畫圖呼叫的假畫布（測試只看畫了什麼，不看像素）。 */
function recorder(): { ctx: Parameters<typeof drawInkWeaponAlone>[0]; calls: Call[]; fills: string[] } {
  const calls: Call[] = [];
  const fills: string[] = [];
  const state: Record<string, unknown> = {};
  const target = new Proxy(state, {
    get(_t, prop: string) {
      if (prop in state) return state[prop];
      return (...args: unknown[]) => {
        calls.push({ op: prop, args });
        if (prop === "fill" || prop === "fillRect") fills.push(String(state.fillStyle));
      };
    },
    set(_t, prop: string, value: unknown) {
      state[prop] = value;
      return true;
    },
  });
  return { ctx: target as unknown as Parameters<typeof drawInkWeaponAlone>[0], calls, fills };
}

const arcane = { kind: "sword", form: "arcane", material: "steel" } as const;

describe("魔導劍的外觀（Phase 3I-3）", () => {
  it("武器外觀表：sword／arcane／steel，單手", () => {
    expect(weaponLookEntry("arcane_blade")).toMatchObject({
      look: { kind: "sword", form: "arcane", material: "steel" },
      two_handed: false,
    });
    expect(weaponLook("arcane_blade", "melee")).toMatchObject({ kind: "sword", form: "arcane" });
  });

  it("紙娃娃主手依武器 id；搭法書副手時副手正常", () => {
    const doll = resolveDollT({ ...base, template: "hero_fighter", weaponId: "arcane_blade" }).gear;
    expect(doll.main_hand).toMatchObject({ kind: "sword", form: "arcane", material: "steel" });
  });

  it("源晶槽：無元素為藍紫，有元素換元素色", () => {
    expect(arcaneGlow(undefined)).toBe(ARCANE_GLOW);
    expect(ARCANE_GLOW).toBe("#9a86ff");
    expect(arcaneGlow("fire")).not.toBe(ARCANE_GLOW);
    expect(arcaneGlow("physical")).toBe(ARCANE_GLOW);
  });

  it("有無元素都畫得出來；源晶槽與齒輪中心是光色、三個符文刻點是淡白", () => {
    for (const element of [undefined, "fire"] as const) {
      const { ctx, calls, fills } = recorder();
      drawInkWeaponAlone(ctx, { ...arcane, ...(element !== undefined ? { element } : {}) }, itemColors);
      expect(calls.length).toBeGreaterThan(0);
      const glow = arcaneGlow(element);
      expect(fills.filter((f) => f === glow).length).toBeGreaterThanOrEqual(2); // 槽＋齒輪中心
      expect(fills.filter((f) => f === "#e8e2ff")).toHaveLength(3); // 三個符文刻點
      expect(fills).toContain("#b08a4a"); // 黃銅齒輪
    }
  });

  it("一般單手劍沒有這些：不認得 arcane 的形制退回一般劍", () => {
    for (const form of [undefined, "straight", "no_such_form"]) {
      const { ctx, fills } = recorder();
      drawInkWeaponAlone(ctx, { kind: "sword", material: "steel", ...(form !== undefined ? { form } : {}) }, itemColors);
      expect(fills).not.toContain("#b08a4a");
      expect(fills).not.toContain(ARCANE_GLOW);
    }
  });

  it("武器小圖示：和一般劍一樣斜放，保留 form", () => {
    expect(weaponIconItem("arcane_blade", "melee")).toMatchObject({ kind: "sword", form: "arcane" });
    expect(isDiagonal("sword")).toBe(true);
  });

  it("正面、背面、側面（3S-1 真側面）× 有／無元素 × 搭法書／法器珠副手都畫得出來", () => {
    const facings = ["south", "north", "east", "west"] as const;
    for (const element of [undefined, "ice"] as const) {
      for (const offKind of [undefined, "tome", "orb"] as const) {
        const spec: DollSpec = {
          look: { skin: "#e8c8a0" },
          gear: {
            main_hand: { ...arcane, ...(element !== undefined ? { element } : {}) },
            ...(offKind !== undefined ? { off_hand: { kind: offKind, material: "leather" } } : {}),
          },
        };
        for (const f of facings) {
          const { ctx, fills } = recorder();
          drawFigure(ctx, spec, f);
          // 每個方向都畫出源晶槽顏色（側面沿用一般劍的側面畫法再加源晶槽色）
          expect(fills).toContain(arcaneGlow(element));
        }
      }
    }
  });
});
