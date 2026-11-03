// 探索地圖上 NPC 與敵群走一格（Phase 6M-3）：新舊畫面比對，位置差一格（上下左右）的人播走路片段；
// 差更多（瞬移、換地圖、剛出現）的照舊直接換位置。純函式，位置一律以伺服器回來的畫面為準。
import type { FieldView, Pos } from "../api/types";
import { enemyUnitId, npcUnitId, STEP_MS } from "./fieldModel";

export interface PersonStep {
  unitId: string;
  from: Pos;
  to: Pos;
  mode: "walk";
  durationMs: number;
  style: "slide";
}

function adjacent(a: Pos, b: Pos): boolean {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y) === 1;
}

/** 同一張地圖上，從 `before` 到 `after` 走了一格的 NPC 與敵群（依單位 ID 排序，確定性）。換地圖時沒有。 */
export function peopleSteps(before: FieldView, after: FieldView | null, stepMs = STEP_MS): PersonStep[] {
  if (after === null || after.map_id !== before.map_id) return [];
  const was = new Map<string, Pos>();
  for (const n of before.npcs) was.set(npcUnitId(n.id), { x: n.x, y: n.y });
  for (const e of before.enemies ?? []) was.set(enemyUnitId(e), { x: e.x, y: e.y });
  const out: PersonStep[] = [];
  const now: Array<[string, Pos]> = [
    ...after.npcs.map((n): [string, Pos] => [npcUnitId(n.id), { x: n.x, y: n.y }]),
    ...(after.enemies ?? []).map((e): [string, Pos] => [enemyUnitId(e), { x: e.x, y: e.y }]),
  ];
  for (const [unitId, to] of now) {
    const from = was.get(unitId);
    if (from !== undefined && adjacent(from, to)) out.push({ unitId, from, to, mode: "walk", durationMs: stepMs, style: "slide" });
  }
  return out.sort((a, b) => (a.unitId < b.unitId ? -1 : a.unitId > b.unitId ? 1 : 0));
}
