// Q 版紙娃娃本體（QK-1；照 docs/art/sample/qDoll.js 改寫，需求 docs/art/QK移植需求.md 第 2 節）。
// 這裡畫：手臂（手臂規則 ARM_SPREAD_SET.E、袖子描邊、內線、拳頭圈、遠側暗一階）、關鍵姿勢表 KEY（6 類 × 正背側、朝西手性互換、雙手劍 GS、
// 出招 Q 版專用關鍵姿勢）、側面兩隻手的規劃（sidePlan）、持弓待機（bowStill）、整隻的圖層順序（drawQ）。
// 姿勢：沒給 `wpn` ＝ 站好（用關鍵姿勢）；給了 `wpn` ＝ 6M／6N 片段（武器角度＝手臂角度＋wpn）。片段本身不改。
import type { Ctx } from "./artDraw";
import {
  ARM, ARM_SPREAD_SET, clamp01, colors, elbowTo, FA, fill, fk, getM, ik, isShield, isTowerLike, mark, mix, OUTA, pz, Q_OUT, rec, rot, rotAt, rr, S, SEAMF, SHX, TAU, UA,
  type P2, type QHooks, type QItem, type QPose, type QUnit, type QView,
} from "./qCore";
import { body, backItem, cloakBack, cloakClasp, cloakFront, cloakSide, crest, leg, neckItem, shieldBack, shieldFront, shieldSide, waistItem } from "./qGear";
import { cowl, drawFreeForms, drawHeadFormTop, drawTopForms, drawTorsoForms, handFormOver, handFormUnder, headgearClip, isCowl, isRingBracer } from "./qGearForms";
import { drawQHead, drawQHeadgear } from "./qHead";
import { raceBuild, raceEars, raceHat, raceHorns, raceTail } from "./qRace";
import { BOW_EY, mainWeapon, offDagger, pdHeld, QW, qWeapon } from "./qWeapons";
import { isHeldOff } from "./qNpcHeld";
import { drawFbLayer, fbFrameAt, fbKindOfIndex, type FbApi, type FbFrame, type FbLayer, type FbView } from "./qAnimFB";
import { npcAfterQ, npcBeforeQ, npcPrep, type NpcFrame } from "./qNpc";

/** 赤膊（QK-8）時手臂內線、拳頭邊、側面描邊的加深量（膚色＋0.23，和胸肌線同色）；其他時候 null＝照舊。 */
let EDGEK: number | null = null;
/** QK-3 檢查第 1 條：側面拿盾、彎肘的那隻手，長手套護套與臂環往肘那頭多包多少（袖口、臂環壓在鱗甲袖子上面露出來，盾照舊在最上層）。 */
let HAND_LIFT = 0;
/** QK-5：正面、背面五類出招這一格（qAnimFB）；null＝照原本的正面、背面畫法。 */
let FB: { kind: string; frame: FbFrame; view: FbView } | null = null;
const SHIELD_HAND_LIFT = 2.2;
/** 副手拿法球、拂塵、符紙、傀儡線（QK-8：畫成對應物件，不是書）。法球沒指定顏色時照元素色（同原本 pdHeld 的副手法球）。 */
const offHeld = (gear: QUnit["gear"]): QItem | null => {
  const it = gear.off_hand;
  if (!isHeldOff(it)) return null;
  const tint = it!.kind === "orb" && !it!.color && it!.element ? S.hooks?.tint(it!.element) : undefined;
  return tint ? { ...it!, color: tint } : it!;
};

type Hand = (hand: P2, ctx: Ctx) => void;

// ---------- 手臂：4×10 的方塊，拆成上臂（肩轉）＋前臂（肘轉）＋手 ----------
/** inHand：在手的座標系畫手上的東西（畫在手掌上面，握把從拳頭上穿過）；handOnly：只畫手上的東西；len：[上臂, 前臂]。 */
function arm(ctx: Ctx, unit: QUnit, x: number, shoulderA0: number, elbowA0: number, side: number, inHand: Hand | null = null, handOnly = false, len0: readonly number[] | null = null): P2 {
  let shoulderA = shoulderA0;
  let elbowA = elbowA0;
  let len = len0;
  let SO = 0;
  let SOd = 0;
  const A = ARM();
  // sideOne（2026-11-06 使用者：「5 欄」）：側面肘角 ≤ 0.15 的手臂當成打直，拳頭留在原位（肩角改成直指拳頭、兩段按比例縮）
  if (A.sideOne && side && elbowA && Math.abs(elbowA) <= 0.15) {
    const u0 = len ? (len[0] ?? UA) : UA;
    const f0 = len ? (len[1] ?? FA) : FA;
    const r = Math.hypot(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA));
    SO = elbowA;
    SOd = Math.atan2(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA));
    shoulderA += SOd;
    len = [(u0 * r) / (u0 + f0), (f0 * r) / (u0 + f0)];
    elbowA = 0;
  }
  const { look, gear } = unit;
  const it = gear.body;
  const kind = it?.kind ?? "shirt";
  const [c0] = colors(it);
  const c = S.FAR ? mix(c0, "#000000", S.FAR) : c0;
  // 正面、背面穿盔甲時袖子深一階（SEAMIN）；遠側手臂、背面持盾畫暗一階（FAR）
  const sleeve = S.TINT ?? (S.SEAMIN ? mix(c, "#000000", 0.15) : c);
  const ua = len ? (len[0] ?? UA) : UA;
  const fa = len ? (len[1] ?? FA) : FA;
  const hy = -20 + ua + fa;
  const hc = gear.hands ? colors(gear.hands)[0] : look.skin;
  const seam = (path: () => void): void => {
    if (!S.SEAM || S.TINT || handOnly) return;
    if (S.SEAMIN) {
      // 盔甲類：袖子描一圈深一點的內框，只畫在袖子裡面（輪廓不變寬）
      ctx.save();
      ctx.beginPath();
      path();
      ctx.clip();
      ctx.strokeStyle = mix(c, "#000000", 0.5);
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      path();
      ctx.stroke();
      ctx.restore();
      return;
    }
    ctx.strokeStyle = mix(c, "#000000", EDGEK ?? 0.38);
    ctx.lineWidth = EDGEK ? 0.9 : 0.55;
    ctx.beginPath();
    path();
    ctx.stroke();
  };
  const pad = (): void => {
    if (!S.NOPAD && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU));
  };
  ctx.save();
  rotAt(ctx, x, -20, shoulderA);
  if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + 1, 2)); // 上臂
  // ONE：打直的手臂（正面、背面、側面 sideOne）袖子描邊只描一圈，沿上臂＋前臂合成的一條（手肘沒有橫線）
  const ONE = S.SEAM && !S.SEAMIN && (!side || !!A.sideOne) && !elbowA;
  if (!(S.SEAMIN && !elbowA) && !ONE) seam(() => ctx.roundRect(x - 2, -21, 4, ua + 1, 2));
  if (!handOnly) pad();
  rotAt(ctx, x, -20 + ua, elbowA);
  if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -20.5 + ua, 4, fa, 2)); // 前臂
  const free = (S.FILLARM || S.FREEARM) && !side && !elbowA;
  if (!handOnly && free) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + 0.5, 2)); // 空手微微離開：上臂、前臂連成一條
  if (!handOnly && free && !S.SEAM && !S.TINT && A.edge) armEdge(ctx, sleeve, x, ua + fa + 0.5); // 布料類空手：靠身體那側一條粗內線
  if (ONE) {
    if (!handOnly && !S.TINT) {
      fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + 0.5, 2));
      seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + 0.5, 2));
      pad();
    }
  } else if (!(S.SEAMIN && !elbowA)) seam(() => ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2));
  else if (!handOnly && !S.TINT) {
    seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + 0.5, 2));
    pad();
  }
  if (!handOnly && gear.hands && gear.hands.kind === "bracers" && !isRingBracer(gear.hands)) {
    const [bc, bd] = colors(gear.hands);
    fill(ctx, S.TINT ?? bc, () => rr(ctx, x - 2.3, hy - 3.1, 4.6, 2.4, 0.8));
    fill(ctx, S.TINT ?? bd, () => ctx.rect(x - 2.3, hy - 1.7, 4.6, 0.6));
  } // 護腕：四方向都跟著前臂
  const k0 = gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin;
  const fistC = S.TINT ?? (S.FARH ? mix(k0, "#000000", S.FARH) : k0);
  if (!handOnly && !S.TINT) handFormUnder(ctx, gear.hands, x, hy); // QK-3：手部形制（鎖鏈護手的袖口）在拳頭下面
  if (!handOnly) fill(ctx, fistC, () => ctx.arc(x, hy, 2.4, 0, TAU));
  const gauntlet = qWeapon(gear.main_hand)?.kind === "gauntlet";
  const ringEdge = free && !S.SEAM && !!A.edge?.fist && !gauntlet;
  if (!handOnly && ringEdge && !S.TINT) fistEdge(ctx, sleeve, fistC, x, hy, ua, fa); // 空手的拳頭一圈深色邊；拳套不畫
  // QK-3：手部形制（露指、鎖子點、長手套、臂環）在拳頭上面、手上的東西下面（武器、盾、背面披風照原本圖層蓋在上面）
  if (!handOnly && !S.TINT) handFormOver(ctx, gear.hands, look.skin, x, hy, (k) => (S.FARH ? mix(k, "#000000", S.FARH) : k), ringEdge ? (k) => fistEdge(ctx, sleeve, k, x, hy, ua, fa) : null, side && elbowA ? HAND_LIFT : 0);
  if (!handOnly && !S.TINT && gauntlet && gear.main_hand) glove(ctx, gear.main_hand, x, hy); // 拳套戴在手上
  rotAt(ctx, x, hy, SO - SOd); // sideOne：手的座標系轉回原本前臂的角度
  if (inHand) inHand([x, hy], ctx);
  ctx.restore();
  return [x, hy];
}

