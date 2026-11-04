// 狀態的持續動作（Phase 6N-9；docs/art/動畫移植需求第二批.md 第 8 節、動畫方案.md 2.5）。
// 疊在現有的狀態圖示與身上特效（3-18b 的 5 類）上面，只加「動」的部分；全部是純函式：
// （狀態種類、單位 ID、動畫時鐘毫秒）→ 一組小粒子的位置與身體的搖晃。不用 Math.random()、不讀時間；
// 相位用單位 ID（加種類）的 FNV-1a 雜湊（`inkStyle.seedOf`）錯開，同一個 ID、同一個時間永遠得到同一個畫面。
// - 只讀畫面資料（狀態 ID 與狀態外觀旗標、站的格子的表面），不改任何規則與數值，不新增伺服器欄位。
// - 粒子只換位置、縮放、透明度、旋轉（貼圖固定一小組，見 statusAnimArt.ts），所以不會讓貼圖數量長大；
//   火苗的形狀量化成 4 張輪播。
// 座標：虛擬格 52 為單位，相對腳底（0, 0），y 往上為負；身高照 statusIcon.bodyOver 的預設 34。
import type { InkPose, PoseKey } from "./inkPose";
import { seedOf } from "./inkStyle";
import { bodyEffects, CONCEALED, type BodyEffects } from "./statusIcon";

const TAU = Math.PI * 2;

/** 8 種狀態動作（固定順序；畫的時候照這個順序疊）。 */
export type StatusAnimKind = "burning" | "frozen" | "poison" | "stunned" | "rooted" | "concealed" | "wet" | "charged";
export const STATUS_ANIM_KINDS: readonly StatusAnimKind[] = ["burning", "frozen", "poison", "stunned", "rooted", "concealed", "wet", "charged"];

/** 帶電的護盾（被打破時電攻擊者）；身上偶爾閃小電弧。 */
export const CHARGED_STATUS = "shielded_charged";

/**
 * 一個單位有哪些狀態動作。只看狀態外觀旗標（和身上特效同一套判定）：
 * - 燃燒：持續傷害的元素是火；中毒：持續傷害是毒；帶電：持續傷害是雷，或帶電護盾；
 * - 冰凍、暈眩、定身：同 `bodyEffects` 的 frozen、stunned、noMove；
 * - 隱身：`concealed`；
 * - 潮濕：站在水面上（規則的「站在水上」，雷電導水、治療減少都看這個；沒有獨立的潮濕狀態）。
 */
export function statusAnimKinds(ids: readonly string[], onWater: boolean): StatusAnimKind[] {
  const e = bodyEffects(ids);
  const on: Record<StatusAnimKind, boolean> = {
    burning: e.dots.includes("fire"),
    frozen: e.frozen,
    poison: e.dots.includes("poison"),
    stunned: e.stunned,
    rooted: e.noMove,
    concealed: ids.includes(CONCEALED),
    wet: onWater,
    charged: e.dots.includes("lightning") || ids.includes(CHARGED_STATUS),
  };
  return STATUS_ANIM_KINDS.filter((k) => on[k]);
}

/** 身上靜態特效裡改成動畫的部分拿掉之後的樣子（暈眩的星星與圈、火與毒的腳邊粒子改由動畫畫）。 */
export function staticRemainder(e: BodyEffects): BodyEffects {
  return { ...e, stunned: false, dots: e.dots.filter((d) => d !== "fire" && d !== "poison") };
}

/** 靜態特效有沒有被動畫取代的部分（沒有就不用換貼圖）。 */
export function hasAnimatedStatic(e: BodyEffects): boolean {
  return e.stunned || e.dots.includes("fire") || e.dots.includes("poison");
}

export type ParticleTex =
  | "flame0"
  | "flame1"
  | "flame2"
  | "flame3"
  | "smoke"
  | "bubble"
  | "star"
  | "ring"
  | "glint"
  | "vine"
  | "drop"
  | "arc0"
  | "arc1"
  | "arc2";

export const PARTICLE_TEXES: readonly ParticleTex[] = ["flame0", "flame1", "flame2", "flame3", "smoke", "bubble", "star", "ring", "glint", "vine", "drop", "arc0", "arc1", "arc2"];

export interface Particle {
  tex: ParticleTex;
  x: number;
  y: number;
  scale: number;
  alpha: number;
  rot: number;
  /** 在小人後面（暈眩的星星轉到後半圈）；目前只影響透明度，順序固定。 */
  behind?: boolean;
  /** 左右鏡像（左邊的藤）。 */
  flip?: boolean;
}

/** 身體本身的動作（套在小人與跟著它的特效上；以腳底為軸）。 */
export interface BodyMotion {
  /** 左右搖（弧度）：暈眩。 */
  rot: number;
  /** 輕微扭曲（skew.x）：隱身。 */
  skewX: number;
  /** 透明度倍率：隱身的閃爍（1 ＝ 不變）。 */
  alphaMul: number;
  /** 臉色偏綠：中毒（`null` ＝ 不染）。 */
  tint: number | null;
}

