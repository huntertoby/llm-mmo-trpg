// 6N-4：受擊者的身體反應從事件推出來（只讀事件，不改規則）；時間＝那一段的命中點。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { skillTimeline } from "./skillSequence";
import { HEAVY_HIT_PERMILLE, scaleVfx, vfxFor } from "./vfx";

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const at = (x: number, y: number): Pos => ({ x, y });

function view(units: Record<string, [Pos, string, number?]>): BattleView {
  return { units: Object.entries(units).map(([id, [pos, team, max]]) => ({ id, pos, team, max_hp: max ?? 40 })), tiles: [] } as unknown as BattleView;
}
const v = view({ [HERO]: [at(2, 2), "ally"], [FOE]: [at(3, 2), "enemy", 40], [FOE2]: [at(4, 2), "enemy", 40] });

function card(effects: string[]): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 1, effects: effects.map((type) => ({ type })) }] } } as unknown as SkillCard;
}
const cards = { sk: card(["damage"]) };
const used = (seq = 1) => ({ seq, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles: [at(3, 2)] });
const roll = (target: string, hit: boolean, seq = 2, attacker = HERO) => ({ seq, round: 1, type: "attack_rolled", attacker_id: attacker, target_id: target, hit });
const dmg = (target: string, lost: number, more: Record<string, unknown> = {}, seq = 3, source = HERO) => ({
  seq,
  round: 1,
  type: "damage_dealt",
  target_id: target,
  source_id: source,
  element: "physical",
  amount: lost,
  hp_before: 40,
  hp_after: 40 - lost,
  ...more,
});

describe("reactions from events (6N-4)", () => {
  it("damage → hit at the cast's hit point; seq kept for variant hashing", () => {
    const vfx = vfxFor([used(), roll(FOE, true), dmg(FOE, 5)], v, cards);
    expect(vfx.reactions).toEqual([{ unitId: FOE, pos: at(3, 2), kind: "hit", atMs: vfx.casts[0]!.impactMs, seq: 3, cast: 0 }]);
  });

  it("losing ≥ 25% of max HP is a heavy hit", () => {
    const edge = (40 * HEAVY_HIT_PERMILLE) / 1000;
    expect(vfxFor([used(), dmg(FOE, edge)], v, cards).reactions![0]!.kind).toBe("heavy");
    expect(vfxFor([used(), dmg(FOE, edge - 1)], v, cards).reactions![0]!.kind).toBe("hit");
  });

  it("block_permille < 1000 is a block (even when heavy)", () => {
    expect(vfxFor([used(), dmg(FOE, 20, { block_permille: 500 })], v, cards).reactions![0]!.kind).toBe("block");
    expect(vfxFor([used(), dmg(FOE, 5, { block_permille: 1000 })], v, cards).reactions![0]!.kind).toBe("hit");
  });

  it("attack_rolled with hit: false is a dodge — for skills and for basic attacks", () => {
    expect(vfxFor([used(), roll(FOE, false)], v, cards).reactions).toMatchObject([{ unitId: FOE, kind: "dodge" }]);
    const basic = vfxFor([roll(FOE, false, 1)], v, {});
    expect(basic.reactions).toMatchObject([{ unitId: FOE, kind: "dodge", cast: 0, atMs: basic.casts[0]!.impactMs }]);
  });

  it("unit_downed replaces the hit of the same segment", () => {
    const vfx = vfxFor([used(), dmg(FOE, 40), { seq: 4, round: 1, type: "unit_downed", unit_id: FOE }], v, cards);
    expect(vfx.reactions).toMatchObject([{ unitId: FOE, kind: "down", seq: 4 }]);
  });

  it("several targets react at the same moment; zero damage does not react", () => {
    const vfx = vfxFor([used(), dmg(FOE, 5, {}, 3), dmg(FOE2, 5, {}, 4), dmg(HERO, 0, {}, 5)], v, cards);
    expect(vfx.reactions!.map((r) => r.unitId)).toEqual([FOE, FOE2]);
    expect(new Set(vfx.reactions!.map((r) => r.atMs)).size).toBe(1);
  });

  it("damage from someone else (counter, damage over time) goes to the end of the step", () => {
    const vfx = vfxFor([used(), dmg(FOE, 5), dmg(HERO, 5, {}, 6, FOE)], v, cards);
    expect(vfx.reactions!.find((r) => r.unitId === HERO)).toMatchObject({ kind: "hit", cast: -1, atMs: vfx.leadMs });
  });

  it("scales with the playback speed", () => {
    const vfx = vfxFor([used(), dmg(FOE, 5)], v, cards);
    expect(scaleVfx(vfx, 2).reactions![0]!.atMs).toBe(vfx.reactions![0]!.atMs * 2);
  });

  it("the sequencer moves reactions with the aligned hit point; knocked-down targets keep only their fall", () => {
    const events = [used(), dmg(FOE, 5)];
    const raw = vfxFor(events, v, cards);
    const tl = skillTimeline(events, v, cards, raw, () => "blade")!;
    expect(tl.vfx.reactions![0]!.atMs).toBeCloseTo(tl.vfx.hits[0]!.atMs, 6);
    expect(tl.vfx.reactions![0]!.atMs).toBeGreaterThan(raw.reactions![0]!.atMs);
    const prone = [used(), dmg(FOE, 5), { seq: 4, round: 1, type: "status_applied", target_id: FOE, source_id: HERO, status_id: "prone" }];
    const c2 = { sk: card(["damage", "knock_prone"]) };
    const tl2 = skillTimeline(prone, v, c2, vfxFor(prone, v, c2), () => "blade")!;
    expect(tl2.rows.some((r) => r.clip === "knocked_down" && r.unitId === FOE)).toBe(true);
    expect(tl2.vfx.reactions).toEqual([]);
  });

  it("is deterministic", () => {
    const events = [used(), roll(FOE, false), roll(FOE2, true, 3), dmg(FOE2, 12, { block_permille: 500 }, 4)];
    expect(vfxFor(events, v, cards)).toEqual(vfxFor(events, v, cards));
  });
});
