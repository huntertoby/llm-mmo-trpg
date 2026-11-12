// 受擊與結果的身體片段（Phase 6N-4；需求 docs/art/動畫移植需求第二批.md 第 4 節，方案 docs/art/動畫方案.md 2.4、2.6）。
// 全部是純函式：（種類、時間 0～1、確定性的變體）→ 一格畫面（量化後的骨架姿勢＋小人的位移、旋轉、白閃）。
// 不用 Math.random()、不讀時鐘；變體（閃避往哪一邊）用 `attackVariants.variantHash`（FNV-1a＋fmix32）照「戰鬥鍵:事件 seq:單位 ID:片段名」挑。
// - 受擊、重擊：沿用 6M-4 的 `humanHit`（白閃只閃剪影、仰一下、退半步再回來）；重擊多一點震動；
// - 閃避：側身一跳（往面向的左或右），殘影由繪製器另畫；
// - 格擋：舉盾（副手是盾）、橫劍（有主手武器）或手臂擋（都沒有），火花、退一小步；
// - 倒下：白閃 → 膝蓋一軟 → 側倒，最後一格和 HP 歸零的倒地圖示（paperdoll `drawFigurePose` 的 downed）完全一樣；
// - 陷阱夾住：夾子合上那一刻白閃、身體一縮、膝蓋彎，之後腳定住；
// - 異形：受擊、重擊、倒下用 6M-2 的通用片段；閃避、格擋退回受擊的輕版（沒有白閃、幅度一半）。
// 座標照 inkPose.ts（側面朝東；`arm` 負＝往前上抬）；位移單位是紙娃娃的虛擬像素，繪製器再乘縮放。
import type { Facing } from "../api/types";
import type { GearItem } from "./appearance";
import { CREATURE_CLIPS, CREATURE_HIT_FLASH, quantizeCreaturePose, type CreaturePose } from "./creaturePose";
import { mixPose, type InkPose } from "./inkPose";
import { variantHash } from "./attackVariants";
import { easeInOut, HUMAN_HIT_FLASH, HUMAN_HIT_MS, humanHit, quantizeFlash, quantizePose } from "./motionClips";
import { frontize, weaponClassOf } from "./skillClips";

export type ReactClip = "hit" | "heavy" | "dodge" | "block" | "down" | "trapped";
export const REACT_CLIPS: readonly ReactClip[] = ["hit", "heavy", "dodge", "block", "down", "trapped"];

/** 人形重擊白閃的峰值。 */
export const HEAVY_HIT_FLASH = 0.95;
/** 格擋白閃的峰值（很淡）。 */
export const BLOCK_FLASH = 0.35;
/** 異形重擊：受擊白閃 × 1.1（峰值 0.99）。 */
export const CREATURE_HEAVY_GAIN = 1.1;

/**
 * OCL-1b（Q6）：人形片段白閃的峰值（外框閃白 k 的分母，由白閃的呼叫點傳給外框）。沒有白閃的片段（閃避）回 0。
 * 每一列都由 `ocl1Playback.test.ts` 鎖住「片段裡最大的白閃 ＝ 這個峰值」。
 */
export function reactFlashPeak(clip: ReactClip): number {
  switch (clip) {
    case "heavy":
      return HEAVY_HIT_FLASH;
    case "block":
      return BLOCK_FLASH;
    case "dodge":
      return 0;
    default:
      return HUMAN_HIT_FLASH; // hit、down（開頭的受擊）、trapped
  }
}

/** OCL-1b（Q6）：異形（含頭目）片段白閃的峰值：受擊 0.9、重擊 0.99；閃避、格擋沒有白閃（0）；倒下不畫外框（0）。 */
export function creatureReactFlashPeak(clip: ReactClip): number {
  if (clip === "hit" || clip === "trapped") return CREATURE_HIT_FLASH;
  if (clip === "heavy") return Math.min(1, CREATURE_HIT_FLASH * CREATURE_HEAVY_GAIN);
  return 0;
}

/** 每個片段的基本長度（毫秒，正常速度；乘播放速度）。受擊同 6M-4 的 360。 */
export const REACT_MS: Readonly<Record<ReactClip, number>> = {
  hit: HUMAN_HIT_MS,
  heavy: 440,
  dodge: 380,
  block: 340,
  down: 640,
  trapped: 400,
};

/** 格擋的方式：舉盾、橫劍（主手武器）、手臂。 */
export type GuardKind = "shield" | "weapon" | "arm";

