// CB-3c 交付 2：第二種近戰（`melee2`）改看技能本身的射程（玩法 PM；`docs/art/敵人招式動畫需求.md` 第 2 節）。
// 射程、武器、單位一律讀實際的 content/*.yaml 與名詞對照表（不手寫射程數字）。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync, readdirSync } from "node:fs";
import { parse } from "yaml";
import type { BattleView, Pos, SkillCard } from "../api/types";
import type { CreatureAttackType } from "../render/creaturePose";
import { creatureActionOf, isMeleeSkill } from "./creatureAction";
import { meleeWeaponRange } from "./glossary";
import { skillTimeline, type StrikeOf } from "./skillSequence";
import { vfxFor } from "./vfx";

const readText = readFileSync as (url: URL, enc: string) => string;
const readDir = readdirSync as (url: URL) => string[];
const CONTENT = new URL("../../../content/", import.meta.url);

interface Seg {
  skeleton?: string;
  shape: { type: string; range?: number | string };
  effects: Array<{ type: string }>;
}
interface Skill extends Seg {
  id: string;
  skeleton: string;
  followup?: Seg | null;
}
interface Unit {
  id: string;
  weapon: string;
  skills?: string[];
}

const yamlFiles = (dir: string): Array<Record<string, unknown>> =>
  readDir(new URL(`${dir}/`, CONTENT))
    .filter((f) => f.endsWith(".yaml"))
    .sort()
    .map((f) => parse(readText(new URL(`${dir}/${f}`, CONTENT), "utf-8")) as Record<string, unknown>);

const SKILLS = new Map((yamlFiles("skills") as unknown as Skill[]).map((s) => [s.id, s]));
const UNITS = new Map((yamlFiles("units") as unknown as Unit[]).map((u) => [u.id, u]));
const skill = (id: string): Skill => SKILLS.get(id)!;

/** 技能 YAML 的射程 → 前端拿到的樣子（數字；`weapon` → `"weapon"`）。 */
const yamlRange = (s: Seg): number | "weapon" => (s.shape.range === "weapon" ? "weapon" : (s.shape.range as number));

/** 實際技能 YAML → API 的技能卡（同 `skill_cards.card_stats`：跟武器時 `range` 為 null、`range_weapon` 為真）。 */
function cardOf(s: Skill): SkillCard {
  const r = yamlRange(s);
  const seg = (x: Seg) => ({ skeleton: x.skeleton ?? s.skeleton, shape_id: x.shape.type, range: typeof x.shape.range === "number" ? x.shape.range : null, effects: x.effects.map((e) => ({ type: e.type })) });
  return {
    id: s.id,
    shape: "",
    skeleton: s.skeleton,
    effect_ids: s.effects.map((e) => e.type),
    stats: { range: typeof r === "number" ? r : null, range_weapon: r === "weapon" },
    icon: { segments: [seg(s), ...(s.followup == null ? [] : [seg(s.followup)])] },
  } as unknown as SkillCard;
}

const at = (x: number, y: number): Pos => ({ x, y });

/** 走真的時間軸：單位（實際的武器）對距離 `dist` 的目標放 `skillId`（null ＝ 普攻）→ 挑到的動作類型。 */
function play(unitId: string, skillId: string | null, dist: number, weapon?: string): CreatureAttackType | null {
  const u = UNITS.get(unitId)!;
  if (skillId !== null) expect(u.skills, unitId).toContain(skillId);
  const target = at(2, 2);
  const view = {
    map_id: "m",
    units: [
      { id: "c", pos: at(2 + dist, 2), team: "enemy", weapon_id: weapon ?? u.weapon },
      { id: "t", pos: target, team: "ally", weapon_id: "fist" },
    ],
    tiles: [],
  } as unknown as BattleView;
  const s = skillId === null ? null : skill(skillId);
  const events =
    s === null
      ? [{ seq: 1, round: 1, type: "attack_rolled", attacker_id: "c", target_id: "t", hit: true }]
      : [{ seq: 1, round: 1, type: "skill_used", unit_id: "c", skill_id: s.id, name_zh: "x", ap: 1, mana: 0, mana_after: 0, tiles: [target] }];
  let action: CreatureAttackType | null = null;
  const strikeOf: StrikeOf = (_, a) => {
    action = a;
    return { ms: 800, hitAt: 0.5 };
  };
  const cards = s === null ? {} : { [s.id]: cardOf(s) };
  skillTimeline(events, view, cards, vfxFor(events, view, cards), () => "bare", () => null, strikeOf);
  return action;
}

