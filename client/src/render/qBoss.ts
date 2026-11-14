// QK-4：兩位頭目的 Q 版（照 docs/art/sample/qBoss.js）：灰燼之心（ashen_heart）、碎晶之主（rift_shard_lord）。
// 結構照 bossArt.js：「部件＋掛點」，每塊殼片、每片浮晶都是一個部件，有自己的掛點（位置、旋轉），動畫只改掛點。
// 畫法：純色平塗、部件細縫線、整隻剪影粗外框（qLayer，1.3 單位）；光改成平塗的半透明同心圓／色帶。
// 外光只代表頭目：兩位都是沿輪廓的一圈傳說金（QK-4b：黑外框再往外 2.2 單位、80% 實心色帶）；灰燼之心的核心光暈只在火焰箭蓄力時亮，
// 熔毀橘光、碎晶之主胸口核心光是狀態效果。頭目在東側（朝西）時呼叫端整隻鏡像；戰場上照 huge ×1.6 畫（BOSS_FIELD_SCALE）。
// 地面的陣營環與精英金環由戰場畫（貼圖不畫，樣張頁另外畫）。確定性：殼片、碎晶的相位由部件名稱雜湊（FNV-1a），不用 Math.random。
import { TAU, type Ctx } from "./artDraw";
import { darken, lighten, mix } from "./color";
import { applyCreaturePose, cp, type CreatureFx, type CreaturePose } from "./creaturePose";
import { seedOf } from "./inkStyle";
import { DOLL_SCALE } from "./paperdoll";
import { CREATURE_FX_TARGET_X, drawCreatureFx } from "./qCreatureAnim";
import { hasDom, qLayer, QC_OUT, type QLayerOpt } from "./qCreatureLayer";

export type BossId = "ah" | "sl";
/** 單位範本 → 頭目畫法。 */
export const BOSS_TEMPLATES: Readonly<Record<string, BossId>> = { ashen_heart: "ah", rift_shard_lord: "sl" };
/** 各頭目的階段數（不認得 → 預設）。 */
const PHASES: Readonly<Record<BossId, number>> = { ah: 3, sl: 4 };

/** 範本 → 頭目與階段；不是頭目 → null。灰燼之心沒有階段資料時：有熔殼＝1、沒有＝2。 */
export function bossOf(template: string | undefined, phase: number | null | undefined, statuses: readonly string[] = []): { id: BossId; phase: number } | null {
  const id = template !== undefined ? BOSS_TEMPLATES[template] : undefined;
  if (id === undefined) return null;
  let p = typeof phase === "number" && Number.isInteger(phase) && phase >= 1 && phase <= PHASES[id] ? phase : 0;
  if (p === 0) p = id === "ah" ? (statuses.includes("molten_shell") ? 1 : 2) : 1;
  return { id, phase: p };
}

/**
 * 頭目貼圖的畫布（單位）：寬 200、高 150、腳底在 130；頭頂高度（HUD 放在它上方）。QK-4b：含剪影外框 1.3＋外光 2.2；
 * 灰燼之心頂殼 −50、碎晶之主晶冠尖 −89 再加浮動最高 −13（待機、受擊都不超過）。
 */
export const BOSS_BOX = { w: 200, h: 150, foot: 130, top: { ah: -55, sl: -106 } as Readonly<Record<BossId, number>> } as const;
const LAYER_BOX: readonly [number, number, number, number] = [-100, -130, 100, 20];

const OUT = QC_OUT;
const clamp = (v: number, a = 0, b = 1): number => Math.max(a, Math.min(b, v));
const rnd = (key: string, k = 0): number => (seedOf(`${key}:${k}`) % 10000) / 10000;
const seam = (c: string): string => mix(c, OUT, 0.55);
type P2 = readonly [number, number];

