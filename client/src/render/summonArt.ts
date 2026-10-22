// 召喚物外觀渲染器（Phase 3-33h1；來源：美術 PM 的 docs/art/sample/summonArt.js 與 docs/art/召喚物外觀.md）。
// 體型 × 款式 × 元素配色 × 大小 × 特徵。座標和紙娃娃相同：腳底中心為原點，往上是負，身高約 46。
// 人形體型直接用紙娃娃（再依款式合成透明度、色調、外光）；其他五種體型在這裡程式繪製，畫到離屏後加深色外框。
// 任何輸入（含不認得的體型、款式、元素、大小）都畫得出來：不認得的退回人形骷髏，不丟例外。
import type { Facing } from "../api/types";
import type { Ctx } from "./artDraw";
import type { DollSpec, Gear } from "./appearance";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W, renderFigureCanvas } from "./paperdoll";

const TAU = Math.PI * 2;
const INK = "#16121a";

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

/** 關鍵字色票（關鍵字 ID → 色；來源樣張的 KW，ID 換成 `skill_keywords.yaml` 的正式 ID）。 */
export const KEYWORD_COLOR: Readonly<Record<string, string>> = {
  ignite: "#ff6a1a",
  wet: "#4aa8ff",
  charged: "#fff36b",
  frozen: "#8fe3ff",
  prone: "#e0b080",
  collision: "#ff9a4a",
  marked: "#d06aff",
  high_ground: "#ffe9a8",
  concealed: "#a0a0c8",
  summon: "#7dffb0",
};

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
  const element = look.element != null && look.element in KEYWORD_COLOR ? look.element : undefined;
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

function mix(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const m = (s: number): number => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
}

function fill(ctx: Ctx, c: string | CanvasGradient, path: () => void): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  path();
  ctx.fill();
}

function shadow(ctx: Ctx, rx: number, ry = rx * 0.35, y = -1, a = 0.3): void {
  fill(ctx, `rgba(0,0,0,${a})`, () => ctx.ellipse(0, y, rx, ry, 0, 0, TAU));
}

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
  fill(ctx, c, () => {
    ctx.arc(x - gap, y, 1.6, 0, TAU);
    ctx.arc(x + gap, y, 1.6, 0, TAU);
  });
}

// ---- 漂浮靈：水滴身體＋元素邊緣＋粒子；底下只有小影子 ----
function spirit(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = (s.element !== undefined ? KEYWORD_COLOR[s.element] : undefined) ?? "#c8ccd4";
  ctx.save();
  ctx.translate(0, -8);
  const g = ctx.createRadialGradient(0, -14, 2, 0, -14, 18);
  g.addColorStop(0, `${c}99`);
  g.addColorStop(1, `${c}00`);
  fill(ctx, g, () => ctx.arc(0, -14, 18, 0, TAU));
  const body = (): void => {
    ctx.moveTo(0, -30);
    ctx.quadraticCurveTo(11, -18, 9, -9);
    ctx.quadraticCurveTo(0, 0, -9, -9);
    ctx.quadraticCurveTo(-11, -18, 0, -30);
  };
  fill(ctx, mix(c, "#ffffff", 0.25), body);
  fill(ctx, mix(c, "#ffffff", 0.7), () => ctx.ellipse(-3, -16, 3, 5, -0.3, 0, TAU));
  ctx.strokeStyle = c;
  if (s.element === "ignite") {
    for (const [x, h] of [[-5, 9], [0, 12], [5, 8]] as const) {
      fill(ctx, c, () => {
        ctx.moveTo(x - 3, -24);
        ctx.quadraticCurveTo(x, -24 - h, x + 1, -26 - h);
        ctx.quadraticCurveTo(x + 3, -24 - h / 2, x + 3, -24);
      });
    }
  }
  if (s.element === "frozen") {
    for (const [x, y, a] of [[-8, -20, -0.6], [8, -20, 0.6], [0, -31, 0]] as const) {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(a);
      fill(ctx, mix(c, "#ffffff", 0.4), () => {
        ctx.moveTo(0, -6);
        ctx.lineTo(2.5, 0);
        ctx.lineTo(0, 3);
        ctx.lineTo(-2.5, 0);
        ctx.closePath();
      });
      ctx.restore();
    }
  }
  if (s.element === "charged") {
    ctx.lineWidth = 1.6;
    for (const sx of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(sx * 8, -26);
      ctx.lineTo(sx * 12, -21);
      ctx.lineTo(sx * 9, -18);
      ctx.lineTo(sx * 14, -12);
      ctx.stroke();
    }
  }
  if (s.element === "wet") {
    for (const [x, y] of [[-10, -12], [10, -16], [7, -27]] as const) {
      fill(ctx, c, () => {
        ctx.moveTo(x, y - 3);
        ctx.quadraticCurveTo(x + 2.5, y + 1, x, y + 2);
        ctx.quadraticCurveTo(x - 2.5, y + 1, x, y - 3);
      });
    }
  }
  eyes(ctx, side, -17, "#1d1a22", 2.6);
  ctx.restore();
}

