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
import { type Surface } from "../render/regionMapPainter";
import { AtlasPainter } from "../render/worldMapPainter";
import { HomeScreen, continueLine, continueTarget, HOME_BUTTONS } from "../screens/HomeScreen";
import { readFile, readSources, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { dialogBox, HUD_BLOCKS, hudLayout, type HudBlock, type Rect, popupsToClose } from "../world/hud";
import { HudPortrait } from "../world/HudIcons";
import { CREATE_LABEL, previewLines } from "../world/WorldCharacterPicker";
import { DialogFrame, DialogHudBox } from "./DialogFrame";
import { documentTitle, GAME_INFO, parseGameInfo } from "./gameInfo";
import { HeroCard } from "./HeroCard";
import { cornerLayers, CORNER_INSET, CORNER_SIZE } from "./regionCorners";
import { regionThemeFor, themeCssVars } from "./regionTheme";
import { nextSmall, SMALL_CORNER_SCALE, SMALL_FRAME_CLEAR, SMALL_FRAME_MAX_H, smallPadding } from "./smallFrames";
import { type OriginOption, type RaceOption, type StartOptions, type WorldCharacterSummary } from "../api/types";
import { islandBody } from "../render/worldIslandArt";
import { CREATE_TEXTS, parseCreateTexts, raceCheckBonusHint, raceCheckBonusZh } from "../run/createTexts";
import { RaceDetail, RaceOriginPicker } from "../run/RaceOriginPicker";
import { clipRect, cornerClashes, cornerSize, cornerZones, hitsZone, type Rect as Rect__uiE1b } from "./cornerClear";
import { KEYWORD_ICON_IDS, KeywordIcon, RegionCrest } from "./CreateIcons";
import { setQCanvasFactory } from "../render/qIcon/core";
import * as QH from "../render/qIcon/hud";
import { crestId } from "../render/qIcon/hud";
import { fakeCanvasFactory, fakeCtx } from "../test/fakeCanvas";

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

  it("預覽框的摘要：名字、種族・出身（沒選的略過；TR-1 武器在主城靶場選）", () => {
    expect(previewLines(" 霜月 ", "矮人", "魔導樞市出身")).toEqual({ name: "霜月", detail: "矮人・魔導樞市出身" });
    expect(previewLines("", undefined, undefined)).toEqual({ name: "（還沒取名字）", detail: "選種族與出身" });
    expect(previewLines("a", "精靈", undefined).detail).toBe("精靈");
  });

  it("TR-1（#134）：建角不選武器與關鍵字，不送 weapon／keywords", () => {
    const pick = src("world/WorldCharacterPicker.tsx");
    expect(pick).not.toContain("StartPickerView");
    expect(pick).not.toMatch(/weapon: picker|keywords: picker/);
    expect(pick).toContain('data-testid="world-start-range"');
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

// --- 原 uiE1b.test.ts ---
describe("原 uiE1b.test.ts", () => {
// UI-E1b：美術 PM 驗收 UI-E1 沒通過的 9 條（docs/archive/art/UI-E1檢查.md）＋ UI-E1 待決的 2 條定案（首頁四顆鈕、同時只開一個彈窗）。
// 只換外觀，不改流程、API、規則；人物繪製（inkDoll、inkStyle、portrait）不動。
type Rect = Rect__uiE1b;

const sources = readSources().map(([path, text]) => [path, stripTsComments(text, path)] as const);
const src = (path: string): string => sources.find(([p]) => p === path)?.[1] ?? "";
const styleFiles = readStyleFiles().map(([path, text]) => [path, stripCssComments(text)] as const);
const css = (path: string): string => styleFiles.find(([p]) => p === path)?.[1] ?? "";
/** 一條 CSS 規則的內容（選擇器完全相同的第一條）。 */
function rule(path: string, selector: string): string {
  const text = css(path);
  const at = text.indexOf(`${selector} {`);
  if (at < 0) return "";
  return text.slice(at, text.indexOf("}", at));
}
/** 規則裡某個屬性的像素值。 */
function px(body: string, prop: string): number {
  const m = new RegExp(`(?:^|[\\s;{])${prop}:\\s*(-?[\\d.]+)px`).exec(body);
  return m === null ? Number.NaN : Number(m[1]);
}

const content = (path: string): string => readFile(SRC_DIR, `../../content/${path}`);
const RACES_YAML = parse(content("races.yaml")) as { races: { id: string; blurb_zh: string; home_realm: string }[] };
const ORIGINS_YAML = parse(content("origins.yaml")) as { origins: { id: string; tagline_zh: string; realm: string }[] };
const KEYWORDS_YAML = parse(content("skill_keywords.yaml")) as { keywords: { id: string; start_hidden?: boolean }[] };

const race = (id: string, realm: string, realmName: string): RaceOption => ({
  id,
  name_zh: id === "fox" ? "狐族" : id,
  home_realm: realm,
  home_realm_name_zh: realmName,
  skill_name_zh: "狐火誘餌",
  skill_description_zh: "在 2 格內放一個誘餌。每場限用 1 次。",
  skill_ap: 1,
  skill_uses: 1,
  passive_name_zh: "靈覺",
  passive_description_zh: "看得見 2 格內的敵方陷阱與隱蔽單位。",
});
const origin = (id: string, realm: string, name: string): OriginOption => ({ id, name_zh: `${name}出身`, realm, realm_name_zh: name, description_zh: "長說明" });
const OPTIONS = {
  weapons: [],
  keywords: [],
  keyword_count: 2,
  races: [race("fox", "cloud_ridge", "雲嶺"), race("human", "crystal_crown", "晶冠城邦")],
  origins: [origin("origin_cloud_ridge", "cloud_ridge", "雲嶺"), origin("origin_ashen_waste", "ashen_waste", "灰燼荒原")],
} as unknown as StartOptions;

// ---------------- 1. 建角頁照 create-v2 ----------------

describe("1. 建角頁：種族格子卡＋右側展開欄、判定加值、出身紋章與區域色、關鍵字小圖示", () => {
  it("一句簡介、短描述讀內容檔（races.yaml blurb_zh、origins.yaml tagline_zh），十族五區都有", () => {
    expect(CREATE_TEXTS.blurbs).toEqual(Object.fromEntries(RACES_YAML.races.map((r) => [r.id, r.blurb_zh])));
    expect(CREATE_TEXTS.taglines).toEqual(Object.fromEntries(ORIGINS_YAML.origins.map((o) => [o.id, o.tagline_zh])));
    expect(Object.keys(CREATE_TEXTS.blurbs)).toHaveLength(10);
    expect(Object.keys(CREATE_TEXTS.taglines)).toHaveLength(5);
    expect(CREATE_TEXTS.taglines.origin_cloud_ridge).toBe("雲海上的山城與竹林");
  });

  it("判定加值讀 situation_rules.yaml 的 race_methods：「攀爬跳躍 +1」（#138）；十族都有；滑過說明照玩法 PM 的字", () => {
    expect(raceCheckBonusZh("fox")).toBe("攀爬跳躍 +1"); // #138 獸耳族
    expect(raceCheckBonusZh("dwarf")).toBe("機關 +1");
    expect(raceCheckBonusZh("seafolk")).toBe("耐力 +1");
    for (const r of RACES_YAML.races) expect(raceCheckBonusZh(r.id), r.id).toMatch(/^\S+ \+1$/);
    expect(raceCheckBonusZh("nobody")).toBeNull();
    expect(raceCheckBonusHint()).toBe("情境判定用這類方法時 +1");
  });

  it("內容檔壞掉或缺欄位時該項回空，不會讓畫面壞掉", () => {
    const bad = parseCreateTexts(":::", "origins: 3", "race_methods: {fox: nope}\nmethods: []");
    expect(bad).toEqual({ blurbs: {}, taglines: {}, methods: {}, bonus: 0 });
    expect(raceCheckBonusZh("fox", bad)).toBeNull();
    // 只在 client/src/run/createTexts.ts 一處匯入這三份 yaml
    const importers = sources.filter(([, t]) => /content\/(races|origins|world\/situation_rules)\.yaml/.test(t)).map(([p]) => p);
    expect(importers).toEqual(["run/createTexts.ts"]);
  });

  it("右側展開欄：名字、發源、一句簡介、種族技、環境被動、「判定加值：攀爬跳躍 +1」（滑過有說明）", () => {
    const html = renderToStaticMarkup(createElement(RaceDetail, { race: race("fox", "cloud_ridge", "雲嶺") }));
    expect(html).toContain('data-testid="race-detail"');
    expect(html).toContain("狐族");
    expect(html).toContain("發源：雲嶺");
    expect(html).toContain(CREATE_TEXTS.blurbs.fox);
    expect(html).toContain("狐火誘餌");
    expect(html).toContain("靈覺");
    expect(html).toContain("判定加值：攀爬跳躍 +1");
    expect(html).toContain(`--realm:${regionThemeFor("cloud_ridge").accent}`);
    expect(renderToStaticMarkup(createElement(RaceDetail, { race: undefined }))).toContain("race-detail empty");
  });

  it("種族卡：頭像位置（不畫人物）＋名字＋發源，外框是發源區的區域色；出身卡：區域紋章＋區名＋短描述", () => {
    const html = renderToStaticMarkup(createElement(RaceOriginPicker, { options: OPTIONS, choice: { race: "fox", origin: "" }, onChoice: () => undefined }));
    expect(html).toContain('data-testid="race-face-slot"');
    expect(html).toMatch(/race-tile selected"[^>]*--realm:#6aa84a/);
    expect(html).toContain("發源：晶冠城邦");
    expect(html).toContain('data-crest="cloud_ridge"');
    expect(html).toContain('data-crest="ashen_waste"');
    expect(html).toContain("雲海上的山城與竹林");
    expect(html).toContain("焦土上的拾荒聚落");
    // 展開欄在格子右側（同一個 race-pick-area 的第二欄）
    expect(html).toMatch(/class="race-pick-area"><div class="race-pick-grid"[\s\S]*<\/div><aside class="race-detail"/);
    expect(rule("styles/entry.css", ".entry-skin .race-pick-area")).toMatch(/grid-template-columns: minmax\(0, 1fr\) 250px/);
    // 人物繪製不動：種族卡、紋章都不呼叫任何人物畫法
    for (const p of ["run/RaceOriginPicker.tsx", "ui/CreateIcons.tsx"]) {
      for (const draw of ["inkDoll", "inkStyle", "portrait", "renderFigureCanvas", "HudPortrait"]) expect(src(p), `${p} ${draw}`).not.toContain(draw);
    }
  });

  it("五區紋章各有自己的圖樣、配區域色；每個關鍵字（skill_keywords.yaml）都有專屬小圖示", () => {
    // QI-5：紋章是 Q 版 canvas（`render/qIcon/hud.ts`）：五區各一個圖樣 id、其他區菱形寶石；框的細環與圖樣用 regionThemeFor(區).accent
    const glyphs = new Set<string>();
    for (const r of ["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"]) {
      const html = renderToStaticMarkup(createElement(RegionCrest, { region: r }));
      expect(html, r).toMatch(new RegExp(`<canvas class="region-crest" width="68" height="68"[^>]*data-crest="${r}"`));
      glyphs.add(crestId(r));
      const log = { calls: [] as string[] };
      setQCanvasFactory(fakeCanvasFactory({ calls: null }));
      try {
        QH.paint(fakeCtx(log), crestId(r), 34, 2, { accent: regionThemeFor(r).accent });
      } finally {
        setQCanvasFactory(null);
      }
      expect(log.calls, r).toContain(`strokeStyle=${regionThemeFor(r).accent}`);
    }
    expect(glyphs.size).toBe(5);
    expect(crestId("hub")).toBe("c_other");
    expect(src("ui/CreateIcons.tsx")).toContain("const accent = regionThemeFor(region).accent;");
    expect(src("ui/CreateIcons.tsx")).toContain("opt={{ accent }}");
    // KW-1：開局不出現（start_hidden）的四個層數關鍵字（連擊、怒氣、專注、氣）的圖示在 KW-3 隨美術補；拿掉 start_hidden 時這裡自動要求。
    const ids = KEYWORDS_YAML.keywords.filter((k) => k.start_hidden !== true).map((k) => k.id).sort();
    expect([...KEYWORD_ICON_IDS].sort()).toEqual(ids);
    const icons = new Set(ids.map((id) => renderToStaticMarkup(createElement(KeywordIcon, { id })).replace(/data-keyword-icon="[^"]+"/, "")));
    expect(icons.size).toBe(ids.length);
    expect(src("run/StartPicker.tsx")).toMatch(/<KeywordIcon id=\{o\.keyword\.id\} \/>\s*<b>\{o\.keyword\.name_zh\}<\/b>/);
  });

  it("新的建角樣式都限定在 .entry-skin 底下", () => {
    const entry = css("styles/entry.css");
    const at = entry.indexOf(".entry-skin .race-pick-area");
    expect(at).toBeGreaterThan(0);
    const selectors = [...entry.slice(at).matchAll(/(^|\})\s*([^{}@]+)\{/g)].map((m) => (m[2] ?? "").trim()).filter((s) => s !== "");
    expect(selectors.filter((s) => s.split(",").some((part) => !part.trim().startsWith(".entry-")))).toEqual([]);
  });
});

// ---------------- 2. 武器圖示 ----------------

describe("2. 武器圖示在深藍底上看得見：墊淺色底圓（畫法不變）", () => {
  it(".weapon-icon 有淺色圓底與金色細框", () => {
    const r = rule("styles/theme.css", ".weapon-icon");
    expect(r).toContain("border-radius: 50%");
    expect(r).toMatch(/background: radial-gradient\(circle[^;]*#f6eed8/);
    expect(r).toContain("box-shadow: 0 0 0 1px var(--ui-gold)");
    expect(src("ui/WeaponIcon.tsx")).toContain("weaponIconCanvas(weaponId, weaponClass, size)");
  });
});

// ---------------- 3. 飾件不能壓到內容 ----------------

const box = (left: number, top: number, w: number, h: number): Rect => ({ left, top, right: left + w, bottom: top + h });
const NO_BORDER = { left: 0, top: 0, right: 0, bottom: 0 };

describe("3. 飾件不能壓到內容（通用規則，不分框的大小）", () => {
  it("cornerZones：飾件在內緣往內 2px、邊長 18（小框 70%）", () => {
    const z = cornerZones(box(0, 0, 250, 74), { left: 1.5, top: 1.5, right: 1.5, bottom: 1.5 }, cornerSize(false));
    expect(z.tl).toEqual({ left: 3.5, top: 3.5, right: 21.5, bottom: 21.5 });
    expect(z.br).toEqual({ left: 228.5, top: 52.5, right: 246.5, bottom: 70.5 });
    expect(cornerSize(false)).toBe(CORNER_SIZE);
    expect(cornerSize(true)).toBeCloseTo(12.6);
    expect(CORNER_INSET).toBe(2);
  });

  it("壓到才算：重疊超過 1px；圓形內容照內切圓算；捲出可見範圍的不算", () => {
    const z = cornerZones(box(0, 0, 100, 100), NO_BORDER, 18);
    // 飾件正方形是 2～20：重疊 2px 算、1px 以內不算
    expect(hitsZone(z.tl, { rect: box(18, 18, 10, 10), label: "a" })).toBe(true);
    expect(hitsZone(z.tl, { rect: box(19, 19, 10, 10), label: "a" })).toBe(false);
    // 直徑 62 的圓：外接方框碰到飾件，但圓本身沒有
    expect(hitsZone(z.tl, { rect: box(18, 6, 62, 62), round: true, label: "頭像" })).toBe(false);
    expect(hitsZone(z.tl, { rect: box(7, 5, 62, 62), round: true, label: "頭像" })).toBe(true);
    expect(clipRect(box(0, 0, 10, 10), [box(20, 20, 10, 10)])).toBeNull();
    expect(cornerClashes(z, [{ rect: box(90, 2, 8, 8), label: "×" }])).toEqual(["右上 × ×"]);
  });

  it("大世界主角卡（250×74）：頭像、三條、階級鈕、等級、補給都讓開四角飾件（UI-E1 時 HP 條壓到右上）", () => {
    const hero = rule("styles/world-hud.css", ".world-hud-hero");
    const w = px(hero, "width");
    const h = px(hero, "height");
    expect([w, h]).toEqual([250, 74]);
    const zones = cornerZones(box(0, 0, w, h), { left: 1.5, top: 1.5, right: 1.5, bottom: 1.5 }, CORNER_SIZE);
    const main = rule("styles/world-hud.css", ".hero-card-world .hero-card-main");
    const face = rule("styles/world-hud.css", ".world-hud-face");
    const rank = rule("styles/world-hud.css", ".world-hud-rank");
    const lv = rule("styles/world-hud.css", ".world-hud-lv");
    const chips = rule("styles/world-hud.css", ".world-hud-hero > .world-hud-chips");
    const items = [
      { rect: box(px(main, "left"), px(main, "top"), px(main, "width"), 14), label: "HP 條" },
      { rect: box(px(main, "left"), 5 + 14 + 2 + 12 + 2, px(main, "width"), 5), label: "耐力條" },
      { rect: box(px(face, "left"), px(face, "top"), 62, 62), round: true, label: "頭像" },
      { rect: box(px(rank, "left"), px(rank, "top"), 22, 22), label: "階級鈕" },
      { rect: box(px(lv, "left"), px(lv, "top"), 30, 17), label: "等級" },
      { rect: box(px(chips, "left"), h - px(chips, "bottom") - 18, 100, 18), label: "補給、靈感" },
    ];
    expect(cornerClashes(zones, items)).toEqual([]);
    // UI-E1 的版面（三條 78～242、頭像 left 7、階級鈕 left 2）會壓到
    const old = [
      { rect: box(78, 5, 164, 14), label: "HP 條" },
      { rect: box(2, 52, 22, 22), label: "階級鈕" },
    ];
    expect(cornerClashes(zones, old)).toEqual(["右上 × HP 條", "左下 × 階級鈕"]);
  });

  it("危險類（遇敵、反應詢問）：紅帶讓出四角（左右各 22px 起）、「！」往右、遇敵卡左右內距加大、上方內距讓出紅帶", () => {
    const band = rule("styles/theme.css", ".ui-popup-band");
    expect(band).toContain("position: absolute");
    expect(px(band, "left")).toBeGreaterThanOrEqual(2 + CORNER_INSET + CORNER_SIZE);
    expect(px(band, "right")).toBeGreaterThanOrEqual(2 + CORNER_INSET + CORNER_SIZE);
    expect(px(rule("styles/theme.css", ".ui-popup-band > span"), "margin-left")).toBeGreaterThan(14);
    const pad = rule("styles/theme.css", ".ui-popup-inline.danger");
    expect(px(pad, "padding-left")).toBeGreaterThanOrEqual(12 + 6);
    expect(px(pad, "padding-left") + 2).toBeGreaterThanOrEqual(2 + CORNER_INSET + CORNER_SIZE);
    expect(px(rule("styles/theme.css", ".ui-popup.danger"), "padding-top") + 2).toBeGreaterThanOrEqual(2 + CORNER_INSET + CORNER_SIZE);
  });

  it("框的內距讓開飾件：inline 彈窗、入口畫面的框與舊 .panel 左右 20px；HUD 面板捲動區上下 20px", () => {
    const clear = 2 + CORNER_INSET + CORNER_SIZE; // 外框邊 2px＋離內緣 2px＋邊長 18px
    for (const [file, sel] of [
      ["styles/theme.css", ".ui-popup-inline"],
      ["styles/entry.css", ".entry-skin .ui-popup-inline"],
      ["styles/entry.css", ".entry-skin .panel"],
    ] as const) {
      const m = /padding: (\d+)px (\d+)px/.exec(rule(file, sel));
      expect(m, `${file} ${sel}`).not.toBeNull();
      expect(Number(m?.[2]) + 2, `${file} ${sel}`).toBeGreaterThanOrEqual(clear);
    }
    expect(rule("styles/world-hud.css", ".world-hud-panel > .ui-popup-body")).toContain("margin: 20px 0");
  });

  it("開發頁畫得出遇敵卡（標題「遇敵：地點」）與反應詢問（正式元件），也能量飾件", () => {
    const g = src("dev/storyGallery.tsx");
    expect(g).toContain("<EncounterPanel view={ENCOUNTER_VIEW}");
    expect(g).toContain("<DecisionDialog pending={PENDING}");
    expect(g).toMatch(/encounter: EncounterScene, reaction: ReactionScene/);
    expect(src("world/WorldPanel.tsx")).toContain('<div className="section-title">遇敵：{e.location_name_zh}</div>');
    for (const p of ["dev/storyGallery.tsx", "dev/themeGallery.tsx"]) expect(src(p), p).toContain("__corners = () => scanCornerIssues(document, window)");
  });

  it("排版煙霧檢查每個階段都量「四角飾件沒有壓到內容」，戰鬥也量；window.__layoutSmoke.corners() 可單獨跑", () => {
    const smoke = src("dev/layoutSmoke.ts");
    expect(smoke).toMatch(/function stageRows[\s\S]*?cornerRow\(stage, scanCornerIssues\(doc, win\), doc\)/);
    expect(smoke).toMatch(/export async function runCase[\s\S]*?cornerRow\("戰鬥", scanCornerIssues\(document, window\), document\)/);
    expect(smoke).toContain("corners: () => scanCornerIssues(win.document, win)");
    expect(smoke).toContain('const CORNER_FRAMES = ".rt-frame, .entry-skin .panel";');
    expect(smoke).toContain("doc.querySelectorAll(CORNER_FRAMES)");
  });
});

// ---------------- 4～7 ----------------

describe("4. 事件卡內框線改低不透明度的金色", () => {
  it("說書人框、輸入框的框線是 --ui-gold-faint（亮金 45%）", () => {
    expect(rule("styles/theme.css", ":root")).toContain("--ui-gold-faint: rgb(232 187 72 / 45%)");
    expect(rule("world/story.css", ".world-dialog")).toContain("border: 1px solid var(--ui-gold-faint)");
    expect(css("styles/world.css")).toMatch(/\.world-answer,\s*\.world-chat-input textarea \{[^}]*border: 1px solid var\(--ui-gold-faint\)/);
  });
});

describe("5. 捲動區下緣漸隱遮罩（不露出被切半的字）", () => {
  it("hud 面板（含設定）與詢問視窗的捲動區最後有一塊 sticky 漸層", () => {
    const r = rule("styles/theme.css", ".ui-popup-hud > .ui-popup-body::after,\n.ui-popup-dialog > .ui-popup-body::after");
    expect(r).toContain("position: sticky");
    expect(r).toContain("bottom: 0");
    expect(r).toContain("pointer-events: none");
    // RT-3：加高加深（32px，後 55% 實色）
    expect(r).toContain("height: 32px");
    expect(r).toMatch(/background: linear-gradient\(180deg, rgb\(30 34 54 \/ 0%\), var\(--ui-navy\) 45%, var\(--ui-navy\)\)/);
    expect(src("world/WorldHud.tsx")).toMatch(/placement=\{\{ kind: "hud", box: popupBox\(layout, SETTINGS_W\) \}\}/);
  });
});

describe("6. 浮動說明卡：深藍金框；釘住時有記號", () => {
  it("float-panel、部件說明框、一句話說明都是深藍底金框；釘住換亮金並加圖釘", () => {
    const panel = rule("styles/float-card.css", ".float-card.float-panel > .float-card-body");
    expect(panel).toContain("background: var(--ui-navy)");
    expect(panel).toContain("border: 1px solid var(--ui-gold)");
    const tip = rule("styles/float-card.css", ".part-tip-box .float-card-body");
    expect(tip).toContain("background: var(--ui-navy)");
    expect(tip).toContain("border: 1px solid var(--ui-gold)");
    expect(css("styles/float-card.css")).not.toMatch(/#14141c|#1d1d2a|#ffffff55/);
    const pin = rule("styles/float-card.css", ".float-card.pinned::after");
    expect(pin).toContain("background:");
    expect(pin).toContain("var(--ui-gold-hi)");
    expect(css("styles/float-card.css")).toMatch(/\.float-card\.float-panel\.pinned > \.float-card-body,\s*\.part-tip-box\.pinned \.float-card-body \{[^}]*var\(--ui-gold-hi\)/);
    expect(src("ui/useFloatCard.tsx")).toContain('${f.pinned ? " pinned" : ""}');
  });
});

describe("7. 路線圖：連線加亮；「存檔／回首頁」用入口按鈕樣式", () => {
  it("連線 3px 亮金（打完的段實心亮金），不再是 35% 暗金", () => {
    const line = rule("styles/entry.css", ".run-route-step + .run-route-step::before");
    expect(px(line, "width")).toBe(3);
    expect(line).toContain("rgb(232 187 72 / 70%)");
    expect(line).not.toContain("--ui-gold-soft");
    expect(rule("styles/entry.css", ".run-route-step.done + .run-route-step::before")).toContain("var(--ui-gold-hi)");
  });

  it("存檔、回首頁和首頁選單鈕共用 .entry-btn", () => {
    const run = src("screens/RunScreen.tsx");
    expect(run).toMatch(/className="entry-btn entry-head-btn"[\s\S]{0,80}?>\s*存檔/);
    expect(run).toMatch(/className="entry-btn entry-head-btn" onClick=\{onHome\}>\s*回首頁/);
    expect(src("screens/HomeScreen.tsx")).toContain('className="entry-btn entry-menu-btn"');
    expect(rule("styles/entry.css", ".entry-skin button.entry-btn")).toMatch(/background: linear-gradient/);
  });
});

// ---------------- 8. 鎖頭徽章 ----------------

/** 數一次繪製裡鎖頭徽章的外圈（medallion 的 arc 半徑 16）次數。 */
function medallionArcs(run: (make: (w: number, h: number) => Surface, ctx: CanvasRenderingContext2D) => void): number {
  let n = 0;
  const mock = () =>
    new Proxy({} as Record<string, unknown>, {
      get: (t, p: string) =>
        p in t
          ? t[p]
          : p === "arc"
            ? (_x: number, _y: number, r: number) => (r === 16 ? (n += 1) : 0)
            : p === "createLinearGradient" || p === "createRadialGradient" || p === "createPattern"
              ? () => ({ addColorStop: () => undefined })
              : p === "measureText"
                ? () => ({ width: 10 })
                : p === "getImageData"
                  ? () => ({ data: new Uint8ClampedArray(4) })
                  : () => undefined,
      set: (t, p: string, v) => ((t[p] = v), true),
    }) as unknown as CanvasRenderingContext2D;
  run((w, h) => ({ width: w, height: h, getContext: () => mock() }), mock());
  return n;
}

describe("8. 首頁、路線圖背景（bare）不畫鎖頭徽章", () => {
  it("islandBody：badge=false 時未開放的島不畫徽章；大世界圖照舊畫", () => {
    const locked = entryScene().islands.find((i) => i.status !== "open");
    expect(locked).toBeDefined();
    if (locked === undefined) return;
    expect(medallionArcs((_m, c) => islandBody(c, locked, () => null))).toBe(1);
    expect(medallionArcs((_m, c) => islandBody(c, locked, () => null, false))).toBe(0);
  });

  it("AtlasPainter：bare 的上層不畫任何鎖頭徽章，不是 bare（大世界圖）每座未開放的島一個", () => {
    const scene = entryScene();
    const lockedCount = scene.islands.filter((i) => i.status !== "open").length;
    expect(lockedCount).toBe(3);
    const paint = (bare: boolean) => medallionArcs((make, ctx) => new AtlasPainter(make).paintOverlay(ctx, scene, false, W, H, 1, { t: null, bare }));
    // 半徑 16 的 arc 別的圖樣也會用（雲、浮島）：比較兩種畫法的差＝徽章數
    expect(paint(false) - paint(true)).toBe(lockedCount);
    expect(src("ui/EntryBackdrop.tsx")).toContain("bare: true");
  });
});

// ---------------- 10. 首頁四顆鈕 ----------------

const CHARS: WorldCharacterSummary[] = [
  { character_id: "c1", name: "阿木", level: 2, region_name_zh: "雲嶺", location_name_zh: "霧渡鎮" },
  { character_id: "c2", name: "霜月", level: 5, region_name_zh: "灰燼荒原", location_name_zh: "餘燼集" },
];
const buttonsOf = (html: string) => [...html.matchAll(/<button([^>]*)>(.*?)<\/button>/g)].map((m) => ({ attrs: m[1] ?? "", text: (m[2] ?? "").replace(/<[^>]+>/g, "") }));

describe("10. 首頁照樣張的四顆鈕：繼續、建立新角色、roguelite 一輪、設定", () => {
  it("沒有角色時「繼續」停用，寫「還沒有角色」", () => {
    const html = renderToStaticMarkup(createElement(HomeScreen, { onContinue: () => undefined, onCreate: () => undefined, onRun: () => undefined, initialChars: [] }));
    const b = buttonsOf(html);
    expect(b.map((x) => x.text)).toEqual(["繼續還沒有角色", "建立新角色", "roguelite 一輪", "設定"]);
    expect(b[0]?.attrs).toContain("disabled");
    expect(HOME_BUTTONS).toEqual(["繼續", "建立新角色", "roguelite 一輪", "設定"]);
    for (const dev of ["技能工坊", "單場戰鬥", "季末重置"]) expect(html).not.toContain(dev);
  });

  it("有角色時「繼續」寫最近的角色（瀏覽器記住的優先，否則第一個）", () => {
    expect(continueTarget(CHARS, "c2")?.character_id).toBe("c2");
    expect(continueTarget(CHARS, "gone")?.character_id).toBe("c1");
    expect(continueTarget([], "c1")).toBeNull();
    expect(continueLine(CHARS[1] as WorldCharacterSummary)).toBe("霜月 Lv 5・灰燼荒原・餘燼集");
    const html = renderToStaticMarkup(createElement(HomeScreen, { onContinue: () => undefined, onCreate: () => undefined, onRun: () => undefined, initialChars: CHARS }));
    const first = buttonsOf(html)[0];
    expect(first?.attrs).not.toContain("disabled");
    expect(first?.text).toBe("繼續阿木 Lv 2・雲嶺・霧渡鎮");
  });

  it("App：繼續記住角色後進大世界、建立新角色清掉記號、roguelite 一輪進開新一輪；開發選單照舊在 ?dev=1", () => {
    const app = src("App.tsx");
    expect(app).toMatch(/onContinue=\{\(id\) => \{\s*writeWorldChar\(id\);\s*setScreen\("world"\);/);
    expect(app).toMatch(/onCreate=\{\(\) => \{\s*writeWorldChar\(null\);\s*setScreen\("world"\);/);
    expect(app).toContain('onRun={() => setScreen("run_new")}');
    expect(app).toMatch(/if \(!isDevMode\(window\.location\.search\)\) \{[\s\S]*<HomeScreen/);
    // 「繼續」用背景請求讀角色列表（401 不導到登入畫面），沒登入、也不是開發模式時不讀
    expect(src("api/client.ts")).toContain('worldCharactersQuiet: () => request<WorldCharacterSummary[]>("GET", "/world/characters", undefined, true)');
    expect(src("screens/HomeScreen.tsx")).toMatch(/s\.account != null \|\| s\.dev_mode \? api\.worldCharactersQuiet\(\) : \[\]/);
    // 設定在同一個框裡展開（聲音、減少動態），不是另開彈窗
    const home = src("screens/HomeScreen.tsx");
    expect(home).toContain("<AudioSettingsPanel />");
    expect(home).toContain("<MotionSettingsSection />");
    expect(home).not.toMatch(/role="dialog"/);
    expect(src("dev/layoutSmoke.ts")).toContain('entryPickStages(doc, win, "建立新角色")');
  });
});

// ---------------- 11. 同一時間只開一個彈窗 ----------------

describe("11. 大世界同一時間只開一個彈窗（設定、面板、地圖）", () => {
  it("popupsToClose：開設定關面板與地圖；開面板關設定；鎖住的面板（閃現、三選一待選）不關", () => {
    const all = { settings: true, panel: true, map: true };
    expect(popupsToClose("settings", all)).toEqual(["panel", "map"]);
    expect(popupsToClose("panel", all)).toEqual(["settings", "map"]);
    expect(popupsToClose("map", { settings: true, panel: false, map: false })).toEqual(["settings"]);
    expect(popupsToClose("settings", { settings: false, panel: true, map: false }, true)).toEqual([]);
    expect(popupsToClose("settings", { settings: false, panel: false, map: false })).toEqual([]);
  });

  it("WorldHud：齒輪鈕先關其他彈窗再開設定；面板、地圖打開時關掉設定；WorldScreen 傳關地圖", () => {
    const hud = src("world/WorldHud.tsx");
    expect(hud).toMatch(/if \(!settings\.open\) for \(const p of popupsToClose\("settings", open, props\.panelLocked === true\)\) closeOf\[p\]\(\);/);
    expect(hud).toMatch(/if \(opened && settings\.open\) settings\.setOpen\(false\);/);
    expect(hud).toContain("<SettingsTool menu={settings} onToggle={toggleSettings} />");
    expect(src("screens/WorldScreen.tsx")).toContain("onCloseMap={() => setRegionOpen(false)}");
    // 面板之間本來就只開一個（togglePanel）
    expect(src("world/hud.ts")).toMatch(/return current === clicked \? null : clicked;/);
  });
});
});
