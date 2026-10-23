import { describe, expect, it } from "vitest";
import { dollKey, elementTint } from "./appearance";
import { resolveDollT } from "./testDolls";

const base = { team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" } as const;

describe("臨時附魔的外觀（Phase 3I-6）", () => {
  it("有生效的攻擊元素時主手改用該元素色，且貼圖快取鍵不同", () => {
    const plain = resolveDollT(base);
    const fiery = resolveDollT({ ...base, attackElement: "fire" });
    expect(plain.gear.main_hand?.element).toBeUndefined();
    expect(fiery.gear.main_hand?.element).toBe("fire");
    expect(elementTint(fiery.gear.main_hand?.element)).toBeDefined();
    expect(dollKey(fiery, "south", false)).not.toBe(dollKey(plain, "south", false));
  });

  it("物理與缺漏沿用武器外觀；法杖被附魔時改成附魔元素", () => {
    expect(resolveDollT({ ...base, attackElement: "physical" })).toEqual(resolveDollT(base));
    expect(resolveDollT({ ...base, attackElement: null })).toEqual(resolveDollT(base));
    const staff = { ...base, weaponId: "fire_staff" } as const;
    expect(resolveDollT(staff).gear.main_hand?.element).toBe("fire");
    expect(resolveDollT({ ...staff, attackElement: "holy" }).gear.main_hand?.element).toBe("holy");
  });
});
