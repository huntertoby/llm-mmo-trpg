import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, SkillCard, StepOut } from "../api/types";
import { moveAnimOf, type MoveAnim } from "./animation";
import { frameOps, playbackPlan } from "./playback";
import { castMode, CHAIN_GAP_MS, eventPrimitive, placeMotions, primitivesOf, skillTimeline, SKILL_CAP_MS, type WeaponOf } from "./skillSequence";
import { vfxFor, type VfxCards } from "./vfx";
import type { Motion } from "./walkAnim";
import { WEAPON_CLASSES, type WeaponClass } from "../render/skillClips";

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const FOE3 = "u_foe3";
const at = (x: number, y: number): Pos => ({ x, y });

function view(units: Record<string, [Pos, string]>): BattleView {
  return { units: Object.entries(units).map(([id, [pos, team]]) => ({ id, pos, team })), tiles: [] } as unknown as BattleView;
}

function card(shapeId: string, range: number, effects: string[], extra: Record<string, unknown> = {}): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: shapeId, range, effects: effects.map((type) => ({ type })) }] }, ...extra } as unknown as SkillCard;
}

const used = (tiles: Pos[], skill = "sk", unit = HERO) => ({ seq: 1, round: 1, type: "skill_used", unit_id: unit, skill_id: skill, tiles });
const followup = (tiles: Pos[], skill = "sk", unit = HERO) => ({ seq: 3, round: 1, type: "skill_followup", unit_id: unit, skill_id: skill, tiles });
const dmg = (target: string, element = "fire", source = HERO) => ({ seq: 2, round: 1, type: "damage_dealt", target_id: target, source_id: source, element, amount: 5 });
const attack = (target: string, attacker = HERO) => ({ seq: 1, round: 1, type: "attack_rolled", attacker_id: attacker, target_id: target, hit: true });

const weapon =
  (w: WeaponClass): WeaponOf =>
  () =>
    w;

function timeline(events: Record<string, unknown>[], v: BattleView, cards: VfxCards, w: WeaponClass = "blade") {
  return skillTimeline(events, v, cards, vfxFor(events, v, cards), weapon(w));
}

describe("cast mode from shape and range", () => {
  it("follows the table", () => {
    expect(castMode("single", 1)).toBe("melee");
    expect(castMode("cone", 1)).toBe("melee");
    expect(castMode("cross", 1)).toBe("melee");
    expect(castMode("single", 5)).toBe("ranged");
    expect(castMode("line", 4)).toBe("ranged");
    expect(castMode("chain", 3)).toBe("ranged");
    for (const s of ["self", "allies_in_radius", "ring"] as const) expect(castMode(s, 0)).toBe("self");
    for (const s of ["ground_tile", "square3"] as const) expect(castMode(s, 4)).toBe("ground");
  });
});

describe("event → primitive", () => {
  it("maps the documented events", () => {
    const e = (type: string, more: Record<string, unknown> = {}) => eventPrimitive({ seq: 1, round: 1, type, ...more } as never);
    expect(e("damage_dealt")).toBe("damage");
    expect(e("healed")).toBe("heal");
    expect(e("shield_gained")).toBe("shield");
    expect(e("unit_dashed")).toBe("dash");
    expect(e("unit_charged")).toBe("charge_through");
    expect(e("unit_revived")).toBe("revive");
    expect(e("resource_restored")).toBe("restore_resource");
    expect(e("status_removed", { reason: "cleansed" })).toBe("cleanse");
    expect(e("status_removed", { reason: "dispelled" })).toBe("dispel");
    expect(e("status_removed", { reason: "stolen" })).toBe("steal_buff");
    expect(e("status_applied", { status_id: "burning" })).toBe("apply_status");
    expect(e("status_applied", { status_id: "time_bomb" })).toBe("delayed_damage");
    expect(e("status_applied", { status_id: "prone" })).toBe("knock_prone");
    expect(e("unit_moved", { mode: "leap" })).toBe("leap");
    expect(e("unit_moved", { mode: "teleported" })).toBe("teleport_target");
    expect(e("unit_moved", { mode: "walk" })).toBeNull();
    expect(e("turn_started")).toBeNull();
  });

  it("card order wins; events only fill in when the card has no parts", () => {
    const c = card("single", 1, ["leap", "damage"]);
    expect(primitivesOf(c, 0, [], false)).toEqual(["leap", "damage"]);
    expect(primitivesOf(undefined, 0, [{ seq: 1, round: 1, type: "healed" }, { seq: 2, round: 1, type: "damage_dealt" }] as never, false)).toEqual(["heal", "damage"]);
    expect(primitivesOf(undefined, 0, [], true)).toEqual(["damage"]);
  });
});

