// Phase 6A-4c：選移動時的路徑提示——分段顏色、每格的點、特殊格外框、結果小牌、停點與到不了；
// 路徑的圓角與虛線；請求節流與快取；畫法（用紀錄器代替 Pixi 的 Graphics）。
import { describe, expect, it } from "vitest";
import type { MoveAction } from "../api/types";
import { dashRuns, outerEdges, polylineLength, roundedPieces } from "./pathGeometry";
import { PathPreviewFetcher, PathPreviewScope, PATH_PREVIEW_THROTTLE_MS } from "./pathFetch";
import { readFile, SRC_DIR } from "../test/sourceScan";
import {
  damageText,
  hoverPathQuery,
  missedEnd,
  pathDraw,
  pathQuery,
  pathSegments,
  PATH_COLORS,
  PATH_DASHED,
  slipRunText,
  stepKind,
  stopBangs,
  type PathEvent,
  type PathPreview,
  type PathStep,
  type SlipRun,
} from "./pathPreview";
import { drawPathLine, drawPathMarks, drawSoftCells, MOVE_SOFT, placeTags, type Pen, type StrokeStyle } from "../render/pathArt";

type Reach = PathStep["reach"];

function ev(kind: PathEvent["kind"], extra: Partial<PathEvent> = {}): PathEvent {
  return {
    kind,
    certain: true,
    other_id: null,
    status_id: null,
    surface: null,
    pos: null,
    amount_min: null,
    amount_max: null,
    chance_permille: null,
    detail: null,
    ...extra,
  };
}

function step(index: number, x: number, y: number, extra: Partial<PathStep> = {}): PathStep {
  return { pos: [x, y], index, surface: "none", trap: false, reach: "certain" as Reach, events: [], ...extra };
}

function preview(steps: PathStep[], extra: Partial<PathPreview> = {}): PathPreview {
  const last = steps[steps.length - 1] as PathStep;
  return {
    unit_id: "unit_0001",
    path: steps.map((s) => s.pos),
    legal_length: steps.length,
    reachable: true,
    reason: null,
    steps,
    stop: last.pos,
    worst_stop: last.pos,
    stop_certain: true,
    certain: true,
    move_cost: steps.length - 1,
    slip_runs: [],
    ...extra,
  };
}

function slipRun(start: number, end: number, chance: number, y = 0): SlipRun {
  return {
    start,
    end,
    start_pos: [start, y],
    end_pos: [end, y],
    tiles: end - start + 1,
    chance_permille: chance,
    fail_stops: Array.from({ length: end - start + 1 }, (_, i) => [start + i, y]),
    status_id: "prone",
  };
}

const plain = preview([step(0, 0, 0), step(1, 1, 0), step(2, 2, 0), step(3, 2, 1)]);

// 冰面滑倒 45%（失敗倒地停在冰上）→ 陷阱 −8、定身（可能）→ 後面因定身可能走不到
const hazard = preview(
  [
    step(0, 0, 0),
    step(1, 1, 0),
    step(2, 2, 0, {
      surface: "ice",
      events: [
        ev("slip_check", { chance_permille: 450, status_id: "prone", detail: "ice" }),
        ev("status", { status_id: "prone", certain: false }),
        ev("stopped", { detail: "prone", certain: false }),
      ],
    }),
    step(3, 3, 0, {
      trap: true,
      reach: "possible",
      events: [
        ev("trap", { other_id: "unit_0009", detail: "bear_trap", certain: false }),
        ev("damage", { other_id: "unit_0009", amount_min: 8, amount_max: 8, certain: false }),
        ev("status", { status_id: "root", certain: false }),
        ev("stopped", { detail: "rooted", certain: false }),
      ],
    }),
    step(4, 3, 1, { reach: "possible", surface: "water" }),
  ],
  { stop: [3, 1], worst_stop: [2, 0], stop_certain: false, certain: false, slip_runs: [slipRun(2, 2, 450)] },
);

