// Phase 3E-2e：效果／條件／觸發的中文名與說明、武器與單位外觀都來自後端（glossary、doll_look），前端沒有寫死的 ID 表。
import { afterEach, describe, expect, it } from "vitest";
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { resolveDoll, weaponLook } from "./appearance";
import { conditionPart, effectPart, partTip, triggerPart } from "./skillParts";

const real = glossary as unknown as Glossary;
afterEach(() => setGlossary(real));

describe("部件名稱讀 glossary", () => {
  it("效果、條件、觸發的名稱與說明來自 API 資料", () => {
    expect(effectPart({ type: "damage" }).label).toBe("傷害");
    expect(effectPart({ type: "damage" }).description).toContain("傷害");
    expect(conditionPart("height_advantage")?.label).toBe("居高臨下");
    expect(triggerPart("on_kill", false)?.label).toBe("擊倒時");
    expect(triggerPart("hit_by_melee", true)?.label).toBe("被近戰擊中時");
    expect(partTip(effectPart({ type: "heal" }))).toMatch(/^效果原語：/);
  });

  it("新增原語只要 glossary 有一列就顯示中文名；沒有時顯示代碼、不壞", () => {
    expect(effectPart({ type: "brand_new" }).label).toBe("brand_new");
    expect(effectPart({ type: "brand_new" }).description).toBeUndefined();
    setGlossary({ ...real, effects: [...real.effects, { id: "brand_new", name_zh: "全新原語", description_zh: "新的說明", tags: [], rules_zh: [] }] });
    expect(effectPart({ type: "brand_new" }).label).toBe("全新原語");
    expect(partTip(effectPart({ type: "brand_new" }))).toBe("效果原語：新的說明");
  });
});

describe("武器外觀讀 glossary", () => {
  it("新武器只要後端有 look 就有造型，不必改前端", () => {
    expect(weaponLook("mystery_blade", "melee").kind).toBe("sword"); // 沒有資料：依武器大類退回
    setGlossary({
      ...real,
      weapon_looks: [...real.weapon_looks, { id: "mystery_blade", weapon_class: "melee", two_handed: true, look: { kind: "scythe", material: "steel" } }],
    });
    expect(weaponLook("mystery_blade", "melee")).toMatchObject({ kind: "scythe", material: "steel", twoHanded: true });
    const doll = resolveDoll({ team: "ally", summon: false, template: "x", weaponId: "mystery_blade" });
    expect(doll.gear.main_hand?.kind).toBe("scythe");
  });
});

describe("單位外觀讀 doll_look", () => {
  it("有 doll_look 就依它畫；沒有依陣營退回", () => {
    const withLook = resolveDoll({
      team: "enemy",
      summon: false,
      template: "anything",
      dollLook: { skin: "#a8724c", skull: false, gear: { body: { kind: "plate", material: "steel" } }, rarity: "epic" },
      weaponId: "dagger",
    });
    expect(withLook.gear.body?.kind).toBe("plate");
    expect(withLook.rarity).toBe("epic");
    const without = resolveDoll({ team: "enemy", summon: false, template: "anything", dollLook: null, weaponId: "dagger" });
    expect(without.gear.body?.kind).toBe("leather");
  });
});
