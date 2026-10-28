// 戰後裝備三選一與背包換裝（Phase 3K-2）：純函式——候選的顯示順序、卡片文字行、和目前裝備的比較、送出的請求。
// 規則（部位不重複、稀有度權重、能不能換上）全由後端裁決；這裡只整理要顯示的文字。
import type { GearCandidate, GearItemInfo, RunChoice, RunHero } from "../api/types";
import type { TipLine } from "../gear/affixStatus";

/** 稀有度 → 卡片的色階 class（未標稀有度的測試物品當普通）。 */
export function rarityClass(item: Pick<GearItemInfo, "rarity" | "legendary">): string {
  return `gear-rarity-${item.rarity ?? (item.legendary ? "legendary" : "common")}`;
}

/** 物品卡的內容行：基礎加成（普通物品）、副手特性、詞條；什麼都沒有時回傳空陣列。 */
export function itemLines(item: GearItemInfo): string[] {
  const lines: string[] = [];
  if (item.base_bonus_zh != null) lines.push(item.base_bonus_zh);
  if (item.offhand_name_zh != null && item.offhand_traits_zh.length > 0) {
    lines.push(`${item.offhand_name_zh}：${item.offhand_traits_zh.join("；")}`);
  }
  for (const a of item.affixes) lines.push(a.text_zh);
  return lines;
}

/** 浮動說明卡（`PartTip`）用的行。 */
export function itemTipLines(item: GearItemInfo): TipLine[] {
  const lines = itemLines(item).map((text) => ({ text, note: null }));
  return lines.length === 0 ? [{ text: "（沒有詞條）", note: null }] : lines;
}

/** 副標題：稀有度・物品等級・武器資訊，例「稀有・Lv3・單手劍」「優良・Lv2・雙手」。 */
export function itemSubtitle(item: GearItemInfo): string {
  const parts: string[] = [];
  if (item.rarity_zh != null) parts.push(item.rarity_zh);
  else if (item.legendary) parts.push("傳說");
  if (item.item_level != null) parts.push(`Lv${item.item_level}`);
  if (item.weapon_name_zh != null) {
    parts.push(`${item.weapon_name_zh}${item.two_handed ? "・雙手" : ""}${item.paired ? "・成對" : ""}`);
  } else if (item.offhand_name_zh != null) {
    parts.push(item.offhand_name_zh);
  }
  return parts.join("・");
}

function fmtPoints(n: number): string {
  const rounded = Math.round(n * 10) / 10;
  return Number.isInteger(rounded) ? `${rounded}` : rounded.toFixed(1);
}

/** 預算分數的比較：「預算分數 8 → 12（+4）」；目前欄位空著時寫「目前沒有裝備」。 */
export function compareText(c: Pick<GearCandidate, "item" | "current">): string {
  const next = c.item.points ?? 0;
  if (c.current == null) return `預算分數 ${fmtPoints(next)}（目前沒有裝備）`;
  const now = c.current.points ?? 0;
  const diff = Math.round((next - now) * 10) / 10;
  const sign = diff > 0 ? "+" : diff < 0 ? "−" : "±";
  return `預算分數 ${fmtPoints(now)} → ${fmtPoints(next)}（${sign}${fmtPoints(Math.abs(diff))}）`;
}

/** 比較結果的色調：變強、變弱、持平。 */
export function compareTone(c: Pick<GearCandidate, "item" | "current">): "up" | "down" | "same" {
  const diff = (c.item.points ?? 0) - (c.current?.points ?? 0);
  return diff > 0.05 ? "up" : diff < -0.05 ? "down" : "same";
}

/** 換上前要不要先問玩家（後端判斷：換主手武器且縮放屬性不同才有提示）。 */
export function needsSwapConfirm(c: Pick<GearCandidate, "weapon_swap_zh">): boolean {
  return c.weapon_swap_zh != null && c.weapon_swap_zh !== "";
}

/** 確認視窗的問句：「這把看力量，你目前最高的是敏捷。要把主手換成「名稱」嗎？」 */
export function swapQuestion(c: Pick<GearCandidate, "item" | "weapon_swap_zh">): string {
  return `${c.weapon_swap_zh ?? ""}。要把主手換成「${c.item.name_zh}」嗎？`;
}

/** 三選一送出的請求（`pick` 為 `null` ＝ 跳過）。 */
export function gearPickChoice(pick: number | null): RunChoice {
  return { kind: "gear_pick", pick };
}

/** 營火換裝（從背包換上）的請求。 */
export function equipChoice(itemId: string, slot?: string): RunChoice {
  return slot === undefined ? { kind: "equip", item_id: itemId } : { kind: "equip", item_id: itemId, slot };
}

/** 角色面板要列出的穿戴裝備：有物品的欄位；主手沒換過時是主角原本的基礎武器（id 以 `base_` 開頭），不算裝備。 */
export function wornGear(hero: Pick<RunHero, "equipment">): { slot: string; slot_zh: string; item: GearItemInfo }[] {
  const out: { slot: string; slot_zh: string; item: GearItemInfo }[] = [];
  for (const s of hero.equipment ?? []) {
    if (s.item != null && !s.item.id.startsWith("base_")) out.push({ slot: s.slot, slot_zh: s.slot_zh, item: s.item });
  }
  return out;
}

/** 「換上後」的提示行：連帶效果（武器換了、副手收進背包）。 */
export function noteLines(c: Pick<GearCandidate, "notes_zh">): readonly string[] {
  return c.notes_zh ?? [];
}
