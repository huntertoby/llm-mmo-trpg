// 裝備外觀 → 紙娃娃部件（Phase 3G-G5b；美術 PM 的 docs/art/裝備外觀移植需求.md 第 4 節、樣張 gearArt.js 的 `dollItem()`／`dollGear()`）。
// 純資料與純函式（不碰 Canvas）：外觀欄位（`kind`／`form`／`material`／`dye`／`keywords`）經 `resolveGear` 驗證與補預設後，
// 轉成紙娃娃的 `GearItem`；不認得的值一律退回預設，不得出錯。項鍊與戒指不畫。
import { GEAR_DYE } from "./artPalette";
import type { GearItem, GearSlot } from "./appearance";
import { gearKinds, resolveGear, type GearLook } from "./gearIcon";

/** 裝備摘要的一個欄位（`UnitView.equipment[]` 的結構子集）。 */
export interface DollEquipment {
  slot: string;
  appearance?: GearLook | null;
}

/** 裝備欄位 → 紙娃娃欄位；項鍊、戒指不在表內（不畫）。 */
const DOLL_SLOT: Readonly<Record<string, GearSlot>> = {
  main_hand: "main_hand",
  off_hand: "off_hand",
  head: "head",
  body: "body",
  hands: "hands",
  feet: "feet",
};

/** 外觀清單的 `slotType` → 紙娃娃欄位。 */
const SLOT_OF_TYPE: Readonly<Record<string, GearSlot | null>> = {
  weapon: "main_hand",
  offhand: "off_hand",
  head: "head",
  body: "body",
  hands: "hands",
  feet: "feet",
  neck: null,
  ring: null,
};

/** 標準 `kind` → 紙娃娃部件（只列名稱不同的；其餘同名）。 */
const HEAD_PART: Readonly<Record<string, (form: string) => string>> = {
  hat: (f) => (f === "wide" ? "wide_hat" : "wizard_hat"),
  circlet: (f) => (f === "crown" ? "crown" : "bandana"),
  helmet: (f) => (f === "horned" ? "horned_helm" : f === "greathelm" ? "greathelm" : "helmet"),
};
const PART_OF: Readonly<Record<string, string>> = {
  cloth_gloves: "gloves",
  leather_gloves: "gloves",
  round_shield: "shield_round",
  kite_shield: "shield_kite",
  dual_dagger: "dagger",
  dual_pistol: "pistol",
};

/** 元素關鍵字 → 紙娃娃的 `element`。 */
export const ELEMENT_OF_KEYWORD: Readonly<Record<string, string>> = { ignite: "fire", wet: "water", charged: "lightning", frozen: "ice" };

/** 一律雙手的武器部件（武器 id 不在外觀表時，用部件判斷副手是否被占用）。 */
const TWO_HANDED_PARTS: ReadonlySet<string> = new Set(["greatsword", "bow", "crossbow", "longgun", "shotgun", "spear", "scythe"]);

const PAIRED_KINDS: ReadonlySet<string> = new Set(gearKinds().filter((k) => k.paired).map((k) => k.id));

function partOf(kind: string, form: string): string {
  const head = HEAD_PART[kind];
  return head !== undefined ? head(form) : (PART_OF[kind] ?? kind);
}

/** 一件裝備的外觀 → 紙娃娃的 `GearItem`；項鍊、戒指（以及找不到欄位時）回傳 `null`。
 *  `slot`：所在的裝備欄位。造型的欄位類型和 `slot` 不符時，退回該欄位的預設造型。 */
export function dollItem(look: GearLook | null | undefined, slot: string): { slot: GearSlot; item: GearItem; paired: boolean } | null {
  const target = DOLL_SLOT[slot];
  if (target === undefined) return null;
  let r = resolveGear(look, slot);
  const type = gearKinds().find((k) => k.id === r.kind)?.slotType;
  if (type === undefined || SLOT_OF_TYPE[type] !== target) r = resolveGear({ ...look, kind: null, form: null, material: null }, slot);
  const item: GearItem = { kind: partOf(r.kind, r.form), form: r.form, material: r.material };
  if (r.dye !== null) item.color = GEAR_DYE[r.dye] as string;
  const element = r.keywords.map((k) => ELEMENT_OF_KEYWORD[k]).find((e) => e !== undefined);
  if (element !== undefined) item.element = element;
  return { slot: target, item, paired: PAIRED_KINDS.has(r.kind) };
}

/** 成對武器造型（雙匕首、雙手槍）→ 單把武器的部件 kind（紙娃娃主手、副手各畫一把）；不是成對造型回傳 `null`。 */
export function pairedPart(kind: string): string | null {
  return PAIRED_KINDS.has(kind) ? partOf(kind, "") : null;
}

export interface DollGear {
  gear: Partial<Record<GearSlot, GearItem>>;
  /** 成對武器：副手也畫同一把。 */
  paired: boolean;
}

/** 一整套裝備 → 各欄位的紙娃娃部件。成對武器：主手、副手各一把單把武器。 */
export function dollGear(equipment: readonly DollEquipment[]): DollGear {
  const gear: DollGear["gear"] = {};
  let paired = false;
  // 依欄位名排序，結果不依賴陣列順序（確定性、快取鍵穩定）
  for (const e of [...equipment].sort((a, b) => (a.slot < b.slot ? -1 : a.slot > b.slot ? 1 : 0))) {
    if (e.slot === "main_hand" && e.appearance?.kind == null) continue; // 主手沒寫造型：沿用武器 id 的外觀
    const d = dollItem(e.appearance, e.slot);
    if (d === null) continue;
    gear[d.slot] = d.item;
    if (d.slot === "main_hand" && d.paired) paired = true;
  }
  const main = gear.main_hand;
  if (paired && main !== undefined) gear.off_hand = { ...main };
  return { gear, paired };
}

/** 紙娃娃的主手部件是否為雙手武器（武器 id 不在外觀表時才用；權杖、短杖、釘頭錘是單手）。 */
export function isTwoHandedPart(item: GearItem): boolean {
  if (item.kind === "staff") return item.form !== "scepter" && item.form !== "wand";
  if (item.kind === "hammer") return item.form !== "mace";
  return TWO_HANDED_PARTS.has(item.kind);
}
