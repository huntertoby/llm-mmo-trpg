// OCL-1a：被遮擋剪影外框的計算（`docs/phases/PhaseOCL-1計畫.md` 交付 1～4、6、7）。
// 擺位改變時（`draw(model)`）算一次：過濾被擋者（倒下、資訊被隱藏、隱匿中）→ 找大型前排（畫的順序在後、南邊 0～3 排、
// 外接矩形相交、身體面積 ≥ 4000 模型 px²、沒有倒下）→ 模型像素算比例 → 遲滯 → 要畫的才在畫面解析度做色帶與裁切。
// 這裡不碰 Pixi 節點：繪製器（`unitLayer.ts` 的 `drawOcclusion`）把結果做成 Sprite 放進 `silhouettes`。
// 遮罩、色帶都照鍵快取；身體 alpha 只經 `OclSource` 取（繪製器接到 `ArtTextures.alphaMask`，同一個鍵只讀一次）。
import type { UnitDraw } from "../../battle/drawModel";
import { RING } from "../artPalette";
import { CONCEALED } from "../statusIcon";
import type { BareBody } from "../unitSprite";
import {
  BIG_FRONT_AREA,
  bitsHash,
  binaryMask,
  boxesMeet,
  clipMask,
  composeOutline,
  coverRatio,
  FRONT_ROWS,
  modelMask,
  OUTLINE_CSS_PX,
  OUTLINE_INK_CSS_PX,
  outlineBand,
  outlineWanted,
  outlineWidthTex,
  type AlphaImage,
  type ModelMask,
  type OutlineBand,
  type TexPlace,
} from "../occludeOutline";

/** 模型像素遮罩用的畫布解析度：每個模型像素約 2 個畫布像素（固定，不隨地圖縮放；Q2「比例和縮放無關」）。 */
export const MASK_TEX_PER_MODEL = 2;

/** 一個單位這一輪的擺位。 */
export interface OclUnit {
  readonly id: string;
  readonly u: UnitDraw;
  /** 畫的順序（越大越後畫：由北到南一排一排、同一排照 `units` 的子節點順序）。 */
  readonly order: number;
  /** 身體錨點（腳底）的模型座標（世界座標，含抬高）。 */
  readonly feet: { readonly x: number; readonly y: number };
  readonly body: BareBody;
  /** 身體節點有旋轉（倒地狀態躺著）：不當被擋者（保守，報告待決）。 */
  readonly tilted?: boolean;
}

/** 身體 alpha 的來源（繪製器接 `ArtTextures.alphaMask`；測試換成合成陣列）。 */
export interface OclSource {
  /** 模型像素遮罩用（固定解析度 `maskRes`）。 */
  maskImage(body: BareBody, res: number): AlphaImage | null;
  /** 畫面解析度（和身體貼圖同一個 `res`）：回傳 alpha 與鍵（含解析度）。 */
  texImage(body: BareBody): { key: string; img: AlphaImage } | null;
}

/** 被擋者先過濾（D6、Q3）：倒下、資訊被隱藏、隱匿中（不分陣營）都不畫，而且不算比例。 */
export function outlineEligible(u: Pick<UnitDraw, "downed" | "hiddenInfo" | "statusIds">): boolean {
  return !u.downed && u.hiddenInfo !== true && u.statusIds?.includes(CONCEALED) !== true;
}

/** D5：6F-22 舊剪影——被地形擋（`terrain`）而且這一格沒有新外框才畫。 */
export function legacySilhouetteWanted(terrain: boolean, hasOutline: boolean): boolean {
  return terrain && !hasOutline;
}

/** 外框色（D3）：`RING[team].stroke`；召喚物 `RING.summon.stroke`。 */
export function outlineColor(u: Pick<UnitDraw, "summon" | "team">): number {
  return (u.summon ? RING.summon : RING[u.team]).stroke;
}

/** 模型像素遮罩的畫布解析度（虛擬像素 → 畫布像素；量化到 0.25，鍵穩定）。 */
export function maskRes(body: BareBody): number {
  return Math.ceil(MASK_TEX_PER_MODEL * body.k * 4 - 1e-9) / 4;
}

/** 貼圖在模型座標的位置：Sprite 錨點 (0.5, foot/h)、寬高 box × k（和身體節點相同）。 */
export function placeOf(unit: Pick<OclUnit, "feet" | "body">, img: Pick<AlphaImage, "w" | "h">): TexPlace {
  const { box, k } = unit.body;
  return { left: unit.feet.x - (box.w * k) / 2, top: unit.feet.y - box.foot * k, sx: (box.w * k) / img.w, sy: (box.h * k) / img.h };
}

/** 一個單位的結果。 */
export interface OclEntry {
  readonly id: string;
  /** 大型前排遮住的比例（沒算時 0）。 */
  readonly ratio: number;
  /** 身體面積（模型 px²；沒算時 null）。 */
  readonly area: number | null;
  readonly drawn: boolean;
  /** 沒算的原因：過濾掉、躺著、附近沒有大型前排。 */
  readonly skip?: "filtered" | "tilted" | "nobig";
  /** 要畫時：裁切用的前排（照畫的順序；`big` ＝ 大型前排）。 */
  readonly layers?: ReadonlyArray<{ readonly unit: OclUnit; readonly big: boolean }>;
}

export interface OclPlanOpts {
  /** 量測（開發頁 `&measure=1`）：每個單位都算面積與比例（過濾掉的照舊不算）。 */
  readonly measure?: boolean;
  /** 關掉外框（開發頁 `&ocl=0`）：什麼都不算、不畫。 */
  readonly off?: boolean;
}

