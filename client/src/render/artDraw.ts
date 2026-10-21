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
