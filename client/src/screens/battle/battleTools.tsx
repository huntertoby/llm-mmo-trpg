// 頂端列的彈出面板內容（由 BattleScreen 抽出，Phase 3T-7）：反應設定、隊友指令、圖例、版面。
// 純函式：吃目前狀態，回傳給 `BattleTopBar` 的 `tools` 陣列。

import type { OrderSet, ReactionMode, UnitView } from "../../api/types";
import type { LayoutPrefs, layoutLimits } from "../../battle/layoutPrefs";
import type { LegendEntry } from "../../battle/legend";
import { EMPTY_ORDERS, hasOrders, withOrder, type OrderKind } from "../../battle/orders";
import type { UnitNames } from "../../battle/units";
import type { TopPopup } from "../../battle/skillTray";
import { LayoutPanel } from "../../ui/LayoutPanel";
import { Legend } from "../../ui/Legend";
import { OrdersPanel } from "../../ui/OrdersPanel";
import { ReactionPanel } from "../../ui/ReactionPanel";

export interface ToolsInput {
  hero: UnitView | null;
  heroId: string;
  canAct: boolean;
  canOrder: boolean;
  autoQueue: readonly string[];
  onSetReaction(reaction: string, m: ReactionMode): void;
  orders: OrderSet;
  ordersIgnored: Parameters<typeof OrdersPanel>[0]["ignored"];
  liveNames: UnitNames;
  orderPick: OrderKind | null;
  onPickOrder(kind: OrderKind): void;
  onCancelOrderPick(): void;
  issueOrders(orders: OrderSet): void;
  legend: LegendEntry[];
  layout: LayoutPrefs;
  limits: ReturnType<typeof layoutLimits>;
  scale: number;
  narrow: boolean;
  onLayoutChange(patch: Partial<LayoutPrefs>): void;
  onLayoutReset(): void;
  shake: boolean;
  onShake(on: boolean): void;
  collapseTile: boolean;
  onCollapseTile(on: boolean): void;
}

export interface ToolEntry {
  id: TopPopup;
  label: string;
  badge?: string;
  content: JSX.Element;
}

export function battleTools(t: ToolsInput): ToolEntry[] {
  return [
    {
      id: "reactions" as const,
      label: "反應設定",
      content: <ReactionPanel hero={t.hero} enabled={t.canAct} queued={t.autoQueue} onSet={t.onSetReaction} />,
    },
    {
      id: "orders" as const,
      label: "隊友指令",
      badge: hasOrders(t.orders) ? "●" : "",
      content: (
        <OrdersPanel
          orders={t.orders}
          ignored={t.ordersIgnored}
          names={t.liveNames}
          enabled={t.canOrder}
          picking={t.orderPick}
          onPick={t.onPickOrder}
          onProtectHero={() => t.issueOrders(withOrder(t.orders, { kind: "protect", ward: t.heroId }))}
          onCancelPick={t.onCancelOrderPick}
          onClear={() => t.issueOrders(EMPTY_ORDERS)}
        />
      ),
    },
    { id: "legend" as const, label: "圖例", content: <Legend entries={t.legend} /> },
    {
      id: "layout" as const,
      label: "版面",
      content: (
        <LayoutPanel
          prefs={t.layout}
          limits={t.limits}
          scale={t.scale}
          narrow={t.narrow}
          onChange={t.onLayoutChange}
          onReset={t.onLayoutReset}
          shake={t.shake}
          onShake={t.onShake}
          collapseTile={t.collapseTile}
          onCollapseTile={t.onCollapseTile}
        />
      ),
    },
  ];
}
