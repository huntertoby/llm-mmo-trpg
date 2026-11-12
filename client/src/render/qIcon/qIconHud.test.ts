// Phase QI-5：HUD 的 Q 版小圖示（第⑦批，`qIcon/hud.ts`）與接線（`render/hudIcon.ts`、各 React 元件）。
// 需求 docs/art/Q版小圖示-HUD移植需求.md；和樣張逐像素（指紋）比對在開發頁 `hud-gallery.html?set=hash`（報告第 4 節），這裡鎖住結構與接線。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { readFile, SRC_DIR, stripCssComments } from "../../test/sourceScan";
import { BattleToolIcon } from "../../ui/BattleToolIcons";
import { RegionCrest } from "../../ui/CreateIcons";
import { regionThemeFor } from "../../ui/regionTheme";
import { SettingsHead } from "../../ui/SettingsHead";
import { StatChipView, StatGlyph } from "../../ui/StatusCardParts";
import { HudBarIcon } from "../../world/HudBarIcons";
import { HudIcon } from "../../world/HudIcons";
import { mix } from "../color";
import { BAR_ICON_ID, clearHudIconCache, floatPinCanvas, HUD_ICON_ID, hudIconOpt, installPinBadge, PIN_BADGE_VAR, SETTINGS_ICON_ID, STAT_ICON_ID, TOOL_ICON_ID } from "../hudIcon";
import { cardGlyphCanvas, clearSkillIconCache } from "../skillIcon";
import { setQCanvasFactory } from "./core";
import * as QH from "./hud";
import * as QP from "./parts";

const log: FakeCanvasLog = { calls: null };
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => {
  setQCanvasFactory(null);
  clearHudIconCache();
  clearSkillIconCache();
  log.calls = null;
});
/** 在假畫布上畫一次，回傳外層 ctx 的呼叫紀錄（內層畫布的紀錄進全域 `log`）。 */
function outer(fn: (c: CanvasRenderingContext2D) => void): string[] {
  const own: FakeCanvasLog = { calls: [] };
  fn(fakeCtx(own));
  return own.calls ?? [];
}
/** 全域 `log` 在 fn 期間的紀錄（`render` 另建的畫布都記在這裡）。 */
function inner(fn: () => void): string[] {
  log.calls = [];
  try {
    fn();
    return log.calls;
  } finally {
    log.calls = null;
  }
}
const sizesOf = (e: QH.HudIconEntry): number[] => [...new Set(e.sizes)].sort((a, b) => a - b);
const optOf = (e: QH.HudIconEntry, px: number): QH.HudPaintOpt => (e.bare?.includes(px) ? { frame: "none" } : {});

describe("T1 清單（需求 1.1、2.1～2.3）", () => {
  it("50 個圖示：功能列 8、通用小圖 16（任務、留言在功能列）、工具鈕 7、資源小圖 8、設定標題 3、源力圓點 2、紋章 6；順序照樣張", () => {
    const count = (g: QH.HudGroup) => QH.list(g).length;
    expect(QH.list().length).toBe(50);
    expect([count("bar"), count("gen"), count("tool"), count("res"), count("set"), count("pip"), count("crest")]).toEqual([8, 16, 7, 8, 3, 2, 6]);
    expect(QH.list().slice(0, 9).map((e) => e.id)).toEqual(["bar_I", "bar_K", "bar_G", "bar_J", "bar_Y", "bar_N", "bar_R", "bar_M", "rank"]);
    expect(QH.ICON.bar_J?.bare).toEqual([20, 14]);
    expect(QH.ICON.bar_N?.bare).toEqual([13]);
  });
  it("同題材直接呼叫前幾批（src）：背包、離開、移動＝風格樣張；潛行＝第④批兜帽；警告、反應、沙漏、AP 等＝第④批卡片；雪＝第⑤批冰；護盾＝第③批", () => {
    const src = (id: string) => QH.ICON[id]?.src;
    expect([src("bar_I"), src("t_exit"), src("r_move")]).toEqual(["style:hud.bag", "style:hud.exit", "style:hud.move"]);
    expect(src("bar_R")).toBe("b4:status.concealed");
    expect([src("warn"), src("t_reactions"), src("t_telegraph"), src("r_ap"), src("r_reaction"), src("pip_on")]).toEqual(["b4:card.drawback", "b4:card.reaction", "b4:card.delayed", "b4:card.ap", "b4:card.reaction", "b4:card.source"]);
    expect([src("snow"), src("r_shield"), src("r_weapon")]).toEqual(["b5:emblem.ice", "b3:act.shield", "b4:skeleton.strike"]);
    // 風、霧、金幣、影子是第 2 版新畫（不呼叫風架勢、物品金幣）
    expect([src("wind"), src("fog"), src("bar_Y")]).toEqual([undefined, undefined, undefined]);
    expect(src("coin")).toBe("style:item.gold");
  });
  it("同一個畫法共用：齒輪（設定 17＝版面 20 同形）、燈泡（靈感點＝提示）呼叫紀錄逐筆相同", () => {
    expect(inner(() => QH.glyph("t_layout", 17, 2))).toEqual(inner(() => QH.glyph("gear", 17, 2)));
    expect(inner(() => QH.glyph("s_hint", 16, 2))).toEqual(inner(() => QH.glyph("bulb", 16, 2)));
    expect(QH.ICON.c_arcane_hub?.src).toBe("same:gear");
  });
});

