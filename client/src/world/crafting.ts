// 鐵匠與附魔台的純函式（Phase 5D-3；docs/phases/Phase5計畫.md 30.5）。
// 規則在後端（能不能打、費用、候選詞條都由後端算好），這裡只處理打造表單的草稿與送出的動作。
import type { WorldAction, WorldCrafting } from "../api/types";

export interface CraftDraft {
  slot: string;
  rarity: string;
  /** 指定的詞條 id；`signature:<種類>`＝改指定招牌類型（E6-a2，和詞條二選一）。 */
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

/** 指定招牌類型的選項值前綴（E6-a2，08 8.27：打造可以改指定招牌「類型」，不能指定是哪一條）。 */
export const SIGNATURE_PREFIX = "signature:";

/** 招牌類型的選項值（`signature:<種類>`）。 */
export function signatureValue(kind: string): string {
  return SIGNATURE_PREFIX + kind;
}

/** 傳說（E6-c2）：類型選項是獨特效果的類型，不是招牌類型（08 8.30 第 10 點）。 */
export const LEGENDARY = "legendary";

type CraftSlot = WorldCrafting["slots"][number];

/** 這個部位、這個稀有度能改指定的類型：傳說是獨特效果（`uniques`），其他是招牌（`signatures`）。 */
export function kindOptions(slot: CraftSlot | undefined, rarity: string): CraftSlot["signatures"] {
  return (rarity === LEGENDARY ? slot?.uniques : slot?.signatures) ?? [];
}

/** 這個稀有度能打的部位（E6-c2：傳說只能打主手、副手、身體、腳、項鍊；後端給空的＝每個部位都能打）。 */
export function slotsFor(crafting: WorldCrafting, rarity: string): CraftSlot[] {
  const allowed = crafting.rarities.find((r) => r.rarity === rarity)?.slots ?? [];
  return allowed.length === 0 ? crafting.slots : crafting.slots.filter((s) => allowed.includes(s.slot_type));
}

/** 換部位：詞條換成新部位的第一條（原本那條、或原本的招牌類型新部位也能選就保留）。 */
export function withSlot(draft: CraftDraft, crafting: WorldCrafting, slot: string): CraftDraft {
  const found = crafting.slots.find((s) => s.slot_type === slot);
  const options = found?.affixes ?? [];
  const kinds = kindOptions(found, draft.rarity).map((k) => signatureValue(k.id));
  const keep = options.some((a) => a.id === draft.affix) || kinds.includes(draft.affix);
  return { ...draft, slot, affix: keep ? draft.affix : options[0]?.id ?? "" };
}

/** 換稀有度（E6-c2）：部位不能打這個稀有度時換成第一個能打的；類型選項跟著換（招牌 ↔ 獨特效果）。 */
export function withRarity(draft: CraftDraft, crafting: WorldCrafting, rarity: string): CraftDraft {
  const slots = slotsFor(crafting, rarity);
  const slot = slots.some((s) => s.slot_type === draft.slot) ? draft.slot : slots[0]?.slot_type ?? draft.slot;
  return withSlot({ ...draft, rarity }, crafting, slot);
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

/** 送出的 `craft` 動作（詞條空白時不帶，給隱藏配方用；選了招牌類型時改帶 `signature`；後端裁決）。 */
export function craftAction(draft: CraftDraft, station: string): WorldAction {
  const signature = draft.affix.startsWith(SIGNATURE_PREFIX) ? draft.affix.slice(SIGNATURE_PREFIX.length) : null;
  return {
    kind: "craft",
    station,
    slot_type: draft.slot as never,
    rarity: draft.rarity as never,
    affix: draft.affix === "" || signature !== null ? null : draft.affix,
    grade: draft.grade,
    materials: draft.materials,
    ...(signature !== null ? { signature: signature as never } : {}),
  };
}
