// UI-E2：共用彈窗元件的位置規則（三個尺寸）、危險紅帶、單層框；探索與戰鬥共用主角卡；設定面板分區標題。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { smallView, unit } from "../battle/testFixtures";
import { readSources, readStyleFiles, stripCssComments } from "../test/sourceScan";
import { HUD_BLOCKS, hudLayout, popupBox, type HudBlock, type Rect } from "../world/hud";
import { HintsSettingsSection } from "../world/HintsSettingsSection";
import { DialogFrame } from "./DialogFrame";
import { HeroCard } from "./HeroCard";
import { Hud } from "./Hud";
import { MotionSettingsSection } from "./MotionSettingsSection";
import { PopupFrame, popupPlacementStyle } from "./PopupFrame";

const SIZES = [
  [1600, 900],
  [1040, 624],
  [800, 600],
] as const;
const AVOID: readonly HudBlock[] = HUD_BLOCKS.filter((id) => id !== "toasts");
const overlaps = (a: Rect, b: Rect) => a.left < b.left + b.width - 0.5 && b.left < a.left + a.width - 0.5 && a.top < b.top + b.height - 0.5 && b.top < a.top + a.height - 0.5;
const px = (v: unknown) => (typeof v === "number" ? v : Number.NaN);

describe("共用彈窗元件：位置規則（6F-3 的 popupBox，三個尺寸）", () => {
  for (const [w, h] of SIZES) {
    it(`${w}×${h}：面板（720）與中上方卡（460×縮放）的樣式不蓋 HUD、上緣在主角卡下、下緣在功能列上`, () => {
      for (const mates of [0, 2]) {
        const layout = hudLayout(w, h, { mates, narrow: w < 900, collapsed: false });
        for (const want of [720, 460 * layout.scale]) {
          const box = popupBox(layout, want);
          const style = popupPlacementStyle({ kind: "hud", box }) ?? {};
          const rect: Rect = { left: (w - px(style.width)) / 2, top: px(style.top), width: px(style.width), height: px(style.maxHeight) };
          expect(style.maxWidth).toBe(box.maxWidth);
          expect(rect.top).toBeGreaterThanOrEqual(layout.blocks.hero.top + layout.blocks.hero.height);
          expect(rect.top + rect.height).toBeLessThanOrEqual(layout.blocks.bar.top);
          for (const id of AVOID) {
            const b = layout.blocks[id];
            if (b.width > 0 && b.height > 0) expect(overlaps(rect, b), `${id}`).toBe(false);
          }
          // 元件真的把這組樣式寫到外框上
          const html = renderToStaticMarkup(createElement(PopupFrame, { placement: { kind: "hud", box }, children: "x" }));
          expect(html).toContain(`top:${box.top}px`);
          expect(html).toContain(`max-height:${box.maxHeight}px`);
          expect(html).toContain(`width:${box.maxWidth}px`);
        }
      }
    });
  }

  it("詢問視窗與內嵌卡不帶內聯位置（詢問視窗的位置在 CSS .decision-card，靠上／靠下）", () => {
    expect(popupPlacementStyle({ kind: "dialog", low: false })).toBeUndefined();
    expect(popupPlacementStyle({ kind: "inline" })).toBeUndefined();
  });
});

