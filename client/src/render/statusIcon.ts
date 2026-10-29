// 狀態圖示與身上特效（Phase 3-36a；畫法移植自 docs/art/sample/fx.js 的 ③ 狀態圖示）。
// 規則優先於圖：外框由 `polarity`、圖樣顏色由 `control_group` → `on_turn_start_damage.element` → `polarity`、
// 身上特效由 `skip_turn`／`removed_by_element`／`absorbs_damage`／`prevents_move`／持續傷害元素決定——
// 這些欄位都來自 glossary 的 `status_look`，前端不寫死狀態 ID 清單（`GLYPH` 是圖樣查表，不認得的走預設）。
// 座標以 52px 的虛擬格為單位；快取鍵用級距（尺寸、極性、控制類別…），不用原始比例。
import type { StatusLook } from "../api/types";
import { statusLook, statusName } from "../battle/glossary";
import { FONT } from "./labels";
import { elementColor } from "./palette";
import type { Ctx } from "./skillGlyphs";

const TAU = Math.PI * 2;
const DPR = 2;

export type Polarity = "buff" | "debuff" | "neutral";

/** 圖樣色：控制類依 control_group。 */
export const CTRL_COLOR: Readonly<Record<string, string>> = { hard: "#ffd84a", movement: "#6ac8ff", mental: "#c890ff" };
const POL_COLOR: Readonly<Record<Polarity, string>> = { buff: "#7dffb0", debuff: "#ff8a8a", neutral: "#e8d8a8" };
/** 外框色。 */
export const FRAME_COLOR: Readonly<Record<Polarity, string>> = { buff: "#3fbf6a", debuff: "#e04848", neutral: "#c8a048" };
/** 少數保留自己顏色的狀態（原本的辨識度；圖樣查表的一部分）。 */
const OWN_COLOR: Readonly<Record<string, string>> = {
  time_bomb: "#ffb03a",
  shielded: "#8ac8ff",
  guarded: "#8ac8ff",
  stoneskin: "#c8a060", // 石膚（3-54b）：大地的土色
  defending: "#8ac8ff",
  entangled: "#6ac8ff", // 纏繞（3I-1）：移動減少，不算控制類別，但用移動控制的藍
  regenerating: "#7dffb0",
  undying: "#ff8a9a",
  soul_link: "#c8a0ff",
  revealed: "#ffd04a",
  marked: "#ff6a4a",
  overwatch: "#ffd04a",
  infused_fire: "#ff6a1a", // 臨時附魔（3I-6）：武器上纏著該元素的色
  infused_holy: "#ffe9a0",
};

const isPolarity = (p: string | undefined): p is Polarity => p === "buff" || p === "debuff" || p === "neutral";

/** 狀態的極性：沒有資料或不認得 → neutral。 */
export function polarityOf(id: string | null | undefined): Polarity {
  const p = id == null ? undefined : statusLook(id)?.polarity;
  return isPolarity(p) ? p : "neutral";
}

/** 圖樣顏色：`control_group` → 持續傷害元素 → 專屬色 → `polarity`。 */
export function glyphColor(id: string | null | undefined): string {
  const look = id == null ? undefined : statusLook(id);
  const ctrl = look?.control_group;
  if (ctrl != null) {
    const c = CTRL_COLOR[ctrl];
    if (c !== undefined) return c;
  }
  if (look?.dot_element != null) return elementColor(look.dot_element);
  return (id == null ? undefined : OWN_COLOR[id]) ?? POL_COLOR[polarityOf(id)];
}

/** 外框形狀：buff 圓、debuff 圓角方、neutral（含姿態）六角。邊長約 2r。 */
export function framePath(ctx: Ctx, pol: Polarity, r: number): void {
  ctx.beginPath();
  if (pol === "buff") ctx.arc(0, 0, r, 0, TAU);
  else if (pol === "debuff") ctx.roundRect(-r * 0.9, -r * 0.9, r * 1.8, r * 1.8, r * 0.35);
  else for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * r, Math.sin((i / 6) * TAU + TAU / 12) * r);
  ctx.closePath();
}

