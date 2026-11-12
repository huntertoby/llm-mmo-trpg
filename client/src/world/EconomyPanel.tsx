// 商店、背包與腰包（Phase 5D-1；docs/phases/Phase5計畫.md 25.6）。
// 說明一律用共用 <Hint>（浮動卡規則 6.5.1）；能不能買、價格、限量、門檻都由後端算好。
// 5D-2：背包也列掉落的裝備（「裝上」在城鎮或營火）與穿戴中的裝備。
// 5D-4（33.2）：右側改成摘要（`InventorySummary`）＋「打開背包」；`InventoryPanel` 是左欄背包畫面的物品與
// 腰包區（裝備在背包畫面用裝備卡另列，`hideGear`）；`ShopPanel` 放在左欄的商店畫面。
import { useState } from "react";
import type { WorldAction, WorldBagItem, WorldInventory, WorldShop } from "../api/types";
import { Hint } from "../ui/Hint";
import { ItemListIcon } from "../ui/ItemIcon";
import { bagSummary } from "./bagView";
import { draftCount, pouchAction, pouchDraft, samePouch, setDraft } from "./economy";

interface ActProps {
  busy: boolean;
  onAct(action: WorldAction): void;
}

export function itemHint(item: { description_zh: string; battle_zh?: string | null }): string {
  return [item.description_zh, item.battle_zh ?? ""].filter((s) => s !== "").join("　");
}

