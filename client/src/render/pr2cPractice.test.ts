// PR-2c：靶場木樁與場景畫法（docs/phases/PhasePR-2計畫.md「行為一致測試」C 組）。
// C1 單位畫法的選擇；C2 水池與滑軌只在測試模式、實戰的 DrawModel 不變；C3 木樁閃白 0.1 秒、減少動態時一格。
// 地圖讀實際的 content/maps/training_range.yaml 與 content/world/newcomer.yaml（地圖不改，PR-2 第 9 點）。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync } from "node:fs";
import { parse } from "yaml";
import type { BattleView, Pos, TileView } from "../api/types";
import { buildDrawModel, type DrawModel, type UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "./artTextures";
import { FACING_ARROW_LABEL, HP_BAR_LABEL, SOUTH_ARROW_LABEL } from "./minMark";
import { PRACTICE_SCENES, poolGeometry, practiceSceneOf, railGeometry, slabWidth, type Rect } from "./practiceRange";
import { dummyFlashEffect, reactEffects, type ReactHost } from "./reactEffects";
import { reduceEffects } from "./reducedMotion";
import { FLASH_LABEL } from "./silhouetteFlash";
import { DUMMY_FLASH_ALPHA, DUMMY_FLASH_MS, dummyFlashAlpha, dummyFlashMs, isTrainingDummy } from "./trainingDummy";
import { BODY_LABEL, bodyTexture, buildUnitSprite, flashTexture, hasSkeleton, overlayFlashKind, Pulses } from "./unitSprite";

const T = TILE_SIZE;
const readText = readFileSync as (url: URL, enc: string) => string;
const CONTENT = new URL("../../../content/", import.meta.url);
const yamlOf = (path: string) => parse(readText(new URL(path, CONTENT), "utf-8")) as Record<string, unknown>;

interface MapYaml {
  size: [number, number];
  terrain: string;
  legend: Record<string, string>;
  surfaces: Array<{ at: [number, number]; surface: string }>;
}
const MAP = yamlOf("maps/training_range.yaml") as unknown as MapYaml;
const RANGE = (yamlOf("world/newcomer.yaml") as { range: { map: string; hero_at: [number, number]; dummies: Array<{ unit: string; at: [number, number] }> } }).range;
const [W, H] = MAP.size;

/** 照 training_range.yaml 組的戰場：主角＋newcomer.yaml 的三個木樁。 */
function rangeView(practice: boolean, over: Partial<BattleView> = {}): BattleView {
  const rows = MAP.terrain.trim().split("\n").map((r) => r.trim());
  const tiles: TileView[] = [];
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const surf = MAP.surfaces.find((s) => s.at[0] === x && s.at[1] === y)?.surface ?? "none";
      tiles.push(tile(x, y, { terrain: MAP.legend[rows[y]![x]!] ?? "stone", surface: surf as TileView["surface"] }));
    }
  }
  const dummies = RANGE.dummies.map((d, i) => unit(`unit_000${i + 2}`, "enemy", d.at[0], d.at[1], { template_id: d.unit, hp: 300, max_hp: 300, facing: "west" }));
  return {
    team: "ally",
    map_id: RANGE.map,
    map_name_zh: "靶場",
    width: W,
    height: H,
    tiles,
    objects: [],
    units: [unit("unit_0001", "ally", RANGE.hero_at[0], RANGE.hero_at[1], { template_id: "hero_fighter" }), ...dummies],
    traps: [],
    turn_order: ["unit_0001"],
    active_unit: "unit_0001",
    round: 1,
    max_rounds: practice ? null : 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
    summon_command_ap_cost: 1,
    summon_infuse_ap_cost: 1,
    practice,
    ...over,
  } as BattleView;
}

const fakeArt = (asked: string[] = []): ArtTextures =>
  ({
    dollFx: (key: string) => (asked.push(key), Texture.WHITE),
    figure: () => (asked.push("figure"), Texture.WHITE),
    figureFlash: () => (asked.push("figureFlash"), Texture.WHITE),
    uniqueOwner: (s: string) => s,
    holdFor: () => undefined,
  }) as unknown as ArtTextures;

const dummyDraw = (model: DrawModel): UnitDraw => model.units.find((u) => u.template === "training_dummy")!;

