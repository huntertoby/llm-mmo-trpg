// OCL-1a：被遮擋剪影外框（`docs/phases/PhaseOCL-1計畫.md`「行為一致測試」第 1～10、13 項）。
// 遮罩一律用合成的 alpha 陣列（不靠真畫布）；繪製器層用 `OcclusionLayer` 的子類別、合成的身體來源與假的外框貼圖。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { DrawModel, UnitDraw } from "../battle/drawModel";
import { RING } from "./artPalette";
import { ArtTextures, figureResolution } from "./artTextures";
import {
  ALPHA_MIN,
  alphaOf,
  BIG_FRONT_AREA,
  binaryMask,
  clipMask,
  composeOutline,
  coverRatio,
  flashAlpha,
  flashTint,
  maskArea,
  modelMask,
  OUTLINE_ALPHA,
  OUTLINE_CSS_PX,
  OUTLINE_INK,
  outlineBand,
  outlineWanted,
  outlineWidthTex,
  type AlphaImage,
} from "./occludeOutline";
import { legacySilhouetteWanted, outlineColor, outlineTexture, planOcclusion, type OclSource, type OclUnit } from "./battle/outlineLayer";
import { OcclusionLayer, OUTLINE_LABEL } from "./battle/occlusionLayer";
import type { BareBody } from "./unitSprite";
import { FEET } from "./unitSprite";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";

const sha256 = async (b: Uint8ClampedArray): Promise<string> => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new Uint8Array(b)))].map((x) => x.toString(16).padStart(2, "0")).join("");

// ---- 合成的身體 ----
/** w×h 的 alpha 圖，`fill(x, y)` 為真的像素 255。 */
function image(w: number, h: number, fill: (x: number, y: number) => boolean, a = 255): AlphaImage {
  const alpha = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (fill(x, y)) alpha[y * w + x] = a;
  return { w, h, alpha };
}
const rect = (w: number, h: number): AlphaImage => image(w, h, () => true);

/** 身體：k ＝ 1、box ＝ 圖的大小、腳底在下緣（貼圖 1 像素 ＝ 1 模型像素，左上角 ＝ 腳底 − (w/2, h)）。 */
function body(key: string, img: AlphaImage): BareBody {
  return { key, box: { w: img.w, h: img.h, foot: img.h }, k: 1, display: 1, draw: () => null };
}
function draw(id: string, x: number, y: number, over: Partial<UnitDraw> = {}): UnitDraw {
  return { id, x, y, team: "ally", summon: false, downed: false, statusIds: [], ...over } as unknown as UnitDraw;
}
/** 單位：格子 (x, y)、腳底在 (x*48 + 24, y*48 + 24 + FEET)；`dx`、`dy` 另外位移（模型像素）。 */
function placed(id: string, img: AlphaImage, x: number, y: number, order: number, over: Partial<UnitDraw> = {}, dx = 0, dy = 0): OclUnit {
  return { id, u: draw(id, x, y, over), order, feet: { x: x * 48 + 24 + dx, y: y * 48 + 24 + FEET + dy }, body: body(`k:${id}`, img) };
}
/** 來源：照身體鍵查合成的圖；記錄每次呼叫的鍵。 */
function source(units: readonly OclUnit[]): OclSource & { calls: string[] } {
  const byKey = new Map(units.map((u) => [u.body.key, u]));
  const calls: string[] = [];
  const imgOf = (b: BareBody): AlphaImage | null => {
    const u = byKey.get(b.key);
    return u === undefined ? null : (u as OclUnit & { img?: AlphaImage }).img ?? null;
  };
  return {
    calls,
    maskImage: (b) => {
      calls.push(`mask:${b.key}`);
      return imgOf(b);
    },
    texImage: (b) => {
      calls.push(`tex:${b.key}`);
      const img = imgOf(b);
      return img === null ? null : { key: b.key, img };
    },
  };
}
const withImg = (u: OclUnit, img: AlphaImage): OclUnit => Object.assign(u, { img });
const unitOf = (id: string, img: AlphaImage, x: number, y: number, order: number, over: Partial<UnitDraw> = {}, dx = 0, dy = 0) => withImg(placed(id, img, x, y, order, over, dx, dy), img);

/** 大型前排：100×60（面積 6000）。被擋者 20×30，腳底往上 FEET + 48 的地方就在前排身上。 */
const BIG = rect(100, 60);
const SMALL = rect(20, 30);

