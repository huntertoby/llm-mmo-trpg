// 城鎮建築與門（Phase 6B-ART1；需求 docs/archive/art/Phase6剩餘美術移植需求.md 1.1、1.2）。
// 照樣張 docs/art/sample/explore.js 的 house()（白牆黛瓦）與 ashenTiles.js 的 scrapHouse()（廢鐵屋、鍛爐屋）移植。
// 全部程式繪製、確定性（沒有亂數，只依尺寸與門的位置）；座標是 52 虛擬單位一格（ART_T）。
// - 建築：範圍 w×h 格，畫在 w×(h+1) 的畫布上（屋頂往上多蓋 1 格）；立面在最下面 1.3 格（廢鐵屋 1.2 格）。
// - 門：另外一個節點（門框＋門洞＋門板），門板可以轉開（`doorOpenness`，doorClips.ts）；入口光圈畫在門前一格。
// - 招牌只畫圖示，不寫字。
import { dot, TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";

const U = 52;
const OUT = "#1c1712";
const C = {
  slate: "#7d8c84",
  ink: "#56645c",
  red: "#b8432f",
  redDark: "#8a2f20",
  tile: "#3c4a48",
  mist: "#e8e8e0",
  lamp: "#ffcf6a",
  wood: "#8a6440",
} as const;
const A = { iron: "#5a5e60", rust: "#9a4a20", rag: "#c8b08a", hot: "#ffb030" } as const;

/** 認得的建築外觀（6B-ART1；主城的 stone_hall、mentor_hall、tent、fountain 是 6D-ART2，畫法在 capitalArt.ts）。 */
export const BUILDING_KINDS = ["tavern", "smithy", "hall", "house", "scrap_house", "forge_house", "stone_hall", "mentor_hall", "tent", "fountain"] as const;
export type BuildingKind = (typeof BUILDING_KINDS)[number];

/** 不認得的 `kind` 退回 `house`（需求 1.1）。 */
export function buildingKind(kind: string): BuildingKind {
  return (BUILDING_KINDS as readonly string[]).includes(kind) ? (kind as BuildingKind) : "house";
}

/** 門的樣式：白牆屋舍是木門，廢鐵屋是布簾門。 */
export type DoorStyle = "wood" | "rag";
export function doorStyleOf(kind: BuildingKind): DoorStyle {
  return kind === "scrap_house" || kind === "forge_house" ? "rag" : "wood";
}

export type SignIcon = "jar" | "anvil" | "scroll";
/** 種類固定的招牌（霧渡鎮的白牆屋舍）；`DOOR_SIGN_KINDS` 的種類改照門通往的室內設施（伺服器的 `sign`）。 */
const SIGN: Readonly<Record<BuildingKind, SignIcon | null>> = {
  tavern: "jar",
  smithy: "anvil",
  hall: "scroll",
  house: null,
  scrap_house: null,
  forge_house: null,
  stone_hall: null,
  mentor_hall: null,
  tent: null,
  fountain: null,
};

/** 招牌照門通往的室內設施決定的種類（6D-ART2；開發 PM 補充 2：廢鐵屋、鍛爐屋也照這個）。沒有門＝不掛。 */
export const DOOR_SIGN_KINDS: ReadonlySet<BuildingKind> = new Set<BuildingKind>(["scrap_house", "forge_house", "stone_hall", "mentor_hall"]);

/** 這種建築的招牌：照門的種類用伺服器的 `sign`（沒有＝不掛）；其他種類回傳 `undefined`（照種類的表）。 */
export function signFromView(kind: BuildingKind, sign: string | null | undefined): SignIcon | null | undefined {
  if (!DOOR_SIGN_KINDS.has(kind)) return undefined;
  return sign === "jar" || sign === "anvil" || sign === "scroll" ? sign : null;
}

/** 一棟建築的畫法輸入：外觀、寬高（格）、門所在的欄（相對建築左邊，0 起算；畫在最下一列）。 */
export interface BuildingSpec {
  kind: BuildingKind;
  w: number;
  h: number;
  doors: readonly number[];
  /** 屋頂往上多蓋幾列；省略＝`ROOF_ROWS`。屋後那一列站著 NPC、設施、情境物件或傳送石時是 0（開發 PM 補充 1）。 */
  roof?: number;
  /** 招牌；省略＝照種類的表，`null`＝不掛。 */
  sign?: SignIcon | null;
}

/** 屋頂往上多蓋的列數（預設）。 */
export const ROOF_ROWS = 1;

/** 這棟的屋頂往上多蓋幾列。 */
export function roofRows(s: BuildingSpec): number {
  return s.roof ?? ROOF_ROWS;
}

/** 這棟的招牌圖示（沒有＝`null`）。 */
export function signOf(s: BuildingSpec): SignIcon | null {
  return s.sign !== undefined ? s.sign : SIGN[s.kind];
}

export function buildingArtKey(s: BuildingSpec): string {
  const roof = roofRows(s) === ROOF_ROWS ? "" : `|r${roofRows(s)}`;
  const sign = s.sign === undefined ? "" : `|s${s.sign ?? "-"}`;
  return `bld|${s.kind}|${s.w}x${s.h}|${s.doors.join(".")}${roof}${sign}`;
}

/** 門的中心（格，相對建築左邊）；沒有門的建築在正中央畫一扇關著的裝飾門。 */
export function doorCenters(s: BuildingSpec): number[] {
  return s.doors.length > 0 ? s.doors.map((d) => d + 0.5) : [s.w / 2];
}

/**
 * 窗戶的中心（格）：由左到右，離每扇門左邊至少 1 格、右邊至少 2 格（右邊掛招牌；沒有招牌時 1 格），
 * 相鄰的窗至少隔 1 格。
 */
export function windowCenters(s: BuildingSpec): number[] {
  const right = signOf(s) === null ? 1 : 2;
  const doors = doorCenters(s);
  const out: number[] = [];
  let last = -10;
  for (let k = 0; k < s.w; k++) {
    const c = k + 0.5;
    if (!doors.every((d) => c - d <= -1 || c - d >= right)) continue;
    if (k - last < 2) continue;
    out.push(c);
    last = k;
  }
  return out;
}

export function box(ctx: Ctx, x: number, y: number, w: number, h: number, fill: string, stroke: string | null = OUT, lw = 2, r = 2): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke !== null) {
    ctx.lineWidth = lw;
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
}

