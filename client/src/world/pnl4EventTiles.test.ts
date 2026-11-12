// PNL-4（docs/art/資訊面板-移植需求.md 3.4、3.5、改字 #34）：事件卡選項列 A（SolutionTile／SolutionGrid）、主字斷詞、
// 次行、放棄右下小鈕、「用〔…〕抵」小鈕、說明卡數字不斷行（KeepNum）、隊友加入對話框的說話者頭像、劇情夥伴頭像、
// 覺醒插圖照顯示寬出圖、判定列在 800×600 不換行、舊事件卡畫法（dev/eventLegacy.ts）已刪。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldEventSolution, WorldPartyIntro, WorldView } from "../api/types";
import { AWAKEN_W, awakenArtFallback, awakenArtScale, EVENT_ART_W, eventArtScale } from "../render/eventArt";
import { readFile, readSources, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { mateCards } from "./hud";
import { INTRO_FACE, PartyIntroDialog } from "./PartyIntroDialog";
import { GLUE_WORD_MAX, glueTail, solutionSub, splitSolutions, tileMain, wordBreaks } from "./solutionGrid";
import { REVEAL_MARGIN, revealBottomDelta } from "../ui/scrollReveal";
import { HintBody, SolutionGrid, TILE_ATTR_ICON, TILE_ICON } from "./SolutionTile";

function sol(kind: string, note = "", attrs = "", over: Partial<WorldEventSolution> = {}): WorldEventSolution {
  const kindZh: Record<string, string> = { situation: "情境判定", combat: "戰鬥", parley: "交涉", abandon: "放棄", opportunity: "機遇" };
  return { index: 0, kind, kind_zh: kindZh[kind] ?? kind, note_zh: note, attributes_zh: attrs, cost_supplies: 0, available: true, template: kind === "situation" ? "t" : null, hint_zh: "", ...over } as WorldEventSolution;
}
const html = (solutions: WorldEventSolution[], openTemplate: string | null = null): string =>
  renderToStaticMarkup(createElement(SolutionGrid, { solutions, busy: false, openTemplate, onOpen: () => undefined, onSolve: () => undefined }));
const css = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
const allCss = Object.values(css).join("\n");
const storyCss = stripCssComments(readFile(SRC_DIR, "world/story.css"));

describe("主字斷詞（樣張 wordBreaks）", () => {
  const seg = new Intl.Segmenter("zh-Hant", { granularity: "word" });
  it("有標點也照詞切（和樣張不同）：收尾標點黏前一個詞、開頭標點黏下一個詞，不會落到行首／行尾", () => {
    for (const text of ["亮出商隊旗號，談條件", "交材料（用補給代替黑曜片）", "賭一把，丟下貨物引開", "說服（獸耳族主角有專屬對話選項，不加數值）"]) {
      const words = wordBreaks(text, seg);
      expect(words.join("")).toBe(text);
      for (const w of words.slice(1)) expect(w).not.toMatch(/^[，、；：）」。！？]/u);
      for (const w of words.slice(0, -1)) expect(w).not.toMatch(/[（「]$/u);
    }
    expect(wordBreaks("賭一把，丟下貨物引開", seg)[0]).toBe("賭一把，");
  });
  it("收尾標點黏住整個詞（PNL-4b 可修 1）；比 GLUE_WORD_MAX 長的詞只黏最後一個字（詞比一行長才任意斷）", () => {
    expect(GLUE_WORD_MAX).toBe(5);
    expect(glueTail("旗號，")).toEqual({ head: "", tail: "旗號，" });
    expect(glueTail("黑曜片）")).toEqual({ head: "", tail: "黑曜片）" });
    expect(glueTail("賭一把，")).toEqual({ head: "", tail: "賭一把，" });
    expect(glueTail("亮出商隊旗號，")).toEqual({ head: "亮出商隊旗", tail: "號，" });
    expect(glueTail("談條件")).toEqual({ head: "談條件", tail: "" });
    expect(glueTail("，")).toEqual({ head: "，", tail: "" });
    expect(storyCss).toMatch(/\.world-sol-glue \{\s*white-space: nowrap;/);
  });
  it("連續單字湊到兩字以上自成一詞（Chrome 把「亮出商隊」切成四個單字；PNL-4b）：「亮出商隊<wbr>旗號，<wbr>談條件」", () => {
    const chrome = { segment: () => ["亮", "出", "商", "隊", "旗號", "，", "談", "條件"].map((segment) => ({ segment })) } as unknown as Intl.Segmenter;
    expect(wordBreaks("亮出商隊旗號，談條件", chrome)).toEqual(["亮出商隊", "旗號，", "談條件"]);
    expect(wordBreaks("亮出商隊旗號，談條件", seg)).toEqual(["亮出商隊", "旗號，", "談條件"]);
    expect(wordBreaks("衝過去撞開路障", seg)).toEqual(["衝過去", "撞開", "路障"]);
    const out = html([sol("situation", "亮出商隊旗號，談條件", "意志")]);
    expect(out).toContain('亮出商隊<wbr/><span class="world-sol-glue">旗號，</span><wbr/>談條件');
  });
  it("沒有標點：切成詞，接起來等於原句；單字的詞併進下一個詞（不會斷成「談／條件」）", () => {
    for (const text of ["悄悄退出", "衝過去撞開路障", "先看清他們的人數", "談條件", "用自己的話回答"]) {
      const words = wordBreaks(text, seg);
      expect(words.join("")).toBe(text);
      expect(words.length).toBeGreaterThan(0);
      if (words.length > 1) for (const w of words.slice(0, -1)) expect([...w].length).toBeGreaterThan(1);
    }
    expect(wordBreaks("談條件", seg)[0]?.startsWith("談條")).toBe(true);
  });
  it("沒有 Intl.Segmenter：整句一段", () => {
    expect(wordBreaks("悄悄退出", null)).toEqual(["悄悄退出"]);
  });
});

describe("次行（改字 #34）", () => {
  it("情境判定：種類・屬性（兩個用「／」）；交涉：種類＋補給；戰鬥、放棄不重複種類名", () => {
    expect(solutionSub(sol("situation", "攀爬", "力量／敏捷"))).toEqual({ kind: "情境判定", attrs: [{ name: "力量", key: "str" }, { name: "敏捷", key: "dex" }], cost: null });
    expect(solutionSub(sol("parley", "付錢", "", { cost_supplies: 1 }))).toEqual({ kind: "交涉", attrs: [], cost: 1 });
    expect(solutionSub(sol("opportunity", "賭一把"))).toEqual({ kind: "機遇", attrs: [], cost: null });
    expect(solutionSub(sol("combat", "和他們打一場"))).toBeNull();
    expect(solutionSub(sol("abandon", "不管了"))).toBeNull();
    expect(tileMain(sol("combat", "和他們打一場"))).toBe("戰鬥");
  });
  it("不認得的屬性名只寫字", () => {
    expect(solutionSub(sol("situation", "看", "運氣"))?.attrs).toEqual([{ name: "運氣", key: null }]);
  });
  it("放棄分出去，其他照伺服器順序", () => {
    const list = [sol("situation", "a"), { ...sol("abandon"), index: 1 }, { ...sol("combat"), index: 2 }];
    const { tiles, leave } = splitSolutions(list);
    expect(tiles.map((s) => s.index)).toEqual([0, 2]);
    expect(leave.map((s) => s.index)).toEqual([1]);
  });
});

describe("選項格版面（需求 3.4）", () => {
  it("兩欄等寬、剩一格撐滿整列（CSS），同一列等高；主字兩行「…」、keep-all＋anywhere", () => {
    expect(storyCss).toMatch(/\.world-sol-grid \{[^}]*display: grid;[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
    expect(storyCss).toMatch(/\.world-sol-grid > \.world-sol-cell:last-child:nth-child\(odd\) \{\s*grid-column: 1 \/ -1;/);
    expect(storyCss).toMatch(/\.world-sol-main \{[^}]*-webkit-line-clamp: 2;[^}]*word-break: keep-all;[^}]*overflow-wrap: anywhere;/);
    expect(allCss).not.toMatch(/\.world-solution-group\b/);
  });
  it("一格＝圖示 24＋主字＋次行（屬性圖 14＋名）；說明卡全文；開著的情境判定那格亮起", () => {
    const out = html([sol("situation", "攀爬", "力量／敏捷", { hint_zh: "回答得用心可以加分（最多 +2）" }), { ...sol("abandon"), index: 1 }], "t");
    expect(TILE_ICON).toBe(24);
    expect(TILE_ATTR_ICON).toBe(14);
    expect(out).toContain('class="world-sol-grid"');
    expect(out).toContain('class="world-solution world-sol primary"');
    expect(out).toContain("情境判定");
    expect(out).toContain('data-attr="str"');
    expect(out).toContain('data-attr="dex"');
    expect(out).toContain('<span class="world-sol-sep">／</span>');
    expect(out).toContain('aria-label="硬闖：攀爬"');
  });
  it("放棄：右下小鈕（不在格子裡）", () => {
    const out = html([sol("combat"), { ...sol("abandon"), index: 1 }]);
    const grid = out.slice(out.indexOf('class="world-sol-grid"'), out.indexOf('class="world-sol-foot"'));
    expect(grid).toContain('data-kind="combat"');
    expect(grid).not.toContain('data-kind="abandon"');
    expect(out.slice(out.indexOf('class="world-sol-foot"'))).toMatch(/class="world-solution world-sol-leave"[^>]*data-kind="abandon"/);
  });
  it("只有放棄：沒有空格子", () => {
    expect(html([sol("abandon")])).not.toContain("world-sol-grid");
  });
  it("「用〔…〕抵」：同一格裡的小鈕＋次行讓出同字寬度，不另佔一格", () => {
    const out = html([sol("parley", "付錢", "", { cost_supplies: 1, waive_thread: "th1", waive_zh: "商人欠你人情" })]);
    expect(out).toContain('class="world-sol-cell has-waive"');
    expect(out).toContain('<span class="world-sol-waive-ghost" aria-hidden="true">用〔商人欠你<span class="world-sol-glue">人情〕抵</span></span>');
    expect(out).toMatch(/class="world-sol-waive"[^>]*data-testid="world-solution-waive">用〔商人欠你<span class="world-sol-glue">人情〕抵<\/span><\/button>/);
    expect(out).toContain("−1 補給");
    expect(out.match(/data-testid="world-solution-cell"/g)?.length).toBe(1);
  });
  it("「用〔…〕抵」不伸出字欄（PNL-4b 必修 1）：小鈕最寬＝字欄寬、可在鈕裡換行，同字照同樣寬度換行；右緣下緣對齊字欄", () => {
    const blocks = new Map([...storyCss.matchAll(/([^{}]+)\{([^}]*)\}/g)].map((m) => [m[1]!.trim(), m[2]!] as const));
    const rule = (sel: string): string => blocks.get(sel) ?? "";
    const px = (block: string, prop: string): string => block.match(new RegExp(`(?:^|\\s)${prop}: ([^;]+);`))?.[1]?.trim() ?? "";
    const cell = rule(".world-sol-cell");
    const tile = rule(".world-sol");
    const [padT, padR, padB, padL] = px(tile, "padding").split(/\s+/).map((v) => Number.parseFloat(v));
    const gap = Number.parseFloat(px(tile, "gap"));
    const border = 1; // base.css 按鈕框
    // 字欄左緣＝左內距＋框＋圖示＋間距
    expect(px(cell, "--sol-waive-inset")).toBe(`${padL! + border + TILE_ICON + gap}px`);
    const shared = rule(".world-sol-waive-ghost,\n.world-sol-waive");
    expect(px(shared, "white-space")).toBe("normal");
    expect(px(shared, "max-width")).toBe("100%");
    const btn = rule(".world-sol-waive");
    expect(px(btn, "max-width")).toBe(`calc(100% - var(--sol-waive-inset) - ${padR! + border}px)`);
    expect(px(btn, "margin")).toBe(`0 ${padR! + border}px ${padB! + border}px 0`);
    expect(padT).toBe(padB);
    // 小鈕左緣 ≥ 字欄左緣：離圖示 ≥ gap（6）≥ 2、離左框 ≥ inset − 1 ≥ 4；右、下各離框 padR／padB ≥ 4
    expect(gap).toBeGreaterThanOrEqual(2);
    expect(padR).toBeGreaterThanOrEqual(4);
    expect(padB).toBeGreaterThanOrEqual(4);
    expect(px(rule(".world-sol-waive-ghost"), "visibility")).toBe("hidden");
  });
  it("說明卡：「詞＋數字」包成不斷行（KeepNum）", () => {
    const out = renderToStaticMarkup(createElement(HintBody, { text: "情境判定：說服\n回答得用心可以加分（最多 +2）" }));
    expect(out).toContain('class="hint-tip-text"');
    expect(out).toContain('class="pnl-nowrap"');
    expect(out).toMatch(/<span class="pnl-nowrap">[^<]*\+2<\/span>/);
  });
  it("事件卡的說明卡（選項、線索、引用）都經 HintBody", () => {
    const ev = stripTsComments(readFile(SRC_DIR, "world/EventCard.tsx"));
    expect(ev).toContain("rich={<HintBody text={clueHint(facts.length)} />}");
    expect(ev).toContain("rich={<HintBody text={citeHint(f)} />}");
    const tile = stripTsComments(readFile(SRC_DIR, "world/SolutionTile.tsx"));
    expect(tile.match(/rich=\{<HintBody text=\{hint\} \/>\}/g)?.length).toBe(2);
  });
});

describe("800×600 判定列（QI-6 驗收觀察）", () => {
  it("說明字先縮，DC、屬性、線索留在同一行；打開判定時把到「擲骰」那一列捲進可視範圍", () => {
    expect(storyCss).toMatch(/\.world-situation-note \{\s*flex: 1 1 3em;/);
    const ev = stripTsComments(readFile(SRC_DIR, "world/EventCard.tsx"));
    expect(ev).toContain("const reveal = () => revealBottomInScroller(el, actions.current);");
    expect(ev).toContain("const timer = window.setTimeout(stop, SETTLE_MS);");
    expect(ev).toMatch(/for \(const ev of \["wheel", "pointerdown", "keydown", "touchstart"\]\) scroller\.addEventListener\(ev, stop/);
    expect(ev).toContain('<div className="world-situation" ref={form} data-testid="world-situation">');
  });
  it("revealBottomDelta：放得下整段都看得到；放不下時先對齊下緣（擲骰那一列），上緣只讓 8", () => {
    const view = { top: 100, bottom: 500 };
    expect(revealBottomDelta(view, { top: 200, bottom: 400 })).toBe(0);
    expect(revealBottomDelta(view, { top: 300, bottom: 520 })).toBe(520 - 460);
    expect(revealBottomDelta(view, { top: 50, bottom: 300 })).toBe(50 - 108);
    expect(revealBottomDelta(view, { top: 150, bottom: 700 })).toBe(700 - 460); // 比可視範圍高：下緣對齊
    expect(revealBottomDelta(view, { top: 150, bottom: 700 }, 8, REVEAL_MARGIN)).toBe(240);
  });
});

describe("隊友加入的對話框：說話者頭像（OB-8，需求 3.5）", () => {
  const PORTRAIT = { look: { skin: "#f1c9a5", hair: "short", hair_color: "#c8a868" } };
  const intro = {
    seen_id: "intro:m",
    member: "m",
    name_zh: "甲",
    lines: [
      { speaker_zh: "乙", text_zh: "一。", portrait: PORTRAIT, region: "capital" },
      { speaker_zh: "甲", text_zh: "二。", portrait: null, region: null },
      { speaker_zh: "甲", text_zh: "三。" },
    ],
  } as unknown as WorldPartyIntro;
  const out = renderToStaticMarkup(createElement(PartyIntroDialog, { intro, onClose: () => undefined }));
  it("每句一個 48 的頭像（同一人連續兩句也各一個），框色照伺服器的 region", () => {
    expect(INTRO_FACE).toBe(48);
    expect(out.match(/data-testid="party-intro-line"/g)?.length).toBe(3);
    expect(out.match(/class="story-portrait"/g)?.length).toBe(3);
    expect(out).toContain('data-region="capital"');
    expect(out.match(/width:48px;height:48px|width="48"/g)?.length).toBeGreaterThanOrEqual(2);
  });
  it("沒有頭像：通用剪影", () => {
    expect(out.match(/data-portrait="silhouette"/g)?.length).toBeGreaterThanOrEqual(2);
  });
  it("前端不用名字查頭像（只讀 line.portrait／line.region）", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/PartyIntroDialog.tsx"));
    expect(src).toContain("portrait={line.portrait ?? null} region={line.region ?? null}");
    expect(src).not.toMatch(/speaker_zh\s*===/);
  });
});

describe("劇情夥伴頭像（PNL-1a 驗收可修 3）", () => {
  it("HUD 隊友小卡與隊伍面板：夥伴用伺服器給的 portrait／region；傭兵照名冊", () => {
    const portrait = { look: { skin: "#fff" } };
    const view = {
      party: {
        members: [
          { name_zh: "主角", title_zh: "主角", level: 1 },
          { name_zh: "阿岳", title_zh: "獵戶・劇情夥伴", level: 1, companion: "companion_ayue", portrait, region: "cloud_ridge" },
          { name_zh: "賽倫", title_zh: "盾衛", level: 1, mercenary: "merc_tiebi" },
        ],
        mercenaries: [{ id: "merc_tiebi", origin: "crystal_crown", portrait: null }],
      },
    } as unknown as WorldView;
    const cards = mateCards(view);
    expect(cards[0]).toMatchObject({ name: "阿岳", portrait, origin: "cloud_ridge" });
    expect(cards[1]).toMatchObject({ name: "賽倫", portrait: null, origin: "crystal_crown" });
    const panel = stripTsComments(readFile(SRC_DIR, "world/PartyShadowPanel.tsx"));
    expect(panel).toContain("portrait={merc?.portrait ?? m.portrait ?? null} region={merc?.origin ?? m.region ?? \"merc\"}");
  });
});

describe("覺醒插圖照顯示寬出圖（QI-6 待決 2）", () => {
  it("畫布寬 ＝ 顯示寬 × 裝置像素比；量不到時退回舊的 ×4（DPR 最多算 2）", () => {
    expect(awakenArtScale(460, 1) * AWAKEN_W).toBe(460);
    expect(awakenArtScale(339.7, 1) * AWAKEN_W).toBe(340);
    expect(awakenArtScale(400, 1.5) * AWAKEN_W).toBe(600);
    expect(awakenArtScale(0, 1)).toBe(2);
    expect(awakenArtScale(0, 2)).toBe(4);
    expect(awakenArtFallback(3)).toBe(4);
    expect(eventArtScale(364, 1) * EVENT_ART_W).toBe(364); // 事件插圖同一個算法
  });
  it("OpeningDialog 的 AwakenArt 用 ResizeObserver 量畫布寬", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/OpeningDialog.tsx"));
    expect(src).toContain("setScale(awakenArtScale(c.getBoundingClientRect().width, window.devicePixelRatio || 1))");
    expect(src).toContain("new ResizeObserver(measure)");
    expect(src).not.toMatch(/Math\.min\(2, window\.devicePixelRatio \|\| 1\) \* 2/);
  });
});

describe("舊事件卡畫法（QI-6 留給開發頁對照）已刪", () => {
  it("dev/eventLegacy.ts 不在了，開發頁也不再引用", () => {
    const files = readSources().map(([p]) => p);
    expect(files).toContain("dev/eventGallery.ts");
    expect(files).not.toContain("dev/eventLegacy.ts");
    expect(stripTsComments(readFile(SRC_DIR, "dev/eventGallery.ts"), "g.ts")).not.toMatch(/eventLegacy|LEGACY_ICON|現行｜Q/);
  });
});