/** 副手是盾 → 舉盾；主手是起手對照表上的武器 → 橫劍（武器）；空手、符紙、拂塵、傀儡線、法球 → 手臂擋。 */
export function guardOf(main: GearItem | undefined, off: GearItem | undefined): GuardKind {
  if (off?.kind.startsWith("shield") === true) return "shield";
  const cls = weaponClassOf(main, off);
  return cls === "bare" || cls === "orb" ? "arm" : "weapon";
}

/**
 * 閃避往哪一邊（1 ＝ 面向的右手邊、-1 ＝ 左手邊）：照「戰鬥鍵:seq:單位:dodge」的雜湊，重播、重新整理都一樣。
 * 6N-8（6N-7 待決 4）：改用 `variantHash`（多一道 fmix32），seq 間隔 2 時不再八成連續同一邊。
 */
export function dodgeSide(battleKey: string, seq: number, unitId: string): 1 | -1 {
  return variantHash(`${battleKey}:${seq}:${unitId}:dodge`) % 2 === 0 ? 1 : -1;
}

/** 一格畫面：骨架姿勢＋小人的位移（虛擬像素）與旋轉。 */
export interface ReactFrame {
  pose: InkPose;
  /** 白閃（0～1，已量化）。 */
  flash: number;
  /** 往面向的反方向退（虛擬像素）。 */
  back: number;
  /** 往面向的右手邊（閃避；虛擬像素）。 */
  side: number;
  /** 離地高度（虛擬像素，正＝往上）。 */
  air: number;
  /** 小人以腳底為軸的旋轉（弧度，順時針為正）。 */
  rotation: number;
  /** 額外位移（倒下時移到倒地圖示的位置；虛擬像素）。 */
  dx: number;
  dy: number;
  /** 倒下的進度（0 站著 → 1 躺平）；繪製器照它把透明度、地上影子換成倒地的樣子。 */
  fall: number;
  /** 閃避的殘影不透明度（0 ＝ 不畫）。 */
  ghost: number;
  /** 格擋的火花強度（0 ＝ 不畫）。 */
  spark: number;
}

const clamp = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t);
const seg = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
const q = (v: number) => Math.round(v * 20) / 20 + 0; // +0：不留 -0
const CLIP_STEPS = 24;
const step = (t: number) => Math.round(clamp(t) * CLIP_STEPS) / CLIP_STEPS;

/** paperdoll.ts 的 HP 歸零倒地：先平移 (-27, -11) 再順時針轉 90°（頭朝右）。倒下片段的最後一格照這個。 */
export const DOWNED_OFFSET = { x: -27, y: -11 } as const;
export const DOWNED_ROTATION = Math.PI / 2;

const BLANK: Omit<ReactFrame, "pose"> = { flash: 0, back: 0, side: 0, air: 0, rotation: 0, dx: 0, dy: 0, fall: 0, ghost: 0, spark: 0 };

function frame(pose: InkPose, more: Partial<Omit<ReactFrame, "pose">>): ReactFrame {
  const clean: InkPose = {};
  for (const [k, v] of Object.entries(quantizePose(frontize(pose))) as Array<[keyof InkPose, number]>) if (v !== 0) clean[k] = v; // 0 的欄位不寫（站好＝ {}，貼圖鍵和站著的一樣）
  const out: ReactFrame = { ...BLANK, pose: clean };
  for (const [k, v] of Object.entries(more) as Array<[keyof Omit<ReactFrame, "pose">, number]>) out[k] = k === "flash" ? quantizeFlash(v) : k === "rotation" ? Math.round(v * 100) / 100 : q(v);
  return out;
}

// ---- 6N-7：受擊、閃避的變體（方案 2.10 第 5 點：受擊 3、閃避 3） ----------------------------
// 變體只改姿勢與位移；長度（`REACT_MS`）、開始的時間（命中點）、白閃、殘影的淡出曲線都和第一個一樣，
// 所以 6N-5 的停頓、格擋、暴擊強化照舊。挑法：`variantHash(「戰鬥鍵:事件 seq:受擊者 ID:hit|dodge」)` ÷ 3。