/** 布料類空手的手臂：沿「上臂＋前臂合成的一條」描邊（inner＝只畫靠身體那側），clip 在手臂裡（輪廓不變寬）。 */
function armEdge(ctx: Ctx, sleeve: string, x: number, h: number): void {
  const e = ARM().edge!;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x - 2, -21, 4, h, 2);
  ctx.clip();
  if (e.mode === "inner") {
    ctx.beginPath();
    if (x > 0) ctx.rect(x - 2.5, -22, 2.5, h + 2);
    else ctx.rect(x, -22, 2.5, h + 2);
    ctx.clip();
  }
  ctx.strokeStyle = mix(sleeve, "#000000", EDGEK ?? e.k);
  ctx.lineWidth = e.w;
  ctx.beginPath();
  ctx.roundRect(x - 2, -21, 4, h, 2);
  ctx.stroke();
  ctx.restore();
}
/** 空手的拳頭一圈深色邊（ring），clip 在拳頭圓裡。 */
function fistEdge(ctx: Ctx, sleeve: string, fistC: string, x: number, hy: number, ua: number, fa: number): void {
  const f = ARM().edge!.fist!;
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, hy, 2.4, 0, TAU);
  ctx.clip();
  if (f.mode === "seam") {
    ctx.beginPath();
    ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2);
    ctx.clip();
  }
  ctx.strokeStyle = mix(f.mode === "seam" ? sleeve : fistC, "#000000", EDGEK ?? f.k);
  ctx.lineWidth = f.w;
  ctx.beginPath();
  ctx.arc(x, hy, 2.4, 0, TAU);
  ctx.stroke();
  ctx.restore();
}
/** 拳套（第 8 版）：包住拳頭、前臂那頭護腕、指節板。 */
function glove(ctx: Ctx, it: QItem, x: number, y: number): void {
  const [k, d] = it.color || it.material ? colors(it) : S.hooks!.colors({ kind: it.kind, material: "steel", ...(it.element ? { element: it.element } : {}) });
  fill(ctx, d, () => rr(ctx, x - 2.7, y - 4.4, 5.4, 2.4, 0.8));
  fill(ctx, k, () => ctx.arc(x, y, 2.9, 0, TAU));
  fill(ctx, d, () => rr(ctx, x - 2.5, y + 1.0, 5, 1.3, 0.6));
  fill(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(x - 1, y - 0.8, 0.9, 0, TAU));
}

/** 背面持盾的左手臂：打直往外下方，前臂套臂帶，拳頭握盾背正中央的握把；前臂與手外面一圈深色輪廓和盾緣分開。 */
function shieldArmBack(ctx: Ctx, unit: QUnit): void {
  S.TINT = S.POSE?.tintOff ?? null;
  const k = { sA: OUTA(), eA: 0 };
  const sx = -SHX();
  const h = fk(sx, k.sA, k.eA);
  const strap = "#3a2414";
  if (!S.TINT) {
    ctx.save();
    rotAt(ctx, sx, -20, k.sA);
    fill(ctx, Q_OUT, () => rr(ctx, sx - 2.45, -15.9, 4.9, FA + 0.8, 2.4));
    ctx.restore();
    fill(ctx, Q_OUT, () => ctx.arc(h[0], h[1], 2.85, 0, TAU));
    ctx.save();
    ctx.translate(h[0], h[1]);
    ctx.rotate(k.sA);
    fill(ctx, strap, () => rr(ctx, -4.4, -0.8, 8.8, 1.6, 0.6)); // 握把：從拳頭兩邊穿出去
    ctx.restore();
  }
  S.EBOFF = true;
  arm(ctx, unit, sx, k.sA, k.eA, 0, rec("off"));
  S.EBOFF = false;
  if (!S.TINT) {
    const hc = unit.gear.hands && unit.gear.hands.kind !== "bracers" ? colors(unit.gear.hands)[0] : unit.look.skin;
    ctx.save();
    ctx.translate(h[0], h[1]);
    ctx.rotate(k.sA);
    fill(ctx, mix(hc, "#000000", 0.1), () => rr(ctx, -2.1, 0.2, 4.2, 1.9, 0.9)); // 彎起來的四指
    ctx.strokeStyle = mix(hc, "#000000", 0.45);
    ctx.lineWidth = 0.32;
    ctx.beginPath();
    for (const xx of [-1.05, 0, 1.05]) {
      ctx.moveTo(xx, 0.35);
      ctx.lineTo(xx, 1.95);
    }
    ctx.moveTo(-2, 0.2);
    ctx.lineTo(2, 0.2);
    ctx.stroke();
    ctx.restore();
  }
  S.TINT = null;
  const m = fk(sx, k.sA, 0, [UA + 1.6, 0]);
  ctx.save();
  ctx.translate(m[0], m[1]);
  ctx.rotate(k.sA);
  fill(ctx, strap, () => rr(ctx, -2.6, -0.75, 5.2, 1.5, 0.5)); // 臂帶：橫套在前臂上
  ctx.restore();
}

// ---------- 關鍵姿勢（第 6～17 版）----------
/** hand＝主手手掌、a＝武器角度（0 朝上、順時針為正）、og＝副手握點（武器座標）、mg＝主手握點、st＝手臂打直。 */
export interface KPose {
  hand: readonly number[];
  a: number;
  og?: readonly number[] | "string" | null;
  short?: boolean | "f";
  mg?: number;
  grip?: number;
  gripS?: number;
  gripW?: number;
  flipS?: boolean;
  st?: boolean;
  animOg?: readonly number[];
  wh?: "off" | "main";
  s?: readonly number[];
  tilt?: number;
  nt?: number;
  ah?: number;
  farX?: number;
  nearX?: number;
  edir?: readonly number[];
  aW?: number;
  hw?: readonly number[];
  needOff?: boolean;
  fore?: readonly number[];
  layer?: string;
  olen?: readonly number[];
  hlen?: readonly number[];
  elbow?: number | "down";
}
interface KAtk {
  from: KPose;
  mid?: KPose;
  to: KPose;
  og: readonly number[];
  mg?: number;
}
export interface KClass {
  zh: string;
  front: KPose;
  back: KPose;
  side: KPose;
  sideW?: KPose;
  backX?: KPose;
  atk?: KAtk;
  atkScythe?: KAtk;
  aim?: KPose;
}

export const CLASS_OF: Readonly<Record<string, string>> = { greatsword: "greatsword", spear: "polearm", scythe: "polearm", bow: "bow", crossbow: "gun", gun: "gun", staff: "staff" };
const SSH = 2;
/** QK-1c：拄劍、待機的雙手劍遠側暗袖子——暗度與上臂、前臂長度（肩到拳頭距離的倍數，> 0.5 才會往下垂出手肘）。 */
const GS_SLEEVE_DARK = 0.2;
const GS_SLEEVE_SAG = 0.75;
const SIDEA = 0.87;
const tailG = (T: number, hw: number, a: number, hy: number): number => T - (0.85 - hy - hw * Math.sin(a)) / Math.cos(a);
const tiltG = (mg: number): number => mg; // 手臂規則 E、A 的 tilt 都是 0

/** 雙手劈：從拄劍把劍提起來 → 舉到臉前上方 → 往前下方劈；朝東、朝西同一組（第 17 版）。 */
const GS_ATK: KAtk = { from: { hand: [11, -15.5], a: 0.8 }, mid: { hand: [13.4, -24.4], a: 0.45 }, to: { hand: [10.5, -12], a: 1.9, elbow: 1 }, og: [0, 6.8], mg: 1.2 };

/** 關鍵姿勢表（依目前的手臂規則算；手臂規則換了就重算）。 */
function buildKey(): Readonly<Record<string, KClass>> {
  const OH = fk(SHX(), -OUTA(), 0);
  const OH16 = fk(8.5, -ARM_SPREAD_SET.A.a, 0);
  const SHD = fk(SSH, -SIDEA, 0);
  const SHP = fk(SSH, -1.07, 0);
  const sideW = fk(SSH, -1.0, 0);
  return {
    greatsword: {
      zh: "拄劍：雙手疊握劍柄在胸前，劍垂直往下，劍尖點在兩腳之間",
      front: { hand: [-0.5, -13.4], a: Math.PI, og: [0, 3.2], short: "f" },
      back: { hand: [0.5, -13.4], a: Math.PI, og: [0, 3.2], short: "f" },
      side: { hand: [7.4, -15.8], a: Math.PI + 0.06, og: [0, 4], short: true },
      // 朝西照朝東的鏡像握法：近側左手握下面、遠側右手握上面（主手握在劍柄上段，劍的位置不變）
      sideW: { hand: [7.2, -19.8], a: Math.PI + 0.06, og: [0, 0], mg: 4, short: true },
      atk: GS_ATK,
    },
    polearm: {
      zh: "右手單手拄地、手臂打直往外、柄直立，左手垂下",
      front: { hand: [-OH[0], OH[1]], a: 0, grip: tiltG(-2.6 + OH[1] + 12.8), gripS: tiltG(-4.6 + OH[1] + 12.8), flipS: true, st: true },
      back: { hand: [OH[0], OH[1]], a: 0, grip: tiltG(-2.6 + OH[1] + 12.8), gripS: tiltG(-4.6 + OH[1] + 12.8), st: true },
      side: { hand: SHP, a: 0.06, grip: tailG(11, 0.9, 0.06, SHP[1]), gripS: tailG(9, 1, 0.06, SHP[1]), animOg: [0, -8], st: true },
      atk: { from: { hand: [2, -14], a: 1.25 }, to: { hand: [6, -17.5], a: Math.PI / 2 + 0.03 }, og: [0, -6] },
      atkScythe: { from: { hand: [7, -15], a: 0.45 }, to: { hand: [5, -17], a: 2.0 }, og: [0, -6] },
    },
    bow: {
      zh: "持弓待機：弓在胸口前、靠中線，左手握弓把、右手扣弦上的箭尾，箭朝前下；背面弓和兩手被身體擋住",
      front: { wh: "off", hand: [3, -11.5], s: [-1.1, -14.6], tilt: 0.72, nt: 1.9, ah: 4.2, a: 0 },
      back: { wh: "off", hand: [-3, -11.5], s: [1.1, -14.6], tilt: 0.72, nt: 1.9, ah: 4.2, a: 0 },
      side: { hand: [11.6, -12.6], a: Math.PI / 2 + 0.6, farX: 5.4 },
      aim: { hand: [16.6, -21.5], a: Math.PI / 2, farX: 6.4, nearX: -1.5, edir: [-1, -0.3] },
    },
    gun: {
      zh: "正面橫持在胸前、口朝右下；背面口從左腰外露出；側面持槍待命、口朝前上",
      front: { hand: [-3, -15], a: 1.87, og: [0, -6.8] },
      back: { hand: [3, -15], a: -1.87, og: [0, -6.8] },
      backX: { hand: [1, -15.5], a: 0, og: [0, -6.8], fore: [1.35, 0, 0.25, -0.3] },
      side: { hand: [6, -11], a: 0.9, og: [0, -5] },
      atk: { from: { hand: [6, -11], a: 0.9 }, to: { hand: [11, -20], a: Math.PI / 2, farX: 6.5, elbow: "down" }, og: [0, -5] },
    },
    staff: {
      zh: "單手握杖：手臂打直往外下方伸、杖身穿過拳頭；正面杖在畫面左、背面在畫面右；側面杖往前傾",
      front: { hand: [-OH[0], OH[1]], a: 0, grip: tiltG(-3.72 + (OH[1] - OH16[1])), st: true },
      back: { hand: [OH[0], OH[1]], a: 0, grip: tiltG(-3.72 + (OH[1] - OH16[1])), st: true },
      side: { hand: SHD, a: 0.2, aW: 0.2, grip: tailG(9, 1.1, 0.2, SHD[1]), gripW: tailG(9, 1.1, 0.2, SHD[1]), st: true },
      sideW: { hand: sideW, a: 0.2, mg: tailG(9, 1.1, 0.2, sideW[1]), needOff: true, st: true },
    },
  };
}
const KEYS = new Map<object, Readonly<Record<string, KClass>>>();
export function KEY(): Readonly<Record<string, KClass>> {
  const a = ARM();
  let k = KEYS.get(a);
  if (k === undefined) {
    k = buildKey();
    KEYS.set(a, k);
  }
  return k;
}

