// 戰場效果（Phase 3-36b）：裂痕、徽章、霧、陷阱踏板、區域單格；未知值一律退回預設、不丟例外。
import { beforeAll, describe, expect, it } from "vitest";
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { fxSkillOf, fxSkillsOf } from "../battle/fxSkills";
import { setGlossary, surfaceBlocksSight } from "../battle/glossary";
import { smallView } from "../battle/testFixtures";
import {
  cracks,
  drawCasterRing,
  drawTrapPad,
  drawZoneCell,
  fxColor,
  hpStageOf,
  sightVeil,
  surfaceHex,
  trapTriggerOf,
  turnsBadge,
  veilKindOf,
} from "./fieldFx";
import { drawObject, objectArtKey, OBJECT_DRAW, type ObjectArtSpec } from "./objectArt";
import { objectArtSpec } from "./artSpecs";

const artSpecDefaults = (over: Partial<ObjectArtSpec>): ObjectArtSpec => ({
  region: "",
  look: "",
  kind: "crate",
  x: 2,
  y: 3,
  joinL: false,
  joinR: false,
  vertical: false,
  flammable: false,
  turnsLeft: null,
  hpStage: 0,
  ...over,
});

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[]; store: Record<string, unknown> } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(prop);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
        void args;
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls, store };
}

beforeAll(() => setGlossary(glossary as unknown as Glossary));

describe("受損級距與裂痕", () => {
  it("hpStageOf：> 66% 為 0，≤ 66% 為 1，≤ 33% 為 2；沒有耐久或壞值為 0", () => {
    expect(hpStageOf(1)).toBe(0);
    expect(hpStageOf(0.67)).toBe(0);
    expect(hpStageOf(0.66)).toBe(1);
    expect(hpStageOf(0.34)).toBe(1);
    expect(hpStageOf(0.33)).toBe(2);
    expect(hpStageOf(0)).toBe(2);
    expect(hpStageOf(null)).toBe(0);
    expect(hpStageOf(Number.NaN)).toBe(0);
  });

  it("級距 0 不畫；級距 1 一道細裂；級距 2 三道粗裂", () => {
    const strokes = (stage: 0 | 1 | 2): { n: number; width: unknown } => {
      const { ctx, calls, store } = mockCtx();
      cracks(ctx, stage, 2, 3);
      return { n: calls.filter((c) => c === "stroke").length, width: store["lineWidth"] };
    };
    expect(strokes(0).n).toBe(0);
    expect(strokes(1)).toEqual({ n: 1, width: 1.3 });
    expect(strokes(2)).toEqual({ n: 3, width: 2 });
  });

  it("物件快取鍵用級距：HP 比例與剩餘回合的細微差別共用貼圖", () => {
    const base = { id: "o", kind: "ice_wall", x: 1, y: 1, name: "", glyph: "", fill: 0, flammable: false, burning: false, floor: false };
    const spec = (hpRatio: number | null, expiresIn: number | null) =>
      objectArtKey(objectArtSpec({ ...base, hpRatio, expiresIn }, new Map()));
    expect(spec(0.9, 3)).toBe(spec(1, 5));
    expect(spec(0.5, 3)).toBe(spec(0.6, 2));
    expect(spec(0.5, 3)).not.toBe(spec(0.9, 3));
    expect(spec(1, 1)).not.toBe(spec(1, 2));
    expect(spec(1, null)).not.toBe(spec(1, 3));
  });

  it("所有可破壞物件依級距疊裂痕（薄冰自己畫）：級距越高呼叫越多", () => {
    for (const kind of [...Object.keys(OBJECT_DRAW), "brand_new_object"]) {
      const counts = ([0, 1, 2] as const).map((hpStage) => {
        const { ctx, calls } = mockCtx();
        drawObject(ctx, artSpecDefaults({ kind, hpStage }));
        return calls.length;
      });
      expect(counts[2], kind).toBeGreaterThanOrEqual(counts[0] ?? 0);
      if (kind !== "thin_ice") expect(counts[1], kind).toBeGreaterThan(counts[0] ?? 0);
    }
  });
});