// ---- 圖樣（中心 (0,0)、半徑約 10；顏色已設在 fill/stroke）----

function line(c: Ctx, pts: ReadonlyArray<readonly [number, number]>): void {
  c.beginPath();
  pts.forEach(([px, py], i) => (i > 0 ? c.lineTo(px, py) : c.moveTo(px, py)));
  c.stroke();
}
function circle(c: Ctx, x: number, y: number, r: number, fill = false): void {
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  if (fill) c.fill();
  else c.stroke();
}
function shield(c: Ctx): void {
  c.beginPath();
  c.moveTo(0, -9);
  c.lineTo(8, -6);
  c.quadraticCurveTo(8, 5, 0, 10);
  c.quadraticCurveTo(-8, 5, -8, -6);
  c.closePath();
  c.stroke();
}
function arrow(c: Ctx, x: number, y: number, up: boolean): void {
  const s = up ? -1 : 1;
  line(c, [[x, y - 5 * s], [x, y + 5 * s]]);
  line(c, [[x - 4, y - 1 * s], [x, y - 5 * s], [x + 4, y - 1 * s]]);
}
function eye(c: Ctx, open: boolean): void {
  c.beginPath();
  c.moveTo(-10, 0);
  c.quadraticCurveTo(0, -9, 10, 0);
  c.quadraticCurveTo(0, 9, -10, 0);
  c.stroke();
  if (open) circle(c, 0, 0, 3.5, true);
}
function star(c: Ctx, x: number, y: number, r: number): void {
  c.beginPath();
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 1 ? r * 0.45 : r;
    const a = (i / 10) * TAU - Math.PI / 2;
    c.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
  }
  c.closePath();
  c.fill();
}
function flame(c: Ctx, x: number, y: number, h: number): void {
  c.beginPath();
  c.moveTo(x, y - h);
  c.quadraticCurveTo(x + h * 0.6, y - h * 0.2, x + h * 0.35, y + h * 0.3);
  c.quadraticCurveTo(x, y + h * 0.5, x - h * 0.35, y + h * 0.3);
  c.quadraticCurveTo(x - h * 0.6, y - h * 0.2, x, y - h);
  c.fill();
}
function drop(c: Ctx, x: number, y: number, s: number): void {
  c.beginPath();
  c.moveTo(x, y - s);
  c.quadraticCurveTo(x + s * 0.8, y + s * 0.2, x, y + s * 0.7);
  c.quadraticCurveTo(x - s * 0.8, y + s * 0.2, x, y - s);
  c.fill();
}
function sword(c: Ctx): void {
  line(c, [[-6, 7], [6, -7]]);
  line(c, [[-7, 2], [-2, 7]]);
}

type Glyph = (c: Ctx) => void;

