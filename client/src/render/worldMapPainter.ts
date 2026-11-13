// 大世界圖的快取、組合與浮島漂浮（Phase 6F-ART1b；docs/archive/art/6F-ART1檢查.md 第 2 節第 3 點）。
// 底層（不動）：天空整組（照尺寸快取）＋島下雲層的投影＋未開放航線的光點。
// 上層每一格只做貼圖與平移、不重畫：
//   浮島本體（每座島一張離屏圖）→ 前景（開放的浮橋、最前排的雲，一張）→ 每座島的標記（字牌、傳送鈕、自己，每島一張）
//   → 標題、圖例、外框（一張）。
// 每座島連同自己的標記上下飄 ±3px、週期 5～6 秒、相位依區域 ID 雜湊錯開；天空、雲、浮橋不動，點擊區（DOM）也不動。
// 畫布由呼叫端給的工廠產生（瀏覽器用 <canvas>，測試用假的），這裡不碰 DOM。
import { H, W, type Ctx, type HitBox } from "./regionMapArt";
import type { Surface, SurfaceFactory } from "./regionMapPainter";
import { bodyBounds, islandBody, type Scratch } from "./worldIslandArt";
import {
  atlasFrame,
  atlasLegend,
  atlasTitle,
  bridge,
  frontClouds,
  islandMarks,
  marksBounds,
  shadowBelow,
  skyScene,
  TAU,
  type AtlasArtIsland,
  type AtlasScene,
} from "./worldMapArt";

// ---------------------------------------------------------------------------
// 漂浮
// ---------------------------------------------------------------------------

/** 振幅（邏輯像素）。 */
export const FLOAT_AMP = 3;
/** 週期範圍（毫秒）。 */
export const FLOAT_PERIOD_MIN = 5000;
export const FLOAT_PERIOD_MAX = 6000;

/** 區域 ID 的確定性雜湊（FNV-1a 32 位元；不用內建 hash）。 */
export function idHash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  h ^= h >>> 15;
  h = Math.imul(h, 2246822519);
  return (h ^ (h >>> 13)) >>> 0;
}

/** 這座島的漂浮週期（5000～6000 毫秒）。 */
export const floatPeriod = (region: string): number => FLOAT_PERIOD_MIN + (idHash(region) % (FLOAT_PERIOD_MAX - FLOAT_PERIOD_MIN + 1));

/** 這座島的起始相位（0～2π）。 */
export const floatPhase = (region: string): number => (((idHash(region) >>> 12) % 1024) / 1024) * TAU;

/** `t` 毫秒時這座島的上下位移（邏輯像素，±3）；`t` 為 null＝不動。 */
export function floatOffset(region: string, t: number | null): number {
  if (t === null) return 0;
  return FLOAT_AMP * Math.sin((t / floatPeriod(region)) * TAU + floatPhase(region));
}

// ---------------------------------------------------------------------------
// 快取
// ---------------------------------------------------------------------------

const asImage = (s: Surface): CanvasImageSource => s as unknown as CanvasImageSource;

/** 一張貼在固定邏輯位置的離屏圖。 */
interface Sprite {
  region: string;
  surface: Surface;
  /** 邏輯座標的左上角。 */
  x: number;
  y: number;
}

interface Layers {
  key: string;
  bodies: Sprite[];
  front: Surface;
  marks: Sprite[];
  chrome: Surface;
}

/** 畫面上的島（主城＋各區），照 y 由遠到近排序。 */
export function islandOrder(scene: AtlasScene): AtlasArtIsland[] {
  return [scene.capital, ...scene.islands].sort((a, b) => a.geo.y - b.geo.y || a.region.localeCompare(b.region));
}

/** 底層的鍵：尺寸＋各島的位置與狀態（投影、未開放航線的光點）。 */
export function atlasBaseKey(scene: AtlasScene, w: number, h: number): string {
  return JSON.stringify([w, h, islandOrder(scene).map((i) => [i.region, i.status, i.geo])]);
}

export interface AtlasPaintOptions {
  /** 動畫時間（毫秒）；null／省略＝不漂浮（prefers-reduced-motion 或靜態畫一次）。 */
  t?: number | null;
  /** 字型版本（字牌的字形跟字型有關）。 */
  epoch?: number;
  /** 只貼浮島本體與前景（不貼字牌、傳送鈕、標題、圖例、外框；UI-E1b 起未開放的島也不畫鎖頭徽章）：入口畫面的背景（UI-E1）用。 */
  bare?: boolean;
  /**
   * RT-5 ③：第一次打開時五座島依序從雲裡浮起，這是浮起動畫開始後的毫秒數；null／省略＝不播（直接到位）。
   * 第 i 座（`scene.islands` 的順序＝`regions.yaml`）在 i×0.3 秒開始、0.3 秒到位；主城不動。
   */
  rise?: number | null;
  /**
   * FIX-ATLAS2：滑鼠滑過的「不能去」浮島（鎖住／之後的賽季）的區域 ID。只有這座島的本體貼成稍亮的那一張
   * （`LOCKED_HOVER_LIGHT`）；不加底色、框、光暈、放大。開放的島傳進來也不理（開放的島滑過照舊由 CSS 處理）。
   */
  hoverLocked?: string | null;
}

