// 6H-1 打擊感：停頓依扣血比例分級、一步的停頓上限、微震只在三種情況、最後一擊放慢（一場一次、無狀態）、減少動態。
import { describe, expect, it } from "vitest";
import { type BattleResponse, type BattleView, type Pos, type SkillCard, type StepOut } from "../api/types";
import { advanceClock, type Freeze } from "../render/hitStop";
import { reduceEffects, reduceVfx } from "../render/reducedMotion";
import { impactShakeEffect } from "../render/vfxEffects";
import { finalBlowOf, hitHoldMs, impactStops, impactTier, shakeEnvelope, shakeOffset, shakesFor, SLOW_RATE, slowExtraMs, slowHoldMs, slowRate, slowRealMs, slowTailMs, TIER_MS, withImpact } from "./impact";
import { frameOps, playbackPlan, type Frame } from "./playback";
import { STEP_STOP_MAX_MS, withSpecials } from "./specials";
import { scaleVfx, vfxFor, type StepVfx, type VfxCards } from "./vfx";
import { cueRealMs } from "../audio/battleSfx";
import { skillTimeline, SKILL_CAP_MS } from "./skillSequence";

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const BOSS = "u_boss";
const MAX = 1000;
const at = (x: number, y: number): Pos => ({ x, y });

type U = { pos: Pos; team: string; tags?: string[]; statuses?: Array<{ status_id: string }>; downed?: boolean; hp?: number };
function view(units: Record<string, U>): BattleView {
  return {
    map_id: "m1",
    team: "ally",
    round: 1,
    units: Object.entries(units).map(([id, u]) => ({ id, pos: u.pos, team: u.team, max_hp: MAX, hp: u.hp ?? MAX, downed: u.downed ?? false, tags: u.tags ?? [], statuses: u.statuses ?? [] })),
    tiles: [],
  } as unknown as BattleView;
}
const base: Record<string, U> = { [HERO]: { pos: at(2, 2), team: "ally" }, [FOE]: { pos: at(3, 2), team: "enemy" }, [FOE2]: { pos: at(3, 3), team: "enemy" } };
const v = view(base);

function card(): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: ["damage"], icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 1, effects: [{ type: "damage" }] }] } } as unknown as SkillCard;
}
const cards = { sk: card() };
const used = (unit = HERO, seq = 1, tiles = [at(3, 2)]) => ({ seq, round: 1, type: "skill_used", unit_id: unit, skill_id: "sk", tiles });
const dmg = (target: string, lost: number, more: Record<string, unknown> = {}, seq = 3, source = HERO, hpBefore = MAX) => ({
  seq,
  round: 1,
  type: "damage_dealt",
  target_id: target,
  source_id: source,
  element: "physical",
  amount: lost,
  hp_before: hpBefore,
  hp_after: hpBefore - lost,
  crit: false,
  ...more,
});
const downed = (unit: string, seq = 4) => ({ seq, round: 1, type: "unit_downed", unit_id: unit });
const ended = (winner = "ally", seq = 9) => ({ seq, round: 1, type: "battle_ended", winner });

/** 一步走正式的推導（vfxFor → withSpecials → withImpact），未縮放。 */
function impact(events: Record<string, unknown>[], before = v, after = v): StepVfx {
  return withImpact(withSpecials(vfxFor(events, after, cards), events, before, after), events, before, after, HERO);
}
const stopMs = (events: Record<string, unknown>[]) => (impact(events).stops ?? []).reduce((s, x) => s + x.ms, 0);