/** 一個狀態一個圖樣（圖樣查表；不認得的狀態畫名稱第一個字）。 */
export const GLYPH: Readonly<Record<string, Glyph>> = {
  defending: (c) => shield(c),
  guarded: (c) => {
    shield(c);
    arrow(c, 0, 0.5, false); // 盾＋↓（受傷減少）
  },
  stoneskin: (c) => {
    // 石膚（3-54b）：盾＋岩石的裂紋（受物理傷害減少、移動變慢）
    shield(c);
    line(c, [[-3, -4], [0, -1], [-2, 2], [1, 5]]);
    line(c, [[0, -1], [4, 0]]);
  },
  shielded: (c) => {
    circle(c, 0, 0, 9); // 泡泡（吸收量）
    c.globalAlpha *= 0.35;
    c.fill();
    c.globalAlpha /= 0.35;
    c.beginPath();
    c.arc(0, 0, 5, Math.PI * 1.1, Math.PI * 1.55);
    c.strokeStyle = "#ffffff";
    c.stroke();
  },
  prone: (c) => {
    circle(c, -6, 3, 3, true);
    line(c, [[-2, 4], [9, 4]]);
    line(c, [[-10, 8], [10, 8]]);
  },
  burning: (c) => flame(c, 0, 1, 10),
  poison: (c) => {
    drop(c, 0, 0, 10);
    c.fillStyle = "#1a2a10";
    c.beginPath();
    c.arc(-2, 2, 2, 0, TAU);
    c.arc(3, -1, 1.4, 0, TAU);
    c.fill();
  },
  bleed: (c) => {
    drop(c, -3, -1, 7);
    drop(c, 5, 3, 5);
  },
  concealed: (c) => {
    c.globalAlpha *= 0.55;
    circle(c, 0, -4, 4, true);
    c.beginPath();
    c.moveTo(-8, 9);
    c.quadraticCurveTo(0, -2, 8, 9);
    c.fill();
    c.globalAlpha /= 0.55;
    line(c, [[-9, 9], [9, -9]]);
  },
  revealed: (c) => {
    eye(c, true);
    line(c, [[-9, -9], [-5, -6]]);
    line(c, [[9, -9], [5, -6]]);
    line(c, [[0, -10], [0, -7]]);
  },
  overwatch: (c) => {
    circle(c, 0, 0, 7); // 狙擊鏡
    line(c, [[0, -10], [0, -4]]);
    line(c, [[0, 4], [0, 10]]);
    line(c, [[-10, 0], [-4, 0]]);
    line(c, [[4, 0], [10, 0]]);
    circle(c, 0, 0, 1.8, true);
  },
  marked: (c) => {
    line(c, [[-7, -7], [7, 7]]); // 靶心叉
    line(c, [[7, -7], [-7, 7]]);
    circle(c, 0, 0, 9);
  },
  time_bomb: (c) => {
    circle(c, -1, 2, 7, true);
    line(c, [[3, -4], [7, -9]]);
    c.fillStyle = "#fff";
    star(c, 8, -9, 3);
  },
  charging: (c) => {
    circle(c, 0, 0, 8);
    circle(c, 0, 0, 3.5, true);
  },
  slow: (c) => {
    circle(c, 0, 0, 8.5);
    line(c, [[0, 0], [0, -6]]);
    line(c, [[0, 0], [4, 3]]);
  },
  root: (c) => {
    line(c, [[0, -9], [0, 4]]);
    line(c, [[0, 4], [-7, 9]]);
    line(c, [[0, 4], [7, 9]]);
    line(c, [[0, 1], [-5, -3]]);
  },
  stun: (c) => {
    star(c, -5, -3, 5);
    star(c, 5, -3, 5);
    star(c, 0, 5, 5);
  },
  frozen: (c) => {
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI;
      line(c, [[Math.cos(a) * -10, Math.sin(a) * -10], [Math.cos(a) * 10, Math.sin(a) * 10]]);
    }
    circle(c, 0, 0, 2.5, true);
  },
  weaken: (c) => {
    sword(c);
    arrow(c, 6, 3, false);
  },
  empowered: (c) => {
    line(c, [[-8, 0], [0, -8], [8, 0]]); // 雙箭頭↑（全屬性提升）
    line(c, [[-8, 8], [0, 0], [8, 8]]);
  },
  infused_fire: (c) => {
    sword(c); // 臨時附魔（3I-6）：劍＋火星
    circle(c, 7, -7, 2.8, true);
    circle(c, -7, 7, 1.6, true);
  },
  infused_holy: (c) => {
    sword(c); // 劍＋十字光
    line(c, [[7, -10], [7, -4]]);
    line(c, [[4, -7], [10, -7]]);
  },
  race_adapt: (c) => {
    line(c, [[-9, 0], [7, 0]]); // 人類種族技「應變」（3R-2）：向前的箭頭（不被藉機攻擊）
    line(c, [[2, -6], [8, 0], [2, 6]]);
    line(c, [[-9, -6], [-4, -6]]);
    line(c, [[-9, 6], [-4, 6]]);
  },
  race_stonewall: (c) => {
    shield(c); // 矮人種族技「穩若磐石」（3R-2）：盾＋底下的岩塊（不被推、拉、擊倒）
    line(c, [[-6, 8], [6, 8]]);
    line(c, [[-3, 5], [3, 5]]);
  },
  rallied: (c) => {
    line(c, [[-6, 10], [-6, -9]]); // 戰旗
    c.beginPath();
    c.moveTo(-6, -9);
    c.lineTo(8, -5);
    c.lineTo(-6, -1);
    c.closePath();
    c.fill();
  },
  vulnerable: (c) => {
    shield(c); // 裂開的盾
    line(c, [[-2, -8], [2, -2], [-2, 2], [2, 9]]);
  },
  entangled: (c) => {
    c.beginPath(); // 纏繞（鞭，3I-1）：繞兩圈的繩＋往下的箭頭（移動減少）
    c.moveTo(-9, -6);
    c.bezierCurveTo(-2, -12, 6, -2, -1, 0);
    c.bezierCurveTo(-8, 2, 0, 8, 9, 2);
    c.stroke();
    arrow(c, -5, 5, false);
  },
  armor_broken: (c) => {
    c.beginPath(); // 胸甲＋↓
    c.moveTo(-8, -6);
    c.lineTo(0, -9);
    c.lineTo(8, -6);
    c.lineTo(8, 1);
    c.lineTo(0, 9);
    c.lineTo(-8, 1);
    c.closePath();
    c.stroke();
    arrow(c, 0, 0, false);
  },
  hasted: (c) => {
    line(c, [[-8, -7], [-1, 0], [-8, 7]]);
    line(c, [[1, -7], [8, 0], [1, 7]]);
  },
  regenerating: (c) => {
    c.fillRect(-2.5, -9, 5, 18);
    c.fillRect(-9, -2.5, 18, 5);
  },
  undying: (c) => {
    c.beginPath();
    c.moveTo(0, 9);
    c.bezierCurveTo(-12, 0, -6, -10, 0, -4);
    c.bezierCurveTo(6, -10, 12, 0, 0, 9);
    c.fill();
    c.fillStyle = "#000";
    c.fillRect(-1, -4, 2, 9);
    c.fillRect(-3.5, -1.5, 7, 2);
  },
  soul_link: (c) => {
    circle(c, -4, 0, 5.5);
    circle(c, 4, 0, 5.5);
  },
  taunted: (c) => {
    circle(c, 0, 0, 9);
    circle(c, 0, 0, 4.5);
    circle(c, 0, 0, 1.5, true);
  },
  feared: (c) => {
    c.font = `bold 17px ${FONT}`;
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("!", 0, 1);
    line(c, [[-8, -6], [-5, -3]]);
    line(c, [[8, -6], [5, -3]]);
  },
  overdrawn: (c) => {
    // 透支（3-50）：下回合少 1 AP——空掉的電池＋↓
    c.beginPath();
    c.roundRect(-8, -6, 14, 12, 2);
    c.stroke();
    line(c, [[6, -2], [9, -2], [9, 2], [6, 2]]);
    arrow(c, -1, 0, false);
  },
  silenced: (c) => {
    c.beginPath();
    c.roundRect(-9, -7, 18, 12, 4);
    c.stroke();
    c.beginPath();
    c.moveTo(-3, 5);
    c.lineTo(-6, 10);
    c.lineTo(2, 5);
    c.stroke();
    line(c, [[-10, 9], [10, -9]]);
  },
  blinded: (c) => {
    eye(c, false);
    line(c, [[-9, 7], [9, -7]]);
  },
  stance_fury: (c) => {
    for (const dx of [-5, 0, 5]) line(c, [[dx - 3, 8], [dx + 3, -8]]); // 爪痕
  },
  stance_bulwark: (c) => {
    c.fillRect(-8, -2, 16, 10); // 城垛
    for (const dx of [-8, -2, 4]) c.fillRect(dx, -7, 4, 5);
  },
  // 3W-4b 的姿態狀態：顏色走 polarity／持續元素，圖樣在這裡
  stance_guard: (c) => {
    // 堅守：盾牌
    c.beginPath();
    c.moveTo(-8, -8);
    c.lineTo(8, -8);
    c.lineTo(8, 1);
    c.lineTo(0, 10);
    c.lineTo(-8, 1);
    c.closePath();
    c.stroke();
  },
  stance_ironwall: (c) => {
    // 鐵壁：磚牆
    c.strokeRect(-9, -7, 18, 14);
    line(c, [[-9, 0], [9, 0]]);
    line(c, [[-3, -7], [-3, 0]]);
    line(c, [[3, 0], [3, 7]]);
  },
  stance_flame: (c) => {
    // 焰刃：劍＋火苗
    line(c, [[-7, 8], [7, -8]]);
    line(c, [[-9, 3], [-3, 9]]);
    c.beginPath();
    c.arc(7, 6, 3, 0, TAU);
    c.fill();
  },
  stance_blaze: (c) => {
    // 烈焰：大火焰
    c.beginPath();
    c.moveTo(0, -10);
    c.quadraticCurveTo(9, -1, 6, 6);
    c.quadraticCurveTo(0, 12, -6, 6);
    c.quadraticCurveTo(-8, 0, -2, -4);
    c.quadraticCurveTo(-1, -7, 0, -10);
    c.closePath();
    c.stroke();
  },
  stance_frost: (c) => {
    // 霜刃：劍＋小雪花
    line(c, [[-7, 8], [7, -8]]);
    line(c, [[3, 4], [9, 4]]);
    line(c, [[6, 1], [6, 7]]);
  },
  stance_glacier: (c) => {
    // 冰川：雪花
    for (const [x, y] of [[0, 9], [8, 4.5], [8, -4.5]] as const) line(c, [[-x, -y], [x, y]]);
  },
};