interface KeyRef {
  c: string;
  K: KClass;
  kind: string;
}
export function keyOf(gear: QUnit["gear"]): KeyRef | null {
  const q = qWeapon(gear.main_hand);
  if (!q) return null;
  const c = CLASS_OF[q.kind];
  if (!c) return null;
  if (c !== "staff" && gear.off_hand) return null; // 雙手武器副手有東西就改單手
  return { c, K: KEY()[c]!, kind: q.kind };
}
const backKey = (key: KeyRef | null): KPose | null => (key ? (key.kind === "crossbow" && key.K.backX ? key.K.backX : key.K.back) : null);
const ogLocal = (og: KPose["og"]): P2 | null => (og && og !== "string" ? [og[0] ?? 0, og[1] ?? 0] : og === "string" ? [0, BOW_EY] : null);
const armTo = (sx: number, hand: readonly number[], out: number | "down"): { sA: number; eA: number } => ik(sx, hand, out);

/** 持單手武器的手臂往外張開的角度；空手、拳套用最小可見縫 ea。 */
const outOf = (gear: QUnit["gear"]): number => {
  const q = qWeapon(gear.main_hand);
  return gear.main_hand && q && q.kind !== "gauntlet" ? OUTA() : SEAMF() ? (ARM().ea ?? 0) : 0;
};
const armK = (sx: number, k: KPose, out: number | "down"): { sA: number; eA: number } => (k.st ? { sA: Math.atan2(-((k.hand[0] ?? 0) - sx), (k.hand[1] ?? 0) + 20), eA: 0 } : armTo(sx, k.hand, out));
const sxOf = (gear: QUnit["gear"]): number => (outOf(gear) ? SHX() : 8.5);
const robeX = (gear: QUnit["gear"]): number => (ARM().robe && gear.body?.kind === "robe" ? ARM().robe : 0);
const SWORDISH = ["sword", "arcane_blade", "saber"];
const swOn = (gear: QUnit["gear"]): boolean => SWORDISH.includes(qWeapon(gear.main_hand)?.kind ?? "");
const swOff = (p: P2, s: number, gear: QUnit["gear"]): P2 => (ARM().sw && swOn(gear) ? [p[0] + s * ARM().sw, p[1]] : p);
const holdA = (gear: QUnit["gear"]): number => (outOf(gear) ? outOf(gear) + ARM().hold + robeX(gear) : 0);
const stK = (sx: number, k: KPose, out: number, gear: QUnit["gear"]): { sA: number; eA: number } => {
  const r = armK(sx, k, out);
  if (k.st && robeX(gear)) r.sA += (sx > 0 ? -1 : 1) * robeX(gear);
  return r;
};
const stMg = (sx: number, k: KPose, k0: { sA: number; eA: number }, mg: number, gear: QUnit["gear"]): number => (k.st && robeX(gear) ? mg + (fk(sx, k0.sA, k0.eA)[1] - (k.hand[1] ?? 0)) / Math.cos(k.a) : mg);
const holdOf = (it: QItem | undefined, which: "side" | "front"): number => {
  const q = qWeapon(it);
  return q ? q.W.hold[which] : which === "side" ? 0.75 : -0.25;
};
/** 弓手預設背箭袋。 */
const backOf = (gear: QUnit["gear"]): QItem | null => gear.back ?? (qWeapon(gear.main_hand)?.kind === "bow" ? { slot: "back", kind: "quiver", material: "leather" } : null);

/** 四指握法的武器（QK-1 第 0.3 節第 2 點單手劍；QK-1b 加匕首、成對武器，鞭不改）→ 握柄寬、顏色。 */
const GRIP: Readonly<Record<string, readonly [number, string]>> = { sword: [2, "#4a3020"], arcane_blade: [2, "#4a3020"], saber: [2, "#3a2a1a"], dagger: [1.6, "#4a3020"], paired: [1.6, "#4a3020"] };
const gripOf = (gear: QUnit["gear"]): readonly [number, string] | null => GRIP[qWeapon(gear.main_hand)?.kind ?? ""] ?? null;
/** 握柄尾端從拳頭下緣穿出（QK-1b 第 4 項）：武器座標 (0, 1)～(0, 3.9)，拳頭半徑 2.4。 */
const GRIP_TAIL = 3.9;

/**
 * 四指握法：四指橫過握把，握柄從拳頭上下穿出（柄尾從拳頭下緣露出來）。
 * wpos＝武器原點（正面、背面單手劍往外偏 sw）；clipR＝四指只畫在拳頭輪廓裡（伸到身前的遠側手）。
 */
function swordGrip(ctx: Ctx, unit: QUnit, hand: P2, a: number, wpos: P2 = hand, clipR = 0): void {
  const g = gripOf(unit.gear);
  if (!g) return;
  ctx.save();
  ctx.translate(wpos[0], wpos[1]);
  ctx.rotate(a);
  fill(ctx, g[1], () => ctx.rect(-g[0] / 2, 1, g[0], GRIP_TAIL - 1));
  ctx.restore();
  ctx.save();
  if (clipR) {
    ctx.beginPath();
    ctx.arc(hand[0], hand[1], clipR, 0, TAU);
    ctx.clip();
  }
  wrap(ctx, unit, hand, a);
  ctx.restore();
}

// ---------- 側面的兩隻手：朝東近側＝主手（右），朝西相反（座標一律朝東畫，外層鏡像）----------
interface SideArm {
  who: "main" | "off";
  sx: number;
  sA: number;
  eA: number;
  len?: readonly number[] | null;
  item?: Hand | null;
  shield?: boolean;
  front?: boolean;
  /** 肩點往下移（QK-1b：朝西遠側握長柄的上臂壓低）。 */
  dy?: number;
}
interface SidePlan {
  wh: "main" | "off";
  sA: number;
  eA: number;
  a: number;
  og: KPose["og"];
  mg: number;
  short: boolean | "f";
  layer: string | null;
  split: boolean;
  farX?: number | undefined;
  olen: readonly number[] | null;
  hlen: readonly number[] | null;
  dy?: number;
  h: P2;
  ol: P2 | null;
  pull: number | null;
  released: boolean;
  near: SideArm;
  far: SideArm;
  bowHand: boolean;
  nearLate: boolean;
  late: boolean;
  nearDone: boolean;
}

/** 側面走路（擺髖、沒有出招姿勢）。 */
const walkingSide = (anim: boolean): boolean => !anim && typeof S.POSE?.atk !== "number" && (pz("hipN") !== 0 || pz("hipF") !== 0 || pz("kneeN") !== 0 || pz("kneeF") !== 0);

