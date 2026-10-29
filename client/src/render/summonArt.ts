// 召喚物外觀渲染器（Phase 3-33h1；來源：美術 PM 的 docs/art/sample/summonArt.js 與 docs/art/召喚物外觀.md）。
// 體型 × 款式 × 元素配色 × 大小 × 特徵。座標和紙娃娃相同：腳底中心為原點，往上是負，身高約 46。
// 人形體型直接用紙娃娃（再依款式合成透明度、色調、外光）；其他五種體型在這裡程式繪製，畫到離屏後加深色外框。
// 任何輸入（含不認得的體型、款式、元素、大小）都畫得出來：不認得的退回人形骷髏，不丟例外。
import type { Facing } from "../api/types";
import { TAU, type Ctx } from "./artDraw";
import type { DollSpec, Gear } from "./appearance";
import { mix } from "./color";
import { KEYWORD_COLOR } from "./palette";
import { FORM_AURA_NEUTRAL, drawFormAura } from "./inkForm";
import { dot, ellPts, ink, INK, shadow, stroke, withShadeDir, type Pt } from "./inkStyle";
import { DOLL_H, DOLL_W, renderFigureCanvas, SUMMON_FOOT_Y, SUMMON_H, SUMMON_W } from "./paperdoll";


/** 後端 `SummonLookView`／前端 `UnitDraw` 的外觀欄位（字串都可能是前端不認得的新值）。 */
export interface SummonLookDraw {
  body: string;
  variant?: string | null;
  element?: string | null;
  size?: string | null;
  trait?: string | null;
}

export type SummonBody = "humanoid" | "spirit" | "construct" | "beast" | "plant" | "totem";
export type SummonSize = "small" | "medium" | "large";

export interface ResolvedLook {
  body: SummonBody;
  variant: string;
  /** 認得的關鍵字 ID；沒有或不認得為 `undefined`（用預設灰白色）。 */
  element: string | undefined;
  size: SummonSize;
  trait: string | undefined;
}

/** 召喚物外觀認得的關鍵字（顏色在 `palette.ts` 的 `KEYWORD_COLOR`；`poisoned`、`form` 不是召喚物的元素，不列）。 */
export const SUMMON_KEYWORDS: readonly string[] = ["ignite", "wet", "charged", "frozen", "prone", "collision", "marked", "high_ground", "concealed", "summon"];

export const SIZE_SCALE: Readonly<Record<SummonSize, number>> = { small: 0.8, medium: 1, large: 1.25 };

const BODIES: readonly SummonBody[] = ["humanoid", "spirit", "construct", "beast", "plant", "totem"];
const VARIANTS: Readonly<Record<SummonBody, readonly string[]>> = {
  humanoid: ["skeleton", "shade", "afterimage", "guardian"],
  spirit: [""],
  construct: ["golem", "bomb", "wall"],
  beast: ["wolf", "bird"],
  plant: [""],
  totem: ["war", "pull", "plateau"],
};

/** 驗證並補預設：永遠回傳畫得出來的外觀（不認得的體型 → 人形骷髏；不認得的款式 → 該體型的預設款）。 */
export function resolveSummonLook(look: SummonLookDraw | null | undefined): ResolvedLook {
  const body = BODIES.find((b) => b === look?.body);
  if (look == null || body === undefined) return { body: "humanoid", variant: "skeleton", element: undefined, size: "medium", trait: undefined };
  const variants = VARIANTS[body];
  const variant = variants.find((v) => v === look.variant) ?? variants[0] ?? "";
  const element = look.element != null && SUMMON_KEYWORDS.includes(look.element) ? look.element : undefined;
  const size: SummonSize = look.size === "small" || look.size === "large" ? look.size : "medium";
  return { body, variant, element, size, trait: look.trait ?? undefined };
}

/** 這個外觀不畫陣營底圈（土牆）。 */
export function hasNoRing(look: ResolvedLook): boolean {
  return look.body === "construct" && look.variant === "wall";
}

/** 貼圖快取鍵（外觀＋朝向；殘影另加召喚者外觀鍵）。 */
export function summonKey(look: ResolvedLook, facing: Facing, ownerKey = ""): string {
  const copy = look.variant === "afterimage" ? ownerKey : "";
  return [look.body, look.variant, look.element ?? "", look.size, look.trait ?? "", facing, copy].join("|");
}

