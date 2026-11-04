// UI-E1b：美術 PM 驗收 UI-E1 沒通過的 9 條（docs/art/UI-E1檢查.md）＋ UI-E1 待決的 2 條定案（首頁四顆鈕、同時只開一個彈窗）。
// 只換外觀，不改流程、API、規則；人物繪製（inkDoll、inkStyle、portrait）不動。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { OriginOption, RaceOption, StartOptions, WorldCharacterSummary } from "../api/types";
import { entryScene } from "../render/entryScene";
import { H, W } from "../render/regionMapArt";
import type { Surface } from "../render/regionMapPainter";
import { islandBody } from "../render/worldIslandArt";
import { AtlasPainter } from "../render/worldMapPainter";
import { CREATE_TEXTS, parseCreateTexts, raceCheckBonusHint, raceCheckBonusZh } from "../run/createTexts";
import { RaceDetail, RaceOriginPicker } from "../run/RaceOriginPicker";
import { continueLine, continueTarget, HOME_BUTTONS, HomeScreen } from "../screens/HomeScreen";
import { readFile, readSources, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { popupsToClose } from "../world/hud";
import { clipRect, cornerClashes, cornerSize, cornerZones, hitsZone, type Rect } from "./cornerClear";
import { KEYWORD_ICON_IDS, KeywordIcon, RegionCrest } from "./CreateIcons";
import { CORNER_INSET, CORNER_SIZE } from "./regionCorners";
import { regionThemeFor } from "./regionTheme";

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
const KEYWORDS_YAML = parse(content("skill_keywords.yaml")) as { keywords: { id: string }[] };

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

  it("判定加值讀 situation_rules.yaml 的 race_methods：「交涉 +1」；十族都有；滑過說明照玩法 PM 的字", () => {
    expect(raceCheckBonusZh("fox")).toBe("交涉 +1");
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

  it("右側展開欄：名字、發源、一句簡介、種族技、環境被動、「判定加值：交涉 +1」（滑過有說明）", () => {
    const html = renderToStaticMarkup(createElement(RaceDetail, { race: race("fox", "cloud_ridge", "雲嶺") }));
    expect(html).toContain('data-testid="race-detail"');
    expect(html).toContain("狐族");
    expect(html).toContain("發源：雲嶺");
    expect(html).toContain(CREATE_TEXTS.blurbs.fox);
    expect(html).toContain("狐火誘餌");
    expect(html).toContain("靈覺");
    expect(html).toContain("判定加值：交涉 +1");
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
    const glyphs = new Set<string>();
    for (const r of ["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"]) {
      const svg = renderToStaticMarkup(createElement(RegionCrest, { region: r }));
      expect(svg, r).toContain(regionThemeFor(r).accent);
      glyphs.add(svg.replaceAll(regionThemeFor(r).accent, "C").replace(/data-crest="[^"]+"/, ""));
    }
    expect(glyphs.size).toBe(5);
    const ids = KEYWORDS_YAML.keywords.map((k) => k.id).sort();
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
    expect(r).toMatch(/background: linear-gradient\(180deg, rgb\(30 34 54 \/ 0%\), var\(--ui-navy\)\)/);
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