// 移動點數不足：後半段到不了
const short = preview([step(0, 0, 0), step(1, 1, 0), step(2, 2, 0, { reach: "unreachable" }), step(3, 3, 0, { reach: "unreachable" })], {
  reachable: false,
  legal_length: 2,
  reason: "移動點數不足：需要 3，剩餘 1",
  stop: [1, 0],
  worst_stop: [1, 0],
});

describe("路徑分段與顏色", () => {
  it("一般地面：白色實線，每格一個點（不含起點）", () => {
    const d = pathDraw(plain);
    expect(d.segments.map((s) => s.kind)).toEqual(["normal", "normal", "normal"]);
    expect(d.dots.map((p) => [p.pos.x, p.pos.y])).toEqual([
      [1, 0],
      [2, 0],
      [2, 1],
    ]);
    expect(PATH_COLORS.normal).toBe(0xffffff);
    expect(PATH_DASHED.normal).toBe(false);
    expect(d.tags).toEqual([]);
    expect(d.bangs).toEqual([]);
    expect(d.missEnd).toBeNull();
  });

  it("冰面藍虛線 #1e78d0、陷阱或火紅色、到不了灰虛線", () => {
    expect(stepKind(step(1, 0, 0, { surface: "ice" }))).toBe("ice");
    expect(stepKind(step(1, 0, 0, { trap: true }))).toBe("danger");
    expect(stepKind(step(1, 0, 0, { surface: "fire" }))).toBe("danger");
    expect(stepKind(step(1, 0, 0, { surface: "water" }))).toBe("normal");
    expect(stepKind(step(1, 0, 0, { reach: "unreachable", surface: "ice" }))).toBe("unreachable");
    expect(stepKind(step(1, 0, 0, { reach: "interrupted" }))).toBe("unreachable");
    expect(PATH_COLORS.ice).toBe(0x1e78d0);
    expect(PATH_DASHED.ice).toBe(true);
    expect(PATH_DASHED.danger).toBe(false);
    expect(PATH_DASHED.unreachable).toBe(true);
    expect(pathSegments(hazard).map((s) => s.kind)).toEqual(["normal", "ice", "danger", "normal"]);
    expect(pathSegments(short).map((s) => s.kind)).toEqual(["normal", "unreachable", "unreachable"]);
  });

  it("只在骰子有利時走得到的段標成可能（畫淡一點）", () => {
    expect(pathSegments(hazard).map((s) => s.possible)).toEqual([false, false, true, true]);
  });

  it("經過的特殊格加地表色外框；到不了的格子不加", () => {
    const d = pathDraw(hazard);
    expect(d.frames).toEqual([
      { pos: { x: 2, y: 0 }, kind: "ice" },
      { pos: { x: 3, y: 0 }, kind: "danger" },
    ]);
    const oil = pathDraw(preview([step(0, 0, 0), step(1, 1, 0, { surface: "oil" }), step(2, 2, 0, { surface: "ice", reach: "unreachable" })], { reachable: false }));
    expect(oil.frames).toEqual([{ pos: { x: 1, y: 0 }, kind: "oil" }]);
  });

  it("伺服器回傳「完全沒有路」（起點＋終點不相鄰）時不畫線，只標到不了", () => {
    const none = preview([step(0, 0, 0), step(1, 5, 5, { reach: "unreachable" })], { reachable: false, legal_length: 1 });
    const d = pathDraw(none);
    expect(d.segments).toEqual([]);
    expect(d.dots).toEqual([]);
    expect(d.missEnd).toEqual({ x: 5, y: 5 });
  });
});

