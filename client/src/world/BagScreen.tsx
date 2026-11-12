// 背包與裝備（Phase 5D-4；docs/phases/Phase5計畫.md 33.2）：大世界左欄的完整畫面（同「成長與技能」的切換）。
// UI-E3（巡檢 #7、G2、hud.png C 案）：穿戴中改成 9 個格子（空的畫該欄的空槽圖示，有裝備畫 `gearIcon` 的實際圖示）；
// 背包改成 6×5 的物品格（裝備與物品同一格表，`bagGrid.ts`）、腰包一排格子；點一格在下方看詳情（裝備卡＋換上、物品說明＋使用）。
// 6T-1b 的別大類兩行字與換裝確認框照舊在裝備卡底下。
// 由上而下：背包滿時選要丟哪件（`LootChoicePanel`）→ 穿戴中 9 欄（圖示滑過看詞條，共用浮動卡 `PartTip`）→
// 背包的裝備（一輪的裝備卡 `GearCardView`：和該欄位目前裝備的比較；換主手且縮放屬性不同時先確認）→
// 其他物品與腰包（`InventoryPanel`）。能不能換上、比較都由後端算好；停用原因用共用 <Hint>。
import { useState } from "react";
import type { GearCandidate, HeroGearSlot, WorldAction, WorldBagItem, WorldInventory, WorldView } from "../api/types";
import type { TipLine } from "../gear/affixStatus";
import { itemSubtitle, itemTipLines, needsSwapConfirm } from "../run/gearOffer";
import { GearIcon } from "../ui/GearIcon";
import { Hint } from "../ui/Hint";
import { PartTip } from "../ui/PartTip";
import { GearCardView } from "../ui/gear/GearCardView";
import { WeaponSwapConfirm } from "../ui/gear/WeaponSwapConfirm";
import { equipAction, equipState, otherRingSlot } from "./bagView";
import { itemHint, PouchEditor } from "./EconomyPanel";
import { bagCells, BAG_COLS, cellHint, pickedCell, pouchCells, tileLines, type BagCell } from "./bagGrid";
import { LootChoicePanel } from "./LootChoicePanel";
import { walletLine } from "./economy";
import "./mail.css";

interface ActProps {
  busy: boolean;
  onAct(action: WorldAction): void;
}

/** 穿戴中一格的說明卡：裝備的詞條行；入門武器、還能重選時的起始武器多一行伺服器給的字（OB-6 Q4），放最前面。 */
export function wornTipLines(entry: HeroGearSlot): TipLine[] {
  const lines = entry.item == null ? [] : itemTipLines(entry.item);
  return entry.opening_note_zh != null ? [{ text: entry.opening_note_zh, note: null }, ...lines] : lines;
}

