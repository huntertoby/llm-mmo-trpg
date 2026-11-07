// Q 版裝備的「新形制」（QK-3；照 docs/art/sample/qDoll.js 的新形制與 docs/art/sample/qGearExtra.js 的 13 件部件改寫）。
// 需求 docs/art/QK移植需求.md 第 4 節：額外裝備 17 件**直接長進 qDoll 的畫法**，不用樣張的色鍵遮罩。
//
// 樣張用「底圖＋色鍵遮罩」把部件疊上去；這裡改成在 qDoll 的圖層順序裡找對應的位置畫，遮擋由圖層順序自然得到：
//   torso（只畫在看得到的軀幹上）→ 身體之後、手臂之前（drawTorsoForms，剪在軀幹裡）
//   free（不蓋手臂、拳頭、武器）    → 身體之後、手臂之前（drawFreeForms）
//   hand（手的座標系）              → arm() 裡、拳頭之後、手上的東西之前（handFormUnder／handFormOver）：武器、盾、背面披風照原本圖層蓋在上面
//   top（最上層，挖掉頭）          → 正面、側面在整隻最後；背面在披風之前（背面披風在最上層，只有頭在它上面）（drawTopForms）
//   頭、腳                          → 頭飾之後（drawHeadFormTop）；每條腿自己的座標系裡（drawLegForm，走路時跟著腿動）
//
// 擴充點（QK-8 之後要加形制時照這裡加）：每一層一個函式、依 `kind`／`form` 判斷，認不得的一律不畫（其他裝備一像素不變）。
// 座標同 qDoll：腳底 (0,0)、往上 −y；側面用朝東座標（朝西由外層鏡像，近側遠側照 S.WEST 互換）。確定性：不用亂數。
import type { Ctx } from "./artDraw";
import { colors, fill, mix, rr, S, TAU, type QGear, type QItem, type QView } from "./qCore";

const dark = (c: string, t = 0.3): string => mix(c, "#000000", t);
const light = (c: string, t = 0.3): string => mix(c, "#ffffff", t);
const STEEL = "#b8c0c8";
const COPPER = "#c8803a";
const GOLD = "#e8bb48";
const BONE = "#efe6cc";
const CORD = "#4a3424";

function line(ctx: Ctx, c: string, w: number, pts: ReadonlyArray<readonly [number, number]>): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
}

/** 頸飾、披肩：不蓋臉（挖掉 qDoll 的頭：頭心 (0,−29)、r 8.45）。 */
function noHead(ctx: Ctx): void {
  ctx.beginPath();
  ctx.rect(-60, -90, 120, 120);
  ctx.arc(0, -29, 8.45, 0, TAU);
  ctx.clip("evenodd");
}

// ============================== 身體 ==============================
/** 身體上的紋（在 body() 裡、軀幹填色之後，側面已壓扁 0.72）。有畫回傳 true（鎖甲的方點就不畫）。 */
export function bodyPattern(ctx: Ctx, it: QItem | undefined, d: string): boolean {
  if (it?.kind === "mail" && it.form === "scale") {
    // 鱗甲（mail・scale）：一排排 U 形魚鱗，最下排停在腰帶上方；側面跟著 0.72 壓扁，沒有鎖甲方點
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(-7.5, -21, 15, 13.5, 3);
    ctx.clip();
    ctx.strokeStyle = d;
    ctx.lineWidth = 0.55;
    let row = 0;
    for (let y = -19.6; y < -11.2; y += 2.3, row++)
      for (let x = -7.5 + (row % 2 ? 1.2 : 0); x <= 8.5; x += 2.4) {
        ctx.beginPath();
        ctx.arc(x, y, 1.15, 0.15 * Math.PI, 0.85 * Math.PI);
        ctx.stroke();
      }
    ctx.restore();
    return true;
  }
  return false;
}