describe("hit stop tiers by share of max HP (6H-1)", () => {
  it("thresholds 9.9% / 10% / 25% / 50% and crit", () => {
    expect(stopMs([used(), dmg(FOE, 99)])).toBe(0); // 9.9%
    expect(stopMs([used(), dmg(FOE, 100)])).toBe(40); // 10%
    expect(stopMs([used(), dmg(FOE, 249)])).toBe(40);
    expect(stopMs([used(), dmg(FOE, 250)])).toBe(70); // 25%
    expect(stopMs([used(), dmg(FOE, 499)])).toBe(70);
    expect(stopMs([used(), dmg(FOE, 500)])).toBe(100); // 50%
    expect(stopMs([used(), dmg(FOE, 10, { crit: true })])).toBe(100); // 暴擊：100（不另外疊加）
    expect(TIER_MS).toEqual([0, 40, 70, 100]);
  });

  it("pure tier function", () => {
    expect([impactTier(99, false), impactTier(100, false), impactTier(250, false), impactTier(500, false), impactTier(0, true)]).toEqual([0, 1, 2, 3, 3]);
  });

  it("the share is the HP actually lost (hp_before − hp_after), not the raw amount; several targets take the largest", () => {
    // amount 300 但 HP 只從 520 掉到 470：實際扣 50（5%）→ 不停
    expect(stopMs([used(), { ...dmg(FOE, 300), hp_before: 520, hp_after: 470 }])).toBe(0);
    // 只剩 50 HP 被打到 0：比例 5%，但扣到 0 ＝ 擊殺（6N-5 照舊 100）
    expect(stopMs([used(), { ...dmg(FOE, 300), hp_before: 50, hp_after: 0 }])).toBe(100);
    // 一下打兩人：取最大的
    const two = [used(HERO, 1, [at(3, 2), at(3, 3)]), dmg(FOE, 50), dmg(FOE2, 260, {}, 4)];
    expect(stopMs(two)).toBe(70);
  });

  it("block keeps 60 ms (6N-5); a tier wins when it is longer", () => {
    expect(stopMs([used(), dmg(FOE, 20, { block_permille: 500 })])).toBe(60);
    expect(stopMs([used(), dmg(FOE, 300, { block_permille: 500 })])).toBe(70);
  });

  it("the stops of one step add up to at most 0.2 s (later ones are shortened)", () => {
    const vfx: StepVfx = {
      casts: [],
      hits: [],
      blasts: [],
      shake: 0,
      leadMs: 400,
      impacts: [100, 200, 300, 400].map((t, i) => ({ kind: "hit" as const, pos: at(3, 2), unitId: FOE, lost: 600, crit: false, seq: i, atMs: t })),
    };
    const stops = impactStops(vfx);
    expect(stops.reduce((s, x) => s + x.ms, 0)).toBe(STEP_STOP_MAX_MS);
    expect(stops.every((x) => x.ms <= 100)).toBe(true);
    const mixed = impactStops({ ...vfx, impacts: [{ ...vfx.impacts![0]!, lost: 300 }, { ...vfx.impacts![1]!, lost: 600 }, { ...vfx.impacts![2]!, lost: 600 }] });
    expect(mixed).toEqual([
      { atMs: 100, ms: 70 },
      { atMs: 200, ms: 100 },
      { atMs: 300, ms: 30 },
    ]);
  });

  it("stops scale with playback speed; skip has none", () => {
    const events = [used(), dmg(FOE, 300)];
    const step = { actor_id: HERO, step: { type: "use_skill" }, events, view: v } as unknown as StepOut;
    const res = { steps: [step], view: v, initial_view: v } as unknown as BattleResponse;
    const normal = playbackPlan(res, HERO, "normal", cards).frames[0]!.vfx!;
    const fast = playbackPlan(res, HERO, "fast", cards).frames[0]!.vfx!;
    expect(normal.stops).toEqual([{ atMs: normal.leadMs, ms: 70 }]);
    expect(fast.stops![0]!.ms).toBe(35);
    const skipped = playbackPlan(res, HERO, "skip", cards);
    expect(skipped.frames.flatMap(frameOps).some((op) => op.op === "vfx")).toBe(false);
  });
});

