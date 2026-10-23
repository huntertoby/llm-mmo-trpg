// 工坊選項整修（Phase 3H-8）：第二屬性與專精擇一、組合規則帶出的對象。
import { describe, expect, it } from "vitest";
import type { Choice, FieldSpec } from "../api/types";
import { addEffect, selectChoice, type Json } from "./draft";

const spec = (field: string, choices: Choice[]): FieldSpec => ({
  field,
  name_zh: field,
  description_zh: "",
  type: "choice",
  required: false,
  choices,
  fields: [],
  dice_sides: [],
  allow_weapon: false,
  locked: false,
  card: false,
  object_choice: false,
});
const choice = (value: string, info: Record<string, unknown> = {}): Choice => ({
  value,
  name_zh: value,
  description_zh: "",
  params: [],
  info,
});

describe("second attribute and mastery", () => {
  it("picking a second attribute drops the mastery", () => {
    const wis = choice("wis");
    const next = selectChoice({ mastery: "range", rarity: "epic" }, spec("secondary_scaling_attr", [wis]), wis);
    expect(next).toEqual({ rarity: "epic", secondary_scaling_attr: "wis" });
  });

  it("picking a mastery keeps the rest of the draft", () => {
    const range = choice("range");
    const next = selectChoice({ rarity: "epic" }, spec("mastery", [range]), range);
    expect(next).toEqual({ rarity: "epic", mastery: "range" });
  });
});

describe("composition rules", () => {
  const effects: FieldSpec = { ...spec("effects", []), type: "effects", max_count: 4 };

  it("adds the forced target when another effect makes the rest self-only", () => {
    const damage = choice("damage", { forced_affects: "self" });
    const draft: Json = { effects: [{ type: "charge_through" }] };
    const next = addEffect(draft, effects, damage);
    expect(next["effects"]).toEqual([{ type: "charge_through" }, { type: "damage", affects: "self" }]);
  });

  it("adds a plain effect without a target when nothing forces one", () => {
    const next = addEffect({}, effects, choice("damage"));
    expect(next["effects"]).toEqual([{ type: "damage" }]);
  });
});
