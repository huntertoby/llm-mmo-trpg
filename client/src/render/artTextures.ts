// 程式繪製美術的貼圖快取：每種「規格」畫一張離屏 canvas，再 `Texture.from(canvas)`（移植需求第 0 節效能原則）。
// 鍵 ＝ 規格鍵（地形＋座標變體＋鄰格遮罩…）；每次重畫場景前後呼叫 `beginFrame`／`endFrame`，
// 本輪沒用到的貼圖會被銷毀，不洩漏。繪圖以 2 倍解析度產生，場景縮放時仍清晰。
// 6N-3 起快取有 LRU 上限（`textureLru.ts`；6R-F 起是位元組預算 256MB）：重畫之間動畫要的姿勢貼圖超過上限時淘汰最久沒用的；本輪重畫用到的不淘汰。
// 6R-F：重畫場景後，這一輪沒畫到的 owner（死掉、離場、換地圖的小人，播完的殘影）的 hold 都放開；
// 銷毀前一律問「畫面上活著的 Sprite 還拿著哪些貼圖」（`setLiveProbe`），拿著的不銷毀。
import { Container, Sprite, Texture } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import { drawFlammableMark, drawObject, objectArtKey, type ObjectArtSpec } from "./objectArt";
import { ART_T, drawTile, tileArtKey, type TileArtSpec } from "./terrainArt";
import type { Ctx } from "./artDraw";
import type { Facing } from "../api/types";
import { dollKey, type DollSpec } from "./appearance";
import { formKey, renderAuraCanvas, renderFormCanvas } from "./inkForm";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, renderFigureCanvas, SUMMON_SCALE } from "./paperdoll";
import { copiesOwner, renderSummonCanvas, summonKey, type ResolvedLook } from "./summonArt";
import { creatureKey, fxSizeOf, HUGE_FIELD_SCALE, renderCreatureCanvas, renderCreatureFxCanvas, type ResolvedCreature } from "./inkCreature";
import { fxTurnScale } from "./creatureFxTurn";
import { creaturePoseKey, splitCreatureOffset, type CreaturePose } from "./creaturePose";
import type { InkPose } from "./inkPose";
import { poseKey, quantizeFlash } from "./motionClips";
import { whiteCanvas } from "./silhouetteFlash";
import { rgbaBytes, TEXTURE_BUDGET_BYTES, TextureLru } from "./textureLru";
import { alphaOf, type AlphaImage } from "./occludeOutline";

/** OCL-1a：身體 alpha 遮罩的快取上限（張數；超過時丟最久沒用的）。 */
export const ALPHA_MASK_CAP = 256;

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

/** 6R-F 安全網：`root` 底下所有活著（沒銷毀）的 Sprite 正在用的貼圖。 */
export function liveSpriteTextures(root: Container): Set<Texture> {
  const out = new Set<Texture>();
  const walk = (c: Container): void => {
    if (c.destroyed) return;
    if (c instanceof Sprite) out.add(c.texture);
    for (const child of c.children) walk(child);
  };
  walk(root);
  return out;
}

