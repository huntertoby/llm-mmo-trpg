// 6N-5：特殊結果的觸發、停頓長度上限、略過不停頓、確定性；復活的反應、勝利的觸發。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, SkillCard, StepOut } from "../api/types";
import { frameOps, playbackPlan } from "./playback";
import { specialsFor, stopHoldMs, stopsOf, STEP_STOP_MAX_MS, STOP_MAX_MS, STOP_MS, victoryOf, withSpecials } from "./specials";
import { vfxFor, type VfxSpecial } from "./vfx";

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const BOSS = "u_boss";
const at = (x: number, y: number): Pos => ({ x, y });

type U = { pos: Pos; team: string; tags?: string[]; statuses?: Array<{ status_id: string }>; downed?: boolean; hp?: number };
function view(units: Record<string, U>, round = 1): BattleView {
  return {
    map_id: "m1",
    team: "ally",
    round,
    units: Object.entries(units).map(([id, u]) => ({ id, pos: u.pos, team: u.team, max_hp: 40, hp: u.hp ?? 40, downed: u.downed ?? false, tags: u.tags ?? [], statuses: u.statuses ?? [] })),
    tiles: [],
  } as unknown as BattleView;
}
const base = { [HERO]: { pos: at(2, 2), team: "ally" }, [FOE]: { pos: at(3, 2), team: "enemy" }, [FOE2]: { pos: at(4, 2), team: "enemy" } };
const v = view(base);

function card(): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: ["damage"], icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 1, effects: [{ type: "damage" }] }] } } as unknown as SkillCard;
}
const cards = { sk: card() };
const used = (unit = HERO, seq = 1) => ({ seq, round: 1, type: "skill_used", unit_id: unit, skill_id: "sk", tiles: [at(3, 2)] });
const roll = (target: string, hit: boolean, seq = 2, attacker = HERO) => ({ seq, round: 1, type: "attack_rolled", attacker_id: attacker, target_id: target, hit });
const dmg = (target: string, lost: number, more: Record<string, unknown> = {}, seq = 3, source = HERO) => ({
  seq,
  round: 1,
  type: "damage_dealt",
  target_id: target,
  source_id: source,
  element: "physical",
  amount: lost,
  hp_before: 40,
  hp_after: 40 - lost,
  crit: false,
  ...more,
});
const downed = (unit: string, seq = 4, round = 1) => ({ seq, round, type: "unit_downed", unit_id: unit });

const specials = (events: Record<string, unknown>[], before = v, after = v): VfxSpecial[] => specialsFor(vfxFor(events, after, cards), events, before, after);
const kinds = (s: readonly VfxSpecial[]) => s.map((x) => x.kind);

