// CB-3b：戰場畫布上緣留半格、右緣留四分之一格（`docs/art/CB-3檢查.md` 追蹤 1）。
// 留邊只是空白：格子的座標換算、點擊命中、浮動卡與 HUD 避讓的對位都不能變；實地地圖與開發頁預設不留。
import { describe, expect, it } from "vitest";
import { BATTLE_DRAW, buildDrawModel } from "./drawModel";
import { STAGE_MARGIN, stagePixels, topReserve, type HeightGrid } from "./elevation";
import { TILE_SIZE } from "./geometry";
import { tileClientRect } from "./hudFade";
import { CARD_GAP, cardPlacement, clientToTile, fitScale, scaledSize } from "./stageLayout";
import { smallView } from "./testFixtures";
import { mapClipRect } from "../render/mapClip";

const T = TILE_SIZE;
const tiles = (w: number, h: number, height = 0) => Array.from({ length: w * h }, () => ({ height }));
const plain: HeightGrid = { width: 10, height: 8, tiles: tiles(10, 8) };
const edged: HeightGrid = { ...plain, margin: STAGE_MARGIN };

describe("留邊的大小", () => {
  it("上緣約半格（半格＋2）、右緣四分之一格；左、下不留", () => {
    expect(STAGE_MARGIN).toEqual({ top: T / 2 + 2, right: T / 4 });
    expect(topReserve(edged)).toBe(topReserve(plain) + STAGE_MARGIN.top);
    const a = stagePixels(plain);
    const b = stagePixels(edged);
    expect(b.width).toBe(a.width + STAGE_MARGIN.right);
    expect(b.height).toBe(a.height + STAGE_MARGIN.top);
  });

  it("上緣放得下量到的最高動作（精英＋大型蜥蜴掄尾 333 ms 的尾尖，超出格頂 52.5 模型像素）", () => {
    expect(topReserve(edged)).toBeGreaterThanOrEqual(52.5);
  });

  it("沒有給 margin 的地圖（實地地圖、開發頁、純幾何）大小不變", () => {
    expect(stagePixels(plain)).toEqual({ width: 10 * T, height: 8 * T + topReserve(plain) });
    expect(topReserve({ width: 10, height: 8 })).toBe(0);
    expect(stagePixels({ width: 10, height: 8 })).toEqual({ width: 10 * T, height: 8 * T });
  });

  it("戰鬥畫面的畫法（BATTLE_DRAW）才帶留邊；預設的 buildDrawModel 不帶", () => {
    const view = smallView();
    expect(buildDrawModel(view, "hero").margin).toBeUndefined();
    expect(buildDrawModel(view, "hero", undefined, undefined, BATTLE_DRAW).margin).toEqual(STAGE_MARGIN);
  });

  it("高地與頭目的上方預留照舊，留邊另外加上去", () => {
    const high: HeightGrid = { width: 4, height: 4, tiles: tiles(4, 4, 3), units: [{ template: "rift_shard_lord" }] };
    expect(topReserve({ ...high, margin: STAGE_MARGIN })).toBe(topReserve(high) + STAGE_MARGIN.top);
  });
});

