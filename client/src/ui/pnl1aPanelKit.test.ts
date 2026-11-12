// PNL-1a：資訊面板的共用元件（分頁列、狀態記號、提示三級、籌碼、標籤、摺疊）與「隊伍與影子」面板（docs/art/資訊面板-移植需求.md）。
// vitest 沒有 DOM：分頁列四級縮、面板量高度的 DOM 部分由瀏覽器實測（報告第 4 節）；這裡鎖純函式、靜態輸出與 CSS 規則。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { WorldMyShadow, WorldPartyView, WorldView } from "../api/types";
import { clearPanelIconCache, eventBareCanvas, panelIconCacheSize, panelIconKey, partGlyphCanvas } from "../render/panelIcon";
import { setQCanvasFactory } from "../render/qIcon/core";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { readFile, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { LimitNote } from "../world/limits";
import { PartyShadowPanel, partyShadowTabs } from "../world/PartyShadowPanel";
import { memberKind, memberNote, partyCountBadge, shadowBadge } from "../world/partyShadow";
import { Callout, Chip, Fold, FoldGroup, FoldMeasureProvider, PanelHead, Tag } from "./PanelKit";
import { PanelTabs, paneVariants, TabBadge, type PanelTabDef } from "./PanelTabs";
import { badgeShowsValue, fitClass, fitLevel, pickTab, tabHintText, type FitLevel, type TabBadgeSpec } from "./panelTabRules";

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);
const css = readStyleFiles()
  .map(([, t]) => stripCssComments(t))
  .join("\n");
const rule = (sel: string): string => {
  const at = css.indexOf(`${sel} {`);
  if (at < 0) return "";
  return css.slice(at, css.indexOf("}", at));
};

const tab = (id: string, badge: TabBadgeSpec | null = null, extra: Partial<PanelTabDef> = {}): PanelTabDef => ({ id, label: `${id}全名`, short: id.slice(0, 2), icon: null, badge, render: () => createElement("p", { "data-pane-body": id }, id), ...extra });

