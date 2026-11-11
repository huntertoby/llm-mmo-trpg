// CB-3：異形第二種近戰片段（docs/art/異形第二種近戰移植需求.md）：片段長度、格數、命中時間的資料測試；挑法；減少動態。
// 技能與單位資料讀實際的 content/*.yaml。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync, readdirSync } from "node:fs";
import { parse } from "yaml";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { creatureStrikePose } from "../render/creaturePose";
import { rigKey } from "../render/inkCreature";
import { BODY_ANIM, attackClipFor, creatureAttackHitU, creatureClipInfo, creatureFrameU, creatureOwnFrames, ownFrameU, qCreaturePartPose, type AnimSubject } from "../render/qCreatureAnim";
import { bossAttackClip } from "../render/qBoss";
import { creatureActionOf } from "./creatureAction";
import { skillTimeline, type StrikeOf } from "./skillSequence";
import { vfxFor } from "./vfx";

const readText = readFileSync as (url: URL, enc: string) => string;
const readDir = readdirSync as (url: URL) => string[];
const CONTENT = new URL("../../../content/", import.meta.url);
interface Seg {
  shape: { type: string; range?: number | string };
  effects: Array<{ type: string }>;
}
interface Skill extends Seg {
  id: string;
  skeleton: string;
}
interface Unit {
  id: string;
  skills?: string[];
  doll?: { creature?: { body: string; variant?: string } };
}
const yamlFiles = (dir: string): Array<Record<string, unknown>> =>
  readDir(new URL(`${dir}/`, CONTENT))
    .filter((f) => f.endsWith(".yaml"))
    .sort()
    .map((f) => parse(readText(new URL(`${dir}/${f}`, CONTENT), "utf-8")) as Record<string, unknown>);
const SKILLS = new Map((yamlFiles("skills") as unknown as Skill[]).map((s) => [s.id, s]));
const UNITS = (yamlFiles("units") as unknown as Unit[]).filter((u) => u.doll?.creature != null);
const unit = (id: string): Unit => UNITS.find((u) => u.id === id)!;
const keyOf = (u: Unit): string => rigKey({ body: u.doll!.creature!.body, variant: u.doll!.creature!.variant ?? "" } as Parameters<typeof rigKey>[0]);
const subject = (key: string, traits: string[] = []): AnimSubject => ({ key, element: undefined, mat: "fur", base: "#888888", accent: null, traits });
const F = 1000 / 12;

/** 移植需求第 1 節的表：身形、片段、毫秒、格數、命中格（命中時間＝格 × 83.33）。 */
const TABLE: ReadonlyArray<readonly [string, string, number, number, number, number]> = [
  ["hound", "atk:maul", 1100, 13, 4, 333],
  ["feline", "atk:upcut", 1000, 12, 6, 500],
  ["bear", "atk:slam", 1100, 13, 7, 583],
  ["boar", "atk:uptusk", 1000, 12, 5, 417],
  ["lizard", "atk:tailover", 1250, 15, 6, 500],
];

