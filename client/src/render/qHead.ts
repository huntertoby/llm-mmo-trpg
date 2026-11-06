// Q 版頭、臉、頭髮四方向、頭飾四面（QK-1 第 3 項；照 docs/art/sample/qDoll.js 的 head／PD_hair／Q_headgear）。
// 頭正圓 r 8.5、中心 (0,−29)。側臉：前半臉一隻眼、鼻尖、腮紅，後半是頭髮；長髮只在耳後；背面整顆是頭髮。
import type { Ctx } from "./artDraw";
import { colors, fill, mix, rr, S, TAU, type QItem, type QLook, type QView } from "./qCore";
import { raceFace } from "./qRace";

export function headShape(ctx: Ctx, look: QLook): void {
  switch (look.face) {
    case "oval":
      ctx.ellipse(0, -29, 7.7, 9, 0, 0, TAU);
      break;
    case "square":
      ctx.roundRect(-8.3, -37.3, 16.6, 16.4, 4.6);
      break;
    case "heart":
      ctx.moveTo(0, -20.3);
      ctx.quadraticCurveTo(-8.7, -23.5, -8.6, -30);
      ctx.arc(0, -30, 8.6, Math.PI, 0);
      ctx.quadraticCurveTo(8.7, -23.5, 0, -20.3);
      ctx.closePath();
      break;
    default:
      ctx.arc(0, -29, 8.5, 0, TAU);
  }
}

function eyes(ctx: Ctx, look: QLook, side: number, ex: number): void {
  const col = look.eyes ?? "#1d1a22";
  const st = look.eyeStyle ?? "square";
  const xs: number[] = [];
  if (side === 0 || side === 1) xs.push(ex + 2.9);
  if (side === 0 || side === -1) xs.push(ex - 2.9);
  for (const x of xs) {
    if (st === "dot") fill(ctx, col, () => ctx.ellipse(x, -28.6, 1.15, 1.45, 0, 0, TAU));
    else if (st === "smile") {
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.05;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.arc(x, -27.7, 1.5, Math.PI * 1.15, Math.PI * 1.85);
      ctx.stroke();
    } else if (st === "big") {
      fill(ctx, col, () => ctx.roundRect(x - 1.3, -30.8, 2.6, 4, 1.2));
      fill(ctx, "#ffffff", () => ctx.arc(x - 0.45, -29.7, 0.6, 0, TAU));
    } else {
      ctx.fillStyle = col;
      ctx.fillRect(x - 0.9, -30, 1.8, 3);
    }
    if (look.lashes) {
      const o = x > ex ? 1 : -1;
      const up = st === "big" ? 0.6 : 0;
      ctx.strokeStyle = col;
      ctx.lineWidth = 0.65;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(x + o * 0.8, -30.3 - up);
      ctx.lineTo(x + o * 2, -31.3 - up);
      ctx.stroke();
    }
  }
}

function beard(ctx: Ctx, look: QLook, side: number): void {
  const st = look.beardStyle;
  if (!st || st === "full") return;
  const c = look.hairColor ?? "#5a3a22";
  const ex = side * 2.6;
  if (st === "short") {
    ctx.save();
    ctx.globalAlpha = 0.45;
    fill(ctx, c, () => {
      ctx.moveTo(ex - 6.9, -26);
      ctx.quadraticCurveTo(ex - 6, -20.6, ex, -20.4);
      ctx.quadraticCurveTo(ex + 6, -20.6, ex + 6.9, -26);
      ctx.quadraticCurveTo(ex, -23.4, ex - 6.9, -26);
    });
    ctx.restore();
  }
  if (st === "goatee") {
    fill(ctx, c, () => {
      ctx.moveTo(ex - 1.8, -23.6);
      ctx.lineTo(ex + 1.8, -23.6);
      ctx.lineTo(ex, -19.2);
      ctx.closePath();
    });
    fill(ctx, c, () => ctx.rect(ex - 1.8, -25.2, 3.6, 0.9));
  }
  if (st === "mustache")
    for (const s2 of side ? [1] : [-1, 1])
      fill(ctx, c, () => {
        ctx.moveTo(ex, -25.6);
        ctx.quadraticCurveTo(ex + s2 * 2.8, -26.6, ex + s2 * 3.9, -24.1);
        ctx.quadraticCurveTo(ex + s2 * 2, -24.9, ex, -24.7);
        ctx.closePath();
      });
}