const light = (c: string, t = 0.3): string => mix(c, "#ffffff", t);
const elemColor = (s: ResolvedLook, fallback: string): string => (s.element !== undefined ? KEYWORD_COLOR[s.element] : undefined) ?? fallback;

/** 矩形的四個角點（搭配 `sharp: true` 畫石塊、木柱）。 */
const box = (x0: number, y0: number, x1: number, y1: number): Pt[] => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

/** `side`：東 1、西 -1、南 0、北 `null`（背面不畫眼睛）。 */
type Side = 1 | -1 | 0 | null;

function sideOf(facing: Facing): Side {
  if (facing === "north") return null;
  if (facing === "east") return 1;
  if (facing === "west") return -1;
  return 0;
}

function eyes(ctx: Ctx, side: Side, y: number, c = "#ffffff", gap = 3): void {
  if (side === null) return;
  const x = side * 2.4;
  dot(ctx, x - gap, y, 1.5, 1.7, c);
  dot(ctx, x + gap, y, 1.5, 1.7, c);
}

// ---- 漂浮靈：水滴身體＋元素邊緣＋粒子；底下只有小影子 ----
const DROP: readonly Pt[] = [[0, -30], [6, -24], [10, -17], [9, -9], [4, -3], [0, -1], [-4, -3], [-9, -9], [-10, -17], [-6, -24]];

function spiritEdge(ctx: Ctx, s: ResolvedLook, c: string): void {
  if (s.element === "ignite") {
    for (const [x, h] of [[-5, 9], [0, 12], [5, 8]] as const) {
      ink(ctx, `sp-flame-${x}`, [[x - 3, -24], [x, -24 - h], [x + 1, -26 - h], [x + 3, -24 - h / 2], [x + 3, -24]], c, { sharp: true, shade: false, w: 0.6 });
    }
  } else if (s.element === "frozen") {
    for (const [x, y, a] of [[-8, -20, -0.6], [8, -20, 0.6], [0, -31, 0]] as const) {
      const rot = (px: number, py: number): Pt => [x + px * Math.cos(a) - py * Math.sin(a), y + px * Math.sin(a) + py * Math.cos(a)];
      ink(ctx, `sp-ice-${x}`, [rot(0, -6), rot(2.5, 0), rot(0, 3), rot(-2.5, 0)], light(c, 0.4), { sharp: true, shade: false, w: 0.6 });
    }
  } else if (s.element === "charged") {
    for (const sx of [-1, 1]) {
      const pts: Pt[] = [[sx * 8, -26], [sx * 12, -21], [sx * 9, -18], [sx * 14, -12]];
      stroke(ctx, `sp-bolt-i${sx}`, pts, 3, INK);
      stroke(ctx, `sp-bolt-${sx}`, pts, 1.5, c);
    }
  } else if (s.element === "wet") {
    for (const [x, y] of [[-10, -12], [10, -16], [7, -27]] as const) {
      ink(ctx, `sp-drop-${x}`, [[x, y - 3], [x + 2.5, y + 1], [x, y + 2], [x - 2.5, y + 1]], c, { shade: false, w: 0.6 });
    }
  }
}

function spirit(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = elemColor(s, "#c8ccd4");
  ctx.save();
  ctx.translate(0, -8);
  const g = ctx.createRadialGradient(0, -14, 2, 0, -14, 18);
  g.addColorStop(0, `${c}99`);
  g.addColorStop(1, `${c}00`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, -14, 18, 0, TAU);
  ctx.fill();
  ink(ctx, "sp-body", DROP, mix(c, "#ffffff", 0.25), { alpha: 0.9 });
  ink(ctx, "sp-shine", ellPts(-3, -16, 3, 5, 10), light(c, 0.7), { shade: false, line: false, alpha: 0.8 });
  spiritEdge(ctx, s, c);
  eyes(ctx, side, -17, "#1d1a22", 2.6);
  ctx.restore();
}

// ---- 構造體：石像、爆裂傀儡、土牆 ----
function constructWall(ctx: Ctx): void {
  ink(ctx, "wall-body", box(-15, -24, 15, -1), "#6e5a40", { sharp: true });
  ink(ctx, "wall-top", box(-15, -26, 15, -20), "#8c7350", { sharp: true });
  for (const [x0, y0, x1, y1] of [[-15, -14, 15, -14], [-5, -20, -5, -14], [6, -14, 6, -2], [-10, -14, -10, -2]] as const) {
    stroke(ctx, `wall-crack-${x0}-${y0}`, [[x0, y0], [x1, y1]], 0.8, "#4a3a28");
  }
}

