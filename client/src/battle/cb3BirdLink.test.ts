// CB-3 順手項（美術 PM docs/art/CB-2b檢查.md）：① 鳥走路後緊接攻擊：略過走路結尾的落地與攻擊開頭的起飛；
// ② 異形的目標在正南、正北時出招不翻面。時間軸走正式的 playbackPlan。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StepOut } from "../api/types";
import { PERCH_MS } from "../render/creaturePose";
import { playbackPlan, SPEED_SCALE, type Frame } from "./playback";
import { unit } from "./testFixtures";
import { creatureFacingTo } from "./walkAnim";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "./viewGrip";

const at = (x: number, y: number): Pos => ({ x, y });
const look = (body: string, variant: string) => ({ doll_look: { creature: { body, variant, material: "fur" } } }) as never;
const BIRD = look("flyer", "bird");

function field(casterAt: Pos, l: ReturnType<typeof look>, heroAt: Pos = at(4, 2)): BattleView {
  return {
    map_id: "t", width: 9, height: 9, tiles: [], objects: [], traps: [], zones: [], runes: [], source_wells: [],
    units: [unit("c", "enemy", casterAt.x, casterAt.y, { hp: 20, max_hp: 20, facing: "east", ...(l as object) }), unit("h", "ally", heroAt.x, heroAt.y, { hp: 20, max_hp: 20, facing: "west" })],
  } as unknown as BattleView;
}
const walk = (a: Pos, b: Pos, seq: number) => ({ seq, round: 1, type: "unit_moved", unit_id: "c", from_pos: a, to_pos: b, mode: "walk", cost: 1 });
const basic = [{ seq: 1, round: 1, type: "attack_rolled", attacker_id: "c", target_id: "h", hit: true }, { seq: 2, round: 1, type: "damage_dealt", target_id: "h", source_id: "c", element: "physical", amount: 3 }];

/** 兩步：c 從 (1,2) 走到 (3,2)，接著打 (4,2) 的 h。 */
function moveThenAttack(l: ReturnType<typeof look>, o: { reduced?: boolean; attacker?: string; between?: boolean } = {}): Frame[] {
  const v0 = field(at(1, 2), l);
  const v1 = field(at(3, 2), l);
  const move = { actor_id: "c", events: [walk(at(1, 2), at(2, 2), 1), walk(at(2, 2), at(3, 2), 2)], view: v1, step: { type: "move" } } as unknown as StepOut;
  const hit = { actor_id: o.attacker ?? "c", events: basic, view: v1, step: { type: "attack" } } as unknown as StepOut;
  const other = { actor_id: "h", events: [], view: v1, step: { type: "end_turn" } } as unknown as StepOut;
  const steps = o.between === true ? [move, other, hit] : [move, hit];
  const res = { steps, initial_view: v0, view: v1 } as unknown as BattleResponse;
  return playbackPlan(res, "h", "normal", {}, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, o.reduced === true).frames;
}
const walkOf = (f: Frame) => {
  const m = f.motions[f.motions.length - 1]!;
  return m.kind === "walk" ? m.walk : null;
};

describe("CB-3 鳥走路後緊接攻擊：不落地、不再起飛", () => {
  it("鳥：走路那一步標 aloft，攻擊那一步沒有起飛列（出招從 0 開始），結尾照舊落地一次", () => {
    const [move, hit] = moveThenAttack(BIRD) as [Frame, Frame];
    expect(walkOf(move)?.aloft).toBe(true);
    const rows = hit.skill!.filter((r) => r.unitId === "c");
    expect(rows.some((r) => r.perch === "up")).toBe(false);
    expect(rows.filter((r) => r.perch === "down")).toHaveLength(1);
    const strike = rows.find((r) => r.strike)!;
    expect(strike.startMs).toBe(0);
    // 命中點比「落地再起飛」早一個起飛過場的長度
    const alone = playbackPlan({ steps: [{ actor_id: "c", events: basic, view: field(at(3, 2), BIRD), step: { type: "attack" } }], initial_view: field(at(3, 2), BIRD), view: field(at(3, 2), BIRD) } as unknown as BattleResponse, "h", "normal", {}, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView).frames[0]!;
    const aloneStrike = alone.skill!.find((r) => r.unitId === "c" && r.strike)!;
    expect(alone.skill!.some((r) => r.perch === "up")).toBe(true);
    expect(aloneStrike.hitMs! - strike.hitMs!).toBeCloseTo(Math.round(PERCH_MS * SPEED_SCALE.normal), 0);
    expect(hit.vfx!.casts[0]!.impactMs).toBeCloseTo(strike.hitMs!, 0);
  });

  it("不是鳥（蝙蝠、走獸、人形）不變：走路不標、沒有過場列", () => {
    for (const l of [look("flyer", "bat"), look("hound", ""), {} as never]) {
      const [move, hit] = moveThenAttack(l) as [Frame, Frame];
      expect(walkOf(move)?.aloft).toBeUndefined();
      expect(hit.skill!.some((r) => r.perch !== undefined)).toBe(false);
    }
  });

  it("接不起來的照舊落地再起飛：中間隔了別人的一步、下一步不是同一隻、減少動態", () => {
    const apart = moveThenAttack(BIRD, { between: true });
    expect(walkOf(apart[0]!)?.aloft).toBeUndefined();
    expect(apart[2]!.skill!.some((r) => r.perch === "up")).toBe(true);
    const reduced = moveThenAttack(BIRD, { reduced: true });
    expect(walkOf(reduced[0]!)?.aloft).toBeUndefined();
    expect(reduced[1]!.skill!.some((r) => r.perch !== undefined)).toBe(false);
  });

  it("只有走路、後面沒有攻擊：不標", () => {
    const v0 = field(at(1, 2), BIRD);
    const v1 = field(at(2, 2), BIRD);
    const res = { steps: [{ actor_id: "c", events: [walk(at(1, 2), at(2, 2), 1)], view: v1, step: { type: "move" } }], initial_view: v0, view: v1 } as unknown as BattleResponse;
    expect(walkOf(playbackPlan(res, "h", "normal", {}, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView).frames[0]!)?.aloft).toBeUndefined();
  });
});

describe("CB-3 異形出招的左右面：正南、正北不翻面", () => {
  it("目標偏東＝東、偏西＝西（含斜向）；同一欄（正南、正北）維持原本的朝向", () => {
    const from = at(4, 4);
    for (const cur of ["east", "west", "south", "north"] as const) {
      expect(creatureFacingTo(from, at(4, 1), cur)).toBe(cur);
      expect(creatureFacingTo(from, at(4, 7), cur)).toBe(cur);
      expect(creatureFacingTo(from, from, cur)).toBe(cur);
      expect(creatureFacingTo(from, at(6, 4), cur)).toBe("east");
      expect(creatureFacingTo(from, at(5, 7), cur)).toBe("east");
      expect(creatureFacingTo(from, at(1, 4), cur)).toBe("west");
      expect(creatureFacingTo(from, at(3, 0), cur)).toBe("west");
    }
  });
});
