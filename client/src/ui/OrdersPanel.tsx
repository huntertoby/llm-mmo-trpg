// 隊友快捷指令：集火、守位、撤退、保護、利用環境、取消。對全隊下達，送 `PUT /orders`。
// 需要目標的指令：按鈕 → 在戰場上點目標（Esc／右鍵取消）。目前的指令與被忽略的原因列在下方。
import type { IgnoredOrder, OrderSet } from "../api/types";
import {
  hasOrders,
  ignoredText,
  orderButton,
  orderLines,
  ORDER_BUTTONS,
  type OrderKind,
} from "../battle/orders";
import type { UnitNames } from "../battle/units";

interface Props {
  orders: OrderSet;
  ignored: readonly IgnoredOrder[];
  names: UnitNames;
  enabled: boolean;
  /** 正在等玩家點目標的指令。 */
  picking: OrderKind | null;
  onPick(kind: OrderKind): void;
  onProtectHero(): void;
  onCancelPick(): void;
  onClear(): void;
}

export function OrdersPanel(props: Props) {
  const { orders, ignored, names, enabled, picking } = props;
  const lines = orderLines(orders, names);
  return (
    <div className="panel orders-panel" aria-label="隊友指令">
      <div className="section-title">隊友指令</div>
      <div className="mode-buttons">
        {ORDER_BUTTONS.map((b) => (
          <button
            key={b.kind}
            type="button"
            className={picking === b.kind ? "selected" : ""}
            disabled={!enabled}
            onClick={() => props.onPick(b.kind)}
          >
            {b.label}
          </button>
        ))}
        <button type="button" disabled={!enabled || !hasOrders(orders)} onClick={props.onClear}>
          取消指令
        </button>
      </div>
      {picking !== null && (
        <div className="mode-help">
          <div className="small muted">{orderButton(picking).hint} Esc／右鍵取消。</div>
          {picking === "protect" && (
            <button type="button" disabled={!enabled} onClick={props.onProtectHero}>
              保護主角
            </button>
          )}
          <button type="button" className="small-button" onClick={props.onCancelPick}>
            取消選取
          </button>
        </div>
      )}
      <ul className="order-list">
        {lines.length === 0 && <li className="muted">目前沒有指令（隊友自行判斷）。</li>}
        {lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
        {ignored.map((i) => (
          <li key={ignoredText(i, names)} className="order-ignored">
            {ignoredText(i, names)}
          </li>
        ))}
      </ul>
    </div>
  );
}
