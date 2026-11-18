// 戰前佈置的格子記號（AR-SK3；移植需求 docs/art/SK-3-移植需求.md 第 1 節第 5 項，美術 SK-3-美術.md 第 4 節、5.3）：
// 取代暫借的選目標紅框。照 docs/art/sample/sk3Mechanics.js 第 2 版的 `placeMark`／`placeBurst` 逐行搬（畫在畫面 px，s＝一格的畫面邊長）：
// - 待放：淡金底（13～18% 呼吸）＋四角金色括號（1.2 秒一次往內收）＋中央一顆金菱形；
// - 指著：整圈金框＋底 30%＋要放的東西的半透明預覽（68%；陷阱＝`fieldFx.drawTrapPad`、刻印＝`terrainLayer.drawRunes` 那段、表面＝部件圖樣）；
// - 放下：0～420 ms 金框往外擴 25%、淡出＋四角四顆金四芒火花。
// 滑過提示「放在這裡」（玩法 PM 定案）：格子右邊一個小提示框（深藍底、金色細框、米白 12 px）。
// 確定性：沒有亂數；動畫只吃 t（毫秒）。
import { drawTrapPad } from "./fieldFx";
import { OUT, poly, starPts } from "./qIcon/core";
import * as QP from "./qIcon/parts";

const TAU = Math.PI * 2;
export const PLACE = { gold: "#ffd23f", hi: "#fff3b0", fill: "255,210,63" } as const;
/** 放下的一下有多長（毫秒）。 */
export const PLACE_BURST_MS = 420;
/** 滑過提示（玩法 PM 定案的字，移植需求第 2 節）。 */
export const PREP_TIP_ZH = "放在這裡";
/** 預覽的透明度。 */
export const GHOST_ALPHA = 0.68;
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";

export type PlaceState = "idle" | "hover";
export type PlaceKind = "trap" | "rune" | "surface";
/** 預覽畫法：中心 (x,y)、一格邊長 s（畫面 px）。 */
export type Ghost = (g: CanvasRenderingContext2D, x: number, y: number, s: number) => void;

const ease = (t: number): number => {
  const u = Math.max(0, Math.min(1, t));
  return u * u * (3 - 2 * u);
};

/** 一格的佈置記號（左上 x,y、邊長 s 畫面 px）。 */
export function placeMark(g: CanvasRenderingContext2D, x: number, y: number, s: number, state: PlaceState, t: number, ghost: Ghost | null = null): void {
  const pulse = 0.5 - 0.5 * Math.cos(((t % 1200) / 1200) * TAU), w = Math.max(2, s * 0.06), i = s * 0.09 + pulse * Math.max(1, s * 0.02), L = s * 0.27, r = s * 0.12;
  g.save();
  g.fillStyle = `rgba(${PLACE.fill},${state === "hover" ? 0.3 : 0.13 + 0.05 * pulse})`;
  g.beginPath();
  g.roundRect(x + s * 0.06, y + s * 0.06, s * 0.88, s * 0.88, r);
  g.fill();
  const corner = (col: string, ww: number): void => {
    g.strokeStyle = col;
    g.lineWidth = ww;
    g.lineCap = "round";
    g.lineJoin = "round";
    for (const [sx, sy] of [[0, 0], [1, 0], [1, 1], [0, 1]] as const) {
      const cx = sx ? x + s - i : x + i, cy = sy ? y + s - i : y + i, dx = sx ? -1 : 1, dy = sy ? -1 : 1;
      g.beginPath();
      g.moveTo(cx, cy + dy * L);
      g.lineTo(cx, cy + dy * r * 0.5);
      g.quadraticCurveTo(cx, cy, cx + dx * r * 0.5, cy);
      g.lineTo(cx + dx * L, cy);
      g.stroke();
    }
  };
  if (state === "hover") {
    g.beginPath();
    g.roundRect(x + i, y + i, s - 2 * i, s - 2 * i, r);
    g.strokeStyle = OUT;
    g.lineWidth = w + 2;
    g.stroke();
    g.strokeStyle = PLACE.gold;
    g.lineWidth = w;
    g.stroke();
    g.strokeStyle = PLACE.hi;
    g.lineWidth = Math.max(1, w * 0.3);
    g.beginPath();
    g.roundRect(x + i + w * 0.15, y + i + w * 0.15, s - 2 * i - w * 0.3, s - 2 * i - w * 0.3, r);
    g.stroke();
  } else {
    corner(OUT, w + 2);
    corner(PLACE.gold, w);
  }
  if (state === "hover" && ghost !== null) {
    g.globalAlpha = GHOST_ALPHA;
    ghost(g, x + s / 2, y + s / 2, s);
    g.globalAlpha = 1;
  } else if (state !== "hover") {
    const d = Math.max(3, s * 0.1), cx = x + s / 2, cy = y + s / 2;
    const dia = (h: number): void => {
      g.beginPath();
      g.moveTo(cx, cy - h);
      g.lineTo(cx + h, cy);
      g.lineTo(cx, cy + h);
      g.lineTo(cx - h, cy);
      g.closePath();
    };
    dia(d + 1.2);
    g.fillStyle = OUT;
    g.fill();
    dia(d);
    g.fillStyle = PLACE.gold;
    g.fill();
    g.beginPath();
    g.moveTo(cx, cy - d);
    g.lineTo(cx - d, cy);
    g.lineTo(cx, cy);
    g.closePath();
    g.fillStyle = PLACE.hi;
    g.fill();
  }
  g.restore();
}