describe("T2 框與畫法路徑（需求 3 第 1、2、6、7 點）", () => {
  it("功能列：先填淺色圓底（半徑 15.5/48、細框），再貼 74% 的圖樣；frame none（任務 20／14、留言 13）不畫圓底、圖樣撐滿", () => {
    for (const { id } of QH.list("bar")) {
      const c = outer((x) => QH.paint(x, id, 35, 2));
      const fill = c.indexOf(`fillStyle=${QH.BACKING}`), img = c.findIndex((s) => s.startsWith("drawImage("));
      expect(fill, id).toBeGreaterThan(0);
      expect(img, id).toBeGreaterThan(fill);
      expect(c, id).toContain(`arc(17.500,17.500,${((15.5 / 48) * 35).toFixed(3)},0.000,${(Math.PI * 2).toFixed(3)})`);
      expect(c, id).toContain(`strokeStyle=${QH.BACKING_EDGE}`);
    }
    const bare = outer((x) => QH.paint(x, "bar_J", 20, 2, { frame: "none" }));
    expect(bare).not.toContain(`fillStyle=${QH.BACKING}`);
    expect(bare.filter((s) => s.startsWith("drawImage("))).toEqual(["drawImage(canvas(40x40),0.000,0.000,20.000,20.000)"]);
  });
  it("紋章：深藍底、金框 1.6、區域色 55% 細環照現行；圖樣 60% 置中；色＝區域色三階（本色、混白 40%、混黑 28%）", () => {
    const accent = "#6aa84a";
    const c = outer((x) => QH.paint(x, "c_cloud_ridge", 30, 2, { accent }));
    expect(c).toContain(`fillStyle=${QH.CREST_NAVY}`);
    expect(c).toContain("strokeStyle=#e8bb48");
    expect(c).toContain(`strokeStyle=${accent}`);
    expect(c).toContain("globalAlpha=0.550");
    expect(c.filter((s) => s.startsWith("drawImage("))).toEqual(["drawImage(canvas(36x36),6.000,6.000,18.000,18.000)"]);
    expect(QH.tone3(accent)).toEqual([accent, mix(accent, "#ffffff", 0.4), mix(accent, "#000000", 0.28)]);
    const pal = inner(() => QH.glyph("c_cloud_ridge", 18, 2, { accent }));
    for (const col of QH.tone3(accent)) expect(pal, col).toContain(`fillStyle=${col}`);
  });
  it("紋章 id：五區各一個、其他區菱形寶石；樣張的區域色表＝遊戲的 regionThemeFor(區).accent", () => {
    expect(["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide", "hub", "brand_new_realm"].map(QH.crestId)).toEqual(["c_crystal_crown", "c_cloud_ridge", "c_arcane_hub", "c_ashen_waste", "c_frost_tide", "c_other", "c_other"]);
    for (const [region, accent] of Object.entries(QH.REGION_ACCENT)) expect(regionThemeFor(region).accent, region).toBe(accent);
  });
  it("資源小圖 AP、法力、源力、反應＝第④批 cardCanvas 原樣；移動、護盾、武器、彈藥走同一條卡片小圖路徑（16 → 圖樣 13.44、不包外框）", () => {
    for (const id of ["r_ap", "r_mana", "r_source", "r_reaction"]) {
      const card = QH.ICON[id]!.card!;
      expect(inner(() => outer((x) => QH.paint(x, id, 16, 2))), id).toEqual(inner(() => QP.cardCanvas(card, 16, 1, { res: 2 })));
    }
    for (const id of ["r_move", "r_shield", "r_weapon", "r_ammo"]) {
      const c = outer((x) => QH.paint(x, id, 16, 2)).filter((s) => s.startsWith("drawImage("));
      expect(c, id).toEqual([`drawImage(canvas(36x36),-1.000,-1.000,18.000,18.000)`]);
      expect(inner(() => QH.paint(fakeCtx({ calls: null }), id, 16, 2)), id).not.toContain("globalCompositeOperation=source-in");
    }
  });
  it("源力圓點 9：晶石撐滿（圖樣 9×0.96），亮＝第④批晶石、暗＝同形紫框深底；不包外框", () => {
    const on = inner(() => QH.paint(fakeCtx({ calls: null }), "pip_on", 9, 2)), off = inner(() => QH.paint(fakeCtx({ calls: null }), "pip_off", 9, 2));
    expect(on).toContain("fillStyle=#b8a8ff");
    expect(off).toContain("fillStyle=#7a68c8");
    expect(off).toContain("fillStyle=#2a2440");
    for (const c of [on, off]) expect(c).not.toContain("globalCompositeOperation=source-in");
    expect(outer((x) => QH.paint(x, "pip_on", 9, 2)).filter((s) => s.startsWith("drawImage("))).toEqual(["drawImage(canvas(23x23),-1.000,-1.000,11.500,11.500)"]);
  });
  it("≤14px 不包外框（警告 13、任務 14、留言 13）；>14px 包外框", () => {
    const outlined = (id: string, px: number, opt: QH.HudPaintOpt = {}) => inner(() => QH.paint(fakeCtx({ calls: null }), id, px, 2, opt)).includes("globalCompositeOperation=source-in");
    expect(outlined("warn", 13)).toBe(false);
    expect(outlined("bar_J", 14, { frame: "none" })).toBe(false);
    expect(outlined("bar_N", 13, { frame: "none" })).toBe(false);
    expect(outlined("warn", 15)).toBe(true);
    expect(outlined("rank", 18)).toBe(true);
    expect(outlined("bar_I", 24)).toBe(true);
  });
  it("貼圖對齊整數裝置像素：全部圖示 × 遊戲裡的每個大小 × res 1、2，drawImage 左上 × res 是整數、寬高＝畫布 ÷ res", () => {
    let n = 0;
    for (const { id, entry: e } of QH.list())
      for (const px of sizesOf(e))
        for (const res of [1, 2]) {
          for (const s of outer((x) => QH.paint(x, id, px, res, optOf(e, px))).filter((t) => t.startsWith("drawImage("))) {
            const m = /^drawImage\(canvas\((\d+)x(\d+)\),(-?[\d.]+),(-?[\d.]+),([\d.]+),([\d.]+)\)$/.exec(s);
            expect(m, `${id} ${px} ${res} ${s}`).not.toBeNull();
            const [, W, , x, y, w] = m!;
            expect(Math.abs(Number(x) * res - Math.round(Number(x) * res)), `${id} ${px} ${res} x`).toBeLessThan(1e-6);
            expect(Math.abs(Number(y) * res - Math.round(Number(y) * res)), `${id} ${px} ${res} y`).toBeLessThan(1e-6);
            expect(Number(w) * res, `${id} ${px} ${res} w`).toBeCloseTo(Number(W), 3);
            n++;
          }
        }
    expect(n).toBeGreaterThan(100);
  });
});

