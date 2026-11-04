// Phase 6B-6：實地地圖的鏡頭（夾邊界、置中、跟隨、框矩形、點擊換算、小地圖的框、出口半透明、排版煙霧）。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { topReserve } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import { clientToTile } from "../battle/stageLayout";
import {
  cameraTransform,
  canvasRect,
  canvasSize,
  clampAxis,
  exitViewRects,
  FIELD_SCALE,
  fitsInView,
  followCamera,
  frameCamera,
  sameCamera,
  tileViewRect,
  viewToTile,
  visibleTiles,
} from "./camera";
import { fadedBlocks, HUD_BLOCKS, hudInsets, hudLayout, type Rect } from "./hud";

const T = TILE_SIZE;

/** 平地的 w×h 實地地圖（出口另給）。 */
function flat(width: number, height: number, over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: width * height }, (_, i) => ({
    x: i % width,
    y: Math.floor(i / width),
    height: 0,
    terrain: "stone",
    surface: "none",
  }));
  return {
    map_id: "m",
    name_zh: "測試",
    width,
    height,
    tiles,
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    stone_targets: [],
    npcs: [],
    facilities: [],
    me: { x: 0, y: 0 },
    ...over,
  } as unknown as FieldView;
}

/** 霧渡鎮（24×18）與渡口石階（20×12）的大小與出口。 */
const mistFerry = (me = { x: 11, y: 9 }) =>
  flat(24, 18, {
    me,
    exits: [
      { id: "to_hunter_hut", cells: [[11, 0], [12, 0]], to: "hunter_hut", to_name_zh: "獵戶小屋" },
      { id: "to_ferry_steps", cells: [[23, 8], [23, 9]], to: "ferry_steps", to_name_zh: "渡口石階" },
    ],
  } as Partial<FieldView>);
const ferrySteps = (me = { x: 1, y: 8 }) =>
  flat(20, 12, {
    me,
    exits: [
      { id: "to_mist_ferry", cells: [[0, 8], [0, 9]], to: "mist_ferry", to_name_zh: "霧渡鎮" },
      { id: "to_bamboo_path", cells: [[14, 0], [15, 0]], to: "bamboo_path", to_name_zh: "竹林小徑" },
    ],
  } as Partial<FieldView>);

/** 1040×624、800×600 視窗扣掉標頭後的舞台（同 hud.test.ts）。 */
const STAGE_1040 = { width: 1008, height: 556 };
const STAGE_800 = { width: 768, height: 532 };

describe("格子大小照戰鬥的預設", () => {
  it("每格 TILE_SIZE（戰鬥繪製器 scale＝1）", () => {
    expect(FIELD_SCALE).toBe(1);
    const cam = followCamera(STAGE_1040, mistFerry(), mistFerry().me);
    expect(cam.scale).toBe(1);
    expect(canvasSize(mistFerry(), cam.scale).width).toBe(24 * T);
  });

  it("霧渡鎮比 1040×624 的舞台大（要跟著走），12×6 的小地圖放得下", () => {
    expect(fitsInView(STAGE_1040, mistFerry())).toBe(false);
    expect(fitsInView(STAGE_1040, flat(12, 6))).toBe(true);
  });
});