export function ShopPanel({ shop, inventory, busy, onAct }: ActProps & { shop: WorldShop; inventory: WorldInventory | null | undefined }) {
  const sellable = (inventory?.bag ?? []).filter((item) => item.sellable !== false);
  return (
    <div className="world-shop" data-testid="world-shop">
      <div className="section-title small">
        {shop.name_zh}　<span className="muted">店主 {shop.npc_name_zh}（{shop.rank_zh}）</span>
      </div>
      {shop.affinity_zh != null && <div className="muted small" data-testid="world-shop-affinity">{shop.affinity_zh}</div>}
      {(shop.price_notes_zh ?? []).map((note) => (
        <div key={note} className="muted small" data-testid="world-shop-price-note">{note}</div>
      ))}
      {!shop.can_trade && shop.trade_problem_zh != null && <div className="muted small">買賣：{shop.trade_problem_zh}</div>}
      <ul className="world-shop-list small">
        {shop.items.map((item) => (
          <li key={item.item} className={item.locked ? "locked" : undefined} data-testid={`world-shop-item-${item.item}`}>
            <Hint text={itemHint(item)}>
              <span className="world-shop-thing">
                <ItemListIcon id={item.item} color={item.color} rare={item.rare} />
                <span className="world-shop-name">{item.name_zh}</span>
              </span>
            </Hint>
            <span className="muted">{item.kind_zh}</span>
            <span className="world-shop-price">{item.price} 金幣</span>
            {item.stock_zh != null && <span className="muted">{item.stock_zh}</span>}
            {item.locked && item.lock_zh != null && <span className="world-shop-lock">{item.lock_zh}</span>}
            {/* 停用的按鈕不接滑鼠事件：說明卡掛在外層 span 上，買不了也看得到原因 */}
            <Hint text={item.can_buy ? `買 1 個（${item.price} 金幣）` : item.problem_zh ?? "不能買"}>
              <span className="world-shop-buy" data-testid={`world-buy-hint-${item.item}`}>
                <button
                  type="button"
                  disabled={busy || !item.can_buy}
                  onClick={() => onAct({ kind: "buy", shop: shop.shop, item: item.item })}
                  data-testid={`world-buy-${item.item}`}
                >
                  買
                </button>
              </span>
            </Hint>
          </li>
        ))}
      </ul>
      {sellable.length > 0 && (
        <>
          <div className="section-title small">賣東西（腰包裡的要先拿出來；材料不收）</div>
          <ul className="world-shop-list small">
            {sellable.map((item) => (
              <li key={item.item}>
                <span className="world-shop-thing">
                  <ItemListIcon id={item.item} gear={item.gear} color={item.color} rare={item.rare} />
                  <span className="world-shop-name">{item.name_zh}</span>
                </span>
                <span className="muted">×{item.count}</span>
                <span className="world-shop-price">賣 {item.sell_price} 金幣</span>
                <button
                  type="button"
                  disabled={busy || !shop.can_trade}
                  onClick={() => onAct({ kind: "sell", shop: shop.shop, item: item.item })}
                  data-testid={`world-sell-${item.item}`}
                >
                  賣
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function BagRow({ item, busy, canUse, onAct }: ActProps & { item: WorldBagItem; canUse: boolean }) {
  return (
    <li>
      <Hint text={itemHint(item)}>
        <span className="world-shop-name">{item.name_zh}</span>
      </Hint>
      {item.gear === true ? <span className="muted">{item.kind_zh}</span> : <span className="muted">×{item.count}</span>}
      {item.gear === true && (
        <Hint text={item.can_equip === true ? "換上（換下的放回背包）" : item.equip_problem_zh ?? "不能換上"}>
          <span className="world-shop-buy">
            <button
              type="button"
              disabled={busy || item.can_equip !== true}
              onClick={() => onAct({ kind: "equip", item: item.item })}
              data-testid={`world-equip-${item.item}`}
            >
              裝上
            </button>
          </span>
        </Hint>
      )}
      {item.field_usable && item.use_zh != null && (
        <Hint text={`使用 1 個：${item.use_zh}`}>
          <button type="button" disabled={busy || !canUse} onClick={() => onAct({ kind: "use_item", item: item.item })} data-testid={`world-use-${item.item}`}>
            使用
          </button>
        </Hint>
      )}
    </li>
  );
}

export function PouchEditor({ inventory, busy, onAct, onDone }: ActProps & { inventory: WorldInventory; onDone(): void }) {
  const [draft, setDraftState] = useState<Record<string, number>>(() => pouchDraft(inventory));
  const choices = inventory.consumables ?? [];
  return (
    <div className="world-pouch-edit small" data-testid="world-pouch-editor">
      {choices.length === 0 ? (
        <div className="muted">背包裡沒有消耗品（可以到商店買）。</div>
      ) : (
        <ul className="world-shop-list">
          {choices.map((c) => (
            <li key={c.item}>
              <span className="world-shop-thing">
                <ItemListIcon id={c.item} gear={c.gear} color={c.color} rare={c.rare} />
                <span className="world-shop-name">{c.name_zh}</span>
              </span>
              <span className="muted">持有 {c.count}</span>
              <label>
                帶
                <select
                  value={draft[c.item] ?? 0}
                  disabled={busy}
                  onChange={(e) => setDraftState(setDraft(draft, inventory, c.item, Number(e.target.value)))}
                  data-testid={`world-pouch-count-${c.item}`}
                >
                  {Array.from({ length: Math.min(c.count, inventory.pouch_max) + 1 }, (_, n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
                個
              </label>
            </li>
          ))}
        </ul>
      )}
      <div className="run-actions">
        <span className="muted">
          {draftCount(draft)}／{inventory.pouch_max}
        </span>
        <button
          type="button"
          className="primary"
          disabled={busy || samePouch(draft, inventory)}
          onClick={() => {
            onAct(pouchAction(draft));
            onDone();
          }}
          data-testid="world-pouch-apply"
        >
          確定
        </button>
      </div>
    </div>
  );
}

/** 右側常駐的背包摘要（5D-4）：格數、裝備件數、腰包、共鳴、等著決定的戰利品；完整內容在左欄的背包畫面。 */
export function InventorySummary({
  inventory,
  pendingLoot,
  open,
  onOpen,
}: {
  inventory: WorldInventory;
  pendingLoot: boolean;
  open: boolean;
  onOpen(): void;
}) {
  return (
    <div className="panel world-inventory" data-testid="world-inventory">
      <div className="section-title">
        背包　<span className="muted small">{bagSummary(inventory)}</span>
      </div>
      {pendingLoot && (
        <div className="small world-loot-alert" data-testid="world-loot-alert">
          背包滿了：戰利品等你決定要丟哪件。
        </div>
      )}
      {inventory.pouch.length > 0 && (
        <div className="muted small">腰包：{inventory.pouch.map((p) => `${p.name_zh} ×${p.count}`).join("、")}</div>
      )}
      {(inventory.resonance_zh ?? []).map((line) => (
        <div key={line} className="small" data-testid="world-resonance">
          {line}
        </div>
      ))}
      <div className="run-actions">
        <button type="button" className={open ? "primary" : ""} onClick={onOpen} data-testid="world-bag-toggle">
          {open ? "回到地點圖" : pendingLoot ? "打開背包（選要丟哪件）" : "打開背包"}
        </button>
      </div>
    </div>
  );
}

export function InventoryPanel({
  inventory,
  busy,
  onAct,
  canUse,
  hideGear = false,
}: ActProps & { inventory: WorldInventory; canUse: boolean; hideGear?: boolean }) {
  const [editing, setEditing] = useState(false);
  const rows = hideGear ? inventory.bag.filter((b) => b.gear !== true) : inventory.bag;
  return (
    <div className="world-inventory-items" data-testid="world-inventory-items">
      <div className="section-title">
        {hideGear ? "其他物品" : "背包"}　<span className="muted small">{inventory.slots_used}／{inventory.slots_max} 格</span>
      </div>
      {rows.length === 0 ? (
        <div className="muted small">空的。</div>
      ) : (
        <ul className="world-shop-list small" data-testid="world-bag">
          {rows.map((item) => (
            <BagRow key={item.item} item={item} busy={busy} canUse={canUse} onAct={onAct} />
          ))}
        </ul>
      )}
      {!hideGear && (inventory.equipped_zh ?? []).length > 0 && (
        <>
          <div className="section-title small">穿戴中</div>
          <ul className="world-shop-list small" data-testid="world-equipped">
            {(inventory.equipped_zh ?? []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      )}
      {!hideGear && (inventory.resonance_zh ?? []).length > 0 && (
        <ul className="world-shop-list small" data-testid="world-resonance">
          {(inventory.resonance_zh ?? []).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {/* UI-E1 追加 8：字級與間距同「其他物品」（section-title、數字前一個全形空格、數字小字） */}
      <div className="section-title" data-testid="world-pouch-title">
        腰包　<span className="muted small">{inventory.pouch_count}／{inventory.pouch_max} 個・戰鬥中 1 AP 使用</span>
      </div>
      {inventory.pouch.length === 0 ? (
        <div className="muted small">沒帶東西。</div>
      ) : (
        <ul className="world-shop-list small" data-testid="world-pouch">
          {inventory.pouch.map((item) => (
            <BagRow key={item.item} item={item} busy={busy} canUse={canUse} onAct={onAct} />
          ))}
        </ul>
      )}
      {inventory.can_pouch ? (
        <div className="run-actions">
          <button type="button" aria-expanded={editing} disabled={busy} onClick={() => setEditing((v) => !v)} data-testid="world-pouch-toggle">
            {editing ? "收起整理腰包" : "整理腰包"}
          </button>
        </div>
      ) : (
        inventory.pouch_problem_zh != null && <div className="muted small">整理腰包：{inventory.pouch_problem_zh}</div>
      )}
      {editing && inventory.can_pouch && (
        <PouchEditor
          key={inventory.pouch.map((p) => `${p.item}:${p.count}`).join(",")}
          inventory={inventory}
          busy={busy}
          onAct={onAct}
          onDone={() => setEditing(false)}
        />
      )}
    </div>
  );
}
