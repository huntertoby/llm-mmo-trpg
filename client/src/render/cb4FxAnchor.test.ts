// CB-4：異形（含頭目）片段自帶的特效在正南、正北、四個斜向時落在目標格；東西向不變（`docs/phases/PhaseCB-4計畫.md`「行為一致測試」1～5）。
// 單位外觀讀實際的 content/units/*.yaml（硫煙獸＝一般、熔爐母獸＋精英＝精英＋大型、灰燼之心第 1 階段、碎晶之主）。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync } from "node:fs";
import { parse } from "yaml";
import type { Facing, Pos } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import type { UnitDraw } from "../battle/drawModel";
import { creatureFxAnchorPx, creatureFxTurnOf, fxTurnScale, turnCreatureFx } from "./creatureFxTurn";
import { creaturePoseKey, quantizeCreaturePose, type CreatureFx, type CreaturePose, type FxTurn } from "./creaturePose";
import { CREATURE_FX_BOX, ELITE_SCALE, fxSizeOf, rigKey, SIZES, turnedCreatureFx, type ResolvedCreature } from "./inkCreature";
import { DOLL_SCALE } from "./paperdoll";
import { BODY_ANIM, CREATURE_FX_TARGET_X, creatureAttackHitU, creatureOwnFrames, drawCreatureFx, qCreaturePartPose } from "./qCreatureAnim";
import { bossAttackHitU, bossPlan, BOSS_CLIPS, drawBossFrame } from "./qBoss";
import { creatureFieldScale, creatureOf, creatureOffsetPx, creatureSide } from "./unitSprite";
import { fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";

const T = TILE_SIZE;
const readText = readFileSync as (url: URL, enc: string) => string;
const dollOf = (id: string): Record<string, unknown> =>
  (parse(readText(new URL(`../../../content/units/${id}.yaml`, import.meta.url), "utf-8")) as { doll: { creature: Record<string, unknown> } }).doll.creature;

function drawOf(id: string, elite: boolean, facing: Facing, bossPhase: number | null = null, at: Pos = { x: 4, y: 4 }): UnitDraw {
  return { id: "c", template: id, x: at.x, y: at.y, dollLook: { creature: dollOf(id) }, summonLook: null, team: "enemy", facing, summon: false, totem: false, downed: false, formId: null, elite, bossPhase } as unknown as UnitDraw;
}

/** 四種：一般、精英＋大型、兩個頭目（灰燼之心第 1 階段＝`ram`）。`east`：修改前（17982c56 的 `creatureOffsetPx`）的東西向錨點 px。 */
const CASES = [
  { label: "一般（硫煙獸）", id: "sulfur_beast", elite: false, phase: null, size: 1, east: 50.88, clip: "atk:uptusk" },
  { label: "精英＋大型（熔爐母獸）", id: "furnace_matriarch", elite: true, phase: null, size: SIZES["large"]! * ELITE_SCALE, east: 73.14, clip: "atk:tailover" },
  { label: "灰燼之心（第 1 階段）", id: "ashen_heart", elite: true, phase: 1, size: 1, east: 81.41, clip: "atk:@melee" },
  { label: "碎晶之主", id: "rift_shard_lord", elite: true, phase: null, size: 1, east: 81.41, clip: "atk:@melee" },
] as const;

const DIRS: ReadonlyArray<readonly [string, number, number]> = [
  ["東", 1, 0],
  ["西", -1, 0],
  ["南", 0, 1],
  ["北", 0, -1],
  ["東南", 1, 1],
  ["東北", 1, -1],
  ["西南", -1, 1],
  ["西北", -1, -1],
];
const TURNED = DIRS.filter(([, , dy]) => dy !== 0);

/** 出招時畫出來的那一面：東西向照目標，同一欄維持原朝向（`creatureFacingTo`，D4 不改）。 */
const sideOf = (dx: number, facing: "east" | "west"): "east" | "west" => (dx > 0 ? "east" : dx < 0 ? "west" : facing);

interface Setup {
  u: UnitDraw;
  cr: ResolvedCreature;
  size: number;
  field: number;
  /** 轉向貼圖裡一個（未乘大小的）虛擬單位＝幾 px（同 `skillLayer.placeTurnedFx` 的 `k` × 大小）。 */
  k: number;
  c: number;
}
function setup(c: (typeof CASES)[number], side: "east" | "west"): Setup {
  const u = drawOf(c.id, c.elite, side, c.phase);
  const cr = creatureOf(u)!;
  const size = fxSizeOf(cr);
  const field = creatureFieldScale(u);
  return { u, cr, size, field, k: (T / 52) * DOLL_SCALE * field * size, c: fxTurnScale(size, field, DOLL_SCALE) };
}

/** 這個片段的格數（第二種近戰照自己的格數；頭目照戰場攻擊片段 12 格）。 */
function framesOf(cr: ResolvedCreature, clip: string): number {
  return cr.boss === undefined ? creatureOwnFrames(rigKey(cr), clip)!.n : 12;
}

describe("CB-4 錨點表：8 方向 × 一般／精英＋大型／兩個頭目 × 原本朝東／朝西", () => {
  for (const c of CASES) {
    for (const [name, dx, dy] of DIRS) {
      for (const facing of ["east", "west"] as const) {
        it(`${c.label} 目標在${name}（原本朝${facing === "east" ? "東" : "西"}）`, () => {
          const from = { x: 4, y: 4 };
          const to = { x: 4 + dx, y: 4 + dy };
          const s = setup(c, sideOf(dx, facing));
          expect(s.size).toBeCloseTo(c.size, 9); // 頭目貼圖不含大小（1）
          expect(s.cr.boss === undefined).toBe(c.phase === null && c.id !== "rift_shard_lord");
          const a = creatureFxAnchorPx({ from, to, side: creatureSide(s.u), size: s.size, fieldScale: s.field, dollScale: DOLL_SCALE, tile: T });
          if (dy === 0) {
            // 東西向：和修改前相同（修改前＝身體貼圖裡的「相鄰目標」點，`creatureOffsetPx` 頭目貼圖不含大小）
            const before = creatureOffsetPx(s.u, s.cr, { dx: CREATURE_FX_TARGET_X });
            expect(a.x).toBeCloseTo(before.x, 9);
            expect(a.y).toBe(0);
            expect(a.x).toBeCloseTo(dx * c.east, 2);
          } else {
            // 南、北、斜向：目標格中心
            expect(Math.abs(a.x - dx * T)).toBeLessThanOrEqual(0.01);
            expect(Math.abs(a.y - dy * T)).toBeLessThanOrEqual(0.01);
          }
        });
      }
    }
  }
});

/** 特效（ground＝地面落點，扣掉離地高度）相對目標格中心的位置（px）。`c＝0` 那一份只剩高度（同 CB-3c 的量法）。 */
function groundRel(s: Setup, pose: CreaturePose, turn: FxTurn): Array<{ k: string; gx: number; gy: number; r: number; h: number }> {
  const fx = turnedCreatureFx(s.cr, pose, s.c);
  const flat = turnedCreatureFx(s.cr, pose, 0);
  const a = creatureFxAnchorPx({ from: { x: 4, y: 4 }, to: { x: 4 + turn.x, y: 4 + turn.y }, side: creatureSide(s.u), size: s.size, fieldScale: s.field, dollScale: DOLL_SCALE, tile: T });
  const mirror = creatureSide(s.u) === "west" ? -1 : 1;
  return fx.map((e, i) => ({
    k: e.k,
    gx: a.x + mirror * (e.x ?? 0) * s.k - turn.x * T,
    gy: a.y + ((e.y ?? 0) - (flat[i]!.y ?? 0)) * s.k - turn.y * T,
    r: (e.r ?? 0) * s.k,
    h: (flat[i]!.y ?? 0) * s.k,
  }));
}

describe("CB-4 實際片段：南、北、四個斜向逐格，星爆／白弧在目標格、塵土在施放者到目標之間", () => {
  for (const c of CASES) {
    for (const [name, dx, dy] of TURNED) {
      it(`${c.label} ${c.clip} 目標在${name}`, () => {
        const turn = { x: dx, y: dy } as FxTurn;
        const s = setup(c, sideOf(dx, "east"));
        const n = framesOf(s.cr, c.clip);
        const seen: Record<string, number> = {};
        for (let f = 0; f < n; f++) {
          const pose: CreaturePose = { clip: c.clip, u: f / (n - 1), fxTurn: turn };
          for (const e of groundRel(s, pose, turn)) {
            seen[e.k] = (seen[e.k] ?? 0) + 1;
            const along = [e.gx * dx, e.gy * dy]; // 往目標方向的分量（相對目標格中心；負＝往施放者）
            if (e.k === "burst" && c.id === "sulfur_beast") {
              // 硫煙獸挑獠牙的星爆在獠牙尖（東西向時圓心離目標格中心 23.3 px、正南北 24.7 px，兩格交界）：圓碰得到目標格（同 CB-3c 的判定）
              for (const v of [e.gx, e.gy]) expect(Math.abs(v) - e.r, `f${f} 星爆`).toBeLessThanOrEqual(T / 2);
            } else if (e.k === "burst" || e.k === "slash") {
              // 星爆、頭目白弧：圓心在目標格內（每軸 |Δ| ≤ 24 px）
              expect(Math.abs(e.gx), `f${f} ${e.k} x`).toBeLessThanOrEqual(T / 2);
              expect(Math.abs(e.gy), `f${f} ${e.k} y`).toBeLessThanOrEqual(T / 2);
            } else if (e.k === "sweep") {
              // 一般異形的白弧是獠牙／尾巴掃過的軌跡：圓心在施放者那一格到目標格之間（同 CB-3c）
              for (const v of along) {
                if (Number.isNaN(v)) continue;
                expect(v, `f${f} 白弧圓心`).toBeGreaterThanOrEqual(-T);
                expect(v, `f${f} 白弧圓心`).toBeLessThanOrEqual(T / 2);
              }
            } else if (e.k === "dust") {
              // 塵土：施放者那一格到目標格之間（往目標方向的分量在 [−1.5 格, 0.5 格]），橫向不偏出連線那一欄
              for (const [i, v] of along.entries()) {
                if ((i === 0 ? dx : dy) === 0) expect(Math.abs(i === 0 ? e.gx : e.gy), `f${f} 塵土橫向`).toBeLessThanOrEqual(T / 2);
                else {
                  expect(v, `f${f} 塵土`).toBeGreaterThanOrEqual(-1.5 * T);
                  expect(v, `f${f} 塵土`).toBeLessThanOrEqual(T / 2);
                }
              }
            }
            // 高度照片段（打在身上，不超過一格半）
            expect(e.h, `f${f} ${e.k} 高度`).toBeLessThanOrEqual(0);
            expect(e.h, `f${f} ${e.k} 高度`).toBeGreaterThanOrEqual(-1.5 * T);
          }
        }
        // 這四個片段在命中那幾格都有星爆或白弧
        expect((seen["burst"] ?? 0) + (seen["slash"] ?? 0)).toBeGreaterThan(0);
      });
    }
  }

  it("片段特效的數值取自片段函式（灰燼之心 `ram`、碎晶之主 `swing`）", () => {
    const ah = setup(CASES[2], "east");
    expect(ah.cr.boss).toEqual({ id: "ah", phase: 1 });
    const u = 6 / 11;
    expect(turnedCreatureFx(ah.cr, { clip: "atk:@melee", u, fxTurn: { x: 1, y: 1 } }, ah.c)).toEqual(turnCreatureFx(bossPlan("ah", "ram", u, { phase: 1 }).fx, { x: 1, y: 1 }, ah.c));
    const sl = setup(CASES[3], "east");
    expect(turnedCreatureFx(sl.cr, { clip: "atk:@melee", u, fxTurn: { x: 0, y: -1 } }, sl.c)).toEqual(turnCreatureFx(bossPlan("sl", "swing", u, { phase: sl.cr.boss!.phase }).fx, { x: 0, y: -1 }, sl.c));
    const boar = setup(CASES[0], "east");
    const pp = qCreaturePartPose({ key: "boar", element: boar.cr.element, mat: "flesh", base: "#888", accent: null, traits: [] }, "atk:uptusk", 5 / 11)!;
    expect(pp.fx.length).toBeGreaterThan(0);
  });

  it("轉向貼圖放得下：一般身形全部攻擊片段 × 精英＋大型 × 6 方向，特效位置在 `CREATURE_FX_BOX` 內；頭目 u 在 −8～−2", () => {
    const big = SIZES["large"]! * ELITE_SCALE;
    const half = CREATURE_FX_BOX.w / 2;
    for (const key of Object.keys(BODY_ANIM)) {
      for (const clip of Object.keys(BODY_ANIM[key]!.attacks)) {
        for (let f = 0; f <= 11; f++) {
          const pp = qCreaturePartPose({ key, element: undefined, mat: "flesh", base: "#888888", accent: null, traits: [] }, `atk:${clip}`, f / 11);
          if (pp === null) continue;
          const fx = pp.fx.filter((e) => e.ranged !== true && e.lobbed !== true && e.k !== "cone");
          for (const [, dx, dy] of TURNED) {
            for (const e of turnCreatureFx(fx, { x: dx, y: dy } as FxTurn, fxTurnScale(big, 1, DOLL_SCALE))) {
              for (const x of [e.x, e.x0, e.x1]) if (x !== undefined) expect((Math.abs(x) + (e.r ?? 0)) * big, `${key} ${clip} f${f} ${e.k}`).toBeLessThanOrEqual(half);
              for (const y of [e.y, e.y0, e.y1]) if (y !== undefined) {
                expect(y * big, `${key} ${clip} f${f} ${e.k}`).toBeGreaterThanOrEqual(-CREATURE_FX_BOX.foot);
                expect(y * big, `${key} ${clip} f${f} ${e.k}`).toBeLessThanOrEqual(CREATURE_FX_BOX.h - CREATURE_FX_BOX.foot);
              }
            }
          }
        }
      }
    }
    for (const [who, clip] of [["ah", "ram"], ["sl", "swing"]] as const)
      for (let f = 0; f <= 11; f++)
        for (const e of turnCreatureFx(bossPlan(who, clip, f / 11, { phase: 1 }).fx, { x: 1, y: 1 }, 1)) {
          expect(e.x!).toBeGreaterThanOrEqual(-8);
          expect(e.x!).toBeLessThanOrEqual(-2);
        }
  });
});

/** CB-3c（17982c56）的 `turnCreatureFx`，原樣抄來當同一欄的期望值。 */
function cb3cTurn(fxs: readonly CreatureFx[], turn: 1 | -1, c: number): CreatureFx[] {
  const ty = (x: number, y: number): number => y + turn * (x - CREATURE_FX_TARGET_X) * c;
  return fxs.map((f) => {
    const out: CreatureFx = { ...f, x: 0, y: ty(f.x ?? 0, f.y ?? 0) };
    if (f.x0 !== undefined || f.y0 !== undefined) Object.assign(out, { x0: 0, y0: ty(f.x0 ?? 0, f.y0 ?? 0) });
    if (f.x1 !== undefined || f.y1 !== undefined) Object.assign(out, { x1: 0, y1: ty(f.x1 ?? 0, f.y1 ?? 0) });
    if (f.k === "cone") {
      const a = f.ang ?? 0;
      const v = turn * c * Math.cos(a) + Math.sin(a);
      Object.assign(out, { ang: v >= 0 ? Math.PI / 2 : -Math.PI / 2, max: (f.max ?? 30) * Math.abs(v) });
    }
    return out;
  });
}

describe("CB-4 退化一致：同一欄＝CB-3c、同一排不轉", () => {
  it("同一欄的一般異形：全部身形的全部攻擊片段逐格，`turnCreatureFx` 和 CB-3c 逐筆相同（含吐息）", () => {
    let n = 0;
    for (const key of Object.keys(BODY_ANIM)) {
      for (const clip of Object.keys(BODY_ANIM[key]!.attacks)) {
        for (let f = 0; f <= 11; f++) {
          const pp = qCreaturePartPose({ key, element: undefined, mat: "flesh", base: "#888888", accent: null, traits: [] }, `atk:${clip}`, f / 11);
          if (pp === null || pp.fx.length === 0) continue;
          for (const turn of [1, -1] as const)
            for (const c of [fxTurnScale(1, 1, DOLL_SCALE), fxTurnScale(SIZES["large"]! * ELITE_SCALE, 1, DOLL_SCALE)]) {
              expect(turnCreatureFx(pp.fx, { x: 0, y: turn }, c)).toEqual(cb3cTurn(pp.fx, turn, c));
              n++;
            }
        }
      }
    }
    expect(n).toBeGreaterThan(100);
    // 吐息斜著噴（ang ≠ 0）也相同
    const cone: CreatureFx[] = [{ k: "cone", x: 10, y: -8, ang: -0.4, max: 30 }];
    expect(turnCreatureFx(cone, { x: 0, y: 1 }, 0.8)).toEqual(cb3cTurn(cone, 1, 0.8));
  });

  it("同一排（東、西）`creatureFxTurnOf` 回 null；沒有轉向時姿勢鍵和修改前相同", () => {
    for (const to of [{ x: 5, y: 4 }, { x: 2, y: 4 }, { x: 4, y: 4 }]) expect(creatureFxTurnOf({ x: 4, y: 4 }, to)).toBeNull();
    // 修改前（17982c56）的鍵，逐字
    expect(creaturePoseKey({ clip: "atk:@melee2", u: 0.5 })).toBe("atk:@melee2@0.5000");
    expect(creaturePoseKey({ clip: "atk:uptusk", u: 5 / 11, dx: 3.3, inPlace: true })).toBe("dx3.3,atk:uptusk@0.4545,inplace");
    expect(quantizeCreaturePose({ clip: "atk:uptusk", u: 0.4 })).toEqual({ clip: "atk:uptusk", u: 0.4 });
  });

  it("斜向的方向與鍵（同一欄的鍵由 `fxturn1` 改成 `fxturn0:1`，只出現在轉向貼圖）", () => {
    expect(creatureFxTurnOf({ x: 4, y: 4 }, { x: 5, y: 5 })).toEqual({ x: 1, y: 1 });
    expect(creatureFxTurnOf({ x: 4, y: 4 }, { x: 3, y: 3 })).toEqual({ x: -1, y: -1 });
    expect(creatureFxTurnOf({ x: 4, y: 4 }, { x: 6, y: 3 })).toEqual({ x: 1, y: -1 }); // 隔一格（Q6：錨點仍放相鄰格）
    expect(creaturePoseKey({ clip: "atk:@melee", u: 0.5, fxTurn: { x: -1, y: 1 } })).toBe("atk:@melee@0.5000,fxturn-1:1");
  });

  it("斜向的剪切：橫向距離照舊、往前的距離加到南北；吐息方向照同一規則", () => {
    const c = 0.9;
    const [hit, self] = turnCreatureFx([{ k: "burst", x: CREATURE_FX_TARGET_X, y: -5 }, { k: "dust", x: 0, y: 0 }], { x: 1, y: -1 }, c);
    expect(hit).toMatchObject({ x: 0, y: -5 });
    expect(self!.x).toBe(-CREATURE_FX_TARGET_X);
    expect(self!.y).toBeCloseTo(CREATURE_FX_TARGET_X * c, 9);
    const [cone] = turnCreatureFx([{ k: "cone", x: 10, y: -8, ang: 0, max: 30 }], { x: 1, y: 1 }, 1);
    expect(cone!.ang).toBeCloseTo(Math.PI / 4, 9);
    expect(cone!.max).toBeCloseTo(30 * Math.SQRT2, 9);
  });
});

describe("CB-4 頭目身體貼圖：有轉向時不畫片段特效，身體逐筆相同", () => {
  const cases = [
    { who: "ah", template: "ashen_heart", phase: 1, clip: "ram" },
    { who: "sl", template: "rift_shard_lord", phase: 2, clip: "swing" },
  ] as const;
  for (const c of cases) {
    it(`${c.template} ${c.clip}：有出手特效的每一格`, () => {
      const boss = { id: c.who, phase: c.phase };
      let checked = 0;
      for (let f = 0; f <= 11; f++) {
        const u = f / 11;
        const fx = bossPlan(c.who, c.clip, u, { phase: c.phase }).fx;
        const rec = (pose: CreaturePose): string[] => {
          const log: FakeCanvasLog = { calls: [] };
          drawBossFrame(fakeCtx(log, 400, 300), boss, pose, false);
          return log.calls!;
        };
        const plain = rec({ clip: "atk:@melee", u });
        const turned = rec({ clip: "atk:@melee", u, fxTurn: { x: 0, y: 1 } });
        if (fx.length === 0) {
          expect(turned).toEqual(plain);
          continue;
        }
        const fxLog: FakeCanvasLog = { calls: [] };
        drawCreatureFx(fakeCtx(fxLog, 400, 300), fx, undefined, [-110, -160, 120, 20]);
        expect(fxLog.calls!.length).toBeGreaterThan(0);
        // 沒轉向＝身體那幾筆＋特效那幾筆＋最後的 restore；有轉向＝少了特效那幾筆
        expect(plain).toEqual([...turned.slice(0, -1), ...fxLog.calls!, turned.at(-1)!]);
        expect(turned.at(-1)).toBe("restore()");
        checked++;
      }
      expect(checked).toBeGreaterThan(0);
    });
  }
});

describe("CB-4 命中對齊不變", () => {
  // 修改前（17982c56）逐一算出的值（`creatureAttackHitU`／`bossAttackHitU`，小數 6 位）
  const BEFORE: Readonly<Record<string, number>> = {"bat|bite":0.454545,"bat|fire":0.454545,"bear|quake":0.545455,"bear|slam":0.530303,"bear|swipe":0.454545,"beetle|burst":0.454545,"beetle|horn":0.545455,"beetle|ram":0.545455,"bird|cast":0.181818,"bird|dive":0.636364,"bird|rake":0.545455,"boar|breath":0.363636,"boar|gore":0.636364,"boar|uptusk":0.416667,"feline|claw":0.454545,"feline|pounce":0.727273,"feline|upcut":0.5,"golem|cast":0.545455,"golem|quake":0.636364,"golem|smash":0.545455,"hound|bite":0.363636,"hound|cast":0.454545,"hound|maul":0.30303,"lizard|bite":0.454545,"lizard|cast":0.545455,"lizard|summon":0.909091,"lizard|tailover":0.4,"ooze|slam":0.636364,"ooze|spit":0.454545,"pylon|beam":0.454545,"pylon|pulse":0.454545,"serpent|strike":0.454545,"shell|breath":0.363636,"shell|lob":0.363636,"spider|bite":0.454545,"wisp|pulse":0.454545,"wisp|shards":0.636364,"wraith|blink":0.5,"wraith|claw":0.454545,"wraith|gaze":0.454545,"boss:ah|spout|1":0.545455,"boss:ah|spout|2":0.545455,"boss:ah|spout|3":0.545455,"boss:ah|firebolt|1":0.545455,"boss:ah|firebolt|2":0.545455,"boss:ah|firebolt|3":0.545455,"boss:ah|ram|1":0.545455,"boss:ah|ram|2":0.545455,"boss:ah|ram|3":0.545455,"boss:ah|hit|1":0.363636,"boss:ah|hit|2":0.363636,"boss:ah|hit|3":0.363636,"boss:ah|death|1":0.090909,"boss:ah|death|2":0.090909,"boss:ah|death|3":0.090909,"boss:sl|thunder|1":0.454545,"boss:sl|thunder|2":0.454545,"boss:sl|thunder|3":0.454545,"boss:sl|swing|1":0.454545,"boss:sl|swing|2":0.454545,"boss:sl|swing|3":0.454545,"boss:sl|hit|1":0.5,"boss:sl|hit|2":0.5,"boss:sl|hit|3":0.5,"boss:sl|death|1":0.090909,"boss:sl|death|2":0.090909,"boss:sl|death|3":0.090909};
  it("一般異形全部攻擊片段、兩個頭目全部片段 × 第 1～3 階段", () => {
    const now: Record<string, number> = {};
    for (const key of Object.keys(BODY_ANIM).sort()) for (const clip of Object.keys(BODY_ANIM[key]!.attacks).sort()) now[`${key}|${clip}`] = Number(creatureAttackHitU(key, `atk:${clip}`).toFixed(6));
    for (const who of ["ah", "sl"] as const) for (const clip of BOSS_CLIPS[who]) for (const ph of [1, 2, 3]) now[`boss:${who}|${clip}|${ph}`] = Number(bossAttackHitU(who, clip, ph).toFixed(6));
    expect(now).toEqual(BEFORE);
  });
});
