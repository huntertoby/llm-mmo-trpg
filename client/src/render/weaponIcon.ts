// 武器小圖示（Phase 3-18b；一輪中英雄面板用）：與地圖上小人手持的同一套畫法（`paperdoll.drawWeaponAlone`），
// 武器 ID 不認得時依武器大類退回（`appearance.weaponLook`）。
import { weaponLook, type GearItem } from "./appearance";
import { drawWeaponAlone } from "./paperdoll";

/** 小圖示的虛擬畫布：握把在 (HALF, BASE)，武器往上最高約 30。 */
const VIRTUAL = 40;
const BASE = 36;

/** 武器小圖示要畫的那一件裝備（供測試與繪製共用）。 */
export function weaponIconItem(weaponId: string | null | undefined, weaponClass: string | null | undefined): GearItem {
  const look = weaponLook(weaponId, weaponClass);
  return { kind: look.kind, material: look.material, ...(look.element !== undefined ? { element: look.element } : {}) };
}

/** 把武器畫到 `ctx`（虛擬座標 40×40）。 */
export function paintWeaponIcon(ctx: CanvasRenderingContext2D, item: GearItem): void {
  ctx.save();
  ctx.translate(VIRTUAL / 2, BASE);
  ctx.translate(0, 9.5); // drawWeapon 內部會往上移 9.5：還原成握把在原點
  drawWeaponAlone(ctx, item);
  ctx.restore();
}

const cache = new Map<string, HTMLCanvasElement>();

/** 邊長 `px` 的武器小圖示（內部解析度 ×2；同一件武器共用）。沒有 DOM 時回傳 `null`。 */
export function weaponIconCanvas(weaponId: string | null | undefined, weaponClass: string | null | undefined, px = 28): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const item = weaponIconItem(weaponId, weaponClass);
  const key = `${px}|${item.kind}|${item.material ?? ""}|${item.element ?? ""}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = px * 2;
  canvas.height = px * 2;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale((px * 2) / VIRTUAL, (px * 2) / VIRTUAL);
  paintWeaponIcon(ctx, item);
  cache.set(key, canvas);
  return canvas;
}