describe("夾邊界與置中", () => {
  it("一個方向：內容比畫面小就置中（負的位移）", () => {
    expect(clampAxis(1000, 600, 0)).toBe(-200);
    expect(clampAxis(1000, 600, 9999)).toBe(-200);
  });

  it("一個方向：內容比畫面大就夾在 [0, 內容−畫面]", () => {
    expect(clampAxis(500, 1200, 0)).toBe(0);
    expect(clampAxis(500, 1200, 600)).toBe(350);
    expect(clampAxis(500, 1200, 5000)).toBe(700);
  });

  it("地圖比畫面小：兩個方向都置中，畫布在畫面正中間", () => {
    const small = flat(10, 6);
    const cam = followCamera(STAGE_1040, small, { x: 0, y: 0 });
    const size = canvasSize(small, 1);
    expect(cam.x).toBeCloseTo(-(STAGE_1040.width - size.width) / 2, 5);
    expect(cam.y).toBeCloseTo(-(STAGE_1040.height - size.height) / 2, 5);
    // 主角在哪都一樣
    expect(sameCamera(cam, followCamera(STAGE_1040, small, { x: 9, y: 5 }))).toBe(true);
  });

  it("只有一個方向比畫面大：那個方向跟、另一個方向置中", () => {
    const wide = flat(30, 6);
    const left = followCamera(STAGE_1040, wide, { x: 0, y: 3 });
    const right = followCamera(STAGE_1040, wide, { x: 29, y: 3 });
    expect(left.x).toBe(0);
    expect(right.x).toBe(30 * T - STAGE_1040.width);
    expect(left.y).toBeLessThan(0);
    expect(left.y).toBe(right.y);
  });

  it("到地圖邊緣停住：四個角都不露出地圖外", () => {
    const f = mistFerry();
    const size = canvasSize(f, 1);
    for (const p of [
      { x: 0, y: 0 },
      { x: 23, y: 0 },
      { x: 0, y: 17 },
      { x: 23, y: 17 },
    ]) {
      const cam = followCamera(STAGE_1040, f, p);
      expect(cam.x).toBeGreaterThanOrEqual(0);
      expect(cam.y).toBeGreaterThanOrEqual(0);
      expect(cam.x + STAGE_1040.width).toBeLessThanOrEqual(size.width);
      expect(cam.y + STAGE_1040.height).toBeLessThanOrEqual(size.height);
    }
  });
});

describe("跟隨", () => {
  it("地圖中間：主角在畫面正中央", () => {
    const f = mistFerry({ x: 12, y: 9 });
    const cam = followCamera(STAGE_1040, f, f.me);
    const r = tileViewRect(f, f.me, cam);
    expect(r.left + r.width / 2).toBeCloseTo(STAGE_1040.width / 2, 5);
    expect(r.top + r.height / 2).toBeCloseTo(STAGE_1040.height / 2, 5);
  });

  it("往東走一格，鏡頭往東移一格（沒碰到邊）", () => {
    const f = mistFerry();
    const a = followCamera(STAGE_1040, f, { x: 11, y: 9 });
    const b = followCamera(STAGE_1040, f, { x: 12, y: 9 });
    expect(b.x - a.x).toBe(T);
    expect(b.y).toBe(a.y);
  });

  it("補間中的小數位置：鏡頭在兩格之間（平滑）", () => {
    const f = mistFerry();
    const a = followCamera(STAGE_1040, f, { x: 11, y: 9 });
    const mid = followCamera(STAGE_1040, f, { x: 11.5, y: 9 });
    expect(mid.x - a.x).toBe(T / 2);
  });

  it("CSS 平移是鏡頭的反方向", () => {
    expect(cameraTransform({ x: 120, y: -30, scale: 1 })).toBe("translate(-120px, 30px)");
  });
});

