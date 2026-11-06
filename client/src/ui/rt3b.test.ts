// RT-3b（docs/archive/art/RT-3檢查.md）：判定等待不再把事件卡撐高（卡片內容捲動、下緣角飾與漸隱、自動捲到等待區）、
// 失敗時自動捲到重試鈕、設定面板上緣漸隱加深加高、「請稍候」彈窗不透明、開發頁 NPC 完成＝直接顯示文字、
// 封蠟改成不規則蠟緣＋壓印紋（確定性）、沙漏翻轉收在羊皮紙裡。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import {
  drawWait,
  hourglassExtent,
  hourglassFlipScale,
  HOURGLASS_HALF,
  JUDGE_PARCH,
  SEAL_EDGE,
  SEAL_EDGE_POINTS,
  sealOutline,
  waitPalette,
  type WaitFrame,
  type WaitStatus,
} from "../render/waitArt";
import { readSources, readStyleFiles, stripCssComments, stripTsComments } from "../test/sourceScan";
import { regionThemeFor } from "./regionTheme";
import { REVEAL_MARGIN, revealDelta, revealInScroller, scrollerOf } from "./scrollReveal";
import { npcDoneShowsText, WaitScene } from "./WaitScene";
import { WAIT_SCENES, waitSeed, type WaitSceneId } from "./waitNarration";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
const css = (p: string): string => styles[p] ?? "";
/** 某個選擇器（可以是選擇器清單裡的一個）的規則內容。 */
function ruleOf(file: string, selector: string): string {
  const text = css(file);
  const re = /([^{}]+)\{([^}]*)\}/g;
  let out = "";
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    const sels = m[1]!.split(",").map((s) => s.trim());
    if (sels.includes(selector)) out += m[2]!;
  }
  return out;
}