describe("skill timeline", () => {
  const v = view({ [HERO]: [at(2, 2), "ally"], [FOE]: [at(3, 2), "enemy"], [FOE2]: [at(6, 2), "enemy"], [FOE3]: [at(3, 3), "enemy"] });

  it("basic melee: windup → slash → recover, hit lands on the slash hitAt", () => {
    const ev = [attack(FOE), dmg(FOE, "physical")];
    const tl = timeline(ev, v, {})!;
    expect(tl.rows.map((r) => r.clip)).toEqual(["windup", "slash", "slash"]);
    expect(tl.rows[2]!.recover).toBe(true);
    const strike = tl.rows.find((r) => r.strike)!;
    expect(tl.vfx.hits[0]!.atMs).toBeCloseTo(strike.hitMs!, 6);
    expect(tl.vfx.casts[0]!.impactMs).toBeCloseTo(strike.hitMs!, 6);
  });

  it("ranged staff: the projectile leaves at the cast release", () => {
    const cards = { sk: card("single", 5, ["damage"]) };
    const tl = timeline([used([at(6, 2)]), dmg(FOE2)], v, cards, "staff")!;
    expect(tl.rows.filter((r) => !r.recover).map((r) => r.clip)).toEqual(["channel", "cast"]);
    const strike = tl.rows.find((r) => r.strike)!;
    const c = tl.vfx.casts[0]!;
    expect(c.startMs + c.chargeMs).toBeCloseTo(strike.hitMs!, 6);
    expect(c.impactMs).toBeGreaterThan(strike.hitMs!);
  });

  it("every weapon class × cast mode builds a timeline with one strike", () => {
    const shapes: Array<[string, number, Pos[]]> = [
      ["single", 1, [at(3, 2)]],
      ["single", 5, [at(6, 2)]],
      ["self", 0, [at(2, 2)]],
      ["ground_tile", 4, [at(6, 2)]],
    ];
    for (const w of WEAPON_CLASSES) {
      for (const [shape, range, tiles] of shapes) {
        const tl = timeline([used(tiles), dmg(FOE)], v, { sk: card(shape, range, ["damage"]) }, w)!;
        expect(tl, `${w} ${shape}`).not.toBeNull();
        expect(tl.rows.filter((r) => r.strike)).toHaveLength(1);
        expect(tl.segments[0]!.mode).toBe(castMode(shape as never, range));
      }
    }
  });

  it("damage_multiplier powers up before the strike; heal plays after", () => {
    const tl = timeline([used([at(3, 2)]), dmg(FOE)], v, { sk: card("single", 1, ["damage_multiplier", "damage", "heal"]) })!;
    expect(tl.rows.map((r) => r.clip)).toEqual(["windup", "empower", "slash", "palm_heal", "palm_heal"]);
  });

  it("apply_status: ally target → buff clip, enemy → debuff clip", () => {
    const st = (target: string) => ({ seq: 2, round: 1, type: "status_applied", target_id: target, source_id: HERO, status_id: "haste" });
    const buff = timeline([used([at(2, 2)]), st(HERO)], v, { sk: card("self", 0, ["apply_status"]) })!;
    expect(buff.rows.map((r) => r.clip)).toContain("raise_hand");
    const debuff = timeline([used([at(3, 2)]), st(FOE)], v, { sk: card("single", 1, ["apply_status"]) })!;
    expect(debuff.rows.map((r) => r.clip)).toContain("point_at");
  });

  it("three targets are hit at the same moment", () => {
    const cards = { sk: card("cone", 1, ["damage"]) };
    const tl = timeline([used([at(3, 2), at(3, 3), at(3, 1)]), dmg(FOE), dmg(FOE3), dmg(FOE2)], v, cards)!;
    const times = new Set(tl.vfx.hits.map((h) => h.atMs));
    expect(times.size).toBe(1);
  });

  it("followup segment: no second windup, 0.15 s gap", () => {
    const cards = { sk: card("single", 1, ["damage"]) };
    const ev = [used([at(3, 2)]), dmg(FOE), followup([at(3, 2)]), dmg(FOE)];
    const plain = vfxFor(ev, v, cards);
    const tl = skillTimeline(ev, v, cards, plain, weapon("blade"))!;
    expect(tl.rows.filter((r) => r.clip === "windup")).toHaveLength(1);
    expect(tl.rows.filter((r) => r.strike)).toHaveLength(2);
    const gap = tl.vfx.casts[1]!.startMs - tl.vfx.casts[0]!.startMs - (plain.casts[1]!.startMs - plain.casts[0]!.startMs);
    expect(gap).toBeGreaterThanOrEqual(CHAIN_GAP_MS);
    // 施放者一次只播一個片段
    const mine = tl.rows.filter((r) => r.unitId === HERO).sort((a, b) => a.startMs - b.startMs);
    for (let i = 1; i < mine.length; i++) expect(mine[i]!.startMs).toBeGreaterThanOrEqual(mine[i - 1]!.startMs + mine[i - 1]!.ms - 1e-6);
  });

  it("a charged far shot stays within 1.8 s to the first hit", () => {
    const cards = { sk: card("single", 9, ["damage_multiplier", "damage"], { timing: "delayed" }) };
    const far = view({ [HERO]: [at(0, 0), "ally"], [FOE]: [at(9, 0), "enemy"] });
    const ev = [used([at(9, 0)]), dmg(FOE)];
    const tl = skillTimeline(ev, far, cards, vfxFor(ev, far, cards), weapon("staff"))!;
    expect(tl.vfx.casts[0]!.impactMs).toBeLessThanOrEqual(SKILL_CAP_MS + 1e-6);
  });

  it("primitives without a clip fall back to opener + existing vfx", () => {
    const tl = timeline([used([at(3, 2)]), dmg(FOE)], v, { sk: card("single", 1, ["summon", "zone", "made_up_primitive"]) })!;
    expect(tl.rows.map((r) => r.clip)).toEqual(["windup", "slash", "slash"]);
  });

  it("knock_prone / shockwave targets fall at the hit", () => {
    const prone = { seq: 3, round: 1, type: "status_applied", target_id: FOE, source_id: HERO, status_id: "prone" };
    const tl = timeline([used([at(3, 2)]), dmg(FOE), prone], v, { sk: card("single", 1, ["damage", "knock_prone"]) })!;
    const fall = tl.rows.find((r) => r.clip === "knocked_down")!;
    expect(fall.unitId).toBe(FOE);
    expect(fall.startMs).toBeCloseTo(tl.vfx.casts[0]!.impactMs, 6);
    expect(tl.rows.map((r) => r.clip)).toContain("sweep_low");
  });

  it("is deterministic", () => {
    const ev = [used([at(6, 2)]), dmg(FOE2)];
    const cards = { sk: card("single", 5, ["damage", "push"]) };
    expect(timeline(ev, v, cards, "gun")).toEqual(timeline(ev, v, cards, "gun"));
  });

  it("returns null when segments and vfx do not line up (falls back to plain vfx)", () => {
    const ev = [used([at(3, 2)]), dmg(FOE)];
    expect(skillTimeline(ev, v, {}, { casts: [], hits: [], blasts: [], shake: 0, leadMs: 0 }, weapon("blade"))).toBeNull();
  });
});