describe("camera shake only for heavy hits, explosions and boss big moves (6H-1)", () => {
  it("a normal or light hit does not shake; a heavy hit (tier 2/3) shakes 2 px", () => {
    expect(impact([used(), dmg(FOE, 50)]).shakes).toBeUndefined();
    expect(impact([used(), dmg(FOE, 200)]).shakes).toBeUndefined(); // 第 1 級：停 40、不震
    expect(impact([used(), dmg(FOE, 250)]).shakes).toMatchObject([{ kind: "heavy", px: 2, ms: 120, targets: [at(3, 2)] }]);
    expect(impact([used(), dmg(FOE, 30, { crit: true })]).shakes).toMatchObject([{ kind: "heavy", px: 2 }]);
  });

  it("a kill with little damage stops (6N-5) but does not shake", () => {
    const events = [used(), { ...dmg(FOE, 30, {}, 3, HERO, 30) }, downed(FOE)];
    const vfx = impact(events, view({ ...base, [FOE]: { ...base[FOE]!, hp: 30 } }), v);
    expect(vfx.stops).toEqual([{ atMs: vfx.leadMs, ms: 100 }]);
    expect(vfx.shakes).toBeUndefined();
  });

  it("explosions: object_exploded, bomb_exploded and detonated runes shake 3 px", () => {
    const boom = { seq: 5, round: 1, type: "object_exploded", object_id: "o1", pos: at(4, 4), radius: 1, source_id: null };
    expect(impact([used(), dmg(FOE, 50), boom]).shakes).toMatchObject([{ kind: "blast", px: 3, ms: 160 }]);
    const bomb = { seq: 5, round: 1, type: "bomb_exploded", unit_id: FOE, pos: at(3, 2) };
    expect(impact([used(), dmg(FOE, 50), bomb]).shakes).toMatchObject([{ kind: "blast", px: 3 }]);
    const rune = { seq: 5, round: 1, type: "rune_removed", reason: "detonated", pos: at(3, 2), element: "fire" };
    expect(impact([used(), dmg(FOE, 50), rune]).shakes).toMatchObject([{ kind: "blast", px: 3 }]);
    // 符文被移除但不是引爆：不震
    expect(impact([used(), dmg(FOE, 50), { ...rune, reason: "expired" }]).shakes).toBeUndefined();
  });

  it("boss big move shakes 4 px at the cast's hit point; a boss without charging does not", () => {
    const charging = view({ ...base, [BOSS]: { pos: at(5, 2), team: "enemy", tags: ["boss"], statuses: [{ status_id: "charging" }] } });
    const after = view({ ...base, [BOSS]: { pos: at(5, 2), team: "enemy", tags: ["boss"] } });
    const release = [{ seq: 1, round: 2, type: "skill_followup", unit_id: BOSS, skill_id: "sk", origin: at(5, 2), tiles: [at(4, 2)] }, dmg(HERO, 20, {}, 2, BOSS)];
    const vfx = impact(release, charging, after);
    expect(vfx.shakes).toMatchObject([{ kind: "boss", px: 4, ms: 220, atMs: vfx.casts[0]!.impactMs }]);
    const idle = view({ ...base, [BOSS]: { pos: at(5, 2), team: "enemy", tags: ["boss"] } });
    expect(impact(release, idle, after).shakes).toBeUndefined();
  });

  it("several shakes at once take the largest, they do not add up", () => {
    const shakes = [
      { kind: "heavy" as const, atMs: 0, ms: 120, baseMs: 120, px: 2, phase: 0.25, targets: [] },
      { kind: "boss" as const, atMs: 0, ms: 220, baseMs: 220, px: 4, phase: 0.25, targets: [] },
    ];
    for (let t = 0; t < 220; t += 7) {
      const o = shakeOffset(shakes, t);
      expect(Math.abs(o.x)).toBeLessThanOrEqual(4 + 1e-9);
      expect(Math.abs(o.y)).toBeLessThanOrEqual(4 + 1e-9);
      expect(o).toEqual(shakeOffset([shakes[1]!], t)); // 4 px 的那個一直比較大
    }
    expect(shakeOffset(shakes, 220)).toEqual({ x: 0, y: 0 });
  });

  it("envelope decays and the last 30% goes linearly back to 0; same input, same output", () => {
    expect(shakeEnvelope(0)).toBe(1);
    expect(shakeEnvelope(0.7)).toBeCloseTo(0.5);
    expect(shakeEnvelope(0.85)).toBeCloseTo(0.25);
    expect(shakeEnvelope(1)).toBe(0);
    const s = impact([used(), dmg(FOE, 300)]).shakes!;
    expect(impact([used(), dmg(FOE, 300)]).shakes).toEqual(s);
    expect(shakeOffset(s, s[0]!.atMs + 30)).toEqual(shakeOffset(s, s[0]!.atMs + 30));
  });

  it("phase comes from battle key + seq (different seq → usually different phase)", () => {
    const a = shakesFor(impact([used(), dmg(FOE, 300, {}, 3)]), [], "m1")[0]!.phase;
    const b = shakesFor(impact([used(), dmg(FOE, 300, {}, 4)]), [], "m1")[0]!.phase;
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThan(1);
    expect(a).not.toBe(b);
  });
});

