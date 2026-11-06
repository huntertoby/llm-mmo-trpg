// Phase 3-18b：地形資訊卡精簡（標籤一行、持續時間只在有剩餘回合時寫、可收起）。
import { describe, expect, it } from "vitest";
import { collapseSections, condenseObjectRules, tileSections } from "./tileInfo";
import { loadTileCollapse, saveTileCollapse } from "./tileCardPrefs";
import { object, smallView, tile } from "./testFixtures";

const at = (x: number, y: number) => ({ x, y });

describe("物件標籤濃縮成一行", () => {
  it("前 N 行是標籤：去括號、用「・」連接；其餘照舊逐行", () => {
    const rules = ["不可通行", "半掩護（遠程攻擊其後的目標，命中 −2）", "可推動", "爆炸範圍 3×3，2d6 火焰傷害", "火焰：爆炸"];
    expect(condenseObjectRules(rules, 3)).toEqual(["不可通行・半掩護・可推動", "爆炸範圍 3×3，2d6 火焰傷害", "火焰：爆炸"]);
    expect(condenseObjectRules(rules, 0)).toEqual(rules);
  });

  it("木箱的卡片：標題後只有一行標籤，加上互動行", () => {
    const sections = tileSections(smallView(), at(1, 2), {});
    const crate = sections.find((s) => s.kind === "object")!;
    expect(crate.lines[0]).toContain("半掩護");
    expect(crate.lines[0]).toContain("・");
    expect(crate.lines[0]).not.toContain("（");
    expect(crate.lines.filter((l) => !l.includes("：")).length).toBeLessThanOrEqual(1);
  });
});

describe("持續時間只在有剩餘回合時寫", () => {
  const withSurface = (remaining: number | null) => {
    const view = smallView();
    const tiles = view.tiles.map((t) => (t.x === 2 && t.y === 0 ? tile(2, 0, { surface: "ice", surface_remaining: remaining }) : t));
    return tileSections({ ...view, tiles }, at(2, 0), {}).find((s) => s.kind === "surface")!;
  };
  const all = (s: { title: string; lines: string[] }) => [s.title, ...s.lines].join("\n");

  it("永久表面（沒有剩餘回合）不寫「由技能產生時持續」", () => {
    expect(all(withSurface(null))).not.toContain("持續");
    expect(all(withSurface(null))).not.toContain("剩");
  });

  it("有剩餘回合的表面寫剩餘回合與持續時間規則", () => {
    const text = all(withSurface(2));
    expect(text).toContain("剩 2 回合");
  });
});

describe("收起", () => {
  it("只留地形那一行標題，沒有規則行", () => {
    const sections = tileSections(smallView(), at(1, 2), {});
    expect(sections.length).toBeGreaterThan(1);
    const collapsed = collapseSections(sections);
    expect(collapsed).toHaveLength(1);
    expect(collapsed[0]).toMatchObject({ kind: "terrain", lines: [] });
    expect(collapseSections([])).toEqual([]);
  });

  it("使用者的選擇記在 localStorage（預設不收）", () => {
    const store = new Map<string, string>();
    const fake = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    Object.defineProperty(globalThis, "window", { value: { localStorage: fake }, configurable: true });
    try {
      expect(loadTileCollapse()).toBe(false);
      saveTileCollapse(true);
      expect(loadTileCollapse()).toBe(true);
      saveTileCollapse(false);
      expect(loadTileCollapse()).toBe(false);
    } finally {
      Reflect.deleteProperty(globalThis, "window");
    }
  });
});

describe("暫時障礙仍寫剩餘回合", () => {
  it("expires_in 在標題", () => {
    const view = smallView({ objects: [object("o1", "ice_wall", 2, 0, { expires_in: 2 })] });
    const tiles = view.tiles.map((t) => (t.x === 2 && t.y === 0 ? tile(2, 0, { object_id: "o1" }) : t));
    const section = tileSections({ ...view, tiles }, at(2, 0), {}).find((s) => s.kind === "object")!;
    expect(section.title).toContain("剩 2 回合消失");
  });
});
