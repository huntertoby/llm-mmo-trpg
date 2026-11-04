// Phase 6C-ART3：事件卡墨線圖示（docs/art/Phase6剩餘美術移植需求.md 第 4 節）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AttrIcon, D20, MiscGlyph, SolutionGlyph } from "../world/StoryIcons";
import { DiceRoll } from "../world/StoryParts";
import { DICE_MS, OUTCOME_COLOR, type AttrKey, type SolutionIcon } from "../world/narration";
import { drawEventArt, SCENES, type EventArtId } from "./eventArt";
import { BADGE_ICON_INK, ICON } from "./eventArtParts";
import {
  ATTR_ART,
  CHIP_BG,
  D20_COLOR,
  D20_FONT_PX,
  D20_HALO,
  D20_HALO_W,
  d20ShowsValue,
  drawStoryIcon,
  MISC_ART,
  SOLUTION_ART,
  storyIconCacheSize,
  storyIconKey,
  storyIconUrl,
  usedDieColor,
  type MiscIcon,
  type StoryIconSpec,
} from "./storyIconArt";

/** 記錄所有呼叫與屬性設定的假 Canvas 2D。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: () => undefined };
        if (prop === "measureText") return { width: String(args[0]).length * 13 };
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

const record = (spec: StoryIconSpec, size: number): string[] => {
  const { ctx, calls } = mockCtx();
  drawStoryIcon(ctx, spec, size);
  return calls;
};

const SOLUTIONS: readonly SolutionIcon[] = ["combat", "persuade", "sneak", "investigate", "force", "chance", "leave", "trade"];
const MISCS: readonly MiscIcon[] = ["clue", "model_off", "narrator", "info", "thread"];
const ATTRS: readonly AttrKey[] = ["str", "dex", "con", "int", "wis", "wil"];
const html = (el: ReturnType<typeof createElement>): string => renderToStaticMarkup(el);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("每種圖示都有墨線畫法", () => {
  it("8 種選項、4＋1 種其他、6 屬性都有，外圈色照樣張", () => {
    expect(Object.keys(SOLUTION_ART).sort()).toEqual([...SOLUTIONS].sort());
    expect(Object.keys(MISC_ART).sort()).toEqual([...MISCS].sort());
    expect(Object.keys(ATTR_ART).sort()).toEqual([...ATTRS].sort());
    expect(SOLUTION_ART.combat.ring).toBe("#d0503a");
    expect(SOLUTION_ART.sneak.ring).toBe("#8a7ab8");
    expect(MISC_ART.narrator.ring).toBe("#a898ff");
    expect(ATTR_ART.int.ring).toBe("#7a8aff");
  });

  it("每個圖示：深底＋圖示色的圓環，縮到 48 格裡畫墨線（有填色、有描線）", () => {
    const specs: StoryIconSpec[] = [
      ...SOLUTIONS.map((icon): StoryIconSpec => ({ kind: "solution", icon })),
      ...MISCS.map((icon): StoryIconSpec => ({ kind: "misc", icon })),
      ...ATTRS.map((attr): StoryIconSpec => ({ kind: "attr", attr })),
    ];
    for (const spec of specs) {
      const ring = spec.kind === "solution" ? SOLUTION_ART[spec.icon].ring : spec.kind === "misc" ? MISC_ART[spec.icon].ring : spec.kind === "attr" ? ATTR_ART[spec.attr].ring : "";
      for (const size of [18, 24]) {
        const calls = record(spec, size);
        expect(calls).toContain(`fillStyle=${CHIP_BG}`);
        expect(calls).toContain(`strokeStyle=${ring}`);
        expect(calls).toContain(`scale(${(size / 48).toFixed(2)},${(size / 48).toFixed(2)})`);
        expect(calls).toContain("clip()");
        expect(calls.filter((c) => c === "fill()").length).toBeGreaterThan(1);
        expect(calls.filter((c) => c === "stroke()").length).toBeGreaterThan(1);
      }
    }
  });

  it("確定性：同一個圖示每次畫出來都一樣", () => {
    expect(record({ kind: "solution", icon: "chance" }, 24)).toEqual(record({ kind: "solution", icon: "chance" }, 24));
    expect(record({ kind: "d20", value: 15 }, 64)).toEqual(record({ kind: "d20", value: 15 }, 64));
  });
});

describe("d20", () => {
  it("64px 寫點數，28px 以下不寫字、也沒有外圈", () => {
    expect(d20ShowsValue(64)).toBe(true);
    expect(d20ShowsValue(28)).toBe(false);
    const big = record({ kind: "d20", value: 15 }, 64);
    expect(big.some((c) => c.startsWith("fillText(15,"))).toBe(true);
    for (const size of [16, 20, 24, 28]) {
      const small = record({ kind: "d20", value: 15 }, size);
      expect(small.some((c) => c.startsWith("fillText"))).toBe(false);
      expect(small).not.toContain(`fillStyle=${CHIP_BG}`);
    }
  });

  it("小 d20 不寫字，點數不進快取鍵（同一張圖）", () => {
    expect(storyIconKey({ kind: "d20", value: 3 }, 24)).toBe(storyIconKey({ kind: "d20", value: 17 }, 24));
    expect(storyIconKey({ kind: "d20", value: 3 }, 64)).not.toBe(storyIconKey({ kind: "d20", value: 17 }, 64));
  });

  it("大成功（自然 20）金、大失敗（自然 1）灰，其他照結果色", () => {
    expect(usedDieColor(20, OUTCOME_COLOR.success)).toBe(D20_COLOR.crit);
    expect(usedDieColor(1, OUTCOME_COLOR.failure)).toBe(D20_COLOR.fumble);
    expect(usedDieColor(12, OUTCOME_COLOR.partial)).toBe(OUTCOME_COLOR.partial);
    expect(D20_COLOR.crit).toBe("#ffe08a");
    expect(D20_COLOR.fumble).toBe("#c8c0b8");
    expect(record({ kind: "d20", value: 20, color: D20_COLOR.crit }, 64)).toContain(`fillStyle=${D20_COLOR.crit}`);
  });

  it("元件：DC 旁的小 d20 不寫字", () => {
    const out = html(createElement(D20, { size: 24, value: 13 }));
    expect(out).toContain('data-value=""');
    expect(out).toContain('class="story-d20"');
    expect(html(createElement(D20, { size: 64, value: 13 }))).toContain('data-value="13"');
  });
});

describe("擲骰動畫（64px；翻滾不寫字，停下才寫點數）", () => {
  it("翻滾中兩顆都不寫字、都是平常色；停下寫點數", () => {
    const mid = html(createElement(DiceRoll, { dice: [3, 15], roll: 15, outcome: "success", elapsed: 100 }));
    expect(mid).toContain('data-done="0"');
    expect(mid.match(/data-value=""/g)?.length).toBe(2);
    expect(mid).toContain('width:64px');
    expect(mid).not.toContain(`data-color="${OUTCOME_COLOR.success}"`);
    const end = html(createElement(DiceRoll, { dice: [3, 15], roll: 15, outcome: "success", elapsed: DICE_MS }));
    expect(end).toContain('data-value="3"');
    expect(end).toContain('data-value="15"');
    expect(end).toContain(`data-color="${OUTCOME_COLOR.success}"`);
  });

  it("用的那顆是自然 20 → 金；自然 1 → 灰", () => {
    expect(html(createElement(DiceRoll, { dice: [20, 4], roll: 20, outcome: "success", elapsed: DICE_MS }))).toContain(`data-color="${D20_COLOR.crit}"`);
    expect(html(createElement(DiceRoll, { dice: [1, 4], roll: 1, outcome: "failure", elapsed: DICE_MS }))).toContain(`data-color="${D20_COLOR.fumble}"`);
  });
});

describe("元件介面不變", () => {
  it("沒有 DOM 時留同大小的框，帶圖示鍵與外圈色", () => {
    for (const icon of SOLUTIONS) {
      const out = html(createElement(SolutionGlyph, { icon, size: 24 }));
      expect(out).toContain(`data-icon="${icon}"`);
      expect(out).toContain(`data-ring="${SOLUTION_ART[icon].ring}"`);
      expect(out).toContain("width:24px");
    }
    for (const icon of MISCS) expect(html(createElement(MiscGlyph, { icon }))).toContain(`data-icon="${icon}"`);
    for (const attr of ATTRS) expect(html(createElement(AttrIcon, { attr, size: 18 }))).toContain(`data-attr="${attr}"`);
  });

  it("有 DOM 時是離屏畫好的圖片，同一圖示同一大小只畫一次", () => {
    let made = 0;
    vi.stubGlobal("document", {
      createElement: () => {
        made += 1;
        return { width: 0, height: 0, getContext: () => mockCtx().ctx, toDataURL: () => `data:image/png;base64,ICON${made}` };
      },
    });
    const before = storyIconCacheSize();
    const a = storyIconUrl({ kind: "solution", icon: "sneak" }, 18);
    expect(storyIconUrl({ kind: "solution", icon: "sneak" }, 18)).toBe(a);
    expect(storyIconUrl({ kind: "solution", icon: "sneak" }, 24)).not.toBe(a);
    expect(made).toBe(2);
    expect(storyIconCacheSize()).toBe(before + 2);
    const out = html(createElement(SolutionGlyph, { icon: "sneak", size: 18 }));
    expect(out).toContain("<img");
    expect(out).toContain(`src="${a}"`);
    expect(out).toContain('data-icon="sneak"');
  });
});

describe("事件插圖小牌：黑色圖示改淺色，彩色不動", () => {
  const badgeCalls = (scene: EventArtId): string[] => {
    const { ctx, calls } = mockCtx();
    drawEventArt(ctx, scene, "cloud");
    let at = 0;
    calls.forEach((c, i) => {
      if (c.startsWith("roundRect(8.00,8.00,")) at = i;
    });
    return calls.slice(at);
  };

  it("古碑（問號）、村民求助（驚嘆號）用 #f2e6c8", () => {
    expect(BADGE_ICON_INK).toBe("#f2e6c8");
    expect(SCENES.stele.icon).toBe("ask");
    expect(SCENES.villager.icon).toBe("bang");
    const stele = badgeCalls("stele");
    expect(stele).toContain(`strokeStyle=${BADGE_ICON_INK}`);
    expect(stele).not.toContain("strokeStyle=#1c1712");
    const villager = badgeCalls("villager");
    const fills = villager.filter((c) => c.startsWith("fillStyle="));
    expect(fills[0]).toBe(`fillStyle=${BADGE_ICON_INK}`); // 驚嘆號（之後才是小牌文字）
    expect(villager.filter((c) => c.startsWith("fillRect(")).length).toBe(2);
  });

  it("泡泡裡的問號、驚嘆號仍是黑色；彩色圖示照原色", () => {
    const { ctx, calls } = mockCtx();
    ICON.bang(ctx, 0, 0, 10);
    ICON.ask(ctx, 0, 0, 10);
    expect(calls).not.toContain(`fillStyle=${BADGE_ICON_INK}`);
    expect(calls).not.toContain(`strokeStyle=${BADGE_ICON_INK}`);
    const coin = mockCtx();
    ICON.coin(coin.ctx, 0, 0, 10, BADGE_ICON_INK);
    expect(coin.calls).not.toContain(`fillStyle=${BADGE_ICON_INK}`);
    expect(coin.calls).toContain("fillStyle=#e8bb48");
  });
});

describe("6Q-1：64px d20 的點數描邊", () => {
  it("先描一圈 #fff8e8（字外約字高 0.2 倍），再寫深色字；平常、綠骰、紅骰、金骰、灰骰都一樣", () => {
    expect(D20_HALO).toBe("#fff8e8");
    expect(D20_HALO_W).toBeCloseTo(D20_FONT_PX * 0.2, 9);
    for (const color of [undefined, OUTCOME_COLOR.success, OUTCOME_COLOR.failure, OUTCOME_COLOR.partial, D20_COLOR.crit, D20_COLOR.fumble]) {
      const calls = record({ kind: "d20", value: 17, color }, 64);
      const stroke = calls.findIndex((c) => c.startsWith("strokeText(17,"));
      const fill = calls.findIndex((c) => c.startsWith("fillText(17,"));
      expect(stroke, String(color)).toBeGreaterThanOrEqual(0);
      expect(fill).toBeGreaterThan(stroke);
      const before = calls.slice(0, stroke);
      expect(before.filter((c) => c.startsWith("strokeStyle=")).at(-1)).toBe(`strokeStyle=${D20_HALO}`);
      expect(before.filter((c) => c.startsWith("lineWidth=")).at(-1)).toBe(`lineWidth=${D20_HALO_W * 2}`);
      expect(calls.slice(stroke, fill).filter((c) => c.startsWith("fillStyle=")).at(-1)).not.toBe(`fillStyle=${D20_HALO}`);
    }
  });

  it("小 d20 不寫字，也沒有描邊", () => {
    for (const size of [16, 20, 24, 28]) expect(record({ kind: "d20", value: 17 }, size).some((c) => c.startsWith("strokeText"))).toBe(false);
  });
});