describe("final blow slow-down (6H-1)", () => {
  const killLast = [used(), dmg(FOE, MAX), downed(FOE), ended()];
  const lastLeft = view({ ...base, [FOE2]: { ...base[FOE2]!, downed: true, hp: 0 } });

  it("defeating the last enemy (our battle_ended win) slows the hit point to 0.4x", () => {
    const vfx = impact(killLast, lastLeft, lastLeft);
    expect(vfx.slow).toMatchObject({ reason: "last", unitId: FOE, rate: SLOW_RATE, rampMs: 60 });
    expect(vfx.slow!.fromMs).toBe(vfx.slow!.atMs - 120);
    expect(vfx.slow!.toMs).toBe(vfx.slow!.atMs + 280);
    // 命中那一刻疊第 3 級停頓與重擊微震
    expect(vfx.stops).toContainEqual({ atMs: vfx.slow!.atMs, ms: 100 });
    expect(vfx.shakes).toMatchObject([{ kind: "heavy", atMs: vfx.slow!.atMs }]);
  });

  it("a kill that is not the last, or a loss, does not slow down", () => {
    expect(impact([used(), dmg(FOE, MAX), downed(FOE)]).slow).toBeUndefined();
    expect(impact([used(), dmg(FOE, MAX), downed(FOE), ended("enemy")], lastLeft, lastLeft).slow).toBeUndefined();
    // 我方贏了但這一步沒有人倒下（例如撤離）：不放慢
    expect(impact([used(), dmg(FOE, 10), ended()]).slow).toBeUndefined();
  });

  it("downing a boss slows down; once a boss is down (in `before`) the battle never slows again", () => {
    const withBoss = view({ ...base, [BOSS]: { pos: at(3, 2), team: "enemy", tags: ["boss"] } });
    const bossDown = [used(), dmg(BOSS, MAX), downed(BOSS)];
    expect(impact(bossDown, withBoss, withBoss).slow).toMatchObject({ reason: "boss", unitId: BOSS });
    // 之後打倒最後一個敵人：before 裡 Boss 已倒下 → 不再放慢（一場只一次）
    const afterBoss = view({ ...base, [BOSS]: { pos: at(5, 5), team: "enemy", tags: ["boss"], downed: true, hp: 0 }, [FOE2]: { ...base[FOE2]!, downed: true, hp: 0 } });
    expect(impact(killLast, afterBoss, afterBoss).slow).toBeUndefined();
    // Boss 就是最後一個：只有一次
    const bossLast = view({ [HERO]: base[HERO]!, [BOSS]: { pos: at(3, 2), team: "enemy", tags: ["boss"] } });
    expect(impact([...bossDown, ended()], bossLast, bossLast).slow).toMatchObject({ reason: "boss" });
  });

  it("a whole battle slows at most once and replay / refresh / spectate get the same result (stateless)", () => {
    const withBoss = view({ ...base, [BOSS]: { pos: at(3, 2), team: "enemy", tags: ["boss"] } });
    const bossFell = view({ ...base, [BOSS]: { pos: at(3, 2), team: "enemy", tags: ["boss"], downed: true, hp: 0 } });
    const end = view({ ...base, [BOSS]: { pos: at(3, 2), team: "enemy", tags: ["boss"], downed: true, hp: 0 }, [FOE]: { ...base[FOE]!, downed: true, hp: 0 }, [FOE2]: { ...base[FOE2]!, downed: true, hp: 0 } });
    const steps = [
      { actor_id: HERO, step: { type: "use_skill" }, events: [used(HERO, 1), dmg(BOSS, MAX, {}, 2), downed(BOSS, 3)], view: bossFell },
      { actor_id: HERO, step: { type: "use_skill" }, events: [used(HERO, 4, [at(3, 3)]), dmg(FOE2, MAX, {}, 5), downed(FOE2, 6)], view: bossFell },
      { actor_id: HERO, step: { type: "use_skill" }, events: [used(HERO, 7), dmg(FOE, MAX, {}, 8), downed(FOE, 9), ended("ally", 10)], view: end },
    ] as unknown as StepOut[];
    const slowsOf = (res: BattleResponse) => playbackPlan(res, HERO, "normal", cards).frames.map((f) => f.vfx?.slow?.unitId ?? null);
    const all = slowsOf({ steps, view: end, initial_view: withBoss } as unknown as BattleResponse);
    expect(all).toEqual([BOSS, null, null]);
    expect(all.filter((x) => x !== null)).toHaveLength(1);
    // 重播：同輸入同輸出；重新整理／觀戰只收到後兩步（initial_view ＝ 第一步之後）：還是沒有放慢
    expect(slowsOf({ steps, view: end, initial_view: withBoss } as unknown as BattleResponse)).toEqual(all);
    expect(slowsOf({ steps: steps.slice(1), view: end, initial_view: bossFell } as unknown as BattleResponse)).toEqual([null, null]);
    // 第一步按了略過（沒有特效），下一個回應照樣不放慢
    playbackPlan({ steps: steps.slice(0, 1), view: bossFell, initial_view: withBoss } as unknown as BattleResponse, HERO, "skip", cards);
    expect(slowsOf({ steps: steps.slice(2), view: end, initial_view: bossFell } as unknown as BattleResponse)).toEqual([null]);
  });

  it("finalBlowOf is pure", () => {
    const vfx = vfxFor(killLast, lastLeft, cards);
    const events = killLast.map((e) => e as never);
    expect(finalBlowOf(vfx, events, lastLeft, lastLeft, HERO)).toEqual(finalBlowOf(vfx, events, lastLeft, lastLeft, HERO));
  });

  it("the slow-down adds about 0.5 s at normal speed, half at fast; the rate ramps in and out", () => {
    const vfx = impact(killLast, lastLeft, lastLeft);
    const s = vfx.slow!;
    const extra = slowExtraMs(s);
    expect(extra).toBeGreaterThan(430);
    expect(extra).toBeLessThan(530);
    expect(slowExtraMs(scaleVfx(vfx, 0.5).slow!)).toBeCloseTo(extra / 2, 0);
    expect(slowRate(s.fromMs - 1, s)).toBe(1);
    expect(slowRate(s.fromMs + 30, s)).toBeCloseTo(0.7);
    expect(slowRate(s.atMs, s)).toBe(SLOW_RATE);
    expect(slowRate(s.toMs + 1, s)).toBe(1);
    // 播放等命中：命中點以前放慢的部分；之後的部分給勝利片段等
    expect(slowHoldMs(vfx)).toBe(Math.round(slowRealMs(s, 0, vfx.leadMs) - vfx.leadMs));
    expect(slowHoldMs(vfx) + slowTailMs(vfx)).toBeGreaterThan(extra);
  });

  it("the renderer clock runs at 0.4x inside the window and the hold matches the integral", () => {
    const span = { fromMs: 100, toMs: 500, rampMs: 60, rate: 0.4 };
    let c = 0;
    let real = 0;
    while (c < 500) {
      c = advanceClock(c, 16, [], [span]);
      real += 16;
    }
    expect(real).toBeGreaterThanOrEqual(Math.floor(slowRealMs(span, 0, 500)));
    expect(real).toBeLessThanOrEqual(Math.ceil(slowRealMs(span, 0, 500)) + 16);
    // 停頓和放慢一起：停頓照舊用掉
    const f: Freeze[] = [{ at: 300, left: 100 }];
    let c2 = 0;
    for (let i = 0; i < 200; i++) c2 = advanceClock(c2, 16, f, [span]);
    expect(f).toEqual([]);
    expect(c2).toBeGreaterThan(500);
  });
});

