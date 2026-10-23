// 鎖定欄位（Phase 3H-6，武器技的縮放屬性看手上武器）：值由規則決定，草稿會對齊成唯一的選項。
import { describe, expect, it } from "vitest";
import type { Choice, FieldSpec } from "../api/types";
import { autoSingles, type Json } from "./draft";

const only: Choice = { value: "str", name_zh: "看手上武器（力量）", description_zh: "", params: [], info: {} };
const scaling = (locked: boolean): FieldSpec => ({
  field: "scaling_attr",
  name_zh: "縮放屬性",
  description_zh: "",
  type: "choice",
  required: true,
  choices: [only],
  fields: [],
  dice_sides: [],
  allow_weapon: false,
  locked,
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
