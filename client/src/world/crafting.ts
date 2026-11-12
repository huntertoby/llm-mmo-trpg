// 鐵匠與附魔台的純函式（Phase 5D-3；docs/phases/Phase5計畫.md 30.5）。
// 規則在後端（能不能打、費用、候選詞條都由後端算好），這裡只處理打造表單的草稿與送出的動作。
import type { WorldAction, WorldCrafting } from "../api/types";

export interface CraftDraft {
  slot: string;
  rarity: string;
  affix: string;
  grade: string;
  materials: string[];
}

/** 表單的初值：第一個有詞條可選的部位、第一個稀有度、第一種通用料。 */
/** 防具的部位（08 8.12 的防具欄位）：入門期打造只限防具時，部位下拉預設第一個防具（美術追蹤②；只是預設值，伺服器照樣擋）。 */
export const ARMOR_SLOT_TYPES: readonly string[] = ["head", "body", "hands", "feet"];

/** 打造表單的起始值。`armorOnly`（入門期，伺服器的限制資料 `limits.smith` 有值）：部位預設第一個防具。 */
export function initialDraft(crafting: WorldCrafting, armorOnly = false): CraftDraft {
  const usable = crafting.slots.filter((s) => s.affixes.length > 0);
  const armor = armorOnly ? usable.find((s) => ARMOR_SLOT_TYPES.includes(s.slot_type)) : undefined;
  const slot = armor ?? usable[0] ?? crafting.slots[0];
  const grade = crafting.materials.find((m) => m.grade);
  return {
    slot: slot?.slot_type ?? "",
    rarity: crafting.rarities[0]?.rarity ?? "rare",
    affix: slot?.affixes[0]?.id ?? "",
    grade: grade?.item ?? "",
    materials: [],
  };
}

/** 換部位：詞條換成新部位的第一條（原本那條新部位也能選就保留）。 */
export function withSlot(draft: CraftDraft, crafting: WorldCrafting, slot: string): CraftDraft {
  const options = crafting.slots.find((s) => s.slot_type === slot)?.affixes ?? [];
  const keep = options.some((a) => a.id === draft.affix);
  return { ...draft, slot, affix: keep ? draft.affix : options[0]?.id ?? "" };
}

/** 勾選或取消一種特色材料（最多 `max` 種；滿了再勾不會加）。 */
export function toggleMaterial(draft: CraftDraft, item: string, max: number): CraftDraft {
  if (draft.materials.includes(item)) return { ...draft, materials: draft.materials.filter((m) => m !== item) };
  if (draft.materials.length >= max) return draft;
  return { ...draft, materials: [...draft.materials, item].sort() };
}

/** 表單還缺什麼（送出鈕停用的原因）；可以送出時為 null。 */
export function draftProblem(draft: CraftDraft): string | null {
  if (draft.slot === "") return "選一個部位";
  if (draft.grade === "") return "背包裡沒有通用料（粗料、精料、上料）";
  return null;
}

/** 送出的 `craft` 動作（詞條空白時不帶，給隱藏配方用；後端裁決）。 */
export function craftAction(draft: CraftDraft, station: string): WorldAction {
  return {
    kind: "craft",
    station,
    slot_type: draft.slot as never,
    rarity: draft.rarity as never,
    affix: draft.affix === "" ? null : draft.affix,
    grade: draft.grade,
    materials: draft.materials,
  };
}
