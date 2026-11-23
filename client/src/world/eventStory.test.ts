// WM-1 第 4 項：地點事件先回畫面、旁白之後補上（前端：占位、要不要補、補上之後只換 `event`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldEventView, WorldView } from "../api/types";
import { EventCard } from "./EventCard";
import { pendingStoryKey, STORY_PENDING_ZH, withStory } from "./eventStory";

const STORY = { text_zh: "石階上，一名行商抱著貨箱喘氣。", more_zh: "", source: "llm" as const };

function event(over: Partial<WorldEventView> = {}): WorldEventView {
  return {
    skeleton: "wounded_peddler",
    location_name_zh: "渡口石階",
    actor_zh: "受傷的行商",
    motive_zh: "回霧渡鎮",
    story: null,
    story_pending: true,
    who_zh: "",
    want_zh: "",
    obstacle_zh: "",
    stakes_zh: "",
    solutions: [],
    leave_zh: "離開",
    art_url: null,
    ...over,
  };
}

function view(ev: WorldEventView | null, me = { x: 1, y: 1 }): WorldView {
  return { event: ev, field: { map_id: "ferry_steps", me: { ...me, facing: "e" } } } as unknown as WorldView;
}

const card = (ev: WorldEventView) => renderToStaticMarkup(createElement(EventCard, { event: ev, busy: false, onOpen: () => undefined, onSolve: () => undefined, onAnswer: () => undefined }));

