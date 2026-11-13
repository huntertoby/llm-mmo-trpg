// Q 版身體、腿、衣服、披風、盾、背掛、腰掛、頸飾、紋章（QK-1 第 2、7、9 項；照 docs/art/sample/qDoll.js，四方向見 docs/art/部件四方向清單.md）。
// 側面一律用「朝東」的座標畫（朝西由外層鏡像），近側、遠側照真人互換（S.WEST）。
import type { Ctx } from "./artDraw";
import { colors, fill, isTowerLike, mix, pz, Q_OUT, rotAt, rr, S, TAU, type QItem, type QLook, type QView } from "./qCore";
import { bodyPattern, drawLegForm, isNeckForm } from "./qGearForms";
import { shellBack, shellSide } from "./qMoltenShell";
import { sectShieldBack, sectShieldSide } from "./qSectShield";
import { pdHeld } from "./qWeapons";

// ---------- 腿：4×8 的方塊，拆成大腿（髖轉）＋小腿（膝轉）＋腳 ----------
const BOOT_TALL: Readonly<Record<string, number>> = { greaves: 4, iron_boots: 3, shoes: 0 };
export function leg(ctx: Ctx, look: QLook, feet: QItem | undefined, sx: number, hip: number, knee: number, lift: number, side: number, view: QView = side ? "side" : "front"): void {
  const pants = look.pants ?? "#4a4038";
  const [b, bd] = feet ? colors(feet) : ["#5a4030", "#3a281c"];
  const tall = feet?.kind === "boots" ? (feet.form === "tall" ? 4 : 2.5) : feet ? (BOOT_TALL[feet.kind] ?? 0) : 0;
  const x = side ? sx * 1.6 : sx * 3;
  ctx.save();
  ctx.translate(0, -lift);
  rotAt(ctx, x, -9, hip * 1.6);
  fill(ctx, pants, () => rr(ctx, x - 2, -9.5, 4, 5, 1.2)); // 大腿
  rotAt(ctx, x, -5, knee * 1.6);
  fill(ctx, pants, () => rr(ctx, x - 2, -5.5, 4, 4.5, 1.2)); // 小腿
  if (tall) fill(ctx, b, () => rr(ctx, x - 2.2, -2 - tall, 4.4, tall + 1, 1));
  fill(ctx, bd, () => ctx.ellipse(x + (side ? side * 0.8 : 0), -1.2, feet?.kind === "iron_boots" ? 3.6 : 3.2, 2, 0, 0, TAU));
  drawLegForm(ctx, feet, sx, x, view); // QK-3：綁腿、尖頭鐵靴、護膝（在小腿的座標系，走路時跟著腿動）
  ctx.restore();
}

