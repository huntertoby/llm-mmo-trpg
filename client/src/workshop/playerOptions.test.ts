// 工坊選項整修（Phase 3H-8）：第二屬性與專精擇一、組合規則帶出的對象。
import { describe, expect, it } from "vitest";
import { type Choice, type FieldSpec, type DraftOptions } from "../api/types";
import { addEffect, selectChoice, type Json, conformScaling, getPath, replaceItem, setPath, conformAffects } from "./draft";
import { descOf, fieldShown, hiddenCount, shownChoices, groupChoices } from "./playerView";
import { displayFactor, formatDisplay } from "../ui/workshop/FieldEditor";

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

// --- 原 player48c.test.ts ---
describe("原 player48c.test.ts", () => {
// 3-48c：玩家模式／開發者模式的說明、之後開放的選項、條件顯示、法術技的縮放與武器需求對齊、數值欄位連續修改。

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
});

// --- 原 display48f.test.ts ---
describe("原 display48f.test.ts", () => {
// 3-48f：千分比欄位的玩家顯示（倍率 ×2、百分比 25%），內部仍存千分比。

const base = (display: FieldSpec["display"]): FieldSpec =>
  ({ field: "x", name_zh: "x", type: "int", display, min: 100, max: 10000 }) as FieldSpec;

describe("displayFactor / formatDisplay", () => {
  it("multiplier shows ×N", () => {
    expect(displayFactor(base("multiplier"))).toBe(1000);
    expect(formatDisplay(base("multiplier"), 2000)).toBe("×2");
    expect(formatDisplay(base("multiplier"), 1500)).toBe("×1.5");
  });
  it("percent shows N%", () => {
    expect(displayFactor(base("percent"))).toBe(10);
    expect(formatDisplay(base("percent"), 250)).toBe("25%");
  });
  it("plain fields are unchanged", () => {
    expect(displayFactor(base(null))).toBe(1);
    expect(formatDisplay(base(null), 7)).toBe("7");
  });
});
});

// --- 原 stackGroups52.test.ts ---
describe("原 stackGroups52.test.ts", () => {
// 3-52：層數選單依「累積在你身上」「疊在敵人身上」分組（後端 `info.group_zh`），對象由後端的 effect_fixes 自動改。

const choice = (value: string, group?: string): Choice =>
  ({ value, name_zh: value, description_zh: "", params: [], info: group === undefined ? {} : { group_zh: group } }) as unknown as Choice;

describe("groupChoices", () => {
  it("依 info.group_zh 分組，組的順序照第一次出現", () => {
    const groups = groupChoices([
      choice("combo_point", "累積在你身上"),
      choice("ki", "累積在你身上"),
      choice("hoarfrost", "疊在敵人身上"),
    ]);
    expect(groups.map(([label, items]) => [label, items.map((c) => c.value)])).toEqual([
      ["累積在你身上", ["combo_point", "ki"]],
      ["疊在敵人身上", ["hoarfrost"]],
    ]);
  });

  it("沒有分組名的欄位全部放同一組（不顯示組名）", () => {
    const groups = groupChoices([choice("a"), choice("b")]);
    expect(groups).toHaveLength(1);
    expect(groups[0]?.[0]).toBeNull();
  });
});

describe("層數的對象自動修正", () => {
  it("後端的 effect_fixes 把疊在敵人身上的層數改成敵方", () => {
    const draft = { effects: [{ type: "add_stack", stack: "hoarfrost", amount: 1, affects: "self" }] } as unknown as Json;
    const options = {
      steps: [],
      problems: [],
      next_step: null,
      effect_fixes: [{ index: 0, value: "enemies", reason_zh: "「寒霜」疊在敵人身上，對象自動決定" }],
    };
    const next = conformAffects(draft, options as never) as { effects: { affects: string }[] };
    expect(next.effects[0]?.affects).toBe("enemies");
  });
});
});
