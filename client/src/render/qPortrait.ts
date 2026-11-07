// Q 版頭像（QK-2；照 docs/art/sample/qPortrait.js 的點列與規則改寫，需求 docs/art/QK移植需求.md 第 3 節）。
// 做法：Q 版紙娃娃正面（drawQ，不描外框）＋頭像配件，三層合起來描同一圈剪影外框（1.3 單位，同 qStamp），取頭和肩膀放大。
// - 每 42 個紙娃娃單位對應頭像邊長，頭心在框的 (0.5, 0.53)。
// - 配件畫在體型座標裡（6T-1d 決定）：先套 build（stout 1.12×0.88、tall 0.96×1.1）與 frame，tall、stout 的頭變形時配件跟著走。
// - 會伸出頭外的配件（斗笠、頭帶、羽冠、珊瑚、頭環、耳環、毛領、郵袋、帽徽、戴帽時的護目鏡）和本體一起描外框（C 層）；
//   臉上的（疤、皺紋、煤灰）只畫在臉的皮膚區域（本體填色層裡和膚色相近的像素：扣掉頭髮、帽、鏡片、鬍子）；
//   義眼、餘燼眼、符文、霧、胸前十字不描外框（D 層）。
// - 好感五級（21.5）：換眼、眉、嘴；被護目鏡、義眼、面紗遮住的部分不換，配件畫在表情上面。頭頂徽章另畫（`drawMoodBadge`）。
// 確定性：沒有亂數。沒有 DOM（vitest）時直接畫填色、不描外框，皮膚區域用臉圓代替。
import type { Ctx } from "./artDraw";
import { fill, getM, Q_OUT, rr, TAU, type QHooks, type QItem, type QLook, type QUnit } from "./qCore";
import { drawQ } from "./qDoll";

/** 頭像邊長對應的紙娃娃單位、頭心在框裡的高度比例。 */
export const QP_UNITS = 42;
export const QP_HEAD_Y = 0.53;
/** 紙娃娃的頭心（單位）。 */
const HEAD_CY = -29;
/** 外框半徑（單位，同 qStamp 的 Q_LINE）。 */
const LINE = 1.3;

/** 體型縮放（同 qRace.raceBuild）。 */
export const QP_BUILD: Readonly<Record<string, readonly [number, number]>> = { stout: [1.12, 0.88], tall: [0.96, 1.1] };
const FRAME: Readonly<Record<string, readonly [number, number]>> = { slim: [0.92, 1.02], broad: [1.08, 0.98] };

/** 頭像配件 23 個（樣張 EXTRAS_ALL；fox 是白狐霜音整張狐臉）。 */
export const Q_PORTRAIT_EXTRAS = [
  "wrinkles", "cap", "mustache", "fur_collar", "mist", "wide_hat", "scar", "fox", "headband", "bandana", "earring", "goggles_up",
  "soot", "goggles", "rune", "ember_eye", "coral", "crest", "apron_cross", "circlet", "cyber_eye", "post_badge", "mailbag",
] as const;

/** 只畫在臉的皮膚區域裡的配件。 */
export const SKIN_EXTRAS: ReadonlySet<string> = new Set(["scar", "wrinkles", "soot"]);

/** 好感五級徽章色：0 敵意、1 冷淡、2 普通、3 友善、4 信賴。 */
export const MOOD_COLORS = ["#c83a2a", "#8a8aa8", "#e8e0d0", "#ffd23a", "#ff8ab0"] as const;

function line(ctx: Ctx, c: string, w: number, pts: readonly (readonly [number, number])[]): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
  ctx.stroke();
}

const dk = (hex: string, t: number): string => {
  const n = (i: number): number => parseInt(hex.slice(i, i + 2), 16);
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return hex;
  return `#${[n(1), n(3), n(5)].map((v) => Math.round(v * (1 - t)).toString(16).padStart(2, "0")).join("")}`;
};

/** 頭像用的部件（樣張 QNpc.prep 對頭像配件的換算＋qNpc 的 PART）：在本體前（C）或後（B）。 */
export interface QPortraitPart {
  k: "douli" | "headband" | "goggles_up" | "mailbag" | "fur_collar";
  cap?: boolean;
}