/** FIX-ATLAS2（美術 PM 第九任）：鎖住浮島滑過時本體疊的白色比例（只疊在島的不透明像素上，約等於亮度 ×1.16；美術驗收由 9% 改 16%）。 */
export const LOCKED_HOVER_LIGHT = 0.16;
export const LOCKED_HOVER_FILL = `rgba(255,255,255,${LOCKED_HOVER_LIGHT})`;

/** 浮起時的位移與透明度（`world/opening.ts` 的 `riseProgress`／`riseOffset` 同一套；放這裡是為了 render 不依賴 world）。 */
export const RISE_STEP_MS = 300;
export const RISE_FROM_PX = 70;

/** 第 `index` 座島浮起到哪：`dy`＝還要往上多少（邏輯像素）、`alpha`＝透明度。`elapsed` 為 null＝到位。 */
export function riseAt(index: number, elapsed: number | null): { dy: number; alpha: number } {
  if (elapsed === null || index < 0) return { dy: 0, alpha: 1 };
  const raw = (elapsed - index * RISE_STEP_MS) / RISE_STEP_MS;
  const p = raw <= 0 ? 0 : raw >= 1 ? 1 : raw;
  const e = 1 - (1 - p) * (1 - p);
  return { dy: (1 - e) * RISE_FROM_PX, alpha: p <= 0 ? 0 : Math.min(1, 0.15 + e) };
}

export class AtlasPainter {
  private readonly skies = new Map<string, Surface>();
  private readonly sprites = new Map<string, Surface>();
  private layers: Layers | null = null;
  /** 鎖住浮島滑過時的稍亮本體（每張本體離屏圖一張；本體被換掉時跟著失效）。 */
  private readonly lit = new WeakMap<Surface, Surface>();
  /** 實際畫了幾次（測試用：快取命中不加）。`frame`＝組合（貼圖）次數。 */
  readonly stats = { sky: 0, base: 0, body: 0, marks: 0, front: 0, chrome: 0, frame: 0 };

  constructor(
    private readonly make: SurfaceFactory,
    private readonly limit = 3,
    private readonly spriteLimit = 40,
  ) {}

  private surface(w: number, h: number, sx: number, sy: number, ox: number, oy: number, draw: (ctx: Ctx) => void): Surface {
    const s = this.make(Math.max(1, Math.ceil(w)), Math.max(1, Math.ceil(h)));
    const ctx = s.getContext("2d");
    if (ctx !== null) {
      ctx.setTransform(sx, 0, 0, sy, -ox * sx, -oy * sy);
      draw(ctx);
    }
    return s;
  }

  private cached(key: string, build: () => Surface): Surface {
    const hit = this.sprites.get(key);
    if (hit !== undefined) {
      this.sprites.delete(key);
      this.sprites.set(key, hit);
      return hit;
    }
    const s = build();
    this.sprites.set(key, s);
    while (this.sprites.size > this.spriteLimit) {
      const first = this.sprites.keys().next().value;
      if (first === undefined) break;
      this.sprites.delete(first);
    }
    return s;
  }

  /** 天空整組（天空、小浮石、下方雲層）：照尺寸快取。 */
  skyLayer(w: number, h: number): Surface {
    const key = `${w}x${h}`;
    const hit = this.skies.get(key);
    if (hit !== undefined) return hit;
    this.stats.sky += 1;
    const s = this.surface(w, h, w / W, h / H, 0, 0, skyScene);
    this.skies.set(key, s);
    while (this.skies.size > this.limit) {
      const first = this.skies.keys().next().value;
      if (first === undefined) break;
      this.skies.delete(first);
    }
    return s;
  }

