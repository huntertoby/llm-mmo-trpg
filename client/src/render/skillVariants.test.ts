// 6N-8 技能變體：三層的變體數、同鍵同變體、不變的部分（顏色、範圍、落點、hitAt）、飛行物落在目標格、
// 三層位元互相獨立、閃避方向與勝利姿勢不再規律。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { skillTimeline, type WeaponOf } from "../battle/skillSequence";
import { vfxFor } from "../battle/vfx";
import { variantHash } from "./attackVariants";
import { seedOf } from "./inkStyle";
import { dodgeSide, victoryPose } from "./reactClips";
import { baseClipOf, clipDef, clipHitFrame, OPENER_TABLE, PRIMITIVE_CLIPS, WEAPON_CLASSES, type ClipId, type WeaponClass } from "./skillClips";
import {
  BURST_SHAPES,
  CAST_OPENERS,
  CHARGE_POSES,
  DASH_ROUTES,
  HEAL_STYLES,
  LAYER_BITS,
  layerField,
  LEAP_ARCS,
  leapShape,
  OPENER_SETS,
  openerClip,
  openerSetOf,
  ORB_CHANTS,
  pickSkillVariant,
  primitiveClip,
  routeOffset,
  SKILL_VARIANT_COUNT,
  skillVariantKey,
  SPREADS,
  spreadParticle,
  STAFF_CHANTS,
  SUMMON_CIRCLES,
  trajectoryPoint,
  TRAILS,

} from "./skillVariants";
import { healStyleOf } from "./skillVariantPoses";

const HERO = "u_hero";
const FOE = "u_foe";
const at = (x: number, y: number): Pos => ({ x, y });

function view(units: Record<string, [Pos, string]>): BattleView {
  return { map_id: "battle_7f3a", units: Object.entries(units).map(([id, [pos, team]]) => ({ id, pos, team })), tiles: [] } as unknown as BattleView;
}
function card(shapeId: string, range: number, effects: string[]): SkillCard {
  return { id: "fireball", shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: shapeId, range, effects: effects.map((type) => ({ type })) }] } } as unknown as SkillCard;
}
const weapon = (w: WeaponClass): WeaponOf => () => w;
const v = view({ [HERO]: [at(1, 2), "ally"], [FOE]: [at(5, 2), "enemy"], u_ally: [at(2, 2), "ally"] });

/** 同一招在 seq 下放一次（skill_used 的 seq ＝ `seq`）。 */
function castAt(seq: number, w: WeaponClass, c: SkillCard, tiles: Pos[], extra: Record<string, unknown>[] = []) {
  const ev: Record<string, unknown>[] = [
    { seq, round: 1, type: "skill_used", unit_id: HERO, skill_id: "fireball", tiles },
    { seq: seq + 1, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "fire", amount: 5 },
    ...extra,
  ];
  const cards = { fireball: c };
  return skillTimeline(ev, v, cards, vfxFor(ev, v, cards), weapon(w))!;
}

const KEYS = (n: number): string[] => {
  const maps = ["skill_gallery", "battle_7f3a", "open_plain", "ice_lake", "canyon", "ferry", "ruins", "crystal"];
  const out: string[] = [];
  for (let i = 0; out.length < n; i++) out.push(skillVariantKey(maps[i % maps.length]!, Math.floor(i / 80) + 1, `u_${(i >> 3) % 10}`, i % 3 === 0 ? "fireball" : "sk_2"));
  return out;
};