export interface StatusFrame {
  particles: Particle[];
  body: BodyMotion;
}

/** 頭頂高度（同 bodyOver 的預設身高）。 */
export const BODY_H = 34;

/** 各動作的週期與數值（原型值，寫進報告）。 */
export const ANIM = {
  flameFrameMs: 90,
  smokeEveryMs: 1600,
  smokeMs: 900,
  glintEveryMs: 2400,
  glintMs: 520,
  bubbleMs: 1200,
  starTurnMs: 1250,
  swayMs: 900,
  sway: 0.07,
  vineMs: 1300,
  concealMs: 1400,
  shimmerMs: 700,
  dropMs: 1100,
  dropFallMs: 520,
  arcMinMs: 900,
  arcSpanMs: 700,
  arcMs: 140,
} as const;

/** 中毒時身體的染色（淡綠；乘在貼圖上）。 */
export const POISON_TINT = 0xc9f2c0;

const phaseOf = (unitId: string, kind: StatusAnimKind): number => seedOf(`${unitId}:${kind}`);
/** 0～1 的相位偏移。 */
const frac = (h: number, mod = 1000): number => (h % mod) / mod;
const posMod = (a: number, m: number): number => ((a % m) + m) % m;

function burning(id: string, ms: number, out: Particle[]): void {
  const h = phaseOf(id, "burning");
  const spots: ReadonlyArray<readonly [number, number, number]> = [
    [-10, -8, 0.9],
    [10, -14, 0.8],
    [-4, -24, 0.7],
  ];
  spots.forEach(([x, y, s], i) => {
    const t = ms + (h >>> (i * 3)) % 400;
    const frame = Math.floor(t / ANIM.flameFrameMs) % 4;
    const k = 1 + 0.18 * Math.sin((t / 260) * TAU);
    out.push({ tex: `flame${frame}` as ParticleTex, x, y, scale: s * k, alpha: 0.92, rot: 0.08 * Math.sin((t / 330) * TAU) });
  });
  // 偶爾冒煙：每 1.6 秒一次，從頭頂往上飄、變大、變淡
  const local = posMod(ms + frac(h >>> 5) * ANIM.smokeEveryMs, ANIM.smokeEveryMs);
  const u = local / ANIM.smokeMs;
  if (u < 1) out.push({ tex: "smoke", x: 3 + 3 * u, y: -BODY_H + 2 - 14 * u, scale: 0.6 + 0.6 * u, alpha: 0.5 * (1 - u), rot: 0 });
}

function frozen(id: string, ms: number, out: Particle[]): void {
  // 冰面反光：一道斜光每 2.4 秒從左下掃到右上
  const h = phaseOf(id, "frozen");
  const local = posMod(ms + frac(h) * ANIM.glintEveryMs, ANIM.glintEveryMs);
  const u = local / ANIM.glintMs;
  if (u < 1) out.push({ tex: "glint", x: -12 + 24 * u, y: -6 - 26 * u, scale: 1, alpha: Math.sin(u * Math.PI) * 0.85, rot: -0.6 });
}

function poison(id: string, ms: number, out: Particle[]): void {
  const h = phaseOf(id, "poison");
  for (let i = 0; i < 3; i++) {
    const local = posMod(ms + frac(h >>> i) * ANIM.bubbleMs + (i * ANIM.bubbleMs) / 3, ANIM.bubbleMs);
    const u = local / ANIM.bubbleMs;
    const alpha = u < 0.75 ? 0.9 : ((1 - u) / 0.25) * 0.9;
    out.push({ tex: "bubble", x: -4 + i * 4 + 1.6 * Math.sin(u * TAU + i), y: -BODY_H - 3 - 13 * u, scale: 0.55 + 0.5 * u, alpha, rot: 0 });
  }
}

function stunned(id: string, ms: number, out: Particle[]): void {
  const h = phaseOf(id, "stunned");
  const head = -BODY_H - 2;
  out.push({ tex: "ring", x: 0, y: head, scale: 1, alpha: 0.7, rot: 0 });
  const base = (ms / ANIM.starTurnMs + frac(h)) * TAU;
  for (let i = 0; i < 3; i++) {
    const a = base + (i / 3) * TAU;
    const behind = Math.sin(a) < 0;
    out.push({ tex: "star", x: Math.cos(a) * 14, y: head + Math.sin(a) * 4, scale: behind ? 0.8 : 1, alpha: behind ? 0.55 : 1, rot: a, behind });
  }
}

function rooted(id: string, ms: number, out: Particle[]): void {
  // 腳邊的藤往上纏、輕輕擺（腳本身不動，靜態的藤與冰圈照舊在腳下）
  const h = phaseOf(id, "rooted");
  for (const s of [-1, 1]) {
    const sway = 0.14 * Math.sin((ms / ANIM.vineMs + frac(h >>> (s > 0 ? 4 : 0))) * TAU);
    out.push({ tex: "vine", x: s * 6, y: 0, scale: 1, alpha: 0.95, rot: s * 0.12 + sway, flip: s < 0 });
  }
}

