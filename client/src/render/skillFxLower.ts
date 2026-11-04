// 技能片段附帶的特效（下半原語，Phase 6N-3；`skillClips.ts` 的 `FxCue`）：地表擴散／收縮、風、範圍線、升起的障礙、
// 揚塵、拋物線、陷阱、落下的符文、爆開、形態收放、保護線、金光、往外掃的光圈、飛過去的光球與圖示、倒轉、層數、
// 硬幣、響指、按住傷口。和 `skillFx.ts` 相同：每幀重畫、時間的函式、沒有亂數。
import type { Graphics } from "pixi.js";
import { TILE_SIZE } from "../battle/geometry";
import type { FxKind } from "./skillClips";

const T = TILE_SIZE;
type Pt = { x: number; y: number };
const TAU = Math.PI * 2;
const SPOKES = [0.1, 0.9, 1.7, 2.5, 3.3, 4.1, 4.9, 5.7];

/** 共用片段的小圖示：技能＝小方卡、行動點＝菱形、反應＝半圓盾、冷卻＝沙漏、重置＝雙線、`+1`／`-1`＝加減號。 */
export function drawIcon(g: Graphics, x: number, y: number, icon: string | null, color: number, alpha: number): void {
  const r = 3.2;
  switch (icon) {
    case "ap":
      g.poly([x, y - r, x + r, y, x, y + r, x - r, y]).fill({ color, alpha });
      return;
    case "reaction":
      g.arc(x, y - 1, r, Math.PI, 0).lineTo(x, y + r).closePath().fill({ color, alpha });
      return;
    case "cooldown":
      g.poly([x - r, y - r, x + r, y - r, x - r, y + r, x + r, y + r]).fill({ color, alpha });
      return;
    case "reset":
      g.moveTo(x - r, y - 1).lineTo(x + r, y - 1).moveTo(x + r, y + 1.5).lineTo(x - r, y + 1.5).stroke({ width: 1.3, color, alpha });
      return;
    case "+1":
      g.rect(x - r, y - 0.7, r * 2, 1.4).rect(x - 0.7, y - r, 1.4, r * 2).fill({ color, alpha });
      return;
    case "-1":
      g.rect(x - r, y - 0.7, r * 2, 1.4).fill({ color, alpha });
      return;
    default:
      g.roundRect(x - r * 0.8, y - r, r * 1.6, r * 2, 0.8).fill({ color, alpha });
  }
}

export interface LowerCue {
  g: Graphics;
  kind: FxKind;
  p: Pt;
  t: number;
  /** 淡出係數。 */
  a: number;
  c1: number;
  c2: number;
  link: { from: Pt; to: () => Pt } | undefined;
  icon: string | null;
}

function along(link: { from: Pt; to: () => Pt }, u: number, lift: number): Pt {
  const to = link.to();
  return { x: link.from.x + (to.x - link.from.x) * u, y: link.from.y + (to.y - link.from.y) * u - lift * Math.sin(u * Math.PI) };
}

/** 地表、地形、物件、符文類。回傳 `false` ＝ 不是這一組。 */
function drawWorld(c: LowerCue): boolean {
  const { g, p, t, a, c1, c2 } = c;
  const grow = Math.min(1, t * 1.6);
  switch (c.kind) {
    case "spread":
      g.ellipse(p.x, p.y, T * 0.5 * grow, T * 0.2 * grow).fill({ color: c1, alpha: 0.35 * a });
      g.ellipse(p.x, p.y, T * 0.5 * grow, T * 0.2 * grow).stroke({ width: 1.2, color: c2, alpha: 0.7 * a });
      return true;
    case "shrink":
      g.ellipse(p.x, p.y, T * 0.5 * (1 - t), T * 0.2 * (1 - t)).stroke({ width: 1.6, color: c1, alpha: 0.8 * a });
      return true;
    case "gust":
      for (const dy of [-T * 0.25, -T * 0.05, T * 0.12]) {
        const x0 = p.x - T * 0.4 + T * 0.5 * t;
        g.moveTo(x0, p.y + dy).quadraticCurveTo(x0 + T * 0.2, p.y + dy - 3, x0 + T * 0.4, p.y + dy).stroke({ width: 1.4, color: 0xffffff, alpha: 0.65 * a });
      }
      return true;
    case "zoneRing":
      g.ellipse(p.x, p.y, T * 0.55, T * 0.22).stroke({ width: 1 + 1.5 * t, color: c1, alpha: grow * a });
      return true;
    case "rise": {
      const h = T * 0.5 * grow;
      g.rect(p.x - T * 0.22, p.y + T * 0.3 - h, T * 0.44, h).fill({ color: 0x8a7a60, alpha: 0.7 * a });
      g.rect(p.x - T * 0.22, p.y + T * 0.3 - h, T * 0.44, 2).fill({ color: 0xd8c8a0, alpha: a });
      return true;
    }
    case "dust":
      for (let k = 0; k < 5; k++) {
        const s = SPOKES[k] as number;
        g.circle(p.x + Math.cos(s) * T * 0.3 * t, p.y - T * 0.1 * t + Math.sin(s) * 2, 2.5 + 3 * t).fill({ color: 0xc8b890, alpha: 0.5 * a });
      }
      return true;
    case "arc": {
      if (c.link === undefined) return true;
      const q = along(c.link, t, T * 0.8);
      g.rect(q.x - 3, q.y - 3, 6, 6).fill({ color: 0x8a6a40, alpha: 1 });
      g.rect(q.x - 3, q.y - 3, 6, 6).stroke({ width: 1, color: 0x2a1a10, alpha: 1 });
      return true;
    }
    case "trap":
      for (let k = -2; k <= 2; k++) {
        const x = p.x + k * 3;
        g.poly([x - 1.5, p.y, x, p.y - 4 * grow, x + 1.5, p.y]).fill({ color: 0xb8b0a0, alpha: a });
      }
      g.ellipse(p.x, p.y, 8, 3).stroke({ width: 1, color: 0x6a6050, alpha: a });
      return true;
    case "runeFall": {
      const y = p.y - T * 0.6 * (1 - grow);
      g.circle(p.x, y, 5).stroke({ width: 1.4, color: c1, alpha: a });
      g.moveTo(p.x - 3, y).lineTo(p.x + 3, y).moveTo(p.x, y - 3).lineTo(p.x, y + 3).stroke({ width: 1, color: c2, alpha: a });
      return true;
    }
    case "burst":
      for (const s of SPOKES) {
        const d = T * 0.4 * t;
        g.moveTo(p.x + Math.cos(s) * d * 0.4, p.y + Math.sin(s) * d * 0.4).lineTo(p.x + Math.cos(s) * d, p.y + Math.sin(s) * d).stroke({ width: 2, color: c1, alpha: a });
      }
      g.circle(p.x, p.y, 4 * (1 - t) + 1).fill({ color: 0xffffff, alpha: a });
      return true;
    default:
      return false;
  }
}