describe("剩餘回合徽章", () => {
  it("最後 1 回合改橘色，其餘白字", () => {
    const orange = mockCtx();
    turnsBadge(orange.ctx, 9, 9, 1);
    expect(orange.store["fillStyle"]).toBe("#ffb03a");
    const white = mockCtx();
    turnsBadge(white.ctx, 9, 9, 3);
    expect(white.store["fillStyle"]).toBe("#ffffff");
    const zero = mockCtx();
    expect(() => turnsBadge(zero.ctx, 9, 9, 0)).not.toThrow();
    expect(zero.store["fillStyle"]).toBe("#ffb03a");
  });
});

describe("擋視線表面的上層霧", () => {
  it("glossary 的 blocks_sight 表面才有霧（新表面只要有旗標就自動套用）", () => {
    expect(surfaceBlocksSight("smoke")).toBe(true);
    expect(surfaceBlocksSight("darkness")).toBe(true);
    for (const s of ["none", "fire", "oil", "water", "brand_new_surface", ""]) expect(surfaceBlocksSight(s), s).toBe(false);
    expect(veilKindOf("darkness")).toBe("dark");
    expect(veilKindOf("smoke")).toBe("gray");
    expect(veilKindOf("brand_new_surface")).toBe("gray");
  });

  it("黑暗多畫紫色光點；兩種都畫得出來、同一格每次一樣", () => {
    const run = (kind: "dark" | "gray", x = 2): string[] => {
      const { ctx, calls } = mockCtx();
      sightVeil(ctx, kind, x, 3);
      return calls;
    };
    const arcs = (x: number): string => {
      const circles: string[] = [];
      const { ctx } = mockCtx();
      ctx.arc = (x0: number, y0: number, r: number) => void circles.push(`${x0},${y0},${r}`);
      sightVeil(ctx, "gray", x, 3);
      return circles.join("|");
    };
    expect(run("dark")).toEqual(run("dark"));
    expect(arcs(2)).toBe(arcs(2));
    expect(arcs(2)).not.toBe(arcs(5));
    expect(run("dark").filter((c) => c === "fillRect")).toHaveLength(3);
    expect(run("gray").filter((c) => c === "fillRect")).toHaveLength(0);
  });
});

describe("陷阱踏板", () => {
  it("我方實線、敵方虛線加「!」；enter 與 delay 畫法不同；不認得的觸發方式與元素都能畫", () => {
    const run = (mine: boolean, trigger: "enter" | "delay", color = fxColor(null)): { calls: string[]; dash: boolean } => {
      const { ctx, calls } = mockCtx();
      let dash = false;
      const real = ctx.setLineDash.bind(ctx);
      ctx.setLineDash = (d: number[]) => {
        if (d.length > 0) dash = true;
        real(d);
      };
      drawTrapPad(ctx, { mine, trigger, color });
      return { calls, dash };
    };
    expect(run(true, "enter").dash).toBe(false);
    expect(run(false, "enter").dash).toBe(true);
    expect(run(false, "enter").calls).toContain("strokeText");
    expect(run(true, "enter").calls).not.toContain("strokeText");
    expect(run(true, "enter").calls.length).not.toBe(run(true, "delay").calls.length);
    expect(trapTriggerOf("delay")).toBe("delay");
    for (const t of ["enter", "brand_new_trigger", "", null, undefined]) expect(trapTriggerOf(t)).toBe("enter");
    expect(() => run(true, trapTriggerOf("???"), fxColor("brand_new_element"))).not.toThrow();
  });
});