describe("OCL-1a 第 1 項：遮罩與面積", () => {
  it("alpha 127 不算、128 算", () => {
    const rgba = new Uint8ClampedArray([0, 0, 0, 127, 0, 0, 0, 128, 0, 0, 0, 255, 0, 0, 0, 0]);
    const img = alphaOf(rgba, 4, 1);
    expect([...binaryMask(img)]).toEqual([0, 1, 1, 0]);
    expect(maskArea(binaryMask(img))).toBe(2);
    expect(ALPHA_MIN).toBe(128);
  });

  it("同一個鍵取兩次只呼叫一次 getImageData（假畫布計數）", () => {
    const art = new ArtTextures();
    let reads = 0;
    let made = 0;
    const make = () => {
      made += 1;
      const ctx = { getImageData: (_x: number, _y: number, w: number, h: number) => { reads += 1; return { data: new Uint8ClampedArray(w * h * 4).fill(200) }; } };
      return { width: 3, height: 2, getContext: () => ctx } as unknown as HTMLCanvasElement;
    };
    const a = art.alphaMask("om|1|x", make);
    const b = art.alphaMask("om|1|x", make);
    expect(a).not.toBeNull();
    expect(b).toBe(a);
    expect(reads).toBe(1);
    expect(made).toBe(1);
    expect(art.alphaReads).toBe(1);
    art.alphaMask("om|1|y", make);
    expect(reads).toBe(2);
    expect(art.alphaMaskCount).toBe(2);
  });

  it("模型像素遮罩：1 貼圖像素 ＝ 1 模型像素時面積 ＝ 像素數；2 倍解析度時面積照模型像素算", () => {
    expect(modelMask(rect(20, 30), { left: 10, top: 5, sx: 1, sy: 1 }).area).toBe(600);
    expect(modelMask(rect(40, 60), { left: 10, top: 5, sx: 0.5, sy: 0.5 }).area).toBe(600);
  });
});

describe("OCL-1a 第 2 項：大型前排", () => {
  const run = (frontImg: AlphaImage, over: Partial<UnitDraw> = {}) => {
    const back = unitOf("b", SMALL, 2, 1, 0);
    const front = unitOf("f", frontImg, 2, 2, 1, over, 0, -40);
    return planOcclusion([back, front], new Map(), source([back, front])).get("b")!;
  };
  it("面積 3999 不算、4000 算", () => {
    const a4000 = image(80, 50, () => true);
    const a3999 = image(80, 50, (x, y) => !(x === 0 && y === 0));
    expect(modelMask(a4000, { left: 0, top: 0, sx: 1, sy: 1 }).area).toBe(4000);
    expect(BIG_FRONT_AREA).toBe(4000);
    expect(run(a4000).drawn).toBe(true);
    const r = run(a3999);
    expect(r.drawn).toBe(false);
    expect(r.skip).toBe("nobig");
  });
  it("倒下的大型前排不算（Q8）", () => {
    expect(run(BIG).drawn).toBe(true);
    expect(run(BIG, { downed: true }).drawn).toBe(false);
  });
  it("隱匿中的大型前排照算（Q8）", () => {
    expect(run(BIG, { statusIds: ["concealed"] }).drawn).toBe(true);
  });
  it("只看南邊 0～3 排、畫在它之後的", () => {
    const back = unitOf("b", SMALL, 2, 1, 1);
    const north = unitOf("n", BIG, 2, 1, 0, {}, 0, 0); // 同一排、先畫（同一排的頭目一定先畫）
    expect(planOcclusion([back, north], new Map(), source([back, north])).get("b")!.drawn).toBe(false);
    const far = unitOf("f", BIG, 2, 5, 2, {}, 0, -4 * 48);
    expect(planOcclusion([back, far], new Map(), source([back, far])).get("b")!.skip).toBe("nobig");
  });
});

