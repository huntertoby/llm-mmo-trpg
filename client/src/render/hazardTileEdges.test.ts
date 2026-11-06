// 6V-2b（docs/archive/art/6V-2檢查.md 第 2 節）：致命角標只畫在外圍；灰渡口的深淵畫成深水（`look.chasm_style`）；
// 水面岸邊羽化、荒原水色提亮；雲嶺的 lava（地熱泉）沒有漂移層。只換外觀，致命判定與規則不在這裡。
import { describe, expect, it, vi } from "vitest";
import { Container, Texture } from "pixi.js";
import type { DrawModel, TileDraw } from "../battle/drawModel";
import { fieldLook } from "../world/fieldModel";
import { DEEP_WATER, drawDeepWater, drawWaterFill, featherFill, WATER_FEATHER } from "./hazardTerrainArt";
import { lethalCornerMask, lethalCornersOf, type CornerMask } from "./lethalMarks";
import { chasmStyleOf, waterColorOf } from "./regionArt";
import { LAVA_DRIFT_OFF_REGIONS, terrainAnimated, terrainShimmer, tileShimmer } from "./surfaceAnim";
import { SurfaceAnimator, type SurfaceHost } from "./surfaceAnimLayer";
import { drawTile, type TileArtSpec } from "./terrainArt";

// 測試環境沒有 DOM：動畫小貼圖改用 Pixi 內建的白圖（同 hazardTiles.test）
vi.mock("./statusAnimArt", () => ({
  shimmerTexture: () => ({ texture: Texture.WHITE, w: 46, h: 10, ax: 0.5, ay: 0.5 }),
  animTextureCount: () => 0,
}));

function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}
const calls = (fn: (ctx: CanvasRenderingContext2D) => void): string[] => {
  const m = mockCtx();
  fn(m.ctx);
  return m.calls;
};
const NO = { n: false, s: false, w: false, e: false };
const YES = { n: true, s: true, w: true, e: true };
function spec(over: Partial<TileArtSpec> = {}): TileArtSpec {
  return { region: "", look: "", terrain: "stone", x: 2, y: 3, height: 0, surface: "none", surfSame: NO, lip: NO, wallFace: false, blocked: false, tint: null, ...over };
}

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

const DEEP = "chasm_style=deep_water";
const deepSpec = (over: Partial<TileArtSpec> = {}): TileArtSpec => spec({ terrain: "chasm", region: "ashen_waste", look: DEEP, blocked: true, ...over });

describe("灰渡口的深淵畫成深水（look.chasm_style）", () => {
  it("chasm_style 只認 deep_water；其他值、沒有 → default", () => {
    expect(chasmStyleOf(DEEP)).toBe("deep_water");
    expect(chasmStyleOf("chasm_style=lava_lake")).toBe("default");
    expect(chasmStyleOf("")).toBe("default");
    expect(fieldLook({ chasm_style: "deep_water" })).toEqual({ chasm_style: "deep_water" });
    expect(fieldLook({ chasm_style: "default" })).toEqual({});
  });

  it("荒原 + deep_water 的 chasm 走深水畫法：沒有裂谷的底部紅光、有暗色層；確定性；不同格不同", () => {
    const lip = { n: true, s: false, w: false, e: false };
    const deep = calls((c) => drawTile(c, deepSpec({ lip })));
    expect(deep).toEqual(calls((c) => drawTile(c, deepSpec({ lip }))));
    const own = calls((c) => drawDeepWater(c, deepSpec({ lip })));
    expect(deep.slice(0, own.length)).toEqual(own); // drawTile 的地形層就是 drawDeepWater
    expect(deep.some((x) => x.includes("rgba(255,74,16"))).toBe(false); // 裂谷底部紅光（#ff4a10）不畫
    expect(deep.some((x) => x.includes("rgba(22,33,44"))).toBe(true); // 暗色層（DEEP_WATER.dark）
    expect(calls((c) => drawDeepWater(c, deepSpec({ x: 7, lip: YES })))).not.toEqual(calls((c) => drawDeepWater(c, deepSpec({ lip: YES }))));
  });

  it("其他荒原裂谷照舊（沒有 look 的 chasm 仍有底部紅光）；雲嶺的 chasm 照舊雲海", () => {
    const plain = calls((c) => drawTile(c, deepSpec({ look: "" })));
    expect(plain.some((x) => x.includes("rgba(255,74,16"))).toBe(true);
    const cloud = calls((c) => drawTile(c, deepSpec({ region: "cloud_ridge", look: "" })));
    expect(cloud.some((x) => x.includes("rgba(22,33,44"))).toBe(false);
  });

  it("深水四鄰都是深水時整格水、沒有濕泥岸；有岸的那一側羽化", () => {
    const inner = calls((c) => drawDeepWater(c, deepSpec({ lip: NO })));
    expect(inner.some((x) => x.startsWith(`fillStyle=${DEEP_WATER.bank}`))).toBe(false);
    expect(inner.filter((x) => x.startsWith("createLinearGradient"))).toHaveLength(0);
    const edge = calls((c) => drawDeepWater(c, deepSpec({ lip: { n: false, s: false, w: true, e: false } })));
    expect(edge.some((x) => x.startsWith(`createLinearGradient(0.000,0.000,${WATER_FEATHER.toFixed(3)},0.000)`))).toBe(true);
  });

  it("大波紋：只有深水畫法的 chasm 會動；時間 → 相位確定性；淡入淡出、在格內", () => {
    const theme = { region: "ashen_waste", look: DEEP };
    expect(terrainAnimated("chasm", theme)).toBe(true);
    expect(terrainAnimated("chasm", { region: "ashen_waste", look: "" })).toBe(false);
    expect(terrainShimmer("chasm", 3, 4, 1000)).toEqual([]);
    const a = terrainShimmer("chasm", 3, 4, 1234, theme);
    expect(a).toHaveLength(2);
    expect(a).toEqual(terrainShimmer("chasm", 3, 4, 1234, theme));
    expect(a).not.toEqual(terrainShimmer("chasm", 3, 4, 3234, theme));
    for (let ms = 0; ms < 20000; ms += 250) {
      for (const f of terrainShimmer("chasm", 3, 4, ms, theme)) {
        expect(f.tex).toBe("swell");
        expect(f.y).toBeGreaterThanOrEqual(0.1);
        expect(f.y).toBeLessThanOrEqual(0.9);
        expect(f.alpha).toBeGreaterThanOrEqual(0);
        expect(f.alpha).toBeLessThanOrEqual(0.21);
        if (f.y < 0.15 || f.y > 0.85) expect(f.alpha).toBeLessThan(0.05);
      }
    }
  });

  it("減少動態時靜止：關掉的 SurfaceAnimator 不登記深水；開著時只有深水畫法的 chasm 登記", () => {
    const tiles: TileDraw[] = [];
    for (let i = 0; i < 3; i++) tiles.push({ x: i, y: 0, height: 0, fill: 0, heightLabel: "0", terrain: "chasm", surface: "none", terrainName: "", surfaceName: null, blocked: true, deadly: true, wall: false });
    const model = (look: string): DrawModel => ({ width: 3, height: 1, tiles, objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [], region: "ashen_waste", look });
    const deco = new Container();
    const host: SurfaceHost = { ground: () => new Container(), deco: () => deco, place: () => undefined, oldTile: () => null };
    const off = new SurfaceAnimator();
    off.setEnabled(false);
    off.draw(model(DEEP), host, 1);
    expect(off.stats().shimmers).toBe(0);
    const plain = new SurfaceAnimator();
    plain.draw(model(""), host, 1);
    expect(plain.stats().shimmers).toBe(0); // 一般荒原裂谷不動
    const on = new SurfaceAnimator();
    on.draw(model(DEEP), host, 1);
    expect(on.stats().shimmers).toBe(3);
    on.tick(800);
    on.setEnabled(false);
    expect(deco.children.every((c) => !c.visible)).toBe(true);
  });
});