describe("結果小牌", () => {
  it("冰面：「滑倒 45%・失敗停在這格」，倒地不另寫", () => {
    const tags = pathDraw(hazard).tags;
    expect(tags[0]).toEqual({ pos: { x: 2, y: 0 }, icon: "ice", text: "滑倒 45%・失敗停在這格" });
  });

  it("陷阱：「陷阱 −8・定身（可能）」；在冰面後面時不加「（可能）」（6A-4f）", () => {
    const tags = pathDraw(hazard).tags;
    expect(tags[1]?.icon).toBe("trap");
    expect(tags[1]?.text).toBe("陷阱 −8・定身");
    const sure = pathDraw(
      preview([
        step(0, 0, 0),
        step(1, 1, 0, {
          trap: true,
          events: [
            ev("trap", { other_id: "e1" }),
            ev("damage", { other_id: "e1", amount_min: 8, amount_max: 8 }),
            ev("status", { status_id: "root", certain: false }),
          ],
        }),
      ]),
    );
    expect(sure.tags[0]?.text).toBe("陷阱 −8・定身（可能）");
  });

  it("火：「點燃」；水：「潮濕」", () => {
    const d = pathDraw(
      preview([
        step(0, 0, 0),
        step(1, 1, 0, { surface: "fire", events: [ev("surface", { surface: "fire" }), ev("status", { status_id: "burning" })] }),
        step(2, 2, 0, { surface: "water", events: [ev("surface", { surface: "water" })] }),
      ]),
    );
    expect(d.tags.map((t) => [t.icon, t.text])).toEqual([
      ["fire", "點燃"],
      ["water", "潮濕"],
    ]);
  });

  it("到不了的格子與起點不出小牌", () => {
    const d = pathDraw(preview([step(0, 0, 0, { surface: "water" }), step(1, 1, 0, { surface: "water", reach: "unreachable" })], { reachable: false }));
    expect(d.tags).toEqual([]);
  });

  it("傷害數字：確定、範圍、只在骰子不利時", () => {
    expect(damageText([ev("damage", { amount_min: 8, amount_max: 8 })])).toBe("−8");
    expect(damageText([ev("damage", { amount_min: 6, amount_max: 9 })])).toBe("−6～9");
    expect(damageText([ev("damage", { amount_min: null, amount_max: 5 })])).toBe("−5");
    expect(damageText([])).toBe("");
  });
});

describe("停點與到不了", () => {
  it("被陷阱定住的格子放驚嘆號；冰面滑倒不放", () => {
    expect(stopBangs(hazard)).toEqual([{ x: 3, y: 0 }]);
    expect(pathDraw(hazard).bangs).toEqual([{ x: 3, y: 0 }]);
  });

  it("被移走時驚嘆號放在新位置；撤離不放", () => {
    const moved = preview([
      step(0, 0, 0),
      step(1, 1, 0, { events: [ev("displaced", { pos: [1, 2], detail: "push" }), ev("stopped", { detail: "displaced" })] }),
      step(2, 2, 0, { reach: "interrupted" }),
    ]);
    expect(stopBangs(moved)).toEqual([{ x: 1, y: 2 }]);
    const fled = preview([step(0, 0, 0), step(1, 1, 0, { events: [ev("escaped"), ev("stopped", { detail: "escaped" })] })]);
    expect(stopBangs(fled)).toEqual([]);
  });

  it("原終點走不到（超出移動點數、或一定會在之前停下）標「到不了」", () => {
    expect(missedEnd(short)).toEqual({ x: 3, y: 0 });
    expect(missedEnd(plain)).toBeNull();
    expect(missedEnd(hazard)).toBeNull(); // 定身只是可能：終點仍可能走到
    const rooted = preview([step(0, 0, 0), step(1, 1, 0, { trap: true, events: [ev("stopped", { detail: "rooted" })] }), step(2, 2, 0, { reach: "interrupted" })]);
    expect(missedEnd(rooted)).toEqual({ x: 2, y: 0 });
    expect(pathDraw(rooted).bangs).toEqual([{ x: 1, y: 0 }]);
  });
});

