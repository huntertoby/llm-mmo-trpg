// 重複詞條標灰（Phase 3-32b）：沒生效的詞條（`AffixLineView.active === false`）在角色面板與裝備說明卡裡標灰並註明原因；
// 裝備比較（測試物品清單）預測「換上這件之後」哪些詞條會變成重複、哪些原本被壓住的會恢復生效。
// 比較是前端的預測：只看「非數值類別的同 id 詞條」（普攻附加、觸發、充能、動作、反應、改變規則——同 id 只生效最強的 1 條）；
// 數值類的遞減（100／50／25／0%）與誰最強由伺服器裁決，預測只標出「會重複」，不判斷哪一條比較強。
import type { AffixLineView, GearCatalog, GearItemInfo } from "../api/types";
import { affixText, type Selection } from "./gearDraft";

/** 說明卡裡的一行詞條。`note` 不為空 ＝ 沒生效（標灰），內容是原因。 */
export interface TipLine {
  text: string;
  note: string | null;
}

/** 有數值部分、同 id 依遞減疊加的類別（和 `content/equipment.py` 的 `NUMERIC_CATEGORIES` 一致）。 */
export const NUMERIC_CATEGORIES: ReadonlySet<string> = new Set(["stat", "conditional", "keyword", "weapon_trait", "cost"]);

/** 沒生效的原因（生效中回傳 `null`）。 */
export function inactiveNote(a: Pick<AffixLineView, "active" | "duplicate_of">): string | null {
  if (a.active) return null;
  if (a.duplicate_of != null && a.duplicate_of !== "") return `和${a.duplicate_of}重複，沒有效果`;
  return "同種詞條疊太多條，這條沒有效果";
}

/** 一件裝備的詞條 → 說明卡的行。 */
export function tipLines(affixes: readonly AffixLineView[]): TipLine[] {
  return affixes.map((a) => ({ text: a.text_zh, note: inactiveNote(a) }));
}

/** 比較預測的一行。 */
export interface CompareLine {
  text: string;
  /** `gray`：換上後會變成重複（沒效果）；`restore`：原本被壓住的詞條，換上後恢復生效。 */
  kind: "gray" | "restore";
  note: string;
}

interface Held {
  slot: string;
  slotName: string;
  affixId: string;
  text: string;
}

function heldAffixes(selection: Selection, catalog: GearCatalog): Held[] {
  const held: Held[] = [];
  for (const slot of catalog.slots) {
    const pick = selection[slot.slot];
    if (pick === undefined) continue;
    if ("custom" in pick) {
      for (const a of pick.custom.affixes) {
        const info = catalog.affixes.find((i) => i.id === a.affix);
        held.push({ slot: slot.slot, slotName: slot.name_zh, affixId: a.affix, text: info === undefined ? a.affix : affixText(info, a.value) });
      }
    } else {
      const item = catalog.items.find((i) => i.id === pick.item_id);
      for (const a of item?.affixes ?? []) held.push({ slot: slot.slot, slotName: slot.name_zh, affixId: a.affix_id, text: a.text_zh });
    }
  }
  return held;
}

function isNonNumeric(catalog: GearCatalog, affixId: string): boolean {
  const info = catalog.affixes.find((i) => i.id === affixId);
  return info !== undefined && !NUMERIC_CATEGORIES.has(info.category);
}

function count(held: readonly Held[], affixId: string): number {
  return held.filter((h) => h.affixId === affixId).length;
}

/**
 * 把 `item` 穿到 `slotId` 之後的變化（只列有變化的行）：
 * 新物品的詞條若和別的欄位重複 → `gray`；被換下的物品若讓別處原本重複的詞條恢復 → `restore`；
 * `item` 已經穿在 `slotId` 時沒有變化（回傳空陣列）。
 */
export function compareItem(catalog: GearCatalog, selection: Selection, slotId: string, item: GearItemInfo): CompareLine[] {
  const before = heldAffixes(selection, catalog);
  const current = selection[slotId];
  if (current !== undefined && "item_id" in current && current.item_id === item.id) return [];
  const others = before.filter((h) => h.slot !== slotId);
  const lines: CompareLine[] = [];
  const slotName = catalog.slots.find((s) => s.slot === slotId)?.name_zh ?? slotId;
  // 新物品的詞條：和別的欄位同 id（非數值類）→ 換上後多一條重複
  for (const a of item.affixes) {
    if (!isNonNumeric(catalog, a.affix_id)) continue;
    const dup = others.find((h) => h.affixId === a.affix_id);
    if (dup !== undefined) lines.push({ text: a.text_zh, kind: "gray", note: `和${dup.slotName}的「${dup.text}」重複，只有較強的一條有效果` });
  }
  // 被換下的物品：它讓別處重複的詞條恢復生效
  for (const h of before.filter((x) => x.slot === slotId)) {
    if (!isNonNumeric(catalog, h.affixId)) continue;
    const stillTwice = count(others, h.affixId) + item.affixes.filter((a) => a.affix_id === h.affixId).length;
    const wasDuplicated = count(before, h.affixId) >= 2;
    if (!wasDuplicated || stillTwice >= 2) continue;
    const other = others.find((o) => o.affixId === h.affixId);
    if (other !== undefined) lines.push({ text: other.text, kind: "restore", note: `${other.slotName}的這條原本和${slotName}的重複，換下後恢復生效` });
  }
  return lines;
}
