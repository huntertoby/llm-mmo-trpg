// 裝備圖示產生器（Phase 3G-G5a；QI-1a／1b 起框裡的圖全部換成 Q 版小圖示，需求 docs/art/Q版小圖示-武器防具移植需求.md）。
// 純函式＋快取：外觀只由資料欄位決定（造型 kind × 形制 form × 材質 material（＋染色 dye）＋關鍵字 keywords ＋稀有度 rarity），
// 不認得的值一律退回預設、不丟例外；不用 Math.random。框（`frame()`）與關鍵字小圖樣（`motif()`）畫在 64 × 64 的虛擬格。
// 清單來自 content/equipment/appearance.yaml（匯出成 gearAppearance.json），色票在 artPalette.ts。
// 框裡的圖：武器、副手 `qIcon/weapons.ts`（QI-1a）；防具、飾品 `qIcon/armor.ts`（QI-1b）。舊的 `D` 表、`SCALE`、`palette()` 已拿掉（寶石色在 `qIcon/core.gemAccent`）。
// 只做 style: common；風格包等世界觀定案再說。顯示尺寸 ≤ 36px 不畫關鍵字小圖樣（第 5 層），快取鍵含是否小圖。
// 外觀的驗證（`resolveGear`、`gearKinds`、`GearLook`、`Resolved`）在 `gearResolve.ts`（QI-4b 搬出，避免 import 環），這裡 re-export。
import { GEAR_RARITY } from "./artPalette";
import { KEYWORD_COLOR } from "./palette";
import { blit, GEAR_PAD, ICON_RES, render, type Pt, type QDef } from "./qIcon/core";
import { qArmorDef, qArmorResolve } from "./qIcon/armor";
import { qResolve, qWeaponDef } from "./qIcon/weapons";
import { resolveGear, type GearLook, type Resolved } from "./gearResolve";

export { gearKinds, resolveGear, type GearLook, type Resolved } from "./gearResolve";

type Ctx = CanvasRenderingContext2D;

const TAU = Math.PI * 2;

// ---- 關鍵字小圖樣（畫在器物上，最多 2 個關鍵字、各 2 處）----
export function motif(ctx: Ctx, kw: string, x: number, y: number) {
  const kc = KEYWORD_COLOR[kw];
  if (kc === undefined) return; ctx.save(); ctx.fillStyle = kc; ctx.strokeStyle = kc; ctx.lineWidth = 1.6; ctx.lineCap = "round";
  switch (kw) {
    case "ignite": ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); break;
    case "wet": ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); break;
    case "charged": ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); break;
    case "frozen": ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); break;
    case "prone": ctx.beginPath(); ctx.moveTo(x - 4, y - 2); ctx.lineTo(x, y + 2); ctx.lineTo(x + 4, y - 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
    case "collision": ctx.beginPath(); for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU, r = i % 2 ? 2 : 5; ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } ctx.closePath(); ctx.fill(); break;
    case "marked": ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x - 4, y); ctx.moveTo(x + 4, y); ctx.lineTo(x + 6, y); ctx.moveTo(x, y - 6); ctx.lineTo(x, y - 4); ctx.moveTo(x, y + 4); ctx.lineTo(x, y + 6); ctx.stroke(); break;
    case "high_ground": ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x, y - 3); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
    case "concealed": ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(x - 2, y, 2.6, 0, TAU); ctx.arc(x + 2, y - 1, 3, 0, TAU); ctx.arc(x + 1, y + 2, 2.2, 0, TAU); ctx.fill(); break;
    case "poisoned": ctx.beginPath(); ctx.arc(x, y - 1, 3.2, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.moveTo(x - 2.5, y + 3); ctx.lineTo(x + 2.5, y + 6); ctx.moveTo(x + 2.5, y + 3); ctx.lineTo(x - 2.5, y + 6); ctx.stroke(); break;
    case "form": ctx.beginPath(); for (let i = -1; i <= 1; i++) { ctx.moveTo(x + i * 3 - 1.5, y - 5); ctx.lineTo(x + i * 3 + 1.5, y + 5); } ctx.stroke(); break;
    case "summon": ctx.beginPath(); ctx.arc(x, y - 1, 3.4, Math.PI, 0); ctx.lineTo(x + 3.4, y + 4); ctx.lineTo(x + 1.2, y + 2.5); ctx.lineTo(x, y + 4); ctx.lineTo(x - 1.2, y + 2.5); ctx.lineTo(x - 3.4, y + 4); ctx.closePath(); ctx.fill(); break;
  }
  ctx.restore();
}

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

