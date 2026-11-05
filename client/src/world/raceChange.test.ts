// 6R-1（#138）：這一季的免費換種族那一行。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { parseRaceNames, RACE_NAMES } from "../run/createTexts";
import { raceChangeAction, raceChangeOptions, RaceChangeLine } from "./RaceChange";

const character = (over: Partial<WorldView["character"]>): WorldView["character"] =>
  ({ race: "fox", race_name_zh: "獸耳族", free_race_change: true, free_race_change_zh: null, ...over }) as WorldView["character"];

describe("免費換種族（6R-1）", () => {
  it("種族名稱照 races.yaml，獸耳族是 fox", () => {
    expect(RACE_NAMES.length).toBe(10);
    expect(RACE_NAMES.find((r) => r.id === "fox")?.name).toBe("獸耳族");
    expect(parseRaceNames(":::")).toEqual([]);
  });

  it("選單去掉目前的種族；動作是 change_race", () => {
    const options = raceChangeOptions("fox");
    expect(options.map((o) => o.id)).not.toContain("fox");
    expect(options.length).toBe(9);
    expect(raceChangeAction("elf")).toEqual({ kind: "change_race", race: "elf" });
  });

  it("不在主城時按鈕灰掉並顯示原因", () => {
    const html = renderToStaticMarkup(createElement(RaceChangeLine, { character: character({ free_race_change_zh: "只有在主城能換種族" }), busy: false, onAct: () => undefined }));
    expect(html).toContain("本季可以免費換一次種族");
    expect(html).toContain("只有在主城能換種族");
    expect(html).toMatch(/<button[^>]*disabled/);
  });

  it("在主城時可以按", () => {
    const html = renderToStaticMarkup(createElement(RaceChangeLine, { character: character({}), busy: false, onAct: () => undefined }));
    expect(html).not.toMatch(/<button[^>]*disabled/);
    expect(html).toContain("精靈");
  });
});