function sidePlan(unit: QUnit, key: KeyRef | null, anim: boolean, W: boolean): SidePlan {
  const { gear } = unit;
  // QK-5（QK-1 驗收）：雙手劍走路不拄劍（劍斜穿小腿）：走路（側面擺髖）時改成「提劍」那一格（atk 0：雙手握柄、劍往前上斜）
  const walking = walkingSide(anim);
  const gsWalk = walking && key?.c === "greatsword";
  const atkOn = typeof S.POSE?.atk === "number" || gsWalk;
  const bowK = !!key && key.c === "bow";
  const SX: Record<"main" | "off", number> = atkOn ? { main: W ? 3 : 4.5, off: W ? 4.5 : 3 } : bowK ? { main: SSH, off: W ? 4.5 : 3 } : { main: SSH, off: SSH };
  const nearWho: "main" | "off" = W ? "off" : "main";
  let P: Omit<SidePlan, "h" | "ol" | "pull" | "released" | "near" | "far" | "bowHand" | "nearLate" | "late" | "nearDone">;
  let bowT = 0;
  if (key && !anim) {
    const ks = W && key.K.sideW && !(key.K.sideW.needOff && !gear.off_hand) ? key.K.sideW : key.K.side;
    const bow = key.c === "bow";
    let hand: readonly number[] = W && ks.hw ? ks.hw : ks.hand;
    let a = W && ks.aW != null ? ks.aW : ks.a;
    let og: KPose["og"] = ks.og ?? null;
    let mg = ks.mg ?? (key.kind === "scythe" && ks.gripS != null ? ks.gripS : W && ks.gripW != null ? ks.gripW : ks.grip) ?? 0;
    let short: boolean | "f" = !!ks.short;
    let layer: string | null = ks.layer ?? null;
    let elbow: number | "down" = -1;
    let olen: readonly number[] | null = ks.olen ?? null;
    let hlen: readonly number[] | null = null;
    if (ks.farX && !W) SX.off = ks.farX;
    const AK = (key.kind === "scythe" && key.K.atkScythe) || key.K.atk;
    if (AK && atkOn) {
      const fr = AK.from;
      const t = gsWalk ? 0 : clamp01(S.POSE!.atk ?? 0);
      const [P0, P1, tt] = AK.mid ? (t < 0.5 ? [fr, AK.mid, t * 2] : [AK.mid, AK.to, t * 2 - 1]) : [fr, AK.to, t];
      const L = (p: number, q: number): number => p + (q - p) * tt;
      hand = [L(P0.hand[0] ?? 0, P1.hand[0] ?? 0), L(P0.hand[1] ?? 0, P1.hand[1] ?? 0)];
      a = L(P0.a, P1.a);
      og = AK.og;
      mg = AK.mg ?? 0;
      short = false;
      elbow = tt > 0.5 ? (P1.elbow ?? -1) : (P0.elbow ?? -1);
      if (P0.farX || P1.farX) SX.off = L(P0.farX ?? SX.off, P1.farX ?? SX.off);
      if (P0.og) og = tt < 0.5 ? P0.og : AK.og;
      olen = tt < 0.5 ? (P0.olen ?? null) : null;
      layer = tt < 0.5 && P0.layer ? P0.layer : Math.sin(a) < -0.3 ? "head" : null;
    }
    if (bow) {
      const t = clamp01(pz("bowAim"));
      const A2 = key.K.aim!;
      const th = t <= 0.4 ? t : Math.min(1, 0.4 + (t - 0.4) * 1.5);
      if (t) {
        hand = [(hand[0] ?? 0) + ((A2.hand[0] ?? 0) - (hand[0] ?? 0)) * th, (hand[1] ?? 0) + ((A2.hand[1] ?? 0) - (hand[1] ?? 0)) * th];
        a += (A2.a - a) * th;
        if (A2.farX) SX.off += (A2.farX - SX.off) * th;
        if (A2.nearX != null) SX.main += (A2.nearX - SX.main) * t;
      }
      og = "string";
      layer = W ? "head" : "mid";
      bowT = t;
    }
    const wh: "main" | "off" = bow ? "off" : "main";
    hlen = ks.hlen && !pz("bowAim") ? ks.hlen : null;
    let k: { sA: number; eA: number };
    let dy = 0;
    if (ks.st && !atkOn) {
      k = { sA: Math.atan2(-((hand[0] ?? 0) - SX[wh]), (hand[1] ?? 0) + 20), eA: 0 };
      // QK-1 第 0.3 節第 3 點：朝西遠側伸去握長柄的手，肩點往後一點、上臂低一點，和下巴之間露出縫；拳頭位置不動
      // QK-1b：「杖＋書」朝西走 sideW 姿勢，不套肩點後移（QK-1 檢查小修 1）
      if (W && wh === "main" && (key.c === "polearm" || (key.c === "staff" && !gear.off_hand))) {
        const h0 = fk(SX[wh], k.sA, 0);
        SX[wh] = SSH - WEST_FAR_BACK;
        dy = WEST_FAR_DROP;
        const ex = h0[0] - SX[wh];
        const ey = h0[1] + 20 - dy;
        const r = Math.hypot(ex, ey);
        hlen = [(UA * r) / (UA + FA), (FA * r) / (UA + FA)];
        k = { sA: Math.atan2(-ex, ey), eA: 0 };
      }
    } else k = ik(SX[wh], hand, elbow, hlen);
    // QK-5（QK-1 驗收）：法杖、拄地長柄走路時手臂擺幅減半、杖身只跟著轉 0.3（杖不甩出跳動的角度）；雙手劍提劍走只擺 0.25
    const pole = walking && (key.c === "staff" || key.c === "polearm");
    const sw = pz("arm") * (gsWalk ? 0.25 : pole ? 0.5 : 1);
    P = { wh, sA: k.sA + sw, eA: k.eA, a: a + pz("arm") * (gsWalk ? 0.25 : pole ? 0.3 : 1) + pz("dw"), og, mg, short, layer, split: true, farX: ks.farX, olen, hlen, dy };
  } else {
    // 6M／6N 片段或沒有關鍵姿勢的武器：主手臂角度 arm、武器角度 arm＋wpn；雙手武器出招時副手去握 og
    const gq = qWeapon(gear.main_hand);
    const empty = W && (!gear.main_hand || (gq?.kind === "gauntlet" && !anim));
    if (empty) SX.main = -4.5;
    const sA = empty ? pz("armR") * 0.6 - 0.1 : pz("arm");
    const eA = empty ? 0.15 : Math.min(0, sA * 0.35);
    const w = anim ? (S.POSE!.wpn as number) : holdOf(gear.main_hand, "side");
    const kc2 = key && key.c !== "bow" && key.c !== "staff" ? (key.K.side.animOg ?? key.K.side.og) : null;
    P = { wh: "main", sA, eA, a: sA + w, og: kc2 && anim ? kc2 : null, mg: key?.K.side.mg ?? 0, short: false, layer: null, split: false, olen: null, hlen: null };
  }
  const h0 = fk(SX[P.wh], P.sA, P.eA, P.hlen);
  const h: P2 = [h0[0], h0[1] + (P.dy ?? 0)];
  const who2: "main" | "off" = P.wh === "main" ? "off" : "main";
  const A: Partial<Record<"main" | "off", SideArm>> = { [P.wh]: { who: P.wh, sx: SX[P.wh], sA: P.sA, eA: P.eA, len: P.hlen, dy: P.dy ?? 0 } };
  let ol: P2 | null = null;
  let pull: number | null = null;
  let og = P.og;
  const released = og === "string" && pz("bowAim") > 0.9 && !(pz("pull") > 0.5); // 放箭那一格
  if (released) og = null;
  const hands = S.POSE?.hands;
  if (og) {
    const ol0: P2 = og === "string" ? [0, BOW_EY + (pz("pull") || 0)] : [og[0] ?? 0, og[1] ?? 0];
    const o = rot(P.a, [ol0[0], ol0[1] - P.mg]);
    const t: P2 = [h[0] + o[0], h[1] + o[1]];
    if (og === "string" && bowT >= 0.6) {
      // 拉弓：拉弦手的手肘往後抬到肩高，前臂往前到下巴下；弦拉到手實際的位置
      const k = elbowTo(SX[who2], key!.K.aim!.edir!, t);
      const ax = rot(P.a, [0, 1]);
      A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA };
      pull = Math.max(0, (k.h[0] - h[0]) * ax[0] + (k.h[1] - h[1]) * ax[1] - BOW_EY);
      ol = [0, BOW_EY + pull];
      if (hands) hands["offTwo"] = true;
    } else {
      const k = ik(SX[who2], t, -1, P.olen);
      if (k.ok) {
        A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA, len: P.olen };
        ol = ol0;
        if (hands) hands["offTwo"] = true;
      }
    }
  }
  if (!A[who2] && released) {
    const k = elbowTo(SX[who2], key!.K.aim!.edir!, h);
    A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA };
  }
  if (!A[who2]) {
    // 空出來的副手：成對武器拿第二把匕首；持盾的手在盾後面；拿書或垂著
    const paired = qWeapon(gear.main_hand)?.kind === "paired";
    if (paired) {
      const att = anim && S.POSE!.wpn !== undefined && !S.POSE!.idle;
      const k = ik(SX.off, att ? [10.2, -18.4] : [10.8, -19], -1);
      const da = att ? 0.55 : 0.75;
      A.off = { who: "off", sx: SX.off, sA: k.sA, eA: k.eA, item: (hand) => {
          offDagger(S.CTX!, gear.main_hand, hand, da - k.sA - k.eA);
          swordGrip(S.CTX!, unit, hand, da - k.sA - k.eA);
        } };
    } else if (isShield(gear.off_hand)) {
      const k = ik(SX.off, [8.6, -13.5 - pz("shieldUp")], -1);
      A.off = { who: "off", sx: SX.off, sA: k.sA, eA: k.eA, item: null, shield: true };
    } else if (offHeld(gear)) {
      // QK-8：副手手持物（法球、拂塵…）：朝西在近側、垂在身側拿著；朝東在遠側、身體後面，只露出身體外的部分
      const oh = offHeld(gear)!;
      const item = (hand: P2): void => mainWeapon(S.CTX!, oh, hand, holdOf(oh, "side"), "side");
      A.off = W ? { who: "off", sx: SX.off, sA: 0.12, eA: 0.05, item } : { who: "off", sx: -4.5, sA: pz("armL") * 0.6 - 0.1, eA: 0.15, item };
    } else if (pz("armF") && !gear.off_hand) {
      // 6N 片段的另一隻手手勢（掌心放出、法球施放…）：空著的另一隻手從肩線照 armF 伸出（同主手的肘角規則）
      const aF = pz("armF");
      A.off = { who: "off", sx: SSH, sA: aF, eA: Math.min(0, aF * 0.35), item: null };
    } else if (W) A.off = { who: "off", sx: SX.off, sA: gear.off_hand ? -0.15 : 0.12, eA: gear.off_hand ? 0.1 : 0.05, item: gear.off_hand ? (hand) => pdHeld(S.CTX!, gear.off_hand!, hand[0] + 1, true) : null };
    else if (gear.off_hand) A.off = { who: "off", sx: SSH, sA: 0, eA: 0, item: (hand) => pdHeld(S.CTX!, gear.off_hand!, hand[0] - (gear.body?.kind === "robe" ? 0 : 1.5), true) };
    else A.off = { who: "off", sx: -4.5, sA: pz("armL") * 0.6 - 0.1, eA: 0.15, item: null };
  }
  // QK-5：臂長加量 reach／reachF（只給空著的手；開場醒來半坐起撐地，Q 版手臂只到腰、原長撐不到地）
  const stretch = (X: SideArm | undefined, r: number): void => {
    if (X && r && !X.item && !(X.who === "main" && gear.main_hand)) X.len = [(X.len?.[0] ?? UA) * (1 + r), (X.len?.[1] ?? FA) * (1 + r)];
  };
  stretch(A.main, pz("reach"));
  stretch(A.off, pz("reachF"));
  const farWho: "main" | "off" = nearWho === "main" ? "off" : "main";
  const near = A[nearWho]!;
  const far = A[farWho]!;
  far.front = fk(far.sx, far.sA, far.eA, far.len ?? null)[0] > 4.6 && far.sx > 0;
  const bowHand = !!key && key.c === "bow" && !anim;
  const plan: SidePlan = { ...P, og, h, ol, pull, released, near, far, bowHand, nearLate: bowHand && !W && bowT >= 0.6, late: false, nearDone: false };
  if (!plan.layer) plan.layer = plan.wh === farWho && !far.front ? "back" : "front";
  return plan;
}
/** QK-1 第 0.3 節第 3 點：朝西遠側握長柄的手，肩點往後移多少（拳頭不動）。 */
const WEST_FAR_BACK = 1.4;
/** QK-1b：同一隻手的肩點再往下移多少（上臂壓低，和下巴之間露出縫）。 */
const WEST_FAR_DROP = 2.5;

