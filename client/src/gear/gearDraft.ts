// 裝備測試（Phase 3G-G4）：手動組物品與整組穿戴的本機檢查、請求格式、數值顯示。
// 規則的裁決在伺服器（沿用引擎的驗證函式）；這裡只做同樣規則的即時提示（讓人不必等請求就看到原因），
// 兩邊的中文原因用語盡量一致。
import type { GearAffixInfo, GearCatalog, GearChoice, GearItemInfo, GearTotalView } from "../api/types";
import type { GearLook } from "../render/gearIcon";

/** 武器大類（`melee`／`ranged`／`focus`）的中文；用目錄裡武器帶的中文名，不寫死。 */
export function weaponClassZh(catalog: GearCatalog, weaponClass: string): string {
  return catalog.weapons.find((w) => w.weapon_class === weaponClass)?.weapon_class_zh ?? "指定類型的武器";
}

/** 武器下拉選項的玩家文字：「冰霜法杖（法器・雙手）」，不露英文代號。 */
export function weaponOptionText(w: GearCatalog["weapons"][number]): string {
  return `${w.name_zh}（${w.weapon_class_zh}${w.two_handed ? "・雙手" : ""}）`;
}

/**
 * 手動組裝的預覽圖示（只影響圖示）：明確選了外觀造型就用它；否則「依欄位預設」——選了武器時依
 * 武器的外觀（`weapons.yaml` 的 `look`），沒選武器才交給欄位（`GearIcon` 的 `slot`）。
 */
export function draftLook(draft: CustomDraft, catalog: GearCatalog): GearLook & { rarity: string } {
  const rarity = draft.legendary ? "legendary" : "common";
  if (draft.kind !== "") return { kind: draft.kind, rarity };
  const look = draft.weapon === "" ? undefined : catalog.weapons.find((w) => w.id === draft.weapon)?.look;
  if (look == null) return { kind: null, rarity };
  return { kind: look.kind, form: look.form ?? null, material: look.material, rarity };
}

/** 手動組的物品（草稿）。 */
export interface CustomDraft {
  name: string;
  /** 主手的武器 id；其他欄位為空字串。 */
  weapon: string;
  paired: boolean;
  /** 副手：是不是盾（詞條有「限盾」）。 */
  shield: boolean;
  legendary: boolean;
  /** 外觀造型；空字串 ＝ 依欄位預設。 */
  kind: string;
  affixes: DraftAffix[];
}

export interface DraftAffix {
  affix: string;
  /** 沒有數值範圍的詞條為 `null`。 */
  value: number | null;
}

/** 一個欄位的選擇：內容庫物品，或自訂物品。 */
export type Pick = { item_id: string } | { custom: CustomDraft };
export type Selection = Partial<Record<string, Pick>>;

export const SHIELD_TAG = "shield";

export function emptyDraft(slotTypeZh: string): CustomDraft {
  return { name: `自訂${slotTypeZh}`, weapon: "", paired: false, shield: false, legendary: false, kind: "", affixes: [] };
}

/** 詞條的玩家文字（`{n}` 換成數值；千分比顯示為百分比）。 */
export function affixText(info: GearAffixInfo, value: number | null): string {
  if (value === null) return info.name_zh;
  const shown = info.value_unit === "permille" ? `${value / 10}%` : String(value);
  return info.name_zh.replace("{n}", shown);
}

/** 詞條的數值範圍文字（沒有範圍時為空字串）。 */
export function rangeText(info: GearAffixInfo): string {
  if (info.value_min == null || info.value_max == null) return "";
  const fmt = (v: number) => (info.value_unit === "permille" ? `${v / 10}%` : String(v));
  return `${fmt(info.value_min)}～${fmt(info.value_max)}`;
}

/** 數值限制在初值範圍內（四捨五入成整數；NaN 退回下限）。 */
export function clampValue(info: GearAffixInfo, value: number): number {
  if (info.value_min == null || info.value_max == null) return value;
  if (Number.isNaN(value)) return info.value_min;
  return Math.min(info.value_max, Math.max(info.value_min, Math.round(value)));
}

/** 加入一條詞條時的初始值（範圍下限；固定效果為 `null`）。 */
export function defaultValue(info: GearAffixInfo): number | null {
  return info.value_min ?? null;
}

function draftTags(draft: CustomDraft): string[] {
  return draft.shield ? [SHIELD_TAG] : [];
}