/** 頭後面的頭髮（側面長髮後片、馬尾、雙馬尾）：正面、側面畫在臉之前。 */
function hairBehind(ctx: Ctx, look: QLook, view: QView, headgear: QItem | undefined): void {
  if (!look.hair || look.hair === "none" || look.skull || view === "back" || headgear?.kind === "hood") return;
  const c = look.hairColor ?? "#5a3a22";
  const band = look.bunBand ?? "#d23c3c";
  const SD = view === "side";
  if (SD && look.hair === "long") fill(ctx, c, () => rr(ctx, -10, -32, 7.2, 14.5, 2.6));
  if (look.hair === "twin")
    for (const s2 of SD ? [-1] : [-1, 1]) {
      const x = SD ? -6.5 : s2 * 9.6;
      fill(ctx, c, () => {
        ctx.moveTo(x - 1.6, -32);
        ctx.quadraticCurveTo(x + s2 * 3.4, -26, x + s2 * 1.6, -17.5);
        ctx.quadraticCurveTo(x - s2 * 0.6, -21, x - s2 * 2, -27);
        ctx.closePath();
      });
      fill(ctx, band, () => ctx.arc(x, -30.6, 1.3, 0, TAU));
    }
  if (look.hair === "ponytail") {
    if (SD) {
      fill(ctx, c, () => {
        ctx.moveTo(-6, -34);
        ctx.quadraticCurveTo(-13.5, -32, -12, -20.5);
        ctx.quadraticCurveTo(-10, -26, -7, -28.5);
        ctx.closePath();
      });
      fill(ctx, band, () => ctx.arc(-7.4, -32.4, 1.3, 0, TAU));
    } else
      fill(ctx, c, () => {
        ctx.moveTo(6.5, -35);
        ctx.quadraticCurveTo(12.5, -31, 10.5, -21);
        ctx.quadraticCurveTo(9.5, -27, 6, -30);
        ctx.closePath();
      });
  }
}

/** 頭：正面照舊版；側面是側臉；背面整顆是頭髮。side：側面 1、正面背面 0。 */
export function drawQHead(ctx: Ctx, look: QLook, view: QView, side: number, head: QItem | undefined): void {
  const skin = look.skin;
  const SD = view === "side";
  hairBehind(ctx, look, view, head);
  fill(ctx, skin, () => headShape(ctx, look));
  if (view === "back") {
    hair(ctx, look, "back", head);
    return;
  }
  if (SD) {
    // 側臉：鼻尖（剪影外框會描出鼻子）、耳朵在後腦
    fill(ctx, skin, () => ctx.ellipse(8.45, -27.1, 1.25, 1.05, 0, 0, TAU));
    fill(ctx, skin, () => ctx.ellipse(-1.2, -28.2, 1.7, 2.3, 0, 0, TAU));
    fill(ctx, mix(skin, "#000000", 0.18), () => ctx.ellipse(-1.0, -28.1, 0.7, 1.2, 0, 0, TAU));
  }
  const ex = side * 3.2;
  eyes(ctx, look, side, ex);
  ctx.fillStyle = "rgba(220,90,90,0.35)";
  if (SD) ctx.fillRect(3.4, -26.3, 2.2, 1.2);
  else {
    ctx.fillRect(ex - 5, -26.5, 2, 1.2);
    ctx.fillRect(ex + 3, -26.5, 2, 1.2);
  }
  const L: QLook = look.beardStyle ? { ...look, beard: look.beardStyle === "full" } : look;
  raceFace(ctx, L, SD ? "side" : view, side, SD && S.WEST);
  beard(ctx, look, side);
  hair(ctx, look, SD ? "side" : "front", head);
}

const COVERING = ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"];

