// NPC 頭像（Phase 6C-7；移植自 docs/art/sample/portraits.js，需求 docs/art/NPC頭像.md 第 1、4 節）：
// 用遊戲的 C 畫風紙娃娃正面頭部放大，加上只畫在頭像上的小配件（斗笠、布帽、頭巾、護目鏡、刀疤……）與圓角框。
// 框色依區域（雲嶺綠、荒原橘、傭兵金），底色同色系漸層。白狐霜音另外畫一張狐臉。
// 沒有頭像資料時畫通用剪影。確定性：沒有亂數，同一位每次畫都一樣；離屏畫好依（鍵、大小）快取成圖片網址。
import type { NpcPortrait } from "../api/types";
import { resolveDoll } from "./appearance";
import { type Ctx, TAU } from "./artDraw";
import { ellPts, ink, INK, stroke } from "./inkStyle";
import { drawFigure } from "./paperdoll";
import { isFox, portraitDollLook, portraitRaceLook } from "../world/npcLook";

/** 區域 → [框色, 底色深, 底色淺]。 */
export const PORTRAIT_REGION: Readonly<Record<string, readonly [string, string, string]>> = {
  cloud_ridge: ["#6aa84a", "#2f4a3a", "#8ab890"],
  ashen_waste: ["#ff6a1a", "#3a2418", "#b07050"],
  merc: ["#c8a868", "#2a2a3a", "#8a8aa8"],
};
const REGION_FALLBACK = PORTRAIT_REGION["merc"]!;

/** 頭像的三種大小（事件卡、字幕與對話泡泡、HUD 與清單）。 */
export const PORTRAIT_SIZES = { card: 96, line: 48, chip: 28 } as const;

/** 說書人的頭像（兜帽長袍；事件卡的對話框用）。 */
export const NARRATOR_PORTRAIT: NpcPortrait = {
  look: { skin: "#e8c8a8", hair: "none", beard: true, hair_color: "#d8d0c0" },
  gear: { body: { kind: "robe", color: "#4a3a5a", trim: "#e8bb48" }, head: { kind: "hood", color: "#3a2e48" } },
  extras: [],
} as NpcPortrait;

function pdot(ctx: Ctx, x: number, y: number, r: number, c: string): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}