function concealedBody(id: string, ms: number): Pick<BodyMotion, "skewX" | "alphaMul"> {
  const h = phaseOf(id, "concealed");
  const p = frac(h);
  return {
    alphaMul: 0.82 + 0.18 * Math.sin((ms / ANIM.concealMs + p) * TAU),
    skewX: 0.05 * Math.sin((ms / ANIM.shimmerMs + p) * TAU),
  };
}

function wet(id: string, ms: number, out: Particle[]): void {
  const h = phaseOf(id, "wet");
  for (let i = 0; i < 2; i++) {
    const local = posMod(ms + frac(h >>> (i * 5)) * ANIM.dropMs + i * (ANIM.dropMs / 2), ANIM.dropMs);
    const u = local / ANIM.dropFallMs;
    if (u >= 1) continue;
    const side = i === 0 ? -1 : 1;
    out.push({ tex: "drop", x: side * (8 + i), y: -22 + 20 * u * u, scale: 0.9, alpha: 0.85 * (u < 0.85 ? 1 : (1 - u) / 0.15), rot: 0 });
  }
}

/** 帶電的閃光排程：每人一個週期（0.9～1.6 秒），每個週期開頭閃 140ms；位置、形狀照「ID:第幾次」雜湊。 */
export function arcAt(id: string, ms: number): Particle | null {
  const h = phaseOf(id, "charged");
  const every = ANIM.arcMinMs + (h % ANIM.arcSpanMs);
  const t = ms + ((h >>> 9) % every);
  const n = Math.floor(t / every);
  const local = t - n * every;
  if (local >= ANIM.arcMs || local < 0) return null;
  const s = seedOf(`${id}:charged:${n}`);
  return {
    tex: `arc${s % 3}` as ParticleTex,
    x: ((s >>> 3) % 17) - 8,
    y: -8 - ((s >>> 8) % 22),
    scale: 0.8 + ((s >>> 13) % 5) / 10,
    alpha: 1 - local / ANIM.arcMs,
    rot: ((s >>> 16) % 628) / 100,
  };
}

/** 一個單位在 `ms` 時的狀態動作（`kinds` 照 `statusAnimKinds`）。 */
export function statusFrame(kinds: readonly StatusAnimKind[], unitId: string, ms: number): StatusFrame {
  const particles: Particle[] = [];
  const body: BodyMotion = { rot: 0, skewX: 0, alphaMul: 1, tint: null };
  for (const k of kinds) {
    switch (k) {
      case "burning":
        burning(unitId, ms, particles);
        break;
      case "frozen":
        frozen(unitId, ms, particles);
        break;
      case "poison":
        poison(unitId, ms, particles);
        body.tint = POISON_TINT;
        break;
      case "stunned":
        stunned(unitId, ms, particles);
        body.rot = ANIM.sway * Math.sin((ms / ANIM.swayMs + frac(phaseOf(unitId, "stunned") >>> 7)) * TAU);
        break;
      case "rooted":
        rooted(unitId, ms, particles);
        break;
      case "concealed":
        Object.assign(body, concealedBody(unitId, ms));
        break;
      case "wet":
        wet(unitId, ms, particles);
        break;
      case "charged": {
        const arc = arcAt(unitId, ms);
        if (arc !== null) particles.push(arc);
        break;
      }
    }
  }
  return { particles, body };
}

/** 靜止的畫面（prefers-reduced-motion）：不畫粒子、身體不動（靜態的身上特效照舊）。 */
export const STILL_FRAME: StatusFrame = Object.freeze({ particles: [], body: Object.freeze({ rot: 0, skewX: 0, alphaMul: 1, tint: null }) }) as StatusFrame;

/** 腿與整個人起伏的欄位（定身時鎖住：腳不動，只有上半身能動）。 */
export const LEG_KEYS: readonly PoseKey[] = ["bob", "hipN", "hipF", "kneeN", "kneeF", "liftL", "liftR"];

/** 定身：拿掉姿勢裡會動到腳的欄位（上半身照舊）。 */
export function lockLegs(pose: InkPose): InkPose {
  const out: InkPose = {};
  for (const [k, v] of Object.entries(pose) as Array<[PoseKey, number]>) if (!LEG_KEYS.includes(k)) out[k] = v;
  return out;
}

/** 冰凍（不呼吸、不做小動作）：`frozen` 狀態，或任何「跳過回合且會被火解除」的狀態（同 bodyEffects 的冰塊）。 */
export function isFrozenLook(ids: readonly string[]): boolean {
  return ids.includes("frozen") || bodyEffects(ids).frozen;
}

/** 定身（腳不動）：同 bodyEffects 的 noMove。 */
export function isRootedLook(ids: readonly string[]): boolean {
  return bodyEffects(ids).noMove;
}