describe("T3 遊戲端的名字對照（需求 4 第 1、2 點）", () => {
  it("HudIcon 只留用到的 18 個；沒用到的 7 個（bag、book、growth、shadow、map、boots、pin）刪掉；任務、留言不畫圓底", () => {
    expect(Object.keys(HUD_ICON_ID).sort()).toEqual(["bulb", "clear", "coin", "fog", "gear", "moon", "night", "notes", "rain", "rank", "ration", "scroll", "snow", "sun", "token", "town", "warn", "wind"]);
    for (const gone of ["bag", "book", "growth", "shadow", "map", "boots", "pin"]) expect(gone in HUD_ICON_ID, gone).toBe(false);
    expect([HUD_ICON_ID.scroll, HUD_ICON_ID.notes]).toEqual(["bar_J", "bar_N"]);
    expect(hudIconOpt("scroll")).toEqual({ frame: "none" });
    expect(hudIconOpt("notes")).toEqual({ frame: "none" });
    expect(hudIconOpt("moon")).toEqual({});
    expect(HUD_ICON_ID.moon).not.toBe(HUD_ICON_ID.night);
    for (const id of [...Object.values(HUD_ICON_ID), ...Object.values(BAR_ICON_ID), ...Object.values(TOOL_ICON_ID), ...Object.values(SETTINGS_ICON_ID), ...Object.values(STAT_ICON_ID)]) expect(QH.ICON[id], id).toBeDefined();
    const hudIcons = readFile(SRC_DIR, "world/HudIcons.tsx");
    for (const gone of ["bag", "book", "growth", "shadow", "boots"]) expect(hudIcons, gone).not.toMatch(new RegExp(`\\| "${gone}"|  ${gone}: \\(`));
  });
  it("元件保留原本的 props，輸出 canvas：寬高＝顯示 × 2、CSS 不縮放；data 屬性照舊", () => {
    // 各元件 props 不同：用寬鬆型別
    const md = (el: unknown, props: object): string => renderToStaticMarkup(createElement(el as (p: object) => null, props));
    expect(md(HudBarIcon, { k: "Y", size: 27 })).toBe('<canvas class="hud-icon hud-bar-icon" width="54" height="54" style="width:27px;height:27px" aria-hidden="true" data-bar-icon="Y"></canvas>');
    expect(md(HudIcon, { name: "night", size: 18 })).toBe('<canvas class="hud-icon" width="36" height="36" style="width:18px;height:18px" aria-hidden="true" data-icon="night"></canvas>');
    expect(md(BattleToolIcon, { name: "reactions" })).toBe('<canvas class="bhud-icon" width="40" height="40" style="width:20px;height:20px" aria-hidden="true" data-icon="reactions"></canvas>');
    expect(md(SettingsHead, { icon: "sound", children: "聲音" })).toContain('<canvas class="settings-head-icon" width="32" height="32" style="width:16px;height:16px" aria-hidden="true" data-icon="sound"></canvas><span>聲音</span>');
    expect(md(RegionCrest, { region: "frost_tide", size: 30 })).toBe('<canvas class="region-crest" width="60" height="60" style="width:30px;height:30px" aria-hidden="true" data-crest="frost_tide"></canvas>');
    expect(md(StatGlyph, { icon: "ammo" })).toBe('<canvas class="skill-chip-glyph" width="32" height="32" style="width:16px;height:16px" aria-hidden="true"></canvas>');
  });
  it("源力圓點換 9px canvas（亮 on／暗），AP、彈藥照舊 CSS 圓點；.stat-pip.source 不畫 CSS 圓框，大小與間距照現行", () => {
    const chip = (icon: "source" | "ap", pips: boolean[]) => renderToStaticMarkup(createElement(StatChipView, { chip: { key: icon, icon, label: "", pips, dim: false, hint: "x" } }));
    const src = chip("source", [true, false, false]);
    expect(src.match(/<canvas class="stat-pip source on" width="18" height="18" style="width:9px;height:9px"/g)).toHaveLength(1);
    expect(src.match(/<canvas class="stat-pip source" width="18" height="18" style="width:9px;height:9px"/g)).toHaveLength(2);
    expect(chip("ap", [true, false])).toContain('<span class="stat-pip ap on"></span><span class="stat-pip ap"></span>');
    const css = stripCssComments(readFile(SRC_DIR, "styles/status-card.css"));
    expect(css).toMatch(/\.stat-pip \{[^}]*width: 9px;[^}]*height: 9px;/);
    expect(css).toMatch(/\.stat-pips \{[^}]*gap: 3px;/);
    expect(css).toMatch(/\.stat-pip\.source \{[^}]*border: none;/);
    expect(css).not.toContain(".stat-pip.source.on");
  });
});