describe("要預覽哪條路徑", () => {
  const view = { width: 6, height: 6, units: [{ id: "e1", pos: { x: 4, y: 4 }, downed: false, escaped: false, dismissed: false }] } as never;
  const move = { kind: "move", unit_id: "unit_0001", path: [{ x: 0, y: 0 }, { x: 1, y: 0 }] } as unknown as MoveAction;
  const moves = new Map([["1,0", move]]);
  const hero = { pos: { x: 0, y: 0 } };

  it("走得到的格子用移動動作的路徑；走不到的格子只給終點", () => {
    expect(hoverPathQuery({ moving: true, hover: { x: 1, y: 0 }, hero, view, moves })).toEqual(pathQuery(move.path, { x: 1, y: 0 }));
    expect(hoverPathQuery({ moving: true, hover: { x: 1, y: 0 }, hero, view, moves })?.body).toEqual({ path: [{ x: 0, y: 0 }, { x: 1, y: 0 }] });
    expect(hoverPathQuery({ moving: true, hover: { x: 3, y: 3 }, hero, view, moves })?.body).toEqual({ dest: { x: 3, y: 3 } });
  });

  it("不在選移動、滑過自己、單位或地圖外時不預覽", () => {
    expect(hoverPathQuery({ moving: false, hover: { x: 1, y: 0 }, hero, view, moves })).toBeNull();
    expect(hoverPathQuery({ moving: true, hover: { x: 0, y: 0 }, hero, view, moves })).toBeNull();
    expect(hoverPathQuery({ moving: true, hover: { x: 4, y: 4 }, hero, view, moves })).toBeNull();
    expect(hoverPathQuery({ moving: true, hover: { x: 6, y: 0 }, hero, view, moves })).toBeNull();
    expect(hoverPathQuery({ moving: true, hover: null, hero, view, moves })).toBeNull();
  });
});

describe("路徑的圓角與虛線", () => {
  it("直線不做圓角；轉角的弧一半屬於進來的段、一半屬於出去的段", () => {
    const straight = roundedPieces(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 20, y: 0 },
      ],
      4,
    );
    expect(straight).toEqual([
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
      ],
      [
        { x: 10, y: 0 },
        { x: 20, y: 0 },
      ],
    ]);
    const turn = roundedPieces(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 10, y: 10 },
      ],
      4,
    );
    expect(turn).toHaveLength(2);
    const inEnd = turn[0]?.[turn[0].length - 1];
    const outStart = turn[1]?.[0];
    expect(inEnd).toEqual(outStart); // 換色點在轉角正中間，接得上
    expect(turn[0]?.[1]).toEqual({ x: 6, y: 0 }); // 圓角從轉角前 4 開始
    expect(turn[1]?.[turn[1].length - 1]).toEqual({ x: 10, y: 10 });
    expect(polylineLength(turn[0] ?? [])).toBeLessThan(10); // 圓角切掉轉角
  });

  it("虛線依長度切段", () => {
    const runs = dashRuns(
      [
        { x: 0, y: 0 },
        { x: 24, y: 0 },
      ],
      7,
      5,
    );
    expect(runs.map((r) => [r[0]?.x, r[r.length - 1]?.x])).toEqual([
      [0, 7],
      [12, 19],
      [24, 24],
    ].filter(([a, b]) => (b as number) > (a as number)));
  });

  it("格子群的外緣只畫露在外面的邊", () => {
    const edges = outerEdges([
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ]);
    expect(edges.map((e) => `${e.x},${e.y},${e.side}`)).toEqual(["0,0,n", "0,0,s", "0,0,w", "1,0,n", "1,0,s", "1,0,e"]);
  });
});

