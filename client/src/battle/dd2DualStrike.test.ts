// DD-2（#153）：雙匕首單體武器技的前端——預覽標「打 2 下」、出招播兩次打擊（照普攻雙匕首：每個 attack_rolled 一段）。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, PreviewOut, SkillCard } from "../api/types";
import { previewLines, strikeLines } from "./previewText";
import { noteStrike, repeatsStrike } from "./repeatStrike";
import { skillTimeline } from "./skillSequence";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";
import { vfxFor } from "./vfx";

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const GUARD = "u_guard";
const at = (x: number, y: number): Pos => ({ x, y });

function view(units: Record<string, Pos>): BattleView {
  return { map_id: "m", units: Object.entries(units).map(([id, pos]) => ({ id, pos, team: id === HERO ? "player" : "enemy" })) } as unknown as BattleView;
}

const STAB: SkillCard = { id: "skill_stab", shape: "單體（射程 1）", skeleton: "strike" } as unknown as SkillCard;
const SWEEP: SkillCard = { id: "skill_sweep", shape: "十字（射程 0）", skeleton: "strike" } as unknown as SkillCard;
const cards = { skill_stab: STAB, skill_sweep: SWEEP };

let seq = 0;
const ev = (type: string, fields: Record<string, unknown>) => ({ seq: ++seq, round: 1, type, ...fields });
const used = (skill: string, tiles: Pos[]) => ev("skill_used", { unit_id: HERO, skill_id: skill, tiles });
const rolled = (target: string, hit = true, skill = "skill_stab") => ev("attack_rolled", { attacker_id: HERO, target_id: target, hit, crit: false, skill_id: skill });
const dealt = (target: string, amount = 4) => ev("damage_dealt", { source_id: HERO, target_id: target, amount, element: "physical", crit: false });

const field = view({ [HERO]: at(2, 2), [FOE]: at(3, 2), [FOE2]: at(2, 3), [GUARD]: at(3, 3) });
const timeline = (events: Record<string, unknown>[]) => skillTimeline(events, field, cards, vfxFor(events, field, cards), () => "blade", () => "pair");

