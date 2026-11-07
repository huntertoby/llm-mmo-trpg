import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import { resolveDollT } from "./testDolls";
import { DOLL_FOOT_Y } from "./paperdoll";
import {
  copiesOwner,
  drawSummonBody,
  drawSummonGround,
  hasNoRing,
  humanoidSpec,
  humanoidStyle,
  SUMMON_KEYWORDS,
  renderSummonCanvas,
  resolveSummonLook,
  SIZE_SCALE,
  summonKey,
  type SummonLookDraw,
} from "./summonArt";
import { setDollSkin } from "./inkStyle";
import { afterEach as afterEachQ } from "vitest";

afterEachQ(() => setDollSkin("q"));

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
const ELEMENTS = [...SUMMON_KEYWORDS, "unknown_element", null, undefined];
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

  it("背面不畫眼睛：漂浮靈、構造體、圖騰（QK-3：Q 版方眼用 fillRect；野獸照樣張朝北用朝西的側面，看得到眼睛）", () => {
    const eyes = (body: string, variant: string | undefined, facing: Facing): number => {
      const { ctx, calls } = mockCtx();
      drawSummonBody(ctx, resolveSummonLook({ body, variant }), facing);
      return calls.filter((c) => c.startsWith("fillRect")).length;
    };
    for (const [body, variant] of [["spirit", undefined], ["construct", "golem"], ["construct", "bomb"], ["totem", "war"]] as const) {
      expect(eyes(body, variant, "south"), `${body}/${variant}`).toBeGreaterThan(0);
      expect(eyes(body, variant, "north"), `${body}/${variant}`).toBe(0);
    }
  });

  it("朝向：野獸朝西、朝北左右鏡像（QK-3 照樣張：朝南用朝東、朝北用朝西）", () => {
    const run = (facing: Facing): string => {
      const { ctx, calls } = mockCtx();
      drawSummonBody(ctx, resolveSummonLook({ body: "beast", variant: "wolf" }), facing);
      return calls.join("|");
    };
    expect(run("west")).toContain("scale(-1.00,1.00)");
    expect(run("east")).toContain("scale(1.00,1.00)");
    expect(run("south")).toContain("scale(1.00,1.00)");
    expect(run("north")).toContain("scale(-1.00,1.00)");
    expect(run("north")).toBe(run("west"));
    expect(run("east")).not.toBe(run("west"));
  });

  it("Q 畫風：影子是平塗深色橢圓、只由 drawSummonGround 畫", () => {
    for (const look of [
      { body: "spirit" }, { body: "construct", variant: "golem" }, { body: "construct", variant: "bomb" },
      { body: "construct", variant: "wall" }, { body: "beast", variant: "wolf" }, { body: "beast", variant: "bird" }, { body: "totem" }, { body: "plant" },
    ] as const) {
      const r = resolveSummonLook(look);
      const ground = mockCtx();
      drawSummonGround(ground.ctx, r);
      const SH = /^fillStyle=rgba\(10,8,14,/;
      expect(ground.calls.some((c) => SH.test(c)), look.body).toBe(look.body !== "plant"); // 藤蔓貼地、沒有影子
      expect(ground.calls.some((c) => c.startsWith("ellipse")), look.body).toBe(look.body !== "plant");
      const body = mockCtx();
      drawSummonBody(body.ctx, r, "south");
      expect(body.calls.some((c) => SH.test(c))).toBe(false); // 影子只在 ground 層
    }
    const human = mockCtx();
    drawSummonGround(human.ctx, resolveSummonLook({ body: "humanoid" }));
    expect(human.calls.length).toBe(0);
  });

  it("水精的水窪與圖騰的光環（QK-3：淡綠虛線、平塗不發光）在 ground 層；沒有特徵就沒有", () => {
    const puddle = mockCtx();
    drawSummonGround(puddle.ctx, resolveSummonLook({ body: "spirit", element: "wet", trait: "puddle" }));
    expect(puddle.calls.some((c) => c.includes("#4aa8ff"))).toBe(true);
    const plain = mockCtx();
    drawSummonGround(plain.ctx, resolveSummonLook({ body: "spirit", element: "wet" }));
    expect(plain.calls.some((c) => c.includes("#4aa8ff"))).toBe(false);
    const aura = mockCtx();
    drawSummonGround(aura.ctx, resolveSummonLook({ body: "totem", variant: "war", element: "summon", trait: "aura" }));
    expect(aura.calls).toContain("setLineDash(object)");
    expect(aura.calls.some((c) => c.startsWith("ellipse(0.00,0.00,22.9"))).toBe(true); // 樣張 17；戰場陣營底圈約 20.3 單位，光環放在它外面 2.6
    expect(aura.calls).toContain("strokeStyle=#7dffb0");
    const noAura = mockCtx();
    drawSummonGround(noAura.ctx, resolveSummonLook({ body: "totem", variant: "war", element: "summon" }));
    expect(noAura.calls).not.toContain("setLineDash(object)");
  });

  it("Q 版平塗、不發外光；同一個外觀每次畫出完全一樣（確定性）", () => {
    for (const [body, variant] of [["spirit", ""], ["construct", "golem"], ["beast", "wolf"], ["beast", "bird"], ["plant", ""], ["totem", "pull"]] as const) {
      const look = resolveSummonLook({ body, variant, element: "frozen" });
      const run = (): string => {
        const { ctx, calls } = mockCtx();
        drawSummonBody(ctx, look, "east");
        return calls.join("|");
      };
      const calls = run();
      expect(calls, body).toBe(run());
      expect(calls, body).not.toMatch(/shadowBlur=[1-9]/); // 外光只代表頭目
      expect(calls, body).not.toContain("strokeStyle=#2b1e16,"); // 不是 C 的墨線（縫線是本色加深）
    }
  });

  it("鷹隼的身體抬高 22；藤蔓貼地（沒有往上畫超過 22）", () => {
    const { ctx, calls } = mockCtx();
    drawSummonBody(ctx, resolveSummonLook({ body: "beast", variant: "bird", trait: "flying" }), "east");
    expect(calls.indexOf("translate(0.00,-22.00)")).toBeGreaterThanOrEqual(0);
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
    const skeleton = resolveDollT({ template: "summon_skeleton_warrior", team: "ally", summon: true });
    const hero = resolveDollT({ template: "hero_mage", team: "ally", summon: false });
    const spec = (look: SummonLookDraw, owner = hero) => humanoidSpec(resolveSummonLook(look), skeleton, owner);
    expect(spec({ body: "humanoid", variant: "shade" }).look.skin).not.toBe(skeleton.look.skin);
    expect(spec({ body: "humanoid", variant: "guardian" }).gear.off_hand?.kind).toBe("shield_kite"); // QK-3 照樣張 qSummon.js：鳶盾、板甲、頭盔
    expect(spec({ body: "humanoid", variant: "afterimage" })).toBe(hero);
    expect(humanoidSpec(resolveSummonLook({ body: "humanoid", variant: "afterimage" }), skeleton, null)).toBe(skeleton);
    expect(spec({ body: "humanoid", variant: "skeleton", trait: "shield" }).gear.off_hand?.kind).toBe("shield_round");
    expect(spec({ body: "humanoid", variant: "skeleton" })).toEqual({ ...skeleton, look: { ...skeleton.look, eyeStyle: "big" } }); // QK-3b：骷髏大眼
  });

  it("霧影（mist_shade，5F-ART1）：人形款式、複製召喚者、去掉外光；不認得的款式仍退回骷髏", () => {
    const shade = resolveSummonLook({ body: "humanoid", variant: "mist_shade" });
    expect(shade.variant).toBe("mist_shade");
    expect(resolveSummonLook({ body: "humanoid", variant: "mist_shadow_typo" }).variant).toBe("skeleton");
    expect(copiesOwner("mist_shade")).toBe(true);
    expect(copiesOwner("afterimage")).toBe(true);
    expect(copiesOwner("shade")).toBe(false);
    expect(copiesOwner(undefined)).toBe(false);
    expect(summonKey(shade, "south", "x")).not.toBe(summonKey(shade, "south", "y"));
    const skeleton = resolveDollT({ template: "summon_skeleton_warrior", team: "ally", summon: true });
    const owner = { ...resolveDollT({ template: "hero_mage", team: "enemy", summon: false }), rarity: "legendary" as const };
    const spec = humanoidSpec(shade, skeleton, owner);
    expect(spec.rarity).toBeUndefined();
    expect(spec.gear).toBe(owner.gear);
    expect(spec.look).toBe(owner.look);
    expect(humanoidSpec(shade, skeleton, null).look).toBe(skeleton.look);
  });

  it("霧影樣式：月白 #dfe4e2、0.55、不發光、腳下 14 單位漸隱、不畫影子；殘影、影魅、守護靈照樣張（半透明＋整隻染色，不發光）", () => {
    expect(humanoidStyle("mist_shade")).toEqual({ alpha: 0.55, tint: "#dfe4e2", t: 0.53, fade: 14, ground: false });
    expect(humanoidStyle("afterimage")).toEqual({ alpha: 0.55, tint: "#8fd0ff", t: 0.5, trail: true });
    expect(humanoidStyle("shade")).toEqual({ alpha: 0.74, tint: "#6a3aa8", t: 0.28 });
    expect(humanoidStyle("guardian")).toEqual({ alpha: 0.86, tint: "#fff2b0", t: 0.3 });
    for (const v of ["mist_shade", "afterimage", "shade", "guardian"]) expect(Object.keys(humanoidStyle(v)!)).not.toContain("glow");
  });

  it("霧影貼圖：destination-in 漸層從腳底往上 14 單位，沒有外光與影子；殘影有影子、身後一個淡影、不發光", () => {
    setDollSkin("c"); // QK-1：這一項數 C 畫法的畫布指令（Q 版的外框另開離屏畫布），鎖 C；afterEach 換回 Q
    const render = (variant: string) => {
      const canvases: string[][] = [];
      const fakeDoc = {
        createElement: () => {
          const { ctx, calls } = mockCtx();
          canvases.push(calls);
          return { width: 0, height: 0, getContext: () => ctx };
        },
      };
      const g = globalThis as { document?: unknown };
      const prev = g.document;
      g.document = fakeDoc;
      try {
        const look = resolveSummonLook({ body: "humanoid", variant });
        const owner = resolveDollT({ template: "hero_mage", team: "enemy", summon: false });
        renderSummonCanvas(look, "south", humanoidSpec(look, owner, owner), 2);
      } finally {
        g.document = prev;
      }
      return canvases.flat();
    };
    const SHADOW = "strokeStyle=rgba(43,30,22,0.5)";
    const mist = render("mist_shade");
    expect(mist).toContain("globalCompositeOperation=destination-in");
    expect(mist).toContain(`createLinearGradient(0.00,${(DOLL_FOOT_Y * 2).toFixed(2)},0.00,${((DOLL_FOOT_Y - 14) * 2).toFixed(2)})`);
    expect(mist).toContain("globalAlpha=0.55");
    expect(mist.some((c) => c.startsWith("shadowBlur="))).toBe(false);
    expect(mist).not.toContain(SHADOW);
    expect(mist).toContain("fillStyle=#dfe4e2");
    expect(mist).toContain("globalAlpha=0.53");
    const ghost = render("afterimage");
    expect(ghost.some((c) => c.startsWith("shadowBlur=") || c.startsWith("shadowColor="))).toBe(false);
    expect(ghost.some((c) => /^globalAlpha=0\.22/.test(c))).toBe(true); // 身後的淡影：0.55 × 0.4
    expect(ghost).toContain(SHADOW);
    expect(ghost).not.toContain("globalCompositeOperation=destination-in");
  });

  it("沒有 DOM 時貼圖產生器回傳 null（不丟例外）", () => {
    for (const body of BODIES) {
      expect(renderSummonCanvas(resolveSummonLook({ body }), "south", null, 2)).toBeNull();
    }
  });
});

// QK-3b（docs/art/QK-3檢查.md 小修 2～4）
describe("QK-3b：骷髏、影魅大眼；骷髏圓盾木色；守護靈拳頭跟著染色、不透明", () => {
  const skeleton = resolveDollT({ template: "summon_skeleton_warrior", team: "ally", summon: true });
  const spec = (look: SummonLookDraw) => humanoidSpec(resolveSummonLook(look), skeleton, null);
  it("骷髏戰士、影魅 eyeStyle big（樣張 HUMAN）", () => {
    expect(spec({ body: "humanoid", variant: "skeleton", trait: "shield" }).look.eyeStyle).toBe("big");
    expect(spec({ body: "humanoid", variant: "shade" }).look.eyeStyle).toBe("big");
  });

  it("骷髏圓盾木色 #7a5a3a", () => {
    expect(spec({ body: "humanoid", variant: "skeleton", trait: "shield" }).gear.off_hand).toMatchObject({ kind: "shield_round", color: "#7a5a3a" });
  });

    expect(g.gear.hands).toMatchObject({ kind: "gloves", color: g.gear.body?.color });
    expect(humanoidStyle("guardian")?.alpha).toBe(1);
  });
});
