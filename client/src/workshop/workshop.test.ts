// 技能工坊（Phase 3F-2）：編輯流程的狀態、選項→草稿、回上一步、檢查結果的顯示、暫存、試玩請求。
// fixtures 是 3F-1 後端的真實回應（衝鋒＋傷害＋擊退；重新產生見 docs/phases/Phase3F-2報告.md）。
import { parse } from "yaml";
import { describe, expect, it } from "vitest";
import type {
  Choice,
  DraftOptions,
  FieldSpec,
  StepOptions,
  WorkshopArena,
  WorkshopCheck,
  WorkshopExport,
} from "../api/types";
import arenaFx from "./fixtures/arena.json";
import checkCommonFx from "./fixtures/check_charge_common.json";
import checkFx from "./fixtures/check_charge.json";
import checkPartialFx from "./fixtures/check_partial.json";
import chargeFx from "./fixtures/charge_full.json";
import exportFx from "./fixtures/export_charge.json";
import optionsEffectsFx from "./fixtures/options_charge_effects.json";
import optionsEmptyFx from "./fixtures/options_empty.json";
import optionsFullFx from "./fixtures/options_charge_full.json";
import {
  addEffect,
  autoSingles,
  changeSkeleton,
  getPath,
  moveItem,
  removeItem,
  selectChoice,
  setPath,
  type Json,
} from "./draft";
import {
  availableSteps,
  budgetView,
  canBack,
  canNext,
  checkHeadline,
  currentStep,
  editorReducer,
  initialState,
  loadSaved,
  missingStepNames,
  parseSaved,
  save,
  STORAGE_KEY,
  type EditorAction,
  type EditorState,
  type KeyValueStore,
} from "./state";
import { buildTryoutRequest, isTrainingMap, manaNote, manaWarning, tryoutSkill } from "./tryout";
import { draftToYaml, parseDraftText, sameDraft } from "./yamlEdit";
import type { BattleResponse } from "../api/types";

const optionsEmpty = optionsEmptyFx as unknown as DraftOptions;
const optionsEffects = optionsEffectsFx as unknown as DraftOptions;
const optionsFull = optionsFullFx as unknown as DraftOptions;
const check = checkFx as unknown as WorkshopCheck;
const checkCommon = checkCommonFx as unknown as WorkshopCheck;
const checkPartial = checkPartialFx as unknown as WorkshopCheck;
const arena = arenaFx as unknown as WorkshopArena;
const exported = exportFx as unknown as WorkshopExport;
const charge = chargeFx as Json;

function step(options: DraftOptions, id: StepOptions["id"]): StepOptions {
  const s = options.steps.find((x) => x.id === id);
  if (s === undefined) throw new Error(`沒有步驟 ${id}`);
  return s;
}

function field(s: StepOptions, name: string): FieldSpec {
  const f = s.fields.find((x) => x.field === name);
  if (f === undefined) throw new Error(`沒有欄位 ${name}`);
  return f;
}

function choice(f: FieldSpec, value: string | number | boolean): Choice {
  const c = f.choices.find((x) => x.value === value);
  if (c === undefined) throw new Error(`沒有選項 ${String(value)}`);
  return c;
}

function run(state: EditorState, ...actions: EditorAction[]): EditorState {
  return actions.reduce(editorReducer, state);
}

describe("building a skill step by step from the real options", () => {
  it("walks 衝鋒＋傷害＋擊退 from an empty draft using only the offered choices", () => {
    // 1. 骨架
    const skeleton = field(step(optionsEmpty, "skeleton"), "skeleton");
    let d: Json = selectChoice({}, skeleton, choice(skeleton, "displace"));
    expect(d).toEqual({ skeleton: "displace" });
    // 2. 基本設定：主動技（AP 起始補最小值 1，再調成 2）、武器技要再選近戰
    const basics = step(optionsEffects, "basics");
    d = setPath(d, "name_zh", "衝鋒擊退");
    d = selectChoice(d, field(basics, "kind"), choice(field(basics, "kind"), "active"));
    expect(d["ap_cost"]).toBe(1);
    d = setPath(d, "ap_cost", 2);
    const category = field(basics, "category");
    d = selectChoice(d, category, choice(category, "weapon"));
    const weaponReq = choice(category, "weapon").params[0] as FieldSpec;
    d = selectChoice(d, weaponReq, choice(weaponReq, "melee"));
    const scaling = field(basics, "scaling_attr");
    d = selectChoice(d, scaling, choice(scaling, "str"));
    d = setPath(d, "tier", 2);
    // 3. 形狀：選了單體就補上射程起始值
    const shape = field(step(optionsEffects, "shape"), "shape");
    d = selectChoice(d, shape, choice(shape, "single"));
    expect(d["shape"]).toEqual({ type: "single", range: 1 });
    d = setPath(d, "shape.range", 4);
    // 4. 效果：衝鋒、傷害、擊退（必填的推幾格從範圍最小值開始，選填的不替使用者決定）
    const effects = field(step(optionsEffects, "effects"), "effects");
    for (const type of ["dash", "damage", "push"]) d = addEffect(d, effects, choice(effects, type));
    expect(getPath(d, "effects")).toEqual([
      { type: "dash" },
      { type: "damage" },
      { type: "push", distance: 1 },
    ]);
    d = setPath(d, "effects", [{ type: "dash" }, { type: "damage", multiplier_permille: 1000 }, { type: "push", distance: 2 }]);
    // 5. 代價與稀有度
    d = setPath(d, "cost.cooldown", 2);
    const rarity = field(step(optionsFull, "rarity"), "rarity");
    d = selectChoice(d, rarity, choice(rarity, "rare"));
    expect(sameDraft(d, charge)).toBe(true);
  });

  it("only offers rarities and effects that the options contain", () => {
    const effects = field(step(optionsEffects, "effects"), "effects");
    const values = effects.choices.map((c) => c.value);
    expect(values).toEqual(expect.arrayContaining(["dash", "damage", "push"]));
    expect(effects.max_count).toBe(4);
    const push = choice(effects, "push").params.find((p) => p.field === "distance");
    expect([push?.min, push?.max]).toEqual([1, 2]);
  });
});

