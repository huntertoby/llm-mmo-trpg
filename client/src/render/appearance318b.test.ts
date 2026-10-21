// Phase 3-18b：外觀小修（docs/art/3-16b檢查.md 第 1–3 項）與 `weapon_class` 退回。
import { describe, expect, it } from "vitest";
import { dollKey, resolveDoll } from "./appearance";

const base = { team: "ally", summon: false } as const;
const doll = (template: string) => resolveDoll({ ...base, template, weaponId: "one_handed_sword" });

describe("四個改外觀的單位", () => {
  it("bandit_warlord：鐵盔＋板甲＋深色披風 #3a2a4a，不加外光（外光留給 bandit_boss）", () => {
    const d = doll("bandit_warlord");
    expect(d.gear.head?.kind).toBe("helmet");
    expect(d.gear.head?.material).toBe("iron");
    expect(d.gear.body?.kind).toBe("plate");
    expect(d.gear.cloak?.color).toBe("#3a2a4a");
    expect(d.rarity).toBeUndefined();
    expect(doll("bandit_boss").rarity).toBe("epic");
    expect(dollKey(d, "south", false)).not.toBe(dollKey(doll("bandit_boss"), "south", false));
  });

  it("hero_stormcaller：法袍與帽子深藍 #2c4f8a、飾邊雷黃 #fff36b，和紫袍的 hero_mage 不同", () => {
    const d = doll("hero_stormcaller");
    expect(d.gear.body).toMatchObject({ kind: "robe", color: "#2c4f8a" });
    expect(d.gear.head).toMatchObject({ kind: "wizard_hat", color: "#2c4f8a" });
    expect(d.look.trim).toBe("#fff36b");
    expect(doll("hero_mage").gear.body?.color).not.toBe(d.gear.body?.color);
  });

  it("sim_companion_fighter：鎖甲＋鳶盾、不披披風；和主角戰士不同", () => {
    const d = doll("sim_companion_fighter");
    expect(d.gear.body?.kind).toBe("mail");
    expect(d.gear.off_hand?.kind).toBe("shield_kite");
    expect(d.gear.cloak).toBeUndefined();
    expect(doll("hero_fighter").gear.cloak).toBeDefined();
  });

  it("sim_companion_archer：皮背心、不戴兜帽；和主角弓手不同", () => {
    const d = resolveDoll({ ...base, template: "sim_companion_archer", weaponId: "bow" });
    expect(d.gear.body).toMatchObject({ kind: "leather", material: "leather" });
    expect(d.gear.head).toBeUndefined();
    expect(resolveDoll({ ...base, template: "hero_archer", weaponId: "bow" }).gear.head?.kind).toBe("hood");
  });
});

describe("未知 weapon_id 依 weapon_class 退回對應武器圖", () => {
  const main = (weaponId: string, weaponClass: string | null) => resolveDoll({ ...base, template: "x", weaponId, weaponClass }).gear.main_hand?.kind;
  it("遠程 → 弓、法器 → 杖、近戰 → 劍；沒有類別畫劍", () => {
    expect(main("mystery_bow", "ranged")).toBe("bow");
    expect(main("mystery_wand", "focus")).toBe("staff");
    expect(main("mystery_blade", "melee")).toBe("sword");
    expect(main("mystery", null)).toBe("sword");
    expect(main("mystery", "weird")).toBe("sword");
  });
  it("認得的 weapon_id 不受 weapon_class 影響", () => {
    expect(main("dagger", "ranged")).toBe("dagger");
  });
});
