// Phase 6A-4d：一格一格走的時間軸、特殊地表的停頓、敵方 2 倍速、略過、滑倒後滑回。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, StepOut } from "../api/types";
import { moveAnimOf } from "./animation";
import { frameOps, motionMs, playbackPlan, SPEED_SCALE, walkRateOf } from "./playback";
import {
  BEAT_HOLD_MS,
  CAMERA_MAX_PX,
  cameraNudge,
  easeInOut,
  ENEMY_WALK_RATE,
  SLIDE_BACK_MS,
  SLIP_ANGLE,
  slipPose,
  stepMotions,
  TILE_STEP_MS,
  walkDurationMs,
  walkTimeline,
  type WalkAnim,
  type WalkBeat,
} from "./walkAnim";
import fixture from "./fixtures/oil_depot_seed3.json";

const base = (fixture as unknown as BattleResponse).initial_view;
const HERO = "unit_0001";
const FOE = "unit_0004";

const P = (x: number, y: number): Pos => ({ x, y });

/** 主角與一個敵人；`surfaces` 是這一步開始前畫面上的表面。 */
function view(hero: Pos, foe: Pos = P(9, 9), surfaces: Array<[number, number, string]> = []): BattleView {
  const units = base.units
    .filter((u) => u.id === HERO || u.id === FOE)
    .map((u) => ({ ...u, pos: u.id === HERO ? hero : foe, facing: "east" as const }));
  const tiles = base.tiles.map((t) => {
    const s = surfaces.find(([x, y]) => x === t.x && y === t.y);
    return s === undefined ? t : { ...t, surface: s[2] as typeof t.surface };
  });
  return { ...base, units, tiles };
}

let seq = 0;
const ev = (type: string, fields: Record<string, unknown>) => ({ seq: (seq += 1), round: 1, type, ...fields });
const walk = (id: string, a: Pos, b: Pos) => ev("unit_moved", { unit_id: id, from_pos: a, to_pos: b, mode: "walk", cost: 1 });

function motions(events: Record<string, unknown>[], opts: { scale?: number; walkRate?: number; before?: BattleView; after?: BattleView } = {}) {
  const before = opts.before ?? view(P(0, 0));
  return stepMotions(
    events,
    { scale: opts.scale ?? 1, walkRate: opts.walkRate ?? 1, before, after: opts.after ?? before, feedbackMs: 1000 },
    (e) => moveAnimOf(e),
  );
}

function onlyWalk(events: Record<string, unknown>[], opts: Parameters<typeof motions>[1] = {}): WalkAnim {
  const m = motions(events, opts).motions;
  expect(m).toHaveLength(1);
  const first = m[0]!;
  if (first.kind !== "walk") throw new Error("expected a walk");
  return first.walk;
}

const beats = (w: WalkAnim) => w.pieces.filter((p): p is WalkBeat => p.kind === "beat");