/**
 * 算這一輪誰畫外框（交付 1～3）。`was`＝上一輪有沒有畫（遲滯）；回傳每個單位的結果（不在 `units` 的不回傳）。
 * 被擋者在過濾之前**不呼叫**任何遮罩函式（D6：測試用 spy 鎖住）。
 */
export function planOcclusion(units: readonly OclUnit[], was: ReadonlyMap<string, boolean>, src: OclSource, opts: OclPlanOpts = {}): Map<string, OclEntry> {
  const out = new Map<string, OclEntry>();
  if (opts.off === true) {
    for (const e of units) out.set(e.id, { id: e.id, ratio: 0, area: null, drawn: false });
    return out;
  }
  const list = [...units].sort((a, b) => a.order - b.order);
  const masks = new Map<string, ModelMask | null>();
  const maskOf = (e: OclUnit): ModelMask | null => {
    if (masks.has(e.id)) return masks.get(e.id) ?? null;
    const res = maskRes(e.body);
    const img = src.maskImage(e.body, res);
    const m = img === null ? null : modelMask(img, placeOf(e, img));
    masks.set(e.id, m);
    return m;
  };
  list.forEach((e, k) => {
    if (!outlineEligible(e.u)) {
      out.set(e.id, { id: e.id, ratio: 0, area: null, drawn: false, skip: "filtered" });
      return;
    }
    if (e.tilted === true) {
      out.set(e.id, { id: e.id, ratio: 0, area: null, drawn: false, skip: "tilted" });
      return;
    }
    // 畫在它之後、南邊 0～3 排的（大型前排候選；倒下的不算前排，Q8）
    const later = list.slice(k + 1).filter((f) => f.u.y - e.u.y >= 0 && f.u.y - e.u.y <= FRONT_ROWS);
    const bigs = later.filter((f) => !f.u.downed && (maskOf(f)?.area ?? 0) >= BIG_FRONT_AREA);
    if (bigs.length === 0 && opts.measure !== true) {
      out.set(e.id, { id: e.id, ratio: 0, area: null, drawn: false, skip: "nobig" });
      return;
    }
    const m = maskOf(e);
    if (m === null) {
      out.set(e.id, { id: e.id, ratio: 0, area: null, drawn: false });
      return;
    }
    const fronts = bigs.map((f) => maskOf(f)).filter((f): f is ModelMask => f !== null && boxesMeet(m, f));
    const ratio = fronts.length === 0 ? 0 : coverRatio(m, fronts).ratio;
    const drawn = fronts.length > 0 && outlineWanted(ratio, was.get(e.id) ?? false);
    if (!drawn) {
      out.set(e.id, { id: e.id, ratio, area: m.area, drawn });
      return;
    }
    // 裁切：畫在它之後、外接矩形相交的全部（大型前排加進 O、其他挖掉；倒下的大型也當挖掉）
    const layers = later
      .filter((f) => {
        const fm = maskOf(f);
        return fm !== null && boxesMeet(m, fm);
      })
      .map((f) => ({ unit: f, big: !f.u.downed && (maskOf(f)?.area ?? 0) >= BIG_FRONT_AREA }));
    out.set(e.id, { id: e.id, ratio, area: m.area, drawn, layers });
  });
  return out;
}

/** 色帶快取（鍵＝畫面解析度身體鍵＋線寬＋襯邊）。 */
export type BandMemo = Map<string, OutlineBand>;
/** 色帶快取上限（張數）。 */
export const BAND_MEMO_CAP = 64;

/** 一張外框貼圖：快取鍵與畫法（RGBA、身體貼圖同大小）。 */
export interface OutlineTex {
  readonly key: string;
  readonly w: number;
  readonly h: number;
  /** 線寬、襯邊（貼圖 px，已量化）。 */
  readonly width: number;
  readonly ink: number;
  make(): Uint8ClampedArray;
}

/**
 * 外框貼圖（交付 4、Q1、Q2）：在被擋者身體貼圖（畫面解析度）上算色帶，裁切 O 照畫的順序疊。
 * `scale` ＝ 地圖縮放（CSS px／模型 px）：線寬 1.5 CSS px、襯邊 0.75 CSS px 換成貼圖 px 後量化 0.25。
 */
export function outlineTexture(unit: OclUnit, layers: NonNullable<OclEntry["layers"]>, src: OclSource, scale: number, memo: BandMemo): OutlineTex | null {
  const me = src.texImage(unit.body);
  if (me === null) return null;
  const { img } = me;
  const place = placeOf(unit, img);
  const texPerModel = 1 / place.sx;
  const width = outlineWidthTex(OUTLINE_CSS_PX, texPerModel, scale);
  const ink = outlineWidthTex(OUTLINE_INK_CSS_PX, texPerModel, scale);
  const clipLayers = layers.flatMap((l) => {
    const t = src.texImage(l.unit.body);
    return t === null ? [] : [{ img: t.img, place: placeOf(l.unit, t.img), big: l.big }];
  });
  const clip = clipMask(img.w, img.h, place, clipLayers);
  const bandKey = `${me.key}|w:${width}|i:${ink}`;
  return {
    key: `${bandKey}|c:${bitsHash(clip)}`,
    w: img.w,
    h: img.h,
    width,
    ink,
    make: () => {
      let band = memo.get(bandKey);
      if (band === undefined) {
        band = outlineBand(binaryMask(img), img.w, img.h, width, ink);
        memo.set(bandKey, band);
        while (memo.size > BAND_MEMO_CAP) {
          const first = memo.keys().next().value;
          if (first === undefined) break;
          memo.delete(first);
        }
      }
      return composeOutline(band, clip, ink);
    },
  };
}
