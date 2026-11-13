import primitivesYaml from "../../../content/skill_primitives.yaml?raw";
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import {
  anchorPoint,
  CAST_MODES,
  CLIP_STEPS,
  clipDef,
  clipFrame,
  OPENER_CLIPS,
  OPENER_TABLE,
  openerFor,
  PRIMITIVE_PLAYS,
  primitivePlay,
  recoverFrame,
  WEAPON_CLASSES,
  weaponClassOf,
  type CastMode,
  type ClipId,
  type WeaponClass,
} from "./skillClips";
import { setDollSkin } from "./inkStyle";
import { afterEach as afterEachQ } from "vitest";

afterEachQ(() => setDollSkin("q"));

/** 6N-3 做的下半原語（需求第二批第 3 節的「下」；6N-1 報告第 4 節的 34 個）。 */
const LOWER_HALF: readonly string[] = [
  "add_stack",
  "blow_surface",
  "cheat_death",
  "clear_surface",
  "consume_stack",
  "consume_status",
  "copy_skill",
  "create_obstacle",
  "create_surface",
  "destroy_object",
  "detonate_runes",
  "enter_form",
  "extra_reaction",
  "gamble",
  "grant_ap",
  "grant_skill",
  "hurl_object",
  "inscribe",
  "intercept",
  "leave_form",
  "lower_terrain",
  "place_trap",
  "raise_terrain",
  "redirect_damage",
  "refund_ap",
  "refund_cooldown",
  "reset_cooldown",
  "reveal",
  "rule_change",
  "sacrifice_summon",
  "self_damage_of_hit",
  "summon",
  "topple",
  "zone",
];

function primitiveIds(): string[] {
  const text = primitivesYaml;
  return [...text.matchAll(/^ {2}- id: ([a-z_]+)/gmu)].map((m) => m[1] as string).sort();
}

describe("opener table (13 weapons × 4 cast modes)", () => {
  it("covers every weapon class and cast mode with real clips", () => {
    expect(WEAPON_CLASSES).toHaveLength(13);
    for (const w of WEAPON_CLASSES) {
      for (const m of CAST_MODES) {
        const o = OPENER_TABLE[w][m];
        expect(o, `${w}/${m}`).toBeDefined();
        expect(clipDef(o.strike).hitAt, `${w}/${m} strike has hitAt`).toBeTypeOf("number");
        if (o.windup !== null) expect(clipDef(o.windup).hitAt, `${w}/${m} windup has no hit`).toBeUndefined();
      }
    }
  });

  it("falls back to the bare-hand row for unknown combos", () => {
    expect(openerFor("nope" as WeaponClass, "ranged")).toEqual(OPENER_TABLE.bare.ranged);
  });

  it("staff fireball, arcane blade (option A) and gun use different openers", () => {
    expect(OPENER_TABLE.staff.ranged).toEqual({ windup: "channel", strike: "cast" });
    expect(OPENER_TABLE.arcane.ranged).toEqual({ windup: "sigil", strike: "sigil_cast" });
    expect(OPENER_TABLE.gun.ranged).toEqual({ windup: "aim_gun", strike: "fire" });
    expect(OPENER_TABLE.blade.melee).toEqual({ windup: "windup", strike: "slash" });
  });

  it("maps doll gear to weapon classes", () => {
    const k = (kind: string, form?: string) => ({ kind, ...(form === undefined ? {} : { form }) });
    expect(weaponClassOf(k("sword"), undefined)).toBe("blade");
    expect(weaponClassOf(k("sword", "curved"), undefined)).toBe("blade");
    expect(weaponClassOf(k("sword", "arcane"), undefined)).toBe("arcane");
    expect(weaponClassOf(k("dagger"), k("dagger"))).toBe("pair");
    expect(weaponClassOf(k("spear"), undefined)).toBe("spear");
    expect(weaponClassOf(k("scythe"), undefined)).toBe("scythe");
    expect(weaponClassOf(k("whip"), undefined)).toBe("whip");
    expect(weaponClassOf(k("fist"), k("fist"))).toBe("fist");
    expect(weaponClassOf(k("staff"), k("orb"))).toBe("staff");
    expect(weaponClassOf(undefined, k("orb"))).toBe("orb");
    expect(weaponClassOf(k("bow"), undefined)).toBe("bow");
    expect(weaponClassOf(k("crossbow"), undefined)).toBe("crossbow");
    for (const g of ["longgun", "pistol", "shotgun"]) expect(weaponClassOf(k(g), undefined)).toBe("gun");
    expect(weaponClassOf(k("whisk"), undefined)).toBe("bare");
    expect(weaponClassOf(undefined, undefined)).toBe("bare");
  });
});