/**
 * 頭像配件換成 Q 版的頭部裝備或部件（樣張 QNpc.prep，portrait＝true）：沒戴帽時斗笠、頭帶畫成部件，帽、頭巾、護目鏡換成頭部裝備；
 * 毛領、額上護目鏡、郵袋是部件；八字鬍是鬍子樣式。回傳新的 unit（不改原物件）與部件清單。
 */
export function qPortraitPrep(unit: QUnit, extras: readonly string[]): { unit: QUnit; parts: QPortraitPart[] } {
  const look: QLook = { ...unit.look };
  const gear: QUnit["gear"] = { ...unit.gear };
  const parts: QPortraitPart[] = [];
  for (const e of extras) {
    if (e === "wide_hat" && !gear.head) parts.push({ k: "douli" });
    else if (e === "headband" && !gear.head) parts.push({ k: "headband" });
    else if (e === "goggles_up") parts.push({ k: "goggles_up", cap: !!gear.head });
    else if (e === "goggles" && !gear.head) gear.head = { kind: "goggles" };
    else if (e === "cap" && !gear.head) gear.head = { kind: "cap", color: "#3a2a1a" };
    else if (e === "bandana" && !gear.head) gear.head = { kind: "bandana", color: "#a83a2a" };
    else if (e === "fur_collar" && !gear.neck) parts.push({ k: "fur_collar" });
    else if (e === "mustache" && !look.beard) look.beardStyle = "mustache";
    else if (e === "mailbag") parts.push({ k: "mailbag" });
  }
  return { unit: { look, gear }, parts };
}

// ---------- 部件（qNpc.js 的 PART，只取正面） ----------
/** 頭下面的部件：挖掉頭（樣張 headClip）。 */
function headClip(ctx: Ctx): void {
  ctx.beginPath();
  ctx.rect(-80, -120, 160, 200);
  ctx.arc(0, HEAD_CY, 8.7, 0, TAU);
  ctx.clip("evenodd");
}

function bagShape(ctx: Ctx, x: number, y: number, col: string | undefined, back: boolean): void {
  const c = col ?? "#d8c8a0";
  fill(ctx, c, () => rr(ctx, x, y, 6, 5.6, 1.2));
  fill(ctx, dk(c, 0.25), () => rr(ctx, x, y, 6, 2.4, 1));
  if (!back) fill(ctx, "#2a2420", () => rr(ctx, x + 2.4, y + 1.8, 1.2, 1.4, 0.3));
}

function partBehind(ctx: Ctx, p: QPortraitPart): void {
  if (p.k === "mailbag") bagShape(ctx, -12.6, -12.2, undefined, true);
}

function partFront(ctx: Ctx, p: QPortraitPart): void {
  switch (p.k) {
    case "douli": {
      const c = "#c8b07a";
      const d = dk(c, 0.22);
      fill(ctx, c, () => {
        ctx.moveTo(-12.6, -33);
        ctx.quadraticCurveTo(0, -31.6, 12.6, -33);
        ctx.lineTo(0, -43.6);
        ctx.closePath();
      });
      for (const x of [-6.6, 0, 6.6]) line(ctx, d, 0.5, [[0, -43.2], [x, -32.4]]);
      line(ctx, d, 0.7, [[-12.6, -33], [12.6, -33]]);
      line(ctx, "#6a4a2a", 0.6, [[-6.4, -31.8], [-5.2, -24.6]]);
      line(ctx, "#6a4a2a", 0.6, [[6.4, -31.8], [5.2, -24.6]]);
      break;
    }
    case "headband": {
      fill(ctx, "#b8432f", () => {
        ctx.moveTo(-8.9, -33.6);
        ctx.quadraticCurveTo(0, -35.4, 8.9, -33.6);
        ctx.lineTo(8.7, -31.6);
        ctx.quadraticCurveTo(0, -33.2, -8.7, -31.6);
        ctx.closePath();
      });
      break;
    }
    case "goggles_up": {
      ctx.save();
      if (p.cap === true) ctx.translate(0, -1.6); // 戴帽子時架在帽沿上
      line(ctx, "#3a3a44", 1.3, [[-8.8, -34.4], [8.8, -34.4]]);
      for (const x of [-3.2, 3.2]) {
        fill(ctx, "#8d969f", () => ctx.ellipse(x, -35, 2.8, 2.3, 0, 0, TAU));
        fill(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(x, -35, 1.9, 1.5, 0, 0, TAU));
      }
      ctx.restore();
      break;
    }
    case "mailbag":
      line(ctx, "#6a4a2a", 1.3, [[6.2, -20.6], [-6.4, -9.6]]);
      break;
    case "fur_collar": {
      // 毛領（qDoll.js neckWide）：脖子一圈蓬鬆毛；頭像在頭下面（挖掉頭）
      const c = "#d8c8a8";
      const xs = [-8, -5.4, -2.7, 0, 2.7, 5.4, 8];
      ctx.save();
      headClip(ctx);
      fill(ctx, c, () => {
        for (const x of xs) {
          ctx.moveTo(x + 1.9, -20.4);
          ctx.ellipse(x, -20.4 + Math.abs(x) * 0.06, 1.9, 1.7, 0, 0, TAU);
        }
      });
      line(ctx, dk(c, 0.2), 0.4, [[xs[0]!, -19.2], [xs[xs.length - 1]!, -19.2]]);
      ctx.restore();
      break;
    }
    default:
      break;
  }
}

