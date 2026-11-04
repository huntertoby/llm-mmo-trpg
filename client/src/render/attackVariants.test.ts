import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { skillTimeline, variantFor, type AttackOf } from "../battle/skillSequence";
import { vfxFor } from "../battle/vfx";
import { ARC_DOWN, arcMirror, arcStrokes, arcTravel, ATTACK_FAMILIES, ATTACK_VARIANTS, attackFamilyOf, battleVariantKey, exploreVariantKey, pickVariant, VARIANT_COUNT, VARIANT_CLIPS, type AttackFamily } from "./attackVariants";
import { pz } from "./inkPose";
import { anchorPoint, clipDef, clipPoseRaw, openerFor, weaponClassOf, type ClipId } from "./skillClips";

const HERO = "u_hero";
const FOE = "u_foe";

function view(mapId = "bamboo_grove"): BattleView {
  return { map_id: mapId, units: [{ id: HERO, pos: { x: 1, y: 1 }, team: "ally" }, { id: FOE, pos: { x: 2, y: 1 }, team: "enemy" }], tiles: [] } as unknown as BattleView;
}
const attack = (seq: number, crit = false) => [
  { seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: true, crit },
  { seq: seq + 1, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "physical", amount: 4, crit },
];
function timeline(events: Record<string, unknown>[], family: AttackFamily | null, v = view()) {
  const attackOf: AttackOf = () => family;
  return skillTimeline(events, v, {}, vfxFor(events, v, {}), () => "blade", attackOf)!;
}

describe("variant table (方案 2.10 第 5 點)", () => {
  it("has the documented count per weapon", () => {
    expect(VARIANT_COUNT).toEqual({ sword: 5, saber: 5, arcane: 4, heavy: 3, pair: 4, spear: 4, scythe: 3, whip: 3 });
    for (const f of ATTACK_FAMILIES) expect(ATTACK_VARIANTS[f].length).toBe(VARIANT_COUNT[f]);
    const ids = ATTACK_FAMILIES.flatMap((f) => ATTACK_VARIANTS[f].map((v) => v.id));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every clip exists; within a weapon all windups and all strikes have the same length and hitAt", () => {
    for (const f of ATTACK_FAMILIES) {
      const list = ATTACK_VARIANTS[f];
      const w0 = clipDef(list[0]!.windup);
      const s0 = clipDef(list[0]!.strike);
      expect(s0.hitAt).toBeDefined();
      for (const v of list) {
        const w = clipDef(v.windup);
        const s = clipDef(v.strike);
        expect(w, `${v.id} windup`).toBeDefined();
        expect(s, `${v.id} strike`).toBeDefined();
        expect(w.hitAt).toBeUndefined();
        expect(w.ms).toBe(w0.ms);
        expect(s.ms).toBe(s0.ms);
        expect(s.hitAt).toBe(s0.hitAt);
      }
    }
  });

  it("the first variant keeps the opener table's timing (variants never change the timeline)", () => {
    const opener: Record<AttackFamily, Parameters<typeof openerFor>[0]> = { sword: "blade", saber: "blade", arcane: "arcane", heavy: "blade", pair: "pair", spear: "spear", scythe: "scythe", whip: "whip" };
    for (const f of ATTACK_FAMILIES) {
      const op = openerFor(opener[f], "melee");
      const v = ATTACK_VARIANTS[f][0]!;
      expect(clipDef(v.windup).ms).toBe(clipDef(op.windup!).ms);
      expect(clipDef(v.strike).ms).toBe(clipDef(op.strike).ms);
      expect(clipDef(v.strike).hitAt).toBe(clipDef(op.strike).hitAt);
    }
  });

  it("each windup ends where its strike starts (no jump between the two clips)", () => {
    for (const f of ATTACK_FAMILIES) {
      for (const v of ATTACK_VARIANTS[f]) {
        if (v.windup === "windup" && f === "scythe") continue;
        const end = clipPoseRaw(v.windup, 1);
        const start = clipPoseRaw(v.strike, 0);
        for (const k of ["arm", "elbow", "wpn", "armF", "lean"] as const) expect(pz(end, k), `${v.id} ${k}`).toBeCloseTo(pz(start, k), 6);
      }
    }
  });

  it("all variant clips are used by the table", () => {
    const used = new Set<ClipId>(ATTACK_FAMILIES.flatMap((f) => ATTACK_VARIANTS[f].flatMap((v) => [v.windup, v.strike])));
    for (const id of Object.keys(VARIANT_CLIPS)) expect(used.has(id as ClipId), id).toBe(true);
  });
});

