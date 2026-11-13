// KW-3：四個層數關鍵字（連擊、怒氣、專注、氣；#161）的前端與美術移植（規格 docs/phases/PhaseKW計畫.md KW-3；美術 docs/art/KW樣張.md 第 1～7 節、第 9 節）。
// 1. 圓章圖樣與色（keywords.ts 的 LIST、palette.ts 的 KEYWORD_COLOR）；2. 裝備不帶這四個（gearResolve、gemAccent、keywords.known）；
// 3. 創角圖示（CreateIcons.tsx）；4. HUD 層數計量（stackGauge.ts、StackPips.tsx、statusCard.hudStacks：0 層規則）；5. 條件部件「層數達 N」。
// 逐像素指紋（docs/art/KW樣張.md 第 7 節）在開發頁 `/dev/keyword-gallery.html?set=hash` 比，報告附結果（vitest 沒有真畫布）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { parse } from "yaml";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import stacksYaml from "../../../../content/stacks.yaml?raw";
import appearance from "../gearAppearance.json";
import type { SkillCard } from "../../api/types";
import { smallView, unit } from "../../battle/testFixtures";
import { gearKeywordLine } from "../../gear/gearKeywords";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { KEYWORD_ICON_COLOR, KEYWORD_ICON_IDS, KeywordIcon } from "../../ui/CreateIcons";
import { Hud } from "../../ui/Hud";
import { hudStacks } from "../../ui/statusCard";
import { resolveGear } from "../gearResolve";
import { KEYWORD_COLOR, STACK_KEYWORDS } from "../palette";
import { gemAccent, mix, OUT, setQCanvasFactory, type QOpts } from "./core";
import * as K from "./keywords";
import * as QP from "./parts";
import * as G from "./stackGauge";

const STACK = ["combo_point", "fury", "focus", "ki"] as const;
const log: FakeCanvasLog = { calls: null };
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => setQCanvasFactory(null));
function sig(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  log.calls = [];
  fn(fakeCtx(log));
  const out = log.calls;
  log.calls = null;
  return out;
}
const O = (tiny: boolean): QOpts => ({ small: tiny, tiny, owPx: 0, badge: false, u: 1 });

describe("1. 圓章圖樣與色（A 案、推薦色組）", () => {
  it("KEYWORD_COLOR 末尾四筆＝美術第 6 節；前 12 個順序不變；STACK_KEYWORDS 是這四個", () => {
    expect(Object.keys(KEYWORD_COLOR)).toEqual([...(appearance.keywords as string[]), ...STACK]);
    expect(STACK.map((k) => KEYWORD_COLOR[k])).toEqual(["#ff3d8b", "#df2046", "#476deb", "#29e0bc"]);
    expect([...STACK_KEYWORDS].sort()).toEqual([...STACK].sort());
  });
  it("LIST 四筆：k 照樣張 CAND.a（0.96／0.84／0.8／0.92），三階色照 TONE", () => {
    expect(STACK.map((k) => K.LIST[k]!.k)).toEqual([0.96, 0.84, 0.8, 0.92]);
    expect(STACK.map((k) => K.LIST[k]!.zh)).toEqual(["連擊", "怒氣", "專注", "氣"]);
    expect(K.KW_TONE["fury"]).toEqual(["#df2046", "#ff7a8c", "#fff0c8"]);
  });
  it("每個圖樣大小兩種（tiny／一般）都畫得出來、彼此不同；氣 ≤14px 用深半邊 #0e7f6a、沒有勾玉眼", () => {
    for (const kw of STACK) {
      const a = sig((c) => K.LIST[kw]!.d(c, O(false))), b = sig((c) => K.LIST[kw]!.d(c, O(true)));
      expect(a.length, kw).toBeGreaterThan(0);
      expect(a, kw).not.toEqual(b);
    }
    const tiny = sig((c) => K.LIST["ki"]!.d(c, O(true))), big = sig((c) => K.LIST["ki"]!.d(c, O(false)));
    expect(tiny).toContain("fillStyle=#0e7f6a");
    expect(big).not.toContain("fillStyle=#0e7f6a");
    expect(tiny.filter((s) => s.startsWith("arc(")).length).toBeLessThan(big.filter((s) => s.startsWith("arc(")).length);
  });
  it("圓章底＝mix(關鍵字色, #191b22, 0.72)、外圈外框色", () => {
    for (const kw of STACK) {
      const calls = sig((c) => K.chip(c, kw, 0, 0, 20, 1));
      expect(calls.indexOf(`fillStyle=${OUT}`), kw).toBeLessThan(calls.indexOf(`fillStyle=${mix(KEYWORD_COLOR[kw]!, "#191b22", 0.72)}`));
    }
  });
});

