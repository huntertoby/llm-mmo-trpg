// AR-SK4：戰前佈置的小修（AR-SK3 驗收第 9、10 件）。
import { describe, expect, it } from "vitest";
import type { PrepOut } from "../api/types";
import { modeHint } from "../ui/ActionPanel";
import { TileCardController } from "../ui/hoverCard";
import { isPrepModeKey, prepHidesTileCard, prepMode, prepModeHint } from "./prep";

const PREP: PrepOut = {
  unit_id: "unit_0001",
  zone: [
    [0, 0],
    [1, 0],
    [2, 0],
  ],
  options: [
    { skill_id: "skill_bear_trap", kind: "trap", tiles: [[1, 0]] },
    { skill_id: "skill_hunt_sigil", kind: "rune", tiles: [[0, 0], [1, 0], [2, 0]] },
  ],
};

describe("AR-SK4 佈置說明卡", () => {
  it("佈置選格的說明卡照定案字，N＝可放的格數，不寫顏色", () => {
    const one = prepMode(PREP, "skill_bear_trap", "捕獸夾");
    const three = prepMode(PREP, "skill_hunt_sigil", "獵印");
    expect(one).not.toBeNull();
    expect(three).not.toBeNull();
    expect(modeHint(one!)).toBe("點框起來的起始區裡的一格放下（可選 1 格）。Esc／右鍵取消。");
    expect(modeHint(three!)).toBe("點框起來的起始區裡的一格放下（可選 3 格）。Esc／右鍵取消。");
    for (const text of [modeHint(one!), modeHint(three!)]) expect(text).not.toMatch(/紅|金|藍|紫|綠/);
  });
  it("只有 prep: 開頭的模式換字", () => {
    expect(isPrepModeKey("prep:skill_bear_trap")).toBe(true);
    expect(isPrepModeKey("skill:skill_bear_trap")).toBe(false);
    expect(prepModeHint(2)).toContain("可選 2 格");
  });
});

describe("AR-SK4 佈置時的格子資訊卡", () => {
  it("佈置選格時滑過可放的格子不出資訊卡，其他格子照舊", () => {
    const mode = prepMode(PREP, "skill_bear_trap", "捕獸夾");
    expect(prepHidesTileCard(mode, { x: 1, y: 0 })).toBe(true);
    expect(prepHidesTileCard(mode, { x: 0, y: 0 })).toBe(false); // 起始區但這招放不下
    expect(prepHidesTileCard(mode, { x: 5, y: 5 })).toBe(false);
    expect(prepHidesTileCard(mode, null)).toBe(false);
    expect(prepHidesTileCard(null, { x: 1, y: 0 })).toBe(false);
  });
  it("一般選目標模式（不是佈置）不受影響", () => {
    const mode = prepMode(PREP, "skill_bear_trap", "捕獸夾")!;
    expect(prepHidesTileCard({ ...mode, key: "skill:skill_bear_trap" }, { x: 1, y: 0 })).toBe(false);
  });
  it("資訊卡控制器：hasContent 回 false 時不顯示", () => {
    const ctl = new TileCardController();
    const mode = prepMode(PREP, "skill_bear_trap", "捕獸夾");
    ctl.hasContent = (tile) => !prepHidesTileCard(mode, tile);
    ctl.setHover({ x: 1, y: 0 });
    expect(ctl.visible).toBe(false);
    ctl.setHover({ x: 0, y: 0 });
    expect(ctl.visible).toBe(true);
    ctl.dispose();
  });
});