describe("DD-2 出招：第二下照普攻另開一段", () => {
  it("兩下都中：兩段（技能段＋普攻段），第二下的打擊在第一下之後", () => {
    const events = [used("skill_stab", [at(3, 2)]), rolled(FOE), dealt(FOE), rolled(FOE), dealt(FOE)];
    const vfx = vfxFor(events, field, cards);
    expect(vfx.casts).toHaveLength(2);
    expect(vfx.casts[0]!.charge).toBe(true); // 技能段
    expect(vfx.casts[1]!.charge).toBe(false); // 普攻段（同普攻：沒有蓄力）
    expect(vfx.casts[1]!.impactMs).toBeGreaterThan(vfx.casts[0]!.impactMs);
    const tl = timeline(events)!;
    expect(tl.segments.map((s) => [s.skillId, s.basic])).toEqual([
      ["skill_stab", false],
      [null, true],
    ]);
    expect(tl.segments[1]!.seq).toBe(events[3]!.seq); // 普攻變體照第二個 attack_rolled 的 seq 挑（同普攻）
  });

  it("第二下沒中也是兩段（閃避算在第二段）", () => {
    const events = [used("skill_stab", [at(3, 2)]), rolled(FOE), dealt(FOE), rolled(FOE, false)];
    const vfx = vfxFor(events, field, cards);
    expect(vfx.casts).toHaveLength(2);
    expect((vfx.reactions ?? []).find((r) => r.kind === "dodge")?.cast).toBe(1);
  });

  it("第一下打倒：引擎不打第二下，只播一下", () => {
    const events = [used("skill_stab", [at(3, 2)]), rolled(FOE), dealt(FOE, 30), ev("unit_downed", { unit_id: FOE })];
    expect(vfxFor(events, field, cards).casts).toHaveLength(1);
    expect(timeline(events)!.segments).toHaveLength(1);
  });

  it("單擊武器的技能、範圍技對不同目標各擲一次：照舊一段", () => {
    const one = [used("skill_stab", [at(3, 2)]), rolled(FOE), dealt(FOE)];
    expect(vfxFor(one, field, cards).casts).toHaveLength(1);
    const area = [used("skill_sweep", [at(3, 2), at(2, 3)]), rolled(FOE, true, "skill_sweep"), rolled(FOE2, true, "skill_sweep"), dealt(FOE), dealt(FOE2)];
    expect(vfxFor(area, field, cards).casts).toHaveLength(1);
    expect(timeline(area)!.segments).toHaveLength(1);
  });

  it("普攻雙匕首照舊每個 attack_rolled 一段", () => {
    const basic = [ev("attack_rolled", { attacker_id: HERO, target_id: FOE, hit: true }), dealt(FOE), ev("attack_rolled", { attacker_id: HERO, target_id: FOE, hit: true }), dealt(FOE)];
    expect(vfxFor(basic, field, {}).casts).toHaveLength(2);
  });

  it("守護者攔下第一下：第二下打守護者也另開一段", () => {
    const events = [
      used("skill_stab", [at(3, 2)]),
      rolled(FOE),
      ev("attack_intercepted", { guardian_id: GUARD, attacker_id: HERO, target_id: FOE, skill_id: "skill_stab" }),
      dealt(GUARD),
      rolled(GUARD),
      dealt(GUARD),
    ];
    expect(vfxFor(events, field, cards).casts).toHaveLength(2);
    expect(timeline(events)!.segments).toHaveLength(2);
  });

  it("別人的命中判定（反擊）不算多打的那一下", () => {
    const seg = { caster: HERO, basic: false, rolled: [] as string[] };
    noteStrike(seg, rolled(FOE));
    expect(repeatsStrike(seg, ev("attack_rolled", { attacker_id: FOE, target_id: HERO }))).toBe(false);
    expect(repeatsStrike(seg, rolled(FOE))).toBe(true);
    expect(repeatsStrike({ ...seg, basic: true }, rolled(FOE))).toBe(false);
  });
});

describe("DD-2 預覽：打 2 下", () => {
  const v = smallView();
  const names = unitNames(v);
  const target = {
    unit_id: "unit_0003",
    hit_permille: 800,
    crit_permille: 50,
    damage: { minimum: 6, maximum: 30, expected_milli: 14200, expected_if_hit_milli: 17750 },
    ally: false,
    knock_permille: null,
    status_chances: [],
  };
  const skill = {
    action: { type: "use_skill", unit_id: "unit_0001", skill_id: "skill_stab", target_id: "unit_0003" },
    hit_permille: null,
    crit_permille: null,
    damage: null,
    affected_tiles: [],
    affected_units: [],
    certain: [],
    possible: [],
    cover: null,
    notes: [],
    targets: [target],
    healed: [],
    min_events: [],
    max_events: [],
  } as unknown as PreviewOut;

  it("strikes 2：第一行寫下數、每下命中率、傷害合計（伺服器給的合計，原樣顯示）", () => {
    const lines = previewLines({ ...skill, strikes: 2 }, names, v);
    expect(lines[0]).toBe(`${names.label("unit_0003")}：打 2 下，每下命中 80%，傷害合計 6–30（期望 14.2）`);
  });

  it("strikes 1 或沒給（其他技能、普攻）：沒有這一行，輸出和改前相同", () => {
    expect(strikeLines({ ...skill, strikes: 1 }, names)).toEqual([]);
    expect(strikeLines(skill, names)).toEqual([]);
    expect(previewLines({ ...skill, strikes: 1 }, names, v)).toEqual(previewLines(skill, names, v));
    expect(previewLines(skill, names, v).some((l) => l.includes("打 "))).toBe(false);
  });

  it("目標沒有傷害（只上狀態）時不寫", () => {
    expect(strikeLines({ ...skill, strikes: 2, targets: [{ ...target, damage: null }] }, names)).toEqual([]);
  });
});
