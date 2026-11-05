// 背包與裝備（Phase 5D-4；docs/phases/Phase5計畫.md 33.2）：大世界左欄的完整畫面（同「成長與技能」的切換）。
// 由上而下：背包滿時選要丟哪件（`LootChoicePanel`）→ 穿戴中 9 欄（圖示滑過看詞條，共用浮動卡 `PartTip`）→
// 背包的裝備（一輪的裝備卡 `GearCardView`：和該欄位目前裝備的比較；換主手且縮放屬性不同時先確認）→
// 其他物品與腰包（`InventoryPanel`）。能不能換上、比較都由後端算好；停用原因用共用 <Hint>。
import { useState } from "react";
import type { GearCandidate, HeroGearSlot, WorldAction, WorldBagItem, WorldInventory, WorldView } from "../api/types";
import { itemSubtitle, itemTipLines, needsSwapConfirm } from "../run/gearOffer";
import { GearIcon } from "../ui/GearIcon";
import { Hint } from "../ui/Hint";
import { PartTip } from "../ui/PartTip";
import { GearCardView } from "../ui/gear/GearCardView";
import { WeaponSwapConfirm } from "../ui/gear/WeaponSwapConfirm";
import { equipAction, equipState, otherRingSlot } from "./bagView";
import { InventoryPanel } from "./EconomyPanel";
import { LootChoicePanel } from "./LootChoicePanel";
import { walletLine } from "./economy";
import "./mail.css";

interface ActProps {
  busy: boolean;
  onAct(action: WorldAction): void;
}

function WornSlot({ entry }: { entry: HeroGearSlot }) {
  const item = entry.item;
  if (item == null) {
    return (
      <li className="world-worn-slot empty" data-testid={`world-worn-${entry.slot}`}>
        <span className="world-worn-cat">{entry.slot_zh}</span>
        <span className="muted">空</span>
      </li>
    );
  }
  return (
    <li className="world-worn-slot" data-testid={`world-worn-${entry.slot}`}>
      <span className="world-worn-cat">{entry.slot_zh}</span>
      <PartTip cat={entry.slot_zh} label={item.name_zh} tip="" lines={itemTipLines(item)}>
        <GearIcon look={item.appearance} slot={entry.slot} size={32} label={item.name_zh} />
      </PartTip>
      <span className="world-worn-name">
        {item.name_zh}
        <span className="muted small"> {itemSubtitle(item)}</span>
      </span>
    </li>
  );
}

/**
 * 別大類的主手換上前的確認（6T-1b；玩法 PM 決定 6T-1a 第 5 項，08 8.13 #135）：列出換上後不能用的武器技，換回同大類就恢復。
 * 字照伺服器給的卡片兩行（`cross_class_zh`、`cross_class_lost_zh`）。
 */
export function CrossClassConfirm({ cand, row, busy, onConfirm, onCancel }: { cand: GearCandidate; row: WorldBagItem; busy: boolean; onConfirm(): void; onCancel(): void }) {
  return (
    <div className="weapon-swap-confirm cross-class-confirm" role="alertdialog" aria-label="換別大類武器確認" data-testid="cross-class-confirm">
      <p className="weapon-swap-text">
        「{cand.item.name_zh}」是別大類的武器。{row.cross_class_lost_zh != null ? `${row.cross_class_lost_zh}（換回同大類就恢復）。` : "目前裝的招都還能用。"}
        {cand.weapon_swap_zh != null && cand.weapon_swap_zh !== "" ? `${cand.weapon_swap_zh}。` : ""}要換上嗎？
      </p>
      <div className="weapon-swap-buttons">
        <button type="button" className="primary" disabled={busy} onClick={onConfirm} data-testid="cross-class-yes">
          換上
        </button>
        <button type="button" disabled={busy} onClick={onCancel} data-testid="cross-class-no">
          不換
        </button>
      </div>
    </div>
  );
}

/** 裝備卡上別大類主手的兩行（6T-1b）：「別大類：可交易・可分解・可賣」與「換上後不能用：〈招名〉」。 */
export function CrossClassLines({ row }: { row: WorldBagItem }) {
  if (row.cross_class_zh == null) return null;
  return (
    <div className="gear-cross-class" data-testid={`cross-class-`}>
      <div>{row.cross_class_zh}</div>
      {row.cross_class_lost_zh != null && <div className="lost">{row.cross_class_lost_zh}</div>}
    </div>
  );
}