describe("6N-8 skill variants: tables", () => {
  it("each layer has the planned number of variants (方案 2.11)", () => {
    expect(STAFF_CHANTS).toHaveLength(SKILL_VARIANT_COUNT.chant);
    expect(ORB_CHANTS).toHaveLength(SKILL_VARIANT_COUNT.chant);
    expect(SKILL_VARIANT_COUNT).toEqual({ chant: 5, cast: 3, charge: 3, dash: 3, leap: 3, summon: 3, heal: 3, trail: 3, burst: 3, spread: 3 });
    expect(CAST_OPENERS).toHaveLength(3);
    expect(CHARGE_POSES).toHaveLength(3);
    expect(DASH_ROUTES).toHaveLength(3);
    expect(LEAP_ARCS).toHaveLength(3);
    expect(SUMMON_CIRCLES).toHaveLength(3);
    expect(HEAL_STYLES).toHaveLength(3);
    expect(TRAILS.map((x) => x.zh)).toEqual(["微弧", "直線", "螺旋"]);
    expect(BURST_SHAPES.map((x) => x.zh)).toEqual(["放射", "圓環", "星形"]);
    expect(SPREADS.map((x) => x.zh)).toEqual(["均勻", "偏一側", "從中心噴出"]);
    expect(STAFF_CHANTS.map((x) => x.zh)).toEqual(["舉杖（腳下法陣）", "身前畫陣", "頓地捲火", "單手結印", "雙手合十"]);
    expect(CHARGE_POSES.map((x) => x.zh)).toEqual(["收在腰側", "舉過頭", "壓低前傾"]);
  });

  it("every pick lands inside its table; all variants of every layer show up", () => {
    const seen = { chant: new Set<number>(), cast: new Set<number>(), charge: new Set<number>(), dash: new Set<number>(), leap: new Set<number>(), summon: new Set<number>(), heal: new Set<number>(), trail: new Set<number>(), burst: new Set<number>(), spread: new Set<number>() };
    for (const k of KEYS(600)) {
      for (const [set, name] of [["chant_s", "chant"], ["cast", "cast"], ["charge", "charge"]] as const) seen[name].add(pickSkillVariant(k, set).opener!.index);
      const p = pickSkillVariant(k, null);
      expect(p.opener).toBeNull();
      for (const f of ["dash", "leap", "summon", "heal", "trail", "burst", "spread"] as const) seen[f].add(p[f]);
    }
    for (const [name, s] of Object.entries(seen)) expect(s.size, name).toBe(SKILL_VARIANT_COUNT[name as keyof typeof SKILL_VARIANT_COUNT]);
  });

  it("the same key picks the same variant (replay, spectate, reload)", () => {
    for (const k of KEYS(50)) expect(pickSkillVariant(k, "chant_s")).toEqual(pickSkillVariant(`${k}`, "chant_s"));
    expect(skillVariantKey("battle_7f3a", 12, "u_1", "fireball")).toBe("battle_7f3a:12:u_1:skill:fireball");
    expect(skillVariantKey("b", 3, "u_1", null)).toBe("b:3:u_1:skill:attack");
    const a = castAt(5, "staff", card("single", 5, ["damage"]), [at(5, 2)]);
    const b = castAt(5, "staff", card("single", 5, ["damage"]), [at(5, 2)]);
    expect(a).toEqual(b);
  });

  it("opener layer: staff/orb chant, other weapons cast or charge, no windup → none", () => {
    expect(openerSetOf("staff", "ranged", false, true)).toBe("chant_s");
    expect(openerSetOf("orb", "self", false, true)).toBe("chant_o");
    expect(openerSetOf("blade", "ranged", false, true)).toBe("cast");
    expect(openerSetOf("blade", "melee", false, true)).toBe("charge");
    expect(openerSetOf("staff", "melee", false, true)).toBe("charge");
    expect(openerSetOf("staff", "ground", false, false)).toBeNull();
    // 法器普攻（6N-7 待決 1）：遠程歸詠唱；近身的杖敲、球推照舊
    expect(openerSetOf("staff", "ranged", true, true)).toBe("chant_s");
    expect(openerSetOf("orb", "melee", true, true)).toBeNull();
    expect(openerSetOf("bow", "ranged", true, true)).toBeNull();
  });
});

