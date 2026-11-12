// 裝備圖示產生器（Phase 3G-G5a；QI-1a／1b 起框裡的圖全部換成 Q 版小圖示，需求 docs/art/Q版小圖示-武器防具移植需求.md）。
// 純函式＋快取：外觀只由資料欄位決定（造型 kind × 形制 form × 材質 material（＋染色 dye）＋關鍵字 keywords ＋稀有度 rarity），
// 不認得的值一律退回預設、不丟例外；不用 Math.random。框（`frame()`）畫在 64 × 64 的虛擬格。
// 清單來自 content/equipment/appearance.yaml（匯出成 gearAppearance.json），色票在 artPalette.ts。
// 框裡的圖：武器、副手 `qIcon/weapons.ts`（QI-1a）；防具、飾品 `qIcon/armor.ts`（QI-1b）。舊的 `D` 表、`SCALE`、`palette()` 已拿掉（寶石色在 `qIcon/core.gemAccent`）。
// 關鍵字層（QI-4b，需求 docs/art/Q版小圖示-關鍵字移植需求.md）：角落一個 Q 版關鍵字小圓章（第一個關鍵字）＋第二個關鍵字的點版記號，
// 畫法在 `qIcon/keywords.ts` 的 `paint`；顯示尺寸 ≥ `KEYWORD_CHIP_MIN_PX`（32）才畫。舊的器物上細線小圖樣 `motif()`／`motifs()` 已拿掉
// （開發頁 `dev/keywordGallery.ts` 的 `set=legacy` 另抄一份給對照）。快取鍵已有 `px`，不再另帶「是否小圖」。
// 只做 style: common；風格包等世界觀定案再說。
// 外觀的驗證（`resolveGear`、`gearKinds`、`GearLook`、`Resolved`）在 `gearResolve.ts`（QI-4b 搬出，避免 import 環），這裡 re-export。
import { GEAR_RARITY } from "./artPalette";
import { blit, GEAR_PAD, ICON_RES, render, type Pt, type QDef } from "./qIcon/core";
import { qArmorDef, qArmorResolve } from "./qIcon/armor";
import { qResolve, qWeaponDef } from "./qIcon/weapons";
import * as KW from "./qIcon/keywords";
import { resolveGear, type GearLook, type Resolved } from "./gearResolve";

export { gearKinds, resolveGear, type GearLook, type Resolved } from "./gearResolve";

type Ctx = CanvasRenderingContext2D;

