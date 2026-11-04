// 6H-1b：停頓時間點跟著技能時間軸移（`skillSequence.retime` 連 `impacts` 一起換算）。
// 壓縮（一招超過 1.8 秒）或起手移動後，每個扣血的時間都等於對應的命中點；停頓、微震、命中聲都在同一刻。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, SkillCard } from "../api/types";
import { cueRealMs } from "../audio/battleSfx";
import { advanceClock, type Freeze } from "../render/hitStop";
import { withImpact } from "./impact";
import { playbackPlan, type Frame } from "./playback";
import { skillTimeline, SKILL_CAP_MS } from "./skillSequence";
import { withSpecials } from "./specials";
import { vfxFor, type StepVfx, type VfxCards } from "./vfx";

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
