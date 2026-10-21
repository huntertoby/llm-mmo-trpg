// 紙娃娃小人（Phase 3-16b；移植自美術 PM 樣張 docs/art/sample/paperdoll.js）。
// 依裝備欄位分層繪製：披風（正面時在身後）→ 腳 → 身（含手臂）→ 手 → 披風（背面時在最上）→ 頭 → 頭髮 → 頭部裝備 → 主手 → 副手。
// 座標：腳底中心為原點、往上為負，身高約 46。畫好後在離屏 canvas 描深色外框（史詩、傳說加外光），由 ArtTextures 快取成貼圖。
import type { Facing } from "../api/types";
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import { elementTint, MATERIAL, RARITY_GLOW, type DollSpec, type GearItem, type Look } from "./appearance";

/** 離屏畫布的虛擬大小與腳底位置（虛擬像素）。 */
export const DOLL_W = 64;
export const DOLL_H = 64;
export const DOLL_FOOT_Y = DOLL_H - 6;

function mix(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const m = (s: number): number => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
}

function darker(c: string, f = 0.68): string {
  return mix(c, "#000000", 1 - f);
}

/** 一件裝備的 [主色, 暗色]：指定顏色或材質色（不認得 → 布料色），有元素時混入元素色 45%。 */
export function itemColors(item: GearItem): [string, string] {
  const base = MATERIAL[item.material ?? "cloth"] ?? MATERIAL.cloth!;
  let [main, dark]: [string, string] = item.color !== undefined ? [item.color, darker(item.color)] : [base[0], base[1]];
  const tint = elementTint(item.element);
  if (tint !== undefined) {
    main = mix(main, tint, 0.45);
    dark = mix(dark, tint, 0.3);
  }
  return [main, dark];
}

function fill(ctx: Ctx, color: string, path: () => void): void {
  ctx.fillStyle = color;
  ctx.beginPath();
  path();
  ctx.fill();
}

type View = "front" | "back";

function drawCloak(ctx: Ctx, it: GearItem, view: View): void {
  const [c, d] = itemColors(it);
  ctx.fillStyle = view === "back" ? c : d;
  ctx.beginPath();
  ctx.moveTo(-8, -21);
  ctx.lineTo(8, -21);
  ctx.lineTo(12, -2);
  ctx.quadraticCurveTo(0, 1, -12, -2);
  ctx.closePath();
  ctx.fill();
  if (view === "back") {
    ctx.strokeStyle = d;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-3, -18);
    ctx.lineTo(-5, -3);
    ctx.moveTo(3, -18);
    ctx.lineTo(5, -3);
    ctx.stroke();
  }
}

function drawLegs(ctx: Ctx, look: Look, feet: GearItem | undefined): void {
  const pants = look.pants ?? "#4a4038";
  fill(ctx, pants, () => rr(ctx, -5, -9, 4, 8, 1));
  fill(ctx, pants, () => rr(ctx, 1, -9, 4, 8, 1));
  const [b, bd] = feet !== undefined ? itemColors(feet) : ["#5a4030", "#3a281c"];
  const tall = feet?.kind === "greaves" ? 4 : feet?.kind === "boots" ? 2.5 : 0;
  for (const sx of [-1, 1]) {
    if (tall > 0) fill(ctx, b, () => rr(ctx, sx * 3 - 2.2, -2 - tall, 4.4, tall + 1, 1));
    fill(ctx, bd, () => {
      ctx.beginPath();
      ctx.ellipse(sx * 3.2, -1.2, 3.2, 2, 0, 0, TAU);
    });
  }
}

function drawRibs(ctx: Ctx): void {
  fill(ctx, "#d9d2bd", () => rr(ctx, -1.5, -21, 3, 13, 1));
  ctx.strokeStyle = "#d9d2bd";
  ctx.lineWidth = 2;
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(-6, -19 + i * 3);
    ctx.quadraticCurveTo(0, -17 + i * 3, 6, -19 + i * 3);
    ctx.stroke();
  }
  fill(ctx, "#d9d2bd", () => rr(ctx, -5, -9, 10, 2.5, 1));
}