// ---- 外框（稀有度）----
function frame(ctx: Ctx, rarity: string): void {
  const c = GEAR_RARITY[rarity] as string;
  ctx.fillStyle = "#23262d";
  ctx.beginPath();
  ctx.roundRect(2, 2, 60, 60, 9);
  ctx.fill();
  if (rarity === "epic" || rarity === "legendary") {
    const g = ctx.createRadialGradient(32, 32, 4, 32, 32, 34);
    g.addColorStop(0, `${c}66`);
    g.addColorStop(1, `${c}00`);
    ctx.fillStyle = g;
    ctx.fill();
  }
  ctx.lineWidth = rarity === "legendary" ? 3.5 : 2.5;
  ctx.strokeStyle = c;
  ctx.beginPath();
  ctx.roundRect(2, 2, 60, 60, 9);
  ctx.stroke();
  if (rarity !== "common") {
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.moveTo(50, 3.5);
    ctx.lineTo(60.5, 3.5);
    ctx.lineTo(60.5, 14);
    ctx.closePath();
    ctx.fill();
  }
  if (rarity === "legendary") {
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.roundRect(6, 6, 52, 52, 6);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}

/** 顯示尺寸 ≥ 這個值（px）才畫關鍵字小圓章（需求 1.3 第 1 點；QI-4 第 0 節第 4 列）。`fit` 在比 800 更窄時可能 < 32，照美術建議不畫。 */
export const KEYWORD_CHIP_MIN_PX = 32;

/** 身上裝備格的圖示邊長（QI-1b D3；取代舊 CSS `min(48px, calc(100% - 4px))`）：外層格子內容寬（CSS px，可能是小數）減 4 取整數、最大 48、最小 1。 */
export const fitIconPx = (contentWidth: number): number => Math.max(1, Math.min(48, Math.floor(contentWidth - 4)));

/** 對齊裝置像素要挪的量（CSS px）：`Math.round(x × dpr) / dpr − x`（QI-2c，身上裝備格置中後左上角可能在小數位置；美術 PM QI-1b 驗收）。 */
export const pixelSnapNudge = (x: number, dpr: number): number => (dpr > 0 ? Math.round(x * dpr) / dpr - x : 0);
/** 座標在裝置像素上嗎（容許 0.01 裝置像素）。 */
export const onDevicePixel = (x: number, dpr: number): boolean => Math.abs(x * dpr - Math.round(x * dpr)) < 0.01;

/** 這件裝備的 Q 版圖樣（武器、副手：`qIcon/weapons.ts`；防具、飾品：`qIcon/armor.ts`）。`resolveGear` 保證種類在清單內，兩邊都沒有時退直劍。 */
export function gearQDef(look: GearLook | null | undefined, r: Resolved): (QDef & { zh: string; meta: { spots: readonly [Pt, Pt]; diag?: boolean; r: { kind: string; form: string } } }) | null {
  return qWeaponDef(qResolve(r, look?.element)) ?? qArmorDef(qArmorResolve(r)) ?? qWeaponDef(qResolve({ ...r, kind: "sword", form: "straight", material: "steel" }));
}

/** Q 版圖樣（需求 3.1 第 1、2 點、3.3 第 16 點、3.4 第 22 點）：圖樣邊長 px × (1 − 2 × GEAR_PAD)，用 `blit` 對齊整數裝置像素貼在四邊留 6% 的位置；
 *  `chips` 時再疊關鍵字層（`qIcon/keywords.ts` 的 `paint`：角落一個圓章＋點版記號；角與記號方向由造型 `def` 決定，同樣張）。
 *  ctx 是 64 格座標、每格 px × res / 64 個裝置像素；兩層都換成 CSS px 座標（每單位 res 個裝置像素）再畫。 */
function drawQ(ctx: Ctx, look: GearLook | null | undefined, r: Resolved, chips: boolean, px: number, res: number): void {
  const def = gearQDef(look, r);
  if (def === null) return;
  const p = px * GEAR_PAD;
  const a = px - 2 * p;
  const art = render(def, a, res);
  if (art !== null) {
    ctx.save();
    ctx.scale(64 / px, 64 / px); // 換成 CSS px 座標（每單位 res 個裝置像素）
    blit(ctx, art, p, p, a, res);
    ctx.restore();
  }
  if (chips && r.keywords.length > 0) {
    ctx.save();
    ctx.scale(64 / px, 64 / px);
    KW.paint(ctx, r.keywords, px, res, { def });
    ctx.restore();
  }
}

/** 在 64 × 64 虛擬格上畫一件裝備。`chips`：畫不畫關鍵字層（小圓章＋點版記號；false 時元素混色與稀有度外框照留）。
 *  `px`、`res`：顯示邊長（CSS px）與內部解析度——Q 版圖樣與關鍵字圓章照這個尺寸出圖、對齊裝置像素。 */
export function drawGear(ctx: Ctx, look: GearLook | null | undefined, chips = true, slot?: string, px = 64, res = ICON_RES): void {
  const r = resolveGear(look, slot);
  frame(ctx, r.rarity);
  drawQ(ctx, look, r, chips, px, res);
}

/** 快取鍵：解析後的欄位＋元素（Q 版杖頭、法器珠的光球色）＋像素大小＋內部解析度；與輸入物件的屬性順序無關，同樣的輸入產生同樣的字串。
 *  畫不畫關鍵字層只由 `px` 決定（`KEYWORD_CHIP_MIN_PX`），鍵裡已有 `px`，所以 QI-4b 拿掉了「是否小圖」那一欄。 */
export function gearIconKey(look: GearLook | null | undefined, px: number, slot?: string, res = ICON_RES): string {
  const r = resolveGear(look, slot);
  return [r.kind, r.form, r.material, r.dye ?? "-", r.keywords.join("+") || "-", look?.element ?? "-", r.rarity, r.style, px, res].join("|");
}

const cache = new Map<string, HTMLCanvasElement>();

/** 邊長 `px` 的裝備圖示（畫布 round(px × res) 裝置像素，res 預設 2；相同外觀共用）。沒有 DOM 時回傳 `null`。 */
export function gearIconCanvas(look: GearLook | null | undefined, px = 64, slot?: string, res = ICON_RES): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const key = gearIconKey(look, px, slot, res);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const size = Math.round(px * res);
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(size / 64, size / 64);
  ctx.lineJoin = "round";
  drawGear(ctx, look, px >= KEYWORD_CHIP_MIN_PX, slot, px, res);
  cache.set(key, canvas);
  return canvas;
}

/** 目前快取的圖示數（測試用）。 */
export const gearIconCacheSize = (): number => cache.size;