/** 顯示尺寸 ≤ 這個值（px）就不畫關鍵字小圖樣。 */
export const SMALL_ICON_MAX_PX = 36;

/** 身上裝備格的圖示邊長（QI-1b D3；取代舊 CSS `min(48px, calc(100% - 4px))`）：外層格子內容寬（CSS px，可能是小數）減 4 取整數、最大 48、最小 1。 */
export const fitIconPx = (contentWidth: number): number => Math.max(1, Math.min(48, Math.floor(contentWidth - 4)));

/** 對齊裝置像素要挪的量（CSS px）：`Math.round(x × dpr) / dpr − x`（QI-2c，身上裝備格置中後左上角可能在小數位置；美術 PM QI-1b 驗收）。 */
export const pixelSnapNudge = (x: number, dpr: number): number => (dpr > 0 ? Math.round(x * dpr) / dpr - x : 0);
/** 座標在裝置像素上嗎（容許 0.01 裝置像素）。 */
export const onDevicePixel = (x: number, dpr: number): boolean => Math.abs(x * dpr - Math.round(x * dpr)) < 0.01;

/** 關鍵字小圖樣：每個關鍵字各一處（只有一個關鍵字時兩處都畫）；位置在 64 格座標。 */
function motifs(ctx: Ctx, keywords: readonly string[], spots: ReadonlyArray<readonly [number, number]>): void {
  keywords.forEach((kw, i) => {
    const s = spots[i % spots.length] as readonly [number, number];
    motif(ctx, kw, s[0], s[1]);
  });
  const only = keywords[0];
  const second = spots[1];
  if (keywords.length === 1 && only !== undefined && second !== undefined) motif(ctx, only, second[0], second[1]);
}

/** 這件裝備的 Q 版圖樣（武器、副手：`qIcon/weapons.ts`；防具、飾品：`qIcon/armor.ts`）。`resolveGear` 保證種類在清單內，兩邊都沒有時退直劍。 */
export function gearQDef(look: GearLook | null | undefined, r: Resolved): (QDef & { zh: string; meta: { spots: readonly [Pt, Pt] } }) | null {
  return qWeaponDef(qResolve(r, look?.element)) ?? qArmorDef(qArmorResolve(r)) ?? qWeaponDef(qResolve({ ...r, kind: "sword", form: "straight", material: "steel" }));
}

/** Q 版圖樣（需求 3.1 第 1、2 點、3.3 第 16 點、3.4 第 22 點）：圖樣邊長 px × (1 − 2 × GEAR_PAD)，用 `blit` 對齊整數裝置像素貼在四邊留 6% 的位置；
 *  > 36px 時照現行 `motif()` 疊關鍵字小圖樣，位置用 Q 版的 `meta.spots`（48 格）換算到框內。ctx 是 64 格座標、每格 px × res / 64 個裝置像素。 */
function drawQ(ctx: Ctx, look: GearLook | null | undefined, r: Resolved, small: boolean, px: number, res: number): void {
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
  if (!small) motifs(ctx, r.keywords, def.meta.spots.map(([x, y]) => [((p + (x * a) / 48) * 64) / px, ((p + (y * a) / 48) * 64) / px] as const));
}

/** 在 64 × 64 虛擬格上畫一件裝備。`small`：不畫關鍵字小圖樣（元素混色與稀有度外框照留）。
 *  `px`、`res`：顯示邊長（CSS px）與內部解析度——Q 版圖樣照這個尺寸出圖、對齊裝置像素。 */
export function drawGear(ctx: Ctx, look: GearLook | null | undefined, small = false, slot?: string, px = 64, res = ICON_RES): void {
  const r = resolveGear(look, slot);
  frame(ctx, r.rarity);
  drawQ(ctx, look, r, small, px, res);
}

/** 快取鍵：解析後的欄位＋元素（Q 版杖頭、法器珠的光球色）＋是否小圖＋像素大小＋內部解析度；與輸入物件的屬性順序無關，同樣的輸入產生同樣的字串。 */
export function gearIconKey(look: GearLook | null | undefined, px: number, slot?: string, res = ICON_RES): string {
  const r = resolveGear(look, slot);
  const small = px <= SMALL_ICON_MAX_PX;
  return [r.kind, r.form, r.material, r.dye ?? "-", r.keywords.join("+") || "-", look?.element ?? "-", r.rarity, r.style, small ? "s" : "l", px, res].join("|");
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
  drawGear(ctx, look, px <= SMALL_ICON_MAX_PX, slot, px, res);
  cache.set(key, canvas);
  return canvas;
}

/** 目前快取的圖示數（測試用）。 */
export const gearIconCacheSize = (): number => cache.size;
