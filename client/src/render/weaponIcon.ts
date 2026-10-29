// 武器小圖示（Phase 3-18b、3T-4b；一輪中英雄面板用）：與地圖上小人手持的同一套 C 墨線畫法（`inkWeapons.drawInkWeaponAlone`），
// 武器 ID 不認得時依武器大類退回（`appearance.weaponLook`）。
// 3T-4b：先在暫時畫布上畫一次只量外框（不顯示），再依外框算出縮放，直接在圖示大小用向量重畫（不放大點陣圖）；
// 墨線寬度除以放大倍率（圖示上約 1.2px）、頭部太小的武器把頭放大（`inkStyle.iconHead`）、一律 45° 斜放（刃朝右上）。
import { weaponLook, type GearItem } from "./appearance";
import { pairedPart } from "./dollGear";
import { drawInkWeaponAlone } from "./inkWeapons";
import { withIconMode, withShadeDir, type IconMode } from "./inkStyle";
import { itemColors } from "./paperdoll";
import type { Ctx } from "./artDraw";

/** 量外框用的暫時畫布：虛擬大小與解析度倍率（武器最長約 60 個虛擬單位，頭放大後更長）。 */
const WORK = 160;
const WORK_RES = 3;
/** 外框離圖示邊緣的留白（兩側各 10％ → 外框的長邊佔圖示 80％）。 */
const PAD = 0.1;
/** 28px 圖示上的墨線寬（CSS 像素；其他尺寸等比）。墨線的基本寬 0.85 個虛擬單位。 */
const LINE_PX = 1.2;
const BASE_LINE = 0.85;
/** 頭部放大倍率（斧、錘、錘矛、鐮刀、杖頭）。 */
const HEAD_SCALE = 1.5;
/** 內部解析度倍率（canvas 實際像素 ＝ 邊長 × 2）。 */
const DPR = 2;
/** 槍弩的槍口朝 +x（畫的時候往右），要逆時針轉 45° 才朝右上；其餘（刃、柄、杖）朝上，順時針轉 45°。 */
const MUZZLE_RIGHT: ReadonlySet<string> = new Set(["pistol", "shotgun", "longgun", "crossbow"]);

/** 武器小圖示要畫的那一件裝備（供測試與繪製共用）。 */
export function weaponIconItem(weaponId: string | null | undefined, weaponClass: string | null | undefined): GearItem {
  const look = weaponLook(weaponId, weaponClass);
  return {
    kind: pairedPart(look.kind) ?? look.kind, // 成對武器（3I-4）畫成單把的造型
    material: look.material,
    ...(look.element !== undefined ? { element: look.element } : {}),
    ...(look.form !== undefined ? { form: look.form } : {}),
  };
}

/** 小圖示一律 45° 斜放（3T-4b；刃朝右上）。 */
export const isDiagonal = (kind: string): boolean => kind !== "pistol" && kind !== "fist";

/** 斜放的角度（弧度）：手槍不斜放（側面 L 形）、拳套正面直立（指虎，3T-4c）；其餘槍弩 -45°（槍口朝右上），其餘 +45°（刃、柄朝右上）。 */
export const iconAngle = (kind: string): number => (kind === "pistol" || kind === "fist" ? 0 : MUZZLE_RIGHT.has(kind) ? -Math.PI / 4 : Math.PI / 4);

function drawIcon(ctx: Ctx, item: GearItem, mode: IconMode): void {
  ctx.rotate(iconAngle(item.kind));
  withShadeDir(ctx, 1, () => withIconMode(ctx, mode, () => drawInkWeaponAlone(ctx, item, itemColors)));
}

interface Box {
  /** 外框中心（虛擬單位，原點＝手的位置）。 */
  cx: number;
  cy: number;
  /** 外框長邊（虛擬單位）。 */
  side: number;
}

/** 在暫時畫布上畫一次量出外框（只量，不顯示）。 */
function measure(item: GearItem): Box | null {
  const canvas = document.createElement("canvas");
  canvas.width = WORK * WORK_RES;
  canvas.height = WORK * WORK_RES;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (ctx === null) return null;
  ctx.scale(WORK_RES, WORK_RES);
  ctx.translate(WORK / 2, WORK / 2);
  drawIcon(ctx, item, { lineScale: 1, headScale: HEAD_SCALE });
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let x0 = canvas.width;
  let y0 = canvas.height;
  let x1 = -1;
  let y1 = -1;
  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      if ((data[(y * canvas.width + x) * 4 + 3] ?? 0) < 8) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  if (x1 < 0) return null;
  return {
    cx: (x0 + x1 + 1) / 2 / WORK_RES - WORK / 2,
    cy: (y0 + y1 + 1) / 2 / WORK_RES - WORK / 2,
    side: Math.max(x1 - x0 + 1, y1 - y0 + 1) / WORK_RES,
  };
}

const cache = new Map<string, HTMLCanvasElement>();

/** 邊長 `px` 的武器小圖示（內部解析度 ×2；同一件武器共用）。沒有 DOM 時回傳 `null`。 */
export function weaponIconCanvas(weaponId: string | null | undefined, weaponClass: string | null | undefined, px = 28): HTMLCanvasElement | null {
  return weaponItemIconCanvas(weaponIconItem(weaponId, weaponClass), px);
}

/** 同上，直接給裝備造型（開發用一覽頁不經過後端的武器對照表）。 */
export function weaponItemIconCanvas(item: GearItem, px = 28): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const key = `${px}|${item.kind}|${item.material ?? ""}|${item.element ?? ""}|${item.form ?? ""}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const box = measure(item);
  if (box === null) return null;
  const size = px * DPR;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  const k = (size * (1 - 2 * PAD)) / box.side;
  // 墨線寬 ＝ 目標像素寬 ÷ 放大倍率 ÷ 基本線寬（直接用向量畫，不放大點陣圖）
  const lineScale = (LINE_PX * (px / 28) * DPR) / (k * BASE_LINE);
  ctx.translate(size / 2, size / 2);
  ctx.scale(k, k);
  ctx.translate(-box.cx, -box.cy);
  drawIcon(ctx, item, { lineScale, headScale: HEAD_SCALE });
  cache.set(key, canvas);
  return canvas;
}