// ---------- 頭像配件（樣張 EXC：和本體一起描外框） ----------
function extraOutlined(ctx: Ctx, e: string, gear: QUnit["gear"]): void {
  switch (e) {
    case "earring":
      fill(ctx, "#e8bb48", () => ctx.arc(-8.9, -24.6, 1.05, 0, TAU));
      break;
    case "coral":
      for (const [x, y, r, c] of [[-6.4, -37, 1.5, "#e8806e"], [-4, -38.4, 1.3, "#f2a090"], [-1.8, -37.8, 1.1, "#e8806e"]] as const) fill(ctx, c, () => ctx.arc(x, y, r, 0, TAU));
      fill(ctx, "#e8806e", () => rr(ctx, -6.8, -37.6, 5.4, 1.4, 0.6));
      break;
    case "crest":
      fill(ctx, "#5a7ad0", () => {
        ctx.moveTo(-1.4, -38.6);
        ctx.quadraticCurveTo(-2.2, -45, 2.6, -47);
        ctx.quadraticCurveTo(1, -43, 1.6, -38.6);
        ctx.closePath();
      });
      fill(ctx, "#8ab0ff", () => rr(ctx, -1.6, -40, 3.2, 1.6, 0.6));
      break;
    case "circlet":
      fill(ctx, "#e8bb48", () => {
        ctx.moveTo(-8.9, -33.4);
        ctx.quadraticCurveTo(0, -36.6, 8.9, -33.4);
        ctx.lineTo(8.8, -32.2);
        ctx.quadraticCurveTo(0, -35.2, -8.8, -32.2);
        ctx.closePath();
      });
      fill(ctx, "#a898ff", () => {
        ctx.moveTo(0, -37.6);
        ctx.lineTo(1.7, -35.2);
        ctx.lineTo(0, -32.8);
        ctx.lineTo(-1.7, -35.2);
        ctx.closePath();
      });
      fill(ctx, "rgba(255,255,255,0.6)", () => ctx.arc(-0.5, -35.8, 0.5, 0, TAU));
      break;
    case "goggles":
      // 沒戴帽子時已換成 Q 版頭部裝備 goggles；戴帽子時在這裡補畫（同一個造型）
      if (gear.head?.kind === "goggles") return;
      line(ctx, "#3a3a44", 1.3, [[-8.8, -29.6], [8.8, -29.6]]);
      for (const x of [-3, 3]) {
        fill(ctx, "#8d969f", () => ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU));
        fill(ctx, "rgba(160,220,255,0.75)", () => ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU));
      }
      break;
    case "post_badge":
      fill(ctx, "#d9b24a", () => rr(ctx, -2, -35.4, 4, 2.6, 0.6));
      fill(ctx, "#f4efe2", () => rr(ctx, -1.3, -34.9, 2.6, 1.6, 0.3));
      line(ctx, "#a8582a", 0.35, [[-1.3, -34.9], [0, -34], [1.3, -34.9]]);
      break;
    default:
      break;
  }
}

/** soot 的位置（右頰，畫面右）與有大鬍子時往上移的那一抹（6T-1d：裁在臉的皮膚區域裡）。 */
export const Q_SOOT = { x: 5.4, y: -25.4, rx: 2.3, ry: 1.2, beardX: 6, beardY: -26.9 } as const;

