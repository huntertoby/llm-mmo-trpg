// CB-2c：蛋的拋物線（四方向的起點、終點、孵化時刻）、鳥的攻擊過場（普攻、俯衝、爪擊 × 減少動態開／關）。
// 時間軸走正式的 skillTimeline／playbackPlan；拋物線是純函式，畫面像素由開發頁截圖驗。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StepOut } from "../api/types";
import { creaturePoseKey, perchRowLevel, perchRowPose, PERCH_MS, quantizeCreaturePose, type CreatureAttackType } from "../render/creaturePose";
import { eggArcPlan, eggAt } from "../render/eggArc";
import { rigKey } from "../render/inkCreature";
import { attackClipFor, BODY_ANIM, creatureAttackHitU, creatureClipInfo, EGG_FROM_U, EGG_START, qCreaturePartPose } from "../render/qCreatureAnim";
import { creatureOf } from "../render/unitSprite";
import { playbackPlan, SPEED_SCALE } from "./playback";
import { RECOVER_MS, skillTimeline, type SkillRow, type StrikeOf } from "./skillSequence";
import { unit } from "./testFixtures";
import { vfxFor } from "./vfx";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "./viewGrip";

const at = (x: number, y: number): Pos => ({ x, y });
const creature = (body: string, variant: string): Partial<Parameters<typeof unit>[4]> => ({ doll_look: { creature: { body, variant, material: "fur" } } }) as never;

function field(casterAt: Pos, targetAt: Pos, look: ReturnType<typeof creature>): BattleView {
  return {
    map_id: "t", width: 9, height: 9, tiles: [], objects: [], traps: [], zones: [], runes: [], source_wells: [],
    units: [unit("c", "enemy", casterAt.x, casterAt.y, { hp: 20, max_hp: 20, facing: "east", ...look }), unit("h", "ally", targetAt.x, targetAt.y, { hp: 20, max_hp: 20, facing: "west" })],
  } as unknown as BattleView;
}
const skillUsed = (tiles: Pos[], skill = "sk") => ({ seq: 1, round: 1, type: "skill_used", unit_id: "c", skill_id: skill, tiles });
const dmg = { seq: 2, round: 1, type: "damage_dealt", target_id: "h", source_id: "c", element: "physical", amount: 3 };
const basic = [{ seq: 1, round: 1, type: "attack_rolled", attacker_id: "c", target_id: "h", hit: true }, dmg];

function respond(view: BattleView, events: Record<string, unknown>[], cards = {}, reduced = false) {
  const step = { actor_id: "c", events, view, step: { type: "skill" } } as unknown as StepOut;
  const res = { steps: [step], initial_view: view, view } as unknown as BattleResponse;
  return playbackPlan(res, "h", "normal", cards, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, reduced).frames[0]!;
}

const BIRD = creature("flyer", "bird");
const birdCases: ReadonlyArray<readonly [string, CreatureAttackType, Record<string, unknown>[], Record<string, unknown>]> = [
  ["普攻（爪擊）", "melee", basic, {}],
  ["俯衝斬", "charge", [skillUsed([at(3, 2)], "skill_plunging_strike"), dmg, dmg], { skill_plunging_strike: { id: "skill_plunging_strike", shape: "single", effect_ids: ["damage", "damage"], icon: { segments: [{ shape_id: "single", range: 1, effects: [{ type: "damage" }] }] } } }],
  ["靜電掌（遠程施放）", "cast", [skillUsed([at(5, 2)], "skill_static_palm"), dmg], { skill_static_palm: { id: "skill_static_palm", shape: "single", effect_ids: ["damage"], icon: { segments: [{ shape_id: "single", range: 2, effects: [{ type: "damage" }] }] } } }],
];

/** 過場這一列取樣的落地比例種類（量化到 4 格）。 */
function levels(rows: readonly SkillRow[], perch: "up" | "down"): number[] {
  const r = rows.find((x) => x.perch === perch);
  if (r === undefined) return [];
  const seen = new Set<number>();
  for (let t = 0; t < 1; t += 0.01) seen.add(perchRowLevel(perch, t));
  seen.delete(0);
  return [...seen].sort((a, b) => a - b);
}