/** torso 層：只畫在看得到的軀幹上（身體之後、手臂之前；剪在腰帶以上的軀幹裡）。 */
export function drawTorsoForms(ctx: Ctx, gear: QGear, view: QView): void {
  const it = gear.body;
  const hunter = it?.kind === "leather" && it.form === "hunter";
  const ribs = it?.kind === "ribs";
  if (!hunter && !ribs) return;
  const SD = view === "side";
  const F = view === "front";
  const B = view === "back";
  ctx.save();
  ctx.beginPath();
  if (SD) ctx.roundRect(-5.4, -21, 10.8, 11.5, 2.2);
  else ctx.roundRect(-7.5, -21, 15, 11.5, 3);
  ctx.clip();
  if (hunter) {
    // 獵裝：正面兩個口袋蓋（在斜背帶下面）；側面口袋在前緣、背面不畫；斜背帶畫回口袋蓋上面
    const [, d] = colors(it);
    if (F)
      for (const x of [-4.6, 1.4]) {
        fill(ctx, d, () => ctx.roundRect(x, -14.2, 3.2, 1.6, 0.5));
        fill(ctx, GOLD, () => ctx.arc(x + 1.6, -13.4, 0.45, 0, TAU));
      }
    else if (SD) fill(ctx, d, () => ctx.roundRect(2.6, -14.2, 2.8, 1.6, 0.5));
    if (F) line(ctx, d, 1, [[-5, -20], [5, -11]]);
    else if (SD) line(ctx, d, 0.85, S.WEST ? [[1.5, -20.8], [-3.5, -11]] : [[-1.5, -20.8], [4.6, -11]]);
  }
  if (ribs) {
    // 骷髏：骨色上衣上畫脊椎與三對肋骨；背面脊椎＋肩胛；側面兩根肋骨在背側
    const k = "#8a826e";
    if (SD) {
      for (const y of [-18, -15]) line(ctx, k, 0.8, [[-4.6, y], [-1, y + 0.8]]);
      line(ctx, k, 0.9, [[-4.2, -20], [-4.2, -10]]);
    } else {
      line(ctx, k, 1, [[0, -20], [0, -10]]);
      if (B) for (const sx of [-1, 1]) line(ctx, k, 0.8, [[sx * 2, -19], [sx * 5, -17.6], [sx * 3.4, -15]]);
      else for (const y of [-18.4, -15.6, -12.8]) for (const sx of [-1, 1]) line(ctx, k, 0.8, [[sx * 1, y], [sx * 4.6, y + 0.6], [sx * 5.6, y + 1.8]]);
    }
  }
  ctx.restore();
}

/** free 層：不蓋手臂、拳頭、武器（身體之後、手臂之前）：獵裝下襬、全身板甲腿甲裙、圍裙。 */
export function drawFreeForms(ctx: Ctx, gear: QGear, view: QView): void {
  const it = gear.body;
  const SD = view === "side";
  const F = view === "front";
  const B = view === "back";
  if (it?.kind === "leather" && it.form === "hunter") {
    // 獵裝：皮背心加長成外套，下襬蓋過大腿（正面中間開衩、側面後開衩、背面中縫）
    const [c, d] = colors(it);
    const w = SD ? 5.9 : 8.2;
    fill(ctx, c, () => {
      ctx.moveTo(-w + 0.6, -7.6);
      ctx.lineTo(w - 0.6, -7.6);
      ctx.lineTo(w, -3.6);
      ctx.lineTo(-w, -3.6);
      ctx.closePath();
    });
    if (F)
      fill(ctx, dark(c, 0.35), () => {
        ctx.moveTo(-0.9, -3.6);
        ctx.lineTo(0, -7.4);
        ctx.lineTo(0.9, -3.6);
        ctx.closePath();
      });
    else if (B) line(ctx, d, 0.6, [[0, -7.4], [0, -3.8]]);
    else
      fill(ctx, dark(c, 0.35), () => {
        ctx.moveTo(-w + 0.3, -3.6);
        ctx.lineTo(-w + 1.6, -6.6);
        ctx.lineTo(-w + 2.4, -3.6);
        ctx.closePath();
      });
  }
  if (it?.kind === "plate" && it.form === "full") {
    // 全身板甲：兩片腿甲裙（側面一片在前、一片在後，背面兩片）
    const [c, d] = colors(it);
    const plates: ReadonlyArray<readonly [number, number]> = SD ? [[-5.4, 4.8], [-0.2, 5.6]] : [[-7.6, 7.2], [0.4, 7.2]];
    for (const [x, w] of plates) {
      fill(ctx, c, () => ctx.roundRect(x, -7.6, w, 4.6, [0, 0, 1.6, 1.6]));
      line(ctx, d, 0.55, [[x + 0.6, -5.4], [x + w - 0.6, -5.4]]);
    }
    if (!SD) line(ctx, d, 0.7, [[0, -7.4], [0, -3.2]]);
  }
  // 圍裙（waist apron）QK-8 起統一由 qNpc 畫（照 qNpc.js；qNpc.npcPrep 把 waist apron 換成部件）
}