function poly(g: Ctx, pts: readonly P2[], c: string, line = true): void {
  g.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.closePath();
  g.fillStyle = c;
  g.fill();
  if (line) {
    g.strokeStyle = seam(c);
    g.lineWidth = 0.6;
    g.lineJoin = "round";
    g.stroke();
  }
}
function ell(g: Ctx, x: number, y: number, rx: number, ry: number, c: string, opt: { line?: boolean; rot?: number } = {}): void {
  g.beginPath();
  g.ellipse(x, y, rx, ry, opt.rot ?? 0, 0, TAU);
  g.fillStyle = c;
  g.fill();
  if (opt.line !== false) {
    g.strokeStyle = seam(c);
    g.lineWidth = 0.6;
    g.stroke();
  }
}
function line(g: Ctx, pts: readonly P2[], w: number, c: string): void {
  g.save();
  g.strokeStyle = c;
  g.lineWidth = w;
  g.lineCap = "round";
  g.lineJoin = "round";
  g.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.stroke();
  g.restore();
}
/** 平塗光暈：3 圈半透明同心圓（取代 C 的放射漸層）。 */
function flatGlow(ctx: Ctx, x: number, y: number, r: number, c: string, a: number): void {
  ctx.save();
  ctx.fillStyle = c;
  for (const [k, al] of [[1, 0.16], [0.72, 0.2], [0.46, 0.26]] as const) {
    ctx.globalAlpha = al * a;
    ctx.beginPath();
    ctx.arc(x, y, r * k, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}
/** 有 DOM：剪影外框層；沒有（測試）：直接平塗。 */
function layer(ctx: Ctx, draw: (g: Ctx) => void, o: QLayerOpt): void {
  if (hasDom() && typeof ctx.getTransform === "function") {
    qLayer(ctx, LAYER_BOX, draw, o);
    return;
  }
  ctx.save();
  draw(ctx);
  ctx.restore();
}
const GOLD = "#ffbf3a";
/** 頭目外光（QK-4b，同樣張 qBoss.js GLOW_W／GLOW_A）：沿輪廓一圈＝黑外框再往外 2.2 單位的實心半透明色帶。 */
export const BOSS_GLOW_W = 2.2;
export const BOSS_GLOW_A = 0.8;
/** 頭目照 huge 尺寸畫（QK-4b，同樣張 QBoss.SIZE＝QCreature.SIZES.huge）：戰場上整隻（含外光）×1.6，腳底在自己那格。 */
export const BOSS_FIELD_SCALE = 1.6;
/** 待機一圈的長度（毫秒）。 */
const IDLE_LOOP_MS = 5278;
/** 線性循環（圈數）：一般＝t／週期；待機一圈時取整成整數圈。 */
export function cyc(t: number, period: number, loop: number | undefined): number {
  if (loop === undefined) return t / period;
  return 1200 / period + Math.max(1, Math.round(IDLE_LOOP_MS / period)) * loop;
}
/**
 * 振盪的相位（弧度）：一般＝t／週期；待機一圈（loop＝0～1）時把週期取整成一圈的整數次（QK-4b：碎晶之主待機接回第一格不跳），
 * 起點同 t＝1200。
 */
export function osc(t: number, period: number, loop: number | undefined): number {
  if (loop === undefined) return t / period;
  const n = Math.max(1, Math.round(IDLE_LOOP_MS / (TAU * period)));
  return 1200 / period + TAU * n * loop;
}

// =========================== 灰燼之心 ===========================
const BASALT = "#4a3b36";
const BASALT_L = "#6a5a52";
const LAVA = "#ff6a1a";
const LAVA_HOT = "#ffd23a";
const CORE = "#ffb23a";
/** GB-4b：灰燼之心色票（3×3 巨型版 `qBossGiant.ts` 共用，不另抄一份）。 */
export const ASH = { BASALT, BASALT_L, LAVA, LAVA_HOT, CORE, EMBER: "#7a2a08" } as const;
/** 殼片：[名稱, 掛點 x, 掛點 y, 旋轉, 寬, 高]（和 bossArt.js 的 PLATES 同一份）。 */
export const PLATES: ReadonlyArray<readonly [string, number, number, number, number, number]> = [
  ["p-back-l", -20, -34, -0.5, 18, 13],
  ["p-back-r", 20, -34, 0.5, 18, 13],
  ["p-top", 0, -44, 0, 20, 12],
  ["p-left", -26, -20, -0.9, 16, 14],
  ["p-right", 26, -20, 0.9, 16, 14],
  ["p-low-l", -18, -8, -0.3, 20, 12],
  ["p-low-r", 18, -8, 0.3, 20, 12],
  ["p-front", 0, -12, 0, 22, 12],
  ["p-mid-l", -12, -30, -0.2, 14, 11],
  ["p-mid-r", 12, -30, 0.2, 14, 11],
];

/** 一片甲蟲殼（Q）：圓背甲＋中線＋鋸齒殼縫（熱度越高越黃）＋左上一塊亮面。 */
function plate(g: Ctx, w: number, h: number, heat: number): void {
  ell(g, 0, 0, w / 2, h / 2, BASALT_L);
  g.save();
  g.beginPath();
  g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU);
  g.clip();
  ell(g, -w * 0.16, -h * 0.18, w * 0.22, h * 0.16, lighten(BASALT_L, 0.22), { line: false, rot: -0.3 });
  g.restore();
  line(g, [[0, -h / 2 + 0.8], [0, h / 2 - 0.8]], 0.9, OUT);
  const z: P2[] = [[-w * 0.34, 0.6], [-w * 0.17, -1.2], [0, 1], [w * 0.17, -1], [w * 0.34, 0.8]];
  line(g, z, 2, "#7a2a08");
  line(g, z, 1, mix(LAVA, LAVA_HOT, clamp(heat)));
}

function heartCore(g: Ctx, cx: number, cy: number, breath: number, crack: number, die = 0): void {
  const s = (1 + 0.06 * breath) * (1 - 0.55 * die);
  g.save();
  g.translate(cx, cy);
  g.scale(s, s);
  const pts: P2[] = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]];
  let c = mix(CORE, "#fff4d0", 0.35 * breath + 0.4 * crack);
  if (die > 0) c = mix(c, "#5a4a44", die); // 倒下：核心熄成灰石
  poly(g, pts, c);
  g.save();
  g.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.closePath();
  g.clip();
  poly(g, [[0, -15], [-9, -9], [-11, 3], [1, 0]], lighten(c, 0.35), false); // 亮面
  poly(g, [[11, 4], [4, 13], [1, 0]], darken(c, 0.12), false); // 暗面（一塊色）
  g.restore();
  g.fillStyle = "#ffffff";
  g.fillRect(-5, -9, 2.2, 4.4);
  g.fillRect(-2, -10.4, 1.4, 1.4);
  if (crack > 0) {
    g.save();
    g.globalAlpha = clamp(crack);
    line(g, [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.6, "#ffffff");
    line(g, [[8, -6], [3, -2], [7, 6]], 1.3, "#fff4c0");
    g.restore();
  }
  g.restore();
}

/** 殼片的掛點：熔殼在＝貼著並隨呼吸張開；脫落＝依名稱雜湊飛出、落地（落點收在 ±36，不超過 2 格寬）。 */
export function plateAnchor(p: (typeof PLATES)[number], shell: number, bt: number, breath: number): { x: number; y: number; r: number; a: number } {
  const [key, x, y, r] = p;
  if (shell > 0) {
    const open = 0.6 * breath;
    return { x: x * (1 + 0.02 * open), y: y - open * 0.6, r, a: 1 };
  }
  const dir = Math.sign(x || rnd(key) - 0.5) || 1;
  const spin = (rnd(key, 3) - 0.5) * 6;
  const fx = Math.max(-36, Math.min(36, x * 1.15 + dir * (4 + 4 * rnd(key, 1))));
  const fy = -2 - 2 * rnd(key, 4);
  const hop = 14 + 12 * rnd(key, 2);
  if (bt >= 1) return { x: fx, y: fy, r: r + spin * 0.8, a: 0.8 };
  const u = clamp(bt);
  return { x: x + (fx - x) * u, y: y + (fy - y) * u * u - hop * Math.sin(Math.PI * u), r: r + spin * 0.8 * u, a: 1 };
}