export function shadow(ctx: Ctx, cx: number, cy: number, rx: number, ry: number, a = 0.3): void {
  ctx.fillStyle = `rgba(0,0,0,${a})`;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fill();
}

export function glow(ctx: Ctx, x: number, y: number, r: number, c: string, a: number): void {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, c);
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.save();
  ctx.globalAlpha = a;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/** 招牌、壁爐共用的小圖示（explore.js 的 ICON）。 */
export const ICON = {
  anvil(ctx: Ctx, x: number, y: number, s: number): void {
    ctx.fillStyle = "#5a5e64";
    ctx.beginPath();
    ctx.moveTo(x - s * 0.7, y - s * 0.3);
    ctx.lineTo(x + s * 0.6, y - s * 0.3);
    ctx.lineTo(x + s * 0.3, y);
    ctx.lineTo(x + s * 0.2, y + s * 0.1);
    ctx.lineTo(x + s * 0.4, y + s * 0.5);
    ctx.lineTo(x - s * 0.4, y + s * 0.5);
    ctx.lineTo(x - s * 0.2, y + s * 0.1);
    ctx.lineTo(x - s * 0.3, y - s * 0.05);
    ctx.closePath();
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  },
  jar(ctx: Ctx, x: number, y: number, s: number): void {
    ctx.fillStyle = "#8a5a30";
    ctx.beginPath();
    ctx.ellipse(x, y + s * 0.15, s * 0.45, s * 0.45, 0, 0, TAU);
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    ctx.fillStyle = C.red;
    ctx.fillRect(x - s * 0.25, y - s * 0.5, s * 0.5, s * 0.25);
    ctx.strokeRect(x - s * 0.25, y - s * 0.5, s * 0.5, s * 0.25);
  },
  scroll(ctx: Ctx, x: number, y: number, s: number): void {
    box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.8, "#f2e6c8", OUT, 1.5, 1);
    ctx.fillStyle = C.redDark;
    ctx.fillRect(x - s * 0.6, y - s * 0.5, s * 1.2, s * 0.15);
    ctx.fillRect(x - s * 0.6, y + s * 0.35, s * 1.2, s * 0.15);
    ctx.strokeStyle = "#8a7a5a";
    ctx.lineWidth = 1;
    for (const k of [-0.15, 0, 0.15]) {
      ctx.beginPath();
      ctx.moveTo(x - s * 0.3, y + s * k);
      ctx.lineTo(x + s * 0.3, y + s * k);
      ctx.stroke();
    }
  },
  rest(ctx: Ctx, x: number, y: number, s: number): void {
    ctx.fillStyle = "#ff8a2a";
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.55);
    ctx.quadraticCurveTo(x + s * 0.45, y, x, y + s * 0.4);
    ctx.quadraticCurveTo(x - s * 0.45, y, x, y - s * 0.55);
    ctx.fill();
    ctx.fillStyle = "#ffd23a";
    ctx.beginPath();
    ctx.ellipse(x, y + s * 0.12, s * 0.15, s * 0.25, 0, 0, TAU);
    ctx.fill();
  },
} as const;