// ============================== 最上層（挖掉頭） ==============================
/** 新頸飾形制（吊牌、符牌、骨符）由 drawTopForms 畫；qGear.neckItem 遇到時跳過。 */
export function isNeckForm(it: QItem | undefined): boolean {
  return (it?.kind === "pendant" && it.form === "tag") || (it?.kind === "charm" && (it.form === "tablet" || it.form === "bone"));
}

/** top 層：全身板甲護頸、披風外套的短披肩、吊牌／符牌／骨符（圍裙 QK-8 起由 qNpc 畫）。正面、側面在整隻最後畫；背面在披風之前畫。 */
export function drawTopForms(ctx: Ctx, gear: QGear, view: QView): void {
  const body = gear.body;
  const fullPlate = body?.kind === "plate" && body.form === "full";
  const cape = body?.kind === "coat" && body.form === "cape";
  const neck = isNeckForm(gear.neck) ? gear.neck : undefined;
  if (!fullPlate && !cape && !neck) return;
  if (S.TINT) return;
  const SD = view === "side";
  const B = view === "back";
  const F = view === "front";
  ctx.save();
  noHead(ctx);
  if (fullPlate) {
    const [c, d] = colors(body);
    fill(ctx, c, () => (SD ? ctx.roundRect(-4.6, -22.4, 9.4, 2.6, 1.2) : ctx.roundRect(-5.6, -22.4, 11.2, 2.6, 1.2)));
    line(ctx, d, 0.5, SD ? [[-4, -20.9], [4.2, -20.9]] : [[-5, -20.9], [5, -20.9]]);
  }
  if (cape) {
    // 披風外套：肩上一片短披肩（蓋過肩膀與上臂），正面圓下緣、背面較長；側面從前胸繞到後背
    const [c, d] = colors(body);
    const k = dark(c, 0.18);
    if (SD)
      fill(ctx, k, () => {
        ctx.moveTo(-6.2, -21.4);
        ctx.quadraticCurveTo(0, -22, 5.6, -21.4);
        ctx.quadraticCurveTo(7, -18, 5.4, -15.6);
        ctx.quadraticCurveTo(0, -14.4, -6.6, -14.6);
        ctx.quadraticCurveTo(-7.6, -18, -6.2, -21.4);
        ctx.closePath();
      });
    else
      fill(ctx, k, () => {
        ctx.moveTo(-9.6, -21);
        ctx.quadraticCurveTo(0, -22.4, 9.6, -21);
        ctx.quadraticCurveTo(11.6, -17, 10.6, B ? -13.6 : -15.2);
        ctx.quadraticCurveTo(0, B ? -11.6 : -13.2, -10.6, B ? -13.6 : -15.2);
        ctx.quadraticCurveTo(-11.6, -17, -9.6, -21);
        ctx.closePath();
      });
    line(ctx, d, 0.6, SD ? [[-6, -15.6], [5, -16.4]] : [[-9.8, -16], [0, B ? -12.8 : -14.2], [9.8, -16]]);
    if (F) fill(ctx, GOLD, () => ctx.arc(0, -19.4, 0.9, 0, TAU));
    else if (SD) fill(ctx, GOLD, () => ctx.arc(5, -19.6, 0.8, 0, TAU));
  }
  if (neck) neckForm(ctx, neck, view);
  ctx.restore();
}