function drawTorso(ctx: Ctx, kind: string, c: string, d: string, look: Look): void {
  if (kind === "robe") {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.moveTo(-7, -21);
      ctx.lineTo(7, -21);
      ctx.lineTo(10, -1.5);
      ctx.lineTo(-10, -1.5);
      ctx.closePath();
    });
    fill(ctx, look.trim ?? d, () => ctx.rect(-1.2, -20, 2.4, 18.5));
    fill(ctx, look.trim ?? d, () => ctx.rect(-10, -3, 20, 1.6));
    return;
  }
  fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
  if (kind === "plate") {
    fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, -5, -19.5, 4, 6, 1.5));
    fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2));
  } else if (kind === "mail") {
    ctx.fillStyle = d;
    for (let y = -19; y < -9; y += 2.4) for (let x = -6 + (Math.trunc(y) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1);
  } else if (kind === "leather") {
    ctx.strokeStyle = d;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-5, -20);
    ctx.lineTo(5, -11);
    ctx.stroke();
  }
  fill(ctx, "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2)); // 腰帶
  fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
}

function drawArms(ctx: Ctx, kind: string, c: string): void {
  fill(ctx, c, () => rr(ctx, -10.5, -20, 4, 10, 2));
  fill(ctx, c, () => rr(ctx, 6.5, -20, 4, 10, 2));
  if (kind === "plate") {
    for (const x of [-8.5, 8.5]) fill(ctx, mix(c, "#ffffff", 0.25), () => ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU));
  }
}

function drawBody(ctx: Ctx, it: GearItem | undefined, look: Look): void {
  const kind = it?.kind ?? "shirt";
  if (kind === "ribs") {
    drawRibs(ctx);
    drawArms(ctx, kind, "#d9d2bd");
    return;
  }
  const [c, d] = it !== undefined ? itemColors(it) : ["#d8cdb4", "#a89c80"];
  drawTorso(ctx, kind, c, d, look);
  drawArms(ctx, kind, c);
}

function drawHands(ctx: Ctx, look: Look, hands: GearItem | undefined): void {
  const c = hands !== undefined ? itemColors(hands)[0] : look.skin;
  for (const x of [-8.5, 8.5]) fill(ctx, c, () => ctx.arc(x, -9.5, 2.4, 0, TAU));
}

function drawHead(ctx: Ctx, look: Look, view: View, side: number): void {
  fill(ctx, look.skin, () => ctx.arc(0, -29, 8.5, 0, TAU));
  if (view === "back") return;
  const ex = side * 2.6; // 側面時眼睛往朝向那邊偏
  ctx.fillStyle = look.eyes ?? "#1d1a22";
  if (look.skull === true) {
    ctx.beginPath();
    ctx.arc(ex - 3, -29, 2.2, 0, TAU);
    ctx.arc(ex + 3, -29, 2.2, 0, TAU);
    ctx.fill();
    ctx.fillRect(ex - 2.5, -24.5, 5, 1.2);
    return;
  }
  if (side === 0 || side === 1) ctx.fillRect(ex + 2, -30, 1.8, 3);
  if (side === 0 || side === -1) ctx.fillRect(ex - 3.8, -30, 1.8, 3);
  ctx.fillStyle = "rgba(220,90,90,0.35)";
  ctx.fillRect(ex - 5, -26.5, 2, 1.2);
  ctx.fillRect(ex + 3, -26.5, 2, 1.2);
}

const HAIR_COVERED = ["helmet", "hood", "wizard_hat", "horned_helm"];

function drawHair(ctx: Ctx, look: Look, view: View, head: GearItem | undefined): void {
  if (look.hair === undefined || look.hair === "none" || look.skull === true) return;
  const c = look.hairColor ?? "#5a3a22";
  if (view === "back") {
    fill(ctx, c, () => ctx.arc(0, -29, 8.8, 0, TAU));
    if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
    return;
  }
  if (head === undefined || !HAIR_COVERED.includes(head.kind)) {
    fill(ctx, c, () => {
      ctx.beginPath();
      ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98);
      ctx.quadraticCurveTo(4, -33, 0, -32.5);
      ctx.quadraticCurveTo(-5, -32, -8.8, -29);
      ctx.closePath();
    });
  }
  if (look.hair === "long") {
    fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5));
    fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5));
  }
}

function drawHood(ctx: Ctx, c: string, d: string, view: View): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.arc(0, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15);
  ctx.lineTo(9, -22);
  ctx.lineTo(-9, -22);
  ctx.closePath();
  if (view !== "back") ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU); // 正面挖出臉的洞（evenodd）
  ctx.fill("evenodd");
  fill(ctx, d, () => ctx.rect(-9, -23, 18, 1.5));
}

