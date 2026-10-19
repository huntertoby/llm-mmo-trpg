import { describe, expect, it } from "vitest";
import type { OrderSet } from "../api/types";
import {
  EMPTY_ORDERS,
  hasOrders,
  ignoredText,
  orderFromTile,
  orderLines,
  orderTargetTiles,
  ORDER_BUTTONS,
  withOrder,
  withoutOrder,
} from "./orders";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

const view = smallView();
const names = unitNames(view);

describe("order targets", () => {
  it("focus fire targets living enemies only", () => {
    expect(orderTargetTiles("focus_target", view, "unit_0001").map((p) => [p.x, p.y])).toEqual([
      [2, 1],
      [2, 0],
    ]);
    expect(orderFromTile("focus_target", view, { x: 2, y: 1 })).toEqual({ kind: "focus_target", target: "unit_0003" });
    expect(orderFromTile("focus_target", view, { x: 0, y: 0 })).toBeNull(); // 我方
    expect(orderFromTile("focus_target", view, { x: 1, y: 1 })).toBeNull(); // 已撤離
  });

  it("protect targets living allies other than the hero", () => {
    expect(orderTargetTiles("protect", view, "unit_0001")).toEqual([]); // 另一位隊友已倒下
    expect(orderFromTile("protect", view, { x: 0, y: 0 })).toEqual({ kind: "protect", ward: "unit_0001" });
    expect(orderFromTile("protect", view, { x: 2, y: 1 })).toBeNull();
  });

  it("tile orders accept any tile; environment needs no target", () => {
    expect(orderFromTile("hold_position", view, { x: 1, y: 2 })).toEqual({
      kind: "hold_position",
      at: [1, 2],
      radius: 1,
    });
    expect(orderFromTile("retreat_to", view, { x: 0, y: 2 })).toEqual({ kind: "retreat_to", at: [0, 2] });
    expect(orderFromTile("use_environment", view, { x: 0, y: 0 })).toEqual({ kind: "use_environment" });
    expect(ORDER_BUTTONS.map((b) => b.label)).toEqual(["集火", "守位", "撤退", "保護", "利用環境"]);
  });
});

describe("order set", () => {
  const focus = { kind: "focus_target", target: "unit_0003" } as const;

  it("replaces an order of the same kind and keeps the others", () => {
    let set: OrderSet = withOrder(EMPTY_ORDERS, focus);
    set = withOrder(set, { kind: "use_environment" });
    set = withOrder(set, { kind: "focus_target", target: "unit_0004" });
    expect(set.team_orders).toEqual([{ kind: "use_environment" }, { kind: "focus_target", target: "unit_0004" }]);
    expect(withoutOrder(set, "focus_target").team_orders).toEqual([{ kind: "use_environment" }]);
    expect(EMPTY_ORDERS.team_orders).toEqual([]); // 不改動原物件
  });

  it("describes orders and ignored orders in Chinese", () => {
    const set = withOrder(withOrder(EMPTY_ORDERS, focus), { kind: "hold_position", at: [1, 2], radius: 1 });
    expect(orderLines(set, names)).toEqual(["集火：a 單位3", "守位：(1, 2)（半徑 1）"]);
    expect(hasOrders(set)).toBe(true);
    expect(hasOrders(EMPTY_ORDERS)).toBe(false);
    expect(ignoredText({ scope: "team", order: focus, reason: "目標已倒下" }, names)).toBe(
      "集火：a 單位3 無法執行（目標已倒下）",
    );
    expect(ignoredText({ scope: "unit_0002", order: focus, reason: "x" }, names)).toContain("B 單位2：");
  });
});