/** 在以 (0,0) 為中心、半徑約 10 的範圍畫狀態圖樣（顏色與線寬由呼叫端設）；不認得的狀態畫名稱第一個字。 */
export function drawGlyph(c: Ctx, id: string | null | undefined): void {
  const known = id == null ? undefined : GLYPH[id];
  if (known !== undefined) {
    known(c);
    return;
  }
  const name = id == null || id === "" ? "?" : statusName(id);
  c.font = `bold 13px ${FONT}`;
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.fillText([...name][0] ?? "?", 0, 1);
}

/** 畫一個完整的狀態圖示（外框依 polarity ＋ 圖樣），中心 (cx, cy)、邊長 `size`。 */
export function paintStatusIcon(ctx: Ctx, id: string | null | undefined, cx: number, cy: number, size: number): void {
  const pol = polarityOf(id);
  const r = size / 2;
  const k = size / 26;
  ctx.save();
  ctx.translate(cx, cy);
  framePath(ctx, pol, r);
  ctx.fillStyle = "rgba(12,12,16,0.88)";
  ctx.fill();
  ctx.lineWidth = Math.max(1.5, size * 0.09);
  ctx.strokeStyle = FRAME_COLOR[pol];
  ctx.stroke();
  ctx.scale(k * 0.95, k * 0.95);
  const col = glyphColor(id);
  ctx.fillStyle = col;
  ctx.strokeStyle = col;
  ctx.lineWidth = size <= 18 ? 3 : 2.4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  drawGlyph(ctx, id);
  ctx.restore();
}

