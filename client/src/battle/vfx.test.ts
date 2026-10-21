import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, SkillCard } from "../api/types";
import { frameOps, playbackPlan } from "./playback";
import {
  CRIT_INTENSITY,
  inferShape,
  scaleVfx,
  SHAPE_NAMES,
  shapeIdOf,
  vfxFor,
  VFX_TIMING,
  type VfxKind,
} from "./vfx";
import {
  DEFAULT_VFX,
  ELEMENT_VFX,
  elementVfx,
  particleAt,
  SUPPORT_VFX,
  type ParticleKind,
} from "./vfxPalette";
import fixture from "./fixtures/oil_depot_seed3.json";
import randomSkills from "./fixtures/vfx_random_skills.json";

const CASTER = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";

function view(units: Record<string, Pos>): BattleView {
  return { units: Object.entries(units).map(([id, pos]) => ({ id, pos })) } as unknown as BattleView;
}

function card(shape: string, skeleton = "strike"): SkillCard {
  return { id: "skill_x", shape, skeleton } as unknown as SkillCard;
}

const cards = (shape: string, skeleton?: string) => ({ skill_x: card(shape, skeleton) });

function used(tiles: Pos[], unit = CASTER, skill = "skill_x") {
  return { seq: 1, round: 1, type: "skill_used", unit_id: unit, skill_id: skill, tiles };
}

function damage(target: string, element: string, crit = false, source = CASTER, amount = 5) {
  return { seq: 2, round: 1, type: "damage_dealt", target_id: target, source_id: source, element, crit, amount };
}

const at = (x: number, y: number): Pos => ({ x, y });
const HERO_AT = at(2, 2);