describe("6N-8 skill variants: what never changes", () => {
  it("derived opener clips keep length, hitAt, anchor, movement and the hit pose", () => {
    for (const w of WEAPON_CLASSES) {
      for (const mode of ["melee", "ranged", "self", "ground"] as const) {
        const op = OPENER_TABLE[w][mode];
        const set = openerSetOf(w, mode, false, op.windup !== null);
        if (set === null) continue;
        OPENER_SETS[set].forEach((_, index) => {
          const pick = { ...pickSkillVariant("x", set), opener: { set, index } };
          const wu = openerClip(op.windup!, pick);
          const st = openerClip(op.strike, pick);
          const bw = clipDef(op.windup!);
          const bs = clipDef(op.strike);
          expect(clipDef(wu).ms, `${w} ${mode} ${index}`).toBe(bw.ms);
          expect(clipDef(wu).hitAt).toBeUndefined();
          expect(clipDef(wu).anchor).toBe(bw.anchor);
          expect(clipDef(wu).keys[0]).toEqual(bw.keys[0]); // 從站好開始
          expect(clipDef(st).ms).toBe(bs.ms);
          expect(clipDef(st).hitAt).toBe(bs.hitAt);
          expect(clipDef(st).anchor).toBe(bs.anchor);
          expect(clipDef(st).move).toEqual(bs.move);
          // 命中（放出）那一格一樣 → 作用端、飛行物起點一樣（沒給的欄位 ＝ 0；`wpn` 沒給 ＝ 預設握法，要一樣沒給）
          const nz = (f: ReturnType<typeof clipHitFrame>) => ({ ...f, pose: Object.fromEntries(Object.entries(f.pose).filter(([, x]) => x !== 0)) });
          expect(nz(clipHitFrame(st)), `${w} ${mode} ${index}`).toEqual(nz(clipHitFrame(op.strike)));
          expect(clipHitFrame(st).pose.wpn).toBe(clipHitFrame(op.strike).pose.wpn);
          // 接得上：原本蓄力最後一格 ＝ 出招第一格時，衍生的也一樣
          const lastW = clipDef(wu).keys[clipDef(wu).keys.length - 1]![1];
          if (JSON.stringify(bw.keys[bw.keys.length - 1]![1]) === JSON.stringify(bs.keys[0]![1])) expect(clipDef(st).keys[0]![1], `${w} ${mode} ${index}`).toEqual(lastW);
          expect(baseClipOf(wu)).toBe(op.windup);
        });
      }
    }
  });

  it("primitive layer (summon circles, heal/buff light) only swaps effects", () => {
    const heal = (c: ClipId) => healStyleOf(clipDef(c));
    for (const clip of ["summon_press", "palm_heal", "raise_hand"] as const) {
      const ids = new Set<string>();
      for (let i = 0; i < 27; i++) {
        const pick = { ...pickSkillVariant("x", null), summon: i % 3, heal: Math.floor(i / 3) % 3 };
        const d = clipDef(primitiveClip(clip, pick, heal));
        ids.add(JSON.stringify(d.fx));
        expect(d.ms).toBe(PRIMITIVE_CLIPS[clip].ms);
        expect(d.keys).toEqual(PRIMITIVE_CLIPS[clip].keys);
        expect(d.anchor).toBe(PRIMITIVE_CLIPS[clip].anchor);
      }
      expect(ids.size, clip).toBe(3);
    }
    expect(primitiveClip("zone_stamp", pickSkillVariant("x", null), heal)).toBe("zone_stamp");
  });

  it("same fireball cast 60 times: element, tiles, target, hit times and the whole timeline stay; poses and trails vary", () => {
    const c = card("single", 5, ["damage"]);
    const base = castAt(1, "staff", c, [at(5, 2)]);
    const clips = new Set<string>();
    const looks = new Set<string>();
    for (let seq = 1; seq <= 120; seq += 2) {
      const tl = castAt(seq, "staff", c, [at(5, 2)]);
      expect(tl.rows.map((r) => [r.startMs, r.ms, r.hitMs, r.strike, r.unitId, r.cast, r.target, r.element])).toEqual(base.rows.map((r) => [r.startMs, r.ms, r.hitMs, r.strike, r.unitId, r.cast, r.target, r.element]));
      const strip = (x: typeof tl) => x.vfx.casts.map(({ look: _look, ...rest }) => rest);
      expect(strip(tl)).toEqual(strip(base));
      expect(tl.vfx.hits).toEqual(base.vfx.hits);
      expect(tl.vfx.leadMs).toBe(base.vfx.leadMs);
      expect(tl.vfx.casts[0]!.element).toBe("fire");
      expect(tl.vfx.casts[0]!.tiles).toEqual([at(5, 2)]);
      clips.add(tl.rows.map((r) => r.clip).join(","));
      looks.add(JSON.stringify(tl.vfx.casts[0]!.look));
    }
    expect(clips.size).toBe(5); // 詠唱 5 種都出現
    expect(looks.size).toBeGreaterThanOrEqual(15); // 軌跡 × 爆發 × 粒子（27 種裡出現大半）
  });

  it("melee, self and ground skills keep their timeline too (charge, cast openers)", () => {
    const cases: Array<[WeaponClass, SkillCard, Pos[]]> = [
      ["blade", card("single", 1, ["damage", "heal"]), [at(2, 2)]],
      ["spear", card("single", 5, ["damage"]), [at(5, 2)]],
      ["blade", card("self", 0, ["damage"]), [at(1, 2)]],
      ["orb", card("ground_tile", 4, ["damage", "summon"]), [at(5, 2)]],
      ["gun", card("ground_tile", 4, ["damage"]), [at(5, 2)]],
    ];
    for (const [w, c, tiles] of cases) {
      const base = castAt(1, w, c, tiles);
      const clips = new Set<string>();
      for (let seq = 1; seq <= 40; seq++) {
        const tl = castAt(seq, w, c, tiles);
        expect(tl.rows.map((r) => [r.startMs, r.ms, r.hitMs]), w).toEqual(base.rows.map((r) => [r.startMs, r.ms, r.hitMs]));
        expect(tl.vfx.casts.map((x) => [x.element, x.tiles, x.to, x.impactMs])).toEqual(base.vfx.casts.map((x) => [x.element, x.tiles, x.to, x.impactMs]));
        clips.add(tl.rows.map((r) => r.clip).join(","));
      }
      expect(clips.size, `${w}`).toBeGreaterThanOrEqual(3);
    }
  });

  it("basic attacks: staff ranged attacks pick a chant only (no fx layer); weapons with attack variants are untouched", () => {
    const atk = (seq: number) => [
      { seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: true },
      { seq: seq + 1, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "physical", amount: 3 },
    ];
    const chants = new Set<string>();
    for (let seq = 1; seq < 60; seq += 2) {
      const ev = atk(seq);
      const tl = skillTimeline(ev, v, {}, vfxFor(ev, v, {}), weapon("staff"))!;
      expect(tl.segments[0]!.skillVariant!.opener!.set).toBe("chant_s");
      expect(tl.vfx.casts[0]!.look).toBeUndefined();
      chants.add(tl.rows[0]!.clip);
      const bow = skillTimeline(ev, v, {}, vfxFor(ev, v, {}), weapon("bow"))!;
      expect(bow.segments[0]!.skillVariant).toBeNull();
    }
    expect(chants.size).toBe(5);
  });

  it("the 1.8 s cap still holds with every chant (charged far shot)", () => {
    const far = view({ [HERO]: [at(0, 0), "ally"], [FOE]: [at(9, 0), "enemy"] });
    const c = { ...card("single", 9, ["damage_multiplier", "damage"]), timing: "delayed" } as unknown as SkillCard;
    for (let seq = 1; seq <= 30; seq++) {
      const ev = [
        { seq, round: 1, type: "skill_used", unit_id: HERO, skill_id: "fireball", tiles: [at(9, 0)] },
        { seq: seq + 1, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "fire", amount: 5 },
      ];
      const tl = skillTimeline(ev, far, { fireball: c }, vfxFor(ev, far, { fireball: c }), weapon("staff"))!;
      expect(tl.vfx.casts[0]!.impactMs).toBeLessThanOrEqual(1800 + 1e-6);
    }
  });
});