describe("共用彈窗元件：外觀", () => {
  it("單層：外框（rt-frame 四角飾件）＋內容區；沒有第二層框", () => {
    const html = renderToStaticMarkup(createElement(PopupFrame, { placement: { kind: "inline" }, className: "world-event", children: "內容" }));
    expect(html).toBe('<div class="ui-popup rt-frame ui-popup-inline world-event" data-popup="inline" data-tone="normal"><div class="ui-popup-body">內容</div></div>');
  });

  it("危險類（遇敵）只在上緣加紅帶和「！」，框還是同一個", () => {
    const html = renderToStaticMarkup(createElement(PopupFrame, { placement: { kind: "inline" }, tone: "danger", className: "world-encounter", children: "遇敵" }));
    expect(html).toMatch(/^<div class="ui-popup rt-frame ui-popup-inline danger world-encounter"[^>]*data-tone="danger"><div class="ui-popup-band" aria-hidden="true"><span>！<\/span><\/div>/);
  });

  it("戰鬥詢問視窗（DialogFrame）收進共用元件：標題列不捲、內容在框內捲；移到下方時加 low", () => {
    const html = renderToStaticMarkup(createElement(DialogFrame, { label: "反應詢問", title: "反應詢問：格擋", children: "選項" }));
    expect(html).toMatch(/^<div class="ui-popup rt-frame ui-popup-dialog decision-card" role="dialog" aria-label="反應詢問"/);
    expect(html).toMatch(/<div class="decision-head">.*<\/div><div class="ui-popup-body">選項<\/div><\/div>$/);
    const low = renderToStaticMarkup(createElement(DialogFrame, { label: "反應詢問", title: "t", startLow: true, children: "x" }));
    expect(low).toContain("ui-popup-dialog low decision-card");
  });

  it("CSS：深藍底金框來自同一組變數；彈窗裡的 .panel 不再畫第二層框，改細分隔線", () => {
    const css = readStyleFiles()
      .map(([, t]) => stripCssComments(t))
      .join("\n");
    expect(css).toMatch(/--ui-navy:\s*#1e2236/);
    expect(css).toMatch(/\.ui-popup\s*\{[^}]*background:\s*var\(--ui-panel-solid\)[^}]*border:\s*2px solid var\(--ui-gold\)/);
    expect(css).toMatch(/\.ui-popup \.panel\s*\{[^}]*border:\s*none/);
    expect(css).toMatch(/\.ui-popup \.panel \+ \.panel\s*\{[^}]*border-top:/);
    // 大世界與戰鬥 HUD 的面板底色都接到同一組變數（不再各寫一套炭黑）
    expect(css).toMatch(/--hud-panel:\s*var\(--ui-panel\)/);
    expect(css).toMatch(/--hud-bg:\s*var\(--ui-panel\)/);
    expect(css).not.toMatch(/rgba\(24, 20, 16|rgb\(24 20 16/);
  });
});

describe("主角卡：探索與戰鬥共用 HeroCard", () => {
  const hero = unit("unit_0001", "ally", 0, 2, { name_zh: "阿青", hp: 41, max_hp: 50, mana: 18, max_mana: 30, stamina: 6, max_stamina: 8 });

  it("戰鬥的主角卡：頭像＋名字＋三條（HP、法力、耐力）", () => {
    const html = renderToStaticMarkup(createElement(Hud, { view: { ...smallView(), units: [hero] }, hero, skills: {} }));
    expect(html).toMatch(/^<div class="hero-card rt-frame hero-card-battle panel hud" data-hero-card="battle"/);
    // QK-2b：戰鬥主角卡是主角自己的 Q 版頭像（沒有 DOM 時是同大小的空框），不再是通用臉
    expect(html).toContain('<div class="hero-card-face"><span class="hero-face"');
    expect(html).not.toContain("hud-portrait");
    expect(html).toContain('<span class="hud-title">阿青</span>');
    expect([...html.matchAll(/class="stat-bar (\w+)"/g)].map((m) => m[1])).toEqual(["hp", "mana", "stamina"]);
  });

  it("窄螢幕（compact）只有三條與圖示（沒有頭像與名字）", () => {
    const html = renderToStaticMarkup(createElement(Hud, { view: { ...smallView(), units: [hero] }, hero, skills: {}, compact: true }));
    expect(html).toContain("hero-card-battle compact panel hud hud-compact");
    expect(html).not.toContain("hero-card-face");
    expect(html).not.toContain("hud-title");
  });

  it("兩個畫面都用同一個元件（原始碼掃描）", () => {
    const src = Object.fromEntries(readSources());
    expect(src["world/WorldHud.tsx"]).toMatch(/<HeroCard\s[\s\S]*?where="world"/);
    expect(src["ui/Hud.tsx"]).toMatch(/<HeroCard where="battle"/);
    expect(src["world/WorldHud.tsx"]).not.toMatch(/<HudPortrait/);
  });

  it("頭像框色是目前區域的 portrait_ring（沒有區域＝hub）", () => {
    const html = renderToStaticMarkup(createElement(HeroCard, { where: "world", bars: null }));
    expect(html).toContain('data-ring="#a898ff"');
    expect(html).toContain('stroke="#a898ff"');
  });
});

describe("設定面板：分區標題＋小圖示（聲音、減少動態、提示）", () => {
  it("每區的標題有自己的圖示", () => {
    const motion = renderToStaticMarkup(createElement(MotionSettingsSection, { value: "system", onChange: () => undefined }));
    const hints = renderToStaticMarkup(createElement(HintsSettingsSection, { onReset: () => undefined }));
    expect(motion).toMatch(/class="section-title settings-head" data-settings-head="motion"><canvas class="settings-head-icon" width="32" height="32" style="width:16px;height:16px"[^>]*data-icon="motion"[\s\S]*<span>減少動態<\/span>/); // QI-5：Q 版 canvas 16px
    expect(hints).toMatch(/data-settings-head="hint"[\s\S]*<span>提示<\/span>/);
    const audio = Object.fromEntries(readSources())["audio/AudioSettingsPanel.tsx"] ?? "";
    expect(audio).toContain('<SettingsHead icon="sound">聲音</SettingsHead>');
  });
});