/** 正面、背面的弓：弓座標 (x, y) → 畫面 x·U − y·F；線寬照畫面算（BOWM）。 */
function bowFace(ctx: Ctx, it: QItem | undefined, hand: P2, U: P2, F: P2, view: string, off: P2 | null = null): void {
  ctx.save();
  ctx.translate(hand[0], hand[1]);
  S.BOWM = getM(ctx);
  ctx.transform(U[0], U[1], -F[0], -F[1], 0, 0);
  QW["bow"]!.draw(ctx, it);
  const probe = S.POSE?.probe;
  if (probe) {
    const m = getM(ctx);
    const T = (x: number, y: number): P2 => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
    probe("bow", T(0, 0), T(0, -QW["bow"]!.len), view, T(off ? off[0] : 0, off ? off[1] : BOW_EY), m, "bow");
  }
  S.BOWM = null;
  ctx.restore();
}

/** 持弓待機（第 13 版）：弓在胸口前、靠中線；左手握弓把、右手扣弦上的箭尾。背面整組在身體之前畫（pre），被身體擋住。 */
function bowStill(ctx: Ctx, unit: QUnit, view: "front" | "back", pre = false): void {
  const k = KEY()["bow"]![view];
  const B = view === "back";
  const o = B ? -1 : 1;
  const ls = 8.5 * o;
  const ph = k.tilt ?? 0;
  if (B !== pre) return;
  const U: P2 = [-o * Math.sin(ph), Math.cos(ph)];
  const F: P2 = [o * Math.cos(ph), Math.sin(ph)];
  const sP = k.s!;
  const nt = k.nt!;
  const G: P2 = [(sP[0] ?? 0) + BOW_EY * F[0], (sP[1] ?? 0) + BOW_EY * F[1]];
  const N: P2 = [(sP[0] ?? 0) - nt * U[0], (sP[1] ?? 0) - nt * U[1]];
  const kl = ik(ls, G, o);
  const kr = ik(-ls, N, "down");
  const it = unit.gear.main_hand;
  const leftArm = (): void => void arm(ctx, unit, ls, kl.sA, kl.eA, 0, rec("off"));
  const rightArm = (): void => void arm(ctx, unit, -ls, kr.sA, kr.eA, 0, rec("main"));
  const bowArrow = (): void => {
    S.BOWP = { nock: false, noArrow: true };
    bowFace(ctx, it, G, U, F, view, [-nt, BOW_EY]);
    S.BOWP = null;
    mark("weapon");
    const dx = G[0] - N[0];
    const dy = G[1] - N[1];
    const dl = Math.hypot(dx, dy);
    const ux = dx / dl;
    const uy = dy / dl;
    const T: P2 = [G[0] + ux * k.ah!, G[1] + uy * k.ah!];
    ctx.strokeStyle = "#c8a070";
    ctx.lineWidth = 0.9;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(N[0] - ux, N[1] - uy);
    ctx.lineTo(T[0], T[1]);
    ctx.stroke();
    fill(ctx, "#c3ccd6", () => {
      ctx.moveTo(T[0] + ux * 2.4, T[1] + uy * 2.4);
      ctx.lineTo(T[0] - uy * 1.2, T[1] + ux * 1.2);
      ctx.lineTo(T[0] + uy * 1.2, T[1] - ux * 1.2);
      ctx.closePath();
    });
  };
  if (B) {
    // 背面：弓、箭只畫在身體輪廓裡（全部被身體擋住），手臂只畫肩膀那段和身體輪廓裡的部分
    const bodyPath = (): void => {
      ctx.beginPath();
      ctx.rect(-7.4, -21, 14.8, 13.4);
    };
    ctx.save();
    bodyPath();
    ctx.clip();
    bowArrow();
    ctx.restore();
    ctx.save();
    bodyPath();
    ctx.rect(-40, -60, 80, 43.5);
    ctx.clip();
    leftArm();
    rightArm();
    ctx.restore();
    return;
  }
  leftArm();
  bowArrow();
  rightArm();
}

/** 握住直的柄（法杖、拄地長柄、劍柄）：一條橫過柄的四指（和手同色、稍暗），柄從拳頭上下穿出。dk＝遠側手再加深。 */
function wrap(ctx: Ctx, unit: QUnit, hand: P2, a: number, dk = 0): void {
  const { look, gear } = unit;
  const hc = gear.hands && gear.hands.kind !== "bracers" ? colors(gear.hands)[0] : look.skin;
  ctx.save();
  ctx.translate(hand[0], hand[1]);
  ctx.rotate(a);
  fill(ctx, mix(hc, "#000000", 0.05 + dk), () => rr(ctx, -2.35, -1.25, 4.7, 2.5, 1.1));
  ctx.strokeStyle = mix(hc, "#000000", 0.4);
  ctx.lineWidth = 0.35;
  ctx.beginPath();
  ctx.moveTo(-1.9, 0);
  ctx.lineTo(1.9, 0);
  ctx.stroke();
  ctx.restore();
}