describe("OCL-1a 第 3 項：比例", () => {
  const M = rect(60, 60);
  it("60×60 被擋 33 列 ＝ 55%：比例逐筆相等", () => {
    const m = modelMask(M, { left: 0, top: 0, sx: 1, sy: 1 });
    const o = modelMask(rect(60, 33), { left: 0, top: 27, sx: 1, sy: 1 });
    expect(coverRatio(m, [o])).toEqual({ n: 3600, hit: 1980, ratio: 0.55 });
    const o2 = modelMask(rect(60, 32), { left: 0, top: 28, sx: 1, sy: 1 });
    expect(coverRatio(m, [o2]).ratio).toBeCloseTo(32 / 60, 12);
    // 聯集：兩個前排重疊的部分只算一次
    const half = modelMask(rect(30, 60), { left: 0, top: 0, sx: 1, sy: 1 });
    expect(coverRatio(m, [half, o]).hit).toBe(1800 + 30 * 33);
  });
  it("原點小數位置照 floor 對齊；平移整數格比例不變", () => {
    const ratioAt = (dx: number, dy: number) => {
      const m = modelMask(M, { left: 10.3 + dx, top: 4.04 + dy, sx: 1, sy: 1 });
      const o = modelMask(rect(70, 30), { left: 5.6 + dx, top: 40.04 + dy, sx: 1, sy: 1 });
      expect(m.x0).toBe(Math.floor(10.3 + dx));
      return coverRatio(m, [o]);
    };
    const base = ratioAt(0, 0);
    expect(ratioAt(48, 0)).toEqual(base);
    expect(ratioAt(-96, 144)).toEqual(base);
    expect(base.ratio).toBeGreaterThan(0);
  });
});

describe("OCL-1a 第 4 項：遲滯", () => {
  it("表格：(0.549, 假)→假、(0.55, 假)→真、(0.45, 真)→真、(0.449, 真)→假", () => {
    expect(outlineWanted(0.549, false)).toBe(false);
    expect(outlineWanted(0.55, false)).toBe(true);
    expect(outlineWanted(0.45, true)).toBe(true);
    expect(outlineWanted(0.449, true)).toBe(false);
  });
  it("序列 0.50→0.56→0.50→0.46→0.44→0.50 ＝ 假、真、真、真、假、假（45～55% 之間進出不閃爍）", () => {
    let was = false;
    const got: boolean[] = [];
    for (const r of [0.5, 0.56, 0.5, 0.46, 0.44, 0.5]) {
      was = outlineWanted(r, was);
      got.push(was);
    }
    expect(got).toEqual([false, true, true, true, false, false]);
  });
});

// ---- 繪製器層：OcclusionLayer 的子類別（不 init Pixi；擺位、身體來源、外框貼圖換成合成的）----
class TestLayer extends OcclusionLayer {
  units: OclUnit[] = [];
  terrain = new Set<string>();
  src: OclSource = source([]);
  constructor() {
    super();
    (this.art as unknown as { outline: () => Texture }).outline = () => Texture.WHITE;
    (this as unknown as { oclSource: OclSource }).oclSource = { maskImage: (b, r) => this.src.maskImage(b, r), texImage: (b) => this.src.texImage(b) };
  }
  protected override occlusionUnits(): OclUnit[] {
    return this.units;
  }
  protected override terrainOccluded(_m: DrawModel, u: UnitDraw): boolean {
    return this.terrain.has(u.id);
  }
  run(units: OclUnit[]): void {
    this.units = units;
    this.src = source(units);
    for (const c of this.silhouettes.removeChildren()) c.destroy();
    this.silhouetteOf.clear();
    this.drawOcclusion({ units: units.map((e) => e.u), height: 8 } as unknown as DrawModel);
  }
  get was(): ReadonlyMap<string, boolean> {
    return this.outlineWas;
  }
  get outlines(): ReadonlyMap<string, Sprite> {
    return this.outlineOf;
  }
  get legacy(): ReadonlyMap<string, unknown> {
    return this.silhouetteOf;
  }
  get calls(): string[] {
    return (this.src as OclSource & { calls: string[] }).calls;
  }
}

/** 被擋者 60×60 在 (2, 1)、大型前排 100×60 在 (2, 2) 往上 `lift` 模型像素（lift 越大擋越多）。 */
function pair(lift: number, over: Partial<UnitDraw> = {}): OclUnit[] {
  const back = unitOf("b", rect(60, 60), 2, 1, 0, over);
  // 被擋者腳底 y ＝ 72 + FEET、上緣 12 + FEET；前排上緣 ＝ 120 + FEET − lift − 60
  const front = unitOf("f", BIG, 2, 2, 1, {}, 0, -lift);
  return [back, front];
}
/** 前排上緣到被擋者下緣的列數 ＝ 擋住的比例 × 60。 */
const liftFor = (ratio: number) => Math.round(ratio * 60) - 12;