describe("框住指定矩形（6C-2 就地開打用）", () => {
  it("12×12 戰場整個在畫面裡，縮放不超過 1", () => {
    const f = flat(40, 30);
    const rect = { x: 10, y: 8, width: 12, height: 12 };
    const cam = frameCamera(STAGE_1040, f, rect);
    expect(cam.scale).toBeLessThanOrEqual(1);
    const tl = tileViewRect(f, { x: rect.x, y: rect.y }, cam);
    const br = tileViewRect(f, { x: rect.x + rect.width - 1, y: rect.y + rect.height - 1 }, cam);
    expect(tl.left).toBeGreaterThanOrEqual(0);
    expect(tl.top).toBeGreaterThanOrEqual(0);
    expect(br.left + br.width).toBeLessThanOrEqual(STAGE_1040.width + 0.01);
    expect(br.top + br.height).toBeLessThanOrEqual(STAGE_1040.height + 0.01);
    // 戰場中心在畫面中央
    expect((tl.left + br.left + br.width) / 2).toBeCloseTo(STAGE_1040.width / 2, 3);
  });

  it("畫面夠大時不放大（維持戰鬥預設大小）", () => {
    const cam = frameCamera({ width: 1600, height: 1000 }, flat(40, 30), { x: 0, y: 0, width: 12, height: 12 });
    expect(cam.scale).toBe(1);
  });

  it("戰場貼著地圖邊：鏡頭照樣夾在地圖內", () => {
    const f = flat(40, 30);
    const cam = frameCamera(STAGE_800, f, { x: 0, y: 0, width: 12, height: 12 });
    expect(cam.x).toBeGreaterThanOrEqual(0);
    expect(cam.y).toBeGreaterThanOrEqual(0);
  });

  it("畫面太小時縮放有下限", () => {
    expect(frameCamera({ width: 100, height: 100 }, flat(40, 30), { x: 0, y: 0, width: 12, height: 12 }).scale).toBe(0.5);
  });
});

describe("點擊換算考慮鏡頭位移", () => {
  it("點畫面正中央＝主角那格", () => {
    const f = mistFerry({ x: 12, y: 9 });
    const cam = followCamera(STAGE_1040, f, f.me);
    expect(viewToTile(STAGE_1040.width / 2, STAGE_1040.height / 2, f, cam)).toEqual({ x: 12, y: 9 });
  });

  it("鏡頭在右下角時點畫面左上角＝不是 (0,0)", () => {
    const f = mistFerry({ x: 23, y: 17 });
    const cam = followCamera(STAGE_1040, f, f.me);
    const t = viewToTile(1, 1, f, cam)!;
    expect(t.x).toBe(Math.floor(cam.x / T));
    expect(t.x).toBeGreaterThan(0);
    expect(t.y).toBeGreaterThan(0);
  });

  it("和 BattleCanvas 用 getBoundingClientRect 換算的結果一樣（畫布平移後的矩形）", () => {
    const f = mistFerry({ x: 20, y: 14 });
    const cam = followCamera(STAGE_1040, f, f.me);
    const stageLeft = 16;
    const stageTop = 60;
    const rect = canvasRect(f, cam, stageLeft, stageTop);
    for (const [px, py] of [
      [5, 5],
      [500, 300],
      [1000, 550],
    ] as const) {
      expect(clientToTile(stageLeft + px, stageTop + py, rect, f)).toEqual(viewToTile(px, py, f, cam));
    }
  });

  it("地圖比畫面小時點到置中留白＝null", () => {
    const small = flat(6, 4);
    const cam = followCamera(STAGE_1040, small, { x: 0, y: 0 });
    expect(viewToTile(2, 2, small, cam)).toBeNull();
  });
});

describe("小地圖上的鏡頭範圍", () => {
  it("霧渡鎮在 1040×624：框比整張小、在地圖裡、包住主角", () => {
    const f = mistFerry({ x: 12, y: 9 });
    const cam = followCamera(STAGE_1040, f, f.me);
    const v = visibleTiles(STAGE_1040, f, cam);
    expect(v.width).toBeCloseTo(STAGE_1040.width / T, 5);
    expect(v.width).toBeLessThan(24);
    expect(v.x).toBeGreaterThanOrEqual(0);
    expect(v.y).toBeGreaterThanOrEqual(0);
    expect(v.x + v.width).toBeLessThanOrEqual(24);
    expect(v.y + v.height).toBeLessThanOrEqual(18);
    expect(f.me.x).toBeGreaterThanOrEqual(v.x);
    expect(f.me.x + 1).toBeLessThanOrEqual(v.x + v.width);
    expect(f.me.y).toBeGreaterThanOrEqual(v.y);
    expect(f.me.y + 1).toBeLessThanOrEqual(v.y + v.height);
  });

  it("地圖比畫面小：框＝整張", () => {
    const small = flat(10, 6);
    const v = visibleTiles(STAGE_1040, small, followCamera(STAGE_1040, small, { x: 0, y: 0 }));
    expect(v).toEqual({ x: 0, y: 0, width: 10, height: 6 });
  });
});

