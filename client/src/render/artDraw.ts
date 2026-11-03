// 程式繪製的共用小工具（Canvas 2D）。

export type Ctx = CanvasRenderingContext2D;
export const TAU = Math.PI * 2;

export function roundRect(ctx: Ctx, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

export function flame(ctx: Ctx, x: number, y: number, h: number): void {
  const w = h * 0.55;
  ctx.fillStyle = "#ff8a1e";
  ctx.beginPath();
  ctx.moveTo(x, y - h);
  ctx.bezierCurveTo(x + w, y - h * 0.4, x + w, y, x, y);
  ctx.bezierCurveTo(x - w, y, x - w, y - h * 0.4, x, y - h);
  ctx.fill();
  ctx.fillStyle = "#ffe07a";
  ctx.beginPath();
  ctx.moveTo(x, y - h * 0.55);
  ctx.bezierCurveTo(x + w * 0.5, y - h * 0.2, x + w * 0.45, y, x, y);
  ctx.bezierCurveTo(x - w * 0.45, y, x - w * 0.5, y - h * 0.2, x, y - h * 0.55);
  ctx.fill();
}

export function shadowEllipse(ctx: Ctx, cx: number, cy: number, rx: number, ry: number): void {
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fill();
}

/** 危險記號（會爆的油桶，四區共用；docs/art/四區移植需求.md 第 1 節）：黃底黑框三角＋驚嘆號，中心在 (cx, cy)。 */
export function hazardMark(ctx: Ctx, cx: number, cy: number, s = 7): void {
  ctx.beginPath();
  ctx.moveTo(cx, cy - s);
  ctx.lineTo(cx + s, cy + s * 0.8);
  ctx.lineTo(cx - s, cy + s * 0.8);
  ctx.closePath();
  ctx.fillStyle = "#ffd23a";
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = "#1a1208";
  ctx.stroke();
  ctx.fillStyle = "#1a1208";
  ctx.fillRect(cx - 1, cy - s * 0.45, 2, s * 0.65);
  ctx.fillRect(cx - 1, cy + s * 0.32, 2, 2);
}

/** 發光線（裝飾光：裂縫熔岩光、晶能線）：`path` 只負責 moveTo／lineTo，畫完還原陰影設定。 */
export function glowLine(ctx: Ctx, color: string, width: number, blur: number, path: () => void): void {
  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = blur;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.beginPath();
  path();
  ctx.stroke();
  ctx.restore();
}

/** 實心小圓點。 */
export function dot(ctx: Ctx, x: number, y: number, r: number, fill: string): void {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}
