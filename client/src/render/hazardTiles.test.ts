// 6V-2 致命與水面地形外觀：四種格子的畫法（雲海、熔岩、致命標記、水面）都是確定性的；減少動態時熔岩靜止；
// 來源不新增 Math.random。致命判定與路徑預覽的規則不在這裡（既有測試不動）。
import { describe, expect, it, vi } from "vitest";
import type { DrawModel, TileDraw } from "../battle/drawModel";
import { EMPTY_PATH_DRAW } from "../battle/pathPreview";
import { cloudNeighbors, drawCloudSea, drawLavaBase, drawWaterFill, WATER_SHORE } from "./hazardTerrainArt";
import { LETHAL_CORNER, LETHAL_CORNER_INSET, lethalCornerPaths, lethalTintCells } from "./lethalMarks";
import { waterColorOf, WATER_BY_REGION } from "./regionArt";
import { ANIMATED_TERRAINS, SHIMMER, surfaceShimmer, terrainShimmer, tileShimmer } from "./surfaceAnim";
import { SurfaceAnimator, type SurfaceHost } from "./surfaceAnimLayer";
import { drawTile, type TileArtSpec } from "./terrainArt";
import { Container, Texture } from "pixi.js";

// 沒有 @types/node：用變數名載入 node:fs（vitest 在 node 環境執行；來源掃描用）
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

