// 地點圖的純函式（Phase 5A-5）。
import { describe, expect, it } from "vitest";
import type { WorldLocationView, WorldView } from "../api/types";
import { canTravel, edgeLine, locationBadge, locationClass, locationHint, nameProblem, statusLine } from "./mapView";

function loc(over: Partial<WorldLocationView> = {}): WorldLocationView {
  return {
    id: "bamboo_path",
    name_zh: "竹林小徑",
    kind: "camp",
    kind_zh: "營地",
    level_zh: "Lv 1～2",
    description_zh: "霧狼、新手任務 2",
    x: 30,
    y: 65,
    current: false,
    adjacent: true,
    blocked_zh: null,
    cleared: false,
    hidden: false,
    fog: "visited",
    quest_marks: [],
    footprints: [],
    ...over,
  };
}

describe("地點可不可以走", () => {
  it("相鄰、沒被擋、沒有遭遇才可以走", () => {
    expect(canTravel(loc(), false)).toBe(true);
    expect(canTravel(loc(), true)).toBe(false);
    expect(canTravel(loc({ adjacent: false }), false)).toBe(false);
    expect(canTravel(loc({ blocked_zh: "還沒開放" }), false)).toBe(false);
    expect(canTravel(loc({ current: true }), false)).toBe(false);
  });

  it("樣式：種類、目前位置、可走、不可走、已清空", () => {
    expect(locationClass(loc(), false)).toBe("world-loc kind-danger reachable");
    expect(locationClass(loc({ current: true, kind: "town" }), false)).toBe("world-loc kind-town current");
    expect(locationClass(loc({ adjacent: false, kind: "ruin" }), false)).toBe("world-loc kind-site far");
    expect(locationClass(loc({ cleared: true }), true)).toBe("world-loc kind-danger far cleared");
  });
});

describe("說明文字", () => {
  it("名稱、種類、建議等級、說明與能不能走", () => {
    expect(locationHint(loc(), false)).toBe("竹林小徑（營地・Lv 1～2）\n霧狼、新手任務 2\n點一下走過去（路上可能遇敵）");
    expect(locationHint(loc({ blocked_zh: "還沒開放" }), false)).toContain("不能走：還沒開放");
    expect(locationHint(loc({ adjacent: false }), false)).toContain("不相鄰");
    expect(locationHint(loc({ current: true, cleared: true }), false)).toBe(
      "竹林小徑（營地・Lv 1～2・已清空）\n霧狼、新手任務 2\n目前位置",
    );
  });

  it("小字：已清空優先，其次建議等級；城鎮沒有", () => {
    expect(locationBadge(loc())).toBe("Lv 1～2");
    expect(locationBadge(loc({ cleared: true }))).toBe("已清空");
    expect(locationBadge(loc({ level_zh: null }))).toBeNull();
  });
});

describe("連線與狀態", () => {
  const view = {
    map: { locations: [loc({ id: "a", x: 10, y: 20, current: true }), loc({ id: "b", x: 30, y: 40 })] },
  } as unknown as WorldView;

  it("連線端點用地點座標；碰到目前位置的標 near；找不到端點時 null", () => {
    expect(edgeLine(view, ["a", "b"])).toEqual({ x1: 10, y1: 20, x2: 30, y2: 40, near: true });
    expect(edgeLine(view, ["a", "zzz"])).toBeNull();
  });

  it("狀態行", () => {
    const c = { level: 2, xp: 120, xp_next: 250, hp: 30, max_hp: 40, mana: 5, max_mana: 10, supplies: 4, max_supplies: 10 };
    expect(statusLine(c as WorldView["character"])).toBe("Lv 2・經驗 120／250・HP 30／40・法力 5／10・補給 4／10");
    expect(statusLine({ ...c, xp_next: null } as WorldView["character"])).toContain("已到頂");
  });

  it("角色名稱：不可空白、最多 12 字", () => {
    expect(nameProblem("  ")).not.toBeNull();
    expect(nameProblem("阿霧")).toBeNull();
    expect(nameProblem("一二三四五六七八九十一二")).toBeNull();
    expect(nameProblem("一二三四五六七八九十一二三")).not.toBeNull();
  });
});