describe("出口半透明照畫面上的出口位置", () => {
  const layout = hudLayout(STAGE_1040.width, STAGE_1040.height, { mates: 2, narrow: false, collapsed: false });

  it("主角在西邊：東側出口在畫面外，不擋任何一塊", () => {
    const f = mistFerry({ x: 2, y: 9 });
    expect(fadedBlocks(layout, exitViewRects(f, followCamera(STAGE_1040, f, f.me)))).toEqual([]);
  });

  it("主角走到東邊：東側出口到了畫面右緣，任務追蹤變半透明", () => {
    const f = mistFerry({ x: 22, y: 9 });
    const cam = followCamera(STAGE_1040, f, f.me);
    const exits = exitViewRects(f, cam);
    const east = exits[2]!;
    expect(east.left + east.width).toBeCloseTo(STAGE_1040.width, 0);
    expect(fadedBlocks(layout, exits)).toContain("tracker");
  });

  it("出口在小地圖底下時小地圖不變半透明（6F-1 U16：「出」口格不畫在小地圖上面）", () => {
    const m = layout.blocks.minimap;
    const exit: Rect = { left: m.left + 4, top: m.top + 4, width: 20, height: 20 };
    expect(fadedBlocks(layout, [exit])).not.toContain("minimap");
  });

  it("出口剛好在畫面外（只差半格緩衝）：給了畫面大小就不讓 HUD 變半透明", () => {
    const f = mistFerry({ x: 12, y: 9 });
    const cam = followCamera(STAGE_1040, f, f.me);
    expect(fadedBlocks(layout, exitViewRects(f, cam))).toContain("tracker");
    expect(exitViewRects(f, cam, STAGE_1040).some((r) => r.left >= STAGE_1040.width)).toBe(false);
    expect(fadedBlocks(layout, exitViewRects(f, cam, STAGE_1040))).toEqual([]);
  });

  it("出口的位置隨鏡頭移動", () => {
    const f = mistFerry();
    const a = exitViewRects(f, { x: 0, y: 0, scale: 1 })[0]!;
    const b = exitViewRects(f, { x: 100, y: 40, scale: 1 })[0]!;
    expect(a.left - b.left).toBe(100);
    expect(a.top - b.top).toBe(40);
    expect(a.top).toBe(topReserve(f));
  });
});

/** 兩個矩形重疊。 */
function overlaps(a: Rect, b: Rect): boolean {
  return a.left < b.left + b.width && b.left < a.left + a.width && a.top < b.top + b.height && b.top < a.top + a.height;
}

