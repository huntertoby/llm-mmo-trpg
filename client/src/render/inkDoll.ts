// C 手繪墨線繪本的紙娃娃骨架與四方向（Phase C-1a；移植自 docs/art/sample/storyDoll.js，需求 docs/art/C畫風移植需求.md 第 2 節）。
// 座標：腳底 (0,0)，往上是 -y；頭 (0,-42)、身體 -33～-12.5、腿 -15～0、手 (±9,-23.2)，頭頂最高約 -70（尖帽）。
// 這一層畫：影子、披風、腿、身體（基本衣著）、手臂與手、頭、臉、頭髮；頭部裝備、武器、盾暫時由 `InkHooks` 呼叫現行畫法（C-1b、C-2 換）。
// 規則不動：`look`、裝備欄位、主手副手左右、成對武器、倒地；不認得的值退回預設，不出錯。
import type { Ctx } from "./artDraw";
import type { DollSpec, GearItem, Look } from "./appearance";
import { drawFootDetail, drawInkBodyArmor, drawInkHand, drawInkHeadgearMore, footTop } from "./inkArmor";
import { drawInkHeadgear, drawInkShieldFront, drawInkShieldSide, drawInkWeapon } from "./inkGear";
import { drawInkKiteBack, drawInkKiteSide, drawInkOffhand } from "./inkOffhand";
import { dot, ellPts, ink, INK, setShadeDir, shadow, stroke, type Pt } from "./inkStyle";

export type InkView = "front" | "back" | "side";

/** 還沒換成 C 畫法的部件，由 paperdoll.ts 提供現行畫法（避免循環匯入）。座標都是 C 骨架的座標。 */
export interface InkHooks {
  colors: (it: GearItem) => readonly [string, string];
  /** 現行畫法的手持物：(x, y) ＝ 手的位置；mirror ＝ 成對武器的副手鏡像；far ＝ 側面遠側那把。 */
  weapon: (it: GearItem, x: number, y: number, o: { front: boolean; mirror: boolean; far: boolean; side: boolean; scale: number }) => void;
  /** 現行畫法的頭部裝備（front／back／side）。 */
  headgear: (it: GearItem, view: InkView) => void;
  /** 現行畫法的側面副手（盾、書）。 */
  offhandSide: (it: GearItem) => void;
}

const MAT = { steel: "#c3ccd6", iron: "#8d969f", gold: "#e8bb48", wood: "#a06a36" } as const;
const SKIN_FALLBACK = "#eab48a";
const HAIR_FALLBACK = "#6a3a1e";
const PANTS_FALLBACK = "#4a4038";
const BOOT_FALLBACK = "#5a4030";
const SHIRT_FALLBACK = "#d8cdb4";

/** 現行畫法裡「蓋住頭髮」的頭部裝備 kind（沿用 paperdoll.ts 的 HAIR_COVERED）。 */
const HAIR_COVERED: readonly string[] = ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"];

const darken = (c: string, t: number): string => {
  if (!/^#[0-9a-f]{6}$/i.test(c)) return c;
  const n = parseInt(c.slice(1), 16);
  const m = (s: number): number => Math.round(((n >> s) & 255) * (1 - t));
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
};
interface Ctxt {
  ctx: Ctx;
  spec: DollSpec;
  hooks: InkHooks;
  skin: string;
}

const colorOf = (h: InkHooks, it: GearItem | undefined, fallback: string): string => (it === undefined ? fallback : h.colors(it)[0]);

// ============================== 腿 ==============================
function drawLegs(t: Ctxt, view: InkView): void {
  const { ctx, spec, hooks } = t;
  const { look, gear } = spec;
  const heavy = gear.body?.kind === "plate";
  const pants = heavy ? MAT.iron : (look.pants ?? PANTS_FALLBACK);
  const boot = gear.feet !== undefined ? colorOf(hooks, gear.feet, BOOT_FALLBACK) : heavy ? MAT.steel : BOOT_FALLBACK;
  const by = footTop(gear.feet) ?? (heavy ? -9 : -7);
  const sabaton = gear.feet?.kind === "iron_boots" && gear.feet.form === "sabaton";
  const toeF = sabaton ? 7 : 5.6;
  const toeS = sabaton ? 9.8 : 7.4;
  if (view !== "side") {
    for (const sx of [-1, 1]) {
      ink(ctx, `leg-${sx}`, [[sx * 0.8, -15], [sx * 4.6, -15], [sx * 4.4, -6], [sx * 1, -6]], pants);
      ink(ctx, `boot-${sx}`, [[sx * 0.6, by], [sx * 4.8, by], [sx * toeF, -0.8], [sx * 0.4, -0.4]], boot);
    }
    drawFootDetail(ctx, gear.feet, view, hooks.colors);
    return;
  }
  ink(ctx, "leg-far", [[-3, -15], [0.6, -15], [-0.6, -6], [-3.8, -6]], darken(pants, 0.25));
  ink(ctx, "boot-far", [[-4.2, by], [-0.4, by], [1, -0.6], [-4.4, -0.4]], darken(boot, 0.25));
  ink(ctx, "leg-near", [[-0.6, -15], [3.2, -15], [3.8, -6], [0.6, -6]], pants);
  ink(ctx, "boot-near", [[0.4, by], [4, by], [toeS, -0.8], [0.4, -0.4]], boot);
  drawFootDetail(ctx, gear.feet, view, hooks.colors);
}

// ============================== 身體 ==============================
const TORSO: Record<InkView, Pt[]> = {
  front: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
  side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]],
  back: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
};

