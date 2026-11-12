// Phase 6F-ART1b：大世界圖第 2 版（光影、岩層、瀑布、雲層、金框字牌、鎖頭徽章）與浮島漂浮。
// 確定性、每島各自快取只平移、漂浮相位錯開與振幅、減少動態與面板關閉時不跑。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AtlasRegionView, AtlasView, WorldMapView } from "../api/types";
import { AtlasMap } from "../world/AtlasMap";
import { atlasScene } from "../world/atlasScene";
import { prefersReducedMotion, shouldAnimate, startFrameLoop, type FrameClock } from "../world/frameLoop";
import { H, hitPercent, W } from "./regionMapArt";
import type { Surface } from "./regionMapPainter";
import { bodyBounds } from "./worldIslandArt";
import { buttonHitBox, islandHitBox, ISLAND_GEO, marksBounds } from "./worldMapArt";
import { AtlasPainter, atlasBaseKey, FLOAT_AMP, floatOffset, floatPeriod, floatPhase, islandOrder, LOCKED_HOVER_FILL, LOCKED_HOVER_LIGHT } from "./worldMapPainter";

function mockCtx(calls: string[] = []): { ctx: CanvasRenderingContext2D; calls: string[] } {
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

interface FakeSurface extends Surface {
  id: number;
  calls: string[];
}

/** 每張離屏圖各自記錄指令；`all` 依建立順序串起來。 */
function recorder(): { make: (w: number, h: number) => Surface; surfaces: FakeSurface[]; all(): string[] } {
  const surfaces: FakeSurface[] = [];
  return {
    surfaces,
    make: (w, h) => {
      const { ctx, calls } = mockCtx();
      const s: FakeSurface = { id: surfaces.length, width: w, height: h, calls, getContext: () => ctx };
      surfaces.push(s);
      return s;
    },
    all: () => surfaces.flatMap((s) => [`#surface ${s.width}x${s.height}`, ...s.calls]),
  };
}

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

function map(): WorldMapView {
  return {
    region: "cloud_ridge",
    name_zh: "雲嶺",
    level_zh: "Lv 1～6",
    hub: false,
    locations: [],
    edges: [],
    stones: [],
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
  };
}

function atlas(over: Partial<AtlasView> = {}): AtlasView {
  return {
    regions: [
      region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", current: true }),
      region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: null }),
      region({ region: "arcane_hub", name_zh: "魔導樞市", status: "later", condition_zh: null }),
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

const scene = atlasScene(atlas(), map()).scene;
const by = Object.fromEntries([scene.capital, ...scene.islands].map((i) => [i.region, i]));
const REGIONS = Object.keys(ISLAND_GEO).sort();

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("第 2 版繪圖", () => {
  it("確定性：不用 Math.random，兩次畫出（含每張離屏圖）完全一樣的指令", () => {
    vi.spyOn(Math, "random").mockImplementation(() => {
      throw new Error("不能用 Math.random");
    });
    const draw = (): string[] => {
      const f = recorder();
      const { ctx, calls } = mockCtx();
      const p = new AtlasPainter(f.make);
      p.paintBase(ctx, scene, W, H);
      p.paintOverlay(ctx, scene, true, W, H, 1, { t: 1234 });
      return [...calls, ...f.all()];
    };
    const a = draw();
    expect(a.length).toBeGreaterThan(5000);
    expect(draw()).toEqual(a);
  });

  it("畫出光影、瀑布、熔岩瀑布、金框字牌、鎖頭徽章與各島名字、條件、傳送鈕", () => {
    const f = recorder();
    const { ctx } = mockCtx();
    const p = new AtlasPainter(f.make);
    p.paintBase(ctx, scene, W, H);
    p.paintOverlay(ctx, scene, true, W, H);
    const all = f.all().join("\n");
    const text = f.all().filter((c) => c.startsWith("fillText("));
    for (const t of ["主城", "雲嶺", "灰燼荒原", "晶冠城邦", "魔導樞市", "霜潮海境", "Lv 1～6", "Lv 5～9", "樞島", "傳送到餘燼集", "傳送到樞島", "你在霧渡鎮", "世界事件：霧潮入侵", "之後的賽季", "大世界"]) {
      expect(text.some((c) => c.startsWith(`fillText(${t},`))).toBe(true);
    }
    expect(text.some((c) => c.includes("傳送到霧渡鎮"))).toBe(false);
    // 太陽光暈、光束（lighter）、金框（#d8b860）、襯線字、瀑布（白）與熔岩瀑布（橘）、未開放去色
    expect(all).toContain("globalCompositeOperation=lighter");
    expect(all).toContain("strokeStyle=#d8b860");
    expect(all).toContain("Noto Serif TC");
    expect(all).toContain("stop(0,rgba(230,245,255,0.95))");
    expect(all).toContain("stop(0,rgba(255,150,60,0.95))");
    expect(all).toContain("filter=grayscale(0.85) brightness(0.92) contrast(0.85)");
    // 鎖頭徽章：每座未開放的島一個（半徑 16 的圓＋12.5 的內圈）
    const locked = scene.islands.filter((i) => i.status !== "open");
    const medals = f.all().filter((c) => /^arc\([\d.]+,[\d.]+,12\.500,/.test(c));
    expect(medals.length).toBe(locked.length + 1); // ＋圖例裡的一個
  });

  it("未開放的航線是一串光點、開放的是木板吊橋；兩者都不跟著島動（在底層與前景）", () => {
    const { ctx, calls } = mockCtx();
    new AtlasPainter(recorder().make).paintBase(ctx, scene, W, H);
    const dots = calls.filter((c) => /^fillRect\([\d.-]+,[\d.-]+,10\.000,10\.000\)$/.test(c));
    expect(dots.length).toBe(15 * scene.islands.filter((i) => i.status !== "open").length);
  });

  it("點擊區照第 2 版版面：傳送鈕在字牌下方置中；字牌放大時點擊區跟著放大", () => {
    const ashen = by.ashen_waste;
    if (ashen === undefined) throw new Error("缺島");
    const b1 = buttonHitBox(ashen);
    const b2 = buttonHitBox(ashen, 1.5);
    if (b1 === null || b2 === null) throw new Error("缺傳送鈕");
    expect(b1.x + b1.w / 2).toBeCloseTo(ashen.geo.x, 6);
    expect(b1.y).toBeGreaterThan(ashen.geo.y + ashen.geo.ry);
    expect(b2.w).toBeCloseTo(b1.w * 1.5, 6);
    expect(b2.y).toBeGreaterThan(b1.y);
    // 傳送鈕在標記離屏圖的範圍裡
    for (const k of [1, 1.5, 2]) {
      const m = marksBounds(ashen, k);
      const b = buttonHitBox(ashen, k);
      if (b === null) throw new Error("缺傳送鈕");
      expect(b.x).toBeGreaterThanOrEqual(m.x);
      expect(b.x + b.w).toBeLessThanOrEqual(m.x + m.w);
      expect(b.y + b.h).toBeLessThanOrEqual(m.y + m.h);
    }
  });

  it("每座島的離屏圖範圍包得住它畫的所有路徑點（本體與標記）", () => {
    const pts = (calls: string[]): [number, number][] =>
      calls
        .filter((c) => /^(moveTo|lineTo)\(/.test(c))
        .map((c) => c.slice(c.indexOf("(") + 1, -1).split(",").map(Number) as [number, number]);
    for (const is of islandOrder(scene)) {
      const f = recorder();
      const p = new AtlasPainter(f.make);
      p.paintOverlay(mockCtx().ctx, { capital: is, islands: [] }, true, W, H);
      // 建立順序：前景、外框、（暫存）、本體、標記；用尺寸找本體與標記
      const body = bodyBounds(is.geo);
      const marks = marksBounds(is);
      const bodySurf = f.surfaces.find((s) => s.width === Math.ceil(body.w) && s.height === Math.ceil(body.h) && s.calls.length > 50);
      const markSurf = f.surfaces.find((s) => s.width === Math.ceil(marks.w) && s.height === Math.ceil(marks.h));
      if (bodySurf === undefined || markSurf === undefined) throw new Error(`找不到 ${is.region} 的離屏圖`);
      for (const [box, surf] of [[body, bodySurf], [marks, markSurf]] as const) {
        for (const [x, y] of pts(surf.calls)) {
          expect(x).toBeGreaterThanOrEqual(box.x);
          expect(x).toBeLessThanOrEqual(box.x + box.w);
          expect(y).toBeGreaterThanOrEqual(box.y);
          expect(y).toBeLessThanOrEqual(box.y + box.h);
        }
      }
    }
  });
});

describe("浮島漂浮", () => {
  it("振幅 ±3px、週期 5～6 秒", () => {
    for (const r of REGIONS) {
      const period = floatPeriod(r);
      expect(period).toBeGreaterThanOrEqual(5000);
      expect(period).toBeLessThanOrEqual(6000);
      let max = 0;
      for (let t = 0; t < 12000; t += 37) {
        const o = floatOffset(r, t);
        expect(Math.abs(o)).toBeLessThanOrEqual(FLOAT_AMP + 1e-9);
        max = Math.max(max, Math.abs(o));
      }
      expect(max).toBeGreaterThan(2.9);
      // 一個週期後回到原位
      expect(floatOffset(r, 777 + period)).toBeCloseTo(floatOffset(r, 777), 9);
    }
    expect(floatOffset("cloud_ridge", null)).toBe(0);
  });

  it("各島相位錯開（依區域 ID 雜湊，確定性）", () => {
    const phases = REGIONS.map(floatPhase);
    expect(new Set(phases.map((p) => p.toFixed(3))).size).toBe(REGIONS.length);
    expect(REGIONS.map(floatPhase)).toEqual(phases);
    // 同一時刻各島位移不全相同
    expect(new Set(REGIONS.map((r) => floatOffset(r, 0).toFixed(2))).size).toBeGreaterThan(3);
  });

  it("每座島各自快取：逐格只貼圖平移、不重畫；天空、前景、外框不動", () => {
    const f = recorder();
    const p = new AtlasPainter(f.make);
    const { ctx, calls } = mockCtx();
    p.paintOverlay(ctx, scene, true, W, H, 1, { t: 0 });
    const made = f.surfaces.length;
    const before = { ...p.stats };
    const frames: string[][] = [];
    for (const t of [500, 1700, 2900, 4100]) {
      calls.length = 0;
      p.paintOverlay(ctx, scene, true, W, H, 1, { t });
      frames.push([...calls]);
    }
    expect(f.surfaces.length).toBe(made);
    expect(p.stats).toEqual({ ...before, frame: before.frame + 4 });
    const n = islandOrder(scene).length;
    for (const fr of frames) {
      // 只有清畫布與貼圖：本體 n 張、前景 1、標記 n 張、外框 1
      expect(fr.filter((c) => !c.startsWith("setTransform(") && !c.startsWith("clearRect("))).toEqual(fr.filter((c) => c.startsWith("drawImage(")));
      expect(fr.filter((c) => c.startsWith("drawImage(")).length).toBe(2 * n + 2);
    }
    // 島的 x 不變、y 照 floatOffset 平移；前景與外框貼在 (0,0)
    const ys = (fr: string[]): number[] => fr.filter((c) => c.startsWith("drawImage(")).map((c) => Number(c.split(",")[2]?.replace(")", "")));
    const xs = (fr: string[]): number[] => fr.filter((c) => c.startsWith("drawImage(")).map((c) => Number(c.split(",")[1]));
    const [f0, f1] = frames as [string[], string[]];
    expect(xs(f0)).toEqual(xs(f1));
    const order = islandOrder(scene);
    order.forEach((is, i) => {
      const d = (ys(f1)[i] ?? 0) - (ys(f0)[i] ?? 0);
      expect(d).toBeCloseTo(floatOffset(is.region, 1700) - floatOffset(is.region, 500), 2);
      // 標記和本體一起動
      const dm = (ys(f1)[n + 1 + i] ?? 0) - (ys(f0)[n + 1 + i] ?? 0);
      expect(dm).toBeCloseTo(d, 2);
    });
    expect(ys(f0)[n]).toBe(0);
    expect(ys(f0)[2 * n + 1]).toBe(0);
  });

  it("狀態變了只重畫有變的：can_teleport 變了本體不重畫、只重畫標記與標題", () => {
    const p = new AtlasPainter(recorder().make);
    const { ctx } = mockCtx();
    p.paintOverlay(ctx, scene, true, W, H);
    const s1 = { ...p.stats };
    expect(s1.body).toBe(islandOrder(scene).length);
    const off = atlasScene(atlas({ can_teleport: false, capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島" }) }), map()).scene;
    p.paintOverlay(ctx, off, false, W, H);
    expect(p.stats.body).toBe(s1.body);
    expect(p.stats.marks).toBe(s1.marks + 1);
    expect(p.stats.chrome).toBe(s1.chrome + 1);
    expect(p.stats.front).toBe(s1.front);
  });

  it("天空照尺寸快取；底層鍵含各島狀態", () => {
    const p = new AtlasPainter(recorder().make);
    const { ctx } = mockCtx();
    p.paintBase(ctx, scene, 1280, 860);
    p.paintBase(ctx, scene, 1280, 860);
    expect(p.stats.sky).toBe(1);
    p.paintBase(ctx, scene, 640, 430);
    expect(p.stats.sky).toBe(2);
    const other = atlasScene(atlas({ regions: atlas().regions.map((r) => (r.region === "frost_tide" ? { ...r, status: "open" as const } : r)) }), map()).scene;
    expect(atlasBaseKey(other, 1280, 860)).not.toBe(atlasBaseKey(scene, 1280, 860));
  });

  it("點擊區不跟著漂浮：畫面的點擊區沒有動畫或位移", () => {
    const html = renderToStaticMarkup(
      createElement(AtlasMap, { atlas: atlas(), map: map(), busy: false, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }),
    );
    const ashen = by.ashen_waste;
    if (ashen === undefined) throw new Error("缺島");
    expect(html).toContain(`top:${hitPercent(islandHitBox(ashen)).top}`);
    expect(html).not.toMatch(/transform|animation/);
  });
});

describe("動畫迴圈", () => {
  function fakeClock(): FrameClock & { pending: Map<number, (t: number) => void>; step(t: number): void; cancelled: number[] } {
    const pending = new Map<number, (t: number) => void>();
    const cancelled: number[] = [];
    let next = 1;
    return {
      pending,
      cancelled,
      request(cb) {
        pending.set(next, cb);
        return next++;
      },
      cancel(id) {
        cancelled.push(id);
        pending.delete(id);
      },
      step(t) {
        const cbs = [...pending.values()];
        pending.clear();
        cbs.forEach((cb) => cb(t));
      },
    };
  }

  it("逐格呼叫；停止（面板關掉＝元件卸載）後取消 requestAnimationFrame、不再畫", () => {
    const clock = fakeClock();
    const seen: number[] = [];
    const stop = startFrameLoop((t) => seen.push(t), clock);
    clock.step(16);
    clock.step(33);
    expect(seen).toEqual([16, 33]);
    stop();
    expect(clock.pending.size).toBe(0);
    expect(clock.cancelled.length).toBe(1);
    clock.step(50);
    expect(seen).toEqual([16, 33]);
  });

  it("prefers-reduced-motion、畫布沒尺寸、畫法不要動畫時不跑", () => {
    expect(shouldAnimate(true, false, 1280, 860)).toBe(true);
    expect(shouldAnimate(true, true, 1280, 860)).toBe(false);
    expect(shouldAnimate(true, false, 0, 0)).toBe(false);
    expect(shouldAnimate(false, false, 1280, 860)).toBe(false);
  });

  it("讀得到 prefers-reduced-motion（沒有 window 時當作沒開）", () => {
    expect(prefersReducedMotion()).toBe(false);
    vi.stubGlobal("window", { matchMedia: (q: string) => ({ matches: q === "(prefers-reduced-motion: reduce)" }) });
    expect(prefersReducedMotion()).toBe(true);
  });
});

describe("FIX-ATLAS2：鎖住浮島滑過只讓本體稍亮", () => {
  /** 畫一格（t＝1234），回傳主畫布的指令與這一格新做的離屏圖。 */
  function frame(hoverLocked: string | null | undefined): { calls: string[]; made: FakeSurface[]; p: AtlasPainter; f: ReturnType<typeof recorder> } {
    const f = recorder();
    const p = new AtlasPainter(f.make);
    const { ctx, calls } = mockCtx();
    p.paintOverlay(ctx, scene, true, W, H, 1, { t: 1234 });
    const before = f.surfaces.length;
    calls.length = 0;
    p.paintOverlay(ctx, scene, true, W, H, 1, { t: 1234, hoverLocked });
    return { calls: [...calls], made: f.surfaces.slice(before), p, f };
  }

  it("亮度參數：16% 白色、只疊在島的像素上（source-atop）", () => {
    expect(LOCKED_HOVER_LIGHT).toBe(0.16);
    const { made } = frame("frost_tide");
    expect(made).toHaveLength(1);
    const lit = made[0]!;
    expect(lit.calls[0]).toMatch(/^drawImage\(object,0\.000,0\.000\)$/);
    expect(lit.calls).toContain("globalCompositeOperation=source-atop");
    expect(lit.calls).toContain(`fillStyle=${LOCKED_HOVER_FILL}`);
    expect(LOCKED_HOVER_FILL).toBe(`rgba(255,255,255,${LOCKED_HOVER_LIGHT})`);
    expect(lit.calls).toContain(`fillRect(0.000,0.000,${lit.width.toFixed(3)},${lit.height.toFixed(3)})`);
    // 沒有光暈、陰影、濾鏡、放大
    expect(lit.calls.filter((c) => /^(shadow|filter|scale\(|setTransform\(|arc\(|create(Radial|Linear)Gradient)/.test(c))).toEqual([]);
    const body = bodyBounds(by.frost_tide!.geo);
    expect([lit.width, lit.height]).toEqual([Math.ceil(body.w), Math.ceil(body.h)]);
  });

  it("鎖住／之後的賽季的島：同一位置、同一張數的貼圖，只有那座島換成稍亮那張；沒有放大、沒有多畫東西", () => {
    const plain = frame(null).calls;
    for (const r of ["frost_tide", "crystal_crown"]) {
      const { calls, made, p } = frame(r);
      expect(calls).toHaveLength(plain.length);
      const diff = calls.map((c, i) => [c, plain[i]] as const).filter(([a, b]) => a !== b);
      expect(diff).toEqual([]); // 指令字串一樣（貼圖物件不同但都記成 object、位置與大小相同）
      expect(made).toHaveLength(1);
      expect(p.stats.body).toBe(islandOrder(scene).length); // 本體沒有重畫
    }
  });

  it("開放的島（雲嶺、主城）傳進來也不變：不做稍亮那張", () => {
    for (const r of ["cloud_ridge", "capital", "nowhere"]) expect(frame(r).made).toEqual([]);
    expect(frame(undefined).made).toEqual([]);
  });

  it("稍亮那張照本體快取：連續滑過同一座島不重做", () => {
    const f = recorder();
    const p = new AtlasPainter(f.make);
    const { ctx } = mockCtx();
    p.paintOverlay(ctx, scene, true, W, H, 1, { t: 0, hoverLocked: "frost_tide" });
    const n = f.surfaces.length;
    for (const t of [100, 200, 300]) p.paintOverlay(ctx, scene, true, W, H, 1, { t, hoverLocked: "frost_tide" });
    expect(f.surfaces.length).toBe(n);
  });
});