/** 這條詞條能不能掛在這件物品上；不能時回傳原因（與引擎的 `_affix_slot_problems` 同規則）。 */
export function affixBlocked(info: GearAffixInfo, slotType: string, draft: CustomDraft, catalog: GearCatalog): string | null {
  if (!info.slot_types.includes(slotType as GearAffixInfo["slot_types"][number])) {
    return `不能出現在${catalog.slots.find((s) => s.slot_type === slotType)?.slot_type_zh ?? "這個欄位"}`;
  }
  const weapon = catalog.weapons.find((w) => w.id === draft.weapon);
  if (slotType === "weapon") {
    if (info.weapons.length > 0 && !info.weapons.includes(draft.weapon)) return "只能出現在特定武器上";
    if (info.weapon_class != null && weapon !== undefined && weapon.weapon_class !== info.weapon_class) {
      return `只能出現在${weaponClassZh(catalog, info.weapon_class)}上`;
    }
  }
  const needed = info.item_tags?.[slotType] ?? [];
  if (needed.length > 0 && !needed.some((t) => draftTags(draft).includes(t))) return "只能掛在盾上";
  if (info.legendary_only && !draft.legendary) return "只能出現在傳說物品上";
  return null;
}

/** 手動組的物品自己的問題（還沒考慮其他欄位）。 */
export function draftProblems(draft: CustomDraft, slotType: string, catalog: GearCatalog): string[] {
  const problems: string[] = [];
  const name = draft.name.trim() === "" ? "自訂物品" : draft.name.trim();
  if (draft.name.trim() === "") problems.push("物品需要一個名稱");
  if (slotType === "weapon" && draft.weapon === "") problems.push("主手物品要選一種武器");
  if (draft.affixes.length === 0) problems.push(`${name}：至少要掛 1 條詞條`);
  if (draft.affixes.length > catalog.max_affixes_per_item) {
    problems.push(`${name}：詞條最多 ${catalog.max_affixes_per_item} 條（有 ${draft.affixes.length} 條）`);
  }
  const seen = new Set<string>();
  for (const pick of draft.affixes) {
    const info = catalog.affixes.find((a) => a.id === pick.affix);
    if (info === undefined) {
      problems.push(`${name}：有不在白名單的詞條`);
      continue;
    }
    const label = info.name_zh.replace("{n}", "N");
    if (seen.has(pick.affix)) problems.push(`${name}：詞條「${label}」不可重複`);
    seen.add(pick.affix);
    const blocked = affixBlocked(info, slotType, draft, catalog);
    if (blocked !== null) problems.push(`${name} 的詞條「${label}」${blocked}`);
    if (info.value_min != null && info.value_max != null) {
      if (pick.value === null) problems.push(`${name} 的詞條「${label}」需要數值（${rangeText(info)}）`);
      else if (pick.value < info.value_min || pick.value > info.value_max) {
        problems.push(`${name} 的詞條「${label}」的數值 ${pick.value} 超出範圍 ${rangeText(info)}`);
      }
    }
  }
  return problems;
}

interface ResolvedPick {
  slot: string;
  name: string;
  item: GearItemInfo | null;
  draft: CustomDraft | null;
}

function resolvePick(slot: string, pick: Pick, catalog: GearCatalog): ResolvedPick | null {
  if ("custom" in pick) return { slot, name: pick.custom.name.trim() || "自訂物品", item: null, draft: pick.custom };
  const item = catalog.items.find((i) => i.id === pick.item_id);
  return item === undefined ? null : { slot, name: item.name_zh, item, draft: null };
}

function pickAffixIds(r: ResolvedPick): string[] {
  return r.item !== null ? r.item.affixes.map((a) => a.affix_id) : (r.draft?.affixes.map((a) => a.affix) ?? []);
}

/** 主手是雙手或成對武器（占用副手）。 */
export function occupiesOffHand(selection: Selection, catalog: GearCatalog): boolean {
  const pick = selection["main_hand"];
  if (pick === undefined) return false;
  const r = resolvePick("main_hand", pick, catalog);
  if (r === null) return false;
  if (r.item !== null) return r.item.two_handed || r.item.paired;
  const weapon = catalog.weapons.find((w) => w.id === r.draft?.weapon);
  return (weapon?.two_handed ?? false) || (r.draft?.paired ?? false);
}