describe("T4 圖釘 A 與死碼（需求 1.3 第 1 點、4 第 3 點）", () => {
  it("浮動卡的圖釘＝技能卡 PinGlyph 同一張畫布（已釘紅頭、未釘灰鋼 55%）；HoverFloat 沒有 SVG", () => {
    expect(floatPinCanvas(true)).toBe(cardGlyphCanvas("pin", 13, 2, { pinned: true }));
    expect(floatPinCanvas(false)).toBe(cardGlyphCanvas("pin", 13, 2, { pinned: false }));
    const hf = readFile(SRC_DIR, "ui/HoverFloat.tsx");
    expect(hf).not.toContain("<svg");
    expect(hf).toContain('<PinIcon className="tile-pin-icon" pinned={ctl.pinned} />');
    expect(hf).toContain('<PinIcon className="tile-pin-glyph" pinned={false} />');
    const css = stripCssComments(readFile(SRC_DIR, "styles/float-card.css"));
    const icon = css.slice(css.indexOf(".unit-float .tile-pin-icon {"));
    expect(icon.slice(0, icon.indexOf("}"))).not.toMatch(/opacity|color/);
    expect(css).not.toContain(".unit-float.pinned .tile-pin-icon");
  });
  it("釘住的說明卡角落：金圓底照留、裡面換紅頭圖釘（CSS 變數），沒有 SVG data URL", () => {
    const css = stripCssComments(readFile(SRC_DIR, "styles/float-card.css"));
    const rule = css.slice(css.indexOf(".float-card.pinned::after {"));
    const body = rule.slice(0, rule.indexOf("}"));
    expect(body).not.toContain("data:image/svg+xml");
    expect(body).toContain(`var(${PIN_BADGE_VAR}, none) center / 12px 12px no-repeat`);
    expect(body).toContain("var(--ui-gold-hi)");
    expect(body).toContain("width: 18px;");
    expect(readFile(SRC_DIR, "main.tsx")).toContain("installPinBadge(document);");
    // 掛上去的是 12px（× 2）的紅頭圖釘 PNG
    const set: [string, string][] = [];
    const doc = { documentElement: { style: { setProperty: (k: string, v: string) => set.push([k, v]) } } } as unknown as Document;
    setQCanvasFactory((w, hgt) => Object.assign(fakeCanvasFactory({ calls: null })(w, hgt), { toDataURL: () => `data:image/png;base64,${w}x${hgt}` }));
    clearSkillIconCache();
    installPinBadge(doc);
    setQCanvasFactory(fakeCanvasFactory(log));
    clearSkillIconCache();
    expect(set).toEqual([[PIN_BADGE_VAR, 'url("data:image/png;base64,24x24")']]);
    // 沒有畫布時不丟例外、不設定
    const none: [string, string][] = [];
    setQCanvasFactory(null);
    clearSkillIconCache();
    installPinBadge({ documentElement: { style: { setProperty: (k: string, v: string) => none.push([k, v]) } } } as unknown as Document);
    setQCanvasFactory(fakeCanvasFactory(log));
    expect(none).toEqual([]);
  });
  it("死碼：STAT_PATHS、PinIcon 的 SVG 路徑、::after 的 SVG data URL、.source-pips 都刪了，全專案沒有呼叫處", () => {
    expect(readFile(SRC_DIR, "ui/StatusCardParts.tsx")).not.toContain("STAT_PATHS");
    expect(readFile(SRC_DIR, "ui/HoverFloat.tsx")).not.toContain("M10.5 1.5 14.5 5.5");
    expect(readFile(SRC_DIR, "styles/float-card.css")).not.toContain("data:image/svg+xml");
    expect(readFile(SRC_DIR, "styles/hud.css")).not.toMatch(/\.source-pips?\b/);
  });
});
