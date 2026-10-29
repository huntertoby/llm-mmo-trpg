// 程式繪製美術的貼圖快取：每種「規格」畫一張離屏 canvas，再 `Texture.from(canvas)`（移植需求第 0 節效能原則）。
// 鍵 ＝ 規格鍵（地形＋座標變體＋鄰格遮罩…）；每次重畫場景前後呼叫 `beginFrame`／`endFrame`，
// 本輪沒用到的貼圖會被銷毀，不洩漏。繪圖以 2 倍解析度產生，場景縮放時仍清晰。
import { Texture } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import { drawFlammableMark, drawObject, objectArtKey, type ObjectArtSpec } from "./objectArt";
import { ART_T, drawTile, tileArtKey, type TileArtSpec } from "./terrainArt";
import type { Ctx } from "./artDraw";
import type { Facing } from "../api/types";
import { dollKey, type DollSpec } from "./appearance";
import { formKey, renderAuraCanvas, renderFormCanvas } from "./inkForm";
import { DOLL_SCALE, renderFigureCanvas, SUMMON_SCALE } from "./paperdoll";
import { renderSummonCanvas, summonKey, type ResolvedLook } from "./summonArt";

/** 貼圖解析度倍率（相對 TILE_SIZE）。 */
export const ART_RESOLUTION = 2;
/** 小人貼圖解析度倍率（相對虛擬像素）的預設值（沒設螢幕縮放時用）；3U-2 起實際值依顯示大小算，見 `ArtTextures.figureRes`。 */
export const FIGURE_RESOLUTION = 3;
const HUMAN_DISPLAY = (TILE_SIZE / 52) * DOLL_SCALE;
const BEAST_DISPLAY = (TILE_SIZE / 52) * SUMMON_SCALE;
const FIGURE_RES_MIN = 1.5;
const FIGURE_RES_MAX = 6;

/** 貼圖照實際顯示大小畫（3U-2）：`shown` ＝ 每個虛擬像素在螢幕上的實際像素數；向上取 0.5 級距，免得縮放微調就整批重畫。 */
export function figureResolution(shown: number): number {
  if (!(shown > 0)) return FIGURE_RESOLUTION;
  return Math.min(FIGURE_RES_MAX, Math.max(FIGURE_RES_MIN, Math.ceil(shown * 2 - 1e-6) / 2));
}

function paint(draw: (ctx: Ctx) => void): Texture | null {
  if (typeof document === "undefined") return null;
  const size = TILE_SIZE * ART_RESOLUTION;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(size / ART_T, size / ART_T);
  ctx.beginPath();
  ctx.rect(0, 0, ART_T, ART_T);
  ctx.clip();
  draw(ctx);
  return Texture.from(canvas);
}

export class ArtTextures {
  private cache = new Map<string, Texture>();
  private used = new Set<string>();
  /** 螢幕縮放（devicePixelRatio × 場景縮放）；`null` ＝ 未設定，小人貼圖用預設解析度。 */
  private screenScale: number | null = null;

  /** 設定螢幕縮放；改變後新請求的小人貼圖換成新解析度（鍵含解析度，舊的在 `endFrame` 被清掉）。 */
  setScreenScale(s: number): void {
    this.screenScale = s > 0 ? s : null;
  }

  /** 小人貼圖解析度：`display` ＝ 虛擬像素 → 格子像素的比例（人 ＝ `(T/52) × DOLL_SCALE`）。 */
  figureRes(display: number): number {
    return this.screenScale === null ? FIGURE_RESOLUTION : figureResolution(display * this.screenScale);
  }

  beginFrame(): void {
    this.used = new Set<string>();
  }

  /** 銷毀本輪沒用到的貼圖。 */
  endFrame(): void {
    for (const [key, tex] of this.cache) {
      if (this.used.has(key)) continue;
      tex.destroy(true);
      this.cache.delete(key);
    }
  }

  private get(key: string, draw: (ctx: Ctx) => void): Texture | null {
    this.used.add(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const tex = paint(draw);
    if (tex !== null) this.cache.set(key, tex);
    return tex;
  }

  /** 查快取 → 沒有就用 `make` 畫一張離屏 canvas 轉成貼圖（Phase 3T-4：人物、召喚物、形態、光環共用同一段）；畫不出來（沒有 DOM）回傳 `null`。 */
  canvas(key: string, make: () => HTMLCanvasElement | null): Texture | null {
    this.used.add(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const canvas = make();
    if (canvas === null) return null;
    const tex = Texture.from(canvas);
    this.cache.set(key, tex);
    return tex;
  }

  tile(spec: TileArtSpec): Texture | null {
    return this.get(`t|${tileArtKey(spec)}`, (ctx) => drawTile(ctx, spec));
  }

  object(spec: ObjectArtSpec): Texture | null {
    return this.get(`o|${objectArtKey(spec)}`, (ctx) => drawObject(ctx, spec));
  }

  /** 可燃小火苗貼圖（3-38）：全場只有一張，所有可燃物件共用。 */
  flammableMark(): Texture | null {
    return this.get("m|flammable", drawFlammableMark);
  }

  /** 戰場效果貼圖（陷阱、區域單格、霧、徽章、施放者環…，Phase 3-36b）：一格大小；`key` 由呼叫端用級距組成。 */
  fx(key: string, draw: (ctx: Ctx) => void): Texture | null {
    return this.get(`x|${key}`, draw);
  }

  /** 紙娃娃小人貼圖（鍵 ＝ 裝備組合＋朝向＋姿勢）；沒有 DOM 時回傳 `null`。 */
  figure(spec: DollSpec, facing: Facing, downed: boolean): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    return this.canvas(`f|${res}|${dollKey(spec, facing, downed)}`, () => renderFigureCanvas(spec, facing, downed, res));
  }

  /** 召喚物貼圖（Phase 3-33h1；鍵 ＝ 外觀＋朝向，殘影另加召喚者外觀）；人形傳入 `humanoid` 紙娃娃規格。 */
  summon(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null): Texture | null {
    const owner = look.variant === "afterimage" && humanoid !== null ? dollKey(humanoid, facing, false) : "";
    const res = this.figureRes(look.body === "humanoid" ? HUMAN_DISPLAY : BEAST_DISPLAY);
    return this.canvas(`s|${res}|${summonKey(look, facing, owner)}`, () => renderSummonCanvas(look, facing, humanoid, res));
  }

  /** 形態貼圖（Phase 3J-5；鍵 ＝ 畫法＋主色＋元素＋朝向＋姿勢）；不認得的畫法或沒有 DOM 時回傳 `null`。 */
  form(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    return this.canvas(`g|${res}|${formKey(id, hero, element, facing, downed)}`, () => renderFormCanvas(id, hero, element, facing, downed, res, DOLL_SCALE));
  }

  /** 腳下的形態光環貼圖（鍵 ＝ 顏色＋半徑）。 */
  formAura(color: string, rx: number): Texture | null {
    const res = this.figureRes(TILE_SIZE / 52);
    return this.canvas(`a|${res}|${color}|${rx.toFixed(2)}`, () => renderAuraCanvas(color, rx, res));
  }

  destroy(): void {
    for (const tex of this.cache.values()) tex.destroy(true);
    this.cache.clear();
  }
}