describe("逐格時間軸", () => {
  it("每格 0.12 秒：格數 × 120ms，時間軸首尾相接", () => {
    const w = onlyWalk([walk(HERO, P(0, 0), P(1, 0)), walk(HERO, P(1, 0), P(2, 0)), walk(HERO, P(2, 0), P(3, 0))]);
    expect(w.pieces.map((p) => p.kind)).toEqual(["leg", "leg", "leg"]);
    expect(walkDurationMs(w)).toBe(3 * TILE_STEP_MS);
    const tl = walkTimeline(w);
    expect(tl.map((e) => [e.startMs, e.endMs])).toEqual([
      [0, 120],
      [120, 240],
      [240, 360],
    ]);
  });

  it("緩入緩出：兩端慢、中間快，0→0、½→½、1→1", () => {
    expect(easeInOut(0)).toBe(0);
    expect(easeInOut(0.5)).toBeCloseTo(0.5);
    expect(easeInOut(1)).toBe(1);
    expect(easeInOut(0.1)).toBeLessThan(0.1);
    expect(easeInOut(0.9)).toBeGreaterThan(0.9);
    expect(easeInOut(-1)).toBe(0);
    expect(easeInOut(2)).toBe(1);
  });

  it("轉彎時轉身：每格記下面向", () => {
    const w = onlyWalk([walk(HERO, P(0, 0), P(1, 0)), walk(HERO, P(1, 0), P(1, 1)), walk(HERO, P(1, 1), P(0, 1))]);
    expect(w.pieces.map((p) => (p.kind === "leg" ? p.facing : null))).toEqual(["east", "south", "west"]);
  });

  it("不同單位、不相接的走路分成兩段；其他位移照舊", () => {
    const m = motions([
      walk(HERO, P(0, 0), P(1, 0)),
      walk(FOE, P(5, 5), P(5, 4)),
      ev("unit_moved", { unit_id: FOE, from_pos: P(5, 4), to_pos: P(5, 2), mode: "forced", cost: 0 }),
    ]).motions;
    expect(m.map((x) => x.kind)).toEqual(["walk", "walk", "move"]);
  });
});

describe("特殊地表的停頓", () => {
  const trapEvents = () => [
    walk(HERO, P(0, 0), P(1, 0)),
    walk(HERO, P(1, 0), P(2, 0)),
    ev("trap_triggered", { owner_id: FOE, pos: P(2, 0), skill_id: "skill_bear_trap", cause: "enter", unit_id: HERO }),
    ev("damage_dealt", { target_id: HERO, source_id: FOE, amount: 8, crit: false, cause: "attack" }),
    ev("status_applied", { target_id: HERO, status_id: "root", duration: 1, refreshed: false, source_id: FOE }),
  ];

  it("陷阱：在那一格停頓 0.4 秒，停頓後在那一格跳傷害數字與定身圖示", () => {
    const after = view(P(2, 0));
    const w = onlyWalk(trapEvents(), { after });
    expect(w.pieces.map((p) => p.kind)).toEqual(["leg", "leg", "beat"]);
    const [trap] = beats(w);
    expect(trap!.beat).toBe("trap");
    expect(trap!.pos).toEqual(P(2, 0));
    expect(trap!.holdMs).toBe(400);
    expect(trap!.feedback.map((f) => f.kind)).toEqual(["float", "status"]);
    expect(trap!.feedback.every((f) => f.kind === "line" || (f.pos.x === 2 && f.pos.y === 0))).toBe(true);
    expect(walkDurationMs(w)).toBe(2 * TILE_STEP_MS + 400);
  });

  it("停頓時跳過的數字，一步結束時不再跳一次", () => {
    const events = trapEvents();
    const { consumed } = motions(events);
    expect([...consumed].sort()).toEqual([2, 3, 4]);
  });

  it("停頓後的藉機攻擊不算進停頓", () => {
    const events = [
      ...trapEvents().slice(0, 3),
      ev("attack_rolled", { attacker_id: FOE, target_id: HERO, hit: true }),
      ev("damage_dealt", { target_id: HERO, source_id: FOE, amount: 3, crit: false, cause: "attack" }),
    ];
    const { consumed } = motions(events);
    expect(consumed.has(3)).toBe(false);
    expect(consumed.has(4)).toBe(false);
  });

  it("冰面檢定通過：冰花，不停；失敗：滑倒停頓，跳倒地圖示", () => {
    const pass = onlyWalk([
      walk(HERO, P(0, 0), P(1, 0)),
      ev("surface_entered", { unit_id: HERO, pos: P(1, 0), surface: "ice" }),
      ev("check_rolled", { unit_id: HERO, reason: "surface:ice", success: true, fail_status: "prone" }),
      walk(HERO, P(1, 0), P(2, 0)),
    ]);
    expect(beats(pass).map((b) => [b.beat, b.holdMs])).toEqual([["ice", 0]]);
    expect(pass.pieces.map((p) => p.kind)).toEqual(["leg", "beat", "leg"]);

    const slip = onlyWalk([
      walk(HERO, P(0, 0), P(1, 0)),
      ev("surface_entered", { unit_id: HERO, pos: P(1, 0), surface: "ice" }),
      ev("check_rolled", { unit_id: HERO, reason: "surface:ice", success: false, fail_status: "prone" }),
      ev("status_applied", { target_id: HERO, status_id: "prone", duration: null, refreshed: false, source_id: null }),
    ]);
    const [b] = beats(slip);
    expect(b!.beat).toBe("slip");
    expect(b!.holdMs).toBe(BEAT_HOLD_MS.slip);
    expect(b!.feedback.filter((f) => f.kind === "status")).toHaveLength(1);
  });

  it("火：腳下冒火後跳燃燒；油：畫面上原本是油就濺油", () => {
    const w = onlyWalk(
      [
        walk(HERO, P(0, 0), P(1, 0)),
        ev("surface_entered", { unit_id: HERO, pos: P(1, 0), surface: "fire" }),
        ev("status_applied", { target_id: HERO, status_id: "burning", duration: 2, refreshed: false, source_id: null }),
        walk(HERO, P(1, 0), P(2, 0)),
        walk(HERO, P(2, 0), P(3, 0)),
      ],
      { before: view(P(0, 0), P(9, 9), [[2, 0, "oil"]]) },
    );
    expect(beats(w).map((b) => [b.beat, b.pos.x, b.holdMs])).toEqual([
      ["fire", 1, BEAT_HOLD_MS.fire],
      ["oil", 2, BEAT_HOLD_MS.oil],
    ]);
    expect(beats(w)[0]!.feedback.map((f) => f.kind)).toEqual(["status"]);
  });
});