describe("CB-3c 第二種近戰看技能本身的射程", () => {
  it("近戰武器的射程讀名詞對照表（weapons.yaml）", () => {
    expect(meleeWeaponRange("fangs")).toBe(1);
    expect(meleeWeaponRange("spear")).toBe(2);
    expect(meleeWeaponRange("whip")).toBe(2);
    expect(meleeWeaponRange("lightning_staff")).toBeNull(); // 法器不是近戰武器
    expect(meleeWeaponRange("short_bow" as string)).toBeUndefined(); // 對照表沒有 → 不知道
  });

  // (技能, 施放者武器, 與目標距離) → 動作類型；射程與武器射程都來自實際資料
  const TABLE: ReadonlyArray<readonly [string, string, string, number, CreatureAttackType]> = [
    ["射程 1 相鄰", "skill_rx_point_blank", "fangs", 1, "melee2"],
    ["跟武器（fangs 射程 1）相鄰", "skill_venom_gore", "fangs", 1, "melee2"],
    ["射程 2 ＝ 近戰武器射程（spear 2）相鄰", "skill_static_palm", "spear", 1, "melee2"],
    ["射程 2 ＝ 近戰武器射程（spear 2）隔一格", "skill_static_palm", "spear", 2, "melee2"],
    ["射程 2 ≠ 近戰武器射程（fangs 1）貼身", "skill_static_palm", "fangs", 1, "cast"],
    ["射程 3 的法術貼身放", "skill_quake_topple", "talons", 1, "cast"],
    ["射程 6 的晶蝕貼身放（法器）", "skill_shard_erosion", "lightning_staff", 1, "cast"],
    ["射程 6 的晶蝕隔著距離放", "skill_shard_erosion", "lightning_staff", 3, "cast"],
  ];
  it.each(TABLE)("%s → creatureActionOf", (_label, skillId, weapon, dist, want) => {
    const s = skill(skillId);
    const range = yamlRange(s);
    const weaponRange = meleeWeaponRange(weapon);
    expect(creatureActionOf({ basic: false, skillId, primitives: ["damage"], shape: s.shape.type, strikeClip: "thrust", dist, range, ...(weaponRange === undefined ? {} : { weaponRange }) })).toBe(want);
  });

  it("isMeleeSkill：射程 1、跟武器（近戰武器）、等於近戰武器射程才算；不知道射程 → null", () => {
    expect(isMeleeSkill(1, null)).toBe(true);
    expect(isMeleeSkill("weapon", 1)).toBe(true);
    expect(isMeleeSkill("weapon", null)).toBe(false); // 遠程武器、法器跟武器的招不是近戰
    expect(isMeleeSkill(2, 2)).toBe(true);
    expect(isMeleeSkill(2, 1)).toBe(false);
    expect(isMeleeSkill(3, null)).toBe(false);
    expect(isMeleeSkill(null, 1)).toBeNull();
    expect(isMeleeSkill("weapon", undefined)).toBeNull();
  });

  it("實際的敵人走整條時間軸：晶蝕、火花連鎖、震地掀翻貼身放＝施法；單體近戰技能＝第二種", () => {
    expect(play("rift_shard_lord", "skill_shard_erosion", 1)).toBe("cast");
    expect(play("rift_shard_lord", "skill_spark_chain", 1)).toBe("cast");
    expect(play("stoneback_bear", "skill_quake_topple", 1)).toBe("cast");
    expect(play("stoneback_bear", "skill_bone_crusher", 1)).toBe("melee2");
    expect(play("sulfur_beast", "skill_venom_gore", 1)).toBe("melee2");
    expect(play("ember_lizard", "skill_ember_bite", 1)).toBe("melee2");
  });

  it("普攻一律第一種（melee），不管武器與射程", () => {
    for (const id of ["sulfur_beast", "stoneback_bear", "ember_lizard", "mist_wolf"]) expect(play(id, null, 1), id).toBe("melee");
    for (const [range, weaponRange] of [[1, 1], ["weapon", 2], [6, null]] as const)
      expect(creatureActionOf({ basic: true, skillId: null, primitives: ["damage"], shape: "single", strikeClip: "thrust", dist: 1, range, weaponRange })).toBe("melee");
  });
});
