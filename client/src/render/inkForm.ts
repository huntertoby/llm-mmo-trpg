// 形態外觀（Phase 3J-5；QK-3 起換成 Q 版：docs/art/sample/qForm.js，畫法在 qForm.ts，圖 docs/art/shots/misc/q-summons-forms.png）。
// 規則見 docs/archive/art/形態外觀.md 的「定稿方向」：10 種全部另畫、帶主角主色、比同類召喚物大一號（`size`）、元素化身與龍吃元素色；
// 腳下形態光環＝陣營底圈（unitSprite）＋藍紫外環＋刻點，平塗不發光（外光只代表頭目）。
// 不認得的形態 id 由呼叫端退回原角色紙娃娃＋光環。座標：腳底 (0,0)、往上是 -y。確定性：不用亂數。
import type { Facing } from "../api/types";
import type { Ctx } from "./artDraw";
import { isHex } from "./color";
import { elementTintColors } from "./palette";
import { DOLL_SCALE } from "./paperdoll";
import { drawQFormBody, drawQFormRing, qFormShadowRx } from "./qForm";
import { groundShadow, layer } from "./qSummonCore";

/** 無元素的光環色（光環貼圖快取鍵用；Q 版光環固定藍紫，不吃元素色）。 */
export const FORM_AURA_NEUTRAL = "#9a86ff";
/** 找不到身體裝備顏色與披風顏色時的主角主色（陣營藍）。 */
export const FORM_HERO_FALLBACK = "#4f7fbf";

/** 形態認得的元素（`palette.ts`，物理與不認得的算「沒有元素」）；回傳元素 id。 */
const elementOf = (el: string | null | undefined): string | null => (elementTintColors(el) === undefined ? null : (el ?? null));

/** 光環色（快取鍵）：認得的元素用元素色，其餘（無元素、不認得的元素）用 #9a86ff。 */
export function formAuraColor(element: string | null | undefined): string {
  const el = elementOf(element);
  return el === null ? FORM_AURA_NEUTRAL : (elementTintColors(el)?.primary ?? FORM_AURA_NEUTRAL);
}

interface FormArt {
  zh: string;
  /** 大小倍率（同 qForm.js）。 */
  size: number;
  /** 畫出來的最高點（腳底往上，未套大小、含外框 1.3）；頭頂狀態列要避開。 */
  top: number;
}

/** 10 種形態（鍵 ＝ 畫法 id；`top` ＝ qForm.ts 各畫法的最高點＋外框）。 */
export const FORM_ARTS: Readonly<Record<string, FormArt>> = {
  bear: { zh: "熊", size: 1.3, top: 37.6 },
  werewolf: { zh: "狼人", size: 1.25, top: 46.3 },
  dragon: { zh: "龍", size: 1.5, top: 47.3 },
  cat: { zh: "貓", size: 1.25, top: 26.3 },
  roc: { zh: "鳥", size: 1.2, top: 48.3 },
  demon: { zh: "惡魔", size: 1.2, top: 47.3 },
  giant: { zh: "巨人", size: 1.45, top: 45.7 },
  avatar: { zh: "元素化身", size: 1.2, top: 48.3 },
  shadow: { zh: "暗影形態", size: 1.2, top: 41.3 },
  treant: { zh: "樹人", size: 1.3, top: 47 },
};

/** 形態外觀 id（`FormView.look`，內容檔 `forms.yaml` 的 `look`）→ 畫法 id。 */
export const FORM_LOOKS: Readonly<Record<string, string>> = {
  form_bear: "bear",
  form_cat: "cat",
  form_roc: "roc",
  form_elemental: "avatar",
  form_werewolf: "werewolf",
  form_demon: "demon",
  form_giant: "giant",
  form_shadow: "shadow",
  form_treant: "treant",
  form_dragon: "dragon",
};

/** 外觀 id → 畫法；不認得（含空值）回傳 `null`，呼叫端退回原角色紙娃娃＋光環。 */
export function formArtOf(look: string | null | undefined): { id: string; art: FormArt } | null {
  if (look === null || look === undefined || !Object.hasOwn(FORM_LOOKS, look)) return null;
  const id = FORM_LOOKS[look];
  const art = id === undefined ? undefined : FORM_ARTS[id];
  return id === undefined || art === undefined ? null : { id, art };
}

/** 形態小人的畫面縮放（相對 52px 虛擬格）：QK-3 照樣張和主角同一個縮放 × size（龍寬不超過 1.5 格）。 */
export function formScale(art: FormArt): number {
  return DOLL_SCALE * art.size;
}

/** 戰場陣營底圈的半徑（52px 虛擬格單位，unitSprite 的 T × 0.36）。 */
const TEAM_RING = 52 * 0.36;

/**
 * 光環（藍紫外環）半徑（52px 虛擬格單位）：樣張內環 13（龍 16）× max(1, size × 0.9) × 小人縮放，至少和陣營底圈一樣大，再往外 2.6。
 * 不認得的形態用陣營底圈＋2.6。
 */
