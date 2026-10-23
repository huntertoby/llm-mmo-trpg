// 工坊選項整修（Phase 3H-8）：第二屬性與專精擇一、組合規則帶出的對象。
import { describe, expect, it } from "vitest";
import type { Choice, FieldSpec } from "../api/types";
import { addEffect, selectChoice, type Json } from "./draft";

const spec = (field: string, choices: Choice[]): FieldSpec => ({
  field,
  name_zh: field,
  description_zh: "", dev_description_zh: "", later: false,
  type: "choice",
  required: false,
  choices,
  fields: [],
  dice_sides: [],
  allow_weapon: false,
  locked: false,
  plain_value: false,
  auto_generated: false,
  show_when: {},
  card: false,
  object_choice: false,
});
const choice = (value: string, info: Record<string, unknown> = {}): Choice => ({
  value,
  name_zh: value,
  description_zh: "", dev_description_zh: "", later: false,
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

  it("puts a must-be-first effect at the front and a must-be-last effect at the end (3-47)", () => {
    const dash = choice("dash", { composition: { position: "first" } });
    const gamble = choice("gamble", { composition: { position: "last" } });
    const damage = choice("damage");
    const all: FieldSpec = { ...effects, choices: [dash, gamble, damage] };
    let d: Json = addEffect({}, all, damage);
    d = addEffect(d, all, dash);
    d = addEffect(d, all, gamble);
    expect((d["effects"] as Json[]).map((e) => e["type"])).toEqual(["dash", "damage", "gamble"]);
    // 之後再加一般效果：夾在「第一個」與「最後一個」之間，不會排到賭注後面
    d = addEffect(d, all, damage);
    expect((d["effects"] as Json[]).map((e) => e["type"])).toEqual(["dash", "damage", "damage", "gamble"]);
  });

  it("adds a plain effect without a target when nothing forces one", () => {
    const next = addEffect({}, effects, choice("damage"));
    expect(next["effects"]).toEqual([{ type: "damage" }]);
  });
});