describe("choosing options writes the draft", () => {
  const basics = step(optionsEffects, "basics");

  it("switching category drops a weapon requirement that no longer fits", () => {
    const category = field(basics, "category");
    let d: Json = { category: "weapon", weapon_req: "melee" };
    d = selectChoice(d, category, choice(category, "spell"));
    expect(d["category"]).toBe("spell");
    expect(d["weapon_req"]).toBeUndefined();
  });

  it("switching the shape replaces the whole shape object and its parameters", () => {
    const shape = field(step(optionsEffects, "shape"), "shape");
    let d: Json = { shape: { type: "single", range: 4 } };
    d = selectChoice(d, shape, choice(shape, "cone"));
    expect(d["shape"]).toEqual({ type: "cone", size: 2 });
  });

  it("removes and reorders effects, and enforces the effect limit", () => {
    const effects = field(step(optionsEffects, "effects"), "effects");
    let d: Json = {};
    for (const type of ["dash", "damage", "push", "knock_prone"]) d = addEffect(d, effects, choice(effects, type));
    expect(addEffect(d, effects, choice(effects, "pull"))).toBe(d);
    d = moveItem(d, effects, 0, 1);
    expect((getPath(d, "effects") as Json[]).map((e) => e["type"])).toEqual(["damage", "dash", "push", "knock_prone"]);
    d = removeItem(d, effects, 1);
    expect((getPath(d, "effects") as Json[]).map((e) => e["type"])).toEqual(["damage", "push", "knock_prone"]);
    for (let i = 0; i < 3; i++) d = removeItem(d, effects, 0);
    expect(d["effects"]).toBeUndefined();
  });

  it("clearing a dotted field removes the empty parent object", () => {
    const d = setPath({ cost: { cooldown: 2 }, tier: 1 }, "cost.cooldown", undefined);
    expect(d).toEqual({ tier: 1 });
  });

  it("changing the skeleton keeps only the name", () => {
    expect(changeSkeleton(charge, "strike")).toEqual({ skeleton: "strike", name_zh: "衝鋒擊退" });
  });

  it("selects the only offered choice by itself (and nothing else)", () => {
    const only: FieldSpec = { ...field(basics, "kind"), choices: [choice(field(basics, "kind"), "active")] };
    const filled = autoSingles({}, [only]);
    expect(filled).toEqual({ kind: "active", ap_cost: 1 });
    expect(autoSingles(filled, [only])).toBe(filled);
    expect(autoSingles({}, [field(basics, "category")])).toEqual({});
  });
});