function constructBomb(ctx: Ctx, c: string, side: Side): void {
  for (const sx of [-1, 1]) ink(ctx, `bomb-leg-${sx}`, box(sx * 4 - 2, -6, sx * 4 + 2, 0), "#5a4a3a", { sharp: true, w: 0.7 });
  ink(ctx, "bomb-body", ellPts(0, -15, 10, 10, 14), "#6a5a4a");
  ctx.save();
  ctx.shadowColor = c;
  ctx.shadowBlur = 4;
  stroke(ctx, "bomb-crack-a", [[-6, -20], [-2, -15], [-5, -10]], 1.6, c);
  stroke(ctx, "bomb-crack-b", [[4, -22], [2, -16], [7, -12]], 1.6, c);
  ctx.restore();
  stroke(ctx, "bomb-fuse", [[3, -24], [7, -30], [4, -33]], 1.3, "#3a2a1c");
  ink(ctx, "bomb-spark", ellPts(4, -34, 2.2, 2.2, 8), "#ffe14d", { shade: false, w: 0.6 });
  dot(ctx, 4, -34, 1.1, 1.1, c);
  eyes(ctx, side, -15, c, 3);
}

function constructGolem(ctx: Ctx, c: string, side: Side): void {
  const st = "#9a968c";
  const sd = "#6c685f";
  for (const sx of [-1, 1]) ink(ctx, `golem-leg-${sx}`, box(sx * 6 - 3.5, -9, sx * 6 + 3.5, 0), sd, { sharp: true, w: 0.7 });
  ink(ctx, "golem-torso", box(-10, -26, 10, -8), st, { sharp: true });
  for (const sx of [-1, 1]) ink(ctx, `golem-arm-${sx}`, box(sx * 14 - 3.5, -25, sx * 14 + 3.5, -9), sd, { sharp: true, w: 0.7 });
  ink(ctx, "golem-head", box(-6, -36, 6, -26), st, { sharp: true });
  stroke(ctx, "golem-seam-h", [[-10, -17], [10, -17]], 0.7, sd);
  stroke(ctx, "golem-seam-v", [[0, -26], [0, -17]], 0.7, sd);
  ctx.save();
  ctx.shadowColor = c;
  ctx.shadowBlur = 4;
  eyes(ctx, side, -31, c, 2.4);
  ctx.restore();
}

function construct(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = elemColor(s, "#ffffff");
  if (s.variant === "wall") constructWall(ctx);
  else if (s.variant === "bomb") constructBomb(ctx, c, side);
  else constructGolem(ctx, c, side);
}

// ---- 野獸（側面骨架；朝南北時沿用東西的側面，朝西左右鏡像）----
function bird(ctx: Ctx, side: Side): void {
  ctx.translate(0, -22);
  const c = "#8a6a48";
  const d = "#5e4430";
  ink(ctx, "bird-wing-far", [[-2, -2], [-9, -10], [-20, -8], [-12, -4], [-4, 2]], d);
  ink(ctx, "bird-tail", [[-8, 0], [-14, -2], [-14, 3]], d, { sharp: true, w: 0.7 });
  ink(ctx, "bird-body", ellPts(0, 0, 8, 4.5, 12), c);
  ink(ctx, "bird-belly", ellPts(1, 1.5, 5, 2.4, 10), "#e6dcc8", { shade: false, line: false });
  ink(ctx, "bird-wing-near", [[2, -2], [8, -12], [18, -12], [12, -4], [4, 2]], d);
  ink(ctx, "bird-head", ellPts(8, -2, 3.5, 3.5, 10), c, { w: 0.7 });
  ink(ctx, "bird-beak", [[11, -3], [14, -1.5], [11, -0.5]], "#e8bb48", { sharp: true, shade: false, w: 0.6 });
  if (side !== null) dot(ctx, 9, -2.6, 0.9, 0.9, "#1d1a22");
  dot(ctx, 8, -9, 1.6, 1.6, KEYWORD_COLOR["marked"] ?? "#d06aff");
}

