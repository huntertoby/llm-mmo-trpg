// SK-3 重擲的骰子層（AR-SK3）：`battle/rerollFx.ts` 的描述與時間軸 → 效果（一張離屏 canvas，畫在單位之上的效果層）。
// 畫法照 docs/art/sample/sk3Mechanics.js 第 2 版的 `fieldDie`／`fieldKnock`／`fieldAdopt`／`fieldBeam`／`fieldPulse`／`fieldCmp` 逐行搬
// （比較箭頭照 N1 一律米白）；二十面骰用 `qIcon/parts.ts` 的 `d20`（同部件、同「擲出自然 20 時」）。
// 身體動作不在這次範圍（暫借的側擋照現行）；反應者只有腳下光圈與引線。時間是未縮放的毫秒，這裡乘上播放速度的倍率 `scale`。
import type { UnitDraw } from "../battle/drawModel";
import { isGiantDraw } from "../battle/drawModel";
import { adoptPx, clamp, DIE_R, dieDy, dieMK, ease, oldOff, RING_K, REROLL_MS, rerollFrame, type DieState, type RerollFx } from "../battle/rerollFx";
import { glow, OUT, poly, TAU, type Pt as QPt } from "./qIcon/core";
import { d20, DIE } from "./qIcon/parts";
import { boxOf, canvasEffect, type Sk2Host } from "./sk2Effects";
import type { Pt } from "./sk2FxArt";
import { creatureOf, FEET, unitTopY } from "./unitSprite";
import type { Effect } from "./vfxEffects";

const CREAM = "#f2e6c8";
const DIE_HEX: QPt[] = [0, 1, 2, 3, 4, 5].map((i): QPt => [Math.cos((i / 6) * TAU - Math.PI / 2) * 10.6, Math.sin((i / 6) * TAU - Math.PI / 2) * 10.6]);
/** 「採用」：玩法 PM 定案的字（移植需求第 2 節）。 */
export const WORD_ADOPT = "採用";
/** 浮字的字型（照現行浮字：Noto Sans TC 700）。 */
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";

/** 繪製器提供的操作：SK-2 的那一組，加上單位的繪製資料（巨型單位、頭目的頭頂）。 */
export interface RerollHost extends Sk2Host {
  draw(id: string): UnitDraw | undefined;
}