describe("CB-3 第二種近戰片段：長度、格數、命中時間（照移植需求第 1 節的表）", () => {
  it.each(TABLE)("%s %s：%i ms／%i 格，命中格 %i（t=%i）", (key, clip, ms, n, hitF, hitMs) => {
    const info = creatureClipInfo(key, clip)!;
    expect(info.ms).toBe(ms);
    expect(info.n).toBe(n);
    expect(info.type).toBe("melee2");
    expect(creatureOwnFrames(key, clip)).toEqual({ n, ms, hitF });
    expect(Math.round(hitF * F)).toBe(hitMs);
    // 命中時間（對齊傷害數字與受擊反應）＝命中格開始的那一刻
    expect(creatureAttackHitU(key, clip) * ms).toBeCloseTo(hitF * F, 6);
    expect(attackClipFor(key, "melee2")).toBe(clip);
  });

  it.each(TABLE)("%s %s：戰場照自己的格數播，第 f 格從 f × 83.33 ms 起（格邊界不取到前一格），最後一格停到片段結束", (key, clip, ms, n) => {
    const own = creatureOwnFrames(key, clip)!;
    for (let f = 0; f < n; f++) {
      expect(ownFrameU(own, (f * F) / ms), `f=${f}`).toBeCloseTo(f / (n - 1), 9);
      expect(ownFrameU(own, (f * F + 80) / ms), `f=${f} 後段`).toBeCloseTo(f / (n - 1), 9);
      expect(creatureStrikePose("melee2", (f * F) / ms, own).u, `strike f=${f}`).toBeCloseTo(f / (n - 1), 9);
      expect(creatureFrameU(key, clip, f * F), `frameU f=${f}`).toBeCloseTo(f / (n - 1), 9);
    }
    expect(ownFrameU(own, 1)).toBe(1);
    expect(creatureStrikePose("melee2", 1, own)).toEqual({ clip: "atk:@melee2", u: 1 });
  });

  it("首格與末格是站姿（整隻沒有位移、旋轉），每格數值有限、同一格兩次相同", () => {
    for (const [key, clip, , n] of TABLE)
      for (let f = 0; f < n; f++) {
        const u = f / (n - 1);
        const p = qCreaturePartPose(subject(key), clip, u)!;
        expect(qCreaturePartPose(subject(key), clip, u)).toEqual(p);
        for (const xf of [p.root, ...Object.values(p.parts)]) for (const [k, v] of Object.entries(xf)) if (k !== "pivot") expect(Number.isFinite(v as number), `${clip} f=${f} ${k}`).toBe(true);
        if (f === 0 || f === n - 1) {
          expect(Math.abs(p.root.dx ?? 0), `${clip} f=${f}`).toBeLessThan(0.01);
          expect(Math.abs(Math.sin(p.root.rot ?? 0)), `${clip} f=${f}`).toBeLessThan(0.01);
          expect(p.fx).toEqual([]);
        }
      }
  });

  it("犬狼撲咬拉扯：咬合圖示在 333～750（第 4～9 格），星爆只在命中格 333；417、583、750 是往後拉（只是畫面）", () => {
    const at = (f: number) => qCreaturePartPose(subject("hound"), "atk:maul", f / 12)!;
    for (let f = 0; f <= 12; f++) expect(at(f).fx.some((x) => x.k === "chomp"), `f=${f}`).toBe(f >= 4 && f <= 9);
    for (let f = 0; f <= 12; f++) expect(at(f).fx.some((x) => x.k === "burst"), `f=${f}`).toBe(f === 4);
    for (const f of [5, 7, 9]) expect(at(f).root.dx!).toBeLessThan(at(f - 1).root.dx!); // 往後坐
    for (const f of [5, 7, 9]) expect(at(f).fx.find((x) => x.k === "chomp")!.q).toBe(1); // 咬緊
  });

  it("熊的乳白三爪只在 atk:slam：83 起伸出、750 縮一半、833 起不畫；其他片段沒有", () => {
    const cw = (f: number) => qCreaturePartPose(subject("bear"), "atk:slam", f / 12)!.claws ?? 0;
    expect([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(cw)).toEqual([0, 0.4, 0.75, 1, 1, 1, 1, 1, 1, 0.5, 0, 0, 0]);
    for (const clip of ["idle", "move", "atk:swipe", "atk:quake", "hit", "death"]) for (const u of [0, 0.25, 0.5, 0.75, 1]) expect(qCreaturePartPose(subject("bear"), clip, u)!.claws).toBeUndefined();
    // 人立時背上石板往身體壓：只有帶 stone_back 的外觀才切身體
    expect(qCreaturePartPose(subject("bear", ["stone_back"]), "atk:slam", 4 / 12)!.split?.["body"]).toHaveLength(2);
    expect(qCreaturePartPose(subject("bear"), "atk:slam", 4 / 12)!.split).toBeUndefined();
  });

  it("蜥蜴掄尾砸擊：尾巴切 5 段、尾根那段不動（尾根每格在臀部）；星爆只在命中格 500", () => {
    for (let f = 0; f < 15; f++) {
      const p = qCreaturePartPose(subject("lizard"), "atk:tailover", f / 14)!;
      const tail = p.split?.["tail"];
      if (f === 0 || f === 14) expect(tail).toBeUndefined();
      else {
        expect(tail, `f=${f}`).toHaveLength(5);
        expect(tail![0]).toEqual({ clip: tail![0]!.clip });
      }
      expect(p.fx.some((x) => x.k === "burst"), `f=${f}`).toBe(f === 6);
    }
  });
});

const at = (x: number, y: number): Pos => ({ x, y });
const cardOf = (s: Skill): SkillCard =>
  ({ id: s.id, shape: "", skeleton: s.skeleton, effect_ids: s.effects.map((e) => e.type), icon: { segments: [{ skeleton: s.skeleton, shape_id: s.shape.type, range: typeof s.shape.range === "number" ? s.shape.range : 1, effects: s.effects.map((e) => ({ type: e.type })) }] } }) as unknown as SkillCard;
/** 走真的時間軸：回傳挑到的動作類型與出招列。`skillId` 為 null＝普攻（attack_rolled）。 */
function play(unitId: string, skillId: string | null, dist: number) {
  const key = keyOf(unit(unitId));
  const target = at(2, 2);
  const view = { map_id: "m", units: [{ id: "c", pos: at(2 + dist, 2), team: "enemy" }, { id: "t", pos: target, team: "ally" }], tiles: [] } as unknown as BattleView;
  const s = skillId === null ? null : SKILLS.get(skillId)!;
  if (s !== null) expect(unit(unitId).skills).toContain(skillId);
  const events =
    s === null
      ? [{ seq: 1, round: 1, type: "attack_rolled", attacker_id: "c", target_id: "t", hit: true }, { seq: 2, round: 1, type: "damage_dealt", target_id: "t", source_id: "c", element: "physical", amount: 3, hp_before: 30, hp_after: 27, crit: false, block_permille: 1000 }]
      : [{ seq: 1, round: 1, type: "skill_used", unit_id: "c", skill_id: s.id, name_zh: "x", ap: 1, mana: 0, mana_after: 0, tiles: [target] }];
  let action: string | null = null;
  const strikeOf: StrikeOf = (_, a) => {
    action = a;
    const clip = attackClipFor(key, a)!;
    const info = creatureClipInfo(key, clip)!;
    const own = creatureOwnFrames(key, clip);
    return { ms: info.ms, hitAt: creatureAttackHitU(key, clip), ...(own === null ? {} : { frames: { n: own.n, ms: own.ms } }) };
  };
  const cards = s === null ? {} : { [s.id]: cardOf(s) };
  const tl = skillTimeline(events, view, cards, vfxFor(events, view, cards), () => "bare", () => null, strikeOf)!;
  const act = action as string | null;
  return { action: act, clip: act === null ? null : attackClipFor(key, act as never), row: tl.rows.find((r) => r.strike)!, tl };
}

describe("CB-3 挑法：普攻播第一種、單體近戰技能播第二種（只影響畫面）", () => {
  it("普攻 → 第一種片段（五款）", () => {
    const first: ReadonlyArray<readonly [string, string]> = [["mist_wolf", "atk:bite"], ["mountain_leopard", "atk:claw"], ["stoneback_bear", "atk:swipe"], ["sulfur_beast", "atk:gore"], ["ember_lizard", "atk:bite"]];
    for (const [id, clip] of first) {
      const r = play(id, null, 1);
      expect(r.action, id).toBe("melee");
      expect(r.clip, id).toBe(clip);
      expect(r.row.creature, id).toEqual({ action: "melee" }); // 照舊量化成 12 格
    }
  });

  it("單體近戰技能 → 第二種片段（五款），命中點＝表上的命中時間、片段照自己的格數", () => {
    const second: ReadonlyArray<readonly [string, string, string, number, number, number]> = [
      ["mist_wolf", "skill_twin_fang", "atk:maul", 1100, 13, 4],
      ["mountain_leopard", "skill_rending_strike", "atk:upcut", 1000, 12, 6],
      ["stoneback_bear", "skill_bone_crusher", "atk:slam", 1100, 13, 7],
      ["sulfur_beast", "skill_venom_gore", "atk:uptusk", 1000, 12, 5],
      ["ember_lizard", "skill_ember_bite", "atk:tailover", 1250, 15, 6],
    ];
    for (const [id, skillId, clip, ms, n, hitF] of second) {
      const r = play(id, skillId, 1);
      expect(r.action, id).toBe("melee2");
      expect(r.clip, id).toBe(clip);
      expect(r.row.ms, id).toBe(ms);
      expect(r.row.hitMs! - r.row.startMs, id).toBeCloseTo(hitF * F, 6);
      expect(r.row.creature, id).toEqual({ action: "melee2", frames: { n, ms } });
      // 特效與扣血對齊同一個命中點
      expect(r.tl.vfx.casts[0]!.impactMs, id).toBeCloseTo(r.row.hitMs!, 6);
    }
  });

  it("同一隻的兩招單體近戰技能共用第二種", () => {
    expect(play("mist_wolf", "skill_twin_fang", 1).clip).toBe("atk:maul");
    expect(play("mist_wolf", "skill_pincer_strike", 1).clip).toBe("atk:maul");
  });

  it("範圍技能、遠程技能、衝鋒不播第二種", () => {
    const area = play("sulfur_beast", "skill_sulfur_breath", 1); // 錐形（範圍）→ 吐息
    expect([area.action, area.clip]).toEqual(["breath", "atk:breath"]);
    const ranged = play("ash_hound", "skill_kindle_pop", 3); // 距離 3 的單體 → 遠程
    expect([ranged.action, ranged.clip]).toEqual(["cast", "atk:cast"]);
    const charge = play("mountain_leopard", "skill_tiger_charge", 1); // 有 dash → 衝鋒
    expect([charge.action, charge.clip]).toEqual(["charge", "atk:pounce"]);
    // 自身、地面的範圍招（距離 0）、相鄰但形狀不是 single 的照現行
    expect(creatureActionOf({ basic: false, skillId: "x", primitives: ["damage"], shape: "self", strikeClip: "thrust", dist: 0 })).toBe("area");
    expect(creatureActionOf({ basic: false, skillId: "x", primitives: ["damage"], shape: "line", strikeClip: "thrust", dist: 1 })).toBe("melee");
    expect(creatureActionOf({ basic: false, skillId: "x", primitives: ["damage"], shape: "single", strikeClip: "stomp", dist: 1 })).toBe("area");
  });

  it("挑法是純函式（不用亂數）：同樣的輸入每次同一個片段；沒有第二種的身形與頭目退回第一種", () => {
    const input = { basic: false, skillId: "skill_ember_bite", primitives: ["damage", "apply_status"], shape: "single", strikeClip: "thrust", dist: 1 } as const;
    const got = Array.from({ length: 20 }, () => creatureActionOf(input));
    expect(new Set(got)).toEqual(new Set(["melee2"]));
    expect(creatureActionOf({ ...input, basic: true, skillId: null })).toBe("melee");
    for (const key of Object.keys(BODY_ANIM)) {
      const has = Object.values(BODY_ANIM[key]!.attacks).some((a) => a.type === "melee2");
      if (!has) expect(attackClipFor(key, "melee2"), key).toBe(attackClipFor(key, "melee"));
      else expect(attackClipFor(key, "melee"), key).not.toBe(attackClipFor(key, "melee2")); // 普攻仍是第一種
    }
    expect(Object.keys(BODY_ANIM).filter((k) => Object.values(BODY_ANIM[k]!.attacks).some((a) => a.type === "melee2")).sort()).toEqual(["bear", "boar", "feline", "hound", "lizard"]);
    for (const phase of [1, 2]) for (const id of ["ah", "sl"] as const) expect(bossAttackClip(id, "melee2", phase)).toBe(bossAttackClip(id, "melee", phase));
  });
});

describe("CB-3 減少動態：第二種近戰照既有規則（身體站著只往前推 2，特效照放）", () => {
  it.each(TABLE)("%s %s", (key, clip, _ms, n, hitF) => {
    for (let f = 0; f < n; f++) {
      const u = f / (n - 1);
      const p = qCreaturePartPose(subject(key, ["stone_back"]), clip, u, true)!;
      expect(Object.keys(p.parts)).toEqual([]);
      expect(p.split).toBeUndefined();
      expect(p.claws).toBeUndefined();
      expect(Math.abs(p.root.dx ?? 0)).toBeLessThanOrEqual(2);
      expect(p.root.rot ?? 0).toBe(0);
      expect(p.fx).toEqual(qCreaturePartPose(subject(key, ["stone_back"]), clip, u)!.fx);
    }
    expect(qCreaturePartPose(subject(key), clip, hitF / (n - 1), true)!.fx.length).toBeGreaterThan(0);
  });
});