describe("PR-2c C1：木樁的畫法選擇", () => {
  const model = buildDrawModel(rangeView(true), "unit_0001");

  it("兩種木樁範本 → 木樁畫法（沒有骨架、受擊疊白色剪影）、沒有血條；其他範本照舊", () => {
    for (const tpl of ["training_dummy", "training_dummy_moving"]) {
      const u = model.units.find((x) => x.template === tpl)!;
      expect(isTrainingDummy(u)).toBe(true);
      expect(u.noBar).toBe(true);
      expect(hasSkeleton(u)).toBe(false);
      expect(overlayFlashKind(u)).toBe("dummy");
    }
    const hero = model.units.find((x) => x.template === "hero_fighter")!;
    expect(isTrainingDummy(hero)).toBe(false);
    expect("noBar" in hero).toBe(false);
    expect(hasSkeleton(hero)).toBe(true);
    expect(overlayFlashKind(hero)).toBeNull();
  });

  it("木樁的節點：只有木樁本身（BODY），沒有陣營圈、朝向三角形、血條", () => {
    const asked: string[] = [];
    const c = buildUnitSprite(fakeArt(asked), new Pulses(), dummyDraw(model));
    const labels = c.children.map((n) => n.label);
    expect(labels).toContain(BODY_LABEL);
    for (const l of [HP_BAR_LABEL, FACING_ARROW_LABEL, SOUTH_ARROW_LABEL]) expect(labels).not.toContain(l);
    expect(c.children.filter((n) => !(n instanceof Sprite))).toHaveLength(0); // 沒有底圈（Graphics）
    expect(asked).toEqual(["training-dummy|v1"]);
    expect(asked).not.toContain("figure");
  });

  it("走路、待機的貼圖也是木樁；白閃用不含影子的白色剪影", () => {
    const asked: string[] = [];
    const art = fakeArt(asked);
    bodyTexture(art, dummyDraw(model), { pose: null });
    flashTexture(art, dummyDraw(model));
    expect(asked).toEqual(["training-dummy|v1", "training-dummy-flash|v1"]);
  });

  it("技能工坊（3F，不帶測試模式）的木樁也換（PR-2 第 8 點）", () => {
    const real = buildDrawModel(rangeView(false), "unit_0001");
    expect(dummyDraw(real).noBar).toBe(true);
    expect(overlayFlashKind(dummyDraw(real))).toBe("dummy");
  });
});

describe("PR-2c C2：滑軌與方角水池只在測試模式", () => {
  it("practice=false 的 DrawModel 沒有 practice 鍵，其餘和測試模式那份逐欄相同（地形、單位、物件都不受旗標影響）", () => {
    const real = buildDrawModel(rangeView(false), "unit_0001");
    const prac = buildDrawModel(rangeView(true), "unit_0001");
    expect("practice" in real).toBe(false);
    const { practice, ...rest } = prac;
    expect(practice).toEqual(PRACTICE_SCENES.training_range);
    expect(JSON.stringify(rest)).toBe(JSON.stringify(real));
  });

  it("實戰的單位畫法不變：不是木樁的單位沒有 noBar 鍵（和改前同一組欄位）", () => {
    const v = rangeView(false, { units: [unit("unit_0001", "ally", 2, 5, { template_id: "hero_fighter" }), unit("unit_0002", "enemy", 6, 4, { template_id: "bandit_brute" })] });
    for (const u of buildDrawModel(v, "unit_0001").units) expect("noBar" in u).toBe(false);
  });

  it("沒列在表上的地圖：測試模式也沒有滑軌、水池", () => {
    expect(practiceSceneOf("open_plain")).toEqual({ rails: [], pool: [] });
    expect(buildDrawModel(rangeView(true, { map_id: "open_plain" }), "unit_0001").practice).toEqual({ rails: [], pool: [] });
  });

  it("表和 content 一致：水池＝training_range.yaml 的水面、滑軌在會動的木樁那一排且包含它、在地圖內、不壓牆", () => {
    const scene = PRACTICE_SCENES[RANGE.map]!;
    const water = MAP.surfaces.filter((s) => s.surface === "water").map((s) => `${s.at[0]},${s.at[1]}`).sort();
    expect(scene.pool.map((p) => `${p.x},${p.y}`).sort()).toEqual(water);
    const mover = RANGE.dummies.find((d) => d.unit === "training_dummy_moving")!;
    expect(scene.rails).toHaveLength(1);
    const rail = scene.rails[0]!;
    expect(rail.y).toBe(mover.at[1]);
    expect(rail.x0).toBeLessThanOrEqual(mover.at[0]);
    expect(rail.x1).toBeGreaterThanOrEqual(mover.at[0]);
    expect(rail.x1 - rail.x0 + 1).toBe(5); // 樣張滑軌 5 格
    expect(rail.x0).toBeGreaterThanOrEqual(0);
    expect(rail.x1).toBeLessThan(W);
    const row = MAP.terrain.trim().split("\n")[rail.y]!.trim();
    for (let x = rail.x0; x <= rail.x1; x++) expect(MAP.legend[row[x]!]).toBe("stone");
  });
});