// ---------- 身體：只該出現在正面的配件（腰帶扣、外套領口與扣子、長袍前襟）側面在前緣、背面不畫 ----------
export function body(ctx: Ctx, it: QItem | undefined, look: QLook, side: number, back = false): void {
  const kind = it?.kind ?? "shirt";
  const [c, d] = colors(it);
  ctx.save();
  if (side) ctx.scale(0.72, 1);
  if (kind === "robe") {
    const hem = it?.form === "short" ? -6 : -1.5;
    fill(ctx, c, () => {
      ctx.moveTo(-7, -21);
      ctx.lineTo(7, -21);
      ctx.lineTo(10, hem);
      ctx.lineTo(-10, hem);
      ctx.closePath();
    });
    // QK-8 小修 1（QK-5 做）：邊色＝外觀的 trim，沒有時用長袍自己的 trim（霧鎖真人金邊、小蓮竹青邊），都沒有＝暗色
    const tr = look.trim ?? it?.trim ?? d;
    if (!side && !back) fill(ctx, tr, () => ctx.rect(-1.2, -20, 2.4, 18.5));
    else if (side) fill(ctx, tr, () => ctx.rect(7.2, -20.5, 1.8, 19));
    fill(ctx, tr, () => ctx.rect(-10, hem - 1.5, 20, 1.6));
  } else if (kind === "coat") {
    fill(ctx, c, () => {
      ctx.moveTo(-7.5, -21);
      ctx.lineTo(7.5, -21);
      ctx.lineTo(8.5, -3);
      ctx.lineTo(1, -3);
      ctx.lineTo(0, -9);
      ctx.lineTo(-1, -3);
      ctx.lineTo(-8.5, -3);
      ctx.closePath();
    });
    if (!side && !back) {
      fill(ctx, d, () => {
        ctx.moveTo(-4, -21);
        ctx.lineTo(0, -15);
        ctx.lineTo(4, -21);
        ctx.closePath();
      });
      for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => ctx.arc(1.8, y, 0.7, 0, TAU));
    } else if (side) {
      fill(ctx, d, () => {
        ctx.moveTo(5.5, -21);
        ctx.lineTo(7.5, -16);
        ctx.lineTo(7.5, -21);
        ctx.closePath();
      });
      for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => ctx.arc(6.6, y, 0.7, 0, TAU));
    }
  } else if (kind === "bare") {
    bareBody(ctx, c, look, side, back);
  } else {
    fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
    // 胸口高光：側面在胸前那半邊，背面不畫
    if (kind === "plate") {
      if (!back) fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, side ? 1.5 : -5, -19.5, 4, 6, 1.5));
      fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2));
    } else if (kind === "mail" && bodyPattern(ctx, it, d)) {
      // QK-3：鱗甲等新形制的紋（qGearForms）
    } else if (kind === "mail") {
      ctx.fillStyle = d;
      for (let y = -19; y < -9; y += 2.4) for (let x = -6 + ((y | 0) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1);
    } else if (kind === "leather") {
      // 斜背帶：右肩到左腰；背面斜向和正面相反；側面照箭袋背帶的方向
      const k = back ? -1 : 1;
      ctx.strokeStyle = d;
      ctx.lineWidth = 1;
      ctx.beginPath();
      if (side) {
        ctx.moveTo((S.WEST ? 1.5 : -1.5) / 0.72, -20.8);
        ctx.lineTo((S.WEST ? -3.5 : 4.6) / 0.72, -11);
      } else {
        ctx.moveTo(-5 * k, -20);
        ctx.lineTo(5 * k, -11);
      }
      ctx.stroke();
    }
    fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
    if (!side && !back) fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
    else if (side && !S.NOBUCKLE) fill(ctx, "#d8b04a", () => ctx.rect(6.2, -9.5, 1.3, 2)); // 側面：帶扣轉到身體前緣
  }
  ctx.restore();
}

/**
 * 赤膊（QK-8，樣張 qDoll.js body.kind "bare"；護法武僧、爐叔）：膚色軀幹（c＝膚色，qNpc.npcPrep 換好）、腰上方收窄 0.5；
 * 腋下陰影、下巴下一道陰影、胸口兩條肌肉線、肚臍；側面只有胸前那半；背面一條脊線。腰帶色＝原本的 body.color（look.belt）。
 */
function bareBody(ctx: Ctx, c: string, look: QLook, side: number, back: boolean): void {
  const sh = mix(c, "#000000", 0.23);
  fill(ctx, c, () => {
    ctx.moveTo(-4.5, -21);
    ctx.lineTo(4.5, -21);
    ctx.quadraticCurveTo(7.5, -21, 7.5, -18);
    ctx.lineTo(7.5, -15);
    ctx.quadraticCurveTo(7, -12, 7, -9.5);
    ctx.lineTo(7, -7.5);
    ctx.lineTo(-7, -7.5);
    ctx.lineTo(-7, -9.5);
    ctx.quadraticCurveTo(-7, -12, -7.5, -15);
    ctx.lineTo(-7.5, -18);
    ctx.quadraticCurveTo(-7.5, -21, -4.5, -21);
    ctx.closePath();
  });
  if (!side) for (const s of [-1, 1]) fill(ctx, sh, () => ctx.ellipse(s * 6.4, -18.4, 1.1, 2, 0, 0, TAU)); // 腋下陰影
  ctx.strokeStyle = sh;
  ctx.lineCap = "round";
  if (!side && !back) {
    fill(ctx, sh, () => ctx.ellipse(0, -20.6, 4.2, 1.1, 0, 0, TAU));
    ctx.lineWidth = 0.7;
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(s * 0.5, -17.4);
      ctx.quadraticCurveTo(s * 3, -15.4, s * 5.6, -17.2);
      ctx.stroke();
    }
    fill(ctx, sh, () => ctx.ellipse(0, -11.4, 0.5, 0.7, 0, 0, TAU));
  } else if (side) {
    fill(ctx, sh, () => ctx.ellipse(4.2, -20.4, 3.2, 1, 0, 0, TAU));
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.moveTo(2.4, -17.6);
    ctx.quadraticCurveTo(5.6, -15, 7.4, -16.8);
    ctx.stroke();
  } else {
    ctx.lineWidth = 0.6;
    ctx.beginPath();
    ctx.moveTo(0, -19.8);
    ctx.lineTo(0, -12);
    ctx.stroke();
  }
  fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
  if (!side && !back) fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
}

