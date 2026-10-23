// 戰場效果的共用畫法（Phase 3-36b；移植自 docs/art/sample/fx.js 的 ② 戰場效果）：
// 受損裂痕、剩餘回合徽章、擋視線表面的上層霧、陷阱踏板、持續區域的單格（紋理＋外框＋箭頭）與施放者虛線環。
// 座標以 52px 的虛擬格為單位（同 terrainArt／objectArt）；每個畫法都由資料欄位決定，
// 不認得的值（元素、觸發方式、表面）一律退回灰色預設。快取鍵只用級距與色碼，不用原始比例。
import { SURFACES } from "../battle/glossary";
import { rgba } from "./artPalette";
import { TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";
import { FONT } from "./labels";
import { elementColor } from "./statusIcon";

const T = 52;
const GRAY = "#d8d8e0";
const BAD = "#ff5a5a";
const TEAM_COLOR = { mine: "#5aa0ff", enemy: "#ff5a5a" } as const;

// ---- 顏色 ------------------------------------------------------------------------------------

const KNOWN_ELEMENTS: ReadonlySet<string> = new Set([
  "fire",
  "ice",
  "lightning",
  "poison",
  "holy",
  "shadow",
  "physical",
  "earth",
  "wind",
  "water",
]);

const hex6 = (n: number): string => `#${n.toString(16).padStart(6, "0")}`;

/** 表面的顏色（色碼）；不認得或沒有表面 → `null`。 */
export function surfaceHex(surface: string | null | undefined): string | null {
  if (surface == null || surface === "") return null;
  const style = (SURFACES as Readonly<Record<string, { color: number } | null | undefined>>)[surface];
  return style == null ? null : hex6(style.color);
}

/** 陷阱、區域的元素色：元素 → 表面色 → 灰。 */
export function fxColor(element: string | null | undefined, surface?: string | null): string {
  if (element != null && KNOWN_ELEMENTS.has(element)) return elementColor(element);
  return surfaceHex(surface) ?? GRAY;
}

// ---- 受損裂痕 --------------------------------------------------------------------------------

/** 受損級距：0＝HP > 66%（或沒有耐久）、1＝≤ 66%、2＝≤ 33%。 */
export type HpStage = 0 | 1 | 2;

export function hpStageOf(ratio: number | null | undefined): HpStage {
  if (ratio == null || !Number.isFinite(ratio) || ratio > 0.66) return 0;
  return ratio > 0.33 ? 1 : 2;
}

/** 物件受損的裂痕（可破壞物件共用）：級距 1 一道細裂、級距 2 三道粗裂。`box` 是格子內的比例範圍。 */
export function cracks(
  ctx: Ctx,
  stage: HpStage,
  gx: number,
  gy: number,
  color = "#1a1a1a",
  box: readonly [number, number, number, number] = [0.25, 0.2, 0.75, 0.75],
): void {
  if (stage === 0) return;
  const heavy = stage === 2;
  const r = rng(gx, gy, 11);
  const [x0, y0, x1, y1] = [box[0] * T, box[1] * T, box[2] * T, box[3] * T];
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineCap = "round";
  ctx.lineWidth = heavy ? 2 : 1.3;
  const lines = heavy ? 3 : 1;
  for (let k = 0; k < lines; k++) {
    let px = x0 + r() * (x1 - x0);
    let py = y0 + r() * (y1 - y0) * 0.3;
    ctx.beginPath();
    ctx.moveTo(px, py);
    for (let s = 0; s < 4; s++) {
      px += (r() - 0.5) * 10;
      py += 4 + r() * 5;
      ctx.lineTo(Math.min(x1, Math.max(x0, px)), Math.min(y1, py));
    }
    ctx.stroke();
  }
  ctx.restore();
}

// ---- 剩餘回合徽章 ----------------------------------------------------------------------------

/** 黑底圓形白字；最後 1 回合改橘色。暫時物件、區域、延遲陷阱共用。 */
export function turnsBadge(ctx: Ctx, cx: number, cy: number, n: number): void {
  const last = n <= 1;
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, 7.5, 0, TAU);
  ctx.fillStyle = "rgba(0,0,0,0.78)";
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = last ? "#ffb03a" : "#e8e8ea";
  ctx.stroke();
  ctx.fillStyle = last ? "#ffb03a" : "#ffffff";
  ctx.font = `bold 10px ${FONT}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(String(n), cx, cy + 0.5);
  ctx.restore();
}

// ---- 擋視線表面的上層霧 ----------------------------------------------------------------------

/** 霧的種類：黑暗是紫黑色加紫色光點，其餘擋視線表面（煙霧與新表面）是灰色。 */
export type VeilKind = "dark" | "gray";

export const veilKindOf = (surface: string): VeilKind => (surface === "darkness" ? "dark" : "gray");

/** 擋視線的表面（煙霧、黑暗）：畫在單位「之上」的半透明上層，蓋住單位下半身。 */
export function sightVeil(ctx: Ctx, kind: VeilKind, gx: number, gy: number): void {
  const r = rng(gx, gy, 7);
  const dark = kind === "dark";
  const color = dark ? "#2a1640" : "#c9ccd2";
  const alpha = dark ? 0.55 : 0.5;
  ctx.save();
  for (let i = 0; i < 5; i++) {
    const px = 8 + r() * (T - 16);
    const py = T * 0.45 + r() * T * 0.45;
    const rad = 9 + r() * 8;
    const g = ctx.createRadialGradient(px, py, 1, px, py, rad);
    g.addColorStop(0, rgba(color, alpha));
    g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(px, py, rad, 0, TAU);
    ctx.fill();
  }
  if (dark) {
    ctx.fillStyle = rgba("#c9a0ff", 0.8);
    for (let i = 0; i < 3; i++) ctx.fillRect(6 + r() * (T - 12), 6 + r() * (T - 12), 2, 2);
  }
  ctx.restore();
}

// ---- 陷阱 ------------------------------------------------------------------------------------

export type TrapTrigger = "enter" | "delay";

/** 不認得的觸發方式一律當成踩到觸發。 */
export const trapTriggerOf = (trigger: string | null | undefined): TrapTrigger => (trigger === "delay" ? "delay" : "enter");

export interface TrapPad {
  /** 放置者是不是目前玩家的陣營（敵方的陷阱只會在被揭露時畫）。 */
  mine: boolean;
  trigger: TrapTrigger;
  /** 元素色（色碼）；見 :func:`fxColor`。 */
  color: string;
}

/** 陷阱踏板：外圈＝陣營色（敵方虛線加「!」）；中央＝元素色的捕獸夾（enter）或沙漏（delay）。 */
export function drawTrapPad(ctx: Ctx, pad: TrapPad): void {
  const col = pad.mine ? TEAM_COLOR.mine : TEAM_COLOR.enemy;
  const cx = T / 2;
  const cy = T / 2 + 2;
  const R = T * 0.3;
  ctx.save();
  ctx.beginPath();
  ctx.ellipse(cx, cy, R, R * 0.78, 0, 0, TAU);
  ctx.fillStyle = "rgba(20,18,16,0.55)";
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = col;
  if (!pad.mine) ctx.setLineDash([5, 3]);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.strokeStyle = pad.color;
  ctx.fillStyle = pad.color;
  ctx.lineWidth = 2;
  if (pad.trigger === "enter") {
    // 捕獸夾：上下兩排三角齒，咬向中線
    for (const sgn of [-1, 1]) {
      for (let i = 0; i < 4; i++) {
        const px = cx - R * 0.6 + (i * R * 1.2) / 3;
        ctx.beginPath();
        ctx.moveTo(px - 3.5, cy + sgn * 8);
        ctx.lineTo(px + 3.5, cy + sgn * 8);
        ctx.lineTo(px, cy + sgn * 1.5);
        ctx.closePath();
        ctx.fill();
      }
      ctx.beginPath();
      ctx.moveTo(cx - R * 0.75, cy + sgn * 8);
      ctx.lineTo(cx + R * 0.75, cy + sgn * 8);
      ctx.stroke();
    }
  } else {
    // 沙漏
    ctx.beginPath();
    ctx.moveTo(cx - 6, cy - 8);
    ctx.lineTo(cx + 6, cy - 8);
    ctx.lineTo(cx - 6, cy + 8);
    ctx.lineTo(cx + 6, cy + 8);
    ctx.closePath();
    ctx.fill();
  }
  if (!pad.mine) {
    ctx.fillStyle = BAD;
    ctx.font = `bold 14px ${FONT}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#000";
    ctx.strokeText("!", T - 9, 10);
    ctx.fillText("!", T - 9, 10);
  }
  ctx.restore();
}

