// 技能工坊的動作段（複合技能，Phase 3F-3b）：點號路徑的欄位寫進草稿 followup。
import { describe, expect, it } from "vitest";
import type { Choice, FieldSpec } from "../api/types";
import { addEffect, clearChoice, getPath, selectChoice, type Json } from "./draft";
import { STEP_NAMES } from "./state";
import { previewOverlays, sceneLines } from "../battle/scenePreview";
import { smallView, unit } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import type { PreviewOut } from "../api/types";

const choice = (value: string, params: FieldSpec[] = []): Choice => ({ value, name_zh: value, description_zh: "", params, info: {} });
const skeleton: FieldSpec = {
  field: "followup.skeleton",
  name_zh: "接一個動作段",
  description_zh: "",
  type: "choice",
  required: false,
  choices: [choice("area"), choice("strike")],
  fields: [],
  dice_sides: [],
  allow_weapon: false,
};
const sizeParam: FieldSpec = {
  field: "size",
  name_zh: "大小",
  description_zh: "",
  type: "int",
  required: true,
  min: 2,
  max: 4,
  choices: [],
  fields: [],
  dice_sides: [],
  allow_weapon: false,
};
const shape: FieldSpec = { ...skeleton, field: "followup.shape", required: true, choices: [choice("cone", [sizeParam])] };
const effects: FieldSpec = {
  ...skeleton,
  field: "followup.effects",
  type: "effects",
  required: true,
  choices: [choice("damage")],
  min_count: 1,
  max_count: 3,
};

describe("the follow-up (second segment) fields", () => {
  it("writes the nested draft with dotted paths, the shape as an object", () => {
    let draft: Json = { skeleton: "displace" };
    draft = selectChoice(draft, skeleton, skeleton.choices[0] as Choice);
    draft = selectChoice(draft, shape, shape.choices[0] as Choice);
    draft = addEffect(draft, effects, effects.choices[0] as Choice);
    expect(draft["followup"]).toEqual({
      skeleton: "area",
      shape: { type: "cone", size: 2 },
      effects: [{ type: "damage" }],
    });
  });

  it("drops the shape and effects when the second segment's skeleton changes", () => {
    const draft: Json = {
      followup: { skeleton: "area", shape: { type: "cone", size: 2 }, effects: [{ type: "damage" }] },
    };
    const same = selectChoice(draft, skeleton, skeleton.choices[0] as Choice);
    expect(getPath(same, "followup.shape")).toEqual({ type: "cone", size: 2 });
    const changed = selectChoice(draft, skeleton, skeleton.choices[1] as Choice);
    expect(changed["followup"]).toEqual({ skeleton: "strike" });
  });

  it("'not using' the follow-up removes the whole second segment", () => {
    const draft: Json = {
      skeleton: "displace",
      followup: { skeleton: "area", shape: { type: "cone", size: 2 }, effects: [{ type: "damage" }] },
    };
    expect(clearChoice(draft, skeleton)).toEqual({ skeleton: "displace" });
  });

  it("has a step name for the follow-up step", () => {
    expect(STEP_NAMES.followup).toBe("第二段"); // 3F-4b：六種第二段，不只「動作段」
  });
});

describe("previewing a composite skill", () => {
  const view = smallView({ units: [unit("unit_0001", "ally", 0, 0)] });
  const base = { followup_tiles: [[3, 1], [4, 1]], landing: [2, 1] } as unknown as PreviewOut;

  it("marks the second segment's area and says what happens", () => {
    const overlays = previewOverlays(base, view);
    expect(overlays.filter((o) => o.kind === "followup_area").map((o) => o.pos)).toEqual([
      { x: 3, y: 1 },
      { x: 4, y: 1 },
    ]);
    const lines = sceneLines(base, unitNames(view), view);
    expect(lines.some((l) => l.includes("第二段") && l.includes("(2, 1)") && l.includes("2 格"))).toBe(true);
  });
});

describe("the kind of second part (Phase 3F-4b)", () => {
  const when: FieldSpec = { ...skeleton, field: "followup.when", choices: [choice("after_move"), choice("delayed")] };

  it("picking another kind starts the second part over", () => {
    const draft: Json = { followup: { when: "after_move", skeleton: "area", shape: { type: "cone", size: 2 } } };
    expect(selectChoice(draft, when, when.choices[0] as Choice)["followup"]).toEqual(draft["followup"]);
    expect(selectChoice(draft, when, when.choices[1] as Choice)["followup"]).toEqual({ when: "delayed" });
  });

  it("clearing the kind removes the second part; clearing the skeleton keeps the kind", () => {
    const draft: Json = {
      skeleton: "aura",
      followup: { when: "delayed", release: "next_turn", skeleton: "area", shape: { type: "cross", range: 0 } },
    };
    expect(clearChoice(draft, when)).toEqual({ skeleton: "aura" });
    expect(clearChoice(draft, skeleton)["followup"]).toEqual({ when: "delayed", release: "next_turn" });
  });
});
