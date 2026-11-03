// C 手繪墨線繪本的紙娃娃骨架與四方向（Phase C-1a；移植自 docs/art/sample/storyDoll.js，需求 docs/art/C畫風移植需求.md 第 2 節）。
// 座標：腳底 (0,0)，往上是 -y；頭 (0,-42)、身體 -33～-12.5、腿 -15～0、手 (±9,-23.2)，頭頂最高約 -70（尖帽）。
// 這一層畫：影子、披風、腿、身體（基本衣著）、手臂與手、頭、臉、頭髮；頭部裝備、武器、盾分別在 inkGear／inkArmor／inkWeapons／inkOffhand。
// 規則不動：`look`、裝備欄位、主手副手左右、成對武器、倒地；不認得的值退回預設，不出錯。
import type { Ctx } from "./artDraw";
import { darken } from "./color";
import type { DollSpec, GearItem, Look } from "./appearance";
import { drawFootDetail, drawInkBodyArmor, drawInkHand, drawInkHeadgearMore, footTop } from "./inkArmor";
import { drawInkHeadgear, drawInkShieldFront, drawInkShieldSide, drawInkWeapon } from "./inkGear";
import { drawInkKiteBack, drawInkKiteSide, drawInkOffhand } from "./inkOffhand";
import { drawInkWeaponMore } from "./inkWeapons";
import { drawBackSpines, drawBeastEarsBeforeHat, drawEarsAfterHat, drawEarsUnder, drawEye, drawInkHorns, drawInkTail, coverOf, drawRaceFace, drawRidge, drawSideEarBeforeHat, hatAdjust, type EarCtx } from "./inkRace";
import { pz, type InkPose } from "./inkPose";
import type { WeaponPoseOpt } from "./inkWeaponFrame";
import { dot, ellPts, ink, INK, MAT, shadow, stroke, type Pt, type View, withShadeDir } from "./inkStyle";
import { drawApron, drawBackItem, drawBareBody, drawBeads, drawBunBack, drawBunHair, drawMantle, drawSectHeld, drawVeil, drawWaist } from "./inkSect";


/** 由 paperdoll.ts 提供的裝備顏色解析（避免循環匯入）。 */
export interface InkHooks {
  colors: (it: GearItem) => readonly [string, string];
  /** 測試用（6M-2）：每畫一件武器就回報握把（手）與作用端在畫布座標的位置。正式畫面不給。 */
  probe?: (slot: "main" | "off", hand: Pt, tip: Pt, edge?: Pt) => void;
}

const SKIN_FALLBACK = "#eab48a";
const HAIR_FALLBACK = "#6a3a1e";
const PANTS_FALLBACK = "#4a4038";
const BOOT_FALLBACK = "#5a4030";
const SHIRT_FALLBACK = "#d8cdb4";

interface Ctxt {
  ctx: Ctx;
  spec: DollSpec;
  hooks: InkHooks;
  skin: string;
  /** 6M-1 姿勢；`null` ＝ 沒設姿勢，畫法與指令流和加鉤子之前完全相同。 */
  pose: InkPose | null;
}

/** 骨架關節（虛擬像素）：髖（前傾的軸）、側面肩（主手）、側面主手肘；遠側（另一隻手）的肩、肘。 */
const HIP: Pt = [0, -15];
const SHOULDER_S: Pt = [0, -31.6];
const ELBOW_S: Pt = [1.9, -28];
const SHOULDER_SF: Pt = [0.6, -32.2];
const ELBOW_SF: Pt = [3.2, -29.4];

/** 繞 (x,y) 轉 a（畫布旋轉，順時針為正）；a 為 0 時不加任何指令。 */
function rotAt(ctx: Ctx, x: number, y: number, a: number): void {
  if (a === 0) return;
  ctx.translate(x, y);
  ctx.rotate(a);
  ctx.translate(-x, -y);
}

/** 有姿勢時把 `fn` 包在 save／restore 裡、先套 `apply`；沒姿勢時直接畫（不多任何指令）。 */
function joint(t: Ctxt, apply: (ctx: Ctx, p: InkPose) => void, fn: () => void): void {
  if (t.pose === null) {
    fn();
    return;
  }
  t.ctx.save();
  apply(t.ctx, t.pose);
  fn();
  t.ctx.restore();
}

/** 正面、背面手臂上下擺（`armL`＝主手側、`armR`＝副手側）。 */
const swing = (k: "armL" | "armR") => (ctx: Ctx, p: InkPose): void => {
  const dy = pz(p, k);
  if (dy !== 0) ctx.translate(0, dy);
};

const colorOf = (h: InkHooks, it: GearItem | undefined, fallback: string): string => (it === undefined ? fallback : h.colors(it)[0]);