describe("6N-8 skill variants: geometry", () => {
  it("a projectile lands on the target tile whatever the trail", () => {
    const pts: Array<[Pos, Pos]> = [
      [{ x: 24, y: 24 }, { x: 264, y: 24 }],
      [{ x: 264, y: 120 }, { x: 24, y: 24 }],
      [{ x: 100, y: 40 }, { x: 100, y: 300 }],
      [{ x: 30, y: 30 }, { x: 31, y: 30 }],
    ];
    for (const tr of TRAILS) {
      for (const [a, b] of pts) {
        expect(trajectoryPoint(a, b, 1, tr.id, 48)).toEqual(b);
        expect(trajectoryPoint(a, b, 0, tr.id, 48)).toEqual(a);
        expect(trajectoryPoint(a, b, 1.2, tr.id, 48)).toEqual(b);
        // 中途離目標越來越近（最後 5% 在半格內）
        const near = trajectoryPoint(a, b, 0.97, tr.id, 48);
        expect(Math.hypot(near.x - b.x, near.y - b.y)).toBeLessThan(24);
      }
    }
    const a = { x: 0, y: 0 };
    const b = { x: 240, y: 0 };
    expect(trajectoryPoint(a, b, 0.5, "straight", 48)).toEqual({ x: 120, y: 0 });
    expect(trajectoryPoint(a, b, 0.5, "arc", 48).y).toBeLessThan(-10); // 往上拱
    const sp = [0.1, 0.2, 0.3, 0.4].map((t) => trajectoryPoint(a, b, t, "spiral", 48).y);
    expect(new Set(sp.map((y) => Math.sign(Math.round(y)))).size).toBeGreaterThan(1); // 繞著直線轉
  });

  it("dash routes start and end on the line; zigzag has two corners; leap flips land upright", () => {
    for (const r of DASH_ROUTES) {
      expect(routeOffset(r.id, 0)).toBe(0);
      expect(Math.abs(routeOffset(r.id, 1))).toBeLessThan(1e-9);
    }
    expect(routeOffset("straight", 0.5)).toBe(0);
    expect(routeOffset("curve", 0.5)).toBeGreaterThan(0.2);
    expect(routeOffset("zigzag", 1 / 3)).toBeGreaterThan(0);
    expect(routeOffset("zigzag", 2 / 3)).toBeLessThan(0);
    expect(leapShape("low", 0.5).airScale).toBe(1); // 低弧 ＝ 原本的 leap_air
    expect(leapShape("high", 0.5).airScale).toBeGreaterThan(1.5);
    expect(leapShape("flip", 0).spin).toBe(0);
    expect(leapShape("flip", 1).spin).toBeCloseTo(Math.PI * 2, 9);
    expect(leapShape("flip", 0.5).spin).toBeCloseTo(Math.PI, 9);
  });

  it("particle spread only moves particles (even = unchanged)", () => {
    const p = { x: 5, y: -3 };
    expect(spreadParticle(p, "even", 0.5, 30, 1)).toEqual(p);
    expect(spreadParticle(p, "side", 0.5, 30, 1).x).toBeGreaterThan(spreadParticle(p, "side", 0.5, 30, -1).x);
    expect(spreadParticle(p, "center", 0.5, 30, 1).y).toBeLessThan(p.y);
  });
});

