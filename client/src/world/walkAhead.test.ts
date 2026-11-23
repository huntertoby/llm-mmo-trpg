// WM-1 第 2 項：前端先走（`walkAhead.ts`）。假的伺服器與動畫，用假時鐘量時間。
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FieldView, Pos, WorldView } from "../api/types";
import { HeldKeys } from "./heldKeys";
import { aheadTarget, devWalkMs, leadCap, pullBackPath, WalkAhead, WALK_AHEAD, type ShownHero } from "./walkAhead";

const STEP = 120;

/** 10×3 的空地；(9, 1) 是出口。主角站在 (0, 1)。 */
function open(over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: 30 }, (_, i) => ({ x: i % 10, y: Math.floor(i / 10), height: 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: "plain",
    name_zh: "空地",
    region: "cloud_ridge",
    location: "plain",
    interior: false,
    width: 10,
    height: 3,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [],
    exits: [{ id: "east", cells: [[9, 1]], to: "far", to_name_zh: "遠方" }],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [],
    me: { x: 0, y: 1, facing: "e" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] },
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
    ...over,
  } as FieldView;
}

const ENEMY = { id: "wolf", x: 5, y: 0 } as unknown as NonNullable<FieldView["enemies"]>[number];

function reply(field: FieldView, over: Partial<WorldView> = {}): WorldView {
  return { field, encounter: null, battle_id: null, ...over } as unknown as WorldView;
}

type Answer = (cell: Pos, field: FieldView) => WorldView | null | "hang";

/** 假的世界：`rtt` 毫秒後照 `answer` 回（預設：走到送的那一格）。 */
function harness(start: FieldView, answer: Answer = (cell, f) => reply({ ...f, me: { ...f.me, x: cell.x, y: cell.y } }), rtt = 30) {
  const keys = new HeldKeys();
  let cur: FieldView | null = start;
  const t0 = Date.now();
  const steps: Array<{ at: number; to: Pos }> = [];
  const sent: Array<{ at: number; cell: Pos }> = [];
  const commits: Array<{ me: Pos; shown: ShownHero | null }> = [];
  const slides: Pos[][] = [];
  const portals: Pos[] = [];
  let inflight = 0;
  let maxInflight = 0;
  let failed = 0;
  const run = new WalkAhead({
    field: () => cur,
    blocked: () => false,
    alive: () => true,
    peek: () => keys.peek(),
    take: () => void keys.take(),
    release: () => keys.clear(),
    send: (cell) => {
      sent.push({ at: Date.now() - t0, cell });
      inflight += 1;
      maxInflight = Math.max(maxInflight, inflight);
      const out = answer(cell, cur!);
      if (out === "hang") return new Promise<WorldView | null>(() => undefined);
      return new Promise((resolve) =>
        setTimeout(() => {
          inflight -= 1;
          resolve(out);
        }, rtt),
      );
    },
    step: (_f, _from, to) => {
      steps.push({ at: Date.now() - t0, to });
      return new Promise((resolve) => setTimeout(resolve, STEP));
    },
    slideBack: (_f, _from, path) => {
      slides.push([...path]);
      return new Promise((resolve) => setTimeout(resolve, STEP * path.length));
    },
    others: () => Promise.resolve(),
    commit: (view, shown) => {
      cur = view.field ?? null;
      commits.push({ me: { x: view.field!.me.x, y: view.field!.me.y }, shown });
    },
    fade: () => Promise.resolve(),
    portal: (cell) => {
      portals.push(cell);
      return Promise.resolve(false);
    },
    failed: () => {
      failed += 1;
    },
  });
  return { keys, run, steps, sent, commits, slides, portals, now: () => cur, stats: () => ({ maxInflight, failed }) };
}

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("WM-1 前端先走：設定與小函式", () => {
  it("領先上限在設定檔：預設 2 格，看得到敵人 1 格", () => {
    expect(WALK_AHEAD).toEqual({ lead_max: 2, lead_max_enemy_seen: 1 });
    expect(leadCap(open())).toBe(2);
    expect(leadCap(open({ enemies: [ENEMY] }))).toBe(1);
    expect(leadCap(open({ enemies: [ENEMY] }), { lead_max: 3, lead_max_enemy_seen: 0 })).toBe(0);
  });

  it("出口、門、傳送石不先走（標成 portal）；走不過去為 null", () => {
    const f = open();
    expect(aheadTarget(f, { x: 0, y: 1 }, "right")).toEqual({ kind: "step", to: { x: 1, y: 1 } });
    expect(aheadTarget(f, { x: 8, y: 1 }, "right")).toEqual({ kind: "portal", to: { x: 9, y: 1 } });
    expect(aheadTarget(f, { x: 0, y: 1 }, "left")).toBeNull();
  });

  it("開發用慢動作只在 ?dev=1 時生效", () => {
    expect(devWalkMs("?walkms=900")).toBeNull();
    expect(devWalkMs("?dev=1&walkms=900")).toBe(900);
    expect(devWalkMs("?dev=1&walkms=abc")).toBeNull();
    expect(devWalkMs("?dev=1")).toBeNull();
  });

  it("拉回路線：在先走的路上就沿原路倒退，不在就直接滑過去", () => {
    const chain = [
      { x: 0, y: 1 },
      { x: 1, y: 1 },
      { x: 2, y: 1 },
    ];
    expect(pullBackPath(chain, { x: 0, y: 1 })).toEqual([
      { x: 1, y: 1 },
      { x: 0, y: 1 },
    ]);
    expect(pullBackPath(chain, { x: 2, y: 1 })).toEqual([]);
    expect(pullBackPath(chain, { x: 5, y: 0 })).toEqual([{ x: 5, y: 0 }]);
  });
});