// ---------- 整隻：view = front | side | back ----------
// 圖層（由後到前，部件四方向清單.md）：
//   正面：披風（暗）→ 背掛 → 尾巴 → 腿 → 身體 → 紋章、頸飾、背帶、腰掛 → 披風扣 → 副手臂＋副手 → 頭 → 武器 → 主手臂
//   側面：披風 → 背掛 → 尾巴 → 遠側手臂 → 遠側腰掛 → 腿 → 身體 → 紋章、頸飾、背帶、近側腰掛 → 盾（朝東）→ 頭 → 武器 → 近側手臂
//   背面：武器與兩隻手臂（在身體前方＝畫面後）→ 副手物品 → 腿 → 身體 → 腰掛 → 披風 → 背掛 → 尾巴 → 頭
function drawBody(ctx: Ctx, unit: QUnit, view: QView, npc: NpcFrame): void {
  const { look, gear } = unit;
  const F = view === "front";
  const B = view === "back";
  const SD = view === "side";
  S.CTX = ctx;
  const side = SD ? 1 : 0;
  const W = SD && S.WEST;
  const key = keyOf(gear);
  const anim = !!S.POSE && typeof S.POSE.wpn === "number";
  const bk = backOf(gear);
  const mq = qWeapon(gear.main_hand);
  const armed = !!(gear.main_hand && mq && mq.kind !== "gauntlet");
  const armor = ["plate", "mail"].includes(gear.body?.kind ?? "");
  S.FILLARM = !SD && !key && SEAMF() && !armed;
  S.SHEDGE = F && SEAMF() && armor;
  S.SEAMIN = !SD && !key && !(B && isShield(gear.off_hand)) && SEAMF() && armor;
  S.SEAM = SD || !!key || (B && isShield(gear.off_hand)) || S.SEAMIN;
  ctx.save();
  raceBuild(ctx, look);
  if (look.frame === "slim") ctx.scale(0.92, 1.02);
  else if (look.frame === "broad") ctx.scale(1.08, 0.98);
  ctx.translate(0, pz("bob"));
  if (SD) rotAt(ctx, 0, -9, pz("lean"));
  const fb = !SD && FB ? FB : null;
  const fbApi = fb ? fbApiOf(ctx, unit, fb.view) : null;
  const FBL = (layer: FbLayer): void => {
    if (fb && fbApi) drawFbLayer(fbApi, fb.frame, layer);
  };
  // QK-5 背面前傾：腰以上以髖 (0,−9) 為軸往上拉長一點（往遠處傾、相機在後上方時頭往畫面上方移），腿另外抵銷
  const leanK = fb && B ? 1 + 0.5 * (fb.frame.lean ?? 0) : 1;
  if (leanK !== 1) {
    ctx.translate(0, -9);
    ctx.scale(1, leanK);
    ctx.translate(0, 9);
  }
  npcBeforeQ(ctx, npc, view); // QK-8：人形敵人、NPC 的新部件在本體後面那層（背葫蘆、木偶箱、郵袋）
  if (gear.cloak && F) cloakFront(ctx, gear.cloak);
  if (F) backItem(ctx, bk, "front", "behind");
  if (gear.cloak && SD) {
    cloakSide(ctx, gear.cloak);
    mark("cloak");
  }
  if (SD) backItem(ctx, bk, "side", "behind");
  if (!B) raceTail(ctx, look, F ? "front" : "side", side);
  FBL("under");
  // ---- 背面：武器與手臂在身體前方（先畫，被身體擋住）----
  if (B && !fb) drawBackPre(ctx, unit, key);
  // ---- 側面：兩隻手的位置、武器在哪隻手、各畫在哪一層 ----
  const SP = SD ? sidePlan(unit, key, anim, W) : null;
  const sideArm = (A: SideArm, clip: boolean | "hand" | "chest" | "sleeve"): void => {
    ctx.save();
    if (clip) {
      ctx.beginPath();
      if (clip === "hand") {
        const hh = fk(A.sx, A.sA, A.eA, A.len ?? null);
        ctx.arc(hh[0], hh[1] + (A.dy ?? 0), 2.6, 0, TAU);
      } else if (clip === "chest") ctx.rect(-80, -80, 160, 120); // 橫過胸前：整隻畫（在身體前面）
      else if (clip === "sleeve") ctx.rect(A.sx, -80, 80, 120); // QK-1c：拄劍遠側袖子從肩點起畫
      else ctx.rect(3.2, -80, 80, 120);
      ctx.clip();
    }
    if (clip) {
      S.FAR = clip === "sleeve" ? GS_SLEEVE_DARK : 0.12;
      S.FARH = 0;
    }
    S.NOPAD = A === SP!.far;
    if (A.dy) ctx.translate(0, A.dy);
    const r = rec(A.who);
    const inHand: Hand | null = A.item
      ? (hand, c): void => {
          A.item!(hand, c);
          if (r) r(hand, c);
        }
      : r;
    HAND_LIFT = A.shield ? SHIELD_HAND_LIFT : 0;
    arm(ctx, unit, A.sx, A.sA, A.eA, side, inHand, false, A.len ?? null);
    HAND_LIFT = 0;
    S.FAR = 0;
    S.FARH = 0;
    S.NOPAD = false;
    ctx.restore();
  };
  /**
   * QK-1 第 0.3 節第 1 點（QK-1b 重做）：雙手劍遠側（上面那隻）拳頭要接自己暗一階的前臂（同成對武器）。
   * 遠側拳頭在近側手臂「下方」（出招 atk：提劍、舉劍、劈）→ 遠側手臂橫過胸前，整隻畫在身體上、近側手臂之下（gsChest）；
   * 在「上方」（拄劍、待機）→ 近側手臂畫好後，從肩到拳頭補一段打直的暗袖子，蓋在近側上臂上緣（gsFarSleeve）。
   */
  const gsFar = (sp: SidePlan): "chest" | "sleeve" | null => {
    if (key?.c !== "greatsword" || !sp.far.front || !sp.ol) return null;
    const N = sp.near;
    const b = fk(N.sx, N.sA, N.eA, N.len ?? null);
    const f = fk(sp.far.sx, sp.far.sA, sp.far.eA, sp.far.len ?? null);
    // 近側手臂（肩 → 拳頭）的哪一邊：外積 < 0 ＝畫面上方
    const cr = (b[0] - N.sx) * (f[1] + 20) - (b[1] + 20) * (f[0] - N.sx);
    return cr < 0 ? "sleeve" : "chest";
  };
  const gsFarSleeve = (sp: SidePlan): void => {
    // QK-1c（美術 PM 決定 1）：從肩點往下垂、再折回拳頭，看得出上臂＋前臂；暗度 0.2
    const F0 = sp.far;
    const fh = fk(F0.sx, F0.sA, F0.eA, F0.len ?? null);
    const r = Math.hypot(fh[0] - F0.sx, fh[1] + 20);
    const len = [GS_SLEEVE_SAG * r, GS_SLEEVE_SAG * r] as const;
    const k = ik(F0.sx, fh, "down", len);
    sideArm({ ...F0, item: null, sA: k.sA, eA: k.eA, len }, "sleeve");
  };
  const sideWeapon = (): void => {
    const sp = SP!;
    if (key && key.c === "bow") S.BOWP = { pull: sp.pull, nock: !sp.released };
    mainWeapon(ctx, gear.main_hand, sp.h, sp.a, "side", sp.short, sp.ol, sp.mg);
    S.BOWP = null;
    mark("weapon");
    if (key && !anim && typeof S.POSE?.atk !== "number" && !(walkingSide(anim) && key.c === "greatsword") && (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword"))) {
      // 雙手劍、杖、拄地長柄：四指橫過柄，柄從拳頭上下穿出。伸到身前的遠側手只畫在拳頭輪廓裡
      const one = (pos: P2, who: "main" | "off"): void => {
        if (!(sp.far.who === who && sp.far.front)) {
          wrap(ctx, unit, pos, sp.a);
          return;
        }
        ctx.save();
        ctx.beginPath();
        ctx.arc(pos[0], pos[1], 2.4, 0, TAU);
        ctx.clip();
        wrap(ctx, unit, pos, sp.a);
        ctx.restore();
        if (sp.nearDone && sp.near.who !== sp.wh && !sp.ol) {
          const N = sp.near;
          ctx.save();
          ctx.beginPath();
          ctx.arc(pos[0], pos[1], 2.9, 0, TAU);
          ctx.clip();
          arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null);
          ctx.restore();
        }
      };
      one(sp.h, sp.wh);
      if (sp.ol && key.c.startsWith("greatsword")) {
        const o = rot(sp.a, [sp.ol[0], sp.ol[1] - sp.mg]);
        one([sp.h[0] + o[0], sp.h[1] + o[1]], sp.wh === "main" ? "off" : "main");
      }
    }
  };
  if (SP) {
    if (!SP.far.front) sideArm(SP.far, false);
    if (SP.layer === "back") {
      sideWeapon();
      if (!SP.split) sideSwordGrip(ctx, unit, SP, false);
    }
  }
  if (SD) waistItem(ctx, gear.waist, "side", "behind");
  // QK-5：蹲低（bob > 0）時腳留在地上：腿往上抵銷下沉，大腿收到身體後面（腿短，照搬下沉會讓腳陷進地面）
  const sink = Math.max(0, pz("bob"));
  const legFix = leanK !== 1 || sink > 0;
  if (legFix) ctx.save();
  if (sink > 0) ctx.translate(0, -sink);
  if (leanK !== 1) {
    ctx.translate(0, -9);
    ctx.scale(1, 1 / leanK);
    ctx.translate(0, 9);
  }
  leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side, view);
  leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side, view);
  if (legFix) ctx.restore();
  if (SP && gear.main_hand)
    S.NOBUCKLE =
      (mq?.kind === "gauntlet" && !anim) ||
      [SP.near, SP.far].some((N) => {
        const nh = fk(N.sx, N.sA, N.eA, N.len ?? null);
        return nh[0] > 1.5 && nh[0] < 9.5 && nh[1] > -13 && nh[1] < -4.5;
      });
  body(ctx, gear.body, look, side, B);
  mark("body");
  S.NOBUCKLE = false;
  const v: QView = F ? "front" : B ? "back" : "side";
  drawTorsoForms(ctx, gear, v); // QK-3：只畫在軀幹上的新部件（獵裝口袋、肋骨）
  drawFreeForms(ctx, gear, v); // QK-3：不蓋手臂的新部件（獵裝下襬、腿甲裙、圍裙）
  crest(ctx, gear.body, v);
  neckItem(ctx, gear.neck, v);
  waistItem(ctx, gear.waist, v, "over");
  if (!B) backItem(ctx, bk, F ? "front" : "side", "over");
  if (B && !fb) drawBackPost(ctx, unit, key);
  if (B && isShield(gear.off_hand) && !fb) shieldArmBack(ctx, unit);
  FBL("over");
  if (SP) {
    cloakClasp(ctx, gear.cloak, true);
    if (!W && isShield(gear.off_hand)) {
      if (SP.far.shield) sideArm(SP.far, true);
      shieldSide(ctx, gear.off_hand!);
    }
  }
  if (B) {
    drawTopForms(ctx, gear, "back"); // QK-3：背面的最上層部件在披風之前（背面披風在最上層，只有頭在它上面）
    if (gear.cloak) {
      cloakBack(ctx, gear.cloak);
      mark("cloak");
    }
    backItem(ctx, bk, "back", "over");
    raceTail(ctx, look, "back", 0);
  }
  if (F && gear.cloak) cloakClasp(ctx, gear.cloak, false);
  const twoF = F && key && (key.K.front.og || key.K.front.wh === "off");
  if (F && !twoF && !fb) drawFrontOff(ctx, unit, key);
  if (SP && SP.split) {
    // 關鍵姿勢：兩隻手臂都在頭之前畫，武器畫在兩隻手上面
    SP.late = W && !!SP.near.item && SP.layer === "front";
    const gf = gsFar(SP);
    if (SP.far.front) sideArm(SP.far, gf === "chest" ? "chest" : true);
    if (SP.layer === "mid") sideWeapon();
    if (!SP.late && !SP.nearLate) {
      sideArm(SP.near, false);
      SP.nearDone = true;
      if (gf === "sleeve") gsFarSleeve(SP);
    }
    if (SP.layer === "head") sideWeapon();
    if (W && SP.bowHand && SP.far.front) sideArm(SP.far, "hand"); // 朝西拉弦手在遠側：弦和箭桿畫好後再補畫手
    if (W && SP.bowHand && SP.far.front) {
      const N = SP.near;
      const nh = fk(N.sx, N.sA, N.eA, N.len ?? null);
      ctx.save();
      ctx.beginPath();
      ctx.rect(-80, -120, 160, 200);
      ctx.arc(nh[0], nh[1], 3, 0, TAU);
      ctx.clip("evenodd");
      ctx.beginPath();
      ctx.rect(-80, -120, 80 + nh[0] - 1.6, 200);
      ctx.clip();
      arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null);
      ctx.restore();
    }
  } else if (SP) {
    if (SP.layer === "head") sideWeapon();
    if (SP.far.front && SP.layer !== "front" && !SP.far.shield) sideArm(SP.far, true);
  }
  mark("head");
  ctx.save();
  rotAt(ctx, 0, -29, SD ? pz("lean") * 0.3 : 0);
  if (isCowl(gear.head) && !B) cowl(ctx, gear.head!, v); // QK-3 斗篷帽披領：正面、側面在頭下面（臉蓋在披領上）
  drawQHead(ctx, look, v, side, gear.head);
  raceEars(ctx, look, v, side, gear.head, "under");
  const hc = headgearClip(ctx, gear.head, v); // QK-3：毛帽側面不畫皮帽伸出臉前的帽舌
  raceHat(ctx, look, gear.head, (it) => drawQHeadgear(ctx, it, v));
  if (hc) ctx.restore();
  drawHeadFormTop(ctx, gear.head, v); // QK-3：毛帽的毛邊與護耳
  raceEars(ctx, look, v, side, gear.head, "over");
  raceHorns(ctx, look, v);
  if (isCowl(gear.head) && B) cowl(ctx, gear.head!, "back"); // 背面：披領上緣蓋到兜帽下緣
  ctx.restore();
  if (fb) FBL("top");
  else if (F && key && key.c === "bow") bowStill(ctx, unit, "front");
  else if (F && key) drawFrontKey(ctx, unit, key);
  else if (F) {
    const rm = rec("main");
    const oF = holdA(gear);
    ctx.save();
    ctx.translate(0, pz("armL"));
    arm(ctx, unit, -sxOf(gear), oF, 0, 0, (hand, c) => {
      const a = holdOf(gear.main_hand, "front") - oF - ARM().swa;
      mainWeapon(ctx, gear.main_hand, swOff(hand, -1, gear), a, "front");
      swordGrip(ctx, unit, hand, a, swOff(hand, -1, gear));
      if (rm) rm(hand, c);
    });
    ctx.restore();
  } else if (SP && SP.split) {
    if (SP.layer === "front") sideWeapon();
    if (SP.late || SP.nearLate) sideArm(SP.near, false);
  } else if (SP) {
    // 武器畫在握著它的那隻手上面
    const inNear = SP.wh === (W ? "off" : "main");
    if (SP.layer === "front") {
      if (SP.far.front && !SP.far.shield) sideArm(SP.far, true);
      if (inNear) {
        sideArm(SP.near, false);
        sideWeapon();
        sideSwordGrip(ctx, unit, SP, false);
      } else {
        sideWeapon();
        sideSwordGrip(ctx, unit, SP, true);
        sideArm(SP.near, false);
      }
    } else sideArm(SP.near, false);
    if (W && isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand!);
  }
  if (!B) drawTopForms(ctx, gear, v); // QK-3：最上層部件（護頸、短披肩、吊牌符牌）挖掉頭、蓋在整隻上面（同樣張 qGearExtra 的 top 層）
  npcAfterQ(ctx, npc, view); // QK-8：新部件在本體前面那層（圍裙、斗笠、頭帶、黃符…）＋劍穗、傀儡線、白紗
  ctx.restore();
  S.SEAM = false;
  S.SEAMIN = false;
  S.SHEDGE = false;
  S.FILLARM = false;
  S.FREEARM = false;
}