// ============================== 腿 ==============================
function drawLegs(t: Ctxt, view: View): void {
  const { ctx, spec, hooks } = t;
  const { look, gear } = spec;
  const heavy = gear.body?.kind === "plate";
  const pants = heavy ? MAT.iron : (look.pants ?? PANTS_FALLBACK);
  const boot = gear.feet !== undefined ? colorOf(hooks, gear.feet, BOOT_FALLBACK) : heavy ? MAT.steel : BOOT_FALLBACK;
  const by = footTop(gear.feet) ?? (heavy ? -9 : -7);
  const sabaton = gear.feet?.kind === "iron_boots" && gear.feet.form === "sabaton";
  const toeF = sabaton ? 7 : 5.6;
  const toeS = sabaton ? 9.8 : 7.4;
  if (t.pose !== null) {
    drawLegsPosed(t, view, { pants, boot, by, toeF, toeS, heavy });
    return;
  }
  if (view !== "side") {
    for (const sx of [-1, 1]) {
      ink(ctx, `leg-${sx}`, [[sx * 0.8, -15], [sx * 4.6, -15], [sx * 4.4, -6], [sx * 1, -6]], pants);
      ink(ctx, `boot-${sx}`, [[sx * 0.6, by], [sx * 4.8, by], [sx * toeF, -0.8], [sx * 0.4, -0.4]], boot);
    }
    drawFootDetail(ctx, gear.feet, view, hooks.colors, heavy);
    return;
  }
  ink(ctx, "leg-far", [[-3, -15], [0.6, -15], [-0.6, -6], [-3.8, -6]], darken(pants, 0.25));
  ink(ctx, "boot-far", [[-4.2, by], [-0.4, by], [1, -0.6], [-4.4, -0.4]], darken(boot, 0.25));
  ink(ctx, "leg-near", [[-0.6, -15], [3.2, -15], [3.8, -6], [0.6, -6]], pants);
  ink(ctx, "boot-near", [[0.4, by], [4, by], [toeS, -0.8], [0.4, -0.4]], boot);
  drawFootDetail(ctx, gear.feet, view, hooks.colors, heavy);
}

interface LegLook {
  pants: string;
  boot: string;
  by: number;
  toeF: number;
  toeS: number;
  heavy: boolean;
}

/** 有姿勢的腿（6M-1）：正面、背面抬腳（大腿抬 45%、靴再抬 55%）；側面髖、膝兩個關節，並抵銷上半身的前傾，腳才留在地上。部件形狀照沒姿勢的畫法。 */
function drawLegsPosed(t: Ctxt, view: View, L: LegLook): void {
  const { ctx, spec, hooks, pose } = t;
  const feet = spec.gear.feet;
  if (view !== "side") {
    for (const sx of [-1, 1]) {
      const up = pz(pose, sx < 0 ? "liftL" : "liftR");
      ctx.save();
      if (up !== 0) ctx.translate(0, -up * 0.45);
      ink(ctx, `leg-${sx}`, [[sx * 0.8, -15], [sx * 4.6, -15], [sx * 4.4, -6], [sx * 1, -6]], L.pants);
      drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, { sx, part: "upper" });
      if (up !== 0) ctx.translate(0, -up * 0.55);
      ink(ctx, `boot-${sx}`, [[sx * 0.6, L.by], [sx * 4.8, L.by], [sx * L.toeF, -0.8], [sx * 0.4, -0.4]], L.boot);
      drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, { sx, part: "lower" });
      ctx.restore();
    }
    return;
  }
  ctx.save();
  rotAt(ctx, HIP[0], HIP[1], -pz(pose, "lean"));
  ctx.save();
  rotAt(ctx, -1.2, -15, -pz(pose, "hipF"));
  ink(ctx, "leg-far", [[-3, -15], [0.6, -15], [-0.6, -6], [-3.8, -6]], darken(L.pants, 0.25));
  rotAt(ctx, -2.2, -6.5, pz(pose, "kneeF"));
  ink(ctx, "boot-far", [[-4.2, L.by], [-0.4, L.by], [1, -0.6], [-4.4, -0.4]], darken(L.boot, 0.25));
  ctx.restore();
  ctx.save();
  rotAt(ctx, 1.3, -15, -pz(pose, "hipN"));
  ink(ctx, "leg-near", [[-0.6, -15], [3.2, -15], [3.8, -6], [0.6, -6]], L.pants);
  drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, { sx: 1, part: "upper" });
  rotAt(ctx, 2.2, -6.5, pz(pose, "kneeN"));
  ink(ctx, "boot-near", [[0.4, L.by], [4, L.by], [L.toeS, -0.8], [0.4, -0.4]], L.boot);
  drawFootDetail(ctx, feet, view, hooks.colors, L.heavy, { sx: 1, part: "lower" });
  ctx.restore();
  ctx.restore();
}