/** 形態、防護、給予、退還、層數、規則類。 */
function drawRules(c: LowerCue): void {
  const { g, p, t, a, c1 } = c;
  const grow = Math.min(1, t * 1.6);
  switch (c.kind) {
    case "formIn":
      g.ellipse(p.x, p.y - T * 0.35, T * 0.5 * (1 - t) + 2, T * 0.6 * (1 - t) + 2).stroke({ width: 2, color: c1, alpha: a });
      return;
    case "formOut":
      g.ellipse(p.x, p.y - T * 0.35, T * 0.15 + T * 0.45 * t, T * 0.2 + T * 0.5 * t).stroke({ width: 2, color: c1, alpha: (1 - t) * a });
      return;
    case "guard": {
      if (c.link === undefined) return;
      const e = along(c.link, grow, 0);
      const f = c.link.from;
      g.moveTo(f.x, f.y - 2).lineTo(e.x, e.y - 2).moveTo(f.x, f.y + 2).lineTo(e.x, e.y + 2).stroke({ width: 1.4, color: 0x9ad0ff, alpha: 0.85 * a });
      return;
    }
    case "goldFlash":
      g.circle(p.x, p.y - T * 0.35, T * 0.2 + T * 0.3 * t).fill({ color: 0xffd23a, alpha: 0.45 * (1 - t) });
      g.circle(p.x, p.y - T * 0.35, 3).fill({ color: 0xffffff, alpha: 1 - t });
      return;
    case "scan":
      g.ellipse(p.x, p.y, T * (0.3 + 1.6 * t), T * (0.12 + 0.64 * t)).stroke({ width: 2, color: 0xfff0b0, alpha: (1 - t) * a });
      return;
    case "orbFly":
    case "iconFly": {
      if (c.link === undefined) return;
      const q = along(c.link, grow, T * 0.25);
      if (c.kind === "orbFly") {
        g.circle(q.x, q.y, 5).fill({ color: c1, alpha: 0.4 * a });
        g.circle(q.x, q.y, 2.4).fill({ color: 0xffffff, alpha: a });
      } else {
        g.circle(q.x, q.y, 5).fill({ color: 0x1a1420, alpha: 0.5 * a });
        drawIcon(g, q.x, q.y, c.icon, 0xffe9a8, a);
      }
      return;
    }
    case "rewind": {
      const ang = -t * TAU;
      g.arc(p.x, p.y, 6, ang, ang + TAU * 0.8).stroke({ width: 1.6, color: 0xffe9a8, alpha: a });
      g.circle(p.x + Math.cos(ang) * 6, p.y + Math.sin(ang) * 6, 1.8).fill({ color: 0xffffff, alpha: a });
      drawIcon(g, p.x, p.y, c.icon, 0xffe9a8, a);
      return;
    }
    case "stack":
      drawIcon(g, p.x, p.y - T * 0.25 * t, c.icon, c.icon === "-1" ? 0xff8a7a : 0xa8f0a0, a);
      return;
    case "coin": {
      const y = p.y - T * 0.5 * Math.sin(t * Math.PI);
      const w = 3.5 * Math.abs(Math.cos(t * TAU * 2)) + 0.6;
      g.ellipse(p.x, y, w, 3.5).fill({ color: 0xffd23a, alpha: a });
      return;
    }
    case "snap":
      for (const s of [0, 1.57, 3.14, 4.71]) g.moveTo(p.x, p.y).lineTo(p.x + Math.cos(s) * 6 * grow, p.y + Math.sin(s) * 6 * grow).stroke({ width: 1.6, color: c1, alpha: a });
      g.circle(p.x, p.y, 1.8).fill({ color: 0xffffff, alpha: a });
      return;
    case "wound":
      g.circle(p.x, p.y, 3 + 2 * Math.sin(t * Math.PI)).fill({ color: 0xd8302a, alpha: 0.6 * a });
      return;
    default:
      return;
  }
}

/** 下半原語的特效一格（`skillFx.cueEffect` 不認得的種類都交給這裡）。 */
export function drawLowerCue(c: LowerCue): void {
  if (!drawWorld(c)) drawRules(c);
}