describe("WM-1 前端先走：走路迴圈", () => {
  it("按住連走：第 1、2 步之間不停頓（每 120 ms 一格，不等 500 ms 的按鍵重複）", async () => {
    const h = harness(open());
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(STEP * 4 + 10);
    h.keys.release("right");
    await vi.advanceTimersByTimeAsync(1000);
    await done;
    const at = h.steps.map((s) => s.at);
    expect(at.slice(0, 4)).toEqual([0, STEP, STEP * 2, STEP * 3]);
    expect(h.steps[0]!.to).toEqual({ x: 1, y: 1 });
    // 請求照順序一個一個送，主角不等回應
    expect(h.stats().maxInflight).toBe(1);
    expect(h.sent.map((s) => s.cell.x)).toEqual(h.steps.map((s) => s.to.x));
    // 走完都確認了：最後一次套用不再領先
    expect(h.commits[h.commits.length - 1]!.shown).toBeNull();
    expect(h.now()!.me.x).toBe(h.steps.length);
  });

  it("放開後不會多走：最多只走完正在播的那一格", async () => {
    const h = harness(open());
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(STEP + 50); // 第 2 格正在播
    h.keys.release("right");
    await vi.advanceTimersByTimeAsync(1000);
    await done;
    expect(h.steps).toHaveLength(2);
    expect(h.now()!.me).toMatchObject({ x: 2, y: 1 });
  });

  it("點一下方向鍵只走一格", async () => {
    const h = harness(open());
    h.keys.press("right", false);
    h.keys.release("right");
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(1000);
    await done;
    expect(h.steps).toHaveLength(1);
  });

  it("伺服器慢的時候最多領先 2 格", async () => {
    const h = harness(open(), undefined, 1000);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(900);
    expect(h.steps).toHaveLength(2); // 第 3 格要等第 1 格的回應
    expect(h.run.lead).toBe(2);
    await vi.advanceTimersByTimeAsync(200);
    expect(h.steps).toHaveLength(3);
    h.keys.release("right");
    await vi.advanceTimersByTimeAsync(5000);
    await done;
    expect(h.run.maxLead).toBe(2);
  });

  it("看得到敵人時最多領先 1 格", async () => {
    const h = harness(open({ enemies: [ENEMY] }), undefined, 1000);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(900);
    expect(h.steps).toHaveLength(1);
    expect(h.run.lead).toBe(1);
    h.keys.release("right");
    await vi.advanceTimersByTimeAsync(5000);
    await done;
    expect(h.run.maxLead).toBe(1);
  });

  it("對不上（遇敵）：不再送，主角沿原路滑回伺服器的格子，套用伺服器畫面，方向鍵放開", async () => {
    // 第 1 格就遇敵：伺服器說主角停在 (1, 1)、有遭遇；前端已經先走到 (2, 1)
    const answer: Answer = (cell, f) => reply({ ...f, me: { ...f.me, x: cell.x, y: cell.y } }, cell.x === 1 ? ({ encounter: {} } as Partial<WorldView>) : {});
    const h = harness(open(), answer, 150);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(2000);
    await done;
    expect(h.steps.map((s) => s.to.x)).toEqual([1, 2]);
    expect(h.sent.map((s) => s.cell.x)).toEqual([1]); // 第 2 格沒送
    expect(h.slides).toEqual([[{ x: 1, y: 1 }]]);
    expect(h.commits).toEqual([{ me: { x: 1, y: 1 }, shown: null }]);
    expect(h.keys.peek()).toBeNull();
  });

  it("對不上（位置不同）：直接滑到伺服器給的格子", async () => {
    const answer: Answer = (_cell, f) => reply({ ...f, me: { ...f.me, x: 0, y: 0 } });
    const h = harness(open(), answer, 150);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(2000);
    await done;
    expect(h.slides).toEqual([[{ x: 0, y: 0 }]]); // (0,0) 不在先走的路上
    expect(h.commits[h.commits.length - 1]).toEqual({ me: { x: 0, y: 0 }, shown: null });
  });

  it("請求失敗：滑回最後確認的格子，重畫", async () => {
    const h = harness(open(), () => null, 150);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(2000);
    await done;
    expect(h.slides[0]![h.slides[0]!.length - 1]).toEqual({ x: 0, y: 1 });
    expect(h.stats().failed).toBe(1);
    expect(h.commits).toEqual([]);
  });

  it("視窗失焦時停止（按住的方向全部放開）", async () => {
    const h = harness(open());
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(STEP + 10);
    h.keys.clear(); // WorldField 在 blur／visibilitychange 時呼叫
    await vi.advanceTimersByTimeAsync(2000);
    await done;
    expect(h.steps).toHaveLength(2);
  });

  it("出口不先走：前面的格子都確認了才照舊流程送", async () => {
    const h = harness(open({ me: { x: 7, y: 1, facing: "e" } }), undefined, 500);
    h.keys.press("right", false);
    const done = h.run.run();
    await vi.advanceTimersByTimeAsync(STEP + 10);
    expect(h.steps.map((s) => s.to.x)).toEqual([8]);
    expect(h.portals).toEqual([]); // (8,1) 還沒確認
    await vi.advanceTimersByTimeAsync(2000);
    await done;
    expect(h.portals).toEqual([{ x: 9, y: 1 }]);
  });
});