describe("座標換算與點擊", () => {
  for (const scale of [0.5, 0.73, 1, 1.31, 2]) {
    it(`每格中心點回同一格（縮放 ${scale}，畫布有位移）`, () => {
      const size = stagePixels(edged);
      const rect = { left: 137.5, top: 48.25, width: size.width * scale, height: size.height * scale };
      for (let y = 0; y < edged.height; y += 1) {
        for (let x = 0; x < edged.width; x += 1) {
          const cx = rect.left + (x + 0.5) * T * scale;
          const cy = rect.top + (topReserve(edged) + (y + 0.5) * T) * scale;
          expect(clientToTile(cx, cy, rect, edged)).toEqual({ x, y });
        }
      }
    });
  }

  it("格子的四個角落（往內 0.5 像素）都點得到自己，縮放後的整數 CSS 大小也一樣", () => {
    const scale = 1.37;
    const shown = scaledSize(edged, scale);
    const rect = { left: 20, top: 30, ...shown };
    const sx = shown.width / stagePixels(edged).width;
    const sy = shown.height / stagePixels(edged).height;
    for (const p of [{ x: 0, y: 0 }, { x: 9, y: 0 }, { x: 0, y: 7 }, { x: 9, y: 7 }, { x: 4, y: 3 }]) {
      const left = rect.left + p.x * T * sx;
      const top = rect.top + (topReserve(edged) + p.y * T) * sy;
      for (const [dx, dy] of [[0.5, 0.5], [T * sx - 0.5, 0.5], [0.5, T * sy - 0.5], [T * sx - 0.5, T * sy - 0.5]] as const) {
        expect(clientToTile(left + dx, top + dy, rect, edged)).toEqual(p);
      }
    }
  });

  it("點在上緣、右緣的留邊上不選到任何格子", () => {
    const size = stagePixels(edged);
    const rect = { left: 0, top: 0, width: size.width, height: size.height };
    // 右緣留邊：整條（從上到下）都沒有格子
    for (const y of [1, topReserve(edged) + 1, size.height - 1]) {
      expect(clientToTile(10 * T + 1, y, rect, edged)).toBeNull();
      expect(clientToTile(size.width - 0.5, y, rect, edged)).toBeNull();
    }
    // 最右欄的右緣內側仍是最右欄
    expect(clientToTile(10 * T - 0.5, topReserve(edged) + 1, rect, edged)).toEqual({ x: 9, y: 0 });
    // 上緣留邊與頭頂預留：平地時沒有格子
    expect(clientToTile(T / 2, 1, rect, edged)).toBeNull();
    expect(clientToTile(T / 2, topReserve(edged) - 0.5, rect, edged)).toBeNull();
    expect(clientToTile(T / 2, topReserve(edged), rect, edged)).toEqual({ x: 0, y: 0 });
  });

  it("同一個畫面位置：留邊前後選到的格子相同（畫布往上、往右各長一條）", () => {
    const a = stagePixels(plain);
    const b = stagePixels(edged);
    const before = { left: 100, top: 100, width: a.width, height: a.height };
    const after = { left: 100, top: 100 - STAGE_MARGIN.top, width: b.width, height: b.height };
    for (let py = 0; py < a.height; py += 7) {
      for (let px = 0; px < a.width; px += 7) {
        expect(clientToTile(100 + px, 100 + py, after, edged)).toEqual(clientToTile(100 + px, 100 + py, before, plain));
      }
    }
  });
});

describe("對位", () => {
  it("HUD 避讓用的格子矩形跟著畫布實際大小（含兩邊留邊）", () => {
    const px = stagePixels(edged);
    const canvas = { left: 100, top: 50, width: px.width / 2, height: px.height / 2 };
    const r = tileClientRect({ x: 9, y: 0 }, edged, canvas);
    expect(r.width).toBeCloseTo(T / 2);
    expect(r.height).toBeCloseTo(T / 2);
    expect(r.left).toBeCloseTo(100 + 9 * T * 0.5);
    expect(r.top).toBeCloseTo(50 + topReserve(edged) * 0.5);
    // 最右欄的右緣 ＋ 右邊留邊 ＝ 畫布右緣
    expect(r.left + r.width + STAGE_MARGIN.right * 0.5).toBeCloseTo(canvas.left + canvas.width);
  });

  it("浮動卡：靠右的格子從畫布右緣量時多算右邊留邊，卡片仍貼在格子左側", () => {
    const scale = 1.5;
    const shown = scaledSize(edged, scale);
    const place = cardPlacement({ x: 8, y: 6 }, edged, scale);
    // 卡片右緣在畫布上的 x ＝ 畫布寬 − right ＝ 格子左緣 − 間距
    expect(shown.width - (place.right ?? 0)).toBeCloseTo(8 * T * scale - CARD_GAP, 0);
    expect(place.bottom).toBe(Math.round((8 - 6 - 1) * T * scale));
    // 靠左、靠上的格子：left 不變，top 含上緣留邊
    const tl = cardPlacement({ x: 1, y: 1 }, edged, scale);
    expect(tl.left).toBe(Math.round(2 * T * scale + CARD_GAP));
    expect(tl.top).toBe(Math.round(T * scale + topReserve(edged) * scale));
    // 沒有留邊時照舊
    expect(cardPlacement({ x: 8, y: 6 }, plain, scale).right).toBe(Math.round(2 * T * scale + CARD_GAP));
  });

  it("自動填滿：照含留邊的畫布大小縮放，整張畫布（含留邊）放得進可用空間", () => {
    const avail = { width: 900, height: 620 };
    const s = fitScale(avail, edged);
    const shown = scaledSize(edged, s);
    expect(shown.width).toBeLessThanOrEqual(avail.width);
    expect(shown.height).toBeLessThanOrEqual(avail.height);
    expect(s).toBeLessThanOrEqual(fitScale(avail, plain));
  });

  it("地上特效的裁切矩形仍是地圖本身（不含留邊）", () => {
    expect(mapClipRect(edged)).toEqual(mapClipRect(plain));
    expect(mapClipRect(edged)).toEqual({ x: 0, y: 0, width: 10 * T, height: 8 * T });
  });
});