function GearOffer({ cand, inventory, busy, onAct }: ActProps & { cand: GearCandidate; inventory: WorldInventory }) {
  const [asking, setAsking] = useState<"swap" | "cross" | null>(null);
  const state = equipState(inventory, cand.item.id);
  const row = inventory.bag.find((b) => b.gear === true && b.item === cand.item.id) ?? null;
  const cross = row != null && row.cross_class_zh != null;
  const other = otherRingSlot(cand.slot);
  const equip = (slot: string | null) => {
    setAsking(null);
    onAct(equipAction(cand, slot));
  };
  return (
    <div className="run-offer-card" data-testid={`world-gear-card-${cand.item.id}`}>
      <GearCardView cand={cand} />
      {row !== null && <CrossClassLines row={row} />}
      {asking === "cross" && row !== null ? (
        <CrossClassConfirm cand={cand} row={row} busy={busy} onConfirm={() => equip(null)} onCancel={() => setAsking(null)} />
      ) : asking === "swap" ? (
        <WeaponSwapConfirm cand={cand} busy={busy} onConfirm={() => equip(null)} onCancel={() => setAsking(null)} />
      ) : (
        <div className="run-actions">
          <Hint text={state.ok ? `換上（放進${cand.slot_zh}；換下的放回背包）` : state.reason}>
            <span className="world-shop-buy">
              <button
                type="button"
                className="primary"
                disabled={busy || !state.ok}
                onClick={() => (cross ? setAsking("cross") : needsSwapConfirm(cand) ? setAsking("swap") : equip(null))}
                data-testid={`world-equip-${cand.item.id}`}
              >
                換上（{cand.slot_zh}）
              </button>
            </span>
          </Hint>
          {other !== null && (
            <Hint text={state.ok ? "改戴在另一隻手" : state.reason}>
              <span className="world-shop-buy">
                <button type="button" disabled={busy || !state.ok} onClick={() => equip(other)} data-testid={`world-equip-other-${cand.item.id}`}>
                  改戴{other === "ring_1" ? "戒指 1" : "戒指 2"}
                </button>
              </span>
            </Hint>
          )}
        </div>
      )}
    </div>
  );
}

export function WorldBagScreen({ view, busy, onAct, onClose }: ActProps & { view: WorldView; onClose(): void }) {
  const inventory = view.inventory;
  const canUse = view.encounter === null && view.battle_id === null;
  return (
    <div className="panel world-screen-pane world-bag-screen" data-testid="world-bag-screen">
      <div className="world-quest-head">
        <h2>背包與裝備</h2>
        <span className="muted small">{view.wallet != null ? walletLine(view.wallet) : ""}</span>
        <button type="button" onClick={onClose} data-testid="world-bag-close">
          回到地點圖
        </button>
      </div>
      {inventory == null ? (
        <div className="muted small">這個世界沒有背包。</div>
      ) : (
        <>
          {view.pending_loot != null && <LootChoicePanel pending={view.pending_loot} inventory={inventory} busy={busy} onAct={onAct} />}
          <div className="section-title">穿戴中</div>
          <ul className="world-worn" data-testid="world-equipped">
            {(inventory.equipment ?? []).map((e) => (
              <WornSlot key={e.slot} entry={e} />
            ))}
          </ul>
          {(inventory.resonance_zh ?? []).map((line) => (
            <div key={line} className="small" data-testid="world-resonance-line">
              {line}
            </div>
          ))}
          <div className="section-title">
            背包的裝備<span className="muted small">　{(inventory.gear_cards ?? []).length} 件・城鎮與營火可以換裝</span>
          </div>
          {(inventory.gear_cards ?? []).length === 0 ? (
            <div className="muted small">沒有裝備。打贏戰鬥會掉，也可以到鐵匠打造。</div>
          ) : (
            <div className="run-offer-cards" data-testid="world-gear-cards">
              {(inventory.gear_cards ?? []).map((cand) => (
                <GearOffer key={cand.item.id} cand={cand} inventory={inventory} busy={busy} onAct={onAct} />
              ))}
            </div>
          )}
          <InventoryPanel inventory={inventory} busy={busy} onAct={onAct} canUse={canUse} hideGear />
        </>
      )}
    </div>
  );
}