describe("滑倒後滑回最近的空格（倒在友軍格）", () => {
  it("滑倒之後同一人的傳送改成短短的滑行，不淡出淡入", () => {
    const w = onlyWalk([
      walk(HERO, P(0, 0), P(1, 0)),
      ev("surface_entered", { unit_id: HERO, pos: P(1, 0), surface: "ice" }),
      ev("check_rolled", { unit_id: HERO, reason: "surface:ice", success: false, fail_status: "prone" }),
      ev("status_applied", { target_id: HERO, status_id: "prone", duration: null, refreshed: false, source_id: null }),
      ev("unit_moved", { unit_id: HERO, from_pos: P(1, 0), to_pos: P(0, 0), mode: "teleport", cost: 0 }),
    ]);
    expect(w.pieces.map((p) => p.kind)).toEqual(["leg", "beat", "slide"]);
    const slide = w.pieces[2]!;
    expect(slide.kind === "slide" && slide.to).toEqual(P(0, 0));
    expect(slide.kind === "slide" && slide.durationMs).toBe(SLIDE_BACK_MS);
  });

  it("沒有滑倒的傳送照舊淡出淡入", () => {
    const m = motions([
      walk(HERO, P(0, 0), P(1, 0)),
      ev("unit_moved", { unit_id: HERO, from_pos: P(1, 0), to_pos: P(5, 5), mode: "teleport", cost: 0 }),
    ]).motions;
    expect(m.map((x) => x.kind)).toEqual(["walk", "move"]);
  });
});