// ---- 構造體：石像、爆裂傀儡、土牆 ----
function constructWall(ctx: Ctx): void {
  fill(ctx, "#6e5a40", () => ctx.roundRect(-15, -24, 30, 23, 2));
  fill(ctx, "#8c7350", () => ctx.roundRect(-15, -26, 30, 6, 2));
  ctx.strokeStyle = "#4a3a28";
  ctx.lineWidth = 1;
  for (const [x0, y0, x1, y1] of [[-15, -14, 15, -14], [-5, -20, -5, -14], [6, -14, 6, -2], [-10, -14, -10, -2]] as const) {
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
  }
}

function constructBomb(ctx: Ctx, c: string, side: Side): void {
  for (const sx of [-1, 1]) fill(ctx, "#5a4a3a", () => ctx.roundRect(sx * 4 - 2, -6, 4, 6, 1));
  fill(ctx, "#6a5a4a", () => ctx.arc(0, -15, 10, 0, TAU));
  ctx.strokeStyle = c;
  ctx.lineWidth = 1.6;
  ctx.shadowColor = c;
  ctx.shadowBlur = 4;
  const cracks: ReadonlyArray<ReadonlyArray<readonly [number, number]>> = [
    [[-6, -20], [-2, -15], [-5, -10]],
    [[4, -22], [2, -16], [7, -12]],
  ];
  for (const pts of cracks) {
    ctx.beginPath();
    pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
    ctx.stroke();
  }
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "#3a2a1c";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(3, -24);
  ctx.quadraticCurveTo(7, -30, 4, -33);
  ctx.stroke();
  fill(ctx, "#ffe14d", () => ctx.arc(4, -34, 2.2, 0, TAU));
  fill(ctx, c, () => ctx.arc(4, -34, 1.2, 0, TAU));
  eyes(ctx, side, -15, c, 3);
}

function constructGolem(ctx: Ctx, c: string, side: Side): void {
  const st = "#9a968c";
  const sd = "#6c685f";
  for (const sx of [-1, 1]) fill(ctx, sd, () => ctx.roundRect(sx * 6 - 3.5, -9, 7, 9, 1.5));
  fill(ctx, st, () => ctx.roundRect(-10, -26, 20, 18, 3));
  for (const sx of [-1, 1]) fill(ctx, sd, () => ctx.roundRect(sx * 14 - 3.5, -25, 7, 16, 2));
  fill(ctx, st, () => ctx.roundRect(-6, -36, 12, 10, 2.5));
  ctx.strokeStyle = sd;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-10, -17);
  ctx.lineTo(10, -17);
  ctx.moveTo(0, -26);
  ctx.lineTo(0, -17);
  ctx.stroke();
  ctx.shadowColor = c;
  ctx.shadowBlur = 4;
  eyes(ctx, side, -31, c, 2.4);
  ctx.shadowBlur = 0;
}

