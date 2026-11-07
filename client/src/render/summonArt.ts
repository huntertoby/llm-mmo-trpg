// 召喚物外觀渲染器（Phase 3-33h1；QK-3 起換成 Q 版：docs/art/sample/qSummon.js，圖 docs/art/shots/misc/q-summons-forms.png）。
// 體型 × 款式 × 元素配色 × 大小 × 特徵。座標和紙娃娃相同：腳底中心為原點，往上是負，身高和 Q 版主角同一套。
// 人形體型直接用 Q 版紙娃娃（再依款式合成半透明＋整隻染色；**不發外光**，外光只代表頭目）；其他五種體型在 qSummon.ts 畫，離屏後描剪影外框。
// 任何輸入（含不認得的體型、款式、元素、大小）都畫得出來：不認得的退回人形骷髏，不丟例外。
import type { Facing } from "../api/types";
import type { Ctx } from "./artDraw";
import type { DollSpec, Gear } from "./appearance";
import { KEYWORD_COLOR } from "./palette";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, renderFigureCanvas } from "./paperdoll";
import { drawQSummonAura, drawQSummonBody, drawQSummonGround, qSummonRing } from "./qSummon";
import { layer } from "./qSummonCore";


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
  humanoid: ["skeleton", "shade", "afterimage", "guardian", "mist_shade"],
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

/** 這個人形款式複製召喚者的紙娃娃：殘影（afterimage）與霧影（mist_shade，5F-ART1）。 */
export function copiesOwner(variant: string | null | undefined): boolean {
  return variant === "afterimage" || variant === "mist_shade";
}

/** 貼圖快取鍵（外觀＋朝向；殘影與霧影另加召喚者外觀鍵）。 */
export function summonKey(look: ResolvedLook, facing: Facing, ownerKey = ""): string {
  const copy = copiesOwner(look.variant) ? ownerKey : "";
  return [look.body, look.variant, look.element ?? "", look.size, look.trait ?? "", facing, copy].join("|");
}

/** Q 版非人形召喚物的貼圖畫布（虛擬像素＝紙娃娃單位，戰場縮放同紙娃娃 DOLL_SCALE）：寬 96、高 80、腳底在 70。 */
export const Q_SUMMON_W = 96;
export const Q_SUMMON_H = 80;
export const Q_SUMMON_FOOT_Y = 70;

/** 戰場陣營底圈的半徑（紙娃娃單位；unitSprite 的格 × 0.36 ÷ DOLL_SCALE）。 */
const TEAM_RING_U = (52 * 0.36) / DOLL_SCALE;

/** 離屏一層的範圍（單位，同樣張 BOX）。 */
const BOX = [-46, -78, 46, 14] as const;

/**
 * 地面（未套大小）：水精的一攤水、地面影子；戰意圖騰的虛線光環（大小 max(1, size×0.9)）。人形什麼都不畫（影子由紙娃娃畫）。
 * 陣營環由戰場畫（unitSprite，半徑見 `summonRingSize`）。
 */
export function drawSummonGround(ctx: Ctx, look: ResolvedLook): void {
  if (look.body === "humanoid") return;
  const sz = SIZE_SCALE[look.size];
  if (look.body === "totem" && look.trait === "aura") {
    ctx.save();
    const a = Math.max(1, sz * 0.9);
    ctx.scale(a, a);
    drawQSummonAura(ctx, Math.max(17, TEAM_RING_U / a + 2.6)); // 在戰場的陣營底圈外面
    ctx.restore();
  }
  ctx.save();
  ctx.scale(sz, sz);
  drawQSummonGround(ctx, look);
  ctx.restore();
}

/**
 * 把「非人形」體型畫到 `ctx`（腳底中心為原點，往上是負；未套大小、不描外框）。
 * 人形請用 `humanoidSpec` ＋ 紙娃娃；對人形呼叫時什麼都不畫。**不含地面**（見 `drawSummonGround`）。
 */
export function drawSummonBody(ctx: Ctx, look: ResolvedLook, facing: Facing): void {
  drawQSummonBody(ctx, look, facing);
}