// ---------- 披風：正面（暗色、在身體後）／側面（背後那片）／背面（主色、蓋住背） ----------
export function cloakFront(ctx: Ctx, it: QItem): void {
  const [, d] = colors(it);
  fill(ctx, d, () => {
    ctx.moveTo(-8, -21);
    ctx.lineTo(8, -21);
    ctx.lineTo(12, -2);
    ctx.quadraticCurveTo(0, 1, -12, -2);
    ctx.closePath();
  });
}
export function cloakSide(ctx: Ctx, it: QItem): void {
  const [c, d] = colors(it);
  fill(ctx, c, () => {
    ctx.moveTo(-1.5, -21.5);
    ctx.lineTo(1.5, -21.5);
    ctx.lineTo(-2.5, -6);
    ctx.quadraticCurveTo(-5.5, -1.8, -9.5, -3.2);
    ctx.lineTo(-8.2, -10);
    ctx.quadraticCurveTo(-6.5, -17, -4.5, -20.5);
    ctx.closePath();
  });
  fill(ctx, d, () => {
    ctx.moveTo(-3.2, -5.6);
    ctx.quadraticCurveTo(-5.8, -2.6, -9.5, -3.2);
    ctx.lineTo(-9, -5);
    ctx.quadraticCurveTo(-6, -4, -3.2, -7);
    ctx.closePath();
  });
}
export function cloakClasp(ctx: Ctx, it: QItem | undefined, side: boolean): void {
  if (!it) return;
  const [, d] = colors(it);
  fill(ctx, d, () => ctx.roundRect(side ? -2.5 : -6.5, -21.6, side ? 5 : 13, 1.8, 0.9));
  fill(ctx, "#e8bb48", () => ctx.arc(side ? 1.6 : 0, -20.7, 1.1, 0, TAU));
}
export function cloakBack(ctx: Ctx, it: QItem): void {
  const [c, d] = colors(it);
  fill(ctx, c, () => {
    ctx.moveTo(-6.5, -23);
    ctx.lineTo(6.5, -23);
    ctx.quadraticCurveTo(11.2, -22.6, 11.4, -18);
    ctx.lineTo(12.6, -2);
    ctx.quadraticCurveTo(0, 1, -12.6, -2);
    ctx.lineTo(-11.4, -18);
    ctx.quadraticCurveTo(-11.2, -22.6, -6.5, -23);
    ctx.closePath();
  });
  ctx.strokeStyle = d;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-3, -18);
  ctx.lineTo(-5, -3);
  ctx.moveTo(3, -18);
  ctx.lineTo(5, -3);
  ctx.stroke();
}