describe("OCL-1a 第 4 項：遲滯狀態跨 draw(model) 保留", () => {
  it("同一個繪製器連續兩次 draw：50%（沒畫）→ 56%（畫）→ 50%（照畫）→ 44%（拿掉）", () => {
    const r = new TestLayer();
    const seq: Array<[number, boolean]> = [[0.5, false], [0.5667, true], [0.5, true], [0.4333, false], [0.5, false]];
    for (const [ratio, want] of seq) {
      r.run(pair(liftFor(ratio)));
      expect(r.occlusionStats().entries.find((e) => e.id === "b")!.ratio).toBeCloseTo(ratio, 3);
      expect(r.was.get("b")).toBe(want);
      expect(r.outlines.has("b")).toBe(want);
    }
  });
  it("單位不在 model.units 時刪掉遲滯狀態", () => {
    const r = new TestLayer();
    r.run(pair(liftFor(0.7)));
    expect(r.was.get("b")).toBe(true);
    r.run([pair(liftFor(0.7))[1]!]);
    expect(r.was.has("b")).toBe(false);
  });
});

describe("OCL-1a 第 5 項：過濾在算比例之前", () => {
  for (const [name, over] of [["倒下", { downed: true }], ["資訊被隱藏", { hiddenInfo: true }], ["隱匿中（友方也不畫，Q3）", { statusIds: ["concealed"] }]] as const) {
    it(`${name}：遮罩函式沒被呼叫、沒有外框 Sprite`, () => {
      const r = new TestLayer();
      r.run(pair(liftFor(0.9), over as Partial<UnitDraw>));
      expect(r.calls.filter((c) => c.endsWith(":k:b"))).toEqual([]);
      expect(r.outlines.has("b")).toBe(false);
      expect(r.occlusionStats().entries.find((e) => e.id === "b")!.skip).toBe("filtered");
      // 對照：沒過濾時有呼叫、有外框
      const r2 = new TestLayer();
      r2.run(pair(liftFor(0.9)));
      expect(r2.calls).toContain("mask:k:b");
      expect(r2.outlines.has("b")).toBe(true);
    });
  }
});

describe("OCL-1a 第 6 項：色帶", () => {
  const R = 20;
  const N = 64;
  const disk = image(N, N, (x, y) => (x + 0.5 - 32) ** 2 + (y + 0.5 - 32) ** 2 <= R * R);
  const bits = binaryMask(disk);
  const W = 3;
  const INK = 1.5;
  const band = outlineBand(bits, N, N, W, INK);
  const all = new Uint8Array(N * N).fill(1);
  const rgba = composeOutline(band, all, INK);
  const row = 32; // 通過圓心的一列，往右走 ＝ 沿法線
  it("色線寬（沿法線量）＝ 指定的貼圖 px ± 0.5；黑邊在色線兩側各 ≈ 襯邊寬", () => {
    let color = 0;
    let inkIn = 0;
    let inkOut = 0;
    for (let x = 32; x < N; x++) {
      const i = row * N + x;
      color += band.color[i]! / 255;
      if (bits[i] === 1) inkIn += (band.ink[i]! - band.color[i]!) / 255;
      else inkOut += band.ink[i]! / 255;
    }
    expect(Math.abs(color - W)).toBeLessThanOrEqual(0.5);
    expect(Math.abs(inkIn - INK)).toBeLessThanOrEqual(0.5);
    expect(Math.abs(inkOut - INK)).toBeLessThanOrEqual(0.5);
  });
  it("色線畫白、黑邊畫 #16121a；外側（黑邊外 1 px 以外）全透明", () => {
    let white = 0;
    let ink = 0;
    for (let i = 0; i < N * N; i++) {
      const a = rgba[i * 4 + 3]!;
      const d = Math.hypot((i % N) + 0.5 - 32, Math.floor(i / N) + 0.5 - 32);
      if (d > R + INK + 1.5) expect(a, `(${i % N}, ${Math.floor(i / N)})`).toBe(0);
      if (d < R - W - INK - 1.5) expect(a).toBe(0);
      if (a === 255 && rgba[i * 4] === 255) white += 1;
      if (a === 255 && rgba[i * 4] === (OUTLINE_INK >> 16)) ink += 1;
    }
    expect(white).toBeGreaterThan(0);
    expect(ink).toBeGreaterThan(0);
  });
  it("只畫被擋段：O 只蓋右半時左半色線像素 0", () => {
    const right = image(N, N, (x) => x >= 32);
    const out = composeOutline(band, binaryMask(right), INK);
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < 32 - INK - 1; x++) expect(out[(y * N + x) * 4 + 3]).toBe(0);
    }
    let rightPx = 0;
    for (let i = 0; i < N * N; i++) if (i % N >= 32 && out[i * 4 + 3]! > 0) rightPx += 1;
    expect(rightPx).toBeGreaterThan(0);
  });
  it("大型前排之後的小兵挖掉：小兵範圍內沒有色線", () => {
    const place = { left: 0, top: 0, sx: 1, sy: 1 };
    const clip = clipMask(N, N, place, [
      { img: rect(N, N), place, big: true },
      { img: rect(16, 16), place: { left: 44, top: 24, sx: 1, sy: 1 }, big: false },
    ]);
    const out = composeOutline(band, clip, INK);
    for (let y = 24; y < 40; y++) {
      for (let x = 44; x < 60; x++) {
        const i = (y * N + x) * 4;
        // 色線（白）不在小兵範圍；黑邊可能伸進來 ≤ 襯邊寬
        expect(out[i + 3] === 0 || out[i]! < 128, `(${x}, ${y})`).toBe(true);
      }
    }
    // 小兵範圍外的右側照畫
    expect(out[(10 * N + 45) * 4 + 3]).toBe(0); // 圓外
    let left = 0;
    for (let i = 0; i < N * N; i++) if (out[i * 4 + 3]! > 0 && out[i * 4]! === 255) left += 1;
    expect(left).toBeGreaterThan(0);
  });
});