/** 側面單手劍：四指橫過握把（遠側手只畫在拳頭裡、暗一階）。 */
function sideSwordGrip(ctx: Ctx, unit: QUnit, SP: SidePlan, farFront: boolean): void {
  swordGrip(ctx, unit, SP.h, SP.a, SP.h, farFront && SP.far.who === SP.wh ? 2.4 : 0);
}

/** 背面：拿在身體前方的東西（雙手武器、弓、杖）連手一起先畫，被身體擋住。 */
function drawBackPre(ctx: Ctx, unit: QUnit, key: KeyRef | null): void {
  const { gear } = unit;
  const kb = backKey(key);
  if (kb && kb.og) {
    // 持武器的手先定位置，另一隻手去握第二握點；武器先畫、兩隻手臂蓋在上面
    const who = kb.wh ?? "main";
    const sx = who === "main" ? 8.5 : -8.5;
    const k0 = armTo(sx, kb.hand, sx > 0 ? 1 : -1);
    const h = fk(sx, k0.sA, k0.eA);
    const ol = ogLocal(kb.og)!;
    const M = kb.fore ?? null;
    const o: P2 = M ? [(M[0] ?? 0) * ol[0] + (M[2] ?? 0) * ol[1], (M[1] ?? 0) * ol[0] + (M[3] ?? 0) * ol[1]] : rot(kb.a, ol);
    const io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx > 0 ? -1 : 1);
    S.BOWP = { nock: true };
    mainWeapon(ctx, gear.main_hand, h, kb.a, "back", kb.short ?? false, ol, 0, M);
    S.BOWP = null;
    mark("weapon");
    arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main"));
    arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
  } else {
    if (key && key.c === "bow") bowStill(ctx, unit, "back", true);
    if (key && kb && (key.c === "staff" || key.c === "polearm")) {
      // 握杖的手臂打直往外下方，杖直立在身體外側；杖在身體之前畫，手臂在身體之後畫、蓋在杖上
      const k0 = stK(SHX(), kb, 1, gear);
      const h = fk(SHX(), k0.sA, k0.eA);
      const mgB = stMg(SHX(), kb, k0, (key.kind === "scythe" && kb.gripS != null ? kb.gripS : kb.grip) ?? 0, gear);
      const po = ARM().po;
      mainWeapon(ctx, gear.main_hand, po ? [h[0] + po, h[1]] : h, kb.a, "back", false, null, mgB);
      mark("weapon");
    }
    if (gear.main_hand && !(key && (key.c === "staff" || key.c === "bow" || key.c === "polearm"))) {
      // 背面單手武器整把先畫在身體後面，只露出身體輪廓外面的刃；手垂在身側之後再畫，拳頭上只補畫握柄
      ctx.save();
      ctx.translate(0, pz("armR"));
      mainWeapon(ctx, gear.main_hand, swOff(fk(sxOf(gear), -holdA(gear), 0), 1, gear), -holdOf(gear.main_hand, "front") + ARM().swa, "back");
      ctx.restore();
      mark("weapon");
    }
  }
  mark("arms");
  if (isShield(gear.off_hand)) {
    const sh = fk(-SHX(), OUTA(), 0);
    const oh = gear.off_hand!;
    shieldBack(ctx, oh, sh[0] + 1, sh[1] + (oh.kind === "shield_round" ? 11.8 : isTowerLike(oh) ? 11.5 : 11));
    mark("shield");
  }
}