describe("motion order follows the card", () => {
  const before = view({ [HERO]: [at(2, 2), "ally"], [FOE]: [at(4, 2), "enemy"] });
  const leap: Motion<MoveAnim> = { kind: "move", anim: moveAnimOf({ seq: 1, round: 1, type: "unit_moved", unit_id: HERO, from_pos: at(2, 2), to_pos: at(3, 2), mode: "leap" } as never) };
  const shove: Motion<MoveAnim> = { kind: "move", anim: moveAnimOf({ seq: 1, round: 1, type: "unit_moved", unit_id: FOE, from_pos: at(4, 2), to_pos: at(5, 2), mode: "forced" } as never) };
  const seg = (prims: string[]) => [{ casterId: HERO, primitives: prims, from: at(2, 2) }] as never;

  it("leap + slash: leap before; slash + leap: leap after", () => {
    const a = placeMotions([leap], seg(["leap", "damage"]), before);
    expect(a.before.map((m) => (m.kind === "move" ? m.anim.clip : null))).toEqual(["leap_air"]);
    expect(a.after).toEqual([]);
    const b = placeMotions([leap], seg(["damage", "leap"]), before);
    expect(b.before).toEqual([]);
    expect(b.after).toHaveLength(1);
    expect(b.casterFrom).toEqual(at(2, 2));
  });

  it("pushed targets move after the hit and lean back; pulled lean forward", () => {
    const a = placeMotions([shove], seg(["damage", "push"]), before);
    expect(a.after.map((m) => (m.kind === "move" ? m.anim.clip : null))).toEqual(["pushed"]);
    const pull: Motion<MoveAnim> = { kind: "move", anim: { ...(shove as { anim: MoveAnim }).anim, from: at(5, 2), to: at(4, 2) } };
    expect(placeMotions([pull], seg(["damage", "pull"]), before).after.map((m) => (m.kind === "move" ? m.anim.clip : null))).toEqual(["pulled"]);
  });

  it("dash with charge_through uses the shoulder charge clip", () => {
    const dash: Motion<MoveAnim> = { kind: "move", anim: { ...(leap as { anim: MoveAnim }).anim, mode: "dash" } };
    expect(placeMotions([dash], seg(["charge_through", "damage"]), before).before.map((m) => (m.kind === "move" ? m.anim.clip : null))).toEqual(["shoulder_charge"]);
  });
});