function drawHelmet(ctx: Ctx, it: GearItem, c: string, d: string, view: View): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(0, -30, 9.4, Math.PI, 0);
    ctx.lineTo(9.4, -27);
    ctx.lineTo(-9.4, -27);
    ctx.closePath();
  });
  fill(ctx, d, () => ctx.rect(-9.4, -28, 18.8, 1.6));
  if (view !== "back") fill(ctx, d, () => ctx.rect(-1, -28, 2, 5));
  fill(ctx, mix(c, "#ffffff", 0.4), () => rr(ctx, -5, -37, 4, 3, 1.5));
  if (it.kind !== "horned_helm") return;
  for (const s of [-1, 1]) {
    fill(ctx, "#efe6cc", () => {
      ctx.beginPath();
      ctx.moveTo(s * 8, -33);
      ctx.quadraticCurveTo(s * 15, -35, s * 14, -42);
      ctx.quadraticCurveTo(s * 11, -37, s * 6, -36);
      ctx.closePath();
    });
  }
}

function drawBandana(ctx: Ctx, c: string, d: string, view: View): void {
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.arc(0, -30, 9, Math.PI * 1.05, Math.PI * 1.95);
    ctx.closePath();
  });
  fill(ctx, c, () => ctx.rect(-9, -31.5, 18, 3));
  const tx = view === "back" ? 0 : 8;
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(tx, -30);
    ctx.lineTo(tx + 5, -27);
    ctx.lineTo(tx + 2, -25);
    ctx.closePath();
  });
}

function drawHeadgear(ctx: Ctx, it: GearItem | undefined, view: View): void {
  if (it === undefined) return;
  const [c, d] = itemColors(it);
  switch (it.kind) {
    case "hood":
      drawHood(ctx, c, d, view);
      break;
    case "helmet":
    case "horned_helm":
      drawHelmet(ctx, it, c, d, view);
      break;
    case "wizard_hat":
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-8, -34);
        ctx.lineTo(3, -50);
        ctx.lineTo(8, -34);
        ctx.closePath();
      });
      fill(ctx, d, () => ctx.ellipse(0, -34, 12, 3, 0, 0, TAU));
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.rect(-7, -36.5, 14, 1.8));
      break;
    case "bandana":
      drawBandana(ctx, c, d, view);
      break;
    case "crown":
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-6, -35);
        ctx.lineTo(-6, -41);
        ctx.lineTo(-3, -38);
        ctx.lineTo(0, -42);
        ctx.lineTo(3, -38);
        ctx.lineTo(6, -41);
        ctx.lineTo(6, -35);
        ctx.closePath();
      });
      fill(ctx, "#d23c3c", () => ctx.arc(0, -37, 1.3, 0, TAU));
      break;
    default:
      break;
  }
}

function drawBlade(ctx: Ctx, it: GearItem, c: string, front: boolean): void {
  const great = it.kind === "greatsword";
  const L = great ? 24 : 16;
  const W = great ? 4 : 2.6;
  ctx.rotate(front ? -0.25 : 0.25);
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-W / 2, -3);
    ctx.lineTo(-W / 2, -L);
    ctx.lineTo(0, -L - 3);
    ctx.lineTo(W / 2, -L);
    ctx.lineTo(W / 2, -3);
    ctx.closePath();
  });
  fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
  fill(ctx, it.hilt ?? "#8a6a2a", () => rr(ctx, -4.5, -4, 9, 2, 1));
  fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, 4));
}

function drawStaff(ctx: Ctx, it: GearItem, c: string): void {
  fill(ctx, "#6a4420", () => ctx.rect(-1.1, -30, 2.2, 34));
  const orb = elementTint(it.element) ?? c; // 法杖寶珠直接用元素色
  ctx.fillStyle = orb;
  ctx.globalAlpha = 0.35;
  ctx.beginPath();
  ctx.arc(0, -32, 6.5, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
  fill(ctx, orb, () => ctx.arc(0, -32, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -33.2, 1.1, 0, TAU));
}

function drawBow(ctx: Ctx, c: string, front: boolean): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.arc(front ? -4 : 4, -8, 13, front ? -1.2 : Math.PI - 1.2, front ? 1.2 : Math.PI + 1.2);
  ctx.stroke();
  ctx.strokeStyle = "rgba(240,240,240,0.8)";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  const sx = (front ? -4 : 4) + (front ? 1 : -1) * Math.cos(1.2) * 13;
  ctx.moveTo(sx, -8 - Math.sin(1.2) * 13);
  ctx.lineTo(sx, -8 + Math.sin(1.2) * 13);
  ctx.stroke();
}