function construct(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = (s.element !== undefined ? KEYWORD_COLOR[s.element] : undefined) ?? "#ffffff";
  if (s.variant === "wall") constructWall(ctx);
  else if (s.variant === "bomb") constructBomb(ctx, c, side);
  else constructGolem(ctx, c, side);
}

// ---- 野獸（側面骨架；朝南北時沿用東西的側面，朝西左右鏡像）----
function bird(ctx: Ctx, side: Side): void {
  ctx.translate(0, -22);
  const c = "#8a6a48";
  const d = "#5e4430";
  fill(ctx, d, () => {
    ctx.moveTo(-2, -2);
    ctx.quadraticCurveTo(-12, -14, -20, -8);
    ctx.quadraticCurveTo(-12, -4, -4, 2);
  });
  fill(ctx, d, () => {
    ctx.moveTo(2, -2);
    ctx.quadraticCurveTo(10, -16, 18, -12);
    ctx.quadraticCurveTo(12, -4, 4, 2);
  });
  fill(ctx, c, () => ctx.ellipse(0, 0, 8, 4.5, 0, 0, TAU));
  fill(ctx, "#e6dcc8", () => ctx.ellipse(1, 1.5, 5, 2.4, 0, 0, TAU));
  fill(ctx, c, () => ctx.arc(8, -2, 3.5, 0, TAU));
  fill(ctx, "#e8bb48", () => {
    ctx.moveTo(11, -3);
    ctx.lineTo(14, -1.5);
    ctx.lineTo(11, -0.5);
    ctx.closePath();
  });
  fill(ctx, d, () => {
    ctx.moveTo(-8, 0);
    ctx.lineTo(-14, -2);
    ctx.lineTo(-14, 3);
    ctx.closePath();
  });
  if (side !== null) fill(ctx, "#1d1a22", () => ctx.arc(9, -2.6, 0.9, 0, TAU));
  fill(ctx, KEYWORD_COLOR.marked ?? "#d06aff", () => ctx.arc(8, -9, 1.6, 0, TAU));
}

function wolf(ctx: Ctx, side: Side): void {
  const c = "#7a7a82";
  const d = "#55555c";
  for (const x of [-9, -5, 6, 10]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 1.6, -10, 3.2, 10, 1.2));
  fill(ctx, c, () => ctx.ellipse(0, -13, 13, 6, 0, 0, TAU));
  fill(ctx, "#b8b8be", () => ctx.ellipse(2, -10, 8, 2.5, 0, 0, TAU));
  fill(ctx, d, () => {
    ctx.moveTo(-12, -15);
    ctx.quadraticCurveTo(-20, -20, -22, -12);
    ctx.quadraticCurveTo(-17, -14, -12, -11);
  });
  fill(ctx, c, () => ctx.ellipse(13, -19, 6, 5, -0.3, 0, TAU));
  fill(ctx, c, () => {
    ctx.moveTo(16, -20);
    ctx.lineTo(23, -17);
    ctx.lineTo(16, -15);
    ctx.closePath();
  });
  for (const x of [10, 14]) {
    fill(ctx, d, () => {
      ctx.moveTo(x - 2, -23);
      ctx.lineTo(x, -28);
      ctx.lineTo(x + 2, -23);
      ctx.closePath();
    });
  }
  if (side !== null) fill(ctx, "#ffe14d", () => ctx.arc(16, -20, 1.1, 0, TAU));
  fill(ctx, "#b83a3a", () => ctx.roundRect(8, -16, 6, 2, 1)); // 戰狼的項圈
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
  ctx.lineCap = "round";
  for (const [a, len] of [[-2.6, 16], [-1.9, 18], [-1.2, 15], [-0.5, 17], [0.2, 14], [-3.2, 13]] as const) {
    ctx.strokeStyle = "#3f6a2a";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, -3);
    const x = Math.cos(a) * len;
    const y = -3 + Math.sin(a) * len * 0.55 - 6;
    ctx.quadraticCurveTo(x * 0.5, y - 8, x, y);
    ctx.stroke();
    fill(ctx, "#5f9a3c", () => ctx.ellipse(x, y, 3.2, 1.8, a, 0, TAU));
    fill(ctx, "#d0c8a0", () => {
      ctx.moveTo(x * 0.6, y * 0.7 - 3);
      ctx.lineTo(x * 0.6 + 2, y * 0.7 - 6);
      ctx.lineTo(x * 0.6 + 3, y * 0.7 - 3);
      ctx.closePath();
    });
  }
  ctx.lineCap = "butt";
  fill(ctx, "#2f5020", () => ctx.ellipse(0, -4, 6, 3, 0, 0, TAU));
}

