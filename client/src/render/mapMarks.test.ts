// Phase 6C-8：實地地圖標記換新畫法（docs/art/地圖標記.md）——標記清單、腳印幾何、視野樣式與虛線、敵群頭上的眼睛、畫法不寫字。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { fieldHighlights, mapThings, SIGHT_COLOR, watchEyes } from "../world/fieldModel";
import type { UnitDraw } from "../battle/drawModel";
import { DOLL_HEAD_TOP } from "./inkDoll";
import {
  drawCampfire,
  drawEventMark,
  drawObjectHint,
  drawStele,
  drawWatchEye,
  eventBob,
  EVENT_BOB_MS,
  EYE_GAP,
  EYE_HALF_H,
  eyeOffset,
  footprintAlpha,
  footprintShapes,
  MARK_PAD,
  MARK_SIZE,
  MARK_T,
  OBJECT_HINT_MS,
  objectHintAlpha,
  sightStyle,
} from "./mapMarks";
import { DOLL_SCALE } from "./paperdoll";
import { FEET, unitTopY } from "./unitSprite";
import { dashRun } from "./regionBlobs";

function field(over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: 48 }, (_, i) => ({ x: i % 8, y: Math.floor(i / 8), height: 0, terrain: "grass", surface: "none", walkable: true }));
  return {
    map_id: "winter_lake",
    name_zh: "冬湖",
    region: "frost",
    location: "winter_lake",
    interior: false,
    width: 8,
    height: 6,
    tiles,
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [],
    me: { x: 0, y: 0, facing: "s" },
    max_climb: 1,
    stone_targets: [],
    enemies: [
      { id: "wolves", x: 5, y: 2, facing: "w", patrol: true, group: "g", name_zh: "霧狼", elite: false, units: [{ unit: "mist_wolf", name_zh: "霧狼", affix: null, elite: false, third: false }], sight: [[4, 2], [3, 2], [4, 3]] },
      { id: "idle", x: 7, y: 5, facing: "n", patrol: false, group: "g", name_zh: "駐守", elite: false, units: [], sight: [] },
    ],
    friends: [],
    campfires: [{ id: "c", x: 1, y: 4 }],
    event_mark: { x: 6, y: 4 },
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    sneak_problem_zh: null,
    footprints: [
      { owner: "bob", name_zh: "阿博", x: 1, y: 2, facing: "e" },
      { owner: "bob", name_zh: "阿博", x: 2, y: 2, facing: "e" },
      { owner: "bob", name_zh: "阿博", x: 3, y: 3, facing: "s" },
    ],
    note_stone: { x: 0, y: 1, count: 2 },
    ...over,
  } as FieldView;
}

describe("6C-8：標記清單", () => {
  it("「！」、營火、石碑、腳印各一種形狀；腳印越舊越淡（第一個最淡）", () => {
    const things = mapThings(field());
    expect(things.map((t) => t.kind)).toEqual(["event", "campfire", "note_stone", "footprint", "footprint", "footprint"]);
    const prints = things.filter((t) => t.kind === "footprint");
    const alphas = prints.map((t) => (t.kind === "footprint" ? t.alpha : 0));
    expect(alphas[0]).toBeCloseTo(0.4);
    expect(alphas[2]).toBeCloseTo(0.85);
    expect(alphas[0]!).toBeLessThan(alphas[1]!);
    expect(footprintAlpha(0, 1)).toBeCloseTo(0.85);
  });

  it("結果固定（同一張地圖兩次一樣）", () => {
    expect(mapThings(field())).toEqual(mapThings(field()));
  });
});

describe("6C-8：腳印幾何", () => {
  it("每格兩步、每步鞋尖＋鞋跟兩個橢圓，都在格子裡", () => {
    for (const f of ["n", "e", "s", "w"] as const) {
      const e = footprintShapes(f);
      expect(e).toHaveLength(4);
      for (const p of e) {
        expect(p.cx - p.rx).toBeGreaterThanOrEqual(0);
        expect(p.cx + p.rx).toBeLessThanOrEqual(MARK_T);
        expect(p.cy - p.ry).toBeGreaterThanOrEqual(0);
        expect(p.cy + p.ry).toBeLessThanOrEqual(MARK_T);
      }
    }
  });

  it("沿方向走：往東時第二步在第一步的東邊、左右腳分在路線兩側；鞋尖朝前", () => {
    const [toe1, heel1, toe2] = footprintShapes("e");
    expect(toe2!.cx).toBeGreaterThan(toe1!.cx);
    expect(Math.sign(toe1!.cy - MARK_T / 2)).toBe(-Math.sign(toe2!.cy - MARK_T / 2)); // 左右腳交替
    expect(toe1!.cx).toBeGreaterThan(heel1!.cx); // 鞋尖在鞋跟前面
    expect(toe1!.rx).toBeGreaterThan(toe1!.ry); // 橫走：長軸在水平方向
    const [toeN] = footprintShapes("n");
    expect(toeN!.ry).toBeGreaterThan(toeN!.rx);
  });
});

