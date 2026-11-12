// CB-3c 交付 1、3（A）：目標在正南／正北時，異形片段自帶的特效（星爆、白弧、塵土）落在目標格；東西向、斜向照舊。
// 單位外觀讀實際的 content/units/*.yaml（硫煙獸＝一般大小、熔爐母獸＋精英＝精英＋大型）。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync } from "node:fs";
import { parse } from "yaml";
import type { Facing, Pos } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import { creatureFxAnchorPx, creatureFxTurnOf, fxTurnScale, turnCreatureFx } from "./creatureFxTurn";
import { creaturePoseKey, quantizeCreaturePose, type CreatureFx } from "./creaturePose";
import { ELITE_SCALE, SIZES, turnedCreatureFx, type ResolvedCreature } from "./inkCreature";
import { DOLL_SCALE } from "./paperdoll";
import { CREATURE_FX_TARGET_X, creatureOwnFrames } from "./qCreatureAnim";
import type { UnitDraw } from "../battle/drawModel";
import { creatureFieldScale, creatureOf, creatureOffsetPx, creatureSide } from "./unitSprite";

const T = TILE_SIZE;
const readText = readFileSync as (url: URL, enc: string) => string;
const dollOf = (id: string): Record<string, unknown> =>
  (parse(readText(new URL(`../../../content/units/${id}.yaml`, import.meta.url), "utf-8")) as { doll: { creature: Record<string, unknown> } }).doll.creature;

function drawOf(id: string, elite: boolean, facing: Facing, at: Pos = { x: 4, y: 4 }): UnitDraw {
  return { id: "c", template: id, x: at.x, y: at.y, dollLook: { creature: dollOf(id) }, summonLook: null, team: "enemy", facing, summon: false, totem: false, downed: false, formId: null, elite } as unknown as UnitDraw;
}

const CASES = [
  { label: "一般（硫煙獸）", id: "sulfur_beast", elite: false, size: 1 },
  { label: "精英＋大型（熔爐母獸）", id: "furnace_matriarch", elite: true, size: SIZES["large"]! * ELITE_SCALE },
] as const;

// 8 個方向（dx, dy）：同一欄只有正南、正北
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

/** 修改前（CB-3b）的錨點：畫進身體貼圖的「相鄰目標」那一點＝朝向 × 52 個虛擬單位（`creatureOffsetPx`），平地、腳底高度。 */
const BEFORE_X: Readonly<Record<string, number>> = { sulfur_beast: 50.88, furnace_matriarch: 73.14 };

const inTile = (p: { x: number; y: number }, dx: number, dy: number): boolean => Math.abs(p.x - dx * T) <= T / 2 && Math.abs(p.y - dy * T) <= T / 2;

describe("CB-3c 特效錨點：8 方向 × 一般／精英＋大型", () => {
  for (const c of CASES) {
    for (const [name, dx, dy] of DIRS) {
      for (const facing of ["east", "west"] as const) {
        it(`${c.label} 目標在${name}（原本朝${facing === "east" ? "東" : "西"}）`, () => {
          const from = { x: 4, y: 4 };
          const to = { x: 4 + dx, y: 4 + dy };
          // 出招時的朝向：東西向照目標，同一欄維持原朝向（`creatureFacingTo`，D4 不改）
          const side: "east" | "west" = dx > 0 ? "east" : dx < 0 ? "west" : facing;
          const u = drawOf(c.id, c.elite, side);
          const cr = creatureOf(u)!;
          expect(cr.size).toBeCloseTo(c.size, 9);
          const a = creatureFxAnchorPx({ from, to, side: creatureSide(u), size: cr.size, fieldScale: creatureFieldScale(u), dollScale: DOLL_SCALE, tile: T });
          if (dx === 0) {
            // 同一欄：錨點就是目標格中心
            expect(a).toEqual({ x: 0, y: dy * T });
            expect(inTile(a, dx, dy)).toBe(true);
          } else {
            // 東西向、斜向：和修改前相同（以修改前的值為期望值）
            const before = creatureOffsetPx(u, cr, { dx: CREATURE_FX_TARGET_X });
            expect(a.x).toBeCloseTo(before.x, 9);
            expect(a.y).toBe(0);
            expect(Math.abs(a.x)).toBeCloseTo(BEFORE_X[c.id]!, 2);
          }
        });
      }
    }
  }

  it("修改前的東西向錨點：一般在目標格內；精英＋大型超出格邊約 1 px（既有，本段不改，見報告待決）", () => {
    expect(inTile({ x: BEFORE_X["sulfur_beast"]!, y: 0 }, 1, 0)).toBe(true);
    expect(BEFORE_X["furnace_matriarch"]! - 1.5 * T).toBeCloseTo(1.14, 2);
  });
});

