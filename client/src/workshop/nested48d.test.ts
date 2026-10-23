// 3-48d：巢狀效果開放一層——在子效果列表（then／win／lose／effects／on_kill）加入、改值、移除，不影響外層。
import { describe, expect, it } from "vitest";
import type { Choice, FieldSpec } from "../api/types";
import { addEffect, listOf, removeItem, replaceItem, type Json } from "./draft";
import { shownChoices } from "./playerView";

const choice = (value: string, extra: Partial<Choice> = {}): Choice => ({
  value,
  name_zh: value,
  description_zh: "",
  dev_description_zh: "",
  later: false,
  params: [],
  info: {},
  ...extra,
});
const spec = (field: string, extra: Partial<FieldSpec> = {}): FieldSpec => ({
  field,
  name_zh: field,
  description_zh: "",
  dev_description_zh: "",
  later: false,
  show_when: {},
  type: "int",
  required: false,
  choices: [],
  fields: [],
  dice_sides: [],
  allow_weapon: false,
  locked: false,
  plain_value: false,
  auto_generated: false,
  card: false,
  object_choice: false,
  ...extra,
});

const then = spec("then", {
  type: "effects",
  min_count: 1,
  max_count: 2,
  choices: [choice("damage", { params: [spec("dice", { type: "dice", required: true, min: 1, max: 4, dice_sides: [4, 6] })] }), choice("heal")],
});

describe("nested effect lists", () => {
  const outer: Json = { effects: [{ type: "consume_status", status: "burning" }] };

  it("adds a sub-effect inside the outer effect without touching the outer one", () => {
    const item = (outer["effects"] as Json[])[0] as Json;
    const next = addEffect(item, then, then.choices[0] as Choice);
    expect(listOf(next, "then")).toHaveLength(1);
    expect(next["status"]).toBe("burning");
    expect((listOf(next, "then")[0] as Json)["type"]).toBe("damage");
  });

  it("stops at the maximum of two and removes by index", () => {
    let item: Json = { type: "consume_status" };
    item = addEffect(item, then, then.choices[0] as Choice);
    item = addEffect(item, then, then.choices[1] as Choice);
    expect(listOf(addEffect(item, then, then.choices[0] as Choice), "then")).toHaveLength(2);
    expect(listOf(removeItem(item, then, 0), "then").map((e) => e["type"])).toEqual(["heal"]);
  });

  it("replaces a sub-effect in place", () => {
    const item = addEffect({ type: "zone" }, then, then.choices[0] as Choice);
    const next = replaceItem(item, then, 0, { type: "damage", dice: "2d6" });
    expect((listOf(next, "then")[0] as Json)["dice"]).toBe("2d6");
  });

  it("lists every nested choice in player mode (nothing is marked later any more)", () => {
    expect(shownChoices(then.choices, false)).toHaveLength(2);
  });
});