// ============================== 身體 ==============================
const TORSO: Record<View, Pt[]> = {
  front: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
  side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]],
  back: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
};

function robePts(view: View, hem: number): Pt[] {
  if (view === "side") return [[-4, -33], [3.4, -33], [5, -27], [4, -22], [7.4, hem], [-1, hem + 0.8], [-7.6, hem], [-4.2, -22]];
  return [[-7, -33], [7, -33], [6, -23], [10, hem], [0, hem + 1], [-10, hem], [-6, -23]];
}

function drawRobe(t: Ctxt, it: GearItem, view: View, c: string): void {
  const { ctx } = t;
  const F = view !== "side";
  const hem = it.form === "short" ? -9 : -1.6;
  const trim = t.spec.look.trim ?? it.trim ?? MAT.gold;
  ink(ctx, `robe-${view}`, robePts(view, hem), c);
  const hy = hem - 1.6;
  if (view === "front") {
    stroke(ctx, "robe-mid", [[0, -31], [0, hem + 0.2]], 1.4, trim);
    stroke(ctx, "robe-mid2", [[0, -31], [0, hem + 0.2]], 0.4);
    stroke(ctx, "robe-hem", [[-9.6, hy], [0, hy + 1], [9.6, hy]], 1.2, trim);
  } else if (view === "back") {
    stroke(ctx, "robe-hem-b", [[-9.6, hy], [0, hy + 1], [9.6, hy]], 1.2, trim);
  } else {
    stroke(ctx, "robe-hem-s", [[-7.2, hy], [-1, hy + 0.8], [7, hy]], 1.2, trim);
  }
  stroke(ctx, `sash-${view}`, F ? [[-6.2, -23], [6.2, -23]] : [[-4.2, -23], [4.4, -23]], 1.8, darken(c, 0.4));
}

function drawPlateDetail(t: Ctxt, view: View): void {
  const { ctx } = t;
  if (view !== "side") {
    stroke(ctx, "plate-c", [[0, -32], [0, -24]], 0.5);
    stroke(ctx, "plate-f", [[-7.4, -18.6], [0, -17.4], [7.4, -18.6]], 0.5);
    for (const sx of [-1, 1]) ink(ctx, `pauldron-${sx}`, ellPts(sx * 7.2, -31.4, 3.6, 2.8, 12), MAT.steel, { w: 0.7 });
    return;
  }
  stroke(ctx, "plate-fs", [[-5, -18.6], [5, -18.6]], 0.5);
  ink(ctx, "pauldron-s", ellPts(-0.4, -31.4, 3.8, 2.9, 12), MAT.steel, { w: 0.7 });
}

function drawBelt(t: Ctxt, view: View): void {
  const { ctx } = t;
  const F = view !== "side";
  const bx = F ? 6.2 : 4.3;
  const bx0 = F ? -bx : -4.2;
  stroke(ctx, `belt-${view}`, [[bx0, -23], [bx, -23]], 1.7, INK);
  stroke(ctx, `belt2-${view}`, [[bx0, -23], [bx, -23]], 0.9, "#6b4426");
  if (view === "front") {
    ctx.fillStyle = MAT.gold;
    ctx.fillRect(-1.2, -24.3, 2.4, 2.6);
    stroke(ctx, "buckle", [[-1.2, -24.3], [1.2, -24.3], [1.2, -21.7], [-1.2, -21.7], [-1.2, -24.3]], 0.4);
  }
}

function drawBody(t: Ctxt, view: View): void {
  const { ctx, spec } = t;
  const it = spec.gear.body;
  const kind = it?.kind ?? "shirt";
  const c = colorOf(t.hooks, it, SHIRT_FALLBACK);
  if (it !== undefined && kind === "robe") {
    drawRobe(t, it, view, c);
    drawApron(ctx, it, view);
    return;
  }
  if (it !== undefined && kind === "bare") {
    drawBareBody(ctx, view, t.skin, c);
    return;
  }
  if (it !== undefined && drawInkBodyArmor(ctx, it, view, t.hooks.colors)) {
    if (kind !== "coat") drawBelt(t, view);
    return;
  }
  const bone = kind === "ribs";
  ink(ctx, `torso-${view}`, TORSO[view], kind === "plate" ? MAT.steel : bone ? "#d9d2bd" : c);
  const F = view !== "side";
  if (kind === "leather" && view !== "back") {
    stroke(ctx, `stitch-${view}`, F ? [[-3.6, -31], [-2.4, -24]] : [[0.6, -31], [1.6, -24]], 0.4);
    if (view === "front") stroke(ctx, "stitch2", [[3.6, -31], [2.4, -24]], 0.4);
  }
  if (kind === "plate") drawPlateDetail(t, view);
  if (kind === "shirt" && view === "front") stroke(ctx, "collar", [[-2.4, -33], [0, -30.4], [2.4, -33]], 0.5);
  if (bone && view !== "back") for (const y of [-30, -27, -24, -21]) stroke(ctx, `rib-${view}-${y}`, F ? [[-5, y], [0, y + 1], [5, y]] : [[-3, y], [1, y + 1], [3.6, y]], 0.5, "#8a826c");
  if (!bone) drawBelt(t, view);
}