describe("weapon → variant row", () => {
  const g = (kind: string, form?: string) => ({ kind, material: "steel", ...(form === undefined ? {} : { form }) });
  it("maps the paper-doll grip", () => {
    expect(attackFamilyOf(g("sword"), undefined)).toBe("sword");
    expect(attackFamilyOf(g("sword", "straight"), undefined)).toBe("sword");
    expect(attackFamilyOf(g("sword", "curved"), undefined)).toBe("saber");
    expect(attackFamilyOf(g("dagger", "kris"), undefined)).toBe("saber");
    expect(attackFamilyOf(g("dagger"), undefined)).toBe("sword");
    expect(attackFamilyOf(g("sword", "arcane"), undefined)).toBe("arcane");
    expect(attackFamilyOf(g("dagger"), g("dagger"))).toBe("pair");
    expect(attackFamilyOf(g("sword"), g("sword"))).toBe("pair");
    for (const k of ["axe", "hammer", "greatsword"]) expect(attackFamilyOf(g(k), undefined)).toBe("heavy");
    for (const k of ["spear", "scythe", "whip"] as const) expect(attackFamilyOf(g(k), undefined)).toBe(k);
  });
  it("ranged, focus and bare hands have no melee variants (6N-7)", () => {
    for (const k of ["bow", "crossbow", "longgun", "pistol", "staff", "fist", "talisman"]) expect(attackFamilyOf(g(k), undefined)).toBeNull();
    expect(attackFamilyOf(undefined, g("orb"))).toBeNull();
  });
  it("agrees with the opener table's row for the shared weapons", () => {
    expect(weaponClassOf(g("sword", "arcane"), undefined)).toBe("arcane");
    expect(weaponClassOf(g("dagger"), g("dagger"))).toBe("pair");
  });
});

describe("picking (第 0 節第 3 點)", () => {
  it("the key is battle key : seq : caster : clip; exploring uses map : unit : action no.", () => {
    expect(battleVariantKey("bamboo_grove", 12, HERO, "sword")).toBe("bamboo_grove:12:u_hero:attack_sword");
    expect(exploreVariantKey("town_01", HERO, 3)).toBe("town_01:u_hero:3");
  });

  it("the same key always picks the same variant (replay, spectate, reload)", () => {
    for (const f of ATTACK_FAMILIES) {
      for (let seq = 1; seq <= 20; seq++) {
        const a = variantFor(f, "bamboo_grove", seq, HERO);
        const b = variantFor(f, "bamboo_grove", seq, HERO);
        expect(b).toEqual(a);
        expect(pickVariant(f, battleVariantKey("bamboo_grove", seq, HERO, f)).id).toBe(a.id);
      }
    }
    const ev = attack(7);
    const t1 = timeline(ev, "saber");
    const t2 = timeline(structuredClone(ev), "saber");
    expect(t2.rows).toEqual(t1.rows);
    expect(t2.vfx).toEqual(t1.vfx);
  });

  it("8 basic attacks in a row show at least 3 variants (dev page and sample keys)", () => {
    // dev 頁（skill_gallery，每人 seq 1～8）與樣張第 6 區（battle_7f3a、unit_0001）的鍵
    for (const [battle, caster] of [["skill_gallery", "u_00"], ["skill_gallery", "u_03"], ["battle_7f3a", "unit_0001"]] as const) {
      for (const f of ATTACK_FAMILIES) {
        const seen = new Set<string>();
        for (let i = 1; i <= 8; i++) seen.add(variantFor(f, battle, i, caster).id);
        expect(seen.size, `${battle} ${f}`).toBeGreaterThanOrEqual(3);
      }
    }
  });

  it("over many battles, 8 attacks in a row usually show 3+ variants and every variant comes up", () => {
    const maps = ["bamboo_grove", "open_plains", "ashen_waste_01", "cloud_ridge", "frost_pass", "town_gate"];
    const units = ["u_hero", "u_01", "u_02", "bandit_3", "ally_1", "boss_0"];
    for (const f of ATTACK_FAMILIES) {
      let runs = 0;
      let ok = 0;
      const all = new Set<number>();
      for (const m of maps)
        for (const u of units)
          for (const start of [1, 40]) {
            const seen = new Set<number>();
            for (let i = 0; i < 8; i++) seen.add(variantFor(f, m, start + i * 3, u).index);
            seen.forEach((x) => all.add(x));
            runs++;
            if (seen.size >= 3) ok++;
          }
      expect(all.size, f).toBe(VARIANT_COUNT[f]);
      expect(ok / runs, f).toBeGreaterThanOrEqual(0.8);
    }
  });

  it("only basic melee attacks pick variants; skills, ranged attacks and creatures keep the opener", () => {
    const melee = timeline(attack(3), "spear");
    expect(melee.segments[0]!.variant?.family).toBe("spear");
    const creature = timeline(attack(3), null);
    expect(creature.segments[0]!.variant).toBeNull();
    expect(creature.rows.find((r) => r.strike)!.clip).toBe("slash");
    expect(creature.vfx.casts[0]!.arc).toBeUndefined();
    const far = { map_id: "m", units: [{ id: HERO, pos: { x: 1, y: 1 }, team: "ally" }, { id: FOE, pos: { x: 5, y: 1 }, team: "enemy" }], tiles: [] } as unknown as BattleView;
    const ranged = timeline(attack(3), "sword", far);
    expect(ranged.segments[0]!.variant).toBeNull();
    const skill = [{ seq: 1, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles: [{ x: 2, y: 1 }] }, { seq: 2, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "fire", amount: 5 }];
    expect(timeline(skill, "sword").segments[0]!.variant).toBeNull();
  });
});

