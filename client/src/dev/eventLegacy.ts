// 開發頁專用（QI-6）：事件插圖小牌、頭頂泡泡在 QI-6 以前的畫法（`render/eventArtParts.ts` 的舊 `ICON` 表原樣，QI-6 從遊戲端拿掉），
// 只給 `event-gallery.html` 的「現行｜Q 版」並排用，不屬於正式 build。舊的事件卡圓環圖示（墨線）沒有搬過來：對照請看樣張 docs/art/closeup/qicons/event/。
import type { Ctx } from "../render/artDraw";
import { box, dot, OUT, type IconId } from "../render/eventArtParts";

const TAU = Math.PI * 2;
type IconDraw = (ctx: Ctx, x: number, y: number, s: number, ink?: string) => void;
/** 舊小牌（深底）上黑色圖示改用的淺色。 */
export const LEGACY_BADGE_INK = "#f2e6c8";

const bang: IconDraw = (ctx, x, y, s, ink = OUT) => {
  ctx.fillStyle = ink;
  ctx.fillRect(x - s * 0.12, y - s * 0.5, s * 0.24, s * 0.65);
  ctx.fillRect(x - s * 0.12, y + s * 0.3, s * 0.24, s * 0.22);
};

export const LEGACY_ICON: Readonly<Record<IconId, IconDraw>> = {
  coin(ctx, x, y, s) {
    dot(ctx, x, y + s * 0.1, s * 0.55, "#e8bb48");
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.beginPath();
    ctx.arc(x, y + s * 0.1, s * 0.55, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = OUT;
    ctx.fillRect(x - s * 0.15, y - s * 0.12, s * 0.3, s * 0.45);
  },
  sword(ctx, x, y, s) {
    ctx.strokeStyle = OUT;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(x - s * 0.5, y + s * 0.5);
    ctx.lineTo(x + s * 0.5, y - s * 0.5);
    ctx.stroke();
    ctx.strokeStyle = "#dfe4ea";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.strokeStyle = "#e8bb48";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(x - s * 0.45, y + s * 0.1);
    ctx.lineTo(x - s * 0.1, y + s * 0.45);
    ctx.stroke();
  },
  bang,
  ask(ctx, x, y, s, ink = OUT) {
    ctx.strokeStyle = ink;
    ctx.lineWidth = s * 0.22;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.arc(x, y - s * 0.18, s * 0.28, Math.PI * 1.05, Math.PI * 0.45);
    ctx.lineTo(x, y + s * 0.18);
    ctx.stroke();
    dot(ctx, x, y + s * 0.45, s * 0.12, ink);
  },
  rest(ctx, x, y, s) {
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
  portal(ctx, x, y, s) {
    ctx.save();
    ctx.shadowColor = "#8fe0ff";
    ctx.shadowBlur = 6;
    ctx.strokeStyle = "#5ac8f0";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, s * 0.45, 0, TAU);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, s * 0.2, 0, TAU);
    ctx.stroke();
    ctx.restore();
  },
  scroll(ctx, x, y, s) {
    box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.8, "#f2e6c8", OUT, 1.5, 1);
    ctx.fillStyle = "#8a2f20";
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
  notes(ctx, x, y, s) {
    box(ctx, x - s * 0.5, y - s * 0.4, s, s * 0.7, "#f2e6c8", OUT, 1.5, 3);
    ctx.fillStyle = "#f2e6c8";
    ctx.beginPath();
    ctx.moveTo(x - s * 0.2, y + s * 0.28);
    ctx.lineTo(x - s * 0.3, y + s * 0.5);
    ctx.lineTo(x, y + s * 0.28);
    ctx.fill();
    ctx.strokeStyle = "#8a7a5a";
    ctx.lineWidth = 1;
    for (const k of [-0.18, 0.02]) {
      ctx.beginPath();
      ctx.moveTo(x - s * 0.3, y + s * k);
      ctx.lineTo(x + s * 0.3, y + s * k);
      ctx.stroke();
    }
  },
  warn(ctx, x, y, s) {
    ctx.beginPath();
    ctx.moveTo(x, y - s * 0.5);
    ctx.lineTo(x + s * 0.5, y + s * 0.4);
    ctx.lineTo(x - s * 0.5, y + s * 0.4);
    ctx.closePath();
    ctx.fillStyle = "#ffd23a";
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.stroke();
    bang(ctx, x, y + s * 0.02, s * 0.6);
  },
};