function wolf(ctx: Ctx, side: Side): void {
  const c = "#7a7a82";
  const d = "#55555c";
  for (const x of [-9, -5, 6, 10]) ink(ctx, `wolf-leg-${x}`, box(x - 1.6, -10, x + 1.6, 0), x < 0 ? d : c, { sharp: true, w: 0.7 });
  ink(ctx, "wolf-tail", [[-12, -15], [-20, -20], [-22, -12], [-17, -14], [-12, -11]], d);
  ink(ctx, "wolf-body", ellPts(0, -13, 13, 6, 14), c);
  ink(ctx, "wolf-belly", ellPts(2, -10, 8, 2.5, 10), "#b8b8be", { shade: false, line: false });
  for (const x of [10, 14]) ink(ctx, `wolf-ear-${x}`, [[x - 2, -23], [x, -28], [x + 2, -23]], d, { sharp: true, shade: false, w: 0.7 });
  ink(ctx, "wolf-head", ellPts(13, -19, 6, 5, 12), c);
  ink(ctx, "wolf-snout", [[16, -20], [23, -17], [16, -15]], c, { sharp: true, shade: false, w: 0.7 });
  ink(ctx, "wolf-collar", box(8, -16, 14, -14), "#b83a3a", { sharp: true, shade: false, w: 0.6 });
  if (side !== null) dot(ctx, 16, -20, 1.1, 1.1, "#ffe14d");
}

function beast(ctx: Ctx, s: ResolvedLook, side: Side): void {
  ctx.save();
  ctx.scale(side === -1 ? -1 : 1, 1);
  if (s.variant === "bird") bird(ctx, side);
  else wolf(ctx, side);
  ctx.restore();
}

// ---- 植物：藤蔓貼地、捲曲＋刺＋葉 ----
function plant(ctx: Ctx): void {
  for (const [a, len] of [[-2.6, 16], [-1.9, 18], [-1.2, 15], [-0.5, 17], [0.2, 14], [-3.2, 13]] as const) {
    const x = Math.cos(a) * len;
    const y = -3 + Math.sin(a) * len * 0.55 - 6;
    const stem: Pt[] = [[0, -3], [x * 0.5, y - 8], [x, y]];
    stroke(ctx, `vine-stem-i${a}`, stem, 4, INK);
    stroke(ctx, `vine-stem-${a}`, stem, 2.6, "#3f6a2a");
    const leaf = ellPts(0, 0, 3.2, 1.8, 10).map(([px, py]): Pt => [x + px * Math.cos(a) - py * Math.sin(a), y + px * Math.sin(a) + py * Math.cos(a)]);
    ink(ctx, `vine-leaf-${a}`, leaf, "#5f9a3c", { shade: false, w: 0.6 });
    ink(ctx, `vine-thorn-${a}`, [[x * 0.6, y * 0.7 - 3], [x * 0.6 + 2, y * 0.7 - 6], [x * 0.6 + 3, y * 0.7 - 3]], "#d0c8a0", { sharp: true, shade: false, w: 0.5 });
  }
  ink(ctx, "vine-base", ellPts(0, -4, 6, 3, 10), "#2f5020");
}

// ---- 圖騰：柱子＋頂端符號 ----
function totemTop(ctx: Ctx, s: ResolvedLook, c: string): void {
  if (s.variant === "war") {
    ink(ctx, "totem-pole", box(-0.8, -46, 0.8, -33), "#5e3b1f", { sharp: true, shade: false, w: 0.5 });
    ink(ctx, "totem-flag", [[0.8, -46], [12, -43], [0.8, -39]], "#c03030", { sharp: true, w: 0.7 });
    dot(ctx, 0, -36, 2.4, 2.4, c);
  } else if (s.variant === "pull") {
    ink(ctx, "totem-orb", ellPts(0, -39, 7, 7, 14), "#5a3f80");
    const spiral: Pt[] = [];
    for (let t = 0; t < 4 * Math.PI; t += 0.5) spiral.push([Math.cos(t) * (6 - t * 0.45), -39 + Math.sin(t) * (6 - t * 0.45)]);
    stroke(ctx, "totem-swirl", spiral, 1.2, "#d06aff");
  } else {
    ink(ctx, "totem-slab", [[-9, -36], [9, -36], [6, -41], [-6, -41]], "#b8b4aa", { sharp: true });
    ink(ctx, "totem-gem", [[0, -47], [4, -43], [-4, -43]], c, { sharp: true, shade: false, w: 0.7 });
  }
}