/** 灰燼之心的狀態（同 bossArt.js）。 */
export interface AshState {
  phase?: number;
  shell?: number;
  breakT?: number;
  t?: number;
  spout?: number;
  inhale?: number;
  dieT?: number;
  /** 待機一圈的進度（0～1）；有值時振盪照整數次（首尾接上）。 */
  loop?: number;
}
interface DrawOpt {
  glow?: string | null;
  flash?: number;
  flare?: number;
  /** 地面的陣營環（樣張頁）；戰場由 unitSprite 畫。 */
  ring?: ((ctx: Ctx, rx: number) => void) | undefined;
  /** 影子：true 畫、false 不畫、"only" 只畫影子。 */
  ground?: boolean | "only";
  /** 不畫外光（樣張頁對照用）。 */
  glowOff?: boolean;
}
const num = (v: number | undefined, d: number): number => (typeof v === "number" && Number.isFinite(v) ? v : d);

/** 灰燼之心（Q）。腳底 (0,0)，寬約 76 單位。外光＝沿輪廓的傳說金（QK-4b）；核心光暈只在火焰箭蓄力（flare）時亮。 */
export function drawAshenHeart(ctx: Ctx, st: AshState = {}, opt: DrawOpt = {}): void {
  const t = num(st.t, 0);
  const lp = st.loop;
  const breath = 0.5 + 0.5 * Math.sin(osc(t, 420, lp));
  const phase = st.phase === 2 || st.phase === 3 ? st.phase : 1;
  const crack = phase === 3 ? 0.6 + 0.4 * Math.sin(osc(t, 160, lp)) : 0;
  const shell = clamp(num(st.shell, phase === 1 ? 1 : 0));
  const bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
  const inhale = clamp(num(st.inhale, 0));
  const spout = clamp(num(st.spout, 0));
  const die = clamp(num(st.dieT, 0));
  const cy = -28 - inhale * 2 + 14 * die;
  opt.ring?.(ctx, 40);
  if (opt.ground !== false) {
    ctx.fillStyle = "rgba(10,8,14,0.35)";
    ctx.beginPath();
    ctx.ellipse(0, 0, 40, 8, 0, 0, TAU);
    ctx.fill();
  }
  if (opt.ground === "only") return;
  if (phase === 3) flatGlow(ctx, 0, -6, 50, "#ff6e1e", 1 - die);
  if (num(opt.flare, 0) > 0) flatGlow(ctx, 0, cy, 32 * (1 + 0.06 * breath), "#ffaa3c", num(opt.flare, 0));
  layer(
    ctx,
    (g) => {
      // 底座：熔岩甲蟲堆（不會掉）
      g.save();
      g.beginPath();
      g.moveTo(-38, 0);
      g.quadraticCurveTo(-36, -12, -20, -16);
      g.quadraticCurveTo(0, -20, 20, -16);
      g.quadraticCurveTo(36, -12, 38, 0);
      g.closePath();
      g.fillStyle = BASALT;
      g.fill();
      g.restore();
      for (const x of [-24, -8, 10, 26]) {
        ell(g, x, -6, 7, 4.4, BASALT_L);
        line(g, [[x - 5, -3], [x - 8, 0]], 1, OUT);
        ell(g, x + 6.4, -6.4, 2, 1.8, BASALT);
      }
      heartCore(g, 0, cy, breath, die > 0 ? crack * (1 - die) : crack, die);
      if (spout > 0) {
        // 殼頂熔岩柱（平塗兩層）
        g.save();
        g.fillStyle = LAVA;
        g.beginPath();
        g.moveTo(-6, -46);
        g.quadraticCurveTo(-9, -60 - 30 * spout, 0, -70 - 36 * spout);
        g.quadraticCurveTo(9, -60 - 30 * spout, 6, -46);
        g.closePath();
        g.fill();
        g.fillStyle = LAVA_HOT;
        g.beginPath();
        g.ellipse(0, -58 - 20 * spout, 2.6, 10 * spout, 0, 0, TAU);
        g.fill();
        g.restore();
      }
      for (const p of PLATES) {
        const A = plateAnchor(p, shell, bt, breath);
        g.save();
        g.globalAlpha = A.a;
        g.translate(A.x, A.y);
        g.rotate(A.r);
        plate(g, p[4], p[5], shell > 0 ? breath : 0.15);
        g.restore();
      }
    },
    { glow: opt.glowOff === true || die > 0 ? null : (opt.glow ?? GOLD), glowW: BOSS_GLOW_W, glowA: BOSS_GLOW_A, flash: num(opt.flash, 0) },
  );
  // 小粒子（吸氣的火星、熔毀滴落）：細外框
  const parts: Array<readonly [number, number, number, string]> = [];
  if (inhale > 0)
    for (let k = 0; k < 12; k++) {
      const a = rnd("in", k) * TAU;
      const d = 60 * (1 - ((t / 600 + rnd("in2", k)) % 1));
      parts.push([Math.cos(a) * d, cy + Math.sin(a) * d * 0.6, 1.8, LAVA_HOT]);
    }
  if (phase === 3 && die < 0.3)
    for (let k = 0; k < 4; k++) {
      const ph = (cyc(t, 900, lp) + rnd("drip", k)) % 1;
      parts.push([-20 + k * 13, -14 + ph * 14, 1.8, LAVA]);
    }
  if (parts.length > 0)
    layer(
      ctx,
      (g) => {
        for (const [x, y, r, c] of parts) {
          g.fillStyle = c;
          g.beginPath();
          g.arc(x, y, r, 0, TAU);
          g.fill();
        }
      },
      { ow: 0.8, alpha: inhale > 0 && phase !== 3 ? Math.max(0.3, inhale) : 1 },
    );
}

// =========================== 碎晶之主 ===========================
const CRYST = "#b8a8ff";
const CRYST_D = "#7a6ae0";
const RIFT = "#8a4ad0";
const CORE2 = "#e0ffff";
/** 掛點（相對身體原點；浮空的上下位移另外加）。Q 版：頭放大成 r≈11（大頭），軀幹縮短。 */
export const SL_ANCHORS: Readonly<Record<string, P2>> = {
  head: [0, -62],
  torso: [0, -36],
  core2: [0, -40],
  "sh-l": [-17, -48],
  "sh-r": [17, -48],
  "hand-l": [-26, -36],
  "hand-r": [26, -36],
  ...Object.fromEntries([0, 1, 2, 3, 4].map((k) => [`crown-${k}`, [-10 + k * 5, -73 - (k === 2 ? 5 : k % 2 ? 2.4 : 0)] as P2])),
  ...Object.fromEntries([0, 1, 2, 3, 4].map((k) => [`tail-${k}`, [0, -16 + k * 4.4] as P2])),
};
const A = (k: string): P2 => SL_ANCHORS[k] ?? [0, 0];