/** 受擊的變體（重擊同一套，多一點震動）：第一個 ＝ 6N-7 以前的「後仰」。 */
export const HIT_VARIANTS = [
  { id: "hit_back", zh: "後仰" },
  { id: "hit_side", zh: "側彎" },
  { id: "hit_bend", zh: "彎腰" },
] as const;
/** 閃避的變體：第一個 ＝ 6N-7 以前的「側跳」。 */
export const DODGE_VARIANTS = [
  { id: "dodge_side", zh: "側跳" },
  { id: "dodge_back", zh: "後跳" },
  { id: "dodge_duck", zh: "蹲低" },
] as const;

/** 受擊、閃避挑哪一個變體：鍵 ＝「戰鬥鍵:seq:受擊者 ID:hit」（重擊也用 `hit`）或「…:dodge」。 */
export function reactVariantKey(battleKey: string, seq: number, unitId: string, clip: "hit" | "dodge"): string {
  return `${battleKey}:${seq}:${unitId}:${clip}`;
}
export function reactVariant(battleKey: string, seq: number, unitId: string, clip: "hit" | "dodge"): number {
  const n = clip === "hit" ? HIT_VARIANTS.length : DODGE_VARIANTS.length;
  return variantHash(reactVariantKey(battleKey, seq, unitId, clip)) % n;
}

/** 受擊（6M-4）；重擊多一點震動：退得多一點、退的時候抖兩下、白閃久一點。`variant`：0 後仰、1 側彎、2 彎腰。 */
function hit(t: number, heavy: boolean, variant = 0): ReactFrame {
  const h = humanHit(t);
  const k = heavy ? 1.4 : 1;
  const flash = heavy ? Math.max(0, 1 - t * 3) * HEAVY_HIT_FLASH : h.flash;
  const shudder = heavy ? Math.sin(t * Math.PI * 9) * 1.6 * (1 - t) : 0;
  const bump = Math.sin(clamp(t * 2) * Math.PI); // 0 → 1 → 0（前半）
  const arc = Math.sin(t * Math.PI);
  if (variant === 1) {
    // 側彎：上半身往被打的那一側歪（小人以腳底為軸轉一點）、兩手甩開，往側邊滑一點
    const pose = { lean: -0.12 * k * bump, arm: 0.45 * k * arc, armF: -0.7 * k * arc, hipN: -0.15 * arc, kneeF: 0.25 * k * arc };
    return frame(pose, { flash, back: h.knock * 0.6 * k + shudder, side: -3 * k * bump, rotation: -0.13 * k * bump });
  }
  if (variant === 2) {
    // 彎腰：被打中肚子，往前彎、膝蓋彎、雙手往內收，往後退一點
    const pose = { lean: 0.38 * k * bump, arm: 0.35 * arc, elbow: -0.6 * arc, armF: 0.3 * arc, elbowF: -0.6 * arc, kneeN: 0.35 * k * arc, kneeF: 0.3 * k * arc, bob: 2 * k * arc };
    return frame(pose, { flash, back: h.knock * 0.7 * k + shudder });
  }
  if (!heavy) return frame(h.pose, { flash: h.flash, back: h.knock });
  const pose = { lean: -0.42 * bump, arm: -0.7 * arc, kneeN: 0.3 * arc };
  return frame(pose, { flash, back: h.knock * 1.3 + shudder });
}

/** 殘影的淡出（三種閃避都一樣，6N-5 的第二層殘影照它）。 */
const dodgeGhost = (t: number): number => 0.45 * (1 - seg(t, 0.15, 0.85)) * (t > 0.08 ? 1 : 0);

/**
 * 閃避：0 側跳（蹲一下 → 往側邊一跳、離地 5 → 落地回原位；身體往跳的反方向斜）、1 後跳（往後跳開 12、離地 6）、
 * 2 蹲低（整個人往下一縮、頭往前低，原地不動）。殘影都留在原地淡掉。
 */