describe("clip timeline", () => {
  it("is deterministic and quantized (16 steps, pose to 0.02)", () => {
    for (const id of Object.keys(OPENER_CLIPS) as ClipId[]) {
      for (const t of [0, 0.13, 0.5, 0.77, 1]) {
        const a = clipFrame(id, t);
        expect(clipFrame(id, t)).toEqual(a);
        for (const v of Object.values(a.pose)) expect(Math.abs(v * 50 - Math.round(v * 50))).toBeLessThan(1e-6);
      }
      // 同一格內的時間取同一個姿勢
      expect(clipFrame(id, 0.5)).toEqual(clipFrame(id, 0.5 + 0.2 / CLIP_STEPS));
    }
  });

  it("recover ends at the rest pose", () => {
    const end = recoverFrame("slash", 1);
    for (const [k, v] of Object.entries(end.pose)) if (k !== "wpn") expect(Math.abs(v), k).toBeLessThan(0.021);
    expect(end.forward).toBe(0);
  });

  it("strike clips hold their hitAt between 0 and 1", () => {
    for (const w of WEAPON_CLASSES) for (const m of CAST_MODES) {
      const h = clipDef(OPENER_TABLE[w][m].strike).hitAt!;
      expect(h).toBeGreaterThan(0);
      expect(h).toBeLessThan(1);
    }
  });
});

describe("fx anchor from the pose", () => {
  const LEN = 20;
  const ranged: Array<[WeaponClass, CastMode]> = WEAPON_CLASSES.map((w) => [w, "ranged"]);
  it.each(ranged)("%s %s: the tip at release is in front of the body (east / west)", (w, m) => {
    const strike = OPENER_TABLE[w][m].strike;
    const def = clipDef(strike);
    const pose = clipFrame(strike, def.hitAt!).pose;
    const east = anchorPoint(pose, def.anchor, "east", LEN);
    const west = anchorPoint(pose, def.anchor, "west", LEN);
    expect(east.x).toBeGreaterThan(4);
    expect(west.x).toBeCloseTo(-east.x, 6);
    expect(east.y).toBeLessThan(0);
  });

  it("melee slash: tip ends in front and low after the swing", () => {
    const p = clipFrame("slash", 1).pose;
    const tip = anchorPoint(p, "tip", "east", LEN);
    expect(tip.x).toBeGreaterThan(8);
  });

  it("feet anchor is the origin; front views use the hands", () => {
    setDollSkin("c"); // QK-1：±9 是 C 骨架的手位置，鎖 C；Q 版另見 qAnchor 測試
    for (const f of ["north", "south", "east", "west"] as Facing[]) expect(anchorPoint({}, "feet", f, LEN)).toEqual({ x: 0, y: 0 });
    expect(anchorPoint({}, "hand", "south", 0).x).toBe(-9);
    expect(anchorPoint({}, "hand", "north", 0).x).toBe(9);
  });
});