describe("renderer pieces (6H-1)", () => {
  it("one shake effect per step, tagged shake (dropped with reduced motion), stage offset within the amplitude", () => {
    const s = impact([used(), dmg(FOE, 600)]).shakes!;
    const seen: Array<[number, number]> = [];
    const e = impactShakeEffect(s, 1000, (x, y) => seen.push([x, y]))!;
    expect(e.motion).toBe("shake");
    expect(e.startMs).toBe(1000 + s[0]!.atMs);
    for (let t = 0; t <= 1; t += 0.05) e.update(t);
    e.end?.();
    expect(seen.every(([x, y]) => Math.abs(x) <= 2 + 1e-9 && Math.abs(y) <= 2 + 1e-9)).toBe(true);
    expect(seen.some(([x]) => Math.abs(x) > 0.5)).toBe(true);
    expect(seen.at(-1)).toEqual([0, 0]);
    expect(impactShakeEffect([], 0, () => undefined)).toBeNull();
    expect(reduceEffects([e], true)).toEqual([]);
  });
});

describe("reduced motion turns them all off (6H-1)", () => {
  const killLast = [used(), dmg(FOE, MAX), downed(FOE), ended()];
  const lastLeft = view({ ...base, [FOE2]: { ...base[FOE2]!, downed: true, hp: 0 } });

  it("no stops, no slow-down; shakes stay only as flash targets (the shake effect itself is dropped)", () => {
    const vfx = impact(killLast, lastLeft, lastLeft);
    expect(vfx.slow).toBeDefined();
    const r = reduceVfx(vfx, true);
    expect(r.stops).toBeUndefined();
    expect(r.slow).toBeUndefined();
    expect(r.shakes![0]!.targets).toEqual([at(3, 2)]);
    expect(hitHoldMs(vfx, true)).toBe(0);
    expect(hitHoldMs(vfx, false)).toBeGreaterThan(100);
    expect(reduceVfx(vfx, false)).toBe(vfx);
  });
});