function dodge(t: number, side: 1 | -1, variant = 0): ReactFrame {
  const out = Math.sin(seg(t, 0, 0.75) * Math.PI); // 跳出去再回來
  const ghost = dodgeGhost(t);
  if (variant === 1) {
    const pose = mixPose({ kneeN: 0.5, kneeF: 0.5, bob: 1.5 }, { lean: 0.2, hipN: 0.5, hipF: 0.2, kneeN: 0.6, kneeF: 0.9, arm: 0.5, armF: 0.4, bob: -0.5 }, easeInOut(seg(t, 0.1, 0.4)));
    const land = mixPose(pose, {}, easeInOut(seg(t, 0.6, 1)));
    return frame(land, { back: 12 * out, air: 6 * Math.sin(seg(t, 0.1, 0.6) * Math.PI), ghost });
  }
  if (variant === 2) {
    const duck = easeInOut(seg(t, 0.05, 0.3)) * (1 - easeInOut(seg(t, 0.6, 1)));
    const pose = mixPose({}, { kneeN: 1.5, kneeF: 1.3, hipN: 0.8, hipF: 0.6, bob: 8, lean: 0.4, arm: -0.6, elbow: -1.2, armF: -0.6, elbowF: -1.2 }, duck);
    return frame(pose, { back: 2 * out, ghost });
  }
  const pose = mixPose({ kneeN: 0.5, kneeF: 0.5, bob: 1.5 }, { lean: -0.25, hipN: 0.35, hipF: -0.3, kneeF: 0.5, armF: -0.9, arm: 0.4, bob: -0.5 }, easeInOut(seg(t, 0.1, 0.4)));
  const land = mixPose(pose, {}, easeInOut(seg(t, 0.6, 1)));
  return frame(land, { side: side * 14 * out, air: 5 * Math.sin(seg(t, 0.1, 0.6) * Math.PI), back: 4 * out, ghost, rotation: -side * 0.08 * out });
}

/** 格擋的姿勢：舉盾（另一隻手往前抬）、橫劍（主手武器豎在身前）、手臂（雙臂交叉擋在臉前）。 */
const GUARD_POSE: Readonly<Record<GuardKind, InkPose>> = {
  shield: { armF: -1.45, elbowF: -0.5, lean: -0.08, kneeN: 0.2 },
  // 不給 `wpn`（照武器的預設握法跟著手轉；給了的話開頭、結尾會從 0 度跳過去）：主手往前上抬、手肘彎，武器擋在身前
  weapon: { arm: -1.25, elbow: -1.0, armF: -0.5, lean: -0.08, kneeN: 0.2 },
  arm: { arm: -1.2, elbow: -1.7, armF: -1.3, elbowF: -1.5, lean: -0.12, kneeN: 0.2 },
};

/** 格擋：很快擋起來 → 被打中那一下迸火花、退一小步 → 放下。白閃很淡。 */
function block(t: number, guard: GuardKind): ReactFrame {
  const up = easeInOut(seg(t, 0, 0.2)) * (1 - easeInOut(seg(t, 0.7, 1)));
  const pose = mixPose({}, GUARD_POSE[guard], up);
  return frame(pose, { back: 3 * Math.sin(seg(t, 0.15, 0.8) * Math.PI), flash: Math.max(0, 1 - t * 6) * BLOCK_FLASH, spark: t >= 0.15 && t < 0.6 ? 1 - seg(t, 0.15, 0.6) : 0 });
}

/** 膝蓋一軟的姿勢（雙膝往前跪、身體下沉往前垂）。 */
const BUCKLE_POSE: Readonly<InkPose> = Object.freeze({ kneeN: 1.4, kneeF: 1.2, hipN: 0.7, hipF: 0.5, bob: 7, lean: 0.25, arm: 0.3, armF: 0.35 });

/**
 * 倒下：0～0.22 受擊（白閃、往後彈）；0.22～0.55 膝蓋一軟、往下沉；0.55～1 側倒，
 * 最後一格＝倒地圖示（站好的貼圖、轉 90°、平移 (-27, -11)、不帶姿勢）。
 */
function down(t: number): ReactFrame {
  const h = humanHit(seg(t, 0, 0.3) * 0.6);
  const buckle = easeInOut(seg(t, 0.22, 0.55));
  const fall = easeInOut(seg(t, 0.55, 1));
  let pose = mixPose(h.pose, BUCKLE_POSE, buckle);
  pose = mixPose(pose, {}, fall);
  return frame(pose, {
    flash: h.flash,
    back: h.knock * (1 - buckle),
    rotation: DOWNED_ROTATION * fall,
    dx: DOWNED_OFFSET.x * fall,
    dy: DOWNED_OFFSET.y * fall,
    fall,
  });
}

/** 陷阱夾住：夾子合上那一刻（0.25）白閃、身體一縮、膝蓋彎，之後腳定住、上半身晃一下。 */
function trapped(t: number): ReactFrame {
  const snap = seg(t, 0.2, 0.32);
  const hold = easeInOut(seg(t, 0.25, 0.45)) * (1 - easeInOut(seg(t, 0.75, 1))); // 最後站直（腳照樣定在那格）
  const wobble = Math.sin(seg(t, 0.3, 1) * Math.PI * 3) * 0.12 * (1 - t);
  const pose = mixPose({}, { kneeN: 0.6, kneeF: 0.5, bob: 2.5, lean: 0.18 + wobble, arm: -0.6, armF: -0.7 }, hold);
  return frame(pose, { flash: t >= 0.25 ? Math.max(0, 1 - (t - 0.25) * 6) * HUMAN_HIT_FLASH : 0, back: 1.5 * Math.sin(snap * Math.PI) });
}