describe("排版煙霧（1040×624、800×600）", () => {
  const cases = [
    { name: "1040×624", stage: STAGE_1040, narrow: false },
    { name: "800×600", stage: STAGE_800, narrow: true },
  ];
  for (const c of cases) {
    for (const [mapName, make] of [
      ["霧渡鎮", mistFerry],
      ["渡口石階", ferrySteps],
    ] as const) {
      it(`${c.name}・${mapName}：地圖蓋滿畫面、主角在畫面裡且不被 HUD 擋`, () => {
        const layout = hudLayout(c.stage.width, c.stage.height, { mates: 2, narrow: c.narrow, collapsed: c.narrow });
        const base = make();
        const size = canvasSize(base, 1);
        // 走遍每一格：主角都在畫面裡；地圖大的方向畫布蓋滿畫面（沒有露出地圖外）
        for (let y = 0; y < base.height; y += 1) {
          for (let x = 0; x < base.width; x += 1) {
            const cam = followCamera(c.stage, base, { x, y });
            const r = tileViewRect(base, { x, y }, cam);
            expect(r.left).toBeGreaterThanOrEqual(-0.01);
            expect(r.top).toBeGreaterThanOrEqual(-0.01);
            expect(r.left + r.width).toBeLessThanOrEqual(c.stage.width + 0.01);
            expect(r.top + r.height).toBeLessThanOrEqual(c.stage.height + 0.01);
            if (size.width > c.stage.width) expect(cam.x + c.stage.width).toBeLessThanOrEqual(size.width);
            if (size.height > c.stage.height) expect(cam.y + c.stage.height).toBeLessThanOrEqual(size.height);
          }
        }
        // 入口附近（不在角落）：主角不被任何 HUD 塊擋住
        const f = make();
        const cam = followCamera(c.stage, f, f.me);
        const hero = tileViewRect(f, f.me, cam);
        if (mapName === "霧渡鎮") for (const id of HUD_BLOCKS) expect(overlaps(hero, layout.blocks[id]), id).toBe(false);
      });
    }
  }
});

describe("6F-3：鏡頭避開 HUD（巡檢 bug 3）", () => {
  const inside = (r: Rect, safe: Rect) =>
    r.left >= safe.left - 0.5 && r.top >= safe.top - 0.5 && r.left + r.width <= safe.left + safe.width + 0.5 && r.top + r.height <= safe.top + safe.height + 0.5;

  it("clampAxis：內容比安全區小在安全區置中；否則邊緣最多捲到安全區的邊", () => {
    expect(clampAxis(600, 300, 0, 100, 50)).toBe(-(100 + (450 - 300) / 2));
    // 內容 1000，主角在最下面（中心 990）：邊緣停在安全區下緣（可以捲過內容−可視區）
    expect(clampAxis(600, 1000, 990, 80, 70)).toBe(1000 - 600 + 70);
    expect(clampAxis(600, 1000, 10, 80, 70)).toBe(-80);
    // 不扣 HUD 時同 6B-6
    expect(clampAxis(600, 1000, 990)).toBe(400);
    expect(clampAxis(600, 300, 0)).toBe(-150);
  });

  for (const [w, h] of [
    [1600, 900],
    [1040, 624],
    [800, 600],
  ] as const) {
    it(`${w}×${h}：主角在任何一格都在安全區內，走到出口旁邊時出口也在`, () => {
      const layout = hudLayout(w, h, { mates: 2, narrow: w < 900, collapsed: false });
      const ins = hudInsets(layout, { width: w, height: h });
      const safe: Rect = { left: ins.left, top: ins.top, width: w - ins.left - ins.right, height: h - ins.top - ins.bottom };
      for (const id of ["hero", "bar", "minimap", "tracker"] as const) {
        const b = layout.blocks[id];
        expect(b.left + b.width <= safe.left || b.left >= safe.left + safe.width || b.top + b.height <= safe.top || b.top >= safe.top + safe.height).toBe(true);
      }
      for (const [mw, mh] of [
        [24, 18],
        [20, 12],
        [32, 24],
        [10, 8],
      ] as const) {
        for (let y = 0; y < mh; y += 1) {
          for (let x = 0; x < mw; x += 1) {
            const field = flat(mw, mh, {
              me: { x, y },
              exits: [{ id: "e", cells: [[mw - 1, y]], to: "t", to_name_zh: "外面" }],
            } as Partial<FieldView>);
            const cam = followCamera({ width: w, height: h }, field, { x, y }, FIELD_SCALE, ins);
            expect(inside(tileViewRect(field, { x, y }, cam), safe)).toBe(true);
            if (x >= mw - 2) expect(inside(tileViewRect(field, { x: mw - 1, y }, cam), safe)).toBe(true);
          }
        }
      }
    });
  }
});
