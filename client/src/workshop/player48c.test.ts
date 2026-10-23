// 3-48c：玩家模式／開發者模式的說明、之後開放的選項、條件顯示、法術技的縮放與武器需求對齊、數值欄位連續修改。
import { describe, expect, it } from "vitest";
import type { Choice, DraftOptions, FieldSpec } from "../api/types";
import { conformScaling, getPath, replaceItem, setPath, type Json } from "./draft";
import { descOf, fieldShown, hiddenCount, shownChoices } from "./playerView";

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
  card: false,
  object_choice: false,
  ...extra,
});
const optionsWith = (fields: FieldSpec[]): DraftOptions =>
  ({ steps: [{ id: "basics", fields }], problems: [], next_step: null }) as unknown as DraftOptions;

describe("player and developer descriptions", () => {
  const item = { description_zh: "玩家版", dev_description_zh: "dev text with refund_ap" };
  it("shows the player text normally and the original under ?dev=1", () => {
    expect(descOf(item, false)).toBe("玩家版");
    expect(descOf(item, true)).toBe("dev text with refund_ap");
  });
  it("falls back to the player text when there is no original", () => {
    expect(descOf({ description_zh: "只有玩家版" }, true)).toBe("只有玩家版");
    expect(descOf({ description_zh: "x", dev_description_zh: "" }, true)).toBe("x");
  });
});

describe("later (nested effects not open yet)", () => {
  const choices = [choice("damage"), choice("zone", { later: true }), choice("gamble", { later: true })];
  it("hides them for players and lists them in dev mode", () => {
    expect(shownChoices(choices, false).map((c) => c.value)).toEqual(["damage"]);
    expect(shownChoices(choices, true)).toHaveLength(3);
    expect(hiddenCount(choices, false)).toBe(2);
    expect(hiddenCount(choices, true)).toBe(0);
  });
  it("hides a later field for players only", () => {
    const onKill = spec("on_kill", { later: true, type: "effects" });
    expect(fieldShown(onKill, {}, "", false)).toBe(false);
    expect(fieldShown(onKill, {}, "", true)).toBe(true);
  });
});

describe("show_when (conditional fields)", () => {
  const speed = spec("speed", { show_when: { anchor: "moving" } });
  it("shows the field only when the sibling has the value", () => {
    expect(fieldShown(speed, { anchor: "tile" }, "", false)).toBe(false);
    expect(fieldShown(speed, {}, "", false)).toBe(false);
    expect(fieldShown(speed, { anchor: "moving" }, "", false)).toBe(true);
  });
  it("compares numbers as text and respects the base path", () => {
    const power = spec("power_permille", { show_when: { count: "2" } });
    expect(fieldShown(power, { shape: { count: 2 } }, "shape", false)).toBe(true);
    expect(fieldShown(power, { shape: { count: 1 } }, "shape", false)).toBe(false);
  });
});

describe("conformScaling for spells and weapon requirements", () => {
  const scaling = (values: string[]) => spec("scaling_attr", { type: "choice", choices: values.map((v) => choice(v)) });
  it("clears a stale strength on a spell that has no effects yet (no default)", () => {
    const draft: Json = { category: "spell", scaling_attr: "str" };
    expect(conformScaling(draft, optionsWith([scaling(["int", "wis", "wil"])]))).toEqual({ category: "spell" });
  });
  it("still replaces it with the first allowed value once effects exist", () => {
    const draft: Json = { category: "spell", scaling_attr: "str", effects: [{ type: "heal" }] };
    expect(conformScaling(draft, optionsWith([scaling(["wis"])]))["scaling_attr"]).toBe("wis");
  });
  it("clears a weapon requirement that the category no longer allows", () => {
    const req = spec("weapon_req", { type: "choice", choices: [choice("focus"), choice("any")] });
    const draft: Json = { category: "spell", weapon_req: "melee" };
    expect(conformScaling(draft, optionsWith([req]))).toEqual({ category: "spell" });
    const ok: Json = { category: "spell", weapon_req: "focus" };
    expect(conformScaling(ok, optionsWith([req]))).toBe(ok);
  });
});

describe("numeric field edits (rune duration 4 -> 1 and 1 -> 4)", () => {
  const effects = spec("effects", { type: "effects" });
  // 欄位編輯器的流程：效果項目內改欄位（setPath）→ replaceItem 寫回草稿
  const edit = (draft: Json, value: number): Json => {
    const item = (draft["effects"] as Json[])[0] as Json;
    return replaceItem(draft, effects, 0, setPath(item, "duration", value));
  };
  const durationOf = (draft: Json): unknown => ((draft["effects"] as Json[])[0] as Json)["duration"];
  it("the draft always holds the last value typed, in both orders", () => {
    const start: Json = { effects: [{ type: "inscribe", element: "fire", duration: 4 }] };
    expect(durationOf(edit(edit(start, 1), 4))).toBe(4);
    expect(durationOf(edit(edit(edit(start, 1), 4), 1))).toBe(1);
    expect(durationOf(start)).toBe(4); // 原草稿不被改動
    const fresh: Json = { effects: [{ type: "inscribe", element: "fire", duration: 1 }] };
    expect(durationOf(edit(fresh, 4))).toBe(4);
    expect(getPath(edit(fresh, 4), "effects")).toHaveLength(1);
  });
});