export interface ReactOpts {
  guard?: GuardKind;
  side?: 1 | -1;
  /** 受擊、重擊、閃避的變體（6N-7，`reactVariant`）；沒給 ＝ 第一個。 */
  variant?: number;
}

/** 片段 `clip` 播到 `t`（0～1）的畫面（時間量化成 24 格，同 skillClips）。 */
export function reactFrame(clip: ReactClip, t: number, opts: ReactOpts = {}): ReactFrame {
  const k = step(t);
  switch (clip) {
    case "hit":
      return hit(k, false, opts.variant);
    case "heavy":
      return hit(k, true, opts.variant);
    case "dodge":
      return dodge(k, opts.side ?? 1, opts.variant);
    case "block":
      return block(k, opts.guard ?? "arm");
    case "down":
      return down(k);
    case "trapped":
      return trapped(k);
  }
}

/**
 * 往面向的右手邊 `d`（虛擬像素）：朝東時右手邊是南、朝西是北（有透視，走 0.8；只走一半時側跳看不太出來）；朝南是西、朝北是東。
 */
export function sideOffset(facing: Facing, d: number): { x: number; y: number } {
  if (facing === "east") return { x: 0, y: d * 0.8 };
  if (facing === "west") return { x: 0, y: -d * 0.8 };
  return { x: facing === "south" ? -d : d, y: 0 };
}

/**
 * 異形（沒有骨架）的版本：受擊、重擊、倒下用 6M-2 的通用片段；閃避、格擋是受擊的輕版（幅度一半、沒有白閃）。
 * 倒下片段的最後一格不變淡（透明度交給倒地的外觀），和重畫後的倒地圖示一樣。
 */
export function creatureReact(clip: ReactClip, t: number): CreaturePose {
  const k = step(t);
  if (clip === "down") return quantizeCreaturePose({ ...CREATURE_CLIPS.fall.pose(k), alpha: 1 });
  const p = CREATURE_CLIPS.hit.pose(k);
  if (clip === "hit" || clip === "trapped") return quantizeCreaturePose(p);
  if (clip === "heavy") return quantizeCreaturePose({ ...p, dx: (p.dx ?? 0) * 1.3 + Math.sin(k * Math.PI * 9) * 1.2 * (1 - k), flash: Math.min(1, (p.flash ?? 0) * CREATURE_HEAVY_GAIN) });
  // QK-4：受擊改成分部件片段後沒有整隻位移可以減半；閃避、格擋＝整隻往後讓半步再回來（沒有白閃）
  return quantizeCreaturePose({ dx: -3 * Math.sin(Math.PI * k), rot: -0.06 * Math.sin(Math.PI * k) });
}

/** 倒地的異形持續的樣子（倒下片段的最後一格；6N-4 起重畫時照這個畫，倒下後不會跳回站著）。 */
export function downedCreaturePose(): CreaturePose {
  return creatureReact("down", 1);
}

// ---- 6N-5：格擋成功的攻擊者被彈開、復活、勝利 ------------------------------------------

/** 6N-5 的片段：被彈開半步（格擋成功時的攻擊者）、復活（從倒地站起）、勝利（舉手或收刀）。 */
export type ResultClip = "recoil" | "rise" | "victory";
export const RESULT_CLIPS: readonly ResultClip[] = ["recoil", "rise", "victory"];

/** 每個片段的基本長度（毫秒，正常速度；乘播放速度）。 */
export const RESULT_MS: Readonly<Record<ResultClip, number>> = { recoil: 300, rise: 520, victory: 520 };

/** 勝利的兩種樣子：舉手（主手高舉）、收刀（武器放低、點頭）。 */
export type VictoryPose = "raise" | "sheathe";

/** 勝利挑哪一種：照「戰鬥鍵:battle_ended 的 seq:單位:victory」的雜湊（6N-8 起 `variantHash`），重播、重新整理都一樣。 */
export function victoryPose(battleKey: string, seq: number, unitId: string): VictoryPose {
  return variantHash(`${battleKey}:${seq}:${unitId}:victory`) % 2 === 0 ? "raise" : "sheathe";
}

