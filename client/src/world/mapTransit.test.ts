// Phase 6M-4：進出門、換地圖的片段時間軸與和畫面淡出淡入的銜接（總長 ≤ 0.6 秒）。
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FieldView } from "../api/types";
import { ARRIVE_MS, arriveFrame, DOOR_SHRINK, FADE_LEAD_MS, LEAVE_MS, leaveFrame, STAGE_FADE_MS, transitTotalMs } from "../render/doorClips";
import { FIELD_HERO } from "./fieldModel";
import { arriveFacing, arriveMap, leaveMap, mapTransit, stepFacing, type TransitRenderer } from "./mapTransit";

function field(over: Partial<FieldView>): FieldView {
  return { map_id: "m", me: { x: 2, y: 2, facing: "s" }, doors: [], exits: [], ...over } as unknown as FieldView;
}

describe("6M-4：片段時間軸", () => {
  it("總長 ＝ 80 ＋ 220 ＋ 220 ＝ 520 毫秒（≤ 600）；畫面淡出、淡入和 world.css 的 0.22 秒相同", () => {
    expect(STAGE_FADE_MS).toBe(220);
    expect(transitTotalMs()).toBe(520);
    expect(transitTotalMs()).toBeLessThanOrEqual(600);
    expect(LEAVE_MS).toBeLessThanOrEqual(FADE_LEAD_MS + STAGE_FADE_MS); // 小人片段在畫面淡完之前播完
    expect(ARRIVE_MS).toBeLessThanOrEqual(STAGE_FADE_MS);
  });

  it("進門：從站好縮小到 0.6、往上移、淡出；出門反過來，最後一格站好", () => {
    expect(leaveFrame("door", "north", 0)).toEqual({ scale: 1, alpha: 1, dx: 0, dy: 0, rise: 0, pose: null });
    const end = leaveFrame("door", "north", 1);
    expect(end.scale).toBeCloseTo(DOOR_SHRINK, 9);
    expect(end.alpha).toBe(0);
    expect(end.rise).toBeGreaterThan(0);
    const a0 = arriveFrame("door", "south", 0);
    expect(a0.alpha).toBe(0);
    expect(a0.scale).toBeCloseTo(DOOR_SHRINK, 9);
    expect(arriveFrame("door", "south", 1)).toEqual({ scale: 1, alpha: 1, dx: 0, dy: 0, rise: 0, pose: null });
    for (let u = 0; u < 1; u += 0.1) {
      expect(leaveFrame("door", "north", u + 0.1).alpha).toBeLessThanOrEqual(leaveFrame("door", "north", u).alpha);
      expect(arriveFrame("door", "north", u + 0.1).scale).toBeGreaterThanOrEqual(arriveFrame("door", "north", u).scale);
    }
  });

  it("邊緣出口：照走的方向走出半格並淡出（播走路姿勢）；新地圖從反方向一格外走進來一步", () => {
    const out = leaveFrame("edge", "east", 1);
    expect(out.dx).toBeCloseTo(0.5, 9);
    expect(out.dy).toBe(0);
    expect(out.alpha).toBe(0);
    expect(leaveFrame("edge", "east", 0.5).pose).not.toBeNull();
    const in0 = arriveFrame("edge", "east", 0);
    expect(in0.dx).toBe(-1);
    expect(in0.alpha).toBe(0);
    expect(arriveFrame("edge", "east", 0.6).alpha).toBeGreaterThan(0.9);
    expect(arriveFrame("edge", "east", 1)).toEqual({ scale: 1, alpha: 1, dx: 0, dy: 0, rise: 0, pose: null });
    expect(arriveFrame("edge", "north", 0).dy).toBe(1);
  });
});

