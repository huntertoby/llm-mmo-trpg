// NPC 頭像（Phase 6C-7；QK-2 換成 Q 版：docs/art/sample/qPortrait.js，需求 docs/art/QK移植需求.md 第 3 節）：
// Q 版紙娃娃正面的頭和肩膀放大（每 42 單位對應邊長、頭心在 0.53），加上只畫在頭像上的配件（qPortrait.ts，畫在體型座標裡）與圓角框。
// 框色依區域（RT-1／RT-4 定的框色照舊；主城＝RT-1 的晶紫 #a898ff〔QK-2b〕；沒有區域＝傭兵金），底色同色系漸層（三區底色照 QK-2 樣張）。白狐霜音另外畫一張狐臉。
// 好感五級（21.5）：`level` 0～4 換眼、眉、嘴（null／2＝普通）。沒有頭像資料時畫通用剪影。
// 確定性：沒有亂數，同一位每次畫都一樣；離屏畫好依（鍵、大小）快取成圖片網址。
import type { NpcPortrait } from "../api/types";
import { resolveDoll, type DollSpec } from "./appearance";
import { type Ctx, TAU } from "./artDraw";
import { drawMoodBadge, drawQPortraitFigure, Q_PORTRAIT_EXTRAS, QP_HEAD_Y, QP_UNITS, type QPortraitFigure } from "./qPortrait";
import { GAME_HOOKS, qUnitOf } from "./qSpec";
import { isFox, portraitDollLook, portraitRaceLook } from "../world/npcLook";

/** 區域 → [框色, 底色深, 底色淺]。 */
export const PORTRAIT_REGION: Readonly<Record<string, readonly [string, string, string]>> = {
  cloud_ridge: ["#6aa84a", "#2f4a3a", "#8ab890"],
  ashen_waste: ["#ff6a1a", "#3a2418", "#b07050"],
  // RT-4（#131）：傭兵出身的另外三區（docs/art/sample/merc-portraits.html；框色＝RT-1 的 portrait_ring）
  crystal_crown: ["#8ab0ff", "#26304a", "#9aaad8"],
  arcane_hub: ["#4ad0c8", "#1e3236", "#6aa0a0"],
  frost_tide: ["#6ac0e8", "#1e3448", "#7aa8c8"],
  // QK-2b（美術 PM，docs/art/QK-2檢查.md 第 4 節）：主城框色＝RT-1 設定檔（region_themes.yaml）capital 的 portrait_ring 晶紫；
  // 底色用樣張主城的紫灰（qPortrait.js REGION.capital）
  capital: ["#a898ff", "#2a2a44", "#7a7aa8"],
  merc: ["#c8a868", "#2a2a3a", "#8a8aa8"],
};
const REGION_FALLBACK = PORTRAIT_REGION["merc"]!;

/** 頭像的三種大小（事件卡、字幕與對話泡泡、HUD 與清單）。 */
export const PORTRAIT_SIZES = { card: 96, line: 48, chip: 28 } as const;

/** 說書人的頭像（兜帽長袍；事件卡的對話框用）。 */
export const NARRATOR_PORTRAIT: NpcPortrait = {
  look: { skin: "#e8c8a8", hair: "none", beard: true, hair_color: "#d8d0c0" },
  gear: { body: { kind: "robe", color: "#4a3a5a", trim: "#e8bb48" }, head: { kind: "hood", color: "#3a2e48" } },
  extras: [],
} as NpcPortrait;

/** 頭像配件的名稱（Q 版 23 個，含白狐 fox；其他值略過）。 */
export const PORTRAIT_EXTRAS = Q_PORTRAIT_EXTRAS;

/** 通用剪影（沒有頭像資料時）：深色頭肩（6T-1c 起不寫「?」），Q 版座標（頭心 (0,−29)）。 */
function drawSilhouette(ctx: Ctx): void {
  ctx.fillStyle = "rgba(20,16,12,0.72)";
  ctx.beginPath();
  ctx.arc(0, -29, 8.8, 0, TAU);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(-13, -4);
  ctx.quadraticCurveTo(-12, -19.6, 0, -20);
  ctx.quadraticCurveTo(12, -19.6, 13, -4);
  ctx.closePath();
  ctx.fill();
}

/** 頭像的人：NpcPortrait → Q 版紙娃娃（主手不畫；副手只在頭像資料有寫時畫）＋配件。 */
export function portraitFigure(portrait: NpcPortrait, level: number | null = null): QPortraitFigure {
  const spec = resolveDoll({ template: "portrait", dollLook: portraitDollLook(portrait, false), team: "ally", summon: false, weaponId: "unarmed", weaponClass: "melee", raceLook: portraitRaceLook(portrait) });
  delete spec.gear.main_hand;
  if ((portrait.gear as Record<string, unknown> | null | undefined)?.["off_hand"] == null) delete spec.gear.off_hand;
  return { unit: qUnitOf(spec), extras: portrait.extras ?? [], level };
}

