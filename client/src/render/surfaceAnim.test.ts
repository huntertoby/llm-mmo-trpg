// Phase 6N-9：地表動畫（surfaceAnim）的觸發條件、火蔓延順序、時間軸、確定性、略過與 reduced-motion。
import { describe, expect, it, vi } from "vitest";
import type { BattleView, TileView } from "../api/types";
import { buildDrawModel, type DrawModel } from "../battle/drawModel";
import { tile } from "../battle/testFixtures";
import { APPEAR_MS, changeTotalMs, hueColor, revealAt, sameBoard, spreadSteps, SPREAD_MAX_STEPS, SPREAD_STEP_MS, surfaceChanges, surfaceShimmer, VANISH_MS } from "./surfaceAnim";
import { SurfaceAnimator, type SurfaceHost } from "./surfaceAnimLayer";

const W = 8;

function model(surfaces: Record<string, string> = {}, over: Partial<BattleView> = {}, terrain: (x: number, y: number) => string = () => "stone"): DrawModel {
  const tiles: TileView[] = [];
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) tiles.push(tile(x, y, { terrain: terrain(x, y), surface: (surfaces[`${x},${y}`] ?? "none") as TileView["surface"] }));
  const view = {
    team: "ally", map_id: "t", map_name_zh: "t", width: W, height: W, tiles, objects: [], units: [], traps: [],
    turn_order: [], active_unit: null, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [], ...over,
  } as unknown as BattleView;
  return buildDrawModel(view, "unit_0001");
}

const line = (y: number, from: number, to: number, s: string): Record<string, string> => Object.fromEntries(Array.from({ length: to - from + 1 }, (_, i) => [`${from + i},${y}`, s]));

describe("觸發條件", () => {
  it("同一張地圖才播：大小、地形不同時沒有轉場", () => {
    const a = model();
    expect(sameBoard(a, model())).toBe(true);
    expect(sameBoard(a, model({}, {}, (x) => (x === 3 ? "dirt" : "stone")))).toBe(false);
    expect(surfaceChanges(a, model({ "1,1": "water" }, {}, (x) => (x === 3 ? "dirt" : "stone")))).toEqual([]);
  });

  it("出現（含換成另一種）從中心擴散；消失往中心收縮；沒變的格子不播", () => {
    const prev = model({ "1,1": "ice", "2,2": "oil" });
    const next = model({ "1,1": "water", "2,2": "none", "5,5": "poison" });
    const c = surfaceChanges(prev, next);
    expect(c.map((x) => [x.x, x.y, x.before, x.after, x.kind])).toEqual([
      [1, 1, "ice", "water", "appear"],
      [2, 2, "oil", "none", "vanish"],
      [5, 5, "none", "poison", "appear"],
    ]);
    expect(c.every((x) => x.delayMs === 0)).toBe(true);
    expect(surfaceChanges(next, next)).toEqual([]);
  });
});

describe("火蔓延的順序照相鄰格", () => {
  it("從原本在燒的那一端沿著油一格一格燒過去，每格 0.08 秒", () => {
    const prev = model({ ...line(3, 1, 6, "oil"), "0,3": "fire" });
    const next = model({ ...line(3, 0, 6, "fire") });
    const d = surfaceChanges(prev, next).map((c) => [c.x, c.delayMs]);
    expect(d).toEqual([1, 2, 3, 4, 5, 6].map((x) => [x, (x - 1) * SPREAD_STEP_MS]));
  });

  it("整片一起點燃（沒有舊火相鄰）：從那一塊最中間的格子往外", () => {
    const next = model(line(2, 0, 4, "fire"));
    const d = new Map(surfaceChanges(model(line(2, 0, 4, "oil")), next).map((c) => [c.x, c.delayMs / SPREAD_STEP_MS]));
    expect([...d.entries()].sort((a, b) => a[0] - b[0])).toEqual([
      [0, 2],
      [1, 1],
      [2, 0],
      [3, 1],
      [4, 2],
    ]);
  });

  it("L 形、兩塊分開：每一格（延遲 > 0）都有一個相鄰格剛好早一步", () => {
    const fire: Record<string, string> = { ...line(1, 1, 4, "fire"), "4,2": "fire", "4,3": "fire", "4,4": "fire", ...line(6, 0, 2, "fire") };
    const changes = surfaceChanges(model(), model(fire));
    const at = new Map(changes.map((c) => [`${c.x},${c.y}`, c.delayMs]));
    for (const c of changes) {
      if (c.delayMs === 0) continue;
      const prev = [
        [0, -1],
        [1, 0],
        [0, 1],
        [-1, 0],
      ].some(([dx, dy]) => at.get(`${c.x + dx!},${c.y + dy!}`) === c.delayMs - SPREAD_STEP_MS);
      expect(prev, `${c.x},${c.y}`).toBe(true);
    }
    // 兩塊各有一個起點
    expect(changes.filter((c) => c.delayMs === 0)).toHaveLength(2);
  });

  it("很長的一條：最多排 12 格的延遲", () => {
    const cells = Array.from({ length: 30 }, (_, i) => ({ x: i, y: 0 }));
    const s = spreadSteps(cells, new Set(["-1,0"]));
    expect(s.get("0,0")).toBe(0);
    expect(Math.max(...s.values())).toBe(SPREAD_MAX_STEPS);
  });

  it("確定性：輸入順序不同結果一樣", () => {
    const cells = [
      { x: 2, y: 2 },
      { x: 3, y: 2 },
      { x: 2, y: 3 },
      { x: 3, y: 3 },
    ];
    const a = spreadSteps(cells, new Set());
    const b = spreadSteps([...cells].reverse(), new Set());
    expect([...a.entries()].sort()).toEqual([...b.entries()].sort());
  });
});

