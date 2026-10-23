// 程式繪製美術的貼圖快取：每種「規格」畫一張離屏 canvas，再 `Texture.from(canvas)`（移植需求第 0 節效能原則）。
// 鍵 ＝ 規格鍵（地形＋座標變體＋鄰格遮罩…）；每次重畫場景前後呼叫 `beginFrame`／`endFrame`，
// 本輪沒用到的貼圖會被銷毀，不洩漏。繪圖以 2 倍解析度產生，場景縮放時仍清晰。
import { Texture } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import { drawObject, objectArtKey, type ObjectArtSpec } from "./objectArt";
import { ART_T, drawTile, tileArtKey, type TileArtSpec } from "./terrainArt";
import type { Ctx } from "./artDraw";
import type { Facing } from "../api/types";
import { dollKey, type DollSpec } from "./appearance";
import { renderFigureCanvas } from "./paperdoll";
import { renderSummonCanvas, summonKey, type ResolvedLook } from "./summonArt";

/** 貼圖解析度倍率（相對 TILE_SIZE）。 */
export const ART_RESOLUTION = 2;
/** 小人貼圖解析度倍率（相對虛擬像素）。 */
export const FIGURE_RESOLUTION = 3;

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

  tile(spec: TileArtSpec): Texture | null {
    return this.get(`t|${tileArtKey(spec)}`, (ctx) => drawTile(ctx, spec));
  }

  object(spec: ObjectArtSpec): Texture | null {
    return this.get(`o|${objectArtKey(spec)}`, (ctx) => drawObject(ctx, spec));
  }

  /** 戰場效果貼圖（陷阱、區域單格、霧、徽章、施放者環…，Phase 3-36b）：一格大小；`key` 由呼叫端用級距組成。 */
  fx(key: string, draw: (ctx: Ctx) => void): Texture | null {
    return this.get(`x|${key}`, draw);
  }

  /** 紙娃娃小人貼圖（鍵 ＝ 裝備組合＋朝向＋姿勢）；沒有 DOM 時回傳 `null`。 */
  figure(spec: DollSpec, facing: Facing, downed: boolean): Texture | null {
    const key = `f|${dollKey(spec, facing, downed)}`;
    this.used.add(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const canvas = renderFigureCanvas(spec, facing, downed, FIGURE_RESOLUTION);
    if (canvas === null) return null;
    const tex = Texture.from(canvas);
    this.cache.set(key, tex);
    return tex;
  }

  /** 召喚物貼圖（Phase 3-33h1；鍵 ＝ 外觀＋朝向，殘影另加召喚者外觀）；人形傳入 `humanoid` 紙娃娃規格。 */
  summon(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null): Texture | null {
    const owner = look.variant === "afterimage" && humanoid !== null ? dollKey(humanoid, facing, false) : "";
    const key = `s|${summonKey(look, facing, owner)}`;
    this.used.add(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const canvas = renderSummonCanvas(look, facing, humanoid, FIGURE_RESOLUTION);
    if (canvas === null) return null;
    const tex = Texture.from(canvas);
    this.cache.set(key, tex);
    return tex;
  }

  destroy(): void {
    for (const tex of this.cache.values()) tex.destroy(true);
    this.cache.clear();
  }
}