/** 任意紙娃娃外觀的頭像（種族卡等）：不畫武器。 */
export function specFigure(spec: DollSpec, extras: readonly string[] = [], level: number | null = null): QPortraitFigure {
  const s: DollSpec = { ...spec, gear: { ...spec.gear } };
  delete s.gear.main_hand;
  delete s.gear.off_hand;
  return { unit: qUnitOf(s), extras, level };
}

/** 畫頭像框（底色、人物、框線）；`who`＝null 畫通用剪影。 */
export function drawPortraitFrame(ctx: Ctx, x: number, y: number, size: number, who: QPortraitFigure | null, region: string | null | undefined): void {
  const [frame, bgD, bgL] = (region != null ? PORTRAIT_REGION[region] : undefined) ?? REGION_FALLBACK;
  ctx.save();
  ctx.translate(x, y);
  ctx.beginPath();
  ctx.roundRect(0, 0, size, size, size * 0.14);
  ctx.save();
  ctx.clip();
  const g = ctx.createLinearGradient(0, 0, 0, size);
  g.addColorStop(0, bgL);
  g.addColorStop(1, bgD);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  if (who === null) {
    const k = size / QP_UNITS;
    ctx.save();
    ctx.translate(size / 2, size * QP_HEAD_Y + 29 * k);
    ctx.scale(k, k);
    drawSilhouette(ctx);
    ctx.restore();
  } else drawQPortraitFigure(ctx, size, who, GAME_HOOKS);
  ctx.restore();
  // 外框：區域色＋墨線（同樣張）
  const lw = Math.max(2, size * 0.04);
  ctx.lineWidth = lw;
  ctx.strokeStyle = frame;
  ctx.beginPath();
  ctx.roundRect(lw / 2, lw / 2, size - lw, size - lw, size * 0.13);
  ctx.stroke();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#1c1712";
  ctx.beginPath();
  ctx.roundRect(0.5, 0.5, size - 1, size - 1, size * 0.14);
  ctx.stroke();
  ctx.restore();
}

/** 不帶框的頭像下緣漸隱的比例（樣張 `heroBare`：肩膀以下 22% 由實到透明）。 */
export const PORTRAIT_BARE_FADE = 0.22;

/**
 * 不帶底色與框的頭像（PNL-2；資訊面板-移植需求 2.3「外觀與種族」分頁圖示、第 5 節第 11 點）：同 `drawPortraitFrame` 的人物（頭＋肩、
 * 剪影外框照舊），不畫區域色底與框線，下緣 22% 漸隱。畫在 (0, 0) 起、邊長 `size`；漸隱用 `destination-in`，所以要畫在自己的離屏畫布上。
 */
export function drawPortraitBare(ctx: Ctx, size: number, who: QPortraitFigure): void {
  ctx.save();
  drawQPortraitFigure(ctx, size, who, GAME_HOOKS);
  ctx.restore();
  ctx.save();
  ctx.globalCompositeOperation = "destination-in";
  const g = ctx.createLinearGradient(0, size * (1 - PORTRAIT_BARE_FADE), 0, size);
  g.addColorStop(0, "#000");
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  ctx.restore();
}

/** 頭像畫在 (x, y) 起、邊長 `size` 的框裡。`portrait` 為 `null` 時畫通用剪影；`level`＝好感 0～4（null＝普通）。 */
export function drawPortrait(ctx: Ctx, x: number, y: number, size: number, portrait: NpcPortrait | null | undefined, region: string | null | undefined, level: number | null = null): void {
  const who = portrait == null ? null : isFox(portrait) ? { unit: { look: { skin: "#f6f2ea" }, gear: {} }, extras: ["fox"] } : portraitFigure(portrait, level);
  drawPortraitFrame(ctx, x, y, size, who, region);
}

const cache = new Map<string, string>();

/** 頭像的快取鍵（外觀內容＋區域＋大小）；同樣的外觀共用一張。 */
export function portraitKey(portrait: NpcPortrait | null | undefined, region: string | null | undefined, size: number, level: number | null = null): string {
  return `${size}|${region ?? ""}|${level ?? ""}|${portrait == null ? "-" : JSON.stringify(portrait)}`;
}

/** 頭像的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。 */
export function portraitUrl(portrait: NpcPortrait | null | undefined, region: string | null | undefined, size: number, dpr = 2, level: number | null = null): string | null {
  if (typeof document === "undefined") return null;
  const key = `${portraitKey(portrait, region, size, level)}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = size * dpr;
  c.height = size * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawPortrait(ctx, 0, 0, size, portrait, region, level);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}

const moodCache = new Map<string, string>();

/** 頭頂好感徽章的圖片網址（Q 版，level 0～4；沒有 DOM 時為 `null`）。 */
export function moodBadgeUrl(level: number, size: number, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${level}|${size}|${dpr}`;
  const hit = moodCache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = c.height = Math.ceil(size * dpr);
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  // 外框線寬 r×0.16（至少 1.2）：半徑扣掉半條線，整個徽章落在 size 裡
  const r = size / 2 - Math.max(0.6, size * 0.04);
  drawMoodBadge(ctx, size / 2, size / 2, r, level);
  const url = c.toDataURL("image/png");
  moodCache.set(key, url);
  return url;
}