/** 陣營環（樣張審查第 3 輪：比身體寬）：半徑與中心往前移（單位，已含大小；朝西、朝北的野獸往 −x）。 */
export function summonRingSize(look: ResolvedLook, facing: Facing): { rx: number; dx: number } {
  const r = qSummonRing(look, SIZE_SCALE[look.size]);
  const back = look.body === "beast" && (facing === "west" || facing === "north");
  return { rx: r.rx, dx: back ? -r.dx : r.dx };
}

// ---- 人形：沿用 Q 版紙娃娃，依款式選外觀與合成 ----
/** 人形款式 → 紙娃娃規格（骷髏照範本；影魅、守護靈照樣張 qSummon.js；殘影、霧影用 `owner`＝召喚者的紙娃娃，沒有時用骷髏）。 */
export function humanoidSpec(look: ResolvedLook, skeleton: DollSpec, owner: DollSpec | null): DollSpec {
  if (look.variant === "shade") {
    const gear: Gear = {
      head: { kind: "hood", material: "cloth", color: "#2e2440" },
      body: { kind: "leather", material: "leather", color: "#3a3050" },
      feet: { kind: "boots", material: "leather", color: "#2a2236" },
      main_hand: { kind: "dagger", material: "steel" },
      off_hand: { kind: "dagger", material: "steel" },
    };
    return { look: { skin: "#7a6a9a", eyes: "#e8d0ff", hair: "none" }, gear };
  }
  if (look.variant === "guardian") {
    return {
      look: { skin: "#f4ecd8", hair: "short", hairColor: "#e8d8a0", eyes: "#6a5a2a" },
      gear: {
        head: { kind: "helmet", material: "steel", color: "#e8dcae" },
        body: { kind: "plate", material: "steel", color: "#e8dcae" },
        feet: { kind: "greaves", material: "steel", color: "#d8cc9e" },
        main_hand: { kind: "sword", material: "gold" },
        off_hand: { kind: "shield_kite", material: "iron", color: "#f0e6c0" },
      },
    };
  }
  if (look.variant === "afterimage") return owner ?? skeleton;
  if (look.variant === "mist_shade") {
    // 霧影不帶本體的外光（外光只代表頭目，docs/archive/art/霧影外觀.md 第 5 點）
    const { rarity: _glow, ...plain } = owner ?? skeleton;
    return plain;
  }
  if (look.trait === "shield") {
    return { ...skeleton, gear: { ...skeleton.gear, off_hand: { kind: "shield_round", material: "wood", color: "#6a5a4a" } } };
  }
  return skeleton;
}

export interface HumanoidStyle {
  alpha: number;
  /** 整隻染色（source-atop）的顏色與強度 `t`。 */
  tint?: string;
  t?: number;
  /** 殘影：身後再一個更淡的影（透明度 ×0.4，往後 7 單位）。 */
  trail?: boolean;
  /** 腳下散成霧：從腳底往上這麼多單位，不透明度由 0 漸變到 1（霧影）。 */
  fade?: number;
  /** `false`：不畫紙娃娃自己的地面影子（霧影）。 */
  ground?: boolean;
}

/** 樣張 qSummon.js 的 HUMAN（外光拿掉，改半透明＋整隻染色）；霧影照 5F-ART1（月白、0.55、不發光、腳下散成霧）。 */
const HUMANOID_STYLE: Readonly<Record<string, HumanoidStyle>> = {
  shade: { alpha: 0.74, tint: "#6a3aa8", t: 0.28 },
  guardian: { alpha: 0.86, tint: "#fff2b0", t: 0.3 },
  afterimage: { alpha: 0.55, tint: "#8fd0ff", t: 0.5, trail: true },
  mist_shade: { alpha: 0.55, tint: "#dfe4e2", t: 0.53, fade: 14, ground: false },
};

/** 人形款式的合成方式；沒有特別合成的款式（骷髏）為 `undefined`。 */
export function humanoidStyle(variant: string): HumanoidStyle | undefined {
  return HUMANOID_STYLE[variant];
}

function makeCanvas(w: number, h: number, dpr: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w * dpr;
  c.height = h * dpr;
  return c;
}