function drawCloak(t: Ctxt, view: View): void {
  const { ctx, spec } = t;
  const it = spec.gear.cloak;
  if (it === undefined) return;
  const c = colorOf(t.hooks, it, "#a83030");
  if (view !== "side") ink(ctx, `cloak-${view}`, [[-8, -33], [8, -33], [11, -8], [5, -6], [0, -7.5], [-5, -6], [-11, -8]], c);
  else ink(ctx, "cloak-s", [[-3, -33], [1, -33], [-4, -9], [-10, -6.5], [-13, -9], [-8, -22]], c);
}

// ============================== 手臂與手 ==============================
function armColor(t: Ctxt): string {
  const body = t.spec.gear.body;
  if (body?.kind === "plate") return MAT.steel;
  if (body?.kind === "ribs") return "#d9d2bd";
  if (body?.kind === "bare") return t.skin; // 赤膊：手臂也是膚色
  return colorOf(t.hooks, body, SHIRT_FALLBACK);
}

function drawArmFront(t: Ctxt, sx: number): void {
  const pts: Pt[] = sx < 0 ? [[-7, -31.5], [-4.8, -31], [-7.4, -22.5], [-9.8, -23.5]] : [[7, -31.5], [4.8, -31], [7.4, -22.5], [9.8, -23.5]];
  ink(t.ctx, `arm-${sx}`, pts, armColor(t));
}

/** 手（含手套、臂甲的袖口）。`ang` ＝ 前臂傾角。 */
function drawHand(t: Ctxt, x: number, y: number, key: string, ang: number): void {
  drawInkHand(t.ctx, t.spec.gear.hands, key, x, y, ang, t.skin, t.hooks.colors);
}

// ============================== 頭 ==============================
const HEAD_SIDE: Pt[] = [[-8.6, -42], [-8, -49], [-2, -51.5], [5, -50], [8.4, -45], [8.2, -42], [9.6, -39.6], [8, -38.6], [6.6, -35], [0, -34], [-6.4, -36]];

function drawHairBack(t: Ctxt, view: View): void {
  const { look } = t.spec;
  if (look.hair !== "long" || look.skull === true) return;
  const c = darken(look.hairColor ?? HAIR_FALLBACK, 0.15);
  if (view === "front") ink(t.ctx, "hair-back", [[-10, -44], [-9.6, -30], [-5, -29], [5, -29], [9.6, -30], [10, -44], [0, -52]], c);
  else if (view === "side") ink(t.ctx, "hair-back-s", [[-9.6, -44], [-10.6, -29], [-5, -28.4], [-2, -34], [0, -46]], c);
}