function hair(ctx: Ctx, look: QLook, view: QView, headgear: QItem | undefined): void {
  if (!look.hair || look.hair === "none" || look.skull) return;
  const c = look.hairColor ?? "#5a3a22";
  const band = look.bunBand ?? "#d23c3c";
  const covered = !!headgear && COVERING.includes(headgear.kind);
  if (view === "back") {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.arc(0, -29, 8.8, 0, TAU);
    });
    if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
    if (look.hair === "bob") fill(ctx, c, () => rr(ctx, -8.8, -30, 17.6, 8.5, 3.5));
    if (look.hair === "ponytail" && headgear?.kind !== "hood") {
      fill(ctx, c, () => rr(ctx, -2, -32, 4, 17.5, 2));
      fill(ctx, band, () => rr(ctx, -2.3, -32, 4.6, 1.6, 0.8));
    }
    if (look.hair === "twin" && headgear?.kind !== "hood")
      for (const s2 of [-1, 1]) {
        fill(ctx, c, () => {
          ctx.moveTo(s2 * 8, -32);
          ctx.quadraticCurveTo(s2 * 13, -26, s2 * 11, -17.5);
          ctx.quadraticCurveTo(s2 * 9.5, -22, s2 * 6.5, -28);
          ctx.closePath();
        });
        fill(ctx, band, () => ctx.arc(s2 * 8.6, -30.8, 1.3, 0, TAU));
      }
    if (look.hair === "spiky" && !covered)
      fill(ctx, c, () => {
        for (let i = 0; i < 7; i++) {
          const a = Math.PI * (1.05 + i * 0.15);
          ctx.moveTo(Math.cos(a - 0.08) * 8.4, -29 + Math.sin(a - 0.08) * 8.4);
          ctx.lineTo(Math.cos(a) * 11.6, -29 + Math.sin(a) * 11.6);
          ctx.lineTo(Math.cos(a + 0.08) * 8.4, -29 + Math.sin(a + 0.08) * 8.4);
        }
      });
    if (look.hair === "bun" && !covered) fill(ctx, look.bunBand ?? c, () => ctx.arc(0, -37, 3, 0, TAU));
    return;
  }
  if (view === "side") {
    // 側面（朝東）：頭髮蓋住頭頂和後半顆頭，前緣在額頭；耳朵前面不畫頭髮（短髮露耳）
    if (!covered)
      fill(ctx, c, () => {
        ctx.moveTo(8.3, -32.6);
        ctx.quadraticCurveTo(6.2, -38.8, -0.8, -38.6);
        ctx.quadraticCurveTo(-9.4, -37.6, -9.3, -29.2);
        ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6);
        ctx.lineTo(-3.4, -22.6);
        ctx.quadraticCurveTo(-3.6, -27.5, -2.6, -31.2);
        ctx.quadraticCurveTo(2.5, -33.6, 6.2, -32.4);
        ctx.lineTo(7.4, -31.2);
        ctx.closePath();
      });
    if (covered)
      fill(ctx, c, () => {
        ctx.moveTo(-9.3, -29);
        ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6);
        ctx.lineTo(-3.4, -22.6);
        ctx.quadraticCurveTo(-4, -26, -4, -29);
        ctx.closePath();
      });
    if (look.hair === "long")
      fill(ctx, c, () => {
        ctx.moveTo(-3.4, -31);
        ctx.quadraticCurveTo(-1.5, -24, -3.2, -19.5);
        ctx.lineTo(-9.6, -19.5);
        ctx.lineTo(-9.4, -30);
        ctx.closePath();
      });
    if (look.hair === "bob")
      fill(ctx, c, () => {
        ctx.moveTo(-2.4, -31.5);
        ctx.quadraticCurveTo(-0.6, -25.5, -1.8, -22);
        ctx.lineTo(-9.4, -22.4);
        ctx.lineTo(-9.4, -30);
        ctx.closePath();
      });
    if (look.hair === "spiky" && !covered)
      fill(ctx, c, () => {
        for (let i = 0; i < 6; i++) {
          const a = Math.PI * (1.0 + i * 0.13);
          ctx.moveTo(Math.cos(a - 0.09) * 8.6 - 0.8, -29.8 + Math.sin(a - 0.09) * 8.6);
          ctx.lineTo(Math.cos(a) * 12 - 1.6, -29.8 + Math.sin(a) * 12);
          ctx.lineTo(Math.cos(a + 0.09) * 8.6 - 0.8, -29.8 + Math.sin(a + 0.09) * 8.6);
        }
      });
    if (look.hair === "bun" && !covered) fill(ctx, look.bunBand ?? c, () => ctx.arc(-5.6, -36, 3, 0, TAU));
    if (look.hair === "twin" && headgear?.kind !== "hood") {
      fill(ctx, c, () => {
        ctx.moveTo(-7.6, -33);
        ctx.quadraticCurveTo(-14, -29, -12.4, -19);
        ctx.quadraticCurveTo(-10.6, -24, -8.2, -28.6);
        ctx.closePath();
      });
      fill(ctx, look.bunBand ?? "#d23c3c", () => ctx.arc(-8.4, -31.4, 1.4, 0, TAU));
    }
    return;
  }
  if (!covered)
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98);
      ctx.quadraticCurveTo(4, -33, 0, -32.5);
      ctx.quadraticCurveTo(-5, -32, -8.8, -29);
      ctx.closePath();
    });
  if (look.hair === "long") {
    fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5));
    fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5));
  }
  if (look.hair === "bob") {
    fill(ctx, c, () => rr(ctx, -9.6, -31.5, 3.4, 8.8, 1.7));
    fill(ctx, c, () => rr(ctx, 6.2, -31.5, 3.4, 8.8, 1.7));
  }
  if (look.hair === "spiky" && !covered)
    fill(ctx, c, () => {
      for (let i = 0; i < 7; i++) {
        const a = Math.PI * (1.05 + i * 0.15);
        ctx.moveTo(Math.cos(a - 0.09) * 8.6, -29.5 + Math.sin(a - 0.09) * 8.6);
        ctx.lineTo(Math.cos(a) * 11.8, -29.5 + Math.sin(a) * 11.8);
        ctx.lineTo(Math.cos(a + 0.09) * 8.6, -29.5 + Math.sin(a + 0.09) * 8.6);
      }
    });
  if (look.hair === "bun")
    fill(ctx, look.bunBand ?? c, () => {
      ctx.beginPath();
      ctx.arc(0, -37, 3, 0, TAU);
    });
}

