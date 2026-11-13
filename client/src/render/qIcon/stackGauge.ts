// KW-3：HUD 層數計量（#161 的四種層數：連擊 5 格、怒氣 4 格、專注 3 格、氣 3 格）。
// 照 docs/art/sample/qIconsKW.js 第 2 版的 ④（`MAX`、`PIP.a`、`HUD_FILL`、`pip`、`gaugeW`、`gaugeOuter`、`gauge`、`gaugeCanvas`）逐行搬；
// 紀錄 docs/art/KW樣張.md 第 4、6、7 節。只搬採用的 A 案（通用斜切段：格 6×10、右傾 2px、步距 7、右內距 5），不搬 B 案與第 1 版 `a1`。
// 膠囊（照 status-card.css 的 .stat-chip：高 22、底 #1a1410、框 #5a4a38、圓角 11、左內距 4）畫在畫布裡；滿層的外暈（shadowBlur 5）也畫在畫布裡，
// 所以畫布四邊各多留 4px（同樣張 `gaugeCanvas`），版面用負邊距收回（`ui/StackPips.tsx`）。
import { blank, ctxOf, ICON_RES, mix, OUT, qCanvasAvailable, TAU, type Ctx } from "./core";
import { chip } from "./keywords";
import { KEYWORD_COLOR } from "../palette";

/** 每種層數的格數（＝`content/stacks.yaml` 的上限；`qIconKW3.test.ts` 對照內容）。 */
export const GAUGE_MAX: Readonly<Record<string, number | undefined>> = { combo_point: 5, fury: 4, focus: 3, ki: 3 };
/** 有計量的層數（其他層數照舊用 `StackBadge`）。 */
export const hasGauge = (id: string): boolean => GAUGE_MAX[id] !== undefined;
const SLOT = "#2a2418", SLOT_EDGE = "#5a4a38", CAP_BG = "#1a1410";
/** 格子（A 案通用斜切段）：寬 6、高 10、步距 7（間距 1）、膠囊右內距 5。 */
export const PIP = { w: 6, h: 10, step: 7, padR: 5 } as const;
const pipPath = (c: Ctx, x: number, y: number, w: number, h: number): void => { c.moveTo(x + 2, y); c.lineTo(x + w, y); c.lineTo(x + w - 2, y + h); c.lineTo(x, y + h); c.closePath(); };
/** 亮格的本色：怒氣亮一階 #ff4a62（第 2 版 K6）；其他同關鍵字色。膠囊框、外暈、圓章仍用關鍵字色。 */
export const HUD_FILL: Readonly<Record<string, string | undefined>> = { combo_point: "#ff3d8b", fury: "#ff4a62", focus: "#476deb", ki: "#29e0bc" };
/** 膠囊高（CSS px）與畫布四邊多留的外暈空間。 */
export const GAUGE_H = 22, GAUGE_PAD = 4;
/** 一格：外形先填外框色（亮格）或槽框色（暗格），再往內縮 1 裝置像素填本色；亮格加上緣亮條與下緣暗條。 */
function pip(c: Ctx, x: number, y: number, on: boolean, full: boolean, col: string, res: number): void {
  const P = PIP, u = 1 / res, path = (k: number) => { c.beginPath(); const cx = x + P.w / 2, cy = y + P.h / 2, sx = (P.w - 2 * k) / P.w, sy = (P.h - 2 * k) / P.h; c.save(); c.translate(cx, cy); c.scale(sx, sy); c.translate(-cx, -cy); pipPath(c, x, y, P.w, P.h); c.restore(); };
  path(0); c.fillStyle = on ? OUT : SLOT_EDGE; c.fill();
  path(u); c.fillStyle = on ? (full ? mix(col, "#ffffff", 0.28) : col) : SLOT; c.fill();
  if (on) { c.save(); path(u); c.clip(); c.fillStyle = full ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.45)"; c.fillRect(x, y, P.w, Math.max(2 * u, Math.round(P.h * 0.28 * res) / res)); c.fillStyle = "rgba(0,0,0,0.22)"; c.fillRect(x, y + P.h - 2 * u, P.w, 2 * u); c.restore(); }
}
/** 圓章 14＋間距 3＋格子（不含膠囊）。 */
export const gaugeW = (id: string): number => 14 + 3 + ((GAUGE_MAX[id] ?? 0) - 1) * PIP.step + PIP.w;
/** 含膠囊的外寬：左內距 4＋`gaugeW`＋右內距 5（連擊 60、怒氣 53、專注與氣 46）。 */
export const gaugeOuter = (id: string): number => 4 + gaugeW(id) + PIP.padR;
/** 在 (x,y) 畫一個層數膠囊（左上角；高 22）：n＝目前層數（超過上限當滿層）。回傳膠囊寬。 */
export function gauge(c: Ctx, id: string, n: number, x: number, y: number, res: number): number {
  const max = GAUGE_MAX[id] ?? 0, full = n >= max, col = KEYWORD_COLOR[id]!, fill = HUD_FILL[id] ?? col, W = gaugeOuter(id), H = GAUGE_H;
  c.save();
  if (full) { c.save(); c.shadowColor = col; c.shadowBlur = 5 * res; c.fillStyle = col; c.beginPath(); c.roundRect(x, y, W, H, 11); c.fill(); c.restore(); }
  c.fillStyle = full ? col : SLOT_EDGE; c.beginPath(); c.roundRect(x, y, W, H, 11); c.fill();
  c.fillStyle = CAP_BG; c.beginPath(); c.roundRect(x + 1, y + 1, W - 2, H - 2, 10); c.fill();
  const cx = x + 4, cy = y + 4;
  if (full) { c.fillStyle = col; c.beginPath(); c.arc(cx + 7, cy + 7, 8, 0, TAU); c.fill(); }
  chip(c, id, cx, cy, 14, res);
  const px0 = cx + 14 + 3, py = y + Math.round((H - PIP.h) / 2);
  for (let i = 0; i < max; i++) pip(c, px0 + i * PIP.step, py, i < n, full, fill, res);
  c.restore(); return W;
}
/** 畫布大小（CSS px）：膠囊四邊各多 4px 給滿層外暈。 */
export const gaugeBox = (id: string): { w: number; h: number } => ({ w: gaugeOuter(id) + 2 * GAUGE_PAD, h: GAUGE_H + 2 * GAUGE_PAD });
/** 一個膠囊的畫布（同樣張 `gaugeCanvas`：寬 gaugeOuter＋8、高 30，膠囊畫在 (4,4)）。沒有畫布時回 null。 */
export function gaugeCanvas(id: string, n: number, res = ICON_RES): HTMLCanvasElement | null {
  if (!qCanvasAvailable() || !hasGauge(id)) return null;
  const { w, h } = gaugeBox(id), cv = blank(Math.round(w * res), Math.round(h * res)), x = ctxOf(cv);
  x.scale(res, res); gauge(x, id, n, GAUGE_PAD, GAUGE_PAD, res);
  return cv;
}