function drawShield(ctx: Ctx, it: GearItem, c: string, d: string): void {
  if (it.kind === "shield_round") {
    fill(ctx, d, () => ctx.arc(0, -4, 7.5, 0, TAU));
    fill(ctx, c, () => ctx.arc(0, -4, 6, 0, TAU));
    fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -4, 2, 0, TAU));
    return;
  }
  fill(ctx, d, () => {
    ctx.beginPath();
    ctx.moveTo(-7, -13);
    ctx.lineTo(7, -13);
    ctx.lineTo(6.5, -2);
    ctx.lineTo(0, 6);
    ctx.lineTo(-6.5, -2);
    ctx.closePath();
  });
  fill(ctx, c, () => {
    ctx.beginPath();
    ctx.moveTo(-5.5, -11.5);
    ctx.lineTo(5.5, -11.5);
    ctx.lineTo(5, -2.5);
    ctx.lineTo(0, 3.8);
    ctx.lineTo(-5, -2.5);
    ctx.closePath();
  });
  fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-0.9, -11, 1.8, 13));
  fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-5, -7, 10, 1.8));
}

function drawWeapon(ctx: Ctx, it: GearItem | undefined, x: number, front: boolean): void {
  if (it === undefined) return;
  const [c, d] = itemColors(it);
  ctx.save();
  ctx.translate(x, -9.5);
  switch (it.kind) {
    case "sword":
    case "greatsword":
      drawBlade(ctx, it, c, front);
      break;
    case "dagger":
      ctx.rotate(front ? -0.6 : 0.6);
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(-1.3, -2);
        ctx.lineTo(0, -10);
        ctx.lineTo(1.3, -2);
        ctx.closePath();
      });
      fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
      break;
    case "axe":
      ctx.rotate(front ? -0.3 : 0.3);
      fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 20));
      fill(ctx, c, () => {
        ctx.beginPath();
        ctx.moveTo(1, -17);
        ctx.quadraticCurveTo(9, -18, 8, -10);
        ctx.lineTo(1, -12);
        ctx.closePath();
      });
      break;
    case "staff":
      drawStaff(ctx, it, c);
      break;
    case "bow":
      drawBow(ctx, c, front);
      break;
    case "shield_round":
    case "shield_kite":
      drawShield(ctx, it, c, d);
      break;
    case "tome":
      fill(ctx, c, () => rr(ctx, -4.5, -6, 9, 8, 1));
      fill(ctx, "#f2ead6", () => ctx.rect(-3.5, -5.5, 7, 1.2));
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -2, 1.6, 0, TAU));
      break;
    default:
      break;
  }
  ctx.restore();
}

/** 圖騰柱（召喚的圖騰）：木柱＋刻出的臉＋頂端寶珠。 */
function drawTotem(ctx: Ctx): void {
  fill(ctx, "rgba(0,0,0,0.25)", () => ctx.ellipse(0, -1, 9, 3, 0, 0, TAU));
  fill(ctx, "#6e4620", () => rr(ctx, -6, -40, 12, 40, 2));
  fill(ctx, "#8f5f2c", () => rr(ctx, -6, -40, 4, 40, 2));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -28, 16, 5, 1));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -14, 16, 5, 1));
  ctx.fillStyle = "#1d1a22";
  ctx.fillRect(-4, -36, 2.4, 3);
  ctx.fillRect(1.6, -36, 2.4, 3);
  ctx.fillRect(-2.5, -31, 5, 1.4);
  fill(ctx, "rgba(143,240,226,0.4)", () => ctx.arc(0, -44, 6.5, 0, TAU));
  fill(ctx, "#8ff0e2", () => ctx.arc(0, -44, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -45.2, 1.1, 0, TAU));
}

