// 任務追蹤的新手指引、方向與建議（6F-2，筆記 U2～U4）；開場只跳一次（#125）。
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { TRACKER_EMPTY, trackHint, trackedQuests } from "./hud";
import { openingKey, readOpeningSeen, shouldShowOpening, writeOpeningSeen } from "./OpeningDialog";

const guide = {
  text_zh: "到霧渡鎮找渡婆婆",
  how_zh: "站上中央廣場的傳送陣",
  opening: [
    { speaker_zh: "說書人", text_zh: "傳送陣的光暗了下去。" },
    { speaker_zh: "守印人", text_zh: "新來的？" },
  ],
};

function view(extra: Partial<WorldView>): WorldView {
  return { quests: [], threads: [], guide: null, ...extra } as unknown as WorldView;
}

const starter = {
  id: "starter_ferry",
  name_zh: "霧渡新手路",
  kind_zh: "新手",
  summary_zh: "",
  giver_zh: "渡婆婆",
  done: false,
  route_zh: "往東邊的出口 → 渡口石階",
  advice_zh: null,
  steps: [
    { text_zh: "渡口石階：趕走搶渡船的盜賊", done: false, current: true },
    { text_zh: "竹林小徑", done: false, current: false },
  ],
};

describe("tracker", () => {
  it("shows the newcomer guide first when the server gives one", () => {
    const lines = trackedQuests(view({ guide }));
    expect(lines).toEqual([{ id: "guide", kind: "guide", name: "到霧渡鎮找渡婆婆", line: "站上中央廣場的傳送陣", route: null, advice: null }]);
    expect(trackHint(lines[0]!)).toBe("指引：到霧渡鎮找渡婆婆・站上中央廣場的傳送陣（點了打開任務面板）");
  });
  it("carries the route and the advice of each quest", () => {
    const main = { ...starter, id: "main_mist_rift", name_zh: "霧中裂痕", kind_zh: "主線", route_zh: null, advice_zh: "建議先完成霧渡新手路" };
    const lines = trackedQuests(view({ quests: [starter, main] as unknown as WorldView["quests"] }));
    const byId = Object.fromEntries(lines.map((l) => [l.id, l]));
    expect(byId.starter_ferry?.route).toBe("往東邊的出口 → 渡口石階");
    expect(byId.main_mist_rift?.advice).toBe("建議先完成霧渡新手路");
    expect(trackHint(byId.starter_ferry!)).toContain("往東邊的出口 → 渡口石階");
  });
  it("empty tracker text points at the「！」", () => {
    expect(TRACKER_EMPTY).toBe("找頭上有「！」的人說話");
    expect(trackedQuests(view({}))).toEqual([]);
  });
});

describe("opening dialog", () => {
  it("shows once per character", () => {
    const data = new Map<string, string>();
    const store = { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) };
    expect(shouldShowOpening(guide, readOpeningSeen("c1", store))).toBe(true);
    writeOpeningSeen("c1", store);
    expect(data.get(openingKey("c1"))).toBe("1");
    expect(shouldShowOpening(guide, readOpeningSeen("c1", store))).toBe(false);
    expect(shouldShowOpening(guide, readOpeningSeen("c2", store))).toBe(true);
    expect(shouldShowOpening({ ...guide, opening: [] }, false)).toBe(false);
    expect(shouldShowOpening(null, false)).toBe(false);
  });
});