function drawFace(t: Ctxt, view: View): void {
  const { ctx } = t;
  const { look } = t.spec;
  const F = view === "front";
  if (look.skull === true) {
    for (const x of F ? [-3.2, 3.2] : [4.4]) dot(ctx, x, -41, 1.9, 2.2, look.eyes ?? INK);
    stroke(ctx, `skull-teeth-${view}`, F ? [[-2.6, -37], [2.6, -37]] : [[3.4, -37], [7.2, -37]], 0.7);
    return;
  }
  for (const x of F ? [-3.2, 3.2] : [4.4]) drawEye(ctx, look, x);
  ctx.fillStyle = "rgba(220,90,80,0.32)";
  for (const x of F ? [-5.4, 5.4] : [3.2]) {
    ctx.beginPath();
    ctx.ellipse(x, -38.6, 1.6, 0.9, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  if (look.beard !== true) stroke(ctx, `mouth-${view}`, F ? [[-1, -37.4], [0, -36.8], [1, -37.4]] : [[6.4, -37], [7.4, -36.6]], 0.5);
  drawRaceFace(ctx, look, F ? "front" : "side");
}

function drawHair(t: Ctxt, view: View): void {
  const { look, gear } = t.spec;
  if (look.hair === undefined || look.hair === "none" || look.skull === true) return;
  const c = look.hairColor ?? HAIR_FALLBACK;
  // 有種族角、帽子被抬高時（巫師帽、寬帽），帽緣下面要看得到頭髮：照「沒有遮頭頂」畫
  const covered = gear.head !== undefined && coverOf(gear.head).hair === true && hatAdjust(look, gear.head).dy === 0;
  if (view === "back") {
    // 背面：帽子只蓋頭頂，後腦頭髮照畫
    const pts: Pt[] = look.hair === "long"
      ? [[-9.8, -44], [-6, -51.8], [6, -51.8], [9.8, -44], [9.6, -30], [0, -28.6], [-9.6, -30]]
      : [[-9.6, -42], [-6, -51.8], [6, -51.8], [9.6, -42], [8, -36], [0, -34.4], [-8, -36]];
    ink(t.ctx, "hair-b", pts, c);
    drawBunBack(t.ctx, look, coverOf(gear.head).top === true);
    return;
  }
  if (covered) return;
  if (drawBunHair(t.ctx, look, view)) return;
  if (view === "front") ink(t.ctx, "hair-f", [[-9.6, -41], [-10, -48], [-5, -52.5], [2, -52.5], [8, -49.5], [10, -42], [8, -45], [5, -45.5], [2, -44], [-1, -46], [-4, -44.8], [-7, -45.5]], c);
  else ink(t.ctx, "hair-s", [[-9.2, -38], [-9.4, -47], [-4, -52.5], [3, -52.6], [8.6, -48.5], [9.4, -44.6], [6, -46], [3, -45.5], [1, -43], [-1.4, -41], [-2.6, -37], [-6, -35.4]], c);
}

function earCtx(t: Ctxt, view: View): EarCtx {
  const head = t.spec.gear.head;
  return { look: t.spec.look, view, head, headColor: colorOf(t.hooks, head, "#7a5a3a") };
}

function drawHead(t: Ctxt, view: View): void {
  const { ctx } = t;
  const ears = earCtx(t, view);
  drawEarsUnder(ctx, ears); // 尖耳、鰭耳（正面、背面）畫在頭之前，頭蓋住耳根
  if (view === "side") {
    ink(ctx, "head-side", HEAD_SIDE, t.skin, { w: 1 });
    ink(ctx, "ear-s", ellPts(-2.6, -40, 1.4, 1.9, 10), t.skin, { shade: false, w: 0.6 });
  } else {
    ink(ctx, `head-${view}`, ellPts(0, -42, 9.2, 8.6), t.skin, { w: 1 });
  }
  if (view !== "back") drawFace(t, view);
  drawHair(t, view);
  drawRidge(ctx, t.spec.look, view);
  drawSideEarBeforeHat(ctx, ears);
  drawBeastEarsBeforeHat(ctx, ears);
}

// ============================== 武器、盾（座標對到 C 骨架） ==============================
const HAND_FRONT: Pt = [-9, -23.2];
const HAND_SIDE_NEAR: Pt = [4.6, -24];
const HAND_SIDE_FAR: Pt = [5.6, -27];

const isShield = (it: GearItem | undefined): boolean => it?.kind.startsWith("shield") === true;
const heldNotMirrored = (it: GearItem): boolean => isShield(it) || it.kind === "tome" || it.kind === "orb";

/** 副手實際拿的東西：副手欄，或拳套（兩手都戴）。 */
function offItemOf(spec: DollSpec): GearItem | undefined {
  return spec.gear.off_hand ?? (spec.gear.main_hand?.kind === "fist" ? spec.gear.main_hand : undefined);
}

/** 雙匕首兩把往外多張開 2px，刃身才跳出身體輪廓。 */
function spreadOf(spec: DollSpec): number {
  return spec.gear.main_hand?.kind === "dagger" && offItemOf(spec)?.kind === "dagger" ? 2 : 0;
}

/** 手持物（C 畫法：inkGear／inkOffhand／inkWeapons；`resolveDoll` 只留認得的 kind，不會走到畫不出來的）。`inkOpt` ＝ C 畫法專用的 key 與鏡像（背面主手鏡像、副手不鏡像）；`main` ＝ 主手才給的姿勢參數（6M-2：`wpn`、`pull`）。 */
function drawHeld(
  t: Ctxt,
  it: GearItem,
  x: number,
  y: number,
  o: { front: boolean; mirror: boolean; far: boolean; side: boolean },
  inkOpt?: { key: string; mirror: boolean },
  main?: WeaponPoseOpt,
): void {
  if (!o.side && drawInkShieldFront(t.ctx, it, x, y, t.hooks.colors)) return;
  const k = inkOpt ?? { key: o.side ? (o.far ? "off-s" : "main-s") : o.mirror ? "off" : "main", mirror: o.mirror };
  const hp = t.hooks.probe;
  const pose = main ?? {};
  const p: WeaponPoseOpt = hp === undefined ? pose : { ...pose, probe: (hand, tip, edge) => hp(main !== undefined ? "main" : "off", hand, tip, edge) };
  if (drawInkOffhand(t.ctx, it, x, y, o.side, t.hooks.colors, p)) return;
  const held = { mirror: k.mirror, side: o.side, far: o.far, back: !o.front, ...p };
  if (drawSectHeld(t.ctx, it, k.key, x, y, held)) return; // 5A-ART3：拂塵、符紙、傀儡線
  if (!drawInkWeapon(t.ctx, it, k.key, x, y, held, t.hooks.colors)) drawInkWeaponMore(t.ctx, it, k.key, x, y, held, t.hooks.colors);
}

function drawWoodShieldBack(t: Ctxt, off: GearItem): void {
  if (off.kind === "shield_kite") {
    drawInkKiteBack(t.ctx, off);
    return;
  }
  ink(t.ctx, "shield-b", ellPts(8.6, -21, 6.6, 7, 20), MAT.wood, { w: 1 });
  stroke(t.ctx, "shield-strap", [[5, -24], [12.2, -18]], 1.2, "#5a3a1e");
}

function drawHeadgearItem(t: Ctxt, view: View): void {
  const it = t.spec.gear.head;
  if (it === undefined) return;
  // 有種族角時：角盔改畫成一般頭盔、小帽變窄、寬帽與巫師帽抬高（可玩種族評估.md 第 2 節）
  const adj = hatAdjust(t.spec.look, it);
  t.ctx.save();
  if (adj.dy !== 0) t.ctx.translate(0, adj.dy);
  if (adj.sx !== 1) t.ctx.scale(adj.sx, 1);
  if (!drawInkHeadgear(t.ctx, adj.item, view, t.hooks.colors) && !drawInkHeadgearMore(t.ctx, adj.item, view, t.hooks.colors)) drawVeil(t.ctx, adj.item, view);
  t.ctx.restore();
}

/** 頭部裝備 → 穿出帽子的耳朵（戴頭盔的側面尖耳、小帽的獸耳、兜帽的耳朵凸起）→ 角（永遠在最上層）。 */
function drawHeadgear(t: Ctxt, view: View): void {
  drawHeadgearItem(t, view);
  drawEarsAfterHat(t.ctx, earCtx(t, view));
  drawInkHorns(t.ctx, t.spec.look, view);
}

/** 修士的身上小部件（5A-ART3）：腰掛黃符、念珠、白羽披肩；畫在身體之後、手臂之前。 */
function drawSectExtras(t: Ctxt, view: View): void {
  const { gear } = t.spec;
  drawWaist(t.ctx, gear.waist, view);
  drawBeads(t.ctx, gear.neck, view);
  drawMantle(t.ctx, gear.cloak, view);
}

// ============================== 組合 ==============================
function drawFront(t: Ctxt): void {
  const { spec } = t;
  const { gear } = spec;
  const off = offItemOf(spec);
  const spread = spreadOf(spec);
  drawCloak(t, "front");
  drawInkTail(t.ctx, spec.look, "front");
  drawHairBack(t, "front");
  drawBackItem(t.ctx, gear.back, "front", false);
  drawLegs(t, "front");
  drawBackSpines(t.ctx, spec.look, "front"); // 只露出肩頭的尖端
  drawBody(t, "front");
  drawSectExtras(t, "front");
  joint(t, swing("armR"), () => {
    drawArmFront(t, 1);
    if (off !== undefined) {
      const mirror = !heldNotMirrored(off);
      drawHeld(t, off, -HAND_FRONT[0] + spread, HAND_FRONT[1], { front: true, mirror, far: false, side: false });
    }
    if (off === undefined || !isShield(off)) drawHand(t, 9, -23.2, "hand-r", -0.32);
  });
  drawHead(t, "front");
  drawHeadgear(t, "front");
  joint(t, swing("armL"), () => {
    drawArmFront(t, -1);
    if (gear.main_hand !== undefined) drawHeld(t, gear.main_hand, HAND_FRONT[0] - spread, HAND_FRONT[1], { front: true, mirror: false, far: false, side: false }, undefined, mainPose(t, false));
    drawHand(t, -9, -23.2, "hand-l", 0.32);
  });
}

/**
 * 主手武器的姿勢參數（6M-2）：`wpn` ＝ 武器相對手的角度（統一座標，見 inkWeaponFrame.ts），只在側面生效（照樣張 storyDoll.js）；
 * `pull` ＝ 弓弦。沒設姿勢、或沒給 `wpn` ＝ 照預設握法（和沒設姿勢時同一個角度）。
 */
function mainPose(t: Ctxt, side: boolean): WeaponPoseOpt {
  const p = t.pose;
  if (p === null) return {};
  const wpn = side && typeof p.wpn === "number" && Number.isFinite(p.wpn) ? p.wpn : undefined;
  return { wpn, pull: pz(p, "pull") };
}

/** 背面（朝北）：左右對調（主手在畫面右）、看不到臉；披風、尾巴蓋在身上，武器在身體後面。 */
function drawBack(t: Ctxt): void {
  const { ctx, spec } = t;
  const { gear } = spec;
  const off = offItemOf(spec);
  const spread = spreadOf(spec);
  ctx.scale(-1, 1);
  // 現行畫法的手持物用螢幕座標（抵銷這層鏡像），主手在畫面右、副手在畫面左
  const screen = (fn: () => void): void => {
    ctx.save();
    ctx.scale(-1, 1);
    fn();
    ctx.restore();
  };
  const main = gear.main_hand;
  if (main !== undefined) joint(t, swing("armL"), () => screen(() => drawHeld(t, main, -HAND_FRONT[0] + spread, HAND_FRONT[1], { front: false, mirror: false, far: false, side: false }, { key: "main-b", mirror: true }, mainPose(t, false))));
  if (off !== undefined && !isShield(off)) joint(t, swing("armR"), () => screen(() => drawHeld(t, off, HAND_FRONT[0] - spread, HAND_FRONT[1], { front: false, mirror: !heldNotMirrored(off), far: false, side: false }, { key: "off-b", mirror: false })));
  drawLegs(t, "back");
  drawBody(t, "back");
  if (t.pose === null) {
    drawArmFront(t, -1);
    drawArmFront(t, 1);
    drawHand(t, -9, -23.2, "hand-bl", 0.32);
    drawHand(t, 9, -23.2, "hand-br", -0.32);
  } else {
    // 有姿勢：兩隻手各自跟著上下擺（局部 -x ＝ 畫面右 ＝ 主手側）
    joint(t, swing("armL"), () => {
      drawArmFront(t, -1);
      drawHand(t, -9, -23.2, "hand-bl", 0.32);
    });
    joint(t, swing("armR"), () => {
      drawArmFront(t, 1);
      drawHand(t, 9, -23.2, "hand-br", -0.32);
    });
  }
  drawCloak(t, "back");
  drawBackItem(ctx, gear.back, "back", true);
  drawBackSpines(ctx, spec.look, "back"); // 背刺畫在披風之上（當作披風開了口）
  drawInkTail(ctx, spec.look, "back");
  if (off !== undefined && isShield(off)) drawWoodShieldBack(t, off);
  drawHead(t, "back");
  drawHeadgear(t, "back");
}

function drawSide(t: Ctxt): void {
  const { ctx, spec } = t;
  const { gear } = spec;
  const off = offItemOf(spec);
  drawCloak(t, "side");
  drawInkTail(ctx, spec.look, "side");
  drawHairBack(t, "side");
  drawBackItem(ctx, gear.back, "side", false);
  if (t.pose === null) drawSideFarHeld(t, off);
  else drawSideFarArm(t, off);
  drawLegs(t, "side");
  drawBackSpines(ctx, spec.look, "side");
  drawBody(t, "side");
  drawSectExtras(t, "side");
  if (off !== undefined && isShield(off) && !drawInkShieldSide(ctx, off, t.hooks.colors)) drawInkKiteSide(ctx, off, t.hooks.colors);
  drawHead(t, "side");
  drawHeadgear(t, "side");
  const main = gear.main_hand;
  const held = (): void => {
    if (main !== undefined) drawHeld(t, main, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], { front: true, mirror: false, far: false, side: true }, undefined, mainPose(t, true));
    drawHand(t, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], "hand-s", -0.54);
  };
  if (t.pose === null) {
    ink(ctx, "arm-s", [[-1.4, -31.5], [1.4, -31.8], [5, -25], [2.6, -23.6]], armColor(t));
    held();
    return;
  }
  // 有姿勢：主手拆成上臂（繞肩 `arm`）與前臂（繞手肘 `elbow`），武器與手跟著前臂
  const pose = t.pose;
  ctx.save();
  rotAt(ctx, SHOULDER_S[0], SHOULDER_S[1], pz(pose, "arm"));
  ink(ctx, "arm-s-up", ARM_S_UPPER, armColor(t));
  rotAt(ctx, ELBOW_S[0], ELBOW_S[1], pz(pose, "elbow"));
  ink(ctx, "arm-s-fore", ARM_S_FORE, armColor(t));
  held();
  ctx.restore();
}