/** 手的位置：正面時慣用手在畫面左、背面相反、側面時武器在前方。 */
export function handSides(facing: Facing): { main: number; off: number; side: number; view: View } {
  const view: View = facing === "north" ? "back" : "front";
  const side = facing === "east" ? 1 : facing === "west" ? -1 : 0;
  if (side !== 0) return { main: side * 8.5, off: -side * 8.5, side, view };
  return view === "back" ? { main: 8.5, off: -8.5, side, view } : { main: -8.5, off: 8.5, side, view };
}

/** 畫一個小人（腳底中心在 (0, 0)）。facing：south ＝ 正面、north ＝ 背面、east／west ＝ 側面（寬度 × 0.9）。 */
export function drawFigure(ctx: Ctx, spec: DollSpec, facing: Facing): void {
  if (spec.totem === true) {
    drawTotem(ctx);
    return;
  }
  const { look, gear } = spec;
  const { main, off, side, view } = handSides(facing);
  const offInFront = gear.off_hand?.kind.startsWith("shield") === true;
  ctx.save();
  if (side !== 0) ctx.scale(0.9, 1);
  if (gear.cloak !== undefined && view !== "back") drawCloak(ctx, gear.cloak, view);
  if (view === "back") {
    drawWeapon(ctx, gear.main_hand, main, false); // 背面時武器畫在身體後面
    drawWeapon(ctx, gear.off_hand, off, false);
  }
  drawLegs(ctx, look, gear.feet);
  drawBody(ctx, gear.body, look);
  drawHands(ctx, look, gear.hands);
  if (gear.cloak !== undefined && view === "back") drawCloak(ctx, gear.cloak, view);
  drawHead(ctx, look, view, side);
  drawHair(ctx, look, view, gear.head);
  drawHeadgear(ctx, gear.head, view);
  if (view !== "back") {
    drawWeapon(ctx, gear.main_hand, main, true);
    drawWeapon(ctx, gear.off_hand, off + (offInFront ? side * 2 : 0), true);
  }
  ctx.restore();
}

/** 倒地姿勢：整個小人橫躺（頭朝右），腳底仍在原點附近。 */
export function drawFigurePose(ctx: Ctx, spec: DollSpec, facing: Facing, downed: boolean): void {
  if (!downed || spec.totem === true) {
    drawFigure(ctx, spec, facing);
    return;
  }
  ctx.save();
  ctx.translate(-20, -11);
  ctx.rotate(Math.PI / 2);
  drawFigure(ctx, spec, facing);
  ctx.restore();
}

/**
 * 產生一張帶深色外框的離屏 canvas（`dpr` 倍解析度；沒有 DOM 時回傳 `null`）。
 * 外框：把剪影往 8 個方向各偏 1.3 px 塗深色；史詩、傳說另外加外光。腳底在 (DOLL_W/2, DOLL_FOOT_Y)。
 */
export function renderFigureCanvas(spec: DollSpec, facing: Facing, downed: boolean, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const make = (): HTMLCanvasElement => {
    const c = document.createElement("canvas");
    c.width = DOLL_W * dpr;
    c.height = DOLL_H * dpr;
    return c;
  };
  const off = make();
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(DOLL_W / 2, DOLL_FOOT_Y);
  drawFigurePose(o, spec, facing, downed);
  const tinted = (color: string): HTMLCanvasElement | null => {
    const c = make();
    const cx = c.getContext("2d");
    if (cx === null) return null;
    cx.drawImage(off, 0, 0);
    cx.globalCompositeOperation = "source-in";
    cx.fillStyle = color;
    cx.fillRect(0, 0, c.width, c.height);
    return c;
  };
  const out = make();
  const ctx = out.getContext("2d");
  const sil = tinted("#16121a");
  if (ctx === null || sil === null) return null;
  const glowColor = spec.rarity !== undefined ? RARITY_GLOW[spec.rarity] : undefined;
  const glow = glowColor !== undefined ? tinted(glowColor) : null;
  if (glow !== null) {
    ctx.save();
    ctx.globalAlpha = 0.5;
    for (let a = 0; a < 12; a++) {
      const ang = (a / 12) * TAU;
      ctx.drawImage(glow, Math.cos(ang) * 2.6 * dpr, Math.sin(ang) * 2.6 * dpr);
    }
    ctx.restore();
  }
  const k = 1.3 * dpr;
  for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]] as const) ctx.drawImage(sil, ox * k, oy * k);
  ctx.drawImage(off, 0, 0);
  return out;
}
