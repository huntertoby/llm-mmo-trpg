// CW-1 冷卻井（docs/art/冷卻井-移植需求.md）：畫法登記、破壞的推算、演出時間表、地表動畫的接線。
import { describe, expect, it } from "vitest";
import type { BattleView, ObjectView, TileView } from "../api/types";
import { buildDrawModel, type DrawModel } from "../battle/drawModel";
import { objectStyle } from "../battle/glossary";
import { object, smallView, tile } from "../battle/testFixtures";
import { tileSections } from "../battle/tileInfo";
import { ASHEN_OBJECTS } from "./ashenObjects";
import { AIR_CHUNK_SCALE, WELL_BREAK_MS, WELL_FRAMES_MS, WELL_GEOM, WELL_MASK_R, WELL_PUDDLES, wellChunks, wellFrameAt, wellMaskRadius } from "./coolingWellArt";
import { OBJECT_DRAW } from "./objectArt";
import { SurfaceAnimator, type SurfaceHost } from "./surfaceAnimLayer";
import { brokenWells, spillSource } from "./wellBreak";

const W = 8;
const WELL: ObjectView = { id: "obj_0001", kind: "cooling_well", pos: { x: 3, y: 3 }, hp: 15, max_hp: 15, burning: null };

function model(surfaces: Record<string, string> = {}, objects: ObjectView[] = [], terrain = "stone"): DrawModel {
  const tiles: TileView[] = [];
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) tiles.push(tile(x, y, { terrain, surface: (surfaces[`${x},${y}`] ?? "none") as TileView["surface"] }));
  const view = {
    team: "ally", map_id: "t", map_name_zh: "t", width: W, height: W, tiles, objects, units: [], traps: [],
    turn_order: [], active_unit: null, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
  return buildDrawModel(view, "unit_0001");
}

const pool = (cx: number, cy: number): Record<string, string> => {
  const out: Record<string, string> = {};
  for (let y = cy - 1; y <= cy + 1; y++) for (let x = cx - 1; x <= cx + 1; x++) out[`${x},${y}`] = "water";
  return out;
};

describe("畫法登記與字", () => {
  it("灰燼荒原與預設都有冷卻井的畫法；字是「井」", () => {
    expect(ASHEN_OBJECTS.cooling_well).toBeTypeOf("function");
    expect(OBJECT_DRAW.cooling_well).toBeTypeOf("function");
    expect(objectStyle("cooling_well").glyph).toBe("井");
  });

  it("格子資訊卡：名稱、HP，說明放在規則前面（玩法 PM 定的字）", () => {
    const view = smallView({ objects: [object("o1", "cooling_well", 2, 0, { hp: 15, max_hp: 15 })] });
    const obj = tileSections(view, { x: 2, y: 0 }, {}).find((s) => s.kind === "object");
    expect(obj?.title).toBe("冷卻井・HP 15/15");
    expect(obj?.lines[0]).toBe("打破後井水漫出，周圍 3×3 變成水面。");
    expect(obj?.lines[1]).toBe("不可通行・可被破壞");
  });

  it("幾何：上緣 15.5 不高於殘牆壓頂石 15.6；最低點在耐久條 43.7 之上；受損小灘不貼格邊", () => {
    expect(WELL_GEOM.ty - WELL_GEOM.ry).toBeLessThanOrEqual(15.6);
    expect(WELL_GEOM.ty + WELL_GEOM.face + WELL_GEOM.ry).toBeLessThan(0.84 * 52);
    expect(WELL_PUDDLES[0] - 3.8).toBeGreaterThan(2);
    expect(WELL_PUDDLES[1] + 3.8).toBeLessThan(50);
  });

  it("碎塊確定性（同格同結果）；飛在空中的放大 1.3 倍、落地照原尺寸", () => {
    expect(wellChunks({ x: 3, y: 4 }, 1)).toEqual(wellChunks({ x: 3, y: 4 }, 1));
    expect(wellChunks({ x: 3, y: 4 }, 4)).not.toEqual(wellChunks({ x: 7, y: 4 }, 4));
    expect(wellChunks({ x: 3, y: 4 }, 1).every((c) => c.air)).toBe(true);
    expect(wellChunks({ x: 3, y: 4 }, 3).every((c) => !c.air && c.wet)).toBe(true);
    expect(AIR_CHUNK_SCALE).toBe(1.3);
  });
});