/** 記錄所有呼叫的假 Canvas 2D。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: () => undefined };
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
const frame = (scene: WaitSceneId, t: number, over: Partial<WaitFrame> = {}): WaitFrame => ({
  scene,
  t,
  seed: waitSeed("rt3b"),
  palette: waitPalette(regionThemeFor("capital")),
  reduced: false,
  status: "wait",
  ...over,
});
const record = (f: WaitFrame): string[] => {
  const { ctx, calls } = mockCtx();
  drawWait(ctx, f);
  return calls;
};

describe("必修 1、2：自動捲進可視範圍（等待區、重試鈕）", () => {
  const view = { top: 100, bottom: 500 };
  it("已經看得見：不捲；上下各讓出漸隱的高度", () => {
    expect(REVEAL_MARGIN).toBeGreaterThanOrEqual(32); // 下緣漸隱 32px
    expect(revealDelta(view, { top: 200, bottom: 300 })).toBe(0);
  });
  it("在下面（例如重試鈕被下緣漸隱切掉一半）：往下捲到完整露出、離下緣留 margin", () => {
    const d = revealDelta(view, { top: 440, bottom: 480 });
    expect(d).toBe(480 - (500 - REVEAL_MARGIN));
    expect(480 - d).toBeLessThanOrEqual(500 - REVEAL_MARGIN);
    expect(revealDelta(view, { top: 700, bottom: 780 })).toBe(780 - 460);
  });
  it("在上面：往上捲", () => {
    expect(revealDelta(view, { top: 50, bottom: 90 })).toBe(50 - 140);
  });
  it("比可視範圍高：對齊上緣（先看到沙漏）", () => {
    expect(revealDelta(view, { top: 600, bottom: 1200 })).toBe(600 - 140);
  });
  describe("只捲最近的捲動區（不用 scrollIntoView）", () => {
    const g = globalThis as { getComputedStyle?: unknown };
    const orig = g.getComputedStyle;
    afterEach(() => {
      g.getComputedStyle = orig;
    });
    it("找到 overflow-y: auto 的祖先，改它的 scrollTop；`until`（擲骰那一列）一起帶進來", () => {
      const rect = (top: number, bottom: number) => () => ({ top, bottom });
      const stage = { parentElement: null, overflowY: "hidden", scrollTop: 0, getBoundingClientRect: rect(0, 900) };
      const body = { parentElement: stage, overflowY: "auto", scrollTop: 10, getBoundingClientRect: rect(100, 500) };
      const wrap = { parentElement: body, overflowY: "visible", getBoundingClientRect: rect(0, 0) };
      const wait = { parentElement: wrap, getBoundingClientRect: rect(380, 460) };
      const row = { getBoundingClientRect: rect(560, 590) };
      g.getComputedStyle = (e: { overflowY?: string }) => ({ overflowY: e.overflowY ?? "visible" });
      expect(scrollerOf(wait as unknown as Element)).toBe(body);
      const d = revealInScroller(wait as unknown as Element, row as unknown as Element);
      expect(d).toBe(590 - (500 - REVEAL_MARGIN));
      expect(body.scrollTop).toBe(10 + d);
      expect(stage.scrollTop).toBe(0); // 外層舞台不動
      expect(revealInScroller({ parentElement: null } as unknown as Element)).toBe(0);
    });
  });
  it("WaitScene 出現、失敗時捲進可視範圍；判定帶上「擲骰」那一列；NPC 面板的 hook 在提早 return 之前", () => {
    const ws = sources["ui/WaitScene.tsx"] ?? "";
    expect(ws).toMatch(/useEffect\(\(\) => \{\s*if \(!reveal \|\| status === "done"\) return undefined;[\s\S]*revealInScroller\(root\.current, revealUntil\?\.current \?\? null\)[\s\S]*\}, \[reveal, status, revealUntil\]\)/);
    expect(ws).not.toContain("scrollIntoView");
    const ev = sources["world/EventCard.tsx"] ?? "";
    expect(ev).toContain('<div className="run-actions" ref={actions}>');
    expect(ev).toMatch(/<WaitScene scene="judge"[^>]*revealUntil=\{actions\}/);
    const npc = sources["world/NpcPanel.tsx"] ?? "";
    expect(npc.indexOf("const [waiting, setWaiting]")).toBeGreaterThan(0);
    expect(npc.indexOf("const [waiting, setWaiting]")).toBeLessThan(npc.indexOf("return null;"));
    expect(npc).toMatch(/<WaitScene\s+scene="npc"[\s\S]*?onRetry=/);
  });
});

describe("必修 1：事件卡內容捲動，外框（四角飾件）整張留在欄裡", () => {
  it("欄裡的事件卡是直的 flex、可以縮；內容在 .ui-popup-body 裡捲", () => {
    const card = ruleOf("styles/theme.css", ".world-hud-center > .world-event.ui-popup-inline");
    expect(card).toContain("display: flex");
    expect(card).toContain("flex-direction: column");
    expect(card).toContain("min-height: 0");
    expect(card).toContain("overflow: hidden");
    const body = ruleOf("styles/theme.css", ".world-hud-center > .world-event > .ui-popup-body");
    expect(body).toContain("overflow-y: auto");
    expect(body).toContain("min-height: 0");
    expect(css("styles/world-hud.css")).toMatch(/\.world-hud-center \{[^}]*display: flex;[^}]*flex-direction: column;/);
    expect(sources["world/WorldHud.tsx"]).toMatch(/className="world-hud-center" style=\{popupStyle\(popupBox\(/); // 欄有 max-height
  });
  it("上下漸隱：下緣 sticky 32px（後 55% 實色）、上緣捲下去才出現", () => {
    const after = ruleOf("styles/theme.css", ".world-hud-center > .world-event > .ui-popup-body::after");
    expect(after).toContain("position: sticky");
    expect(after).toContain("bottom: 0");
    expect(after).toContain("height: 32px");
    expect(after).toMatch(/var\(--ui-navy\) 45%/);
    const before = ruleOf("styles/theme.css", ".world-hud-center > .world-event > .ui-popup-body::before");
    expect(before).toContain("position: sticky");
    expect(before).toContain("opacity: 0");
    expect(ruleOf("styles/theme.css", '.world-hud-center > .world-event > .ui-popup-body[data-scrolled="1"]::before')).toContain("opacity: 1");
  });
  it("事件卡左右內距讓開四角飾件（捲動內容不壓到飾件）", () => {
    expect(ruleOf("styles/theme.css", ".ui-popup-inline")).toContain("padding: 10px 20px");
  });
});

describe("必修 3：設定面板上緣漸隱加深加高", () => {
  it("56px、上方實色（6F-8 起 70%，見 fix6f8.test.ts）；z-index 蓋得住勾選框", () => {
    const r = ruleOf("styles/theme.css", ".ui-popup-hud > .ui-popup-body::before");
    expect(r).toContain("height: 56px");
    expect(r).toContain("margin-bottom: -56px");
    expect(r).toMatch(/linear-gradient\(0deg, rgb\(30 34 54 \/ 0%\), rgb\(30 34 54 \/ 70%\) 15%, var\(--ui-navy\) 30%, var\(--ui-navy\)\)/);
    const solid = 56 * 0.7;
    expect(solid).toBeGreaterThanOrEqual(33);
    expect(Number(/z-index: (\d+)/.exec(r)?.[1] ?? 0)).toBeGreaterThanOrEqual(5);
  });
});

describe("必修 4：「請稍候」彈窗不透明（≥ 0.96）", () => {
  const alphaOf = (color: string): number => {
    if (/^#[0-9a-f]{6}$/i.test(color)) return 1;
    const m = /\/\s*(\d+)%\)/.exec(color);
    return m === null ? 1 : Number(m[1]) / 100;
  };
  it("大世界的詢問視窗（DialogFrame → world-hud-dialog）底色是實色 --ui-navy", () => {
    const r = ruleOf("styles/world-hud.css", ".ui-popup.world-hud-dialog");
    expect(r).toContain("background: var(--ui-navy)");
    const navy = /--ui-navy:\s*([^;]+);/.exec(css("styles/theme.css"))?.[1]?.trim() ?? "";
    expect(alphaOf(navy)).toBeGreaterThanOrEqual(0.96);
    expect(alphaOf(navy)).toBe(1);
    expect(sources["ui/DialogFrame.tsx"]).toContain('" world-hud-dialog"');
    expect(sources["world/PregenWaitDialog.tsx"]).toContain('<DialogFrame label={text} title="請稍候">');
  });
});

describe("必修 5：NPC 聊天的「完成」＝泡泡消失、直接顯示文字", () => {
  it("只有 npc＋done 是純文字；其他場合完成時照舊有畫布", () => {
    expect(npcDoneShowsText("npc", "done")).toBe(true);
    for (const s of WAIT_SCENES) for (const st of ["wait", "fail"] as WaitStatus[]) expect(npcDoneShowsText(s, st)).toBe(false);
    for (const s of WAIT_SCENES.filter((x) => x !== "npc")) expect(npcDoneShowsText(s, "done")).toBe(false);
  });
  it("元件：沒有畫布、沒有泡泡，直接是回覆文字", () => {
    const html = renderToStaticMarkup(createElement(WaitScene, { scene: "npc", requestId: "r", status: "done", doneText: "葛蘭：河上起霧了。", reveal: false }));
    expect(html).not.toContain("<canvas");
    expect(html).toContain("葛蘭：河上起霧了。");
    expect(html).toContain('data-status="done"');
    const wait = renderToStaticMarkup(createElement(WaitScene, { scene: "npc", requestId: "r", status: "wait", reveal: false }));
    expect(wait).toContain("<canvas");
    expect(sources["dev/waitGallery.tsx"]).toMatch(/doneText="[^"]+"/);
  });
});

describe("小修 7：沙漏翻轉收在羊皮紙裡", () => {
  const halfW = JUDGE_PARCH.w / 2;
  const halfH = JUDGE_PARCH.h / 2;
  it("原本（不縮）轉到斜的時候超出羊皮紙約 2px", () => {
    const e = hourglassExtent(Math.PI / 4);
    expect(e.w - halfW).toBeGreaterThan(1.5);
  });
  it("翻轉中每個角度都收在紙裡（離邊 ≥ 1px）；直立時不縮", () => {
    expect(hourglassFlipScale(0)).toBe(1);
    expect(hourglassFlipScale(Math.PI)).toBeCloseTo(1, 9);
    for (let i = 0; i <= 180; i++) {
      const a = (Math.PI * i) / 180;
      const e = hourglassExtent(a, hourglassFlipScale(a));
      expect(e.w).toBeLessThanOrEqual(halfW - 1 + 1e-9);
      expect(e.h).toBeLessThanOrEqual(halfH - 1 + 1e-9);
    }
    expect(HOURGLASS_HALF.h).toBeLessThanOrEqual(halfH - 1); // 直立時本來就在紙裡
  });
  it("畫法：翻轉中有縮放、流沙時沒有（判定一輪 1.4 秒，前 15% 翻轉）", () => {
    const flipping = record(frame("judge", 100));
    expect(flipping.some((c) => c.startsWith("rotate("))).toBe(true);
    expect(flipping.some((c) => c.startsWith("scale("))).toBe(true);
    const flowing = record(frame("judge", 900));
    expect(flowing.some((c) => c.startsWith("scale("))).toBe(false);
  });
});

describe("小修 8：封蠟＝不規則的蠟緣＋壓印紋（程式繪製、確定性）", () => {
  it("蠟緣是固定點列：每次一樣、起伏不規則（不是正多邊形）", () => {
    expect(SEAL_EDGE).toHaveLength(SEAL_EDGE_POINTS);
    expect(sealOutline(10, 10, 8)).toEqual(sealOutline(10, 10, 8));
    for (const m of SEAL_EDGE) {
      expect(m).toBeGreaterThan(0.75);
      expect(m).toBeLessThan(1.12);
    }
    const distinct = new Set(SEAL_EDGE.map((m) => m.toFixed(3)));
    expect(distinct.size).toBeGreaterThan(SEAL_EDGE_POINTS / 2);
    const spread = Math.max(...SEAL_EDGE) - Math.min(...SEAL_EDGE);
    expect(spread).toBeGreaterThan(0.12);
  });
  it("畫法：圓潤的蠟緣（二次曲線）、壓印的星芒與一圈小點、高光；換成會丟例外的 Math.random 也畫得出來、兩次一樣", () => {
    const orig = Math.random;
    Math.random = () => {
      throw new Error("不可以用 Math.random");
    };
    try {
      const done = frame("skill", 3000, { status: "done", doneT: 300 });
      const a = record(done);
      expect(a).toEqual(record(done));
      expect(a.filter((c) => c.startsWith("quadraticCurveTo(")).length).toBeGreaterThanOrEqual(SEAL_EDGE_POINTS);
      expect(a.some((c) => c.startsWith("ellipse("))).toBe(true);
      for (const scene of ["skill", "retell"] as WaitSceneId[]) expect(() => record(frame(scene, 2600, { status: "done", doneT: 300 }))).not.toThrow();
    } finally {
      Math.random = orig;
    }
  });
});

describe("RT-3b 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["ui/scrollReveal.ts", "ui/WaitScene.tsx", "render/waitArt.ts", "world/EventCard.tsx", "world/NpcPanel.tsx", "dev/waitGallery.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