  /** 底層（不動）：天空＋投影＋未開放航線的光點。 */
  paintBase(ctx: Ctx, scene: AtlasScene, w: number, h: number): void {
    this.stats.base += 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(asImage(this.skyLayer(w, h)), 0, 0);
    ctx.setTransform(w / W, 0, 0, h / H, 0, 0);
    for (const is of islandOrder(scene)) shadowBelow(ctx, is.geo);
    for (const is of scene.islands) if (is.status !== "open") bridge(ctx, scene.capital.geo, is.geo, false);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  private sprite(kind: "body" | "marks", is: AtlasArtIsland, box: HitBox, key: string, w: number, h: number, draw: (ctx: Ctx) => void): Sprite {
    const sx = w / W;
    const sy = h / H;
    const surface = this.cached(`${kind}|${key}|${w}x${h}`, () => {
      this.stats[kind] += 1;
      return this.surface(box.w * sx, box.h * sy, sx, sy, box.x, box.y, draw);
    });
    return { region: is.region, surface, x: box.x, y: box.y };
  }

  private bodySprite(is: AtlasArtIsland, w: number, h: number, badge: boolean): Sprite {
    const box = bodyBounds(is.geo);
    const sx = w / W;
    const sy = h / H;
    const scratch = (): Scratch | null => {
      const s = this.make(Math.max(1, Math.ceil(box.w * sx)), Math.max(1, Math.ceil(box.h * sy)));
      const c = s.getContext("2d");
      if (c === null) return null;
      c.setTransform(sx, 0, 0, sy, -box.x * sx, -box.y * sy);
      return { ctx: c, image: asImage(s) };
    };
    // 本體只跟位置、地形、開放與否有關（字牌、傳送鈕另一張）
    const key = JSON.stringify([is.region, is.status === "open", is.geo, badge]);
    return this.sprite("body", is, box, key, w, h, (c) => islandBody(c, is, scratch, badge));
  }

  private marksSprite(is: AtlasArtIsland, w: number, h: number, k: number, epoch: number): Sprite {
    const box = marksBounds(is, k);
    return this.sprite("marks", is, box, JSON.stringify([is, k, epoch]), w, h, (c) => islandMarks(c, is, k));
  }

  /** 本體的稍亮版本：原圖貼上，再用 source-atop 只在島的像素上疊 `LOCKED_HOVER_FILL`。 */
  private litSurface(src: Surface): Surface {
    const hit = this.lit.get(src);
    if (hit !== undefined) return hit;
    const s = this.make(src.width, src.height);
    const c = s.getContext("2d");
    if (c !== null) {
      c.drawImage(asImage(src), 0, 0);
      c.globalCompositeOperation = "source-atop";
      c.fillStyle = LOCKED_HOVER_FILL;
      c.fillRect(0, 0, src.width, src.height);
      c.globalCompositeOperation = "source-over";
    }
    this.lit.set(src, s);
    return s;
  }

  /** 準備上層的各張離屏圖（場景、尺寸、字牌倍數、字型版本變了才重做；沒變的島直接沿用）。`bare`：未開放的島不畫鎖頭徽章。 */
  prepare(scene: AtlasScene, canTeleport: boolean, w: number, h: number, k = 1, epoch = 0, bare = false): Layers {
    const key = JSON.stringify([scene, canTeleport, w, h, k, epoch, bare]);
    if (this.layers !== null && this.layers.key === key) return this.layers;
    const order = islandOrder(scene);
    const sx = w / W;
    const sy = h / H;
    const front = this.cached(`front|${JSON.stringify([scene.capital.geo, scene.islands.map((i) => [i.geo, i.status === "open"])])}|${w}x${h}`, () => {
      this.stats.front += 1;
      return this.surface(w, h, sx, sy, 0, 0, (c) => {
        for (const is of scene.islands) if (is.status === "open") bridge(c, scene.capital.geo, is.geo, true);
        frontClouds(c);
      });
    });
    const chrome = this.cached(`chrome|${canTeleport}|${epoch}|${w}x${h}`, () => {
      this.stats.chrome += 1;
      return this.surface(w, h, sx, sy, 0, 0, (c) => {
        atlasTitle(c, canTeleport);
        atlasLegend(c);
        atlasFrame(c);
      });
    });
    this.layers = {
      key,
      bodies: order.map((is) => this.bodySprite(is, w, h, !bare)),
      front,
      marks: order.map((is) => this.marksSprite(is, w, h, k, epoch)),
      chrome,
    };
    return this.layers;
  }

  /** 上層：貼上各張離屏圖；`opts.t` 有值時每座島照 `floatOffset` 上下平移（不重畫）。 */
  paintOverlay(ctx: Ctx, scene: AtlasScene, canTeleport: boolean, w: number, h: number, k = 1, opts: AtlasPaintOptions = {}): void {
    const layers = this.prepare(scene, canTeleport, w, h, k, opts.epoch ?? 0, opts.bare === true);
    const t = opts.t ?? null;
    const sx = w / W;
    const sy = h / H;
    this.stats.frame += 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const rise = opts.rise ?? null;
    const order = new Map(scene.islands.map((is, i) => [is.region, i]));
    const hover = opts.hoverLocked ?? null;
    const lockedHover = hover !== null && [scene.capital, ...scene.islands].some((is) => is.region === hover && is.status !== "open") ? hover : null;
    const blit = (s: Sprite, lit = false): void => {
      const r = riseAt(order.get(s.region) ?? -1, rise);
      if (r.alpha <= 0) return;
      if (r.alpha < 1) ctx.globalAlpha = r.alpha;
      ctx.drawImage(asImage(lit ? this.litSurface(s.surface) : s.surface), s.x * sx, (s.y + floatOffset(s.region, t) + r.dy) * sy);
      if (r.alpha < 1) ctx.globalAlpha = 1;
    };
    layers.bodies.forEach((s) => blit(s, s.region === lockedHover));
    ctx.drawImage(asImage(layers.front), 0, 0);
    if (opts.bare === true) return;
    layers.marks.forEach((s) => blit(s));
    ctx.drawImage(asImage(layers.chrome), 0, 0);
  }
}