describe("OCL-1a 第 7 項：確定性", () => {
  it("同一輸入算兩次，外框位元組的 SHA-256 相同", async () => {
    const back = unitOf("b", image(48, 64, (x, y) => (x - 24) ** 2 / 400 + (y - 34) ** 2 / 900 <= 1), 2, 1, 0);
    const front = unitOf("f", BIG, 2, 2, 1, {}, 3.5, -30);
    const hash = async () => {
      const plan = planOcclusion([back, front], new Map(), source([back, front])).get("b")!;
      expect(plan.drawn).toBe(true);
      const t = outlineTexture(back, plan.layers!, source([back, front]), 1.31, new Map())!;
      return { key: t.key, sha: await sha256(t.make()) };
    };
    const a = await hash();
    expect(await hash()).toEqual(a);
    expect(a.sha).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe("OCL-1a 第 8 項：線寬換算（Q2）", () => {
  // 800×600 的地圖縮放約 0.53、1600×900 約 1.31（樣張 S800／S1600）；人形 1 虛擬像素 ＝ 48/52 × 1.06 模型像素，頭目再 × 1.6
  const HUMAN = (48 / 52) * 1.06;
  for (const [name, scale] of [["800 寬", 0.53], ["1600 寬", 1.31]] as const) {
    for (const dpr of [1, 2]) {
      for (const display of [HUMAN, HUMAN * 1.6]) {
        it(`${name}、DPR ${dpr}、${display > 1.2 ? "頭目" : "人形"}：換回 CSS px 在 1.5 ± 0.12；縮放 ± 0.001 鍵不變`, () => {
          const res = figureResolution(display * dpr * scale);
          const texPerModel = res / display;
          const w = outlineWidthTex(OUTLINE_CSS_PX, texPerModel, scale);
          expect(Math.abs((w / texPerModel) * scale - 1.5)).toBeLessThanOrEqual(0.12);
          expect(w % 0.25).toBe(0);
          expect(outlineWidthTex(OUTLINE_CSS_PX, texPerModel, scale + 0.001)).toBe(w);
          expect(outlineWidthTex(OUTLINE_CSS_PX, texPerModel, scale - 0.001)).toBe(w);
        });
      }
    }
  }
});

describe("OCL-1a 第 9 項：6F-22 舊剪影規則", () => {
  it("legacySilhouetteWanted 四種組合", () => {
    expect(legacySilhouetteWanted(false, false)).toBe(false);
    expect(legacySilhouetteWanted(false, true)).toBe(false);
    expect(legacySilhouetteWanted(true, false)).toBe(true);
    expect(legacySilhouetteWanted(true, true)).toBe(false);
  });
  it("繪製器層：同一單位有外框時 silhouetteOf 沒有它、沒有外框時照舊有", () => {
    const r = new TestLayer();
    r.terrain = new Set(["b", "f"]);
    r.run(pair(liftFor(0.9)));
    expect(r.outlines.has("b")).toBe(true);
    expect(r.legacy.has("b")).toBe(false);
    expect(r.legacy.has("f")).toBe(true); // 前排自己沒有外框：被地形擋就照畫
    r.run(pair(liftFor(0.2)));
    expect(r.outlines.has("b")).toBe(false);
    expect(r.legacy.has("b")).toBe(true);
    r.terrain = new Set();
    r.run(pair(liftFor(0.2)));
    expect(r.legacy.size).toBe(0);
  });
  it("外框與舊剪影都在 silhouettes 容器；外框節點名稱、錨點、位置對齊身體", () => {
    const r = new TestLayer();
    r.run(pair(liftFor(0.9)));
    const s = r.outlines.get("b")!;
    expect(s.label).toBe(OUTLINE_LABEL);
    expect(s.parent).toBeInstanceOf(Container);
    expect(s.position.x).toBe(2 * 48 + 24);
    expect(s.position.y).toBeCloseTo(48 + 24 + FEET, 9);
    expect(s.anchor.y).toBe(1);
    expect(s.alpha).toBeCloseTo(OUTLINE_ALPHA, 6);
  });
  it("原始碼：drawUnit 不再自己畫舊剪影；BattleRenderer 畫完全部單位才呼叫 drawOcclusion", () => {
    const unit = stripTsComments(readFile(SRC_DIR, "render/battle/unitLayer.ts"));
    const body = unit.slice(unit.indexOf("protected drawUnit("), unit.indexOf("protected terrainOccluded("));
    expect(body.length).toBeGreaterThan(0);
    expect(body).not.toMatch(/silhouette\(/);
    expect(body).not.toMatch(/silhouetteOf\.set/);
    const br = stripTsComments(readFile(SRC_DIR, "render/BattleRenderer.ts"));
    const loop = br.indexOf("for (const u of model.units) this.drawUnit(model, u);");
    expect(loop).toBeGreaterThan(0);
    expect(br.indexOf("this.drawOcclusion(model);")).toBeGreaterThan(loop);
  });
});

describe("OCL-1a 第 10 項：陣營色", () => {
  it("友／敵／第三方／召喚物的 tint 分別是 RING.*.stroke", () => {
    expect(outlineColor({ team: "ally", summon: false })).toBe(RING.ally.stroke);
    expect(outlineColor({ team: "enemy", summon: false })).toBe(RING.enemy.stroke);
    expect(outlineColor({ team: "third", summon: false })).toBe(RING.third.stroke);
    expect(outlineColor({ team: "enemy", summon: true })).toBe(RING.summon.stroke);
    expect(RING.ally.stroke).toBe(0xa9ccff);
    expect(RING.summon.stroke).toBe(0x8ff0e2);
  });
  it("繪製器層：外框 Sprite 的 tint 照陣營", () => {
    for (const [team, summon, want] of [["ally", false, RING.ally.stroke], ["enemy", false, RING.enemy.stroke], ["third", false, RING.third.stroke], ["ally", true, RING.summon.stroke]] as const) {
      const r = new TestLayer();
      r.run(pair(liftFor(0.9), { team, summon }));
      expect(r.outlines.get("b")!.tint).toBe(want);
    }
  });
  it("閃白的純函式（1b 接上）：k ＝ 1 時白、alpha 1；k ＝ 0 時原色、0.8", () => {
    expect(flashTint(RING.ally.stroke, 1)).toBe(0xffffff);
    expect(flashTint(RING.ally.stroke, 0)).toBe(RING.ally.stroke);
    expect(flashAlpha(1)).toBe(1);
    expect(flashAlpha(0)).toBe(0.8);
  });
});

describe("OCL-1a：開發頁開關與量測", () => {
  it("outlinesEnabled ＝ false 時什麼都不算、不畫（舊剪影照畫）", () => {
    const r = new TestLayer();
    r.outlinesEnabled = false;
    r.terrain = new Set(["b"]);
    r.run(pair(liftFor(0.9)));
    expect(r.calls).toEqual([]);
    expect(r.outlines.size).toBe(0);
    expect(r.legacy.has("b")).toBe(true);
  });
});
