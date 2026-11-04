import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { skillTimeline, variantFor, type AttackOf } from "../battle/skillSequence";
import { vfxFor } from "../battle/vfx";
import { ARC_DOWN, arcMirror, arcStrokes, arcTravel, ATTACK_FAMILIES, ATTACK_VARIANTS, attackFamilyOf, battleVariantKey, exploreVariantKey, fmix32, pickVariant, RANGED_FAMILIES, VARIANT_COUNT, VARIANT_CLIPS, variantHash, type AttackFamily } from "./attackVariants";
import { pz } from "./inkPose";
import { seedOf } from "./inkStyle";

/** dev 頁 `#variants` 連續 8 次那幾排的施放者 ID（`dev/skillGallery.ts` 的 `liveCaster`）。 */
const DEV_LIVE_CASTER = (i: number): string => `r_${i}`;

/** 規律輪替：每一步都差同一個（不是 0 的）餘數，例如 0,1,2,3,0,1… 或 2,0,1,2,0,1…。 */
function isRotation(seq: readonly number[], n: number): boolean {
  if (seq.length < 3) return false;
  const d = (((seq[1]! - seq[0]!) % n) + n) % n;
  if (d === 0) return false;
  for (let i = 2; i < seq.length; i++) if ((((seq[i]! - seq[i - 1]!) % n) + n) % n !== d) return false;
  return true;
}
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
    expect(VARIANT_COUNT).toEqual({ sword: 5, saber: 5, arcane: 4, heavy: 3, pair: 4, spear: 4, scythe: 3, whip: 3, fist: 5, bow: 4, crossbow: 3, gun: 3 });
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
    const opener: Record<AttackFamily, Parameters<typeof openerFor>[0]> = { sword: "blade", saber: "blade", arcane: "arcane", heavy: "blade", pair: "pair", spear: "spear", scythe: "scythe", whip: "whip", fist: "fist", bow: "bow", crossbow: "crossbow", gun: "gun" };
    for (const f of ATTACK_FAMILIES) {
      const op = openerFor(opener[f], RANGED_FAMILIES.includes(f) ? "ranged" : "melee");
      const v = ATTACK_VARIANTS[f][0]!;
      // 6N-7 的列：第一個就是起手對照表原本的片段
      if (["fist", "bow", "crossbow", "gun"].includes(f)) expect([v.windup, v.strike], f).toEqual([op.windup, op.strike]);
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
  it("6N-7: bow, crossbow, guns, fist and bare hands get their rows; staff and orb stay on the opener", () => {
    expect(attackFamilyOf(g("bow"), undefined)).toBe("bow");
    expect(attackFamilyOf(g("crossbow"), undefined)).toBe("crossbow");
    for (const k of ["longgun", "pistol", "shotgun"]) expect(attackFamilyOf(g(k), undefined)).toBe("gun");
    for (const k of ["fist", "talisman", "whisk"]) expect(attackFamilyOf(g(k), undefined), k).toBe("fist");
    expect(attackFamilyOf(g("fist"), g("fist"))).toBe("fist");
    expect(attackFamilyOf(undefined, undefined)).toBe("fist");
    expect(attackFamilyOf(g("staff"), undefined)).toBeNull();
    expect(attackFamilyOf(undefined, g("orb"))).toBeNull();
    expect(attackFamilyOf(g("talisman"), g("orb"))).toBeNull();
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

  it("8 basic attacks in a row show at least 3 variants (dev page keys)", () => {
    // dev 頁 `#variants` 最後幾排：第 i 種武器的施放者 ＝ `r_<i>`，戰鬥鍵 skill_gallery，seq 1～8（6N-7 換了挑法後重新挑過的鍵）
    ATTACK_FAMILIES.forEach((f, i) => {
      const seen = new Set<string>();
      for (let s = 1; s <= 8; s++) seen.add(variantFor(f, "skill_gallery", s, DEV_LIVE_CASTER(i)).id);
      expect(seen.size, `${f} ${DEV_LIVE_CASTER(i)}`).toBeGreaterThanOrEqual(3);
    });
  });

  it("over many battles every variant comes up and consecutive attacks do not rotate regularly (6N-7 criterion)", () => {
    const maps = ["bamboo_grove", "open_plains", "ashen_waste_01", "cloud_ridge", "frost_pass", "town_gate"];
    const units = ["u_hero", "u_01", "u_02", "bandit_3", "ally_1", "boss_0"];
    for (const f of ATTACK_FAMILIES) {
      const n = VARIANT_COUNT[f];
      let runs = 0;
      let regular = 0;
      const all = new Set<number>();
      for (const m of maps)
        for (const u of units)
          for (const start of [1, 40, 200]) {
            const seq = Array.from({ length: 8 }, (_, i) => variantFor(f, m, start + i, u).index); // 連續的 seq（最容易輪替的情形）
            seq.forEach((x) => all.add(x));
            runs++;
            if (isRotation(seq, n)) regular++;
          }
      expect(all.size, f).toBe(n);
      expect(regular / runs, f).toBeLessThanOrEqual(0.02);
    }
  });

  it("the finalizer breaks the FNV-1a low-bit rotation (4 variants, consecutive seq)", () => {
    // 6N-6 的挑法（seedOf % 4）在連續 seq 時幾乎都是規律輪替；fmix32 之後不是
    let before = 0;
    let after = 0;
    let runs = 0;
    for (const u of ["u_hero", "u_01", "bandit_3", "boss_0"])
      for (let start = 1; start <= 200; start += 8) {
        const keys = Array.from({ length: 8 }, (_, i) => battleVariantKey("bamboo_grove", start + i, u, "spear"));
        if (isRotation(keys.map((k) => seedOf(k) % 4), 4)) before++;
        if (isRotation(keys.map((k) => variantHash(k) % 4), 4)) after++;
        runs++;
      }
    expect(before / runs).toBeGreaterThan(0.1);
    expect(after / runs).toBeLessThanOrEqual(0.02);
  });

  it("fmix32 is deterministic, a bijection-style 32-bit mix, and leaves seedOf alone", () => {
    expect(fmix32(0)).toBe(0);
    expect(fmix32(1)).toBe(fmix32(1));
    expect(fmix32(1)).toBe(0x514e28b7); // murmur3 fmix32 的已知值
    expect(fmix32(0xffffffff)).toBe(fmix32(-1));
    for (const k of ["a", "bamboo_grove:12:u_hero:attack_sword"]) {
      expect(variantHash(k)).toBe(fmix32(seedOf(k)));
      expect(variantHash(k)).toBeGreaterThanOrEqual(0);
      expect(variantHash(k)).toBeLessThan(2 ** 32);
    }
    expect(seedOf("a")).toBe(0xe40c292c); // FNV-1a 本身不變
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
    // 6N-7：遠程的列只在遠程挑；弓在近身（用弓身敲）、拳套在遠程（拳風）不挑
    expect(timeline(attack(3), "bow", far).segments[0]!.variant?.family).toBe("bow");
    expect(timeline(attack(3), "bow").segments[0]!.variant).toBeNull();
    expect(timeline(attack(3), "fist").segments[0]!.variant?.family).toBe("fist");
    expect(timeline(attack(3), "fist", far).segments[0]!.variant).toBeNull();
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

  it("6N-7 ranged: every bow, crossbow and gun variant keeps the projectile, its landing tile and timing", () => {
    const far = { map_id: "open_plains", units: [{ id: HERO, pos: { x: 1, y: 1 }, team: "ally" }, { id: FOE, pos: { x: 5, y: 3 }, team: "enemy" }], tiles: [] } as unknown as BattleView;
    const weapon = { bow: "bow", crossbow: "crossbow", gun: "gun" } as const;
    for (const f of RANGED_FAMILIES) {
      const w = weapon[f as keyof typeof weapon];
      const casts = new Set<string>();
      const rows = new Set<string>();
      const picked = new Set<string>();
      for (let seq = 1; seq <= 60; seq++) {
        const ev = attack(seq);
        const tl = skillTimeline(ev, far, {}, vfxFor(ev, far, {}), () => w, () => f)!;
        const seg = tl.segments[0]!;
        expect(seg.variant?.family, f).toBe(f);
        picked.add(seg.variant!.id);
        const c = tl.vfx.casts[0]!;
        expect(c.arc, f).toBeUndefined(); // 遠程不畫弧光
        casts.add(JSON.stringify({ kind: c.kind, from: c.from, to: c.to, path: c.path, startMs: c.startMs, impactMs: c.impactMs }));
        rows.add(JSON.stringify(tl.rows.map((r) => [r.startMs, r.ms, r.hitMs])));
        // 沒有變體時（6N-7 以前）的特效一樣
        const plain = skillTimeline(ev, far, {}, vfxFor(ev, far, {}), () => w)!;
        expect(plain.vfx.casts[0]!.to).toEqual(c.to);
      }
      expect(picked.size, f).toBe(VARIANT_COUNT[f]);
      expect(casts.size, f).toBe(1);
      expect(rows.size, f).toBe(1);
      expect(JSON.parse([...casts][0]!).to).toEqual({ x: 5, y: 3 });
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

  it("ranged variants have no slash arc", () => {
    for (const f of RANGED_FAMILIES) for (const v of ATTACK_VARIANTS[f]) expect(v.arc, v.id).toBeNull();
  });

  for (const f of ATTACK_FAMILIES.filter((x) => !RANGED_FAMILIES.includes(x))) {
    it(`${f}: weapon tip (fist: hand, knee: chest) and arc move the same way`, () => {
      for (const v of ATTACK_VARIANTS[f]) {
        const def = clipDef(v.strike);
        const hitAt = def.hitAt!;
        const name = `${v.id}（${v.zh}）`;
        const spec = v.arc!;
        expect(spec, name).not.toBeNull();
        if (def.anchor === "feet") {
          // 迴旋踢：腳是作用端（anchorPoint 的 feet 永遠是腳底原點），只鎖弧光是一圈
          expect(spec.kind, name).toBe("ring");
          continue;
        }
        const at = (t: number) => (def.anchor === "tip" ? tip(v.strike, t) : anchorPoint(clipPoseRaw(v.strike, t), def.anchor, "east", 0));
        const a = at(0);
        const b = at(hitAt);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const arc = arcTravel(spec);
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
            expect(spec.kind, name).toBe("line");
            expect(arc.dx, name).toBeGreaterThan(0);
            break;
          case "shoot":
            throw new Error(`${name}: melee variant marked as shoot`);
          case "spin": {
            expect(spec.kind, name).toBe("ring");
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
        if (v.arc === null) continue;
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

