import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { SkillIconData } from "../api/types";
import { ELEMENT_VFX } from "../battle/vfxPalette";
import fixture from "./fixtures/skill_icons.json";
import { ELEMENT_ICON, elementPalette, isRanged, SKELETON_NAME } from "./skillGlyphs";
import {
  assemblyTiles,
  iconCacheKey,
  optionTile,
  paintSkillIcon,
  partsOf,
  stableStringify,
  tileKey,
  tileTitle,
} from "./skillIcon";
import { conditionPart, costPart, effectPart, KNOWN_PARTS, linkPart, modifierChangePart, modifierTargetPart, triggerPart } from "./skillParts";

// ---- 假的 Canvas 2D：記錄呼叫，不真的畫（vitest 在 node 跑）----
function fakeCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const target: Record<string, unknown> = {};
  const ctx = new Proxy(target, {
    get(_t, name: string) {
      if (name in target) return target[name];
      if (name === "createRadialGradient" || name === "createLinearGradient") {
        return () => ({ addColorStop: () => undefined });
      }
      return (..._args: unknown[]) => {
        calls.push(name);
      };
    },
    set(_t, name: string, value) {
      target[name] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const data = fixture as unknown as {
  skills: Record<string, SkillIconData>;
  random: SkillIconData[];
  workshop: Record<string, SkillIconData[]>;
};
const SKILLS = Object.entries(data.skills);

function yamlIds(raw: string, key: string): string[] {
  const doc = parse(raw) as Record<string, Array<{ id: string }>>;
  return (doc[key] ?? []).map((r) => r.id);
}
const content = import.meta.glob("../../../content/*.yaml", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const skeletonFiles = import.meta.glob("../../../content/skeletons/*.yaml", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const contentIds = (file: string, key: string) => yamlIds(content[`../../../content/${file}`] as string, key);

const minimal = (over: Partial<SkillIconData> = {}): SkillIconData => ({
  kind: "active",
  rarity: "common",
  elements: [],
  weapon_req: "any",
  segments: [{ skeleton: "strike", shape_id: "single", range: 1, elements: [], effects: [{ type: "damage" }] }],
  link: null,
  condition: null,
  costs: [],
  trigger: null,
  modifier: null,
  partial: false,
  ...over,
});

describe("部件庫：對照 content/ 沒有漏", () => {
  it("每個效果原語、狀態、表面、條件、觸發都有專屬圖示", () => {
    const missing = (ids: string[], known: readonly string[]) => ids.filter((id) => !known.includes(id));
    expect(missing(contentIds("skill_primitives.yaml", "primitives"), KNOWN_PARTS.effects)).toEqual([]);
    expect(missing(contentIds("statuses.yaml", "statuses").filter((s) => !s.startsWith("stance_")), KNOWN_PARTS.statuses)).toEqual([]);
    expect(missing(contentIds("surfaces.yaml", "surfaces"), KNOWN_PARTS.surfaces)).toEqual([]);
    expect(missing(contentIds("skill_conditions.yaml", "conditions"), KNOWN_PARTS.conditions)).toEqual([]);
    expect(missing(contentIds("skill_triggers.yaml", "triggers"), KNOWN_PARTS.triggers)).toEqual([]);
  });

  it("元素配色與特效色票同一組元素（沒有多、沒有漏）", () => {
    const vfx = Object.keys(ELEMENT_VFX).filter((k) => k !== "water");
    expect(Object.keys(ELEMENT_ICON).sort()).toEqual([...vfx].sort());
  });

  it("每個骨架都有名稱", () => {
    const ids = Object.keys(skeletonFiles).map((f) => f.replace(/^.*\/(\w+)\.yaml$/, "$1"));
    expect(ids.length).toBeGreaterThan(10);
    for (const id of ids) expect(SKELETON_NAME[id], id).toBeDefined();
  });
});

describe("部件庫：不認得的部件走預設", () => {
  it("未知效果、狀態、表面、條件、觸發、代價、修正都產生部件且畫得出來", () => {
    const { ctx } = fakeCtx();
    const parts = [
      effectPart({ type: "teleport_to_moon" }),
      effectPart({ type: "apply_status", status: "glitter" }),
      effectPart({ type: "create_surface", surface: "jelly" }),
      conditionPart("moon_is_full"),
      conditionPart("target_has_status", "glitter"),
      triggerPart("on_eclipse", false),
      triggerPart("on_eclipse", true),
      costPart("mystery"),
      linkPart("sometime"),
      modifierTargetPart({ mystery: true }),
      modifierChangePart("mystery", 1),
    ];
    for (const p of parts) {
      expect(p).not.toBeNull();
      expect(() => p?.draw(ctx)).not.toThrow();
      expect(p?.label).not.toBe("");
    }
    expect(effectPart({ type: "apply_status", status: "glitter" }).label).toBe("glitter"); // 沒有名稱時顯示代碼
    expect(effectPart({ type: "apply_status", status: "burning" }).label).toBe("燃燒");
    expect(effectPart({ type: "create_surface", surface: "oil" }).label).toBe("油表面");
    expect(linkPart("sometime").key).toBe("sometime");
    expect(linkPart("sometime").label).toBe(linkPart("after_action").label);
  });

  it("空的條件、觸發沒有部件", () => {
    expect(conditionPart(null)).toBeNull();
    expect(conditionPart("")).toBeNull();
    expect(triggerPart(null, true)).toBeNull();
  });
});

describe("技能圖示：每個技能都畫得出來", () => {
  it("內容庫的每個技能（大圖與小圖）不丟例外", () => {
    expect(SKILLS.length).toBeGreaterThan(100);
    for (const [id, icon] of SKILLS) {
      for (const small of [false, true]) {
        const { ctx, calls } = fakeCtx();
        expect(() => paintSkillIcon(ctx, icon, small), id).not.toThrow();
        expect(calls.length).toBeGreaterThan(10);
      }
    }
  });

  it("隨機組合器 50 個技能與工坊每一步的半成品也畫得出來", () => {
    expect(data.random).toHaveLength(50);
    const drafts = Object.values(data.workshop).flat();
    for (const icon of [...data.random, ...drafts]) {
      const { ctx } = fakeCtx();
      expect(() => paintSkillIcon(ctx, icon, false)).not.toThrow();
      expect(() => assemblyTiles(icon)).not.toThrow();
    }
  });

  it("不認得的元素、形狀、骨架、類型、稀有度走預設", () => {
    const icon = minimal({
      kind: "wizard",
      rarity: "mythic",
      elements: ["plasma", "ether"],
      segments: [{ skeleton: "kung_fu", shape_id: "tesseract", range: null, elements: [], effects: [{ type: "mystery" }] }],
    });
    const { ctx } = fakeCtx();
    expect(() => paintSkillIcon(ctx, icon, false)).not.toThrow();
    expect(() => paintSkillIcon(ctx, icon, true)).not.toThrow();
    expect(elementPalette("plasma")).toEqual(elementPalette(null));
    expect(elementPalette(undefined).name).toBe("（未選）");
  });

  it("小圖只畫元素、形狀、核心效果與外框（比大圖少很多筆畫）", () => {
    const icon = data.skills["skill_leap_slam"] as SkillIconData;
    const big = fakeCtx();
    const small = fakeCtx();
    paintSkillIcon(big.ctx, icon, false);
    paintSkillIcon(small.ctx, icon, true);
    expect(small.calls.length).toBeLessThan(big.calls.length);
  });
});

describe("拆解：核心效果與組裝順序", () => {
  it("核心效果＝第一個不是單純傷害的效果，放在效果列第一個；最多 4 個", () => {
    const icon = minimal({
      segments: [
        {
          skeleton: "area",
          shape_id: "cone",
          range: null,
          elements: [],
          effects: [{ type: "damage" }, { type: "push" }, { type: "apply_status", status: "burning" }, { type: "create_surface", surface: "fire" }, { type: "heal" }],
        },
      ],
    });
    const p = partsOf(icon);
    expect(p.core?.key).toBe("push");
    expect(p.effects.map((e) => e.key)).toEqual(["push", "damage", "status:burning", "surface:fire"]);
    expect(partsOf(minimal()).core?.key).toBe("damage");
    expect(partsOf(minimal({ segments: [{ skeleton: null, shape_id: null, range: null, elements: [], effects: [] }] })).core).toBeNull();
  });

  it("組裝列順序：類型 → 骨架 → 元素 → 形狀 → 效果 → 接續 → 第二段 → 條件 → 代價 → 稀有度", () => {
    const icon = minimal({
      rarity: "epic",
      elements: ["fire"],
      link: "after_move",
      condition: { id: "height_advantage", status: null },
      costs: ["source", "once"],
      segments: [
        { skeleton: "displace", shape_id: "single", range: 4, elements: [], effects: [{ type: "leap" }] },
        { skeleton: "area", shape_id: "cross", range: null, elements: ["ice"], effects: [{ type: "damage" }, { type: "knock_prone" }] },
      ],
    });
    const cats = assemblyTiles(icon).map((t) => t.cat);
    expect(cats).toEqual([
      "類型",
      "骨架",
      "元素",
      "形狀",
      "效果（核心）",
      "接續",
      "骨架（第二段）",
      "元素", // 第二段元素不同才多一塊
      "形狀",
      "效果",
      "效果",
      "條件",
      "代價",
      "代價",
      "稀有度",
    ]);
    expect(assemblyTiles(icon).find((t) => t.cat === "接續")?.label).toBe("移動後觸發");
  });

  it("被動、反應：觸發時機在類型之後；修正：改造對象與改變內容", () => {
    const passive = assemblyTiles(minimal({ kind: "passive", trigger: "on_kill" }));
    expect(passive.map((t) => t.cat).slice(0, 2)).toEqual(["類型", "觸發"]);
    expect(passive[1]?.label).toBe("擊倒時");
    const reaction = assemblyTiles(minimal({ kind: "reaction", trigger: "hit_by_melee" }));
    expect(reaction[1]?.tip).toBe("反應時機");
    const mod = assemblyTiles(
      minimal({
        kind: "modifier",
        modifier: { applies_to: { actions: ["attack"] }, changes: [{ key: "damage_permille", value: 200 }, { key: "add_element", value: "fire" }] },
      }),
    );
    expect(mod.map((t) => t.cat)).toEqual(["類型", "改造對象", "改變內容", "改變內容", "稀有度"]);
    expect(mod[2]?.label).toBe("傷害 +20%");
    expect(mod[3]?.label).toBe("加上火元素");
  });

  it("每個浮動說明都是「類別：名稱（位置）」", () => {
    for (const t of assemblyTiles(data.skills["skill_leap_slam"] as SkillIconData)) {
      expect(tileTitle(t)).toBe(`${t.cat}：${t.label}（${t.tip}）`);
    }
  });

  it("工坊每多一步，組裝列只會變長不會變短", () => {
    // 修正技能到效果那一步才換成「改造對象＋改變內容」，只比頭尾；其他技能逐步遞增
    for (const [name, steps] of Object.entries(data.workshop)) {
      const lengths = steps.map((icon) => assemblyTiles(icon).length);
      if (name === "modifier") continue;
      expect(lengths).toEqual([...lengths].sort((a, b) => a - b));
      expect(lengths[lengths.length - 1]).toBeGreaterThan(lengths[0] as number);
    }
  });

  it("工坊半成品：還沒有形狀＝虛線圈、還沒有元素＝中性色", () => {
    const empty = partsOf(minimal({ partial: true, segments: [{ skeleton: "strike", shape_id: null, range: null, elements: [], effects: [] }] }));
    expect(empty.el).toBeUndefined();
    expect(empty.segs[0]?.motif.shape_id).toBeNull();
    const { ctx, calls } = fakeCtx();
    paintSkillIcon(ctx, minimal({ partial: true, segments: [{ skeleton: null, shape_id: null, range: null, elements: [], effects: [] }] }), false);
    expect(calls).toContain("setLineDash");
    expect(partsOf(minimal()).el).toBeNull(); // 完整但沒有元素 → 紫色預設
  });
});

describe("快取鍵", () => {
  it("同一組合（不管欄位順序）鍵相同，不同組合鍵不同，尺寸也算", () => {
    const a = minimal();
    const reordered = JSON.parse(JSON.stringify(a)) as Record<string, unknown>;
    const shuffled = Object.fromEntries(Object.entries(reordered).reverse()) as unknown as SkillIconData;
    expect(iconCacheKey(shuffled, 40)).toBe(iconCacheKey(a, 40));
    expect(iconCacheKey(a, 40)).not.toBe(iconCacheKey(a, 28));
    expect(iconCacheKey(minimal({ rarity: "rare" }), 40)).not.toBe(iconCacheKey(a, 40));
    expect(stableStringify({ b: 1, a: [2, { d: 1, c: 2 }] })).toBe('{"a":[2,{"c":2,"d":1}],"b":1}');
  });

  it("不同技能只要部件組合相同就共用一張貼圖鍵", () => {
    const keys = new Set(SKILLS.map(([, icon]) => iconCacheKey(icon, 40)));
    expect(keys.size).toBeLessThan(SKILLS.length);
  });

  it("組裝列的小圖：同一個部件鍵相同；形狀隨元素與骨架變", () => {
    const tiles = assemblyTiles(minimal({ elements: ["fire"] }));
    const again = assemblyTiles(minimal({ elements: ["fire"] }));
    expect(tiles.map((t) => tileKey(t, 44))).toEqual(again.map((t) => tileKey(t, 44)));
    const shapeOf = (el: string) => tileKey(assemblyTiles(minimal({ elements: [el] })).find((t) => t.cat === "形狀") as never, 44);
    expect(shapeOf("fire")).not.toBe(shapeOf("ice"));
  });
});

describe("工坊選項小圖與其他", () => {
  it("有圖示的欄位給小圖，沒有的給 null", () => {
    for (const [field, value] of [
      ["skeleton", "strike"],
      ["shape", "cone"],
      ["condition", "flanked"],
      ["event", "on_hit"],
      ["effects", "damage"],
      ["status", "burning"],
      ["surface", "fire"],
      ["element", "ice"],
      ["effects", "totally_unknown"],
    ] as const) {
      const tile = optionTile(field, value);
      expect(tile, `${field}:${value}`).not.toBeNull();
      const { ctx } = fakeCtx();
      expect(() => tile?.draw(ctx)).not.toThrow();
    }
    expect(optionTile("name_zh", "震地重擊")).toBeNull();
    expect(optionTile("shape", 3)).toBeNull();
    expect(optionTile("cost.mana", "x")).toBeNull();
  });

  it("單體的遠近：有射程看射程，武器射程看武器需求", () => {
    expect(isRanged(2, "melee")).toBe(true);
    expect(isRanged(1, "ranged")).toBe(false);
    expect(isRanged(null, "ranged")).toBe(true);
    expect(isRanged(null, "melee")).toBe(false);
  });
});