/** 貼圖的位元組數（`w*h*4`，用實際像素大小）。 */
function textureBytes(t: Texture): number {
  const src = t.source as { pixelWidth?: number; pixelHeight?: number } | undefined;
  return rgbaBytes(src?.pixelWidth ?? t.width, src?.pixelHeight ?? t.height);
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
  private readonly cache: TextureLru<Texture>;
  private used = new Set<string>();
  /** 正在重畫場景（`beginFrame`～`endFrame`）：這段時間要的貼圖釘住，不被 LRU 淘汰。 */
  private inFrame = false;

  /** 這一輪重畫（`beginFrame`～`endFrame`）呼叫過 `holdFor` 的 owner；其他的在 `endFrame` 放開（6R-F）。 */
  private frameOwners = new Set<string>();
  /** 畫面上活著的 Sprite 正在用的貼圖（6R-F 安全網；沒設時當作沒有）。 */
  private liveProbe: () => ReadonlySet<Texture> = () => new Set<Texture>();
  private ownerSeq = 0;

  constructor(budget: number = TEXTURE_BUDGET_BYTES) {
    this.cache = new TextureLru<Texture>(budget, true, textureBytes); // 6N-4：淘汰的貼圖延到重畫場景後才銷毀
  }

  /** 6R-F：設定「畫面上活著的 Sprite 正在用哪些貼圖」；銷毀前一律跳過這些。 */
  setLiveProbe(probe: () => ReadonlySet<Texture>): void {
    this.liveProbe = probe;
  }

  /** 一個不會和別人重複的 owner 名稱（殘影等短暫效果用；同一人一步內兩次閃避不互相頂掉）。 */
  uniqueOwner(prefix: string): string {
    this.ownerSeq += 1;
    return `${prefix}#${this.ownerSeq}`;
  }

  /** 量測用（dev 的 `window.__texStats`）：張數、位元組、淘汰待銷毀、有 hold 的 owner 數。 */
  stats(): { count: number; bytes: number; pending: number; pendingBytes: number; owners: number } {
    const c = this.cache;
    return { count: c.size, bytes: c.bytes, pending: c.pendingDestroy, pendingBytes: c.pendingBytes, owners: c.owners };
  }

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

  /** 異形貼圖的解析度：頭目在戰場上放大 ×1.6（QK-4b），解析度跟著提高才不會糊。 */
  private creatureRes(r: ResolvedCreature): number {
    return this.figureRes(r.boss === undefined ? HUMAN_DISPLAY : HUMAN_DISPLAY * HUGE_FIELD_SCALE);
  }

  /** 目前快取的貼圖數量（效能量測用）。 */
  get size(): number {
    return this.cache.size;
  }

  beginFrame(): void {
    this.used = new Set<string>();
    this.cache.unpinAll();
    this.frameOwners = new Set<string>();
    // 小人正在用的貼圖不放開：重畫中途還在播的片段（倒下、閃避殘影）下一幀才換貼圖，先放開會被 endFrame 銷毀
    this.inFrame = true;
  }

  /**
   * 銷毀本輪沒用到的貼圖（小人正在用的、畫面上還有活著的 Sprite 拿著的不銷毀）。
   * 6R-F：這一輪沒畫到的 owner（死掉、離場、換了地圖的小人，播完或還在播的殘影）的 hold 先放開；
   * 還在播的殘影由「活著的 Sprite」安全網保護，不會被銷毀。
   */
  endFrame(): void {
    this.inFrame = false;
    this.cache.releaseExcept(this.frameOwners);
    const live = this.liveProbe();
    for (const key of this.cache.keys()) {
      if (this.used.has(key) || this.cache.isHeld(key)) continue;
      const tex = this.cache.peek(key);
      if (tex !== undefined && live.has(tex)) continue;
      this.cache.drop(key);
    }
    this.cache.flushEvicted((t) => live.has(t)); // 舊的小人已經拆掉，淘汰的貼圖可以銷毀了
  }

  /**
   * 6N-4（美術 PM 6N-3 驗收第 4 點）：`owner`（單位 ID）目前畫在畫面上的貼圖，釘住直到它換成別張。
   * 動畫、待機每次換小人的貼圖時呼叫；不是這個快取的貼圖（或 `null`）時放開。
   */
  holdFor(owner: string, tex: Texture | null): void {
    if (this.inFrame && tex !== null) this.frameOwners.add(owner);
    const key = tex === null ? undefined : this.keyOf.get(tex);
    if (key === undefined) this.cache.release(owner);
    else this.cache.hold(owner, key);
  }

  /** 這一張貼圖現在是不是被某個小人釘住（測試用）。 */
  isHeld(tex: Texture): boolean {
    const key = this.keyOf.get(tex);
    return key !== undefined && this.cache.isHeld(key);
  }

  private readonly keyOf = new WeakMap<Texture, string>();

  private store(key: string, tex: Texture, bytes?: number): void {
    this.keyOf.set(tex, key);
    this.cache.set(key, tex, bytes);
    // 很久沒重畫（城鎮裡一直播待機）時，延後銷毀的貼圖累積到預算的一半就先銷毀（畫面上還拿著的跳過）
    if (this.cache.pendingBytes > this.cache.budget / 2) {
      const live = this.liveProbe();
      this.cache.flushEvicted((t) => live.has(t));
    }
  }

  private touch(key: string): void {
    this.used.add(key);
    if (this.inFrame) this.cache.pin(key);
  }

  private get(key: string, draw: (ctx: Ctx) => void): Texture | null {
    this.touch(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const tex = paint(draw);
    if (tex !== null) this.store(key, tex, rgbaBytes(TILE_SIZE * ART_RESOLUTION, TILE_SIZE * ART_RESOLUTION));
    return tex;
  }

  /** 查快取 → 沒有就用 `make` 畫一張離屏 canvas 轉成貼圖（Phase 3T-4：人物、召喚物、形態、光環共用同一段）；畫不出來（沒有 DOM）回傳 `null`。 */
  canvas(key: string, make: () => HTMLCanvasElement | null): Texture | null {
    this.touch(key);
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const canvas = make();
    if (canvas === null) return null;
    const tex = Texture.from(canvas);
    this.store(key, tex, rgbaBytes(canvas.width, canvas.height));
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

  /** 不含地上影子的紙娃娃（6N-4 倒下片段側倒時用；和 HP 歸零的倒地圖示一樣沒有影子）。 */
  figureBare(spec: DollSpec, facing: Facing, pose: InkPose | null, flash = 0): Texture | null {
    const res = this.figureRes(HUMAN_DISPLAY);
    const w = quantizeFlash(flash);
    const key = `fb|${res}|${dollKey(spec, facing, false)}${pose === null ? "" : `|p:${poseKey(pose)}`}${w > 0 ? `|w:${w}` : ""}`;
    return this.canvas(key, () => renderFigureCanvas(spec, facing, false, res, false, pose, w));
  }

  /** 召喚物貼圖（Phase 3-33h1；鍵 ＝ 外觀＋朝向，殘影另加召喚者外觀）；人形傳入 `humanoid` 紙娃娃規格。 */
  summon(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null): Texture | null {
    const owner = copiesOwner(look.variant) && humanoid !== null ? dollKey(humanoid, facing, false) : "";
    const res = this.figureRes(look.body === "humanoid" ? HUMAN_DISPLAY : BEAST_DISPLAY);
    return this.canvas(`s|${res}|${summonKey(look, facing, owner)}`, () => renderSummonCanvas(look, facing, humanoid, res));
  }

  /** 異形貼圖（Phase 5A-ART1；鍵 ＝ 解析後的外觀＋朝向，依狀態的特徵已解進外觀）。 */
  creature(r: ResolvedCreature, facing: Facing, pose: CreaturePose | null = null): Texture | null {
    const res = this.creatureRes(r);
    const key = `c|${res}|${creatureKey(r, facing)}${pose === null ? "" : `|p:${creaturePoseKey(pose)}`}`;
    return this.canvas(key, () => renderCreatureCanvas(r, facing, res, pose));
  }

  /**
   * 動畫中的異形身體（6R-F）：只畫身體、不含影子，姿勢的位移（dx、dy）不進鍵、不畫進貼圖，
   * 由呼叫端移動節點（`unitSprite.placeCreatureBody`）；影子另用 `creatureShadow`，留在原地。
   */
  creatureBody(r: ResolvedCreature, facing: Facing, pose: CreaturePose): Texture | null {
    const res = this.creatureRes(r);
    const still = splitCreatureOffset(pose).pose;
    const key = `cb|${res}|${creatureKey(r, facing)}|p:${creaturePoseKey(still)}`;
    return this.canvas(key, () => renderCreatureCanvas(r, facing, res, still, "body"));
  }

  /**
   * CB-3c／CB-4：目標不在同一排（`pose.fxTurn`：正南北、斜向）時，片段這一格自帶的特效（另一張；原點＝「相鄰目標」那一點，畫布 `CREATURE_FX_BOX`）。
   * 頭目用戰場縮放 `HUGE_FIELD_SCALE`、大小 1（貼圖不含大小）。沒有轉向、這一格沒有特效 → `null`。
   */
  creatureFx(r: ResolvedCreature, facing: Facing, pose: CreaturePose): Texture | null {
    if (pose.fxTurn === undefined) return null;
    const res = this.creatureRes(r);
    const still = splitCreatureOffset(pose).pose;
    const key = `cfx|${res}|${creatureKey(r, facing)}|p:${creaturePoseKey(still)}`;
    return this.canvas(key, () => renderCreatureFxCanvas(r, facing, res, still, fxTurnScale(fxSizeOf(r), r.boss === undefined ? 1 : HUGE_FIELD_SCALE, DOLL_SCALE)));
  }

  /** 異形地上的影子（6R-F；和 `creature` 同畫布、同錨點，只有影子）。 */
  creatureShadow(r: ResolvedCreature, facing: Facing): Texture | null {
    const res = this.creatureRes(r);
    return this.canvas(`cs|${res}|${creatureKey(r, facing)}`, () => renderCreatureCanvas(r, facing, res, null, "shadow"));
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

  // ---- OCL-1a：被遮擋外框 ----------------------------------------------------
  /** 身體 alpha 遮罩（`om|`＝模型像素用、`oa|`＝畫面解析度用）：同一個鍵只取一次 `getImageData`。 */
  private readonly alphaMasks = new Map<string, AlphaImage | null>();
  /** 實際呼叫 `getImageData` 的次數（效能量測：應等於不同遮罩鍵數）。 */
  alphaReads = 0;

  /** 查遮罩快取 → 沒有就用 `make` 畫一張畫布、讀一次 alpha（沒有 DOM 或畫不出來時 `null`，也記住）。 */
  alphaMask(key: string, make: () => HTMLCanvasElement | null): AlphaImage | null {
    const hit = this.alphaMasks.get(key);
    if (hit !== undefined || this.alphaMasks.has(key)) {
      this.alphaMasks.delete(key);
      this.alphaMasks.set(key, hit ?? null);
      return hit ?? null;
    }
    const cv = make();
    const ctx = cv === null || cv.width <= 0 || cv.height <= 0 ? null : cv.getContext("2d", { willReadFrequently: true });
    let img: AlphaImage | null = null;
    if (cv !== null && ctx !== null) {
      this.alphaReads += 1;
      img = alphaOf(ctx.getImageData(0, 0, cv.width, cv.height).data, cv.width, cv.height);
    }
    this.alphaMasks.set(key, img);
    while (this.alphaMasks.size > ALPHA_MASK_CAP) {
      const first = this.alphaMasks.keys().next().value;
      if (first === undefined) break;
      this.alphaMasks.delete(first);
    }
    return img;
  }

  /** 遮罩快取的張數（量測用）。 */
  get alphaMaskCount(): number {
    return this.alphaMasks.size;
  }

  /** 外框貼圖（鍵 `ol|…`：身體鍵＋量化線寬＋襯邊＋裁切雜湊，見 `render/battle/outlineLayer.ts`）。 */
  outline(key: string, make: () => HTMLCanvasElement | null): Texture | null {
    return this.canvas(`ol|${key}`, make);
  }

  destroy(): void {
    this.cache.clear();
    this.alphaMasks.clear();
  }
}