// ---- 快取 ----

const iconCache = new Map<string, HTMLCanvasElement>();

/** 字型載入後（`fontLoad`）清掉，讓「名稱第一個字」用正確的字型重畫。 */
export function clearStatusIconCache(): void {
  iconCache.clear();
}
export const statusIconCacheSize = (): number => iconCache.size;

export function statusIconKey(id: string, size: number): string {
  return `${lookKey(id)}|${size}`;
}

function lookKey(id: string): string {
  const l = statusLook(id);
  const first = GLYPH[id] === undefined ? [...statusName(id)][0] ?? "?" : "";
  return `${id}|${l?.polarity ?? "-"}|${l?.control_group ?? "-"}|${l?.dot_element ?? "-"}|${first}`;
}

/** 一個狀態圖示的離屏 canvas（邊長 `size` px，內部解析度 ×2）；沒有 DOM 時回傳 `null`。 */
export function statusIconCanvas(id: string, size: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const key = statusIconKey(id, size);
  const hit = iconCache.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = size * DPR;
  canvas.height = size * DPR;
  const ctx = canvas.getContext("2d");
  if (ctx !== null) {
    ctx.scale(DPR, DPR);
    paintStatusIcon(ctx, id, size / 2, size / 2, size - 2);
  }
  iconCache.set(key, canvas);
  return canvas;
}

