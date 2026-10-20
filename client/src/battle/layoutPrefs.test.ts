import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TILE_SIZE } from "./geometry";
import {
  clampLayout,
  clampZoom,
  DEFAULT_LAYOUT,
  dragValue,
  layoutLimits,
  loadLayout,
  saveLayout,
  zoomBy,
  zoomPercent,
  ZOOM_MAX,
  ZOOM_MIN,
  ZOOM_STEP,
} from "./layoutPrefs";
import { clientToTile, scaledSize } from "./stageLayout";

describe("layout limits and dragging", () => {
  const viewport = { width: 1280, height: 720 };

  it("never lets the side column or bottom row take more than half of the area", () => {
    const l = layoutLimits(viewport);
    expect(l.side[1]).toBeLessThanOrEqual(viewport.width / 2);
    expect(l.bottom[1]).toBeLessThanOrEqual(viewport.height / 2);
    expect(l.side[0]).toBeLessThan(l.side[1]);
    expect(l.bottom[0]).toBeLessThan(l.bottom[1]);
    // 很小的視窗仍保持 min <= max
    const tiny = layoutLimits({ width: 300, height: 200 });
    expect(tiny.side[0]).toBeLessThanOrEqual(tiny.side[1]);
    expect(tiny.bottom[0]).toBeLessThanOrEqual(tiny.bottom[1]);
  });

  it("drags with the right direction and clamps", () => {
    const l = layoutLimits(viewport);
    // 右側窄欄的左緣往左拖（位移為負）會變寬
    expect(dragValue(300, -50, -1, l.side)).toBe(350);
    expect(dragValue(300, 50, -1, l.side)).toBe(250);
    expect(dragValue(300, -5000, -1, l.side)).toBe(l.side[1]);
    expect(dragValue(300, 5000, -1, l.side)).toBe(l.side[0]);
    // 主角狀態卡的右緣往右拖變寬
    expect(dragValue(300, 40, 1, l.hero)).toBe(340);
  });

  it("clamps a stored layout into the current viewport (shrinking the window pulls it back)", () => {
    const big = { sideWidth: 900, bottomHeight: 600, heroWidth: 900, zoom: 9 };
    const c = clampLayout(big, viewport);
    const l = layoutLimits(viewport);
    expect(c).toEqual({ sideWidth: l.side[1], bottomHeight: l.bottom[1], heroWidth: l.hero[1], zoom: ZOOM_MAX });
    expect(clampLayout(DEFAULT_LAYOUT, viewport)).toEqual(DEFAULT_LAYOUT);
  });
});

describe("zoom", () => {
  it("steps by the factor and stays in range", () => {
    expect(zoomBy(1, ZOOM_STEP)).toBe(1.25);
    expect(zoomBy(1, 1 / ZOOM_STEP)).toBe(0.8);
    expect(zoomBy(ZOOM_MAX, ZOOM_STEP)).toBe(ZOOM_MAX);
    expect(zoomBy(ZOOM_MIN, 1 / ZOOM_STEP)).toBe(ZOOM_MIN);
    expect(clampZoom(0.01)).toBe(ZOOM_MIN);
    expect(zoomPercent(1.25)).toBe("125%");
  });

  it("maps a click back to the right tile when zoomed in and panned", () => {
    const grid = { width: 12, height: 8 };
    const scale = 2; // 放大兩倍
    const size = scaledSize(grid, scale);
    expect(size.width).toBe(12 * TILE_SIZE * 2);
    // 捲動區 600×400 的左上角在 (100, 50)；捲動了 (250, 130)：畫布左上角在畫面上 (100-250, 50-130)
    const rect = { left: 100 - 250, top: 50 - 130, width: size.width, height: size.height };
    // 模型像素 (7.5, 3.5) 格的中心 → 畫面位置
    const t = TILE_SIZE * scale;
    const cx = rect.left + 7.5 * t;
    const cy = rect.top + 3.5 * t;
    expect(clientToTile(cx, cy, rect, grid)).toEqual({ x: 7, y: 3 });
    // 同一個點在不同捲動位置下對應不同的格子
    const panned = { ...rect, left: rect.left - t, top: rect.top };
    expect(clientToTile(cx, cy, panned, grid)).toEqual({ x: 8, y: 3 });
    // 畫布範圍外
    expect(clientToTile(rect.left - 1, cy, rect, grid)).toBeNull();
    expect(clientToTile(rect.left + size.width + 1, cy, rect, grid)).toBeNull();
  });

  it("maps a click correctly when zoomed out (smaller than the area)", () => {
    const grid = { width: 10, height: 10 };
    const rect = { left: 40, top: 20, width: 10 * TILE_SIZE * 0.5, height: 10 * TILE_SIZE * 0.5 };
    const t = TILE_SIZE * 0.5;
    expect(clientToTile(rect.left + 2.5 * t, rect.top + 9.5 * t, rect, grid)).toEqual({ x: 2, y: 9 });
  });
});

describe("persistence", () => {
  const store = new Map<string, string>();
  const fakeStorage = {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  };

  beforeEach(() => {
    store.clear();
    vi.stubGlobal("window", { localStorage: fakeStorage });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("round-trips through localStorage", () => {
    const prefs = { sideWidth: 380, bottomHeight: 200, heroWidth: 340, zoom: 1.5 };
    saveLayout(prefs);
    expect(loadLayout()).toEqual(prefs);
    saveLayout({ ...prefs, zoom: null });
    expect(loadLayout().zoom).toBeNull();
  });

  it("falls back to defaults for missing, broken or partial data", () => {
    expect(loadLayout()).toEqual(DEFAULT_LAYOUT);
    store.set("trpg.battleLayout", "not json");
    expect(loadLayout()).toEqual(DEFAULT_LAYOUT);
    store.set("trpg.battleLayout", JSON.stringify({ sideWidth: "x", heroWidth: 350 }));
    expect(loadLayout()).toEqual({ ...DEFAULT_LAYOUT, heroWidth: 350 });
  });

  it("does not throw when localStorage is unavailable", () => {
    vi.stubGlobal("window", {
      get localStorage(): never {
        throw new Error("blocked");
      },
    });
    expect(loadLayout()).toEqual(DEFAULT_LAYOUT);
    expect(() => saveLayout(DEFAULT_LAYOUT)).not.toThrow();
  });
});