describe("special results: triggers (6N-5)", () => {
  it("crit: true → crit at the hit point", () => {
    const events = [used(), dmg(FOE, 5, { crit: true })];
    const vfx = vfxFor(events, v, cards);
    const s = specialsFor(vfx, events, v, v);
    expect(s).toEqual([{ kind: "crit", pos: at(3, 2), unitId: FOE, atMs: vfx.casts[0]!.impactMs }]);
    expect(kinds(specials([used(), dmg(FOE, 5)]))).toEqual([]);
  });

  it("kill: unit_downed or hp_after == 0", () => {
    expect(kinds(specials([used(), dmg(FOE, 40), downed(FOE)]))).toEqual(["kill"]);
    expect(kinds(specials([used(), dmg(FOE, 40)]))).toEqual(["kill"]); // 扣到 0、沒有倒下事件
    expect(kinds(specials([used(), dmg(FOE, 39)]))).toEqual([]);
  });

  it("6R-F: stateless — the first unit to fall in each round of the step is emphasized once", () => {
    // 同一步兩個人倒下：只強化最先倒下的那個
    const two = specials([used(), dmg(FOE, 40), downed(FOE), dmg(FOE2, 40, {}, 5), downed(FOE2, 6)]).filter((x) => x.kind === "kill");
    expect(two).toHaveLength(1);
    expect(two[0]!.unitId).toBe(FOE);
    // 同一步跨了一輪（第 1 輪倒一個、第 2 輪又倒一個）：每輪各一次
    const spanning = [used(), dmg(FOE, 40), downed(FOE), { ...dmg(FOE2, 40, {}, 5), round: 2 }, downed(FOE2, 6, 2)];
    expect(specials(spanning).filter((x) => x.kind === "kill").map((x) => x.unitId)).toEqual([FOE, FOE2]);
    // 事件沒有 round：用 before 的輪數
    const noRound = [used(), { ...dmg(FOE, 40), round: undefined }, { ...downed(FOE), round: undefined }];
    expect(kinds(specials(noRound, view(base, 7)))).toEqual(["kill"]);
    // 同樣的輸入不管呼叫幾次、先後順序，結果都一樣（沒有跨步驟的記憶）
    const a = specials([used(), dmg(FOE2, 40), downed(FOE2)]);
    specials([used(), dmg(FOE, 40), downed(FOE)]);
    expect(specials([used(), dmg(FOE2, 40), downed(FOE2)])).toEqual(a);
  });

  it("6R-F: skip, refresh and spectate pick the same kills (no memory across responses)", () => {
    const step = (unit: string, seq: number): StepOut => ({ actor_id: HERO, step: { type: "use_skill" }, events: [used(HERO, seq), dmg(unit, 40, {}, seq + 2), downed(unit, seq + 3)], view: v }) as unknown as StepOut;
    const s1 = step(FOE, 1);
    const s2 = step(FOE2, 11);
    const killsOf = (res: BattleResponse) => playbackPlan(res, HERO, "normal", cards).frames.map((f) => (f.vfx?.specials ?? []).filter((x) => x.kind === "kill").map((x) => x.unitId));
    // 一次收到兩步（正常播放）
    const together = killsOf({ steps: [s1, s2], view: v, initial_view: v } as unknown as BattleResponse);
    // 重新整理／觀戰：第一步已經播過（或在別的回應裡），只收到第二步
    const later = killsOf({ steps: [s2], view: v, initial_view: v } as unknown as BattleResponse);
    // 第一步按了略過
    playbackPlan({ steps: [s1], view: v, initial_view: v } as unknown as BattleResponse, HERO, "skip", cards);
    const afterSkip = killsOf({ steps: [s2], view: v, initial_view: v } as unknown as BattleResponse);
    expect(together[1]).toEqual(later[0]);
    expect(afterSkip[0]).toEqual(later[0]);
    expect(together).toEqual([[FOE], [FOE2]]);
  });

  it("block_permille < 1000 → block with the attacker who gets bounced back", () => {
    const s = specials([used(), dmg(FOE, 3, { block_permille: 500 })]);
    expect(s).toMatchObject([{ kind: "block", unitId: FOE, attackerId: HERO }]);
    expect(kinds(specials([used(), dmg(FOE, 3, { block_permille: 1000 })]))).toEqual([]);
  });

  it("hit: false → dodge (skills and basic attacks)", () => {
    expect(specials([used(), roll(FOE, false)])).toMatchObject([{ kind: "dodge", unitId: FOE }]);
    expect(kinds(specials([roll(FOE, false, 1)]))).toEqual(["dodge"]);
  });

  it("boss big move: a boss-tagged caster that was charging releases its skill", () => {
    const charging = view({ ...base, [BOSS]: { pos: at(5, 5), team: "enemy", tags: ["boss"], statuses: [{ status_id: "charging" }] } });
    const after = view({ ...base, [BOSS]: { pos: at(5, 5), team: "enemy", tags: ["boss"] } });
    const release = [{ seq: 1, round: 2, type: "skill_followup", unit_id: BOSS, skill_id: "sk", name_zh: "大招", when: "next_turn", origin: at(5, 5), tiles: [at(4, 5)] }];
    expect(specials(release, charging, after)).toMatchObject([{ kind: "boss", unitId: BOSS, atMs: 0 }]);
    // 不是 Boss、或沒有在蓄力：沒有
    const plain = view({ ...base, [BOSS]: { pos: at(5, 5), team: "enemy", statuses: [{ status_id: "charging" }] } });
    expect(specials(release, plain, after)).toEqual([]);
    const idle = view({ ...base, [BOSS]: { pos: at(5, 5), team: "enemy", tags: ["boss"] } });
    expect(specials(release, idle, after)).toEqual([]);
  });
});

