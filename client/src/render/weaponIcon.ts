// 武器小圖示（米色圓章裡的圖；Phase 3-18b 起，QI-1a 換成 Q 版圖樣）：英雄面板 24、開局選武器與靶場武器架 20、元件預設 28。
// 圓章底是 CSS（`.weapon-icon`），這裡只畫圖樣：`resolveGear` → Q 版 `def`（`qIcon/weapons.ts`）→ `render(def, px × meta.badge, res, { ow: outlinePx(px), badge: true })`
// → 用 `blit` 照原尺寸、對齊整數裝置像素貼在 round(px × res) 的畫布正中（需求 docs/art/Q版小圖示-武器防具移植需求.md 3.1 第 1、5～7 點、3.2 第 9、10 點）。
// 成對武器（雙匕首、雙手槍）畫兩把，不再換成單把；方向已在畫法裡轉好（不再用 iconAngle／measure）。
import { weaponLook, type GearItem } from "./appearance";
import { resolveGear } from "./gearIcon";
import { blit, ICON_RES, outlinePx, render } from "./qIcon/core";
import { qResolve, qWeaponDef, type QResolved, type QWeaponDef } from "./qIcon/weapons";

export { ICON_RES };

/** 武器小圖示要畫的那一件裝備（供測試與繪製共用）。成對武器保留 `dual_*`（圖示畫兩把；人物另由 `dollGear.pairedPart` 換單把）。 */
export function weaponIconItem(weaponId: string | null | undefined, weaponClass: string | null | undefined): GearItem {
  const look = weaponLook(weaponId, weaponClass);
  return {
    kind: look.kind,
    material: look.material,
    ...(look.element !== undefined ? { element: look.element } : {}),
    ...(look.form !== undefined ? { form: look.form } : {}),
  };
}

/** 畫布邊長（裝置像素）＝ round(CSS px × 內部解析度)。 */
export const iconCanvasPx = (cssPx: number, res = ICON_RES): number => Math.round(cssPx * res);

/** 一件裝備 → `resolveGear`（唯一的驗證與預設來源）→ Q 版畫法要的欄位。 */
const qItem = (item: GearItem): QResolved => qResolve(resolveGear({ kind: item.kind, form: item.form ?? null, material: item.material ?? null, element: item.element ?? null }), item.element);

/** 這一件在圖示上畫的 Q 版圖樣（種類不是武器、副手時 `null`；測試與開發頁也用）。 */
export const weaponIconDef = (item: GearItem): QWeaponDef | null => qWeaponDef(qItem(item));

/** 快取鍵：解析後的 kind、form、material、keywords、element、rarity ＋ px、frame、res（需求 3.1 第 8 點；不含 color，D2）。與輸入屬性順序無關。 */
export function weaponIconKey(item: GearItem, px: number, res = ICON_RES): string {
  const q = qItem(item);
  return [q.kind, q.form, q.material, q.keywords.join("+") || "-", q.element ?? "-", q.rarity, px, "badge", res].join("|");
}

const cache = new Map<string, HTMLCanvasElement>();

/** 邊長 `px` 的武器小圖示（內部解析度 `res`，預設 2；同一件武器共用）。沒有 DOM 時回傳 `null`。 */
export function weaponIconCanvas(weaponId: string | null | undefined, weaponClass: string | null | undefined, px = 28, res = ICON_RES): HTMLCanvasElement | null {
  return weaponItemIconCanvas(weaponIconItem(weaponId, weaponClass), px, res);
}

/** 同上，直接給裝備造型（開發頁不經過後端的武器對照表）。 */
export function weaponItemIconCanvas(item: GearItem, px = 28, res = ICON_RES): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const key = weaponIconKey(item, px, res);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const def = weaponIconDef(item);
  const size = iconCanvasPx(px, res);
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  if (def !== null) {
    const a = px * def.meta.badge;
    const art = render(def, a, res, { ow: outlinePx(px), badge: true });
    if (art !== null) {
      ctx.scale(res, res);
      blit(ctx, art, (px - a) / 2, (px - a) / 2, a, res);
    }
  }
  cache.set(key, canvas);
  return canvas;
}