// ---------- 樣張 EXD：不描外框（臉上的） ----------
function extraFace(ctx: Ctx, e: string, look: QLook): void {
  switch (e) {
    case "scar":
      line(ctx, "#8a3a2a", 0.9, [[-5.6, -33.2], [-3.4, -29.6], [-2.2, -25.4]]);
      for (const [x, y] of [[-4.9, -31.8], [-3.2, -28.2]] as const) line(ctx, "#8a3a2a", 0.55, [[x - 1, y + 0.4], [x + 1, y - 0.4]]);
      break;
    case "wrinkles":
      for (const s of [-1, 1]) line(ctx, "rgba(120,80,60,0.75)", 0.45, [[s * 6.2, -27.6], [s * 6.9, -26.4]]);
      line(ctx, "rgba(120,80,60,0.6)", 0.45, [[-2.4, -33.4], [2.4, -33.4]]);
      break;
    case "soot":
      fill(ctx, "rgba(40,30,25,0.45)", () => ctx.ellipse(Q_SOOT.x, Q_SOOT.y, Q_SOOT.rx, Q_SOOT.ry, 0.2, 0, TAU));
      if (look.beard === true) fill(ctx, "rgba(40,30,25,0.45)", () => ctx.ellipse(Q_SOOT.beardX, Q_SOOT.beardY, 2, 0.9, 0.2, 0, TAU));
      break;
    case "ember_eye":
      ctx.save();
      ctx.shadowColor = "#ff6a1a";
      ctx.shadowBlur = 5;
      fill(ctx, "#ffb030", () => ctx.rect(1.9, -30.2, 2, 3.4));
      ctx.restore();
      break;
    case "cyber_eye":
      fill(ctx, "#4a5058", () => rr(ctx, 0.6, -31.4, 4.6, 5.2, 1.2));
      ctx.save();
      ctx.shadowColor = "#4ad0c8";
      ctx.shadowBlur = 5;
      fill(ctx, "#7af0e8", () => ctx.rect(2.1, -30, 1.8, 2.4));
      ctx.restore();
      line(ctx, "#4ad0c8", 0.5, [[5.2, -29], [7.4, -29], [7.4, -26]]);
      break;
    case "rune":
      ctx.save();
      ctx.shadowColor = "#ff3a2a";
      ctx.shadowBlur = 3;
      fill(ctx, "#e84a2a", () => {
        ctx.moveTo(0, -35.6);
        ctx.lineTo(1.2, -33.6);
        ctx.lineTo(0, -32.2);
        ctx.lineTo(-1.2, -33.6);
        ctx.closePath();
      });
      ctx.restore();
      break;
    case "mist": {
      const g = ctx.createRadialGradient(0, -24, 2, 0, -24, 20);
      g.addColorStop(0, "rgba(236,238,232,0.0)");
      g.addColorStop(0.55, "rgba(236,238,232,0.35)");
      g.addColorStop(1, "rgba(236,238,232,0)");
      ctx.fillStyle = g;
      ctx.fillRect(-24, -48, 48, 44);
      break;
    }
    case "apron_cross":
      fill(ctx, "#f4efe2", () => rr(ctx, -2.6, -18.6, 5.2, 5.2, 1));
      fill(ctx, "#c83a2a", () => ctx.rect(-0.7, -17.8, 1.4, 3.6));
      fill(ctx, "#c83a2a", () => ctx.rect(-1.8, -16.7, 3.6, 1.4));
      break;
    default:
      break;
  }
}

// ---------- 好感五級表情 ----------
/** 哪些被配件遮住：eyes 兩眼（護目鏡）、eyeR 畫面右那隻眼（義眼、餘燼眼）、mouth 嘴與腮紅（面紗）。 */
export interface QCover {
  eyes: boolean;
  eyeR: boolean;
  mouth: boolean;
}

export function qCovers(extras: readonly string[], head: QItem | undefined): QCover {
  return {
    eyes: extras.includes("goggles") || head?.kind === "goggles",
    eyeR: extras.includes("cyber_eye") || extras.includes("ember_eye"),
    mouth: head?.kind === "veil",
  };
}