describe("6M-4：換地圖播哪一段", () => {
  const before = field({ doors: [{ id: "d", x: 3, y: 1, to: "inn", to_name_zh: "客棧" }], exits: [{ id: "x", cells: [[0, 2], [0, 3]], to: "road", to_name_zh: "路" }] } as Partial<FieldView>);

  it("最後一格是門＝進門（朝走進去的方向），是出口＝邊緣；其他（傳送石等）沒有片段", () => {
    expect(mapTransit(before, { x: 3, y: 2 }, { x: 3, y: 1 })).toEqual({ kind: "door", facing: "north" });
    expect(mapTransit(before, { x: 1, y: 2 }, { x: 0, y: 2 })).toEqual({ kind: "edge", facing: "west" });
    expect(mapTransit(before, { x: 1, y: 1 }, { x: 2, y: 1 })).toBeNull();
    expect(mapTransit(before, { x: 1, y: 1 }, undefined)).toBeNull();
    // 沒有走任何一步（站在門上）時照目前的朝向
    expect(mapTransit(before, { x: 3, y: 1 }, { x: 3, y: 1 })).toEqual({ kind: "door", facing: "south" });
    expect(stepFacing({ x: 0, y: 0 }, { x: 1, y: 1 })).toBeNull();
  });

  it("抵達的朝向：邊緣照走進來的方向；出門照伺服器的朝向（不轉身）", () => {
    const after = field({ me: { x: 5, y: 5, facing: "e" } } as Partial<FieldView>);
    expect(arriveFacing({ kind: "edge", facing: "west" }, after)).toBe("west");
    expect(arriveFacing({ kind: "door", facing: "north" }, after)).toBe("east");
  });
});

describe("6M-4：和畫面淡出淡入銜接（假計時器）", () => {
  const g = globalThis as { window?: unknown };
  let saved: unknown;
  beforeEach(() => {
    vi.useFakeTimers();
    saved = g.window;
    g.window = globalThis;
  });
  afterEach(() => {
    vi.useRealTimers();
    g.window = saved;
  });

  function fakeRenderer(log: string[]): TransitRenderer {
    const at = () => Date.now();
    const t0 = at();
    return {
      playLeave: (id, kind, facing, ms) => (log.push(`leave ${id} ${kind} ${facing} ${ms} @${at() - t0}`), new Promise((r) => setTimeout(r, ms))),
      playArrive: (id, kind, facing, ms) => (log.push(`arrive ${id} ${kind} ${facing} ${ms} @${at() - t0}`), new Promise((r) => setTimeout(r, ms))),
      nextDraw: () => (log.push(`draw @${at() - t0}`), new Promise((r) => setTimeout(r, 16))),
    };
  }

  it("離開：片段馬上開始，80 毫秒後畫面淡出，300 毫秒時換地圖；抵達片段和淡入同時播，整段 ≤ 600 毫秒", async () => {
    const log: string[] = [];
    const r = fakeRenderer(log);
    const fades: string[] = [];
    const start = Date.now();
    const leaving = leaveMap(r, { kind: "door", facing: "north" }, (on) => fades.push(`${on} @${Date.now() - start}`), () => false);
    await vi.advanceTimersByTimeAsync(400);
    await leaving;
    expect(log[0]).toBe(`leave ${FIELD_HERO} door north ${LEAVE_MS} @0`);
    expect(fades).toEqual([`true @${FADE_LEAD_MS}`]);
    const left = Date.now() - start;
    expect(left).toBeGreaterThanOrEqual(FADE_LEAD_MS + STAGE_FADE_MS);
    const after = field({ me: { x: 1, y: 1, facing: "s" } } as Partial<FieldView>);
    const arriving = arriveMap({ current: r }, { kind: "door", facing: "north" }, after, () => false);
    await vi.advanceTimersByTimeAsync(400);
    await arriving;
    expect(log.some((l) => l.startsWith(`arrive ${FIELD_HERO} door south ${ARRIVE_MS}`))).toBe(true);
    // 換地圖（300）＋ 等新地圖畫好（一幀）＋ 抵達片段（220）
    expect(300 + 16 + ARRIVE_MS).toBeLessThanOrEqual(600);
  });

  it("沒有繪製器時照舊只淡出（不會卡住）", async () => {
    const fades: boolean[] = [];
    const p = leaveMap(null, { kind: "edge", facing: "east" }, (on) => fades.push(on), () => false);
    await vi.advanceTimersByTimeAsync(400);
    await p;
    expect(fades).toEqual([true]);
    await arriveMap({ current: null }, { kind: "edge", facing: "east" }, field({}), () => false);
  });
});