describe("播放速度與敵方 2 倍速", () => {
  const events = () => [
    walk(FOE, P(5, 0), P(4, 0)),
    walk(FOE, P(4, 0), P(3, 0)),
    ev("trap_triggered", { owner_id: HERO, pos: P(3, 0), skill_id: "skill_bear_trap", cause: "enter", unit_id: FOE }),
  ];

  it("敵方 2 倍速：每格減半，停頓保留", () => {
    const w = onlyWalk(events(), { walkRate: ENEMY_WALK_RATE });
    expect(w.pieces.map((p) => (p.kind === "beat" ? p.holdMs : p.durationMs))).toEqual([60, 60, 400]);
  });

  it("慢速：每格與停頓都 2 倍", () => {
    const w = onlyWalk(events(), { scale: SPEED_SCALE.slow });
    expect(w.pieces.map((p) => (p.kind === "beat" ? p.holdMs : p.durationMs))).toEqual([240, 240, 800]);
  });

  function response(actor: string, evs: Record<string, unknown>[]): BattleResponse {
    const r = fixture as unknown as BattleResponse;
    const initial = view(P(0, 0), P(5, 0));
    const step: StepOut = { actor_id: actor, step: { type: "move" } as never, events: evs, view: view(P(0, 0), P(3, 0)) };
    return { ...r, initial_view: initial, steps: [step], view: step.view };
  }

  it("敵方回合（和主角不同陣營）走路 2 倍速；主角照常", () => {
    const r = response(FOE, events());
    expect(walkRateOf(r.steps[0]!, r.initial_view, HERO)).toBe(2);
    expect(walkRateOf({ ...r.steps[0]!, actor_id: HERO }, r.initial_view, HERO)).toBe(1);
    const plan = playbackPlan(r, HERO, "normal");
    expect(plan.frames[0]!.motions.map(motionMs)).toEqual([60 + 60 + 400]);
    expect(frameOps(plan.frames[0]!).map((o) => o.op)).toContain("walk");
  });

  it("停頓時已跳過的數字不會在一步結束時重複", () => {
    const evs = [...events(), ev("damage_dealt", { target_id: FOE, source_id: HERO, amount: 8, crit: false, cause: "attack" })];
    const plan = playbackPlan(response(FOE, evs), HERO, "normal");
    expect(plan.frames[0]!.feedback).toEqual([]);
    const walkMotion = plan.frames[0]!.motions[0]!;
    expect(walkMotion.kind === "walk" && beats(walkMotion.walk)[0]!.feedback.length).toBe(1);
  });

  it("略過：沒有走路動畫，直接到終點", () => {
    const plan = playbackPlan(response(FOE, events()), HERO, "skip");
    expect(plan.frames).toHaveLength(1);
    expect(plan.frames[0]!.motions).toEqual([]);
    expect(frameOps(plan.frames[0]!).map((o) => o.op)).not.toContain("walk");
  });
});

describe("畫面小算式", () => {
  it("滑倒姿勢：開始站著；倒地後轉 SLIP_ANGLE，腳底留在往前溜的位置", () => {
    const feet = 11;
    const start = slipPose(0, "east", feet);
    expect([start.x, start.y, Math.abs(start.rotation)]).toEqual([0, 0, 0]);
    const end = slipPose(1, "east", feet);
    expect(Math.abs(end.rotation)).toBeCloseTo(SLIP_ANGLE);
    // 腳底 (0, feet) 旋轉後加上位移 ＝ (往前溜 6, feet)
    const footX = end.x - feet * Math.sin(end.rotation);
    const footY = end.y + feet * Math.cos(end.rotation);
    expect(footX).toBeCloseTo(6);
    expect(footY).toBeCloseTo(feet);
    expect(Math.sign(slipPose(1, "west", feet).rotation)).toBe(-Math.sign(end.rotation));
  });

  it("鏡頭只稍微跟著：往畫面中央帶一點，夾在上限內", () => {
    const size = { width: 480, height: 480 };
    expect(cameraNudge({ x: 240, y: 240 }, size)).toEqual({ x: 0, y: 0 });
    const far = cameraNudge({ x: 480, y: 0 }, size);
    expect(far.x).toBe(-CAMERA_MAX_PX);
    expect(far.y).toBe(CAMERA_MAX_PX);
    const near = cameraNudge({ x: 290, y: 240 }, size);
    expect(near.x).toBeLessThan(0);
    expect(near.x).toBeGreaterThan(-CAMERA_MAX_PX);
  });
});