/** 放下的一下（p＝0～1）：金框從格子往外擴 25%、淡出；四角各一顆金四芒火花往外飛。 */
export function placeBurst(g: CanvasRenderingContext2D, x: number, y: number, s: number, p: number): void {
  if (p <= 0 || p >= 1) return;
  const e = ease(p), k = 1 + 0.25 * e, cx = x + s / 2, cy = y + s / 2, h = s * 0.44 * k, w = Math.max(2, s * 0.06);
  g.save();
  g.globalAlpha = 1 - e;
  g.beginPath();
  g.roundRect(cx - h, cy - h, 2 * h, 2 * h, s * 0.14);
  g.strokeStyle = OUT;
  g.lineWidth = w + 2;
  g.stroke();
  g.strokeStyle = PLACE.gold;
  g.lineWidth = w;
  g.stroke();
  for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const) {
    const R = Math.max(3, s * 0.1) * (1 - 0.4 * e), px = cx + sx * (h + s * 0.08 * e), py = cy + sy * (h + s * 0.08 * e);
    poly(g, PLACE.gold, starPts(px, py, R, R * 0.36, 4), 0.3);
    poly(g, "#ffffff", starPts(px, py, R * 0.55, R * 0.2, 4));
  }
  g.restore();
}

/** 預覽的灰（沒有元素：同陷阱踏板的 GRAY）與我方陣營色。 */
const GRAY = "#d8d8e0";
const TEAM = "#5aa0ff";

