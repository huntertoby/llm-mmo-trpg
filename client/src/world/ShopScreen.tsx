// 商店（Phase 5D-4；docs/phases/Phase5計畫.md 33.2）：大世界左欄的完整畫面。內容沿用 5D-1 的 `ShopPanel`
// （價格、限量、門檻、買、賣）；上方加金幣與背包格數，方便邊買邊看。
import type { WorldAction, WorldView } from "../api/types";
import { bagSummary } from "./bagView";
import { ShopPanel } from "./EconomyPanel";
import { walletLine } from "./economy";

export function WorldShopScreen({
  view,
  busy,
  onAct,
  onClose,
}: {
  view: WorldView;
  busy: boolean;
  onAct(action: WorldAction): void;
  onClose(): void;
}) {
  return (
    <div className="panel world-screen-pane world-shop-screen" data-testid="world-shop-screen">
      <div className="world-quest-head">
        <h2>商店</h2>
        <span className="muted small">
          {view.wallet != null ? walletLine(view.wallet) : ""}
          {view.inventory != null ? `・背包 ${bagSummary(view.inventory)}` : ""}
        </span>
        <button type="button" onClick={onClose} data-testid="world-shop-close">
          回到地點圖
        </button>
      </div>
      {view.shop == null ? (
        <div className="muted small">這裡沒有店。</div>
      ) : (
        <ShopPanel shop={view.shop} inventory={view.inventory} busy={busy} onAct={onAct} />
      )}
    </div>
  );
}
