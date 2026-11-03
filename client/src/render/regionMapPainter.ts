// 區域圖的快取與組合（Phase 6F-ART1；docs/art/雲嶺區域插畫.md 第 4 節第 2 點）。
// 底層＝地景：照（區域、畫布尺寸、字型版本）快取在離屏畫布，同一區開兩次直接貼上。
// 上層＝迷霧、路、足跡、標記、標題、指北針、圖例、外框：狀態變時才重畫；霧的整張材質也照（區域、尺寸）快取，每次只重挖洞。
// 畫布由呼叫端給的工廠產生（瀏覽器用 <canvas>，測試用假的），這裡不碰 DOM。
import {
  CLOUD_FOG,
  compass,
  cutFog,
  fogHoles,
  fogTexture,
  frame,
  H,
  legend,
  plainTerrain,
  roads,
  spotMarks,
  title,
  trails,
  W,
  type Ctx,
  type RegionArtDef,
  type RegionScene,
} from "./regionMapArt";
import { ASHEN_WASTE_ART } from "./regionArtAshen";
import { CLOUD_RIDGE_ART } from "./regionArtCloud";

/** 離屏畫布（`HTMLCanvasElement` 的子集）。 */
export interface Surface {
  width: number;
  height: number;
  getContext(id: "2d"): CanvasRenderingContext2D | null;
}

export type SurfaceFactory = (w: number, h: number) => Surface;

/** 各區地景（之後開放的區照 `regionArtAshen.ts` 的格式補一個檔，登記在這裡；共用層不用改）。 */
export const REGION_ART: Readonly<Record<string, RegionArtDef>> = {
  cloud_ridge: CLOUD_RIDGE_ART,
  ashen_waste: ASHEN_WASTE_ART,
};

const PLAIN_ART: RegionArtDef = { terrain: plainTerrain, fog: CLOUD_FOG };

/** 區域的地景定義；還沒有地景檔的區＝草地底色＋白霧。 */
export function regionArtOf(region: string): RegionArtDef {
  return REGION_ART[region] ?? PLAIN_ART;
}

/** 底層的快取鍵：區域、畫布像素尺寸、字型版本（地名小字跟字型有關）。 */
export function baseKey(region: string, w: number, h: number, fontEpoch = 0): string {
  return `${region}@${w}x${h}#${fontEpoch}`;
}

/** 上層的重畫鍵：場景（迷霧與標記的全部狀態）、尺寸、字牌倍數、字型版本。 */
export function overlayKey(scene: RegionScene, w: number, h: number, k: number, fontEpoch = 0): string {
  return JSON.stringify([scene, w, h, k, fontEpoch]);
}

const asImage = (s: Surface): CanvasImageSource => s as unknown as CanvasImageSource;

/** 邏輯座標（1280×860）縮放到 `w`×`h` 像素。 */
function toLogical(ctx: Ctx, w: number, h: number): void {
  ctx.setTransform(w / W, 0, 0, h / H, 0, 0);
}

class LruSurfaces {
  private readonly map = new Map<string, Surface>();

  constructor(private readonly limit: number) {}

  get(key: string, build: () => Surface): Surface {
    const hit = this.map.get(key);
    if (hit !== undefined) {
      this.map.delete(key);
      this.map.set(key, hit);
      return hit;
    }
    const s = build();
    this.map.set(key, s);
    while (this.map.size > this.limit) {
      const first = this.map.keys().next().value;
      if (first === undefined) break;
      this.map.delete(first);
    }
    return s;
  }

  get size(): number {
    return this.map.size;
  }
}

export class RegionMapPainter {
  private readonly terrains: LruSurfaces;
  private readonly fogs: LruSurfaces;
  private work: Surface | null = null;
  /** 實際畫了幾次（測試用：快取命中不加）。 */
  readonly stats = { terrain: 0, fog: 0, overlay: 0 };

  constructor(
    private readonly make: SurfaceFactory,
    limit = 4,
  ) {
    this.terrains = new LruSurfaces(limit);
    this.fogs = new LruSurfaces(limit);
  }

  get cachedTerrains(): number {
    return this.terrains.size;
  }

  private layer(w: number, h: number, draw: (ctx: Ctx) => void): Surface {
    const s = this.make(w, h);
    const ctx = s.getContext("2d");
    if (ctx !== null) {
      toLogical(ctx, w, h);
      draw(ctx);
    }
    return s;
  }

  /** 地景（快取）。 */
  terrainLayer(region: string, w: number, h: number, fontEpoch = 0): Surface {
    return this.terrains.get(baseKey(region, w, h, fontEpoch), () => {
      this.stats.terrain += 1;
      return this.layer(w, h, (ctx) => regionArtOf(region).terrain(ctx));
    });
  }

  /** 還沒挖洞的整張霧（快取；霧材質沒有文字，不看字型版本）。 */
  fogLayer(region: string, w: number, h: number): Surface {
    return this.fogs.get(baseKey(region, w, h), () => {
      this.stats.fog += 1;
      return this.layer(w, h, (ctx) => fogTexture(ctx, regionArtOf(region).fog));
    });
  }

  /** 底層：把快取的地景貼到畫布上。 */
  paintBase(ctx: Ctx, region: string, w: number, h: number, fontEpoch = 0): void {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(asImage(this.terrainLayer(region, w, h, fontEpoch)), 0, 0);
  }

  private workSurface(w: number, h: number): Surface {
    if (this.work === null || this.work.width !== w || this.work.height !== h) this.work = this.make(w, h);
    return this.work;
  }

  /** 上層：迷霧（快取的材質挖洞）、霧上地景、路、足跡、地點標記、標題、指北針、圖例、外框。`k`＝字牌倍數。 */
  paintOverlay(ctx: Ctx, scene: RegionScene, w: number, h: number, k = 1): void {
    this.stats.overlay += 1;
    const art = regionArtOf(scene.region);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const work = this.workSurface(w, h);
    const wctx = work.getContext("2d");
    if (wctx !== null) {
      wctx.setTransform(1, 0, 0, 1, 0, 0);
      wctx.globalCompositeOperation = "source-over";
      wctx.clearRect(0, 0, w, h);
      wctx.drawImage(asImage(this.fogLayer(scene.region, w, h)), 0, 0);
      toLogical(wctx, w, h);
      cutFog(wctx, fogHoles(scene));
      ctx.drawImage(asImage(work), 0, 0);
    }
    toLogical(ctx, w, h);
    art.afterFog?.(ctx);
    roads(ctx, scene);
    trails(ctx, scene);
    // 下方的地點後畫（字牌蓋在上方地點的圖示上，不會被上方的圖示壓住）
    const spots = [...scene.spots].sort((a, b) => a.y - b.y || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    for (const s of spots) spotMarks(ctx, s, k);
    title(ctx, scene.title, scene.level);
    compass(ctx);
    legend(ctx);
    frame(ctx);
  }
}