/** 陷阱預覽：現行陷阱踏板（我方、踩到觸發、沒有元素）。 */
export const ghostTrap: Ghost = (g, x, y, s) => {
  g.save();
  g.translate(x - s / 2, y - s / 2);
  g.scale(s / 52, s / 52);
  drawTrapPad(g, { mine: true, trigger: "enter", color: GRAY });
  g.restore();
};
/** 刻印預覽：現行地面符文（`terrainLayer.drawRunes` 那段：菱形外框＝我方陣營色、淡填色＋內菱形＋四端刻痕）。 */
export const ghostRune: Ghost = (g, x, y, s) => {
  const k = s / 48, half = 48 * 0.3 * k;
  const dia = (h: number): void => {
    g.beginPath();
    g.moveTo(x, y - h);
    g.lineTo(x + h, y);
    g.lineTo(x, y + h);
    g.lineTo(x - h, y);
    g.closePath();
  };
  const a0 = g.globalAlpha;
  g.save();
  dia(half);
  g.globalAlpha = a0 * 0.18;
  g.fillStyle = GRAY;
  g.fill();
  g.globalAlpha = a0 * 0.95;
  g.lineWidth = 2 * k;
  g.strokeStyle = TEAM;
  g.stroke();
  dia(half * 0.5);
  g.globalAlpha = a0 * 0.75;
  g.fillStyle = GRAY;
  g.fill();
  g.beginPath();
  for (const [ux, uy] of [[0, -1], [1, 0], [0, 1], [-1, 0]] as const) {
    g.moveTo(x + ux * half * 0.62, y + uy * half * 0.62);
    g.lineTo(x + ux * half, y + uy * half);
  }
  g.lineWidth = 1.5 * k;
  g.strokeStyle = GRAY;
  g.globalAlpha = a0 * 0.9;
  g.stroke();
  g.restore();
};
/** 表面預覽：那種表面的部件圖樣（現行沒有表面的畫法，照樣張先用部件圖樣示意）。 */
export const ghostSurface =
  (surface: string): Ghost =>
  (g, x, y, s) => {
    const px = Math.round(s * 0.62), cv = QP.glyph("surface", surface, px, 2);
    if (cv !== null) g.drawImage(cv, x - (px * QP.BOX) / 2, y - (px * QP.BOX) / 2, px * QP.BOX, px * QP.BOX);
  };
export function ghostOf(kind: PlaceKind, surface: string | null): Ghost {
  return kind === "trap" ? ghostTrap : kind === "rune" ? ghostRune : ghostSurface(surface ?? "water");
}

/** 滑過提示框的大小（畫面 px）。 */
export function tipSize(g: CanvasRenderingContext2D, text = PREP_TIP_ZH): { w: number; h: number } {
  g.save();
  g.font = `500 12px ${FONT}`;
  const w = Math.ceil(g.measureText(text).width) + 14;
  g.restore();
  return { w: w + 6, h: 22 };
}
export type TipSide = "right" | "left";

/**
 * SK-3b（美術 AR-SK3 驗收）：提示框放格子哪一邊。預設右邊；右邊會超出地圖右緣時翻到左邊。
 * `cellX`＝格子左緣、`cell`＝一格寬、`tipW`＝提示框寬（含小三角）、`mapRight`＝地圖右緣，單位一致即可。
 * 回傳那一邊與提示框的左緣。
 */
export function tipPlacement(cellX: number, cell: number, tipW: number, mapRight: number): { side: TipSide; x: number } {
  const right = cellX + cell;
  if (right + tipW <= mapRight) return { side: "right", x: right };
  return { side: "left", x: cellX - tipW };
}

/** 滑過提示「放在這裡」：左上 (x,y)（畫面 px）；小三角指向格子（`side` 是提示框在格子的哪一邊）。 */
export function placeTip(g: CanvasRenderingContext2D, x: number, y: number, text = PREP_TIP_ZH, side: TipSide = "right"): void {
  g.save();
  g.font = `500 12px ${FONT}`;
  const w = Math.ceil(g.measureText(text).width) + 14, h = 22, bx = side === "right" ? x + 5 : x;
  const edge = side === "right" ? bx + 0.5 : bx + w + 0.5, tipX = side === "right" ? bx - 4 : bx + w + 5;
  g.beginPath();
  g.roundRect(bx + 0.5, y + 0.5, w, h, 4);
  g.fillStyle = "rgba(24,27,42,0.94)";
  g.fill();
  g.strokeStyle = "#c9a65a";
  g.lineWidth = 1;
  g.stroke();
  g.beginPath();
  g.moveTo(edge, y + h / 2 - 4);
  g.lineTo(tipX, y + h / 2);
  g.lineTo(edge, y + h / 2 + 4);
  g.closePath();
  g.fillStyle = "#c9a65a";
  g.fill();
  g.fillStyle = "#eadfcc";
  g.textBaseline = "middle";
  g.fillText(text, bx + 7.5, y + h / 2 + 0.5);
  g.restore();
}