// 側面主手的上臂、前臂（6M-1）：合起來就是沒姿勢時的 arm-s（肩 (0,-31.6) → 手 (4.6,-24)），在手肘 (1.9,-28) 分段、略重疊
const ARM_S_UPPER: Pt[] = [[-1.4, -31.5], [1.4, -31.8], [3.4, -27.8], [0.6, -27]];
const ARM_S_FORE: Pt[] = [[0.4, -28.6], [3.2, -29.2], [5, -25], [2.6, -23.6]];
// 側面另一隻手（遠側）：肩 (0.6,-32.2) → 手肘 (3.2,-29.4) → 手 HAND_SIDE_FAR (5.6,-27)，比主手往前上錯開，顏色較暗
const ARM_SF_UPPER: Pt[] = [[-0.6, -32.2], [1.8, -32.8], [4.2, -29.8], [2, -28.6]];
const ARM_SF_FORE: Pt[] = [[2, -30.2], [4.4, -30.4], [6.4, -27.8], [4.6, -26.2]];

/** 沒姿勢：遠側手持物（成對武器的副手、書、法球）畫在身體後面，和加鉤子之前一樣。 */
function drawSideFarHeld(t: Ctxt, off: GearItem | undefined): void {
  // 成對武器的副手在遠側手，畫在身體後面，比近側手往前上錯開約 3px
  if (off !== undefined && !heldNotMirrored(off)) {
    drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], { front: true, mirror: false, far: true, side: true });
    dot(t.ctx, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], 1.7, 1.7, darken(t.skin, 0.2));
  }
  // 書、法球（非武器、非盾的副手物品）也畫在身體後面（美術 PM：照 storyDoll.js）；盾留在身體前面
  if (off !== undefined && !isShield(off) && heldNotMirrored(off)) {
    drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], { front: true, mirror: false, far: true, side: true });
  }
}