describe("2. 裝備不帶層數關鍵字（KEYWORD_COLOR 認得它們之後要擋住）", () => {
  it("resolveGear 丟掉四個層數關鍵字，其他照舊（最多 2 個）", () => {
    expect(resolveGear({ kind: "sword", keywords: ["combo_point", "ignite", "fury", "marked"] }).keywords).toEqual(["ignite", "marked"]);
    for (const kw of STACK) expect(resolveGear({ kind: "ring", form: "gem", keywords: [kw] }).keywords, kw).toEqual([]);
  });
  it("寶石色不取層數關鍵字；說明框沒有「關鍵字」行；keywords.paint 不畫", () => {
    for (const kw of STACK) {
      expect(gemAccent([kw], "gold"), kw).toBe("#e04060");
      expect(gemAccent([kw], "crystal"), kw).toBe("#b8a8ff");
      expect(gemAccent([kw, "prone"], "gold"), kw).toBe(KEYWORD_COLOR["prone"]);
      expect(gearKeywordLine({ kind: "sword", keywords: [kw] }), kw).toBeNull();
      expect(K.known([kw, "ignite"])).toEqual(["ignite"]);
      expect(sig((c) => K.paint(c, [kw], 48, 2)), kw).toEqual([]);
    }
  });
  it("gearAppearance.json 的 keywords 沒有它們（後端 test_gear_never_carries_stack_keywords 鎖內容那一半）", () => {
    for (const kw of STACK) expect(appearance.keywords as string[]).not.toContain(kw);
  });
});