describe("6C-8：敵人視野併成一塊、虛線外緣", () => {
  it("平常淡紅 0.20、虛線 [7, 4]；潛行時 0.10、虛線更短更淡", () => {
    const normal = fieldHighlights(field(), null).regions![0]!;
    expect(normal).toMatchObject({ color: SIGHT_COLOR, fill: 0.2, edge: 0.9, dash: [7, 4] });
    expect(normal.cells.map((p) => `${p.x},${p.y}`)).toEqual(["3,2", "4,2", "4,3"]);
    const sneak = fieldHighlights(field({ sneaking: true }), null).regions![0]!;
    expect(sneak).toMatchObject({ fill: 0.1, edge: 0.55, dash: [3, 5] });
    expect(sightStyle(true).fill).toBeLessThan(sightStyle(false).fill);
  });

  it("不再有格子框或格角記號（telegraph 裡沒有視野、也沒有「！」等標記）", () => {
    const h = fieldHighlights(field(), null);
    expect(h.telegraph).toEqual([]);
  });

  it("dashRun：沿折線切成實線段，跨轉角接著量；總長照比例", () => {
    const run = [
      { x: 0, y: 0 },
      { x: 20, y: 0 },
      { x: 20, y: 10 },
    ];
    const dashes = dashRun(run, 7, 4);
    const len = (r: { x: number; y: number }[]) => r.slice(1).reduce((s, p, i) => s + Math.hypot(p.x - r[i]!.x, p.y - r[i]!.y), 0);
    expect(dashes.map((d) => Math.round(len(d) * 100) / 100)).toEqual([7, 7, 7]); // 0–7、11–18、22–29
    expect(dashes[1]![0]).toEqual({ x: 11, y: 0 });
    expect(dashes[2]![0]).toEqual({ x: 20, y: 2 }); // 空白 18–22 跨過轉角，接著量
    expect(dashRun(run, 6, 2)[2]!.some((p) => p.x === 20 && p.y === 0)).toBe(true); // 實線 16–22 跨過轉角時帶著轉角點
    expect(dashRun(run, 0, 4)).toEqual([run]);
    expect(dashRun([{ x: 0, y: 0 }], 7, 4)).toEqual([]);
  });
});

describe("6C-8：「誰在看」改成敵群頭上的眼睛", () => {
  it("有視野的敵群才有眼睛，放在敵群那格的頭上；潛行時半閉", () => {
    expect(watchEyes(field())).toEqual([{ pos: { x: 5, y: 2 }, sneaking: false }]);
    expect(watchEyes(field({ sneaking: true }))).toEqual([{ pos: { x: 5, y: 2 }, sneaking: true }]);
    expect(fieldHighlights(field(), null).eyes).toEqual(watchEyes(field()));
    const at = eyeOffset(48);
    expect(at.x).toBe(24);
    expect(at.y).toBeLessThan(0); // 找不到單位時：格子上緣再往上 18px（6C-8 的位置）
  });
});

describe("6C-8b：眼睛放在單位圖實際頂端再往上 6px", () => {
  const unit = (over: Partial<UnitDraw>): UnitDraw => ({
    id: "u1", x: 0, y: 0, marker: "A", template: "t", name: "n", team: "enemy", fill: 0, hpRatio: 1, shieldRatio: 0,
    active: false, hero: false, downed: false, summon: false, totem: false, remaining: null, revivable: false, bomb: null,
    facing: "west", weaponId: "fangs", weaponClass: "melee", ...over,
  });
  const look = (creature: Record<string, unknown> | null, over: Record<string, unknown> = {}): UnitDraw["dollLook"] =>
    ({ skin: "#f1c9a5", skull: false, gear: {}, beard: false, affixes: [], traits: [], ...(creature === null ? {} : { creature: { traits: [], ...creature } }), ...over }) as UnitDraw["dollLook"];
  /** 眼睛下緣（相對格子中心）。 */
  const eyeBottom = (u: UnitDraw) => eyeOffset(48, unitTopY(u)).y - 24 + EYE_HALF_H;

  it("眼睛下緣 ＝ 單位頂端 − 6px（人形、異形、頭目都一樣）", () => {
    const cases = [unit({}), unit({ dollLook: look({ body: "golem", size: "large" }) }), unit({ dollLook: look({ body: "bear", size: "huge" }) })];
    for (const u of cases) expect(eyeBottom(u)).toBeCloseTo(unitTopY(u) - EYE_GAP);
    expect(EYE_GAP).toBe(6);
  });

  it("單位頂端照實際畫出來的高度：人形約 47px 高；越高大的異形頂端越高；精英人形比一般人形高", () => {
    const human = unitTopY(unit({}));
    expect(FEET - human).toBeCloseTo(DOLL_HEAD_TOP * (48 / 52) * DOLL_SCALE);
    const ooze = unitTopY(unit({ dollLook: look({ body: "ooze", size: "medium" }) }));
    const golem = unitTopY(unit({ dollLook: look({ body: "golem", size: "medium" }) }));
    const golemL = unitTopY(unit({ dollLook: look({ body: "golem", size: "large" }) }));
    const golemBoss = unitTopY(unit({ dollLook: look({ body: "golem", size: "huge" }) }));
    expect(ooze).toBeGreaterThan(human); // 軟泥比人矮：眼睛跟著低
    expect(golemL).toBeLessThan(golem);
    expect(golemBoss).toBeLessThan(golemL); // 頭目（×0.9 後）仍比 large 高
    expect(golemBoss).toBeLessThan(human - 10); // 大型異形頭頂遠高於人：6C-8 固定位置（−42）會蓋在身上
    expect(eyeOffset(48, golemBoss).y + EYE_HALF_H).toBeLessThan(24 + golemBoss);
    expect(unitTopY(unit({ elite: true }))).toBeLessThan(human);
  });
});

