// AR-SK3：重擲的演出描述與時間軸（`rerollFx.ts`）、接到播放計畫（`playback.ts`：骰子層在出招前、浮字「重擲！」延到 1250 ms）。
// 事件是真引擎跑的（`dev/fixtures/sk3Events.json`）。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, StepOut, UnitView } from "../api/types";
import fixture from "../dev/fixtures/sk3Events.json";
import { WORD_REROLL, type FloatItem } from "./feedback";
import { frameOps, playbackPlan, SPEED_SCALE } from "./playback";
import { adoptPx, ADOPT_MIN_PX, DIE_MIN_PX, DIE_R, dieDy, dieMK, envelope, jumpMax, REROLL_FLOAT_AT_MS, REROLL_MS, rerollFrame, rerollFxOf, UPPER_HP_BOTTOM } from "./rerollFx";
import { tile, unit } from "./testFixtures";

type FixtureCase = { events: Record<string, unknown>[] };
const DATA = fixture as unknown as Record<string, FixtureCase>;
const HERO = "unit_0001";

function view(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < 7; y++) for (let x = 0; x < 9; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: 9, height: 7, tiles, objects: [], units, traps: [], turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const UNITS = (): UnitView[] => [unit(HERO, "ally", 4, 3), unit("unit_0002", "enemy", 5, 3), unit("unit_0003", "ally", 4, 4)];
const resOf = (events: Record<string, unknown>[], actor: string): BattleResponse => {
  const v = view(UNITS());
  return { steps: [{ actor_id: actor, events, view: v, step: { type: "attack", unit_id: actor } } as unknown as StepOut], initial_view: v, view: v } as unknown as BattleResponse;
};

describe("描述（rerollFxOf）", () => {
  it("變壞：盜賊擲 19 → 2，反應者＝戰士，算第二次、取較差", () => {
    expect(rerollFxOf(DATA.reroll_worse!.events)).toEqual([{ rollerId: "unit_0002", reactorId: HERO, first: 19, second: 2, keptFirst: false, better: false }]);
  });
  it("變好：戰士擲 1 → 18，反應者＝法師，算第二次、取較好", () => {
    expect(rerollFxOf(DATA.reroll_better!.events)).toEqual([{ rollerId: HERO, reactorId: "unit_0003", first: 1, second: 18, keptFirst: false, better: true }]);
  });
  it("沒有重擲、欄位不齊時沒有演出", () => {
    expect(rerollFxOf(DATA.exploit!.events)).toEqual([]);
    expect(rerollFxOf([{ type: "attack_rerolled", attacker_id: "a" }])).toEqual([]);
  });
});

describe("位置與畫面下限（移植需求第 4 項）", () => {
  it("骰子半徑 ≥ 9 畫面 px：1600 寬（1.31）倍率 1，800 寬（0.53）約 1.54", () => {
    expect(dieMK(1.31)).toBe(1);
    expect(dieMK(0.53)).toBeCloseTo(9 / (11 * 0.53), 6);
    for (const s of [0.4, 0.53, 0.8, 1, 1.31, 2]) expect(DIE_R * dieMK(s) * s).toBeGreaterThanOrEqual(DIE_MIN_PX - 1e-9);
  });
  it("「採用」字級 ≥ 10 畫面 px（12 模型 px）", () => {
    expect(adoptPx(1.31)).toBe(12);
    for (const s of [0.4, 0.53, 0.8, 1, 1.31]) expect(adoptPx(s) * s).toBeGreaterThanOrEqual(ADOPT_MIN_PX - 1e-9);
  });
  it("骰子中心：1600 寬在格子中心往上約 8.1、800 寬往下約 0.9（樣張 dieDy）；整組上緣收在上一排血條下緣往下 1", () => {
    expect(dieDy(dieMK(1.31))).toBeCloseTo(-8.06, 1);
    expect(dieDy(dieMK(0.53))).toBeCloseTo(0.9, 0);
    for (const s of [0.53, 1.31]) expect(dieDy(dieMK(s)) - envelope(dieMK(s))).toBeCloseTo(UPPER_HP_BOTTOM + 1, 6);
  });
  it("巨型單位、頭目：上緣改用頭頂（呼叫端給 unitTopY）", () => {
    expect(dieDy(1, -80)).toBeCloseTo(-80 + 1 + envelope(1), 6);
  });
  it("新骰子跳起來不超過採用時的上緣", () => {
    const mk = dieMK(0.53), f = rerollFxOf(DATA.reroll_better!.events)[0]!;
    for (let t = 560; t <= 960; t += 10) {
      const fr = rerollFrame(t, f, mk);
      if (fr.fresh !== null) expect(fr.fresh.y - DIE_R * mk).toBeGreaterThanOrEqual(-envelope(mk) - 1e-9);
    }
    expect(jumpMax(mk)).toBeGreaterThan(0);
  });
});

describe("時間軸（美術 2 節第 2 版＋N1）", () => {
  const worse = rerollFxOf(DATA.reroll_worse!.events)[0]!;
  const keepFirst = { ...worse, first: 6, second: 15, keptFirst: true };
  it("0–160 第一次彈出、260 前停住；560–660 往左退、變灰", () => {
    expect(rerollFrame(0, worse, 1).old.k).toBe(0);
    expect(rerollFrame(110, worse, 1).old.k).toBeCloseTo(1.15, 6);
    expect(rerollFrame(200, worse, 1).old).toMatchObject({ x: 0, y: 0, k: 1, face: 19, dim: false });
    expect(rerollFrame(200, worse, 1).fresh).toBeNull();
    const back = rerollFrame(700, worse, 1).old;
    expect(back).toMatchObject({ x: -30, y: 2, dim: true });
    expect(back.k).toBeCloseTo(0.84, 6);
  });
  it("580–860 新骰子轉、骰面閃換；860 之後是第二次的點數", () => {
    const a = rerollFrame(700, worse, 1).fresh!, b = rerollFrame(1000, worse, 1).fresh!;
    expect(a.rot).toBeGreaterThan(0);
    expect(a.face).not.toBe(2);
    expect(b).toMatchObject({ face: 2, rot: 0 });
  });
  it("比較：算第二次時第二次金環＋採用、第一次紅斜槓；算第一次（被逼重擲反而變好）時反過來", () => {
    const a = rerollFrame(1120, worse, 1);
    expect(a.fresh!.ring).toBe(1);
    expect(a.old.cross).toBe(1);
    expect(a.adoptOld).toBe(false);
    expect(a.adoptA).toBe(1);
    expect(a.cmpUp).toBe(false);
    const b = rerollFrame(1120, keepFirst, 1);
    expect(b.old.ring).toBe(1);
    expect(b.old.k).toBeCloseTo(1.1, 6);
    expect(b.fresh!.cross).toBe(1);
    expect(b.fresh!.dim).toBe(true);
    expect(b.adoptOld).toBe(true);
    expect(b.cmpUp).toBe(true);
  });
  it("1250–1450 淡出；之後不畫", () => {
    expect(rerollFrame(1250, worse, 1).fade).toBe(1);
    expect(rerollFrame(1350, worse, 1).fade).toBeCloseTo(0.5, 6);
    expect(rerollFrame(1450, worse, 1).fade).toBe(0);
  });
});

describe("接到播放計畫（移植需求第 2、3 項）", () => {
  it("骰子層排在出招之前；浮字「重擲！」從回饋搬到骰子比較完（1250 ms，照速度縮放）才出，字、顏色不變", () => {
    for (const [id, actor, tone] of [["reroll_worse", "unit_0002", "bad"], ["reroll_better", HERO, "good"]] as const) {
      const plan = playbackPlan(resOf(DATA[id]!.events, actor), HERO, "normal");
      const fr = plan.frames[0]!;
      const scale = SPEED_SCALE.normal;
      expect(fr.reroll?.fx).toHaveLength(1);
      expect(fr.reroll?.durationMs).toBe(Math.round(REROLL_MS * scale));
      expect(fr.reroll?.floats.map((f) => f.atMs)).toEqual([Math.round(REROLL_FLOAT_AT_MS * scale)]);
      const word = fr.reroll!.floats[0]!.items[0] as FloatItem;
      expect(word).toMatchObject({ kind: "float", text: WORD_REROLL, tone });
      expect(fr.feedback.some((i) => i.kind === "float" && i.text === WORD_REROLL)).toBe(false);
      const ops = frameOps(fr).map((o) => o.op);
      expect(ops.indexOf("reroll")).toBeGreaterThan(-1);
      if (ops.includes("vfx")) expect(ops.indexOf("reroll")).toBeLessThan(ops.indexOf("vfx"));
    }
  });
  it("減少動態：不播骰子層，浮字照舊在回饋裡", () => {
    const plan = playbackPlan(resOf(DATA.reroll_worse!.events, "unit_0002"), HERO, "normal", {}, new Set(), undefined, undefined, undefined, true);
    const fr = plan.frames[0]!;
    expect(fr.reroll).toBeUndefined();
    expect(fr.feedback.some((i) => i.kind === "float" && i.text === WORD_REROLL)).toBe(true);
  });
  it("沒有重擲的步驟不變（沒有 reroll 鍵）", () => {
    const plan = playbackPlan(resOf(DATA.exploit!.events, HERO), HERO, "normal");
    expect("reroll" in plan.frames[0]!).toBe(false);
  });
});
