// Phase 6F-ART1：區域圖與大世界圖的程式插畫（B 俯視彩繪）。
// 快取鍵（區域、尺寸）、狀態變時只重畫上層、點擊區位置對齊 pos、迷霧三段、確定性。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AtlasRegionView, AtlasView, WorldLocationView, WorldMapView } from "../api/types";
import { atlasScene } from "../world/atlasScene";
import { fitStage, labelScale } from "../world/MapStage";
import { RegionMap } from "../world/RegionMap";
import { AtlasMap } from "../world/AtlasMap";
import { regionScene } from "../world/regionModel";
import { FOG_HOLE, fogHoles, H, hitPercent, P, spotHitBox, stoneHitBox, trailSteps, W } from "./regionMapArt";
import { baseKey, overlayKey, REGION_ART, RegionMapPainter, type Surface } from "./regionMapPainter";
import { AtlasPainter, buttonHitBox, islandHitBox, islandLayout, sky } from "./worldMapArt";

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
        if (prop === "measureText") return { width: String(args[0]).length * 10 };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${fmt(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

function fakeFactory(): { make: (w: number, h: number) => Surface; made: string[] } {
  const made: string[] = [];
  return {
    made,
    make: (w, h) => {
      made.push(`${w}x${h}`);
      const { ctx } = mockCtx();
      return { width: w, height: h, getContext: () => ctx };
    },
  };
}

function loc(id: string, over: Partial<WorldLocationView> = {}): WorldLocationView {
  return {
    id,
    name_zh: `地點${id}`,
    kind: "camp",
    kind_zh: "營地",
    level_zh: "Lv 1～2",
    description_zh: "",
    x: 30,
    y: 60,
    current: false,
    adjacent: false,
    blocked_zh: null,
    cleared: false,
    hidden: false,
    fog: "visited",
    quest_marks: [],
    footprints: [],
    ...over,
  };
}

function map(over: Partial<WorldMapView> = {}): WorldMapView {
  return {
    region: "cloud_ridge",
    name_zh: "雲嶺",
    level_zh: "Lv 1～6",
    locations: [
      loc("town", { kind: "town", current: true, level_zh: null, x: 10, y: 80 }),
      loc("camp", { cleared: true, quest_marks: ["霧狼"], x: 30, y: 60, footprints: ["阿岳"] }),
      loc("near", { fog: "silhouette", kind: "gate", level_zh: "Lv 3～4", x: 50, y: 40 }),
      loc("near2", { fog: "silhouette", x: 60, y: 30 }),
      loc("far", { fog: "fog", quest_marks: ["更遠"], x: 80, y: 10 }),
    ],
    edges: [
      ["town", "camp"],
      ["camp", "near"],
      ["near", "near2"],
      ["near", "far"],
    ],
    stones: [
      { id: "stone_town", location: "town", unlocked: true, here: true },
      { id: "stone_near", location: "near", unlocked: false, here: false },
      { id: "stone_far", location: "far", unlocked: true, here: false },
    ],
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
    ...over,
  };
}

describe("迷霧三段（場景資料）", () => {
  const scene = regionScene(map());

  it("霧裡的地點不在場景裡（名字、等級、任務、傳送石都不畫）；剪影寫「？？？」、渡口不寫等級", () => {
    expect(scene.spots.map((s) => s.id)).toEqual(["town", "camp", "near", "near2"]);
    const near = scene.spots.find((s) => s.id === "near");
    expect(near).toMatchObject({ fog: "silhouette", name: "？？？", stone: "off", kind: "gate" });
    expect(JSON.stringify(scene)).not.toContain("更遠");
    expect(JSON.stringify(scene)).not.toContain("far");
  });

  it("路：兩端去過＝實線、一端剪影＝虛線、兩端都剪影或有一端在霧裡＝不畫", () => {
    expect(scene.roads).toEqual([
      { a: "town", b: "camp", solid: true },
      { a: "camp", b: "near", solid: false },
    ]);
  });

  it("挖洞：去過 190、剪影 105（0.72）、霧不挖；兩端去過的路上再挖三點", () => {
    const holes = fogHoles(scene);
    const [tx, ty] = P(10, 80);
    expect(holes).toContainEqual({ x: tx, y: ty, rad: FOG_HOLE.visited.rad, alpha: 1 });
    const [nx, ny] = P(50, 40);
    expect(holes).toContainEqual({ x: nx, y: ny, rad: 105, alpha: 0.72 });
    const [fx, fy] = P(80, 10);
    expect(holes.some((h) => h.x === fx && h.y === fy)).toBe(false);
    expect(holes.filter((h) => h.rad === FOG_HOLE.road.rad)).toHaveLength(3);
    expect(holes).toHaveLength(4 + 3);
  });

  it("標記：自己、清空、任務、傳送石（解鎖／沒解鎖）", () => {
    const by = Object.fromEntries(scene.spots.map((s) => [s.id, s]));
    expect(by.town).toMatchObject({ current: true, stone: "on", level: "" });
    expect(by.camp).toMatchObject({ cleared: true, quest: true, level: "Lv 1～2", stone: null });
    expect(by.near?.cleared).toBe(false);
  });

  it("足跡：畫在通往地點、看得到的路上；好幾條時選連到的 ID 排序最前的；越接近地點越清楚", () => {
    // camp 連到 town（實線）與 near（虛線）：選 "near" < "town"
    expect(scene.trails).toEqual([{ road: { a: "camp", b: "near", solid: false }, to: "camp" }]);
    const steps = trailSteps(scene, scene.trails[0] as (typeof scene.trails)[number]);
    expect(steps.length).toBeGreaterThan(3);
    const [cx, cy] = P(30, 60);
    const dist = steps.map(([x, y]) => Math.hypot(x - cx, y - cy));
    expect(dist[dist.length - 1]).toBeLessThan(dist[0] as number);
    const alpha = steps.map((s) => s[3]);
    expect(alpha[alpha.length - 1]).toBeGreaterThan(alpha[0] as number);
  });

  it("沒有看得到的路的足跡：畫在地點旁", () => {
    const m = map({ locations: [loc("solo", { footprints: ["小白"] })], edges: [], stones: [] });
    expect(regionScene(m).lonelyTrails).toEqual(["solo"]);
  });
});

describe("快取與重畫", () => {
  it("快取鍵＝區域＋尺寸（＋字型版本）", () => {
    expect(baseKey("cloud_ridge", 1280, 860)).not.toBe(baseKey("ashen_waste", 1280, 860));
    expect(baseKey("cloud_ridge", 1280, 860)).not.toBe(baseKey("cloud_ridge", 640, 430));
    expect(baseKey("cloud_ridge", 1280, 860, 1)).not.toBe(baseKey("cloud_ridge", 1280, 860, 2));
    expect(baseKey("cloud_ridge", 1280, 860)).toBe(baseKey("cloud_ridge", 1280, 860));
  });

  it("同一區同尺寸開兩次只畫一次地景；換尺寸或換區才重畫", () => {
    const f = fakeFactory();
    const p = new RegionMapPainter(f.make);
    const { ctx } = mockCtx();
    p.paintBase(ctx, "cloud_ridge", 1280, 860);
    p.paintBase(ctx, "cloud_ridge", 1280, 860);
    expect(p.stats.terrain).toBe(1);
    p.paintBase(ctx, "cloud_ridge", 640, 430);
    p.paintBase(ctx, "ashen_waste", 640, 430);
    expect(p.stats.terrain).toBe(3);
    p.paintBase(ctx, "cloud_ridge", 1280, 860);
    expect(p.stats.terrain).toBe(3);
  });

  it("快取有上限（最舊的先丟）", () => {
    const p = new RegionMapPainter(fakeFactory().make, 2);
    const { ctx } = mockCtx();
    for (const w of [100, 200, 300]) p.paintBase(ctx, "cloud_ridge", w, w);
    expect(p.cachedTerrains).toBe(2);
    p.paintBase(ctx, "cloud_ridge", 100, 100);
    expect(p.stats.terrain).toBe(4);
  });

  it("狀態變時只重畫上層：地景與霧材質都不重畫，只重新挖洞", () => {
    const p = new RegionMapPainter(fakeFactory().make);
    const base = mockCtx();
    const over = mockCtx();
    const before = regionScene(map());
    const after = regionScene(map({ locations: map().locations.map((l) => (l.id === "near" ? { ...l, fog: "visited" as const } : l)) }));
    expect(overlayKey(before, 1280, 860, 1)).not.toBe(overlayKey(after, 1280, 860, 1));
    p.paintBase(base.ctx, "cloud_ridge", 1280, 860);
    p.paintOverlay(over.ctx, before, 1280, 860);
    const baseCalls = base.calls.length;
    p.paintOverlay(over.ctx, after, 1280, 860);
    expect(p.stats).toEqual({ terrain: 1, fog: 1, overlay: 2 });
    expect(base.calls.length).toBe(baseCalls);
  });

  it("上層畫得出名字牌、等級牌（伺服器的 level_zh）、清空、任務、傳送石；霧裡的名字不畫", () => {
    const p = new RegionMapPainter(fakeFactory().make);
    const over = mockCtx();
    p.paintOverlay(over.ctx, regionScene(map()), 1280, 860);
    const text = over.calls.filter((c) => c.startsWith("fillText(")).join("\n");
    expect(text).toContain("fillText(地點camp");
    expect(text).toContain("fillText(Lv 1～2");
    expect(text).toContain("fillText(？？？");
    expect(text).toContain("fillText(!");
    expect(text).toContain("fillText(建議 Lv 1～6");
    expect(text).not.toContain("Lv 3～4"); // 剪影的渡口不寫等級
    expect(text).not.toContain("地點far");
  });
});

describe("確定性（同一區開兩次，地景完全一樣；不用 Math.random）", () => {
  beforeEach(() => {
    vi.spyOn(Math, "random").mockImplementation(() => {
      throw new Error("不能用 Math.random");
    });
  });
  afterEach(() => vi.restoreAllMocks());

  for (const region of Object.keys(REGION_ART)) {
    it(`${region} 的地景、霧上地景兩次畫出一樣的指令`, () => {
      const draw = (): string[] => {
        const { ctx, calls } = mockCtx();
        const art = REGION_ART[region];
        art?.terrain(ctx);
        art?.afterFog?.(ctx);
        return calls;
      };
      const a = draw();
      expect(a.length).toBeGreaterThan(1000);
      expect(draw()).toEqual(a);
    });
  }

  it("大世界圖的天空與浮島兩次畫出一樣的指令", () => {
    const { scene } = atlasScene(atlas(), map());
    const draw = (): string[] => {
      const { ctx, calls } = mockCtx();
      sky(ctx);
      new AtlasPainter(fakeFactory().make).paintOverlay(ctx, scene, true, W, H);
      return calls;
    };
    expect(draw()).toEqual(draw());
  });
});

describe("點擊區和畫布用同一套 pos 換算", () => {
  it("地點點擊區以 P(pos) 為中心（水平）、包住圖示與名字牌", () => {
    for (const [x, y] of [[10, 80], [50, 55], [90, 8]] as const) {
      const [cx, cy] = P(x, y);
      const b = spotHitBox(x, y);
      expect(b.x + b.w / 2).toBeCloseTo(cx, 6);
      expect(b.y).toBeLessThan(cy - 20);
      expect(b.y + b.h).toBeGreaterThan(cy + 30 + 10);
      const pct = hitPercent(b);
      expect(parseFloat(pct.left) + parseFloat(pct.width) / 2).toBeCloseTo((cx / W) * 100, 2);
    }
  });

  it("P()：左右各留 80、上下各留 70", () => {
    expect(P(0, 0)).toEqual([80, 70]);
    expect(P(100, 100)).toEqual([W - 80, H - 70]);
  });

  it("傳送石點擊區在地點右邊（畫布上晶石的位置 x+28）", () => {
    const [cx, cy] = P(30, 60);
    const b = stoneHitBox(30, 60);
    expect(b.x + b.w / 2).toBeCloseTo(cx + 28, 6);
    expect(b.y + b.h / 2).toBeCloseTo(cy + 1, 6);
  });

  it("字牌倍數：面板 ≥ 900 寬不放大；更窄時點擊區跟著放大", () => {
    expect(labelScale(1280)).toBe(1);
    expect(labelScale(900)).toBe(1);
    expect(labelScale(600)).toBe(1.5);
    expect(spotHitBox(30, 60, 1.5).w).toBeCloseTo(spotHitBox(30, 60).w * 1.5, 6);
  });

  it("舞台等比縮放、置中放進面板", () => {
    expect(fitStage(1280, 2000)).toEqual({ w: 1280, h: 860 });
    expect(fitStage(2000, 430)).toEqual({ w: 640, h: 430 });
    expect(fitStage(0, 500)).toEqual({ w: 0, h: 0 });
  });

  it("區域圖畫面：霧裡的地點沒有點擊區；傳送石照 6C-6 的狀態；位置是百分比", () => {
    const html = renderToStaticMarkup(createElement(RegionMap, { map: map(), busy: false, onTeleport: () => undefined, onClose: () => undefined }));
    expect(html).toContain('data-loc="town"');
    expect(html).toContain('data-loc="near"');
    expect(html).not.toContain('data-loc="far"');
    expect(html).not.toContain("stone_far");
    expect(html).toContain('data-stone="stone_town"');
    expect(html).toContain('data-state="here"');
    expect(html).toContain('data-state="locked"');
    expect(html).toContain('data-testid="region-quest"');
    expect(html).toContain('data-testid="region-me"');
    expect(html).toContain('data-testid="region-footprint"');
    const b = hitPercent(spotHitBox(10, 80));
    expect(html).toContain(`left:${b.left}`);
    expect(html).not.toContain("region-map-lines");
    expect(html).not.toContain("region-fog");
  });
});

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, ...over };
}

