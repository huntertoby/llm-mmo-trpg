// CR-1c（美術 CR-1b 驗收小修 2）：預覽牌放在上方或下方、水平置中時，像浮動卡一樣往內推，整塊留在地圖可見範圍內。
import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { visibleFieldBounds } from "./floatStack";
import { placeTags, pushInside, TAG_HEIGHT } from "./pathArt";
import { readFile, SRC_DIR } from "../test/sourceScan";

const T = TILE_SIZE;
const H = TAG_HEIGHT;
const W = 170;
const at = (x: number, y: number) => ({ x: x * T, y: y * T });
const bounds = visibleFieldBounds(8 * T, 6 * T, 40, { x: 0, y: 0 }, { x: 0, y: 0 }); // 8×6 的地圖，上面預留 40

describe("pushInside", () => {
  it("超出左緣往右推、超出右緣往左推、上下同理；範圍內不動", () => {
    expect(pushInside({ x: -30, y: 10 }, W, H, bounds)).toEqual({ x: 0, y: 10 });
    expect(pushInside({ x: 8 * T - 50, y: 10 }, W, H, bounds)).toEqual({ x: 8 * T - W, y: 10 });
    expect(pushInside({ x: 10, y: 6 * T - 5 }, W, H, bounds)).toEqual({ x: 10, y: 6 * T - H });
    expect(pushInside({ x: 10, y: -100 }, W, H, bounds)).toEqual({ x: 10, y: -40 });
    expect(pushInside({ x: 10, y: 10 }, W, H, bounds)).toEqual({ x: 10, y: 10 });
  });

  it("沒給範圍時照原位", () => {
    expect(pushInside({ x: -30, y: 10 }, W, H)).toEqual({ x: -30, y: 10 });
  });
});

describe("placeTags 置中的位置留在地圖內", () => {
  const inside = (p: { x: number; y: number }) =>
    p.x >= bounds.left && p.x + W <= bounds.right && p.y >= bounds.top && p.y + H <= bounds.bottom;

  it("靠左邊界：停點在第 0 欄，右邊有人 → 上方置中，往右推到左緣以內", () => {
    const stop = at(0, 3);
    const units = [at(2, 3), at(3, 3)];
    const [p] = placeTags([{ o: stop, w: W }], [], H, units, bounds);
    expect(p).toEqual({ x: 0, y: stop.y - T * 0.45 - H });
    expect(inside(p!)).toBe(true);
    // 沒給範圍時（改前）會超出左緣
    const [old] = placeTags([{ o: stop, w: W }], [], H, units);
    expect(old!.x).toBeLessThan(0);
  });

  it("靠左邊界、改擺下方（霜行那一幕的情況）：往右推", () => {
    const stop = at(0, 3);
    const units = [at(1, 3), at(0, 2), at(2, 3), at(1, 2)]; // 右邊、上方有人；左邊的位置也蓋到頭上那一格的人 → 下方
    const [p] = placeTags([{ o: stop, w: W }], [], H, units, bounds);
    expect(p).toEqual({ x: 0, y: stop.y + T - 4 });
    expect(inside(p!)).toBe(true);
  });

  it("靠右邊界：停點在最右欄 → 置中的位置往左推到右緣以內", () => {
    const stop = at(7, 3);
    const lone = [at(0, 0)]; // 停點附近沒人：右邊（原位）出界不選 → 上方置中、往左推
    const [first] = placeTags([{ o: stop, w: W }], [], H, lone, bounds);
    expect(first).toEqual({ x: 8 * T - W, y: stop.y - T * 0.45 - H });
    expect(inside(first!)).toBe(true);
    const crowded = [at(7, 2), at(6, 2), at(5, 3), at(6, 3), at(4, 3)]; // 右邊原位、上方、左邊都蓋到人 → 下方
    const [p] = placeTags([{ o: stop, w: W }], [], H, crowded, bounds);
    expect(p).toEqual({ x: 8 * T - W, y: stop.y + T - 4 });
    expect(inside(p!)).toBe(true);
  });

  it("左右兩邊的位置出界時不選（實機：主角在第 0 欄往下走一格，左邊那個位置會被地圖左緣切掉）", () => {
    const stop = at(0, 6);
    const units = [at(0, 3), at(1, 5)]; // 主角原位、隊友；右邊與上方都會蓋到隊友
    const [p] = placeTags([{ o: stop, w: W }], [], H, units, bounds);
    expect(inside(p!)).toBe(true);
    const [old] = placeTags([{ o: stop, w: W }], [], H, units);
    expect(old).toEqual({ x: stop.x + T / 2 - W, y: stop.y - H + 4 }); // 沒給範圍（改前）：左邊，出界
  });

  it("沒有單位時：靠右邊界的右上、右下出界 → 改左邊", () => {
    const stop = at(7, 3);
    const [p] = placeTags([{ o: stop, w: W }], [], H, [], bounds);
    expect(p).toEqual({ x: stop.x + T / 2 - W, y: stop.y - H + 4 });
  });

  it("全部的位置都出界時照舊（右上）", () => {
    const tiny = visibleFieldBounds(T, T, 0, { x: 0, y: 0 }, { x: 0, y: 0 });
    const [p] = placeTags([{ o: at(0, 0), w: W }], [], H, [], tiny);
    expect(p).toEqual({ x: T / 2, y: -H + 4 });
  });

  it("接線：HighlightLayer 把地圖可見範圍傳給 placeTags", () => {
    const src = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    expect(src).toMatch(/p\.units,\s*\/\/[^\n]*\n\s*visibleFieldBounds\(/);
  });
});