function humanoidCanvas(look: ResolvedLook, facing: Facing, spec: DollSpec, dpr: number, ground: boolean): HTMLCanvasElement | null {
  const style = HUMANOID_STYLE[look.variant];
  const fig = renderFigureCanvas(spec, facing, false, dpr, ground && (style?.ground ?? true));
  if (fig === null) return null;
  if (style === undefined) return fig;
  const out = makeCanvas(DOLL_W, DOLL_H, dpr);
  const ctx = out.getContext("2d");
  if (ctx === null) return null;
  let src: HTMLCanvasElement = fig;
  if (style.tint !== undefined) {
    // 整隻染色：source-atop 只蓋在身體上（不會染到透明處）
    const tinted = makeCanvas(DOLL_W, DOLL_H, dpr);
    const t = tinted.getContext("2d");
    if (t !== null) {
      t.drawImage(fig, 0, 0);
      t.globalCompositeOperation = "source-atop";
      t.globalAlpha = style.t ?? 0.5;
      t.fillStyle = style.tint;
      t.fillRect(0, 0, tinted.width, tinted.height);
      src = tinted;
    }
  }
  if (style.trail) {
    // 殘影：身後再一個更淡的影（側面往背後 7 單位，正面、背面往左 5 單位）
    const back = facing === "east" ? -7 : facing === "west" ? 7 : -5;
    ctx.globalAlpha = style.alpha * 0.4;
    ctx.drawImage(src, back * dpr, 0);
  }
  ctx.globalAlpha = style.alpha;
  ctx.drawImage(src, 0, 0);
  if (style.fade !== undefined) {
    // 腳下散成霧：destination-in 疊直向漸層（腳底 0 → 往上 fade 單位 1，以上全部 1）
    const foot = DOLL_FOOT_Y * dpr;
    const g = ctx.createLinearGradient(0, foot, 0, foot - style.fade * dpr);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, "rgba(0,0,0,1)");
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "destination-in";
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.globalCompositeOperation = "source-over";
  }
  return out;
}

/** 非人形召喚物的貼圖：地面＋身體（Q 版：平塗＋整隻剪影外框 1.3 單位；藤蔓整體半透明 0.9）。`ground` ＝ false 時不畫地面。 */
function bodyCanvas(look: ResolvedLook, facing: Facing, dpr: number, ground: boolean): HTMLCanvasElement | null {
  const size = SIZE_SCALE[look.size];
  const out = makeCanvas(Q_SUMMON_W, Q_SUMMON_H, dpr);
  const ctx = out.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  ctx.translate(Q_SUMMON_W / 2, Q_SUMMON_FOOT_Y);
  if (ground) drawSummonGround(ctx, look);
  ctx.scale(size, size);
  layer(ctx, BOX, (g) => drawQSummonBody(g, look, facing), { ow: 1.3 / size, ...(look.body === "plant" ? { alpha: 0.9 } : {}) });
  return out;
}

/**
 * 產生召喚物貼圖用的離屏 canvas（人形與紙娃娃同尺寸 DOLL_W×DOLL_H；其他體型 Q_SUMMON_W×Q_SUMMON_H，腳底在 (W/2, FOOT_Y)）。
 * 人形用 `humanoid`（已解析好的紙娃娃規格）；沒有 DOM 時回傳 `null`。`ground` ＝ false 時不畫地上的東西（6C-8 受擊白閃用的身體）。
 */
export function renderSummonCanvas(look: ResolvedLook, facing: Facing, humanoid: DollSpec | null, dpr: number, ground = true): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  if (look.body === "humanoid") return humanoid === null ? null : humanoidCanvas(look, facing, humanoid, dpr, ground);
  return bodyCanvas(look, facing, dpr, ground);
}

/** 關鍵字 → 色（`0xRRGGBB` 數字，給 Pixi 用）。 */
export function keywordColorNumber(element: string | undefined): number | undefined {
  const hex = element === undefined ? undefined : KEYWORD_COLOR[element];
  return hex === undefined ? undefined : parseInt(hex.slice(1), 16);
}