// ---- 持續區域 --------------------------------------------------------------------------------

export type Side = "n" | "s" | "w" | "e";

export interface ZoneCell {
  /** 區域元素色（色碼）。 */
  color: string;
  /** 對看的人有害：實線外框＋斜紋；否則虛線外框＋光點（有益）。 */
  harmful: boolean;
  /** 不影響看的人（3-37b）：虛線外框、只有淡底色，不畫紋理。優先於 `harmful`。 */
  neutral?: boolean;
  /** 要描外框的邊（鄰格不在同一區域的邊）。 */
  sides: readonly Side[];
  /** 移動型：前進方向沒有鄰格的那一格，在這一側畫三角箭頭。 */
  arrow: Side | null;
  /** 斜紋相位（0–8，偶數）：讓相鄰格的斜紋接起來。 */
  phase: number;
}

const SIDE_VEC: Readonly<Record<Side, readonly [number, number]>> = { n: [0, -1], s: [0, 1], w: [-1, 0], e: [1, 0] };

/** 區域單格：底色＋（斜紋｜光點）＋只描外緣的外框＋移動型的箭頭。 */
export function drawZoneCell(ctx: Ctx, c: ZoneCell): void {
  ctx.save();
  const neutral = c.neutral === true;
  ctx.fillStyle = rgba(c.color, neutral ? 0.1 : c.harmful ? 0.2 : 0.16);
  ctx.fillRect(0, 0, T, T);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, T, T);
  ctx.clip();
  if (neutral) {
    // 不影響我方：不畫紋理
  } else if (c.harmful) {
    ctx.strokeStyle = rgba(c.color, 0.45);
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let u = c.phase; u < T * 2; u += 10) {
      ctx.moveTo(u, 0);
      ctx.lineTo(u - T, T);
    }
    ctx.stroke();
  } else {
    ctx.fillStyle = rgba(c.color, 0.7);
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        ctx.beginPath();
        ctx.arc(9 + i * 17 + (j % 2) * 8, 9 + j * 17, 1.6, 0, TAU);
        ctx.fill();
      }
    }
  }
  ctx.restore();
  ctx.strokeStyle = c.color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  if (neutral || !c.harmful) ctx.setLineDash([6, 4]);
  ctx.beginPath();
  const inset = 1.5;
  for (const s of c.sides) {
    if (s === "n") {
      ctx.moveTo(0, inset);
      ctx.lineTo(T, inset);
    } else if (s === "s") {
      ctx.moveTo(0, T - inset);
      ctx.lineTo(T, T - inset);
    } else if (s === "w") {
      ctx.moveTo(inset, 0);
      ctx.lineTo(inset, T);
    } else {
      ctx.moveTo(T - inset, 0);
      ctx.lineTo(T - inset, T);
    }
  }
  ctx.stroke();
  ctx.setLineDash([]);
  if (c.arrow !== null) {
    const [dx, dy] = SIDE_VEC[c.arrow];
    ctx.save();
    ctx.translate(T / 2 + dx * T * 0.36, T / 2 + dy * T * 0.36);
    ctx.rotate(Math.atan2(dy, dx));
    ctx.beginPath();
    ctx.moveTo(8, 0);
    ctx.lineTo(-4, -7);
    ctx.lineTo(-4, 7);
    ctx.closePath();
    ctx.fillStyle = c.color;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "#000";
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}

/** 跟隨施放者的區域：施放者腳下的一圈虛線環。 */
export function drawCasterRing(ctx: Ctx, color: string): void {
  ctx.save();
  ctx.setLineDash([4, 3]);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.beginPath();
  ctx.ellipse(T / 2, T * 0.8, T * 0.36, T * 0.13, 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}
