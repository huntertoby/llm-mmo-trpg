// Phase 6C-ART3：事件卡圖示（docs/archive/art/Phase6剩餘美術移植需求.md 第 4 節）；QI-6 起畫法換成 Q 版第⑧批（`qIcon/event.ts`），
// 改到的項目在 docs/phases/PhaseQI-6報告.md 第 3 節逐項列舊 → 新。假 2D context 的紀錄含 Q 版圖樣另建的畫布（`setQCanvasFactory`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { AttrIcon, D20, MiscGlyph, SolutionGlyph } from "../world/StoryIcons";
import { DiceRoll } from "../world/StoryParts";
import { DICE_MS, OUTCOME_COLOR, type AttrKey, type SolutionIcon } from "../world/narration";
import { drawEventArt, SCENES, type EventArtId } from "./eventArt";
import { bubble } from "./eventArtParts";
import { setQCanvasFactory } from "./qIcon/core";
import * as QE from "./qIcon/event";
import {
  CHIP_BG,
  D20_COLOR,
  D20_FONT_PX,
  D20_HALO,
  D20_HALO_W,
  d20ShowsValue,
  drawStoryIcon,
  ringOf,
  storyIconCacheSize,
  storyIconKey,
  storyIconUrl,
  usedDieColor,
  type MiscIcon,
  type StoryIconSpec,
} from "./storyIconArt";

/** 記錄所有呼叫與屬性設定的假 Canvas 2D（`calls` 可以共用：Q 版圖樣另建的畫布也記進同一份）。 */
function mockCtx(calls: string[] = [], canvas: Record<string, unknown> = { width: 128, height: 128 }): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const store: Record<string, unknown> = { canvas };
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: () => undefined };
        if (prop === "measureText") return { width: String(args[0]).length * 13 };
        if (prop === "getImageData") return { data: new Uint8ClampedArray(0) };
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

/** Q 版圖樣另建的畫布：寫進目前這一次紀錄（`sink`）。 */
let sink: string[] = [];
beforeAll(() =>
  setQCanvasFactory((w, h) => {
    const cv: Record<string, unknown> = { width: w, height: h };
    const { ctx } = mockCtx(sink, cv);
    cv.getContext = () => ctx;
    return cv as unknown as HTMLCanvasElement;
  }),
);
afterAll(() => setQCanvasFactory(null));

const record = (spec: StoryIconSpec, size: number): string[] => {
  sink = [];
  const { ctx } = mockCtx(sink);
  drawStoryIcon(ctx, spec, size);
  return sink;
};