/** 表情（level 2 普通＝不換）：換眼、眉、嘴；被遮住的不換。 */
export function drawExpression(ctx: Ctx, level: number | null, look: QLook, cv: QCover): void {
  if (level == null || level === 2) return;
  const ink = "#1d1a22";
  const sk = look.skin;
  const xs = cv.eyes ? [] : cv.eyeR ? [-2.9] : [-2.9, 2.9];
  const brow = (s: number, y0: number, y1: number): void =>
    line(ctx, ink, 0.9, [
      [s * 4.6, cv.eyes ? y0 - 1.4 : y0],
      [s * 1.6, cv.eyes ? y1 - 1.4 : y1],
    ]);
  if (level === 0) {
    for (const s of [-1, 1]) brow(s, -32.6, -31.2);
    if (!cv.mouth) line(ctx, ink, 0.7, [[-1.4, -23.4], [0, -24.2], [1.4, -23.4]]);
  }
  if (level === 1) {
    for (const x of xs) {
      fill(ctx, sk, () => ctx.rect(x - 1.1, -30.4, 2.2, 1.6));
      line(ctx, ink, 0.6, [[x - 1.2, -28.8], [x + 1.2, -28.8]]);
    }
    if (cv.eyes) for (const s of [-1, 1]) line(ctx, ink, 0.7, [[s * 4.4, -33.4], [s * 1.8, -33.4]]);
    if (!cv.mouth) line(ctx, ink, 0.6, [[-1.2, -23.8], [1.2, -23.8]]);
  }
  if (level >= 3) {
    for (const x of xs) {
      fill(ctx, sk, () => ctx.rect(x - 1.2, -30.4, 2.4, 3.8));
      line(ctx, ink, 0.95, [[x - 1.3, -28.2], [x, -29.6], [x + 1.3, -28.2]]);
    }
    if (cv.eyes) for (const s of [-1, 1]) line(ctx, ink, 0.7, [[s * 4.4, -33], [s * 3, -33.8], [s * 1.6, -33]]);
    if (!cv.mouth)
      fill(ctx, "#8a3a3a", () => {
        ctx.moveTo(-1.6, -24.4);
        ctx.quadraticCurveTo(0, -22.2, 1.6, -24.4);
        ctx.closePath();
      });
  }
  if (level === 4 && !cv.mouth) {
    ctx.fillStyle = "rgba(240,90,110,0.5)";
    for (const s of [-1, 1]) ctx.fillRect(s * 4.5 - 1.5, -26.8, 3, 1.6);
  }
}

/** 頭頂的好感徽章（Q 版：圓臉、方眼、腮紅；r＝半徑 px）。level 0～4。 */
export function drawMoodBadge(ctx: Ctx, x: number, y: number, r: number, level: number): void {
  const lv = Math.max(0, Math.min(4, Math.round(level)));
  const ink = "#16121a";
  ctx.save();
  ctx.translate(x, y);
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, TAU);
  ctx.fillStyle = MOOD_COLORS[lv]!;
  ctx.fill();
  ctx.lineWidth = Math.max(1.2, r * 0.16);
  ctx.strokeStyle = ink;
  ctx.stroke();
  const e = r * 0.36;
  const ew = r * 0.17;
  const eh = r * 0.32;
  ctx.fillStyle = ink;
  ctx.strokeStyle = ink;
  ctx.lineCap = "round";
  ctx.lineWidth = r * 0.13;
  if (lv === 3 || lv === 4)
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(s * e - ew * 1.3, -r * 0.08);
      ctx.lineTo(s * e, -r * 0.3);
      ctx.lineTo(s * e + ew * 1.3, -r * 0.08);
      ctx.stroke();
    }
  else if (lv === 1)
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(s * e - ew * 1.2, -r * 0.12);
      ctx.lineTo(s * e + ew * 1.2, -r * 0.12);
      ctx.stroke();
    }
  else for (const s of [-1, 1]) ctx.fillRect(s * e - ew / 2, -r * 0.34, ew, eh);
  if (lv === 0)
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(s * r * 0.62, -r * 0.56);
      ctx.lineTo(s * r * 0.16, -r * 0.4);
      ctx.stroke();
    }
  ctx.fillStyle = "rgba(220,90,90,0.45)";
  if (lv >= 2) for (const s of [-1, 1]) ctx.fillRect(s * r * 0.58 - r * 0.15, r * 0.12, r * 0.3, r * 0.14);
  ctx.beginPath();
  if (lv === 0) ctx.arc(0, r * 0.62, r * 0.28, Math.PI * 1.15, Math.PI * 1.85);
  else if (lv === 1) {
    ctx.moveTo(-r * 0.22, r * 0.4);
    ctx.lineTo(r * 0.22, r * 0.4);
  } else if (lv === 2) ctx.arc(0, r * 0.18, r * 0.22, Math.PI * 0.2, Math.PI * 0.8);
  else {
    ctx.moveTo(-r * 0.3, r * 0.2);
    ctx.quadraticCurveTo(0, r * 0.66, r * 0.3, r * 0.2);
    ctx.closePath();
    ctx.fillStyle = "#8a3a3a";
    ctx.fill();
  }
  ctx.stroke();
  if (lv === 4) {
    ctx.fillStyle = "#e83a5a";
    ctx.lineWidth = r * 0.1;
    ctx.beginPath();
    const hx = r * 0.86;
    const hy = -r * 0.82;
    const s = r * 0.42;
    ctx.moveTo(hx, hy + s * 0.9);
    ctx.bezierCurveTo(hx - s * 1.2, hy, hx - s * 0.6, hy - s * 0.8, hx, hy - s * 0.2);
    ctx.bezierCurveTo(hx + s * 0.6, hy - s * 0.8, hx + s * 1.2, hy, hx, hy + s * 0.9);
    ctx.fill();
    ctx.stroke();
  }
  ctx.restore();
}