describe("WM-1 旁白後補", () => {
  it("旁白還沒來：事件卡畫占位；來了換成旁白、占位消失", () => {
    const waiting = card(event());
    expect(waiting).toContain('data-testid="world-event-story-pending"');
    expect(waiting).toContain(STORY_PENDING_ZH);
    const done = card(event({ story: STORY, story_pending: false }));
    expect(done).toContain('data-testid="world-event-story"');
    expect(done).not.toContain("world-event-story-pending");
  });

  it("WM-1 小修：占位就畫同一個說書人框（頭像、名字），框裡是灰色的占位句；補上後同一個框、同一個文字區", () => {
    const waiting = card(event());
    const done = card(event({ story: STORY, story_pending: false }));
    // 框的開頭（外框 class、頭像、名字）：從外框的 data-testid 到文字區之前，兩邊要一樣
    const head = (html: string, id: string) => {
      const at = html.indexOf(`data-testid="${id}"`);
      expect(at).toBeGreaterThan(-1);
      const open = html.lastIndexOf("<div", at);
      const body = html.slice(html.indexOf(">", at) + 1, html.indexOf('class="world-dialog-text', at));
      return { open: html.slice(open, at), body };
    };
    const pending = head(waiting, "world-event-story-pending");
    const filled = head(done, "world-event-story");
    expect(pending.open).toContain('class="world-dialog world-dialog-pending"');
    expect(filled.open).toContain('class="world-dialog"');
    expect(pending.body).toContain("<b>說書人</b>");
    expect(pending.body.replace(/<div class="world-dialog-name small"><b>說書人<\/b>.*$/su, "")).toBe(
      filled.body.replace(/<div class="world-dialog-name small"><b>說書人<\/b>.*$/su, ""),
    );
    // 文字區同一個 class（事件卡裡至少兩行，story.css），占位是灰色的
    expect(waiting).toMatch(/class="world-dialog-text world-dialog-placeholder"[^>]*>說書人正在構思這段故事……</u);
    expect(done).toContain('class="world-dialog-text"');
    // 框以外的卡片內容（選項列）一樣
    const tail = (html: string) => html.slice(html.indexOf("world-sol"));
    expect(tail(waiting)).toBe(tail(done));
  });

  it("QF-7（ak）：只有一段旁白又有「多講一點」：占位和補上是同一個框、都留「多講一點」那一列，框以外逐字相同", () => {
    const ONE_MORE = { text_zh: "石階上，一名行商抱著貨箱喘氣。", more_zh: "他的腳踝腫得發亮。", source: "llm" as const };
    const waiting = card(event());
    const done = card(event({ story: ONE_MORE, story_pending: false }));
    const plain = card(event({ story: STORY, story_pending: false }));
    // 框：從外框的 <div 到外框結束（說書人框裡沒有巢狀的 world-dialog）
    const frame = (html: string, id: string) => {
      const at = html.indexOf(`data-testid="${id}"`);
      expect(at).toBeGreaterThan(-1);
      const start = html.lastIndexOf("<div", at);
      const end = html.indexOf('<div class="world-event-solutions"', at);
      expect(end).toBeGreaterThan(at);
      return { start, end, inner: html.slice(start, end) };
    };
    const p = frame(waiting, "world-event-story-pending");
    const d = frame(done, "world-event-story");
    const n = frame(plain, "world-event-story");
    // 同一個框：外框、頭像、名字、文字區、「多講一點」那一列的結構一樣（只差文字與狀態屬性）
    const shape = (s: string) =>
      s
        .replace(/>[^<]*</gu, "><")
        .replace(/ (data-[a-z-]+|aria-[a-z-]+|disabled|tabindex|style)(="[^"]*")?/gu, "")
        .replace(/ class="([^"]*)"/gu, (_m, c: string) => ` class="${c.split(" ").filter((x) => !["world-dialog-pending", "world-dialog-placeholder", "world-more-slot"].includes(x)).join(" ")}"`)
        .replace(/<button type="button" class="world-dialog-text">/gu, '<div class="world-dialog-text">')
        .replace(/<\/button><button/gu, "</div><button");
    expect(shape(p.inner)).toBe(shape(d.inner));
    expect(shape(n.inner)).toBe(shape(d.inner));
    // 「多講一點」：補上後是真的按鈕；占位、沒有補充時是同一顆看不見的留位
    expect(d.inner).toContain('data-testid="world-event-story-more"');
    expect(p.inner).toMatch(/<button type="button" class="world-more-btn small world-more-slot" disabled="" tabindex="-1" aria-hidden="true">多講一點<\/button>/u);
    expect(n.inner).toContain("world-more-slot");
    expect(d.inner).not.toContain("world-more-slot");
    // 框以外的內容逐字相同
    expect(waiting.slice(0, p.start)).toBe(done.slice(0, d.start));
    expect(waiting.slice(p.end)).toBe(done.slice(d.end));
  });

  it("沒有在等旁白（LLM 關著已經寫好、或沒有事件）時不送", () => {
    expect(pendingStoryKey("c1", view(event()))).toBe("c1|wounded_peddler|渡口石階");
    expect(pendingStoryKey("c1", view(event({ story: STORY, story_pending: false })))).toBeNull();
    expect(pendingStoryKey("c1", view(event({ story_pending: false })))).toBeNull();
    expect(pendingStoryKey("c1", view(null))).toBeNull();
    expect(pendingStoryKey(null, view(event()))).toBeNull();
  });

  it("補上之後只換 event：走路的回應已經把位置往前更新了，不被補旁白的舊位置蓋掉", () => {
    const now = view(event(), { x: 5, y: 1 });
    const filled = view(event({ story: STORY, story_pending: false }), { x: 3, y: 1 });
    const merged = withStory(now, filled);
    expect(merged.event?.story).toEqual(STORY);
    expect(merged.field?.me).toMatchObject({ x: 5, y: 1 });
  });

  it("事件已經換了、或已經有旁白：不動目前的畫面", () => {
    const filled = view(event({ story: STORY, story_pending: false }));
    const other = view(event({ skeleton: "gang_toll" }));
    expect(withStory(other, filled)).toBe(other);
    const gone = view(null);
    expect(withStory(gone, filled)).toBe(gone);
    const already = view(event({ story: { ...STORY, text_zh: "別的" }, story_pending: false }));
    expect(withStory(already, filled)).toBe(already);
  });
});