/** 吊牌（pendant・tag）、符牌（charm・tablet）、骨符（charm・bone）：側面掛在胸前前緣、露在手臂前方；背面鏈子被後腦擋住。 */
function neckForm(ctx: Ctx, it: QItem, view: QView): void {
  const tag = it.kind === "pendant";
  const cord = tag ? "#8d969f" : CORD;
  if (view === "back") {
    line(ctx, cord, tag ? 0.6 : 0.7, [[-3.5, -20.8], [0, -20.2], [3.5, -20.8]]);
    return;
  }
  const fang = (x: number, y: number): void =>
    fill(ctx, BONE, () => {
      ctx.moveTo(x - 1.2, y);
      ctx.quadraticCurveTo(x - 0.8, y + 3, x + 0.9, y + 4.4);
      ctx.quadraticCurveTo(x + 0.3, y + 2.4, x + 1.2, y);
      ctx.closePath();
    });
  if (view === "side") {
    line(ctx, cord, tag ? 0.55 : 0.6, [[3.4, -21], [5.8, -19.6], [6.6, tag ? -18.4 : -18.6]]);
    if (tag) {
      fill(ctx, STEEL, () => ctx.roundRect(5.6, -18.6, 2.2, 3.4, 0.6));
      fill(ctx, "#6a7078", () => ctx.arc(6.7, -17.8, 0.35, 0, TAU));
    } else if (it.form === "tablet") {
      fill(ctx, GOLD, () => ctx.roundRect(5.4, -18.8, 2.6, 4, 0.5));
      line(ctx, "#c0392b", 0.5, [[6.7, -18], [6.7, -15.6]]);
    } else {
      fill(ctx, "#8a5a32", () => ctx.arc(6.6, -18.6, 0.75, 0, TAU));
      fang(6.8, -18.2);
    }
    return;
  }
  if (tag) {
    line(ctx, cord, 0.55, [[-4.2, -20.8], [0, -16.4], [4.2, -20.8]]);
    fill(ctx, STEEL, () => ctx.roundRect(-1.3, -16.6, 2.6, 3.6, 0.7));
    fill(ctx, "#6a7078", () => ctx.arc(0, -15.8, 0.4, 0, TAU));
  } else if (it.form === "tablet") {
    line(ctx, cord, 0.6, [[-4.2, -20.8], [0, -16.6], [4.2, -20.8]]);
    fill(ctx, GOLD, () => ctx.roundRect(-2, -16.8, 4, 4.4, 0.6));
    line(ctx, "#c0392b", 0.5, [[0, -16], [-0.9, -14.6], [0.9, -14.2], [0, -13.1]]);
  } else {
    line(ctx, cord, 0.6, [[-4.2, -20.8], [0, -16.8], [4.2, -20.8]]);
    fang(0, -17);
    for (const x of [-2, 2]) fill(ctx, "#8a5a32", () => ctx.arc(x, -17.9, 0.75, 0, TAU));
  }
}

// ============================== 頭 ==============================
/** 斗篷帽（hood・cowl）：兜帽下面接一片披領；正面尖角垂到胸口、和兜帽的接縫順著下巴；背面尖角到肩胛；側面前後各一角。
 *  正面、側面畫在頭下面（臉蓋在披領上），背面畫在兜帽之後（drawQ 的頭那一段呼叫）。 */