describe("editor state: steps, going back, check results", () => {
  const start = initialState({ skeleton: "displace" });

  it("opens on the first unfinished step once the options arrive", () => {
    const s = run(start, { type: "options", options: optionsEffects });
    expect(currentStep(s)).toBe("effects");
    expect(availableSteps(s.options)).toEqual(["skeleton", "basics", "shape", "effects"]);
    expect(canNext(s)).toBe(false);
    expect(canBack(s)).toBe(true);
  });

  it("goes back to earlier steps and forward again", () => {
    let s = run(start, { type: "options", options: optionsEffects });
    s = run(s, { type: "back" });
    expect(currentStep(s)).toBe("shape");
    s = run(s, { type: "back" }, { type: "back" });
    expect(currentStep(s)).toBe("skeleton");
    expect(canBack(s)).toBe(false);
    expect(run(s, { type: "back" })).toEqual(s);
    s = run(s, { type: "next" });
    expect(currentStep(s)).toBe("basics");
    s = run(s, { type: "goto", step: "effects" });
    expect(currentStep(s)).toBe("effects");
  });

  it("keeps the step you are on while editing, and falls back when it disappears", () => {
    let s = run(start, { type: "options", options: optionsEffects }, { type: "goto", step: "basics" });
    s = run(s, { type: "edit", draft: { skeleton: "displace", tier: 3 } });
    expect(currentStep(s)).toBe("basics");
    s = run(s, { type: "options", options: optionsEmpty });
    expect(currentStep(s)).toBe("skeleton");
  });

  it("a finished skill is viewed from its last step and can move through all of them", () => {
    let s = run(initialState(charge), { type: "options", options: optionsFull });
    expect(currentStep(s)).toBe("rarity");
    expect(canNext(s)).toBe(false);
    s = run(s, { type: "goto", step: "skeleton" });
    for (let i = 0; i < 6; i++) s = run(s, { type: "next" });
    expect(currentStep(s)).toBe("rarity");
  });

  it("replacing the draft (random, reset, YAML) forgets the old options and check", () => {
    const s = run(start, { type: "options", options: optionsEffects }, { type: "check", check: checkPartial });
    const r = run(s, { type: "replace", draft: {} });
    expect(r).toEqual(initialState({}));
  });

  it("shows the check result in plain Chinese", () => {
    expect(checkHeadline(null).tone).toBe("pending");
    expect(checkHeadline(checkPartial).tone).toBe("partial");
    expect(checkHeadline(check)).toEqual({ tone: "ok", text: "合法：可以匯出，也可以裝上試玩" });
    const bad = checkHeadline(checkCommon);
    expect(bad.tone).toBe("bad");
    expect(bad.text).toContain("3 項問題");
    expect(checkCommon.problems[0]?.message_zh).toContain("稀有度 common");
  });

  it("lists unfinished steps without nagging about the optional ones", () => {
    expect(missingStepNames(checkPartial)).toEqual(["效果", "稀有度"]);
    expect(missingStepNames({ ...checkPartial, missing_steps: ["condition", "cost"] })).toEqual(["條件"]);
  });
});

describe("budget display", () => {
  it("shows 70.7% as an acceptable skill with the bar and marks in the right places", () => {
    const b = check.budget;
    if (b === null) throw new Error("沒有預算");
    const v = budgetView(b);
    expect(v.tone).toBe("ok");
    expect(v.percentText).toBe("70.7%");
    expect(v.verdict).toBe("合格");
    expect(v.fill).toBeCloseTo(0.7071 / 1.5, 4);
    expect([v.minMark, v.maxMark]).toEqual([0.7 / 1.5, 1 / 1.5]);
    expect([v.total, v.usable]).toEqual([14, 19.8]);
  });

  it("marks weak and over-budget skills with a hint on what to change", () => {
    const b = check.budget;
    if (b === null) throw new Error("沒有預算");
    const weak = budgetView({ ...b, ratio: 0.5, ratio_text: "50.0%", verdict: "weak", verdict_zh: "過弱" });
    expect(weak.tone).toBe("weak");
    expect(weak.hint).toContain("太弱");
    const over = budgetView({ ...b, ratio: 1.3, ratio_text: "130.0%", verdict: "over", verdict_zh: "過強" });
    expect(over.tone).toBe("over");
    expect(over.hint).toContain("太強");
    expect(over.fill).toBeCloseTo(1.3 / 1.5, 4);
    expect(budgetView({ ...b, ratio: 3 }).fill).toBe(1);
  });

  it("explains the rarity rule in the check result", () => {
    expect(checkCommon.minimum_rarity).toBe("rare");
    expect(checkCommon.rarity_reasons.length).toBeGreaterThan(0);
  });
});

describe("browser storage", () => {
  function fakeStore(): KeyValueStore & { data: Map<string, string> } {
    const data = new Map<string, string>();
    return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
  }

  it("keeps the draft, the step and the tryout choices across a reload", () => {
    const store = fakeStore();
    expect(save(store, { draft: charge, step: "effects", tryout: { build: "build_push", map: "training_range" } })).toBe(true);
    expect(store.data.has(STORAGE_KEY)).toBe(true);
    expect(loadSaved(store)).toEqual({ draft: charge, step: "effects", tryout: { build: "build_push", map: "training_range" } });
  });

  it("survives missing, broken or unwritable storage", () => {
    expect(loadSaved(null)).toBeNull();
    expect(parseSaved("not json")).toBeNull();
    expect(parseSaved('{"draft": 3}')).toBeNull();
    expect(parseSaved('{"draft": {}, "step": "bogus", "tryout": {"build": 5}}')).toEqual({ draft: {}, step: null, tryout: {} });
    const broken: KeyValueStore = {
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => {
        throw new Error("full");
      },
    };
    expect(loadSaved(broken)).toBeNull();
    expect(save(broken, { draft: {}, step: null, tryout: {} })).toBe(false);
    expect(save(null, { draft: {}, step: null, tryout: {} })).toBe(false);
  });
});