const SOLUTIONS: readonly SolutionIcon[] = ["combat", "persuade", "sneak", "investigate", "force", "chance", "leave", "trade"];
const MISCS: readonly MiscIcon[] = ["clue", "model_off", "narrator", "info", "thread"];
const ATTRS: readonly AttrKey[] = ["str", "dex", "con", "int", "wis", "wil"];
const html = (el: ReturnType<typeof createElement>): string => renderToStaticMarkup(el);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("每種圖示都有 Q 版畫法（QI-6）", () => {
  it("8 種選項、4＋1 種其他、6 屬性都有，外圈色照現行", () => {
    expect(QE.list("sol").map((e) => e.id).sort()).toEqual([...SOLUTIONS].sort());
    expect(QE.list("misc").map((e) => e.id).sort()).toEqual([...MISCS].sort());
    expect(QE.list("attr").map((e) => e.id).sort()).toEqual([...ATTRS].sort());
    expect(ringOf("combat")).toBe("#d0503a");
    expect(ringOf("sneak")).toBe("#8a7ab8");
    expect(ringOf("narrator")).toBe("#a898ff");
    expect(ringOf("int")).toBe("#7a8aff");
  });

  it("每個圖示：深底＋圖示色的圓環照現行，圖樣裁在圓環內緣、照原尺寸貼上（不縮放進 48 格）", () => {
    const specs: StoryIconSpec[] = [
      ...SOLUTIONS.map((icon): StoryIconSpec => ({ kind: "solution", icon })),
      ...MISCS.map((icon): StoryIconSpec => ({ kind: "misc", icon })),
      ...ATTRS.map((attr): StoryIconSpec => ({ kind: "attr", attr })),
    ];
    for (const spec of specs) {
      const ring = spec.kind === "solution" || spec.kind === "misc" ? ringOf(spec.icon) : spec.kind === "attr" ? ringOf(spec.attr) : "";
      for (const size of [18, 24]) {
        const calls = record(spec, size);
        const lw = Math.max(1.2, size * 0.06);
        expect(calls).toContain(`fillStyle=${CHIP_BG}`);
        expect(calls).toContain(`strokeStyle=${ring}`);
        expect(calls).toContain(`lineWidth=${lw}`);
        expect(calls).toContain(`arc(${(size / 2).toFixed(2)},${(size / 2).toFixed(2)},${(size / 2 - lw / 2).toFixed(2)},0.00,${(Math.PI * 2).toFixed(2)})`);
        expect(calls).toContain("clip()");
        expect(calls.some((c) => c.startsWith("drawImage(object,"))).toBe(true);
        expect(calls.filter((c) => c === "fill()").length).toBeGreaterThan(1);
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
      expect(out).toContain(`data-ring="${ringOf(icon)}"`);
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

describe("事件插圖小牌與泡泡換 Q 版（QI-6；舊：小牌的黑色圖示改淺色）", () => {
  /** 小牌（roundRect(8,8,…) 之後）那一段的紀錄；外層 ctx 沒有變換（假 ctx 的 getTransform 回 undefined → 每單位 1 裝置像素）。 */
  const badgeCalls = (scene: EventArtId): string[] => {
    sink = [];
    const { ctx } = mockCtx(sink);
    drawEventArt(ctx, scene, "cloud");
    let at = 0;
    sink.forEach((c, i) => {
      if (c.startsWith("roundRect(8.00,8.00,")) at = i;
    });
    return sink.slice(at);
  };

  it("小牌：Q 版圖樣中心 (21,20)、邊長 14，照原尺寸貼在整數像素，膠囊之後、標題字之前", () => {
    expect(SCENES.stele.icon).toBe("ask");
    expect(SCENES.villager.icon).toBe("bang");
    for (const scene of ["stele", "villager", "anomaly", "caravan"] as const) {
      const calls = badgeCalls(scene);
      const img = calls.findIndex((c) => c === "drawImage(object,14.00,13.00,14.00,14.00)");
      const text = calls.findIndex((c) => c.startsWith(`fillText(${SCENES[scene].zh},`));
      expect(img, scene).toBeGreaterThan(0);
      expect(text, scene).toBeGreaterThan(img);
    }
  });

  it("泡泡：驚嘆號、問號是近黑單色墨、不包外框；彩色的圖包 1px 外框（淺底）", () => {
    expect(QE.BU_INK).toBe("#16121a");
    for (const [icon, ow] of [["bang", 0], ["ask", 0], ["coin", 1], ["scroll", 1], ["sword", 1], ["rest", 1], ["portal", 1], ["notes", 1], ["warn", 1]] as const) expect(QE.BUBBLE[icon]?.ow, icon).toBe(ow);
    sink = [];
    const { ctx } = mockCtx(sink);
    bubble(ctx, 100, 60, "bang", "danger");
    expect(sink).toContain(`fillStyle=${QE.BU_INK}`);
    expect(sink).toContain("drawImage(object,93.00,38.00,14.00,14.00)");
    expect(sink).not.toContain("fillStyle=#f2e6c8");
  });
});

describe("6Q-1：64px d20 的點數描邊", () => {
  it("先描一圈 #fff8e8（線寬 3.5、字外 1.75；6N-4 改細），再寫深色字；平常、綠骰、紅骰、金骰、灰骰都一樣", () => {
    expect(D20_HALO).toBe("#fff8e8");
    expect(D20_HALO_W * 2).toBe(3.5);
    expect(D20_HALO_W).toBeLessThan(D20_FONT_PX * 0.2);
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