// --- 原 impact6h1b.test.ts ---
describe("原 impact6h1b.test.ts", () => {
// 6H-1b：停頓時間點跟著技能時間軸移（`skillSequence.retime` 連 `impacts` 一起換算）。
// 壓縮（一招超過 1.8 秒）或起手移動後，每個扣血的時間都等於對應的命中點；停頓、微震、命中聲都在同一刻。

const HERO = "u_hero";
const FOE = "u_foe";
const FOE2 = "u_foe2";
const MAX = 1000;
const at = (x: number, y: number): Pos => ({ x, y });

type U = { pos: Pos; team: string; hp?: number };
function view(units: Record<string, U>): BattleView {
  return {
    map_id: "m1",
    team: "ally",
    round: 1,
    units: Object.entries(units).map(([id, u]) => ({ id, pos: u.pos, team: u.team, max_hp: MAX, hp: u.hp ?? MAX, downed: false, tags: [], statuses: [] })),
    tiles: [],
  } as unknown as BattleView;
}

function card(shapeId: string, range: number, effects: string[], extra: Record<string, unknown> = {}): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: shapeId, range, effects: effects.map((type) => ({ type })) }] }, ...extra } as unknown as SkillCard;
}

const used = (tiles: Pos[], unit = HERO, seq = 1) => ({ seq, round: 1, type: "skill_used", unit_id: unit, skill_id: "sk", tiles });
const followup = (tiles: Pos[], unit = HERO, seq = 5) => ({ seq, round: 1, type: "skill_followup", unit_id: unit, skill_id: "sk", tiles });
const dmg = (target: string, lost: number, seq = 3, source = HERO, more: Record<string, unknown> = {}) => ({
  seq,
  round: 1,
  type: "damage_dealt",
  target_id: target,
  source_id: source,
  element: "physical",
  amount: lost,
  hp_before: MAX,
  hp_after: MAX - lost,
  crit: false,
  ...more,
});

/** 近身：劍，目標在隔壁。 */
const near = view({ [HERO]: { pos: at(2, 2), team: "ally" }, [FOE]: { pos: at(3, 2), team: "enemy" }, [FOE2]: { pos: at(3, 3), team: "enemy" } });
/** 遠程蓄力：法杖打 9 格外，起手會被壓縮。 */
const far = view({ [HERO]: { pos: at(0, 0), team: "ally" }, [FOE]: { pos: at(9, 0), team: "enemy" } });
const farCards: VfxCards = { sk: card("single", 9, ["damage_multiplier", "damage"], { timing: "delayed" }) };
const nearCards: VfxCards = { sk: card("single", 1, ["damage"]) };

function laid(events: Record<string, unknown>[], v: BattleView, cards: VfxCards, weapon = "blade"): { raw: StepVfx; vfx: StepVfx; full: StepVfx } {
  const raw = vfxFor(events, v, cards);
  const tl = skillTimeline(events, v, cards, raw, () => weapon as never);
  expect(tl).not.toBeNull();
  const vfx = (tl as NonNullable<typeof tl>).vfx;
  return { raw, vfx, full: withImpact(withSpecials(vfx, events, v, v), events, v, v, HERO) };
}