/** 背面：垂在身側、看得到的手（法杖在畫面右、弓、空手、單手武器、書）。 */
function drawBackPost(ctx: Ctx, unit: QUnit, key: KeyRef | null): void {
  const { gear } = unit;
  const kb = backKey(key);
  const paired = qWeapon(gear.main_hand)?.kind === "paired";
  if (key && key.c === "bow") bowStill(ctx, unit, "back");
  else if (key && kb && (key.c === "staff" || key.c === "polearm")) {
    const k0 = stK(SHX(), kb, 1, gear);
    arm(ctx, unit, SHX(), k0.sA, k0.eA, 0, rec("main"));
  } else if (!(kb && kb.og)) {
    // 空手或單手武器：右手垂在身側（畫面右），握柄從拳頭上穿過
    const rm = rec("main");
    ctx.save();
    ctx.translate(0, pz("armR"));
    const guard = swOn(gear);
    const oB = holdA(gear);
    const a = -holdOf(gear.main_hand, "front") + oB + ARM().swa;
    arm(
      ctx,
      unit,
      sxOf(gear),
      -oB,
      0,
      0,
      gear.main_hand
        ? (hand, c): void => {
            c.save();
            c.beginPath();
            c.arc(hand[0], hand[1], 2.6, 0, TAU);
            if (guard) {
              c.save();
              c.translate(hand[0], hand[1]);
              c.translate(swOn(gear) ? ARM().sw : 0, 0);
              c.rotate(a);
              c.rect(-4.8, -4.6, 9.6, 3.2);
              c.restore();
            }
            c.clip();
            mainWeapon(ctx, gear.main_hand, swOff(hand, 1, gear), a, "back");
            c.restore();
            swordGrip(ctx, unit, hand, a, swOff(hand, 1, gear));
            if (rm) rm(hand, c);
          }
        : rm,
    );
    ctx.restore();
  }
  // 左手：拿書的手打直往外下方，書蓋住手的大半（只露一點拳頭邊緣），在身體前方被身體擋住一部分
  const OHB = offHeld(gear);
  if (gear.off_hand && !isShield(gear.off_hand) && !OHB) {
    ctx.save();
    ctx.translate(0, pz("armL"));
    S.TINT = S.POSE?.tintOff ?? null;
    const bookA = OUTA() + robeX(gear);
    arm(ctx, unit, -SHX(), bookA, 0, 0, rec("off"));
    S.TINT = null;
    const bh = fk(-SHX(), bookA, 0);
    const [bc, bd] = colors(gear.off_hand);
    if (SEAMF()) {
      const rb = gear.body?.kind === "robe";
      const hem = gear.body?.form === "short" ? -6 : -1.5;
      ctx.beginPath();
      ctx.rect(-80, -120, 160, 200);
      if (rb) {
        ctx.moveTo(-7, -21);
        ctx.lineTo(7, -21);
        ctx.lineTo(10, hem);
        ctx.lineTo(-10, hem);
        ctx.closePath();
      } else ctx.rect(-7.5, -21, 15, 13.5);
      ctx.clip("evenodd");
    }
    ctx.translate(bh[0] - (ARM().bk ?? 2), bh[1] + 0.1);
    fill(ctx, bc, () => rr(ctx, -4.5, -6, 9, 8, 1));
    fill(ctx, bd, () => rr(ctx, 2.9, -6, 1.6, 8, 0.6));
    ctx.restore();
    mark("shield");
  }
  if ((!gear.off_hand || OHB) && !(kb && kb.og) && key?.c !== "bow") {
    S.FREEARM = !key && !paired && !S.SEAMIN && !OHB;
    arm(
      ctx,
      unit,
      -sxOf(gear),
      OHB ? OUTA() : outOf(gear),
      0,
      0,
      OHB
        ? (hand, c): void => {
            mainWeapon(ctx, OHB, hand, holdOf(OHB, "front") - OUTA(), "back");
            const r = rec("off");
            if (r) r(hand, c);
          }
        : paired
        ? (hand, c): void => {
            offDagger(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front") - OUTA());
            swordGrip(ctx, unit, hand, holdOf(gear.main_hand, "front") - OUTA());
            const r = rec("off");
            if (r) r(hand, c);
          }
        : rec("off"),
    );
    S.FREEARM = false;
  }
}

/** 正面：空著或拿盾、書的左手（打直往外下方），盾心對準拳頭、書往外。 */
function drawFrontOff(ctx: Ctx, unit: QUnit, key: KeyRef | null): void {
  const { gear } = unit;
  const pairedF = qWeapon(gear.main_hand)?.kind === "paired";
  const off = gear.off_hand;
  const OHF = offHeld(gear);
  const freeF = OHF ? OUTA() : off ? (isShield(off) ? (ARM().shA ?? OUTA()) : OUTA() + robeX(gear)) : outOf(gear);
  ctx.save();
  ctx.translate(0, pz("armR"));
  S.FREEARM = !key && !pairedF && !S.SEAMIN && !OHF;
  const sx = freeF ? SHX() : 8.5;
  arm(
    ctx,
    unit,
    sx,
    -freeF,
    0,
    0,
    OHF
      ? (hand, c): void => {
          mainWeapon(ctx, OHF, hand, -holdOf(OHF, "front") + OUTA(), "front");
          const r = rec("off");
          if (r) r(hand, c);
        }
      : pairedF
      ? (hand, c): void => {
          offDagger(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front") + OUTA());
          swordGrip(ctx, unit, hand, -holdOf(gear.main_hand, "front") + OUTA());
          const r = rec("off");
          if (r) r(hand, c);
        }
      : rec("off"),
  );
  S.FREEARM = false;
  const bh = fk(sx, -freeF, 0);
  ctx.translate(0, bh[1] + 9.6 + (ARM().shf && isShield(off) ? 3.9 : 0));
  if (off && isShield(off)) {
    if (ARM().shf) ctx.translate(0, off.kind !== "shield_kite" ? 0 : isTowerLike(off) ? 1.5 : -0.5);
    else if (off.kind === "shield_kite" && !isTowerLike(off)) ctx.translate(0, 3.5);
    shieldFront(ctx, off, bh[0] + (ARM().shf ? 0 : 2.7));
  } else if (off && !OHF) pdHeld(ctx, off, bh[0] + (ARM().bk ?? 2), true);
  ctx.restore();
}

/** 正面關鍵姿勢：兩隻手臂先畫，武器畫在手上面；杖、拄地長柄、雙手劍四指橫過柄。 */
function drawFrontKey(ctx: Ctx, unit: QUnit, key: KeyRef): void {
  const { gear } = unit;
  const k = key.K.front;
  const who = k.wh ?? "main";
  const sx = (who === "main" ? -1 : 1) * (k.st ? SHX() : 8.5);
  const k0 = stK(sx, k, who === "main" ? -1 : 1, gear);
  const h = fk(sx, k0.sA, k0.eA);
  const ol = ogLocal(k.og);
  if (ol) {
    const o = rot(k.a, ol);
    const io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx < 0 ? 1 : -1);
    arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main"));
  }
  arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
  if (who === "off" && !ol) arm(ctx, unit, -8.5, 0, 0, 0, rec("main"));
  const mgF = stMg(sx, k, k0, (key.kind === "scythe" && k.gripS != null ? k.gripS : k.grip) ?? 0, gear);
  const MF = k.flipS && key.kind === "scythe" ? [-1, 0, 0, 1] : null;
  const po = ARM().po;
  S.BOWP = { nock: true };
  mainWeapon(ctx, gear.main_hand, po && k.st ? [h[0] - po, h[1]] : h, k.a, "front", k.short ?? false, ol, mgF, MF);
  S.BOWP = null;
  if (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword")) wrap(ctx, unit, h, k.a);
  if (ol && key.c.startsWith("greatsword")) {
    const o = rot(k.a, ol);
    wrap(ctx, unit, [h[0] + o[0], h[1] + o[1]], k.a);
  }
}

/** QK-5：正面、背面五類出招的畫圖工具（樣張 fbApiOf）。手臂：彎肘兩段描邊、打直一圈（SEAM 開、SEAMIN 關）。 */
function fbApiOf(ctx: Ctx, unit: QUnit, view: FbView): FbApi {
  const { gear } = unit;
  return {
    ctx,
    view,
    main: gear.main_hand,
    arm: (A) => {
      const s0 = [S.SEAM, S.SEAMIN, S.FILLARM, S.FREEARM, S.FAR] as const;
      S.SEAM = true;
      S.SEAMIN = false;
      S.FILLARM = false;
      S.FREEARM = false;
      S.FAR = 0;
      arm(ctx, unit, A.sx, A.sA, A.eA, 0, null, false, A.len);
      [S.SEAM, S.SEAMIN, S.FILLARM, S.FREEARM, S.FAR] = s0;
    },
    weapon: (hand, a, M, mg) => mainWeapon(ctx, gear.main_hand, hand, a, view, false, null, mg, M),
    wrap: (hand, a) => wrap(ctx, unit, hand, a),
    bow: (hand, U, F, pull, nock) => {
      S.BOWP = { pull, nock, noArrow: !nock };
      bowFace(ctx, gear.main_hand, hand, U, F, view);
      S.BOWP = null;
    },
    offItem: (hand) => {
      const off = gear.off_hand;
      // QK-5b：成對匕首（Q 版 paired，只有主手）借劍那組時，副手那把照原本的正面、背面畫法畫在副手上
      if (!off && qWeapon(gear.main_hand)?.kind === "paired") {
        const a = view === "front" ? -holdOf(gear.main_hand, "front") + OUTA() : holdOf(gear.main_hand, "front") - OUTA();
        offDagger(ctx, gear.main_hand, hand, a);
        swordGrip(ctx, unit, hand, a);
        return;
      }
      if (!off) return;
      const OH = offHeld(gear);
      ctx.save();
      if (OH) mainWeapon(ctx, OH, hand, view === "front" ? -holdOf(OH, "front") + OUTA() : holdOf(OH, "front") - OUTA(), view);
      else if (view === "front") {
        ctx.translate(0, hand[1] + 9.6 + (ARM().shf && isShield(off) ? 3.9 : 0));
        if (isShield(off)) {
          if (ARM().shf) ctx.translate(0, off.kind !== "shield_kite" ? 0 : isTowerLike(off) ? 1.5 : -0.5);
          shieldFront(ctx, off, hand[0]);
        } else pdHeld(ctx, off, hand[0] + (ARM().bk ?? 2), true);
      } else if (isShield(off)) shieldBack(ctx, off, hand[0] + 1, hand[1] + (off.kind === "shield_round" ? 11.8 : isTowerLike(off) ? 11.5 : 11));
      else if (off.kind !== "tome") {
        // QK-5b：副手拿武器（成對劍、斧…）背面照正面的拿法畫（原本一律畫成書）
        ctx.translate(0, hand[1] + 9.6);
        pdHeld(ctx, off, hand[0] - (ARM().bk ?? 2), false);
      } else {
        const [bc, bd] = colors(off);
        ctx.translate(hand[0] - (ARM().bk ?? 2), hand[1] + 0.1);
        fill(ctx, bc, () => rr(ctx, -4.5, -6, 9, 8, 1));
        fill(ctx, bd, () => rr(ctx, 2.9, -6, 1.6, 8, 0.6));
      }
      ctx.restore();
    },
    colors: (it) => (it ? colors(it) : (["#c8ccd4", "#8a8e96"] as const)),
  };
}

/** 畫一隻 Q 版小人（腳底中心在原點、朝東的座標；朝西由呼叫端鏡像並給 west＝true）。不畫外框（外框由 qStamp 做）。 */
export function drawQ(ctx: Ctx, unit: QUnit, view: QView, hooks: QHooks, pose: QPose | null = null, west = false): void {
  const keep = { POSE: S.POSE, WEST: S.WEST, hooks: S.hooks, EDGEK, FB };
  // QK-8：人形敵人、NPC 的新部件（qNpc）：資料換算成 Q 版認得的部件；劍穗、傀儡線要武器的位置（POSE.probe）
  const npc = npcPrep(unit, pose, view === "side" && west);
  S.POSE = npc.pose;
  // QK-5：正面、背面五類出招：這一格的起伏、抬腳、杖頭光照關鍵幀（疊在片段原本的值上）
  const fbk = fbKindOfIndex(npc.pose?.fbk ?? 0);
  FB = null;
  if (fbk !== null && view !== "side") {
    const frame = fbFrameAt(fbk, view, npc.pose?.fbt ?? 0);
    FB = { kind: fbk, frame, view };
    const p0 = npc.pose ?? {};
    S.POSE = { ...p0, bob: (p0.bob ?? 0) + (frame.bob ?? 0), liftL: (p0.liftL ?? 0) + (frame.liftL ?? 0), liftR: (p0.liftR ?? 0) + (frame.liftR ?? 0), glow: Math.max(p0.glow ?? 0, frame.glow ?? 0), armL: 0, armR: 0 };
  }
  S.WEST = west && view === "side";
  S.hooks = hooks;
  EDGEK = npc.unit.gear.body?.kind === "bare" ? 0.23 : null; // 赤膊照布料內線規則，線色＝膚色加深 0.23
  try {
    drawBody(ctx, npc.unit, view, npc);
  } finally {
    S.POSE = keep.POSE;
    S.WEST = keep.WEST;
    S.hooks = keep.hooks;
    EDGEK = keep.EDGEK;
    FB = keep.FB;
  }
}
