// 鎖定欄位（Phase 3H-6，武器技的縮放屬性看手上武器）：值由規則決定，草稿會對齊成唯一的選項。
import { describe, expect, it } from "vitest";
import type { Choice, DraftOptions, FieldSpec } from "../api/types";
import { autoSingles, conformScaling, type Json } from "./draft";

const only: Choice = { value: "str", name_zh: "看手上武器（力量）", description_zh: "", dev_description_zh: "", later: false, params: [], info: {} };
const scaling = (locked: boolean): FieldSpec => ({
  field: "scaling_attr",
  name_zh: "縮放屬性",
  description_zh: "", dev_description_zh: "", later: false,
  type: "choice",
  required: true,
  choices: [only],
  fields: [],
  dice_sides: [],
  allow_weapon: false,
  locked,
  show_when: {},
  card: false,
  object_choice: false,
});

describe("locked single-choice field", () => {
  it("fills an empty draft and overrides a stale value", () => {
    expect(autoSingles({}, [scaling(true)])).toEqual({ scaling_attr: "str" });
    const stale: Json = { scaling_attr: "int" };
    expect(autoSingles(stale, [scaling(true)])).toEqual({ scaling_attr: "str" });
  });

  it("returns the same object when the value already matches", () => {
    const draft: Json = { scaling_attr: "str" };
    expect(autoSingles(draft, [scaling(true)])).toBe(draft);
  });

  it("keeps the player's pick for an unlocked single-choice field", () => {
    const draft: Json = { scaling_attr: "int" };
    expect(autoSingles(draft, [scaling(false)])).toBe(draft);
  });
});

// 3-48：允許範圍改變（類別、武器需求、效果）後，草稿裡不合法的縮放屬性自動對齊
const choice = (value: string): Choice => ({ value, name_zh: value, description_zh: "", dev_description_zh: "", later: false, params: [], info: {} });
const optionsWith = (primary: string[], secondary?: string[]): DraftOptions => {
  const field = (name: string, values: string[]): FieldSpec => ({ ...scaling(false), field: name, choices: values.map(choice) });
  const fields = [field("scaling_attr", primary), ...(secondary === undefined ? [] : [field("secondary_scaling_attr", secondary)])];
  return { steps: [{ id: "basics", fields }], problems: [], next_step: null } as unknown as DraftOptions;
};

describe("conformScaling", () => {
  it("replaces a stale primary attribute with the first allowed one (spell wil -> holy wis)", () => {
    const draft: Json = { category: "spell", scaling_attr: "wil", effects: [{ type: "heal" }] };
    expect(conformScaling(draft, optionsWith(["wis"]))).toEqual({ category: "spell", scaling_attr: "wis", effects: [{ type: "heal" }] });
  });

  it("switching spell -> weapon: primary follows the weapon class, secondary is dropped", () => {
    const draft: Json = { category: "weapon", scaling_attr: "wil", secondary_scaling_attr: "int" };
    expect(conformScaling(draft, optionsWith(["str"]))).toEqual({ category: "weapon", scaling_attr: "str" });
  });

  it("drops a secondary attribute outside the range or equal to the primary", () => {
    const base: Json = { category: "spell", scaling_attr: "int" };
    expect(conformScaling({ ...base, secondary_scaling_attr: "wil" }, optionsWith(["int"], ["wis"]))).toEqual(base);
    expect(conformScaling({ ...base, secondary_scaling_attr: "int" }, optionsWith(["int"], ["wis"]))).toEqual(base);
  });

  it("returns the same object when everything is legal or no scaling is chosen", () => {
    const ok: Json = { category: "spell", scaling_attr: "int", secondary_scaling_attr: "wis" };
    expect(conformScaling(ok, optionsWith(["int"], ["wis"]))).toBe(ok);
    const none: Json = { category: "spell" };
    expect(conformScaling(none, optionsWith(["wis"]))).toBe(none);
  });
});
