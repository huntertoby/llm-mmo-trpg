// 「晶冠城邦」的物件點綴（Phase 5A-ART6；docs/art/四區移植需求.md 第 3 節；畫法移植自 docs/art/sample/regions4.js）。
// 只換石柱 → 晶柱（擋視線，畫到格頂）；其他物件不在表內（退回預設）。推倒後的倒塌物是另一個物件，照預設。
// 晶柱的外光比頭目外光淡、不閃動（貼圖是靜態的，不做動畫）。
// 這個檔案不匯入 objectArt 的值（避免循環匯入）；表由 objectArt 組裝。
import { roundRect, type Ctx } from "./artDraw";
import { rgba } from "./color";
import { CRYSTAL } from "./crystalTerrain";
import type { ObjectArtSpec } from "./objectArt";

const T = 52;
const OUT = CRYSTAL.outline;

type ObjectDrawer = (ctx: Ctx, s: ObjectArtSpec) => void;

/** 晶柱外光的透明度（模糊 10；比頭目外光淡）。 */
export const CRYSTAL_PILLAR_GLOW_ALPHA = 0.5;

/** 晶柱：藍紫水晶柱，淡淡的外光（模糊 10）、金色底座（擋視線）。 */
function crystalPillar(ctx: Ctx): void {
  const c = T / 2;
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.moveTo(c - 6, 46);
  ctx.lineTo(c + 6, 46);
  ctx.lineTo(c + 22, 52);
  ctx.lineTo(c + 8, 52);
  ctx.fill();
  roundRect(ctx, c - 11, 40, 22, 8, 2); // 石礎
  ctx.fillStyle = CRYSTAL.slab;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.save();
  ctx.shadowColor = rgba(CRYSTAL.glint, CRYSTAL_PILLAR_GLOW_ALPHA);
  ctx.shadowBlur = 10;
  ctx.beginPath();
  ctx.moveTo(c - 8, 41);
  ctx.lineTo(c - 9, 14);
  ctx.lineTo(c, 2);
  ctx.lineTo(c + 9, 14);
  ctx.lineTo(c + 8, 41);
  ctx.closePath();
  ctx.fillStyle = "#a898ff";
  ctx.fill();
  ctx.restore();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.35)"; // 亮面
  ctx.beginPath();
  ctx.moveTo(c - 5, 38);
  ctx.lineTo(c - 6, 15);
  ctx.lineTo(c, 6);
  ctx.lineTo(c - 1, 38);
  ctx.fill();
  ctx.fillStyle = "rgba(0,0,0,0.18)"; // 暗面
  ctx.beginPath();
  ctx.moveTo(c + 2, 38);
  ctx.lineTo(c + 1, 6);
  ctx.lineTo(c + 8, 15);
  ctx.lineTo(c + 7, 38);
  ctx.fill();
  roundRect(ctx, c - 11, 38, 22, 4, 1); // 金色底座
  ctx.fillStyle = CRYSTAL.gold;
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = OUT;
  ctx.stroke();
}

/** 晶冠的物件畫法（物件 ID → 畫法）；需求第 3 節只有晶柱。 */
export const CRYSTAL_OBJECTS: Readonly<Record<string, ObjectDrawer>> = {
  stone_pillar: crystalPillar,
};