describe("PR-2c：水池幾何（方角、填滿到石緣、L 形內角方角）", () => {
  const pool = PRACTICE_SCENES.training_range!.pool;
  const all = () => true;
  const g = poolGeometry(pool, all, W, H, T);
  const o = slabWidth(T);
  const inside = (r: Rect) => r.x0 >= 0 && r.y0 >= 0 && r.x1 <= W * T && r.y1 <= H * T;

  it("每一格一塊方角水面：填滿整格（相鄰水面多蓋 1，不透出格縫）；貼地圖下緣的那一邊停在石條內緣", () => {
    expect(g.water.map((w) => w.tile)).toEqual([{ x: 6, y: 8 }, { x: 7, y: 8 }, { x: 6, y: 9 }]);
    const at = (x: number, y: number) => g.water.find((w) => w.tile.x === x && w.tile.y === y)!.rect;
    expect(at(6, 8)).toEqual({ x0: 6 * T, y0: 8 * T, x1: 7 * T + 1, y1: 9 * T + 1 });
    expect(at(7, 8)).toEqual({ x0: 7 * T - 1, y0: 8 * T, x1: 8 * T, y1: 9 * T });
    expect(at(6, 9)).toEqual({ x0: 6 * T, y0: 9 * T - 1, x1: 7 * T, y1: 10 * T - o });
  });

  it("石條：池外一圈（外角往外多伸一個石條寬）、池內格子之間沒有石條、地圖外不畫", () => {
    const sides = g.slabs.map((s) => `${s.tile.x},${s.tile.y}${s.side}`).sort();
    expect(sides).toEqual(["6,8n", "6,8w", "6,9e", "6,9s", "6,9w", "7,8e", "7,8n", "7,8s"]);
    for (const s of g.slabs) expect(inside(s.rect), `${s.tile.x},${s.tile.y}${s.side}`).toBe(true);
    const slab = (x: number, y: number, side: string) => g.slabs.find((s) => s.tile.x === x && s.tile.y === y && s.side === side)!;
    // 外角：北邊石條往西（6,8）、往東（7,8）各多伸一個石條寬；北邊受光
    expect(slab(6, 8, "n").rect).toEqual({ x0: 6 * T - o, x1: 7 * T, y0: 8 * T - o, y1: 8 * T });
    expect(slab(7, 8, "n").rect).toEqual({ x0: 7 * T, x1: 8 * T + o, y0: 8 * T - o, y1: 8 * T });
    expect(slab(6, 8, "n").light).toBe(true);
    expect(slab(6, 8, "n").row).toBe(7); // 石條壓在北邊那一排的格子上
    // L 形內角：(7,8) 南邊石條與 (6,9) 東邊石條在 (7T, 9T) 方角相接，都不往內角伸
    expect(slab(7, 8, "s").rect).toEqual({ x0: 7 * T, x1: 8 * T + o, y0: 9 * T, y1: 9 * T + o });
    expect(slab(6, 9, "e").rect).toEqual({ x0: 7 * T, x1: 7 * T + o, y0: 9 * T, y1: 10 * T });
    // 地圖下緣：石條在水面裡面
    expect(slab(6, 9, "s").rect).toEqual({ x0: 6 * T - o, x1: 7 * T + o, y0: 10 * T - o, y1: 10 * T });
    expect(slab(6, 9, "s").row).toBe(9);
  });

  it("石條把水面圍起來：水面的每一條外緣都貼著一條石條（沒有露出地磚）", () => {
    for (const w of g.water) {
      const touch = (x: number, y: number) => g.slabs.some((s) => x >= s.rect.x0 && x <= s.rect.x1 && y >= s.rect.y0 && y <= s.rect.y1) || g.water.some((v) => v !== w && x >= v.rect.x0 && x <= v.rect.x1 && y >= v.rect.y0 && y <= v.rect.y1);
      const { x0, y0, x1, y1 } = w.rect;
      for (const [x, y] of [[x0, y0], [x1, y0], [x0, y1], [x1, y1], [(x0 + x1) / 2, y0], [(x0 + x1) / 2, y1], [x0, (y0 + y1) / 2], [x1, (y0 + y1) / 2]] as const) {
        expect(touch(x, y), `${w.tile.x},${w.tile.y} @ ${x},${y}`).toBe(true);
      }
    }
  });

  it("結冰或蒸發的格子不畫水面，石條照舊圍著整個水池", () => {
    const frozen = poolGeometry(pool, (p: Pos) => !(p.x === 6 && p.y === 8), W, H, T);
    expect(frozen.water.map((w) => `${w.tile.x},${w.tile.y}`)).toEqual(["7,8", "6,9"]);
    expect(frozen.water.find((w) => w.tile.x === 7)!.rect.x0).toBe(7 * T); // 隔壁不是水，不多蓋
    expect(frozen.slabs).toEqual(g.slabs);
  });

  it("滑軌：第 3 排、兩條鐵軌在格子 0.62 高度上下、枕木只比鐵軌寬一點、不出地圖", () => {
    const r = railGeometry(PRACTICE_SCENES.training_range!.rails[0]!, T);
    expect(r.row).toBe(3);
    expect(r.y).toBeCloseTo(3.62 * T);
    expect(r.rails[1] - r.rails[0]).toBeCloseTo((12 * T) / 52);
    expect(r.x0).toBeGreaterThan(7 * T);
    expect(r.x1).toBeLessThan(W * T);
    expect(r.ties.length).toBeGreaterThan(8);
    for (const t of r.ties) {
      expect(t.y0).toBeLessThan(r.rails[0]);
      expect(r.rails[0] - t.y0).toBeCloseTo((2.5 * T) / 52); // 枕木上下各比鐵軌多 2.5（樣張第 2 版）
      expect(t.x0).toBeGreaterThanOrEqual(r.x0);
      expect(t.x1).toBeLessThanOrEqual(r.x1);
    }
  });
});

