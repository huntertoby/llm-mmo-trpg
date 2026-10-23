// 矮牆的畫法（Phase 3-18b；美術 PM docs/art/矮牆.md）。預設是暖色石塊；區域主題（雲嶺的白牆黛瓦…）換色盤共用同一套外框規則。
import type { Ctx } from "./artDraw";
import type { ObjectArtSpec } from "./objectArt";

const T = 52;

/** 矮牆色盤：壓頂石頂面與亮邊、正面、灰縫、外框。 */
export interface LowWallPalette {
  top: string;
  topEdge: string;
  face: string;
  mortar: string;
  outline: string;
}

/** 矮牆（美術 PM docs/art/矮牆.md）：暖色石塊——頂面亮、正面錯縫磚、2px 深色外框（相連的一側不畫）、較深的投影。 */
export const LOW_WALL: LowWallPalette = { top: "#d8c7a2", topEdge: "#f2e6c8", face: "#86704f", mortar: "#4c3d2a", outline: "#241c13" };

export function drawLowWall(ctx: Ctx, s: ObjectArtSpec, pal: LowWallPalette = LOW_WALL): void {
  const x0 = s.joinL ? 0 : 4;
  const x1 = s.joinR ? T : T - 4;
  const capY = T * 0.3;
  const capH = T * 0.16;
  const faceH = T * 0.26;
  const faceY = capY + capH;
  const w = x1 - x0;
  // 投影（落向右下）
  ctx.fillStyle = "rgba(0,0,0,0.42)";
  ctx.fillRect(x0 + 4, faceY + faceH, w, 7);
  // 正面：兩排錯縫磚
  ctx.fillStyle = pal.face;
  ctx.fillRect(x0, faceY, w, faceH);
  ctx.strokeStyle = pal.mortar;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const rowH = faceH / 2;
  ctx.moveTo(x0, faceY + rowH);
  ctx.lineTo(x1, faceY + rowH);
  for (let r = 0; r < 2; r++) {
    for (let bx = r ? 8 : 17; bx < x1 - 1; bx += 17) {
      if (bx <= x0 + 1) continue;
      ctx.moveTo(bx, faceY + r * rowH);
      ctx.lineTo(bx, faceY + (r + 1) * rowH);
    }
  }
  ctx.stroke();
  // 壓頂石（頂面）：最上面 2px 亮邊，每 26px 一條縫
  ctx.fillStyle = pal.top;
  ctx.fillRect(x0, capY, w, capH);
  ctx.fillStyle = pal.topEdge;
  ctx.fillRect(x0, capY, w, 2);
  ctx.strokeStyle = "rgba(76,61,42,0.6)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let bx = 13; bx < x1 - 1; bx += 26) {
    if (bx <= x0 + 1) continue;
    ctx.moveTo(bx, capY);
    ctx.lineTo(bx, capY + capH);
  }
  ctx.stroke();
  // 外框：只框外輪廓，相連的那一側不畫；壓頂石與正面之間一條 1px 線
  ctx.strokeStyle = pal.outline;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x0, capY);
  ctx.lineTo(x1, capY);
  ctx.moveTo(x0, faceY + faceH);
  ctx.lineTo(x1, faceY + faceH);
  if (!s.joinL) {
    ctx.moveTo(x0, capY);
    ctx.lineTo(x0, faceY + faceH);
  }
  if (!s.joinR) {
    ctx.moveTo(x1, capY);
    ctx.lineTo(x1, faceY + faceH);
  }
  ctx.stroke();
  ctx.strokeStyle = "rgba(36,28,19,0.7)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x0, faceY);
  ctx.lineTo(x1, faceY);
  ctx.stroke();
}

