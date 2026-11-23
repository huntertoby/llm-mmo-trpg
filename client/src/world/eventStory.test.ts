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