function robePts(view: InkView, hem: number): Pt[] {
  if (view === "side") return [[-4, -33], [3.4, -33], [5, -27], [4, -22], [7.4, hem], [-1, hem + 0.8], [-7.6, hem], [-4.2, -22]];
  return [[-7, -33], [7, -33], [6, -23], [10, hem], [0, hem + 1], [-10, hem], [-6, -23]];
}

function drawRobe(t: Ctxt, it: GearItem, view: InkView, c: string): void {
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

function drawPlateDetail(t: Ctxt, view: InkView): void {
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

function drawBelt(t: Ctxt, view: InkView): void {
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

function drawBody(t: Ctxt, view: InkView): void {
  const { ctx, spec } = t;
  const it = spec.gear.body;
  const kind = it?.kind ?? "shirt";
  const c = colorOf(t.hooks, it, SHIRT_FALLBACK);
  if (it !== undefined && kind === "robe") {
    drawRobe(t, it, view, c);
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

function drawCloak(t: Ctxt, view: InkView): void {
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

function drawHairBack(t: Ctxt, view: InkView): void {
  const { look } = t.spec;
  if (look.hair !== "long" || look.skull === true) return;
  const c = darken(look.hairColor ?? HAIR_FALLBACK, 0.15);
  if (view === "front") ink(t.ctx, "hair-back", [[-10, -44], [-9.6, -30], [-5, -29], [5, -29], [9.6, -30], [10, -44], [0, -52]], c);
  else if (view === "side") ink(t.ctx, "hair-back-s", [[-9.6, -44], [-10.6, -29], [-5, -28.4], [-2, -34], [0, -46]], c);
}

function drawFace(t: Ctxt, view: InkView): void {
  const { ctx } = t;
  const { look } = t.spec;
  const F = view === "front";
  if (look.skull === true) {
    for (const x of F ? [-3.2, 3.2] : [4.4]) dot(ctx, x, -41, 1.9, 2.2, look.eyes ?? INK);
    stroke(ctx, `skull-teeth-${view}`, F ? [[-2.6, -37], [2.6, -37]] : [[3.4, -37], [7.2, -37]], 0.7);
    return;
  }
  for (const x of F ? [-3.2, 3.2] : [4.4]) dot(ctx, x, -41, 0.9, 1.3, look.eyes ?? INK);
  ctx.fillStyle = "rgba(220,90,80,0.32)";
  for (const x of F ? [-5.4, 5.4] : [3.2]) {
    ctx.beginPath();
    ctx.ellipse(x, -38.6, 1.6, 0.9, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  stroke(ctx, `mouth-${view}`, F ? [[-1, -37.4], [0, -36.8], [1, -37.4]] : [[6.4, -37], [7.4, -36.6]], 0.5);
}

function drawHair(t: Ctxt, view: InkView): void {
  const { look, gear } = t.spec;
  if (look.hair === undefined || look.hair === "none" || look.skull === true) return;
  const c = look.hairColor ?? HAIR_FALLBACK;
  const covered = gear.head !== undefined && HAIR_COVERED.includes(gear.head.kind);
  if (view === "back") {
    // 背面：帽子只蓋頭頂，後腦頭髮照畫
    const pts: Pt[] = look.hair === "long"
      ? [[-9.8, -44], [-6, -51.8], [6, -51.8], [9.8, -44], [9.6, -30], [0, -28.6], [-9.6, -30]]
      : [[-9.6, -42], [-6, -51.8], [6, -51.8], [9.6, -42], [8, -36], [0, -34.4], [-8, -36]];
    ink(t.ctx, "hair-b", pts, c);
    return;
  }
  if (covered) return;
  if (view === "front") ink(t.ctx, "hair-f", [[-9.6, -41], [-10, -48], [-5, -52.5], [2, -52.5], [8, -49.5], [10, -42], [8, -45], [5, -45.5], [2, -44], [-1, -46], [-4, -44.8], [-7, -45.5]], c);
  else ink(t.ctx, "hair-s", [[-9.2, -38], [-9.4, -47], [-4, -52.5], [3, -52.6], [8.6, -48.5], [9.4, -44.6], [6, -46], [3, -45.5], [1, -43], [-1.4, -41], [-2.6, -37], [-6, -35.4]], c);
}

function drawHead(t: Ctxt, view: InkView): void {
  const { ctx } = t;
  if (view === "side") {
    ink(ctx, "head-side", HEAD_SIDE, t.skin, { w: 1 });
    ink(ctx, "ear-s", ellPts(-2.6, -40, 1.4, 1.9, 10), t.skin, { shade: false, w: 0.6 });
  } else {
    ink(ctx, `head-${view}`, ellPts(0, -42, 9.2, 8.6), t.skin, { w: 1 });
  }
  if (view !== "back") drawFace(t, view);
  drawHair(t, view);
}

// ============================== 武器、盾（現行畫法，座標對到 C 骨架） ==============================
const HAND_FRONT: Pt = [-9, -23.2];
const HAND_SIDE_NEAR: Pt = [4.6, -24];
const HAND_SIDE_FAR: Pt = [5.6, -27];
const WEAPON_SCALE = 1.3;
const SHIELD_SCALE = 1.15;

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

/** 手持物：樣張畫過的走 C 畫法（inkGear.ts），其餘退回現行畫法。`inkOpt` ＝ C 畫法專用的 key 與鏡像（背面主手鏡像、副手不鏡像）。 */
function legacyHeld(
  t: Ctxt,
  it: GearItem,
  x: number,
  y: number,
  o: { front: boolean; mirror: boolean; far: boolean; side: boolean },
  inkOpt?: { key: string; mirror: boolean },
): void {
  if (!o.side && drawInkShieldFront(t.ctx, it, x, y, t.hooks.colors)) return;
  if (drawInkOffhand(t.ctx, it, x, y, o.side, t.hooks.colors)) return;
  const k = inkOpt ?? { key: o.side ? (o.far ? "off-s" : "main-s") : o.mirror ? "off" : "main", mirror: o.mirror };
  if (drawInkWeapon(t.ctx, it, k.key, x, y, { mirror: k.mirror, side: o.side, far: o.far, back: !o.front }, t.hooks.colors)) return;
  const scale = heldNotMirrored(it) ? SHIELD_SCALE : WEAPON_SCALE;
  t.hooks.weapon(it, x, y, { ...o, scale });
}

function drawWoodShieldBack(t: Ctxt, off: GearItem): void {
  if (off.kind === "shield_kite") {
    drawInkKiteBack(t.ctx, off);
    return;
  }
  ink(t.ctx, "shield-b", ellPts(8.6, -21, 6.6, 7, 20), MAT.wood, { w: 1 });
  stroke(t.ctx, "shield-strap", [[5, -24], [12.2, -18]], 1.2, "#5a3a1e");
}

function drawHeadgear(t: Ctxt, view: InkView): void {
  const it = t.spec.gear.head;
  if (it === undefined || drawInkHeadgear(t.ctx, it, view, t.hooks.colors) || drawInkHeadgearMore(t.ctx, it, view, t.hooks.colors)) return;
  t.hooks.headgear(it, view);
}

// ============================== 組合 ==============================
function drawFront(t: Ctxt): void {
  const { spec } = t;
  const { gear } = spec;
  const off = offItemOf(spec);
  const spread = spreadOf(spec);
  drawCloak(t, "front");
  drawHairBack(t, "front");
  drawLegs(t, "front");
  drawBody(t, "front");
  drawArmFront(t, 1);
  if (off !== undefined) {
    const mirror = !heldNotMirrored(off);
    legacyHeld(t, off, -HAND_FRONT[0] + spread, HAND_FRONT[1], { front: true, mirror, far: false, side: false });
  }
  if (off === undefined || !isShield(off)) drawHand(t, 9, -23.2, "hand-r", -0.32);
  drawHead(t, "front");
  drawHeadgear(t, "front");
  drawArmFront(t, -1);
  if (gear.main_hand !== undefined) legacyHeld(t, gear.main_hand, HAND_FRONT[0] - spread, HAND_FRONT[1], { front: true, mirror: false, far: false, side: false });
  drawHand(t, -9, -23.2, "hand-l", 0.32);
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
  if (gear.main_hand !== undefined) screen(() => legacyHeld(t, gear.main_hand!, -HAND_FRONT[0] + spread, HAND_FRONT[1], { front: false, mirror: false, far: false, side: false }, { key: "main-b", mirror: true }));
  if (off !== undefined && !isShield(off)) screen(() => legacyHeld(t, off, HAND_FRONT[0] - spread, HAND_FRONT[1], { front: false, mirror: !heldNotMirrored(off), far: false, side: false }, { key: "off-b", mirror: false }));
  drawLegs(t, "back");
  drawBody(t, "back");
  drawArmFront(t, -1);
  drawArmFront(t, 1);
  drawHand(t, -9, -23.2, "hand-bl", 0.32);
  drawHand(t, 9, -23.2, "hand-br", -0.32);
  drawCloak(t, "back");
  if (off !== undefined && isShield(off)) drawWoodShieldBack(t, off);
  drawHead(t, "back");
  drawHeadgear(t, "back");
}

function drawSide(t: Ctxt): void {
  const { ctx, spec } = t;
  const { gear } = spec;
  const off = offItemOf(spec);
  drawCloak(t, "side");
  drawHairBack(t, "side");
  // 成對武器的副手在遠側手，畫在身體後面，比近側手往前上錯開約 3px
  if (off !== undefined && !heldNotMirrored(off)) {
    legacyHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], { front: true, mirror: false, far: true, side: true });
    dot(ctx, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], 1.7, 1.7, darken(t.skin, 0.2));
  }
  // 書、法球（非武器、非盾的副手物品）也畫在身體後面（美術 PM：照 storyDoll.js）；盾留在身體前面
  if (off !== undefined && !isShield(off) && heldNotMirrored(off)) {
    legacyHeld(t, off, HAND_SIDE_FAR[0], HAND_SIDE_FAR[1], { front: true, mirror: false, far: true, side: true });
  }
  drawLegs(t, "side");
  drawBody(t, "side");
  if (off !== undefined && isShield(off) && !drawInkShieldSide(ctx, off, t.hooks.colors) && !drawInkKiteSide(ctx, off, t.hooks.colors)) t.hooks.offhandSide(off);
  drawHead(t, "side");
  drawHeadgear(t, "side");
  ink(ctx, "arm-s", [[-1.4, -31.5], [1.4, -31.8], [5, -25], [2.6, -23.6]], armColor(t));
  if (gear.main_hand !== undefined) legacyHeld(t, gear.main_hand, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], { front: true, mirror: false, far: false, side: true });
  drawHand(t, HAND_SIDE_NEAR[0], HAND_SIDE_NEAR[1], "hand-s", -0.54);
}

/** 體型縮放：stout 整個人 ×(1.12, 0.88)、tall ×(0.96, 1.1)；不認得的值不縮放。 */
export function buildScale(look: Look): readonly [number, number] {
  if (look.build === "stout") return [1.12, 0.88];
  if (look.build === "tall") return [0.96, 1.1];
  return [1, 1];
}

/** 畫一個 C 畫風小人（腳底中心在 (0,0)）。facing 的鏡像（西）由呼叫端處理；`ground` ＝ false 時不畫地面影子（倒地）。 */
export function drawInkFigure(ctx: Ctx, spec: DollSpec, view: InkView, hooks: InkHooks, ground = true): void {
  const t: Ctxt = { ctx, spec, hooks, skin: spec.look.skin ?? SKIN_FALLBACK };
  setShadeDir(view === "front" ? 1 : -1);
  ctx.save();
  const [sx, sy] = buildScale(spec.look);
  if (sx !== 1 || sy !== 1) ctx.scale(sx, sy);
  if (ground) shadow(ctx);
  if (view === "front") drawFront(t);
  else if (view === "back") drawBack(t);
  else drawSide(t);
  ctx.restore();
}