describe("元素色", () => {
  it("元素 → 表面色 → 灰；不認得的值都是灰", () => {
    const gray = fxColor(null);
    expect(fxColor("fire")).toBe("#ff6a1a");
    expect(fxColor("brand_new_element")).toBe(gray);
    expect(fxColor("brand_new_element", "brand_new_surface")).toBe(gray);
    expect(fxColor(null, "fire")).toBe(surfaceHex("fire"));
    expect(surfaceHex("fire")).toMatch(/^#[0-9a-f]{6}$/);
    expect(surfaceHex("brand_new_surface")).toBeNull();
    expect(surfaceHex("none")).toBeNull();
    expect(fxColor("brand_new_element", "smoke")).toBe(surfaceHex("smoke"));
  });
});

describe("區域單格與施放者環", () => {
  it("有害＝斜紋實線、有益＝光點虛線；任何邊組合、箭頭方向都畫得出來", () => {
    const run = (harmful: boolean): { dash: boolean; lines: number } => {
      const { ctx, calls } = mockCtx();
      let dash = false;
      ctx.setLineDash = (d: number[]) => {
        if (d.length > 0) dash = true;
      };
      drawZoneCell(ctx, { color: "#ff7a1a", harmful, sides: ["n", "s", "w", "e"], arrow: "e", phase: 4 });
      return { dash, lines: calls.filter((c) => c === "lineTo").length };
    };
    // 不影響我方：虛線、沒有紋理（斜紋用 lineTo；光點用 arc）
    const neutral = ((): { dash: boolean; arcs: number; lines: number } => {
      const { ctx, calls } = mockCtx();
      let dash = false;
      ctx.setLineDash = (d: number[]) => {
        if (d.length > 0) dash = true;
      };
      drawZoneCell(ctx, { color: "#ff7a1a", harmful: true, neutral: true, sides: ["n"], arrow: null, phase: 4 });
      return { dash, arcs: calls.filter((c) => c === "arc").length, lines: calls.filter((c) => c === "lineTo").length };
    })();
    expect(neutral).toEqual({ dash: true, arcs: 0, lines: 1 });
    expect(run(true).dash).toBe(false);
    expect(run(false).dash).toBe(true);
    for (const arrow of ["n", "s", "w", "e", null] as const) {
      const { ctx } = mockCtx();
      expect(() => drawZoneCell(ctx, { color: "#d8d8e0", harmful: true, sides: [], arrow, phase: 0 })).not.toThrow();
    }
    const ring = mockCtx();
    expect(() => drawCasterRing(ring.ctx, "#d8d8e0")).not.toThrow();
  });
});

describe("陷阱與區域的繪製模型", () => {
  it("觸發方式與元素來自技能表；查不到或不認得退回 enter＋灰色（null）", () => {
    const view = smallView({
      traps: [
        { owner_id: "unit_0001", team: "ally", pos: { x: 1, y: 1 }, skill_id: "skill_bear_trap", remaining: 3 },
        { owner_id: "unit_0001", team: "ally", pos: { x: 2, y: 2 }, skill_id: "skill_mine", remaining: 2 },
        { owner_id: "unit_0003", team: "enemy", pos: { x: 3, y: 2 }, skill_id: "skill_unknown", remaining: 1 },
        { owner_id: "unit_0003", team: "enemy", pos: { x: 0, y: 2 }, skill_id: "skill_weird", remaining: 1 },
      ],
    });
    const skills = (id: string) =>
      id === "skill_bear_trap"
        ? { element: "physical", zoneElement: null, surface: null, trapTrigger: "enter" }
        : id === "skill_mine"
          ? { element: "fire", zoneElement: null, surface: null, trapTrigger: "delay" }
          : id === "skill_weird"
            ? { element: "brand_new_element", zoneElement: null, surface: null, trapTrigger: "brand_new_trigger" }
            : undefined;
    const traps = buildDrawModel(view, "unit_0001", undefined, skills).traps;
    expect(traps.map((t) => [t.trigger, t.element, t.mine, t.remaining])).toEqual([
      ["enter", "physical", true, 3],
      ["delay", "fire", true, 2],
      ["enter", null, false, 1],
      ["enter", "brand_new_element", false, 1],
    ]);
    // 沒有技能表：全部 enter、沒有元素
    expect(buildDrawModel(view, "unit_0001").traps.every((t) => t.trigger === "enter" && t.element === null)).toBe(true);
  });

  it("fxSkillOf 從技能卡的 icon 取出元素、區域元素、表面與陷阱觸發", () => {
    const icon = {
      elements: ["fire"],
      zone_element: "ice",
      trap_trigger: "delay",
      segments: [{ effects: [{ type: "damage" }, { type: "zone", surface: "smoke" }] }],
    };
    const card = { icon } as unknown as Parameters<typeof fxSkillOf>[0];
    expect(fxSkillOf(card)).toEqual({ element: "fire", zoneElement: "ice", surface: "smoke", trapTrigger: "delay" });
    const bare = { icon: { elements: [], segments: [] } } as unknown as Parameters<typeof fxSkillOf>[0];
    expect(fxSkillOf(bare)).toEqual({ element: null, zoneElement: null, surface: null, trapTrigger: null });
    expect(fxSkillsOf({ a: card })("a")).toBeDefined();
    expect(fxSkillsOf({ a: card })("b")).toBeUndefined();
  });
});