export function isCowl(it: QItem | undefined): boolean {
  return it?.kind === "hood" && it.form === "cowl";
}
export function cowl(ctx: Ctx, it: QItem, view: QView): void {
  const [c, d] = colors(it);
  ctx.save();
  ctx.lineJoin = "round";
  ctx.strokeStyle = d;
  ctx.lineWidth = 0.6;
  if (view === "side") {
    fill(ctx, c, () => {
      ctx.moveTo(-8.4, -24);
      ctx.lineTo(7.4, -24);
      ctx.lineTo(6.6, -16);
      ctx.lineTo(1.6, -18.6);
      ctx.lineTo(-3, -15.4);
      ctx.lineTo(-8.8, -17.6);
      ctx.closePath();
    });
    ctx.beginPath();
    ctx.moveTo(-8.6, -17.6);
    ctx.lineTo(-3, -15.4);
    ctx.lineTo(1.6, -18.6);
    ctx.lineTo(6.6, -16);
    ctx.stroke();
  } else if (view === "back") {
    fill(ctx, c, () => {
      ctx.moveTo(-9.6, -23.2);
      ctx.lineTo(9.6, -23.2);
      ctx.lineTo(10.4, -17.6);
      ctx.lineTo(0, -12.6);
      ctx.lineTo(-10.4, -17.6);
      ctx.closePath();
    });
    ctx.beginPath();
    ctx.moveTo(-10.4, -17.6);
    ctx.lineTo(0, -12.6);
    ctx.lineTo(10.4, -17.6);
    ctx.stroke();
  } else {
    fill(ctx, c, () => {
      ctx.moveTo(-9.6, -24);
      ctx.lineTo(9.6, -24);
      ctx.lineTo(10.4, -17.6);
      ctx.lineTo(0, -13.8);
      ctx.lineTo(-10.4, -17.6);
      ctx.closePath();
    });
    ctx.beginPath();
    ctx.moveTo(-10.4, -17.6);
    ctx.lineTo(0, -13.8);
    ctx.lineTo(10.4, -17.6);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(-9.4, -22.6);
    ctx.quadraticCurveTo(0, -18.4, 9.4, -22.6);
    ctx.stroke();
  }
  ctx.restore();
}

const isFurCap = (it: QItem | undefined): boolean => it?.kind === "cap" && it.form === "fur";

/** 頭飾畫之前的剪裁（毛帽側面：皮帽伸出臉前的帽舌不畫）。有剪裁回傳 true，呼叫端畫完頭飾要 restore。 */
export function headgearClip(ctx: Ctx, it: QItem | undefined, view: QView): boolean {
  if (!(isFurCap(it) && view === "side")) return false;
  ctx.save();
  ctx.beginPath();
  ctx.rect(-80, -120, 160, 200);
  ctx.rect(8.7, -34.5, 6, 4.4);
  ctx.clip("evenodd");
  return true;
}

/** 頭飾之後：毛帽的米白毛邊（圓角、不凸出頭、下緣一排圓凸）與兩側護耳；側面護耳沿後腦垂下一片。 */
export function drawHeadFormTop(ctx: Ctx, it: QItem | undefined, view: QView): void {
  if (!isFurCap(it) || S.TINT) return;
  const FUR = "#ece4cc";
  const FURD = "#c8bc9c";
  const SD = view === "side";
  ctx.save();
  ctx.beginPath();
  ctx.arc(0, -29, 8.5, 0, TAU);
  ctx.arc(SD ? -0.4 : 0, -31, 9.1, Math.PI, 0);
  ctx.clip();
  const x0 = SD ? -9.6 : -9.2;
  const x1 = SD ? 8.8 : 9.2;
  const n = 5;
  const st = (x1 - x0) / n;
  fill(ctx, FUR, () => {
    ctx.moveTo(x0, -32);
    ctx.quadraticCurveTo(x0, -34.4, x0 + 2, -34.4);
    ctx.lineTo(x1 - 2, -34.4);
    ctx.quadraticCurveTo(x1, -34.4, x1, -32);
    for (let i = 0; i < n; i++) {
      const x = x1 - i * st;
      ctx.quadraticCurveTo(x - st / 2, -29.6, x - st, -31.4);
    }
    ctx.closePath();
  });
  if (SD) {
    fill(ctx, FUR, () => {
      ctx.moveTo(-5.2, -31.4);
      ctx.quadraticCurveTo(-6.4, -26.4, -4.2, -23.4);
      ctx.quadraticCurveTo(-1.4, -22.4, 0.4, -24.8);
      ctx.quadraticCurveTo(1.4, -28, 1, -31.4);
      ctx.closePath();
    });
    line(ctx, FURD, 0.5, [[-2.6, -29.6], [-2.2, -24.6]]);
    ctx.restore();
    return;
  }
  ctx.restore();
  for (const sx of [-1, 1]) {
    fill(ctx, FUR, () => ctx.roundRect(sx * 7.6 - 1.9, -31.6, 3.8, 7.6, 1.9));
    line(ctx, FURD, 0.45, [[sx * 7.6, -29.8], [sx * 7.6, -25.6]]);
  }
}

