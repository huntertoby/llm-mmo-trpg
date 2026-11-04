// 6V-2b（docs/art/6V-2檢查.md 第 2 節）：致命角標只畫在外圍；灰渡口的深淵畫成深水（`look.chasm_style`）；
// 水面岸邊羽化、荒原水色提亮；雲嶺的 lava（地熱泉）沒有漂移層。只換外觀，致命判定與規則不在這裡。
import { describe, expect, it } from "vitest";
import type { DrawModel, TileDraw } from "../battle/drawModel";
import { lethalCornerMask, lethalCornersOf, type CornerMask } from "./lethalMarks";

/** 由字元圖建畫面資料：`#` 致命、`.` 安全、空白 ＝ 沒有格子。 */
function modelOf(rows: readonly string[]): DrawModel {
  const tiles: TileDraw[] = [];
  rows.forEach((row, y) =>
    [...row].forEach((c, x) => {
      if (c === " ") return;
      const deadly = c === "#";
      tiles.push({ x, y, height: 0, fill: 0, heightLabel: "0", terrain: deadly ? "chasm" : "stone", surface: "none", terrainName: "", surfaceName: null, blocked: deadly, deadly, wall: false });
    }),
  );
  return { width: rows[0]?.length ?? 0, height: rows.length, tiles, objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [], region: "", look: "" };
}

const ALL: CornerMask = [true, true, true, true];
const NONE: CornerMask = [false, false, false, false];
/** 畫出的角數（整張圖）。 */
const cornerCount = (m: DrawModel): number => m.tiles.filter((t) => t.deadly).reduce((n, t) => n + lethalCornersOf(m, t).filter(Boolean).length, 0);

describe("致命角標只畫在外圍", () => {
  it("單格：四角都畫", () => {
    const m = modelOf(["...", ".#.", "..."]);
    expect(lethalCornersOf(m, { x: 1, y: 1 })).toEqual(ALL);
  });

  it("一列（吊橋、渡橋）：每格四角都畫", () => {
    const m = modelOf([".....", ".###.", "....."]);
    for (let x = 1; x <= 3; x++) expect(lethalCornersOf(m, { x, y: 1 })).toEqual(ALL);
  });

  it("大片 5×5：內部 3×3 不畫，只剩外圈；不會拼成紅十字網格", () => {
    const m = modelOf([".......", ".#####.", ".#####.", ".#####.", ".#####.", ".#####.", "......."]);
    for (let y = 2; y <= 4; y++) for (let x = 2; x <= 4; x++) expect(lethalCornersOf(m, { x, y })).toEqual(NONE);
    expect(lethalCornersOf(m, { x: 1, y: 1 })).toEqual([true, true, false, true]); // 左上角那格：右下角在內部
    expect(lethalCornersOf(m, { x: 3, y: 1 })).toEqual([true, true, false, false]); // 上緣中間：只畫上面兩角
    // 外圈 16 格；原本 25 格 × 4 角 ＝ 100 個，現在 4 個角格各 3 個、12 個邊格各 2 個 ＝ 36
    expect(cornerCount(m)).toBe(36);
  });

  it("L 形：內轉角（凹角）那一格的斜鄰是安全格，要畫", () => {
    const m = modelOf(["....", ".##.", ".#..", "...."]);
    // (1,1) 的右下角共用 (2,1)#、(1,2)#、(2,2). → 斜鄰安全 → 畫
    expect(lethalCornersOf(m, { x: 1, y: 1 })).toEqual(ALL);
    expect(lethalCornersOf(m, { x: 2, y: 1 })).toEqual(ALL);
    expect(lethalCornersOf(m, { x: 1, y: 2 })).toEqual(ALL);
    const big = modelOf(["......", ".####.", ".####.", ".##...", ".##...", "......"]);
    expect(lethalCornersOf(big, { x: 2, y: 2 })).toEqual([false, false, true, false]); // 凹角：只畫右下
    expect(lethalCornersOf(big, { x: 2, y: 1 })).toEqual([true, true, false, false]);
  });

  it("孔洞：大片中間一格安全格，四周的角都描出來", () => {
    const m = modelOf([".......", ".#####.", ".#####.", ".##.##.", ".#####.", ".#####.", "......."]);
    expect(lethalCornersOf(m, { x: 2, y: 2 })).toEqual([false, false, true, false]);
    expect(lethalCornersOf(m, { x: 3, y: 2 })).toEqual([false, false, true, true]);
    expect(lethalCornersOf(m, { x: 4, y: 4 })).toEqual([true, false, false, false]);
    expect(lethalCornersOf(m, { x: 2, y: 3 })).toEqual([false, true, true, false]);
    expect(lethalCornersOf(m, { x: 2, y: 1 })).toEqual([true, true, false, false]); // 離孔洞兩格：照外圈
  });

  it("地圖外不算非致命格：貼著地圖邊的那一側不畫", () => {
    const m = modelOf(["###", "###", "..."]);
    expect(lethalCornersOf(m, { x: 0, y: 0 })).toEqual(NONE);
    expect(lethalCornersOf(m, { x: 0, y: 1 })).toEqual([false, false, true, true]);
    expect(lethalCornerMask(() => false, 5, 5)).toEqual(NONE);
    expect(lethalCornerMask(() => true, 5, 5)).toEqual(ALL);
  });
});
