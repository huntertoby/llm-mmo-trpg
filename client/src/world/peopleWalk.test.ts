// Phase 6M-3：探索地圖上 NPC 與敵群走一格才播走路片段；差更多、換地圖照舊直接換位置。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { STEP_MS } from "./fieldModel";
import { peopleSteps } from "./peopleWalk";

type Enemy = NonNullable<FieldView["enemies"]>[number];
const enemy = (id: string, x: number, y: number): Enemy =>
  ({ id, x, y, facing: "w", patrol: true, group: "g", name_zh: "盜賊", elite: false, units: [{ unit: "bandit_blade", name_zh: "刀盜", affix: null, elite: false, third: false }], sight: [] }) as Enemy;
const npc = (id: string, x: number, y: number): FieldView["npcs"][number] => ({ id, name_zh: id, x, y, rank: "neutral", rank_zh: "中立" }) as FieldView["npcs"][number];

function field(over: Partial<FieldView>): FieldView {
  return { map_id: "m", npcs: [], enemies: [], ...over } as unknown as FieldView;
}

describe("6M-3：NPC 與敵群走一格", () => {
  it("差一格（上下左右）的才播，依單位 ID 排序；時間照每格 STEP_MS", () => {
    const before = field({ npcs: [npc("b", 1, 1), npc("a", 3, 3)], enemies: [enemy("e0", 5, 5), enemy("e1", 7, 7)] });
    const after = field({ npcs: [npc("b", 2, 1), npc("a", 3, 3)], enemies: [enemy("e0", 5, 4), enemy("e1", 9, 7)] });
    const steps = peopleSteps(before, after);
    expect(steps.map((s) => s.unitId)).toEqual(["enemy_e0", "npc_b"]);
    expect(steps[0]).toEqual({ unitId: "enemy_e0", from: { x: 5, y: 5 }, to: { x: 5, y: 4 }, mode: "walk", durationMs: STEP_MS, style: "slide" });
  });

  it("斜走、沒動、剛出現、換地圖：都不播", () => {
    const before = field({ npcs: [npc("a", 1, 1)], enemies: [enemy("e0", 5, 5)] });
    expect(peopleSteps(before, field({ npcs: [npc("a", 2, 2)], enemies: [enemy("e0", 5, 5), enemy("e9", 1, 0)] }))).toEqual([]);
    expect(peopleSteps(before, field({ map_id: "other", npcs: [npc("a", 2, 1)] }))).toEqual([]);
    expect(peopleSteps(before, null)).toEqual([]);
  });
});