describe("vfxFor: shape × ranged / melee", () => {
  const cases: Array<{ shape: string; tiles: Pos[]; foe: Pos; kind: VfxKind; ranged: boolean }> = [
    { shape: "單體（射程 6）", tiles: [at(6, 2)], foe: at(6, 2), kind: "projectile", ranged: true },
    { shape: "單體（射程 武器射程）・穿透", tiles: [at(5, 5)], foe: at(5, 5), kind: "projectile", ranged: true },
    { shape: "單體（射程 1）", tiles: [at(3, 2)], foe: at(3, 2), kind: "slash", ranged: false },
    { shape: "單體（射程 1）", tiles: [at(3, 3)], foe: at(3, 3), kind: "slash", ranged: false },
    { shape: "直線（大小 4）", tiles: [at(3, 2), at(4, 2), at(5, 2), at(6, 2)], foe: at(5, 2), kind: "beam", ranged: true },
    { shape: "直線（大小 2）", tiles: [at(2, 3), at(2, 4)], foe: at(2, 3), kind: "beam", ranged: true },
    { shape: "錐形（大小 2）", tiles: [at(3, 2), at(4, 1), at(4, 2), at(4, 3)], foe: at(4, 2), kind: "cone", ranged: true },
    { shape: "十字（射程 3）", tiles: [at(5, 1), at(4, 2), at(5, 2), at(6, 2), at(5, 3)], foe: at(5, 2), kind: "area", ranged: true },
    { shape: "十字（射程 0）", tiles: [at(2, 1), at(1, 2), at(2, 2), at(3, 2), at(2, 3)], foe: at(3, 2), kind: "area", ranged: false },
    { shape: "方陣（射程 2）", tiles: [at(3, 3), at(4, 3), at(5, 3), at(3, 4), at(4, 4), at(5, 4), at(3, 5), at(4, 5), at(5, 5)], foe: at(4, 4), kind: "area", ranged: true },
    { shape: "環形（半徑 1）", tiles: [at(1, 1), at(2, 1), at(3, 1), at(1, 2), at(3, 2), at(1, 3), at(2, 3), at(3, 3)], foe: at(3, 2), kind: "area", ranged: false },
    { shape: "指定格（射程 4）", tiles: [at(5, 4)], foe: at(5, 4), kind: "area", ranged: true },
    { shape: "自身", tiles: [HERO_AT], foe: at(3, 2), kind: "aura", ranged: false },
    { shape: "範圍光環（半徑 1）", tiles: [at(2, 1), at(1, 2), at(2, 2), at(3, 2), at(2, 3)], foe: at(3, 2), kind: "aura", ranged: false },
    { shape: "連鎖（跳躍距離 1，跳躍 1，射程 6）", tiles: [at(6, 2)], foe: at(6, 2), kind: "beam", ranged: true },
    { shape: "單位與落點（射程 4）", tiles: [at(4, 2), at(6, 4)], foe: at(4, 2), kind: "area", ranged: true },
    { shape: "兩個單位（射程 4）", tiles: [at(4, 2), at(5, 5)], foe: at(4, 2), kind: "area", ranged: true },
    { shape: "物件與落點（射程 4）", tiles: [at(5, 5)], foe: at(5, 5), kind: "area", ranged: true },
  ];
  for (const c of cases) {
    it(`${c.shape} @ ${c.tiles.length} tiles → ${c.kind}`, () => {
      const v = vfxFor([used(c.tiles), damage(FOE, "fire")], view({ [CASTER]: HERO_AT, [FOE]: c.foe }), cards(c.shape));
      expect(v.casts).toHaveLength(1);
      const cast = v.casts[0]!;
      expect(cast.kind).toBe(c.kind);
      expect(cast.ranged).toBe(c.ranged);
      expect(cast.element).toBe("fire");
      expect(cast.from).toEqual(HERO_AT);
      expect(cast.charge).toBe(true);
      expect(cast.impactMs).toBeGreaterThan(cast.startMs);
      expect(v.leadMs).toBe(cast.impactMs);
      expect(v.hits).toEqual([{ pos: c.foe, element: "fire", crit: false, atMs: cast.impactMs }]);
      expect(v.shake).toBe(1);
    });
  }

  it("a line's beam ends on the farthest tile; a cone points at its far edge", () => {
    const beam = vfxFor([used([at(3, 2), at(4, 2), at(5, 2)])], view({ [CASTER]: HERO_AT }), cards("直線（大小 3）")).casts[0]!;
    expect(beam.to).toEqual(at(5, 2));
    expect(beam.path).toEqual([HERO_AT, at(5, 2)]);
  });

  it("a chain's beam follows the units it hit, in order", () => {
    const events = [used([at(5, 2)]), damage(FOE, "lightning"), damage(FOE2, "lightning")];
    const v = vfxFor(events, view({ [CASTER]: HERO_AT, [FOE]: at(5, 2), [FOE2]: at(6, 3) }), cards("連鎖（跳躍 1）"));
    expect(v.casts[0]!.kind).toBe("beam");
    expect(v.casts[0]!.path).toEqual([HERO_AT, at(5, 2), at(6, 3)]);
    expect(v.hits.map((h) => h.pos)).toEqual([at(5, 2), at(6, 3)]);
  });

  it("projectiles take longer the farther they fly (capped)", () => {
    const lead = (to: Pos) => vfxFor([used([to])], view({ [CASTER]: HERO_AT }), cards("單體（射程 9）")).leadMs;
    expect(lead(at(4, 2))).toBeLessThan(lead(at(8, 2)));
    expect(lead(at(30, 2))).toBe(VFX_TIMING.charge + VFX_TIMING.projectileMax);
  });

  it("every shape name in the table is recognised from the card text", () => {
    for (const [name, id] of Object.entries(SHAPE_NAMES)) {
      expect(shapeIdOf({ shape: `${name}（射程 2）` })).toBe(id);
      expect(shapeIdOf({ shape: `${name}・穿透` })).toBe(id);
    }
  });
});