/** 整組穿戴的問題（占用、種類、同一枚戒指、代價型條數，以及每件自訂物品的問題）。 */
export function selectionProblems(selection: Selection, catalog: GearCatalog): string[] {
  const problems: string[] = [];
  const resolved: ResolvedPick[] = [];
  for (const slot of catalog.slots) {
    const pick = selection[slot.slot];
    if (pick === undefined) continue;
    const r = resolvePick(slot.slot, pick, catalog);
    if (r === null) {
      problems.push(`${slot.name_zh}：未知的物品`);
      continue;
    }
    if (r.item !== null && r.item.slot_type !== slot.slot_type) {
      problems.push(`${slot.name_zh}只能放${slot.slot_type_zh}類物品：${r.item.name_zh}`);
    }
    if (r.draft !== null) problems.push(...draftProblems(r.draft, slot.slot_type, catalog));
    resolved.push(r);
  }
  const off = resolved.find((r) => r.slot === "off_hand");
  if (off !== undefined && occupiesOffHand(selection, catalog)) {
    const main = resolved.find((r) => r.slot === "main_hand");
    problems.push(`主手是雙手或成對武器（${main?.name ?? ""}），副手被占用，不能放 ${off.name}`);
  }
  const r1 = selection["ring_1"];
  const r2 = selection["ring_2"];
  if (r1 !== undefined && r2 !== undefined && "item_id" in r1 && "item_id" in r2 && r1.item_id === r2.item_id) {
    const name = resolved.find((r) => r.slot === "ring_1")?.name ?? "";
    problems.push(`同一枚戒指不能裝兩次：${name}`);
  }
  const costs = resolved.reduce(
    (n, r) => n + pickAffixIds(r).filter((id) => catalog.affixes.find((a) => a.id === id)?.category === "cost").length,
    0,
  );
  if (costs > catalog.max_cost_affixes) {
    problems.push(`代價型詞條全身最多 ${catalog.max_cost_affixes} 條（目前 ${costs} 條）`);
  }
  return problems;
}

/** 手動組的物品 → API 的自訂物品。 */
export function toCustomItem(draft: CustomDraft, slotType: string): GearChoice["custom"] {
  return {
    name_zh: draft.name.trim() || "自訂物品",
    weapon: slotType === "weapon" && draft.weapon !== "" ? draft.weapon : null,
    paired: slotType === "weapon" && draft.paired,
    tags: slotType === "offhand" && draft.shield ? [SHIELD_TAG] : [],
    legendary: draft.legendary,
    kind: draft.kind === "" ? null : draft.kind,
    affixes: draft.affixes.map((a) => ({ affix: a.affix, value: a.value })),
  };
}

/** 選擇 → `POST /api/battles`（以及 `/api/gear/check`）的 `equipment`。 */
export function toEquipment(selection: Selection, catalog: GearCatalog): Record<string, GearChoice> {
  const out: Record<string, GearChoice> = {};
  for (const slot of catalog.slots) {
    const pick = selection[slot.slot];
    if (pick === undefined) continue;
    out[slot.slot] = "custom" in pick ? { custom: toCustomItem(pick.custom, slot.slot_type) } : { item_id: pick.item_id };
  }
  return out;
}

/** 物品的詞條摘要（列表每一列用）。 */
export function itemSummary(item: GearItemInfo): string {
  return item.affixes.map((a) => a.text_zh).join("；");
}

/** 自訂物品的詞條摘要。 */
export function draftSummary(draft: CustomDraft, catalog: GearCatalog): string {
  return draft.affixes
    .map((a) => {
      const info = catalog.affixes.find((i) => i.id === a.affix);
      return info === undefined ? a.affix : affixText(info, a.value);
    })
    .join("；");
}

/** 手動組物品時可選的詞條（依物品種類篩出可用的，不可用的附原因）。 */
export function affixOptions(catalog: GearCatalog, slotType: string, draft: CustomDraft): { info: GearAffixInfo; blocked: string | null }[] {
  return catalog.affixes.map((info) => ({ info, blocked: affixBlocked(info, slotType, draft, catalog) }));
}

/** 英雄面板的一行加成：主文字、副文字（遞減／截斷說明）。 */
export function totalLine(t: GearTotalView): { main: string; badge: string | null; detail: string } {
  const badge = t.capped ? "已截斷" : null;
  const before = t.capped ? `（截斷前 ${signed(t.before_cap, t.permille)}）` : "";
  const cond = t.condition_zh != null ? `（條件：${t.condition_zh}）` : "";
  return { main: `${t.text_zh}${cond}${before}`, badge, detail: t.note_zh };
}

function signed(value: number, permille: boolean): string {
  if (permille) return `${value > 0 ? "+" : ""}${value / 10}%`;
  return `${value > 0 ? "+" : ""}${value}`;
}

export const SELECTION_KEY = "trpg-gear-test";

export function parseSelection(text: string | null): Selection {
  if (text === null) return {};
  try {
    const raw: unknown = JSON.parse(text);
    return raw !== null && typeof raw === "object" && !Array.isArray(raw) ? (raw as Selection) : {};
  } catch {
    return {};
  }
}

/** 只留下目錄裡還認得的物品（存檔與內容檔不同步時不壞）。 */
export function sanitizeSelection(selection: Selection, catalog: GearCatalog): Selection {
  const out: Selection = {};
  for (const slot of catalog.slots) {
    const pick = selection[slot.slot];
    if (pick === undefined) continue;
    if ("custom" in pick) {
      const ok = pick.custom !== null && typeof pick.custom === "object" && Array.isArray(pick.custom.affixes);
      if (ok) out[slot.slot] = pick;
    } else if (catalog.items.some((i) => i.id === pick.item_id)) {
      out[slot.slot] = pick;
    }
  }
  return out;
}