// ---------- 盾：正面（舊版＋一圈鋼邊）／側面（近乎側看的窄盾，在胸前）／背面（木板＋皮帶） ----------
const RIM = "#c3ccd6";
export function shieldFront(ctx: Ctx, it: QItem, x: number): void {
  ctx.save();
  ctx.translate(0, -pz("shieldUp"));
  pdHeld(ctx, it, x, true);
  if (it.kind === "shield_round") {
    ctx.strokeStyle = RIM;
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.arc(x, -13.5, 7.1, 0, TAU);
    ctx.stroke();
    if (S.SHEDGE) {
      ctx.strokeStyle = Q_OUT;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.arc(x, -13.5, 7.3, 0, TAU);
      ctx.stroke();
    }
  }
  ctx.restore();
}
export function shieldSide(ctx: Ctx, it: QItem): void {
  const [c, d] = colors(it);
  const tower = isTowerLike(it);
  ctx.save();
  ctx.translate(8.6, -13.5 - pz("shieldUp"));
  if (it.form === "sect_great" && tower) sectShieldSide(ctx, it);
  else if (it.form === "molten_shell" && tower) shellSide(ctx, it);
  else if (it.kind === "shield_round") {
    fill(ctx, d, () => ctx.ellipse(0, 0, 2.9, 7.5, 0, 0, TAU));
    fill(ctx, c, () => ctx.ellipse(0.6, 0, 2.1, 6.2, 0, 0, TAU));
    ctx.strokeStyle = RIM;
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.ellipse(0.2, 0, 2.7, 7.2, 0, 0, TAU);
    ctx.stroke();
    fill(ctx, it.trim ?? "#e8bb48", () => ctx.ellipse(1.9, 0, 1.1, 2, 0, 0, TAU));
  } else {
    const top = tower ? -9 : -7;
    const bot = tower ? 11 : 9;
    fill(ctx, d, () => {
      ctx.moveTo(-1.6, top);
      ctx.lineTo(2.2, top);
      ctx.lineTo(2.2, bot - 6);
      ctx.lineTo(0.6, bot);
      ctx.lineTo(-1.6, bot - 7);
      ctx.closePath();
    });
    fill(ctx, c, () => {
      ctx.moveTo(-0.6, top + 1.2);
      ctx.lineTo(1.4, top + 1.2);
      ctx.lineTo(1.4, bot - 6.4);
      ctx.lineTo(0.5, bot - 2.4);
      ctx.lineTo(-0.6, bot - 7);
      ctx.closePath();
    });
    fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(1.3, top + 1, 1, bot - top - 4));
  }
  ctx.restore();
}
export function shieldBack(ctx: Ctx, it: QItem, x: number, dy = 0): void {
  const [, d] = colors(it);
  const wood = "#7a5232";
  ctx.save();
  ctx.translate(x - 1, (it.kind === "shield_round" ? -11.8 : -16.5) + dy);
  if (it.kind === "shield_round") {
    fill(ctx, d, () => ctx.arc(0, 0, 7.5, 0, TAU));
    fill(ctx, wood, () => ctx.arc(0, 0, 6.2, 0, TAU));
    ctx.strokeStyle = RIM;
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.arc(0, 0, 7.1, 0, TAU);
    ctx.stroke();
  } else if (it.form === "sect_great" && isTowerLike(it)) {
    sectShieldBack(ctx, it);
  } else if (it.form === "molten_shell" && isTowerLike(it)) {
    shellBack(ctx, it);
  } else if (isTowerLike(it)) {
    fill(ctx, d, () => rr(ctx, -7, -6, 14, 22, 1.5));
    fill(ctx, wood, () => rr(ctx, -5.6, -4.6, 11.2, 19.2, 1));
  } else {
    fill(ctx, d, () => {
      ctx.moveTo(-7, -4);
      ctx.lineTo(7, -4);
      ctx.lineTo(6.5, 7);
      ctx.lineTo(0, 15);
      ctx.lineTo(-6.5, 7);
      ctx.closePath();
    });
    fill(ctx, wood, () => {
      ctx.moveTo(-5.5, -2.5);
      ctx.lineTo(5.5, -2.5);
      ctx.lineTo(5, 6.5);
      ctx.lineTo(0, 12.8);
      ctx.lineTo(-5, 6.5);
      ctx.closePath();
    });
  }
  ctx.restore();
}

