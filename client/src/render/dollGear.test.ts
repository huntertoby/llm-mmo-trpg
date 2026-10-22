// Phase 3G-G5b：裝備外觀 → 紙娃娃（對照表、退回預設、成對武器、全組合畫得出來）。
import { describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import { dollKey, KNOWN_KINDS, resolveDoll, type DollSpec } from "./appearance";
import { dollGear, dollItem, type DollEquipment } from "./dollGear";
import { gearKinds } from "./gearIcon";
import appearance from "./gearAppearance.json";
import { drawFigure } from "./paperdoll";

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
const base = { team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" } as const;
const eq = (slot: string, kind: string | null, extra: Record<string, unknown> = {}): DollEquipment => ({ slot, appearance: { kind, ...extra } });

describe("dollItem（對照表）", () => {
  it("每個造型的每個形制都對得到紙娃娃認得的部件；項鍊、戒指不畫", () => {
    for (const k of gearKinds()) {
      for (const f of k.forms) {
        const slot = { weapon: "main_hand", offhand: "off_hand", body: "body", head: "head", hands: "hands", feet: "feet", neck: "neck", ring: "ring_1" }[k.slotType] as string;
        const d = dollItem({ kind: k.id, form: f.id }, slot);
        if (k.slotType === "neck" || k.slotType === "ring") {
          expect(d).toBeNull();
          continue;
        }
        expect(d, `${k.id}/${f.id}`).not.toBeNull();
        expect(KNOWN_KINDS[d!.slot]).toContain(d!.item.kind);
      }
    }
  });

  it("頭：帽、頭環、盔依形制分流", () => {
    const part = (kind: string, form: string) => dollItem({ kind, form }, "head")?.item.kind;
    expect([part("hat", "wizard"), part("hat", "wide")]).toEqual(["wizard_hat", "wide_hat"]);
    expect([part("circlet", "bandana"), part("circlet", "crown")]).toEqual(["bandana", "crown"]);
    expect([part("helmet", "iron"), part("helmet", "horned"), part("helmet", "greathelm")]).toEqual(["helmet", "horned_helm", "greathelm"]);
    expect([part("hood", "cloth"), part("cap", "fur")]).toEqual(["hood", "cap"]);
  });

  it("手套合併、盾與火器改名、成對武器退成單把", () => {
    expect(dollItem({ kind: "cloth_gloves" }, "hands")?.item.kind).toBe("gloves");
    expect(dollItem({ kind: "leather_gloves", form: "long" }, "hands")?.item).toMatchObject({ kind: "gloves", form: "long" });
    expect(dollItem({ kind: "round_shield" }, "off_hand")?.item.kind).toBe("shield_round");
    expect(dollItem({ kind: "kite_shield", form: "tower" }, "off_hand")?.item).toMatchObject({ kind: "shield_kite", form: "tower" });
    expect(dollItem({ kind: "dual_dagger" }, "main_hand")).toMatchObject({ paired: true, item: { kind: "dagger" } });
    expect(dollItem({ kind: "dual_pistol" }, "main_hand")).toMatchObject({ paired: true, item: { kind: "pistol" } });
  });

  it("染色只對布、皮有效；元素關鍵字對應 element", () => {
    expect(dollItem({ kind: "robe", dye: "red" }, "body")?.item.color).toBe("#b83a3a");
    expect(dollItem({ kind: "plate", dye: "red" }, "body")?.item.color).toBeUndefined();
    const el = (k: string) => dollItem({ kind: "sword", keywords: [k] }, "main_hand")?.item.element;
    expect([el("ignite"), el("wet"), el("charged"), el("frozen")]).toEqual(["fire", "water", "lightning", "ice"]);
    expect(el("prone")).toBeUndefined();
    expect(dollItem({ kind: "sword", keywords: ["prone", "frozen"] }, "main_hand")?.item.element).toBe("ice");
  });

  it("不認得的值退回預設、不丟例外；造型和欄位不符時退回該欄位預設", () => {
    expect(dollItem({ kind: "???", form: "x", material: "unobtainium", dye: "pink", keywords: ["nope"] }, "main_hand")?.item).toMatchObject({ kind: "sword", form: "straight", material: "iron" });
    expect(dollItem(null, "head")?.item.kind).toBe("helmet");
    expect(dollItem(undefined, "feet")?.item.kind).toBe("boots");
    expect(dollItem({ kind: "sword" }, "head")?.item.kind).toBe("helmet");
    expect(dollItem({ kind: "helmet", form: "weird" }, "head")?.item.kind).toBe("helmet");
    expect(dollItem({ kind: "plate" }, "mystery_slot")).toBeNull();
  });
});

describe("dollGear（一整套裝備）", () => {
  it("成對武器：主手、副手各一把單把的武器", () => {
    const g = dollGear([eq("main_hand", "dual_dagger", { material: "steel" })]);
    expect(g.gear.main_hand).toMatchObject({ kind: "dagger", material: "steel" });
    expect(g.gear.off_hand).toMatchObject({ kind: "dagger", material: "steel" });
    expect(g.paired).toBe(true);
    expect(dollGear([eq("main_hand", "dual_pistol")]).gear.off_hand?.kind).toBe("pistol");
    expect(dollGear([eq("main_hand", "sword")]).paired).toBe(false);
  });

  it("項鍊、戒指不畫；結果不依陣列順序；不帶稀有度", () => {
    const a = dollGear([eq("neck", "pendant"), eq("ring_1", "ring"), eq("head", "helmet", { rarity: "epic" }), eq("body", "robe", { rarity: "legendary" })]);
    const b = dollGear([eq("body", "robe", { rarity: "legendary" }), eq("head", "helmet", { rarity: "epic" }), eq("ring_2", "ring")]);
    expect(Object.keys(a.gear).sort()).toEqual(["body", "head"]);
    expect(a).toEqual(b);
    expect("rarity" in a).toBe(false);
  });
});

describe("resolveDoll（有穿裝備的單位）", () => {
  it("沒有裝備或空陣列：和舊畫面完全一樣", () => {
    const plain = resolveDoll(base);
    expect(resolveDoll({ ...base, equipment: [] })).toEqual(plain);
    expect(resolveDoll({ ...base, equipment: undefined })).toEqual(plain);
  });

  it("穿了的欄位依外觀畫，沒穿的沿用範本", () => {
    const d = resolveDoll({ ...base, equipment: [eq("head", "hat", { form: "wide", dye: "red" }), eq("feet", "iron_boots")] });
    expect(d.gear.head).toMatchObject({ kind: "wide_hat" });
    expect(d.gear.feet).toMatchObject({ kind: "iron_boots", material: "iron" });
    expect(d.gear.body).toEqual(resolveDoll(base).gear.body); // hero_fighter 的板甲
    expect(d.gear.off_hand?.kind).toBe("shield_round");
    expect(d.gear.cloak).toEqual(resolveDoll(base).gear.cloak);
  });

  it("主手：有造型就用裝備的，沒寫造型沿用武器 id 的外觀", () => {
    expect(resolveDoll({ ...base, equipment: [eq("main_hand", "pistol", { form: "revolver" })] }).gear.main_hand).toMatchObject({ kind: "pistol", form: "revolver" });
    expect(resolveDoll({ ...base, weaponId: "bow", equipment: [eq("main_hand", null)] }).gear.main_hand?.kind).toBe("bow");
  });

  it("雙手武器副手留空；單手保留；成對武器副手是第二把", () => {
    const two = resolveDoll({ ...base, weaponId: "greatsword", equipment: [eq("main_hand", "greatsword")] });
    expect(two.gear.off_hand).toBeUndefined();
    const newTwo = resolveDoll({ ...base, weaponId: "mystery_cannon", equipment: [eq("main_hand", "scythe")] });
    expect(newTwo.gear.off_hand).toBeUndefined();
    expect(resolveDoll({ ...base, equipment: [eq("main_hand", "axe")] }).gear.off_hand?.kind).toBe("shield_round");
    const pair = resolveDoll({ ...base, weaponId: "dagger", equipment: [eq("main_hand", "dual_dagger")] });
    expect(pair.gear.main_hand?.kind).toBe("dagger");
    expect(pair.gear.off_hand?.kind).toBe("dagger");
    const pairBow = resolveDoll({ ...base, weaponId: "bow", equipment: [eq("main_hand", "dual_pistol")] });
    expect(pairBow.gear.off_hand?.kind).toBe("pistol");
  });

  it("裝備稀有度不讓小人帶外光；範本（頭目）原有的外光保留", () => {
    expect(resolveDoll({ ...base, equipment: [eq("body", "plate", { rarity: "legendary" })] }).rarity).toBeUndefined();
    expect(resolveDoll({ ...base, template: "bandit_boss", equipment: [eq("body", "plate", { rarity: "legendary" })] }).rarity).toBe("epic");
  });

  it("快取鍵：外觀不同則不同，相同輸入相同", () => {
    const k = (e: DollEquipment[]) => dollKey(resolveDoll({ ...base, equipment: e }), "south", false);
    expect(k([eq("head", "helmet")])).toBe(k([eq("head", "helmet")]));
    expect(k([eq("head", "helmet")])).not.toBe(k([eq("head", "hood")]));
    expect(k([eq("head", "helmet", { material: "steel" })])).not.toBe(k([eq("head", "helmet", { material: "gold" })]));
    expect(k([eq("main_hand", "hammer", { form: "mace" })])).not.toBe(k([eq("main_hand", "hammer", { form: "flail" })]));
  });
});

describe("全組合畫得出來", () => {
  it("每個造型 × 形制 × 4 朝向、材質（含不認得）× 關鍵字（含不認得）：不丟例外、不用 Math.random", () => {
    const spy = vi.spyOn(Math, "random");
    const slotOf = { weapon: "main_hand", offhand: "off_hand", body: "body", head: "head", hands: "hands", feet: "feet" } as const;
    let drawn = 0;
    for (const k of gearKinds()) {
      const slot = slotOf[k.slotType as keyof typeof slotOf];
      if (slot === undefined) continue;
      for (const form of [...k.forms.map((f) => f.id), "???"]) {
        for (const material of [...appearance.materials, "???"]) {
          for (const keywords of [[], ["ignite"], ["frozen", "summon"], ["nope"]]) {
            const spec: DollSpec = resolveDoll({ ...base, equipment: [{ slot, appearance: { kind: k.id, form, material, dye: "red", keywords } }] });
            for (const f of FACINGS) {
              const { ctx } = mockCtx();
              expect(() => drawFigure(ctx, spec, f)).not.toThrow();
              drawn++;
            }
          }
        }
      }
    }
    expect(drawn).toBeGreaterThan(5000);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  }, 30_000); // 全組合較重，機器忙時（多個 agent 同時跑）5 秒不夠

  it("成對武器與拳套：副手那一側也畫手持物", () => {
    const count = (equipment: DollEquipment[], weaponId: string, op: string): number => {
      const { ctx, calls } = mockCtx();
      drawFigure(ctx, resolveDoll({ ...base, template: "unknown_ally", weaponId, equipment }), "south");
      return calls.filter((c) => c.startsWith(op)).length;
    };
    // 匕首每把轉一次；成對匕首兩把
    expect(count([eq("main_hand", "dagger")], "dagger", "rotate")).toBe(1);
    expect(count([eq("main_hand", "dual_dagger")], "dagger", "rotate")).toBe(2);
    // 拳套每隻手一個圓角方塊：兩手各一個，比單把匕首（沒有圓角方塊）多 2 個
    expect(count([eq("main_hand", "fist")], "dagger", "roundRect") - count([eq("main_hand", "dagger")], "dagger", "roundRect")).toBe(2);
  });

  it("蓋住頭髮頂的頭部裝備：全罩盔、皮帽與頭盔一樣不畫髮頂", () => {
    const count = (kind: string, form?: string): number => {
      const { ctx, calls } = mockCtx();
      drawFigure(ctx, resolveDoll({ ...base, equipment: [eq("head", kind, form === undefined ? {} : { form })] }), "south");
      return calls.filter((c) => c.startsWith("quadraticCurveTo")).length;
    };
    // 髮頂用 quadraticCurveTo 畫；沒戴頭部裝備時有畫，蓋住頭髮的裝備比較少
    const bare = (() => {
      const { ctx, calls } = mockCtx();
      drawFigure(ctx, resolveDoll(base), "south");
      return calls.filter((c) => c.startsWith("quadraticCurveTo")).length;
    })();
    expect(count("helmet")).toBeLessThan(bare);
    expect(count("helmet", "greathelm")).toBeLessThan(bare);
    expect(count("cap")).toBeLessThan(bare);
    expect(count("hat", "wide")).toBe(bare); // 寬簷帽沒蓋住髮頂
  });
});
