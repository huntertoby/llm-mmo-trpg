// Phase 3I-1：拳套、鐮刀、鞭——武器外觀表（glossary）、紙娃娃主手、武器小圖示（鐮刀與鞭斜放）。
import { describe, expect, it } from "vitest";
import { weaponLookEntry } from "../battle/glossary";
import { weaponLook } from "./appearance";
import { resolveDollT } from "./testDolls";
import { isDiagonal, weaponIconItem } from "./weaponIcon";

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
    expect(isDiagonal("scythe")).toBe(true);
    expect(isDiagonal("whip")).toBe(true);
    expect(isDiagonal("fist")).toBe(false);
  });
});