// ---------- 白狐霜音（不是紙娃娃） ----------
/** 狐臉（Q 語言：圓頭、三角耳、方眼冰藍、腮紅、額上冰紋），紙娃娃座標（頭心 (0,−29)）。 */
export function drawQFox(ctx: Ctx): void {
  const W = "#f6f2ea";
  const P = "#f0b0b0";
  fill(ctx, W, () => ctx.ellipse(0, -14, 9, 8, 0, 0, TAU));
  for (const s of [-1, 1]) {
    fill(ctx, W, () => {
      ctx.moveTo(s * 3, -36);
      ctx.lineTo(s * 9.6, -44.6);
      ctx.lineTo(s * 9.2, -31);
      ctx.closePath();
    });
    fill(ctx, P, () => {
      ctx.moveTo(s * 4.6, -36);
      ctx.lineTo(s * 8.8, -41.8);
      ctx.lineTo(s * 8.4, -33.4);
      ctx.closePath();
    });
  }
  fill(ctx, W, () => ctx.arc(0, -29, 8.8, 0, TAU));
  for (const s of [-1, 1])
    fill(ctx, W, () => {
      ctx.moveTo(s * 7.6, -27);
      ctx.lineTo(s * 11.4, -23.4);
      ctx.lineTo(s * 6.6, -22.6);
      ctx.closePath();
    });
  fill(ctx, "#ffffff", () => ctx.ellipse(0, -24.4, 4.2, 3, 0, 0, TAU));
  for (const s of [-1, 1]) {
    fill(ctx, "#3aa8e0", () => ctx.rect(s * 3.2 - 1, -30.6, 2, 3.2));
    fill(ctx, "#ffffff", () => ctx.rect(s * 3.2 - 0.6, -30.2, 0.7, 0.8));
  }
  ctx.fillStyle = "rgba(220,90,90,0.35)";
  ctx.fillRect(-7.2, -26.4, 2, 1.2);
  ctx.fillRect(5.2, -26.4, 2, 1.2);
  fill(ctx, "#2a2430", () => ctx.ellipse(0, -25.4, 1.2, 0.9, 0, 0, TAU));
  fill(ctx, "#7ad8ff", () => {
    ctx.moveTo(0, -36.8);
    ctx.lineTo(1.3, -34.4);
    ctx.lineTo(0, -33);
    ctx.lineTo(-1.3, -34.4);
    ctx.closePath();
  });
  for (const s of [-1, 1]) line(ctx, "#7ad8ff", 0.5, [[s * 1.6, -35.4], [s * 3.2, -36.6]]);
}

// ---------- 合成 ----------
type C2 = CanvasRenderingContext2D;
const hasDom = (): boolean => typeof document !== "undefined" && typeof document.createElement === "function";

function mk(w: number, h: number): C2 {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c.getContext("2d", { willReadFrequently: true }) as C2;
}