describe("playback integration", () => {
  const v0 = view({ [HERO]: [at(2, 2), "ally"], [FOE]: [at(3, 2), "enemy"] });
  const v1 = view({ [HERO]: [at(3, 1), "ally"], [FOE]: [at(3, 2), "enemy"] });
  const step = (events: Record<string, unknown>[]): StepOut => ({ actor_id: HERO, events, view: v1, step: { type: "skill" } }) as unknown as StepOut;
  const res = (steps: StepOut[]) => ({ steps, initial_view: v0, view: v1 }) as unknown as BattleResponse;
  const ev = [used([at(3, 2)]), dmg(FOE), { seq: 4, round: 1, type: "unit_moved", unit_id: HERO, from_pos: at(2, 2), to_pos: at(3, 1), mode: "leap" }];

  it("slash + leap: vfx op comes before the leap, and fx start from the pre-leap tile", () => {
    const plan = playbackPlan(res([step(ev)]), HERO, "normal", { sk: card("single", 1, ["damage", "leap"]) }, new Set(), weapon("blade"));
    const ops = frameOps(plan.frames[0]!).map((o) => o.op);
    expect(ops.indexOf("vfx")).toBeLessThan(ops.indexOf("move"));
    expect(plan.frames[0]!.vfx!.casts[0]!.from).toEqual(at(2, 2));
    expect(plan.frames[0]!.skill!.length).toBeGreaterThan(0);
  });

  it("leap + slash: leap first", () => {
    const plan = playbackPlan(res([step(ev)]), HERO, "normal", { sk: card("single", 1, ["leap", "damage"]) }, new Set(), weapon("blade"));
    const ops = frameOps(plan.frames[0]!).map((o) => o.op);
    expect(ops.indexOf("move")).toBeLessThan(ops.indexOf("vfx"));
  });

  it("speed scales the clips; skip has none; without weaponOf nothing changes", () => {
    const cards = { sk: card("single", 1, ["damage"]) };
    const normal = playbackPlan(res([step(ev.slice(0, 2))]), HERO, "normal", cards, new Set(), weapon("blade")).frames[0]!.skill!;
    const fast = playbackPlan(res([step(ev.slice(0, 2))]), HERO, "fast", cards, new Set(), weapon("blade")).frames[0]!.skill!;
    expect(fast[1]!.startMs).toBe(Math.round(normal[1]!.startMs / 2));
    expect(playbackPlan(res([step(ev.slice(0, 2))]), HERO, "skip", cards, new Set(), weapon("blade")).frames[0]!.skill).toBeUndefined();
    expect(playbackPlan(res([step(ev.slice(0, 2))]), HERO, "normal", cards).frames[0]!.skill).toBeUndefined();
  });
});