describe("timing (第 0 節第 5 點)", () => {
  it("every variant of a weapon lands the hit at the same moment", () => {
    for (const f of ATTACK_FAMILIES) {
      const hits = new Set<number>();
      const impacts = new Set<number>();
      const ends = new Set<number>();
      for (let seq = 1; seq <= 60; seq++) {
        const tl = timeline(attack(seq), f);
        hits.add(tl.rows.find((r) => r.strike)!.hitMs!);
        impacts.add(tl.vfx.casts[0]!.impactMs);
        ends.add(Math.max(...tl.rows.map((r) => r.startMs + r.ms)));
      }
      expect(hits.size, f).toBe(1);
      expect(impacts.size, f).toBe(1);
      expect(ends.size, f).toBe(1);
      expect([...hits][0]).toBeCloseTo([...impacts][0]!, 6);
    }
  });
});

describe("arc follows the swing (由下往上揮，弧光也由下往上)", () => {
  const LEN = 20;
  const tip = (id: ClipId, t: number) => anchorPoint(clipPoseRaw(id, t), "tip", "east", LEN);
  const absAngle = (id: ClipId, t: number) => {
    const p = clipPoseRaw(id, t);
    return pz(p, "arm") + pz(p, "elbow") + (p.wpn ?? 0.75);
  };

  for (const f of ATTACK_FAMILIES) {
    it(`${f}: weapon tip and arc move the same way`, () => {
      for (const v of ATTACK_VARIANTS[f]) {
        const hitAt = clipDef(v.strike).hitAt!;
        const a = tip(v.strike, 0);
        const b = tip(v.strike, hitAt);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const arc = arcTravel(v.arc);
        const name = `${v.id}（${v.zh}）`;
        switch (v.swing) {
          case "down":
            expect(dy, name).toBeGreaterThan(0);
            expect(arc.dy, name).toBeGreaterThan(0);
            break;
          case "up":
            expect(dy, name).toBeLessThan(0);
            expect(arc.dy, name).toBeLessThan(0);
            break;
          case "across":
            expect(dx, name).toBeGreaterThan(0);
            expect(arc.dx, name).toBeGreaterThan(0);
            expect(Math.abs(arc.dy), name).toBeLessThan(Math.abs(arc.dx) * 0.5);
            break;
          case "thrust":
            expect(dx, name).toBeGreaterThan(0);
            expect(v.arc.kind, name).toBe("line");
            expect(arc.dx, name).toBeGreaterThan(0);
            break;
          case "spin": {
            expect(v.arc.kind, name).toBe("ring");
            let turn = 0;
            for (let i = 1; i <= 16; i++) turn += absAngle(v.strike, (hitAt * i) / 16) - absAngle(v.strike, (hitAt * (i - 1)) / 16);
            expect(Math.abs(turn), name).toBeGreaterThanOrEqual(Math.PI - 1e-6);
            break;
          }
        }
      }
    });
  }

  it("the default arc (no variant) is the old top-down arc", () => {
    expect(arcTravel(ARC_DOWN).dy).toBeGreaterThan(0);
  });

  it("attacking west mirrors left-right only; up and down stay", () => {
    expect(arcMirror(1, 0)).toBe(1);
    expect(arcMirror(-1, 0)).toBe(-1);
    expect(arcMirror(0, 1)).toBe(1);
    expect(arcMirror(0, -1)).toBe(1);
  });

  it("strokes grow from the start of the swing", () => {
    for (const f of ATTACK_FAMILIES)
      for (const v of ATTACK_VARIANTS[f]) {
        const full = arcStrokes(v.arc, 1);
        const half = arcStrokes(v.arc, 0.3);
        expect(half[0]![0]).toEqual(full[0]![0]);
      }
  });

  it("the picked variant's arc goes on the cast; crit keeps the gold flag on every variant", () => {
    const seenKinds = new Set<string>();
    for (let seq = 1; seq <= 30; seq++) {
      const tl = timeline(attack(seq, true), "saber");
      const cast = tl.vfx.casts[0]!;
      expect(cast.arc).toEqual(tl.segments[0]!.variant!.arc);
      expect(cast.crit).toBe(true);
      seenKinds.add(cast.arc!.kind);
    }
    expect(seenKinds.size).toBeGreaterThanOrEqual(2);
  });
});