// ---- 頭頂狀態列 ----

/** 戰場上的排序：硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性。同級依 ID 排序（與輸入順序無關）。 */
export function statusRank(id: string): number {
  const l = statusLook(id);
  if (l?.control_group === "hard") return 0;
  if (l?.control_group != null) return 1;
  if (l?.dot_element != null) return 2;
  const pol = polarityOf(id);
  if (pol === "debuff") return 3;
  if (pol === "buff") return 4;
  return 5;
}

export function sortStatuses(ids: readonly string[]): string[] {
  return [...new Set(ids)].sort((a, b) => statusRank(a) - statusRank(b) || (a < b ? -1 : a > b ? 1 : 0));
}

export const ROW_ICON = 14;
/** 狀態列最多顯示的格數（含「+N」）。 */
export const ROW_SLOTS = 3;

export type RowItem = { kind: "icon"; id: string; x: number } | { kind: "more"; extra: number; x: number };

/**
 * 頭頂狀態列的排版（相對列中心的 x）：最多 `slots` 格；超過時顯示 `slots - 1` 個圖示加「+N」。
 * 0 個狀態回傳空陣列。
 */
export function statusRowLayout(ids: readonly string[], slots = ROW_SLOTS, size = ROW_ICON): RowItem[] {
  const sorted = sortStatuses(ids);
  const shown = sorted.slice(0, sorted.length > slots ? slots - 1 : slots);
  const extra = sorted.length - shown.length;
  const gap = size + 1;
  const n = shown.length + (extra > 0 ? 1 : 0);
  const items: RowItem[] = [];
  let x = -((n - 1) * gap) / 2;
  for (const id of shown) {
    items.push({ kind: "icon", id, x });
    x += gap;
  }
  if (extra > 0) items.push({ kind: "more", extra, x });
  return items;
}

// ---- 身上特效 ----

/** 身上特效的描述（只有 5 類，依欄位決定）；也是特效貼圖的快取鍵來源。 */
export interface BodyEffects {
  /** `skip_turn` 且 `removed_by_element` 含 fire：冰塊罩全身。 */
  frozen: boolean;
  /** 其他 `skip_turn`：頭上轉圈星星。 */
  stunned: boolean;
  /** `absorbs_damage`：淡藍泡泡。 */
  absorb: boolean;
  /** `prevents_move`：腳下藤蔓。 */
  noMove: boolean;
  /** `on_turn_start_damage` 的元素（去重、依狀態 ID 排序、最多 2 種）。 */
  dots: string[];
}

export function bodyEffects(ids: readonly string[]): BodyEffects {
  const looks: StatusLook[] = [...new Set(ids)]
    .sort()
    .map((id) => statusLook(id))
    .filter((l): l is StatusLook => l !== undefined);
  const frozen = looks.some((l) => l.skip_turn && l.removed_by_element.includes("fire"));
  const dots: string[] = [];
  for (const l of looks) if (l.dot_element != null && !dots.includes(l.dot_element)) dots.push(l.dot_element);
  return {
    frozen,
    stunned: !frozen && looks.some((l) => l.skip_turn),
    absorb: looks.some((l) => l.absorbs_damage),
    noMove: looks.some((l) => l.prevents_move),
    dots: dots.slice(0, 2),
  };
}

export const hasUnderEffect = (e: BodyEffects): boolean => e.noMove;
export const hasOverEffect = (e: BodyEffects): boolean => e.frozen || e.stunned || e.absorb || e.dots.length > 0;