/** 剪影膨脹 r（像素）：12 個方向的短線段膨脹（同 qStamp 的 dilate）。 */
function dilate(src: HTMLCanvasElement, r: number): HTMLCanvasElement {
  const N = 12;
  const a = (r * Math.PI) / (2 * N);
  const P = [mk(src.width, src.height), mk(src.width, src.height)];
  let cur: HTMLCanvasElement = src;
  let n = 0;
  for (let i = 0; i < N; i++) {
    const t = (Math.PI * i) / N;
    const c = P[n++ % 2]!;
    c.clearRect(0, 0, src.width, src.height);
    for (const f of [-1, -0.5, 0, 0.5, 1]) c.drawImage(cur, Math.cos(t) * a * f, Math.sin(t) * a * f);
    cur = c.canvas;
  }
  return cur;
}

/** 把填色層描上剪影外框後貼到 ctx（同 qStamp：外框色、半徑 r 像素）。 */
function outlineOnto(ctx: Ctx, layer: HTMLCanvasElement, r: number, size: number): void {
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  const s = mk(layer.width, layer.height);
  s.drawImage(layer, 0, 0);
  s.globalCompositeOperation = "source-in";
  s.fillStyle = Q_OUT;
  s.fillRect(0, 0, layer.width, layer.height);
  const o = mk(layer.width, layer.height);
  o.drawImage(dilate(s.canvas, r), 0, 0);
  o.globalCompositeOperation = "source-in";
  o.fillStyle = Q_OUT;
  o.fillRect(0, 0, layer.width, layer.height);
  ctx.drawImage(o.canvas, 0, 0, size, size);
  ctx.drawImage(layer, 0, 0, size, size);
}

/** 離屏取樣倍數：至少照目前畫布縮放，且至少 192px（小的從 192 縮下來，同樣張），上限 8 倍。 */
function sampleScale(ctx: Ctx, px: number): number {
  const m = getM(ctx);
  const dev = Math.max(Math.hypot(m.a, m.b), Math.hypot(m.c, m.d), 0.25);
  return Math.min(8, Math.max(dev, 192 / px));
}

/** 臉的皮膚區域：本體填色層裡和膚色相近的像素（頭圓扣掉頭髮、帽、頭巾、鏡片、鬍子；腮紅、眼睛也扣掉）。 */
function skinMask(A: C2, hex: string, lim = 26): HTMLCanvasElement {
  const { width: w, height: h } = A.canvas;
  const d = A.getImageData(0, 0, w, h);
  const q = d.data;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  for (let i = 0; i < q.length; i += 4) {
    const ok = q[i + 3]! > 200 && Math.abs(q[i]! - r) + Math.abs(q[i + 1]! - g) + Math.abs(q[i + 2]! - b) < lim;
    q[i] = q[i + 1] = q[i + 2] = 0;
    q[i + 3] = ok ? 255 : 0;
  }
  const c = mk(w, h);
  c.putImageData(d, 0, 0);
  return c.canvas;
}

/** 頭像裡要畫的人：Q 版紙娃娃 unit（未換算頭像配件）、頭像配件、好感級別（null＝普通）。 */
export interface QPortraitFigure {
  unit: QUnit;
  extras: readonly string[];
  level?: number | null;
}

/** 腳底位置與縮放：頭心落在 (px/2, px × 0.53)（體型 by 會改頭心高度）。 */
export function qPortraitFrame(px: number, look: QLook): { k: number; fx: number; fy: number; bx: number; by: number } {
  const [bx0, by0] = QP_BUILD[look.build ?? ""] ?? [1, 1];
  const [fx0, fy0] = FRAME[look.frame ?? ""] ?? [1, 1];
  const k = px / QP_UNITS;
  return { k, fx: px / 2, fy: px * QP_HEAD_Y - HEAD_CY * by0 * fy0 * k, bx: bx0 * fx0, by: by0 * fy0 };
}

/**
 * 在 (0,0)～(px,px) 畫一個 Q 版頭像的人物（不含底色與框）。沒有 DOM 時直接畫填色（不描外框、皮膚區域用臉圓）。
 * 狐臉（extras 含 fox）另畫，一樣描外框。
 */