function totem(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = elemColor(s, "#ffffff");
  const plateau = s.variant === "plateau";
  const wood = plateau ? "#9a968c" : "#8a5a32";
  const wd = plateau ? "#6c685f" : "#5e3b1f";
  ink(ctx, "totem-body", box(-4.5, -34, 4.5, 0), wood, { sharp: true });
  for (const y of [-27, -16]) {
    ink(ctx, `totem-band-${y}`, box(-4.5, y, 4.5, y + 2), wd, { sharp: true, shade: false, w: 0.6 });
    if (side !== null) {
      dot(ctx, -1.7, y - 3, 0.9, 0.9, INK);
      dot(ctx, 1.7, y - 3, 0.9, 0.9, INK);
    }
  }
  totemTop(ctx, s, c);
}

/** 地面影子的半寬；人形（自己有影子）沒有。飛行的鷹隼影子留在地上、身體抬高。 */
function groundShadow(look: ResolvedLook): number | null {
  switch (look.body) {
    case "spirit":
      return 7;
    case "construct":
      return look.variant === "wall" ? 14 : look.variant === "bomb" ? 8 : 12;
    case "beast":
      return look.variant === "bird" ? 6 : 14;
    case "totem":
      return 8;
    case "plant":
      return 16;
    default:
      return null;
  }
}

/**
 * 地面影子、水精的水窪與圖騰光環（C 畫風）：影子是一排短斜線（`shadow()`），水窪與光環不描黑框；腳底中心為原點。
 */
export function drawSummonGround(ctx: Ctx, look: ResolvedLook): void {
  const rx = groundShadow(look);
  if (rx !== null) shadow(ctx, rx);
  if (look.body === "spirit" && look.trait === "puddle") {
    ink(ctx, "puddle", ellPts(0, -1, 13, 4, 18), "#4aa8ff", { alpha: 0.45, shade: false, w: 0.5 });
  }
  if (look.body === "totem" && look.trait === "aura") drawFormAura(ctx, elemColor(look, FORM_AURA_NEUTRAL), 20);
}

/**
 * 把「非人形」體型畫到 `ctx`（腳底中心為原點，往上是負；未套大小）。
 * 人形請用 `humanoidSpec` ＋ 紙娃娃；對人形呼叫時什麼都不畫。**不含地面影子**（見 `drawSummonGround`）。
 */
export function drawSummonBody(ctx: Ctx, look: ResolvedLook, facing: Facing): void {
  const side = sideOf(facing);
  withShadeDir(ctx, side === 0 ? 1 : -1, () => {
    switch (look.body) {
      case "spirit":
        spirit(ctx, look, side);
        break;
      case "construct":
        construct(ctx, look, side);
        break;
      case "beast":
        beast(ctx, look, side);
        break;
      case "plant":
        plant(ctx);
        break;
      case "totem":
        totem(ctx, look, side);
        break;
      case "humanoid":
        break;
    }
  });
}

// ---- 人形：沿用紙娃娃，依款式選範本與修飾 ----
/** 人形款式 → 紙娃娃規格（殘影用 `owner`＝召喚者的紙娃娃，沒有時用預設戰士）。 */
export function humanoidSpec(look: ResolvedLook, skeleton: DollSpec, owner: DollSpec | null): DollSpec {
  if (look.variant === "shade") {
    const gear: Gear = {
      body: { kind: "leather", material: "leather", color: "#2a2632" },
      head: { kind: "hood", material: "cloth", color: "#1f1c26" },
      main_hand: { kind: "dagger", material: "steel" },
      off_hand: { kind: "dagger", material: "steel" },
      feet: { kind: "boots", material: "leather", color: "#1f1c26" },
    };
    return { look: { skin: "#3a3448", eyes: "#d06aff", hair: "none" }, gear };
  }
  if (look.variant === "guardian") {
    return {
      look: { skin: "#f4ecd0", hair: "long", hairColor: "#fff3c4", eyes: "#fffbe6" },
      gear: {
        body: { kind: "robe", material: "cloth", color: "#f2e6c8" },
        off_hand: { kind: "shield_round", material: "gold" },
        feet: { kind: "shoes", material: "cloth", color: "#e8dcc0" },
      },
    };
  }
  if (look.variant === "afterimage") return owner ?? skeleton;
  if (look.trait === "shield") {
    return { ...skeleton, gear: { ...skeleton.gear, off_hand: { kind: "shield_round", material: "wood", color: "#6a5a4a" } } };
  }
  return skeleton;
}