/** 頭像專用配件（正面、紙娃娃座標：頭中心約在 (0, −42)，半徑約 9）。不認得的略過。 */
function drawExtra(ctx: Ctx, key: string): void {
  switch (key) {
    case "wide_hat":
      ink(ctx, "p-hat", [[-17, -47], [0, -58], [17, -47], [12, -45.6], [-12, -45.6]], "#c8a868", { w: 0.8 });
      stroke(ctx, "p-hat-band", [[-8, -48], [8, -48]], 1, "#6a4a2a");
      break;
    case "cap":
      ink(ctx, "p-cap", [[-9.6, -45], [-8, -52], [0, -54.4], [8, -52], [9.6, -45]], "#3a2a1a", { w: 0.7 });
      break;
    case "headband":
      stroke(ctx, "p-band", [[-9.4, -47], [9.4, -47]], 1.8, "#b8432f");
      stroke(ctx, "p-band-tail", [[9, -47], [13, -44], [12, -40]], 1.2, "#b8432f");
      break;
    case "bandana":
      ink(ctx, "p-bandana", [[-9.8, -45], [-7, -52.6], [0, -54], [7, -52.6], [9.8, -45], [0, -47.4]], "#a83a2a", { w: 0.7 });
      stroke(ctx, "p-knot", [[9, -46], [13, -42]], 1.4, "#a83a2a");
      break;
    case "goggles":
      for (const x of [-3.4, 3.4]) {
        ink(ctx, `p-gog${x}`, ellPts(x, -42, 3, 2.6, 12), "#8d969f", { shade: false, w: 0.6 });
        ctx.fillStyle = "rgba(160,220,255,0.7)";
        ctx.beginPath();
        ctx.ellipse(x, -42, 1.9, 1.6, 0, 0, TAU);
        ctx.fill();
      }
      stroke(ctx, "p-gog-strap", [[-9, -42], [-6.4, -42]], 1, "#3a2a1a");
      stroke(ctx, "p-gog-strap2", [[6.4, -42], [9, -42]], 1, "#3a2a1a");
      break;
    case "goggles_up":
      for (const x of [-3.4, 3.4]) ink(ctx, `p-gogu${x}`, ellPts(x, -50, 3, 2.4, 12), "#8d969f", { shade: false, w: 0.6 });
      stroke(ctx, "p-gogu-strap", [[-9, -49], [9, -49]], 1, "#3a2a1a");
      break;
    case "scar":
      stroke(ctx, "p-scar", [[-6, -46], [-2, -40], [1, -36]], 1, "#7a2a20");
      stroke(ctx, "p-scar-x", [[-5, -43], [-2.4, -44], [-3, -41], [0, -41.6]], 0.6, "#7a2a20");
      break;
    case "mustache":
      stroke(ctx, "p-must", [[-3, -38.4], [0, -39], [3, -38.4]], 1.1, "#2a1a10");
      break;
    case "wrinkles":
      for (const x of [-6.6, 6.6]) stroke(ctx, `p-wr${x}`, [[x - 0.8, -40], [x + 0.6, -38.8]], 0.5, "rgba(120,80,60,0.7)");
      stroke(ctx, "p-wr-f", [[-2.6, -47.6], [2.6, -47.6]], 0.5, "rgba(120,80,60,0.6)");
      break;
    case "fur_collar":
      ink(ctx, "p-fur", [[-10, -34], [-4, -31.6], [0, -32.6], [4, -31.6], [10, -34], [8, -30], [-8, -30]], "#d8c8a8", { w: 0.6 });
      break;
    case "earring":
      pdot(ctx, -9.2, -38.4, 1, "#e8bb48");
      break;
    case "soot":
      ctx.fillStyle = "rgba(40,30,25,0.35)";
      ctx.beginPath();
      ctx.ellipse(4.6, -38.6, 2.4, 1.2, 0.2, 0, TAU);
      ctx.fill();
      break;
    case "rune":
      ctx.save();
      ctx.shadowColor = "#ff3a2a";
      ctx.shadowBlur = 4;
      stroke(ctx, "p-rune", [[0, -48], [-1.2, -46], [1.2, -46], [0, -48]], 0.8, "#c83a2a");
      ctx.restore();
      break;
    case "ember_eye":
      ctx.save();
      ctx.shadowColor = "#ff6a1a";
      ctx.shadowBlur = 6;
      pdot(ctx, 3.2, -41, 1.3, "#ffb030");
      ctx.restore();
      break;
    case "mist": {
      ctx.save();
      const g = ctx.createRadialGradient(0, -36, 2, 0, -36, 22);
      g.addColorStop(0, "rgba(232,232,224,0.6)");
      g.addColorStop(1, "rgba(232,232,224,0)");
      ctx.fillStyle = g;
      ctx.fillRect(-24, -60, 48, 40);
      ctx.restore();
      break;
    }
    case "apron_cross":
      stroke(ctx, "p-cross-v", [[0, -31], [0, -26]], 1.6, "#c83a2a");
      stroke(ctx, "p-cross-h", [[-2.5, -28.5], [2.5, -28.5]], 1.6, "#c83a2a");
      break;
    default:
      break;
  }
}