// ---- 圖騰：柱子＋頂端符號 ----
function totem(ctx: Ctx, s: ResolvedLook, side: Side): void {
  const c = (s.element !== undefined ? KEYWORD_COLOR[s.element] : undefined) ?? "#ffffff";
  if (s.trait === "aura") {
    ctx.strokeStyle = `${c}aa`;
    ctx.lineWidth = 1.4;
    ctx.setLineDash([3, 2]);
    ctx.beginPath();
    ctx.ellipse(0, -1, 20, 6, 0, 0, TAU);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  const plateau = s.variant === "plateau";
  const wood = plateau ? "#9a968c" : "#8a5a32";
  const wd = plateau ? "#6c685f" : "#5e3b1f";
  fill(ctx, wood, () => ctx.roundRect(-4.5, -34, 9, 34, 2));
  for (const y of [-27, -16]) {
    fill(ctx, wd, () => ctx.rect(-4.5, y, 9, 2));
    if (side !== null) {
      fill(ctx, INK, () => {
        ctx.rect(-2.6, y - 4, 1.8, 1.8);
        ctx.rect(0.8, y - 4, 1.8, 1.8);
      });
    }
  }
  if (s.variant === "war") {
    fill(ctx, "#5e3b1f", () => ctx.rect(-0.8, -46, 1.6, 13));
    fill(ctx, "#c03030", () => {
      ctx.moveTo(0.8, -46);
      ctx.lineTo(12, -43);
      ctx.lineTo(0.8, -39);
      ctx.closePath();
    });
    fill(ctx, c, () => ctx.arc(0, -36, 2.4, 0, TAU));
  } else if (s.variant === "pull") {
    fill(ctx, "#5a3f80", () => ctx.arc(0, -39, 7, 0, TAU));
    ctx.strokeStyle = "#d06aff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let t = 0; t < 4 * Math.PI; t += 0.2) {
      const r = 6 - t * 0.45;
      ctx.lineTo(Math.cos(t) * r, -39 + Math.sin(t) * r);
    }
    ctx.stroke();
  } else {
    fill(ctx, "#b8b4aa", () => {
      ctx.moveTo(-9, -36);
      ctx.lineTo(9, -36);
      ctx.lineTo(6, -41);
      ctx.lineTo(-6, -41);
      ctx.closePath();
    });
    fill(ctx, c, () => {
      ctx.moveTo(0, -47);
      ctx.lineTo(4, -43);
      ctx.lineTo(-4, -43);
      ctx.closePath();
    });
  }
}

/** 地面影子的橢圓參數 `[rx, ry, 透明度]`；人形與植物（自己貼地）沒有。飛行的鷹隼影子留在地上、身體抬高。 */
function groundShadow(look: ResolvedLook): readonly [number, number, number] | null {
  switch (look.body) {
    case "spirit":
      return [8, 3, 0.25];
    case "construct":
      return look.variant === "wall" ? [15, 4, 0.3] : look.variant === "bomb" ? [9, 3.15, 0.3] : [13, 4.55, 0.3];
    case "beast":
      return look.variant === "bird" ? [7, 2.5, 0.22] : [15, 4, 0.3];
    case "totem":
      return [8, 2.8, 0.3];
    default:
      return null;
  }
}

