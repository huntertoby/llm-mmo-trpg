// 裝備欄位格（Phase 3G-G4）：9 個欄位排成 3×3，每格 64px 圖示；點格子選欄位，右側換成該欄位的物品清單。
import type { GearCatalog, GearItemInfo } from "../../api/types";
import { draftLook, draftSummary, type CustomDraft, type Selection } from "../../gear/gearDraft";
import { GearIcon } from "../GearIcon";
import { PartTip } from "../PartTip";

/** 3×3 的排列（依欄位 id）：戒指放在角落，主手與副手在身體兩側。 */
export const GRID_ORDER: readonly string[] = ["head", "neck", "ring_1", "main_hand", "body", "off_hand", "hands", "feet", "ring_2"];

interface Props {
  catalog: GearCatalog;
  selection: Selection;
  selected: string;
  /** 副手被占用時為 `true`。 */
  offHandBlocked: boolean;
  onSelect(slot: string): void;
}

function pickLook(pick: NonNullable<Selection[string]>, catalog: GearCatalog): { name: string; look: GearItemInfo["appearance"] | null; tip: string } {
  if ("custom" in pick) {
    const d: CustomDraft = pick.custom;
    const look = { ...draftLook(d, catalog), keywords: [] as string[] };
    return { name: d.name, look, tip: `${d.name}（自訂）：${draftSummary(d, catalog)}` };
  }
  const item = catalog.items.find((i) => i.id === pick.item_id);
  if (item === undefined) return { name: "（未知物品）", look: null, tip: "目錄裡找不到這件物品" };
  return { name: item.name_zh, look: item.appearance, tip: `${item.name_zh}：${item.affixes.map((a) => a.text_zh).join("；")}` };
}

export function SlotGrid({ catalog, selection, selected, offHandBlocked, onSelect }: Props) {
  return (
    <div className="gear-grid" role="group" aria-label="裝備欄位">
      {GRID_ORDER.map((slotId) => {
        const slot = catalog.slots.find((s) => s.slot === slotId);
        if (slot === undefined) return null;
        const pick = selection[slotId];
        const blocked = slotId === "off_hand" && offHandBlocked;
        const shown = pick === undefined ? null : pickLook(pick, catalog);
        const classes = ["gear-cell", selected === slotId ? "selected" : "", blocked ? "blocked" : "", pick === undefined ? "empty" : ""].filter(Boolean).join(" ");
        return (
          <PartTip key={slotId} cat={slot.name_zh} label={shown?.name ?? "空"} tip={shown?.tip ?? ""} pin={false} className="gear-cell-tip">
          <button type="button" className={classes} onClick={() => onSelect(slotId)} data-slot={slotId}>
            <span className="gear-cell-slot">{slot.name_zh}</span>
            <span className="gear-cell-art">
              {shown !== null && shown.look !== null ? (
                <GearIcon look={shown.look} slot={slotId} size={64} />
              ) : (
                <span className="gear-cell-empty">{blocked ? "被主手占用" : "空"}</span>
              )}
            </span>
            <span className="gear-cell-name">{shown?.name ?? ""}</span>
          </button>
          </PartTip>
        );
      })}
    </div>
  );
}
