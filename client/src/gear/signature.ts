// 招牌效果（E6-b2；規則 docs/design/08-裝備.md 8.27、8.30 第 4 點；美術移植需求 docs/art/E6-招牌-移植需求.md）：純函式。
// - 裝備卡第一行的招牌框：物品的第一條招牌詞條（後端 `GearItemLine.signature` 不為空）；框色＝卡片的稀有度色，標灰時換灰。
// - 撿到時的一次性強調：同一件（物品 ID）這次開遊戲只播一次；減少動態時不播（CSS 也擋）。
// - 角色面板的勾選：後端給「誰生效」與灰字（`SignaturePanelOut`），這裡只決定按一列要做什麼（送出、先在畫面上取消勾選、已滿提示）。
//   勾選的合法性（最多 3 個、改寫規則 1 條、必須是身上的）由後端裁決。
import type { GearItemInfo, SignaturePanel, SignatureRow } from "../api/types";

/** 裝備卡上的一行詞條。 */
export type ItemLine = GearItemInfo["affixes"][number];

/** 稀有度 → 招牌框色（照 gear.css 的稀有度徽章色；沒標時普通）。 */
export const SIGNATURE_RARITY_COLOR: Readonly<Record<string, string>> = {
  common: "#9a98a6",
  uncommon: "#7fd08a",
  rare: "#6fb4ff",
  epic: "#c58cff",
  legendary: "#ffb938",
};
/** 標灰的框色（樣張 GRAY）。 */
export const SIGNATURE_GRAY = "#6a6878";

/** 物品的稀有度（沒標時看 `legendary`，再否則普通；同 `run/gearOffer.ts` 的 `rarityClass`）。 */
export function rarityOf(item: Pick<GearItemInfo, "rarity" | "legendary">): string {
  return item.rarity ?? (item.legendary ? "legendary" : "common");
}

/** 招牌框的顏色：標灰時灰，否則稀有度色。 */
export function signatureColor(rarity: string, off: boolean): string {
  return off ? SIGNATURE_GRAY : (SIGNATURE_RARITY_COLOR[rarity] ?? SIGNATURE_RARITY_COLOR.common ?? SIGNATURE_GRAY);
}

/** 物品的招牌詞條（第一條；沒有時 null）。 */
export function signatureLine(item: Pick<GearItemInfo, "affixes">): ItemLine | null {
  return item.affixes.find((a) => a.signature != null && a.signature !== "") ?? null;
}

/** 招牌框的名字：後端給了（新動作是那一招的名字）就用它，否則詞條的字。 */
export function signatureName(line: ItemLine): string {
  return line.signature_name_zh ?? line.text_zh;
}

/** 招牌框的說明行：有另外的名字時是詞條的字，否則沒有（名字就是全文）。 */
export function signatureText(line: ItemLine): string | null {
  return line.signature_name_zh != null && line.signature_name_zh !== "" ? line.text_zh : null;
}

// ---------------------------------------------------------------------------
// 撿到時的一次性強調
// ---------------------------------------------------------------------------

const shown = new Set<string>();

/** 這件（物品 ID）還沒播過強調。 */
export const fxPending = (id: string): boolean => !shown.has(id);
/** 記下這件已經播過（畫面掛上之後呼叫；同一件之後不再播）。 */
export function markFxShown(id: string): void {
  shown.add(id);
}
/** 測試用：清掉播過的紀錄。 */
export function resetFxShown(): void {
  shown.clear();
}

// ---------------------------------------------------------------------------
// 角色面板的勾選
// ---------------------------------------------------------------------------

/** 這一列現在勾著：生效中、而且沒有在畫面上先取消。 */
export const rowChecked = (row: SignatureRow, dropped: ReadonlySet<string>): boolean => row.active && !dropped.has(row.key);

/** 佔名額的招牌比上限多（才有「換選」可言；不多時全部都生效，不能取消）。 */
export const overCap = (panel: SignaturePanel): boolean => panel.rows.filter((r) => r.counted).length > panel.cap;

/** 按一列的結果：送出新的勾選、先在畫面上取消勾選（等勾另一個）、恢復勾選、已滿提示、沒事。 */
export type PickResult =
  | { kind: "send"; chosen: string[] }
  | { kind: "drop"; key: string }
  | { kind: "undrop"; key: string }
  | { kind: "full" }
  | { kind: "none" };

/** 目前勾著的列（依列的順序）。 */
function checkedKeys(panel: SignaturePanel, dropped: ReadonlySet<string>, keep: (r: SignatureRow) => boolean = () => true): string[] {
  return panel.rows.filter((r) => rowChecked(r, dropped) && keep(r)).map((r) => r.key);
}

/** 勾著的招牌（佔名額）幾個。 */
export function checkedCount(panel: SignaturePanel, dropped: ReadonlySet<string>): number {
  const droppedLive = panel.rows.filter((r) => r.counted && r.active && dropped.has(r.key)).length;
  return Math.max(0, panel.active - droppedLive);
}

/** 節名後面的字：「生效 N／3・改寫規則 N／1」（沒有改寫規則時只寫「生效 N／3」；N 算進畫面上先取消的）。 */
export function countText(panel: SignaturePanel, dropped: ReadonlySet<string>): string {
  const head = `生效 ${checkedCount(panel, dropped)}／${panel.cap}`;
  return panel.has_rule ? `${head}・改寫規則 ${panel.rules}／${panel.rule_cap}` : head;
}

/** 按一列（見 `PickResult`）。改寫規則是圓鈕：按另一條就直接換過去；招牌是方框：已滿時要先取消一個，再勾這個。 */
export function clickRow(panel: SignaturePanel, dropped: ReadonlySet<string>, row: SignatureRow): PickResult {
  const checked = rowChecked(row, dropped);
  if (row.rule) {
    if (checked) return { kind: "none" };
    const chosen = [...checkedKeys(panel, dropped, (r) => !r.rule), row.key];
    const counted = panel.rows.filter((r) => r.counted && chosen.includes(r.key)).length;
    return row.counted && counted > panel.cap ? { kind: "full" } : { kind: "send", chosen };
  }
  if (checked) return overCap(panel) ? { kind: "drop", key: row.key } : { kind: "none" };
  if (dropped.has(row.key)) return { kind: "undrop", key: row.key };
  if (checkedCount(panel, dropped) >= panel.cap) return { kind: "full" };
  return { kind: "send", chosen: [...checkedKeys(panel, dropped), row.key] };
}