describe("3. 創角圖示（15px，A 案；怒氣亮一階 #ff4a62，其他和圓章同色）", () => {
  it("KEYWORD_ICON_IDS 16 個；四個新色", () => {
    expect(KEYWORD_ICON_IDS).toHaveLength(16);
    expect(STACK.map((k) => KEYWORD_ICON_COLOR[k])).toEqual(["#ff3d8b", "#ff4a62", "#476deb", "#29e0bc"]);
  });
  it("四個都有專屬圖樣（不是預設圓點）、預設 15px、彼此不同", () => {
    const svgs = STACK.map((id) => renderToStaticMarkup(createElement(KeywordIcon, { id })));
    for (const s of svgs) {
      expect(s).toContain('width="15"');
      expect(s).not.toContain('r="3.5"');
    }
    expect(new Set(svgs.map((s) => s.replace(/data-keyword-icon="[^"]+"/, ""))).size).toBe(4);
    expect(svgs[0]).toContain('fill-opacity="0.7"');
    expect(svgs[1]).toContain('fill-rule="evenodd"');
  });
});

describe("4. HUD 層數計量（A 案：格 6、步距 7、右內距 5）", () => {
  it("格數＝content/stacks.yaml 的上限", () => {
    const max = Object.fromEntries((parse(stacksYaml) as { stacks: { id: string; max: number }[] }).stacks.map((s) => [s.id, s.max]));
    for (const kw of STACK) expect(G.GAUGE_MAX[kw], kw).toBe(max[kw]);
  });
  it("含膠囊外寬：連擊 60、怒氣 53、專注與氣 46（≤60）；畫布四邊多 4px", () => {
    expect(STACK.map((k) => G.gaugeOuter(k))).toEqual([60, 53, 46, 46]);
    expect(G.gaugeBox("combo_point")).toEqual({ w: 68, h: 30 });
  });
  it("亮格本色：怒氣 #ff4a62、其他同關鍵字色；滿層才有外暈與關鍵字色框", () => {
    const mid = sig((c) => G.gauge(c, "fury", 2, 4, 4, 1)), full = sig((c) => G.gauge(c, "fury", 4, 4, 4, 1));
    expect(mid).toContain("fillStyle=#ff4a62");
    expect(mid.some((s) => s.startsWith("shadowBlur="))).toBe(false);
    expect(full.some((s) => s.startsWith("shadowBlur="))).toBe(true);
    expect(full).toContain(`fillStyle=${mix("#ff4a62", "#ffffff", 0.28)}`);
    const ki = sig((c) => G.gauge(c, "ki", 1, 4, 4, 1));
    expect(ki).toContain("fillStyle=#29e0bc");
  });
  const card = (id: string, stack: string, role: "makes" | "uses"): SkillCard => ({ id, name_zh: id, stacks: [{ id: stack, name_zh: stack, role }] }) as unknown as SkillCard;
  const cards = { s_make: card("s_make", "combo_point", "makes"), s_use: card("s_use", "fury", "uses"), s_other: card("s_other", "static_charge", "makes") };
  it("0 層：有會累積或消耗它的技能才顯示空格；沒有就不顯示；其他層數照舊（>0 才列、不是計量）", () => {
    const hero = unit("u1", "ally", 0, 0, { skills: ["s_make", "s_use", "s_other"], stacks: { static_charge: 2 } });
    expect(hudStacks(hero, cards)).toEqual([
      { id: "combo_point", count: 0, gauge: true },
      { id: "fury", count: 0, gauge: true },
      { id: "static_charge", count: 2, gauge: false },
    ]);
    const bare = unit("u2", "ally", 0, 0, { skills: [], stacks: { ki: 1 } });
    expect(hudStacks(bare, cards)).toEqual([{ id: "ki", count: 1, gauge: true }]);
    expect(hudStacks(unit("u3", "ally", 0, 0, { skills: ["s_other"], stacks: {} }), cards)).toEqual([]);
  });
  it("Hud：四種層數畫成 StackPips（沒有右下角數字），其他層數照舊 StackBadge", () => {
    const hero = unit("unit_0001", "ally", 0, 2, { name_zh: "主角", skills: ["s_make"], stacks: { fury: 4, static_charge: 1 } });
    const html = renderToStaticMarkup(createElement(Hud, { view: { ...smallView(), units: [hero] }, hero, skills: {}, cards }));
    expect(html).toMatch(/class="stack-pips" data-stack="combo_point" data-count="0"/);
    expect(html).toMatch(/class="stack-pips full" data-stack="fury" data-count="4"/);
    expect(html).toContain('data-stack="static_charge"');
    expect(html).not.toMatch(/stack-badge" data-stack="(combo_point|fury|focus|ki)"/);
    expect(html).toMatch(/<canvas width="136" height="60" style="width:68px;height:30px"/);
  });
});

describe("5. 條件部件「層數達 N」：A 案取代暫代的「第一輪」", () => {
  it("不再呼叫 first_round；畫三個金格（#e8bb48）＋米白小人形", () => {
    const e = QP.entry("condition", "self_stack_at_least");
    expect(e.topic).not.toContain("暫代");
    for (const tiny of [false, true]) {
      const calls = sig((c) => e.d(c, O(tiny)));
      expect(calls).not.toEqual(sig((c) => QP.entry("condition", "first_round").d(c, O(tiny))));
      expect(calls.filter((s) => s === "fillStyle=#e8bb48")).toHaveLength(3);
    }
  });
});