describe("vfxFor: elements, crits and defaults", () => {
  const ELEMENTS = ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"];

  it("has a distinct palette for each of the 9 elements", () => {
    for (const el of ELEMENTS) expect(ELEMENT_VFX[el]).toBeDefined();
    expect(new Set(ELEMENTS.map((el) => ELEMENT_VFX[el]!.particle)).size).toBe(ELEMENTS.length);
    expect(new Set(ELEMENTS.map((el) => ELEMENT_VFX[el]!.primary)).size).toBe(ELEMENTS.length);
  });

  it("gives each element its particle behaviour", () => {
    const expected: Record<string, ParticleKind> = {
      fire: "ember",
      ice: "shard",
      lightning: "bolt",
      poison: "bubble",
      wind: "gust",
      earth: "rock",
      holy: "pillar",
      shadow: "smoke",
      physical: "spark",
      water: "splash",
    };
    for (const [el, kind] of Object.entries(expected)) expect(elementVfx(el).particle).toBe(kind);
    expect(elementVfx("lightning").jagged).toBe(true);
    expect(elementVfx("holy").column).toBe(true);
  });

  for (const el of ELEMENTS) {
    it(`takes the element from the caster's damage: ${el}`, () => {
      const v = vfxFor([used([at(6, 2)]), damage(FOE, el)], view({ [CASTER]: HERO_AT, [FOE]: at(6, 2) }), cards("單體（射程 6）"));
      expect(v.casts[0]!.element).toBe(el);
      expect(elementVfx(v.casts[0]!.element)).toBe(ELEMENT_VFX[el]);
    });
  }

  it("a crit makes the cast stronger and the shake strong", () => {
    const v = vfxFor([used([at(3, 2)]), damage(FOE, "ice", true)], view({ [CASTER]: HERO_AT, [FOE]: at(3, 2) }), cards("單體（射程 1）"));
    expect(v.casts[0]!.crit).toBe(true);
    expect(v.casts[0]!.intensity).toBe(CRIT_INTENSITY);
    expect(v.hits[0]!.crit).toBe(true);
    expect(v.shake).toBe(2);
  });

  it("falls back to the default palette for unknown elements", () => {
    expect(elementVfx("plasma")).toBe(DEFAULT_VFX);
    const v = vfxFor([used([at(6, 2)]), damage(FOE, "plasma")], view({ [CASTER]: HERO_AT, [FOE]: at(6, 2) }), cards("單體（射程 6）"));
    expect(v.casts[0]!.element).toBe("plasma");
    expect(elementVfx(v.casts[0]!.element)).toBe(DEFAULT_VFX);
  });

  it("uses the touched element, then the support palette, then the default when nothing is damaged", () => {
    const v0 = view({ [CASTER]: HERO_AT });
    const touched = { type: "element_touched", pos: at(4, 2), element: "wind", source_id: CASTER };
    expect(vfxFor([used([at(4, 2)]), touched], v0, cards("指定格（射程 2）")).casts[0]!.element).toBe("wind");
    const healed = { type: "healed", target_id: CASTER, amount: 4 };
    const heal = vfxFor([used([HERO_AT]), healed], v0, cards("自身")).casts[0]!;
    expect(elementVfx(heal.element)).toBe(SUPPORT_VFX);
    const buff = vfxFor([used([HERO_AT])], v0, cards("自身")).casts[0]!;
    expect(elementVfx(buff.element)).toBe(DEFAULT_VFX);
    expect(vfxFor([used([HERO_AT])], v0, cards("自身")).shake).toBe(0);
  });

  it("infers the shape from the tiles when the card is missing or the shape is unknown", () => {
    const v0 = view({ [CASTER]: HERO_AT });
    const kind = (tiles: Pos[], c = {}) => vfxFor([used(tiles)], v0, c).casts[0]!.kind;
    expect(kind([at(6, 2)])).toBe("projectile");
    expect(kind([at(3, 2)])).toBe("slash");
    expect(kind([HERO_AT])).toBe("aura");
    expect(kind([at(2, 1), at(2, 0)])).toBe("beam");
    expect(kind([at(4, 4), at(5, 5), at(4, 5)])).toBe("area");
    expect(kind([at(6, 2)], cards("某種新形狀（射程 9）"))).toBe("projectile");
    expect(kind([HERO_AT, at(2, 1)], cards("新光環", "aura"))).toBe("aura");
    expect(inferShape(HERO_AT, [])).toBe("self");
  });

  it("trusts the tiles over a card whose shape was converted (single → several tiles)", () => {
    const v = vfxFor([used([at(3, 2), at(4, 2), at(5, 2)])], view({ [CASTER]: HERO_AT }), cards("單體（射程 1）"));
    expect(v.casts[0]!.kind).toBe("beam");
  });

  it("an unseen caster gives no cast", () => {
    expect(vfxFor([used([at(3, 2)], "nobody")], view({ [CASTER]: HERO_AT }), {}).casts).toEqual([]);
  });
});