describe("時間軸", () => {
  const appear = { x: 0, y: 0, before: "none", after: "water", kind: "appear" as const, delayMs: 160 };
  const vanish = { ...appear, after: "none", kind: "vanish" as const, delayMs: 0 };

  it("出現：延遲期間舊的樣子蓋滿，之後洞從 0 長到蓋過整格；總長 ＝ 延遲＋0.26 秒", () => {
    expect(revealAt(appear, 0)).toEqual({ radius: 0, inverse: true, done: false });
    expect(revealAt(appear, 160).radius).toBe(0);
    expect(revealAt(appear, 160 + APPEAR_MS / 2).radius).toBeGreaterThan(0.3);
    expect(revealAt(appear, 160 + APPEAR_MS)).toEqual({ radius: 0.75, inverse: true, done: true });
    expect(changeTotalMs(appear)).toBe(160 + APPEAR_MS);
  });

  it("消失：舊的樣子從整格縮到 0", () => {
    expect(revealAt(vanish, 0)).toEqual({ radius: 0.75, inverse: false, done: false });
    expect(revealAt(vanish, VANISH_MS)).toEqual({ radius: 0, inverse: false, done: true });
  });

  it("播放速度：慢速 2 倍時間（延遲也一起放慢）", () => {
    expect(changeTotalMs(appear, 2)).toBe((160 + APPEAR_MS) * 2);
    expect(revealAt(appear, 320, 2).radius).toBe(0);
  });
});

describe("持續的表面動態", () => {
  it("水面：兩條反光線慢慢往右飄（5.2 秒一格），兩端淡出", () => {
    const a = surfaceShimmer("water", 3, 4, 0);
    expect(a).toHaveLength(2);
    // 每 100ms 往右 0.56 × 100 / 5200 格（到右邊淡出後從左邊重來）
    const b = surfaceShimmer("water", 3, 4, 100);
    const dx = b[0]!.x - a[0]!.x;
    expect(dx > 0 ? dx : dx + 0.56).toBeCloseTo((0.56 * 100) / 5200, 6);
    for (let ms = 0; ms < 6000; ms += 50) {
      for (const s of surfaceShimmer("water", 3, 4, ms)) {
        expect(s.x).toBeGreaterThanOrEqual(0.2);
        expect(s.x).toBeLessThanOrEqual(0.8);
        expect(s.alpha).toBeLessThanOrEqual(0.42 + 1e-9);
      }
    }
  });

  it("油面：虹彩的顏色隨時間流動", () => {
    const tints = new Set<number>();
    for (let ms = 0; ms < 6000; ms += 500) tints.add(surfaceShimmer("oil", 1, 1, ms)[0]!.tint);
    expect(tints.size).toBeGreaterThan(6);
    expect(hueColor(0)).toBe(hueColor(1));
  });

  it("火面閃、其他表面沒有動態；相位照格子座標，不用 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    expect(surfaceShimmer("fire", 0, 0, 100)).toHaveLength(1);
    expect(surfaceShimmer("ice", 0, 0, 100)).toEqual([]);
    expect(surfaceShimmer("water", 1, 2, 777)).toEqual(surfaceShimmer("water", 1, 2, 777));
    expect(surfaceShimmer("water", 1, 2, 777)).not.toEqual(surfaceShimmer("water", 2, 1, 777));
    expect(rnd).not.toHaveBeenCalled();
    rnd.mockRestore();
  });
});

describe("驅動（SurfaceAnimator）", () => {
  // 測試環境沒有 DOM：貼圖都是 null，只看轉場的登記與作廢
  const host: SurfaceHost = { ground: () => null as never, deco: () => null as never, place: () => undefined, oldTile: () => null };

  it("前後畫面不同時登記轉場；播完就拿掉", () => {
    const a = new SurfaceAnimator();
    a.draw(model(), host, 1);
    a.draw(model({ "1,1": "water" }), host, 1);
    expect(a.activeChanges().map((c) => c.after)).toEqual(["water"]);
    a.tick(APPEAR_MS + 1);
    expect(a.activeChanges()).toEqual([]);
  });

  it("「略過」（timeScale null）不播轉場", () => {
    const a = new SurfaceAnimator();
    a.draw(model(), host, 1);
    a.draw(model({ "1,1": "water" }), host, null);
    expect(a.activeChanges()).toEqual([]);
  });

  it("轉場中又重畫：表面一樣的接著播，又變了就作廢", () => {
    const a = new SurfaceAnimator();
    a.draw(model(), host, 1);
    a.draw(model({ "1,1": "water", "2,2": "oil" }), host, 1);
    a.tick(100);
    a.draw(model({ "1,1": "water", "2,2": "fire" }), host, 1);
    const c = a.activeChanges();
    expect(c.find((x) => x.x === 1)?.after).toBe("water");
    expect(c.find((x) => x.x === 2)?.before).toBe("oil");
    expect(c.find((x) => x.x === 2)?.after).toBe("fire");
  });

  it("reduced-motion：關掉時清掉轉場、之後也不登記", () => {
    const a = new SurfaceAnimator();
    a.draw(model(), host, 1);
    a.draw(model({ "1,1": "water" }), host, 1);
    a.setEnabled(false);
    expect(a.activeChanges()).toEqual([]);
    a.draw(model({ "1,1": "none" }), host, 1);
    expect(a.activeChanges()).toEqual([]);
  });
});