describe("分頁規則（3.2）：預設分頁、四級縮、滑過說明、記號", () => {
  it("預設開第一個；第一個整頁鎖住時開第一個金底數字的，沒有就第一個沒鎖的", () => {
    const lock: TabBadgeSpec = { kind: "lock", hint: "閃現 4 級起" };
    expect(pickTab([tab("a"), tab("b", { kind: "n", value: 2, hint: "x" })])).toBe("a");
    expect(pickTab([tab("flash", lock), tab("attr"), tab("care", { kind: "n", value: 3, hint: "x" })])).toBe("care");
    expect(pickTab([tab("flash", lock), tab("attr"), tab("care")])).toBe("attr");
    expect(pickTab([tab("a", lock), tab("b", lock)])).toBe("a");
    expect(pickTab([])).toBeNull();
  });
  it("四級縮：放得下就停在那一級；三級都放不下＝折兩列（不藏分頁）", () => {
    const at = (ok: FitLevel) => fitLevel((lv) => lv >= ok);
    expect(at(0)).toBe(0);
    expect(at(1)).toBe(1);
    expect(at(2)).toBe(2);
    expect(fitLevel(() => false)).toBe(3);
    expect([0, 1, 2, 3].map((l) => fitClass(l as FitLevel))).toEqual(["", "fit1", "fit2", "fit3"]);
  });
  it("滑過的說明：只剩圖示時寫名字，記號另有說明；全名時沒有記號就不開卡", () => {
    const t = { label: "隊伍", badge: { kind: "p", value: "3／3", hint: "隊伍 3／3（含主角）" } as TabBadgeSpec };
    expect(tabHintText(t, 0)).toBe("隊伍 3／3（含主角）");
    expect(tabHintText(t, 2)).toBe("隊伍　隊伍 3／3（含主角）");
    expect(tabHintText({ label: "賽季時程" }, 0)).toBeNull();
    expect(tabHintText({ label: "賽季時程" }, 3)).toBe("賽季時程");
    expect(tabHintText({ label: "整備", hint: "整備：重閃、溶掉與傳承、誓約" }, 0)).toBe("整備：重閃、溶掉與傳承、誓約");
  });
  it("五種記號：只有金底、細框寫數字；鎖住、三角、綠點不寫數字", () => {
    expect(badgeShowsValue({ kind: "n", value: 3, hint: "" })).toBe(true);
    expect(badgeShowsValue({ kind: "p", value: "0／3", hint: "" })).toBe(true);
    expect(badgeShowsValue({ kind: "lock", value: 3, hint: "" })).toBe(false);
    const out = (b: TabBadgeSpec) => html(createElement(TabBadge, { badge: b }));
    expect(out({ kind: "n", value: 3, hint: "懸賞中 3" })).toBe('<span class="pnl-tbadge n" data-badge="n" aria-label="懸賞中 3">3</span>');
    expect(out({ kind: "p", value: "0／3", hint: "今日目標完成 0／3" })).toContain('class="pnl-tbadge p"');
    expect(out({ kind: "live", hint: "霧潮入侵 進行中" })).toBe('<span class="pnl-tbadge live" data-badge="live" aria-label="霧潮入侵 進行中"></span>');
    expect(out({ kind: "lock", value: 9, hint: "封印中" })).toMatch(/pnl-tbadge ico" data-badge="lock"[^>]*><canvas[^>]*data-icon="skeleton:control"/);
    expect(out({ kind: "warn", hint: "還沒存" })).toMatch(/data-badge="warn"[^>]*><canvas[^>]*data-icon="warn"/);
    expect(out({ kind: "lock", value: 9, hint: "封印中" })).not.toContain(">9<");
  });
  it("量高度：沒有摺疊的頁量一次，有摺疊的每個摺疊打開各量一次", () => {
    expect(paneVariants({ id: "attr" })).toEqual([{ key: "attr", fold: null }]);
    expect(paneVariants({ id: "care", folds: ["reflash", "dissolve", "oath"] }).map((v) => v.fold)).toEqual(["reflash", "dissolve", "oath"]);
  });
});

describe("PanelTabs 靜態輸出", () => {
  it("分頁列：role=tablist、目前分頁 on＋aria-selected、全名與短名都帶 data-t（粗體預留字寬）", () => {
    const out = html(createElement(PanelTabs, { tabs: [tab("flash", { kind: "lock", hint: "閃現 4 級起" }), tab("attr")], head: createElement("b", null, "標頭"), testId: "t" }));
    expect(out).toContain('role="tablist"');
    expect(out).toMatch(/<button type="button" role="tab" aria-selected="true" aria-label="attr全名" class="pnl-tab on" data-tab="attr">/);
    expect(out).toMatch(/aria-selected="false"[^>]*class="pnl-tab" data-tab="flash"/);
    expect(out).toContain('<span class="lbl" data-t="flash全名">flash全名</span><span class="lbl-s" data-t="fl">fl</span>');
    expect(out).toContain('data-pane-body="attr"');
    expect(out).not.toContain('data-pane-body="flash"'); // 伺服器端只畫目前分頁
    expect(out.indexOf("標頭")).toBeLessThan(out.indexOf('role="tablist"')); // 固定區：標頭在分頁列上面
    expect(out).toMatch(/^<div class="pnl-tabs"[^>]*><div class="pnl-fixed">/);
  });
  it("initial 指定開哪一頁（從別處點進來）；不認得的照預設", () => {
    expect(html(createElement(PanelTabs, { tabs: [tab("a"), tab("b")], initial: "b" }))).toContain('data-pane-body="b"');
    expect(html(createElement(PanelTabs, { tabs: [tab("a"), tab("b")], initial: "zz" }))).toContain('data-pane-body="a"');
  });
  it("只有一頁時不畫分頁列（2～5 個才拆）", () => {
    const out = html(createElement(PanelTabs, { tabs: [tab("a")] }));
    expect(out).not.toContain("tablist");
    expect(out).toContain('data-pane-body="a"');
  });
});

describe("提示三級、籌碼、標籤、摺疊、標頭", () => {
  it("提示：三級各自的 class 與圖示（警告 HUD warn、鎖住第④批金鎖、資訊事件卡 info）", () => {
    expect(html(createElement(Callout, { tone: "warn", children: "x" }))).toMatch(/^<div class="pnl-callout warn" role="note" data-tone="warn"><canvas[^>]*data-icon="warn"/);
    expect(html(createElement(Callout, { tone: "lock", children: "x" }))).toMatch(/pnl-callout lock[^>]*><canvas[^>]*data-icon="skeleton:control"/);
    expect(html(createElement(Callout, { tone: "info", sub: "次行", end: createElement("i", null, "e"), children: "x" }))).toMatch(
      /pnl-callout info[^>]*><canvas[^>]*data-icon="info"[^>]*><\/canvas><div class="body">x<span class="sub">次行<\/span><\/div><span class="end"><i>e<\/i><\/span>/,
    );
  });
  it("LimitNote 換成鎖住級提示（字照伺服器）", () => {
    const out = html(createElement(LimitNote, { reason: "4 級前不能溶掉技能或傳承" }));
    expect(out).toContain('class="pnl-callout lock"');
    expect(out).toContain('data-testid="world-limit-note"');
    expect(out).toContain("4 級前不能溶掉技能或傳承");
    expect(stripTsComments(readFile(SRC_DIR, "world/limits.tsx"))).not.toContain("world-limit-banner");
  });
  it("籌碼 0 灰、標籤六種樣子、標頭有「回到地點圖」", () => {
    expect(html(createElement(Chip, { label: "未分配屬性點", value: 0, zero: true }))).toBe('<span class="pnl-chip zero">未分配屬性點<b>0</b></span>');
    expect(html(createElement(Tag, { tone: "warn", children: "還沒存" }))).toBe('<span class="pnl-tag warn">還沒存</span>');
    expect(html(createElement(Tag, null, "第 1～3 天"))).toBe('<span class="pnl-tag">第 1～3 天</span>');
    const head = html(createElement(PanelHead, { heading: "隊伍與影子", onBack: () => undefined }));
    expect(head).toContain('<h2 class="pnl-title">隊伍與影子</h2>');
    expect(head).toContain(">回到地點圖</button>");
    expect(html(createElement(PanelHead, { heading: "x" }))).not.toContain("回到地點圖");
  });
  it("摺疊：同一組同一個 name（原生互斥）；量高度時只打開指定的那一個", () => {
    const group = (forced: string | null | undefined) =>
      html(
        createElement(
          FoldMeasureProvider,
          { value: forced },
          createElement(FoldGroup, {
            name: "care",
            children: [createElement(Fold, { key: "a", id: "a", summary: "A", end: "標籤", children: "a 內容" }), createElement(Fold, { key: "b", id: "b", summary: "B", defaultOpen: true, children: "b 內容" })],
          }),
        ),
      );
    const normal = group(undefined);
    expect(normal.match(/<details class="pnl-fold" name="care"/g)?.length).toBe(2);
    expect(normal).toMatch(/data-fold="a"><summary>A<span class="end">標籤<\/span><\/summary>/);
    expect(normal).toMatch(/name="care" open="" data-fold="b"/);
    // PNL-2：量高度時不掛 name（同名的 details 在整份文件互斥，各種樣子會互相關掉）
    expect(group("a")).toMatch(/<details class="pnl-fold" open="" data-fold="a"/);
    expect(group("a")).not.toContain('name="care"');
    expect(group("a")).not.toMatch(/open="" data-fold="b"/);
  });
});

describe("panelIcon：事件卡圖樣本身的快取（QI-6 裁定 6）", () => {
  const log: FakeCanvasLog = { calls: [] } as unknown as FakeCanvasLog;
  beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
  afterAll(() => {
    setQCanvasFactory(null);
    clearPanelIconCache();
  });
  it("同鍵同一張；鍵含種類、id、大小、解析度", () => {
    clearPanelIconCache();
    const a = eventBareCanvas("thread", 18);
    expect(eventBareCanvas("thread", 18)).toBe(a);
    expect(eventBareCanvas("thread", 18, 1)).not.toBe(a);
    expect(a.width).toBe(36);
    expect(partGlyphCanvas("skeleton", "control", 18).width).toBe(36);
    expect(panelIconCacheSize()).toBe(3);
    expect(panelIconKey("bare", "thread", 18)).toBe("bare|thread|18|2");
  });
});

function party(n: number, over: Partial<WorldPartyView> = {}): WorldPartyView {
  const members = [
    { name_zh: "AA", title_zh: "主角", level: 2, mercenary: null },
    { name_zh: "賽倫", title_zh: "盾衛・守護", level: 2, mercenary: "merc_tiebi", ai_zh: "預設（守衛）", backstory_zh: "守著你的人。" },
    { name_zh: "阿岳", title_zh: "獵戶", level: 2, companion: "companion_ayue", ai_zh: "預設（弓手）", note_zh: "劇情夥伴：任務結束後離隊" },
  ].slice(0, n);
  return { members, max_hired: 2, can_hire: false, hire_problem_zh: "入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵", mercenaries: [], shadows: [], ai_choices: [], ai: {}, season_boss_ok: true, free_slots: 0, ...over } as WorldPartyView;
}
const SHADOW: WorldMyShadow = { saved: false, ai_zh: "預設", can_set_ai: false, coins: 0, reports_zh: [] } as WorldMyShadow;
function view(p: WorldPartyView | null, s: WorldMyShadow | null = SHADOW): WorldView {
  return { character: { hero_look: null, origin_realm: null }, field: null, party: p, my_shadow: s } as unknown as WorldView;
}
const noop = () => undefined;

describe("隊伍與影子（3.3、#29～#33、#41、#42）", () => {
  it("記號：細框「3／3」（滑過「隊伍 3／3（含主角）」）；影子還沒存＝琥珀三角，存了不掛", () => {
    expect(partyCountBadge(party(3))).toEqual({ kind: "p", value: "3／3", hint: "隊伍 3／3（含主角）" });
    expect(partyCountBadge(party(1))).toMatchObject({ value: "1／3" });
    expect(shadowBadge({ saved: false })).toEqual({ kind: "warn", hint: "還沒存" });
    expect(shadowBadge({ saved: true })).toBeNull();
  });
  it("成員種類：主角＝第一位且不是傭兵／影子／夥伴；夥伴的 note 改由綠底標籤帶到", () => {
    const p = party(3);
    expect(p.members.map((m, i) => memberKind(m, i))).toEqual(["hero", "mercenary", "companion"]);
    expect(memberNote(p.members[2]!)).toBeNull();
    expect(memberNote({ ...p.members[1]!, note_zh: "x" })).toBe("x");
  });
  it("面板：標題「隊伍與影子」＋回到地點圖、兩個分頁（旗、影子）、預設開隊伍", () => {
    const out = html(createElement(PartyShadowPanel, { view: view(party(3)), busy: false, onAct: noop, onClose: noop }));
    expect(out).toContain('<h2 class="pnl-title">隊伍與影子</h2>');
    expect(out).toContain(">回到地點圖</button>");
    expect(out).toMatch(/data-tab="party">[^]*data-icon="t_orders"[^]*data-t="隊伍"[^]*class="pnl-tbadge p" data-badge="p" aria-label="隊伍 3／3（含主角）">3／3</);
    expect(out).toMatch(/data-tab="shadow">[^]*data-icon="bar_Y"[^]*data-t="我的影子"[^]*data-t="影子"[^]*data-badge="warn"/);
    expect(out).toContain('data-pane="party"');
  });
  it("隊伍分頁：第一行「主角＋最多 2 名」、卡上「Lv 2」、身分、「打法 預設（守衛）」、主角金框、夥伴綠框＋「劇情夥伴」、來歷行", () => {
    const out = html(createElement(PartyShadowPanel, { view: view(party(3)), busy: false, onAct: noop }));
    expect(out).toContain("主角＋最多 2 名");
    expect(out.match(/<span class="lvl">Lv 2<\/span>/g)?.length).toBe(3);
    expect(out).not.toContain("2 級");
    expect(out).toContain('class="pnl-member hero" data-member="hero"');
    expect(out).toMatch(/class="pnl-member comp" data-member="companion"[^]*<span class="pnl-tag live">劇情夥伴<\/span>/);
    expect(out).toContain('<span class="ai">打法 <b>預設（守衛）</b></span>');
    expect(out).toContain('data-testid="world-party-backstory">守著你的人。</span>');
    expect(out).not.toContain("劇情夥伴：任務結束後離隊");
    expect(out).toMatch(/pnl-callout lock[^]*<b>換隊友<\/b>：入門期隊友固定/);
  });
  it("獨行、劇情夥伴說明＝資訊級；賽季頭目限制＝鎖住級", () => {
    const solo = html(createElement(PartyShadowPanel, { view: view(party(1, { companion_zh: null, season_boss_zh: "有影子的隊伍不能打賽季頭目" })), busy: false, onAct: noop }));
    expect(solo).toMatch(/pnl-callout info"[^>]*data-testid="world-party-solo"[^]*<b>獨行<\/b>：只帶主角（可以在城鎮雇傭兵或借影子）/);
    expect(solo).toMatch(/pnl-callout lock"[^>]*data-testid="world-party-boss"[^]*有影子的隊伍不能打賽季頭目/);
    const comp = html(createElement(PartyShadowPanel, { view: view(party(3, { companion_zh: "阿岳跟著你（霧渡新手路），佔 1 個隊友位；任務結束後離隊" })), busy: false, onAct: noop }));
    expect(comp).toMatch(/pnl-callout info"[^>]*data-testid="world-party-companion"/);
  });
  it("我的影子分頁：還沒存＝琥珀標籤＋一行小字；兩格數值；空狀態", () => {
    const tabs = partyShadowTabs(view(party(3)), false, noop);
    const pane = html(tabs.find((t) => t.id === "shadow")!.render() as Parameters<typeof renderToStaticMarkup>[0]);
    expect(pane).toMatch(/<span class="pnl-tag warn"><canvas[^>]*data-icon="warn"[^>]*><\/canvas>還沒存<\/span><span class="pnl-l3">在城鎮休息、換技能等整備時自動存<\/span>/);
    expect(pane).toContain('<span class="k">預設打法</span>');
    expect(pane).toContain('<span class="k">被借用得到的任務幣</span>');
    expect(pane).toContain('<div class="pnl-empty">還沒有人借過你的影子。</div>');
    const saved = partyShadowTabs(view(party(3), { ...SHADOW, saved: true, saved_zh: "霧渡鎮・Lv 3", reports_zh: ["甲借了你的影子"] } as WorldMyShadow), false, noop);
    expect(saved.find((t) => t.id === "shadow")!.badge).toBeNull();
    const savedPane = html(saved.find((t) => t.id === "shadow")!.render() as Parameters<typeof renderToStaticMarkup>[0]);
    expect(savedPane).toContain('<span class="pnl-l2">霧渡鎮・Lv 3</span>');
    expect(savedPane).toContain('data-testid="world-shadow-reports"');
  });
  it("只有一邊的資料時只有一頁、不畫分頁列；都沒有時不畫", () => {
    expect(html(createElement(PartyShadowPanel, { view: view(null), busy: false, onAct: noop }))).not.toContain("tablist");
    expect(html(createElement(PartyShadowPanel, { view: view(null, null), busy: false, onAct: noop }))).toBe("");
  });
  it("接線：HUD 的 Y 面板用新面板、WorldScreen 傳 onClose", () => {
    expect(readFile(SRC_DIR, "world/HudPanels.tsx")).toContain("<PartyShadowPanel view={view} busy={busy} onAct={onAct} onClose={onClose} />");
    expect(readFile(SRC_DIR, "screens/WorldScreen.tsx")).toContain("<HudShadowPanel view={v} busy={busy} onAct={act} onClose={closeHud} />");
  });
});

describe("CSS（3.1、3.2）", () => {
  it("文字三級、提示三級的色", () => {
    expect(css).toContain("--pnl-l3: #a39d8c;");
    expect(css).toContain("--pnl-l2: #bdb5a2;");
    expect(css).toContain("--pnl-warn: #e8b45a;");
    expect(css).toContain("--pnl-lock: #b9b0e8;");
    expect(css).toContain("--pnl-lock-bar: #8a80c0;");
    expect(css).toContain("--pnl-info: #8cd0e4;");
    expect(css).toContain("--pnl-info-bar: #4ab0d0;");
  });
  it("窄版看面板寬（容器查詢 < 560）：隊友卡兩欄、第 3 張撐滿；「預設（守衛）」不斷行", () => {
    expect(css).toMatch(/\.world-hud-panel \{\s*container: world-panel \/ inline-size;\s*\}/);
    const at = css.indexOf("@container world-panel (max-width: 559px)");
    expect(at).toBeGreaterThan(-1);
    const block = css.slice(at, css.indexOf("}\n}", at) + 3);
    expect(block).toContain(".pnl-members { grid-template-columns: repeat(2, minmax(0, 1fr)); }");
    expect(block).toContain(".pnl-members > .pnl-member:last-child:nth-child(odd) { grid-column: 1 / -1; }");
    expect(css).toMatch(/\.pnl-member \.ai b \{[^}]*white-space: nowrap/);
  });
  it("分頁列：字寬照粗體預留、四級的 class、目前分頁的亮金上緣", () => {
    expect(css).toMatch(/\.pnl-tab \.lbl-s::after \{[^}]*content: attr\(data-t\);[^}]*font-weight: 700;/);
    expect(css).toContain(".pnl-tabbar.fit1 .pnl-tab .lbl-s { display: inline-flex; }");
    expect(css).toContain(".pnl-tabbar.fit3 { flex-wrap: wrap; row-gap: 2px; }");
    expect(rule(".pnl-tab.on::before")).toContain("background: var(--ui-gold-hi)");
  });
  it("固定區不捲（sticky、在上緣漸隱之上）；有固定區時「×」擺到外框右上", () => {
    expect(rule(".pnl-fixed")).toMatch(/position: sticky;[^]*top: 0;[^]*z-index: 6;/);
    expect(rule(".world-hud-panel:has(.pnl-fixed) > .ui-popup-body > .world-hud-panel-close")).toContain("position: absolute");
  });
  it("清單、卡片不描框（淡底）；描框只在主角／夥伴卡、空狀態", () => {
    expect(rule(".pnl-row")).not.toContain("border:");
    expect(rule(".pnl-stat")).not.toContain("border:");
    expect(css).toMatch(/\.pnl-member\.hero \{ box-shadow: inset 0 0 0 1px/);
    expect(css).toMatch(/\.pnl-member\.comp \{ box-shadow: inset 0 0 0 1px/);
  });
});