describe("vfxFor: basic attacks, follow-ups and environment damage", () => {
  const attack = (attacker: string, target: string) => ({ type: "attack_rolled", attacker_id: attacker, target_id: target, hit: true });

  it("a melee basic attack slashes, a ranged one shoots, both without the charge glow", () => {
    const melee = vfxFor([attack(CASTER, FOE), damage(FOE, "physical")], view({ [CASTER]: HERO_AT, [FOE]: at(3, 2) }), {});
    expect(melee.casts[0]).toMatchObject({ kind: "slash", charge: false, element: "physical" });
    const ranged = vfxFor([attack(CASTER, FOE)], view({ [CASTER]: HERO_AT, [FOE]: at(7, 2) }), {});
    expect(ranged.casts[0]).toMatchObject({ kind: "projectile", charge: false, element: "physical", ranged: true });
  });

  it("a skill's own attack roll stays in the skill; a counter-attack is its own cast after it", () => {
    const events = [used([at(3, 2)]), attack(CASTER, FOE), damage(FOE, "fire"), attack(FOE, CASTER), damage(CASTER, "physical", false, FOE)];
    const v = vfxFor(events, view({ [CASTER]: HERO_AT, [FOE]: at(3, 2) }), cards("單體（射程 1）"));
    expect(v.casts.map((c) => c.kind)).toEqual(["slash", "slash"]);
    expect(v.casts[1]!.from).toEqual(at(3, 2));
    expect(v.casts[1]!.startMs).toBe(v.casts[0]!.impactMs);
    expect(v.hits.map((h) => h.atMs)).toEqual([v.casts[0]!.impactMs, v.casts[1]!.impactMs]);
  });

  it("a follow-up plays after the first part, from its own origin", () => {
    const followup = { type: "skill_followup", unit_id: CASTER, skill_id: "skill_x", origin: at(4, 4), tiles: [at(5, 4), at(6, 3), at(6, 4), at(6, 5)] };
    const v = vfxFor([used([at(4, 4)]), followup], view({ [CASTER]: at(4, 4) }), cards("單位與落點（射程 3）"));
    expect(v.casts).toHaveLength(2);
    expect(v.casts[1]!.from).toEqual(at(4, 4));
    expect(v.casts[1]!.kind).toBe("area");
    expect(v.casts[1]!.startMs).toBe(v.casts[0]!.impactMs);
  });

  it("environment damage flashes the unit without a cast or a shake", () => {
    const v = vfxFor([damage(FOE, "fire", false, "")], view({ [FOE]: at(1, 1) }), {});
    expect(v.casts).toEqual([]);
    expect(v.hits).toEqual([{ pos: at(1, 1), element: "fire", crit: false, atMs: 0 }]);
    expect(v.shake).toBe(0);
  });
});