/** 掛在門右邊的招牌（只畫圖示）。`dark` ＝ 廢鐵屋的深色框。 */
export function sign(ctx: Ctx, x: number, y: number, icon: SignIcon, dark = false): void {
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x - 10, y);
  ctx.lineTo(x + 10, y);
  ctx.stroke();
  box(ctx, x - 12, y + 2, 24, 22, dark ? "#3a2a1e" : "#5a3a24", OUT, 2, 3);
  box(ctx, x - 9, y + 5, 18, 16, "#f2e6c8", null, 0, 2);
  ICON[icon](ctx, x, y + 13, 13);
}

/** 燈籠的高度（畫布 px）：燈籠框從 `y` 到 `y + LANTERN_H`。 */
export const LANTERN_H = 13;

/**
 * 酒館屋簷下燈籠的中心（6Q-1）：畫布 px，原點在建築畫布左上（屋頂那一列，`52` px 一格）。
 * 畫燈籠（`whiteHouse`）和畫光暈（`ambientLayer.drawLights`）共用這一個公式，立面高度改了也不會對不準。
 * 只有白牆屋舍的酒館有燈籠；其他種類回傳空陣列。
 */
export function lanternCenters(s: BuildingSpec): { x: number; y: number }[] {
  if (s.kind !== "tavern" || doorStyleOf(s.kind) === "rag") return [];
  const faceTop = (s.h + roofRows(s) - 1.3) * U;
  return windowCenters(s).map((wx) => ({ x: wx * U, y: faceTop + 2 + LANTERN_H / 2 }));
}

/** 建築畫布一格的 px（`lanternCenters` 的單位）。 */
export const BUILDING_ART_T = U;

export function lantern(ctx: Ctx, x: number, y: number): void {
  ctx.save();
  ctx.shadowColor = C.lamp;
  ctx.shadowBlur = 10;
  box(ctx, x - 5, y, 10, LANTERN_H, C.red, OUT, 1.5, 4);
  ctx.restore();
  ctx.fillStyle = C.lamp;
  ctx.fillRect(x - 2, y + 3, 4, 7);
}

/** 煙囪冒的煙（靜態的三團灰煙）。 */
function smoke(ctx: Ctx, x: number, y: number): void {
  for (const [dx, dy, r, a] of [
    [0, 0, 6, 0.55],
    [5, -9, 7, 0.42],
    [12, -19, 8, 0.3],
  ] as const) {
    ctx.fillStyle = `rgba(200,200,196,${a})`;
    ctx.beginPath();
    ctx.arc(x + dx, y + dy, r, 0, TAU);
    ctx.fill();
  }
}