function atlas(over: Partial<AtlasView> = {}): AtlasView {
  return {
    regions: [
      region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", current: true }),
      region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: null }),
      region({ region: "ashen_waste", name_zh: "灰燼荒原", town: "ember_market", town_name_zh: "餘燼集", can_teleport: true }),
      region({ region: "frost_tide", name_zh: "霜潮海境", status: "locked", condition_zh: "世界事件：霧潮入侵" }),
    ],
    capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島", can_teleport: true }),
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
    maps: [{ ...map(), region: "ashen_waste", name_zh: "灰燼荒原", level_zh: "Lv 5～9" }],
    ...over,
  };
}

describe("大世界圖", () => {
  const { scene } = atlasScene(atlas(), map());
  const by = Object.fromEntries(scene.islands.map((i) => [i.region, i]));

  it("方位照 6D-5：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮，主城在中央", () => {
    const cap = scene.capital.geo;
    expect(cap.x).toBeGreaterThan(W * 0.45);
    expect(cap.x).toBeLessThan(W * 0.55);
    expect(by.cloud_ridge?.geo.x).toBeLessThan(cap.x);
    expect(by.ashen_waste?.geo.y).toBeGreaterThan(cap.y);
    expect(by.crystal_crown?.geo.y).toBeLessThan(cap.y);
    expect(by.frost_tide?.geo.x).toBeGreaterThan(cap.x);
    expect(by.frost_tide?.geo.y).toBeGreaterThan(cap.y);
  });

  it("三種狀態：已開放有等級牌（區域圖的 level_zh）；未開放寫條件，沒條件就寫「之後的賽季」", () => {
    expect(by.ashen_waste).toMatchObject({ status: "open", level: "Lv 5～9", town: "餘燼集", condition: "" });
    expect(by.cloud_ridge?.level).toBe("Lv 1～6");
    expect(by.frost_tide).toMatchObject({ status: "locked", condition: "世界事件：霧潮入侵" });
    expect(by.crystal_crown).toMatchObject({ status: "later", condition: "之後的賽季" });
  });

  it("傳送鈕只在可以傳送、不是自己所在的區；自己所在的區改寫「你在〇〇」", () => {
    const ashen = by.ashen_waste;
    const cloud = by.cloud_ridge;
    if (ashen === undefined || cloud === undefined) throw new Error("缺島");
    expect(islandLayout(ashen).buttonY).not.toBeNull();
    expect(islandLayout(cloud).buttonY).toBeNull();
    expect(islandLayout(cloud).hereY).not.toBeNull();
    expect(buttonHitBox(cloud)).toBeNull();
    const b = buttonHitBox(ashen);
    expect(b !== null && b.x + b.w / 2).toBeCloseTo(ashen.geo.x, 6);
    const ib = islandHitBox(ashen);
    expect(ib.x + ib.w / 2).toBe(ashen.geo.x);
  });

  it("上層畫出名字、條件、傳送鈕、「你在霧渡鎮」與浮橋（開放＝木板、未開放＝虛線）", () => {
    const { ctx, calls } = mockCtx();
    new AtlasPainter(fakeFactory().make).paintOverlay(ctx, scene, true, W, H);
    const text = calls.filter((c) => c.startsWith("fillText(")).join("\n");
    for (const t of ["雲嶺", "灰燼荒原", "傳送到餘燼集", "你在霧渡鎮", "世界事件：霧潮入侵", "之後的賽季", "傳送到樞島"]) expect(text).toContain(`fillText(${t}`);
    expect(text).not.toContain("傳送到霧渡鎮");
    expect(calls.some((c) => c.startsWith("setLineDash(object"))).toBe(true);
  });

  it("天空照尺寸快取；浮島狀態變了只重畫上層", () => {
    const p = new AtlasPainter(fakeFactory().make);
    const { ctx } = mockCtx();
    p.paintBase(ctx, 1280, 860);
    p.paintBase(ctx, 1280, 860);
    p.paintOverlay(ctx, scene, true, 1280, 860);
    p.paintOverlay(ctx, atlasScene(atlas({ can_teleport: false }), map()).scene, false, 1280, 860);
    expect(p.stats).toEqual({ sky: 1, overlay: 2 });
    p.paintBase(ctx, 640, 430);
    expect(p.stats.sky).toBe(2);
  });

  it("畫面：點擊區保留（島、傳送鈕、條件、自己），浮島位置用畫布座標的百分比", () => {
    const html = renderToStaticMarkup(
      createElement(AtlasMap, { atlas: atlas(), map: map(), busy: false, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }),
    );
    expect(html).toContain('data-testid="atlas-teleport-ashen_waste"');
    expect(html).not.toContain("atlas-teleport-cloud_ridge");
    expect(html).toContain('data-testid="atlas-condition-frost_tide"');
    expect(html).toContain('data-testid="atlas-me"');
    const ashen = by.ashen_waste;
    if (ashen === undefined) throw new Error("缺島");
    expect(html).toContain(`left:${hitPercent(islandHitBox(ashen)).left}`);
    expect(html).not.toContain("atlas-bridges");
  });
});
