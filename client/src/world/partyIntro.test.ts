// OB-8（#154）：隊友加入的台詞對話框與隊伍面板的來歷行。台詞、名字、來歷全部來自伺服器（這裡用假資料）。
import { createElement, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldPartyIntro, WorldPartyView } from "../api/types";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { PartyIntroDialog, partyIntroShown, partyIntroTitle } from "./PartyIntroDialog";
import { PartyPanel } from "./PartyPanel";

const INTRO: WorldPartyIntro = {
  seen_id: "intro:merc_x",
  member: "merc_x",
  name_zh: "甲",
  lines: [
    { speaker_zh: "乙", text_zh: "第一句。" },
    { speaker_zh: "甲", text_zh: "第二句。" },
  ],
};

const noop = () => undefined;

/** 在元件回傳的 React 元素樹裡找 data-testid 符合的元素（vitest 是 node 環境，沒有 DOM）。 */
function findByTestId(node: ReactNode, id: string): ReactElement<Record<string, unknown>> | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const hit = findByTestId(child as ReactNode, id);
      if (hit !== null) return hit;
    }
    return null;
  }
  if (!isValidElement(node)) return null;
  const el = node as ReactElement<Record<string, unknown>>;
  if (el.props["data-testid"] === id) return el;
  return findByTestId(el.props.children as ReactNode, id);
}

describe("隊友加入的台詞（WorldView.party_intro）", () => {
  it("有 party_intro、有台詞、還沒看過才彈", () => {
    expect(partyIntroShown(INTRO, new Set())).toBe(true);
    expect(partyIntroShown(INTRO, new Set(["intro:other"]))).toBe(true);
  });
  it("沒有 party_intro、沒有台詞、已看過（含這次畫面剛關掉的）都不彈", () => {
    expect(partyIntroShown(null, new Set())).toBe(false);
    expect(partyIntroShown(undefined, new Set())).toBe(false);
    expect(partyIntroShown({ ...INTRO, lines: [] }, new Set())).toBe(false);
    expect(partyIntroShown(INTRO, new Set(["intro:merc_x"]))).toBe(false);
  });
  it("對話框照伺服器的順序寫出每一句（說話的人＋台詞），標題用名字，只有一個「好」", () => {
    const html = renderToStaticMarkup(createElement(PartyIntroDialog, { intro: INTRO, onClose: noop }));
    expect(partyIntroTitle(INTRO)).toBe("甲加入隊伍");
    expect(html).toContain("甲加入隊伍");
    expect(html).toContain('data-member="merc_x"');
    // PNL-4：每句改成「頭像＋粗體名字＋台詞」（開場 AwakenDialog 的排法，頭像測試在 pnl4EventTiles.test.ts）
    const a = html.indexOf("<b>乙</b></div><p class=\"world-awaken-text\">第一句。");
    const b = html.indexOf("<b>甲</b></div><p class=\"world-awaken-text\">第二句。");
    expect(a).toBeGreaterThan(-1);
    expect(b).toBeGreaterThan(a);
    expect(html.match(/data-testid="party-intro-close"/g)?.length).toBe(1);
    expect(html).toContain("decision-head"); // 共用彈窗外框 DialogFrame
  });
  it("按「好」呼叫 onClose；WorldScreen 的 onClose 送 hint_seen [seen_id]", () => {
    let closed = 0;
    const tree = PartyIntroDialog({ intro: INTRO, onClose: () => (closed += 1) });
    const button = findByTestId(tree, "party-intro-close");
    expect(button).not.toBeNull();
    (button?.props.onClick as () => void)();
    expect(closed).toBe(1);
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen).toContain("<PartyIntroDialog intro={partyIntro} onClose={() => markSeen([partyIntro.seen_id])} />");
    const markSeen = screen.slice(screen.indexOf("function markSeen(ids: string[], level?: number) {"));
    expect(markSeen.slice(0, 300)).toContain("act(hintSeenAction(ids, level));");
    // 靶場那段話（RangeDoneDialog）關掉之後才播；播著時升級畫面與教學先等
    expect(screen).toContain("rangeDone === null && !shouldShowAbsence(absence) && !shouldShowOpening(view.guide, seenIds) && partyIntroShown(view.party_intro, seenIds)");
    expect(screen.match(/partyIntro === null && (showLevelUp|!showLevelUp && showLesson)/g)?.length).toBe(3);
  });
  it("前端不寫死台詞與名字", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/PartyIntroDialog.tsx"));
    for (const word of ["賽倫", "阿岳", "守印人", "merc_tiebi", "companion_ayue"]) expect(src).not.toContain(word);
  });
});

function party(backstory: (string | null | undefined)[]): WorldPartyView {
  return {
    members: [
      { name_zh: "主角甲", title_zh: "主角", level: 1, mercenary: null },
      ...backstory.map((b, i) => ({ name_zh: `隊友${i}`, title_zh: "x", level: 1, mercenary: `m${i}`, ...(b === undefined ? {} : { backstory_zh: b }) })),
    ],
    max_hired: 2,
    can_hire: true,
    hire_problem_zh: null,
    mercenaries: [],
    shadows: [],
    ai_choices: [],
    ai: {},
    season_boss_ok: true,
    free_slots: 0,
  };
}

describe("隊伍面板的來歷行（PartyMemberView.backstory_zh）", () => {
  it("有來歷的成員在名字那一列下面多一行", () => {
    const html = renderToStaticMarkup(createElement(PartyPanel, { party: party(["守著你的人。"]) }));
    expect(html.match(/data-testid="world-party-backstory"/g)?.length).toBe(1);
    expect(html).toMatch(/隊友0[^]*<div class="muted world-party-backstory" data-testid="world-party-backstory">守著你的人。<\/div><\/li>/);
  });
  it("沒有來歷（null、沒給、空字串）就沒有這一行", () => {
    const html = renderToStaticMarkup(createElement(PartyPanel, { party: party([null, undefined, ""]) }));
    expect(html).not.toContain("world-party-backstory");
  });
});
