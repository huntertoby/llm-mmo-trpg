// 實地地圖的環境動態資料（Phase 6N-10，純函式）：FieldView → AmbientScene（NPC 身分、營火位置、場景鍵）。
// 伺服器沒有 NPC 職業欄位，也不新增：照「NPC 站在哪個設施旁邊」推。鐵匠鋪、附魔台旁 ＝ 鐵匠；酒館、雇用櫃檯、商店旁 ＝ 掌櫃；
// 其他 ＝ 一般。距離用切比雪夫 2 格以內（石師傅站在鐵砧旁、柳掌櫃站在攤位後）。只影響畫面。
import type { FieldView } from "../api/types";
import type { AmbientScene } from "../render/ambientModel";
import type { NpcRole } from "../render/npcFidgets";
/** 同 fieldModel.npcUnitId（不從那裡匯入，免得兩個檔互相匯入）。 */
const npcUnitId = (id: string): string => `npc_${id}`;

/** 設施種類 → NPC 身分（鐵匠優先於掌櫃）。 */
export const ROLE_FACILITIES: Readonly<Record<Exclude<NpcRole, "town">, readonly string[]>> = {
  smith: ["smithy", "enchanter"],
  keeper: ["tavern", "hire", "shop", "tavern_storyteller", "tavern_veteran"],
};

/** 離設施幾格內算「在那個設施工作」。 */
export const ROLE_REACH = 2;

type Spot = { x: number; y: number; kind: string };

export function npcRole(at: { x: number; y: number }, facilities: readonly Spot[]): NpcRole {
  const near = (kinds: readonly string[]) => facilities.some((f) => kinds.includes(f.kind) && Math.max(Math.abs(f.x - at.x), Math.abs(f.y - at.y)) <= ROLE_REACH);
  if (near(ROLE_FACILITIES.smith)) return "smith";
  if (near(ROLE_FACILITIES.keeper)) return "keeper";
  return "town";
}

export function fieldAmbient(field: FieldView): AmbientScene {
  const roles: Record<string, NpcRole> = {};
  for (const n of [...field.npcs].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))) roles[npcUnitId(n.id)] = npcRole(n, field.facilities);
  const fires = (field.campfires ?? []).map((c) => ({ x: c.x, y: c.y })).sort((a, b) => a.y - b.y || a.x - b.x);
  return { key: field.map_id, roles, fires };
}