/** 有姿勢：側面另一隻手（遠側，畫在身體後面）＝ 上臂繞肩 `armF`、前臂繞手肘 `elbowF`；遠側手持物跟著手走，手一律畫出來（較暗）。 */
function drawSideFarArm(t: Ctxt, off: GearItem | undefined): void {
  const { ctx, pose } = t;
  const c = darken(armColor(t), 0.25);
  ctx.save();
  rotAt(ctx, SHOULDER_SF[0], SHOULDER_SF[1], pz(pose, "armF"));
  ink(ctx, "arm-sf-up", ARM_SF_UPPER, c);
  rotAt(ctx, ELBOW_SF[0], ELBOW_SF[1], pz(pose, "elbowF"));
  ink(ctx, "arm-sf-fore", ARM_SF_FORE, c);
  if (off !== undefined && !isShield(off)) drawHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], { front: true, mirror: false, far: true, side: true });
  dot(ctx, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], 1.7, 1.7, darken(t.skin, 0.2));
  ctx.restore();
}

export const DOLL_HEAD_TOP = 53; // 頭頂（不含角、帽）離腳底約 53

/** 體型縮放：stout 整個人 ×(1.12, 0.88)、tall ×(0.96, 1.1)；不認得的值不縮放。 */
export function buildScale(look: Look): readonly [number, number] {
  if (look.build === "stout") return [1.12, 0.88];
  if (look.build === "tall") return [0.96, 1.1];
  return [1, 1];
}

