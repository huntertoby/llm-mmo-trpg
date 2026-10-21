import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "./geometry";
import {
  drawRows,
  easeOut,
  edgeMarks,
  heightAt,
  heightShifts,
  LIFT_MS,
  liftedCenter,
  liftedOrigin,
  liftHeightAt,
  maxHeight,
  occluded,
  pickTile,
  RAISE,
  stagePixels,
  tileLift,
  topReserve,
  type HeightGrid,
} from "./elevation";
import { cardPlacement, clientToTile, fitScale, scaledSize } from "./stageLayout";

const T = TILE_SIZE;

/** 高度表（每列一排，北在上）→ 地圖。 */
function grid(rows: number[][]): HeightGrid {
  return { width: rows[0]?.length ?? 0, height: rows.length, tiles: rows.flat().map((height) => ({ height })) };
}

describe("tileLift", () => {
  it("每階抬高 RAISE（6）模型像素，0 與負值不抬", () => {
    expect(RAISE).toBe(6);
    expect(tileLift(0)).toBe(0);
    expect(tileLift(1)).toBe(6);
    expect(tileLift(3)).toBe(18);
    expect(tileLift(-2)).toBe(0);
    expect(tileLift(1.5)).toBe(9); // 補間中的小數高度
  });

  it("頂面座標、畫布預留都由 tileLift 推出", () => {
    const g = grid([
      [0, 3],
      [1, 0],
    ]);
    expect(maxHeight(g)).toBe(3);
    expect(topReserve(g)).toBe(tileLift(3));
    expect(stagePixels(g)).toEqual({ width: 2 * T, height: 2 * T + 18 });
    expect(liftedOrigin({ x: 1, y: 0 }, 3)).toEqual({ x: T, y: -18 });
    expect(liftedCenter({ x: 0, y: 1 }, 1)).toEqual({ x: T / 2, y: T + T / 2 - 6 });
    expect(topReserve({ width: 3, height: 3 })).toBe(0); // 沒有高度資料：平地
    expect(heightAt(g, { x: 5, y: 0 })).toBe(0);
  });
});

describe("pickTile（世界座標）", () => {
  it("平地：就是格子座標", () => {
    const g = grid([
      [0, 0],
      [0, 0],
    ]);
    expect(pickTile(1, 1, g)).toEqual({ x: 0, y: 0 });
    expect(pickTile(T + 1, T + 1, g)).toEqual({ x: 1, y: 1 });
    expect(pickTile(T - 0.01, T - 0.01, g)).toEqual({ x: 0, y: 0 });
  });

  it("前排高格蓋住後排：點前排的頂面與崖面都選前排，後排露出的部分選後排", () => {
    // (0,1) 高 3：頂面 [T − 18, 2T − 18)，崖面 [2T − 18, 2T)
    const g = grid([[0], [3], [0]]);
    expect(pickTile(5, T - 10, g)).toEqual({ x: 0, y: 1 }); // 前排頂面蓋住後排下緣
    expect(pickTile(5, T - 19, g)).toEqual({ x: 0, y: 0 }); // 後排還看得到的部分
    expect(pickTile(5, 2 * T - 5, g)).toEqual({ x: 0, y: 1 }); // 前排崖面
    expect(pickTile(5, 2 * T + 1, g)).toEqual({ x: 0, y: 2 });
  });

  it("後排高格：頂面往上抬，點頂面選它", () => {
    const g = grid([[2], [0]]);
    expect(pickTile(5, -11, g)).toEqual({ x: 0, y: 0 }); // 抬到畫布預留區
    expect(pickTile(5, T - 1, g)).toEqual({ x: 0, y: 0 }); // 崖面
    expect(pickTile(5, T, g)).toEqual({ x: 0, y: 1 });
  });

  it("地圖邊緣：範圍外回傳 null", () => {
    const g = grid([
      [1, 0],
      [0, 0],
    ]);
    expect(pickTile(-1, 5, g)).toBeNull();
    expect(pickTile(2 * T, 5, g)).toBeNull();
    expect(pickTile(T + 5, -1, g)).toBeNull(); // (1,0) 沒抬高，上方是空的
    expect(pickTile(5, -6, g)).toEqual({ x: 0, y: 0 }); // (0,0) 抬高 6
    expect(pickTile(5, -6.5, g)).toBeNull();
    expect(pickTile(5, 2 * T, g)).toBeNull();
  });
});