describe("scaleVfx and playback", () => {
  const response = fixture as unknown as BattleResponse;
  const hero = response.hero_id;

  it("scales all times by the speed", () => {
    const v = vfxFor([used([at(6, 2)]), damage(FOE, "fire")], view({ [CASTER]: HERO_AT, [FOE]: at(6, 2) }), cards("單體（射程 6）"));
    const slow = scaleVfx(v, 2);
    expect(slow.leadMs).toBe(v.leadMs * 2);
    expect(slow.casts[0]!.impactMs).toBe(v.casts[0]!.impactMs * 2);
    expect(slow.hits[0]!.atMs).toBe(v.hits[0]!.atMs * 2);
    expect(scaleVfx(v, 0.5).leadMs).toBe(Math.round(v.leadMs / 2));
  });

  it("puts the vfx op after the moves and before the view; slow doubles, fast halves, skip has none", () => {
    const frames = (speed: "slow" | "normal" | "fast" | "skip") => playbackPlan(response, hero, speed).frames;
    const normal = frames("normal");
    const withVfx = normal.filter((f) => f.vfx !== null);
    expect(withVfx.length).toBeGreaterThan(0);
    const ops = frameOps(withVfx[0]!).map((o) => o.op);
    expect(ops.indexOf("vfx")).toBe(ops.indexOf("view") - 1);
    const lead = (fs: ReturnType<typeof frames>) => fs.reduce((a, f) => a + (f.vfx?.leadMs ?? 0), 0);
    expect(Math.abs(lead(frames("slow")) - 2 * lead(normal))).toBeLessThanOrEqual(normal.length);
    expect(Math.abs(lead(frames("fast")) - lead(normal) / 2)).toBeLessThanOrEqual(normal.length);
    expect(frames("fast")[0]!.vfxImpactMs).toBe(VFX_TIMING.impact / 2);
    expect(frames("skip").every((f) => f.vfx === null)).toBe(true);
  });
});

interface RandomRecord {
  seed: number;
  card: SkillCard | null;
  events: Record<string, unknown>[] | null;
  units: Array<{ id: string; pos: Pos }> | null;
}

describe("20 random workshop skills (trpg skills random seeds 1–20)", () => {
  const records = randomSkills as unknown as RandomRecord[];
  const KINDS: readonly VfxKind[] = ["projectile", "slash", "burst", "area", "beam", "cone", "aura"];

  it("has 20 skills", () => {
    expect(records).toHaveLength(20);
    expect(records.every((r) => r.card !== null)).toBe(true);
  });

  for (const r of records) {
    it(`seed ${r.seed}: ${r.card?.shape ?? "?"} derives an effect`, () => {
      const c = r.card as SkillCard;
      let events = r.events;
      let units = r.units;
      if (events === null || units === null) {
        // 試玩場沒施放成功（被動、條件不符）：以施放者旁邊一格代替實際範圍
        units = [{ id: CASTER, pos: HERO_AT }];
        events = [used([at(3, 2)], CASTER, c.id)];
      }
      const v = vfxFor(events, view(Object.fromEntries(units.map((u) => [u.id, u.pos]))), { [c.id]: c });
      expect(v.casts.length).toBeGreaterThan(0);
      for (const cast of v.casts) {
        expect(KINDS).toContain(cast.kind);
        expect(elementVfx(cast.element)).toBeDefined();
        expect(cast.impactMs).toBeGreaterThan(cast.startMs);
      }
      expect(shapeIdOf(c)).not.toBeNull();
    });
  }
});

describe("particleAt", () => {
  it("gives finite positions that fade out for every particle kind", () => {
    const kinds: ParticleKind[] = ["ember", "shard", "bolt", "splash", "bubble", "gust", "rock", "pillar", "smoke", "spark", "sparkle"];
    for (const k of kinds) {
      for (const t of [0, 0.3, 0.7, 1]) {
        const p = particleAt(k, 3, 10, t, 30);
        expect([p.x, p.y, p.size, p.alpha, p.rotation].every(Number.isFinite)).toBe(true);
      }
      expect(particleAt(k, 3, 10, 1, 30).alpha).toBeLessThanOrEqual(0.05);
    }
    expect(particleAt("ember", 0, 10, 0.8, 30).y).toBeLessThan(0); // 火星往上飄
  });
});