/** 被彈開半步：一下往後退 8、上半身往後仰、手被甩開，再站回原位；沒有白閃。 */
function recoil(t: number): ReactFrame {
  const push = t < 0.3 ? easeInOut(t / 0.3) : 1 - easeInOut(seg(t, 0.3, 1));
  return frame(mixPose({}, { lean: -0.3, arm: 0.35, armF: 0.3, kneeN: 0.25, hipF: 0.2 }, push), { back: 8 * push });
}

/**
 * 復活：倒下片段倒過來——0～0.5 從倒地圖示（轉 90°、平移 (-27, -11)）翻回跪姿，0.5～0.95 從跪姿站直。
 * 第一格＝倒下片段的最後一格（接在倒地圖示上不跳一下），最後一格＝站好。
 */
function rise(t: number): ReactFrame {
  const fall = 1 - easeInOut(seg(t, 0, 0.5));
  const stand = easeInOut(seg(t, 0.5, 0.95));
  const pose = mixPose(mixPose(BUCKLE_POSE, {}, fall), {}, stand);
  return frame(pose, { rotation: DOWNED_ROTATION * fall, dx: DOWNED_OFFSET.x * fall, dy: DOWNED_OFFSET.y * fall, fall });
}

/**
 * 勝利的姿勢（最高點）。武器角度 `wpn`：絕對角度＝ arm＋elbow＋wpn（0 朝上、π 朝下）——舉手時武器朝天，收刀時刀尖朝下。
 * 從 `VICTORY_REST`（主手武器的預設握法 0.75，同 skillClips 的 REST）內插，開頭結尾不會跳。
 */
const VICTORY_POSE: Readonly<Record<VictoryPose, InkPose>> = {
  raise: { arm: -2.9, wpn: 2.9, armF: -2.6, elbowF: 0.3, lean: -0.08, bob: -1 },
  sheathe: { arm: 0.35, elbow: -0.2, wpn: 2.95, armF: 0.25, lean: 0.22, kneeN: 0.12 },
};
const VICTORY_REST: Readonly<InkPose> = { wpn: 0.75 };

/** 勝利：0～0.3 抬到最高點（舉手時小跳一下），停住，0.8～1 放回站好（第一格、最後一格＝站好）。 */
function victory(t: number, kind: VictoryPose): ReactFrame {
  const up = easeInOut(seg(t, 0, 0.3)) * (1 - easeInOut(seg(t, 0.8, 1)));
  const air = kind === "raise" ? 3 * Math.sin(seg(t, 0.12, 0.45) * Math.PI) : 0;
  return frame(up <= 0 ? {} : mixPose(VICTORY_REST, VICTORY_POSE[kind], up), { air });
}

/** 片段 `clip` 播到 `t`（0～1）的畫面（時間量化成 24 格）。 */
export function resultFrame(clip: ResultClip, t: number, kind: VictoryPose = "raise"): ReactFrame {
  const k = step(t);
  if (clip === "recoil") return recoil(k);
  if (clip === "rise") return rise(k);
  return victory(k, kind);
}

/** 復活的綠光圈（0～1）：0.15 起從腳下擴開，0.95 前淡掉。 */
export function riseRing(t: number): number {
  const k = step(t);
  return k < 0.15 || k >= 0.95 ? 0 : q(Math.sin(seg(k, 0.15, 0.95) * Math.PI));
}

/**
 * 異形（沒有骨架）：被彈開＝受擊的輕版（沒有白閃）；復活＝倒下片段倒著播（第一格＝倒地的樣子）；
 * 勝利＝撲的小跳版（往前只走三成）。
 */
export function creatureResult(clip: ResultClip, t: number): CreaturePose {
  const k = step(t);
  if (clip === "rise") return quantizeCreaturePose({ ...CREATURE_CLIPS.fall.pose(1 - k), alpha: 1 });
  // QK-4：被彈開＝整隻往後退再回來；勝利＝原地小跳（整隻欄位，疊在站好的 Q 版身上）
  if (clip === "recoil") return quantizeCreaturePose({ dx: -4.2 * Math.sin(Math.PI * k), rot: -0.1 * Math.sin(Math.PI * k) });
  return quantizeCreaturePose({ dy: -4 * Math.sin(Math.PI * k), sy: 1 + 0.04 * Math.sin(Math.PI * k) });
}
