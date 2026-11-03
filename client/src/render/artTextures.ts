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
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, renderFigureCanvas, SUMMON_SCALE } from "./paperdoll";
import { copiesOwner, renderSummonCanvas, summonKey, type ResolvedLook } from "./summonArt";
import { creatureKey, renderCreatureCanvas, type ResolvedCreature } from "./inkCreature";
import { creaturePoseKey, type CreaturePose } from "./creaturePose";
import type { InkPose } from "./inkPose";
import { poseKey, quantizeFlash } from "./motionClips";
import { whiteCanvas } from "./silhouetteFlash";

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

  /** 目前快取的貼圖數量（效能量測用）。 */
  get size(): number {
    return this.cache.size;
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

  /**
   * 紙娃娃小人貼圖（鍵 ＝ 裝備組合＋朝向＋倒地；6M-3 起再加骨架姿勢）；沒有 DOM 時回傳 `null`。
   * `pose`：走路、倒地等片段的姿勢，呼叫端先量化（motionClips.ts 的 `quantizePose`），鍵用 `poseKey`，同一個姿勢共用一張貼圖。
   * 沒給姿勢時鍵和畫法都和之前相同。
   */
  figure(spec: DollSpec, facing: Facing, downed: boolean, pose: InkPose | null = null, flash = 0): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    const w = quantizeFlash(flash); // 受擊白閃（6M-4）：量化到 0.05；沒有白閃時鍵和畫法都不變
    const key = `f|${res}|${dollKey(spec, facing, downed)}${pose === null ? "" : `|p:${poseKey(pose)}`}${w > 0 ? `|w:${w}` : ""}`;
    return this.canvas(key, () => renderFigureCanvas(spec, facing, downed, res, true, pose, w));
  }

  /** 召喚物貼圖（Phase 3-33h1；鍵 ＝ 外觀＋朝向，殘影另加召喚者外觀）；人形傳入 `humanoid` 紙娃娃規格。 */
  summon(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null): Texture | null {
    const owner = copiesOwner(look.variant) && humanoid !== null ? dollKey(humanoid, facing, false) : "";
    const res = this.figureRes(look.body === "humanoid" ? HUMAN_DISPLAY : BEAST_DISPLAY);
    return this.canvas(`s|${res}|${summonKey(look, facing, owner)}`, () => renderSummonCanvas(look, facing, humanoid, res));
  }

  /** 異形貼圖（Phase 5A-ART1；鍵 ＝ 解析後的外觀＋朝向，依狀態的特徵已解進外觀）。 */
  creature(r: ResolvedCreature, facing: Facing, pose: CreaturePose | null = null): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    const key = `c|${res}|${creatureKey(r, facing)}${pose === null ? "" : `|p:${creaturePoseKey(pose)}`}`;
    return this.canvas(key, () => renderCreatureCanvas(r, facing, res, pose));
  }

  /** 人形敵人的詞綴特效／人形特徵貼圖（Phase 5A-ART2；與紙娃娃同畫布、同錨點）。`draw` 在腳底原點畫。 */
  dollFx(key: string, draw: (ctx: Ctx) => void): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    return this.canvas(`d|${res}|${key}`, () => {
      if (typeof document === "undefined") return null;
      const c = document.createElement("canvas");
      c.width = DOLL_W * res;
      c.height = DOLL_H * res;
      const ctx = c.getContext("2d");
      if (ctx === null) return null;
      ctx.scale(res, res);
      ctx.translate(DOLL_W / 2, DOLL_FOOT_Y);
      draw(ctx);
      return c;
    });
  }

  /** 形態貼圖（Phase 3J-5；鍵 ＝ 畫法＋主色＋元素＋朝向＋姿勢）；不認得的畫法或沒有 DOM 時回傳 `null`。 */
  form(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    return this.canvas(`g|${res}|${formKey(id, hero, element, facing, downed)}`, () => renderFormCanvas(id, hero, element, facing, downed, res, DOLL_SCALE));
  }

  /**
   * 受擊白閃用的白色剪影（6C-8）：形態、召喚物、倒地的人沒有骨架，改把「同一張圖」不含地上影子再畫一次、
   * 轉成白色剪影（等同 `brightness(0) invert(1)`，`whiteCanvas`），由戰場疊在小人上、用不透明度閃。
   * 畫布大小、腳底錨點和本來的貼圖相同（疊上去像素對齊）。
   */
  formFlash(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    return this.canvas(`wg|${res}|${formKey(id, hero, element, facing, downed)}`, () => whiteCanvas(renderFormCanvas(id, hero, element, facing, downed, res, DOLL_SCALE, false)));
  }

  /** 召喚物的白色剪影（6C-8，見 `formFlash`）：不含地上的影子、水窪、光環。 */
  summonFlash(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null): Texture | null {
    const owner = copiesOwner(look.variant) && humanoid !== null ? dollKey(humanoid, facing, false) : "";
    const res = this.figureRes(look.body === "humanoid" ? HUMAN_DISPLAY : BEAST_DISPLAY);
    return this.canvas(`ws|${res}|${summonKey(look, facing, owner)}`, () => whiteCanvas(renderSummonCanvas(look, facing, humanoid, res, false)));
  }

  /** 倒地的人（倒下、倒地狀態）的白色剪影（6C-8，見 `formFlash`）：不含地上的影子。 */
  figureFlash(spec: DollSpec, facing: Facing, downed: boolean, pose: InkPose | null): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    const key = `wf|${res}|${dollKey(spec, facing, downed)}${pose === null ? "" : `|p:${poseKey(pose)}`}`;
    return this.canvas(key, () => whiteCanvas(renderFigureCanvas(spec, facing, downed, res, false, pose)));
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