/** 每個扣血都和「同一個受擊者的受擊反應」同一刻（反應是畫面上命中的那一刻）。 */
function expectImpactsOnHits(vfx: StepVfx): void {
  const impacts = vfx.impacts ?? [];
  expect(impacts.length).toBeGreaterThan(0);
  for (const m of impacts) {
    const react = vfx.reactions?.find((r) => r.unitId === m.unitId);
    expect(react, `reaction of ${m.unitId ?? "?"}`).toBeDefined();
    expect(m.atMs).toBeCloseTo((react as NonNullable<typeof react>).atMs, 6);
    expect(vfx.hits.some((h) => Math.abs(h.atMs - m.atMs) < 1e-6)).toBe(true);
  }
}

describe("impacts follow the skill timeline (6H-1b)", () => {
  it("a squeezed charged far shot: every impact lands on the hit point, not the pre-squeeze time", () => {
    const events = [used([at(9, 0)]), dmg(FOE, 300)];
    const { raw, vfx } = laid(events, far, farCards, "staff");
    expect(vfx.casts[0]!.impactMs).toBeLessThanOrEqual(SKILL_CAP_MS + 1e-6);
    // 時間軸真的移動了（不然這個測試沒有意義）
    expect(vfx.casts[0]!.impactMs).not.toBeCloseTo(raw.casts[0]!.impactMs, 6);
    expect(raw.impacts![0]!.atMs).toBeCloseTo(raw.casts[0]!.impactMs, 6);
    expectImpactsOnHits(vfx);
    expect(vfx.impacts![0]!.atMs).toBeCloseTo(vfx.casts[0]!.impactMs, 6);
  });

  it("a plain melee skill (no squeeze): impacts move with the windup exactly like hits", () => {
    const events = [used([at(3, 2)]), dmg(FOE, 300)];
    const { raw, vfx } = laid(events, near, nearCards);
    const shift = vfx.casts[0]!.impactMs - raw.casts[0]!.impactMs;
    expect(shift).toBeGreaterThan(0);
    expect(vfx.impacts![0]!.atMs).toBeCloseTo(raw.impacts![0]!.atMs + shift, 6);
    expect(vfx.impacts![0]!.atMs).toBeCloseTo(vfx.hits[0]!.atMs, 6);
    expectImpactsOnHits(vfx);
    // 其他欄位不變
    expect(vfx.impacts!.map(({ atMs: _a, ...rest }) => rest)).toEqual(raw.impacts!.map(({ atMs: _a, ...rest }) => rest));
  });

  it("without a timeline (no weapon resolver) impacts stay where vfxFor put them", () => {
    const events = [used([at(3, 2)]), dmg(FOE, 300)];
    const raw = vfxFor(events, near, nearCards);
    const tl = skillTimeline(events, near, nearCards, raw, () => "blade" as never);
    expect(tl).not.toBeNull();
    // 串接器自己是純函式：同輸入同輸出；原本的特效描述沒有被改到
    expect(raw.impacts![0]!.atMs).toBeCloseTo(raw.casts[0]!.impactMs, 6);
    const again = skillTimeline(events, near, nearCards, raw, () => "blade" as never);
    expect(again!.vfx.impacts).toEqual(tl!.vfx.impacts);
  });

  it("two segments (followup): each impact follows its own segment's hit point; the loose hit follows the last", () => {
    const events = [used([at(3, 2)]), dmg(FOE, 300, 3), followup([at(3, 3)]), dmg(FOE2, 300, 6), dmg(FOE, 120, 7, FOE2)];
    const { raw, vfx } = laid(events, near, nearCards);
    expect(vfx.casts.length).toBe(2);
    expect(raw.impacts!.length).toBe(3);
    expect(vfx.impacts![0]!.atMs).toBeCloseTo(vfx.casts[0]!.impactMs, 6);
    expect(vfx.impacts![1]!.atMs).toBeCloseTo(vfx.casts[1]!.impactMs, 6);
    expect(vfx.impacts![2]!.atMs).toBeCloseTo(vfx.casts[1]!.impactMs, 6); // 別人打的放在最後
    expect(vfx.casts[1]!.impactMs).toBeGreaterThan(vfx.casts[0]!.impactMs);
  });

  it("stops and heavy shakes start at the same instant as the hit", () => {
    for (const [events, v, cards, w] of [
      [[used([at(9, 0)]), dmg(FOE, 300)], far, farCards, "staff"],
      [[used([at(3, 2)]), dmg(FOE, 600)], near, nearCards, "blade"],
    ] as const) {
      const { full } = laid([...events], v, cards, w);
      const hit = full.hits[0]!.atMs;
      expect(full.stops?.length).toBe(1);
      expect(full.stops![0]!.atMs).toBeCloseTo(hit, 6);
      expect(full.shakes?.length).toBe(1);
      expect(full.shakes![0]!.atMs).toBeCloseTo(hit, 6);
      expect(full.leadMs).toBeCloseTo(hit, 6);
    }
  });
});