// ---------- 配件 × 四方向（部件四方向清單.md）：角色的右手、右肩、右腰：正面在畫面左、背面在畫面右、朝東在近側、朝西在遠側 ----------
function arrows(ctx: Ctx, xs: ReadonlyArray<readonly [number, string]>, y0: number, y1: number): void {
  for (const [x, col] of xs)
    fill(ctx, col, () => {
      ctx.moveTo(x - 0.7, y0);
      ctx.lineTo(x, y1);
      ctx.lineTo(x + 0.7, y0);
      ctx.closePath();
    });
}
const FEATHERS: ReadonlyArray<readonly [number, string]> = [[-1.4, "#e8e0c8"], [0.2, "#d23c3c"], [1.6, "#e8e0c8"]];

/** 背掛：quiver 箭袋（右肩出口，斜背到左腰）、backpack 背包、scroll_case 卷軸筒。layer：behind＝身體之前畫、over＝身體之後。 */
export function backItem(ctx: Ctx, it: QItem | null | undefined, view: QView, layer: "behind" | "over"): void {
  if (!it) return;
  const [c, d] = colors(it);
  const SD = view === "side";
  const B = view === "back";
  const F = view === "front";
  const strap = it.strap ?? "#4a3020";
  if (it.kind === "quiver" || it.kind === "scroll_case") {
    const tube = it.kind === "scroll_case";
    if (F) {
      if (layer === "behind") {
        ctx.save();
        ctx.translate(-5.5, -23);
        ctx.rotate(-0.5);
        if (tube) fill(ctx, d, () => rr(ctx, -2, -4, 4, 4, 1.2));
        else arrows(ctx, FEATHERS, 0, -4.2);
        ctx.restore();
      } else {
        ctx.strokeStyle = strap;
        ctx.lineWidth = 1.3;
        ctx.beginPath();
        ctx.moveTo(-6.2, -20.6);
        ctx.lineTo(6.6, -9.8);
        ctx.stroke();
      }
      return;
    }
    if (B) {
      if (layer !== "over") return;
      ctx.save();
      ctx.translate(3.4, -14.6);
      ctx.rotate(0.2);
      fill(ctx, c, () => rr(ctx, -2.6, -9, 5.2, 15, 1.8));
      fill(ctx, d, () => ctx.rect(-2.6, -2, 5.2, 1.2));
      fill(ctx, d, () => ctx.rect(-2.6, 3, 5.2, 1.2));
      if (tube) fill(ctx, d, () => rr(ctx, -3, -11, 6, 3, 1.2));
      else arrows(ctx, FEATHERS, -9, -13.5);
      ctx.restore();
      return;
    }
    if (SD && layer === "behind") {
      ctx.save();
      ctx.translate(-6, -15.5);
      ctx.rotate(-0.28);
      fill(ctx, c, () => rr(ctx, -2.4, -9, 4.8, 14, 1.8));
      fill(ctx, d, () => ctx.rect(-2.4, -1.5, 4.8, 1.2));
      if (tube) fill(ctx, d, () => rr(ctx, -2.8, -11, 5.6, 3, 1.2));
      else arrows(ctx, [[-1.3, "#e8e0c8"], [0.2, "#d23c3c"], [1.5, "#e8e0c8"]], -9, -13.2);
      ctx.restore();
    }
    if (SD && layer === "over") {
      ctx.strokeStyle = strap;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.moveTo(S.WEST ? 1.5 : -1.5, -20.8);
      ctx.lineTo(S.WEST ? -3.5 : 4.6, -11);
      ctx.stroke();
    }
    return;
  }
  if (it.kind === "backpack") {
    if (F) {
      if (layer === "over") for (const x of [-4.8, 4.8]) fill(ctx, strap, () => rr(ctx, x - 0.9, -21, 1.8, 10, 0.8));
      return;
    }
    if (B) {
      if (layer === "over") {
        fill(ctx, c, () => rr(ctx, -6, -20.5, 12, 11, 2.5));
        fill(ctx, d, () => rr(ctx, -6, -20.5, 12, 4, 2));
        fill(ctx, "#d8b04a", () => ctx.rect(-0.8, -17, 1.6, 1.6));
      }
      return;
    }
    if (SD && layer === "behind") {
      fill(ctx, c, () => rr(ctx, -9.6, -20.5, 5.6, 11, 2));
      fill(ctx, d, () => rr(ctx, -9.6, -20.5, 5.6, 3.5, 1.6));
    }
    if (SD && layer === "over") fill(ctx, strap, () => rr(ctx, -1.6, -21, 1.8, 9, 0.8));
  }
}

