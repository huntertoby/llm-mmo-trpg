// Phase 3-22：勝利條件的文字、HUD 剩餘輪數、目標格標記（繪製資料與格子資訊卡）、結算原因。
import { describe, expect, it } from "vitest";
import type { RunResponse } from "../api/types";
import { runView } from "../run/flow";
import { buildDrawModel } from "./drawModel";
import {
  endDetail,
  markerAt,
  markerCard,
  objectiveBadge,
  objectiveHud,
  objectiveLine,
  objectiveMarkers,
  roundsLeft,
  type ObjectiveLike,
} from "./objective";
import { smallView } from "./testFixtures";
import { tileSections } from "./tileInfo";

const ESCAPE: ObjectiveLike = { kind: "escape", rounds: 5, tiles: [[2, 0], [2, 1]] };
const DEFEND: ObjectiveLike = { kind: "defend", rounds: 6, tiles: [[0, 2]] };
const ELIMINATE: ObjectiveLike = { kind: "eliminate", rounds: null, tiles: [] };

describe("勝利條件文字", () => {
  it("一行說明", () => {
    expect(objectiveLine(ESCAPE)).toBe("撤離：5 輪內，所有還活著的我方單位抵達出口");
    expect(objectiveLine(DEFEND)).toBe("守點：守住守點 6 輪，別讓敵人站在上面");
    expect(objectiveLine(ELIMINATE)).toBe("全滅：擊倒所有敵人");
  });

  it("圖示加名稱", () => {
    expect(objectiveBadge(ESCAPE)).toBe("➜ 撤離");
    expect(objectiveBadge(DEFEND)).toBe("◎ 守點");
    expect(objectiveBadge(ELIMINATE)).toBe("⚔ 全滅");
  });
});

describe("HUD 剩餘輪數", () => {
  it("第 1 輪剩全部輪數，最後一輪標明，全滅沒有輪數", () => {
    expect(roundsLeft(ESCAPE, 1)).toBe(5);
    expect(roundsLeft(ESCAPE, 3)).toBe(3);
    expect(roundsLeft(ESCAPE, 5)).toBe(1);
    expect(roundsLeft(ESCAPE, 9)).toBe(0);
    expect(roundsLeft(ELIMINATE, 2)).toBeNull();
    expect(objectiveHud(ESCAPE, 3)).toBe("➜ 撤離・剩 3 輪");
    expect(objectiveHud(DEFEND, 6)).toBe("◎ 守點・最後 1 輪");
    expect(objectiveHud(ELIMINATE, 4)).toBe("⚔ 全滅");
  });
});

describe("目標格標記", () => {
  it("撤離畫出口格、守點畫守點格、全滅沒有", () => {
    expect(objectiveMarkers(ESCAPE)).toEqual([
      { x: 2, y: 0, kind: "exit" },
      { x: 2, y: 1, kind: "exit" },
    ]);
    expect(objectiveMarkers(DEFEND)).toEqual([{ x: 0, y: 2, kind: "point" }]);
    expect(objectiveMarkers(ELIMINATE)).toEqual([]);
  });

  it("繪製模型帶著標記（格子位置與高度由繪圖端的 place 套用抬高）", () => {
    const view = smallView({ objective: { kind: "escape", rounds: 5, tiles: [[2, 0]] } });
    expect(buildDrawModel(view, "unit_0001").markers).toEqual([{ x: 2, y: 0, kind: "exit" }]);
    expect(buildDrawModel(smallView(), "unit_0001").markers).toEqual([]);
  });

  it("格子資訊卡說明出口與守點", () => {
    const view = smallView({ objective: { kind: "escape", rounds: 5, tiles: [[2, 0]] }, round: 2 });
    expect(markerAt(view, { x: 2, y: 0 })).toBe("exit");
    expect(markerAt(view, { x: 0, y: 0 })).toBeNull();
    const card = markerCard(view, { x: 2, y: 0 });
    expect(card?.title).toBe("出口格（剩 4 輪）");
    const sections = tileSections(view, { x: 2, y: 0 }, {});
    expect(sections.some((s) => s.kind === "objective")).toBe(true);
    expect(tileSections(view, { x: 1, y: 0 }, {}).some((s) => s.kind === "objective")).toBe(false);
    const defend = smallView({ objective: { kind: "defend", rounds: 6, tiles: [[0, 0]] } });
    expect(markerCard(defend, { x: 0, y: 0 })?.title).toBe("守點格（剩 6 輪）");
  });
});

describe("結算原因", () => {
  it("撤離成功、守住、守點失守、撤離超時各有說明", () => {
    expect(endDetail("escaped")).toContain("撤離成功");
    expect(endDetail("defended")).toContain("守住了");
    expect(endDetail("point_lost")).toContain("守點失守");
    expect(endDetail("escape_failed")).toContain("撤離超時");
    expect(endDetail("eliminate")).toBeNull();
    expect(endDetail(null)).toBeNull();
  });
});

describe("選路／下一場畫面", () => {
  it("下一場的畫面帶本場勝利條件；沒有資料時當作全滅", () => {
    const base = {
      run_id: "r",
      seed: 1,
      battles_done: 0,
      history: [],
      battle_id: null,
      node: { kind: "battle", battle_index: 1, boss: false },
      plan: [
        { index: 1, map_id: "m", map_name_zh: "雲海吊橋", boss: false, enemies: ["盜賊"], done: false, objective: ESCAPE },
        { index: 2, map_id: "m2", map_name_zh: "油庫", boss: false, enemies: ["盜賊"], done: false, objective: DEFEND },
      ],
    } as unknown as RunResponse;
    const v = runView(base);
    expect(v).toMatchObject({
      screen: "progress",
      goalKind: "escape",
      goalBadge: "➜ 撤離",
      goalLine: "撤離：5 輪內，所有還活著的我方單位抵達出口",
    });
    const second = runView({ ...base, node: { kind: "battle", battle_index: 2, boss: false } });
    expect(second).toMatchObject({ goalKind: "defend" });
    const none = runView({ ...base, plan: [] });
    expect(none).toMatchObject({ goalKind: "eliminate" });
  });
});