// ---- 音效（AU-3）和畫面的命中點對齊 ----------------------------------------------------------

function response(events: Record<string, unknown>[], v: BattleView): BattleResponse {
  return { battle_id: "b", hero_id: HERO, initial_view: v, view: v, steps: [{ actor_id: HERO, events, view: v, step: { type: "use_skill" } }] } as unknown as BattleResponse;
}
function frameOf(events: Record<string, unknown>[], v: BattleView, cards: VfxCards, weapon: string): Frame {
  return playbackPlan(response(events, v), HERO, "normal", cards, new Set(), () => weapon as never, () => null).frames[0] as Frame;
}

/** 模擬繪製器：效果時鐘每 1 ms 走一次（碰到停頓停住、放慢照倍速），回傳走到 `t` 的實際時間。 */
function realTimeOf(vfx: StepVfx, t: number): number {
  const freezes: Freeze[] = (vfx.stops ?? []).map((s) => ({ at: s.atMs, left: s.ms }));
  const slows = vfx.slow === undefined ? [] : [vfx.slow];
  let clock = 0;
  let real = 0;
  while (clock < t - 1e-6) {
    clock = advanceClock(clock, 1, freezes, slows);
    real += 1;
  }
  return real;
}

describe("hit sound and the visual hit are the same instant (6H-1b / AU-3)", () => {
  it.each([
    ["squeezed far shot (staff)", [used([at(9, 0)]), dmg(FOE, 300)], far, farCards, "staff"],
    ["melee heavy (blade)", [used([at(3, 2)]), dmg(FOE, 600)], near, nearCards, "blade"],
    ["melee light (blade, no stop)", [used([at(3, 2)]), dmg(FOE, 50)], near, nearCards, "blade"],
  ] as const)("%s", (_name, events, v, cards, weapon) => {
    const f = frameOf([...events], v, cards, weapon);
    const vfx = f.vfx as StepVfx;
    const hitCue = f.sfx?.find((c) => c.id === "hit_blunt");
    expect(hitCue).toBeDefined();
    const hitAt = vfx.hits[0]!.atMs;
    // 效果時鐘：命中聲 ＝ 受擊反應 ＝ 扣血（停頓分級）同一刻
    expect(hitCue!.atMs).toBe(Math.round(hitAt));
    expect(vfx.reactions![0]!.atMs).toBe(hitAt);
    expect(vfx.impacts![0]!.atMs).toBe(hitAt);
    for (const s of vfx.stops ?? []) expect(s.atMs).toBe(hitAt);
    // 實際時間：聲音排程用的 `cueRealMs` 和繪製器走到命中那一刻的時間差 ≤ 2 ms；命中聲不會被自己的停頓往後推
    const real = realTimeOf(vfx, hitAt);
    expect(Math.abs(cueRealMs(hitCue!.atMs, vfx, false) - real)).toBeLessThanOrEqual(2);
    expect(Math.abs(cueRealMs(hitCue!.atMs, vfx, false) - hitAt)).toBeLessThanOrEqual(1);
  });

  it("squeeze really happened in the playback frame (the bug case: stop used to sit before the hit)", () => {
    const events = [used([at(9, 0)]), dmg(FOE, 300)];
    const raw = vfxFor(events, far, farCards);
    const f = frameOf(events, far, farCards, "staff");
    const vfx = f.vfx as StepVfx;
    expect(vfx.stops![0]!.atMs).not.toBe(raw.impacts![0]!.atMs);
    expect(vfx.stops![0]!.atMs).toBe(vfx.hits[0]!.atMs);
  });
});
});
