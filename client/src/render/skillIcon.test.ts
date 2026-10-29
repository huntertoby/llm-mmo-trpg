import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { SkillIconData } from "../api/types";
import { ELEMENT_VFX, hexToNumber } from "../battle/vfxPalette";
import { ELEMENT_COLORS } from "./palette";
import fixture from "./fixtures/skill_icons.json";
import { ELEMENT_ICON, elementPalette, isRanged, SKELETON_NAME } from "./skillGlyphs";
import {
  assemblyFormula,
  statusTile,
  surfaceTile,
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
  cost_values: {},
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
      expect(() => assemblyFormula(icon)).not.toThrow();
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

  it("組裝算式：每段一行（骨架＋形狀＋效果），段間是接續，條件與代價在最後；類型、元素、稀有度被濾掉", () => {
    const icon = minimal({
      rarity: "epic",
      elements: ["fire"],
      link: "after_move",
      condition: { id: "height_advantage", status: null },
      costs: ["source", "once"],
      cost_values: { source: 2, once: 1 },
      segments: [
        { skeleton: "displace", shape_id: "single", range: 4, elements: [], effects: [{ type: "leap" }] },
        { skeleton: "area", shape_id: "cross", range: null, elements: ["ice"], effects: [{ type: "damage" }, { type: "knock_prone" }] },
      ],
    });
    const f = assemblyFormula(icon);
    expect(f.rows.map((r) => r.map((t) => t.cat))).toEqual([
      ["骨架", "形狀", "效果（核心）"],
      ["骨架（第二段）", "形狀", "效果", "效果"],
    ]);
    expect(f.links.map((t) => [t.cat, t.label])).toEqual([["接續", "移動後觸發"]]);
    expect(f.extras.map((t) => t.cat)).toEqual(["條件", "代價", "代價"]);
    const all = [...f.rows.flat(), ...f.links, ...f.extras].map((t) => t.cat);
    for (const gone of ["類型", "元素", "稀有度"]) expect(all).not.toContain(gone);
  });

  it("單段技能只有一行、沒有接續", () => {
    const f = assemblyFormula(minimal());
    expect(f.rows).toHaveLength(1);
    expect(f.links).toEqual([]);
    expect(f.extras).toEqual([]);
  });

  it("接續是延遲時，代價裡的延遲不重複；代價帶數值", () => {
    const delayed = assemblyFormula(
      minimal({
        link: "delayed",
        costs: ["delay", "source"],
        cost_values: { delay: 1, source: 2 },
        segments: [
          { skeleton: "strike", shape_id: "single", range: 1, elements: [], effects: [{ type: "damage" }] },
          { skeleton: "area", shape_id: "cross", range: null, elements: [], effects: [{ type: "damage" }] },
        ],
      }),
    );
    expect(delayed.extras.map((t) => t.label)).toEqual(["源力 2"]);
    const timed = assemblyFormula(minimal({ costs: ["delay", "once", "stacks"], cost_values: { delay: 3, once: 2, stacks: 1 } }));
    expect(timed.extras.map((t) => t.label)).toEqual(["延遲 3 回合", "每場 2 次", "消耗層數 1"]);
  });

  it("被動、反應：觸發時機放在第一行最前面；修正：改造對象與改變內容", () => {
    const passive = assemblyFormula(minimal({ kind: "passive", trigger: "on_kill" }));
    expect(passive.rows[0]?.slice(0, 2).map((t) => t.cat)).toEqual(["觸發", "骨架"]);
    expect(passive.rows[0]?.[0]?.label).toBe("擊倒時");
    const reaction = assemblyFormula(minimal({ kind: "reaction", trigger: "hit_by_melee" }));
    expect(reaction.rows[0]?.[0]?.tip).toBe("反應時機：被近戰攻擊命中、傷害結算之後。");
    const mod = assemblyFormula(
      minimal({
        kind: "modifier",
        modifier: {
          applies_to: { actions: ["attack"] },
          changes: [
            { key: "damage_permille", value: 200, part_ids: [] },
            { key: "add_element", value: "fire", part_ids: [] },
          ],
        },
      }),
    );
    expect(mod.rows).toHaveLength(1);
    expect(mod.rows[0]?.map((t) => t.cat)).toEqual(["改造對象", "改變內容", "改變內容"]);
    expect(mod.rows[0]?.[1]?.label).toBe("傷害 +20%");
    expect(mod.rows[0]?.[2]?.label).toBe("加上火元素");
  });

  it("add_tags 與 on_hit_effects 有專屬部件（不是「?」）", () => {
    const tags = modifierChangePart("add_tags", ["push", "fire"], ["push", "fire"]);
    expect(tags.label).toBe("加上標籤：推擊／fire");
    const hit = modifierChangePart("on_hit_effects", [{ type: "damage" }, { type: "apply_status", status: "burning" }], ["damage", "apply_status:burning"]);
    expect(hit.label).toContain("命中後：傷害／");
    expect(hit.label).toContain(effectPart({ type: "apply_status", status: "burning" }).label);
    const { ctx } = fakeCtx();
    expect(() => tags.draw(ctx)).not.toThrow();
    expect(() => hit.draw(ctx)).not.toThrow();
    // 沒有 part_ids（舊資料）也能從 value 取
    expect(modifierChangePart("on_hit_effects", [{ type: "damage" }]).label).toBe("命中後：傷害");
  });

  it("治療量與召喚物數值（Phase 3-24b1）有專屬部件", () => {
    const heal = modifierChangePart("heal_permille", 150);
    const hp = modifierChangePart("summon_hp_permille", 200);
    const dice = modifierChangePart("summon_attack_dice", 1);
    expect([heal.label, hp.label, dice.label]).toEqual(["治療量 +15%", "召喚物 HP +20%", "召喚物攻擊 +1 骰"]);
    expect(modifierChangePart("heal_permille", -300).label).toBe("治療量 -30%");
    const { ctx } = fakeCtx();
    for (const p of [heal, hp, dice]) {
      expect(p.cat).toBe("change");
      expect(() => p.draw(ctx)).not.toThrow();
    }
  });

  it("召喚專精的改變（Phase 3-33f1）有專屬部件", () => {
    const limit = modifierChangePart("summon_limit_delta", -1);
    const dur = modifierChangePart("summon_duration_delta", 2);
    const dmg = modifierChangePart("summon_damage_permille", 500);
    expect([limit.label, dur.label, dmg.label]).toEqual(["召喚物上限 -1", "召喚物持續 +2 輪", "召喚物傷害 +50%"]);
    const { ctx } = fakeCtx();
    for (const p of [limit, dur, dmg]) expect(() => p.draw(ctx)).not.toThrow();
  });

  it("代價名稱帶數值", () => {
    expect(costPart("source", 2).label).toBe("源力 2");
    expect(costPart("delay", 1).label).toBe("延遲 1 回合");
    expect(costPart("once", 1).label).toBe("每場一次");
    expect(costPart("gamble").label).toBe("賭注");
  });

  it("每個說明都是「類別：名稱（說明）」", () => {
    const f = assemblyFormula(data.skills["skill_leap_slam"] as SkillIconData);
    for (const t of [...f.rows.flat(), ...f.links, ...f.extras]) {
      expect(tileTitle(t)).toBe(`${t.cat}：${t.label}（${t.tip}）`);
    }
  });

  it("狀態與表面部件：類別、名稱與說明取自名詞對照表", () => {
    const burning = statusTile("burning");
    expect(burning.cat).toBe("狀態");
    expect(burning.label).not.toBe("burning");
    expect(burning.tip.length).toBeGreaterThan(2);
    expect(surfaceTile("fire").cat).toBe("表面");
    const { ctx } = fakeCtx();
    expect(() => statusTile("never_heard_of").draw(ctx)).not.toThrow();
    expect(() => surfaceTile("never_heard_of").draw(ctx)).not.toThrow();
  });

  it("工坊每多一步，算式只會變長不會變短", () => {
    const size = (icon: SkillIconData) => {
      const f = assemblyFormula(icon);
      return f.rows.flat().length + f.links.length + f.extras.length;
    };
    for (const [name, steps] of Object.entries(data.workshop)) {
      const lengths = steps.map(size);
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

  it("算式的小圖：同一個部件鍵相同；形狀隨元素與骨架變", () => {
    const tiles = assemblyFormula(minimal({ elements: ["fire"] })).rows.flat();
    const again = assemblyFormula(minimal({ elements: ["fire"] })).rows.flat();
    expect(tiles.map((t) => tileKey(t, 30))).toEqual(again.map((t) => tileKey(t, 30)));
    const shapeOf = (el: string) => tileKey(assemblyFormula(minimal({ elements: [el] })).rows.flat().find((t) => t.cat === "形狀") as never, 30);
    expect(shapeOf("fire")).not.toBe(shapeOf("ice"));
  });

  it("大小圖是不同的快取鍵", () => {
    const a = minimal();
    expect(iconCacheKey(a, 72, true)).not.toBe(iconCacheKey(a, 72, false));
    expect(iconCacheKey(a, 72, true)).not.toBe(iconCacheKey(a, 40));
    expect(iconCacheKey(a, 40)).toBe(iconCacheKey(a, 40, true));
  });
});

describe("元素配色只有一個來源", () => {
  it("技能圖示與特效取到同一個顏色", () => {
    for (const [id, c] of Object.entries(ELEMENT_COLORS)) {
      expect(ELEMENT_VFX[id]?.primary).toBe(hexToNumber(c.primary));
      expect(ELEMENT_VFX[id]?.secondary).toBe(hexToNumber(c.secondary));
      expect(elementPalette(id).accent).toBe(c.accent);
      expect(elementPalette(id).dark).toBe(c.dark);
      expect(elementPalette(id).light).toBe(c.light);
    }
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