function shard(g: Ctx, x: number, y: number, len: number, wid: number, rot: number, color: string): void {
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  poly(g, [[0, -len], [wid, -len * 0.25], [wid * 0.6, len * 0.4], [0, len * 0.5], [-wid * 0.7, len * 0.3], [-wid, -len * 0.3]], color);
  poly(g, [[0, -len], [-wid, -len * 0.3], [-wid * 0.7, len * 0.3], [0, len * 0.5]], lighten(color, 0.3), false);
  g.restore();
}

/** 碎晶之主的狀態（同 bossArt.js）。 */
export interface LordState {
  phase?: number;
  t?: number;
  cast?: number;
  blink?: number;
  channel?: boolean;
  dieT?: number;
  swingA?: number;
  swingR?: number;
  /** 待機一圈的進度（0～1）；有值時振盪照整數次（首尾接上）。 */
  loop?: number;
}

function slBody(g: Ctx, st: LordState, hover: number, cast: number, tint: (c: string) => string, phase: number, t: number): P2 {
  g.save();
  g.translate(0, hover);
  const spread = phase === 4 ? 1.8 : 1;
  // 碎界脈動：後半圈的碎晶畫在身體後面
  const orbs =
    phase >= 2
      ? [0, 1, 2, 3, 4, 5].map((k) => {
          const a = osc(t, 800, st.loop) + rnd("orb", k) * TAU;
          const r = 30 + 4 * Math.sin(osc(t, 300, st.loop) + k);
          return { k, a, x: Math.cos(a) * r, y: -38 + Math.sin(a) * r * 0.35, front: Math.sin(a) >= 0 };
        })
      : [];
  for (const o of orbs) if (!o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
  for (let k = 0; k < 5; k++) {
    const ph = osc(t, 700, st.loop) + rnd("tail", k) * TAU;
    const [ax, ay] = A(`tail-${k}`);
    shard(g, ax + Math.sin(ph) * 3 * spread + (rnd("tx", k) - 0.5) * 8 * spread, ay + k * 0.6 * (spread - 1) * 5, 7 - k, 4.4 - k * 0.6, Math.sin(ph) * 0.3, tint(k % 2 ? CRYST_D : CRYST));
  }
  shard(g, A("sh-l")[0], A("sh-l")[1], 9, 4.4, -0.9, tint(CRYST_D));
  shard(g, A("sh-r")[0], A("sh-r")[1], 9, 4.4, 0.9, tint(CRYST_D));
  // 軀幹：倒三角晶塊（亮面一塊）
  poly(g, [[-14, -50], [14, -50], [9, -32], [3, -20], [-3, -20], [-9, -32]], tint(CRYST));
  poly(g, [[-14, -50], [0, -50], [0, -36], [-3, -20], [-9, -32]], tint(lighten(CRYST, 0.22)), false);
  line(g, [[-14, -50], [0, -38], [14, -50]], 0.7, tint(CRYST_D));
  // 胸口核心
  const over = phase >= 3 ? 0.7 + 0.3 * Math.sin(osc(t, 130, st.loop)) : 0.4 + 0.2 * Math.sin(osc(t, 400, st.loop));
  const [cx, cy] = A("core2");
  poly(g, [[cx, cy - 6.4], [cx + 5.6, cy], [cx, cy + 6.4], [cx - 5.6, cy]], mix(phase === 4 ? "#ffc0d8" : CORE2, "#ffffff", over * 0.5));
  g.fillStyle = "#ffffff";
  g.fillRect(cx - 2, cy - 3, 1.6, 2.4);
  if (phase >= 3) line(g, [[cx - 2, cy - 5], [cx + 1, cy - 1], [cx - 1, cy + 4]], 1.2, "#ffffff");
  // 頭（Q 大頭）：六角晶面＋兩隻方眼
  const [hx, hy] = A("head");
  for (let k = 0; k < 5; k++) {
    const [x, y] = A(`crown-${k}`);
    shard(g, x, y, 6 + (k === 2 ? 5 : 2), 2.6, (k - 2) * 0.24, tint(k === 2 ? CORE2 : CRYST));
  }
  poly(g, [[hx - 9, hy - 9], [hx + 9, hy - 9], [hx + 11.5, hy], [hx + 7, hy + 9], [hx - 7, hy + 9], [hx - 11.5, hy]], tint(lighten(CRYST, 0.15)));
  poly(g, [[hx - 9, hy - 9], [hx, hy - 9], [hx - 4, hy + 9], [hx - 7, hy + 9], [hx - 11.5, hy]], tint(lighten(CRYST, 0.35)), false);
  for (const x of [-4.2, 4.2]) {
    if (phase >= 3) {
      // 過載：眼睛變大、純白＋青色外圈＋十字光點
      g.fillStyle = OUT;
      g.fillRect(hx + x - 2.2, hy - 3, 4.4, 5.2);
      g.fillStyle = "#a0f0ff";
      g.fillRect(hx + x - 1.7, hy - 2.5, 3.4, 4.2);
      g.fillStyle = "#ffffff";
      g.fillRect(hx + x - 1.1, hy - 1.9, 2.2, 3);
      line(g, [[hx + x, hy - 5], [hx + x, hy - 3.4]], 0.7, "#ffffff");
      line(g, [[hx + x + 2.6, hy - 0.4], [hx + x + 3.8, hy - 0.4]], 0.7, "#ffffff");
    } else {
      g.fillStyle = OUT;
      g.fillRect(hx + x - 1.6, hy - 2.4, 3.2, 4);
      g.fillStyle = CORE2;
      g.fillRect(hx + x - 1, hy - 1.8, 2, 2.8);
    }
  }
  // 浮空手晶：施法時往前（東）伸；揮擊：前手晶繞右肩劃弧（靜止約 0.93 rad、半徑 15）
  let hxr = 26 + 16 * cast;
  let hyr = -36 - 4 * Math.sin(osc(t, 360, st.loop));
  let hrot = 0.4 + 1.2 * cast;
  if (typeof st.swingA === "number") {
    const a = st.swingA;
    const R0 = num(st.swingR, 15);
    hxr = A("sh-r")[0] + Math.cos(a) * R0;
    hyr = A("sh-r")[1] + Math.sin(a) * R0;
    hrot = a - 0.53;
  }
  shard(g, -hxr + 30 * cast, hyr + 4, 9.5, 5.4, -0.4 + 1.6 * cast, tint(CRYST));
  shard(g, hxr, hyr, 9.5, 5.4, hrot, tint(CRYST));
  for (const o of orbs) if (o.front) shard(g, o.x, o.y, 5, 2.8, o.a, tint(o.k % 2 ? RIFT : CRYST));
  g.restore();
  return [hxr, hyr + hover];
}

/** 碎晶之主（Q）。正面對稱；東側（朝西）時呼叫端整隻鏡像。外光預設傳說金（`glow: false` 不畫）。 */
export function drawShardLord(ctx: Ctx, st: LordState = {}, opt: DrawOpt = {}): void {
  const die = clamp(num(st.dieT, 0));
  const t = num(st.t, 0);
  const phase = st.phase === 2 || st.phase === 3 || st.phase === 4 ? st.phase : 1;
  const hover = (-10 - 3 * Math.sin(osc(t, 500, st.loop))) * (1 - die);
  const cast = clamp(num(st.cast, 0));
  const blink = clamp(num(st.blink, 0));
  const tint = phase === 4 ? (c: string) => mix(c, "#ff5a8a", 0.35) : (c: string) => c;
  opt.ring?.(ctx, 26);
  if (opt.ground !== false) {
    ctx.fillStyle = "rgba(10,8,14,0.3)";
    ctx.beginPath();
    ctx.ellipse(0, 0, 24, 5, 0, 0, TAU);
    ctx.fill();
  }
  if (opt.ground === "only") return;
  flatGlow(ctx, 0, hover - 40, 24, phase === 4 ? "#ff5a8c" : "#a0f0ff", (phase >= 3 ? 1 : 0.7) * (1 - die));
  // 瞬步殘影：整隻剪影單色平塗 2 層
  if (blink > 0)
    for (const [gx, al] of [[2, 0.35], [1, 0.55]] as const) {
      ctx.save();
      ctx.translate(-gx * 16, 0);
      layer(ctx, (o) => void slBody(o, st, hover, cast, tint, phase, t), { alpha: al * blink, flat: tint("#c8b8ff") });
      ctx.restore();
    }
  // 灌注光束（三柱階段）：從左右側後方接到胸口核心，畫在本體後面
  if (phase === 1 && st.channel !== false)
    for (let k = 0; k < 3; k++) {
      const a = [-2.75, -0.4, -2.25][k]!;
      const c = ["#ff7a2a", "#9ad8c8", "#c8a0ff"][k]!;
      const p0: P2 = [Math.cos(a) * 95, hover - 40 + Math.sin(a) * 70];
      const p1: P2 = [0, hover - 40];
      ctx.save();
      ctx.globalAlpha = 0.75 + 0.2 * Math.sin(osc(t, 200, st.loop) + k);
      line(ctx, [p0, p1], 4.4, OUT);
      line(ctx, [p0, p1], 3, c);
      line(ctx, [p0, p1], 0.9, "#ffffff");
      ctx.restore();
    }
  const lo: QLayerOpt = { glow: opt.glowOff === true || die > 0 ? null : (opt.glow ?? GOLD), glowW: BOSS_GLOW_W, glowA: BOSS_GLOW_A };
  if ((opt.flash ?? 0) > 0) lo.flash = opt.flash ?? 0;
  if (die > 0) {
    // 倒下：以腳底為準往下壓扁、往兩側散開（碎晶堆在地面上，不穿地）
    ctx.save();
    ctx.globalAlpha = 1 - 0.55 * die;
    layer(
      ctx,
      (g) => {
        g.scale(1 + 0.3 * die, 1 - 0.62 * die);
        slBody(g, { ...st, phase: 4 }, hover, 0, phase === 4 ? tint : (c) => mix(c, "#6a6480", 0.5 * die), 4, t);
      },
      lo,
    );
    ctx.restore();
    return;
  }
  let hand: P2 = [0, 0];
  layer(
    ctx,
    (g) => {
      hand = slBody(g, st, hover, cast, tint, phase, t);
    },
    lo,
  );
  if (cast > 0) {
    const [hx, hy] = hand;
    layer(
      ctx,
      (g) => {
        g.fillStyle = "#d8b8ff";
        g.beginPath();
        g.arc(hx + 10, hy, 4.4 * cast, 0, TAU);
        g.fill();
        g.fillStyle = "#ffffff";
        g.beginPath();
        g.arc(hx + 10, hy, 2 * cast, 0, TAU);
        g.fill();
      },
      { ow: 0.9 },
    );
    flatGlow(ctx, hx + 10, hy, 16, "#c8a0ff", cast);
  }
}

// =========================== 頭目動作片段（攻擊依技能類型、受擊、倒下） ===========================
// 灰燼之心：熔岩噴發 spout＝自身範圍、火焰箭 firebolt＝遠程、殼片撞擊 ram＝普攻（第 1 階段）；碎晶之主：聚雷 thunder＝遠程施放、手晶揮擊 swing＝普攻、
// 瞬步殘影 blink＝位移（BAL-21c）。
// t 的純函式；12 格／秒；倒下停在最後一格。
const kfB = (u: number, pts: ReadonlyArray<readonly [number, number]>): number => {
  const first = pts[0]!;
  if (u <= first[0]) return first[1];
  for (let i = 1; i < pts.length; i++) {
    const [b, vb] = pts[i]!;
    if (u <= b) {
      const [a, va] = pts[i - 1]!;
      const x = (u - a) / (b - a || 1);
      return va + (vb - va) * x * x * (3 - 2 * x);
    }
  }
  return pts[pts.length - 1]![1];
};
const segB = (u: number, a: number, b: number): number => clamp((u - a) / (b - a));
const bumpB = (u: number, a: number, b: number): number => Math.sin(Math.PI * segB(u, a, b));

/** 頭目的片段（含待機）。 */
export const BOSS_CLIPS: Readonly<Record<BossId, readonly string[]>> = { ah: ["spout", "firebolt", "ram", "hit", "death"], sl: ["thunder", "swing", "blink", "hit", "death"] };
export const BOSS_CLIP_ZH: Readonly<Record<string, string>> = {
  idle: "待機",
  spout: "範圍爆發：熔岩噴發",
  firebolt: "遠程施放：火焰箭（從核心）",
  ram: "普攻：殼片撞擊（第 1 階段）",
  thunder: "遠程施放：聚雷（手晶放電）",
  swing: "普攻：手晶揮擊",
  blink: "位移：瞬步殘影（在目的格）",
  hit: "受擊",
  death: "倒下",
};
/** 片段長度（毫秒）。待機 16 格一圈（灰燼之心呼吸兩次）。 */
export const BOSS_MS: Readonly<Record<string, number>> = { idle: 5278, spout: 1300, firebolt: 950, ram: 900, thunder: 1000, swing: 800, blink: 600, hit: 400, death: 1500 };
export const BOSS_IDLE_N = 16;

/** 片段在 t 毫秒的格數與 u（同樣張 act：12 格／秒，最後一格 u＝1）。 */
export function bossFrameU(clip: string, t: number): number {
  const ms = BOSS_MS[clip] ?? 0;
  if (clip === "idle") return Math.floor((((t % ms) + ms) % ms) / (ms / BOSS_IDLE_N)) / BOSS_IDLE_N;
  const n = Math.max(2, Math.round((ms || 1) / (1000 / 12)));
  const f = Math.min(n - 1, Math.max(0, Math.floor(num(t, 0) / (1000 / 12))));
  return f / (n - 1);
}

export interface BossActOpt {
  phase?: number;
  reduce?: boolean;
  ring?: ((ctx: Ctx, rx: number) => void) | undefined;
  ground?: boolean | "only";
  /** 連飛向目標的特效也畫（樣張頁）；戰場上由技能特效畫。 */
  fxAll?: boolean;
  /** 另外的白閃（戰場的命中白閃，沒有片段時）。 */
  flash?: number;
  /** CB-4：片段自帶的特效不畫（目標不在同一排時，由戰場另畫轉向的特效貼圖，`bossPoseFx`）。 */
  noFx?: boolean;
  /** CB-4b：戰場上同一排（東西向，特效畫進身體貼圖）：灰燼之心 `ram` 的星爆、塵土內收到目標格（`bossSameRowFx`）。 */
  sameRow?: boolean;
}

/** 頭目畫法的虛擬格寬（同 `creatureFxTurn` 的 52：模型像素 ＝ 單位 × 一格 / 52 × `DOLL_SCALE` × `BOSS_FIELD_SCALE`）。 */
const BOSS_VIRTUAL_TILE = 52;
/**
 * CB-4b：戰場上頭目貼圖（朝東、腳底原點、不含大小）裡，東西向相鄰目標格中心的 x（單位）＝ 一格 48 px 換回單位 ≈ 30.66。
 * 片段裡的「相鄰目標」點 `CREATURE_FX_TARGET_X`（52）在頭目放大後落在 81.4 px，比目標格中心多約 33 px。
 */
export const BOSS_EW_TARGET_X = BOSS_VIRTUAL_TILE / (DOLL_SCALE * BOSS_FIELD_SCALE);

/**
 * CB-4b（美術驗收 `QI-2c-2d-3a-3b驗收.md` 第 5.3 節）：東西向（同一排、特效畫進身體貼圖）時片段特效的位置。
 * 只改灰燼之心 `ram`：星爆（接觸點）水平放在目標格中心（同正南北的 0；高度照片段）；塵土照剪切跟著目標格
 * （相對「相鄰目標」點的距離照舊、原點換成目標格中心 → 往施放者側 8 單位 ≈ 12.5 px，同南北、斜向）。其他片段、碎晶之主原樣回傳。
 */
export function bossSameRowFx(who: BossId, clip: string, fx: CreatureFx[]): CreatureFx[] {
  if (who !== "ah" || clip !== "ram") return fx;
  return fx.map((f) => {
    if (f.k === "burst") return { ...f, x: BOSS_EW_TARGET_X };
    if (f.k === "dust") return { ...f, x: BOSS_EW_TARGET_X + (f.x ?? 0) - CREATURE_FX_TARGET_X };
    return f;
  });
}

/** 依動作類型挑頭目的攻擊片段（不認得的類型 → 該頭目的普攻）。 */
export function bossAttackClip(id: BossId, type0: string, phase: number): string {
  const type = type0 === "melee2" ? "melee" : type0; // CB-3：頭目沒有第二種近戰，照普攻
  if (id === "ah") {
    // BAL-21b：熔岩濺落（選 4 格內的 3×3）施放回合也歸 area（人形出招 palm_ground），播 spout；落下回合不播片段（skillSequence 的 bodyless）
    if (type === "area") return "spout";
    if ((type === "melee" || type === "charge") && phase === 1) return "ram";
    return "firebolt";
  }
  // BAL-21c（T7 美術 PM）：位移（界隙閃擊的第二段）播瞬步殘影 blink，不再退回揮擊 swing
  if (type === "blink") return "blink";
  return type === "cast" || type === "area" || type === "breath" ? "thunder" : "swing";
}

/**
 * 畫頭目的一個片段在 u（0～1，已量化）的那一格（腳底 (0,0)，呼叫端已縮放／鏡像）。`clip`：idle、spout、firebolt、ram、thunder、swing、hit、death；
 * 不認得 → 靜態。opt.reduce：姿勢固定在當下階段的靜止狀態，只留白閃與特效；倒下直接最後一格。
 */
export function bossAct(ctx: Ctx, who: BossId, clip: string, u0: number, opt: BossActOpt = {}): void {
  const P = bossPlan(who, clip, u0, opt);
  const base = { ring: opt.ring, ground: opt.ground ?? true };
  ctx.save();
  ctx.translate(P.dx, 0);
  if (P.rot) {
    const [px, py] = P.who === "ah" ? [-30, 0] : [0, -40];
    ctx.translate(px, py);
    ctx.rotate(P.rot);
    ctx.translate(-px, -py);
  }
  if (P.who === "ah") drawAshenHeart(ctx, P.st, { ...P.o, ...base });
  else drawShardLord(ctx, P.st, { ...P.o, ...base });
  ctx.restore();
  const fx = opt.sameRow === true ? bossSameRowFx(who, clip, P.fx) : P.fx;
  if (fx.length > 0 && opt.ground !== "only" && opt.noFx !== true) drawCreatureFx(ctx, opt.fxAll === true ? fx : fx.filter((f) => f.ranged !== true), undefined, [-110, -160, 120, 20]);
}

/** 頭目一格要畫什麼（純函式，bossAct 照它畫；命中對齊也看它的特效）。 */
type BossPlan = { dx: number; rot: number; fx: CreatureFx[]; o: { flash: number; flare?: number } } & ({ who: "ah"; st: AshState } | { who: "sl"; st: LordState });
export function bossPlan(who: BossId, clip: string, u0: number, opt: BossActOpt = {}): BossPlan {
  const known = clip === "idle" || (BOSS_CLIPS[who] ?? []).includes(clip);
  const c = known ? clip : "static";
  const ms = BOSS_MS[c] ?? 0;
  let u = clamp(u0);
  if (opt.reduce === true && c === "death") u = 1;
  const tt = c === "idle" ? 1200 + u * ms : opt.reduce === true || c === "static" ? 1200 : 1200 + u * ms;
  const fx: CreatureFx[] = [];
  const o: { flash: number; flare?: number } = { flash: Math.max(opt.flash ?? 0, c === "hit" && u < 0.2 ? 0.9 : c === "death" && u < 0.12 ? 0.7 : 0) };
  let dx = 0;
  let rot = 0;
  if (who === "ah") {
    const ph = opt.phase === 2 || opt.phase === 3 ? opt.phase : 1;
    const lp = c === "idle" ? { loop: u } : {};
    const phaseSt: AshState = ph === 1 ? { phase: 1, shell: 1, t: tt, ...lp } : { phase: ph, shell: 0, breakT: 1, t: tt, ...lp };
    let st: AshState = { ...phaseSt };
    if (c === "spout") {
      st = { phase: 1, shell: 1, t: tt, inhale: bumpB(u, 0, 0.42), spout: kfB(u, [[0, 0], [0.4, 0], [0.52, 1], [0.8, 0.9], [1, 0]]) };
      if (u > 0.5) {
        const k = segB(u, 0.5, 1);
        fx.push({ k: "ring", x: 0, rx: 30 + 40 * k, c: LAVA, a: 1 - k }, { k: "ring", x: 0, rx: 22 + 26 * k, c: LAVA_HOT, a: (1 - k) * 0.8 });
        for (let i = 0; i < 6; i++) {
          const an = -Math.PI * (0.1 + 0.8 * (i / 5));
          const d = 20 + 50 * k;
          fx.push({ k: "orb", x: Math.cos(an) * d, y: -2 - 46 * Math.sin(Math.PI * k) * (0.6 + 0.4 * (i % 2)), r: 2.4, c: LAVA, c2: LAVA_HOT, a: 1 - 0.5 * k });
        }
      }
    } else if (c === "firebolt") {
      o.flare = 0.6 * bumpB(u, 0.05, 0.55);
      if (u > 0.08 && u < 0.46) fx.push({ k: "orb", x: 0, y: -28, r: 3 + 4 * segB(u, 0.08, 0.46), c: LAVA, c2: LAVA_HOT });
      if (u >= 0.46 && u <= 0.72) fx.push({ k: "orb", x: 6 + 78 * segB(u, 0.46, 0.72), y: -28 + 8 * segB(u, 0.46, 0.72), r: 4.4, c: LAVA, c2: LAVA_HOT, tail: 1, ranged: true });
      if (u > 0.72) {
        const k = segB(u, 0.72, 1);
        fx.push({ k: "glow", x: 84, y: -20, r: 14 + 6 * k, c: LAVA, a: 1 - k, ranged: true }, { k: "burst", x: 84, y: -20, r: 7 + 4 * k, c: LAVA, c2: LAVA_HOT, a: 1 - k, ranged: true });
      }
    } else if (c === "ram") {
      st = { phase: 1, shell: 1, t: 1200 + 900 * bumpB(u, 0.1, 0.55) };
      dx = kfB(u, [[0, 0], [0.35, -5], [0.55, 10], [0.68, 8], [1, 0]]);
      rot = kfB(u, [[0, 0], [0.35, -0.06], [0.55, 0.08], [1, 0]]);
      if (u > 0.52 && u < 0.8) {
        const k = segB(u, 0.52, 0.8);
        fx.push({ k: "burst", x: 50, y: -24, r: 7 + 4 * k, c: "#ffffff", c2: "#ffe08a", a: 1 - k }, { k: "dust", x: 44, y: -1, r: 6, a: 1 - k });
      }
    } else if (c === "hit") dx = u < 0.6 ? 1.6 * Math.sign(Math.sin(u * 60)) * (1 - u / 0.6) : 0;
    else if (c === "death") {
      st = { phase: 3, shell: 0, breakT: 1, t: tt, dieT: segB(u, 0.25, 1) };
      dx = u < 0.3 ? 1.4 * Math.sign(Math.sin(u * 90)) : 0;
      if (u > 0.55 && u < 0.95) fx.push({ k: "dust", x: 0, y: -1, r: 12, a: 1 - segB(u, 0.55, 0.95) });
    }
    if (opt.reduce === true) {
      dx = 0;
      rot = 0;
      if (c !== "death") st = { ...phaseSt };
      delete o.flare;
    }
    return { who: "ah", st, dx, rot, fx, o };
  }
  {
    const phaseSt: LordState = { phase: opt.phase === 1 || opt.phase === 3 || opt.phase === 4 ? opt.phase : 2, t: tt, ...(c === "idle" ? { loop: u } : {}) };
    let st: LordState = { ...phaseSt };
    if (c === "thunder") {
      st.cast = kfB(u, [[0, 0], [0.35, 1], [0.8, 1], [1, 0]]);
      const hand: P2 = [26 + 16 * (opt.reduce === true ? 0 : st.cast) + 10, -46];
      if (u > 0.15 && u < 0.45) fx.push({ k: "glow", x: hand[0], y: hand[1], r: 8 + 8 * segB(u, 0.15, 0.45), c: "#fff36b", a: 0.8 });
      if (u >= 0.45 && u <= 0.75) fx.push({ k: "bolt", x0: hand[0], y0: hand[1], x1: 84, y1: -18, c: "#fff36b", amp: 1.4 + 0.6 * Math.sin(u * 80), ranged: true }, { k: "glow", x: 84, y: -18, r: 14, c: "#fff36b", a: 0.9, ranged: true });
    } else if (c === "swing") {
      st.swingA = kfB(u, [[0, 0.93], [0.35, -2.2], [0.55, 0.7], [0.7, 0.75], [1, 0.93]]);
      st.swingR = kfB(u, [[0, 15], [0.35, 20], [0.55, 26], [0.7, 25], [1, 15]]);
      dx = kfB(u, [[0, 0], [0.35, -2], [0.55, 6], [1, 0]]);
      if (u > 0.45 && u < 0.68) fx.push({ k: "slash", x: 44, y: -38, r: 14, c: "#e0d8ff", a: 1 - segB(u, 0.45, 0.68) * 0.7, len: 1.4 });
    } else if (c === "blink") {
      // BAL-21c（T7 美術 PM，樣張 bosses.html 第 81 行）：約 600 ms、殘影 blink 1 → 0 線性；在目的格播（motionLayer 一開始就站在終點）
      st.blink = 1 - u;
    } else if (c === "hit") {
      dx = -kfB(u, [[0, 0], [0.18, 5], [1, 0]]);
      rot = -0.06 * kfB(u, [[0, 0], [0.18, 1], [1, 0]]);
    } else if (c === "death") {
      st = { phase: 3, t: tt, dieT: segB(u, 0.2, 1) };
      dx = u < 0.25 ? 1.4 * Math.sign(Math.sin(u * 90)) : 0;
    }
    if (opt.reduce === true) {
      dx = 0;
      rot = 0;
      if (c !== "death") st = { ...phaseSt };
    }
    return { who: "sl", st, dx, rot, fx, o };
  }
}

/** 戰場的攻擊片段格數（creaturePose 的 CLIP_FRAMES.atk）。 */
const BOSS_ATK_FRAMES = 12;
/** 出手那一刻的特效（同 qCreatureAnim 的命中對齊）：飛向目標的特效、爆開、揮砍、雷、震地環。 */
const BOSS_IMPACT: ReadonlySet<string> = new Set(["slash", "chomp", "ring", "burst", "bolt", "beam", "cone", "wave", "flame", "shard", "rock"]);
/**
 * QK-4b（QK-5 待決 4）：頭目攻擊片段的出手格（0～1，照戰場攻擊片段的量化 12 格，u＝f／11，同 creaturePose.creatureStrikePose）：第一個出現出手特效的格；沒有＝整隻往前推最遠那格；都沒有＝0.5。
 * 純函式（同 qCreatureAnim.creatureAttackHitU）。
 */
export function bossAttackHitU(who: BossId, clip: string, phase: number): number {
  const n = BOSS_ATK_FRAMES;
  let best = 0.5;
  let far = 0;
  for (let f = 1; f < n; f++) {
    const u = f / (n - 1);
    const p = bossPlan(who, clip, u, { phase });
    if (p.fx.some((x) => x.ranged === true || BOSS_IMPACT.has(x.k))) return u;
    if (p.dx > far + 1e-6) {
      far = p.dx;
      best = u;
    }
  }
  return best;
}


/** 片段名（`CreaturePose.clip`）→ 頭目片段：idle、move（不動）→ 待機；atk:xxx → xxx；hit、death 照舊。 */
function bossClipOf(boss: { id: BossId; phase: number }, clip: string | undefined): string {
  if (clip === undefined) return "static";
  if (clip === "move") return "idle";
  if (clip.startsWith("atk:@")) return bossAttackClip(boss.id, clip.slice(5), boss.phase);
  return clip.startsWith("atk:") ? clip.slice(4) : clip;
}

/** inkCreature 用：畫頭目貼圖的一格（呼叫端已平移到腳底、鏡像）。 */
export function drawBossFrame(ctx: Ctx, boss: { id: BossId; phase: number }, pose: CreaturePose | null, ground: boolean | "only"): void {
  ctx.save();
  if (pose !== null && ground !== "only") applyCreaturePose(ctx, pose);
  const flash = pose === null ? 0 : cp(pose, "flash");
  bossAct(ctx, boss.id, bossClipOf(boss, pose?.clip), pose?.u ?? 0, { phase: boss.phase, ground, fxAll: pose?.fxAll === true, flash, ...(pose?.fxTurn === undefined ? { sameRow: true } : { noFx: true }) });
  ctx.restore();
}

/**
 * CB-4：這一格頭目片段自帶的特效（腳底座標、朝東；和 `bossAct` 畫進貼圖的相同：樣張頁 `fxAll` 全部，否則不含飛向目標的 `ranged`）。
 * 目標不在同一排（`pose.fxTurn`）時由 `inkCreature.turnedCreatureFx` 轉向、另畫一張。
 */
export function bossPoseFx(boss: { id: BossId; phase: number }, pose: CreaturePose): CreatureFx[] {
  const fx = bossPlan(boss.id, bossClipOf(boss, pose.clip), pose.u ?? 0, { phase: boss.phase }).fx;
  return pose.fxAll === true ? fx : fx.filter((f) => f.ranged !== true);
}
