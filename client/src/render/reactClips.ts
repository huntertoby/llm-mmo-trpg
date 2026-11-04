// 受擊與結果的身體片段（Phase 6N-4；需求 docs/art/動畫移植需求第二批.md 第 4 節，方案 docs/art/動畫方案.md 2.4、2.6）。
// 全部是純函式：（種類、時間 0～1、確定性的變體）→ 一格畫面（量化後的骨架姿勢＋小人的位移、旋轉、白閃）。
// 不用 Math.random()、不讀時鐘；變體（閃避往哪一邊）用 `inkStyle.seedOf`（FNV-1a）照「戰鬥鍵:事件 seq:單位 ID:片段名」挑。
// - 受擊、重擊：沿用 6M-4 的 `humanHit`（白閃只閃剪影、仰一下、退半步再回來）；重擊多一點震動；
// - 閃避：側身一跳（往面向的左或右），殘影由繪製器另畫；
// - 格擋：舉盾（副手是盾）、橫劍（有主手武器）或手臂擋（都沒有），火花、退一小步；
// - 倒下：白閃 → 膝蓋一軟 → 側倒，最後一格和 HP 歸零的倒地圖示（paperdoll `drawFigurePose` 的 downed）完全一樣；
// - 陷阱夾住：夾子合上那一刻白閃、身體一縮、膝蓋彎，之後腳定住；
// - 異形：受擊、重擊、倒下用 6M-2 的通用片段；閃避、格擋退回受擊的輕版（沒有白閃、幅度一半）。
// 座標照 inkPose.ts（側面朝東；`arm` 負＝往前上抬）；位移單位是紙娃娃的虛擬像素，繪製器再乘縮放。
import type { Facing } from "../api/types";
import type { GearItem } from "./appearance";
import { CREATURE_CLIPS, quantizeCreaturePose, type CreaturePose } from "./creaturePose";
import { mixPose, type InkPose } from "./inkPose";
import { seedOf } from "./inkStyle";
import { easeInOut, HUMAN_HIT_MS, humanHit, quantizeFlash, quantizePose } from "./motionClips";
import { frontize, weaponClassOf } from "./skillClips";

export type ReactClip = "hit" | "heavy" | "dodge" | "block" | "down" | "trapped";
export const REACT_CLIPS: readonly ReactClip[] = ["hit", "heavy", "dodge", "block", "down", "trapped"];

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

/** 閃避往哪一邊（1 ＝ 面向的右手邊、-1 ＝ 左手邊）：照「戰鬥鍵:seq:單位:dodge」的雜湊，重播、重新整理都一樣。 */
export function dodgeSide(battleKey: string, seq: number, unitId: string): 1 | -1 {
  return seedOf(`${battleKey}:${seq}:${unitId}:dodge`) % 2 === 0 ? 1 : -1;
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
const q = (v: number) => Math.round(v * 20) / 20;
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

/** 受擊（6M-4）；重擊多一點震動：退得多一點、退的時候抖兩下、白閃久一點。 */
function hit(t: number, heavy: boolean): ReactFrame {
  const h = humanHit(t);
  if (!heavy) return frame(h.pose, { flash: h.flash, back: h.knock });
  const shudder = Math.sin(t * Math.PI * 9) * 1.6 * (1 - t);
  const pose = { lean: -0.42 * Math.sin(clamp(t * 2) * Math.PI), arm: -0.7 * Math.sin(t * Math.PI), kneeN: 0.3 * Math.sin(t * Math.PI) };
  return frame(pose, { flash: Math.max(0, 1 - t * 3) * 0.95, back: h.knock * 1.3 + shudder });
}

/** 閃避：蹲一下 → 往側邊一跳（離地 4）→ 落地回原位；身體往跳的反方向斜，殘影留在原地淡掉。 */
function dodge(t: number, side: 1 | -1): ReactFrame {
  const out = Math.sin(seg(t, 0, 0.75) * Math.PI); // 跳出去再回來
  const pose = mixPose({ kneeN: 0.5, kneeF: 0.5, bob: 1.5 }, { lean: -0.25, hipN: 0.35, hipF: -0.3, kneeF: 0.5, armF: -0.9, arm: 0.4, bob: -0.5 }, easeInOut(seg(t, 0.1, 0.4)));
  const land = mixPose(pose, {}, easeInOut(seg(t, 0.6, 1)));
  return frame(land, { side: side * 14 * out, air: 5 * Math.sin(seg(t, 0.1, 0.6) * Math.PI), back: 4 * out, ghost: 0.45 * (1 - seg(t, 0.15, 0.85)) * (t > 0.08 ? 1 : 0), rotation: -side * 0.08 * out });
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
  return frame(pose, { back: 3 * Math.sin(seg(t, 0.15, 0.8) * Math.PI), flash: Math.max(0, 1 - t * 6) * 0.35, spark: t >= 0.15 && t < 0.6 ? 1 - seg(t, 0.15, 0.6) : 0 });
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
  return frame(pose, { flash: t >= 0.25 ? Math.max(0, 1 - (t - 0.25) * 6) * 0.85 : 0, back: 1.5 * Math.sin(snap * Math.PI) });
}

export interface ReactOpts {
  guard?: GuardKind;
  side?: 1 | -1;
}

/** 片段 `clip` 播到 `t`（0～1）的畫面（時間量化成 24 格，同 skillClips）。 */
export function reactFrame(clip: ReactClip, t: number, opts: ReactOpts = {}): ReactFrame {
  const k = step(t);
  switch (clip) {
    case "hit":
      return hit(k, false);
    case "heavy":
      return hit(k, true);
    case "dodge":
      return dodge(k, opts.side ?? 1);
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
  if (clip === "heavy") return quantizeCreaturePose({ ...p, dx: (p.dx ?? 0) * 1.3 + Math.sin(k * Math.PI * 9) * 1.2 * (1 - k), flash: Math.min(1, (p.flash ?? 0) * 1.1) });
  return quantizeCreaturePose({ dx: (p.dx ?? 0) * 0.5, rot: (p.rot ?? 0) * 0.5, sx: 1 + ((p.sx ?? 1) - 1) * 0.5, sy: 1 + ((p.sy ?? 1) - 1) * 0.5 });
}

/** 倒地的異形持續的樣子（倒下片段的最後一格；6N-4 起重畫時照這個畫，倒下後不會跳回站著）。 */
export function downedCreaturePose(): CreaturePose {
  return creatureReact("down", 1);
}
