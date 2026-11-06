// UI-E1：入口畫面換皮（遊戲名稱只從一處讀、浮島背景、標題牌、建角步驟、路線圖），以及美術 PM 驗收 RT-1＋UI-E2 的
// 14 項追加（反應詢問紅帶、詢問視窗避開 HUD、遇敵標題、小框飾件、頭像框淡入、設定面板、面板不透明、事件卡內框、
// 「更多動作」選單、捲動區讓出飾件、腰包標題、開發頁事件卡場景）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { coverPixels, ENTRY_OPEN_REGIONS, ENTRY_REGIONS, entryScene } from "../render/entryScene";
import { eventArtBg } from "../render/eventArt";
import { H, W } from "../render/regionMapArt";
import type { Surface } from "../render/regionMapPainter";
import { AtlasPainter } from "../render/worldMapPainter";
import { HomeScreen } from "../screens/HomeScreen";
import { readFile, readSources, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { dialogBox, HUD_BLOCKS, hudLayout, type HudBlock, type Rect } from "../world/hud";
import { HudPortrait } from "../world/HudIcons";
import { CREATE_LABEL, previewLines } from "../world/WorldCharacterPicker";
import { DialogFrame, DialogHudBox } from "./DialogFrame";
import { documentTitle, GAME_INFO, parseGameInfo } from "./gameInfo";
import { HeroCard } from "./HeroCard";
import { cornerLayers } from "./regionCorners";
import { regionThemeFor, themeCssVars } from "./regionTheme";
import { nextSmall, SMALL_CORNER_SCALE, SMALL_FRAME_CLEAR, SMALL_FRAME_MAX_H, smallPadding } from "./smallFrames";

const sources = readSources().map(([path, text]) => [path, stripTsComments(text, path)] as const);
const src = (path: string): string => sources.find(([p]) => p === path)?.[1] ?? "";
const styleFiles = readStyleFiles().map(([path, text]) => [path, stripCssComments(text)] as const);
const css = (path: string): string => styleFiles.find(([p]) => p === path)?.[1] ?? "";
/** 一條 CSS 規則的內容（選擇器完全相同的第一條）。 */
function rule(path: string, selector: string, last = false): string {
  const text = css(path);
  const at = last ? text.lastIndexOf(`${selector} {`) : text.indexOf(`${selector} {`);
  if (at < 0) return "";
  return text.slice(at, text.indexOf("}", at));
}

const GAME_YAML = readFile(SRC_DIR, "../../content/ui/game.yaml");

describe("遊戲名稱只從 content/ui/game.yaml 一處讀", () => {
  it("前端讀到的名稱與標語就是內容檔的值", () => {
    const doc = parse(GAME_YAML) as { title_zh: string; tagline_zh: string };
    expect(GAME_INFO).toEqual({ title_zh: doc.title_zh, tagline_zh: doc.tagline_zh });
    expect(documentTitle(false)).toBe(doc.title_zh);
    expect(documentTitle(true)).toContain("開發模式");
  });

  it("檔案壞掉、欄位缺或空白時退回空位，不寫死名稱", () => {
    expect(parseGameInfo("title_zh: [")).toEqual({ title_zh: "（遊戲名稱）", tagline_zh: "" });
    expect(parseGameInfo("tagline_zh: 一句話")).toEqual({ title_zh: "（遊戲名稱）", tagline_zh: "一句話" });
    expect(parseGameInfo("title_zh: '  '\ntagline_zh: x").title_zh).toBe("（遊戲名稱）");
    expect(parseGameInfo("title_zh: 新名字\ntagline_zh: x")).toEqual({ title_zh: "新名字", tagline_zh: "x" });
  });

  it("只有 gameInfo.ts 匯入 game.yaml；畫面原始碼裡沒有寫死的名稱", () => {
    const importers = sources.filter(([, t]) => t.includes("content/ui/game.yaml")).map(([p]) => p);
    expect(importers).toEqual(["ui/gameInfo.ts"]);
    const hard = sources.filter(([p, t]) => p.endsWith(".tsx") && (t.includes("LLM-MMO-TRPG") || t.includes(GAME_INFO.title_zh))).map(([p]) => p);
    expect(hard).toEqual([]);
    for (const p of ["screens/HomeScreen.tsx", "screens/StartScreen.tsx"]) expect(src(p), p).toContain("GAME_INFO.title_zh");
    expect(src("main.tsx")).toContain("document.title = documentTitle(");
  });
});

describe("入口畫面（首頁、開發選單、角色列表與建角、開新一輪、一輪路線圖）", () => {
  it("正式首頁：浮島背景、標題牌（遊戲名稱與標語）、選單是四顆鈕（UI-E1b 起；原本只有「開始」）", () => {
    const html = renderToStaticMarkup(createElement(HomeScreen, { onContinue: () => undefined, onCreate: () => undefined, onRun: () => undefined, initialChars: [] }));
    expect(html).toContain('data-testid="entry-backdrop"');
    expect(html).toMatch(/<h1 class="entry-plaque-title">[^<]+<\/h1>/);
    expect(html).toContain(`>${GAME_INFO.title_zh}</h1>`);
    expect(html).toContain(GAME_INFO.tagline_zh);
    const buttons = [...html.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((m) => (m[1] ?? "").replace(/<[^>]+>/g, ""));
    expect(buttons).toEqual(["繼續還沒有角色", "建立新角色", "roguelite 一輪", "設定"]);
    for (const dev of ["技能工坊", "開發模式", "季末重置", "單場戰鬥"]) expect(html).not.toContain(dev);
  });

  it("五個入口畫面都包在同一個外殼（背景＋深藍金框），框用共用彈窗元件", () => {
    for (const p of ["screens/HomeScreen.tsx", "screens/StartScreen.tsx", "world/WorldCharacterPicker.tsx", "screens/RunNewScreen.tsx", "screens/RunScreen.tsx"]) {
      expect(src(p), p).toMatch(/<EntryShell\b/);
    }
    expect(src("ui/EntryShell.tsx")).toMatch(/<PopupFrame placement=\{\{ kind: "inline" \}\}/);
    // 外觀規則都在 .entry-skin 底下，不影響大世界與戰鬥
    const entry = css("styles/entry.css");
    const selectors = [...entry.matchAll(/(^|\})\s*([^{}@]+)\{/g)].map((m) => (m[2] ?? "").trim()).filter((s) => s !== "" && !s.startsWith("from") && !s.startsWith("to"));
    const loose = selectors.filter((s) => s.split(",").some((part) => !/^\.(entry-|run-route|world-pick|world-account-row|run-new|run-shell)/.test(part.trim())));
    expect(loose).toEqual([]);
  });

  it("建角：按鈕「建立並在主城醒來」（#125）；預覽框的人物由外觀步驟的 LookPreview 畫（6R-2，#137），建角頁本身不直接畫；步驟標題自動編號", () => {
    expect(CREATE_LABEL).toBe("建立並在主城醒來");
    const pick = src("world/WorldCharacterPicker.tsx");
    expect(pick).toContain("CREATE_LABEL");
    expect(pick).toContain('data-testid="create-preview-slot"');
    for (const draw of ["renderFigureCanvas", "inkDoll", "drawFigure", "portrait.ts", "StoryDoll"]) expect(pick).not.toContain(draw);
    expect(css("styles/entry.css")).toContain("counter-increment: entry-step");
    expect(src("run/RaceOriginPicker.tsx")).toMatch(/section-title">種族<\/div>[\s\S]*section-title">出身<\/div>/);
  });

  it("預覽框的摘要：名字、種族・出身・武器（沒選的略過）", () => {
    expect(previewLines(" 霜月 ", "矮人", "魔導樞市出身", "斧")).toEqual({ name: "霜月", detail: "矮人・魔導樞市出身・斧" });
    expect(previewLines("", undefined, undefined, undefined)).toEqual({ name: "（還沒取名字）", detail: "選種族、出身與武器" });
    expect(previewLines("a", "精靈", undefined, "弓").detail).toBe("精靈・弓");
  });

  it("一輪路線圖：節點加連線、Boss 用頭目紋章", () => {
    const run = src("screens/RunScreen.tsx");
    expect(run).toContain('className="run-plan-list run-route"');
    expect(run).toMatch(/p\.boss \? <BossCrest \/> : p\.index/);
    expect(css("styles/entry.css")).toContain(".run-route-step + .run-route-step::before");
  });
});

describe("入口背景：大世界圖第 2 版的畫法（只有天空、浮島、浮橋、雲）", () => {
  it("場景固定：主城＋五區，第一季開放的雲嶺、荒原彩色，其他去色", () => {
    const s = entryScene();
    expect(s.capital.region).toBe("capital");
    expect(s.islands.map((i) => i.region)).toEqual([...ENTRY_REGIONS]);
    expect(ENTRY_REGIONS).toHaveLength(5);
    expect(s.islands.filter((i) => i.status === "open").map((i) => i.region).sort()).toEqual([...ENTRY_OPEN_REGIONS].sort());
    expect(entryScene()).toEqual(s);
  });

  it("蓋滿視窗：等比放大到兩邊都蓋住，最長邊有上限", () => {
    const a = coverPixels(1600, 900, W, H, 1);
    expect(a.w).toBeGreaterThanOrEqual(1600);
    expect(a.h).toBeGreaterThanOrEqual(900);
    expect(a.w / a.h).toBeCloseTo(W / H, 2);
    const b = coverPixels(800, 1200, W, H, 1);
    expect(b.h).toBeGreaterThanOrEqual(1200);
    expect(Math.max(...Object.values(coverPixels(3840, 2160, W, H, 2)))).toBeLessThanOrEqual(2600);
    expect(coverPixels(0, 600, W, H, 1)).toEqual({ w: 0, h: 0 });
  });

  it("bare：上層只貼浮島本體與前景，不貼字牌、傳送鈕、標題、圖例、外框", () => {
    const draws = (bare: boolean): number => {
      let n = 0;
      // 目標畫布數 drawImage；離屏圖（島、前景、標記）用另一個不計數的畫布
      const mock = (count: boolean) =>
        new Proxy({} as Record<string, unknown>, {
          get: (t, p: string) =>
            p in t ? t[p] : p === "drawImage" ? () => (count ? (n += 1) : 0) : p === "createLinearGradient" || p === "createRadialGradient" || p === "createPattern" ? () => ({ addColorStop: () => undefined }) : p === "measureText" ? () => ({ width: 10 }) : () => undefined,
          set: (t, p: string, v) => ((t[p] = v), true),
        }) as unknown as CanvasRenderingContext2D;
      const ctx = mock(true);
      const make = (w: number, h: number): Surface => ({ width: w, height: h, getContext: () => mock(false) });
      const scene = entryScene();
      new AtlasPainter(make).paintOverlay(ctx, scene, false, W, H, 1, { t: null, bare });
      return n;
    };
    const islands = entryScene().islands.length + 1;
    expect(draws(true)).toBe(islands + 1); // 每座島一張＋前景
    expect(draws(false)).toBe(islands * 2 + 2); // ＋每座島的標記、標題與外框
  });

  it("減少動態時浮島不動、背景不接滑鼠（CSS），sticky 不被 overflow: hidden 打斷", () => {
    const back = src("ui/EntryBackdrop.tsx");
    expect(back).toMatch(/shouldAnimate\(true, reduced/);
    expect(back).toContain("bare: true");
    const b = rule("styles/entry.css", ".entry-backdrop");
    expect(b).toContain("pointer-events: none");
    expect(b).toContain("overflow: clip");
    expect(rule("styles/entry.css", ".entry-backdrop-sticky")).toContain("position: sticky");
  });
});

// ---------------- 美術 PM 驗收 RT-1＋UI-E2 的追加 ----------------

const SIZES = [
  [1600, 900],
  [1040, 624],
  [800, 600],
] as const;
const AVOID: readonly HudBlock[] = HUD_BLOCKS.filter((id) => id !== "toasts");
const overlaps = (a: Rect, b: Rect) => a.left < b.left + b.width - 0.5 && b.left < a.left + a.width - 0.5 && a.top < b.top + b.height - 0.5 && b.top < a.top + a.height - 0.5;

describe("追加 1：戰鬥反應詢問走共用彈窗的危險類", () => {
  it("反應詢問的 DialogFrame 帶 tone=danger；外框上緣有紅帶與「！」，框還是 decision-card", () => {
    expect(src("ui/DecisionDialog.tsx")).toMatch(/<DialogFrame label="反應詢問"[^>]*tone="danger"/);
    const html = renderToStaticMarkup(createElement(DialogFrame, { label: "反應詢問", title: "反應詢問：格擋", tone: "danger", children: "選項" }));
    expect(html).toMatch(/^<div class="ui-popup rt-frame ui-popup-dialog danger decision-card"[^>]*data-tone="danger"><div class="ui-popup-band" aria-hidden="true"><span>！<\/span><\/div>/);
    // UI-E1b：紅帶改成讓出四角飾件（絕對定位、左右各 22px），不再用負邊距貼齊左右邊
    expect(rule("styles/theme.css", ".ui-popup-band")).toContain("left: 22px");
  });
});

describe("追加 2：大世界的詢問視窗（開場、配點教學）照 6F-3 避開四角 HUD", () => {
  for (const [w, h] of SIZES) {
    it(`${w}×${h}：上緣在主角卡下、下緣在功能列上、不碰任何 HUD 塊`, () => {
      for (const mates of [0, 2]) {
        const layout = hudLayout(w, h, { mates, narrow: w < 900, collapsed: false });
        const top = 58; // 舞台上緣（頂列下方）
        const box = dialogBox(layout, top);
        const rect: Rect = { left: (w - box.maxWidth) / 2, top: box.top - top, width: box.maxWidth, height: box.maxHeight };
        expect(box.maxWidth).toBeLessThanOrEqual(480);
        expect(rect.top).toBeGreaterThanOrEqual(layout.blocks.hero.top + layout.blocks.hero.height);
        expect(rect.top + rect.height).toBeLessThanOrEqual(layout.blocks.bar.top);
        for (const id of AVOID) {
          const b = layout.blocks[id];
          if (b.width > 0 && b.height > 0) expect(overlaps(rect, b), `${id}`).toBe(false);
        }
      }
    });
  }

  it("有 DialogHudBox 時外框走 hud 位置（內聯 top／max-height／width），不顯示「移到下方」；戰鬥照舊", () => {
    const box = { top: 190, maxHeight: 300, maxWidth: 420 };
    const html = renderToStaticMarkup(createElement(DialogHudBox.Provider, { value: box }, createElement(DialogFrame, { label: "開場", title: "樞島", children: "x" })));
    expect(html).toContain("ui-popup-hud decision-card world-hud-dialog");
    expect(html).toContain("top:190px");
    expect(html).toContain("max-height:300px");
    expect(html).toContain("width:420px");
    expect(html).not.toContain("移到下方");
    const battle = renderToStaticMarkup(createElement(DialogFrame, { label: "反應詢問", title: "t", children: "x" }));
    expect(battle).toContain("ui-popup-dialog decision-card");
    expect(battle).toContain("移到下方");
    expect(src("screens/WorldScreen.tsx")).toMatch(/<DialogHudBox\.Provider value=\{[^}]*dialogBox\(layoutOf\(view\)\.layout, stage\.top\)/);
  });
});

describe("追加 3：遇敵標題拿掉驚嘆號（紅帶上的「！」保留）", () => {
  it("標題「遇敵：地點」，不再有「遇敵！」", () => {
    for (const [p, t] of sources) expect(t.includes("遇敵！"), p).toBe(false);
    expect(src("world/WorldPanel.tsx")).toContain("遇敵：{e.location_name_zh}");
    expect(src("world/WorldPanel.tsx")).toMatch(/<PopupFrame[^>]*tone="danger"[^>]*className="world-encounter"/);
  });
});

describe("追加 4（含複查第 2 項）：小框的四角飾件", () => {
  it("高度 64px 以下算小框；標上之後要高過 64＋24 才拿掉；資訊塊（任務、戰鬥主角卡）一律算小框", () => {
    expect(nextSmall(64, false)).toBe(true);
    expect(nextSmall(65, false)).toBe(false);
    expect(nextSmall(80, true)).toBe(true);
    expect(nextSmall(SMALL_FRAME_MAX_H + 25, true)).toBe(false);
    expect(nextSmall(0, false)).toBe(false);
    expect(nextSmall(0, true)).toBe(true);
    expect(nextSmall(200, false, true)).toBe(true);
  });

  it("內距：原本＋6px，且至少 16px（70% 的飾件到內緣 14.6px 為止，靠邊的按鈕和頭尾的字都讓開）", () => {
    expect(smallPadding(6)).toBe(SMALL_FRAME_CLEAR);
    expect(smallPadding(12)).toBe(18);
    expect(2 + 18 * SMALL_CORNER_SCALE).toBeLessThan(SMALL_FRAME_CLEAR);
  });

  it("飾件縮成 70%（--rt-corners-small），CSS 依 data-rt-small 換用", () => {
    expect(SMALL_CORNER_SCALE).toBe(0.7);
    expect(cornerLayers("cloud", { accent: "#000000", seal: "#111111" }, 0.7)).toContain("/ 12.6px 12.6px no-repeat");
    expect(cornerLayers("cloud", { accent: "#000000", seal: "#111111" })).toContain("/ 18px 18px no-repeat");
    const vars = themeCssVars(regionThemeFor("cloud_ridge"));
    expect(vars["--rt-corners-small"]).toContain("12.6px");
    expect(rule("styles/theme.css", '.rt-frame[data-rt-small="true"]::after')).toContain("var(--rt-corners-small");
    expect(src("main.tsx")).toContain("installSmallFrames(document)");
  });

  it("任務框與戰鬥主角卡標成資訊塊（data-rt-compact）；探索主角卡不標", () => {
    expect(src("world/WorldHud.tsx")).toMatch(/className="world-hud-tracker rt-frame"[^>]*data-rt-compact="true"/);
    const battle = renderToStaticMarkup(createElement(HeroCard, { where: "battle", name: "阿青", bars: "b" }));
    expect(battle).toContain('data-rt-compact="true"');
    const world = renderToStaticMarkup(createElement(HeroCard, { where: "world", bars: "b" }));
    expect(world).not.toContain("data-rt-compact");
  });
});

describe("追加 5：頭像框色換區時 0.3 秒淡入", () => {
  it("框色寫在 style、CSS 有 0.3 秒 transition；減少動態時不淡入", () => {
    const html = renderToStaticMarkup(createElement(HudPortrait, { size: 40, ring: "#6aa84a" }));
    expect(html).toContain('class="hud-portrait-ring"');
    expect(html).toContain("stroke:#6aa84a");
    expect(rule("styles/theme.css", ".hud-portrait-ring")).toContain("transition: stroke 0.3s");
    expect(rule("styles/theme.css", ':root[data-reduced-motion="true"] .hud-portrait-ring')).toContain("transition: none");
  });
});

describe("複查第 3 項：設定面板改用共用彈窗", () => {
  it("PopupFrame 的 hud 位置（避開四角 HUD）＋標題列；不再是貼著齒輪的 top-popup", () => {
    const hud = src("world/WorldHud.tsx");
    expect(hud).toMatch(/<PopupFrame\s+placement=\{\{ kind: "hud", box: popupBox\(layout, SETTINGS_W\) \}\}\s+className="world-hud-panel world-settings-popup"/);
    expect(hud).toContain('<span className="world-settings-title">設定</span>');
    expect(hud).not.toContain("top-popup popup-menu world-settings-popup");
    expect(hud).toContain("frameRef={menu.panelRef}");
    expect(src("ui/usePopupMenu.ts")).toContain("panelRef.current?.contains(t)");
    // 標題列下已有分隔線：第一區不再畫上緣
    expect(rule("styles/world-hud.css", ".world-settings-popup > .ui-popup-body > :first-child")).toContain("border-top: none");
  });
});

describe("複查第 4～8 項：面板底色、事件卡內框、更多動作、捲動區、腰包", () => {
  it("4：浮動面板底色不透明（--ui-navy）", () => {
    expect(rule("styles/world-hud.css", ".ui-popup.world-hud-panel")).toContain("background: var(--ui-navy)");
    expect(css("styles/theme.css")).toMatch(/--ui-navy: #[0-9a-f]{6};/);
  });

  it("5：事件卡的說書人框與輸入框是深藍系", () => {
    expect(rule("world/story.css", ".world-dialog")).toContain("background: var(--ui-navy-deep)");
    expect(css("styles/world.css")).toMatch(/\.world-answer,\s*\.world-chat-input textarea \{[^}]*background: var\(--ui-navy-deep\)/);
  });

  it("6：「更多動作」選單寬度跟按鈕一樣（收進行動面板）", () => {
    const more = rule("styles/skill-bar.css", ".more-list");
    expect(more).toContain("width: 100%");
    expect(more).not.toContain("220px");
  });

  it("7：可捲動的面板，捲動區上下讓出飾件（18px）", () => {
    expect(rule("styles/world-hud.css", ".world-hud-panel > .ui-popup-body")).toContain("margin: 20px 0"); // UI-E1b：18 → 20px
    expect(rule("styles/theme.css", ".ui-popup-dialog > .ui-popup-body", true)).toContain("margin-bottom: 6px");
  });

  it("8：腰包標題和「其他物品」同一種（section-title、數字前空格、數字小字）", () => {
    const eco = src("world/EconomyPanel.tsx");
    expect(eco).toMatch(/<div className="section-title" data-testid="world-pouch-title">\s*腰包　<span className="muted small">/);
    expect(eco).not.toMatch(/section-title small">\s*腰包</);
  });

  it("9：開發頁事件卡的場景是雲嶺（標題是霧渡鎮・斷橋）", () => {
    const gallery = src("dev/storyGallery.tsx");
    expect(gallery).toMatch(/location_name_zh: "霧渡鎮・斷橋",\s*region: "cloud_ridge"/);
    expect(eventArtBg("cloud_ridge")).toBe("cloud");
  });
});