describe("CB-2c 鳥的攻擊過場", () => {
  describe.each(birdCases)("%s", (_name, action, events, cards) => {
    const target = action === "cast" ? at(5, 2) : at(3, 2);
    const view = field(at(2, 2), target, BIRD);

    it("減少動態關：前後各一列、各 4 格（動作類型沿用），命中點照舊對齊出手格", () => {
      const f = respond(view, events, cards);
      const rows = f.skill!.filter((r) => r.unitId === "c");
      const strike = rows.find((r) => r.strike)!;
      const up = rows.find((r) => r.perch === "up")!;
      const down = rows.find((r) => r.perch === "down")!;
      const scale = SPEED_SCALE.normal;
      expect(strike.creature?.action).toBe(action);
      expect(up.ms).toBe(Math.round(PERCH_MS * scale));
      expect(up.startMs + up.ms).toBeCloseTo(strike.startMs, 0);
      expect(down.startMs).toBeCloseTo(strike.startMs + strike.ms, 0);
      expect(down.ms).toBe(Math.round(PERCH_MS * scale));
      expect(up.creature?.action).toBe(action);
      expect(down.creature?.action).toBe(action);
      expect(levels(rows, "up")).toEqual([0.25, 0.5, 0.75, 1]);
      expect(levels(rows, "down")).toEqual([0.25, 0.5, 0.75, 1]);
      expect(rows.some((r) => r.recover && r.perch === undefined)).toBe(false);
      expect(f.vfx!.casts[0]!.startMs).toBeLessThanOrEqual(strike.hitMs!);
    });

    it("減少動態開：沒有過場列（時間軸不留位置），命中點和不加過場時一樣", () => {
      const f = respond(view, events, cards, true);
      const rows = f.skill!.filter((r) => r.unitId === "c");
      expect(rows.some((r) => r.perch !== undefined)).toBe(false);
      const strike = rows.find((r) => r.strike)!;
      expect(strike.startMs).toBe(0);
      expect(rows.filter((r) => r.recover)).toHaveLength(1);
    });
  });

  it("非鳥異形（鷹以外的飛行、走獸）沒有過場；人形也沒有", () => {
    for (const look of [creature("flyer", "bat"), creature("hound", ""), creature("lizard", "")]) {
      const view = field(at(2, 2), at(3, 2), look);
      for (const reduced of [false, true]) expect(respond(view, basic, {}, reduced).skill!.some((r) => r.perch !== undefined)).toBe(false);
    }
    const view = field(at(2, 2), at(3, 2), {});
    for (const reduced of [false, true]) expect(respond(view, basic, {}, reduced).skill!.some((r) => r.perch !== undefined)).toBe(false);
  });

  it("同一步連續兩段：只有開頭起飛一次、最後落地一次", () => {
    const view = field(at(2, 2), at(3, 2), BIRD);
    const strikeOf: StrikeOf = (id) => (id === "c" ? { ms: 600, hitAt: 0.5, perch: true } : null);
    const ev = [skillUsed([at(3, 2)]), dmg, { ...skillUsed([at(3, 2)]), type: "skill_followup", seq: 3, name_zh: "x", when: "immediate", origin: at(2, 2) }, { ...dmg, seq: 4 }];
    const tl = skillTimeline(ev, view, {}, vfxFor(ev, view, {}), () => "bare", () => null, strikeOf)!;
    const rows = tl.rows.filter((r) => r.unitId === "c");
    expect(rows.filter((r) => r.strike)).toHaveLength(2);
    expect(rows.filter((r) => r.perch === "up")).toHaveLength(1);
    expect(rows.filter((r) => r.perch === "down")).toHaveLength(1);
    expect(rows.find((r) => r.perch === "up")!.startMs).toBeLessThan(rows.find((r) => r.strike)!.startMs);
    expect(rows.find((r) => r.perch === "down")!.startMs).toBeGreaterThanOrEqual(rows.filter((r) => r.strike)[1]!.startMs);
  });

  it("RECOVER 還是給其他異形（非鳥沒有落地列時收勢 RECOVER_MS）", () => {
    const view = field(at(2, 2), at(3, 2), creature("hound", ""));
    const rows = respond(view, basic).skill!.filter((r) => r.unitId === "c" && r.recover);
    expect(rows).toHaveLength(1);
    expect(rows[0]!.ms).toBe(Math.round(RECOVER_MS * SPEED_SCALE.normal));
  });

  it("過場列的姿勢：起飛接片段第一格、落地從片段最後一格往待機；快取鍵含 perch；移動的過場不變", () => {
    const up = perchRowPose("up", "melee", 0.1);
    expect(up.clip).toBe("atk:@melee");
    expect(up.u).toBe(0);
    expect(up.perch).toBe(1);
    const down = perchRowPose("down", "charge", 0.99);
    expect(down.u).toBe(1);
    expect(down.perch).toBe(1);
    expect(creaturePoseKey(quantizeCreaturePose(up))).toContain("perch1");
    const subject = { key: "bird", element: undefined, mat: "fur", base: "#888888", accent: null };
    const sit = qCreaturePartPose(subject, "idle", 0)!;
    const clip = attackClipFor("bird", "melee")!;
    // perch 1＝落地；perch 0.25 接近攻擊片段第一格（飛行）；過場沒有攻擊特效
    expect(qCreaturePartPose(subject, clip, 0, false, 1)!.root.dy!).toBeCloseTo(sit.root.dy!, 5);
    const first = qCreaturePartPose(subject, clip, 0)!;
    expect(Math.abs(qCreaturePartPose(subject, clip, 0, false, 0.25)!.root.dy! - (first.root.dy ?? 0))).toBeLessThan(Math.abs(sit.root.dy! - (first.root.dy ?? 0)));
    expect(qCreaturePartPose(subject, clip, 1, false, 0.5)!.fx).toEqual([]);
    // 減少動態（pose.reduce）不走過場：和沒有 perch 一樣
    expect(qCreaturePartPose(subject, clip, 0.5, true, 0.75)).toEqual(qCreaturePartPose(subject, clip, 0.5, true));
    // 非鳥不受影響
    const hound = { key: "hound", element: undefined, mat: "fur", base: "#888888", accent: null };
    expect(qCreaturePartPose(hound, "atk:bite", 0, false, 1)).toEqual(qCreaturePartPose(hound, "atk:bite", 0));
  });
});

