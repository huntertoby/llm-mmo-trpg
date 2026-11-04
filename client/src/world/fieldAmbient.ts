// 實地地圖的環境動態資料（Phase 6N-10，純函式）：FieldView → AmbientScene（NPC 身分、營火位置、場景鍵）。
// 伺服器沒有 NPC 職業欄位，也不新增：照「NPC 站在哪個設施旁邊」推。鐵匠鋪、附魔台旁 ＝ 鐵匠；酒館、雇用櫃檯、商店旁 ＝ 掌櫃；
// 其他 ＝ 一般。距離用切比雪夫 2 格以內（石師傅站在鐵砧旁、柳掌櫃站在攤位後）。只影響畫面。
import type { FieldView } from "../api/types";
import type { AmbientScene } from "../render/ambientModel";
import type { NpcRole } from "../render/npcFidgets";
import { figureUnitId } from "./npcLook";
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

/**
 * 做職業動作時轉向哪一側（6Q-1）：朝最近的那個工作設施（切比雪夫距離，再依 y、x、種類排序，確定性）。
 * 設施在正上方或正下方（同一欄）時沒有偏好，回傳 `null`（由 `npcFidgets.workFacing` 決定）。
 */
export function workSide(at: { x: number; y: number }, facilities: readonly Spot[], role: NpcRole): "east" | "west" | null {
  if (role === "town") return null;
  const kinds = ROLE_FACILITIES[role];
  const dist = (f: Spot) => Math.max(Math.abs(f.x - at.x), Math.abs(f.y - at.y));
  const near = facilities
    .filter((f) => kinds.includes(f.kind) && dist(f) <= ROLE_REACH)
    .sort((a, b) => dist(a) - dist(b) || a.y - b.y || a.x - b.x || (a.kind < b.kind ? -1 : a.kind > b.kind ? 1 : 0));
  const f = near[0];
  if (f === undefined || f.x === at.x) return null;
  return f.x > at.x ? "east" : "west";
}

export function fieldAmbient(field: FieldView): AmbientScene {
  const roles: Record<string, NpcRole> = {};
  const sides: Record<string, "east" | "west"> = {};
  for (const n of [...field.npcs].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))) {
    const role = npcRole(n, field.facilities);
    roles[npcUnitId(n.id)] = role;
    const side = workSide(n, field.facilities, role);
    if (side !== null) sides[npcUnitId(n.id)] = side;
  }
  // 6V-1：情境物件上的人（主城功能型 NPC）的身分照內容的 `figure.work`（工坊師傅打鐵）；
  // 朝向東西的做職業動作時本來就是側面，不用另給 `sides`
  for (const o of field.situation_objects ?? []) if (o.figure != null) roles[figureUnitId(o.id)] = o.figure.work ?? "town";
  const fires = (field.campfires ?? []).map((c) => ({ x: c.x, y: c.y })).sort((a, b) => a.y - b.y || a.x - b.x);
  return { key: field.map_id, roles, sides, fires };
}