/**
 * 地面影子與水精的水窪（Phase 3-33h2）：畫在**不加外框**的那一層（透明度 0.22～0.3、不描邊），
 * 才不會被 8 方向深色外框描成一塊實心黑橢圓。腳底中心為原點。
 */
export function drawSummonGround(ctx: Ctx, look: ResolvedLook): void {
  const sh = groundShadow(look);
  if (sh !== null) shadow(ctx, sh[0], sh[1], -1, sh[2]);
  if (look.body === "spirit" && look.trait === "puddle") fill(ctx, "rgba(74,168,255,0.45)", () => ctx.ellipse(0, -1, 13, 4, 0, 0, TAU));
  if (look.body === "plant") fill(ctx, "rgba(40,70,30,0.35)", () => ctx.ellipse(0, -2, 18, 6, 0, 0, TAU)); // 藤蔓底影：不加外框，透明度 0.35
}

/**
 * 把「非人形」體型畫到 `ctx`（腳底中心為原點，往上是負；未套大小與外框）。
 * 人形請用 `humanoidSpec` ＋ 紙娃娃；對人形呼叫時什麼都不畫。**不含地面影子**（見 `drawSummonGround`）。
 */
export function drawSummonBody(ctx: Ctx, look: ResolvedLook, facing: Facing): void {
  const side = sideOf(facing);
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

function makeCanvas(dpr: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = DOLL_W * dpr;
  c.height = DOLL_H * dpr;
  return c;
}

function humanoidCanvas(look: ResolvedLook, facing: Facing, spec: DollSpec, dpr: number): HTMLCanvasElement | null {
  const fig = renderFigureCanvas(spec, facing, false, dpr);
  if (fig === null) return null;
  const style = HUMANOID_STYLE[look.variant];
  if (style === undefined) return fig;
  const out = makeCanvas(dpr);
  const ctx = out.getContext("2d");
  if (ctx === null) return null;
  let src: HTMLCanvasElement = fig;
  if (style.tint !== undefined) {
    // 色調只蓋在身體上（source-atop 不會染到透明處）
    const tinted = makeCanvas(dpr);
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

function bodyCanvas(look: ResolvedLook, facing: Facing, dpr: number): HTMLCanvasElement | null {
  const size = SIZE_SCALE[look.size];
  const off = makeCanvas(dpr);
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(DOLL_W / 2, DOLL_FOOT_Y);
  o.scale(size, size);
  drawSummonBody(o, look, facing);
  const sil = makeCanvas(dpr);
  const sc = sil.getContext("2d");
  const out = makeCanvas(dpr);
  const ctx = out.getContext("2d");
  if (sc === null || ctx === null) return null;
  sc.drawImage(off, 0, 0);
  sc.globalCompositeOperation = "source-in";
  sc.fillStyle = INK;
  sc.fillRect(0, 0, sil.width, sil.height);
  const k = 1.3 * size * dpr;
  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.translate(DOLL_W / 2, DOLL_FOOT_Y);
  ctx.scale(size, size);
  drawSummonGround(ctx, look); // 影子在外框那層之外：透明、不描邊
  ctx.restore();
  ctx.globalAlpha = look.body === "plant" ? 0.9 : 1;
  for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]] as const) ctx.drawImage(sil, ox * k, oy * k);
  ctx.drawImage(off, 0, 0);
  return out;
}

/**
 * 產生召喚物貼圖用的離屏 canvas（與紙娃娃同尺寸、同腳底位置：DOLL_W×DOLL_H，腳底在 (DOLL_W/2, DOLL_FOOT_Y)）。
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