/** 頭頂狀態列要跟著體型升高的量（虛擬格 52px 單位）：高瘦會把頭頂推高 10%，矮壯不降（維持原位）。 */
export function buildRowRise(look: Look): number {
  const [, sy] = buildScale(look);
  return sy > 1 ? Math.round(DOLL_HEAD_TOP * (sy - 1) * 10) / 10 : 0;
}

/**
 * 畫一個 C 畫風小人（腳底中心在 (0,0)）。facing 的鏡像（西）由呼叫端處理；`ground` ＝ false 時不畫地面影子（倒地）。
 * `pose`（6M-1）：骨架姿勢（見 inkPose.ts）；不給或 `null` 時畫出來和加鉤子之前逐像素相同。影子不跟著起伏。
 */
export function drawInkFigure(ctx: Ctx, spec: DollSpec, view: View, hooks: InkHooks, ground = true, pose: InkPose | null = null): void {
  const t: Ctxt = { ctx, spec, hooks, skin: spec.look.skin ?? SKIN_FALLBACK, pose };
  withShadeDir(ctx, view === "front" ? 1 : -1, () => {
    ctx.save();
    const [sx, sy] = buildScale(spec.look);
    if (sx !== 1 || sy !== 1) ctx.scale(sx, sy);
    if (ground) shadow(ctx);
    if (pose !== null) {
      const bob = pz(pose, "bob");
      if (bob !== 0) ctx.translate(0, bob);
      if (view === "side") rotAt(ctx, HIP[0], HIP[1], pz(pose, "lean"));
    }
    if (view === "front") drawFront(t);
    else if (view === "back") drawBack(t);
    else drawSide(t);
    ctx.restore();
  });
}