describe("try it out", () => {
  const choiceOf = (over: Partial<Parameters<typeof buildTryoutRequest>[0]> = {}) => ({
    mapId: "training_range",
    seed: 7,
    buildId: "build_push",
    replaceId: "skill_gale_kick",
    opponents: "fighting",
    ...over,
  });

  it("sends the checked skill, the slot to replace, the opponents and the round limit", () => {
    const req = buildTryoutRequest(choiceOf(), check, arena);
    expect(req).not.toBeNull();
    expect(req?.map_id).toBe("training_range");
    expect(req?.replace_skills).toEqual(["skill_gale_kick"]);
    expect(req?.opponents).toBe("fighting");
    expect(req?.max_rounds).toBe(30);
    const skill = req?.custom_skills?.[0];
    expect(skill?.["id"]).toBe("skill_ws_e9737f7780");
    expect(getPath(skill, "provenance.origin")).toBe("workshop");
  });

  it("adds to an empty slot when nothing is replaced, and only sends opponents on the training range", () => {
    const req = buildTryoutRequest(choiceOf({ replaceId: "", mapId: "open_plain" }), check, arena);
    expect(req?.replace_skills).toEqual([]);
    expect(req?.opponents).toBeUndefined();
    expect(isTrainingMap(arena, "training_range")).toBe(true);
    expect(isTrainingMap(arena, "open_plain")).toBe(false);
    expect(arena.default_map).toBe("training_range");
  });

  it("refuses to try out a skill that is illegal or unfinished", () => {
    expect(buildTryoutRequest(choiceOf(), checkCommon, arena)).toBeNull();
    expect(buildTryoutRequest(choiceOf(), checkPartial, arena)).toBeNull();
    expect(tryoutSkill(checkCommon)).toBeNull();
  });

  it("warns when the hero's mana limit is below the skill's mana cost", () => {
    const withMana = { ...check, skill: { ...(check.skill as Json), cost: { mana: 8, cooldown: 2 } } } as WorkshopCheck;
    const response = (maxMana: number) =>
      ({ hero_id: "u1", view: { units: [{ id: "u1", max_mana: maxMana }] } }) as unknown as BattleResponse;
    expect(manaWarning(withMana, response(3))).toContain("法力上限只有 3");
    expect(manaWarning(withMana, response(3))).toContain("需要 8 點");
    expect(manaWarning(withMana, response(8))).toBeNull();
    expect(manaWarning(check, response(0))).toBeNull();
    expect(manaNote(withMana)).toContain("8 點法力");
    expect(manaNote(check)).toBeNull();
  });
});

describe("advanced YAML editing", () => {
  it("turns the draft into YAML and back", () => {
    const text = draftToYaml(charge);
    expect(text).toContain("skeleton: displace");
    const back = parseDraftText(text);
    expect(back.ok && sameDraft(back.draft, charge)).toBe(true);
    expect(draftToYaml({})).toBe("");
    expect(parseDraftText("  ")).toEqual({ ok: true, draft: {} });
  });

  it("reads the exported file back as the checked skill", () => {
    const parsed = parseDraftText(exported.yaml);
    if (!parsed.ok) throw new Error(parsed.error);
    expect(parsed.draft).toEqual(parse(exported.yaml));
    expect(getPath(parsed.draft, "provenance.origin")).toBe("workshop");
    expect(getPath(parsed.draft, "effects")).toEqual(getPath(check.skill, "effects"));
  });

  it("explains bad YAML in Chinese instead of applying it", () => {
    const broken = parseDraftText("skeleton: [displace\ntier: 2");
    expect(broken.ok).toBe(false);
    if (!broken.ok) expect(broken.error).toMatch(/^YAML 格式有誤：/);
    const list = parseDraftText("- a\n- b");
    expect(list.ok).toBe(false);
    if (!list.ok) expect(list.error).toContain("欄位: 值");
  });

  it("lets nested effects through untouched so the check can judge them", () => {
    const nested = parseDraftText("effects:\n  - type: gamble\n    chance_permille: 500\n    win:\n      - type: damage\n        multiplier_permille: 2000\n");
    expect(nested.ok && getPath(nested.draft, "effects.0.win")).toBeUndefined();
    expect(nested.ok && (getPath(nested.draft, "effects") as Json[])[0]?.["win"]).toEqual([{ type: "damage", multiplier_permille: 2000 }]);
  });
});