/** 腰掛：scabbard 劍鞘（左腰，斜往後下）、pouch 腰包（右腰）。 */
export function waistItem(ctx: Ctx, it: QItem | undefined, view: QView, layer: "behind" | "over"): void {
  if (!it) return;
  const [c, d] = colors(it);
  const SD = view === "side";
  const B = view === "back";
  const F = view === "front";
  const left = it.kind === "scabbard";
  const near = SD ? (left ? S.WEST : !S.WEST) : true;
  if (SD && (layer === "behind") !== !near) return;
  if (!SD && layer !== "over") return;
  const x = F ? (left ? 7.2 : -7.2) : B ? (left ? -7.2 : 7.2) : 0;
  if (it.kind === "scabbard") {
    ctx.save();
    if (SD) {
      ctx.translate(-0.5, -9.5);
      ctx.rotate(0.95);
    } else {
      ctx.translate(x, -9.5);
      ctx.rotate((F ? -1 : 1) * (left ? 0.45 : -0.45));
    }
    fill(ctx, c, () => rr(ctx, -1.5, 0, 3, 11, 1.4));
    fill(ctx, d, () => ctx.rect(-1.5, 8.5, 3, 2.5));
    fill(ctx, "#d8b04a", () => ctx.rect(-1.7, 0, 3.4, 1.4));
    ctx.restore();
    return;
  }
  if (it.kind === "pouch") {
    const px = SD ? 0.2 : x * 0.64;
    fill(ctx, c, () => rr(ctx, px - 2.2, -9.2, 4.4, 4.6, 1.4));
    fill(ctx, d, () => rr(ctx, px - 2.2, -9.2, 4.4, 1.8, 1));
  }
}

/** 頸飾：necklace 項鍊（墜子在胸前）、beads 念珠。 */
/** 念珠的預設顏色（樣張 qNpc.js 護法武僧）。 */
export const BEAD_COLOR = "#6a3a22";
export function neckItem(ctx: Ctx, it: QItem | undefined, view: QView): void {
  if (!it || isNeckForm(it)) return; // QK-3：吊牌、符牌、骨符在最上層畫（qGearForms.drawTopForms）
  if (it.kind === "fur_collar" || it.kind === "feathers") {
    neckWide(ctx, it, view); // QK-8：毛領、白羽披肩（畫在身體上、手臂和胸前武器下面、頭下面）
    return;
  }
  const bead = it.kind === "beads";
  // QK-8 小修 2（QK-5 做）：念珠沒指定顏色時照樣張 qNpc.js 的深褐木珠 #6a3a22（不走木頭材質色）
  const c = bead && !it.color ? BEAD_COLOR : colors(it)[0];
  const SD = view === "side";
  const B = view === "back";
  if (B) {
    ctx.strokeStyle = c;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-3.5, -20.8);
    ctx.quadraticCurveTo(0, -20.2, 3.5, -20.8);
    ctx.stroke();
    return;
  }
  if (SD) {
    ctx.strokeStyle = c;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-1.5, -20.8);
    ctx.quadraticCurveTo(3.8, -17.6, 5.4, -18.4);
    ctx.stroke();
    fill(ctx, bead ? c : "#e8bb48", () => ctx.ellipse(5.4, -17.4, 1, 1.3, 0, 0, TAU));
    return;
  }
  if (bead)
    for (let i = 0; i <= 6; i++) {
      const t = i / 6;
      const bx = -4.5 + 9 * t;
      const by = -20.5 + 4.2 * Math.sin(t * Math.PI);
      fill(ctx, c, () => ctx.arc(bx, by, 0.9, 0, TAU));
    }
  else {
    ctx.strokeStyle = c;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-4.5, -20.6);
    ctx.quadraticCurveTo(0, -14.5, 4.5, -20.6);
    ctx.stroke();
    fill(ctx, "#e8bb48", () => {
      ctx.moveTo(0, -17.8);
      ctx.lineTo(1.4, -16.2);
      ctx.lineTo(0, -14.4);
      ctx.lineTo(-1.4, -16.2);
      ctx.closePath();
    });
  }
}

