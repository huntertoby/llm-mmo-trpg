// HC-7 a 裁定 8：誓約冷卻的「N 天內」由 API 帶秒數、前端照同一規則組字（整天「N 天」、不整天「N 小時」）。
import { describe, expect, it } from "vitest";
import { CRYSTAL_SURGE_RE, statusTier } from "./statusCard";
import { aboutDurationText, durationText } from "./rulesText";
import { filterRows, upTo } from "../tuning/skillModel";

describe("HC-7 b 前端照資料組字", () => {
  it("誓約冷卻：整天寫天、不整天寫小時（四捨五入）；目前 86400 秒和改前逐字相同", () => {
    expect(`解除後現實 ${durationText(86400)}內不能再立。`).toBe("解除後現實 1 天內不能再立。");
    expect(`解除後現實 ${durationText(86400)}內不能再立誓，確定？`).toBe("解除後現實 1 天內不能再立誓，確定？");
    expect(durationText(2 * 86400)).toBe("2 天");
    expect(durationText(5400)).toBe("2 小時");
    expect(durationText(90000)).toBe("25 小時");
  });

  it("線頭到期的「約 N 天」照舊", () => {
    expect(aboutDurationText(259200)).toBe("約 3 天");
    expect(aboutDurationText(90000)).toBe("約 25 小時");
  });

  it("晶能湧動的階照 ID 樣式", () => {
    expect(statusTier("crystal_surge")).toBe(1);
    expect(statusTier("crystal_surge_2")).toBe(2);
    expect(statusTier("crystal_surge_3")).toBe(3);
    expect(CRYSTAL_SURGE_RE.test("crystal_surge_x")).toBe(false);
  });
});

describe("HC-7 b.5 工坊的階級與 AP 選項照伺服器的 skill_limits", () => {
  it("篩選列：階級 1～skill_tiers、AP 1～max_ap_cost；預設讀名詞表（目前 5 階、3 AP）", () => {
    const labels = (rows: ReturnType<typeof filterRows>, label: string) => rows.find((r) => r.label === label)?.choices.map((c) => c.label);
    expect(labels(filterRows(), "階級")).toEqual(["1 階", "2 階", "3 階", "4 階", "5 階"]);
    expect(labels(filterRows(), "AP")).toEqual(["1 AP", "2 AP", "3 AP"]);
    const custom = filterRows({ skill_tiers: 2, max_ap_cost: 4 });
    expect(labels(custom, "階級")).toEqual(["1 階", "2 階"]);
    expect(labels(custom, "AP")).toEqual(["1 AP", "2 AP", "3 AP", "4 AP"]);
    expect(upTo(5)).toEqual([1, 2, 3, 4, 5]);
  });
});
