// CB-2b：異形招式動畫挑選的表格測試。技能與單位資料一律讀實際的 content/*.yaml（不手寫假原語）。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync, readdirSync } from "node:fs";
import { parse } from "yaml";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { creatureAttackTypeOf, creaturePoseKey, quantizeCreaturePose, type CreatureAttackType } from "../render/creaturePose";
import { rigKey } from "../render/inkCreature";
import { attackClipFor, creatureClipInfo } from "../render/qCreatureAnim";
import { CREATURE_CHARGE_SKILLS, creatureActionOf } from "./creatureAction";
import { moveAnimOf } from "./animation";
import { placeMotions, skillTimeline, type StrikeOf } from "./skillSequence";
import { vfxFor } from "./vfx";

const readText = readFileSync as (url: URL, enc: string) => string;
const readDir = readdirSync as (url: URL) => string[];
const CONTENT = new URL("../../../content/", import.meta.url);

interface Effect {
  type: string;
}
interface Seg {
  shape: { type: string; range?: number | string };
  effects: Effect[];
}
interface Skill extends Seg {
  id: string;
  skeleton: string;
  followup?: Seg | null;
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
const skill = (id: string): Skill => SKILLS.get(id)!;
const unit = (id: string): Unit => UNITS.find((u) => u.id === id)!;
const keyOf = (u: Unit): string => rigKey({ body: u.doll!.creature!.body, variant: u.doll!.creature!.variant ?? "" } as Parameters<typeof rigKey>[0]);

const rangeOf = (s: Seg): number => (typeof s.shape.range === "number" ? s.shape.range : 1);

/** 實際技能 YAML → 前端拿到的技能卡（`icon.segments`，同 API 的 skill_card）。 */
function cardOf(s: Skill): SkillCard {
  const seg = (x: Seg) => ({ skeleton: s.skeleton, shape_id: x.shape.type, range: rangeOf(x), effects: x.effects.map((e) => ({ type: e.type })) });
  return { id: s.id, shape: "", skeleton: s.skeleton, effect_ids: s.effects.map((e) => e.type), icon: { segments: [seg(s), ...(s.followup == null ? [] : [seg(s.followup)])] } } as unknown as SkillCard;
}

const at = (x: number, y: number): Pos => ({ x, y });

function viewOf(casterAt: Pos, targetAt: Pos): BattleView {
  return { map_id: "m", units: [{ id: "c", pos: casterAt, team: "enemy" }, { id: "t", pos: targetAt, team: "ally" }], tiles: [] } as unknown as BattleView;
}

/** 走真的時間軸：`skill_used`＋（可選）位移事件 → 挑到的動作類型（`strikeOf` 收到的）與列。 */
function play(s: Skill, dist: number, more: Record<string, unknown>[] = [], end: Pos = at(2 + dist, 2)) {
  const target = at(2, 2);
  const view = viewOf(end, target);
  const events = [{ seq: 1, round: 1, type: "skill_used", unit_id: "c", skill_id: s.id, name_zh: "x", ap: 1, mana: 0, mana_after: 0, tiles: [target] }, ...more];
  let action: CreatureAttackType | null = null;
  const strikeOf: StrikeOf = (_, a) => {
    action = a;
    return { ms: 800, hitAt: 0.5, ...(a === "blink" ? { blink: true } : {}) };
  };
  const cards = { [s.id]: cardOf(s) };
  const tl = skillTimeline(events, view, cards, vfxFor(events, view, cards), () => "bare", () => null, strikeOf)!;
  return { action: action as CreatureAttackType | null, tl, view };
}

// 美術 PM 第 1 節的六層，全部用實際的敵人與技能
const TABLE: ReadonlyArray<readonly [string, string, number, string, string]> = [
  ["furnace_matriarch", "skill_summon_ember_whelp", 2, "summon", "atk:summon"], // 1 召喚：蜥蜴產卵
  ["mist_wraith", "skill_blink", 3, "blink", "atk:blink"], // 2 位移：魅閃現
  ["molten_wraith", "skill_blink", 3, "blink", "atk:blink"],
  ["mountain_leopard", "skill_tiger_charge", 1, "charge", "atk:pounce"], // 3 衝鋒原語：山豹撲擊
  // 4 錐形：噴岩龜原本帶火牆，RG-1（#162）換成瞄準預告的熔岩彈，錐形改由下面的硫煙獸涵蓋
  ["sulfur_beast", "skill_sulfur_breath", 1, "breath", "atk:breath"], // 4 錐形：硫煙獸貼身不再退回獠牙撞
  ["sulfur_beast", "skill_sulfur_breath", 3, "breath", "atk:breath"],
  ["lava_beetle", "skill_battering_ram", 1, "charge", "atk:ram"], // 5 指定招：甲蟲破城衝撞
  ["molten_lord", "skill_battering_ram", 1, "charge", "atk:ram"],
  ["thunder_hawk", "skill_plunging_strike", 1, "charge", "atk:dive"], // 5 指定招：鷹俯衝斬
  ["thunder_hawk", "skill_static_palm", 2, "cast", "atk:cast"], // 6 其他：距離 2 以上＝遠程
  ["magma_slug", "skill_oil_flask", 3, "cast", "atk:spit"],
  // 6 其他：相鄰的單體技能＝第二種近戰（CB-3；改前暫時共用普攻片段 atk:bite）
  ["mist_wolf", "skill_twin_fang", 1, "melee2", "atk:maul"],
  ["ember_lizard", "skill_ember_bite", 1, "melee2", "atk:tailover"],
  ["shard_golem", "skill_rock_smash", 1, "melee2", "atk:smash"], // 沒有第二種近戰的身形退回第一種
];

describe("CB-2b 異形招式動畫挑選", () => {
  it.each(TABLE)("%s %s（距離 %i）→ %s → %s", (unitId, skillId, dist, action, clip) => {
    const u = unit(unitId);
    expect(u.skills).toContain(skillId);
    const r = play(skill(skillId), dist);
    expect(r.action).toBe(action);
    expect(attackClipFor(keyOf(u), r.action!)).toBe(clip);
  });

  it("每一個實際的技能 YAML（含後段）都照順序：summon → 位移 → 衝鋒 → 錐形 → 指定招", () => {
    let n = 0;
    for (const s of SKILLS.values())
      for (const seg of [s, ...(s.followup == null ? [] : [s.followup])]) {
        const primitives = seg.effects.map((e) => e.type);
        const has = (...ids: string[]) => primitives.some((p) => ids.includes(p));
        const want = has("summon") ? "summon" : has("teleport", "shadowstep", "swap", "swap_any") ? "blink" : has("dash", "charge_through", "leap") ? "charge" : seg.shape.type === "cone" ? "breath" : CREATURE_CHARGE_SKILLS.has(s.id) ? "charge" : null;
        for (const dist of [0, 1, 3]) {
          const got = creatureActionOf({ basic: false, skillId: s.id, primitives, shape: seg.shape.type, strikeClip: "thrust", dist });
          // CB-3：其餘的照現行，只有「相鄰＋形狀 single」從普攻片段改成第二種近戰
          const rest = dist === 1 && seg.shape.type === "single" ? "melee2" : creatureAttackTypeOf("thrust", dist);
          expect(got, `${s.id} dist ${dist}`).toBe(want ?? rest);
        }
        n += 1;
      }
    expect(n).toBeGreaterThan(100);
  });

  it("現有異形的招：不屬於前五層的，和改前（`creatureAttackTypeOf`）一樣（CB-3：只有相鄰的單體近戰改成第二種近戰）；普攻不看原語", () => {
    let kept = 0;
    for (const u of UNITS)
      for (const id of u.skills ?? []) {
        const s = skill(id);
        const primitives = s.effects.map((e) => e.type);
        const special = primitives.some((p) => ["summon", "teleport", "shadowstep", "swap", "swap_any", "dash", "charge_through", "leap"].includes(p)) || s.shape.type === "cone" || CREATURE_CHARGE_SKILLS.has(id);
        if (special) continue;
        for (const [clip, dist] of [["thrust", 1], ["cast_ball", 3], ["stab_ground", 2], ["thrust", 0]] as const) {
          const before = creatureAttackTypeOf(clip, dist);
          expect(creatureActionOf({ basic: false, skillId: id, primitives, shape: s.shape.type, strikeClip: clip, dist }), id).toBe(before === "melee" && dist === 1 && s.shape.type === "single" ? "melee2" : before);
        }
        kept += 1;
      }
    expect(kept).toBeGreaterThan(5);
    // 普攻：卡上就算寫衝鋒也照現行（相鄰＝普攻片段、遠程＝cast）
    expect(creatureActionOf({ basic: true, skillId: null, primitives: ["dash"], shape: "cone", strikeClip: "thrust", dist: 1 })).toBe("melee");
    expect(creatureActionOf({ basic: true, skillId: null, primitives: ["damage"], shape: "single", strikeClip: "thrust", dist: 3 })).toBe("cast");
  });

  it("沒有吐息、召喚片段的身形照 attackClipFor 退回（不用改）", () => {
    expect(attackClipFor("hound", "breath")).toBe(attackClipFor("hound", "cast"));
    expect(creatureClipInfo("wraith", attackClipFor("wraith", "blink")!)?.type).toBe("blink");
    expect(creatureClipInfo("hound", attackClipFor("hound", "blink")!)?.type).not.toBe("blink");
  });

  it("山豹撲擊：有 dash 位移時整隻前衝歸零（不和引擎位移疊加），位移排在出招前", () => {
    const moved = [{ seq: 2, round: 1, type: "unit_dashed", unit_id: "c", target_id: "t", path: [at(6, 2), at(3, 2)] }, { seq: 3, round: 1, type: "unit_moved", unit_id: "c", from_pos: at(6, 2), to_pos: at(3, 2), mode: "dash", cost: 0 }];
    const { tl, view } = play(skill("skill_tiger_charge"), 1, moved);
    expect(tl.rows.find((r) => r.strike)!.creature).toEqual({ action: "charge", inPlace: true });
    const m = moveAnimOf(moved[1] as never);
    expect(placeMotions([{ kind: "move", anim: m }], tl.segments, view).before).toHaveLength(1);
    // 相鄰不用衝：片段自己的前衝照播
    expect(play(skill("skill_tiger_charge"), 1).tl.rows.find((r) => r.strike)!.creature).toEqual({ action: "charge" });
  });

  it("甲蟲衝撞：不移動的招，片段自己前衝再回原位；被撞者在命中點之後才推開", () => {
    const forced = [{ seq: 2, round: 1, type: "unit_moved", unit_id: "t", from_pos: at(2, 2), to_pos: at(0, 2), mode: "forced", cost: 0 }];
    const { tl, view } = play(skill("skill_battering_ram"), 1, forced, at(3, 2));
    const row = tl.rows.find((r) => r.strike)!;
    expect(row.creature).toEqual({ action: "charge" });
    const placed = placeMotions([{ kind: "move", anim: moveAnimOf(forced[0] as never) }], tl.segments, view);
    expect(placed.before).toHaveLength(0);
    expect(placed.after).toHaveLength(1);
    expect(tl.vfx.casts[0]!.impactMs).toBeCloseTo(row.hitMs!, 6);
  });

  it("魅閃現：閃現片段播在傳送上（長度＝片段、照速度縮放），出招列不再原地多閃一次", () => {
    const moved = [{ seq: 2, round: 1, type: "unit_moved", unit_id: "c", from_pos: at(6, 2), to_pos: at(3, 2), mode: "teleport", cost: 0 }];
    const { tl, view } = play(skill("skill_blink"), 1, moved);
    expect(tl.rows.some((r) => r.strike)).toBe(false);
    const m = moveAnimOf(moved[0] as never, 0.5);
    const placed = placeMotions([{ kind: "move", anim: m }], tl.segments, view, 0.5);
    expect(placed.before).toHaveLength(1);
    const a = placed.before[0]! as { kind: "move"; anim: typeof m };
    expect(a.anim.creatureBlink).toBe(true);
    expect(a.anim.durationMs).toBe(400);
    // 沒傳送到（事件裡沒有 unit_moved）時出招列照播，不會整段消失
    expect(play(skill("skill_blink"), 1).tl.rows.some((r) => r.strike)).toBe(true);
  });

  it("蜥蜴產卵：幼蜥在出手格之後才進畫面（召喚事件的時間＝片段出手格）", () => {
    const { tl } = play(skill("skill_summon_ember_whelp"), 2);
    const row = tl.rows.find((r) => r.strike)!;
    expect(row.creature).toEqual({ action: "summon" });
    expect(tl.vfx.leadMs).toBeGreaterThanOrEqual(row.hitMs! - 1);
  });

  it("inPlace 進貼圖快取鍵（量化後保留），避免共用到會前衝的那一張", () => {
    const p = { clip: "atk:@charge", u: 0.5, inPlace: true };
    expect(quantizeCreaturePose(p).inPlace).toBe(true);
    expect(creaturePoseKey(p)).not.toBe(creaturePoseKey({ clip: "atk:@charge", u: 0.5 }));
  });
});