// 測試環境沒有 DOM：動畫小貼圖改用 Pixi 內建的白圖，才看得到 SurfaceAnimator 有沒有登記熔岩的動態
vi.mock("./statusAnimArt", () => ({
  shimmerTexture: () => ({ texture: Texture.WHITE, w: 20, h: 14, ax: 0.5, ay: 0.5 }),
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

const NO = { n: false, s: false, w: false, e: false };
function spec(over: Partial<TileArtSpec> = {}): TileArtSpec {
  return { region: "", look: "", terrain: "stone", x: 2, y: 3, height: 0, surface: "none", surfSame: NO, lip: NO, wallFace: false, blocked: false, tint: null, ...over };
}
function calls(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  const m = mockCtx();
  fn(m.ctx);
  return m.calls;
}

describe("雲海／深淵（chasm）", () => {
  it("同一格畫兩次一樣；不同格不一樣（只看格子座標雜湊）", () => {
    const a = calls((c) => drawCloudSea(c, spec({ terrain: "chasm" }), 5));
    const b = calls((c) => drawCloudSea(c, spec({ terrain: "chasm" }), 5));
    const other = calls((c) => drawCloudSea(c, spec({ terrain: "chasm", x: 9 }), 5));
    expect(a).toEqual(b);
    expect(a).not.toEqual(other);
  });

  it("白雲團鋪滿格子：底下淡藍、至少 5 團有羽化邊（半徑 1 處透明）的雲；鄰格也是雲海時連鄰格的雲團一起畫", () => {
    const alone = calls((c) => drawCloudSea(c, spec({ terrain: "chasm", lip: { n: true, s: true, w: true, e: true } }), 5));
    expect(alone[0]).toMatch(/^createLinearGradient/);
    expect(alone.filter((x) => x.startsWith("stop(1,rgba(168,182,210,0)")).length).toBeGreaterThanOrEqual(5);
    const joined = calls((c) => drawCloudSea(c, spec({ terrain: "chasm" }), 5));
    expect(joined.filter((x) => x.startsWith("stop(1,rgba(168,182,210,0)")).length).toBeGreaterThan(alone.filter((x) => x.startsWith("stop(1,rgba(168,182,210,0)")).length);
    expect(cloudNeighbors(spec({ lip: NO }))).toHaveLength(8);
    expect(cloudNeighbors(spec({ lip: { n: true, s: false, w: false, e: false } }))).toEqual([[-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]]);
  });

  it("預設與雲嶺的 chasm 都走雲海畫法；崖緣（lip）仍有（預設灰紫崖唇、雲嶺青石崖線）", () => {
    for (const [region, lipColor] of [["", "fillStyle=#3b3742"], ["cloud_ridge", "fillStyle=#56645c"], ["crystal_crown", "fillStyle=#3b3742"]] as const) {
      const flat = calls((c) => drawTile(c, spec({ terrain: "chasm", region, blocked: true })));
      expect(flat.some((x) => x.startsWith("stop(0,rgba(250,250,253"))).toBe(true);
      const lipped = calls((c) => drawTile(c, spec({ terrain: "chasm", region, blocked: true, lip: { n: true, s: false, w: false, e: false } })));
      expect(lipped).toContain(lipColor);
      expect(lipped).not.toEqual(flat);
    }
  });
});

describe("熔岩（lava）", () => {
  it("底圖確定性：同格同圖；發光、熱紋、岩殼都有；靠岸那邊多一圈冷卻黑殼", () => {
    const a = calls((c) => drawLavaBase(c, spec({ terrain: "lava" }), 6));
    expect(a).toEqual(calls((c) => drawLavaBase(c, spec({ terrain: "lava" }), 6)));
    expect(a).toContain("stop(0,rgba(255,122,26,0.9))");
    expect(a).toContain("strokeStyle=rgba(255,211,107,0.8)");
    expect(a.filter((x) => x === "closePath()").length).toBeGreaterThanOrEqual(2);
    const shore = calls((c) => drawLavaBase(c, spec({ terrain: "lava", lip: { n: true, s: false, w: true, e: false } }), 6));
    expect(shore.filter((x) => x === "fillStyle=#2a1610").length).toBe(2);
    expect(shore.length).toBeGreaterThan(a.length);
  });

  it("預設與荒原的 lava 都是這套畫法（荒原底色略暗）", () => {
    const base = calls((c) => drawTile(c, spec({ terrain: "lava", blocked: true })));
    const ash = calls((c) => drawTile(c, spec({ terrain: "lava", blocked: true, region: "ashen_waste" })));
    expect(base).toContain("stop(0,rgba(255,122,26,0.9))");
    expect(ash).toContain("stop(0,rgba(255,122,26,0.9))");
    expect(base[0]).not.toEqual(ash[0]);
  });

  it("岩殼漂移：時間 → 相位，確定性；慢（一格 ≥ 8 秒）；漂到格緣前淡出；岩殼用 normal 混色、熱光用 add", () => {
    expect(ANIMATED_TERRAINS).toEqual(["lava", "chasm"]); // 6V-2b：chasm 只在深水畫法時動（terrainAnimated）
    expect(SHIMMER.lavaDriftMs).toBeGreaterThanOrEqual(8000);
    const t0 = terrainShimmer("lava", 3, 4, 1234);
    expect(t0).toEqual(terrainShimmer("lava", 3, 4, 1234));
    expect(t0).not.toEqual(terrainShimmer("lava", 3, 4, 1234 + 2000));
    expect(t0).not.toEqual(terrainShimmer("lava", 5, 4, 1234));
    expect(t0).toHaveLength(3);
    expect(t0.filter((f) => f.tex === "crust").every((f) => f.blend === "normal")).toBe(true);
    expect(t0.find((f) => f.tex === "ember")?.blend).toBeUndefined();
    for (let ms = 0; ms < SHIMMER.lavaDriftMs * 2; ms += 250) {
      for (const f of terrainShimmer("lava", 3, 4, ms)) {
        expect(f.x).toBeGreaterThanOrEqual(0.05);
        expect(f.x).toBeLessThanOrEqual(0.95);
        expect(f.y).toBeGreaterThanOrEqual(0.05);
        expect(f.y).toBeLessThanOrEqual(0.95);
        expect(f.alpha).toBeGreaterThanOrEqual(0);
        expect(f.alpha).toBeLessThanOrEqual(1);
      }
    }
    // 漂到端點時幾乎透明（不會在格緣突然消失）
    const ends = [];
    for (let ms = 0; ms < SHIMMER.lavaDriftMs; ms += 50) {
      const f = terrainShimmer("lava", 3, 4, ms)[0]!;
      if (f.x < 0.12 || f.x > 0.88 || f.y < 0.12 || f.y > 0.88) ends.push(f.alpha);
    }
    expect(ends.length).toBeGreaterThan(0);
    expect(Math.max(...ends)).toBeLessThan(0.25);
    expect(terrainShimmer("stone", 3, 4, 0)).toEqual([]);
    expect(tileShimmer("lava", "water", 3, 4, 0)).toEqual([...surfaceShimmer("water", 3, 4, 0), ...terrainShimmer("lava", 3, 4, 0)]);
  });

  it("減少動態時靜止：關掉的 SurfaceAnimator 不登記熔岩的動態；開著時每格一個節點", () => {
    const tiles: TileDraw[] = [];
    for (let i = 0; i < 4; i++) tiles.push({ x: i, y: 0, height: 0, fill: 0, heightLabel: "0", terrain: "lava", surface: "none", terrainName: "", surfaceName: null, blocked: true, deadly: true, wall: false });
    const model: DrawModel = { width: 4, height: 1, tiles, objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [], region: "", look: "" };
    const ground = new Container();
    const deco = new Container();
    const host: SurfaceHost = { ground: () => ground, deco: () => deco, place: () => undefined, oldTile: () => null };
    const off = new SurfaceAnimator();
    off.setEnabled(false);
    off.draw(model, host, 1);
    expect(off.stats().shimmers).toBe(0);
    expect(deco.children).toHaveLength(0);
    const on = new SurfaceAnimator();
    on.draw(model, host, 1);
    expect(on.stats().shimmers).toBe(4);
    on.tick(500);
    on.setEnabled(false);
    expect(deco.children.every((c) => !c.visible)).toBe(true);
  });
});

describe("致命標記", () => {
  it("四角角標：四條折線、每條 6px、縮 2px；不是整格 X", () => {
    const paths = lethalCornerPaths(48);
    expect(paths).toHaveLength(4);
    expect(LETHAL_CORNER).toBe(6);
    expect(LETHAL_CORNER_INSET).toBe(2);
    expect(paths[0]).toEqual([2, 8, 2, 2, 8, 2]);
    expect(paths[2]).toEqual([46, 40, 46, 46, 40, 46]);
    for (const [x0, y0, x1, y1, x2, y2] of paths) {
      expect(Math.abs(x1 - x0) + Math.abs(y1 - y0)).toBe(6);
      expect(Math.abs(x2 - x1) + Math.abs(y2 - y1)).toBe(6);
    }
  });

  it("淡紅只疊在致命格：滑過、路徑經過與停點、預覽範圍、可選目標、已選格；去重、排序", () => {
    const tile = (x: number, y: number, deadly: boolean): TileDraw => ({ x, y, height: 0, fill: 0, heightLabel: "0", terrain: deadly ? "chasm" : "stone", surface: "none", terrainName: "", surfaceName: null, blocked: deadly, deadly, wall: false });
    const tiles = [tile(0, 0, false), tile(1, 0, true), tile(2, 0, true), tile(0, 1, true), tile(1, 1, false), tile(2, 1, true)];
    const model: DrawModel = { width: 3, height: 2, tiles, objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [], region: "", look: "" };
    const none = lethalTintCells(model, { hover: { x: 0, y: 0 }, preview: [{ x: 1, y: 1 }], attacks: [], picked: [] });
    expect(none).toEqual([]);
    const path = { ...EMPTY_PATH_DRAW, dots: [{ pos: { x: 2, y: 1 }, kind: "normal" as const }], segments: [{ from: { x: 0, y: 0 }, to: { x: 1, y: 0 }, kind: "normal" as const, possible: true, dashed: false }] };
    const got = lethalTintCells(model, { hover: { x: 2, y: 0 }, path, preview: [{ x: 0, y: 1 }, { x: 2, y: 0 }], attacks: [{ x: 9, y: 9 }], picked: [] });
    expect(got).toEqual([{ x: 1, y: 0 }, { x: 2, y: 0 }, { x: 0, y: 1 }, { x: 2, y: 1 }]);
  });
});

describe("水面（water）", () => {
  it("水色依區域：雲嶺清藍、荒原深灰藍、主城晶藍；look.water_tint 優先；其他區域用預設", () => {
    expect(Object.keys(WATER_BY_REGION).sort()).toEqual(["ashen_waste", "capital", "cloud_ridge"]);
    expect(waterColorOf({ region: "cloud_ridge", look: "" }, "#000000")).toBe("#3f93d6");
    expect(waterColorOf({ region: "ashen_waste", look: "" }, "#000000")).toBe("#45627a"); // 6V-2b 提亮
    expect(waterColorOf({ region: "capital", look: "" }, "#000000")).toBe("#4aa6e4");
    expect(waterColorOf({ region: "frost_tide", look: "" }, "#123456")).toBe("#123456");
    expect(waterColorOf({ region: "cloud_ridge", look: "water_tint=green" }, "#000000")).toBe("#4f9a62");
    expect(waterColorOf({ region: "", look: "constructor=x" }, "#123456")).toBe("#123456");
  });

  it("填滿格子：四鄰都是水時整格；岸邊留一圈濕痕（6V-2b 起羽化，見 hazardTileEdges.test）；確定性", () => {
    const full = calls((c) => drawWaterFill(c, spec({ surface: "water", surfSame: { n: true, s: true, w: true, e: true } }), "#3a86d8"));
    expect(full).toContain("fillRect(0.000,0.000,52.000,52.000)");
    expect(full.filter((x) => x === "fillRect(0.000,0.000,52.000,52.000)").length).toBeGreaterThanOrEqual(2);
    expect(full.filter((x) => x.startsWith("moveTo(0.500") || x.startsWith("moveTo(51.500"))).toHaveLength(0);
    const shore = calls((c) => drawWaterFill(c, spec({ surface: "water", surfSame: { n: false, s: true, w: false, e: true } }), "#3a86d8"));
    expect(WATER_SHORE).toBe(4);
    expect(shore.some((x) => x.startsWith("createLinearGradient(0.000,0.000,0.000,"))).toBe(true); // 北岸的羽化漸層
    expect(shore).toEqual(calls((c) => drawWaterFill(c, spec({ surface: "water", surfSame: { n: false, s: true, w: false, e: true } }), "#3a86d8")));
  });

  it("drawTile 的水面不再走併塊：沒有 clip、反光線只有 1px", () => {
    const got = calls((c) => drawTile(c, spec({ surface: "water", region: "capital" })));
    expect(got).toContain("fillStyle=rgba(74,166,228,0.86)");
    expect(got.filter((x) => x === "clip()")).toHaveLength(0);
    expect(got).toContain("strokeStyle=rgba(235,248,255,0.55)");
  });
});

describe("來源掃描", () => {
  it("6V-2 動到的檔案沒有 Math.random", () => {
    for (const f of ["hazardTerrainArt.ts", "lethalMarks.ts", "terrainArt.ts", "surfaceAnim.ts", "surfaceAnimLayer.ts", "statusAnimArt.ts", "cloudRidgeTerrain.ts", "ashenTerrain.ts", "regionArt.ts", "BattleRenderer.ts"]) {
      const src = readFileSync(`src/render/${f}`, "utf-8")
        .split("\n")
        .map((line: string) => line.replace(/\/\/.*/, "")) // 註解裡提到「不用 Math.random」不算（CRLF 的 \r 也一起拿掉）
        .join("\n");
      expect(src.includes("Math.random("), f).toBe(false);
    }
  });
});