describe("時間表", () => {
  it("K0～K4 在 0／90／200／340／520 ms；遮罩半徑照表、格間內插、K4 不用遮罩", () => {
    expect(WELL_FRAMES_MS).toEqual([0, 90, 200, 340, 520]);
    expect([0, 89, 90, 199, 200, 339, 340, 519, 520].map(wellFrameAt)).toEqual([0, 0, 1, 1, 2, 2, 3, 3, 4]);
    expect(WELL_MASK_R.slice(0, 4).map((_, i) => wellMaskRadius(WELL_FRAMES_MS[i] as number))).toEqual([0, 30, 60, 92]);
    expect(wellMaskRadius(145)).toBe(45);
    expect(wellMaskRadius(WELL_BREAK_MS)).toBe(Infinity);
  });
});

describe("推算哪口井被打破、哪些水是它漏的", () => {
  it("前一次有、這一次沒有的井；水在 3×3 內才算；油、別處的水不算", () => {
    const prev = model({}, [WELL]);
    const next = model({ ...pool(3, 3), "6,6": "water", "4,2": "oil" });
    const wells = brokenWells(prev, next);
    expect(wells).toEqual([{ x: 3, y: 3 }]);
    expect(spillSource({ x: 2, y: 4, before: "none", after: "water", kind: "appear", delayMs: 0 }, wells)).toEqual({ x: 3, y: 3 });
    expect(spillSource({ x: 6, y: 6, before: "none", after: "water", kind: "appear", delayMs: 0 }, wells)).toBeNull();
    expect(spillSource({ x: 4, y: 2, before: "none", after: "oil", kind: "appear", delayMs: 0 }, wells)).toBeNull();
    expect(brokenWells(prev, model({}, [{ ...WELL, hp: 4 }]))).toEqual([]); // 受損但沒破
  });
});

describe("地表動畫的接線（SurfaceAnimator）", () => {
  const host: SurfaceHost = { ground: () => null as never, deco: () => null as never, place: () => undefined, oldTile: () => null };

  it("打破：9 格水照井的時間表（520 ms）播完；碎屑留著；同一格又有井（新的一場）時拿掉", () => {
    const a = new SurfaceAnimator();
    a.draw(model({}, [WELL]), host, 1);
    a.draw(model(pool(3, 3)), host, 1);
    expect(a.activeChanges()).toHaveLength(9);
    expect(a.wellStats()).toEqual({ breaking: 1, rubble: [{ x: 3, y: 3 }] });
    a.tick(300); // 一般的出現（260 ms）早就播完了，井的水還在長
    expect(a.activeChanges()).toHaveLength(9);
    a.tick(WELL_BREAK_MS - 300);
    expect(a.activeChanges()).toEqual([]);
    expect(a.wellStats().breaking).toBe(0);
    a.draw(model(pool(3, 3)), host, 1);
    expect(a.wellStats().rubble).toEqual([{ x: 3, y: 3 }]);
    a.draw(model({}, [WELL]), host, 1);
    expect(a.wellStats().rubble).toEqual([]);
  });

  it("「略過」：不播演出，碎屑直接留著", () => {
    const a = new SurfaceAnimator();
    a.draw(model({}, [WELL]), host, 1);
    a.draw(model(pool(3, 3)), host, null);
    expect(a.activeChanges()).toEqual([]);
    expect(a.wellStats()).toEqual({ breaking: 0, rubble: [{ x: 3, y: 3 }] });
  });

  it("換地圖時碎屑清掉", () => {
    const a = new SurfaceAnimator();
    a.draw(model({}, [WELL]), host, 1);
    a.draw(model(pool(3, 3)), host, 1);
    a.draw(model({}, [], "dirt"), host, 1);
    expect(a.wellStats()).toEqual({ breaking: 0, rubble: [] });
  });
});