describe("hit stops (6N-5)", () => {
  it("lengths: crit and kill 0.1 s, block 0.06 s; dodge and boss do not stop", () => {
    expect(STOP_MS).toEqual({ crit: 100, kill: 100, block: 60, dodge: 0, boss: 0 });
    const vfx = withSpecials(vfxFor([used(), dmg(FOE, 3, { block_permille: 500 })], v, cards), [used(), dmg(FOE, 3, { block_permille: 500 })], v, v);
    expect(vfx.stops).toEqual([{ atMs: vfx.casts[0]!.impactMs, ms: 60 }]);
    const dodge = [used(), roll(FOE, false)];
    expect(withSpecials(vfxFor(dodge, v, cards), dodge, v, v).stops).toBeUndefined();
  });

  it("each stop ≤ 0.1 s; crit + kill on the same hit stop only once; a step adds up to at most 0.2 s", () => {
    const sp = (kind: VfxSpecial["kind"], atMs: number): VfxSpecial => ({ kind, atMs, pos: at(0, 0), unitId: null });
    expect(stopsOf([sp("crit", 100), sp("kill", 100), sp("block", 100)])).toEqual([{ atMs: 100, ms: 100 }]);
    const many = stopsOf([sp("crit", 100), sp("crit", 300), sp("crit", 500), sp("crit", 700)]);
    for (const s of many) expect(s.ms).toBeLessThanOrEqual(STOP_MAX_MS);
    expect(many.reduce((a, s) => a + s.ms, 0)).toBeLessThanOrEqual(STEP_STOP_MAX_MS);
    expect(many.map((s) => s.atMs)).toEqual([100, 300]);
  });

  it("many crits in one battle: every step's stop ≤ 0.1 s at normal speed", () => {
    const steps: StepOut[] = [];
    for (let i = 0; i < 6; i++) steps.push({ actor_id: HERO, step: { type: "use_skill" }, events: [used(HERO, i * 10 + 1), dmg(FOE, 2, { crit: true }, i * 10 + 3)], view: v } as unknown as StepOut);
    const res = { steps, view: v, initial_view: v } as unknown as BattleResponse;
    const plan = playbackPlan(res, HERO, "normal", cards);
    expect(plan.frames).toHaveLength(6);
    for (const f of plan.frames) {
      expect(f.vfx!.stops).toHaveLength(1);
      expect(f.vfx!.stops![0]!.ms).toBeLessThanOrEqual(100);
      expect(stopHoldMs(f.vfx!)).toBeLessThanOrEqual(100);
    }
  });

  it("stops scale with the play speed; skip has no vfx so no stop", () => {
    const step = { actor_id: HERO, step: { type: "use_skill" }, events: [used(), dmg(FOE, 2, { crit: true })], view: v } as unknown as StepOut;
    const res = { steps: [step], view: v, initial_view: v } as unknown as BattleResponse;
    expect(playbackPlan(res, HERO, "normal", cards).frames[0]!.vfx!.stops).toEqual([{ atMs: expect.any(Number), ms: 100 }]);
    expect(playbackPlan(res, HERO, "fast", cards).frames[0]!.vfx!.stops![0]!.ms).toBe(50);
    const skip = playbackPlan(res, HERO, "skip", cards);
    expect(skip.frames.every((f) => f.vfx === null)).toBe(true);
    expect(skip.frames.flatMap(frameOps).some((op) => op.op === "vfx" || op.op === "victory")).toBe(false);
  });

  it("the hold before the result redraw counts only stops at or before the last hit", () => {
    const events = [used(), dmg(FOE, 2, { crit: true })];
    const vfx = withSpecials(vfxFor(events, v, cards), events, v, v);
    expect(stopHoldMs(vfx)).toBe(100);
    expect(stopHoldMs({ ...vfx, stops: [{ atMs: vfx.leadMs + 1, ms: 100 }] })).toBe(0);
  });
});