describe("clientToTile（含預留與縮放）", () => {
  // 第 0 排 (1,0) 高 3 → 預留 18；第 2 排 (1,2) 高 2
  const g = grid([
    [0, 3, 0],
    [0, 0, 0],
    [0, 2, 0],
  ]);

  it("每一格頂面中心換算回同一格（各種縮放與位移）", () => {
    for (const scale of [0.5, 0.8, 1, 1.37, 2]) {
      const px = stagePixels(g);
      const rect = { left: 33.5, top: 71.25, width: px.width * scale, height: px.height * scale };
      for (let y = 0; y < 3; y += 1) {
        for (let x = 0; x < 3; x += 1) {
          const c = liftedCenter({ x, y }, heightAt(g, { x, y }));
          const cx = rect.left + c.x * scale;
          const cy = rect.top + (c.y + topReserve(g)) * scale;
          expect(clientToTile(cx, cy, rect, g)).toEqual({ x, y });
        }
      }
    }
  });

  it("縮放後：點前排高格的崖面選前排，點後排露出的頂面選後排", () => {
    const scale = 1.5;
    const px = stagePixels(g);
    const rect = { left: 0, top: 0, width: px.width * scale, height: px.height * scale };
    const reserve = topReserve(g);
    const at = (wx: number, wy: number) => clientToTile(wx * scale, (wy + reserve) * scale, rect, g);
    expect(at(T + 5, 3 * T - 4)).toEqual({ x: 1, y: 2 }); // (1,2) 的崖面
    expect(at(T + 5, 2 * T - 4)).toEqual({ x: 1, y: 2 }); // (1,2) 的頂面蓋住 (1,1) 的下緣
    expect(at(T + 5, 2 * T - 13)).toEqual({ x: 1, y: 1 });
    expect(at(T + 5, -17)).toEqual({ x: 1, y: 0 }); // 抬到預留區的頂面
    expect(at(5, -1)).toBeNull(); // 沒抬高的格子上方是空的
  });

  it("畫布大小、縮放都含上方預留", () => {
    expect(scaledSize(g, 1)).toEqual({ width: 3 * T, height: 3 * T + 18 });
    expect(fitScale({ width: 10000, height: 3 * T + 18 }, g, T, 0.1, 5)).toBeCloseTo(1);
  });

  it("浮動卡頂端對齊抬高後的頂面", () => {
    const top = cardPlacement({ x: 1, y: 0 }, g, 2);
    expect(top.top).toBe(Math.round((18 - 18) * 2)); // 預留 18 − 抬高 18
    const flat = cardPlacement({ x: 0, y: 0 }, g, 2);
    expect(flat.top).toBe(36);
  });
});

describe("drawRows 繪製順序", () => {
  it("由北到南一排一排，同排由西到東；空排也在", () => {
    const rows = drawRows(
      [
        { x: 2, y: 1, id: "c" },
        { x: 0, y: 2, id: "d" },
        { x: 1, y: 0, id: "a" },
        { x: 0, y: 1, id: "b" },
      ],
      4,
    );
    expect(rows.map((r) => r.y)).toEqual([0, 1, 2, 3]);
    expect(rows.flatMap((r) => r.items.map((i) => i.id))).toEqual(["a", "b", "c", "d"]);
    expect(rows[3]?.items).toEqual([]);
  });
});

describe("遮擋判定與描邊", () => {
  const g = grid([
    [0, 1, 2],
    [2, 1, 1],
    [0, 0, 0],
  ]);

  it("南鄰比自己高才算被擋；同高、較低、地圖底邊都不算", () => {
    expect(occluded(g, { x: 0, y: 0 })).toBe(true);
    expect(occluded(g, { x: 1, y: 0 })).toBe(false);
    expect(occluded(g, { x: 2, y: 0 })).toBe(false);
    expect(occluded(g, { x: 0, y: 2 })).toBe(false);
  });

  it("較低的鄰邊才描線，地圖外不畫", () => {
    expect(edgeMarks(g, { x: 0, y: 1 })).toEqual({ east: true, west: false, north: true, south: true });
    expect(edgeMarks(g, { x: 2, y: 0 })).toEqual({ east: false, west: true, north: false, south: true });
    expect(edgeMarks(g, { x: 1, y: 2 })).toEqual({ east: false, west: false, north: false, south: false });
  });
});

describe("升降補間", () => {
  it("ease-out：開始快、結束慢，夾在 0–1", () => {
    expect(easeOut(0)).toBe(0);
    expect(easeOut(1)).toBe(1);
    expect(easeOut(2)).toBe(1);
    expect(easeOut(0.5)).toBeGreaterThan(0.5);
    expect(easeOut(0.25) - easeOut(0)).toBeGreaterThan(easeOut(1) - easeOut(0.75));
  });

  it("從舊高度補到新高度；時間到或 0 秒直接是結果", () => {
    expect(liftHeightAt(0, 2, 0, LIFT_MS)).toBe(0);
    expect(liftHeightAt(0, 2, LIFT_MS, LIFT_MS)).toBe(2);
    const mid = liftHeightAt(0, 2, LIFT_MS / 2, LIFT_MS);
    expect(mid).toBeGreaterThan(1);
    expect(mid).toBeLessThan(2);
    expect(liftHeightAt(3, 1, LIFT_MS / 2, LIFT_MS)).toBeLessThan(2); // 下降也一樣
    expect(liftHeightAt(0, 2, 10, 0)).toBe(2); // 略過
  });

  it("heightShifts：只取高度真的改變的格子，同格多次合併", () => {
    const events = [
      { type: "terrain_changed", pos: { x: 1, y: 2 }, height_before: 0, height_after: 1 },
      { type: "terrain_changed", pos: { x: 3, y: 3 }, height_before: 1, height_after: 1 },
      { type: "damage_dealt", pos: { x: 1, y: 2 } },
      { type: "terrain_changed", pos: { x: 1, y: 2 }, height_before: 1, height_after: 2 },
      { type: "terrain_changed", pos: { x: 0, y: 0 }, height_before: 2, height_after: 1 },
      { type: "terrain_changed", pos: { x: 0, y: 0 }, height_before: 1, height_after: 2 },
    ];
    expect(heightShifts(events)).toEqual([{ pos: { x: 1, y: 2 }, from: 0, to: 2 }]);
  });
});