describe("水面岸邊羽化、荒原水色提亮", () => {
  it("荒原水色 #45627a", () => {
    expect(waterColorOf({ region: "ashen_waste", look: "" }, "#000000")).toBe("#45627a");
  });

  it("單格水（四邊都是岸）：沒有硬邊的濕痕框與水線；每邊漸層淡到透明、四角放射漸層", () => {
    const one = calls((c) => drawWaterFill(c, spec({ surface: "water", surfSame: NO }), "#45627a"));
    expect(one).not.toContain("fillRect(0.000,0.000,52.000,52.000)"); // 6V-2 的整格硬邊濕痕（先鋪整格再蓋水）
    expect(one.filter((x) => x.startsWith("moveTo(4.500") || x.startsWith("moveTo(47.500"))).toHaveLength(0); // 6V-2 的水線
    expect(one.filter((x) => x === "stop(1,rgba(69,98,122,0))" || x === "stop(0,rgba(69,98,122,0))").length).toBe(8); // 4 邊 + 4 角都淡到 0
    expect(one.filter((x) => x.startsWith("createRadialGradient")).length).toBeGreaterThanOrEqual(8); // 濕痕與水各 4 角
  });

  it("featherFill 的各塊不重疊：實心區 + 邊帶 + 角剛好鋪滿整格", () => {
    for (const same of [NO, YES, { n: true, s: false, w: false, e: true }, { n: false, s: true, w: true, e: false }]) {
      const got = calls((c) => featherFill(c, same, 9, "#45627a", 0.86));
      const area = got
        .filter((x) => x.startsWith("fillRect("))
        .map((x) => x.slice(9, -1).split(",").map(Number))
        .reduce((n, [, , w, h]) => n + (w ?? 0) * (h ?? 0), 0);
      expect(area).toBeCloseTo(52 * 52, 3);
    }
  });
});

describe("雲嶺的 lava（地熱泉）沒有漂移層", () => {
  it("雲嶺 lava 不登記動態；其他區域的 lava 照舊漂", () => {
    expect(LAVA_DRIFT_OFF_REGIONS).toEqual(["cloud_ridge"]);
    const cloud = { region: "cloud_ridge", look: "" };
    expect(terrainAnimated("lava", cloud)).toBe(false);
    expect(terrainShimmer("lava", 3, 4, 1234, cloud)).toEqual([]);
    expect(tileShimmer("lava", "none", 3, 4, 1234, cloud)).toEqual([]);
    expect(terrainShimmer("lava", 3, 4, 1234, { region: "ashen_waste", look: "" })).toHaveLength(3);
    expect(terrainShimmer("lava", 3, 4, 1234)).toHaveLength(3);
    const tiles: TileDraw[] = [{ x: 0, y: 0, height: 0, fill: 0, heightLabel: "0", terrain: "lava", surface: "none", terrainName: "", surfaceName: null, blocked: true, deadly: true, wall: false }];
    const host: SurfaceHost = { ground: () => new Container(), deco: () => new Container(), place: () => undefined, oldTile: () => null };
    const anim = new SurfaceAnimator();
    anim.draw({ width: 1, height: 1, tiles, objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [], region: "cloud_ridge", look: "" }, host, 1);
    expect(anim.stats().shimmers).toBe(0);
  });
});
