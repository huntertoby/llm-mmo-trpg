// Phase 6M-3：衝刺（這個回合跑過）之後的步行用跑步片段；跑步只看畫面，不改時間軸（每格照 6A-4d）。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StepOut } from "../api/types";
import { moveAnimOf } from "./animation";
import { playbackPlan } from "./playback";
import { stepMotions, TILE_STEP_MS, trackRunning, walkDurationMs, type WalkAnim } from "./walkAnim";
import fixture from "./fixtures/oil_depot_seed3.json";

const base = (fixture as unknown as BattleResponse).initial_view;
const HERO = "unit_0001";
const P = (x: number, y: number): Pos => ({ x, y });
const view: BattleView = { ...base, units: base.units.filter((u) => u.id === HERO).map((u) => ({ ...u, pos: P(0, 0), facing: "east" as const })) };

let seq = 0;
const ev = (type: string, fields: Record<string, unknown>) => ({ seq: (seq += 1), round: 1, type, ...fields });
const walk = (a: Pos, b: Pos) => ev("unit_moved", { unit_id: HERO, from_pos: a, to_pos: b, mode: "walk", cost: 1 });
const ran = () => ev("unit_ran", { unit_id: HERO, bonus: 3, move_points: 6 });

function walkOf(events: Record<string, unknown>[], running?: Set<string>): WalkAnim {
  const m = stepMotions(events, { scale: 1, walkRate: 1, before: view, after: view, feedbackMs: 1000, ...(running === undefined ? {} : { running }) }, (e) => moveAnimOf(e)).motions;
  const w = m.find((x) => x.kind === "walk");
  if (w === undefined || w.kind !== "walk") throw new Error("no walk");
  return w.walk;
}

describe("6M-3：衝刺之後的步行用跑步片段", () => {
  it("沒有跑過：走路（gait 省略）", () => {
    expect(walkOf([walk(P(0, 0), P(1, 0))]).gait).toBeUndefined();
    expect(walkOf([walk(P(0, 0), P(1, 0))], new Set()).gait).toBeUndefined();
  });

  it("同一步裡先跑再走：跑步；時間軸不變（每格照 6A-4d）", () => {
    const w = walkOf([ran(), walk(P(0, 0), P(1, 0)), walk(P(1, 0), P(2, 0))], new Set());
    expect(w.gait).toBe("run");
    expect(walkDurationMs(w)).toBe(2 * TILE_STEP_MS);
  });

  it("跑過的狀態跨回應保留，回合開始或結束時清掉；走完才結束回合不影響這一段", () => {
    const running = new Set<string>();
    walkOf([ran()].concat(walk(P(0, 0), P(1, 0))), running);
    expect(running.has(HERO)).toBe(true);
    // 下一個回應：繼續走（同一回合）
    expect(walkOf([walk(P(1, 0), P(2, 0)), ev("turn_ended", { unit_id: HERO, ap_carried: 0 })], running).gait).toBe("run");
    expect(running.has(HERO)).toBe(false);
    // 新的回合：走路
    expect(walkOf([ev("turn_started", { unit_id: HERO, ap: 2, move_points: 3 }), walk(P(2, 0), P(3, 0))], running).gait).toBeUndefined();
  });

  it("trackRunning：只看 unit_ran／turn_started／turn_ended，別人的事件不影響", () => {
    const s = new Set<string>(["unit_0002"]);
    trackRunning(s, { type: "unit_ran", unit_id: HERO } as never);
    trackRunning(s, { type: "turn_ended", unit_id: "unit_0003" } as never);
    trackRunning(s, { type: "damage_dealt", target_id: HERO } as never);
    expect([...s].sort()).toEqual([HERO, "unit_0002"]);
  });

  it("playbackPlan：跑過的集合由呼叫端保留；略過速度也會更新", () => {
    const step = (events: Record<string, unknown>[]): StepOut => ({ actor_id: HERO, step: null, events, view } as unknown as StepOut);
    const res = (events: Record<string, unknown>[]): BattleResponse => ({ ...(fixture as unknown as BattleResponse), initial_view: view, view, steps: [step(events)] });
    const running = new Set<string>();
    playbackPlan(res([ran()]), HERO, "skip", {}, running);
    expect(running.has(HERO)).toBe(true);
    const plan = playbackPlan(res([walk(P(0, 0), P(1, 0))]), HERO, "normal", {}, running);
    const m = plan.frames[0]!.motions[0]!;
    expect(m.kind === "walk" && m.walk.gait).toBe("run");
  });
});
