// Phase 3-25b：戰場變奏的顯示規則（型態列表、發亮條件、預覽型態切換）。
import { describe, expect, it } from "vitest";
import type { Action, DraftOptions, PreviewOut, SkillCard, SkillVariantCard, UnitView, VariantState } from "../api/types";
import { defaultStep, STEP_NAMES } from "../workshop/state";
import { previewLines } from "./previewText";
import { skillButtons } from "./targeting";
import { activeVariantCard, conditionNote, previewVariantLine, readyVariants, skillVariantView, variantBadge } from "./variants";
import { unitNames } from "./units";

const icon = (tag: string) => ({ tag }) as unknown as SkillCard["icon"];

function variant(id: string, name: string, kind: string, dependent: boolean): SkillVariantCard {
  return {
    id,
    name_zh: name,
    condition: `條件 ${id}`,
    condition_kind: kind,
    target_dependent: dependent,
    change: `替換 ${id}`,
    icon: icon(id),
  };
}

const WATER = variant("tide_pierce", "水中貫穿", "caster_surface", false);
const HIGH = variant("high_tide", "居高投矛", "caster_high_ground", true);

function card(variants: SkillVariantCard[]): SkillCard {
  return {
    id: "skill_tidal_spear",
    name_zh: "潮汐之矛",
    ap_cost: 2,
    cost: ["AP 2"],
    source_cost: null,
    effect_ids: ["damage"],
    icon: icon("base"),
    variants,
  } as unknown as SkillCard;
}

const state = (active: string | null, available: string[]): VariantState => ({
  skill_id: "skill_tidal_spear",
  active,
  available,
});

describe("戰場變奏：技能列的狀態", () => {
  it("沒有變奏的技能沒有狀態（不發亮）", () => {
    expect(skillVariantView(card([]), state(null, []))).toBeUndefined();
    expect(skillVariantView(card([WATER]), undefined)).toBeUndefined();
    expect(skillVariantView(undefined, state("tide_pierce", []))).toBeUndefined();
  });

  it("條件成立（施放者站在水上）：生效、發亮、圖示換成該型態", () => {
    const view = skillVariantView(card([WATER, HIGH]), state("tide_pierce", ["tide_pierce"]));
    expect(view).toEqual({ activeId: "tide_pierce", reachableIds: ["tide_pierce"], glow: true });
    expect(activeVariantCard(card([WATER, HIGH]), view)?.icon).toEqual(icon("tide_pierce"));
    expect(variantBadge(card([WATER, HIGH]), view!)).toBe("水中貫穿");
  });

  it("條件不成立：不發亮、圖示維持基礎型態", () => {
    const view = skillVariantView(card([WATER, HIGH]), state(null, []));
    expect(view).toEqual({ activeId: null, reachableIds: [], glow: false });
    expect(activeVariantCard(card([WATER, HIGH]), view)).toBeNull();
    expect(variantBadge(card([WATER, HIGH]), view!)).toBe("");
  });

  it("只對某些目標點成立（居高）：發亮，但圖示不換、標「可用」", () => {
    const c = card([WATER, HIGH]);
    const view = skillVariantView(c, state(null, ["high_tide"]));
    expect(view?.glow).toBe(true);
    expect(activeVariantCard(c, view)).toBeNull();
    expect(readyVariants(c, view).map((v) => v.id)).toEqual(["high_tide"]);
    expect(variantBadge(c, view!)).toBe("可用：居高投矛");
  });

  it("伺服器列了卡片上沒有的型態時略過它", () => {
    const view = skillVariantView(card([WATER]), state("ghost", ["ghost"]));
    expect(view).toEqual({ activeId: null, reachableIds: [], glow: false });
  });

  it("依目標點的條件有說明", () => {
    expect(conditionNote(HIGH)).toContain("預覽");
    expect(conditionNote(WATER)).toBe("");
  });
});

function hero(): UnitView {
  return { id: "u1", skills: ["skill_tidal_spear"], granted_skills: [], cooldowns: {}, source: 0 } as unknown as UnitView;
}

describe("戰場變奏：技能按鈕", () => {
  const legal: Action[] = [{ type: "use_skill", unit_id: "u1", skill_id: "skill_tidal_spear", target_id: "u2" } as Action];

  it("按鈕帶變奏狀態；沒有 variant_states 時不帶", () => {
    const c = { skill_tidal_spear: card([WATER, HIGH]) };
    const withState = skillButtons(hero(), legal, c, [state("tide_pierce", ["tide_pierce"])]);
    expect(withState[0]?.variant?.glow).toBe(true);
    expect(withState[0]?.variant?.activeId).toBe("tide_pierce");
    const without = skillButtons(hero(), legal, c);
    expect(without[0]?.variant).toBeUndefined();
  });
});

describe("戰場變奏：預覽的型態", () => {
  const base = {
    hit_permille: 800,
    crit_permille: 50,
    damage: null,
    cover: null,
    targets: [],
    healed: [],
    certain: [],
    possible: [],
    notes: [],
    min_events: [],
    max_events: [],
    topples: [],
    hurls: [],
    summons: [],
    bombs: [],
    revives: [],
    grants: [],
    collisions: [],
    moves: [],
    displace_checks: [],
    miss_notes: [],
    backstab: [],
    run_range: [],
  } as unknown as PreviewOut;

  it("目標點選出變奏型態時第一行寫型態名；基礎型態不寫", () => {
    const oil = { ...base, variant: { id: "oil_spark", name_zh: "油上火星" } } as PreviewOut;
    expect(previewVariantLine(oil)).toBe("型態：油上火星");
    expect(previewVariantLine({ ...base, variant: null } as PreviewOut)).toBeNull();
    const names = unitNames({ units: [] } as never);
    const view = { units: [], objects: [] } as never;
    expect(previewLines(oil, names, view)[0]).toBe("型態：油上火星");
    expect(previewLines({ ...base, variant: null } as PreviewOut, names, view)[0]).not.toContain("型態");
  });

  it("技能工坊：填完稀有度後預設停在稀有度，不自動跳到可省略的變奏步驟", () => {
    const steps = ["skeleton", "basics", "rarity", "variants"].map((id) => ({ id, complete: true }));
    const options = { steps, next_step: null, problems: [] } as unknown as DraftOptions;
    expect(defaultStep(options)).toBe("rarity");
    expect(STEP_NAMES.variants).toBe("戰場變奏");
  });

  it("滑到不同目標點，型態跟著預覽切換", () => {
    const a = { ...base, variant: { id: "high_tide", name_zh: "居高投矛" } } as PreviewOut;
    const b = { ...base, variant: null } as PreviewOut;
    expect([a, b].map(previewVariantLine)).toEqual(["型態：居高投矛", null]);
  });
});