describe("6C-8b：情境物件提示（金色虛線呼吸光＋小手）", () => {
  it("虛線圈的不透明度呼吸：0.45～0.85、週期 1.4 秒", () => {
    expect(objectHintAlpha(0)).toBeCloseTo(0.65);
    expect(objectHintAlpha(OBJECT_HINT_MS / 4)).toBeCloseTo(0.85);
    expect(objectHintAlpha((OBJECT_HINT_MS * 3) / 4)).toBeCloseTo(0.45);
    expect(objectHintAlpha(OBJECT_HINT_MS)).toBeCloseTo(0.65);
  });

  it("虛線圈在物件底下（格子下方 0.7 處的金色虛線橢圓）、小手在右上", () => {
    const calls: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get(t, p: string) {
        if (p in t) return t[p];
        return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (Array.isArray(x) ? `[${x.join(",")}]` : String(x))).join(",")})`);
      },
      set(t, p: string, v) {
        t[p] = v;
        calls.push(`${p}=${String(v)}`);
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    drawObjectHint(ctx, "ring");
    expect(calls).toContain("setLineDash([4,3])");
    expect(calls.some((c) => c.startsWith(`ellipse(${MARK_T / 2},${MARK_T * 0.7},19,8`))).toBe(true);
    expect(calls).toContain("strokeStyle=rgb(255,210,58)");
    calls.length = 0;
    drawObjectHint(ctx, "hand");
    expect(calls).toContain(`translate(${MARK_T - 8},8)`);
  });
});

describe("6C-8：畫法（程式繪製、不寫字、不畫格子框）", () => {
  function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
    const calls: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get(t, p: string) {
        if (p in t) return t[p];
        if (p === "createLinearGradient" || p === "createRadialGradient") return () => ({ addColorStop: () => undefined });
        return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(1) : String(x))).join(",")})`);
      },
      set(t, p: string, v) {
        t[p] = v;
        calls.push(`${p}=${String(v)}`);
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    return { ctx, calls };
  }
  const draws: Array<[string, (c: CanvasRenderingContext2D) => void]> = [
    ["事件", (c) => drawEventMark(c)],
    ["營火", (c) => drawCampfire(c, true)],
    ["營火（紮過）", (c) => drawCampfire(c, false)],
    ["石碑", (c) => drawStele(c, false)],
    ["石碑（未讀）", (c) => drawStele(c, true)],
    ["眼睛", (c) => drawWatchEye(c, false)],
    ["眼睛（潛行）", (c) => drawWatchEye(c, true)],
    ["情境物件虛線圈", (c) => drawObjectHint(c, "ring")],
    ["情境物件小手", (c) => drawObjectHint(c, "hand")],
  ];

  it.each(draws)("%s：沒有 fillText、沒有格子大小的 rect／strokeRect", (_name, draw) => {
    const { ctx, calls } = recorder();
    draw(ctx);
    expect(calls.length).toBeGreaterThan(5);
    expect(calls.some((c) => c.startsWith("fillText") || c.startsWith("strokeText"))).toBe(false);
    expect(calls.some((c) => /^(strokeRect|fillRect|rect)\(/.test(c))).toBe(false);
  });

  it("狀態不同畫法不同：營火熄了少畫火苗、石碑有未讀多一個紅點、潛行的眼睛多一片眼皮", () => {
    const n = (draw: (c: CanvasRenderingContext2D) => void) => {
      const r = recorder();
      draw(r.ctx);
      return r.calls.length;
    };
    expect(n((c) => drawCampfire(c, false))).toBeLessThan(n((c) => drawCampfire(c, true)));
    expect(n((c) => drawStele(c, true))).toBeGreaterThan(n((c) => drawStele(c, false)));
    expect(n((c) => drawWatchEye(c, true))).toBeGreaterThan(n((c) => drawWatchEye(c, false)));
  });

  it("「！」上下浮 3px、週期 1.6 秒；貼圖四周留邊", () => {
    expect(eventBob(0)).toBeCloseTo(0);
    expect(eventBob(EVENT_BOB_MS / 4)).toBeCloseTo(3);
    expect(eventBob(EVENT_BOB_MS)).toBeCloseTo(0);
    expect(MARK_SIZE).toBe(MARK_T + 2 * MARK_PAD);
  });
});
