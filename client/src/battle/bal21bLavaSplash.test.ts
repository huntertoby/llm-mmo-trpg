// BAL-21b（T7 美術 PM 答覆）：灰燼之心熔岩濺落（`skill_lava_splash`，落在選定格的延遲段）。
// 施放回合播殼頂熔岩柱 `spout`（不退到 `firebolt`）；落下回合頭目不播片段，落點 3×3 照現有火屬性範圍命中特效。
// 跟著施放者的延遲段（`lava_spout`）落下時照舊播片段。時間軸走正式的 playbackPlan。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StatusView, StepOut } from "../api/types";
import { bossAttackClip } from "../render/qBoss";
import { playbackPlan } from "./playback";
import { anchoredReleaseOf } from "./skillSequence";
import { unit } from "./testFixtures";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "./viewGrip";

const at = (x: number, y: number): Pos => ({ x, y });
const HEART = { body: "wisp", material: "crystal", element: "fire", size: "huge", traits: ["core"] };
const SPLASH = "skill_lava_splash";
const SPOUT = "skill_lava_spout";
const SPOT = at(2, 5);
const sq = (c: Pos): Pos[] => [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => at(c.x + dx, c.y + dy)));
const seg = (shape: string, range: number) => ({ shape_id: shape, range, effects: [{ type: "damage" }] });
const CARDS = {
  [SPLASH]: { id: SPLASH, shape: "square3", timing: "delayed", effect_ids: ["shield"], stats: { range: 4 }, icon: { segments: [{ ...seg("square3", 4), effects: [{ type: "shield" }] }, seg("square3", 0)] } },
  [SPOUT]: { id: SPOUT, shape: "self", timing: "delayed", effect_ids: ["shield"], icon: { segments: [{ ...seg("self", 0), effects: [{ type: "shield" }] }, seg("ring", 0)] } },
};

const charging = (skill: string, anchored: boolean): StatusView => ({ status_id: "charging", remaining: null, source_id: "c", amount: null, skill_id: skill, release: "next_turn", charge_tiles: sq(anchored ? SPOT : at(5, 5)), charge_anchored: anchored ? true : null }) as unknown as StatusView;

function field(statuses: StatusView[] = []): BattleView {
  const shell = { status_id: "molten_shell", remaining: null, source_id: null, amount: null, charge_tiles: [] } as unknown as StatusView;
  return {
    map_id: "molten_heart_pit", width: 11, height: 11, tiles: [], objects: [], traps: [], zones: [], runes: [], source_wells: [],
    units: [
      unit("c", "enemy", 5, 5, { hp: 160, max_hp: 160, facing: "west", template_id: "ashen_heart", weapon_id: "fire_staff", statuses: [shell, ...statuses], doll_look: { creature: HEART } } as never),
      unit("h", "ally", 2, 5, { hp: 20, max_hp: 20, facing: "east" }),
    ],
  } as unknown as BattleView;
}

function frame(events: Record<string, unknown>[], view: BattleView) {
  const step = { actor_id: "c", events, view, step: { type: "skill" } } as unknown as StepOut;
  const res = { steps: [step], initial_view: view, view } as unknown as BattleResponse;
  return playbackPlan(res, "h", "normal", CARDS as never, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, false).frames[0]!;
}

const castEvents = [
  { seq: 11, round: 1, type: "skill_used", unit_id: "c", skill_id: SPLASH, tiles: sq(SPOT) },
  { seq: 12, round: 1, type: "shield_gained", unit_id: "c", source_id: "c", amount: 2, total: 2 },
  { seq: 13, round: 1, type: "followup_charged", unit_id: "c", skill_id: SPLASH, pos: SPOT, tiles: sq(SPOT), anchored: true, release: "next_turn" },
];
const release = (skill: string, origin: Pos) => [
  { seq: 21, round: 2, type: "skill_followup", unit_id: "c", skill_id: skill, name_zh: "x", when: "delayed", origin, tiles: sq(origin) },
  { seq: 22, round: 2, type: "damage_dealt", target_id: "h", source_id: "c", element: "fire", amount: 3 },
  { seq: 23, round: 2, type: "surface_created", pos: origin, surface: "fire" },
];

describe("BAL-21b 熔岩濺落的頭目片段", () => {
  it("施放回合：頭目出招列是範圍類（area），第 1 階段播 spout，不退到 firebolt", () => {
    for (let s = 0; s < 40; s++) {
      const evs = castEvents.map((e) => ({ ...e, seq: e.seq + s * 10 }));
      const strike = frame(evs, field()).skill!.find((r) => r.unitId === "c" && r.strike)!;
      expect(strike.creature?.action, `seq ${s}`).toBe("area");
      expect(bossAttackClip("ah", strike.creature!.action, 1)).toBe("spout");
    }
  });

  it("落下回合（落在選定格）：頭目沒有任何片段列；落點照火屬性範圍特效、命中照播", () => {
    const f = frame(release(SPLASH, SPOT), field([charging(SPLASH, true)]));
    expect((f.skill ?? []).filter((r) => r.unitId === "c")).toEqual([]);
    const vfx = f.vfx!;
    const cast = vfx.casts[0]!;
    expect(cast.element).toBe("fire");
    expect(cast.to).toEqual(SPOT);
    expect(vfx.hits.map((h) => [h.pos, h.element])).toEqual([[SPOT, "fire"]]);
    expect(cast.kind).not.toBe("projectile"); // 範圍爆發，不是火焰箭的飛行物
  });

  it("跟著施放者的延遲段（lava_spout、沒有 anchored）落下時照舊播片段", () => {
    const f = frame(release(SPOUT, at(5, 5)), field([charging(SPOUT, false)]));
    const strike = (f.skill ?? []).find((r) => r.unitId === "c" && r.strike);
    expect(strike?.creature?.action).toBe("area");
  });

  it("anchoredReleaseOf：只認後段＋同一招的 anchored 蓄力", () => {
    const view = field([charging(SPLASH, true)]);
    expect(anchoredReleaseOf({ followup: true, casterId: "c", skillId: SPLASH }, view)).toBe(true);
    expect(anchoredReleaseOf({ followup: false, casterId: "c", skillId: SPLASH }, view)).toBe(false);
    expect(anchoredReleaseOf({ followup: true, casterId: "c", skillId: SPOUT }, view)).toBe(false);
    expect(anchoredReleaseOf({ followup: true, casterId: "c", skillId: SPOUT }, field([charging(SPOUT, false)]))).toBe(false);
  });
});