export function drawQPortraitFigure(ctx: Ctx, px: number, fig: QPortraitFigure, hooks: QHooks): void {
  const extras = fig.extras;
  const level = fig.level ?? null;
  if (extras.includes("fox")) {
    drawFoxFigure(ctx, px);
    return;
  }
  const { unit, parts } = qPortraitPrep(fig.unit, extras);
  const look = unit.look;
  const cv = qCovers(extras, fig.unit.gear.head);
  const f = qPortraitFrame(px, look);
  const inFrame = (c: Ctx, build: boolean): void => {
    c.translate(f.fx, f.fy);
    c.scale(f.k, f.k);
    if (build) c.scale(f.bx, f.by);
  };
  const front = (c: Ctx): void => {
    for (const p of parts) partFront(c, p);
    for (const e of extras) extraOutlined(c, e, unit.gear);
  };
  const skinLayer = (c: Ctx): void => {
    for (const e of extras) if (SKIN_EXTRAS.has(e)) extraFace(c, e, look);
  };
  const top = (c: Ctx): void => {
    drawExpression(c, level, look, cv);
    for (const e of extras) if (!SKIN_EXTRAS.has(e)) extraFace(c, e, look);
  };
  if (!hasDom()) {
    ctx.save();
    inFrame(ctx, false);
    ctx.save();
    ctx.scale(f.bx, f.by);
    for (const p of parts) partBehind(ctx, p);
    ctx.restore();
    drawQ(ctx, unit, "front", hooks, null, false);
    ctx.scale(f.bx, f.by);
    front(ctx);
    ctx.save();
    ctx.beginPath();
    ctx.arc(0, HEAD_CY, 8.4, 0, TAU);
    ctx.clip();
    skinLayer(ctx);
    ctx.restore();
    top(ctx);
    ctx.restore();
    return;
  }
  const sc = sampleScale(ctx, px);
  const w = Math.ceil(px * sc);
  const inOff = (c: Ctx, build: boolean): void => {
    c.scale(sc, sc);
    inFrame(c, build);
  };
  const A = mk(w, w);
  A.save();
  inOff(A, false);
  drawQ(A, unit, "front", hooks, null, false);
  A.restore();
  const B = mk(w, w);
  const C = mk(w, w);
  const D = mk(w, w);
  for (const [c, fn] of [
    [B, (x: Ctx) => parts.forEach((p) => partBehind(x, p))],
    [C, front],
    [D, top],
  ] as const) {
    c.save();
    inOff(c, true);
    fn(c);
    c.restore();
  }
  if (extras.some((e) => SKIN_EXTRAS.has(e))) {
    const E = mk(w, w);
    E.save();
    inOff(E, true);
    skinLayer(E);
    E.restore();
    E.globalCompositeOperation = "destination-in";
    E.drawImage(skinMask(A, look.skin), 0, 0);
    // 臉上的配件在表情之下（樣張 extraSkin 先畫進 D 層，表情再蓋上去）
    const D2 = mk(w, w);
    D2.drawImage(E.canvas, 0, 0);
    D2.drawImage(D.canvas, 0, 0);
    D.clearRect(0, 0, w, w);
    D.drawImage(D2.canvas, 0, 0);
  }
  const comb = mk(w, w);
  comb.drawImage(B.canvas, 0, 0);
  comb.drawImage(A.canvas, 0, 0);
  comb.drawImage(C.canvas, 0, 0);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  outlineOnto(ctx, comb.canvas, LINE * f.k * sc, px);
  ctx.drawImage(D.canvas, 0, 0, px, px);
  ctx.restore();
}

function drawFoxFigure(ctx: Ctx, px: number): void {
  const k = px / QP_UNITS;
  const place = (c: Ctx): void => {
    c.translate(px / 2, px * QP_HEAD_Y - HEAD_CY * k);
    c.scale(k, k);
  };
  if (hasDom()) {
    const sc = sampleScale(ctx, px);
    const off = mk(Math.ceil(px * sc), Math.ceil(px * sc));
    off.save();
    off.scale(sc, sc);
    place(off);
    drawQFox(off);
    off.restore();
    outlineOnto(ctx, off.canvas, LINE * k * sc, px);
  } else {
    ctx.save();
    place(ctx);
    drawQFox(ctx);
    ctx.restore();
  }
  const g = ctx.createRadialGradient(px / 2, px * QP_HEAD_Y, px * 0.2, px / 2, px * QP_HEAD_Y, px * 0.7);
  g.addColorStop(0, "rgba(200,240,255,0)");
  g.addColorStop(1, "rgba(200,240,255,0.32)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, px, px);
}