interface HumanoidStyle {
  alpha: number;
  glow?: string;
  tint?: string;
}

const HUMANOID_STYLE: Readonly<Record<string, HumanoidStyle>> = {
  shade: { alpha: 0.72, glow: "#7a4ab0" },
  guardian: { alpha: 0.8, glow: "#ffe9a8" },
  afterimage: { alpha: 0.5, tint: "#8fc8ff", glow: "#8fc8ff" },
};

/** 人形召喚物用紙娃娃的畫布大小（DOLL_*，C 骨架）；其他體型沿用舊的 64×64（SUMMON_*）。 */
function makeCanvas(dpr: number, humanoid = false): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = (humanoid ? DOLL_W : SUMMON_W) * dpr;
  c.height = (humanoid ? DOLL_H : SUMMON_H) * dpr;
  return c;
}

function humanoidCanvas(look: ResolvedLook, facing: Facing, spec: DollSpec, dpr: number): HTMLCanvasElement | null {
  const fig = renderFigureCanvas(spec, facing, false, dpr);
  if (fig === null) return null;
  const style = HUMANOID_STYLE[look.variant];
  if (style === undefined) return fig;
  const out = makeCanvas(dpr, true);
  const ctx = out.getContext("2d");
  if (ctx === null) return null;
  let src: HTMLCanvasElement = fig;
  if (style.tint !== undefined) {
    // 色調只蓋在身體上（source-atop 不會染到透明處）
    const tinted = makeCanvas(dpr, true);
    const t = tinted.getContext("2d");
    if (t !== null) {
      t.drawImage(fig, 0, 0);
      t.globalCompositeOperation = "source-atop";
      t.fillStyle = `${style.tint}88`;
      t.fillRect(0, 0, tinted.width, tinted.height);
      src = tinted;
    }
  }
  if (style.glow !== undefined) {
    ctx.shadowColor = style.glow;
    ctx.shadowBlur = 8 * dpr;
  }
  ctx.globalAlpha = style.alpha;
  ctx.drawImage(src, 0, 0);
  return out;
}

/** 非人形召喚物的貼圖：地面影子＋身體（C 畫風：墨線取代黑色剪影外框；藤蔓整體半透明 0.9）。 */
function bodyCanvas(look: ResolvedLook, facing: Facing, dpr: number): HTMLCanvasElement | null {
  const size = SIZE_SCALE[look.size];
  const off = makeCanvas(dpr);
  const o = off.getContext("2d");
  const out = makeCanvas(dpr);
  const ctx = out.getContext("2d");
  if (o === null || ctx === null) return null;
  for (const c of [o, ctx]) {
    c.scale(dpr, dpr);
    c.translate(SUMMON_W / 2, SUMMON_FOOT_Y);
    c.scale(size, size);
  }
  drawSummonBody(o, look, facing);
  drawSummonGround(ctx, look);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = look.body === "plant" ? 0.9 : 1;
  ctx.drawImage(off, 0, 0);
  return out;
}


/**
 * 產生召喚物貼圖用的離屏 canvas（人形與紙娃娃同尺寸 DOLL_W×DOLL_H；其他體型 SUMMON_W×SUMMON_H，腳底在 (W/2, FOOT_Y)）。
 * 人形用 `humanoid`（已解析好的紙娃娃規格）；沒有 DOM 時回傳 `null`。
 */
export function renderSummonCanvas(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null, dpr: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  if (look.body === "humanoid") return humanoid === null ? null : humanoidCanvas(look, facing, humanoid, dpr);
  return bodyCanvas(look, facing, dpr);
}

/** 關鍵字 → 色（`0xRRGGBB` 數字，給 Pixi 用）。 */
export function keywordColorNumber(element: string | undefined): number | undefined {
  const hex = element === undefined ? undefined : KEYWORD_COLOR[element];
  return hex === undefined ? undefined : parseInt(hex.slice(1), 16);
}
