// Phase 5A-ART1／ART2：異形畫法（docs/art/敵人外觀.md、docs/art/sample/enemyArt.js）。
import { describe, expect, it } from "vitest";
import type { UnitDraw } from "../battle/drawModel";
import {
  AFFIX,
  BODIES,
  BODY_IDS,
  BODY_VARIANTS,
  CREATURE_ELEM,
  CREATURE_GLOW,
  ELITE_SCALE,
  MATERIALS,
  SIZES,
  TRAITS,
  creatureKey,
  drawCreature,
  drawHumanoidFx,
  knownAffixes,
  renderCreatureCanvas,
  resolveCreature,
  type CreatureLookDraw,
} from "./inkCreature";
import { linkPairs } from "./linkLines";
import { creatureOf, creatureSide, hasEliteMark, humanoidEliteScale, isLinked } from "./unitSprite";

/** 記錄所有呼叫的假 Canvas 2D：任何方法都可以呼叫、任何屬性都可以設定。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a)).join(",")})`);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const draw = (look: CreatureLookDraw, extra: Parameters<typeof resolveCreature>[0] extends infer T ? Omit<T & object, "look"> : never = {}): string[] => {
  const { ctx, calls } = mockCtx();
  drawCreature(ctx, resolveCreature({ look, ...extra }));
  return calls;
};

describe("身形 × 材質 × 大小", () => {
  it("14 種身形（含款式）× 6 種材質都畫得出來，而且彼此不同", () => {
    expect(BODY_IDS).toHaveLength(14);
    expect(MATERIALS).toHaveLength(6);
    const seen = new Set<string>();
    for (const body of BODY_IDS) {
      for (const variant of BODY_VARIANTS[body] ?? [undefined]) {
        for (const material of MATERIALS) {
          const calls = draw({ body, variant: variant ?? null, material });
          expect(calls.length).toBeGreaterThan(20);
          seen.add(calls.join(";"));
        }
      }
    }
    expect(seen.size).toBe((BODY_IDS.length + 2) * MATERIALS.length);
  });

  it("每種大小的倍率照樣張：tiny 0.62、small 0.8、medium 1、large 1.25、huge 1.6；不認得 → 1", () => {
    expect(SIZES).toEqual({ tiny: 0.62, small: 0.8, medium: 1, large: 1.25, huge: 1.6 });
    for (const [id, k] of Object.entries(SIZES)) {
      const r = resolveCreature({ look: { body: "lizard", size: id } });
      expect(r.size).toBeCloseTo(k);
      expect(draw({ body: "lizard", size: id })).toContain(`scale(${k.toFixed(2)},${k.toFixed(2)})`);
    }
    expect(resolveCreature({ look: { body: "lizard", size: "giant_unknown" } }).size).toBe(1);
  });

  it("材質的色票：熔岩玄武岩黑＋元素光、源晶混 40% 元素、霧 62% 半透明、毛皮混 22% 元素", () => {
    expect(draw({ body: "ooze", material: "magma" }).join(";")).toContain("fillStyle=#4a3631");
    expect(draw({ body: "ooze", material: "magma", element: "ice" }).join(";")).toContain("strokeStyle=#8fe3ff");
    expect(draw({ body: "ooze", material: "crystal" }).join(";")).toContain("fillStyle=#9a86ff");
    expect(draw({ body: "hound", material: "mist" }).join(";")).toContain("globalAlpha=0.62");
    const furFire = draw({ body: "ooze", material: "fur", element: "fire" }).join(";");
    expect(furFire).not.toContain("fillStyle=#6a9a5a");
  });

  it("不認得的值一律退回、不丟錯（全組合自測）", () => {
    const bodies = [...BODY_IDS, "dragon_unknown"];
    const mats = [...MATERIALS, "lava_unknown", null];
    const els = [null, ...Object.keys(CREATURE_ELEM), "void_unknown"];
    const sizes = [...Object.keys(SIZES), "giant_unknown", null];
    const traits = [[], Object.keys(TRAITS), ["nope"]];
    const affixes = [[], [...Object.keys(AFFIX), "mirror"], ["nope"]];
    let n = 0;
    for (const body of bodies)
      for (const material of mats)
        for (const element of els) {
          const look: CreatureLookDraw = { body, material, element, size: sizes[n % sizes.length] ?? null, traits: traits[n % traits.length] ?? [], variant: ["bat", "spider", "?", null][n % 4] ?? null };
          expect(() => draw(look, { affixes: affixes[n % affixes.length], elite: n % 2 === 0, rarity: n % 5 === 0 ? "legendary" : n % 7 === 0 ? "weird" : null })).not.toThrow();
          n++;
        }
    expect(n).toBeGreaterThan(1000);
    expect(resolveCreature({ look: { body: "dragon_unknown" } }).body).toBe("ooze");
    expect(resolveCreature({ look: { body: "hound", material: "lava_unknown" } }).material).toBe("fur");
    expect(resolveCreature({ look: { body: "hound", element: "void_unknown" } }).element).toBeUndefined();
    expect(resolveCreature({ look: { body: "flyer", variant: "?" } }).variant).toBe("bird");
    expect(resolveCreature({ look: { body: "hound", traits: ["nope", "mist"] } }).traits).toEqual(["mist"]);
  }, 30_000); // 全組合自測：完整平行跑時會超過預設 5 秒

  it("熔爐母獸的熔核在腹部（lizard 的 core 點 (2,-7.4)）；晶靈的熔核 (0,-20)", () => {
    expect(BODIES["lizard"]!.core).toEqual([2, -7.4]);
    expect(BODIES["wisp"]!.core).toEqual([0, -20]);
    expect(draw({ body: "lizard", material: "magma", size: "large", traits: ["brood", "core"] })).toContain("ellipse(1.40,-8.20,1.20,1.20,0.00,0.00,6.28)");
  });

  it("沒有 DOM 時貼圖回傳 null（不丟錯）", () => {
    expect(renderCreatureCanvas(resolveCreature({ look: { body: "hound" } }), "east", 2)).toBeNull();
  });
});

describe("status_traits：依狀態多畫的特徵", () => {
  const heart: CreatureLookDraw = { body: "wisp", material: "crystal", element: "fire", size: "huge", traits: ["core"], status_traits: { molten_shell: ["crust"] } };

  it("灰燼之心有熔殼時畫甲蟲殼堆；狀態移除（第 2 階段）殼就消失", () => {
    const shell = resolveCreature({ look: heart, statusIds: ["molten_shell"], rarity: "legendary" });
    const bare = resolveCreature({ look: heart, statusIds: [], rarity: "legendary" });
    expect(shell.traits).toEqual(["core", "crust"]);
    expect(bare.traits).toEqual(["core"]);
    expect(creatureKey(shell, "west")).not.toBe(creatureKey(bare, "west"));
    const withShell = draw(heart, { statusIds: ["molten_shell"] }).join(";");
    const without = draw(heart, { statusIds: ["burning"] }).join(";");
    expect(withShell).toContain("fillStyle=#4a3631"); // 玄武岩色的殼片
    expect(without).not.toContain("fillStyle=#4a3631");
  });

  it("不認得的狀態 ID 或特徵略過", () => {
    const r = resolveCreature({ look: { body: "wisp", status_traits: { molten_shell: ["nope"], other: ["crust"] } }, statusIds: ["molten_shell"] });
    expect(r.traits).toEqual([]);
  });
});

describe("精英與頭目記號", () => {
  it("精英 ×1.15；頭目（有外光）不放大", () => {
    expect(resolveCreature({ look: { body: "crawler", size: "large" }, elite: true }).size).toBeCloseTo(1.25 * ELITE_SCALE);
    const boss = resolveCreature({ look: { body: "golem", size: "huge" }, elite: true, rarity: "legendary" });
    expect(boss.size).toBeCloseTo(1.6);
    expect(boss.glow).toBe(CREATURE_GLOW["legendary"]);
    expect(resolveCreature({ look: { body: "golem" }, rarity: "weird" }).glow).toBeUndefined();
  });

  it("詞綴：內容 ID 與美術 id 都認得；不認得的略過；mirror 畫分身、mist_hidden 本體 75%", () => {
    expect(knownAffixes(["hard_shelled", "regenerating", "mist_veiled", "heart_linked", "berserk", "blazing", "nope", "regen"])).toEqual(["hardshell", "regen", "mist_hidden", "linked", "berserk", "blazing"]);
    const mirror = draw({ body: "hound" }, { affixes: ["mirror"] });
    expect(mirror).toContain("globalAlpha=0.35");
    expect(mirror).toContain("translate(-9.00,-1.00)");
    expect(draw({ body: "hound" }, { affixes: ["mist_hidden"] })).toContain("globalAlpha=0.75");
    const plain = draw({ body: "hound" }).join(";");
    expect(draw({ body: "hound" }, { affixes: ["berserk"] }).join(";")).not.toBe(plain);
    expect(draw({ body: "hound" }, { affixes: ["nope"] }).join(";")).toBe(plain);
  });

  it("人形敵人：詞綴畫在身上、霧氣繞身畫在身體後面", () => {
    const over = mockCtx();
    drawHumanoidFx(over.ctx, ["regen"], ["mist", "sparks"], false);
    expect(over.calls.join(";")).toContain("strokeStyle=#3f9a4a");
    expect(over.calls.join(";")).toContain("strokeStyle=#fff36b");
    expect(over.calls.join(";")).not.toContain("fillStyle=#eef2f4");
    const under = mockCtx();
    drawHumanoidFx(under.ctx, ["regen"], ["mist", "sparks"], true);
    expect(under.calls.join(";")).toContain("fillStyle=#eef2f4");
    expect(under.calls.join(";")).not.toContain("strokeStyle=#3f9a4a");
  });
});

const unit = (over: Partial<UnitDraw>): UnitDraw => ({
  id: "u1", x: 0, y: 0, marker: "A", template: "t", name: "n", team: "enemy", fill: 0, hpRatio: 1, shieldRatio: 0,
  active: false, hero: false, downed: false, summon: false, totem: false, remaining: null, revivable: false, bomb: null,
  facing: "west", weaponId: "fangs", weaponClass: "melee", ...over,
});
const dollLook = (over: Record<string, unknown>): UnitDraw["dollLook"] => ({ skin: "#f1c9a5", skull: false, gear: {}, beard: false, affixes: [], traits: [], ...over }) as UnitDraw["dollLook"];

describe("戰場單位（unitSprite）", () => {
  it("doll_look.creature 有值才用異形；召喚物也是（優先於 summon_look）", () => {
    expect(creatureOf(unit({}))).toBeNull();
    expect(creatureOf(unit({ dollLook: dollLook({}) }))).toBeNull();
    const whelp = creatureOf(unit({ summon: true, summonLook: { body: "beast", variant: "wolf" }, dollLook: dollLook({ creature: { body: "lizard", material: "magma", size: "tiny", traits: [] } }) }));
    expect(whelp?.body).toBe("lizard");
    expect(whelp?.size).toBeCloseTo(0.8); // 戰場最小大小（5A-ART5）
    const heart = unit({ statusIds: ["molten_shell"], dollLook: dollLook({ rarity: "legendary", creature: { body: "wisp", traits: ["core"], status_traits: { molten_shell: ["crust"] } } }) });
    expect(creatureOf(heart)?.traits).toEqual(["core", "crust"]);
    expect(creatureOf({ ...heart, statusIds: [] })?.traits).toEqual(["core"]);
  });

  it("異形只有側面：南北依陣營朝向對手（敵方朝西、我方朝東）", () => {
    expect(creatureSide({ facing: "west", team: "ally" })).toBe("west");
    expect(creatureSide({ facing: "east", team: "enemy" })).toBe("east");
    expect(creatureSide({ facing: "south", team: "enemy" })).toBe("west");
    expect(creatureSide({ facing: "north", team: "third" })).toBe("west");
    expect(creatureSide({ facing: "south", team: "ally" })).toBe("east");
  });

  it("金環：精英或頭目；倒下不畫。人形精英 ×1.15、頭目不放大", () => {
    expect(hasEliteMark(unit({}))).toBe(false);
    expect(hasEliteMark(unit({ elite: true }))).toBe(true);
    expect(hasEliteMark(unit({ dollLook: dollLook({ rarity: "legendary" }) }))).toBe(true);
    expect(hasEliteMark(unit({ elite: true, downed: true }))).toBe(false);
    expect(humanoidEliteScale(unit({ elite: true }))).toBeCloseTo(ELITE_SCALE);
    expect(humanoidEliteScale(unit({ elite: true, dollLook: dollLook({ rarity: "legendary" }) }))).toBe(1);
    expect(humanoidEliteScale(unit({}))).toBe(1);
  });

  it("連心的：和相鄰（曼哈頓 1）同陣營、沒倒下的單位連線，每對一次", () => {
    const a = unit({ id: "a", x: 2, y: 2, dollLook: dollLook({ affixes: ["linked"] }) });
    const units = [
      a,
      unit({ id: "b", x: 3, y: 2 }),
      unit({ id: "c", x: 2, y: 3, downed: true }),
      unit({ id: "d", x: 1, y: 2, team: "ally" }),
      unit({ id: "e", x: 3, y: 3 }),
      unit({ id: "f", x: 2, y: 1, dollLook: dollLook({ affixes: ["heart_linked"] }) }),
    ];
    expect(isLinked(a)).toBe(true);
    expect(linkPairs(units, isLinked).map(([p, q]) => `${p.id}-${q.id}`)).toEqual(["a-b", "a-f"]);
  });
});
