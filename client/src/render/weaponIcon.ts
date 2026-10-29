// 武器小圖示（Phase 3-18b；一輪中英雄面板用）：與地圖上小人手持的同一套 C 墨線畫法（`inkWeapons.drawInkWeaponAlone`），
// 武器 ID 不認得時依武器大類退回（`appearance.weaponLook`）。畫好後量出實際佔用的範圍，等比放大填滿小圖示
// （劍、匕首轉成斜放），所以匕首與法杖看起來一樣大。
import { weaponLook, type GearItem } from "./appearance";
import { pairedPart } from "./dollGear";
import { drawInkWeaponAlone } from "./inkWeapons";
import { withShadeDir } from "./inkStyle";
import { itemColors } from "./paperdoll";

/** 暫時畫布的虛擬大小與解析度倍率（武器最長約 40 個虛擬單位）。 */
const WORK = 120;
const WORK_RES = 3;
/** 這些武器斜放（-45 度）；弓與杖直立。 */
const DIAGONAL: ReadonlySet<string> = new Set(["sword", "greatsword", "dagger", "axe", "hammer", "spear", "scythe", "whip"]);
const PAD = 0.08;

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

/** 斜放的武器種類。 */
export const isDiagonal = (kind: string): boolean => DIAGONAL.has(kind);

function workCanvas(item: GearItem): { canvas: HTMLCanvasElement; box: { x: number; y: number; w: number; h: number } } | null {
  const canvas = document.createElement("canvas");
  canvas.width = WORK * WORK_RES;
  canvas.height = WORK * WORK_RES;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (ctx === null) return null;
  ctx.scale(WORK_RES, WORK_RES);
  ctx.translate(WORK / 2, WORK / 2);
  if (isDiagonal(item.kind)) ctx.rotate(Math.PI / 4);
  withShadeDir(ctx, 1, () => drawInkWeaponAlone(ctx, item, itemColors));
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
  return { canvas, box: { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 } };
}

const cache = new Map<string, HTMLCanvasElement>();

/** 邊長 `px` 的武器小圖示（內部解析度 ×2；同一件武器共用）。沒有 DOM 時回傳 `null`。 */
export function weaponIconCanvas(weaponId: string | null | undefined, weaponClass: string | null | undefined, px = 28): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const item = weaponIconItem(weaponId, weaponClass);
  const key = `${px}|${item.kind}|${item.material ?? ""}|${item.element ?? ""}|${item.form ?? ""}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const work = workCanvas(item);
  if (work === null) return null;
  const size = px * 2;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  const { box } = work;
  const k = (size * (1 - 2 * PAD)) / Math.max(box.w, box.h);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(work.canvas, box.x, box.y, box.w, box.h, (size - box.w * k) / 2, (size - box.h * k) / 2, box.w * k, box.h * k);
  cache.set(key, canvas);
  return canvas;
}
