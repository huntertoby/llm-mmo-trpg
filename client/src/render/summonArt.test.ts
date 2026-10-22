import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import { resolveDoll } from "./appearance";
import {
  drawSummonBody,
  hasNoRing,
  humanoidSpec,
  KEYWORD_COLOR,
  renderSummonCanvas,
  resolveSummonLook,
  SIZE_SCALE,
  summonKey,
  type SummonLookDraw,
} from "./summonArt";

/** 記錄所有呼叫的假 Canvas 2D：任何方法都可以呼叫、任何屬性都可以設定。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
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

const FACINGS: Facing[] = ["north", "east", "south", "west"];
const BODIES = ["humanoid", "spirit", "construct", "beast", "plant", "totem"];
const VARIANTS = ["skeleton", "shade", "afterimage", "guardian", "golem", "bomb", "wall", "wolf", "bird", "war", "pull", "plateau", "nope", "", null, undefined];
const ELEMENTS = [...Object.keys(KEYWORD_COLOR), "unknown_element", null, undefined];
const SIZES = ["small", "medium", "large", "huge", null, undefined];
const TRAITS = ["puddle", "shield", "translucent", "glow", "fuse", "flying", "aura", "no_ring", "ground", "weird", null, undefined];

describe("召喚物外觀渲染器", () => {
  it("全組合（含不認得的輸入）都解析得出來、畫得出來、不丟例外", () => {
    let count = 0;
    for (const body of [...BODIES, "dragon", "", "HUMANOID"]) {
      for (const variant of VARIANTS) {
        for (const element of ELEMENTS.filter((_, i) => i % 3 === 0)) {
          for (const size of SIZES.slice(1)) {
            for (const trait of TRAITS.slice(0, 2)) {
              const look = resolveSummonLook({ body, variant, element, size, trait } as SummonLookDraw);
              expect(SIZE_SCALE[look.size]).toBeGreaterThan(0);
              for (const facing of FACINGS) {
                const { ctx, calls } = mockCtx();
                expect(() => drawSummonBody(ctx, look, facing)).not.toThrow();
                if (look.body !== "humanoid") expect(calls.length).toBeGreaterThan(5);
                count++;
              }
            }
          }
        }
      }
    }
    expect(count).toBeGreaterThan(2000);
  }, 60_000);

  it("所有特徵（含不認得的）都不丟例外", () => {
    for (const trait of TRAITS) {
      for (const body of BODIES) {
        const look = resolveSummonLook({ body, trait });
        for (const facing of FACINGS) expect(() => drawSummonBody(mockCtx().ctx, look, facing)).not.toThrow();
      }
    }
  });

  it("不認得的體型退回人形骷髏；沒有外觀（null／undefined）也一樣", () => {
    for (const bad of [{ body: "dragon" }, { body: "" }, null, undefined]) {
      const look = resolveSummonLook(bad);
      expect(look).toMatchObject({ body: "humanoid", variant: "skeleton", size: "medium" });
      expect(look.element).toBeUndefined();
    }
  });

  it("不認得的款式、元素、大小各自退回預設", () => {
    expect(resolveSummonLook({ body: "beast", variant: "dragon" }).variant).toBe("wolf");
    expect(resolveSummonLook({ body: "construct", variant: "x" }).variant).toBe("golem");
    expect(resolveSummonLook({ body: "totem", variant: "x" }).variant).toBe("war");
    expect(resolveSummonLook({ body: "humanoid", variant: "x" }).variant).toBe("skeleton");
    expect(resolveSummonLook({ body: "spirit", element: "plasma" }).element).toBeUndefined();
    expect(resolveSummonLook({ body: "spirit", size: "gigantic" }).size).toBe("medium");
    expect(resolveSummonLook({ body: "spirit", element: "frozen", size: "large" })).toMatchObject({ element: "frozen", size: "large" });
  });

  it("四種元素靈的畫法不同（顏色與邊緣）", () => {
    const sig = (element: string, facing: Facing = "south"): string => {
      const { ctx, calls } = mockCtx();
      drawSummonBody(ctx, resolveSummonLook({ body: "spirit", element }), facing);
      return calls.join("|");
    };
    const all = ["ignite", "frozen", "charged", "wet"].map((e) => sig(e));
    expect(new Set(all).size).toBe(4);
  });

  it("背面不畫眼睛：漂浮靈、構造體、圖騰、狼", () => {
    const arcs = (body: string, variant: string | undefined, facing: Facing): number => {
      const { ctx, calls } = mockCtx();
      drawSummonBody(ctx, resolveSummonLook({ body, variant }), facing);
      return calls.length;
    };
    for (const [body, variant] of [["spirit", undefined], ["construct", "golem"], ["construct", "bomb"], ["totem", "war"], ["beast", "wolf"], ["beast", "bird"]] as const) {
      const front = arcs(body, variant, "south");
      const back = arcs(body, variant, "north");
      expect(front, `${body}/${variant}`).toBeGreaterThan(back);
    }
  });

  it("朝向：野獸朝西左右鏡像、朝南北沿用東邊的側面", () => {
    const run = (facing: Facing): string => {
      const { ctx, calls } = mockCtx();
      drawSummonBody(ctx, resolveSummonLook({ body: "beast", variant: "wolf" }), facing);
      return calls.join("|");
    };
    expect(run("west")).toContain("scale(-1.00,1.00)");
    expect(run("east")).toContain("scale(1.00,1.00)");
    expect(run("south")).toContain("scale(1.00,1.00)");
    expect(run("north")).toContain("scale(1.00,1.00)");
    expect(run("east")).not.toBe(run("west"));
  });

  it("鷹隼的身體抬高 22、影子留在地上；藤蔓貼地（沒有往上畫超過 22）", () => {
    const { ctx, calls } = mockCtx();
    drawSummonBody(ctx, resolveSummonLook({ body: "beast", variant: "bird", trait: "flying" }), "east");
    const shadowAt = calls.findIndex((c) => c.startsWith("ellipse(0.00,-1.00,7.00"));
    const liftAt = calls.indexOf("translate(0.00,-22.00)");
    expect(shadowAt).toBeGreaterThanOrEqual(0);
    expect(liftAt).toBeGreaterThan(shadowAt); // 影子先畫在地上，之後身體才抬高
    const vine = mockCtx();
    drawSummonBody(vine.ctx, resolveSummonLook({ body: "plant" }), "east");
    expect(vine.calls.some((c) => c.startsWith("translate(0.00,-22"))).toBe(false);
  });

  it("土牆沒有底圈，其他都有", () => {
    expect(hasNoRing(resolveSummonLook({ body: "construct", variant: "wall" }))).toBe(true);
    expect(hasNoRing(resolveSummonLook({ body: "construct", variant: "golem" }))).toBe(false);
    expect(hasNoRing(resolveSummonLook({ body: "humanoid" }))).toBe(false);
    expect(hasNoRing(resolveSummonLook(null))).toBe(false);
  });

  it("快取鍵：朝向、元素不同鍵不同；殘影另加召喚者外觀", () => {
    const a = resolveSummonLook({ body: "spirit", element: "ignite" });
    const b = resolveSummonLook({ body: "spirit", element: "frozen" });
    expect(summonKey(a, "south")).not.toBe(summonKey(b, "south"));
    expect(summonKey(a, "south")).not.toBe(summonKey(a, "north"));
    const ghost = resolveSummonLook({ body: "humanoid", variant: "afterimage" });
    expect(summonKey(ghost, "south", "x")).not.toBe(summonKey(ghost, "south", "y"));
    expect(summonKey(a, "south", "x")).toBe(summonKey(a, "south", "y")); // 非殘影不吃召喚者鍵
  });

  it("人形款式：影魅、守護靈、殘影、骷髏盾牌各有規格；殘影複製召喚者", () => {
    const skeleton = resolveDoll({ template: "summon_skeleton_warrior", team: "ally", summon: true });
    const hero = resolveDoll({ template: "hero_mage", team: "ally", summon: false });
    const spec = (look: SummonLookDraw, owner = hero) => humanoidSpec(resolveSummonLook(look), skeleton, owner);
    expect(spec({ body: "humanoid", variant: "shade" }).look.skin).not.toBe(skeleton.look.skin);
    expect(spec({ body: "humanoid", variant: "guardian" }).gear.off_hand?.kind).toBe("shield_round");
    expect(spec({ body: "humanoid", variant: "afterimage" })).toBe(hero);
    expect(humanoidSpec(resolveSummonLook({ body: "humanoid", variant: "afterimage" }), skeleton, null)).toBe(skeleton);
    expect(spec({ body: "humanoid", variant: "skeleton", trait: "shield" }).gear.off_hand?.kind).toBe("shield_round");
    expect(spec({ body: "humanoid", variant: "skeleton" })).toBe(skeleton);
  });

  it("沒有 DOM 時貼圖產生器回傳 null（不丟例外）", () => {
    for (const body of BODIES) {
      expect(renderSummonCanvas(resolveSummonLook({ body }), "south", null, 2)).toBeNull();
    }
  });
});