/** 毛領（脖子一圈蓬鬆毛）、白羽披肩（肩上一圈白羽，羽尖到胸口上緣）；樣張 qDoll.js neckWide。顏色照 it.color，沒寫用樣張預設（不走材質色）。 */
function neckWide(ctx: Ctx, it: QItem, view: QView): void {
  const SD = view === "side";
  const fur = it.kind === "fur_collar";
  const c = it.color ?? (fur ? "#d8c8a8" : "#f2f0ea");
  const d = mix(c, "#000000", 0.2);
  if (fur) {
    const xs = SD ? [-5.6, -3, -0.4, 2.2, 4.8] : [-8, -5.4, -2.7, 0, 2.7, 5.4, 8];
    fill(ctx, c, () => {
      for (const x of xs) {
        ctx.moveTo(x + 1.9, -20.4);
        ctx.ellipse(x, -20.4 + Math.abs(x) * 0.06, 1.9, 1.7, 0, 0, TAU);
      }
    });
    ctx.strokeStyle = d;
    ctx.lineWidth = 0.4;
    ctx.beginPath();
    ctx.moveTo(xs[0]!, -19.2);
    ctx.lineTo(xs[xs.length - 1]!, -19.2);
    ctx.stroke();
    return;
  }
  const tips: ReadonlyArray<readonly [number, number]> = SD
    ? [[-6, -16.4], [-3.4, -15.6], [-0.6, -15.8], [2.2, -16], [5, -16.8]]
    : [[-10, -17.2], [-6.6, -16.2], [-3.2, -15.8], [0, -15.6], [3.2, -15.8], [6.6, -16.2], [10, -17.2]];
  const top: ReadonlyArray<readonly [number, number]> = SD ? [[-7, -21.6], [6.2, -21]] : [[-8.4, -21.6], [8.4, -21.6]];
  fill(ctx, c, () => {
    ctx.moveTo(top[0]![0], top[0]![1]);
    ctx.quadraticCurveTo(0, -22.6, top[1]![0], top[1]![1]);
    const L = tips.length;
    ctx.lineTo(tips[L - 1]![0] + 0.6, tips[L - 1]![1] - 2);
    for (let i = L - 1; i >= 0; i--) {
      const [x, y] = tips[i]!;
      ctx.quadraticCurveTo(x + 1.2, y + 0.4, x, y);
      ctx.quadraticCurveTo(x - 1.2, y - 1.6, x - 1.4, y - 2.4);
    }
    ctx.closePath();
  });
  ctx.strokeStyle = d;
  ctx.lineWidth = 0.45;
  ctx.lineCap = "round";
  for (const [x, y] of tips) {
    ctx.beginPath();
    ctx.moveTo(x, y - 0.4);
    ctx.lineTo(x * 0.8, y - 3.4);
    ctx.stroke();
  }
}

/** 胸前紋章（body.crest：顏色）：正面在胸口；側面只在胸前前緣露一條；背面不畫。 */
export function crest(ctx: Ctx, it: QItem | undefined, view: QView): void {
  if (!it?.crest) return;
  const cr = it.crest;
  if (view === "back") return;
  if (view === "side") {
    fill(ctx, cr, () => rr(ctx, 4.4, -18.5, 1.6, 5, 0.6));
    return;
  }
  fill(ctx, cr, () => {
    ctx.moveTo(-2.6, -18.8);
    ctx.lineTo(2.6, -18.8);
    ctx.lineTo(2.6, -15.4);
    ctx.lineTo(0, -13.2);
    ctx.lineTo(-2.6, -15.4);
    ctx.closePath();
  });
  fill(ctx, "#e8bb48", () => ctx.rect(-0.6, -18.2, 1.2, 4));
}