describe("CB-3c 特效轉向", () => {
  it("只有同一欄算轉向（正南 1、正北 -1）", () => {
    expect(creatureFxTurnOf({ x: 3, y: 3 }, { x: 3, y: 4 })).toBe(1);
    expect(creatureFxTurnOf({ x: 3, y: 3 }, { x: 3, y: 0 })).toBe(-1);
    for (const to of [{ x: 4, y: 3 }, { x: 2, y: 4 }, { x: 3, y: 3 }]) expect(creatureFxTurnOf({ x: 3, y: 3 }, to)).toBeNull();
    expect(creatureFxTurnOf({ x: 3, y: 3 }, null)).toBeNull();
  });

  it("「相鄰目標」那一點到原點（目標格）、異形自己（x＝0）剛好往回一格；高度不變", () => {
    for (const c of CASES) {
      const k = (T / 52) * DOLL_SCALE * c.size; // 未乘大小的虛擬單位 → 模型像素
      const s = fxTurnScale(c.size, 1, DOLL_SCALE);
      for (const turn of [1, -1] as const) {
        const [hit, self, high] = turnCreatureFx([{ k: "burst", x: CREATURE_FX_TARGET_X, y: 0 }, { k: "dust", x: 0, y: 0 }, { k: "glow", x: CREATURE_FX_TARGET_X, y: -10 }], turn, s);
        expect([hit!.x, hit!.y]).toEqual([0, 0]);
        expect(self!.x).toBe(0);
        expect(self!.y! * k).toBeCloseTo(-turn * T, 9);
        expect(high!.y).toBe(-10);
      }
    }
  });

  it("線段兩端、吐息方向一起轉", () => {
    const [bolt, cone] = turnCreatureFx([{ k: "bolt", x0: 0, y0: -20, x1: CREATURE_FX_TARGET_X, y1: -10 }, { k: "cone", x: 10, y: -8, ang: 0, max: 30 }], 1, 1);
    expect(bolt).toMatchObject({ x0: 0, y0: -20 - CREATURE_FX_TARGET_X, x1: 0, y1: -10 });
    expect(cone!.ang).toBeCloseTo(Math.PI / 2, 9);
    expect(cone!.max).toBeCloseTo(30, 9);
  });

  it("姿勢的快取鍵帶轉向（身體貼圖不含特效時另一張）；沒有轉向時鍵不變", () => {
    const p = { clip: "atk:@melee2", u: 0.5 };
    expect(creaturePoseKey(p)).toBe("atk:@melee2@0.5000");
    expect(creaturePoseKey({ ...p, fxTurn: 1 })).toBe("atk:@melee2@0.5000,fxturn1");
    expect(quantizeCreaturePose({ ...p, fxTurn: -1 }).fxTurn).toBe(-1);
  });
});

describe("CB-3c 實際片段：第二種近戰的星爆、白弧轉向後落在目標身上", () => {
  // 硫煙獸挑獠牙（`3-real-boar-uptusk.jpg` 那一招）、熔爐母獸甩尾（`x-matriarch-…south-target.png` 那一招）
  const CLIPS = [
    { id: "sulfur_beast", elite: false, key: "boar", clip: "atk:uptusk" },
    { id: "furnace_matriarch", elite: true, key: "lizard", clip: "atk:tailover" },
  ] as const;
  for (const c of CLIPS) {
    for (const turn of [1, -1] as const) {
      it(`${c.id} ${c.clip} 目標在正${turn === 1 ? "南" : "北"}`, () => {
        const u = drawOf(c.id, c.elite, "east");
        const cr: ResolvedCreature = creatureOf(u)!;
        const own = creatureOwnFrames(c.key, c.clip)!;
        const s = fxTurnScale(cr.size, 1, DOLL_SCALE);
        const k = (T / 52) * DOLL_SCALE * cr.size;
        let seen = 0;
        for (let f = 0; f < own.n; f++) {
          const pose = { clip: c.clip, u: f / (own.n - 1), fxTurn: turn };
          const fx: CreatureFx[] = turnedCreatureFx(cr, pose, s);
          const flat: CreatureFx[] = turnedCreatureFx(cr, pose, 0); // c＝0：只剩高度（離地多高）
          fx.forEach((e, i) => {
            if (e.k !== "burst" && e.k !== "sweep") return;
            seen++;
            // 相對目標格中心：星爆（命中）的落地點（往前轉成的南北距離）在目標格內；白弧是獠牙／尾巴掃過的軌跡，
            // 圓心在施放者與目標的連線上（施放者那一格到目標格之間）。橫向收在中線；高度照片段（打在身上，不超過一格半）
            const ground = ((e.y ?? 0) - (flat[i]!.y ?? 0)) * k;
            const height = (flat[i]!.y ?? 0) * k;
            expect(e.x, `f${f} ${e.k}`).toBe(0);
            // 星爆畫出來的圓（半徑 r）碰得到目標格（硫煙獸挑獠牙的星爆在獠牙尖，圓心離目標格中心 24.7 px，東西向時同樣在兩格交界）
            if (e.k === "burst") expect(Math.abs(ground) - (e.r ?? 0) * k, `f${f} 星爆落地點`).toBeLessThanOrEqual(T / 2);
            else {
              expect(ground * turn, `f${f} 白弧圓心`).toBeGreaterThanOrEqual(-T);
              expect(ground * turn, `f${f} 白弧圓心`).toBeLessThanOrEqual(T / 2);
            }
            expect(height, `f${f} ${e.k} 高度`).toBeLessThanOrEqual(0);
            expect(height, `f${f} ${e.k} 高度`).toBeGreaterThanOrEqual(-1.5 * T);
          });
        }
        expect(seen).toBeGreaterThan(0);
      });
    }
  }

  it("頭目、沒有轉向時不另畫（照舊畫進身體貼圖）", () => {
    const u = drawOf("sulfur_beast", false, "east");
    const cr = creatureOf(u)!;
    expect(turnedCreatureFx(cr, { clip: "atk:uptusk", u: 0.4 }, 1)).toEqual([]);
    const boss = creatureOf(drawOf("rift_shard_lord", true, "east"))!;
    expect(boss.boss).toBeDefined();
    expect(turnedCreatureFx(boss, { clip: "atk:@melee", u: 0.5, fxTurn: 1 }, 1)).toEqual([]);
  });
});
