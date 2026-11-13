// Phase 6N-10：介面動畫（延遲血條、升級、拿到物品）——只看前後兩次畫面的差，什麼時候播、播什麼。
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import type { WorldInventory, WorldView } from "../api/types";
import { DelayTrail, FlipNumber, trailWidth } from "../ui/MotionBits";
import { flyAt, gainedItems, gainIconOf, levelUp, MAX_FLY } from "./gainFx";
import { feetAnchor, GainFlyIcon, GainIcon } from "./GainEffects";

const item = (id: string, count: number, gear = false) => ({ item: id, name_zh: id, count, gear }) as unknown as WorldInventory["bag"][number];
const inv = (bag: WorldInventory["bag"], pouch: WorldInventory["bag"] = [], equipment: WorldInventory["equipment"] = []): WorldInventory =>
  ({ bag, pouch, equipment }) as unknown as WorldInventory;
const view = (id: string, level: number): WorldView => ({ character: { character_id: id, level } }) as unknown as WorldView;

describe("6N-10：拿到物品", () => {
  it("數量變多才飛；依物品 ID 排序、最多 3 個；任一份沒有時不播", () => {
    const a = inv([item("herb", 1)]);
    const b = inv([item("herb", 3), item("sword", 1, true), item("apple", 1), item("zz", 1)]);
    const g = gainedItems(a, b);
    expect(g.map((x) => x.item)).toEqual(["apple", "herb", "sword"]);
    expect(g.length).toBe(MAX_FLY);
    expect(g.find((x) => x.item === "herb")!.count).toBe(2);
    expect(g.find((x) => x.item === "sword")!.gear).toBe(true);
    expect(gainedItems(null, b)).toEqual([]);
    expect(gainedItems(a, undefined)).toEqual([]);
  });

  it("放進腰包、穿上裝備只是換位置，不算拿到；用掉、賣掉也不播", () => {
    const before = inv([item("herb", 2), item("sword", 1, true)]);
    const pouched = inv([item("sword", 1, true)], [item("herb", 2)]);
    expect(gainedItems(before, pouched)).toEqual([]);
    const worn = inv([item("herb", 2)], [], [{ slot: "main", slot_zh: "主手", item: { id: "sword", name_zh: "劍" } }] as unknown as WorldInventory["equipment"]);
    expect(gainedItems(before, worn)).toEqual([]);
    expect(gainedItems(before, inv([item("herb", 1)]))).toEqual([]);
  });

  it("飛行路徑：從起點拱起再落到背包，最後淡出；確定性", () => {
    const from = { x: 100, y: 300 };
    const to = { x: 400, y: 600 };
    expect(flyAt(from, to, 0)).toMatchObject({ x: 100, y: 300 });
    const end = flyAt(from, to, 1);
    expect(end.x).toBeCloseTo(400, 9);
    expect(end.y).toBeCloseTo(600, 9);
    expect(end.alpha).toBeCloseTo(0, 9);
    expect(flyAt(from, to, 0.5).y).toBeLessThan((300 + 600) / 2); // 往上拱
    expect(flyAt(from, to, 0.37)).toEqual(flyAt(from, to, 0.37));
  });

  it("圖示：裝備一把劍、其他一個布袋，不寫字", () => {
    const g = renderToStaticMarkup(createElement(GainIcon, { gear: true }));
    const b = renderToStaticMarkup(createElement(GainIcon, { gear: false }));
    expect(g).not.toBe(b);
    expect(g).not.toMatch(/<text/);
  });
});

describe("6Q-1：飛行圖示的選擇", () => {
  const look = { kind: "dagger", material: "steel" };
  const cards = [{ item: { id: "blade", name_zh: "短刀", appearance: look }, slot: "main_hand", slot_zh: "主手" }];
  const worn = [{ slot: "body", slot_zh: "身體", item: { id: "robe", name_zh: "袍", appearance: { kind: "robe" } } }];
  const full = { ...inv([item("herb", 1), item("blade", 1, true)], [], worn as unknown as WorldInventory["equipment"]), gear_cards: cards } as unknown as WorldInventory;

  it("裝備：從背包的裝備卡或身上穿的找到外觀，用實際圖示；其他物品維持通用圖示", () => {
    expect(gainIconOf(full, { item: "blade", gear: true })).toEqual({ kind: "gear", look, slot: "main_hand" });
    expect(gainIconOf(full, { item: "robe", gear: true })).toEqual({ kind: "gear", look: { kind: "robe" }, slot: "body" });
    expect(gainIconOf(full, { item: "herb", gear: false })).toEqual({ kind: "generic", gear: false });
    // 找不到外觀、沒有背包：退回通用的劍
    expect(gainIconOf(full, { item: "ghost", gear: true })).toEqual({ kind: "generic", gear: true });
    expect(gainIconOf(null, { item: "blade", gear: true })).toEqual({ kind: "generic", gear: true });
    expect(gainIconOf(inv([item("blade", 1, true)]), { item: "blade", gear: true })).toEqual({ kind: "generic", gear: true });
  });

  it("畫法：裝備畫 GearIcon 的 canvas，其他畫通用圖示（QI-7 起是 Q 版畫布，不是 SVG）", () => {
    const gear = renderToStaticMarkup(createElement(GainFlyIcon, { choice: gainIconOf(full, { item: "blade", gear: true }) }));
    expect(gear).toContain("gear-icon");
    expect(gear).not.toContain("<svg");
    const herb = renderToStaticMarkup(createElement(GainFlyIcon, { choice: gainIconOf(full, { item: "herb", gear: false }) }));
    expect(herb).toBe(renderToStaticMarkup(createElement(GainIcon, { gear: false })));
  });
});

describe("6N-10：升級", () => {
  it("同一個角色等級變高才播；第一次載入、換角色、沒變都不播", () => {
    expect(levelUp(view("a", 3), view("a", 4))).toBe(4);
    expect(levelUp(null, view("a", 4))).toBeNull();
    expect(levelUp(view("a", 3), view("b", 9))).toBeNull();
    expect(levelUp(view("a", 4), view("a", 4))).toBeNull();
  });

  it("光柱放在主角腳底（跟著格子與縮放）", () => {
    const grid = { width: 4, height: 4, tiles: [] } as never;
    const a = feetAnchor(grid, { x: 1, y: 2 }, 1);
    const b = feetAnchor(grid, { x: 1, y: 2 }, 2);
    expect(b.left).toBeCloseTo(a.left * 2, 9);
    expect(feetAnchor(grid, { x: 2, y: 2 }, 1).left - a.left).toBe(48);
  });

  it("Lv 數字：第一次畫不翻；值變了才翻", () => {
    expect(renderToStaticMarkup(createElement(FlipNumber, { value: 3 }))).toContain('data-flip="0"');
  });
});

describe("6N-10：延遲血條", () => {
  it("殘量寬度照比例、夾在 0～100%", () => {
    expect(trailWidth(0.5)).toBe("50%");
    expect(trailWidth(-1)).toBe("0%");
    expect(trailWidth(2)).toBe("100%");
    expect(trailWidth(Number.NaN)).toBe("0%");
    expect(renderToStaticMarkup(createElement(DelayTrail, { ratio: 0.25 }))).toContain("width:25%");
  });
});
