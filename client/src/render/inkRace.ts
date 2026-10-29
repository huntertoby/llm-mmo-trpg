// C 畫風的種族部件：耳、角、尾（Phase 3R-3b；移植自 docs/art/sample/storyDoll.js 的 `tail`、`ears`、`horns`，
// 衝突規則以 docs/art/可玩種族評估.md 第 2 節為準，不是樣張的簡化版）。
// 規則寫在「頭部裝備的種類」上（`COVERS`，每種 kind 一個標記），新增帽子或種族時不用一一配對。
// 所有欄位選填，不認得的值＝沒有，不會出錯。Phase 3R-3c 加上體型、臉部紋路、鬍子、獠牙、豎瞳、鱗脊、背刺。
import type { Ctx } from "./artDraw";
import type { GearItem, Look } from "./appearance";
import { dot, ink, stroke, type Pt } from "./inkStyle";

export type RaceView = "front" | "back" | "side";

// ============================== 欄位值的檢查 ==============================
const EARS = ["pointed", "fin", "beast"] as const;
const HORNS = ["small", "curved", "dragon"] as const;
const TAILS = ["fox", "scaled", "demon", "dragon"] as const;
const PATTERNS = ["scales", "marks", "circuit", "dragonscale"] as const;
const BUILDS = ["stout", "tall"] as const;
const HEX = /^#[0-9a-f]{6}$/i;

const pick = <T extends string>(list: readonly T[], v: unknown): T | undefined => (typeof v === "string" ? list.find((x) => x === v) : undefined);
const hex = (v: unknown): string | undefined => (typeof v === "string" && HEX.test(v) ? v : undefined);

/** 後端 `RaceLook`（snake_case、自由 ID）→ 紙娃娃 `Look` 的種族欄位；不認得的值一律略過（＝沒有）。膚色、髮型、眼色一併帶入。 */
export function raceLookToLook(r: Readonly<Record<string, unknown>> | null | undefined): Partial<Look> {
  if (r == null) return {};
  const out: Partial<Look> = {};
  const skin = hex(r["skin"]);
  if (skin !== undefined) out.skin = skin;
  const hair = pick(["short", "long", "none"] as const, r["hair"]);
  if (hair !== undefined) out.hair = hair;
  const hairColor = hex(r["hair_color"]);
  if (hairColor !== undefined) out.hairColor = hairColor;
  const eyes = hex(r["eyes"]);
  if (eyes !== undefined) out.eyes = eyes;
  const ears = pick(EARS, r["ears"]);
  if (ears !== undefined) out.ears = ears;
  const horns = pick(HORNS, r["horns"]);
  if (horns !== undefined) out.horns = horns;
  const hornColor = hex(r["horn_color"]);
  if (hornColor !== undefined) out.hornColor = hornColor;
  const tail = pick(TAILS, r["tail"]);
  if (tail !== undefined) out.tail = tail;
  const tailColor = hex(r["tail_color"]);
  if (tailColor !== undefined) out.tailColor = tailColor;
  const scaleColor = hex(r["scale_color"]);
  if (scaleColor !== undefined) out.scaleColor = scaleColor;
  const build = pick(BUILDS, r["build"]);
  if (build !== undefined) out.build = build;
  const pattern = pick(PATTERNS, r["pattern"]);
  if (pattern !== undefined) out.pattern = pattern;
  const markColor = hex(r["mark_color"]);
  if (markColor !== undefined) out.markColor = markColor;
  // 旗標欄位：只有明確的 true 才算（"true"、1 之類不認得的值＝沒有）
  if (r["beard"] === true) out.beard = true;
  if (r["tusks"] === true) out.tusks = true;
  if (r["slit_eyes"] === true) out.slitEyes = true;
  if (r["ridge"] === true) out.ridge = true;
  if (r["spines"] === true) out.spines = true;
  return out;
}

