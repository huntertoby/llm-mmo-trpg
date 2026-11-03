import { describe, expect, it } from "vitest";
import type { AbsenceView } from "../api/types";
import { absenceKindLabel, newsSeenAction, shouldShowAbsence } from "./absence";

const view: AbsenceView = {
  since: 100,
  as_of: 900,
  items: [
    { kind: "world_event", at: 500, text_zh: "世界事件「霧潮入侵」失敗（0／30），灰燼荒原建議等級 +1。" },
    { kind: "opened", at: 500, text_zh: "「往灰燼荒原的渡口」開放了，可以前往灰燼荒原。" },
  ],
};

describe("absence summary", () => {
  it("only shows when there is news", () => {
    expect(shouldShowAbsence(view)).toBe(true);
    expect(shouldShowAbsence({ ...view, items: [] })).toBe(false);
    expect(shouldShowAbsence(null)).toBe(false);
  });

  it("acknowledges up to as_of", () => {
    expect(newsSeenAction(view)).toEqual({ kind: "news_seen", until: 900 });
  });

  it("labels each kind", () => {
    expect(absenceKindLabel("world_event")).toBe("世界事件");
    expect(absenceKindLabel("bounty")).toBe("懸賞");
    expect(absenceKindLabel("opened")).toBe("新區域");
    expect(absenceKindLabel("other")).toBe("消息");
  });
});
