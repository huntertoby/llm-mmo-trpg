// 隊友快捷指令（純函式）：按鈕種類、點選目標 → `TacticalOrder`、指令清單與文字。
// 指令對全隊（`team_orders`）下達，送 `PUT /orders`；每種指令最多一個，新的取代同種舊的。
import type { BattleView, IgnoredOrder, OrderSet, Pos, TacticalOrder } from "../api/types";
import { samePos } from "./geometry";
import type { UnitNames } from "./units";

export type OrderKind = TacticalOrder["kind"];

/** 下達這種指令需要再點什麼。 */
export type OrderTarget = "enemy" | "tile" | "ally" | null;

export interface OrderButton {
  kind: OrderKind;
  label: string;
  target: OrderTarget;
  hint: string;
}

export const ORDER_BUTTONS: readonly OrderButton[] = [
  { kind: "focus_target", label: "集火", target: "enemy", hint: "點一個敵人，隊友優先攻擊它。" },
  { kind: "hold_position", label: "守位", target: "tile", hint: "點一個格子，隊友守在它附近。" },
  { kind: "retreat_to", label: "撤退", target: "tile", hint: "點一個格子，隊友撤往那裡。" },
  { kind: "protect", label: "保護", target: "ally", hint: "點一個隊友（或按「保護主角」）。" },
  { kind: "use_environment", label: "利用環境", target: null, hint: "" },
];

export const HOLD_RADIUS = 1;

export const EMPTY_ORDERS: OrderSet = { team_orders: [], unit_orders: {} };

export function orderButton(kind: OrderKind): OrderButton {
  return ORDER_BUTTONS.find((b) => b.kind === kind) ?? (ORDER_BUTTONS[0] as OrderButton);
}

function livingUnitAt(view: BattleView, tile: Pos) {
  return view.units.find((u) => !u.downed && !u.escaped && !u.dismissed && samePos(u.pos, tile));
}

/** 該種指令可以點選的格子（高亮用）：集火＝活著的敵人、保護＝活著的隊友（不含主角）。 */
export function orderTargetTiles(kind: OrderKind, view: BattleView, heroId: string): Pos[] {
  if (kind === "focus_target") {
    return view.units.filter((u) => u.team !== view.team && !u.downed && !u.escaped && !u.dismissed).map((u) => u.pos);
  }
  if (kind === "protect") {
    return view.units
      .filter((u) => u.team === view.team && u.id !== heroId && !u.downed && !u.escaped && !u.dismissed)
      .map((u) => u.pos);
  }
  return [];
}

/** 點選格子 → 指令；格子不能當這種指令的目標時 `null`。 */
export function orderFromTile(kind: OrderKind, view: BattleView, tile: Pos): TacticalOrder | null {
  switch (kind) {
    case "focus_target": {
      const u = livingUnitAt(view, tile);
      return u !== undefined && u.team !== view.team ? { kind, target: u.id } : null;
    }
    case "protect": {
      const u = livingUnitAt(view, tile);
      return u !== undefined && u.team === view.team ? { kind, ward: u.id } : null;
    }
    case "hold_position":
      return { kind, at: [tile.x, tile.y], radius: HOLD_RADIUS };
    case "retreat_to":
      return { kind, at: [tile.x, tile.y] };
    case "use_environment":
      return { kind };
  }
}

/** 新指令取代同種的舊指令，其他保留（每種 `kind` 最多一個）。 */
export function withOrder(current: OrderSet, order: TacticalOrder): OrderSet {
  return {
    ...current,
    team_orders: [...current.team_orders.filter((o) => o.kind !== order.kind), order],
  };
}

/** 移除某一種指令。 */
export function withoutOrder(current: OrderSet, kind: OrderKind): OrderSet {
  return { ...current, team_orders: current.team_orders.filter((o) => o.kind !== kind) };
}

function atText(at: readonly number[]): string {
  return `(${at[0]}, ${at[1]})`;
}

export function orderText(order: TacticalOrder, names: UnitNames): string {
  switch (order.kind) {
    case "focus_target":
      return `集火：${names.label(order.target)}`;
    case "hold_position":
      return `守位：${atText(order.at)}（半徑 ${order.radius}）`;
    case "retreat_to":
      return `撤退：${atText(order.at)}`;
    case "protect":
      return `保護：${names.label(order.ward)}`;
    case "use_environment":
      return "利用環境";
  }
}

/** 目前的所有指令（團隊與個別）→ 文字行。 */
export function orderLines(orders: OrderSet, names: UnitNames): string[] {
  const lines = orders.team_orders.map((o) => orderText(o, names));
  for (const [unitId, list] of Object.entries(orders.unit_orders ?? {})) {
    for (const o of list) lines.push(`${names.label(unitId)}：${orderText(o, names)}`);
  }
  return lines;
}

export function ignoredText(i: IgnoredOrder, names: UnitNames): string {
  const scope = i.scope === "team" ? "" : `${names.label(i.scope)}：`;
  return `${scope}${orderText(i.order, names)} 無法執行（${i.reason}）`;
}

export function hasOrders(orders: OrderSet): boolean {
  return orders.team_orders.length > 0 || Object.values(orders.unit_orders ?? {}).some((l) => l.length > 0);
}
