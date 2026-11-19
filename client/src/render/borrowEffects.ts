// AP-2 預支的施放演出（AR-AP2）：`battle/borrowFx.ts` 的時間軸 → 效果（一張離屏 canvas，畫在單位之上的效果層）。
// 畫法照 docs/art/sample/ap2Borrow.js 的 `fieldGem`／`fieldSlot`／`fieldArrive` 逐行搬（AP-2-美術.md 第 4 節、5.3）；
// 菱形用部件的 `gem`（半對角 < 7 模型 px 走兩階 tiny 版）。時間是未縮放的毫秒，這裡乘上播放速度的倍率 `scale`。
import { BORROW_MS, borrowFrame, borrowMK, chestAt, GEM_R, SLOT_R, slotAt } from "../battle/borrowFx";
import { lerp } from "../battle/rerollFx";
import { OUT, TAU } from "./qIcon/core";
import { BORROW, gem, SLOT_ICON } from "./qIcon/parts";
import { boxOf, canvasEffect, type Sk2Host } from "./sk2Effects";
import type { Pt } from "./sk2FxArt";
import type { Effect } from "./vfxEffects";

type G = CanvasRenderingContext2D;
const ease = (t: number): number => {
  const u = Math.max(0, Math.min(1, t));
  return u * u * (3 - 2 * u);
};

/** 菱形（模型 px）：部件 `gem` 的戰場版（外框色描一圈 2.4×MK）。 */
export function fieldGem(g: G, x: number, y: number, k: number, a: number, mk: number): void {
  const R = GEM_R * mk * k;
  if (R < 0.3 || a <= 0) return;
  g.save();
  g.globalAlpha *= a;
  g.lineJoin = "round";
  g.beginPath();
  g.moveTo(x, y - R);
  g.lineTo(x + R, y);
  g.lineTo(x, y + R);
  g.lineTo(x - R, y);
  g.closePath();
  g.strokeStyle = OUT;
  g.lineWidth = 2.4 * mk;
  g.stroke();
  g.save();
  g.translate(x, y);
  g.scale(R / 10, R / 10);
  gem(g, { tiny: R * 2 < 14 }, 0, 0, 10);
  g.restore();
  g.restore();
}

/** 「下回合的那格」（模型 px）：灰框空心圓（洞是半透明深色）、不透明度 0.8；`slash`＝紅斜線畫到哪（0～1）。框用亮一階的 #b3a994（美術 PM 裁定 6）。 */
export function fieldSlot(g: G, x: number, y: number, k: number, a: number, slash: number, mk: number): void {
  const r = SLOT_R * mk * k;
  if (r < 0.3 || a <= 0) return;
  g.save();
  g.globalAlpha *= a * 0.8;
  g.beginPath();
  g.arc(x, y, r, 0, TAU);
  g.fillStyle = "rgba(10,12,18,0.55)";
  g.fill();
  g.lineWidth = 3.8 * mk;
  g.strokeStyle = OUT;
  g.stroke();
  g.lineWidth = 2.0 * mk;
  g.strokeStyle = SLOT_ICON.ring;
  g.stroke();
  if (slash > 0) {
    const d = r * 0.62, x0 = x - d, y0 = y + d, x1 = lerp(x0, x + d, slash), y1 = lerp(y0, y - d, slash);
    g.lineCap = "round";
    for (const [w, col] of [[3.6 * mk, OUT], [2.0 * mk, SLOT_ICON.slash]] as const) {
      g.beginPath();
      g.moveTo(x0, y0);
      g.lineTo(x1, y1);
      g.lineWidth = w;
      g.strokeStyle = col;
      g.stroke();
    }
  }
  g.restore();
}

/** 菱形到胸口的一下：一圈橘色光圈往外擴、淡出（p＝0～1；0、1 不畫）。 */
export function fieldArrive(g: G, x: number, y: number, p: number, mk: number): void {
  if (p <= 0 || p >= 1) return;
  const r = (4 + 7 * ease(p)) * mk;
  g.save();
  g.globalAlpha *= 1 - p;
  g.beginPath();
  g.arc(x, y, r, 0, TAU);
  g.lineWidth = 3 * mk;
  g.strokeStyle = OUT;
  g.stroke();
  g.lineWidth = 1.6 * mk;
  g.strokeStyle = BORROW.body;
  g.stroke();
  g.restore();
}

/** 演出這一刻（`c`＝施放者格子中心，世界座標）：那格、光圈、菱形（同樣張的順序）。 */
export function paintBorrow(g: G, t: number, c: Pt, mk: number, dir: 1 | -1): void {
  const f = borrowFrame(t, mk, dir);
  if (f === null) return;
  fieldSlot(g, c.x + f.slot.x, c.y + f.slot.y, f.slot.k, f.slot.a, f.slot.slash, mk);
  fieldArrive(g, c.x + f.arrive.x, c.y + f.arrive.y, f.arrive.p, mk);
  fieldGem(g, c.x + f.gem.x, c.y + f.gem.y, f.gem.k, f.gem.a, mk);
}

/** 離屏 canvas 要框住的範圍：那格、胸口、弧線的控制點，外加光圈最大半徑。 */
export function borrowBox(c: Pt, mk: number, dir: 1 | -1): { x: number; y: number; w: number; h: number } {
  const s = slotAt(dir, mk), ch = chestAt(dir);
  const pts: Pt[] = [{ x: c.x + s.x, y: c.y + s.y }, { x: c.x + ch.x, y: c.y + ch.y }, { x: c.x + (s.x + ch.x) / 2, y: c.y + Math.min(s.y, ch.y) - 6 * mk }];
  return boxOf(pts, Math.max((SLOT_R + 1.9) * mk, 12.5 * mk, GEM_R * mk + 1.2 * mk) + 4);
}

/** 施放演出 `borrow_pull` 的特效（`startMs` 起、長 `BORROW_MS × scale`）；建不出畫布時 `null`。 */
export function borrowEffect(host: Pick<Sk2Host, "deco">, c: Pt, dir: 1 | -1, mapScale: number, startMs: number, scale: number): Effect | null {
  const mk = borrowMK(mapScale);
  return canvasEffect(host, startMs, BORROW_MS, scale, borrowBox(c, mk, dir), (ctx, t) => paintBorrow(ctx, t, c, mk, dir));
}