/** 特效貼圖的快取鍵（級距：只看有哪幾類）。 */
export function effectsKey(e: BodyEffects): string {
  return `${e.frozen ? "F" : ""}${e.stunned ? "S" : ""}${e.absorb ? "A" : ""}${e.noMove ? "R" : ""}|${e.dots.join(",")}`;
}

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/** 腳下特效（畫在小人之前）：定身的藤蔓。`cx` 為格子中心、`feet` 為腳底 y。 */
export function bodyUnder(ctx: Ctx, e: BodyEffects, cx: number, feet: number): void {
  if (!e.noMove) return;
  ctx.save();
  ctx.strokeStyle = "#6ac8ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(cx, feet - 2, 13, 4.5, 0, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "#3d8a2a";
  ctx.lineWidth = 2.5;
  for (const s of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(cx + s * 12, feet);
    ctx.quadraticCurveTo(cx + s * 14, feet - 10, cx + s * 5, feet - 13);
    ctx.stroke();
  }
  ctx.restore();
}

/** 身上特效（畫在小人之後）：冰塊、星星、泡泡、腳邊粒子。`t` 為星星的轉動角度（弧度）。 */
export function bodyOver(ctx: Ctx, e: BodyEffects, cx: number, feet: number, t = 0, bodyH = 34): void {
  const head = feet - bodyH;
  if (e.frozen) {
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(cx - 15, head - 6, 30, feet - head + 8, 5);
    ctx.fillStyle = rgba("#9fe6ff", 0.42);
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#e8fbff";
    ctx.stroke();
    ctx.strokeStyle = rgba("#ffffff", 0.8);
    ctx.beginPath();
    ctx.moveTo(cx - 10, feet - 4);
    ctx.lineTo(cx - 6, head);
    ctx.stroke();
    ctx.restore();
  }
  if (e.stunned) {
    ctx.save();
    ctx.strokeStyle = rgba("#ffd84a", 0.7);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.ellipse(cx, head - 2, 14, 4, 0, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = "#ffd84a";
    for (let i = 0; i < 3; i++) {
      const a = t + (i / 3) * TAU;
      star(ctx, cx + Math.cos(a) * 14, head - 2 + Math.sin(a) * 4, 3.6);
    }
    ctx.restore();
  }
  if (e.absorb) {
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, feet - bodyH * 0.6, 19, bodyH * 0.7, 0, 0, TAU);
    const g = ctx.createRadialGradient(cx - 6, feet - bodyH * 0.9, 2, cx, feet - bodyH * 0.6, 24);
    g.addColorStop(0, rgba("#ffffff", 0.18));
    g.addColorStop(1, rgba("#8ac8ff", 0.22));
    ctx.fillStyle = g;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = rgba("#bfe2ff", 0.85);
    ctx.stroke();
    ctx.restore();
  }
  e.dots.forEach((el, k) => dotParticles(ctx, el, k === 0 ? 1 : -1, cx, feet));
}

function dotParticles(ctx: Ctx, el: string, side: number, cx: number, feet: number): void {
  ctx.save();
  ctx.fillStyle = elementColor(el);
  ctx.strokeStyle = "#1a0e06";
  ctx.lineWidth = 1;
  for (let i = 0; i < 2; i++) {
    const px = cx + side * (11 + i * 5);
    const py = feet - 4 - i * 9;
    if (el === "fire") flame(ctx, px, py, 5.5);
    else if (el === "poison") {
      ctx.beginPath();
      ctx.arc(px, py, 2.6 - i * 0.6, 0, TAU);
      ctx.fill();
      ctx.stroke();
    } else drop(ctx, px, py, 4);
  }
  ctx.restore();
}

/** 隱蔽的單位畫成半透明。 */
export const CONCEALED_ALPHA = 0.55;
/** 隱蔽狀態的 ID（和 `TIME_BOMB`、`CHARGING` 一樣是引擎規則直接引用的狀態）。 */
export const CONCEALED = "concealed";
