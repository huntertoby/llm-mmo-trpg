// 背包畫面與鐵匠畫面的純函式（Phase 5D-4；docs/phases/Phase5計畫.md 33.2）。
// 規則都在後端（能不能換上、比較、能不能打造都由後端算好）；這裡只整理顯示與送出的動作。
import type { GearCandidate, WorldAction, WorldBagItem, WorldInventory } from "../api/types";

/** 背包裡某件裝備能不能換上與原因（後端的 `can_equip`／`equip_problem_zh`）。 */
export function equipState(inventory: WorldInventory, itemId: string): { ok: boolean; reason: string } {
  const row: WorldBagItem | undefined = inventory.bag.find((b) => b.gear === true && b.item === itemId);
  if (row === undefined) return { ok: false, reason: "背包裡沒有這件" };
  if (row.can_equip === true) return { ok: true, reason: "" };
  return { ok: false, reason: row.equip_problem_zh ?? "不能換上" };
}

/** 戒指的另一個欄位（戒指可以指定戴在哪一隻；其他部位為 `null`）。 */
export function otherRingSlot(slot: string): string | null {
  if (slot === "ring_1") return "ring_2";
  if (slot === "ring_2") return "ring_1";
  return null;
}

/** 換上的動作：照後端建議的欄位（戒指可另指定）。 */
export function equipAction(cand: Pick<GearCandidate, "item">, slot: string | null = null): WorldAction {
  return slot === null ? { kind: "equip", item: cand.item.id } : { kind: "equip", item: cand.item.id, slot: slot as never };
}

/** 背包裡不是裝備的物品（消耗品、材料、染料；裝備在背包畫面另外用裝備卡列）。 */
export function nonGear(inventory: WorldInventory): WorldBagItem[] {
  return inventory.bag.filter((b) => b.gear !== true);
}

/** 右側摘要的一行：「12／30 格・裝備 2 件・腰包 1／3」。 */
export function bagSummary(inventory: WorldInventory): string {
  const gear = inventory.bag.filter((b) => b.gear === true).length;
  return `${inventory.slots_used}／${inventory.slots_max} 格・裝備 ${gear} 件・腰包 ${inventory.pouch_count}／${inventory.pouch_max}`;
}

/** 配方碼輸入的正規化：去空白與連字號、轉大寫。 */
export function normalizeCode(text: string): string {
  return text.replace(/[\s-]/g, "").toUpperCase();
}

/** 配方碼輸入的問題（送出鈕停用的原因）；可以送出時為 `null`。碼存不存在、能不能打由後端裁決。 */
export function codeProblem(text: string): string | null {
  const code = normalizeCode(text);
  if (code === "") return "輸入 10 碼的配方碼";
  if (!/^[0-9A-F]{10}$/.test(code)) return "配方碼是 10 碼（0～9、A～F）";
  return null;
}