describe("PR-2c C3：木樁閃白", () => {
  const model = buildDrawModel(rangeView(true), "unit_0001");
  const d = dummyDraw(model);
  function host(): { host: ReactHost; sprite: Container; body: Sprite } {
    const sprite = new Container();
    const body = new Sprite(Texture.EMPTY);
    body.label = BODY_LABEL;
    sprite.addChild(body);
    const h = {
      art: fakeArt(),
      sprite: () => sprite,
      draw: () => d,
      hold: () => undefined,
      release: () => undefined,
      setTexture: () => undefined,
      restBody: () => undefined,
    } as unknown as ReactHost;
    return { host: h, sprite, body };
  }
  const flashOf = (s: Container) => s.children.find((n) => n.label === FLASH_LABEL) as Sprite | undefined;

  it("受擊產生一個 0.1 秒的白閃（照播放速度縮放）；不動、不換姿勢", () => {
    expect(DUMMY_FLASH_MS).toBe(100);
    expect(dummyFlashMs(1)).toBe(100);
    expect(dummyFlashMs(10)).toBe(1000);
    const { host: h, sprite } = host();
    const fx = reactEffects(h, { unitId: d.id, kind: "hit", atMs: 0 } as never, 500, 1);
    expect(fx).toHaveLength(1);
    expect(fx[0]!.endMs - fx[0]!.startMs).toBe(100);
    fx[0]!.update(0);
    expect(flashOf(sprite)?.alpha).toBeCloseTo(DUMMY_FLASH_ALPHA);
    fx[0]!.update(0.9);
    expect(flashOf(sprite)?.alpha).toBeCloseTo(DUMMY_FLASH_ALPHA);
    fx[0]!.end?.();
    expect(flashOf(sprite)).toBeUndefined();
    expect(reactEffects(h, { unitId: d.id, kind: "heavy", atMs: 0 } as never, 0, 1)).toHaveLength(1);
    expect(reactEffects(h, { unitId: d.id, kind: "dodge", atMs: 0 } as never, 0, 1)).toHaveLength(0);
  });

  it("減少動態：同一張白閃停一格（第一次更新就是最後一格、不淡出），結束時拿掉", () => {
    const { host: h, sprite } = host();
    const [fx] = reduceEffects([dummyFlashEffect(h, d.id, 0, 1)], true);
    fx!.update(0);
    expect(flashOf(sprite)?.alpha).toBeCloseTo(DUMMY_FLASH_ALPHA);
    fx!.update(0.5);
    expect(flashOf(sprite)?.alpha).toBeCloseTo(DUMMY_FLASH_ALPHA);
    fx!.end?.();
    expect(flashOf(sprite)).toBeUndefined();
    expect(dummyFlashAlpha(1)).toBe(DUMMY_FLASH_ALPHA);
    expect(dummyFlashAlpha(1.01)).toBe(0);
  });
});
