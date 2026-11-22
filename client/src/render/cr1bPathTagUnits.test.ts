// CR-1b（美術 E3b 驗收小修 1，併進佇列 (w)）：走路預覽的預覽牌不要蓋住單位。
import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { placeTags, TAG_HEIGHT, unitBox } from "./pathArt";
import { readFile, SRC_DIR } from "../test/sourceScan";

const T = TILE_SIZE;
const H = TAG_HEIGHT;
const W = 170; // 「沿路留下冰 3 格（1 回合後消失）」約這麼寬
const at = (x: number, y: number) => ({ x: x * T, y: y * T });
const box = (p: { x: number; y: number }, w: number) => ({ x: p.x, y: p.y, w, h: H });
const hit = (a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

describe("placeTags 避開單位", () => {
  const stop = at(3, 3);

  it("沒有單位時和改前一樣（停點右上）", () => {
    expect(placeTags([{ o: stop, w: W }])).toEqual([{ x: stop.x + T / 2, y: stop.y - H + 4 }]);
    expect(placeTags([{ o: stop, w: W }], [], H, [])).toEqual([{ x: stop.x + T / 2, y: stop.y - H + 4 }]);
  });

  it("右邊沒有單位時位置不變", () => {
    const units = [at(0, 6)];
    expect(placeTags([{ o: stop, w: W }], [], H, units)).toEqual([{ x: stop.x + T / 2, y: stop.y - H + 4 }]);
  });

  it("霜行那一幕：停點右邊同一排有兩個敵人 → 改擺上方，不蓋到任何單位", () => {
    const units = [at(5, 3), at(6, 3)];
    const [p] = placeTags([{ o: stop, w: W }], [], H, units);
    expect(p).toEqual({ x: stop.x + T / 2 - W / 2, y: stop.y - T * 0.45 - H });
    for (const u of units) expect(hit(box(p!, W), unitBox(u))).toBe(false);
  });

  it("右邊、上方都有人 → 左邊", () => {
    const units = [at(5, 3), at(5, 2)];
    const [p] = placeTags([{ o: stop, w: W }], [], H, units);
    expect(p).toEqual({ x: stop.x + T / 2 - W, y: stop.y - H + 4 });
  });

  it("右、上、左都有人 → 下方", () => {
    const units = [at(5, 3), at(3, 2), at(4, 2), at(1, 3), at(0, 3), at(2, 2)];
    const [p] = placeTags([{ o: stop, w: W }], [], H, units);
    expect(p).toEqual({ x: stop.x + T / 2 - W / 2, y: stop.y + T - 4 });
  });

  it("四邊都會蓋到 → 選蓋到最少的那一邊", () => {
    // 右邊兩個、上方一個（頭上那一格）、左邊兩個、下方兩個
    const units = [at(5, 3), at(6, 3), at(3, 2), at(1, 3), at(0, 3), at(2, 4), at(4, 4)];
    const [p] = placeTags([{ o: stop, w: W }], [], H, units);
    const area = (q: { x: number; y: number }) =>
      units.reduce((s, u) => {
        const b = unitBox(u);
        const w = Math.min(q.x + W, b.x + b.w) - Math.max(q.x, b.x);
        const h = Math.min(q.y + H, b.y + b.h) - Math.max(q.y, b.y);
        return s + (w > 0 && h > 0 ? w * h : 0);
      }, 0);
    const tries = [
      { x: stop.x + T / 2, y: stop.y - H + 4 },
      { x: stop.x + T / 2 - W / 2, y: stop.y - T * 0.45 - H },
      { x: stop.x + T / 2 - W, y: stop.y - H + 4 },
      { x: stop.x + T / 2 - W / 2, y: stop.y + T - 4 },
    ];
    expect(tries.every((q) => area(q) > 0)).toBe(true);
    expect(area(p!)).toBe(Math.min(...tries.map(area)));
  });

  it("高亮層把有單位的格子（巨型單位每一格）交給 placeTags", () => {
    const layer = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    expect(layer).toContain("isGiantDraw(u) ? (u.tiles ?? []) : [{ x: u.x, y: u.y }]");
    expect(layer).toMatch(/TAG_HEIGHT \* k,\s*p\.units,/);
  });
});