describe("請求節流與快取", () => {
  function setup() {
    let clock = 0;
    const timers: Array<{ at: number; fn: () => void; id: number }> = [];
    let nextId = 1;
    const resolvers: Array<{ body: unknown; resolve: (pv: PathPreview) => void }> = [];
    const results: Array<string | null> = [];
    const f = new PathPreviewFetcher({
      fetch: (body) =>
        new Promise<PathPreview>((resolve) => {
          resolvers.push({ body, resolve });
        }),
      onResult: (key) => results.push(key),
      now: () => clock,
      setTimer: (fn, ms) => {
        const id = nextId++;
        timers.push({ at: clock + ms, fn, id });
        return id;
      },
      clearTimer: (id) => {
        const i = timers.findIndex((t) => t.id === id);
        if (i >= 0) timers.splice(i, 1);
      },
    });
    const advance = (ms: number) => {
      clock += ms;
      for (const t of [...timers].filter((x) => x.at <= clock)) {
        timers.splice(timers.indexOf(t), 1);
        t.fn();
      }
    };
    return { f, advance, resolvers, results };
  }
  const q = (x: number) => pathQuery(null, { x, y: 0 });
  const flush = () => new Promise((r) => setTimeout(r, 0));

  it("第一次立刻送；120ms 內滑過的格子只在時間到時送最後一格", async () => {
    const { f, advance, resolvers } = setup();
    f.want(q(1));
    expect(f.sent).toBe(1);
    advance(30);
    f.want(q(2));
    advance(30);
    f.want(q(3));
    expect(f.sent).toBe(1);
    advance(PATH_PREVIEW_THROTTLE_MS);
    expect(f.sent).toBe(2);
    expect(resolvers.map((r) => r.body)).toEqual([{ dest: { x: 1, y: 0 } }, { dest: { x: 3, y: 0 } }]);
  });

  it("同一條路徑快取：再滑回來不重送，立刻有結果", async () => {
    const { f, advance, resolvers, results } = setup();
    f.want(q(1));
    resolvers[0]?.resolve(plain);
    await flush();
    expect(results).toEqual(["d:1,0"]);
    advance(500);
    f.want(q(2));
    f.want(q(1));
    expect(results[results.length - 1]).toBe("d:1,0");
    expect(f.sent).toBe(2);
  });

  it("晚到的舊回應不蓋掉目前要的；狀態改變後清掉快取、舊回應丟掉", async () => {
    const { f, advance, resolvers, results } = setup();
    f.want(q(1));
    advance(200);
    f.want(q(2));
    resolvers[0]?.resolve(plain); // 第 1 格的回應晚到
    await flush();
    expect(results).toEqual([]);
    f.reset();
    resolvers[1]?.resolve(plain);
    await flush();
    expect(results).toEqual([]);
    advance(200);
    f.want(q(1));
    expect(f.sent).toBe(3); // 快取已清：重新問
  });

  it("換戰鬥（6C-R1）：同一個 fetcher 之後的請求送到新的 battleId，並清掉舊戰鬥的快取", async () => {
    const scope = new PathPreviewScope("b1", "s0");
    const calls: string[] = [];
    let clock = 0;
    const f = new PathPreviewFetcher({
      fetch: scope.fetchWith((id) => {
        calls.push(id);
        return Promise.resolve(plain);
      }),
      onResult: () => {},
      now: () => clock,
      setTimer: () => 0,
      clearTimer: () => {},
    });
    expect(scope.update("b1", "s0")).toBe(false);
    f.want(q(1));
    await flush();
    expect(calls).toEqual(["b1"]);
    expect(scope.update("b2", "s0")).toBe(true);
    expect(scope.battleId).toBe("b2");
    f.reset();
    clock += 500;
    f.want(q(1)); // 同一條路徑：舊戰鬥的快取已清，要向新戰鬥重問
    await flush();
    expect(calls).toEqual(["b1", "b2"]);
    expect(scope.update("b2", "s1")).toBe(true); // 狀態變了也要清
  });

  it("usePathPreview 用 PathPreviewScope，不在建立 fetcher 時綁死 battleId", () => {
    const src = readFile(SRC_DIR, "ui/usePathPreview.ts");
    expect(src).toMatch(/fetchWith\(/);
    expect(src).not.toMatch(/api\.pathPreview\(battleId\b/);
  });

  it("不預覽時通知清掉", () => {
    const { f, results } = setup();
    f.want(null);
    expect(results).toEqual([null]);
    expect(f.sent).toBe(0);
  });
});

/** 紀錄畫筆的呼叫（代替 Pixi 的 Graphics）。 */
function recorder(): Pen & { calls: string[]; strokes: StrokeStyle[] } {
  const calls: string[] = [];
  const strokes: StrokeStyle[] = [];
  return {
    calls,
    strokes,
    moveTo: (x, y) => calls.push(`M${Math.round(x)},${Math.round(y)}`),
    lineTo: (x, y) => calls.push(`L${Math.round(x)},${Math.round(y)}`),
    roundRect: (x, y, w, h, r) => calls.push(`R${x},${y},${w},${h},${r}`),
    circle: (x, y, r) => calls.push(`C${x},${y},${r}`),
    closePath: () => calls.push("Z"),
    fill: (s) => calls.push(`F${s.color.toString(16)}`),
    stroke: (s) => {
      strokes.push(s);
      calls.push(`S${s.color.toString(16)}`);
    },
  };
}

const geo = {
  origin: (p: { x: number; y: number }) => ({ x: p.x * 48, y: p.y * 48 }),
  center: (p: { x: number; y: number }) => ({ x: p.x * 48 + 24, y: p.y * 48 + 24 }),
};

describe("畫法", () => {
  it("路徑：黑色底線、各段顏色、冰面虛線、每格一點", () => {
    const g = recorder();
    drawPathLine(g, pathDraw(hazard), geo);
    const colors = g.strokes.map((s) => s.color);
    expect(colors).toEqual([0x000000, 0xffffff, 0x1e78d0, 0xff6a50, 0xffffff]);
    // 冰面那段是虛線：同一筆裡有多個 moveTo
    const iceStroke = g.calls.indexOf("S1e78d0");
    const prevStroke = g.calls.indexOf("Sffffff");
    const iceMoves = g.calls.slice(prevStroke + 1, iceStroke).filter((c) => c.startsWith("M")).length;
    expect(iceMoves).toBeGreaterThan(1);
    expect(g.calls.filter((c) => c.startsWith("C") && c.endsWith(",3.8"))).toHaveLength(4);
  });

  it("外框、到不了的虛線框、驚嘆號", () => {
    const g = recorder();
    drawPathMarks(g, pathDraw(short), geo);
    expect(g.calls.filter((c) => c.startsWith("R"))).toEqual(["R149,5,38,38,9"]); // 終點 (3,0) 的虛線框
    const h = recorder();
    drawPathMarks(h, pathDraw(hazard), geo);
    expect(h.calls).toContain("R99,3,42,42,8"); // 冰 (2,0) 外框
    expect(h.calls).toContain("R147,3,42,42,8"); // 陷阱 (3,0) 外框
    expect(h.calls.filter((c) => c === "Fe0302a")).toHaveLength(2); // 驚嘆號泡泡（尾巴＋圓）
  });

  it("可走格：白描邊＋藍填色，外緣亮線只畫露在外面的邊", () => {
    const g = recorder();
    drawSoftCells(g, [{ x: 0, y: 0 }, { x: 1, y: 0 }], geo, MOVE_SOFT);
    expect(g.calls.filter((c) => c.startsWith("R"))).toHaveLength(2);
    expect(g.strokes[0]?.color).toBe(0xffffff);
    expect(g.calls.filter((c) => c.startsWith("M"))).toHaveLength(6);
    expect(g.strokes[g.strokes.length - 1]?.color).toBe(MOVE_SOFT.edge);
  });

  it("小牌不互相疊：右上被佔就換位置，都疊到時往上疊", () => {
    const items = [0, 48, 96, 144].map((x) => ({ o: { x, y: 100 }, w: 150 }));
    const spots = placeTags(items);
    expect(spots[0]).toEqual({ x: 24, y: 82 });
    expect(spots[1]).toEqual({ x: 72, y: 144 });
    for (let i = 0; i < spots.length; i++) {
      for (let j = i + 1; j < spots.length; j++) {
        const a = spots[i] as { x: number; y: number };
        const b = spots[j] as { x: number; y: number };
        expect(a.x < b.x + 150 && a.x + 150 > b.x && a.y < b.y + 22 && a.y + 22 > b.y).toBe(false);
      }
    }
  });
});

// 6A-4f：兩格冰（整段滑倒 80%）→ 後方陷阱 −6～14・定身
const iceRun = preview(
  [
    step(0, 0, 0),
    step(1, 1, 0, {
      surface: "ice",
      events: [
        ev("surface", { surface: "ice" }),
        ev("slip_check", { chance_permille: 550, status_id: "prone", detail: "ice" }),
        ev("status", { status_id: "prone", certain: false }),
        ev("stopped", { detail: "prone", certain: false }),
      ],
    }),
    step(2, 2, 0, {
      surface: "ice",
      reach: "possible",
      events: [
        ev("surface", { surface: "ice", certain: false }),
        ev("slip_check", { chance_permille: 550, status_id: "prone", detail: "ice", certain: false }),
      ],
    }),
    step(3, 3, 0, {
      trap: true,
      reach: "possible",
      events: [
        ev("trap", { other_id: "e1", certain: false }),
        ev("damage", { other_id: "e1", amount_min: 6, amount_max: 14, certain: false }),
        ev("status", { status_id: "root", certain: false }),
      ],
    }),
    step(4, 4, 0, { reach: "possible" }),
  ],
  { stop: [4, 0], worst_stop: [1, 0], stop_certain: false, certain: false, slip_runs: [slipRun(1, 2, 798)] },
);

describe("連續冰面合成一張小牌（6A-4f）", () => {
  it("兩格冰只出一張，放在第一格冰旁：「冰 2 格・滑倒 80%・失敗停在那格」，不加「（可能）」", () => {
    const tags = pathDraw(iceRun).tags;
    const ice = tags.filter((t) => t.icon === "ice");
    expect(ice).toEqual([{ pos: { x: 1, y: 0 }, icon: "ice", text: "冰 2 格・滑倒 80%・失敗停在那格" }]);
    expect(tags.some((t) => t.text.includes("（可能）"))).toBe(false);
  });

  it("單格冰照舊寫「滑倒 xx%・失敗停在這格」", () => {
    expect(slipRunText(slipRun(2, 2, 450))).toBe("滑倒 45%・失敗停在這格");
    expect(slipRunText(slipRun(1, 3, 914))).toBe("冰 3 格・滑倒 91%・失敗停在那格");
  });

  it("冰後面的陷阱：「陷阱 −6～14・定身」", () => {
    const trap = pathDraw(iceRun).tags.find((t) => t.icon === "trap");
    expect(trap).toEqual({ pos: { x: 3, y: 0 }, icon: "trap", text: "陷阱 −6～14・定身" });
  });

  it("冰後面的陷阱段改紅色虛線；沒有冰時陷阱段是實線", () => {
    const segs = pathSegments(iceRun);
    expect(segs.map((s) => [s.kind, s.dashed])).toEqual([
      ["ice", true],
      ["ice", true],
      ["danger", true],
      ["normal", false],
    ]);
    const solo = preview([step(0, 0, 0), step(1, 1, 0, { trap: true, events: [ev("trap", { other_id: "e1" })] })]);
    expect(pathSegments(solo).map((s) => s.dashed)).toEqual([false]);
  });

  it("畫法：陷阱紅段在冰後面時是虛線（同一筆裡有多個 moveTo）", () => {
    const g = recorder();
    drawPathLine(g, pathDraw(iceRun), geo);
    const red = g.calls.indexOf("Sff6a50");
    const before = g.calls.lastIndexOf("S1e78d0", red);
    const moves = g.calls.slice(before + 1, red).filter((c) => c.startsWith("M")).length;
    expect(moves).toBeGreaterThan(1);
  });
});
