// 3-48h：違規的對象事前停用的前端部分——對象自動修正（conformAffects）、變奏代號自動產生、
// 玩家模式隱藏自動產生的欄位。選項本身（unavailable_zh）由後端推導，這裡不重寫規則。
import { describe, expect, it } from "vitest";
import type { DraftOptions, FieldSpec } from "../api/types";
import { addModifier, conformAffects, withAutoValues, type Json } from "./draft";
import { fieldShown } from "./playerView";

const optionsWith = (fixes: { index: number; value: string | null; reason_zh: string }[]): DraftOptions =>
  ({ steps: [], problems: [], next_step: null, effect_fixes: fixes }) as unknown as DraftOptions;

describe("conformAffects", () => {
  const draft: Json = { effects: [{ type: "apply_status", status: "rallied" }, { type: "heal", affects: "allies" }] };

  it("applies the suggested legal target to the effect that has it", () => {
    const next = conformAffects(draft, optionsWith([{ index: 0, value: "self", reason_zh: "自身形狀不能對敵方出手" }]));
    expect(next["effects"]).toEqual([{ type: "apply_status", status: "rallied", affects: "self" }, { type: "heal", affects: "allies" }]);
  });

  it("leaves the draft alone when there is no fix, no legal value, or it already matches", () => {
    expect(conformAffects(draft, optionsWith([]))).toBe(draft);
    expect(conformAffects(draft, optionsWith([{ index: 0, value: null, reason_zh: "沒有合法的對象" }]))).toBe(draft);
    expect(conformAffects(draft, optionsWith([{ index: 1, value: "allies", reason_zh: "" }]))).toBe(draft);
  });

  it("ignores fixes for effects that do not exist", () => {
    expect(conformAffects(draft, optionsWith([{ index: 9, value: "self", reason_zh: "" }]))).toBe(draft);
  });
});

const codeField = (over: Partial<FieldSpec> = {}): FieldSpec =>
  ({
    field: "id",
    name_zh: "型態代碼",
    description_zh: "",
    dev_description_zh: "",
    later: false,
    type: "text",
    required: true,
    choices: [],
    fields: [],
    dice_sides: [],
    allow_weapon: false,
    locked: false,
    plain_value: false,
    show_when: {},
    auto_generated: true,
    card: false,
    object_choice: false,
    ...over,
  }) as FieldSpec;

describe("auto-generated fields (variant code names)", () => {
  it("generates unique codes for new list items", () => {
    expect(withAutoValues({}, [codeField()], [])).toEqual({ id: "form_1" });
    expect(withAutoValues({}, [codeField()], [{ id: "form_1" }, { id: "form_3" }])).toEqual({ id: "form_2" });
  });

  it("keeps a code the player or the data already has", () => {
    expect(withAutoValues({ id: "tide_pierce" }, [codeField()], [])).toEqual({ id: "tide_pierce" });
  });

  it("adding a variant fills the code", () => {
    const list: FieldSpec = codeField({ field: "variants", type: "variants", required: false, auto_generated: false, fields: [codeField()], max_count: 2 });
    const first = addModifier({}, list);
    expect(first["variants"]).toEqual([{ id: "form_1" }]);
    expect(addModifier(first, list)["variants"]).toEqual([{ id: "form_1" }, { id: "form_2" }]);
  });

  it("hides the field in player mode and shows it with ?dev=1", () => {
    expect(fieldShown(codeField(), {}, "", false)).toBe(false);
    expect(fieldShown(codeField(), {}, "", true)).toBe(true);
  });
});