describe("determinism (6N-5)", () => {
  it("same events → same specials and stops", () => {
    const events = [used(), roll(FOE, true), dmg(FOE, 40, { crit: true }), downed(FOE), roll(FOE2, false, 5)];
    const a = withSpecials(vfxFor(events, v, cards), events, v, v);
    const b = withSpecials(vfxFor(events, v, cards), events, v, v);
    expect(a).toEqual(b);
    expect(kinds(a.specials!)).toEqual(["crit", "kill", "dodge"]);
  });
});

describe("revive reaction (6N-5, from 6N-4's table)", () => {
  it("unit_revived by the caster → rise at the cast's hit point", () => {
    const before = view({ ...base, u_ally: { pos: at(1, 2), team: "ally", downed: true, hp: 0 } });
    const after = view({ ...base, u_ally: { pos: at(1, 2), team: "ally", hp: 5 } });
    const events = [{ seq: 1, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles: [at(1, 2)] }, { seq: 2, round: 1, type: "unit_revived", unit_id: "u_ally", source_id: HERO, skill_id: "sk", hp: 5 }];
    const vfx = vfxFor(events, after, cards);
    expect(vfx.reactions).toEqual([{ unitId: "u_ally", pos: at(1, 2), kind: "rise", seq: 2, atMs: vfx.casts[0]!.impactMs, cast: 0 }]);
    expect(before.units.find((u) => u.id === "u_ally")!.downed).toBe(true);
  });
});

describe("victory (6N-5, from 6N-4's table)", () => {
  const end = (winner: string | null) => [{ seq: 9, round: 3, type: "battle_ended", winner, reason: "eliminated" }];
  it("battle_ended won by the hero's team → standing allies; lost or draw → none", () => {
    const after = view({ ...base, u_ally: { pos: at(1, 2), team: "ally" }, u_down: { pos: at(0, 2), team: "ally", downed: true, hp: 0 } });
    expect(victoryOf(end("ally"), after, HERO)).toEqual({ unitIds: [HERO, "u_ally"], seq: 9, battleKey: "m1" });
    expect(victoryOf(end("enemy"), after, HERO)).toBeNull();
    expect(victoryOf(end(null), after, HERO)).toBeNull();
  });

  it("playback adds a victory op after the result; skip has none", () => {
    const step = { actor_id: HERO, step: { type: "attack" }, events: [roll(FOE, true, 1), dmg(FOE, 40, {}, 2), downed(FOE, 3), ...end("ally")], view: v } as unknown as StepOut;
    const res = { steps: [step], view: v, initial_view: v } as unknown as BattleResponse;
    const ops = frameOps(playbackPlan(res, HERO, "normal", cards).frames[0]!);
    const idx = (name: string) => ops.findIndex((o) => o.op === name);
    expect(idx("victory")).toBeGreaterThan(idx("view"));
    const op = ops[idx("victory")] as Extract<(typeof ops)[number], { op: "victory" }>;
    expect(op.victory).toMatchObject({ unitIds: [HERO], seq: 9, ms: 1000, clipMs: 520 });
    expect(playbackPlan(res, HERO, "skip", cards).frames.flatMap(frameOps).some((o) => o.op === "victory")).toBe(false);
  });
});