// ============================== 手（手的座標系在 (x, hy)，+y 往指尖、−y 往手肘） ==============================
/** 拳頭下面：鎖鏈護手的喇叭袖口。 */
export function handFormUnder(ctx: Ctx, h: QItem | undefined, x: number, hy: number): void {
  if (h?.kind === "gauntlets" && h.form === "mail") {
    const [c, d] = colors(h);
    fill(ctx, c, () => {
      ctx.moveTo(x - 2.1, hy - 1.2);
      ctx.lineTo(x + 2.1, hy - 1.2);
      ctx.lineTo(x + 3, hy - 5.6);
      ctx.lineTo(x - 3, hy - 5.6);
      ctx.closePath();
    });
    fill(ctx, d, () => ctx.rect(x - 3, hy - 5.8, 6, 0.8));
    ctx.fillStyle = d;
    for (const [dx, dy] of [[-1.4, -4.2], [0.4, -4.2], [-0.5, -2.8], [1.3, -2.8]] as const) ctx.fillRect(x + dx - 0.3, hy + dy - 0.3, 0.6, 0.6);
  }
}

/**
 * 拳頭上面：鎖鏈護手的鎖子點、露指手套的膚色指頭與手套口、長皮手套的護套、臂環。
 * far：遠側暗一階的換色；edge：正面背面空手時拳頭整圈邊（露出的指頭保留下半圈）。
 */
export function handFormOver(ctx: Ctx, h: QItem | undefined, skin: string, x: number, hy: number, far: (c: string) => string, edge: ((c: string) => void) | null): void {
  if (h?.kind === "gauntlets" && h.form === "mail") {
    const [, d] = colors(h);
    ctx.fillStyle = far(d);
    for (const [dx, dy] of [[-1.2, -1], [0.6, -1], [-0.3, 0.4], [1.4, 0.4], [-1.3, 1.6], [0.5, 1.6]] as const) ctx.fillRect(x + dx - 0.3, hy + dy - 0.3, 0.6, 0.6);
  }
  if (h?.kind === "gloves" && h.form === "fingerless") {
    const sk = far(skin);
    const [, d] = colors(h);
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, hy, 2.4, 0, TAU);
    ctx.clip();
    ctx.beginPath();
    ctx.rect(x - 3, hy + 0.6, 6, 3);
    ctx.clip();
    fill(ctx, sk, () => ctx.rect(x - 3, hy + 0.6, 6, 3));
    if (edge) edge(sk);
    ctx.restore();
    fill(ctx, far(d), () => ctx.rect(x - 2.3, hy + 0.35, 4.6, 0.5)); // 手套口（指根）
    fill(ctx, far(d), () => rr(ctx, x - 2.3, hy - 2.9, 4.6, 1.3, 0.5)); // 手腕一圈
  }
  if (h?.kind === "gloves" && h.form === "long") {
    // 長皮手套：往上包到前臂一半，袖口外翻一圈淺色
    const [c, d] = colors(h);
    fill(ctx, c, () => ctx.roundRect(x - 2.2, hy - 6.2, 4.4, 5.4, 1));
    fill(ctx, light(c, 0.22), () => ctx.roundRect(x - 2.6, hy - 6.8, 5.2, 1.6, 0.7));
    line(ctx, d, 0.4, [[x - 2, hy - 1.2], [x + 2, hy - 1.2]]);
  }
  if (h?.kind === "bracers" && h.form === "ring") {
    // 臂環：前臂兩圈細金屬環（銅色＋一點高光）
    for (const y of [-5.2, -3.2]) {
      fill(ctx, COPPER, () => ctx.roundRect(x - 2.5, hy + y, 5, 1.1, 0.5));
      fill(ctx, light(COPPER, 0.5), () => ctx.rect(x - 1.6, hy + y + 0.2, 1.2, 0.35));
    }
  }
}