// ============================== 顏色 ==============================
function mix(a: string, b: string, t: number): string {
  if (!HEX.test(a) || !HEX.test(b)) return a;
  const x = parseInt(a.slice(1), 16);
  const y = parseInt(b.slice(1), 16);
  const m = (s: number): number => Math.round(((x >> s) & 255) * (1 - t) + ((y >> s) & 255) * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
}
const dark = (c: string, t = 0.3): string => mix(c, "#000000", t);
const light = (c: string, t = 0.3): string => mix(c, "#ffffff", t);

// ============================== 頭部裝備的遮蓋（衝突規則） ==============================
/** top ＝ 蓋頭頂、side ＝ 蓋兩側、hood ＝ 兜帽（有耳朵版）、tall ＝ 寬帽／巫師帽（有角時要抬高）、narrow ＝ 小帽（有角時變窄）。 */
export interface Cover {
  top?: boolean;
  side?: boolean;
  hood?: boolean;
  tall?: boolean;
  narrow?: boolean;
}

export const COVERS: Readonly<Record<string, Cover>> = {
  helmet: { top: true, side: true },
  greathelm: { top: true, side: true },
  horned_helm: { top: true, side: true },
  hood: { top: true, side: true, hood: true },
  cap: { top: true, narrow: true },
  bandana: { top: true, narrow: true },
  crown: { narrow: true },
  wide_hat: { top: true, tall: true },
  wizard_hat: { top: true, tall: true },
};

/** 沒戴＝什麼都不蓋；沒登記的 kind 當作只蓋頭頂。 */
export const coverOf = (head: GearItem | undefined): Cover => (head === undefined ? {} : (COVERS[head.kind] ?? { top: true }));

const hasHorns = (look: Look): boolean => pick(HORNS, look.horns) !== undefined;

/** 有種族角時頭部裝備的調整：角盔改畫成一般頭盔（種族角取代裝飾角）、小帽變窄、寬帽與巫師帽抬高。 */
export function hatAdjust(look: Look, head: GearItem): { item: GearItem; dy: number; sx: number } {
  if (!hasHorns(look)) return { item: head, dy: 0, sx: 1 };
  if (head.kind === "horned_helm") return { item: { ...head, kind: "helmet" }, dy: 0, sx: 1 };
  const c = coverOf(head);
  return { item: head, dy: c.tall === true ? -5 : 0, sx: c.narrow === true ? 0.8 : 1 };
}

// ============================== 尾巴 ==============================
/** 正面：從腰側往畫面右邊伸出；側面：往身後（西）伸出；背面：畫在披風之上。畫在身體之前（身體、下襬會蓋住根部）。 */
export function drawInkTail(ctx: Ctx, look: Look, view: RaceView): void {
  const k = pick(TAILS, look.tail);
  if (k === undefined) return;
  const s = view === "side" ? -1 : 1;
  const P = (pts: readonly Pt[]): Pt[] => pts.map(([x, y]): Pt => [x * s, y]);
  const skin = look.skin ?? "#eab48a";
  if (k === "fox") {
    const c = look.tailColor ?? look.hairColor ?? "#d8762a";
    ink(ctx, `tail-fox-${view}`, P([[2, -16], [10, -17], [16, -10], [17, -3], [12, -1], [9, -8], [2, -11]]), c);
    ink(ctx, `tail-foxtip-${view}`, P([[14.6, -5], [17.4, -3.6], [15.6, -0.6], [12.4, -1.4]]), "#f4ece0", { shade: false, w: 0.6 });
    return;
  }
  if (k === "demon") {
    const c = look.tailColor ?? dark(skin, 0.3);
    const line = P([[2, -13], [9, -12], [13, -6], [13.6, -1.6]]);
    stroke(ctx, `tail-dm-${view}`, line, 1.9);
    stroke(ctx, `tail-dm2-${view}`, line, 1.1, c);
    ink(ctx, `tail-dmtip-${view}`, P([[13.6, -2.4], [11.2, 0.6], [13.8, 3.2], [16, 0.4]]), c, { shade: false, w: 0.6 });
    return;
  }
  // scaled／dragon：粗尾巴，龍裔另有背刺
  const c = look.tailColor ?? look.scaleColor ?? dark(skin, 0.15);
  const thick = k === "dragon" ? 1.35 : 1;
  ink(ctx, `tail-sc-${view}`, P([[1, -17 * thick + 1], [10, -14], [17, -5], [21, 0.6], [15, 0], [8, -6], [1, -9]]), c);
  if (k === "dragon") {
    for (const t of [0.25, 0.48, 0.7]) {
      const x = 2 + 16 * t;
      const y = -15 + 13 * t;
      ink(ctx, `spine-${t}-${view}`, P([[x - 1.6, y - 0.4], [x + 0.2, y - 4.2], [x + 1.8, y + 0.2]]), light(c, 0.35), { shade: false, w: 0.5 });
    }
  }
}

// ============================== 耳朵 ==============================
export interface EarCtx {
  look: Look;
  view: RaceView;
  head: GearItem | undefined;
  /** 頭部裝備的主色（兜帽的耳朵凸起用）。 */
  headColor: string;
}

/** 尖耳、鰭耳：正面／背面畫在頭之前（頭蓋住耳根，只露出伸出的部分）。兜帽蓋住側耳＝不畫。 */
export function drawEarsUnder(ctx: Ctx, e: EarCtx): void {
  const k = pick(EARS, e.look.ears);
  if (k === undefined || k === "beast" || e.view === "side") return;
  if (coverOf(e.head).hood === true) return;
  const c = e.look.skin ?? "#eab48a";
  for (const sx of [-1, 1]) {
    if (k === "pointed") ink(ctx, `ear-p-${sx}`, [[sx * 8, -44], [sx * 15.6, -48.6], [sx * 9, -39.6]], c, { w: 0.7 });
    else ink(ctx, `ear-f-${sx}`, [[sx * 8.4, -45], [sx * 14, -47.6], [sx * 13, -42], [sx * 14.4, -38.6], [sx * 8.4, -39]], light(c, 0.15), { w: 0.7 });
  }
}

function sideEar(ctx: Ctx, look: Look, k: "pointed" | "fin"): void {
  const c = look.skin ?? "#eab48a";
  if (k === "pointed") ink(ctx, "ear-p-s", [[-1, -43.6], [-9.6, -48.6], [-1.6, -39.2]], c, { w: 0.7 });
  else ink(ctx, "ear-f-s", [[-0.6, -45], [-7.4, -48.6], [-6, -42.4], [-7.8, -38.4], [-0.6, -39]], light(c, 0.15), { w: 0.7 });
}

/** 側面的尖耳／鰭耳：沒有蓋住兩側的頭部裝備時，畫在頭髮之後、頭部裝備之前。 */
export function drawSideEarBeforeHat(ctx: Ctx, e: EarCtx): void {
  const k = pick(EARS, e.look.ears);
  if (e.view !== "side" || k === undefined || k === "beast") return;
  if (coverOf(e.head).side === true) return;
  sideEar(ctx, e.look, k);
}

/** 獸耳：頭頂兩隻（側面前後各一）。 */
function drawBeastEars(ctx: Ctx, e: EarCtx, c: string, inner: string | null, scale: number): void {
  const F = e.view !== "side";
  const pos: ReadonlyArray<readonly [number, number]> = F ? [[-1, -5.6], [1, 5.6]] : [[-1, -5], [1, 0]];
  for (const [i, x] of pos) {
    const far = !F && i < 0;
    const lean = (F ? i * 1.2 : -1.4) * scale;
    const top = -48.6 - 9 * scale;
    ink(ctx, `ear-b-${e.view}-${i}-${scale}`, [[x - 3.6, -48.6], [x + lean, top], [x + 3.4, -49]], far ? dark(c, 0.2) : c, { w: 0.8 });
    if (inner !== null) ink(ctx, `ear-bi-${e.view}-${i}-${scale}`, [[x - 1.8, -49.4], [x + (F ? i * 0.8 : -1) * scale, -48.6 - 6.4 * scale], [x + 1.6, -49.6]], inner, { shade: false, line: false });
  }
}

/** 獸耳在頭部裝備之前畫的情形：沒戴、皇冠（不蓋頭頂）。其餘蓋頭頂的頭盔、寬帽、巫師帽藏起來；小帽與兜帽見 `drawEarsAfterHat`。 */
export function drawBeastEarsBeforeHat(ctx: Ctx, e: EarCtx): void {
  if (e.look.ears !== "beast") return;
  if (coverOf(e.head).top === true) return;
  drawBeastEars(ctx, e, e.look.hairColor ?? "#d8762a", "#f2c4b8", 1);
}

/**
 * 頭部裝備之後才畫的耳朵：
 * - 側面的尖耳／鰭耳戴頭盔時從頭盔兩側伸出（兜帽蓋住＝不畫）；
 * - 獸耳戴小帽（cap、bandana）從帽子兩側穿出；戴兜帽時兜帽頂端多兩個凸起（有耳朵的兜帽，帽色）。
 */
export function drawEarsAfterHat(ctx: Ctx, e: EarCtx): void {
  const k = pick(EARS, e.look.ears);
  if (k === undefined || e.head === undefined) return;
  const cov = coverOf(e.head);
  if (k === "beast") {
    if (cov.hood === true) drawBeastEars(ctx, e, e.headColor, null, 1);
    else if (cov.narrow === true && cov.top === true) drawBeastEars(ctx, e, e.look.hairColor ?? "#d8762a", "#f2c4b8", 1);
    return;
  }
  if (e.view === "side" && cov.side === true && cov.hood !== true) sideEar(ctx, e.look, k);
}

// ============================== 角 ==============================
/** 角：永遠在最上層。小角、彎角、龍角（龍角的雙叉外形照樣張；鱗色、龍鱗屬 3R-3c）。 */
export function drawInkHorns(ctx: Ctx, look: Look, view: RaceView): void {
  const k = pick(HORNS, look.horns);
  if (k === undefined) return;
  const c = look.hornColor ?? "#e8d8b8";
  const F = view !== "side";
  const one = (key: string, s: number, far: boolean): void => {
    const P = (pts: readonly Pt[]): Pt[] => pts.map(([x, y]): Pt => [x * s, y]);
    const col = far ? dark(c, 0.25) : c;
    if (k === "small") ink(ctx, key, P(F ? [[3, -50], [5.4, -56.4], [6.4, -49.4]] : [[0.6, -50.6], [-2, -57], [-2.6, -50]]), col, { w: 0.7 });
    else if (k === "curved") ink(ctx, key, P(F ? [[4, -49], [9, -55], [12.6, -54], [9.6, -57.4], [6.4, -51.6]] : [[1, -50], [-5, -56], [-9, -54.6], [-6.6, -58.4], [-1.6, -52.4]]), col, { w: 0.7 });
    else ink(ctx, key, P(F ? [[3.4, -49.4], [8, -57], [14.4, -61.6], [10.6, -54.6], [7.2, -49]] : [[1.6, -49.6], [-4, -56.6], [-12.4, -60.6], [-7.6, -53], [-2, -47.6]]), col, { w: 0.8 });
  };
  if (F) {
    one("horn-l", -1, false);
    one("horn-r", 1, false);
  } else {
    one("horn-far", 1, true);
    ctx.save();
    ctx.translate(2.2, 0.6);
    one("horn-near", 1, false);
    ctx.restore();
  }
}

// ============================== 臉部（Phase 3R-3c） ==============================
const INK_EYE = "#1d1a22";
const DRAGON_FALLBACK = "#a8784a";

/** 眼睛：豎瞳（金色眼白＋黑色細縫）或一般圓眼。`x` 是眼的橫向位置。 */
export function drawEye(ctx: Ctx, look: Look, x: number): void {
  if (look.slitEyes === true) {
    dot(ctx, x, -41, 1.3, 1.5, "#e8b830");
    dot(ctx, x, -41, 0.35, 1.3, INK_EYE);
  } else dot(ctx, x, -41, 0.9, 1.3, look.eyes ?? INK_EYE);
}

function drawFacePattern(ctx: Ctx, look: Look, view: "front" | "side"): void {
  const F = view === "front";
  const pc = look.scaleColor ?? look.markColor ?? dark(look.skin ?? "#eab48a", 0.25);
  const k = pick(PATTERNS, look.pattern);
  if (k === "scales" || k === "dragonscale") {
    const base: ReadonlyArray<readonly [number, number]> = F ? [[-6.6, -43.6], [-7.4, -41], [6.6, -43.6], [7.4, -41], [0, -48]] : [[1.6, -44], [0.4, -41.4], [2.6, -47.6]];
    // 龍鱗：臉頰到下顎再多一排，線條加粗，鱗色才看得出來
    const more: ReadonlyArray<readonly [number, number]> = k !== "dragonscale" ? [] : F ? [[-7, -38.4], [7, -38.4], [-5.8, -36], [5.8, -36]] : [[2.4, -38.6], [4, -36]];
    for (const [x, y] of [...base, ...more]) stroke(ctx, `scale-${view}-${x}-${y}`, [[x - 1.2, y], [x, y + 1], [x + 1.2, y]], k === "dragonscale" ? 0.8 : 0.6, pc);
  } else if (k === "marks") {
    const mc = look.markColor ?? pc;
    for (const sx of F ? [-1, 1] : [1]) {
      const x = F ? sx * 6 : 2.6;
      stroke(ctx, `mark-${view}-${sx}`, [[x - 1.4, -40.4], [x + 1.4, -39.4]], 0.8, mc);
      stroke(ctx, `mark2-${view}-${sx}`, [[x - 1.4, -38.6], [x + 1.4, -37.6]], 0.8, mc);
    }
  } else if (k === "circuit") {
    const x = F ? 5 : 1.4;
    const cc = "#3ad0e8";
    stroke(ctx, `circ-${view}`, [[x, -46], [x, -42.6], [x + 2.4, -41]], 0.6, cc);
    dot(ctx, x + 2.4, -41, 0.6, 0.6, cc);
    dot(ctx, x, -46, 0.6, 0.6, cc);
  }
}

/** 臉部紋路、獠牙、鬍子（畫在眼睛與嘴之後、頭髮與頭部裝備之前，所以頭盔、頭髮會蓋住該蓋的部分）。背面不畫。 */
export function drawRaceFace(ctx: Ctx, look: Look, view: "front" | "side"): void {
  const F = view === "front";
  drawFacePattern(ctx, look, view);
  if (look.tusks === true) {
    for (const x of F ? [-1.8, 1.8] : [6.6]) ink(ctx, `tusk-${view}-${x}`, [[x - 0.7, -36.4], [x, -39.2], [x + 0.7, -36.4]], "#f4ecd8", { shade: false, w: 0.45 });
  }
  if (look.beard === true) {
    const c = look.hairColor ?? "#a8481e";
    if (F) ink(ctx, "beard", [[-7.6, -40], [-4, -37.6], [0, -38.2], [4, -37.6], [7.6, -40], [6.4, -32], [2.4, -28.6], [-2.4, -28.6], [-6.4, -32]], c);
    else ink(ctx, "beard-s", [[1, -38.6], [9, -37], [8, -32], [4.4, -28.8], [0.4, -31]], c);
  }
}

/** 鱗脊：鼻樑到額頭一排小尖，畫在頭髮之後（不被瀏海蓋住）、頭部裝備之前。 */
export function drawRidge(ctx: Ctx, look: Look, view: RaceView): void {
  if (look.ridge !== true || view === "back") return;
  const c = look.scaleColor ?? DRAGON_FALLBACK;
  const F = view === "front";
  [-46.4, -44, -41.6].forEach((y, i) => {
    const x = F ? 0 : 5.4 - i * 0.4;
    ink(ctx, `ridge-${view}-${i}`, [[x - 1.2, y + 1.1], [x, y - 1.1], [x + 1.2, y + 1.1]], light(c, 0.15), { shade: false, w: 0.5 });
  });
}

/** 背刺：肩後三根骨刺。正面只從肩頭露出尖端（畫在身體之前，身體蓋住大半）；背面畫在背上；側面在背後。 */
export function drawBackSpines(ctx: Ctx, look: Look, view: RaceView): void {
  if (look.spines !== true) return;
  const c = light(look.scaleColor ?? DRAGON_FALLBACK, 0.2);
  const spike = (key: string, x: number, y: number, dx: number, dy: number): void => {
    const n = Math.hypot(dx, dy);
    const px = (-dy / n) * 1.7;
    const py = (dx / n) * 1.7;
    ink(ctx, key, [[x + px, y + py], [x + dx, y + dy], [x - px, y - py]], c, { shade: false, w: 0.5 });
  };
  if (view === "front") for (const x of [-6.5, 6.5]) spike(`spine-f-${x}`, x, -29, 0, -5);
  else if (view === "back") for (const x of [-4.5, 0, 4.5]) spike(`spine-b-${x}`, x, -28, 0, -5.2);
  else for (const [x, y] of [[-3.6, -30], [-4.8, -26.4], [-5.2, -22.8]] as const) spike(`spine-s-${y}`, x, y, -4.4, -0.6);
}