/** 穿戴中的一格（UI-E3）：空的畫該欄的空槽圖示（淡色剪影），有裝備畫實際圖示；滑過看詞條（共用部件說明框）。 */
export function WornSlot({ entry }: { entry: HeroGearSlot }) {
  const item = entry.item;
  if (item == null) {
    return (
      <li className="world-worn-slot empty" data-testid={`world-worn-${entry.slot}`} data-empty="1">
        <PartTip cat={entry.slot_zh} label="空" tip="這一欄還沒有裝備。">
          <span className="world-worn-box">
            <GearIcon look={null} slot={entry.slot} size={48} label={`${entry.slot_zh}：空`} />
          </span>
        </PartTip>
        <span className="world-worn-cat">{entry.slot_zh}</span>
      </li>
    );
  }
  return (
    <li className="world-worn-slot" data-testid={`world-worn-${entry.slot}`}>
      <PartTip cat={entry.slot_zh} label={`${item.name_zh}（${itemSubtitle(item)}）`} tip="" lines={wornTipLines(entry)}>
        <span className="world-worn-box">
          <GearIcon look={item.appearance} slot={entry.slot} size={48} label={item.name_zh} />
        </span>
      </PartTip>
      <span className="world-worn-cat">{entry.slot_zh}</span>
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
      {row?.opening_note_zh != null && (
        // OB-6 Q4：還能重選時，背包裡的起始武器本體寫明重選會收回（字由伺服器給）
        <div className="gear-cross-class" data-testid="world-gear-opening-note">
          {row.opening_note_zh}
        </div>
      )}
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

function gearCardOf(inventory: WorldInventory, item: string): GearCandidate | null {
  return (inventory.gear_cards ?? []).find((c) => c.item.id === item) ?? null;
}

/** 物品格的一格：裝備畫圖示，其他是名字小牌（物品圖示 G10 移植前）＋右下角個數；點了選取。 */
export function BagCellView({ cell, inventory, picked, onPick }: { cell: BagCell; inventory: WorldInventory; picked: boolean; onPick(key: string): void }) {
  if (cell.kind === "empty") return <li className="world-bag-cell empty" aria-hidden="true" />;
  const row = cell.row;
  const card = row.gear === true ? gearCardOf(inventory, row.item) : null;
  const cls = ["world-bag-cell", picked ? "picked" : "", row.gear === true ? "gear" : "", row.cross_class_zh != null ? "cross" : ""].filter((c) => c !== "").join(" ");
  return (
    <li className={cls}>
      <Hint text={cellHint(row)}>
        <button type="button" aria-pressed={picked} aria-label={cellHint(row)} onClick={() => onPick(cell.key)} data-testid={`world-bag-cell-${cell.key}`}>
          {row.gear === true ? (
            <GearIcon look={card?.item.appearance ?? null} slot={card?.slot} size={48} label={row.name_zh} />
          ) : (
            <span className="world-bag-tile" aria-hidden="true">
              {tileLines(row.name_zh).map((l, i) => (
                <span key={i} className="world-bag-tile-line">
                  {l}
                </span>
              ))}
            </span>
          )}
          {row.gear !== true && row.count > 1 && <b className="world-bag-count">{row.count}</b>}
        </button>
      </Hint>
    </li>
  );
}

/** 選取的物品（不是裝備）的詳情：名字、種類、個數、說明、野外使用。 */
export function ItemDetail({ row, busy, canUse, onAct }: ActProps & { row: WorldBagItem; canUse: boolean }) {
  const hint = itemHint(row);
  return (
    <div className="world-bag-detail" data-testid={`world-bag-detail-${row.item}`}>
      <div>
        <b>{row.name_zh}</b>
        <span className="muted small">　{row.kind_zh}・×{row.count}</span>
      </div>
      {hint !== "" && <div className="small">{hint}</div>}
      {row.bound_zh != null && <div className="muted small">{row.bound_zh}</div>}
      {row.field_usable && row.use_zh != null && (
        <div className="run-actions">
          <Hint text={`使用 1 個：${row.use_zh}`}>
            <button type="button" disabled={busy || !canUse} onClick={() => onAct({ kind: "use_item", item: row.item })} data-testid={`world-use-${row.item}`}>
              使用
            </button>
          </Hint>
        </div>
      )}
    </div>
  );
}

type ThingCell = Extract<BagCell, { kind: "thing" }>;

/** 格子下方的詳情：裝備＝裝備卡（和目前裝備比較、別大類兩行字、換上與確認）；其他＝物品說明。 */
export function BagDetail({ cell, inventory, busy, canUse, onAct }: ActProps & { cell: ThingCell | null; inventory: WorldInventory; canUse: boolean }) {
  if (cell === null) return <div className="muted small world-bag-detail">背包是空的。打贏戰鬥會掉東西，也可以到鐵匠打造。</div>;
  const card = cell.row.gear === true ? gearCardOf(inventory, cell.row.item) : null;
  if (card !== null) {
    return (
      <div className="run-offer-cards world-bag-detail" data-testid="world-gear-cards">
        <GearOffer key={card.item.id} cand={card} inventory={inventory} busy={busy} onAct={onAct} />
      </div>
    );
  }
  return <ItemDetail row={cell.row} busy={busy} canUse={canUse} onAct={onAct} />;
}

function BagGrid({ cells, inventory, picked, onPick, testId, cols }: { cells: readonly BagCell[]; inventory: WorldInventory; picked: string | null; onPick(key: string): void; testId: string; cols: number }) {
  return (
    <ul className="world-bag-grid" style={{ gridTemplateColumns: `repeat(${cols}, var(--bag-cell))` }} data-testid={testId}>
      {cells.map((c) => (
        <BagCellView key={c.key} cell={c} inventory={inventory} picked={c.key === picked} onPick={onPick} />
      ))}
    </ul>
  );
}

/** 背包格、腰包格與詳情；`initialPick` 只給測試與開發頁指定一開始選哪一格。 */
export function BagContents({ inventory, busy, onAct, canUse, initialPick = null }: ActProps & { inventory: WorldInventory; canUse: boolean; initialPick?: string | null }) {
  const [picked, setPicked] = useState<string | null>(initialPick);
  const [editing, setEditing] = useState(false);
  const cells = bagCells(inventory);
  const pouch = pouchCells(inventory);
  const current = pickedCell([...cells, ...pouch], picked);
  const gearCount = inventory.bag.filter((b) => b.gear === true).length;
  return (
    <div className="world-bag-main">
      <div className="world-bag-left">
        <div className="section-title">
          背包<span className="muted small">　{inventory.slots_used}／{inventory.slots_max} 格・裝備 {gearCount} 件・城鎮與營火可以換裝</span>
        </div>
        <BagGrid cells={cells} inventory={inventory} picked={current?.key ?? null} onPick={setPicked} testId="world-bag" cols={BAG_COLS} />
        <div className="section-title" data-testid="world-pouch-title">
          腰包　<span className="muted small">{inventory.pouch_count}／{inventory.pouch_max} 個・戰鬥中 1 AP 使用</span>
        </div>
        <div className="world-pouch-row">
          <BagGrid cells={pouch} inventory={inventory} picked={current?.key ?? null} onPick={setPicked} testId="world-pouch" cols={Math.max(1, pouch.length)} />
          {inventory.can_pouch ? (
            <button type="button" aria-expanded={editing} disabled={busy} onClick={() => setEditing((v) => !v)} data-testid="world-pouch-toggle">
              {editing ? "收起整理腰包" : "整理腰包"}
            </button>
          ) : (
            inventory.pouch_problem_zh != null && <span className="muted small">整理腰包：{inventory.pouch_problem_zh}</span>
          )}
        </div>
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
      {/* 詳情：寬的面板放在格子右邊，窄的時候換到下面（flex-wrap） */}
      <div className="world-bag-side" data-testid="world-bag-side">
        <div className="section-title small">詳情</div>
        <BagDetail cell={current} inventory={inventory} busy={busy} canUse={canUse} onAct={onAct} />
      </div>
    </div>
  );
}

export function WorldBagScreen({ view, busy, onAct, onClose, initialPick = null }: ActProps & { view: WorldView; onClose(): void; initialPick?: string | null }) {
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
          <BagContents inventory={inventory} busy={busy} onAct={onAct} canUse={canUse} initialPick={initialPick} />
        </>
      )}
    </div>
  );
}
