// 區域圖的純函式（Phase 6C-6）：迷霧三段、傳送石能不能點、隱藏地點不顯示。
import { describe, expect, it } from "vitest";
import type { WorldLocationView, WorldMapView } from "../api/types";
import { regionEdges, regionNodes, regionNote, stoneTarget, UNKNOWN_ZH, type RegionNode } from "./regionModel";

function loc(id: string, over: Partial<WorldLocationView> = {}): WorldLocationView {
  return {
    id,
    name_zh: `地點${id}`,
    kind: "camp",
    kind_zh: "營地",
    level_zh: "Lv 1～2",
    description_zh: "",
    x: 10,
    y: 20,
    current: false,
    adjacent: false,
    blocked_zh: null,
    cleared: false,
    hidden: false,
    fog: "visited",
    quest_marks: [],
    footprints: [],
    ...over,
  };
}

function map(over: Partial<WorldMapView> = {}): WorldMapView {
  return {
    region: "cloud_ridge",
    name_zh: "雲嶺",
    level_zh: "Lv 1～10",
    hub: false,
    locations: [
      loc("town", { kind: "town", current: true, level_zh: null, x: 10, y: 80 }),
      loc("camp", { cleared: true, quest_marks: ["霧狼"], x: 30, y: 60 }),
      loc("near", { fog: "silhouette", level_zh: "Lv 3～4", cleared: true, quest_marks: ["遠方"], x: 50, y: 40 }),
      loc("far", { fog: "fog", level_zh: "Lv 9～10", quest_marks: ["更遠"], x: 80, y: 10 }),
    ],
    edges: [
      ["town", "camp"],
      ["camp", "near"],
      ["near", "far"],
    ],
    stones: [
      { id: "stone_town", location: "town", unlocked: true, here: true },
      { id: "stone_camp", location: "camp", unlocked: true, here: false },
      { id: "stone_near", location: "near", unlocked: false, here: false },
    ],
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
    ...over,
  };
}

function node(m: WorldMapView, id: string): RegionNode {
  const found = regionNodes(m).find((n) => n.id === id);
  if (found === undefined) throw new Error(`沒有 ${id}`);
  return found;
}

function first<T>(items: readonly T[]): T {
  const item = items[0];
  if (item === undefined) throw new Error("空的");
  return item;
}

describe("迷霧三段", () => {
  it("去過：名字、建議等級、清空狀態、任務標記", () => {
    const camp = node(map(), "camp");
    expect(camp.fog).toBe("visited");
    expect(camp.label).toBe("地點camp");
    expect(camp.cleared).toBe(true);
    expect(camp.quests).toEqual(["霧狼"]);
    expect(camp.hint).toContain("已清空");
  });

  it("和去過的相連：灰色剪影、「？？？」＋建議等級，不顯示名字與清空", () => {
    const near = node(map(), "near");
    expect(near.fog).toBe("silhouette");
    expect(near.label).toBe(UNKNOWN_ZH);
    expect(near.level).toBe("Lv 3～4");
    expect(near.cleared).toBe(false);
    expect(near.hint).not.toContain("地點near");
    expect(near.hint).toContain(UNKNOWN_ZH);
  });

  it("更遠：被霧蓋住，沒有名字、等級、任務、傳送石", () => {
    const far = node(map(), "far");
    expect(far.fog).toBe("fog");
    expect(far.label).toBeNull();
    expect(far.level).toBeNull();
    expect(far.quests).toEqual([]);
    expect(far.stones).toEqual([]);
    expect(far.hint).not.toContain("地點far");
  });

  it("霧裡的路不畫；去過的兩端是實線、一端剪影是虛線", () => {
    const edges = regionEdges(map());
    expect(edges.map((e) => [e.key, e.known])).toEqual([
      ["town-camp", true],
      ["camp-near", false],
    ]);
  });

  it("隱藏地點：後端沒送就不會出現（連線也不畫）", () => {
    const m = map({ edges: [...map().edges, ["camp", "secret"]] });
    expect(regionNodes(m).map((n) => n.id)).not.toContain("secret");
    expect(regionEdges(m).some((e) => e.key.includes("secret"))).toBe(false);
  });

  it("自己的位置", () => {
    expect(regionNodes(map()).filter((n) => n.current).map((n) => n.id)).toEqual(["town"]);
  });
});

describe("從圖上傳送", () => {
  it("在城鎮或傳送石上：已解鎖、不是出發點的才可以點", () => {
    const m = map();
    expect(node(m, "town").stones.map((s) => s.state)).toEqual(["here"]);
    expect(node(m, "camp").stones.map((s) => s.state)).toEqual(["go"]);
    expect(node(m, "near").stones.map((s) => s.state)).toEqual(["locked"]);
    expect(stoneTarget(first(node(m, "camp").stones))).toBe("stone_camp");
    expect(stoneTarget(first(node(m, "town").stones))).toBeNull();
    expect(stoneTarget(first(node(m, "near").stones))).toBeNull();
    expect(regionNote(map())).toContain("可以傳送");
  });

  it("其他時候只能看：已解鎖的也顯示鎖頭與原因、點了不送動作", () => {
    const why = "站在傳送石上或在城鎮裡打開地圖，才能點傳送石傳送";
    const m = map({
      can_teleport: false,
      teleport_problem_zh: why,
      stones: map().stones.map((s) => ({ ...s, here: false })),
    });
    const camp = first(node(m, "camp").stones);
    expect(camp.state).toBe("view");
    expect(camp.hint).toContain(why);
    expect(stoneTarget(camp)).toBeNull();
    expect(regionNodes(m).flatMap((n) => n.stones).every((s) => stoneTarget(s) === null)).toBe(true);
    expect(regionNote(m)).toBe(`只能看：${why}`);
  });

  it("剪影地點的傳送石說明不洩漏地名", () => {
    expect(first(node(map(), "near").stones).hint).toContain(UNKNOWN_ZH);
    expect(first(node(map(), "near").stones).hint).not.toContain("地點near");
  });
});