/** 白牆黛瓦的屋舍（explore.js 的 house；酒館、鐵匠鋪、導師堂、民宅）。畫布 w×(h+1) 格，原點在屋頂那一列的左上。 */
function whiteHouse(ctx: Ctx, s: BuildingSpec): void {
  const H = s.h + roofRows(s);
  const W = s.w * U;
  const faceTop = (H - 1.3) * U;
  const faceH = 1.3 * U;
  shadow(ctx, W / 2 + 6, H * U - 4, W / 2, 8, 0.35);
  box(ctx, 4, faceTop, W - 8, faceH - 4, C.mist, "#1f2a28", 2, 2); // 白牆立面
  ctx.fillStyle = "rgba(0,0,0,0.08)";
  ctx.fillRect(6, faceTop + faceH - 18, W - 12, 12);
  box(ctx, 4, faceTop + faceH - 10, W - 8, 6, C.ink, "#1f2a28", 1.5, 1); // 牆基
  // 屋頂：深色瓦，前簷翹起
  ctx.beginPath();
  ctx.moveTo(-0 + 2, faceTop + 6);
  ctx.lineTo(8, 4);
  ctx.lineTo(W - 8, 4);
  ctx.lineTo(W - 2, faceTop + 6);
  ctx.quadraticCurveTo(W / 2, faceTop - 2, 2, faceTop + 6);
  ctx.closePath();
  ctx.fillStyle = C.tile;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#141c1a";
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.12)";
  ctx.lineWidth = 1.2;
  for (let k = 12; k < W - 8; k += 7) {
    ctx.beginPath();
    ctx.moveTo(k, 6);
    ctx.lineTo(k + (k - W / 2) * 0.04, faceTop + 2);
    ctx.stroke();
  }
  box(ctx, 6, 2, W - 12, 5, "#2a3634", "#141c1a", 1.5, 2); // 屋脊
  if (s.kind === "tavern") {
    ctx.fillStyle = C.red; // 朱紅邊
    ctx.fillRect(6, faceTop + 4, W - 12, 3);
  }
  const lit = s.kind === "tavern";
  const windows = windowCenters(s);
  for (const wx of windows) {
    const x = wx * U;
    box(ctx, x - 9, faceTop + 18, 18, 14, "#3a2a1e", "#1f2a28", 1.5, 1);
    ctx.strokeStyle = "#8a6a44";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, faceTop + 18);
    ctx.lineTo(x, faceTop + 32);
    ctx.stroke();
    if (lit) {
      ctx.fillStyle = rgba(C.lamp, 0.55);
      ctx.fillRect(x - 7, faceTop + 20, 14, 10);
    }
  }
  if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0]! * U, H * U, "wood");
  const icon = signOf(s);
  if (icon !== null) sign(ctx, doorCenters(s)[0]! * U + 20, faceTop + 6, icon);
  for (const l of lanternCenters(s)) lantern(ctx, l.x, l.y - LANTERN_H / 2);
  if (s.kind === "smithy") {
    const cx = W - 26;
    box(ctx, cx - 6, faceTop - 30, 12, 26, "#5a5450", OUT, 1.6, 1);
    smoke(ctx, cx, faceTop - 36);
  }
}

/** 廢鐵屋（ashenTiles.js 的 scrapHouse）：鏽鐵板拼的牆＋斜鐵皮屋頂；鍛爐屋多一根冒火光的煙囪。 */
function scrapHouse(ctx: Ctx, s: BuildingSpec): void {
  const H = s.h + roofRows(s);
  const W = s.w * U;
  const faceTop = (H - 1.2) * U;
  shadow(ctx, W / 2 + 6, H * U - 4, W / 2, 8, 0.4);
  const n = s.w * 3;
  for (let k = 0; k < n; k++) {
    box(ctx, 4 + (k * (W - 8)) / n, faceTop, (W - 8) / n + 1, 1.2 * U - 4, shade(k % 2 ? A.iron : A.rust, 0.85 + (k % 3) * 0.08), OUT, 1.4, 1);
  }
  for (let k = 0; k < s.w * 2; k++) dot(ctx, 10 + (k * (W - 20)) / (s.w * 2 - 1), faceTop + 6, 1.4, "#c8b8a0");
  ctx.beginPath();
  ctx.moveTo(0, faceTop + 4);
  ctx.lineTo(8, 6);
  ctx.lineTo(W - 2, 14);
  ctx.lineTo(W - 2, faceTop + 6);
  ctx.closePath();
  ctx.fillStyle = shade(A.iron, 0.8);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.strokeStyle = "rgba(0,0,0,0.35)";
  ctx.lineWidth = 1.2;
  for (let k = 14; k < W - 4; k += 12) {
    ctx.beginPath();
    ctx.moveTo(k, 8 + k * 0.03);
    ctx.lineTo(k - 6, faceTop + 4);
    ctx.stroke();
  }
  if (s.doors.length === 0) closedDoor(ctx, doorCenters(s)[0]! * U, H * U, "rag");
  if (s.kind === "forge_house") {
    box(ctx, W - 24, 2, 10, 26, A.iron, OUT, 1.6, 1);
    glow(ctx, W - 19, 6, 16, "rgba(255,140,60,0.9)", 0.6);
    dot(ctx, W - 19, 4, 2.5, A.hot);
  }
  const icon = signOf(s);
  if (icon !== null) sign(ctx, doorCenters(s)[0]! * U + 22, faceTop + 2, icon, true);
}

