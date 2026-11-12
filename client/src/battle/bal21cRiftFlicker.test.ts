// BAL-21c（T7 美術 PM 答覆）：碎晶之主第 3 階段「界隙閃擊」（`skill_rift_flicker`，先打再閃走）。
// 第一段（單體、射程 6）照舊播 `thunder`；第二段的傳送播 `blink` 片段接 `LordState.blink`：約 600 ms、blink 1 → 0 線性、
// 在目的格播（傳送排在出招後、整段站在終點）；`swing` 不再當位移的退回片段。時間軸走正式的 playbackPlan。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StepOut } from "../api/types";
import { BOSS_MS, bossAttackClip, bossPlan } from "../render/qBoss";
import { playbackPlan } from "./playback";
import { unit } from "./testFixtures";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "./viewGrip";

const at = (x: number, y: number): Pos => ({ x, y });
const LORD = { body: "golem", material: "crystal", size: "huge", traits: ["core"] };
const FLICK = "skill_rift_flicker";
const FROM = at(4, 3);
const TO = at(5, 0);
const CARDS = {
  [FLICK]: {
    id: FLICK,
    shape: "single",
    timing: "after_action",
    effect_ids: ["damage"],
    stats: { range: 6 },
    icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 6, effects: [{ type: "damage" }] }, { skeleton: "displace", shape_id: "ground_tile", range: 4, effects: [{ type: "teleport" }] }] },
  },
};

function view(lord: Pos, phase: number): BattleView {
  return {
    map_id: "rift_gate", width: 9, height: 7, tiles: [], objects: [], traps: [], zones: [], runes: [], source_wells: [],
    units: [
      unit("c", "enemy", lord.x, lord.y, { hp: 160, max_hp: 380, facing: "west", template_id: "rift_shard_lord", weapon_id: "lightning_staff", boss_phase: { index: phase, total: 4, name_zh: "核心過載" }, doll_look: { creature: LORD } } as never),
      unit("h", "ally", 1, 3, { hp: 20, max_hp: 20, facing: "east" }),
    ],
  } as unknown as BattleView;
}

/** 引擎實際的事件順序（`skill_used` → 命中 → `skill_followup` → 傳送；BAL-21c 報告第 1 節）。 */
function events(seq0: number): Record<string, unknown>[] {
  return [
    { seq: seq0, round: 3, type: "skill_used", unit_id: "c", skill_id: FLICK, name_zh: "界隙閃擊", tiles: [at(1, 3)] },
    { seq: seq0 + 1, round: 3, type: "attack_rolled", attacker_id: "c", target_id: "h", hit: true, skill_id: FLICK },
    { seq: seq0 + 2, round: 3, type: "damage_dealt", target_id: "h", source_id: "c", element: "physical", amount: 6, hp_before: 20, hp_after: 14 },
    { seq: seq0 + 3, round: 3, type: "skill_followup", unit_id: "c", skill_id: FLICK, name_zh: "界隙閃擊", when: "after_action", origin: FROM, tiles: [TO] },
    { seq: seq0 + 4, round: 3, type: "unit_moved", unit_id: "c", from_pos: FROM, to_pos: TO, mode: "teleport", cost: 0 },
  ];
}

function frame(phase: number, seq0 = 7) {
  const before = view(FROM, phase);
  const after = view(TO, phase);
  const step = { actor_id: "c", events: events(seq0), view: after, step: { type: "skill" } } as unknown as StepOut;
  const res = { steps: [step], initial_view: before, view: after } as unknown as BattleResponse;
  return playbackPlan(res, "h", "normal", CARDS as never, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, false).frames[0]!;
}

describe("BAL-21c 碎晶之主的瞬步殘影 blink 片段", () => {
  it("位移類挑 blink，不再退回揮擊 swing（各階段）", () => {
    for (const phase of [1, 2, 3, 4]) {
      expect(bossAttackClip("sl", "blink", phase)).toBe("blink");
      expect(bossAttackClip("sl", "melee", phase)).toBe("swing"); // 普攻照舊
      expect(bossAttackClip("sl", "cast", phase)).toBe("thunder");
    }
  });

  it("約 600 ms，殘影 blink 1 → 0 線性；沒有前推、沒有自帶特效", () => {
    expect(BOSS_MS["blink"]).toBe(600);
    for (const u of [0, 0.25, 0.5, 0.75, 1]) {
      const p = bossPlan("sl", "blink", u, { phase: 3 });
      expect(p.who).toBe("sl");
      expect((p.st as { blink?: number }).blink).toBeCloseTo(1 - u, 9);
      expect(p.dx).toBe(0);
      expect(p.fx).toEqual([]);
    }
    expect((bossPlan("sl", "blink", 0.4, { phase: 3, reduce: true }).st as { blink?: number }).blink).toBeUndefined(); // 減少動態：靜止
  });

  it("界隙閃擊：先在原地播 thunder，傳送排在出招後、整段在目的格播 blink（600 ms）", () => {
    for (let s = 0; s < 20; s++) {
      const f = frame(3, 7 + s * 10);
      const rows = (f.skill ?? []).filter((r) => r.unitId === "c" && r.strike);
      expect(rows.map((r) => r.creature?.action)).toEqual(["cast"]); // 第二段不另排出招列（由傳送播）
      expect(f.motions).toEqual([]); // 不在出招前先閃走
      const moves = (f.after ?? []).flatMap((m) => (m.kind === "move" ? [m.anim] : []));
      expect(moves).toHaveLength(1);
      expect(moves[0]).toMatchObject({ unitId: "c", from: FROM, to: TO, mode: "teleport", creatureBlink: true, creatureBlinkAt: "to", durationMs: 600 });
    }
  });

  it("第一段的特效從傳送前的格子發出", () => {
    const cast = frame(3).vfx!.casts[0]!;
    expect(cast.from).toEqual(FROM);
  });

  it("第 4 階段（沒有自己的招式組，沿用第 3 階段）同樣播 blink", () => {
    const moves = (frame(4).after ?? []).flatMap((m) => (m.kind === "move" ? [m.anim] : []));
    expect(moves[0]).toMatchObject({ creatureBlink: true, creatureBlinkAt: "to" });
  });
});