/** 白狐霜音：不是紙娃娃，另外畫一張狐臉（白毛、冰藍眼、額頭冰紋）。 */
function drawFox(ctx: Ctx): void {
  ink(ctx, "fox-head", [[-10, -40], [-12, -54], [-5, -47], [0, -48], [5, -47], [12, -54], [10, -40], [6, -33], [0, -30], [-6, -33]], "#f4f0e8", { w: 1 });
  for (const s of [-1, 1]) ink(ctx, `fox-ear${s}`, [[s * 9, -49], [s * 11, -53], [s * 7, -48]], "#e8a0a0", { shade: false, w: 0.4 });
  for (const x of [-4, 4]) {
    ctx.fillStyle = "#3aa8e0";
    ctx.beginPath();
    ctx.ellipse(x, -41, 1.4, 1.8, 0, 0, TAU);
    ctx.fill();
  }
  pdot(ctx, 0, -34.6, 1.3, INK);
  stroke(ctx, "fox-mark", [[-1.4, -46], [0, -44.4], [1.4, -46]], 0.8, "#7ad8ff");
  ctx.save();
  const g = ctx.createRadialGradient(0, -40, 4, 0, -40, 22);
  g.addColorStop(0, "rgba(200,240,255,0.0)");
  g.addColorStop(1, "rgba(200,240,255,0.35)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, -40, 22, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/** 通用剪影（沒有頭像資料時）：深色頭肩。 */
function drawSilhouette(ctx: Ctx): void {
  ctx.fillStyle = "rgba(20,16,12,0.72)";
  ctx.beginPath();
  ctx.ellipse(0, -42, 8.6, 9.6, 0, 0, TAU);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(-15, -20);
  ctx.quadraticCurveTo(-13, -32, 0, -32.5);
  ctx.quadraticCurveTo(13, -32, 15, -20);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgba(242,230,200,0.75)";
  ctx.font = "bold 9px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("?", 0, -39);
}

/** 頭像畫在 (x, y) 起、邊長 `size` 的框裡。`portrait` 為 `null` 時畫通用剪影。 */
export function drawPortrait(ctx: Ctx, x: number, y: number, size: number, portrait: NpcPortrait | null | undefined, region: string | null | undefined): void {
  const [frame, bgD, bgL] = (region != null ? PORTRAIT_REGION[region] : undefined) ?? REGION_FALLBACK;
  ctx.save();
  ctx.translate(x, y);
  ctx.beginPath();
  ctx.roundRect(0, 0, size, size, size * 0.14);
  ctx.save();
  ctx.clip();
  const g = ctx.createLinearGradient(0, 0, 0, size);
  g.addColorStop(0, bgL);
  g.addColorStop(1, bgD);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const k = size / 34;
  const cy = size * 0.47;
  ctx.translate(size / 2, cy + 42 * k);
  ctx.scale(k, k);
  if (portrait == null) drawSilhouette(ctx);
  else if (isFox(portrait)) drawFox(ctx);
  else {
    const spec = resolveDoll({ template: "portrait", dollLook: portraitDollLook(portrait, false), team: "ally", summon: false, weaponId: "unarmed", weaponClass: "melee", raceLook: portraitRaceLook(portrait) });
    delete spec.gear.main_hand;
    delete spec.gear.off_hand;
    drawFigure(ctx, spec, "south", false);
    for (const e of portrait.extras ?? []) drawExtra(ctx, e);
  }
  ctx.restore();
  ctx.lineWidth = Math.max(2, size * 0.04);
  ctx.strokeStyle = frame;
  ctx.beginPath();
  ctx.roundRect(0, 0, size, size, size * 0.14);
  ctx.stroke();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#1c1712";
  ctx.stroke();
  ctx.restore();
}

const cache = new Map<string, string>();

/** 頭像的快取鍵（外觀內容＋區域＋大小）；同樣的外觀共用一張。 */
export function portraitKey(portrait: NpcPortrait | null | undefined, region: string | null | undefined, size: number): string {
  return `${size}|${region ?? ""}|${portrait == null ? "-" : JSON.stringify(portrait)}`;
}

/** 頭像的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。 */
export function portraitUrl(portrait: NpcPortrait | null | undefined, region: string | null | undefined, size: number, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${portraitKey(portrait, region, size)}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = size * dpr;
  c.height = size * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawPortrait(ctx, 0, 0, size, portrait, region);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}
