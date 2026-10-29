import { describe, expect, it } from "vitest";
import type { OriginOption, RaceOption, StartOptions } from "../api/types";
import { hasRaceOrigin, originCardLines, raceCardLines, raceOriginBody, raceOriginDone, raceOriginText, raceSummary } from "./raceOrigin";

const race: RaceOption = {
  id: "elf",
  name_zh: "精靈",
  home_realm: "cloud_ridge",
  home_realm_name_zh: "雲嶺",
  skill_name_zh: "林隱",
  skill_description_zh: "站在草叢或黑暗中時，立刻進入隱蔽。",
  skill_ap: 1,
  skill_uses: 2,
  passive_name_zh: "林間視野",
  passive_description_zh: "森林地圖視線 +1。",
};
const origin: OriginOption = { id: "origin_cloud_ridge", name_zh: "雲嶺出身", realm: "cloud_ridge", realm_name_zh: "雲嶺", description_zh: "來自薄霧籠罩的青石山嶺。" };
const options = { weapons: [], keywords: [], keyword_count: 2, races: [race], origins: [origin] } as StartOptions;

describe("開局的種族與出身", () => {
  it("沒有種族資料的選項不顯示這一步，也不擋開局", () => {
    const none = { weapons: [], keywords: [], keyword_count: 2, races: [], origins: [] } as StartOptions;
    expect(hasRaceOrigin(none)).toBe(false);
    expect(hasRaceOrigin(null)).toBe(false);
    expect(raceOriginDone(none, { race: "", origin: "" })).toBe(true);
  });

  it("有種族資料時兩個都要選才算好", () => {
    expect(hasRaceOrigin(options)).toBe(true);
    expect(raceOriginDone(options, { race: "", origin: "" })).toBe(false);
    expect(raceOriginDone(options, { race: "elf", origin: "" })).toBe(false);
    expect(raceOriginDone(options, { race: "", origin: "origin_cloud_ridge" })).toBe(false);
    expect(raceOriginDone(options, { race: "elf", origin: "origin_cloud_ridge" })).toBe(true);
  });

  it("送出的欄位只帶有選的", () => {
    expect(raceOriginBody({ race: "", origin: "" })).toEqual({});
    expect(raceOriginBody({ race: "elf", origin: "origin_cloud_ridge" })).toEqual({ race: "elf", origin: "origin_cloud_ridge" });
  });

  it("種族卡列出種族技、花費次數與環境被動；出身卡寫明不影響戰鬥", () => {
    const lines = raceCardLines(race);
    expect(lines[0]).toContain("林隱");
    expect(lines[1]).toBe("花費 1 AP・不佔技能欄");
    expect(lines[2]).toContain("林間視野");
    expect(raceSummary(race)).toBe("林隱／林間視野");
    const o = originCardLines(origin);
    expect(o[0]).toBe("界域：雲嶺");
    expect(o[2]).toContain("不影響戰鬥");
  });

  it("面板的一句話", () => {
    expect(raceOriginText("精靈", "雲嶺出身")).toBe("精靈・雲嶺出身");
    expect(raceOriginText("精靈", "")).toBe("精靈");
    expect(raceOriginText(null, undefined)).toBeNull();
  });
});