/** 臂環不畫成皮護腕（qDoll 的 bracers 一律畫寬皮帶；ring 形制改由 handFormOver 畫兩條細環）。 */
export const isRingBracer = (h: QItem | undefined): boolean => h?.kind === "bracers" && h.form === "ring";

// ============================== 腳（每條腿自己的座標系；rotAt 不改座標，用站好時的絕對座標畫） ==============================
/**
 * 一條腿的鞋子形制（腳畫好之後）：綁腿鞋布條、尖頭鐵靴的鞋尖、護膝脛甲的護膝。
 * sx：−1／1（側面 1＝近側）；x：這條腿的中心；part：lower＝小腿段（膝轉之後）、upper＝護膝（同一個座標系，膝蓋那一端）。
 */
export function drawLegForm(ctx: Ctx, feet: QItem | undefined, sx: number, x: number, view: QView): void {
  if (!feet) return;
  const SD = view === "side";
  if (feet.kind === "shoes" && feet.form === "wrapped") {
    // 綁腿鞋：小腿纏三圈淺色斜布條；側面兩腿的布條同一條斜線（站好時連成一條）
    const a = SD ? -1.6 - 2.4 : x - 2.4;
    const b = SD ? 1.6 + 2.4 : x + 2.4;
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(x - 2.1, -5.6, 4.2, 4.6, 1.2);
    ctx.clip();
    for (const y of [-5, -3.3, -1.6])
      fill(ctx, "#e2d8bc", () => {
        ctx.moveTo(a, y + 0.6);
        ctx.lineTo(b, y - 0.6);
        ctx.lineTo(b, y + 0.4);
        ctx.lineTo(a, y + 1.6);
        ctx.closePath();
      });
    ctx.restore();
  } else if (feet.kind === "iron_boots" && feet.form === "sabaton") {
    // 尖頭鐵靴：側面往前尖出、正面往下尖（不低於地面線）、背面看不到尖；鞋面一道分節線
    const [c, d] = colors(feet);
    if (SD) {
      if (sx < 0) return;
      fill(ctx, c, () => {
        ctx.moveTo(2, -3);
        ctx.lineTo(5.4, -2.4);
        ctx.lineTo(8.6, -0.6);
        ctx.lineTo(5.6, 0.6);
        ctx.lineTo(1.8, 0.6);
        ctx.closePath();
      });
      line(ctx, d, 0.5, [[3.4, -2.6], [4, 0.4]]);
      return;
    }
    if (view === "front")
      fill(ctx, c, () => {
        ctx.moveTo(x - 3.4, -1.6);
        ctx.lineTo(x + 3.4, -1.6);
        ctx.lineTo(x + 2.2, -0.3);
        ctx.lineTo(x, 0.8);
        ctx.lineTo(x - 2.2, -0.3);
        ctx.closePath();
      });
    line(ctx, d, 0.5, [[x - 3, -1.8], [x + 3, -1.8]]);
  } else if (feet.kind === "greaves" && feet.form === "knee") {
    // 護膝脛甲：膝蓋一片圓護膝（亮一階、中間一道稜）：正面兩片、側面近側一片往前凸、背面不畫
    if (view === "back" || (SD && sx < 0)) return;
    const [c, d] = colors(feet);
    const kx = SD ? 2.2 : x;
    fill(ctx, light(c, 0.2), () => ctx.ellipse(kx, -5.4, SD ? 2.4 : 2.6, 2, 0, 0, TAU));
    line(ctx, d, 0.45, SD ? [[kx + 0.4, -6.8], [kx + 1.4, -4.2]] : [[kx, -7], [kx, -3.8]]);
  }
}