describe("6N-8 skill variants: independent bits", () => {
  it("the three layers use disjoint bit ranges covering all 32 bits", () => {
    const r = Object.values(LAYER_BITS).sort((a, b) => a[0] - b[0]);
    expect(r[0]![0]).toBe(0);
    for (let i = 1; i < r.length; i++) expect(r[i]![0]).toBe(r[i - 1]![1]);
    expect(r[r.length - 1]![1]).toBe(32);
    const h = 0b1011_0110_1100_1010_0101_1110_0011_1001 >>> 0;
    expect(layerField(h, "opener")).toBe(h & 0x3ff);
    expect(layerField(h, "primitive")).toBe((h >>> 10) & 0x7ff);
    expect(layerField(h, "fx")).toBe(h >>> 21);
  });

  it("joint distributions across layers are close to uniform (chi-square)", () => {
    const N = 27000;
    const keys = KEYS(N);
    const picks = keys.map((k) => pickSkillVariant(k, "chant_s"));
    const pairs: Array<[string, (p: (typeof picks)[number]) => number, number, (p: (typeof picks)[number]) => number, number]> = [
      ["chant×trail", (p) => p.opener!.index, 5, (p) => p.trail, 3],
      ["chant×dash", (p) => p.opener!.index, 5, (p) => p.dash, 3],
      ["dash×burst", (p) => p.dash, 3, (p) => p.burst, 3],
      ["leap×spread", (p) => p.leap, 3, (p) => p.spread, 3],
      ["trail×burst", (p) => p.trail, 3, (p) => p.burst, 3],
      ["burst×spread", (p) => p.burst, 3, (p) => p.spread, 3],
      ["summon×heal", (p) => p.summon, 3, (p) => p.heal, 3],
    ];
    for (const [name, fa, na, fb, nb] of pairs) {
      const cells = new Array<number>(na * nb).fill(0);
      for (const p of picks) cells[fa(p) * nb + fb(p)]! += 1;
      const e = N / (na * nb);
      const chi = cells.reduce((s, o) => s + ((o - e) * (o - e)) / e, 0);
      // 自由度 (na·nb − 1)：8 → 99.9% 臨界 26.1；14 → 36.1
      expect(chi, `${name} ${cells.join(",")}`).toBeLessThan(na * nb <= 9 ? 26.1 : 36.1);
      for (const o of cells) expect(Math.abs(o - e) / e, name).toBeLessThan(0.08);
    }
    // 全組合（詠唱 5 × 軌跡 3 × 爆發 3）45 種都出現
    expect(new Set(picks.map((p) => `${p.opener!.index}${p.trail}${p.burst}`)).size).toBe(45);
  });
});