describe("primitive clips (6N-2 first half, 6N-3 second half)", () => {
  it("every primitive in skill_primitives.yaml has a clip (6N-3: none left)", () => {
    const ids = primitiveIds();
    expect(ids.length).toBeGreaterThan(50);
    const missing = ids.filter((id) => primitivePlay(id) === null && primitivePlay(id, "buff") === null);
    expect(missing).toEqual([]);
    for (const id of LOWER_HALF) {
      const play = primitivePlay(id);
      expect(play?.clip, id).not.toBeNull();
      expect(play?.role, id).toBe("post");
      const def = clipDef(play!.clip!);
      expect(def.ms, id).toBeGreaterThanOrEqual(200);
      expect(def.ms, id).toBeLessThanOrEqual(520);
      expect(def.keys.length, id).toBeGreaterThanOrEqual(2);
    }
  });

  it("only the groups marked shared in the table share a clip", () => {
    const by = new Map<string, string[]>();
    for (const [p, play] of Object.entries(PRIMITIVE_PLAYS)) if (play.clip !== null) by.set(play.clip, [...(by.get(play.clip) ?? []), p]);
    const shared = [...by.values()].filter((ps) => ps.length > 1).map((ps) => [...ps].sort());
    expect(shared.sort()).toEqual(
      [
        ["swap", "swap_any"],
        ["intercept", "redirect_damage"],
        ["extra_reaction", "grant_ap", "grant_skill"],
        ["refund_ap", "refund_cooldown", "reset_cooldown"],
        ["add_stack", "consume_stack", "consume_status"],
        ["summon", "summon_beside"], // TF-1：召喚到身邊暫借召喚的動作
      ]
        .map((g) => [...g].sort())
        .sort(),
    );
  });

  it("shared clips tell members apart with an icon; raise / lower terrain have their own clips", () => {
    expect(new Set(["grant_skill", "grant_ap", "extra_reaction"].map((p) => primitivePlay(p)?.icon)).size).toBe(3);
    expect(new Set(["refund_ap", "refund_cooldown", "reset_cooldown"].map((p) => primitivePlay(p)?.icon)).size).toBe(3);
    expect(primitivePlay("add_stack")?.icon).toBe("+1");
    expect(primitivePlay("consume_stack")?.icon).toBe("-1");
    expect(primitivePlay("raise_terrain")?.clip).not.toBe(primitivePlay("lower_terrain")?.clip);
    // 升降地形特效共用現有的升降補間：片段本身不帶特效
    expect(clipDef(primitivePlay("raise_terrain")!.clip!).fx).toBeUndefined();
    expect(clipDef(primitivePlay("lower_terrain")!.clip!).fx).toBeUndefined();
  });

  it("only refund / stack clips are still (no body motion)", () => {
    const still = Object.entries(PRIMITIVE_PLAYS)
      .filter(([, p]) => p.clip !== null && clipDef(p.clip).still === true)
      .map(([id]) => id)
      .sort();
    expect(still).toEqual(["add_stack", "consume_stack", "consume_status", "refund_ap", "refund_cooldown", "reset_cooldown"]);
  });

  it("lower-half clips are deterministic and recover to the rest pose", () => {
    for (const id of LOWER_HALF) {
      const clip = primitivePlay(id)!.clip!;
      for (const t of [0, 0.3, 0.77, 1]) expect(clipFrame(clip, t), `${id} ${t}`).toEqual(clipFrame(clip, t));
      for (const v of Object.values(recoverFrame(clip, 1).pose)) expect(Math.abs(v as number), id).toBeLessThan(1e-9);
    }
  });

  it("apply_status has a buff and a debuff clip", () => {
    expect(primitivePlay("apply_status", "buff")?.clip).toBe("raise_hand");
    expect(primitivePlay("apply_status", "debuff")?.clip).toBe("point_at");
    expect(primitivePlay("made_up_primitive")).toBeNull();
  });

  it("damage uses the opener strike; damage_multiplier powers up before it", () => {
    expect(primitivePlay("damage")).toEqual({ role: "strike", clip: null });
    expect(primitivePlay("damage_multiplier")?.role).toBe("pre");
    for (const m of ["dash", "charge_through", "leap", "teleport", "shadowstep", "swap"]) expect(primitivePlay(m)?.role, m).toBe("move");
  });
});
