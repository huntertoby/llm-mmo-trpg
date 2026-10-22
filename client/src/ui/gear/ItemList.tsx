// 測試物品清單（Phase 3G-G4）：每列 48px 圖示＋名稱＋詞條摘要；點一列穿到目前的欄位，再點一次卸下。不做背包格。
import type { GearCatalog, GearSlotInfo } from "../../api/types";
import { itemSummary, type Selection } from "../../gear/gearDraft";
import { GearIcon } from "../GearIcon";

interface Props {
  catalog: GearCatalog;
  slot: GearSlotInfo;
  selection: Selection;
  onPick(itemId: string | null): void;
}

export function ItemList({ catalog, slot, selection, onPick }: Props) {
  const items = catalog.items.filter((i) => i.slot_type === slot.slot_type);
  const current = selection[slot.slot];
  const currentId = current !== undefined && "item_id" in current ? current.item_id : null;
  return (
    <div className="gear-list" role="list" aria-label={`${slot.name_zh}的測試物品`}>
      {items.length === 0 && <div className="muted">沒有適合{slot.name_zh}的測試物品，請用「手動組裝」。</div>}
      {items.map((item) => {
        const active = item.id === currentId;
        return (
          <button
            key={item.id}
            type="button"
            role="listitem"
            className={`gear-row-item${active ? " active" : ""}`}
            onClick={() => onPick(active ? null : item.id)}
            data-item={item.id}
          >
            <GearIcon look={item.appearance} slot={slot.slot} size={48} />
            <span className="gear-row-text">
              <span className="gear-row-name">
                {item.name_zh}
                {item.weapon_name_zh != null && <span className="muted small">（{item.weapon_name_zh}{item.two_handed ? "・雙手" : ""}{item.paired ? "・成對" : ""}）</span>}
                {item.legendary && <span className="gear-legend">傳說</span>}
              </span>
              <span className="gear-row-affixes muted small">{itemSummary(item)}</span>
            </span>
            <span className="gear-row-action">{active ? "卸下" : "穿上"}</span>
          </button>
        );
      })}
    </div>
  );
}