describe("6N-8: dodge side and victory pose use variantHash", () => {
  const runs = (fn: (seq: number, unit: string, map: string) => number, step: number) => {
    let same = 0;
    let total = 0;
    for (const map of ["skill_gallery", "battle_7f3a", "open_plain", "ice_lake"]) {
      for (let u = 0; u < 10; u++) {
        let prev: number | null = null;
        for (let k = 0; k < 40; k++) {
          const cur = fn(1 + k * step, `u_${u}`, map);
          if (prev !== null) {
            total += 1;
            if (cur === prev) same += 1;
          }
          prev = cur;
        }
      }
    }
    return same / total;
  };

  it("consecutive dodges are no longer stuck on one side (seq step 1 and 2)", () => {
    for (const step of [1, 2, 3]) {
      const r = runs((seq, u, m) => dodgeSide(m, seq, u), step);
      expect(r, `step ${step}`).toBeGreaterThan(0.4);
      expect(r, `step ${step}`).toBeLessThan(0.6);
    }
    // 改善前（seedOf % 2）間隔 2 時八成連續同一邊
    expect(runs((seq, u, m) => (seedOf(`${m}:${seq}:${u}:dodge`) % 2 === 0 ? 1 : -1), 2)).toBeGreaterThan(0.7);
    expect(dodgeSide("b", 3, "u_1")).toBe(variantHash("b:3:u_1:dodge") % 2 === 0 ? 1 : -1);
  });

  it("victory pose: both kinds, no long runs", () => {
    const r = runs((seq, u, m) => (victoryPose(m, seq, u) === "raise" ? 1 : 0), 2);
    expect(r).toBeGreaterThan(0.4);
    expect(r).toBeLessThan(0.6);
  });
});