// ---- 蛋 -----------------------------------------------------------------------------

const LIZARD = creature("lizard", "");
const eggEvents = (to: Pos): Record<string, unknown>[] => [skillUsed([to], "skill_summon_ember_whelp"), { seq: 3, round: 1, type: "unit_summoned", unit_id: "w", owner_id: "c", template_id: "w", team: "enemy", pos: to, skill_id: "skill_summon_ember_whelp", expires_round: 3, order_index: 1 }];
const eggCards = { skill_summon_ember_whelp: { id: "skill_summon_ember_whelp", shape: "ground_tile", effect_ids: ["summon"], icon: { segments: [{ shape_id: "ground_tile", range: 2, effects: [{ type: "summon" }] }] } } };

const DIRS = [
  ["朝東", at(4, 4), at(6, 4)],
  ["朝西", at(4, 4), at(2, 4)],
  ["正北", at(4, 4), at(4, 2)],
  ["正南", at(4, 4), at(4, 6)],
] as const;

describe("CB-2c 蛋的拋物線", () => {
  describe.each(DIRS)("%s", (_name, from, to) => {
    const view = field(from, at(0, 0), LIZARD);
    const f = respond(view, eggEvents(to), eggCards);
    const row = f.skill!.find((r) => r.strike)!;
    const key = rigKey(creatureOf({ dollLook: { creature: { body: "lizard", material: "fur" } }, summonLook: null, team: "enemy", facing: "east", summon: false, totem: false, downed: false, formId: null } as never)!);

    it("片段是產卵；蛋落點＝孵化格（unit_summoned）", () => {
      expect(attackClipFor(key, "summon")).toBe("atk:summon");
      expect(row.creature?.action).toBe("summon");
      expect(row.eggTo).toEqual(to);
    });

    it("落地時刻＝片段的出手格＝畫面更新出幼體的時刻（不提早）", () => {
      const hitU = creatureAttackHitU(key, "atk:summon");
      expect(row.hitMs! - row.startMs).toBeCloseTo(creatureClipInfo(key, "atk:summon")!.ms * SPEED_SCALE.normal * hitU, 0);
      expect(Math.abs(f.vfx!.leadMs - row.hitMs!)).toBeLessThanOrEqual(1);
      expect(row.hitMs! - row.startMs).toBeGreaterThan(row.ms * EGG_FROM_U);
    });

    it("起點在身後、終點＝格子中心腳底、途中最高點在直線上方", () => {
      const T = 48;
      const start = { x: from.x * T + T / 2 + EGG_START[0], y: from.y * T + T / 2 + EGG_START[1] };
      const end = { x: to.x * T + T / 2, y: to.y * T + T / 2 };
      const plan = eggArcPlan({ from: start, to: end, startMs: row.startMs + row.ms * EGG_FROM_U, landMs: row.hitMs!, endMs: row.startMs + row.ms, unit: 1 });
      expect(eggAt(plan, plan.startMs).landed).toBe(false);
      expect(eggAt(plan, plan.startMs).x).toBeCloseTo(start.x, 5);
      expect(eggAt(plan, plan.startMs).y).toBeCloseTo(start.y, 5);
      const land = eggAt(plan, plan.landMs);
      expect(land.landed).toBe(true);
      expect(land.x).toBe(end.x);
      expect(land.y).toBe(end.y);
      expect(land.burst).toBe(0);
      expect(eggAt(plan, plan.landMs - 1).landed).toBe(false);
      const mid = eggAt(plan, (plan.startMs + plan.landMs) / 2);
      expect(mid.y).toBeLessThan((start.y + end.y) / 2 - 10);
      expect(eggAt(plan, plan.endMs).burst).toBe(1);
    });
  });

  it("身形沒有產卵片段（退回遠程）不拋蛋", () => {
    const view = field(at(4, 4), at(0, 0), creature("hound", ""));
    const row = respond(view, eggEvents(at(6, 4)), eggCards).skill!.find((r) => r.strike)!;
    expect(row.creature?.action).toBe("summon");
    expect(row.eggTo).toBeUndefined();
  });

  it("孵化格取 unit_summoned 的位置，沒有事件時退回目標格", () => {
    const view = field(at(4, 4), at(0, 0), LIZARD);
    const moved = [skillUsed([at(6, 4)], "skill_summon_ember_whelp"), { ...eggEvents(at(5, 3))[1]! }];
    expect(respond(view, moved, eggCards).skill!.find((r) => r.strike)!.eggTo).toEqual(at(5, 3));
    expect(respond(view, [skillUsed([at(6, 4)], "skill_summon_ember_whelp")], eggCards).skill!.find((r) => r.strike)!.eggTo).toEqual(at(6, 4));
  });

  it("片段的蛋標 lobbed：戰場貼圖不畫（fxAll 樣張照畫）；出手格仍在孵化爆開（不提早）", () => {
    expect(Object.keys(BODY_ANIM).includes("lizard")).toBe(true);
    const subject = { key: "lizard", element: undefined, mat: "fur", base: "#888888", accent: null };
    for (const u of [0.5, 0.7, 0.95]) {
      const fx = qCreaturePartPose(subject, "atk:summon", u)!.fx.filter((f) => f.k === "egg" || f.k === "glow" || f.k === "burst");
      expect(fx.length).toBeGreaterThan(0);
      for (const f of fx) expect(f.lobbed).toBe(true);
    }
    expect(creatureAttackHitU("lizard", "atk:summon")).toBeGreaterThan(0.86);
  });
});