/** 一棟建築（不含門板；門是另外的節點）。 */
export function drawBuilding(ctx: Ctx, s: BuildingSpec): void {
  if (doorStyleOf(s.kind) === "rag") scrapHouse(ctx, s);
  else whiteHouse(ctx, s);
}

/** 沒有門格的建築正面畫一扇關著的門（純裝飾，沒有入口光圈）；`bottom` ＝ 建築底邊的 y。 */
export function closedDoor(ctx: Ctx, cx: number, bottom: number, style: DoorStyle): void {
  doorFrame(ctx, cx, bottom, style);
  doorPanel(ctx, cx - DOOR_W / 2, bottom, style);
}

// ---------------- 門（另一個節點，可以轉開）----------------

/** 門洞的寬、高與底邊離格子底邊的距離（52 單位）。 */
export const DOOR_W = 24;
export const DOOR_H = 30;
export const DOOR_FOOT = 6;

/** 門框與門洞（暗）；`bottom` ＝ 格子底邊的 y。 */
export function doorFrame(ctx: Ctx, cx: number, bottom: number, style: DoorStyle): void {
  const top = bottom - DOOR_FOOT - DOOR_H;
  box(ctx, cx - DOOR_W / 2 - 3, top - 3, DOOR_W + 6, DOOR_H + 3, style === "rag" ? "#3a2e26" : "#5a3a24", OUT, 2, 2);
  ctx.fillStyle = "#14100c";
  ctx.fillRect(cx - DOOR_W / 2, top, DOOR_W, DOOR_H);
  const g = ctx.createLinearGradient(0, top, 0, top + DOOR_H);
  g.addColorStop(0, "rgba(255,207,106,0.0)");
  g.addColorStop(1, "rgba(255,207,106,0.28)");
  ctx.fillStyle = g;
  ctx.fillRect(cx - DOOR_W / 2, top, DOOR_W, DOOR_H);
  if (style === "wood") {
    ctx.fillStyle = C.red;
    ctx.fillRect(cx - DOOR_W / 2 - 3, top - 3, DOOR_W + 6, 4);
  }
}

/** 門板（關著的樣子）：左緣是門軸，`x0` ＝ 門軸的 x。 */
export function doorPanel(ctx: Ctx, x0: number, bottom: number, style: DoorStyle): void {
  const top = bottom - DOOR_FOOT - DOOR_H;
  if (style === "rag") {
    box(ctx, x0, top, DOOR_W, DOOR_H, A.rag, OUT, 1.6, 2);
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    for (const k of [6, 12, 18]) ctx.fillRect(x0 + k, top + 2, 1.5, DOOR_H - 4);
    return;
  }
  box(ctx, x0, top, DOOR_W, DOOR_H, "#4a3020", "#1f2a28", 2, 2);
  ctx.strokeStyle = "rgba(0,0,0,0.35)";
  ctx.lineWidth = 1;
  for (const k of [8, 16]) {
    ctx.beginPath();
    ctx.moveTo(x0 + k, top + 3);
    ctx.lineTo(x0 + k, top + DOOR_H - 3);
    ctx.stroke();
  }
  dot(ctx, x0 + DOOR_W - 5, top + DOOR_H * 0.55, 1.8, "#e8bb48");
}

/** 門前的入口光圈（explore.js 的 entrance）：中心在 (cx, cy)。 */
export function entrance(ctx: Ctx, cx: number, cy: number): void {
  ctx.save();
  ctx.globalAlpha = 0.85;
  const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, 22);
  g.addColorStop(0, "rgba(255,230,160,0.55)");
  g.addColorStop(1, "rgba(255,230,160,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(cx, cy, 22, 13, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,230,160,0.9)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.ellipse(cx, cy, 16, 9, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

/** 門板轉開 `open`（0 關～1 開）時的水平縮放（門軸在左緣，往內轉開只剩一條邊）。 */
export function doorPanelScale(open: number): number {
  const o = Math.max(0, Math.min(1, open));
  return 1 - 0.85 * o;
}