/** 頭飾 × 四方向：正面照舊版；側面（朝東）各自轉成側面；背面看不到臉前的東西。12 種：兜帽、頭盔、角盔、巫師帽、便帽、頭巾、頭冠、寬帽、面紗、護目鏡、王冠、全罩盔。 */
export function drawQHeadgear(ctx: Ctx, it: QItem | undefined, view: QView): void {
  if (!it) return;
  const [c, d] = colors(it);
  const SD = view === "side";
  const B = view === "back";
  switch (it.kind) {
    case "hood":
      if (SD) {
        ctx.fillStyle = c;
        ctx.beginPath();
        ctx.arc(-0.6, -29.6, 10.2, 0, TAU);
        ctx.ellipse(4.4, -28.2, 4.6, 6.4, 0.12, 0, TAU);
        ctx.fill("evenodd");
        fill(ctx, c, () => {
          ctx.moveTo(-10.6, -29);
          ctx.quadraticCurveTo(-11, -22, -6, -20.6);
          ctx.lineTo(1, -21);
          ctx.lineTo(-3, -25);
          ctx.closePath();
        });
        ctx.strokeStyle = d;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.ellipse(4.4, -28.2, 4.6, 6.4, 0.12, -1.9, 1.9);
        ctx.stroke();
        break;
      }
      ctx.fillStyle = c;
      ctx.beginPath();
      ctx.arc(0, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15);
      ctx.lineTo(9, -22);
      ctx.lineTo(-9, -22);
      ctx.closePath();
      if (!B) ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU);
      ctx.fill("evenodd");
      fill(ctx, d, () => ctx.rect(-9, -23, 18, 1.5));
      if (B) {
        ctx.strokeStyle = d;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(0, -38);
        ctx.lineTo(0, -24);
        ctx.stroke();
      }
      break;
    case "helmet":
    case "horned_helm":
      if (SD) {
        fill(ctx, c, () => {
          ctx.moveTo(8.8, -31.6);
          ctx.quadraticCurveTo(8, -40.2, -0.6, -40);
          ctx.quadraticCurveTo(-9.8, -39.4, -9.8, -29);
          ctx.lineTo(-9.4, -24.5);
          ctx.lineTo(-5, -25.5);
          ctx.lineTo(-4.5, -31.4);
          ctx.lineTo(8.8, -31.6);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.rect(-4.5, -32.6, 13.6, 1.2));
        fill(ctx, d, () => ctx.rect(8.2, -32.6, 1.6, 1.8));
        if (it.kind === "horned_helm")
          fill(ctx, "#e8d8b8", () => {
            ctx.moveTo(-2, -38);
            ctx.quadraticCurveTo(-6, -46, -11, -46);
            ctx.quadraticCurveTo(-6, -42, -4.5, -36.5);
            ctx.closePath();
          });
        break;
      }
      if (B) {
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.arc(0, -30, 9.4, Math.PI, 0);
          ctx.lineTo(9.4, -27);
          ctx.lineTo(-9.4, -27);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.rect(-9.4, -27.5, 18.8, 1.2));
        fill(ctx, c, () => rr(ctx, -8.6, -27, 17.2, 3, 1));
      } else {
        fill(ctx, c, () => {
          ctx.beginPath();
          ctx.arc(0, -31, 9.4, Math.PI, 0);
          ctx.lineTo(9.4, -25.5);
          ctx.lineTo(7.2, -25.5);
          ctx.lineTo(7.2, -31);
          ctx.lineTo(-7.2, -31);
          ctx.lineTo(-7.2, -25.5);
          ctx.lineTo(-9.4, -25.5);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.rect(-9.4, -32.2, 18.8, 1.2));
      }
      if (it.kind === "horned_helm")
        for (const s of [-1, 1])
          fill(ctx, "#e8d8b8", () => {
            ctx.beginPath();
            ctx.moveTo(s * 8, -31);
            ctx.lineTo(s * 13, -40);
            ctx.lineTo(s * 10, -30);
            ctx.closePath();
          });
      break;
    case "wizard_hat":
      if (SD) {
        fill(ctx, c, () => ctx.ellipse(-0.5, -34.2, 12.5, 2.6, -0.04, 0, TAU));
        fill(ctx, c, () => {
          ctx.moveTo(-6.5, -35.5);
          ctx.lineTo(5.5, -35.5);
          ctx.quadraticCurveTo(1, -44, -6, -51);
          ctx.quadraticCurveTo(-4, -44, -6.5, -35.5);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.rect(-6.3, -37.2, 11.6, 1.4));
        break;
      }
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-12, -34);
        ctx.lineTo(12, -34);
        ctx.lineTo(3, -37);
        ctx.lineTo(2, -52);
        ctx.lineTo(-4, -37);
        ctx.closePath();
      });
      fill(ctx, d, () => ctx.rect(-6, -36.5, 12, 1.4));
      break;
    case "cap":
      if (SD) {
        fill(ctx, c, () => {
          ctx.moveTo(-9, -31);
          ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6);
          ctx.quadraticCurveTo(7.6, -39.4, 8.6, -32);
          ctx.closePath();
        });
        fill(ctx, d, () => rr(ctx, 4, -32.6, 9.2, 1.8, 0.9));
        break;
      }
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.arc(0, -31, 9, Math.PI, 0);
        ctx.closePath();
      });
      if (!B) fill(ctx, d, () => rr(ctx, -9.5, -32, 19, 1.6, 0.8));
      break;
    case "bandana":
      if (SD) {
        fill(ctx, c, () => {
          ctx.moveTo(-9, -30);
          ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6);
          ctx.quadraticCurveTo(7.6, -39.4, 8.4, -32.6);
          ctx.lineTo(-9, -30);
          ctx.closePath();
        });
        fill(ctx, c, () => {
          ctx.moveTo(-8.4, -31);
          ctx.lineTo(-13, -28);
          ctx.lineTo(-12, -25.5);
          ctx.lineTo(-8.2, -29);
          ctx.closePath();
        });
        fill(ctx, d, () => ctx.arc(-8.6, -30.6, 1.3, 0, TAU));
        break;
      }
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.arc(0, -31, 9, Math.PI, 0);
        ctx.closePath();
      });
      if (B) {
        fill(ctx, d, () => ctx.arc(0, -31.5, 1.6, 0, TAU));
        for (const s of [-1, 1])
          fill(ctx, c, () => {
            ctx.moveTo(0, -31.5);
            ctx.lineTo(s * 3, -25);
            ctx.lineTo(s * 1, -24.6);
            ctx.closePath();
          });
      }
      break;
    case "circlet":
      if (SD) {
        fill(ctx, c, () => ctx.rect(-8.6, -34.6, 17, 1.6));
        fill(ctx, "#a898ff", () => {
          ctx.moveTo(8.6, -36.6);
          ctx.lineTo(9.8, -34);
          ctx.lineTo(8.6, -31.8);
          ctx.lineTo(7.6, -34);
          ctx.closePath();
        });
        break;
      }
      fill(ctx, c, () => rr(ctx, -9, -34, 18, 1.6, 0.8));
      if (!B)
        fill(ctx, "#a898ff", () => {
          ctx.beginPath();
          ctx.moveTo(0, -36.5);
          ctx.lineTo(1.8, -34);
          ctx.lineTo(0, -31.5);
          ctx.lineTo(-1.8, -34);
          ctx.closePath();
        });
      break;
    case "wide_hat":
      if (SD) {
        fill(ctx, c, () => ctx.ellipse(0, -34, 14.5, 2.4, 0, 0, TAU));
        fill(ctx, d, () => {
          ctx.arc(-0.5, -35, 8, Math.PI, 0);
          ctx.closePath();
        });
        break;
      }
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.ellipse(0, -34, 14, 4, 0, 0, TAU);
      });
      fill(ctx, d, () => {
        ctx.beginPath();
        ctx.arc(0, -35, 8, Math.PI, 0);
        ctx.closePath();
      });
      break;
    case "veil":
      if (SD) {
        fill(ctx, c, () => {
          ctx.moveTo(2.8, -26.6);
          ctx.lineTo(9.4, -26.2);
          ctx.lineTo(8.6, -21);
          ctx.lineTo(3.6, -20.8);
          ctx.closePath();
        });
        ctx.strokeStyle = d;
        ctx.lineWidth = 0.6;
        ctx.beginPath();
        ctx.moveTo(2.8, -26.4);
        ctx.lineTo(-2, -28.4);
        ctx.stroke();
        break;
      }
      if (B) {
        ctx.strokeStyle = d;
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.moveTo(-7.5, -26.5);
        ctx.lineTo(7.5, -26.5);
        ctx.stroke();
        break;
      }
      fill(ctx, c, () => rr(ctx, -9, -26, 18, 5, 2));
      break;
    case "goggles":
      if (SD) {
        ctx.strokeStyle = "#3a3a44";
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(6, -30);
        ctx.lineTo(-8.8, -30.6);
        ctx.stroke();
        fill(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU));
        fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU));
        break;
      }
      if (B) {
        ctx.strokeStyle = "#3a3a44";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(-8.8, -30);
        ctx.lineTo(8.8, -30);
        ctx.stroke();
        break;
      }
      for (const x of [-3, 3]) {
        fill(ctx, "#8d969f", () => {
          ctx.beginPath();
          ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU);
        });
        fill(ctx, "rgba(160,220,255,0.7)", () => {
          ctx.beginPath();
          ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU);
        });
      }
      break;
    case "crown":
      fill(ctx, c, () => rr(ctx, SD ? -6.6 : -7.4, -36, SD ? 13.2 : 14.8, 3, 0.8));
      for (const x of SD ? [-4.5, 0.5, 5.5] : [-6, 0, 6])
        fill(ctx, c, () => {
          ctx.moveTo(x - 1.6, -35.6);
          ctx.lineTo(x, -39.6);
          ctx.lineTo(x + 1.6, -35.6);
          ctx.closePath();
        });
      if (!B) fill(ctx, "#d23c3c", () => ctx.arc(SD ? 5 : 0, -34.5, 1, 0, TAU));
      break;
    case "greathelm":
      fill(ctx, c, () => rr(ctx, -9.6, -39.6, 19.2, 18.6, 4.5));
      if (SD) {
        fill(ctx, d, () => ctx.rect(4.6, -30.6, 5, 1.4));
        fill(ctx, d, () => ctx.rect(-9.6, -27, 19.2, 1));
      } else if (!B) {
        fill(ctx, d, () => ctx.rect(-6.5, -30.6, 13, 1.4));
        fill(ctx, d, () => ctx.rect(-0.6, -30, 1.2, 6));
      }
      break;
    default:
      break;
  }
}