/** 戰場上的一顆骰子（中心 x,y）。 */
function fieldDie(g: CanvasRenderingContext2D, x: number, y: number, mk: number, s: DieState): void {
  const R = DIE_R * mk * s.k, a = s.a;
  if (R < 0.5 || a <= 0) return;
  const pal = s.dim ? DIE.dim : DIE.lav;
  g.save();
  g.globalAlpha *= a;
  g.translate(x, y);
  g.scale(1, s.sy);
  if (s.ring > 0) {
    g.save();
    g.globalAlpha *= s.ring;
    glow(g, 0, 0, R * 1.9, "#ffe066", 0.5);
    g.beginPath();
    g.arc(0, 0, R * RING_K, 0, TAU);
    g.lineWidth = 4.2 * mk;
    g.strokeStyle = OUT;
    g.stroke();
    g.lineWidth = 2.2 * mk;
    g.strokeStyle = "#ffd23f";
    g.stroke();
    g.restore();
  }
  d20(g, 0, 0, R, pal, { rot: s.rot, face: s.face, ink: ((1.6 * 10.6) / R) * mk });
  if (s.flash > 0) {
    g.save();
    g.globalAlpha *= s.flash;
    g.save();
    g.rotate(s.rot);
    g.scale(R / 10.6, R / 10.6);
    poly(g, "#ffffff", DIE_HEX, 0.5);
    g.restore();
    g.restore();
  }
  if (s.cross > 0) {
    const L = R * 0.95 * s.cross;
    g.lineCap = "round";
    for (const [w, col] of [[3.8 * mk, OUT], [2.0 * mk, "#ff4a5a"]] as const) {
      g.beginPath();
      g.moveTo(-R * 0.95, R * 0.95);
      g.lineTo(-R * 0.95 + 2 * L, R * 0.95 - 2 * L);
      g.lineWidth = w;
      g.strokeStyle = col;
      g.stroke();
    }
    // 點數在紅斜槓之上再描一次（骰面色描邊），劃掉的那顆仍讀得出點數
    g.save();
    g.rotate(s.rot);
    g.scale(R / 10.6, R / 10.6);
    const t = String(s.face);
    g.font = `900 ${t.length > 1 ? 7.2 : 8.4}px Arial, sans-serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.lineJoin = "round";
    g.lineWidth = 1.6;
    g.strokeStyle = pal.face;
    g.strokeText(t, 0, 1.4);
    g.fillStyle = pal.ink;
    g.fillText(t, 0, 1.4);
    g.restore();
  }
  g.restore();
}

/** 敲一下：骰子左右各兩道短金線往外彈、淡出（只往左右）。p＝0～1。 */
function fieldKnock(g: CanvasRenderingContext2D, x: number, y: number, p: number, mk: number): void {
  if (p <= 0 || p >= 1) return;
  const R = DIE_R * mk, e = ease(p);
  g.save();
  g.globalAlpha *= 1 - p;
  g.lineCap = "round";
  for (const ang of [-0.32, 0.32, Math.PI - 0.32, Math.PI + 0.32]) {
    const c0 = Math.cos(ang), s0 = Math.sin(ang), r0 = R * (1.15 + 0.35 * e), r1 = r0 + R * (0.55 - 0.15 * e);
    for (const [w, col] of [[3.6 * mk, OUT], [1.8 * mk, "#ffd23f"]] as const) {
      g.beginPath();
      g.moveTo(x + c0 * r0, y + s0 * r0);
      g.lineTo(x + c0 * r1, y + s0 * r1);
      g.lineWidth = w;
      g.strokeStyle = col;
      g.stroke();
    }
  }
  g.restore();
}

/** 「採用」：壓在算數那一顆的下半（點數下面）；字型照現行浮字（Noto Sans TC 700、黑邊、金 #ffe066）。 */
function fieldAdopt(g: CanvasRenderingContext2D, x: number, y: number, k: number, a: number, mk: number, mapScale: number): void {
  if (a <= 0) return;
  const R = DIE_R * mk * k, px = adoptPx(mapScale), cy = y + R * 0.5 + px * 0.55;
  g.save();
  g.globalAlpha *= a;
  g.font = `700 ${px}px ${FONT}`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.lineJoin = "round";
  g.strokeStyle = "#000";
  g.lineWidth = Math.max(3, px * 0.24);
  g.strokeText(WORD_ADOPT, x, cy);
  g.fillStyle = "#ffe066";
  g.fillText(WORD_ADOPT, x, cy);
  g.restore();
}

/** 引線的控制點：中點沿法線外推 0.35 倍長＋10；兩條法線取較往上的那條，一樣高時取往左。 */
export function beamControl(from: Pt, to: Pt): Pt {
  const dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1;
  let nx = -dy / len, ny = dx / len;
  if (ny > 1e-6 || (Math.abs(ny) <= 1e-6 && nx > 0)) {
    nx = -nx;
    ny = -ny;
  }
  const bow = 0.35 * len + 10;
  return { x: (from.x + to.x) / 2 + nx * bow, y: (from.y + to.y) / 2 + ny * bow };
}

/** 金色引線（反應者胸口 → 骰子）：二次曲線往旁邊拱；p＝長到哪；頭上一顆金光點。 */
function fieldBeam(g: CanvasRenderingContext2D, from: Pt, to: Pt, p: number, a: number, mk: number): void {
  if (p <= 0 || a <= 0) return;
  const c = beamControl(from, to);
  const pt = (q: number): Pt => {
    const u = 1 - q;
    return { x: u * u * from.x + 2 * u * q * c.x + q * q * to.x, y: u * u * from.y + 2 * u * q * c.y + q * q * to.y };
  };
  g.save();
  g.globalAlpha *= a;
  g.lineCap = "round";
  g.lineJoin = "round";
  for (const [w, col] of [[4.2 * mk, OUT], [2.2 * mk, "#ffd23f"], [0.9 * mk, "#fff6d0"]] as const) {
    g.beginPath();
    for (let q = 0; q <= p + 1e-6; q += 0.04) {
      const s = pt(Math.min(q, p));
      if (q === 0) g.moveTo(s.x, s.y);
      else g.lineTo(s.x, s.y);
    }
    g.strokeStyle = col;
    g.lineWidth = w;
    g.stroke();
  }
  if (p < 1) {
    const h = pt(p);
    glow(g, h.x, h.y, 9 * mk, "#ffe066", 0.8);
    g.beginPath();
    g.arc(h.x, h.y, 2.6 * mk, 0, TAU);
    g.fillStyle = "#ffffff";
    g.fill();
  }
  g.restore();
}

/** 反應者腳下的金色光圈（腳底橢圓往外擴、淡出）。 */
function fieldPulse(g: CanvasRenderingContext2D, feet: Pt, p: number, mk: number): void {
  if (p <= 0 || p >= 1) return;
  const r = 14 + 12 * ease(p);
  g.save();
  g.globalAlpha *= 1 - p;
  g.beginPath();
  g.ellipse(feet.x, feet.y, r, r * 0.42, 0, 0, TAU);
  g.lineWidth = 3 * mk;
  g.strokeStyle = "#ffd23f";
  g.stroke();
  g.restore();
}

/** 比較箭頭（舊 → 新）：往上（變大）或往下（變小），一律米白中性色（N1），只表示方向。 */
function fieldCmp(g: CanvasRenderingContext2D, x: number, y: number, up: boolean, a: number, mk: number): void {
  if (a <= 0) return;
  const s = mk * 0.62;
  g.save();
  g.globalAlpha *= a;
  g.translate(x, y);
  g.scale(s, up ? s : -s);
  const P: QPt[] = [[-2.8, 9], [-2.8, -1], [-7.4, -1], [0, -9.6], [7.4, -1], [2.8, -1], [2.8, 9]];
  poly(g, OUT, P.map(([px, py]): QPt => [px * 1.25, py * 1.18]), 0.6);
  poly(g, CREAM, P, 0.4);
  poly(g, "#ffffff", [[0, -9.6], [-7.4, -1], [-2.8, -1], [-2.8, 9], [-0.8, 9], [-0.8, -6.6]]);
  g.restore();
}

/** 骰子層的幾何：骰子原位（世界座標）、反應者的腳與胸口。 */
export interface RerollGeom {
  home: Pt;
  feet: Pt;
  chest: Pt;
  mk: number;
  mapScale: number;
}

/** 一整格骰子層（照 `rerollFrame` 的樣子）。 */
export function paintReroll(g: CanvasRenderingContext2D, t: number, f: RerollFx, geo: RerollGeom): void {
  const fr = rerollFrame(t, f, geo.mk), { home, mk } = geo;
  if (fr.fade <= 0) return;
  const off = oldOff(mk), gh = { x: home.x + off.x, y: home.y + off.y };
  g.save();
  g.globalAlpha = fr.fade;
  fieldPulse(g, geo.feet, fr.pulse, mk);
  fieldBeam(g, geo.chest, home, fr.beam, fr.beamA, mk);
  fieldDie(g, home.x + fr.old.x, home.y + fr.old.y, mk, fr.old);
  fieldKnock(g, home.x, home.y, fr.knock, mk);
  if (fr.fresh !== null) fieldDie(g, home.x + fr.fresh.x, home.y + fr.fresh.y, mk, fr.fresh);
  if (fr.cmpA > 0) fieldCmp(g, (gh.x + home.x) / 2, (gh.y + home.y) / 2 + mk, fr.cmpUp, fr.cmpA, mk);
  if (fr.adoptA > 0) {
    if (fr.adoptOld) fieldAdopt(g, gh.x, gh.y, fr.old.k, fr.adoptA, mk, geo.mapScale);
    else if (fr.fresh !== null) fieldAdopt(g, home.x, home.y, fr.fresh.k, fr.adoptA, mk, geo.mapScale);
  }
  g.restore();
}

/**
 * 骰子中心的上緣基準（相對格子中心）：一般單位＝上一排血條下緣（`dieDy` 的預設）；
 * 巨型單位、頭目＝它自己的頭頂（`unitTopY`；頭頂上方是它的 HUD，不往上長，移植需求第 6 項）。
 */
export function dieTopOf(u: UnitDraw | undefined): number | undefined {
  if (u === undefined) return undefined;
  return isGiantDraw(u) || creatureOf(u)?.boss !== undefined ? unitTopY(u) : undefined;
}

function nodeAt(host: RerollHost, id: string): Pt | null {
  const n = host.unitNode(id);
  if (n !== null && !n.destroyed) return { x: n.x, y: n.y };
  const u = host.draw(id);
  return u === undefined ? null : host.center({ x: u.x, y: u.y });
}

/** 這一次重擲的骰子層效果（`now` 起、長 `REROLL_MS × scale`）；找不到擲骰的人時 `null`。 */
export function rerollEffect(host: RerollHost, f: RerollFx, now: number, scale: number): Effect | null {
  const roller = nodeAt(host, f.rollerId);
  if (roller === null) return null;
  const mapScale = host.boardScale(), mk = dieMK(mapScale);
  const home = { x: roller.x, y: roller.y + dieDy(mk, dieTopOf(host.draw(f.rollerId))) };
  const reactor = nodeAt(host, f.reactorId) ?? roller;
  const feet = { x: reactor.x, y: reactor.y + FEET }, chest = { x: feet.x, y: feet.y - 22 };
  const off = oldOff(mk);
  const R = DIE_R * mk;
  const pts = [home, { x: home.x + off.x, y: home.y + off.y }, feet, chest, beamControl(chest, home)];
  const box = boxOf(pts, Math.max(R * 2.2, adoptPx(mapScale) * 1.6 + R) + 26);
  const geo: RerollGeom = { home, feet, chest, mk, mapScale };
  return canvasEffect(host, now, REROLL_MS, scale, box, (ctx, t) => paintReroll(ctx, clamp(t, 0, REROLL_MS), f, geo));
}

/** 這一步的重擲：一個接一個（每個 `REROLL_MS`）。 */
export function rerollEffects(host: RerollHost, list: readonly RerollFx[], now: number, scale: number): Effect[] {
  const out: Effect[] = [];
  list.forEach((f, i) => {
    const e = rerollEffect(host, f, now + i * REROLL_MS * scale, scale);
    if (e !== null) out.push(e);
  });
  return out;
}