export function formAuraRadius(look: string | null | undefined, doll: number): number {
  const f = formArtOf(look);
  const inner = f === null ? 0 : (f.id === "dragon" ? 16 : 13) * Math.max(1, f.art.size * 0.9) * doll;
  return Math.max(TEAM_RING, inner) + 2.6 * doll;
}

/** 頭頂狀態列要比一般小人再往上移多少（畫面像素，≥ 0）：形態比小人高出的部分；`tile` ＝ 格子像素、`doll` ＝ 小人縮放、`humanTop` ＝ 小人最高點。 */
export function formRowRise(look: string | null | undefined, tile: number, doll: number, humanTop = 44): number {
  const f = formArtOf(look);
  if (f === null) return 0;
  const k = tile / 52;
  return Math.max(0, f.art.top * formScale(f.art) * k - humanTop * doll * k);
}

/** 主角主色：身體裝備 color → 披風 color → 陣營藍；不是 #rrggbb 的值跳過。 */
export function formHeroColor(bodyColor?: string, cloakColor?: string): string {
  for (const c of [bodyColor, cloakColor]) if (c !== undefined && isHex(c)) return c;
  return FORM_HERO_FALLBACK;
}

/** 形態光環（Q 版平塗）：藍紫外環（半徑 rx）＋8 個刻點；陣營藍環由戰場的陣營底圈畫。`color` 只是快取鍵（Q 版不吃元素色）。 */
export function drawFormAura(ctx: Ctx, _color: string, rx: number): void {
  drawQFormRing(ctx, rx - 2.6, false);
}

/** 倒地：整個形態橫躺（頭朝右），躺在腳底附近。 */
function lieDown(ctx: Ctx, art: FormArt): void {
  ctx.translate(-art.top * 0.45, -art.top * 0.2);
  ctx.rotate(Math.PI / 2);
}

/**
 * 畫一個形態（原點 ＝ 腳底；單位 ＝ 紙娃娃單位，未套大小）：影子＋形態本體（不描外框）。
 * 側面形態（熊、貓、鳥、龍）朝西與朝北鏡像；正面形態朝東、朝西眼睛偏移、朝北畫背面。
 * 光環另外畫（`drawFormAura`），因為不認得的形態也要有光環。不認得的 id 回傳 `false`、什麼都不畫。
 * `ground` ＝ false 時不畫地上的影子（6C-8 受擊白閃用的身體）。
 */
export function drawForm(ctx: Ctx, id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean, ground = true, outline = false): boolean {
  const art = Object.hasOwn(FORM_ARTS, id) ? FORM_ARTS[id] : undefined;
  if (art === undefined) return false;
  ctx.save();
  if (downed) lieDown(ctx, art);
  else if (ground) groundShadow(ctx, qFormShadowRx(id), 0.2, id === "roc" ? 0.22 : 0.3);
  if (outline) layer(ctx, [-50, -84, 50, 14], (g) => void drawQFormBody(g, id, hero, element, facing), { ow: 1.3 / art.size, ...(id === "shadow" ? { fade: [0, -8] as const } : {}) });
  else drawQFormBody(ctx, id, hero, element, facing);
  ctx.restore();
  return true;
}

/** 形態貼圖畫布（寬於小人，免得龍的尾巴與吐息被切掉）。腳底在 (FORM_W/2, FORM_FOOT_Y)。 */
export const FORM_W = 104;
export const FORM_H = 92;
export const FORM_FOOT_Y = FORM_H - 8;
/** 光環貼圖畫布（中心 ＝ 橢圓中心）。 */
export const AURA_W = 72;
export const AURA_H = 28;

/** 形態貼圖的快取鍵。 */
export function formKey(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean): string {
  return `${id}|${hero}|${elementOf(element) ?? "-"}|${facing}|${downed ? "down" : "up"}`;
}

/** 產生形態離屏 canvas（`dpr` 倍解析度；`dollScale` ＝ 小人縮放，畫面比例以它為基準）；沒有 DOM 或不認得的形態回傳 `null`。`ground` 同 `drawForm`。 */
export function renderFormCanvas(id: string, hero: string, element: string | null | undefined, facing: Facing, downed: boolean, dpr: number, dollScale: number, ground = true): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const art = Object.hasOwn(FORM_ARTS, id) ? FORM_ARTS[id] : undefined;
  if (art === undefined) return null;
  const c = document.createElement("canvas");
  c.width = FORM_W * dpr;
  c.height = FORM_H * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  ctx.translate(FORM_W / 2, FORM_FOOT_Y);
  const k = formScale(art) / dollScale;
  ctx.scale(k, k);
  drawForm(ctx, id, hero, element, facing, downed, ground, true);
  return c;
}

/** 產生光環離屏 canvas（原點在中心；`rx` 為 52px 虛擬格單位）；沒有 DOM 時回傳 `null`。 */
export function renderAuraCanvas(color: string, rx: number, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = AURA_W * dpr;
  c.height = AURA_H * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  ctx.translate(AURA_W / 2, AURA_H / 2);
  drawFormAura(ctx, color, Math.min(rx, AURA_W / 2 - 2));
  return c;
}
